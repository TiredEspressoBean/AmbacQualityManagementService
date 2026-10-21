"""The order book: open customer demand, how far it's got, and whether it will make
its promise (user-approved spec, 2026-10-21).

Read-side aggregation over records that already exist — orders and their lines, the
work orders pegged to them, their parts, the active schedule, shipments, holds and
reman cores. Nothing financial: UQMES records demand, progress and promises; prices,
order value and credit belong to the system that owns them (CLAUDE.md boundary).

Two entry points, both scoped to what `user` may see (`for_user`):
- `order_book(user)` — one row per open order, including orders with no work orders
  (the ones a planner most needs to see, and that /tracker can't show).
- `order_detail(order, user)` — the staff order page: lines, work orders, shipments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone

OPEN_ORDER_EXCLUDED = ("COMPLETED", "CANCELLED")
IN_WORK_STATUSES = frozenset({
    "IN_PROGRESS", "AT_OUTSIDE_PROCESS", "AWAITING_QA", "READY_FOR_NEXT_STEP",
    "QUARANTINED", "REWORK_NEEDED", "REWORK_IN_PROGRESS", "ON_HOLD"})
DONE_STATUSES = frozenset({"COMPLETED", "IN_STOCK", "AWAITING_PICKUP"})
MAX_CHIPS = 3


@dataclass(frozen=True)
class Blocker:
    """Something holding the order up, and where it's resolved."""
    kind: str          # no_units | on_hold | quarantined | awaiting_authorisation | material_short | cores_missing
    label: str
    link: str


@dataclass(frozen=True)
class Progress:
    ordered: int
    planned: int
    in_work: int
    done: int
    shipped: int


@dataclass(frozen=True)
class Projection:
    """Projected finish against the promise. `state` is late | on_track | not_scheduled."""
    due: date | None
    projected: date | None
    slip_days: int | None
    state: str


@dataclass(frozen=True)
class OrderBookRow:
    order_id: str
    order_number: str
    name: str
    customer_name: str | None
    earliest_due: date | None
    unplanned: int
    projection: Projection
    blockers: tuple[Blocker, ...]
    more_blockers: int
    progress: Progress

    @property
    def at_risk(self) -> bool:
        return self.projection.state == "late" or bool(self.blockers) or self.more_blockers > 0


@dataclass(frozen=True)
class OnTimeDelivery:
    days: int
    deliveries: int
    on_time: int
    on_time_pct: float | None
    unmeasured: int


@dataclass(frozen=True)
class OrderBook:
    rows: tuple[OrderBookRow, ...]
    on_time: OnTimeDelivery


@dataclass(frozen=True)
class LineView:
    line_id: str
    line_number: int
    part_type_id: str
    part_type_name: str
    quantity: int
    remaining: int
    due_date: date | None
    status: str
    progress: Progress


@dataclass(frozen=True)
class WorkOrderView:
    work_order_id: str
    erp_id: str
    status: str
    released: bool
    due: date | None
    projection: Projection
    blockers: tuple[Blocker, ...]
    # Set when the WO isn't the order's own: the order's units that are on it.
    units: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShipmentView:
    shipment_id: str
    shipment_number: str
    shipped_at: date | None
    line_number: int | None
    quantity: int
    on_time: bool | None    # None: no due date to judge against


@dataclass(frozen=True)
class OrderDetail:
    row: OrderBookRow
    original_completion: date | None
    estimated_completion: date | None
    lines: tuple[LineView, ...]
    work_orders: tuple[WorkOrderView, ...]
    shipments: tuple[ShipmentView, ...]
    ready_to_ship: int


# --------------------------------------------------------------------------- facts

@dataclass
class _Facts:
    """Everything the rows are built from, fetched once for the orders in view."""
    wos_by_order: dict = field(default_factory=dict)        # order_id -> [WorkOrder]
    parts_by_wo: dict = field(default_factory=dict)         # wo_id -> [Parts]
    finish_by_wo: dict = field(default_factory=dict)        # wo_id -> latest task end (datetime)
    covered_by_wo: dict = field(default_factory=dict)       # wo_id -> parts with a task
    held_wo: set = field(default_factory=set)               # wo ids with an open hold
    short_wo: set = field(default_factory=set)              # wo ids with a material shortage
    awaiting_cores_by_wo: dict = field(default_factory=dict)  # wo_id -> [Core]
    cores_by_wo: dict = field(default_factory=dict)         # wo_id -> count of cores
    cores_by_order: dict = field(default_factory=dict)      # order_id -> [Core] received for it
    # The order's units worked on a work order that isn't the order's — a repair core
    # torn down and rebuilt on its teardown WO (`Parts.order`, set at receipt).
    linked_parts_by_order: dict = field(default_factory=dict)  # order_id -> [Parts]
    finish_by_part: dict = field(default_factory=dict)      # linked part_id -> task end


