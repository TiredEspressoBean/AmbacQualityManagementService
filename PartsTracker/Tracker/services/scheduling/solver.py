"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`).

Layers built so far:
- Lot-based route-aware tasks: a WO's parts at the SAME current step form one lot that
  moves through the remaining nominal route together (DEFAULT edges; rework/scrap
  excluded), scheduled as one machine occupancy per operation sized by the lot's piece
  count (cycle × count). Parts stranded at different steps form separate lots. Written
  back per part (each shares the lot's window) so tracking/pins stay part-grained.
  Merge-capable DAG precedence (see `routing.resolve_route`). A reman core is a part
  (Documents/CORE_AS_PART_DESIGN.md): teardown cores batch like any part, and a core
  under rebuild schedules on its own (`PartData.individual`) since its scope is its own.
- Lock-step batches: a WO's parts at one step schedule as one cohesive lot (one
  occupancy, one synchronized start). A part split off to rework (`split_from_lot`) is
  carved into its OWN lot so the cohort keeps progressing — the batch is NOT held for a
  straggler; the split part schedules its own rework path and re-converges later via
  `rejoin_part_to_lot` (`Parts.rejoined_at`), else at finished goods.
- Machine choice: one of the step's eligible schedulable machines (optional intervals
  + exactly-one), honoring per-machine `cycle_time_override`; one task per machine.
