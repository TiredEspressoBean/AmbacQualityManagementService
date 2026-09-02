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

# Reman cores past teardown (all components harvested, or scrapped) have no work left.
_UNSCHEDULABLE_CORE_STATUSES = frozenset({'DISASSEMBLED', 'SCRAPPED'})


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
    split_from_lot: bool = False  # True = split off in rework, a lock-step straggler
    in_progress: bool = False     # current step has an OPEN StepExecution (work has started)
    elapsed_minutes: float = 0.0  # minutes since that in-progress op actually started


@dataclass(frozen=True)
class CoreData:
    """A reman core being torn down — scheduled like a part, through the teardown
    process, but written back as ScheduledTask.core (not .part)."""
    core_id: UUID
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
    max_minutes: int | None = None  # max elapsed from_step end → to_step start (cure window)


@dataclass(frozen=True)
class WorkOrderData:
    wo_id: UUID
    erp_id: str
    priority: int
    expected_completion: date | None
    expected_start: date | None  # earliest-release gate (no task starts before this)
    pegged_to_wo_id: UUID | None  # parent assembly WO this component job feeds (#9)
    pegged_consumes_step_id: UUID | None  # the parent step that consumes it (#9); None → whole parent waits
    lockstep_batch: bool | None  # per-WO lot cohesion; None → inherit tenant default
    quantity: int
    process_id: UUID
    parts: tuple  # tuple[PartData, ...]
    cores: tuple  # tuple[CoreData, ...] — reman teardown units on this WO
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