def _facts(user, orders) -> _Facts:
    from Tracker.models import (
        Core, Parts, ScheduledTask, ScheduleResult, WorkOrder, WorkOrderHold)
    f = _Facts()
    order_ids = [o.id for o in orders]
    if not order_ids:
        return f
    # The cores received FOR each order (`Parts.order`, set at receipt). Fetched before
    # the work orders: a repair order's cores arrive before anything is planned.
    for core in (Core.objects  # tenant-safe: .objects auto-scopes; keyed to scoped orders
                 .filter(archived=False, part__order_id__in=order_ids)
                 .exclude(status='SCRAPPED').select_related('part')):
        f.cores_by_order.setdefault(core.part.order_id, []).append(core)
    wos = list(WorkOrder.objects.for_user(user)  # scoped to what the user may see
               .filter(archived=False, related_order_id__in=order_ids)
               .select_related('order_line', 'process'))
    for wo in wos:
        f.wos_by_order.setdefault(wo.related_order_id, []).append(wo)
    wo_ids = [wo.id for wo in wos]
    for p in (Parts.objects.for_user(user)  # scoped
              .filter(archived=False, work_order_id__in=wo_ids).select_related('step')):
        f.parts_by_wo.setdefault(p.work_order_id, []).append(p)
    linked_ids = []
    for p in (Parts.objects.for_user(user)  # scoped
              .filter(archived=False, order_id__in=order_ids, work_order__isnull=False)
              .exclude(work_order_id__in=wo_ids).select_related('step', 'work_order')):
        f.linked_parts_by_order.setdefault(p.order_id, []).append(p)
        linked_ids.append(p.id)
    if not wo_ids and not linked_ids:
        return f

    from django.db.models import Q
    schedule = (ScheduleResult.objects  # tenant-safe: .objects auto-scopes to the request tenant
                .filter(is_active=True, is_draft=False).order_by('-created_at').first())
    if schedule is not None:
        for wo_id, part_id, end in (ScheduledTask.objects  # tenant-safe: scoped by the schedule FK
                                    .filter(Q(part__work_order_id__in=wo_ids) | Q(part_id__in=linked_ids),
                                            schedule=schedule)
                                    .values_list('part__work_order_id', 'part_id', 'end_time')):
            if part_id in linked_ids and wo_id not in wo_ids:
                if end and (part_id not in f.finish_by_part or end > f.finish_by_part[part_id]):
                    f.finish_by_part[part_id] = end
                continue
            if end and (wo_id not in f.finish_by_wo or end > f.finish_by_wo[wo_id]):
                f.finish_by_wo[wo_id] = end
            f.covered_by_wo.setdefault(wo_id, set()).add(part_id)
    if not wo_ids:
        return f

    f.held_wo = set(WorkOrderHold.objects  # tenant-safe: .objects auto-scopes; keyed to scoped WOs
                    .filter(work_order_id__in=wo_ids, cleared_at__isnull=True, is_voided=False)
                    .values_list('work_order_id', flat=True))
    for core in (Core.objects  # tenant-safe: .objects auto-scopes; keyed to scoped WOs
                 .filter(archived=False, part__work_order_id__in=wo_ids)
                 .select_related('part')):
        wo_id = core.part.work_order_id
        f.cores_by_wo[wo_id] = f.cores_by_wo.get(wo_id, 0) + 1
        if core.status == 'AWAITING_AUTHORISATION':
            f.awaiting_cores_by_wo.setdefault(wo_id, []).append(core)

    try:
        from Tracker.services.scheduling import data as sched
        horizon = sched.get_schedule_horizon(wos[0].tenant)
        _release, short_keys, _detail = sched.get_material_gates(wos[0].tenant, horizon)
        f.short_wo = {k[0] for k in short_keys} & set(wo_ids)
    except Exception:  # noqa: BLE001 — a shortage chip is advisory; never fail the book on it
        f.short_wo = set()
    return f


