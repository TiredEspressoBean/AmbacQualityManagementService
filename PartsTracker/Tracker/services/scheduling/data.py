"""
Scheduling data layer (Phase 1).

Pure Django ORM → solver-ready **frozen dataclasses**. No OR-Tools imports here;
the solver (Phase 2) consumes these DTOs. Every function takes `tenant` and uses
tenant-scoped `.objects`.

See `Documents/SCHEDULING_IMPLEMENTATION_PLAN.md` (Phase 1) and
`Documents/OR_TOOLS_INTEGRATION.md` (Data Layer).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone


# Parts in these states can't be worked, so they never enter the schedule
# (finished/shipped/inventory, cancelled/scrapped, or held for QA). Active states
# — PENDING/IN_PROGRESS/AWAITING_QA/READY_FOR_NEXT_STEP/REWORK_* — stay schedulable.
_UNSCHEDULABLE_PART_STATUSES = frozenset({
    'COMPLETED', 'SCRAPPED', 'CANCELLED', 'SHIPPED', 'IN_STOCK',
    'AWAITING_PICKUP', 'CORE_BANKED', 'RMA_CLOSED', 'QUARANTINED',
})


# --- DTOs -------------------------------------------------------------------

@dataclass(frozen=True)
class TimingData:
    """Resolved time elements for a step. `cycle_time_minutes` comes from the
    fallback chain; `cycle_source` records which rung supplied it.

    Carries the timing accessors so the solver (which consumes these DTOs, not the
    `StepTiming` model) can compute wall/attended/transfer-batch times directly.
    """
    step_id: UUID
    cycle_time_minutes: float
    setup_minutes: float
    load_unload_per_piece: float
    external_setup_minutes: float
    attention_type: str  # 'full' | 'load_unload'
    cycle_source: str  # 'timing' | 'history' | 'expected' | 'none'

    def machine_wall_time(self, quantity: int) -> float:
        """Minutes the machine is occupied for a batch: internal setup + run."""
        return self.setup_minutes + self.cycle_time_minutes * max(0, quantity)

    def first_piece_done(self) -> float:
        """Minutes until the first piece is complete (enables transfer batches)."""
        return self.setup_minutes + self.cycle_time_minutes + self.load_unload_per_piece

    def operator_attended_time(self, quantity: int) -> float:
        """Operator-attention minutes: full attention = the whole machine run;
        load/unload = setup + a touch per piece (machine runs unattended)."""
        quantity = max(0, quantity)
        if self.attention_type == 'full':
            return self.machine_wall_time(quantity)
        return self.setup_minutes + self.load_unload_per_piece * quantity


@dataclass(frozen=True)
class AffinityData:
    equipment_id: UUID
    affinity: str  # 'eligible' | 'preferred' | 'dialed_in'
    cycle_time_override: float | None
    is_schedulable: bool  # only schedulable machines get a capacity constraint


@dataclass(frozen=True)
class FixtureData:
    fixture_id: UUID
    quantity: int
    step_ids: frozenset


@dataclass(frozen=True)
class HorizonData:
    start: datetime
    end: datetime
    frozen_end: datetime
    slushy_end: datetime


@dataclass(frozen=True)
class PartData:
    part_id: UUID
    current_step_id: UUID | None


@dataclass(frozen=True)
class StepNode:
    step_id: UUID
    is_terminal: bool
    requires_first_piece_inspection: bool
    order: int  # ProcessStep.order — the linear fallback when a process has no edges


@dataclass(frozen=True)
class EdgeData:
    from_step_id: UUID
    to_step_id: UUID
    edge_type: str  # 'DEFAULT' (nominal/pass) | 'ALTERNATE' (rework/fail) | 'ESCALATION'


@dataclass(frozen=True)
class WorkOrderData:
    wo_id: UUID
    erp_id: str
    priority: int
    expected_completion: date | None
    expected_start: date | None  # earliest-release gate (no task starts before this)
    pegged_to_wo_id: UUID | None  # parent assembly WO this component job feeds (#9)
    pegged_consumes_step_id: UUID | None  # the parent step that consumes it (#9); None → whole parent waits
    quantity: int
    process_id: UUID
    parts: tuple  # tuple[PartData, ...]
    steps: tuple   # tuple[StepNode, ...] — the process routing nodes, ordered
    edges: tuple   # tuple[EdgeData, ...] — the routing DAG


@dataclass(frozen=True)
class MachineWindow:
    equipment_id: UUID
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ContinuousMachineData:
    equipment_id: UUID
    parts_per_hour: float
    bar_change_interval_hours: float | None
    bar_change_duration_minutes: float


@dataclass(frozen=True)
class PreviousTaskData:
    part_id: UUID
    step_id: UUID
    machine_id: UUID | None
    start_time: datetime
    end_time: datetime
    is_pinned: bool


@dataclass(frozen=True)
class PreviousScheduleData:
    """The active schedule's tasks, for warm-start hints + honoring pinned tasks."""
    schedule_id: UUID
    tasks: tuple  # tuple[PreviousTaskData, ...]