def get_outside_process_data(tenant, config, horizon) -> dict:
    """Outside-processing (subcontract) scheduling inputs.

    Returns `{'step_minutes': {step_id: elapsed_minutes}, 'return_min': {part_id: minute}}`:
      - `step_minutes` — the planned vendor turnaround for each outside-process step, as
        ELAPSED calendar minutes. Resolution: `Steps.outside_process_lead_days` →
        `outside_supplier.default_outside_process_turnaround_days` →
        `OptimizationConfig.default_outside_process_turnaround_days` (fallback). The solver
        schedules these as no-machine, no-crew, calendar-time intervals that gate downstream.
      - `return_min` — for parts physically AT the vendor now (an open SENT shipment), the
        expected return as minutes from the horizon start (`shipped_at + turnaround`), so a
        re-solve pins the in-flight op to its expected return instead of re-planning it.
    """
    from datetime import timedelta
    from Tracker.models import Steps, OutsideProcessShipment, StepExecution

    default_days = int(getattr(config, 'default_outside_process_turnaround_days', 7) or 7)
    step_days: dict = {}
    step_minutes: dict = {}
    for s in (Steps.objects.filter(tenant=tenant, is_current_version=True,
                                   is_outside_process=True)
              .select_related('outside_supplier')):
        days = s.outside_process_lead_days
        if days is None and s.outside_supplier_id:
            days = s.outside_supplier.default_outside_process_turnaround_days
        if days is None:
            days = default_days
        days = max(1, int(days))
        step_days[s.id] = days
        step_minutes[s.id] = days * 24 * 60  # calendar days → elapsed minutes

    return_min: dict = {}
    for sh in (OutsideProcessShipment.objects.filter(tenant=tenant, status='SENT')
               .select_related('step')):
        days = step_days.get(sh.step_id, default_days)
        expected = sh.shipped_at + timedelta(days=days)
        rmin = max(1, int((expected - horizon.start).total_seconds() // 60))
        # tenant-safe: scoped via outside_process_shipment=sh (a tenant-owned shipment).
        for pid in (StepExecution.objects
                    .filter(outside_process_shipment=sh, part__isnull=False)
                    .values_list('part_id', flat=True)):
            if pid is not None and (pid not in return_min or rmin < return_min[pid]):
                return_min[pid] = rmin

    return {'step_minutes': step_minutes, 'return_min': return_min}


def get_machine_batch_capacities(tenant) -> dict:
    """Batch/process resources split by mode:
      `{'concurrent': {equipment_id: capacity}, 'cycle': {equipment_id: capacity}}`.
    - concurrent — up to `capacity` independent jobs at once (cumulative; parallel stations).
    - cycle — a furnace/oven: ONE load at a time of ≤ `capacity` parts, fixed cycle time
      regardless of load (a job of N parts = ceil(N/capacity) loads).
    Machines at the default capacity 1 are omitted (ordinary no-overlap machines)."""
    from Tracker.models import Equipments
    concurrent: dict = {}
    cycle: dict = {}
    for e in Equipments.objects.filter(tenant=tenant, is_schedulable=True, batch_capacity__gt=1):
        (cycle if e.batch_mode == Equipments.BatchMode.CYCLE else concurrent)[e.id] = e.batch_capacity
    return {'concurrent': concurrent, 'cycle': cycle}


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

def _release_mode(tenant) -> str:
    """The tenant's release mode, defaulting to AUTO when unconfigured — an absent
    config must never hide every work order from the scheduler."""
    from Tracker.models import OptimizationConfig
    from Tracker.models.scheduling import ReleaseMode

    cfg = OptimizationConfig.objects.filter(tenant=tenant).only('release_mode').first()
    return cfg.release_mode if cfg else ReleaseMode.AUTO


def get_active_workorders(tenant) -> list[WorkOrderData]:
    """Schedulable work orders with a process, each carrying its schedulable parts
    (current step) and the process routing graph (steps + edges). Excludes finished
    (COMPLETED/CANCELLED) and held (ON_HOLD) WOs, and drops parts in a state that
    can't be worked (finished, shipped, quarantined). Under `release_mode=MANUAL`
    also drops work orders a planner hasn't released. The process graph is resolved
    once per distinct process and shared across its work orders."""
    from Tracker.models import (
        ProcessStep, StepEdge, StepExecution, WorkOrder, WorkOrderStatus,
    )
    from Tracker.models.scheduling import ReleaseMode

    excluded = [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED,
                WorkOrderStatus.ON_HOLD]
    wos = (
        WorkOrder.objects.filter(tenant=tenant, process__isnull=False)
        .exclude(workorder_status__in=excluded)
        .select_related('pegged_to_bom_line')
        .prefetch_related('parts', 'cores')
    )
    # Release gate. Under MANUAL the solver only plans work a planner authorized, so
    # the board shows authorized work and nothing else. Under AUTO (the default)
    # `released_at` is recorded but never filters — the plan stays date-driven.
    if _release_mode(tenant) == ReleaseMode.MANUAL:
        wos = wos.filter(released_at__isnull=False)

    # In-progress signal: an OPEN StepExecution (not yet exited) means work has physically
    # started on that part's current step. `entered_at` is the actual start; elapsed is
    # measured from "now" so the solver can schedule only the REMAINING duration and pin
    # the running op in place (see solver's in-progress branch). tenant-safe: .objects
    # auto-scopes to the request tenant.
    now = timezone.now()
    open_execs = {
        (se['part_id'], se['step_id']): se['entered_at']
        for se in StepExecution.objects.filter(
            tenant=tenant, exited_at__isnull=True, part__isnull=False
        ).values('part_id', 'step_id', 'entered_at')
    }

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
                         edge_type=e.edge_type, max_minutes=e.max_minutes)
                for e in StepEdge.objects.filter(process_id=process_id)
            )
            graph_cache[process_id] = (steps, edges)
        return graph_cache[process_id]

    result: list[WorkOrderData] = []
    for wo in wos:
        steps, edges = _graph(wo.process_id)
        parts = tuple(
            PartData(
                part_id=p.id, current_step_id=p.step_id,
                split_from_lot=p.split_from_lot,
                in_progress=(p.id, p.step_id) in open_execs,
                elapsed_minutes=(
                    max(0.0, (now - open_execs[(p.id, p.step_id)]).total_seconds() / 60.0)
                    if (p.id, p.step_id) in open_execs else 0.0
                ),
            )
            for p in wo.parts.all()
            if p.part_status not in _UNSCHEDULABLE_PART_STATUSES
        )
        cores = tuple(
            CoreData(core_id=c.id, current_step_id=c.step_id)
            for c in wo.cores.all()
            if c.status not in _UNSCHEDULABLE_CORE_STATUSES
        )
        consumes_step_id = (wo.pegged_to_bom_line.consumed_at_step_id
                            if wo.pegged_to_bom_line_id else None)
        result.append(WorkOrderData(
            wo_id=wo.id, erp_id=wo.ERP_id, priority=wo.priority,
            expected_completion=wo.expected_completion, expected_start=wo.expected_start,
            pegged_to_wo_id=wo.pegged_to_workorder_id,
            pegged_consumes_step_id=consumes_step_id,
            lockstep_batch=wo.lockstep_batch,
            quantity=wo.quantity,
            process_id=wo.process_id, parts=parts, cores=cores, steps=steps, edges=edges,
        ))
    return result