# --------------------------------------------------------------------------- pieces

# Unschedulable but not finished: the unit still owes the order work, and nothing can
# schedule it until someone decides. Counted open, so it can never read "on track".
HELD_STATUSES = frozenset({"ON_HOLD", "QUARANTINED"})


def _open_parts(parts):
    from Tracker.services.scheduling import data as sched
    finished = sched._UNSCHEDULABLE_PART_STATUSES - HELD_STATUSES
    return [p for p in parts if p.part_status not in finished
            and not (p.step_id and p.step.is_terminal)]


def _missing_units(wo, parts) -> int:
    """Units an open work order is for but has no part for yet. Nothing can schedule
    them, so they count against the projection as unplanned quantity does."""
    if wo.workorder_status in ('COMPLETED', 'CANCELLED'):
        return 0
    return max(0, (wo.quantity or 0) - sum(1 for p in parts if p.part_status != 'CANCELLED'))


def _wo_due(wo) -> date | None:
    return (wo.order_line.due_date if wo.order_line_id and wo.order_line else None) or wo.expected_completion


def _projection(due, projected_dt, open_count, covered_count, unplanned, tenant) -> Projection:
    """Projected finish against `due`, on the plant's calendar. Work not on the schedule
    (unplanned quantity, or open units with no task) is "not scheduled" — never "on
    track"."""
    from Tracker.services.core.clock import plant_tz, tenant_today
    projected = projected_dt.astimezone(plant_tz(tenant)).date() if projected_dt else None
    if unplanned > 0 or (open_count and covered_count < open_count):
        slip = (projected - due).days if (projected and due and projected > due) else None
        return Projection(due, projected, slip, "not_scheduled")
    if projected is None:
        # Nothing open to schedule: on track if it's not past due.
        late = bool(due and open_count and tenant_today(tenant) > due)
        return Projection(due, None, None, "late" if late else "on_track")
    if due and projected > due:
        return Projection(due, projected, (projected - due).days, "late")
    return Projection(due, projected, 0 if due else None, "on_track")


def _wo_blockers(wo, f: _Facts) -> list[Blocker]:
    out: list[Blocker] = []
    if _missing_units(wo, f.parts_by_wo.get(wo.id, [])) and not f.parts_by_wo.get(wo.id):
        out.append(Blocker('no_units', f"{wo.ERP_id}: no units created yet", f"/workorder/{wo.id}"))
    if wo.id in f.held_wo or wo.workorder_status == 'ON_HOLD':
        out.append(Blocker('on_hold', f"{wo.ERP_id} on hold", f"/workorder/{wo.id}"))
    parts = f.parts_by_wo.get(wo.id, [])
    quarantined = sum(1 for p in parts if p.part_status == 'QUARANTINED')
    if quarantined:
        out.append(Blocker('quarantined', f"{wo.ERP_id}: {quarantined} quarantined",
                           f"/workorder/{wo.id}/control"))
    for core in f.awaiting_cores_by_wo.get(wo.id, []):
        out.append(Blocker('awaiting_authorisation', f"{core.core_number} awaiting authorisation",
                           f"/reman/cores/{core.id}"))
    if wo.id in f.short_wo:
        out.append(Blocker('material_short', f"{wo.ERP_id} material short", "/production/requirements"))
    return out


def _order_core_blockers(order, lines, f: _Facts) -> list[Blocker]:
    """From the cores received for the order: lines still short of their cores, and
    cores waiting on the customer's authorisation. Counted against the LINE's quantity
    by core type, since the cores arrive before (and apart from) any work order. A line
    with no core received for it isn't a core line, so it gets no chip."""
    cores = f.cores_by_order.get(order.id, [])
    out: list[Blocker] = []
    for ln in lines:
        n = sum(1 for c in cores if c.core_type_id == ln.part_type_id)
        if 0 < n < ln.quantity:
            out.append(Blocker('cores_missing', f"L{ln.line_number}: cores {n}/{ln.quantity} received",
                               "/reman/cores"))
    for core in cores:
        if core.status == 'AWAITING_AUTHORISATION':
            out.append(Blocker('awaiting_authorisation', f"{core.core_number} awaiting authorisation",
                               f"/reman/cores/{core.id}"))
    return out