@dataclass(frozen=True)
class OperatorData:
    """A dispatchable operator (Layer 2). `shift_id` is the shift they are rostered to
    (always set — unrostered operators are not dispatchable). `work_center_ids` is the
    stations they may work; `primary_work_center_ids` their preferred ones (soft)."""
    user_id: int
    name: str
    shift_id: object
    work_center_ids: frozenset
    primary_work_center_ids: frozenset


# --- Timings (with the duration fallback chain) -----------------------------

def get_step_timings(tenant, min_samples: int = 20) -> dict[UUID, TimingData]:
    """Per current step: `StepTiming.cycle_time_minutes` → `StepExecution`
    historical average (≥ `min_samples` completed visits) → `Steps.expected_duration`.
    Setup / load-unload / external / attention come from `StepTiming` when present,
    else default to 0 / FULL."""
    from Tracker.models import StepExecution, Steps, StepTiming
    from Tracker.models.scheduling import AttentionType

    timings = {t.step_id: t for t in StepTiming.objects.filter(tenant=tenant)}

    dur = ExpressionWrapper(F('exited_at') - F('entered_at'), output_field=DurationField())
    hist = {
        row['step']: row
        for row in StepExecution.objects
        .filter(tenant=tenant, exited_at__isnull=False)
        .values('step').annotate(avg=Avg(dur), n=Count('id'))
    }

    def _historical(step_id):
        h = hist.get(step_id)
        if h and h['n'] >= min_samples and h['avg'] is not None:
            return h['avg'].total_seconds() / 60.0
        return None

    result: dict[UUID, TimingData] = {}
    for step in Steps.objects.filter(tenant=tenant, is_current_version=True):
        t = timings.get(step.id)
        if t and t.cycle_time_minutes:
            cycle, source = t.cycle_time_minutes, 'timing'
        else:
            hist_cycle = _historical(step.id)
            if hist_cycle is not None:
                cycle, source = hist_cycle, 'history'
            elif step.expected_duration:
                cycle, source = step.expected_duration.total_seconds() / 60.0, 'expected'
            else:
                cycle, source = 0.0, 'none'
        result[step.id] = TimingData(
            step_id=step.id,
            cycle_time_minutes=cycle,
            setup_minutes=t.setup_minutes if t else 0.0,
            load_unload_per_piece=t.load_unload_per_piece if t else 0.0,
            external_setup_minutes=t.external_setup_minutes if t else 0.0,
            attention_type=t.attention_type if t else AttentionType.FULL,
            cycle_source=source,
        )
    return result


# --- Machine eligibility / setup / fixtures ---------------------------------