# --- Machine availability (shift windows minus downtime) --------------------

def get_machine_availability(tenant, horizon: HorizonData) -> dict[UUID, list[MachineWindow]]:
    """Per equipment: concrete available windows over the horizon = the machine's operating
    calendar expanded to datetimes, minus that machine's downtime. The calendar is the
    machine's own `operating_shifts` when set (per-machine calendar — a bottleneck can run
    more shifts than the floor), else the tenant-wide active shift calendar. (Plant closures
    are applied separately by the solver, which blocks every machine.)"""
    from Tracker.models import DowntimeEvent, Equipments, Shift

    tenant_shifts = list(Shift.objects.filter(tenant=tenant, is_active=True, is_current_version=True))
    tenant_base = _expand_shifts(tenant_shifts, horizon.start, horizon.end)
    base_cache: dict[tuple, list] = {}

    def _base_for(eq):
        own = [s for s in eq.operating_shifts.all() if s.is_active]
        if not own:
            return tenant_base
        key = tuple(sorted(str(s.id) for s in own))
        if key not in base_cache:
            base_cache[key] = _expand_shifts(own, horizon.start, horizon.end)
        return base_cache[key]

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
    for eq in (Equipments.objects.filter(tenant=tenant)
               .select_related('equipment_type').prefetch_related('operating_shifts')):
        free = _subtract_intervals(_base_for(eq), downtime.get(eq.id, []))
        # Calibration-as-time-window: a machine calibrated now but whose calibration
        # lapses within the horizon is available only up to that expiry — not for the
        # whole horizon. Without this, `get_step_equipment_affinities` keeps the
        # (currently-operational) machine eligible and the solver would schedule work
        # onto it past the lapse. A machine that is already non-current is dropped by
        # the affinity filter; truncating to `horizon.start` here keeps availability
        # self-consistent with that.
        if eq.requires_calibration:
            expiry = _calibration_expiry(eq, horizon)
            free = [(s, min(e, expiry)) for (s, e) in free if s < expiry]
        result[eq.id] = [MachineWindow(equipment_id=eq.id, start=s, end=e) for s, e in free]
    return result


def _calibration_expiry(equipment, horizon: HorizonData) -> datetime:
    """The datetime a machine's calibration lapses, clamped for scheduling.
    Returns `horizon.start` (i.e. no availability) when calibration is not current
    or has never been recorded; otherwise the end of the calibration due date (the
    gauge is usable through the due date, unavailable the following day)."""
    if not equipment.is_calibration_current:
        return horizon.start
    from datetime import time as _time
    due = equipment.next_calibration_due  # a date, or None
    if due is None:
        return horizon.start
    return timezone.make_aware(datetime.combine(due + timedelta(days=1), _time.min))


def get_step_labor_models(tenant) -> dict[UUID, str]:
    """Effective labor model per current step: the step's own `labor_model`, else the
    tenant's `OptimizationConfig.default_labor_model` ('pool' when unconfigured). One of
    'off' | 'pool' | 'named' — how the solver constrains that step's operators."""
    from Tracker.models import OptimizationConfig, Steps

    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    default = cfg.default_labor_model if cfg else 'pool'
    return {
        s.id: (s.labor_model or default)
        for s in Steps.objects.filter(tenant=tenant, is_current_version=True)
    }