- Cost objective (integer cents): Σ (lot lateness × the WO's priority penalty) +
  makespan tiebreaker + a small preferred/dialed-in machine nudge.
- Durations carry a PFD (personal/fatigue/delay) allowance on attended run time.
- Calendars: machines run lights-out (24/7, blocked only by downtime) by default, so a
  lot-operation may span nights/weekends; machines flagged `runs_unattended=False` are
  confined to the shift calendar instead.
- Labor capacity: concurrent attended operations are capped at the crew on shift (one
  operator per lot-op) AND, for training-gated steps, at the qualified crew on shift —
  so a scarce skill (e.g. one assembler) serializes and pushes work late instead of
  piling up uncoverable, and attended work is kept to staffed hours while machines run
  unattended. A step no rostered operator is trained for makes the solve refuse
  (`LaborInfeasible`) — that work can't be executed at all. Which operator takes each
  task is still a Layer-2 (dispatch) concern; breaks live there too.
- Secondary resources: a step's schedulable gauges (Keyence/CMM) are reserved
  one-at-a-time while the task runs.
- Fixtures: shared tooling as a cumulative resource (≤ quantity concurrent users).
- Setup/changeover: sequence-dependent transition gaps between machine neighbours.
- Continuous machines: throughput-based duration + recurring bar-change downtime.
- Time fences + warm-start: frozen-zone / planner-pinned tasks held to the previous
  schedule (time and machine) by a SOFT penalty — a re-solve after the world changed
  moves them the minimum instead of going INFEASIBLE, and reports the count
  (`relaxed_pin_count`); slushy/liquid tasks seeded as solver hints.
- Cross-WO pegs: a component WO must finish (+ staging buffer) before its parent
  assembly WO starts (WorkOrder.pegged_to_workorder; multi-level chains transitively).

Follow-ons: changeover-as-circuit (scalability), transfer-batching. Time is
discretized to integer minutes from `horizon.start`; results are written back as
absolute datetimes.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta
from decimal import Decimal
from uuid import UUID

from django.utils import timezone

from Tracker.services.scheduling import data
from Tracker.services.scheduling.routing import resolve_route
from Tracker.utils.tenant_context import tenant_context

logger = logging.getLogger(__name__)

_PENALTY_FIELD = {1: 'late_penalty_urgent', 2: 'late_penalty_high',
                  3: 'late_penalty_normal', 4: 'late_penalty_low'}
_PENALTY_DEFAULT = {1: Decimal('1000'), 2: Decimal('500'),
                    3: Decimal('100'), 4: Decimal('25')}
_MINUTES_PER_DAY = 24 * 60

# Lightweight window for feeding overtime intervals (plain (start, end) tuples from
# data.get_overtime_windows) into _window_gaps, which reads .start / .end.
from collections import namedtuple as _namedtuple
_OTWindow = _namedtuple('_OTWindow', ('start', 'end'))

# The time fence (user decision 2026-10-21, after re-solves were measured compounding:
# cold 0.8% gap / 1 late order vs 96% / 3 late on the same inputs).
#
# FROZEN and planner-PINNED operations keep their machine, their operator and their ORDER
# on that machine — "freeze the order, not the clock" (user decision 2026-10-21). Their
# start may only slide LATER, and only when what is ahead of them runs late: each minute
# of slide costs `_SLIDE_WEIGHT_FACTOR` x the Urgent late penalty, so held work is never
# moved to make room for anything. Fixed clock times made any work that slipped past its
# slot — every re-solve runs minutes after the last — lose its place and queue behind
# the whole frozen window (3x lateness on dev). Held work that can't happen on its
# machine at all (`_frozen_refusal`) goes back to normal planning, reported with why. The soft pins they replace (10,000-100,000/min, 1,000,000 per machine change)
# swamped lateness: each re-solve protected stale positions, pushed new work late, and
# the next re-solve inherited it.
#
# SLUSHY operations prefer to stay put, on the LATENESS scale: moving one costs a
# quarter of a Normal-priority late minute per minute, and changing its machine about
# an hour of Normal lateness — so slushy work moves when that saves real lateness.
SLUSHY_STICKINESS = 0.25
_SLIDE_WEIGHT_FACTOR = 4

# Seed each solve with a dispatch-rule plan (`_greedy_plan`) for the work the live plan
# doesn't already hint. A module flag so a benchmark can compare with and without.
USE_GREEDY_HINT = True
_SLUSHY_MACHINE_MINUTES = 60
# Blowing a max-time-between-ops window (cure/coat/pot-life) means the part scraps or
# reworks — heavily penalized (flat, per violated edge) so the solver only relaxes it when
# capacity genuinely can't meet the window; then the op is flagged, never a hard INFEASIBLE.
_CURE_WINDOW_WEIGHT = 200_000     # flat, per violated max-time edge


def _pfd_factor(config) -> float:
    """PFD (personal/fatigue/delay) allowance as a duration multiplier. Inflates
    attended run time to account for the operator's unavoidable micro-stoppages;
    unattended machine time isn't extended by an operator allowance."""
    pct = float(getattr(config, 'pfd_allowance_pct', 0) or 0) if config else 0.0
    return 1.0 + max(0.0, pct) / 100.0


def _dur(timing, affinity, pfd_factor: float = 1.0, quantity: int = 1) -> int:
    """Machine minutes for a lot-operation: the per-piece cycle × the lot's piece
    count. Setup is NOT folded in here — it's charged separately as the changeover
    gap when a machine switches operations (see `_transition`)."""
    cycle = None
    if affinity is not None and affinity.cycle_time_override is not None:
        cycle = affinity.cycle_time_override
    elif timing is not None:
        cycle = timing.cycle_time_minutes
    if not cycle:
        return 1
    # PFD inflates ATTENDED time only (the field is "added to attended time"); a
    # load/unload step's machine runs unattended, so its cycle isn't stretched.
    attended = (timing is None) or (timing.attention_type == 'full')
    eff = cycle * pfd_factor if attended else cycle
    return max(1, round(eff * max(1, quantity)))


def _batch_cycle_dur(timing, capacity: int, count: int) -> int:
    """Furnace/oven ('cycle' batch mode): the cycle time is FIXED per load regardless of how
    full it is, and a lot of `count` parts takes ceil(count / capacity) loads run back-to-back
    (one load at a time). So machine time = setup + cycle_time × n_loads — NOT per-part time."""
    import math
    cycle = timing.cycle_time_minutes if timing is not None else 0.0
    setup = timing.setup_minutes if timing is not None else 0.0
    n_loads = max(1, math.ceil(max(1, count) / max(1, capacity)))
    return max(1, round(setup + cycle * n_loads))


def _dur_on_machine(timing, affinity, continuous, pfd_factor: float = 1.0,
                    quantity: int = 1) -> int:
    """Lot minutes on a machine. Continuous-feed machines use throughput
    (60 / parts_per_hour × count, lights-out — no PFD); everything else uses the step
    cycle / override × count, PFD-inflated when attended."""
    cm = continuous.get(affinity.equipment_id)
    if cm is not None and cm.parts_per_hour:
        return max(1, round(60.0 / cm.parts_per_hour * max(1, quantity)))
    return _dur(timing, affinity, pfd_factor, quantity)


# Machine-preference nudge: choosing a less-preferred machine costs a small objective
# penalty so the solver favors dialed_in > preferred > eligible when the schedule is
# otherwise equivalent. Kept tiny (a few makespan-minutes) so it only breaks ties and
# never makes a job late just to honor a preference.
_AFFINITY_PENALTY = {'dialed_in': 0, 'preferred': 3, 'eligible': 8}
_AFFINITY_PENALTY_DEFAULT = 8


def _affinity_penalty(affinity_level) -> int:
    return _AFFINITY_PENALTY.get(affinity_level, _AFFINITY_PENALTY_DEFAULT)


def _fence_zone(start_min, frozen_min, slushy_min):
    from Tracker.models.scheduling import FenceZone
    if start_min < frozen_min:
        return FenceZone.FROZEN
    if start_min < slushy_min:
        return FenceZone.SLUSHY
    return FenceZone.LIQUID


_JOB_CHANGE_DEFAULT = 10   # minutes — minor setup to switch work orders on the same op


def _job_change_minutes(config) -> int:
    """Setup charged when a resource switches to a different work order on the SAME
    operation — keeps a job's parts batched. Below op-change setups by design (op
    continuity outranks WO continuity)."""
    v = getattr(config, 'job_change_minutes', None) if config else None
    return int(v) if v is not None else _JOB_CHANGE_DEFAULT


def _penalty_cents_per_min(config, priority: int) -> int:
    if config is not None:
        dollars_per_day = getattr(config, _PENALTY_FIELD.get(priority, 'late_penalty_normal'))
    else:
        dollars_per_day = _PENALTY_DEFAULT.get(priority, Decimal('100'))
    return max(0, round(float(dollars_per_day) * 100 / _MINUTES_PER_DAY))


def _due_minutes(due_date, horizon_start, H) -> int | None:
    if due_date is None:
        return None
    due_dt = timezone.make_aware(datetime.combine(due_date, dtime.max))
    minutes = int((due_dt - horizon_start).total_seconds() // 60)
    return max(-H, minutes)


def _release_minutes(start_date, horizon_start, H) -> int:
    """Earliest a WO's work may begin: start-of-day of its expected_start, clamped
    to [0, H]. 0 (already releasable) when unset or in the past."""
    if start_date is None:
        return 0
    rel_dt = timezone.make_aware(datetime.combine(start_date, dtime.min))
    return max(0, min(H, int((rel_dt - horizon_start).total_seconds() // 60)))


def _to_minutes(intervals, horizon_start, H) -> list[tuple]:
    """Datetime intervals → clipped integer-minute [start, end] tuples from H0."""
    out = []
    for s, e in intervals:
        ms = max(0, int((s - horizon_start).total_seconds() // 60))
        me = min(H, int((e - horizon_start).total_seconds() // 60))
        if ms < me:
            out.append((ms, me))
    return out


def _window_gaps(windows, horizon_start, H) -> list[tuple]:
    """Unavailable [start, end] minute intervals between a machine's availability
    windows, within [0, H]. Empty when the machine has no windows (treated as
    always-available so a tenant with no shift config still schedules)."""
    if not windows:
        return []
    mins = []
    for w in windows:
        s = max(0, int((w.start - horizon_start).total_seconds() // 60))
        e = min(H, int((w.end - horizon_start).total_seconds() // 60))
        if s < e:
            mins.append((s, e))
    mins.sort()
    gaps = []
    cursor = 0
    for s, e in mins:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < H:
        gaps.append((cursor, H))
    return gaps


def _merge_minute_gaps(gaps) -> list[tuple]:
    """Merge integer-minute [s, e) gaps into a disjoint, sorted set — so the blocked
    intervals fed to a single AddNoOverlap never overlap each other (which would make the
    constraint infeasible)."""
    if not gaps:
        return []
    gaps = sorted(gaps)
    out = [gaps[0]]
    for s, e in gaps[1:]:
        ls, le = out[-1]
        if s <= le:
            out[-1] = (ls, max(le, e))
        else:
            out.append((s, e))
    return out


def _staffing_segments(op_windows, horizon_start, H):
    """Piecewise operator headcount over [0, H] from the rostered shift windows:
    a list of (start_min, end_min, count) covering the whole horizon (count 0 where
    nobody is on shift), plus the peak count. Drives the labor-capacity cumulative —
    concurrent attended work is capped at the crew on hand, and attended work is barred
    from unstaffed hours (count 0) while machines keep running lights-out."""
    delta: dict = defaultdict(int)
    for windows in op_windows.values():
        for s, e in windows:
            ms = max(0, int((s - horizon_start).total_seconds() // 60))
            me = min(H, int((e - horizon_start).total_seconds() // 60))
            if ms < me:
                delta[ms] += 1
                delta[me] -= 1
    if not delta:
        return 0, []
    points = sorted(set([0, H]) | set(delta))
    segs, count = [], 0
    for i in range(len(points) - 1):
        count += delta.get(points[i], 0)
        a, b = points[i], points[i + 1]
        if a < b:
            segs.append((a, b, count))
    cap_max = max((c for _, _, c in segs), default=0)
    return cap_max, segs


def _transition(changeover, equipment_id, from_step, to_step, to_setup,
                from_wo=None, to_wo=None, job_change=0) -> int:
    """Minutes between consecutive tasks on a machine — the setup the solver pays to
    switch, so it prefers to keep a resource on the same work:
    - same step AND same work order → 0 (piece after piece within one job's batch);
    - same step, DIFFERENT work order → `job_change` (a job change on the same
      operation: paperwork, re-fixturing, first-off — keeps a WO's parts together);
    - different step → the WorkCenterChangeover value, or the incoming step's setup
      as a fallback (an operation change).
    These costs push switching later, so minimizing makespan/lateness batches work."""
    if from_step == to_step:
        return 0 if from_wo == to_wo else job_change
    # Operation change. Keeping the same OPERATION matters more than keeping the same
    # work order, so an op change never costs less than a job change (floor at
    # job_change); a configured changeover/setup above that is used as-is.
    val = changeover.get((equipment_id, from_step, to_step))
    op_change = int(round(val)) if val is not None else to_setup
    return max(op_change, job_change)


def _map_status(cp_status) -> str:
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import SolverStatus
    return {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.MODEL_INVALID: SolverStatus.MODEL_INVALID,
    }.get(cp_status, SolverStatus.UNKNOWN)


def _chosen_machine(task, solver) -> object | None:
    if not task['choices']:
        return None
    for lit, equipment_id in task['choices']:
        if solver.Value(lit) == 1:
            return equipment_id
    return None


# Stop a phase once it has had a plan and found nothing better for this long. A re-solve
# with held work can rarely PROVE its plan best, so it ran the whole time budget (~180 s
# against ~30 s cold) while its plan barely moved — the time went to proof, not to
# planning (walk 2026-10-22). Interim fix; why the bound stays loose under holds is
# still to be investigated.
STALL_SECONDS = 15.0


def _solve_until_stalled(solver, model, stall_seconds: float = STALL_SECONDS):
    """`solver.Solve(model)`, stopped early once the incumbent hasn't improved for
    `stall_seconds`. A watchdog thread calls StopSearch (thread-safe); the result is
    then FEASIBLE with the best plan found, exactly as at the time limit."""
    import threading
    import time
    from ortools.sat.python import cp_model

    class _Tracker(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__()
            self.last_improved = None
            self.best = None

        def on_solution_callback(self):
            obj = self.objective_value
            if self.best is None or obj < self.best - 1e-9:
                self.best = obj
                self.last_improved = time.monotonic()

    tracker = _Tracker()
    done = threading.Event()

    def watchdog():
        while not done.wait(1.0):
            if (tracker.last_improved is not None
                    and time.monotonic() - tracker.last_improved > stall_seconds):
                solver.stop_search()
                return

    thread = threading.Thread(target=watchdog, daemon=True)
    thread.start()
    try:
        return solver.solve(model, tracker)
    finally:
        done.set()
        thread.join(timeout=2.0)


def _freed_report(freed: list) -> list[dict]:
    """Freed fence operations named for the planner: part serial(s), step, and why."""
    if not freed:
        return []
    from Tracker.models import Parts, Steps
    part_ids = {pid for f in freed for pid in f['part_ids']}
    erp = dict(Parts.objects.filter(id__in=part_ids).values_list('id', 'ERP_id'))  # tenant-safe: ids from this tenant's solve
    steps = dict(Steps.objects.filter(id__in={f['step_id'] for f in freed})  # tenant-safe: ids from this tenant's solve
                 .values_list('id', 'name'))
    out = []
    for f in freed:
        names = sorted(erp.get(pid, str(pid)) for pid in f['part_ids'])
        part = names[0] + (f" (+{len(names) - 1})" if len(names) > 1 else "")
        out.append({'part': part, 'step': steps.get(f['step_id'], ''),
                    'reason_code': f['reason_code'], 'reason': f['reason'],
                    'was_pinned': f['was_pinned']})
    return out


def solve_schedule(tenant, time_limit_seconds: int = 300, draft: bool = False):
    """Solve the Layer-1 machine schedule for a tenant and persist it as the new
    active `ScheduleResult`. Returns the ScheduleResult (empty + OPTIMAL when there
    is no work)."""
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import (
        OptimizationConfig, ScheduledTask, ScheduleResult,
    )

    with tenant_context(str(tenant.id)):
        # A step in the active work that needs a certification no rostered operator
        # holds can't be executed, so nothing is planned from it onward — but the rest
        # of the shop still gets a plan (user decision 2026-10-22: one leaver or one
        # lapsed cert used to refuse every solve). Not scheduled reports the cut work
        # with who holds the cert and why they don't count. (Scarce-but-present skills
        # are handled by the labor capacity below: they serialize and push work late.)
        from Tracker.services.scheduling.preflight import find_unstaffable_steps
        unstaffable = {(UUID(g['step_id']), g['process_id'])
                       for g in find_unstaffable_steps(tenant)}

        horizon = data.get_schedule_horizon(tenant)
        unrunnable = data.get_unrunnable_steps(tenant, horizon)  # every machine down
        H = max(1, int((horizon.end - horizon.start).total_seconds() // 60))
        wos = data.get_active_workorders(tenant)
        timings = data.get_step_timings(tenant)
        affinities = data.get_step_equipment_affinities(tenant)
        availability = data.get_machine_availability(tenant, horizon)
        attended_only = data.get_attended_only_machines(tenant)  # shift-confined machines
        overtime_windows = data.get_overtime_machine_windows(tenant, horizon)  # extra/weekend shifts (union)
        machine_downtime = data.get_machine_downtime(tenant, horizon)  # eq -> [(s,e)]
        closures = data.get_calendar_closures(tenant, horizon)  # plant holidays/shutdowns
        material_release, material_short, material_detail = data.get_material_gates(tenant, horizon)  # buy-side
        op_windows = data.get_operator_shift_windows(tenant, horizon)  # rostered crew
        skill_pools = data.get_step_operator_pools(tenant)  # gated step -> qualified crew
        # step -> {op: minute their cert for it lapses}, for lapses inside the horizon.
        qual_lapse = {
            sid: {uid: max(0, int((lapse - horizon.start).total_seconds() // 60))
                  for uid, (lapse, _name) in by_op.items()}
            for sid, by_op in data.get_operator_qualification_lapses(tenant, horizon).items()}
        labor_models = data.get_step_labor_models(tenant)  # step -> off|pool|named
        all_op_ids = frozenset(o.user_id for o in data.get_dispatchable_operators(tenant))
        secondary = data.get_step_secondary_resources(tenant)   # step_id -> {gauge_id}
        fixtures = data.get_fixture_availability(tenant)         # fixture_id -> FixtureData
        changeover = data.get_changeover_matrix(tenant)         # (equip, from, to) -> minutes
        continuous = {cm.equipment_id: cm for cm in data.get_continuous_machines(tenant)}
        prev = data.get_previous_schedule(tenant)               # for pins + warm-start
        config = OptimizationConfig.objects.filter(tenant=tenant).first()
        # Outside processing: subcontract steps schedule as elapsed calendar time (no machine/
        # crew); parts already at the vendor pin to their expected return. {step_id: minutes},
        # {part_id: return-minute}.
        osp = data.get_outside_process_data(tenant, config, horizon)
        osp_minutes = osp['step_minutes']
        osp_return = osp['return_min']
        # Batch/process resources. concurrent_cap → up to N jobs at once (cumulative);
        # cycle_cap → furnace: one load at a time, ceil(count/cap) loads at a fixed cycle time.
        _bc = data.get_machine_batch_capacities(tenant)
        concurrent_cap = _bc['concurrent']
        cycle_cap = _bc['cycle']

        prev_map = {}
        if prev is not None:
            prev_map = {(t.part_id, t.step_id): t for t in prev.tasks}
        frozen_min = int((horizon.frozen_end - horizon.start).total_seconds() // 60)
        slushy_min = int((horizon.slushy_end - horizon.start).total_seconds() // 60)
        staging_buffer = config.staging_buffer_minutes if config else 0
        move_min = config.default_move_minutes if config else 0  # inter-op transfer/queue gap
        # Plant closures (holidays/shutdowns) block EVERY machine, in minute space.
        # Convert conservatively — floor the start, CEIL the end — so a closure is always
        # covered in full (flooring the end would leave its final sub-minute schedulable).
        closure_gaps = []
        for _cs, _ce in closures:
            ms = max(0, int((_cs - horizon.start).total_seconds() // 60))
            me = min(H, -(-int((_ce - horizon.start).total_seconds()) // 60))  # ceil to minute
            if ms < me:
                closure_gaps.append((ms, me))
        job_change_min = _job_change_minutes(config)   # WO-change setup on the same op
        pfd_factor = _pfd_factor(config)               # attended-time allowance multiplier

        def _machine_gaps(equipment_id) -> list[tuple]:
            """Minutes a machine can't run: downtime (lights-out machines) or outside the
            shift calendar plus overtime (attended-only ones), and plant closures for
            every machine. Merged, so a NoOverlap over them is well-formed."""
            if equipment_id in attended_only:
                avail = list(availability.get(equipment_id, []))
                avail += [_OTWindow(s, e) for (s, e) in overtime_windows]
                gaps = _window_gaps(avail, horizon.start, H)
            else:
                gaps = []
            # Downtime blocks every machine. For an attended one it is also netted out of
            # its shift windows — but with no shift calendar those windows are empty,
            # read as "always available", and a machine down for days stayed bookable.
            gaps += _to_minutes(machine_downtime.get(equipment_id, []), horizon.start, H)
            return _merge_minute_gaps(gaps + closure_gaps)

        op_minutes = {u: _to_minutes(w, horizon.start, H) for u, w in op_windows.items()}
        _crew_cap, crew_segs = _staffing_segments(op_windows, horizon.start, H)

        def _crew_on_shift(a, b) -> int:
            """The fewest operators on shift at any point in [a, b)."""
            counts = [c for sa, sb, c in crew_segs if sa < b and a < sb]
            return min(counts) if counts else 0

        def _peak_with(a, b, held) -> int:
            """Most held attended operations running at once in [a, b), counting one more
            over the whole span."""
            points = [a] + [x for x, _y in held if a <= x < b]
            return 1 + max((sum(1 for x, y in held if x <= p < y) for p in points), default=0)
        normal_per_min = max(1, _penalty_cents_per_min(config, 3))
        slushy_per_min = max(1, round(normal_per_min * SLUSHY_STICKINESS))
        slushy_machine_cost = normal_per_min * _SLUSHY_MACHINE_MINUTES

        # Which steps need an unconditional occupancy interval (gauge and/or fixture).
        fixture_by_step: dict = defaultdict(list)
        for fx in fixtures.values():
            for step_id in fx.step_ids:
                fixture_by_step[step_id].append(fx.fixture_id)
        occupancy_steps = set(secondary) | set(fixture_by_step)

        # One solve phase. `labor_override`: None keeps each step's own labor_model;
        # 'pool' forces non-off steps to the cheap cumulative (the fast MACHINE phase);
        # 'named' forces exact per-operator assignment (the OPERATOR phase).
        # `machine_hints` {task_index: (start_min, machine_id)} warm-starts the operator
        # phase from the machine phase — CP-SAT refines a good layout, not a cold search.
        def _overlaps(a, b, gaps) -> bool:
            return any(gs < b and a < ge for gs, ge in gaps)

        def _covered(a, b, windows) -> bool:
            """[a, b) lies inside one of `windows` (merged minute intervals)."""
            return any(ws <= a and b <= we for ws, we in windows)

        def _frozen_refusal(*, prev_raw, rep, release_min, mat_lb, choices, durs, dur_free,
                            prec, step_id, fixed_end, lm, front_len, fixed_by_machine,
                            fixed_attended=()):
            """Why a frozen or planner-pinned operation can't be held where the live plan
            put it, as `(code, text)` — or None, when it is held exactly.

            Only reasons it CAN'T happen there: its slot has passed unstarted; its order
            may not start yet or its material isn't in; its machine is out of service,
            no longer eligible or blocked (downtime, closure, off-shift); the crew on shift
            is already taken; or its operator is off the crew, no longer qualified or not on
            shift then. A slot that has passed, or a predecessor running late, is not a
            reason: held work slides later in its order. A part that moved on,
            was scrapped or shipped, or whose order is held or cancelled, simply isn't
            in this solve, so its old slot isn't consulted at all."""
            ps = max(0, prev_raw)   # a slot already passed slides to now
            if release_min and ps < release_min:
                return ('not_released', "its order can't start that early")
            if mat_lb and ps < mat_lb:
                return ('material', "its material doesn't arrive in time for that slot")
            eq = rep.machine_id
            if choices:
                if eq is None or eq not in durs:
                    return ('machine_unavailable',
                            "its machine is out of service or no longer eligible for the step")
                op_dur = durs[eq]
                if _overlaps(ps, ps + op_dur, _machine_gaps(eq)):
                    return ('machine_blocked',
                            "its machine is down, closed or off-shift in that slot")
            else:
                op_dur = dur_free or 1
                if _overlaps(ps, ps + op_dur, closure_gaps):
                    return ('closure', "the plant is closed in that slot")
            att_len = front_len if front_len is not None else op_dur
            if lm != 'off' and att_len and crew_segs:
                # The crew on shift is a hard cap on attended work at once. Held work
                # that would exceed it (another plan's double-booking, the crew shrinking
                # under it) can't all hold; this one goes back to planning.
                if _peak_with(ps, ps + att_len, fixed_attended) > _crew_on_shift(ps, ps + att_len):
                    return ('crew_full', "the crew on shift then is already taken by other "
                            "fixed work")
            op = getattr(rep, 'assigned_operator_id', None)
            if op is not None and lm != 'off':
                if op not in all_op_ids:
                    return ('operator_off_crew', "its operator is no longer on the crew")
                pool = skill_pools.get(step_id)
                if pool is not None and op not in pool:
                    return ('operator_unqualified', "its operator is no longer qualified for it")
                att = front_len if front_len is not None else op_dur
                if att and not _covered(ps, ps + att, op_minutes.get(op, ())):
                    return ('operator_unavailable',
                            "its operator isn't on shift then (rota, leave or training)")
            return None

        def _earliest_slot(est, d, blocked) -> int:
            """First start >= est with [start, start+d) clear of every blocked interval."""
            t = est
            for bs, be in sorted(blocked):
                if be <= t:
                    continue
                if bs >= t + d:
                    break
                t = be
            return t

        _gap_cache: dict = {}

        def _greedy_plan(tasks) -> list:
            """A quick dispatch-rule plan: `[(task, (start, end, machine))]`.

            Operations are placed once their predecessors are, earliest due date first
            (higher late penalty breaking ties), each on the eligible machine where it
            finishes soonest — clear of that machine's downtime, closures and off-shift
            time and of whatever is already on it. Held, running and at-vendor work
            stays where it is. Crew limits, changeovers, gauges and fixtures are left to
            CP-SAT, which repairs the hint where it doesn't fit; the point is a good
            first plan in milliseconds, not a feasible one."""
            plan: dict = {}
            busy: dict = defaultdict(list)
            by_id = {id(t): t for t in tasks}
            for t in tasks:
                if t.get('fixed_pos') is not None:
                    plan[id(t)] = t['fixed_pos']
                    if t['fixed_pos'][2] is not None:
                        busy[t['fixed_pos'][2]].append(t['fixed_pos'][:2])
            pending = [t for t in tasks if id(t) not in plan]
            while pending:
                ready = [t for t in pending if all(id(p) in plan for p in t['preds'])]
                if not ready:          # a cycle can't happen on a resolved route; be safe
                    ready = pending
                t = min(ready, key=lambda x: (x['due'] if x['due'] is not None else 10 * H,
                                              -(x['prio'] or 0)))
                pending.remove(t)
                est = max([t['est'] or 0] + [plan[id(p)][1] + move_min for p in t['preds']])
                if t['durs']:
                    best = None
                    for eq, d in t['durs'].items():
                        if eq not in _gap_cache:
                            _gap_cache[eq] = _machine_gaps(eq)
                        st = _earliest_slot(est, d, _gap_cache[eq] + busy[eq])
                        if best is None or st + d < best[1]:
                            best = (st, st + d, eq)
                    plan[id(t)] = best
                    busy[best[2]].append(best[:2])
                else:
                    d = t['dur_free'] or 1
                    plan[id(t)] = (est, est + d, None)
            return [(by_id[k], v) for k, v in plan.items()]

        def _build_and_solve(labor_override, machine_hints, tlimit, hard_fence=True,
                             release=frozenset(), find_core=False):
            """`hard_fence=False` is the fallback when fixing every valid frozen/pinned
            operation made the model infeasible (fixed blocks that the changed world can
            no longer fit together): they are then held only by slushy stickiness and all
            reported as freed with reason `conflict`.

            `release`: held operations ((part_ids, step_id)) a previous attempt found in
            an infeasible core — re-planned this time and reported as `conflict`. Each
            hold is enforced through an assumption literal, so when the fixed set can't
            fit together CP-SAT names the operations that conflict instead of the whole
            fence being dropped."""
            def _eff(step_id):
                base = labor_models.get(step_id, 'pool')
                return 'off' if base == 'off' else (labor_override or base)

            model = cp_model.CpModel()

            # NB: scheduled breaks/lunch are NOT enforced here. In the lights-out model a
            # machine keeps running through a break; operator presence for the attended
            # portions is a Layer-2 concern, and dispatch already honors break TimeEntries.

            tasks: list[dict] = []
            machine_intervals: dict = defaultdict(list)
            machine_tasks: dict = defaultdict(list)   # equip_id -> [(present, start, end, step_id, setup, wo_id)]
            gauge_intervals: dict = defaultdict(list)
            fixture_intervals: dict = defaultdict(list)
            lateness_cost = []
            lateness_terms = []   # (lateness_var, penalty) — for the isolated lateness total
            affinity_cost = []    # small penalties nudging toward preferred/dialed-in machines
            labor_intervals = []  # (attended_interval, step_id, model) per attended lot-op
            named_op_intervals: dict = defaultdict(list)  # user_id -> [optional intervals]
            named_uncovered = []  # soft penalty terms for unassignable NAMED lots
            warm_hints = []   # (start_var, minute) warm-start warm_hints from the previous schedule
            max_time_penalty = []  # soft penalty terms for blown max-time-between-ops windows
            max_time_viols = []    # (viol_bool, task_dict) — flag the op post-solve if relaxed
            pins = []          # (start_var, prev_start, prev_machine_id, choices) — fixed operations
            stick_terms = []   # ('dev', var, weight) | ('mach', lit, weight) — the slushy term
            freed = []         # frozen/pinned operations sent back to planning, with why
            kept = 0           # frozen/pinned operations held exactly
            fixed_by_machine: dict = defaultdict(list)   # equip_id -> [(s, e)] fixed so far
            fixed_by_operator: dict = defaultdict(list)  # user_id -> [(s, e)] attended, fixed
            fixed_attended: list = []   # [(s, e)] attended spans of held work (crew cap)
            holds: list = []   # (assumption_lit, (part_ids, step_id)) per held operation
            slide_terms: list = []   # minutes each held operation slid past its planned start
            held_on_machine: dict = defaultdict(list)  # equip -> [(planned, start, end, step, setup, wo, hold)]
            wo_starts: dict = defaultdict(list)   # wo_id -> [start vars] (for peg gating)
            wo_ends: dict = defaultdict(list)     # wo_id -> [end vars]   (for peg completion)
            wo_step_starts: dict = defaultdict(list)  # (wo_id, step_id) -> [start vars]

            for wo in wos:
                due_minutes = _due_minutes(wo.expected_completion, horizon.start, H)
                release_min = _release_minutes(wo.expected_start, horizon.start, H)
                penalty = _penalty_cents_per_min(config, wo.priority)
                # Lot-based scheduling: a WO's parts sitting at the SAME current step form
                # one cohesive lot that moves the remaining route together — one machine
                # occupancy per operation, sized by the lot's piece count (cycle × count;
                # setup is the changeover gap). Lock-step lives HERE: co-located cohort
                # parts schedule as one lot with a single start.
                # Carve-out: a part split off to rework (`split_from_lot`) is grouped into
                # its OWN lot (keyed by split-state) so it never drags the cohort — the
                # cohort keeps progressing, and the split part schedules its own rework path
                # and re-converges later via rejoin_part_to_lot. Cores schedule individually.
                # Group key per part. The solver only ever *batches* — it groups the
                # UNPINNED cohort into one lot (lock-step, within this WO) and never
                # breaks a lot on its own. A planner PIN is what fixes a part in place, so
                # each distinct pinned (start, machine) becomes its own fixed lot — that's
                # how a manual "break apart" (pin the parts to separate slots) holds, and
                # how a manual "merge" (pin them onto one slot) locks a batch. Quality
                # stragglers (`split_from_lot`) keep their own lot as before. Unpinned →
                # the cohort lot the solver places freely and batches.
                def _group_key(p):
                    if p.individual:
                        # A core under rebuild: its scope is its own, so it never moves in
                        # lock-step with another unit. (Teardown cores batch like parts.)
                        return ('u', p.part_id)
                    if p.split_from_lot:
                        return ('q',)  # quality carve-out → its own lot
                    prev = prev_map.get((p.part_id, p.current_step_id))
                    if prev is not None and prev.is_pinned:
                        return ('p', prev.start_time, prev.machine_id)  # planner-fixed slot
                    return ('c',)  # unpinned cohort → one solver-batched lot
                pdata = {p.part_id: p for p in wo.parts}
                part_batches: dict = defaultdict(list)
                for p in wo.parts:
                    part_batches[(p.current_step_id, _group_key(p))].append(p.part_id)
                lots = []
                for (step, gk), pids in part_batches.items():
                    # A lot is in-progress if any of its parts has already started this step;
                    # elapsed = the longest-running part (earliest start → most elapsed), so
                    # the solver schedules only the remaining duration of the running lot.
                    ip_parts = [pdata[pid] for pid in pids if pdata[pid].in_progress]
                    lots.append({'label': f"b{wo.wo_id}:{step}:{gk[0]}", 'step': step,
                                 'part_ids': tuple(pids), 'count': len(pids),
                                 'in_progress': bool(ip_parts),
                                 'elapsed': max((p.elapsed_minutes for p in ip_parts), default=0.0)})
                for lot in lots:
                    count = lot['count']
                    # The lot's remaining NOMINAL route from its current step (DEFAULT
                    # edges; rework/scrap branches excluded), with merge-capable DAG
                    # precedence so convergence/divergence nodes schedule correctly.
                    # A core under rebuild books the main line like any part: nothing on
                    # it is skipped (services/reman/repair_routing).
                    route_ids, prec = resolve_route(lot['step'], wo.steps, wo.edges)
                    # Plan up to a step nobody rostered can run, not past it: that step
                    # and everything after it on this lot wait, and Not scheduled says why
                    # (diagnostics). A running op is already staffed, so it stays.
                    # Same for a step whose every machine is down for the whole horizon.
                    cut = {sid for sid in route_ids
                           if ((sid, wo.process_id) in unstaffable or sid in unrunnable)
                           and not (lot.get('in_progress') and sid == lot['step'])}
                    if cut:
                        frontier = list(cut)
                        while frontier:
                            here = frontier.pop()
                            for a, b in prec:
                                if a == here and b not in cut:
                                    cut.add(b)
                                    frontier.append(b)
                        route_ids = [sid for sid in route_ids if sid not in cut]
                        prec = [(a, b) for a, b in prec if a not in cut and b not in cut]
                    node_start: dict = {}
                    node_end: dict = {}
                    node_task: dict = {}   # step_id -> task dict (to flag cure-window violations)
                    fixed_end: dict = {}   # step_id -> end minute, for operations held fixed
                    lot_ends = []
                    for step_id in route_ids:
                        timing = timings.get(step_id)
                        eligible = [a for a in affinities.get(step_id, []) if a.is_schedulable]
                        key = f"{lot['label']}_{step_id}"
                        start = model.NewIntVar(0, H, f"s_{key}")
                        end = model.NewIntVar(0, H, f"e_{key}")

                        # Outside processing: a subcontract op runs OFF-SITE — no machine, no
                        # crew, on calendar (24/7) time, for the vendor turnaround. Precedence
                        # alone gates downstream on its return. Parts already at the vendor pin
                        # to their expected return (shipped_at + turnaround). Checked before the
                        # in-progress branch so a sent-out part isn't treated as a machine op.
                        if step_id in osp_minutes:
                            dur = osp_minutes[step_id]
                            if release_min:
                                model.Add(start >= release_min)
                            ret = min((osp_return[pid] for pid in lot['part_ids']
                                       if pid in osp_return), default=None)
                            if ret is not None:
                                ret = max(1, min(H, ret))
                                model.Add(end == ret)
                                model.Add(start == max(0, ret - dur))
                                fixed_end[step_id] = ret
                            else:
                                model.Add(end == start + dur)
                                # Frozen and not yet sent: like any held op it may slide
                                # later but never earlier — shipping out sooner is a shop
                                # act (packing, a truck) the fence promised not to move.
                                osp_prev = [prev_map[(pid, step_id)] for pid in lot['part_ids']
                                            if (pid, step_id) in prev_map]
                                if osp_prev:
                                    first = min(pt.start_time for pt in osp_prev)
                                    raw = -int(-(first - horizon.start).total_seconds() // 60)
                                    if 0 <= raw < frozen_min:
                                        model.Add(start >= min(raw, max(0, H - dur)))
                            tasks.append({'part_ids': lot['part_ids'],
                                          'step_id': step_id, 'start': start, 'end': end,
                                          'choices': [], 'pinned': ret is not None,
                                          'planner_pinned': False, 'named_assign': [],
                                          'requires_operator': False, 'in_progress': False,
                                          'durs': {}, 'dur_free': dur, 'est': release_min,
                                          'due': due_minutes, 'prio': penalty, 'preds': [],
                                          'fixed_pos': ((max(0, ret - dur), ret, None)
                                                        if ret is not None else None)})
                            node_start[step_id] = start
                            node_end[step_id] = end
                            node_task[step_id] = tasks[-1]
                            lot_ends.append(end)
                            continue

                        # In-progress: the lot's CURRENT step is physically running. Pin it to
                        # start "now" (0) with only its REMAINING duration, on the machine it's
                        # on, so a re-solve can't shove a running op later or re-charge time
                        # already spent. Setup is done (charge none); no soft pin needed (it's
                        # hard-fixed); labor for the remainder isn't re-demanded. Only the first
                        # route step (== lot['step']) can be in progress.
                        if lot.get('in_progress') and step_id == lot['step']:
                            full_dur = _dur(timing, None, pfd_factor, count)
                            remaining = max(1, min(H, full_dur - int(round(lot['elapsed']))))
                            model.Add(start == 0)
                            model.Add(end == remaining)
                            fixed_end[step_id] = remaining
                            prev_here = [prev_map[(pid, step_id)] for pid in lot['part_ids']
                                         if (pid, step_id) in prev_map]
                            fixed_m = None
                            if prev_here:
                                repm = min(prev_here, key=lambda pt: pt.start_time).machine_id
                                if repm and any(a.equipment_id == repm for a in eligible):
                                    fixed_m = repm
                            # The machine it's running on went down: it isn't running
                            # there any more, so don't hold the remainder on it (that
                            # made the whole model infeasible — walk 2026-10-22).
                            if fixed_m is not None:
                                run_end = horizon.start + timedelta(minutes=remaining)
                                if any(s < run_end and e > horizon.start
                                       for s, e in machine_downtime.get(fixed_m, ())):
                                    fixed_m = None
                            choices = []
                            if fixed_m is not None:
                                lit = model.NewBoolVar(f"ip_{key}_{fixed_m}")
                                model.Add(lit == 1)
                                iv = model.NewOptionalFixedSizeIntervalVar(
                                    start, remaining, lit, f"ipi_{key}")
                                machine_intervals[fixed_m].append(iv)
                                machine_tasks[fixed_m].append(
                                    (lit, start, end, step_id, 0, wo.wo_id))
                                choices.append((lit, fixed_m))
                            else:
                                model.NewIntervalVar(start, remaining, end, f"ipi_{key}")
                            tasks.append({'part_ids': lot['part_ids'],
                                          'step_id': step_id, 'start': start, 'end': end,
                                          'choices': choices, 'pinned': True,
                                          'planner_pinned': False, 'named_assign': [],
                                          'requires_operator': False, 'in_progress': True,
                                          'durs': {}, 'dur_free': remaining, 'est': 0,
                                          'due': due_minutes, 'prio': penalty, 'preds': [],
                                          'fixed_pos': (0, remaining, fixed_m)})
                            node_start[step_id] = start
                            node_end[step_id] = end
                            node_task[step_id] = tasks[-1]
                            lot_ends.append(end)
                            continue

                        if release_min:
                            model.Add(start >= release_min)   # earliest-release gate
                        # Buy-side material availability: gate the consuming op on the
                        # earliest incoming receipt when purchased material is short; flag
                        # the op when it's short with no known receipt date.
                        mat_lb = max(material_release.get((wo.wo_id, step_id), 0),
                                     material_release.get((wo.wo_id, None), 0))
                        if mat_lb:
                            model.Add(start >= mat_lb)
                        mat_short = ((wo.wo_id, step_id) in material_short
                                     or (wo.wo_id, None) in material_short)
                        mat_detail = (material_detail.get((wo.wo_id, step_id))
                                      or material_detail.get((wo.wo_id, None)) or "")

                        setup_int = int(round(timing.setup_minutes)) if timing else 0
                        choices = []
                        durs: dict = {}     # equip_id -> lot minutes on that machine
                        dur_free = None     # lot minutes when the step uses no machine
                        if eligible:
                            for a in eligible:
                                if a.equipment_id in cycle_cap:
                                    # Furnace/oven: fixed cycle time per load, ceil(count/cap)
                                    # loads back-to-back (not per-part time).
                                    dur = _batch_cycle_dur(timing, cycle_cap[a.equipment_id], count)
                                else:
                                    dur = _dur_on_machine(timing, a, continuous, pfd_factor, count)
                                durs[a.equipment_id] = dur
                                lit = model.NewBoolVar(f"m_{key}_{a.equipment_id}")
                                opt = model.NewOptionalFixedSizeIntervalVar(start, dur, lit, f"i_{key}_{a.equipment_id}")
                                machine_intervals[a.equipment_id].append(opt)
                                machine_tasks[a.equipment_id].append(
                                    (lit, start, end, step_id, setup_int, wo.wo_id))
                                model.Add(end == start + dur).OnlyEnforceIf(lit)
                                choices.append((lit, a.equipment_id))
                                penalty_lvl = _affinity_penalty(a.affinity)
                                if penalty_lvl:
                                    affinity_cost.append(lit * penalty_lvl)  # pay iff this machine is chosen
                            model.AddExactlyOne([lit for lit, _ in choices])
                        else:
                            dur = _dur(timing, None, pfd_factor, count)
                            dur_free = dur
                            model.NewIntervalVar(start, dur, end, f"i_{key}")

                        # Occupancy interval for the finite secondary resources the lot ties
                        # up while it runs — measurement gauges and shared fixtures.
                        if step_id in occupancy_steps:
                            size = model.NewIntVar(1, H, f"sz_{key}")
                            occ = model.NewIntervalVar(start, size, end, f"occ_{key}")
                            for gauge_id in secondary.get(step_id, ()):
                                gauge_intervals[gauge_id].append(occ)
                            for fixture_id in fixture_by_step.get(step_id, ()):
                                fixture_intervals[fixture_id].append(occ)

                        # Labor demand: ONE operator tends the lot at this operation (not one
                        # per piece). Full-attention → tied to the whole run; load/unload →
                        # only the front touch (setup + a load/unload per piece), the machine
                        # then running unattended. Feeds the crew-capacity cumulative below.
                        lm = _eff(step_id)
                        named_assign: list = []  # (op_id, assign_lit) chosen in the NAMED phase
                        front_len = None         # attended minutes for a load/unload step
                        if lm != 'off':
                            full = timing is None or timing.attention_type == 'full'
                            if full:
                                asz = model.NewIntVar(0, H, f"asz_{key}")
                                att_iv = model.NewIntervalVar(start, asz, end, f"att_{key}")
                            else:
                                front = int(round(timing.setup_minutes + timing.load_unload_per_piece * count))
                                front_len = front
                                att_iv = (model.NewFixedSizeIntervalVar(start, front, f"att_{key}")
                                          if front > 0 else None)
                            if att_iv is not None:
                                labor_intervals.append((att_iv, step_id, lm))
                                if lm == 'named':
                                    # Assign a SPECIFIC qualified operator to this lot (exact
                                    # dual-resource): optional per-operator intervals a
                                    # per-operator NoOverlap serialises, so a scarce specialist
                                    # pushes the work late rather than leaving it uncovered. A
                                    # soft `uncov` fallback keeps the model feasible.
                                    pool = skill_pools.get(step_id)
                                    qualified = (pool if pool is not None else all_op_ids) & all_op_ids
                                    assign_lits = []
                                    lapses = qual_lapse.get(step_id, {})
                                    for op in qualified:
                                        lit = model.NewBoolVar(f"na_{key}_{op}")
                                        if op in lapses:
                                            # Their cert runs out mid-horizon: only work
                                            # finished by then is theirs to take.
                                            model.Add(end <= lapses[op]).OnlyEnforceIf(lit)
                                        if full:
                                            oiv = model.NewOptionalIntervalVar(start, asz, end, lit, f"noi_{key}_{op}")
                                        else:
                                            oiv = model.NewOptionalFixedSizeIntervalVar(start, front, lit, f"noi_{key}_{op}")
                                        named_op_intervals[op].append(oiv)
                                        assign_lits.append(lit)
                                        named_assign.append((op, lit))
                                    if assign_lits:
                                        uncov = model.NewBoolVar(f"nunc_{key}")
                                        model.Add(sum(assign_lits) + uncov == 1)
                                        named_uncovered.append(uncov)   # weighted coverage-first below

                        # Time fence from the live plan. A lot inherits the state of its
                        # parts: planner-pinned if ANY part was, else frozen if its earliest
                        # part started inside the frozen zone. Frozen/pinned -> held EXACTLY
                        # (start, machine, operator) unless it can't happen there any more;
                        # slushy -> a stickiness cost on the lateness scale; liquid -> only a
                        # warm-start hint.
                        pinned = False          # held fixed this solve
                        planner_pinned = False  # the DB is_pinned flag — planner lock ONLY
                        fixed_start_dt = None   # the live plan's exact start, for write-back
                        held_pos = None         # (start, end, machine) when held, for the greedy hint
                        op_unfixed = None       # held op whose operator couldn't be kept
                        warm_start = None       # the live plan's start when only hinted
                        prevts = [prev_map[(pid, step_id)] for pid in lot['part_ids']
                                  if (pid, step_id) in prev_map]
                        if prevts:
                            rep = min(prevts, key=lambda pt: pt.start_time)
                            any_pinned = any(pt.is_pinned for pt in prevts)
                            # Ceiling, not floor: the horizon starts at "now", so an
                            # operation the last plan put at "now" is a few seconds in the
                            # past on the next solve. Flooring read that as minute -1 — a
                            # passed slot — and freed it and everything after it.
                            prev_raw = -int(-(rep.start_time - horizon.start).total_seconds() // 60)
                            prev_start = max(0, min(H, prev_raw))
                            fence_held = any_pinned or prev_raw < frozen_min
                            why = None
                            hold_key = (lot['part_ids'], step_id)
                            if fence_held and hold_key in release:
                                why = ('conflict', "it couldn't be held together with other "
                                       "fixed work as the shop now stands")
                            elif fence_held and hard_fence:
                                why = _frozen_refusal(
                                    prev_raw=prev_raw, rep=rep, release_min=release_min,
                                    mat_lb=mat_lb, choices=choices, durs=durs,
                                    dur_free=dur_free, prec=prec, step_id=step_id,
                                    fixed_end=fixed_end, lm=lm, front_len=front_len,
                                    fixed_by_machine=fixed_by_machine,
                                    fixed_attended=fixed_attended)
                            elif fence_held:
                                why = ('conflict', "it couldn't be held together with the other "
                                       "fixed work as the shop now stands")
                            if fence_held and why is None:
                                fixed_m = rep.machine_id if choices else None
                                op_dur = durs.get(fixed_m) if fixed_m else dur_free
                                hold = model.NewBoolVar(f"hold_{key}")
                                holds.append((hold, hold_key))
                                model.Add(start >= prev_start).OnlyEnforceIf(hold)
                                slide = model.NewIntVar(0, H, f"slide_{key}")
                                model.Add(slide >= start - prev_start)
                                slide_terms.append(slide)
                                if fixed_m is not None:
                                    held_on_machine[fixed_m].append(
                                        (prev_start, start, end, step_id,
                                         int(round(timing.setup_minutes)) if timing else 0,
                                         wo.wo_id, hold))
                                for lit, eqid in choices:
                                    model.Add(lit == (1 if eqid == fixed_m else 0)).OnlyEnforceIf(hold)
                                # Keep its operator too — unless that person is already held
                                # on other fixed work then. Operators on the live plan may
                                # come from Dispatch, which models attention differently
                                # from this solve; fixing every one exactly double-booked
                                # people and made the whole fixed set infeasible (walk
                                # 2026-10-21). Time and machine still hold; the solve
                                # picks the operator.
                                op_id = rep.assigned_operator_id
                                if op_id is not None and named_assign:
                                    att = front_len if front_len is not None else op_dur
                                    span = (prev_start, prev_start + (att or 0))
                                    if att and not _overlaps(span[0], span[1],
                                                             fixed_by_operator.get(op_id, ())):
                                        for op, lit in named_assign:
                                            model.Add(lit == (1 if op == op_id else 0)).OnlyEnforceIf(hold)
                                        fixed_by_operator[op_id].append(span)
                                    else:
                                        # Reported if the plan does give it to someone else.
                                        op_unfixed = op_id
                                held_att = front_len if front_len is not None else op_dur
                                if lm != 'off' and held_att:
                                    fixed_attended.append((prev_start, prev_start + held_att))
                                if op_dur is not None:
                                    fixed_end[step_id] = prev_start + op_dur
                                    if fixed_m is not None:
                                        fixed_by_machine[fixed_m].append(
                                            (prev_start, prev_start + op_dur))
                                pins.append((start, prev_start, rep.machine_id, choices))
                                if op_dur is not None:
                                    held_pos = (prev_start, prev_start + op_dur, fixed_m)
                                pinned = True
                                planner_pinned = any_pinned
                                fixed_start_dt = rep.start_time
                                kept += 1
                            else:
                                if fence_held:
                                    freed.append({'part_ids': lot['part_ids'], 'step_id': step_id,
                                                  'reason_code': why[0], 'reason': why[1],
                                                  'was_pinned': any_pinned})
                                if 0 <= prev_raw < slushy_min:
                                    # Slushy (or a freed frozen op): prefer staying put,
                                    # priced against lateness so moving saves real time.
                                    dev = model.NewIntVar(0, H, f"stick_{key}")
                                    model.AddAbsEquality(dev, start - prev_start)
                                    stick_terms.append(('dev', dev, slushy_per_min))
                                    if rep.machine_id:
                                        for lit, eqid in choices:
                                            if eqid == rep.machine_id:
                                                stick_terms.append(('mach', lit, slushy_machine_cost))
                                warm_hints.append((start, prev_start))
                                warm_start = prev_start

                        tasks.append({'part_ids': lot['part_ids'],
                                      'step_id': step_id,
                                      'start': start, 'end': end, 'choices': choices,
                                      'pinned': pinned, 'planner_pinned': planner_pinned,
                                      'fixed_start_dt': fixed_start_dt,
                                      # Exact write-back only for a slot still ahead: one already
                                      # passed was held at "now", and writing its old time back
                                      # would put the plan in the past.
                                      'held_minute': prev_start if (pinned and prev_raw >= 0) else None,
                                      'op_unfixed': op_unfixed,
                                      'named_assign': named_assign,
                                      'requires_operator': lm != 'off',
                                      'material_short': mat_short,
                                      'material_detail': mat_detail,
                                      'durs': durs, 'dur_free': dur_free,
                                      'est': max(release_min, mat_lb), 'due': due_minutes,
                                      'prio': penalty, 'preds': [], 'fixed_pos': held_pos,
                                      'warm': warm_start})
                        node_start[step_id] = start
                        node_end[step_id] = end
                        node_task[step_id] = tasks[-1]
                        lot_ends.append(end)

                    # Merge-capable precedence: for each DEFAULT edge
                    # start[to] >= end[from] + move_min (inter-op transport/queue gap);
                    # a node with several predecessors waits for the latest (max) of them.
                    # Max-time-between-ops (cure/coat/pot-life): a SOFT upper bound
                    # start[to] <= end[from] + max_minutes — met unless capacity can't, then
                    # the op is flagged (cure_violation) and penalized, never hard-INFEASIBLE.
                    max_by_edge = {(e.from_step_id, e.to_step_id): e.max_minutes
                                   for e in wo.edges if e.max_minutes}
                    for from_id, to_id in prec:
                        if from_id in node_task and to_id in node_task:
                            node_task[to_id]['preds'].append(node_task[from_id])
                        if from_id in node_end and to_id in node_start:
                            model.Add(node_start[to_id] >= node_end[from_id] + move_min)
                            max_m = max_by_edge.get((from_id, to_id))
                            if max_m is not None:
                                viol = model.NewBoolVar(f"cure_{lot['label']}_{from_id}_{to_id}")
                                model.Add(
                                    node_start[to_id] <= node_end[from_id] + max_m
                                ).OnlyEnforceIf(viol.Not())
                                max_time_penalty.append(viol * _CURE_WINDOW_WEIGHT)
                                if to_id in node_task:
                                    max_time_viols.append((viol, node_task[to_id]))

                    wo_starts[wo.wo_id].extend(node_start.values())
                    wo_ends[wo.wo_id].extend(node_end.values())
                    for sid, s in node_start.items():
                        wo_step_starts[(wo.wo_id, sid)].append(s)

                    # Lateness is per-LOT (the lot is late or not) — not per piece, so a big
                    # WO no longer swamps the objective with count-many identical late terms.
                    if due_minutes is not None and penalty > 0 and lot_ends:
                        lot_done = model.NewIntVar(0, H, f"done_{lot['label']}")
                        model.AddMaxEquality(lot_done, lot_ends)   # DAG completion = last sink
                        lateness = model.NewIntVar(0, 2 * H, f"late_{lot['label']}")
                        model.Add(lateness >= lot_done - due_minutes)
                        lateness_cost.append(lateness * penalty)
                        lateness_terms.append((lateness, penalty))  # for the isolated total

            # Cross-WO assembly-convergence pegs (plan #9): a component WO must finish
            # (+ staging buffer) before its parent assembly WO may start. Both WOs are in
            # this solve; multi-level BOMs chain transitively (A waits on B waits on C).
            # When the BOM line names the consuming step, only that assembly step waits —
            # pre-assembly parent work can overlap the component build; otherwise (no
            # consumed_at_step authored) the whole parent waits, conservatively.
            for wo in wos:
                parent_id = wo.pegged_to_wo_id
                if not parent_id or parent_id == wo.wo_id:
                    continue
                child_ends = wo_ends.get(wo.wo_id)
                if not child_ends:
                    continue
                if wo.pegged_consumes_step_id is not None:
                    gated = wo_step_starts.get((parent_id, wo.pegged_consumes_step_id))
                else:
                    gated = wo_starts.get(parent_id)
                if not gated:
                    continue   # parent produced no (matching) tasks — e.g. already past it
                child_done = model.NewIntVar(0, H, f"child_done_{wo.wo_id}")
                model.AddMaxEquality(child_done, child_ends)
                for ps in gated:
                    model.Add(ps >= child_done + staging_buffer)

            # Held work keeps its order on its machine: each held operation starts after
            # the one planned before it (plus the changeover between them), so a slide
            # carries the queue along instead of reshuffling it.
            for equipment_id, held in held_on_machine.items():
                held.sort(key=lambda h: h[0])
                for a, b in zip(held, held[1:]):
                    gap = _transition(changeover, equipment_id, a[3], b[3], b[4],
                                      a[5], b[5], job_change_min)
                    model.Add(b[1] >= a[2] + gap).OnlyEnforceIf([a[6], b[6]])

            # Machine capacity. Lights-out machines (the default) run 24/7 and are blocked
            # only by their downtime — a lot-operation may span nights/weekends. Machines
            # flagged attended-only (`runs_unattended=False`) are instead confined to the
            # shift calendar (operator must be present), so their unavailable gaps are the
            # complement of the shift windows. Continuous-feed machines also periodically
            # stop for a bar change; those are recurring fixed downtime over the horizon.
            for equipment_id, intervals in machine_intervals.items():
                # Attended machines run only while operators are present (shift calendar
                # plus company overtime); lights-out ones are blocked only by downtime.
                # Plant closures block every machine (`_machine_gaps`).
                gaps = _machine_gaps(equipment_id)
                blocked = [model.NewFixedSizeIntervalVar(gs, ge - gs, f"gap_{equipment_id}_{i}")
                           for i, (gs, ge) in enumerate(gaps)]
                cm = continuous.get(equipment_id)
                if cm is not None and cm.bar_change_interval_hours and cm.bar_change_duration_minutes:
                    step = int(cm.bar_change_interval_hours * 60)
                    dur_bc = max(1, int(round(cm.bar_change_duration_minutes)))
                    t = step
                    while t < H:
                        blocked.append(model.NewFixedSizeIntervalVar(
                            t, min(dur_bc, H - t), f"bar_{equipment_id}_{t}"))
                        t += step + dur_bc
                cap = concurrent_cap.get(equipment_id)
                if cap:
                    # CONCURRENT batch resource: up to `cap` jobs run at once. Downtime/closure
                    # gaps demand the full capacity so they still block it entirely. (CYCLE
                    # furnaces stay no-overlap — one load at a time — with a per-load duration.)
                    model.AddCumulative(intervals + blocked,
                                        [1] * len(intervals) + [cap] * len(blocked), cap)
                else:
                    model.AddNoOverlap(intervals + blocked)

            # Sequence-dependent setup / changeover: for each pair of tasks that could
            # share a machine, insert the changeover gap in whichever order they run
            # (gated on both being assigned to that machine). Same-step neighbours cost
            # 0 (piece after piece); different-step neighbours pay the WorkCenterChangeover
            # (or the incoming step's setup as a fallback). NoOverlap already prevents
            # time overlap; this adds the transition gap on top.
            for equipment_id, mtasks in machine_tasks.items():
                # Batch/process resources (either mode) don't do pairwise "consecutive"
                # changeover — concurrent jobs overlap; a furnace cycle bakes setup into its
                # per-load duration.
                if equipment_id in concurrent_cap or equipment_id in cycle_cap:
                    continue
                for i in range(len(mtasks)):
                    pi, si, ei, stepi, setupi, woi = mtasks[i]
                    for j in range(i + 1, len(mtasks)):
                        pj, sj, ej, stepj, setupj, woj = mtasks[j]
                        t_ij = _transition(changeover, equipment_id, stepi, stepj, setupj,
                                           woi, woj, job_change_min)
                        t_ji = _transition(changeover, equipment_id, stepj, stepi, setupi,
                                           woj, woi, job_change_min)
                        if not t_ij and not t_ji:
                            continue
                        i_before_j = model.NewBoolVar(f"seq_{equipment_id}_{i}_{j}")
                        model.Add(sj >= ei + t_ij).OnlyEnforceIf([pi, pj, i_before_j])
                        model.Add(si >= ej + t_ji).OnlyEnforceIf([pi, pj, i_before_j.Not()])

            # Secondary gauges: one task at a time per gauge.
            for intervals in gauge_intervals.values():
                model.AddNoOverlap(intervals)

            # Fixtures: cumulative — at most `quantity` concurrent users.
            for fixture_id, intervals in fixture_intervals.items():
                capacity = fixtures[fixture_id].quantity
                model.AddCumulative(intervals, [1] * len(intervals), capacity)

            # Labor capacity (Layer-1 crew constraint): the attended operations may not
            # demand more operators at once than the crew on shift — a cumulative resource
            # whose capacity varies by shift. Deficit "blocker" intervals consume the gap
            # between each segment's headcount and the peak, so an off-shift stretch (count
            # 0) is fully blocked — attended work is pushed into staffed hours while machines
            # keep running lights-out. Skipped entirely when no crew is rostered (cap 0), so
            # a tenant without shift/roster data schedules unconstrained as before.
            def _add_capacity(intervals, windows, tag):
                """Cumulative capping `intervals` at the headcount on shift in `windows`,
                with deficit blockers so low-staff (and zero-staff) stretches are respected."""
                cap, segs = _staffing_segments(windows, horizon.start, H)
                if not intervals or cap <= 0:
                    return
                ivs = list(intervals)
                dems = [1] * len(intervals)
                for a, b, count in segs:
                    deficit = cap - count
                    if deficit > 0 and b > a:
                        ivs.append(model.NewFixedSizeIntervalVar(a, b - a, f"{tag}_{a}_{b}"))
                        dems.append(deficit)
                model.AddCumulative(ivs, dems, cap)

            # Total crew: no more concurrent attended work than operators on shift (applies
            # to POOL and NAMED lots alike — every attended op needs one of the crew).
            _add_capacity([iv for iv, _, _ in labor_intervals], op_windows, "crew")

            # Per-skill (POOL model only): each training-gated step's attended work is capped
            # at ITS qualified crew on shift, so a scarce skill runs limited-at-a-time and the
            # excess pushes later. NAMED steps are handled exactly below instead.
            pool_intervals: dict = defaultdict(list)
            for iv, sid, m in labor_intervals:
                if m == 'pool':
                    pool = skill_pools.get(sid)
                    if pool:
                        pool_intervals[pool].append(iv)
            for i, (pool, intervals) in enumerate(pool_intervals.items()):
                pool_windows = {u: w for u, w in op_windows.items() if u in pool}
                _add_capacity(intervals, pool_windows, f"skill{i}")

            # NAMED model: a specific operator runs each lot and can't be in two places — a
            # per-operator NoOverlap over their assigned intervals, blocked outside their
            # shift. This is the exact dual-resource assignment for specialist steps.
            for op, intervals in named_op_intervals.items():
                _, off_segs = _staffing_segments({op: op_windows.get(op, [])}, horizon.start, H)
                blockers = [model.NewFixedSizeIntervalVar(a, b - a, f"noff_{op}_{a}")
                            for a, b, c in off_segs if c == 0 and b > a]
                model.AddNoOverlap(intervals + blockers)

            if tasks:
                makespan = model.NewIntVar(0, H, "makespan")
                model.AddMaxEquality(makespan, [t['end'] for t in tasks])
                stickiness = (sum(w * v for kind, v, w in stick_terms if kind == 'dev')
                              + sum(w * (1 - v) for kind, v, w in stick_terms if kind == 'mach'))
                urgent_per_min = max(1, _penalty_cents_per_min(config, 1))
                slide_cost = _SLIDE_WEIGHT_FACTOR * urgent_per_min * sum(slide_terms)
                obj = (sum(lateness_cost) + makespan + stickiness + slide_cost
                       + sum(affinity_cost) + sum(max_time_penalty))
                if named_uncovered:
                    # Coverage-first (lexicographic-by-weight): one uncovered attended op is
                    # priced ABOVE the largest the rest of the objective could ever reach, so
                    # the solver NEVER trades coverage for less lateness/makespan — pushing
                    # work late is always preferred to leaving it unstaffed.
                    max_pen = max((_penalty_cents_per_min(config, w.priority) for w in wos), default=0)
                    stick_max = (sum(w * (H if kind == 'dev' else 1) for kind, _v, w in stick_terms)
                                 + _SLIDE_WEIGHT_FACTOR * max(1, _penalty_cents_per_min(config, 1))
                                 * H * len(slide_terms))
                    w_unc = (len(tasks) * 2 * H * max_pen + H + stick_max
                             + len(affinity_cost) * _AFFINITY_PENALTY_DEFAULT
                             + len(max_time_penalty) * _CURE_WINDOW_WEIGHT + 1)
                    obj = obj + w_unc * sum(named_uncovered)
                model.Minimize(obj)

            for var, minute in warm_hints:            # warm-start from the previous schedule
                model.AddHint(var, minute)

            if machine_hints is None and USE_GREEDY_HINT and tasks:
                # A dispatch-rule starting plan for every operation the live plan doesn't
                # already hint (`_greedy_plan`) — CP-SAT then improves on it rather than
                # searching from nothing, which is where run-to-run swings came from.
                for t, (gs, ge, geq) in _greedy_plan(tasks):
                    if t['fixed_pos'] is not None or t.get('warm') is not None:
                        continue
                    model.AddHint(t['start'], gs)
                    model.AddHint(t['end'], ge)
                    for lit, eqid in t['choices']:
                        model.AddHint(lit, 1 if eqid == geq else 0)

            if machine_hints:
                # Hint the MACHINE choice from the machine phase (that layout is good),
                # but NOT the start time — leaving times free lets the operator phase push
                # attended work out into idle capacity to cover it, instead of clinging to
                # the machine phase's compact makespan and parking lots as uncovered.
                for _i, _t in enumerate(tasks):
                    _h = machine_hints.get(_i)
                    if not _h:
                        continue
                    for _lit, _eqid in _t['choices']:
                        if _eqid == _h[1]:
                            model.AddHint(_lit, 1)
            if holds:
                if find_core:
                    # Only to name an infeasible set: assumptions switch off much of
                    # CP-SAT's presolve and neighbourhood search, so an ordinary solve
                    # with them lands far worse (walk 2026-10-21: 1.2M vs 73k lateness).
                    model.AddAssumptions([h for h, _k in holds])
                else:
                    for h, _k in holds:
                        model.Add(h == 1)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = tlimit

            cp_status = _solve_until_stalled(solver, model) if tasks else cp_model.OPTIMAL
            solved = cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            conflicts = []
            if holds and cp_status == cp_model.INFEASIBLE:
                by_index = {h.Index(): k for h, k in holds}
                conflicts = [by_index[i] for i in solver.SufficientAssumptionsForInfeasibility()
                             if i in by_index]
            return {'cp_status': cp_status, 'solver': solver, 'tasks': tasks,
                    'pins': pins, 'lateness_terms': lateness_terms, 'solved': solved,
                    'max_time_viols': max_time_viols, 'stick_terms': stick_terms,
                    'freed': freed, 'kept': kept, 'conflicts': conflicts}

        # Two-phase when operator matching is on AND a crew is rostered: solve machines
        # (pooled labor, ~40% of the budget), then re-solve assigning specific operators
        # warm-started from that layout (~60%). Else a single fast machine solve.
        _match = bool(getattr(config, 'match_operators', False)) and bool(all_op_ids)
        # Per-phase wall-clock (ms), surfaced to the planner: how long the machine
        # (Layer-1) vs named-operator (Layer-2 in-solve) side each took.
        machine_solve_ms = 0
        operator_solve_ms = 0
        _wt = lambda p: int(p['solver'].WallTime() * 1000) if p['tasks'] else 0
        def _run(hard, release=frozenset(), find_core=False):
            ms_m = ms_o = 0
            if _match:
                _ta = max(1, int(time_limit_seconds * 0.4))
                _pa = _build_and_solve('pool', None, _ta, hard, release, find_core)
                if not _pa['solved']:
                    return _pa, _wt(_pa), 0
                ms_m = _wt(_pa)
                _hints = None
                if _pa['solved']:
                    _sa = _pa['solver']
                    _hints = {i: (_sa.Value(t['start']), _chosen_machine(t, _sa))
                              for i, t in enumerate(_pa['tasks'])}
                _pb = _build_and_solve('named', _hints, max(1, time_limit_seconds - _ta), hard,
                                       release, find_core)
                ms_o = _wt(_pb)
                return (_pb if _pb['solved'] else _pa), ms_m, ms_o
            out = _build_and_solve(None, None, time_limit_seconds, hard, release, find_core)
            return out, _wt(out), 0

        _final, machine_solve_ms, operator_solve_ms = _run(True)
        # Held blocks that can't fit together: free the ones CP-SAT names as the
        # conflict (its infeasible core) and try again, so one collision doesn't drop
        # the whole fence. A few rounds; then the whole-fence fallback below.
        released: set = set()
        for _round in range(5):
            if _final['solved'] or not _final['kept']:
                break
            if not _final['conflicts']:
                # Infeasible with plain holds: re-solve once with assumptions so CP-SAT
                # names the conflicting ones.
                _final, machine_solve_ms, operator_solve_ms = _run(
                    True, frozenset(released), find_core=True)
                if _final['solved'] or not _final['conflicts']:
                    break
            released |= set(_final['conflicts'])
            logger.info("Frozen fence: releasing %s conflicting held operation(s), round %s.",
                        len(_final['conflicts']), _round + 1)
            _final, machine_solve_ms, operator_solve_ms = _run(True, frozenset(released))
        if not _final['solved'] and _final['kept']:
            # The fixed blocks no longer fit together (a duration grew, crew shrank
            # under them). Rather than return no plan, re-plan them with stickiness and
            # say so — each reported as freed with reason `conflict`.
            logger.warning("Hard frozen fence infeasible (%s held); re-solving with it soft.",
                           _final['kept'])
            _final, machine_solve_ms, operator_solve_ms = _run(False)

        solver = _final['solver']
        tasks = _final['tasks']
        pins = _final['pins']
        lateness_terms = _final['lateness_terms']
        cp_status = _final['cp_status']
        solved = _final['solved']

        # The fence report: what was held, and what had to be re-planned and why.
        frozen_kept = _final['kept']
        # A held op keeps its time and machine, and its operator unless that person is
        # already held on other fixed work then. When the plan does hand it to someone
        # else, say so — a held op quietly changing hands read as the fence leaking.
        reassigned = []
        if tasks and solved:
            for t in tasks:
                was = t.get('op_unfixed')
                if was is None or not t['pinned']:
                    continue
                now = next((op for op, lit in t['named_assign'] if solver.Value(lit)), None)
                if now != was:
                    reassigned.append({
                        'part_ids': t['part_ids'], 'step_id': t['step_id'],
                        'reason_code': 'operator_changed',
                        'reason': "kept its time and machine, but its operator is already "
                                  "held on other fixed work then, so someone else takes it",
                        'was_pinned': t['planner_pinned']})
        frozen_freed = _freed_report(_final['freed'] + reassigned)
        stickiness_cost = 0
        if tasks and solved:
            for kind, v, w in _final['stick_terms']:
                stickiness_cost += w * (solver.Value(v) if kind == 'dev' else 1 - solver.Value(v))

        # Flag ops whose max-time-between-ops (cure) window the solver had to relax.
        if tasks and solved:
            for viol, task in _final.get('max_time_viols', []):
                if solver.Value(viol):
                    task['cure_violation'] = True

        # The lateness term on its own — priority-weighted late-minutes, isolated from
        # the makespan + pin-stickiness terms that dominate the raw objective.
        weighted_lateness = (
            sum(solver.Value(var) * penalty for var, penalty in lateness_terms)
            if (tasks and solved) else 0
        )

        # Proven optimality gap: how far the found objective is from the solver's best
        # bound. 0.0 when OPTIMAL; small positive on a time-limited FEASIBLE result.
        relative_gap = None
        if tasks and solved:
            obj_v = solver.ObjectiveValue()
            bound = solver.BestObjectiveBound()
            relative_gap = abs(obj_v - bound) / max(1.0, abs(obj_v))

        # An INFEASIBLE solve returns no plan and no reason. Say why in the planner's
        # terms before writing the (empty) result — an unexplained blank board is the
        # worst thing this can produce. Diagnosis must never itself break the solve.
        infeasible_reason = ''
        if not (tasks and solved):
            try:
                from Tracker.services.scheduling.infeasibility import diagnose_infeasible
                infeasible_reason = diagnose_infeasible(tenant, horizon)['summary']
            except Exception:  # noqa: BLE001 - advisory only
                logger.exception("Infeasibility diagnosis failed; reporting without it.")

        # A solve that found no plan never replaces the live one: the floor keeps the
        # last good plan (marked stale), and the failed result is kept beside it with
        # its reason (walk 2026-10-22 — one downtime emptied the board).
        failed = bool(tasks) and not solved
        if draft:
            # A draft is a reviewable what-if; it never supersedes the live schedule.
            # Replace only the prior draft (scratch — cascade-deletes its tasks).
            ScheduleResult.objects.filter(tenant=tenant, is_draft=True).delete()
        elif failed:
            ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(is_stale=True)
        else:
            ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, is_stale=True)

        result = ScheduleResult.objects.create(
            tenant=tenant,
            horizon_start=horizon.start, horizon_end=horizon.end,
            solver_status=_map_status(cp_status),
            solve_time_ms=(machine_solve_ms + operator_solve_ms) if tasks else 0,
            machine_solve_ms=machine_solve_ms,
            operator_solve_ms=operator_solve_ms,
            objective_value_cents=int(solver.ObjectiveValue()) if (tasks and solved) else 0,
            weighted_lateness=weighted_lateness,
            relaxed_pin_count=len(_final['freed']),
            frozen_kept=frozen_kept,
            frozen_freed=frozen_freed,
            stickiness_cost=stickiness_cost,
            relative_gap=relative_gap,
            infeasible_reason=infeasible_reason,
            is_active=not draft and not failed,
            is_draft=draft,
        )

        if tasks and solved:
            # Write back per PART (and per core) so tracking, pins, and pegging stay
            # part-grained: every part in a lot gets its own ScheduledTask sharing the
            # lot-operation's machine/time window. The Gantt merges contiguous same-WO
            # bars, so a lot renders as one bar.
            rows = []
            for t in tasks:
                machine_id = _chosen_machine(t, solver)
                start_dt = horizon.start + timedelta(minutes=solver.Value(t['start']))
                end_dt = horizon.start + timedelta(minutes=solver.Value(t['end']))
                if (t.get('fixed_start_dt') is not None
                        and t.get('held_minute') == solver.Value(t['start'])):
                    # Held operations keep their exact time. Minutes are counted from a
                    # horizon that starts "now", so writing the minute back would creep
                    # each held task up to a minute earlier on every re-solve.
                    span = end_dt - start_dt
                    start_dt = t['fixed_start_dt']
                    end_dt = start_dt + span
                fence = _fence_zone(solver.Value(t['start']), frozen_min, slushy_min)
                # Persist the NAMED phase's operator choice (the one assign lit set to 1),
                # so a match_operators solve produces a covered schedule directly instead of
                # leaving assigned_operator for a separate Dispatch pass.
                assigned_op_id = next(
                    (op for op, lit in t.get('named_assign', ()) if solver.Value(lit) == 1),
                    None)
                common = dict(
                    tenant=tenant, schedule=result, step_id=t['step_id'],
                    machine_id=machine_id, start_time=start_dt, end_time=end_dt,
                    is_pinned=t['planner_pinned'], fence_zone=fence,
                    requires_operator=t.get('requires_operator', True),
                    assigned_operator_id=assigned_op_id,
                    material_shortage=t.get('material_short', False),
                    material_detail=t.get('material_detail', ''),
                    cure_window_violation=t.get('cure_violation', False),
                    in_progress=t.get('in_progress', False),
                )
                for part_id in t['part_ids']:
                    rows.append(ScheduledTask(part_id=part_id, **common))
            # tenant-safe: every row is constructed with tenant=tenant via `common` above.
            ScheduledTask.objects.bulk_create(rows)
            # Attribute a binding-constraint reason to any late task (heuristic, E7).
            from Tracker.services.scheduling.late_cause import attribute_late_causes
            attribute_late_causes(result)

        return result