def _progress(ordered, planned, parts) -> Progress:
    return Progress(
        ordered=ordered, planned=planned,
        in_work=sum(1 for p in parts if p.part_status in IN_WORK_STATUSES),
        done=sum(1 for p in parts if p.part_status in DONE_STATUSES),
        shipped=sum(1 for p in parts if p.part_status == 'SHIPPED'))


def _row(order, f: _Facts) -> OrderBookRow:
    lines = [ln for ln in order.lines.all() if ln.status == 'OPEN']
    wos = [w for w in f.wos_by_order.get(order.id, []) if w.workorder_status != 'CANCELLED']
    linked = f.linked_parts_by_order.get(order.id, [])
    parts = [p for w in wos for p in f.parts_by_wo.get(w.id, [])] + linked
    ordered = sum(ln.quantity for ln in lines)
    planned = sum(ln.planned_quantity for ln in lines)
    unplanned = sum(ln.remaining_quantity for ln in lines)
    if not lines:
        # An order with work but no lines (entered before lines existed): its work
        # orders are the only statement of what it's for.
        ordered = planned = sum(w.quantity or 0 for w in wos)
    missing = sum(_missing_units(w, f.parts_by_wo.get(w.id, [])) for w in wos)

    dues = [ln.due_date for ln in lines if ln.due_date] or [d for d in map(_wo_due, wos) if d]
    earliest_due = min(dues) if dues else None
    due = order.estimated_completion or (max(dues) if dues else None)

    finishes = [f.finish_by_wo[w.id] for w in wos if w.id in f.finish_by_wo]
    open_count = covered = 0
    for w in wos:
        op = _open_parts(f.parts_by_wo.get(w.id, []))
        open_count += len(op)
        covered += sum(1 for p in op if p.id in f.covered_by_wo.get(w.id, ()))
    op = _open_parts(linked)
    open_count += len(op)
    covered += sum(1 for p in op if p.id in f.finish_by_part)
    finishes += [f.finish_by_part[p.id] for p in linked if p.id in f.finish_by_part]
    projection = _projection(due, max(finishes) if finishes else None, open_count, covered,
                             unplanned + missing, order.tenant)

    blockers = _order_core_blockers(order, lines, f)
    blockers += [Blocker('quarantined', f"{p.ERP_id} quarantined", f"/workorder/{p.work_order_id}/control")
                 for p in linked if p.part_status == 'QUARANTINED']
    for b in (b for w in wos for b in _wo_blockers(w, f)):
        if b not in blockers:  # a linked core on one of the order's WOs is chipped once
            blockers.append(b)
    return OrderBookRow(
        order_id=str(order.id), order_number=order.order_number or "", name=order.name,
        customer_name=order.company.name if order.company_id else None,
        earliest_due=earliest_due, unplanned=unplanned, projection=projection,
        blockers=tuple(blockers[:MAX_CHIPS]), more_blockers=max(0, len(blockers) - MAX_CHIPS),
        progress=_progress(ordered, planned, parts))


def _on_time(tenant) -> OnTimeDelivery:
    from Tracker.services.mes.shipping import delivery_performance
    d = delivery_performance(tenant, days=90)
    return OnTimeDelivery(days=d['days'], deliveries=d['deliveries'], on_time=d['on_time'],
                          on_time_pct=d['on_time_pct'], unmeasured=d['unmeasured'])


# --------------------------------------------------------------------------- API

def order_book(user, tenant) -> OrderBook:
    """Every open order the user may see, at risk first, then earliest due."""
    from Tracker.models import Orders
    orders = list(Orders.objects.for_user(user)  # scoped to what the user may see
                  .filter(archived=False).exclude(order_status__in=OPEN_ORDER_EXCLUDED)
                  .select_related('company').prefetch_related('lines'))
    f = _facts(user, orders)
    rows = [_row(o, f) for o in orders]
    far = date.max
    rows.sort(key=lambda r: (not r.at_risk, r.earliest_due or far, r.order_number))
    return OrderBook(rows=tuple(rows), on_time=_on_time(tenant))