def get_step_operator_pools(tenant) -> dict[UUID, frozenset]:
    """For each TRAINING-GATED step, the dispatchable operators qualified to run it:
    `step_id -> frozenset(user_id)`. Ungated steps are omitted — any operator can run
    them, so they're governed by the total-crew cap, not a per-skill one. Lets Layer-1
    cap a scarce skill (e.g. one assembler) at its trained crew, so that work serializes
    and pushes late instead of piling up uncoverable."""
    from Tracker.models import Steps
    from Tracker.services.training import (
        get_qualified_users_for_step, get_required_training,
    )

    op_ids = {o.user_id for o in get_dispatchable_operators(tenant)}
    pools: dict[UUID, frozenset] = {}
    for step in Steps.objects.filter(tenant=tenant, is_current_version=True):
        if not get_required_training(step):
            continue
        qualified = {u.id for u in get_qualified_users_for_step(step, tenant=tenant)}
        pools[step.id] = frozenset(qualified & op_ids)
    return pools


def get_attended_only_machines(tenant) -> frozenset:
    """Machines that CANNOT run lights-out: their Layer-1 work is confined to the shift
    calendar (an operator must be present). Everything else runs 24/7, gated only by
    downtime — a lot-operation may span nights.

    Tri-state resolution: a machine's `runs_unattended` overrides; NULL inherits the
    facility default (`OptimizationConfig.default_machine_unattended`, itself defaulting
    to attended — the safe choice)."""
    from Tracker.models import Equipments, OptimizationConfig

    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    default_unattended = bool(cfg.default_machine_unattended) if cfg else False
    attended = set()
    for eid, ru in Equipments.objects.filter(tenant=tenant).values_list('id', 'runs_unattended'):
        effective_unattended = ru if ru is not None else default_unattended
        if not effective_unattended:
            attended.add(eid)
    return frozenset(attended)


def get_machine_downtime(tenant, horizon: HorizonData) -> dict[UUID, list[tuple]]:
    """Per equipment: merged [start, end] downtime intervals overlapping the horizon.
    The machine is unavailable during these regardless of lights-out status (a down
    machine is down); the 24/7 default subtracts only these from the timeline."""
    from Tracker.models import DowntimeEvent

    out: dict[UUID, list[tuple]] = {}
    for d in (
        DowntimeEvent.objects.filter(tenant=tenant, equipment__isnull=False)
        .filter(start_time__lt=horizon.end)
        .exclude(end_time__lt=horizon.start)
    ):
        out.setdefault(d.equipment_id, []).append(
            (d.start_time, d.end_time or horizon.end)
        )
    return {eq: _merge_intervals(iv) for eq, iv in out.items()}


def _yearly_closure_occurrences(e, horizon: HorizonData) -> list[tuple]:
    """A YEARLY closure recurs on its stored month/day span every year. Emit the
    occurrence(s) landing in the horizon (a 30-day window touches at most two years)."""
    span = e.end_time - e.start_time
    out = []
    for year in {horizon.start.year, horizon.end.year}:
        try:
            occ_start = e.start_time.replace(year=year)
        except ValueError:
            continue  # Feb 29 in a non-leap year — skip this year
        occ_end = occ_start + span
        if occ_start < horizon.end and occ_end >= horizon.start:
            out.append((max(occ_start, horizon.start), min(occ_end, horizon.end)))
    return out


def get_calendar_closures(tenant, horizon: HorizonData) -> list[tuple]:
    """Tenant-wide plant closures — holidays / shutdowns / inventory days — overlapping the
    horizon, as merged [start, end] datetime intervals. The scheduler blocks EVERY machine
    during these and treats operators as absent. ONCE closures use their dated span; YEARLY
    closures recur on their month/day each year. Empty when none are configured."""
    from Tracker.models import PlantCalendarException

    out: list[tuple] = []
    for e in PlantCalendarException.objects.filter(tenant=tenant, is_active=True):
        if e.recurrence == 'YEARLY':
            out.extend(_yearly_closure_occurrences(e, horizon))
        elif e.start_time < horizon.end and e.end_time >= horizon.start:
            out.append((max(e.start_time, horizon.start), min(e.end_time, horizon.end)))
    return _merge_intervals(out)