def get_step_equipment_affinities(tenant) -> dict[UUID, list[AffinityData]]:
    """Which machines can run each step, and how well. `step_id → [AffinityData]`.
    Machines that can't be used right now — not in service, or with lapsed
    calibration (`Equipments.is_operational`) — are dropped so the solver never
    assigns work to them."""
    from Tracker.models import StepEquipmentAffinity

    result: dict[UUID, list[AffinityData]] = {}
    for a in (
        StepEquipmentAffinity.objects.filter(tenant=tenant)
        .select_related('equipment__equipment_type')
    ):
        if not a.equipment.is_operational:
            continue
        result.setdefault(a.step_id, []).append(AffinityData(
            equipment_id=a.equipment_id,
            affinity=a.affinity,
            cycle_time_override=a.cycle_time_override,
            is_schedulable=a.equipment.is_schedulable,
        ))
    return result


def get_step_secondary_resources(tenant) -> dict[UUID, frozenset]:
    """Schedulable *secondary* equipment a step requires beyond its production
    machine — measurement stations (a Keyence/CMM) that are finite resources.
    `step_id → frozenset(equipment_id)`. Derived from the step's measurement
    definitions whose gauge is flagged `is_schedulable`; plentiful handhelds
    (is_schedulable=False) are excluded so they never constrain the schedule."""
    from Tracker.models import MeasurementDefinition

    result: dict[UUID, set] = {}
    for md in (
        MeasurementDefinition.objects
        .filter(tenant=tenant, default_equipment__is_schedulable=True)
        .values('step_id', 'default_equipment_id')
    ):
        result.setdefault(md['step_id'], set()).add(md['default_equipment_id'])
    return {step_id: frozenset(eqs) for step_id, eqs in result.items()}


def get_changeover_matrix(tenant) -> dict[tuple, float]:
    """Sequence-dependent setup: `(equipment_id, from_step_id, to_step_id) → minutes`."""
    from Tracker.models import WorkCenterChangeover

    return {
        (c.equipment_id, c.from_step_id, c.to_step_id): c.changeover_minutes
        for c in WorkCenterChangeover.objects.filter(tenant=tenant)
    }


def get_fixture_availability(tenant) -> dict[UUID, FixtureData]:
    """Shared tooling with limited quantity: `fixture_id → FixtureData`."""
    from Tracker.models import Fixture

    result: dict[UUID, FixtureData] = {}
    for f in Fixture.objects.filter(tenant=tenant).prefetch_related('steps'):
        result[f.id] = FixtureData(
            fixture_id=f.id,
            quantity=f.quantity,
            step_ids=frozenset(s.id for s in f.steps.all()),
        )
    return result


# --- Horizon ----------------------------------------------------------------

def get_schedule_horizon(tenant, horizon_days: int = 30) -> HorizonData:
    """The planning window and time-fence boundaries. Frozen/slushy widths come
    from `OptimizationConfig` (defaults 2 / 7 days); the slushy zone follows the
    frozen zone."""
    from Tracker.models import OptimizationConfig

    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    frozen_days = cfg.frozen_zone_days if cfg else 2
    slushy_days = cfg.slushy_zone_days if cfg else 7

    start = timezone.now()
    return HorizonData(
        start=start,
        end=start + timedelta(days=horizon_days),
        frozen_end=start + timedelta(days=frozen_days),
        slushy_end=start + timedelta(days=frozen_days + slushy_days),
    )


# --- Active work orders (the routing graph to schedule) ---------------------