def order_detail(order, user) -> OrderDetail:
    from Tracker.models import Parts
    f = _facts(user, [order])
    row = _row(order, f)
    wos = [w for w in f.wos_by_order.get(order.id, []) if w.workorder_status != 'CANCELLED']

    lines = []
    for ln in order.lines.all().select_related('part_type'):
        parts = [p for w in wos if w.order_line_id == ln.id for p in f.parts_by_wo.get(w.id, [])]
        parts += [p for p in f.linked_parts_by_order.get(order.id, []) if p.part_type_id == ln.part_type_id]
        lines.append(LineView(
            line_id=str(ln.id), line_number=ln.line_number, part_type_id=str(ln.part_type_id),
            part_type_name=ln.part_type.name, quantity=ln.quantity, remaining=ln.remaining_quantity,
            due_date=ln.due_date, status=ln.status,
            progress=_progress(ln.quantity, ln.planned_quantity, parts)))

    wo_views = []
    for w in sorted(wos, key=lambda w: w.ERP_id):
        op = _open_parts(f.parts_by_wo.get(w.id, []))
        cov = sum(1 for p in op if p.id in f.covered_by_wo.get(w.id, ()))
        wo_views.append(WorkOrderView(
            work_order_id=str(w.id), erp_id=w.ERP_id, status=w.workorder_status,
            released=w.released_at is not None, due=_wo_due(w),
            projection=_projection(_wo_due(w), f.finish_by_wo.get(w.id), len(op), cov,
                                   _missing_units(w, f.parts_by_wo.get(w.id, [])), order.tenant),
            blockers=tuple(_wo_blockers(w, f))))
    # The work orders the order's own units are worked on without being the order's —
    # a repair core on its teardown WO. Judged on those units alone, against the order.
    linked_by_wo: dict = {}
    for p in f.linked_parts_by_order.get(order.id, []):
        linked_by_wo.setdefault(p.work_order, []).append(p)
    for w, ps in sorted(linked_by_wo.items(), key=lambda kv: kv[0].ERP_id):
        op = _open_parts(ps)
        finishes = [f.finish_by_part[p.id] for p in ps if p.id in f.finish_by_part]
        wo_views.append(WorkOrderView(
            work_order_id=str(w.id), erp_id=w.ERP_id, status=w.workorder_status,
            released=w.released_at is not None, due=row.projection.due,
            projection=_projection(row.projection.due, max(finishes) if finishes else None, len(op),
                                   sum(1 for p in op if p.id in f.finish_by_part), 0, order.tenant),
            blockers=(), units=tuple(p.ERP_id for p in ps)))

    # One row per shipment per line, judged as delivery_performance judges it.
    shipped = (Parts.objects.for_user(user)  # scoped
               .filter(archived=False, work_order__related_order=order, part_status='SHIPPED',
                       customer_shipment__isnull=False, customer_shipment__is_voided=False)
               .values_list('customer_shipment_id', 'customer_shipment__shipment_number',
                            'customer_shipment__shipped_at', 'work_order__order_line__line_number',
                            'work_order__order_line__due_date', 'work_order__expected_completion'))
    groups: dict = {}
    for sid, number, at, line_no, line_due, wo_due in shipped:
        key = (sid, line_no)
        g = groups.setdefault(key, {'number': number, 'at': at, 'line': line_no,
                                    'due': line_due or wo_due, 'qty': 0})
        g['qty'] += 1
    shipments = []
    for (sid, _), g in sorted(groups.items(), key=lambda kv: (kv[1]['at'] or timezone.now())):
        # The same day rule as delivery_performance, so a row's mark and the OTD agree.
        shipped_on = timezone.localdate(g['at']) if g['at'] else None
        shipments.append(ShipmentView(
            shipment_id=str(sid), shipment_number=g['number'] or "", shipped_at=shipped_on,
            line_number=g['line'], quantity=g['qty'],
            on_time=(shipped_on <= g['due']) if (shipped_on and g['due']) else None))

    ready = sum(1 for w in wos for p in f.parts_by_wo.get(w.id, [])
                if p.step_id and p.step.is_terminal and p.part_status not in ('SHIPPED', 'SCRAPPED', 'CANCELLED'))
    return OrderDetail(row=row, original_completion=order.original_completion_date,
                       estimated_completion=order.estimated_completion,
                       lines=tuple(lines), work_orders=tuple(wo_views),
                       shipments=tuple(shipments), ready_to_ship=ready)