def get_working_windows(tenant, start: datetime, end: datetime) -> list[tuple]:
    """Tenant-wide working windows (merged, sorted) over [start, end] — the active
    shift calendar expanded to datetimes, PLUS overtime (extra/weekend runs), minus
    plant closures (holidays/shutdowns). The complement is non-working time
    (nights/weekends/holidays), which the Gantt shades. Overtime is unioned in so the
    Gantt doesn't shade an overtime day as non-working while the solver schedules
    operators on it (get_operator_shift_windows counts the same overtime). Empty when
    no shifts are configured (the solver treats that as always-available)."""
    from Tracker.models import PlantCalendarException, Shift

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True, is_current_version=True))
    horizon = HorizonData(start=start, end=end, frozen_end=start, slushy_end=start)
    base = _merge_intervals(
        _expand_shifts(shifts, start, end) + get_overtime_machine_windows(tenant, horizon))
    closures = _merge_intervals([
        (max(e.start_time, start), min(e.end_time, end))
        for e in PlantCalendarException.objects.filter(tenant=tenant, is_active=True)
        .filter(start_time__lt=end).exclude(end_time__lt=start)
    ])
    return _subtract_intervals(base, closures)


# Fallback purchase lead time (days) for a BUY component whose Material/PartTypes
# record has no purchase_lead_time_days set. Only the order-by window for
# unconfigured items depends on it; a real lead time on the master data overrides.
_DEFAULT_LEAD_DAYS = 14


