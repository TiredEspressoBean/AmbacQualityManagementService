"""The solver's pure terms: durations, penalties, transitions, minute arithmetic, and
the stall-stopping solve. No model building here — `solver.py` assembles these into
the CP-SAT model. Everything is integer minutes from the horizon start.
"""
from __future__ import annotations

from collections import defaultdict, namedtuple
from datetime import datetime, time as dtime
from decimal import Decimal

from django.utils import timezone

_PENALTY_FIELD = {1: 'late_penalty_urgent', 2: 'late_penalty_high',
                  3: 'late_penalty_normal', 4: 'late_penalty_low'}
_PENALTY_DEFAULT = {1: Decimal('1000'), 2: Decimal('500'),
                    3: Decimal('100'), 4: Decimal('25')}
_MINUTES_PER_DAY = 24 * 60

# Lightweight window for feeding overtime intervals (plain (start, end) tuples from
# calendars.get_overtime_machine_windows) into _window_gaps, which reads .start / .end.
_OTWindow = namedtuple('_OTWindow', ('start', 'end'))

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
# machine at all (`_frozen_refusal`) goes back to normal planning, reported with why.
# The soft pins they replace (10,000-100,000/min, 1,000,000 per machine change)
# swamped lateness: each re-solve protected stale positions, pushed new work late, and
# the next re-solve inherited it.
#
# SLUSHY operations prefer to stay put, on the LATENESS scale: moving one costs a
# quarter of a Normal-priority late minute per minute, and changing its machine about
# an hour of Normal lateness — so slushy work moves when that saves real lateness.
SLUSHY_STICKINESS = 0.25
_SLIDE_WEIGHT_FACTOR = 4

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


def _minute(dt, horizon_start) -> int:
    """Whole minutes from the horizon start (floored; negative before it)."""
    return int((dt - horizon_start).total_seconds() // 60)


def _to_minutes(intervals, horizon_start, H) -> list[tuple]:
    """Datetime intervals → clipped integer-minute [start, end] tuples from H0."""
    out = []
    for s, e in intervals:
        ms = max(0, _minute(s, horizon_start))
        me = min(H, _minute(e, horizon_start))
        if ms < me:
            out.append((ms, me))
    return out


def _window_gaps(windows, horizon_start, H) -> list[tuple]:
    """Unavailable [start, end] minute intervals between a machine's availability
    windows, within [0, H]. Empty when the machine has no windows (treated as
    always-available so a tenant with no shift config still schedules)."""
    if not windows:
        return []
    mins = sorted(_to_minutes([(w.start, w.end) for w in windows], horizon_start, H))
    gaps = []
    cursor = 0
    for s, e in mins:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < H:
        gaps.append((cursor, H))
    return gaps


def _staffing_segments(op_windows, horizon_start, H):
    """Piecewise operator headcount over [0, H] from the rostered shift windows:
    a list of (start_min, end_min, count) covering the whole horizon (count 0 where
    nobody is on shift), plus the peak count. Drives the labor-capacity cumulative —
    concurrent attended work is capped at the crew on hand, and attended work is barred
    from unstaffed hours (count 0) while machines keep running lights-out."""
    delta: dict = defaultdict(int)
    for windows in op_windows.values():
        for ms, me in _to_minutes(windows, horizon_start, H):
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


def _overlaps(a, b, gaps) -> bool:
    """[a, b) meets one of `gaps`."""
    return any(gs < b and a < ge for gs, ge in gaps)


def _covered(a, b, windows) -> bool:
    """[a, b) lies inside one of `windows` (merged minute intervals)."""
    return any(ws <= a and b <= we for ws, we in windows)


def _peak_with(a, b, held) -> int:
    """Most held attended operations running at once in [a, b), counting one more
    over the whole span."""
    points = [a] + [x for x, _y in held if a <= x < b]
    return 1 + max((sum(1 for x, y in held if x <= p < y) for p in points), default=0)


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