def get_active_workorders(tenant) -> list[WorkOrderData]:
    """Schedulable work orders with a process, each carrying its schedulable parts
    (current step) and the process routing graph (steps + edges). Excludes finished
    (COMPLETED/CANCELLED) and held (ON_HOLD) WOs, and drops parts in a state that
    can't be worked (finished, shipped, quarantined). The process graph is resolved
    once per distinct process and shared across its work orders."""
    from Tracker.models import ProcessStep, StepEdge, WorkOrder, WorkOrderStatus

    excluded = [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED,
                WorkOrderStatus.ON_HOLD]
    wos = (
        WorkOrder.objects.filter(tenant=tenant, process__isnull=False)
        .exclude(workorder_status__in=excluded)
        .select_related('pegged_to_bom_line')
        .prefetch_related('parts')
    )

    graph_cache: dict[UUID, tuple] = {}

    def _graph(process_id):
        if process_id not in graph_cache:
            steps = tuple(
                StepNode(
                    step_id=ps.step_id,
                    is_terminal=ps.step.is_terminal,
                    requires_first_piece_inspection=ps.step.requires_first_piece_inspection,
                    order=ps.order,
                )
                for ps in ProcessStep.objects.filter(process_id=process_id)
                .select_related('step').order_by('order')
            )
            edges = tuple(
                EdgeData(from_step_id=e.from_step_id, to_step_id=e.to_step_id,
                         edge_type=e.edge_type)
                for e in StepEdge.objects.filter(process_id=process_id)
            )
            graph_cache[process_id] = (steps, edges)
        return graph_cache[process_id]

    result: list[WorkOrderData] = []
    for wo in wos:
        steps, edges = _graph(wo.process_id)
        parts = tuple(
            PartData(part_id=p.id, current_step_id=p.step_id)
            for p in wo.parts.all()
            if p.part_status not in _UNSCHEDULABLE_PART_STATUSES
        )
        consumes_step_id = (wo.pegged_to_bom_line.consumed_at_step_id
                            if wo.pegged_to_bom_line_id else None)
        result.append(WorkOrderData(
            wo_id=wo.id, erp_id=wo.ERP_id, priority=wo.priority,
            expected_completion=wo.expected_completion, expected_start=wo.expected_start,
            pegged_to_wo_id=wo.pegged_to_workorder_id,
            pegged_consumes_step_id=consumes_step_id,
            quantity=wo.quantity,
            process_id=wo.process_id, parts=parts, steps=steps, edges=edges,
        ))
    return result


# --- Machine availability (shift windows minus downtime) --------------------

def get_machine_availability(tenant, horizon: HorizonData) -> dict[UUID, list[MachineWindow]]:
    """Per equipment: concrete available windows over the horizon = the tenant's
    active shift calendar expanded to datetimes, minus that machine's downtime.
    Shifts are tenant-wide (no per-machine shift assignment in the model yet)."""
    from Tracker.models import DowntimeEvent, Equipments, Shift

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True))
    base = _expand_shifts(shifts, horizon.start, horizon.end)

    downtime: dict[UUID, list[tuple]] = {}
    for d in (
        DowntimeEvent.objects.filter(tenant=tenant, equipment__isnull=False)
        .filter(start_time__lt=horizon.end)
        .exclude(end_time__lt=horizon.start)
    ):
        downtime.setdefault(d.equipment_id, []).append(
            (d.start_time, d.end_time or horizon.end)
        )

    result: dict[UUID, list[MachineWindow]] = {}
    for eq in Equipments.objects.filter(tenant=tenant):
        free = _subtract_intervals(base, downtime.get(eq.id, []))
        result[eq.id] = [MachineWindow(equipment_id=eq.id, start=s, end=e) for s, e in free]
    return result


def _expand_shifts(shifts, start: datetime, end: datetime) -> list[tuple]:
    """Expand recurring shifts into concrete [start, end] datetime windows over
    [start, end], clipped to that range. Overnight shifts (end_time <= start_time)
    roll into the next day. Returned sorted + merged."""
    windows: list[tuple] = []
    day = start.date()
    last = end.date()
    while day <= last:
        weekday = day.weekday()  # 0=Monday
        for sh in shifts:
            active_days = _parse_days(sh.days_of_week)
            if active_days and weekday not in active_days:
                continue
            w_start = timezone.make_aware(datetime.combine(day, sh.start_time))
            end_day = day + timedelta(days=1) if sh.end_time <= sh.start_time else day
            w_end = timezone.make_aware(datetime.combine(end_day, sh.end_time))
            w_start = max(w_start, start)
            w_end = min(w_end, end)
            if w_start < w_end:
                windows.append((w_start, w_end))
        day += timedelta(days=1)
    return _merge_intervals(windows)