def get_material_gates(tenant, horizon: HorizonData):
    """Buy-side material availability, per operation. For each active work order, net its
    released ASSEMBLY BOM's BUY-line demand (line.quantity × WO quantity) against on-hand
    accepted stock of that component. When short:
      - if incoming lots carry a promised delivery date, GATE the consuming operation so it
        can't start before the earliest such date (a release lower bound);
      - otherwise FLAG a shortage (scheduled anyway, surfaced to the planner).
    A reman line that allows harvested components is treated as covered by teardown and
    skipped (new-build never skips). Cores are the reman unit, never purchasable material.

    Returns (release, short, detail): release[(wo_id, step_id | None)] = earliest-start
    minute; short = set of (wo_id, step_id | None); detail[key] = human string naming the
    short component(s), shortfall, and receipt date. A None step = the whole WO (no
    consumed_at_step authored). tenant-safe: all .objects calls auto-scope to the tenant.
    """
    from collections import defaultdict
    from datetime import datetime as _dt, time as _time
    from django.db.models import Sum
    from Tracker.models import BOM, BOMLine, MaterialLot, WorkOrder, WorkOrderStatus

    onhand = {
        row['material']: float(row['q'] or 0)
        for row in MaterialLot.objects.filter(tenant=tenant, status__in=('ACCEPTED', 'IN_USE'))
        .values('material').annotate(q=Sum('quantity_remaining'))
    }
    receipts: dict = defaultdict(list)
    for lot in (
        MaterialLot.objects.filter(tenant=tenant, promised_date__isnull=False,
                                   quantity_remaining__gt=0)
        .exclude(status__in=('CONSUMED', 'SCRAPPED', 'REJECTED'))
        .values('material_id', 'promised_date')
    ):
        receipts[lot['material_id']].append(lot['promised_date'])

    bom_cache: dict = {}

    def _bom_lines(pt_id):
        if pt_id not in bom_cache:
            # Latest RELEASED — not is_current_version: an open draft revision flips the
            # released row non-current but the floor still builds to it, so the material
            # gate must keep seeing it (else drafting a rev silently drops the gate).
            bom = (BOM.objects.filter(part_type_id=pt_id, bom_type='ASSEMBLY',
                   status='RELEASED').order_by('-version').first())
            # tenant-safe: `bom` is a tenant-scoped row; its lines belong to the same tenant.
            bom_cache[pt_id] = (
                list(BOMLine.objects.filter(bom=bom).values(
                    'material_id', 'material__name', 'material__purchase_lead_time_days',
                    'quantity', 'source', 'consumed_at_step_id', 'allow_harvested',
                    'is_optional'))
                if bom else [])
        return bom_cache[pt_id]

    excluded = [WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED, WorkOrderStatus.ON_HOLD]
    release: dict = {}
    short: set = set()
    detail: dict = {}  # (wo_id, step_id|None) -> [human shortage lines]
    hstart_date = horizon.start.date()
    for wo in (WorkOrder.objects.filter(tenant=tenant, process__isnull=False)
               .exclude(workorder_status__in=excluded)
               .select_related('process').prefetch_related('cores')):
        pt_id = wo.process.part_type_id
        if pt_id is None:
            continue
        is_reman = wo.cores.exists()
        for line in _bom_lines(pt_id):
            if line['source'] != 'BUY' or line['is_optional']:
                continue
            if is_reman and line['allow_harvested']:
                continue  # a harvested component from teardown covers this line
            mat_id = line['material_id']
            if mat_id is None:
                continue  # BUY line without a Material set (misconfigured) — nothing to net
            required = float(line['quantity']) * wo.quantity
            have = onhand.get(mat_id, 0.0)
            if have >= required:
                continue  # enough on hand → no gate
            key = (wo.id, line['consumed_at_step_id'])  # step_id, or None = whole WO
            comp = line['material__name'] or "component"
            short_qty = int(round(required - have))
            need = int(round(required))
            future = [d for d in receipts.get(mat_id, []) if d >= hstart_date]
            if future:
                d = min(future)
                naive = _dt.combine(d, _time.min)
                aware = timezone.make_aware(naive) if timezone.is_naive(naive) else naive
                rmin = max(0, int((aware - horizon.start).total_seconds() // 60))
                release[key] = max(release.get(key, 0), rmin)
                msg = f"{comp}: short {short_qty} of {need} (due {d:%b %d})"
            else:
                # Time-phased: a short BUY line with no incoming receipt is only a
                # shortage EXCEPTION once we're at/after the order-by date
                # (need-by − purchase lead time) — i.e. too late to procure normally.
                # Demand further out simply hasn't been ordered yet: normal, not a
                # shortage. Same need-by − lead-time basis as the sourcing report.
                # An undated active WO reads as imminent (flagged).
                lead = line.get('material__purchase_lead_time_days') or _DEFAULT_LEAD_DAYS
                need_by = wo.expected_start or wo.expected_completion
                if need_by is not None and hstart_date < need_by - timedelta(days=lead):
                    continue  # before order-by → still time to procure, not short
                short.add(key)
                msg = f"{comp}: short {short_qty} of {need} (no incoming receipt)"
            detail.setdefault(key, []).append(msg)
    detail = {k: "; ".join(v) for k, v in detail.items()}
    return release, short, detail


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

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True, is_current_version=True))
    intervals: list[tuple] = []
    day = horizon.start.date()
    last = horizon.end.date()
    while day <= last:
        weekday = day.weekday()
        for sh in shifts:
            active_days = _parse_days(sh.days_of_week)
            if active_days and weekday not in active_days:
                continue
            # Serializer validates shape on write; the isinstance guards keep a
            # legacy/hand-edited bad row degrading to "break ignored", not a
            # crashed solve.
            windows = sh.break_windows if isinstance(sh.break_windows, list) else []
            for br in windows:
                if not isinstance(br, dict):
                    continue
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
        for t in sched.tasks.filter(part__isnull=False)   # core tasks: no pin/warm-start in v1
    )
    return PreviousScheduleData(schedule_id=sched.id, tasks=tasks)


# --- Operator dispatch (Layer 2) --------------------------------------------

# The scheduler treats as shop-floor operators only users in these tenant groups
# (the seeded `TenantGroup` names). Gating on the group keeps non-floor staff — admins,
# managers, QA, engineering — out of the dispatch roster even if they have a shift set.
SHOP_FLOOR_GROUPS = ('Operator', 'Shift Lead')


def _shop_floor_user_ids(tenant) -> set:
    """Ids of users who belong to the tenant's shop-floor groups (Operator / Shift Lead),
    via UserRole → TenantGroup. Empty when the tenant hasn't put anyone in those groups —
    callers then fall back to the internal+shift roster so scheduling still works."""
    from Tracker.models import User

    # tenant-safe: scoped through user_roles__group__tenant (User is not tenant-scoped).
    return set(
        User.objects.filter(
            user_roles__group__name__in=SHOP_FLOOR_GROUPS,
            user_roles__group__tenant=tenant,
        ).values_list('id', flat=True).distinct()
    )


