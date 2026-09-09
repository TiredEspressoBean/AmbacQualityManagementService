"""Sourcing & production requirements — what open demand needs that must be bought or
made, with lead-time-driven order-by dates. Feeds the "source it / produce it" report so
purchasing/receiving and production know what to act on and by when.

Three lanes:
  - source  : short purchased Materials (BUY lines) — order-by = need-by − lead time.
  - produce : open pegged child work orders (MAKE lines) — what production must run.
  - tooling : fixtures not yet on hand (quantity 0) that upcoming work needs.

Need-by uses the live schedule's start of the consuming step when available, else the work
order's expected start, else the horizon start.
"""
from __future__ import annotations

from datetime import timedelta

from Tracker.services.mes.bom import buy_line_item

# On-hand = usable stock. Incoming = inbound, not-yet-usable receipts. The two must be
# disjoint or accepted stock double-counts (it's both "on hand" and "promised"): incoming
# therefore excludes the on-hand statuses as well as the terminal ones.
_ON_HAND_LOT_STATUSES = ('ACCEPTED', 'IN_USE')
_TERMINAL_LOT_STATUSES = ('CONSUMED', 'SCRAPPED', 'REJECTED')
_NOT_INCOMING_LOT_STATUSES = _ON_HAND_LOT_STATUSES + _TERMINAL_LOT_STATUSES


def work_order_material_requirements(work_order) -> dict:
    """Top-level material requirements for one work order — the "what this job needs"
    readout (picklist-*lite*: components, quantities, consumed-at-step, and a shortage
    flag; NO bins / lot picking / reservations — that's the ERP/WMS's job).

    Explodes only the immediate released ASSEMBLY BOM (one level): MAKE sub-components are
    their own work orders with their own requirements. Coverage is net-vs-on-hand + promised
    (same "gate and flag" the material gate uses), not a reservation.
    """
    from decimal import Decimal
    from django.db.models import Sum
    from Tracker.models import (
        BOM, BOMLine, MaterialLot, Parts, PartsStatus, WorkOrder,
    )
    from Tracker.services.scheduling.data import get_schedule_horizon

    pt_id = work_order.process.part_type_id if work_order.process_id else None
    if pt_id is None:
        return {'rows': []}
    # The effective production BOM is the latest RELEASED one — NOT gated on
    # is_current_version, since an open DRAFT revision makes the released row
    # non-current while it's still what the floor builds to.
    bom = (BOM.objects.filter(part_type_id=pt_id, bom_type='ASSEMBLY',
           status='RELEASED').order_by('-version').first())
    if bom is None:
        return {'rows': []}

    # For "when to order" on short BUY lines: need-by = the live schedule's start of the
    # consuming step (else WO start, else horizon), order-by = need-by − purchase lead time.
    tenant = work_order.tenant
    h_date = get_schedule_horizon(tenant).start.date()
    sched = _active_schedule_starts(tenant)
    wo_need = sched.get((work_order.id, None)) or work_order.expected_start or h_date

    live_wo = ('PENDING', 'IN_PROGRESS', 'ON_HOLD', 'WAITING_FOR_OPERATOR')
    rows = []
    # tenant-safe: `bom` is a tenant-scoped row; its lines belong to the same tenant.
    for line in (BOMLine.objects.filter(bom=bom)
                 .select_related('component_type', 'material', 'consumed_at_step')
                 .order_by('line_number')):
        required = float(Decimal(str(line.quantity)) * Decimal(work_order.quantity))
        step = line.consumed_at_step.name if line.consumed_at_step_id else None
        row = {
            'source': line.source,
            'quantity': required,
            'unit_of_measure': line.unit_of_measure or '',
            'consumed_at_step': step,
            'is_optional': line.is_optional,
            # Present on every row so the response shape is uniform; the BUY branch
            # below fills them in. A MAKE line is built, not bought, so it has neither
            # a purchase kind nor a stocking buffer.
            'buy_kind': None,
            'safety_stock': 0.0,
        }

        buy = buy_line_item(line)
        if buy is not None:
            # Stock hangs off `material` for a raw Material and `material_type` for a
            # buyable PartType — same lot table, different column.
            # `tenant=` stays spelled out on each call rather than folded into the dict:
            # the tenant-scoping lint reads these literally, and a scoping filter that
            # only a human can see is exactly the kind it exists to catch.
            item_q = {f'{buy.lot_field}_id': buy.id}
            on_hand = float(MaterialLot.objects.filter(
                tenant=tenant, **item_q, status__in=_ON_HAND_LOT_STATUSES)
                .aggregate(s=Sum('quantity_remaining'))['s'] or 0)
            incoming = float(MaterialLot.objects.filter(
                tenant=tenant, **item_q,
                promised_date__isnull=False, quantity_remaining__gt=0)
                .exclude(status__in=_NOT_INCOMING_LOT_STATUSES)  # not already on-hand or terminal
                .aggregate(s=Sum('quantity_remaining'))['s'] or 0)
            # Safety stock is held back from planning, so coverage nets against what is
            # free to commit — not the whole shelf. `on_hand` still reports the physical
            # count; a report that quietly shrinks it would have the picker and the
            # planner disagreeing about the same bin.
            safety = buy.safety_stock
            short = max(0.0, required - (on_hand - safety) - incoming)
            lead = buy.lead_time_days
            need_by = sched.get((work_order.id, line.consumed_at_step_id)) or wo_need
            order_by = (need_by - timedelta(days=lead)) if lead else need_by
            row.update({
                'component': buy.name, 'kind': 'BUY',
                'buy_kind': buy.kind,
                'on_hand': on_hand, 'incoming': incoming,
                'safety_stock': safety,
                'short_qty': short,
                'status': 'short' if short > 0 else 'ok',
                # "When to order" — only meaningful when there's a shortfall to buy.
                'lead_time_days': lead,
                'need_by': need_by if short > 0 else None,
                'order_by': order_by if short > 0 else None,
            })
        elif line.source == 'MAKE' and line.component_type_id:
            comp = line.component_type
            on_hand = float(Parts.objects.filter(
                tenant=tenant, part_type_id=comp.id, part_status=PartsStatus.IN_STOCK).count())
            pegged = float(WorkOrder.objects.filter(
                tenant=tenant, pegged_to_workorder=work_order, pegged_to_bom_line=line,
                workorder_status__in=live_wo).aggregate(s=Sum('quantity'))['s'] or 0)
            short = max(0.0, required - on_hand - pegged)
            row.update({
                'component': comp.name, 'kind': 'MAKE',
                'on_hand': on_hand, 'incoming': pegged,  # 'incoming' = qty on live child WOs
                'short_qty': short,
                'status': 'ok' if short <= 0 else ('building' if pegged > 0 else 'short'),
                # Made in-house, not purchased — no buy lead time / order-by.
                'lead_time_days': None, 'need_by': None, 'order_by': None,
            })
        else:
            # Misconfigured line (source set but no matching component) — surface it plainly.
            row.update({'component': '(unset)', 'kind': line.source or '?',
                        'on_hand': 0.0, 'incoming': 0.0, 'short_qty': required,
                        'status': 'short',
                        'lead_time_days': None, 'need_by': None, 'order_by': None})
        rows.append(row)

    return {'rows': rows}


