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

from datetime import date, timedelta

from Tracker.services.mes.bom import buy_line_item
from Tracker.services.reman.demand import (
    LineDemand, takes_pooled_parts, work_order_line_demand,
)

# On-hand = usable stock. Incoming = inbound, not-yet-usable receipts. The two must be
# disjoint or accepted stock double-counts (it's both "on hand" and "promised"): incoming
# therefore excludes the on-hand statuses as well as the terminal ones.
_ON_HAND_LOT_STATUSES = ('ACCEPTED', 'IN_USE')
_TERMINAL_LOT_STATUSES = ('CONSUMED', 'SCRAPPED', 'REJECTED')
_NOT_INCOMING_LOT_STATUSES = _ON_HAND_LOT_STATUSES + _TERMINAL_LOT_STATUSES


def _recoverable_for(line, tenant=None) -> float:
    """What the core bank could yield of this line's component, or 0.

    A raw-material line always returns 0 — you cannot harvest sealant — and so does
    anything the item master says is expendable.
    """
    from Tracker.services.reman.recovery import recoverable_supply

    if line.component_type_id is None:
        return 0.0
    return float(recoverable_supply(line.component_type, tenant=tenant).quantity)


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
        BOM, BOMLine, MaterialLot, WorkOrder,
    )
    from Tracker.services.mes.bom import usable_stock_parts
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
    # Recovered stock may only go into units that take pooled parts — exchange
    # rebuilds. See `usable_stock_parts` and services/reman/demand.py.
    takes_pool = takes_pooled_parts(work_order)
    rows = []
    # tenant-safe: `bom` is a tenant-scoped row; its lines belong to the same tenant.
    lines = list(BOMLine.objects.filter(bom=bom)
                 .select_related('component_type', 'material', 'consumed_at_step')
                 .order_by('line_number'))
    # A reman work order's demand is read per core from where each core is — the
    # same reading the buy list uses, so the two cannot disagree about one order.
    reman = (work_order_line_demand(work_order, lines)
             if work_order.cores.exists() else None)
    for line in lines:
        if reman is None:
            required = float(Decimal(str(line.quantity)) * Decimal(work_order.quantity))
            line_forecast, pool_ok = 0.0, False
        else:
            d = reman.get(line.id) or LineDemand()
            required, line_forecast, pool_ok = d.firm, d.forecast, d.pool_eligible > 0
        step = line.consumed_at_step.name if line.consumed_at_step_id else None
        row = {
            'source': line.source,
            'quantity': required,
            # Expected replacements on a unit not yet opened. Reported, never netted
            # into `short_qty`.
            'forecast': round(line_forecast, 2),
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
            # The RECOVER lane: what the core bank could yield of this component.
            # REPORTED, never netted into `short_qty` — teardown has not happened, so
            # it is a forecast sitting beside facts. Netting it would let a planner
            # skip an order on stock that does not exist yet, and that error stops a
            # line while the reverse only buys a part you could have harvested.
            # Zero on a new build: the bank's yield cannot go into it, so reporting
            # it there would invite a planner to wait on supply the job may not use.
            recoverable = (_recoverable_for(line, tenant=work_order.tenant)
                           if pool_ok else 0.0)
            row.update({
                'component': buy.name, 'kind': 'BUY',
                'buy_kind': buy.kind,
                'on_hand': on_hand, 'incoming': incoming,
                'recoverable': recoverable,
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
            on_hand = float(usable_stock_parts(
                comp.id, tenant=tenant, for_reman=takes_pool).count())
            pegged = float(WorkOrder.objects.filter(
                tenant=tenant, pegged_to_workorder=work_order, pegged_to_bom_line=line,
                workorder_status__in=live_wo).aggregate(s=Sum('quantity'))['s'] or 0)
            short = max(0.0, required - on_hand - pegged)
            row.update({
                'component': comp.name, 'kind': 'MAKE',
                'on_hand': on_hand, 'incoming': pegged,  # 'incoming' = qty on live child WOs
                'recoverable': (_recoverable_for(line, tenant=work_order.tenant)
                                if pool_ok else 0.0),
                'short_qty': short,
                'status': 'ok' if short <= 0 else ('building' if pegged > 0 else 'short'),
                # Made in-house, not purchased — no buy lead time / order-by.
                'lead_time_days': None, 'need_by': None, 'order_by': None,
            })
        else:
            # Misconfigured line (source set but no matching component) — surface it plainly.
            row.update({'component': '(unset)', 'kind': line.source or '?',
                        'on_hand': 0.0, 'incoming': 0.0, 'recoverable': 0.0,
                        'short_qty': required,
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
                BOMLine.objects.filter(bom=bom)  # tenant-safe: `bom` is tenant-scoped; its lines share its tenant
                .select_related('material', 'component_type')
                if bom else [])
        return bom_cache[pt_id]

    demand: dict = {}       # (kind, id) -> firm qty needed
    # Expected replacements on repair-and-return units not yet opened. Kept apart from
    # `demand` — nobody knows which parts a unit loses until it is torn down — and
    # reported beside the buy figure, never inside it. See services/reman/demand.py.
    forecast: dict = {}
    # Replacements recovered stock may fill: slots on exchange rebuilds. The ONLY
    # demand teardown can be proposed to cover — a repair-and-return unit keeps its
    # own parts and is never offered the pool, and a new build never takes recovered
    # stock at all.
    pool_need: dict = {}
    pool_need_by: dict = {}
    pool_name: dict = {}
    need_by: dict = {}      # (kind, id) -> earliest need-by date
    buy_obj: dict = {}      # (kind, id) -> BuyItem
    for wo in (WorkOrder.objects.filter(tenant=tenant, process__isnull=False)
               .exclude(workorder_status__in=excluded).select_related('process')
               .prefetch_related('parts__core_role')):
        pt_id = wo.process.part_type_id
        if pt_id is None:
            continue
        wo_need = sched.get((wo.id, None)) or wo.expected_start or h_date
        lines = [ln for ln in _lines(pt_id) if not ln.is_optional]
        # A reman work order's demand is read per core from where each core is, not
        # from its process BOM times its quantity: that asked for a full rebuild kit
        # per core, for exchange cores only being harvested and for a unit's own
        # nozzles that go back into it.
        reman = work_order_line_demand(wo, lines) if wo.cores.all() else None
        for line in lines:
            if reman is None:
                firm, fc, pool = float(line.quantity) * wo.quantity, 0.0, 0.0
            else:
                d = reman.get(line.id)
                if d is None:
                    continue
                firm, fc, pool = d.firm, d.forecast, d.pool_eligible
            nb = sched.get((wo.id, line.consumed_at_step_id)) or wo.expected_start or wo_need

            # Pool demand is recorded BEFORE the buy filter: a recovered nozzle replaces
            # a made one as well as a bought one. Gating it on BUY lines left the
            # recover lane blind wherever the recoverable parts are made in-house.
            if pool and line.component_type_id:
                pk = ('PART_TYPE', line.component_type_id)
                pool_need[pk] = pool_need.get(pk, 0.0) + pool
                pool_name[pk] = line.component_type.name
                if pk not in pool_need_by or nb < pool_need_by[pk]:
                    pool_need_by[pk] = nb

            buy = buy_line_item(line)
            if buy is None:
                continue
            k = buy.key
            if firm:
                demand[k] = demand.get(k, 0.0) + firm
            if fc:
                forecast[k] = forecast.get(k, 0.0) + fc
            buy_obj[k] = buy
            if k not in need_by or nb < need_by[k]:
                need_by[k] = nb

    # --- recoverable: what teardown could yield, as its own lane ---------------
    # REPORTED, NEVER NETTED. Recoverable supply is a forecast — teardown has not
    # happened — while on-hand and on-order are facts. Subtracting it from `qty_short`
    # would let a planner skip an order on stock that does not exist yet, and the error
    # is asymmetric: over-counting future supply stops a line, under-counting only buys
    # a part you could have harvested. Shown only where some exchange rebuild could use
    # it: anywhere else the bank's yield is no help to the line.
    recoverable: dict = {}
    pt_ids = [k[1] for k in pool_need if k[0] == 'PART_TYPE']
    if pt_ids:
        from Tracker.models import PartTypes
        from Tracker.services.reman.recovery import recoverable_supply
        for pt in PartTypes.objects.filter(tenant=tenant, id__in=pt_ids,
                                           can_recover=True, archived=False):
            supply = recoverable_supply(pt, tenant=tenant)
            if supply.quantity > 0:
                recoverable[('PART_TYPE', pt.id)] = supply

    source = []
    for k in set(demand) | set(forecast):
        buy = buy_obj[k]
        # Held-back buffer is not available to commit — see the per-WO pass above.
        safety = buy.safety_stock
        cover = (onhand.get(k, 0.0) - safety) + incoming.get(k, 0.0)
        firm = demand.get(k, 0.0)
        short = firm - cover
        # What ELSE would be short if the forecast came true — the part of the
        # forecast that current cover does not already absorb. Purchasing can buy
        # ahead on it; nothing here makes them.
        forecast_short = max(0.0, firm + forecast.get(k, 0.0) - cover) - max(0.0, short)
        if short <= 0 and forecast_short <= 0:
            continue
        nb = need_by.get(k, h_date)
        lead = buy.lead_time_days
        source.append({
            'material': buy.name,
            'buy_kind': buy.kind,
            'qty_short': int(round(max(0.0, short))),
            'forecast_short': round(forecast_short, 2),
            'safety_stock': safety,
            'need_by': nb,
            'lead_time_days': lead,
            'order_by': order_by(nb, lead),
            'incoming_date': incoming_date.get(k),
            'recoverable': float(recoverable[k].quantity) if k in recoverable else 0.0,
            'recoverable_cores': recoverable[k].core_count if k in recoverable else 0,
            # Which cores the number came from. A planner who cannot see the basis of a
            # forecast cannot judge whether to trust it, and an untrusted number is
            # just noise on the sheet.
            'recoverable_sources': recoverable[k].sources if k in recoverable else [],
        })
    source.sort(key=lambda r: (r['order_by'] or r['need_by']))

    recover = _recover_lane(tenant, pool_need, pool_need_by, pool_name, order_by)

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

    return {'source': source, 'produce': produce, 'tooling': tooling,
            'recover': recover}


def _recover_lane(tenant, pool_need, need_by, names, order_by) -> list:
    """Teardown proposed to refill the recovered pool — one row per CORE TYPE.

    Per core type, not per component: one core yields several components, so a
    per-component list asks for the same unit over and over — nozzles need 2 cores,
    bodies need 3 of the same type, and the answer is 3 cores, not 5.

    What it covers is pool demand: replacement slots on exchange rebuilds. Against
    that it counts, in order, what is already on the shelf and what teardowns already
    committed will yield, and proposes only the rest — so accepting a proposal makes
    it disappear rather than reappear.

    It PROPOSES; accepting raises a PLANNED teardown work order through
    `plan_teardown`. Nothing here commits a core: a unit in pieces has no undo.
    """
    from math import ceil
    from Tracker.services.mes.bom import recovered_stock_by_type
    from Tracker.services.reman.recovery import teardown_banks, teardown_lead_days

    comp_ids = [k[1] for k, q in pool_need.items() if k[0] == 'PART_TYPE' and q > 0]
    if not comp_ids:
        return []
    banks = teardown_banks(tenant)
    on_shelf = recovered_stock_by_type(tenant)

    in_flight_yield: dict = {}
    for bank in banks.values():
        for comp, per_core in bank.yields.items():
            in_flight_yield[comp] = in_flight_yield.get(comp, 0.0) + bank.in_flight * per_core

    gap, basis = {}, {}
    for comp in comp_ids:
        need = pool_need[('PART_TYPE', comp)]
        shelf = float(on_shelf.get(comp, 0))
        flight = in_flight_yield.get(comp, 0.0)
        gap[comp] = max(0.0, need - shelf - flight)
        basis[comp] = {'needed': need, 'on_shelf': shelf, 'in_flight': round(flight, 2)}

    rows = []
    for ct_id, bank in sorted(banks.items(), key=lambda kv: kv[1].core_type.name):
        comps = [c for c in bank.yields if gap.get(c, 0.0) > 0]
        if not comps or not bank.proposable:
            continue
        # Enough units for the component that needs the most of them; the others ride
        # along. Whole units — you cannot tear down part of a core.
        n = min(max(ceil(gap[c] / bank.yields[c]) for c in comps), len(bank.proposable))
        components = []
        for c in comps:
            covered = min(gap[c], n * bank.yields[c])
            gap[c] -= covered
            components.append({
                'component': names[('PART_TYPE', c)],
                '_id': c,
                **basis[c],
                'covered_by_teardown': round(covered, 2),
            })
        needs = [need_by[('PART_TYPE', c)] for c in comps if ('PART_TYPE', c) in need_by]
        nb = min(needs) if needs else None
        lead = teardown_lead_days(bank.core_type, tenant=tenant)
        rows.append({
            'core_type': bank.core_type.name,
            'core_type_id': str(ct_id),
            'cores_to_tear_down': n,
            'cores_available': len(bank.proposable),
            'cores_in_flight': bank.in_flight,
            # What "accept" commits, oldest received first. A planner can swap them:
            # these are the default, not a decision.
            'candidate_cores': [{'id': str(core.id), 'core_number': core.core_number}
                                for core in bank.proposable[:n]],
            'lead_time_days': lead,
            'need_by': nb,
            # Omitted when the core type has no authored teardown duration. A made-up
            # lead time reads as authored fact on the sheet and gets scheduled against.
            'start_by': order_by(nb, lead) if (lead is not None and nb) else None,
            'components': components,
        })

    # What is still short once every core type has contributed — set last, since a
    # component can be yielded by more than one type.
    for row in rows:
        for comp in row['components']:
            comp['still_short'] = round(gap[comp.pop('_id')], 2)
    # Soonest first; an undated row sorts last rather than failing the comparison.
    rows.sort(key=lambda r: r['start_by'] or r['need_by'] or date.max)
    return rows