def _parse_days(raw: str) -> set:
    if not raw:
        return set()
    return {int(x) for x in raw.split(',') if x.strip().isdigit()}


def _merge_intervals(intervals: list[tuple]) -> list[tuple]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _subtract_intervals(base: list[tuple], holes: list[tuple]) -> list[tuple]:
    """Remove `holes` (e.g. downtime) from `base` free windows."""
    if not holes:
        return list(base)
    holes = _merge_intervals(holes)
    result: list[tuple] = []
    for b_start, b_end in base:
        cursor = b_start
        for h_start, h_end in holes:
            if h_end <= cursor or h_start >= b_end:
                continue
            if h_start > cursor:
                result.append((cursor, min(h_start, b_end)))
            cursor = max(cursor, h_end)
            if cursor >= b_end:
                break
        if cursor < b_end:
            result.append((cursor, b_end))
    return result


# --- Continuous machines / warm-start ---------------------------------------

def get_continuous_machines(tenant) -> list[ContinuousMachineData]:
    """Continuous-feed machines (throughput + bar-change), for the lights-out
    feed-rate constraint."""
    from Tracker.models import ContinuousMachine

    return [
        ContinuousMachineData(
            equipment_id=cm.equipment_id,
            parts_per_hour=cm.parts_per_hour,
            bar_change_interval_hours=cm.bar_change_interval_hours,
            bar_change_duration_minutes=cm.bar_change_duration_minutes,
        )
        for cm in ContinuousMachine.objects.filter(tenant=tenant)
    ]


def get_break_windows(tenant, horizon: HorizonData) -> list[tuple]:
    """Scheduled break/lunch intervals ([start, end] datetimes) over the horizon,
    expanded from active shifts' `break_windows`. Attended (full-attention) work is
    kept out of these; actual clock-out/in lives in TimeEntry BREAK/LUNCH."""
    from Tracker.models import Shift

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True))
    intervals: list[tuple] = []
    day = horizon.start.date()
    last = horizon.end.date()
    while day <= last:
        weekday = day.weekday()
        for sh in shifts:
            active_days = _parse_days(sh.days_of_week)
            if active_days and weekday not in active_days:
                continue
            for br in (sh.break_windows or []):
                bs, be = _parse_hhmm(br.get('start')), _parse_hhmm(br.get('end'))
                if bs is None or be is None:
                    continue
                w_start = max(timezone.make_aware(datetime.combine(day, bs)), horizon.start)
                w_end = min(timezone.make_aware(datetime.combine(day, be)), horizon.end)
                if w_start < w_end:
                    intervals.append((w_start, w_end))
        day += timedelta(days=1)
    return _merge_intervals(intervals)


def _parse_hhmm(raw):
    from datetime import time as _time
    if not raw or ':' not in str(raw):
        return None
    try:
        h, m = str(raw).split(':')[:2]
        return _time(int(h), int(m))
    except (ValueError, TypeError):
        return None


def get_previous_schedule(tenant) -> PreviousScheduleData | None:
    """The active schedule's tasks — warm-start hints + the pinned tasks the
    solver must keep fixed. None when no active schedule exists yet."""
    from Tracker.models import ScheduleResult

    sched = (
        ScheduleResult.objects.filter(tenant=tenant, is_active=True)
        .order_by('-created_at').first()
    )
    if sched is None:
        return None
    tasks = tuple(
        PreviousTaskData(
            part_id=t.part_id, step_id=t.step_id, machine_id=t.machine_id,
            start_time=t.start_time, end_time=t.end_time, is_pinned=t.is_pinned,
        )
        for t in sched.tasks.all()
    )
    return PreviousScheduleData(schedule_id=sched.id, tasks=tasks)


# --- Operator dispatch (Layer 2) --------------------------------------------