def get_dispatchable_operators(tenant) -> list[OperatorData]:
    """Internal, active operators eligible for dispatch, with their rostered shift and
    work-center memberships. Dispatchable = the account is enabled, the person has an
    ACTIVE membership in this tenant (User is not tenant-scoped, so we filter
    explicitly), they are in a shop-floor group (Operator / Shift Lead — so admins and
    office staff aren't scheduled), AND they are rostered to a shift (Layer 2 needs an
    availability window). When no one is in a shop-floor group yet, the group gate is
    skipped so an un-configured tenant still schedules."""
    from Tracker.models import TenantMembership, User, UserWorkCenterMembership

    active_ids = set(
        TenantMembership.objects.filter(tenant=tenant, status='ACTIVE')
        .values_list('user_id', flat=True)
    )
    users = list(
        User.objects.filter(tenant=tenant, is_active=True, user_type='INTERNAL',
                            default_shift__isnull=False)
    )
    shop_ids = _shop_floor_user_ids(tenant)
    if shop_ids:
        users = [u for u in users if u.id in shop_ids]

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


def _labor_block_intervals(block, horizon: HorizonData) -> list[tuple]:
    """Concrete [start, end] datetime intervals a LaborCalendarBlock covers over the
    horizon. ONCE = its clamped datetime span; WEEKLY = its time-of-day window on each
    matching day-of-week (reusing the shift expander). Malformed rows yield nothing."""
    from types import SimpleNamespace

    if block.recurrence == 'WEEKLY':
        if block.window_start is None or block.window_end is None:
            return []
        shim = SimpleNamespace(
            days_of_week=block.days_of_week or '',
            start_time=block.window_start, end_time=block.window_end)
        return _expand_shifts([shim], horizon.start, horizon.end)
    # ONCE
    if block.start_time is None or block.end_time is None:
        return []
    if block.start_time >= horizon.end or block.end_time <= horizon.start:
        return []
    return [(max(block.start_time, horizon.start), min(block.end_time, horizon.end))]


def get_labor_calendar_blocks(tenant, horizon: HorizonData):
    """Operator non-working time over the horizon from `LaborCalendarBlock` — PTO,
    sick, training, meetings, ad-hoc breaks — one-off or weekly, company-wide or for
    one person. Returns `(company, by_user)`: `company` is merged intervals that apply
    to EVERY operator (user is null — e.g. an all-hands); `by_user` maps a user id to
    their own merged intervals. Machines are unaffected (a meeting doesn't stop a
    lights-out CNC — only PlantCalendarException does)."""
    from Tracker.models import LaborCalendarBlock

    company: list[tuple] = []
    by_user: dict[int, list[tuple]] = {}
    rows = LaborCalendarBlock.objects.filter(tenant=tenant, is_active=True)
    for b in rows:
        intervals = _labor_block_intervals(b, horizon)
        if not intervals:
            continue
        if b.user_id is None:
            company.extend(intervals)
        else:
            by_user.setdefault(b.user_id, []).extend(intervals)
    return _merge_intervals(company), {u: _merge_intervals(iv) for u, iv in by_user.items()}


def _overtime_intervals(o, shift, horizon: HorizonData) -> list[tuple]:
    """Concrete datetime windows for one overtime entry: the shift's hours on the days
    it runs — ONCE across [start_date, end_date], WEEKLY on days_of_week — clipped to
    the horizon. Hours come from the referenced shift (overnight handled by the shift
    expander)."""
    from types import SimpleNamespace
    from datetime import time as _time

    if o.recurrence == 'WEEKLY':
        if not (o.days_of_week or '').strip():
            return []
        shim = SimpleNamespace(days_of_week=o.days_of_week,
                               start_time=shift.start_time, end_time=shift.end_time)
        return _expand_shifts([shim], horizon.start, horizon.end)
    # ONCE — run the shift's hours on each date in [start_date, end_date]
    if not o.start_date or not o.end_date:
        return []
    lo = max(timezone.make_aware(datetime.combine(o.start_date, _time.min)), horizon.start)
    hi = min(timezone.make_aware(datetime.combine(o.end_date, _time.max)), horizon.end)
    if lo >= hi:
        return []
    shim = SimpleNamespace(days_of_week='',  # every date in the range
                           start_time=shift.start_time, end_time=shift.end_time)
    return _expand_shifts([shim], lo, hi)