def _active_schedule_starts(tenant):
    """{(work_order_id, step_id): earliest scheduled start date} on the live schedule."""
    from Tracker.models import ScheduledTask, ScheduleResult

    active = (ScheduleResult.objects.filter(tenant=tenant, is_active=True, is_draft=False)
              .order_by('-created_at').first())
    if active is None:
        return {}
    out: dict = {}
    # tenant-safe: scoped via schedule=active (the tenant's own active ScheduleResult).
    for t in (ScheduledTask.objects.filter(schedule=active, part__isnull=False)
              .values('part__work_order_id', 'step_id', 'start_time')):
        key = (t['part__work_order_id'], t['step_id'])
        d = t['start_time'].date()
        if key not in out or d < out[key]:
            out[key] = d
    return out


def sourcing_requirements(tenant) -> dict:
    """Compute the source / produce / tooling requirement lanes for open demand."""
    from django.db.models import Sum
    from Tracker.models import (
        BOM, BOMLine, Fixture, MaterialLot, WorkOrder, WorkOrderStatus,
    )
    from Tracker.services.scheduling.data import get_schedule_horizon

    horizon = get_schedule_horizon(tenant)
    h_date = horizon.start.date()
    sched = _active_schedule_starts(tenant)
    excluded = [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED, WorkOrderStatus.ON_HOLD]

    def order_by(need_by, lead_days):
        return (need_by - timedelta(days=lead_days)) if lead_days else need_by

    # --- coverage: on-hand + incoming per Material ---------------------------
    # Keyed by (kind, id): a lot is stock of a raw Material or of a buyable PartType,
    # and both kinds can appear on the same BOM, so the kind has to be part of the key.
    def _lot_key(row):
        if row['material_id'] is not None:
            return ('MATERIAL', row['material_id'])
        if row['material_type_id'] is not None:
            return ('PART_TYPE', row['material_type_id'])
        return None  # ad-hoc lot named only by description — not a planning subject

    onhand: dict = {}
    for r in (MaterialLot.objects.filter(tenant=tenant, status__in=_ON_HAND_LOT_STATUSES)
              .values('material_id', 'material_type_id', 'quantity_remaining')):
        k = _lot_key(r)
        if k is not None:
            onhand[k] = onhand.get(k, 0.0) + float(r['quantity_remaining'] or 0)

    incoming: dict = {}
    incoming_date: dict = {}
    for lot in (MaterialLot.objects.filter(tenant=tenant, promised_date__isnull=False,
                                           quantity_remaining__gt=0)
                .exclude(status__in=_NOT_INCOMING_LOT_STATUSES)  # not already on-hand or terminal
                .values('material_id', 'material_type_id', 'promised_date',
                        'quantity_remaining')):
        k = _lot_key(lot)
        if k is None:
            continue
        incoming[k] = incoming.get(k, 0.0) + float(lot['quantity_remaining'] or 0)
        if k not in incoming_date or lot['promised_date'] < incoming_date[k]:
            incoming_date[k] = lot['promised_date']

    # --- demand: BUY-line materials aggregated across open WOs ----------------
    bom_cache: dict = {}

    def _lines(pt_id):
        if pt_id not in bom_cache:
            # Latest RELEASED — not is_current_version (an open draft revision must not
            # hide the in-force production BOM). See work_order_material_requirements.
            bom = (BOM.objects.filter(part_type_id=pt_id, bom_type='ASSEMBLY',
                   status='RELEASED').order_by('-version').first())
            bom_cache[pt_id] = list(
                BOMLine.objects.filter(bom=bom)
                .select_related('material', 'component_type')
                if bom else [])
        return bom_cache[pt_id]

    demand: dict = {}       # (kind, id) -> qty needed
    need_by: dict = {}      # (kind, id) -> earliest need-by date
    buy_obj: dict = {}      # (kind, id) -> BuyItem
    for wo in (WorkOrder.objects.filter(tenant=tenant, process__isnull=False)
               .exclude(workorder_status__in=excluded).select_related('process')):
        pt_id = wo.process.part_type_id
        if pt_id is None:
            continue
        wo_need = sched.get((wo.id, None)) or wo.expected_start or h_date
        for line in _lines(pt_id):
            if line.is_optional:
                continue
            buy = buy_line_item(line)
            if buy is None:
                continue
            k = buy.key
            demand[k] = demand.get(k, 0.0) + float(line.quantity) * wo.quantity
            buy_obj[k] = buy
            nb = sched.get((wo.id, line.consumed_at_step_id)) or wo.expected_start or wo_need
            if k not in need_by or nb < need_by[k]:
                need_by[k] = nb

    source = []
    for k, qty in demand.items():
        buy = buy_obj[k]
        # Held-back buffer is not available to commit — see the per-WO pass above.
        safety = buy.safety_stock
        short = qty - (onhand.get(k, 0.0) - safety) - incoming.get(k, 0.0)
        if short <= 0:
            continue
        nb = need_by.get(k, h_date)
        lead = buy.lead_time_days
        source.append({
            'material': buy.name,
            'buy_kind': buy.kind,
            'qty_short': int(round(short)),
            'safety_stock': safety,
            'need_by': nb,
            'lead_time_days': lead,
            'order_by': order_by(nb, lead),
            'incoming_date': incoming_date.get(k),
        })
    source.sort(key=lambda r: (r['order_by'] or r['need_by']))

    # --- produce: open pegged child work orders (MAKE) -----------------------
    produce = []
    for cwo in (WorkOrder.objects.filter(tenant=tenant, pegged_to_bom_line__isnull=False)
                .exclude(workorder_status__in=excluded)
                .select_related('process__part_type', 'pegged_to_workorder')):
        comp = cwo.process.part_type.name if (cwo.process_id and cwo.process.part_type_id) else cwo.ERP_id
        parent = cwo.pegged_to_workorder
        nb = (parent.expected_start if parent else None) or cwo.expected_completion or h_date
        produce.append({
            'work_order': cwo.ERP_id,
            'component': comp,
            'qty': cwo.quantity,
            'need_by': nb,
            'status': cwo.workorder_status,
        })
    produce.sort(key=lambda r: r['need_by'])

    # --- tooling: fixtures not yet on hand ----------------------------------
    tooling = []
    for fx in Fixture.objects.filter(tenant=tenant, quantity=0):
        lead = fx.lead_time_days
        tooling.append({
            'fixture': fx.name,
            'kind': fx.kind,
            'need_by': h_date,
            'lead_time_days': lead,
            'order_by': order_by(h_date, lead),
        })

    return {'source': source, 'produce': produce, 'tooling': tooling}