def get_dispatchable_operators(tenant) -> list[OperatorData]:
    """Internal, active operators eligible for dispatch, with their rostered shift and
    work-center memberships. Dispatchable = the account is enabled, the person has an
    ACTIVE membership in this tenant (User is not tenant-scoped, so we filter
    explicitly), AND they are rostered to a shift — an operator with no shift is not
    dispatchable (Layer 2 has no availability window for them)."""
    from Tracker.models import TenantMembership, User, UserWorkCenterMembership

    active_ids = set(
        TenantMembership.objects.filter(tenant=tenant, status='ACTIVE')
        .values_list('user_id', flat=True)
    )
    users = list(
        User.objects.filter(tenant=tenant, is_active=True, user_type='INTERNAL',
                            default_shift__isnull=False)
    )

    wc: dict = {}
    primary: dict = {}
    for m in UserWorkCenterMembership.objects.filter(tenant=tenant):
        wc.setdefault(m.user_id, set()).add(m.work_center_id)
        if m.is_primary:
            primary.setdefault(m.user_id, set()).add(m.work_center_id)

    result: list[OperatorData] = []
    for u in users:
        if active_ids and u.id not in active_ids:
            continue  # has memberships configured but not active here
        name = (f"{u.first_name or ''} {u.last_name or ''}".strip()
                or u.get_username())
        result.append(OperatorData(
            user_id=u.id, name=name, shift_id=u.default_shift_id,
            work_center_ids=frozenset(wc.get(u.id, ())),
            primary_work_center_ids=frozenset(primary.get(u.id, ())),
        ))
    return result


def get_operator_shift_windows(tenant, horizon: HorizonData) -> dict[int, list[tuple]]:
    """Per dispatchable operator, the concrete [start, end] datetime windows they are
    on shift over the horizon — their rostered `default_shift` expanded. Operators with
    no shift are absent (not dispatchable). Distinct shifts are expanded once and
    shared across the operators rostered to them."""
    from Tracker.models import Shift, User

    roster = dict(
        User.objects.filter(tenant=tenant, is_active=True, user_type='INTERNAL',
                            default_shift__isnull=False)
        .values_list('id', 'default_shift_id')
    )
    shift_ids = set(roster.values())
    by_shift = {
        s.id: _expand_shifts([s], horizon.start, horizon.end)
        for s in Shift.objects.filter(tenant=tenant, id__in=shift_ids, is_active=True)
    }
    return {uid: by_shift.get(sid, []) for uid, sid in roster.items()
            if by_shift.get(sid)}


def get_shift_windows(tenant, horizon: HorizonData) -> list[tuple]:
    """The tenant's active shift calendar expanded to concrete [start, end] datetime
    windows over the horizon — the times operators can be on the floor at all. No
    per-operator roster exists yet, so this is shared across operators."""
    from Tracker.models import Shift

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True))
    return _expand_shifts(shifts, horizon.start, horizon.end)


def get_operator_unavailability(tenant, horizon: HorizonData,
                                open_entry_minutes: int = 30) -> dict[int, list[tuple]]:
    """Per operator, [start, end] datetime intervals they are NOT available to be
    dispatched — actual clock-out breaks from `TimeEntry` (BREAK / LUNCH) overlapping
    the horizon. An open entry (no end yet = currently on break) is treated as lasting
    `open_entry_minutes` from its start, so a re-dispatch mid-shift won't hand work to
    someone who just clocked out for lunch."""
    from Tracker.models import TimeEntry

    out: dict[int, list[tuple]] = {}
    entries = (
        TimeEntry.objects.filter(tenant=tenant, entry_type__in=['BREAK', 'LUNCH'])
        .filter(start_time__lt=horizon.end)
    )
    for e in entries:
        end = e.end_time or (e.start_time + timedelta(minutes=open_entry_minutes))
        if end <= horizon.start:
            continue
        out.setdefault(e.user_id, []).append((e.start_time, end))
    return {uid: _merge_intervals(iv) for uid, iv in out.items()}