def get_overtime_windows(tenant, horizon: HorizonData) -> dict[int, list[tuple]]:
    """Extra runs of each shift over the horizon → {shift_id: [(s,e)] merged}. An
    `OvertimeWindow` names a Shift (its hours + crew); ONCE runs it on a date range,
    WEEKLY on weekdays. Operators rostered to a shift get that shift's overtime (so a
    'Night shift Saturday' pulls the night crew, not the whole company). Attended
    machines get the union — see get_overtime_machine_windows."""
    from Tracker.models import OvertimeWindow

    by_shift: dict[int, list[tuple]] = {}
    for o in (OvertimeWindow.objects.filter(tenant=tenant, is_active=True)
              .select_related('shift')):
        sh = o.shift
        if sh is None or not sh.is_active:
            continue
        iv = _overtime_intervals(o, sh, horizon)
        if iv:
            by_shift.setdefault(sh.id, []).extend(iv)
    return {sid: _merge_intervals(v) for sid, v in by_shift.items()}


def get_overtime_machine_windows(tenant, horizon: HorizonData) -> list[tuple]:
    """Union of ALL overtime windows over the horizon (merged) — attended machines are
    open whenever any overtime shift is running (the shop is running)."""
    by_shift = get_overtime_windows(tenant, horizon)
    return _merge_intervals([iv for lst in by_shift.values() for iv in lst])


def get_operator_shift_windows(tenant, horizon: HorizonData) -> dict[int, list[tuple]]:
    """Per dispatchable operator, the concrete [start, end] datetime windows they are
    available over the horizon: their rostered `default_shift` expanded, PLUS company
    overtime (extra/weekend shifts), MINUS plant closures (closures always win), MINUS
    company-wide labor blocks (all-hands) and their own blocks (PTO/sick/training).
    Operators fully unavailable over the horizon are dropped. Shifts and overtime are
    expanded once and shared; blocks are subtracted per operator."""
    from Tracker.models import Shift, User

    roster = dict(
        User.objects.filter(tenant=tenant, is_active=True, user_type='INTERNAL',
                            default_shift__isnull=False)
        .values_list('id', 'default_shift_id')
    )
    shop_ids = _shop_floor_user_ids(tenant)  # gate to shop-floor groups when configured
    if shop_ids:
        roster = {uid: sid for uid, sid in roster.items() if uid in shop_ids}
    shift_ids = set(roster.values())
    closures = get_calendar_closures(tenant, horizon)
    by_shift = {
        s.id: _expand_shifts([s], horizon.start, horizon.end)
        for s in Shift.objects.filter(tenant=tenant, id__in=shift_ids, is_active=True, is_current_version=True)
    }
    overtime_by_shift = get_overtime_windows(tenant, horizon)  # {shift_id: [(s,e)]}
    company_blocks, user_blocks = get_labor_calendar_blocks(tenant, horizon)
    out: dict[int, list[tuple]] = {}
    for uid, sid in roster.items():
        # Overtime is scoped to the shift's own crew — an operator only gets the extra
        # runs of the shift they're rostered to.
        overtime = overtime_by_shift.get(sid, [])
        windows = _merge_intervals(by_shift.get(sid, []) + overtime)  # shift + its overtime
        windows = _subtract_intervals(windows, closures)             # closures always win
        own = user_blocks.get(uid)
        blocks = _merge_intervals(company_blocks + own) if own else company_blocks
        if blocks:
            windows = _subtract_intervals(windows, blocks)
        if windows:
            out[uid] = windows
    return out


def get_shift_windows(tenant, horizon: HorizonData) -> list[tuple]:
    """The tenant's active shift calendar expanded to concrete [start, end] datetime
    windows over the horizon — the times operators can be on the floor at all. No
    per-operator roster exists yet, so this is shared across operators."""
    from Tracker.models import Shift

    shifts = list(Shift.objects.filter(tenant=tenant, is_active=True, is_current_version=True))
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
