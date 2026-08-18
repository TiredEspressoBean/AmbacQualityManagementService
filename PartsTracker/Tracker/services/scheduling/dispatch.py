"""
Operator dispatch (Layer 2).

Takes the Layer-1 machine schedule (`ScheduleResult` + `ScheduledTask`) as GIVEN
and assigns an operator to each attended task. This is a fixed-time assignment
problem, not a re-solve — task start/end come straight from Layer 1.

Constraints:
- Capability: an operator may only take a step they are qualified for
  (`training.get_qualified_users_for_step` — TrainingRequirement at min level).
- One operator per task; one task per operator at a time. For full-attention steps
  the operator is tied to the whole machine interval; for load/unload steps only to
  the attended sub-interval at the front (front-loaded approximation), which lets one
  operator tend several machines whose load phases don't collide.
- Availability: an operator may only be assigned work during their rostered shift
  (`User.default_shift`) and never during their actual clock-out breaks (`TimeEntry`
  BREAK / LUNCH). An operator with no rostered shift is not dispatchable.

Objective: maximize priority-weighted coverage, then softly prefer an operator whose
primary work-center matches the step. Attended tasks that can't be covered (no
qualified operator free) are left unassigned and flagged, not dropped.

Follow-ons: per-operator load balancing, work-center eligibility as a hard gate,
multi-shift/rotation rostering (one shift per operator today), and consuming actual
setup/production TimeEntry for a live mid-shift re-dispatch.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from Tracker.services.scheduling import data
from Tracker.utils.tenant_context import tenant_context

_PRIORITY_WEIGHT = {1: 1000, 2: 500, 3: 100, 4: 25}   # URGENT, HIGH, NORMAL, LOW
_WC_MATCH_BONUS = 1                                    # << smallest coverage weight


def _off_shift_gaps(windows, H0, H) -> list[tuple]:
    """Minute intervals within [0, H] that fall OUTSIDE an operator's shift windows.
    Unlike machines, an operator with no windows is never available — empty windows
    yield the whole horizon as a gap."""
    mins = []
    for s, e in windows:
        ms = max(0, int((s - H0).total_seconds() // 60))
        me = min(H, int((e - H0).total_seconds() // 60))
        if ms < me:
            mins.append((ms, me))
    mins.sort()
    gaps, cursor = [], 0
    for s, e in mins:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < H:
        gaps.append((cursor, H))
    return gaps


@dataclass(frozen=True)
class DispatchSummary:
    schedule_id: object
    attended: int      # tasks needing an operator
    covered: int       # of those, assigned one
    uncovered: int     # attended but nobody qualified was free


def dispatch_operators(tenant, schedule=None, time_limit_seconds: int = 60) -> DispatchSummary | None:
    """Assign operators to the attended tasks of `schedule` (default: the active
    schedule). Writes `assigned_operator` + `requires_operator` back onto the tasks.
    Returns a coverage summary, or None when there is no schedule to dispatch."""
    from ortools.sat.python import cp_model
    from Tracker.models import ScheduledTask, ScheduleResult
    from Tracker.services.training import get_qualified_users_for_step

    with tenant_context(str(tenant.id)):
        if schedule is None:
            schedule = (
                ScheduleResult.objects.filter(tenant=tenant, is_active=True)
                .order_by('-created_at').first()
            )
        if schedule is None:
            return None

        H0 = schedule.horizon_start
        H = max(1, int((schedule.horizon_end - H0).total_seconds() // 60))
        # A horizon anchored on the schedule (not "now") so re-dispatch of an older
        # schedule still lines its break windows up with the task minute axis.
        sched_horizon = data.HorizonData(
            start=H0, end=schedule.horizon_end, frozen_end=H0, slushy_end=H0)
        timings = data.get_step_timings(tenant)
        operators = data.get_dispatchable_operators(tenant)
        op_ids = {o.user_id for o in operators}
        op_primary = {o.user_id: o.primary_work_center_ids for o in operators}
        unavail = data.get_operator_unavailability(tenant, sched_horizon)
        op_windows = data.get_operator_shift_windows(tenant, sched_horizon)

        tasks = list(
            schedule.tasks.select_related('step', 'part__work_order').all()
        )

        # Cache qualified operators per (step, process) — reused across a WO's parts.
        qual_cache: dict = {}

        def _qualified(step, process):
            ck = (step.id, getattr(process, 'id', None))
            if ck not in qual_cache:
                users = get_qualified_users_for_step(step, process=process, tenant=tenant)
                qual_cache[ck] = {u.id for u in users} & op_ids
            return qual_cache[ck]

        model = cp_model.CpModel()
        per_op_intervals: dict = defaultdict(list)   # user_id -> [interval, ...]
        covered_terms = []                           # (covered_bool, weight)
        bonus_terms = []                             # assign lits that hit primary WC
        task_meta = []                               # (task, chosen_lits{op_id: lit}, requires_op)

        for t in tasks:
            timing = timings.get(t.step_id)
            attention = timing.attention_type if timing else 'full'
            dur_total = max(1, int((t.end_time - t.start_time).total_seconds() // 60))
            if timing is not None and attention != 'full':
                attended = max(0, int(round(timing.operator_attended_time(1))))
            else:
                attended = dur_total
            attended = min(attended, dur_total)
            requires_op = attended > 0

            if not requires_op:
                task_meta.append((t, {}, False))
                continue

            start_min = max(0, min(H, int((t.start_time - H0).total_seconds() // 60)))
            wo = t.part.work_order if t.part_id else None
            process = wo.process if wo else None
            weight = _PRIORITY_WEIGHT.get(getattr(wo, 'priority', 3), 100)
            step_wc = getattr(t.step, 'work_center_id', None)

            candidates = _qualified(t.step, process)
            lits = {}
            for op_id in candidates:
                lit = model.NewBoolVar(f"a_{t.id}_{op_id}")
                lits[op_id] = lit
                iv = model.NewOptionalFixedSizeIntervalVar(
                    start_min, attended, lit, f"iv_{t.id}_{op_id}")
                per_op_intervals[op_id].append(iv)
                if step_wc is not None and step_wc in op_primary.get(op_id, ()):
                    bonus_terms.append(lit)

            if lits:
                covered = model.NewBoolVar(f"cov_{t.id}")
                model.Add(sum(lits.values()) == covered)   # at-most-one + covered flag
                covered_terms.append((covered, weight))
            task_meta.append((t, lits, True))

        # Operator capacity: no two assigned tasks overlap, and none overlap a break
        # or fall outside the operator's rostered shift.
        for op_id, intervals in per_op_intervals.items():
            blocked = []
            for bs, be in unavail.get(op_id, []):
                s = max(0, int((bs - H0).total_seconds() // 60))
                e = min(H, int((be - H0).total_seconds() // 60))
                if s < e:
                    blocked.append(model.NewFixedSizeIntervalVar(
                        s, e - s, f"br_{op_id}_{s}"))
            for gs, ge in _off_shift_gaps(op_windows.get(op_id, []), H0, H):
                blocked.append(model.NewFixedSizeIntervalVar(
                    gs, ge - gs, f"off_{op_id}_{gs}"))
            model.AddNoOverlap(intervals + blocked)

        if covered_terms:
            model.Maximize(
                sum(c * w for c, w in covered_terms)
                + _WC_MATCH_BONUS * sum(bonus_terms)
            )

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        if covered_terms:
            solver.Solve(model)

        attended_n = covered_n = 0
        to_update = []
        for t, lits, requires_op in task_meta:
            t.requires_operator = requires_op
            chosen = None
            if requires_op:
                attended_n += 1
                for op_id, lit in lits.items():
                    if solver.Value(lit) == 1:
                        chosen = op_id
                        break
                if chosen is not None:
                    covered_n += 1
            t.assigned_operator_id = chosen
            to_update.append(t)

        ScheduledTask.objects.bulk_update(to_update, ['requires_operator', 'assigned_operator'])

        return DispatchSummary(
            schedule_id=schedule.id, attended=attended_n,
            covered=covered_n, uncovered=attended_n - covered_n,
        )
