"""
Operator dispatch (Layer 2).

Takes the Layer-1 machine schedule (`ScheduleResult` + `ScheduledTask`) as GIVEN
and assigns an operator to each attended LOT-operation. The solver writes one row per
part, but a WO's parts at one step ran as a single machine occupancy (one lot) and need
ONE operator, so dispatch groups those rows and assigns per lot — not per piece. This is
a fixed-time assignment problem, not a re-solve — start/end come straight from Layer 1.

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
qualified operator free) are left unassigned and flagged, not dropped. A
coverage-preserving continuity polish then regroups assignments so an operator does
consecutive same-WO lots where possible.

The assignment is solved exactly with CP-SAT (per-operator no-overlap is a hard
constraint, so an operator is never double-booked). An earlier min-cost-flow
implementation was removed: a single-commodity flow cannot enforce per-operator
no-overlap with skill eligibility (the gadget could credit a lot to one operator while
advancing another), so it could double-book. CP-SAT models it correctly.

Follow-ons: per-operator load balancing, work-center eligibility as a hard gate,
multi-shift/rotation rostering (one shift per operator today), and consuming actual
setup/production TimeEntry for a live mid-shift re-dispatch.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

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
    attended: int      # lot-operations needing an operator
    covered: int       # of those, assigned one
    uncovered: int     # attended but nobody qualified was free


# Continuity reward tiers for the operator-sequence polish (dispatch).
_CONT_SAME_WO = 3     # strong: an operator's consecutive lots on the same work order
_CONT_SAME_STEP = 1   # weak: consecutive lots on the same step but a different WO


def _improve_continuity(covered: dict, lots: list) -> dict:
    """Coverage-preserving local search over the assignment: swap operators between
    two already-covered lots when it (a) stays feasible — the receiving operator is
    eligible and doesn't double-book — and (b) raises continuity (an operator doing
    back-to-back same-WO lots scores strongly, same-step lots weakly). Every swap keeps
    both lots covered, so coverage never drops. State is read from `covered` each time
    (the single source of truth), so it can't desync. `lots[i]['elig']` must contain
    only operators eligible AND available for lot i, so a swap can't place an operator
    off-shift or on a step they aren't qualified for."""

    by_op: dict = defaultdict(set)   # operator -> set of lot indices (kept in sync)
    for li, o in covered.items():
        by_op[o].add(li)

    def op_seq(o):
        return sorted(by_op[o], key=lambda li: lots[li]['s'])

    def op_score(o):
        seq, sc = op_seq(o), 0
        for a, b in zip(seq, seq[1:]):
            la, lb = lots[a], lots[b]
            if la['wo'] is not None and la['wo'] == lb['wo']:
                sc += _CONT_SAME_WO
            elif la['step'] == lb['step']:
                sc += _CONT_SAME_STEP
        return sc

    def feasible(o):
        seq = op_seq(o)
        return all(lots[a]['e'] <= lots[b]['s'] for a, b in zip(seq, seq[1:]))

    def assign(li, o):
        by_op[covered[li]].discard(li)
        covered[li] = o
        by_op[o].add(li)

    keys = list(covered.keys())
    for _sweep in range(3):
        improved = False
        for a_pos in range(len(keys)):
            i = keys[a_pos]
            for b_pos in range(a_pos + 1, len(keys)):
                j = keys[b_pos]
                A, B = covered[i], covered[j]
                if A == B:
                    continue
                if B not in lots[i]['elig'] or A not in lots[j]['elig']:
                    continue
                before = op_score(A) + op_score(B)
                assign(i, B); assign(j, A)
                if feasible(A) and feasible(B) and op_score(A) + op_score(B) > before:
                    improved = True
                else:
                    assign(i, A); assign(j, B)   # revert
        if not improved:
            break
    return covered


def dispatch_operators(tenant, schedule=None, time_limit_seconds: int = 60) -> DispatchSummary | None:
    """Assign operators to a schedule's attended lot-operations (default: the active
    schedule); writes `assigned_operator` + `requires_operator` back.

    CP-SAT max-coverage matching: each attended lot needs one qualified operator, no
    operator is double-booked or scheduled off-shift / through a break; the objective
    maximizes priority-weighted coverage, then softly prefers a work-center match. A
    coverage-preserving continuity pass then regroups assignments toward same-WO
    operator continuity."""
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

        def _mins(dt):
            return max(0, min(H, int((dt - H0).total_seconds() // 60)))

        # Per-operator shift windows + breaks in minutes — used to filter continuity
        # eligibility to operators actually available for a lot's interval (CP-SAT
        # enforces the same via off-shift/break blockers on the assignment itself).
        win_min = {o: [(_mins(s), _mins(e)) for s, e in op_windows.get(o, [])] for o in op_ids}
        brk_min = {o: [(_mins(s), _mins(e)) for s, e in unavail.get(o, [])] for o in op_ids}

        def _available(o, s, e):
            if not any(ws <= s and e <= we for ws, we in win_min.get(o, [])):
                return False
            return not any(bs < e and s < be for bs, be in brk_min.get(o, []))

        tasks = list(
            schedule.tasks.select_related(
                'step', 'part__work_order', 'core__work_order').all()
        )

        # Group the part-rows into LOT-operations. The Layer-1 solver ran a WO's parts at
        # one step as a single machine occupancy, writing one row per part sharing
        # step/start/end/machine — so they need ONE operator, not one per piece. Cores are
        # their own single-unit lots. Assigning per lot (not per part) is what makes
        # coverage honest: a 15-part lot demands one operator, not fifteen.
        lot_map: dict = defaultdict(list)
        for t in tasks:
            if t.part_id:
                wo_id = t.part.work_order_id
                key = ('p', t.step_id, t.start_time, t.end_time, t.machine_id, wo_id)
            else:
                wo_id = t.core.work_order_id if t.core_id else None
                key = ('c', t.step_id, t.start_time, t.end_time, t.machine_id, t.core_id)
            lot_map[key].append(t)

        # Cache qualified operators per (step, process) — reused across lots.
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
        lot_meta = []                                # dict per lot (see below)

        for key, rows in lot_map.items():
            rep = rows[0]
            count = len(rows)
            timing = timings.get(rep.step_id)
            attention = timing.attention_type if timing else 'full'
            dur_total = max(1, int((rep.end_time - rep.start_time).total_seconds() // 60))
            if timing is not None and attention != 'full':
                # Load/unload: one operator handles the whole lot's front touch.
                attended = max(0, int(round(timing.operator_attended_time(count))))
            else:
                attended = dur_total
            attended = min(attended, dur_total)
            requires_op = attended > 0

            if not requires_op:
                lot_meta.append({'rows': rows, 'lits': {}, 'requires_op': False})
                continue

            start_min = max(0, min(H, int((rep.start_time - H0).total_seconds() // 60)))
            end_min = min(H, start_min + attended)
            wo = (rep.part.work_order if rep.part_id
                  else rep.core.work_order if rep.core_id else None)
            process = wo.process if wo else None
            weight = _PRIORITY_WEIGHT.get(getattr(wo, 'priority', 3), 100)
            step_wc = getattr(rep.step, 'work_center_id', None)

            candidates = _qualified(rep.step, process)
            lits = {}
            for op_id in candidates:
                lit = model.NewBoolVar(f"a_{rep.id}_{op_id}")
                lits[op_id] = lit
                iv = model.NewOptionalFixedSizeIntervalVar(
                    start_min, attended, lit, f"iv_{rep.id}_{op_id}")
                per_op_intervals[op_id].append(iv)
                if step_wc is not None and step_wc in op_primary.get(op_id, ()):
                    bonus_terms.append(lit)

            if lits:
                covered = model.NewBoolVar(f"cov_{rep.id}")
                model.Add(sum(lits.values()) == covered)   # at-most-one + covered flag
                covered_terms.append((covered, weight))
            # Continuity eligibility: qualified AND available for the lot's interval.
            elig = {op_id for op_id in candidates if _available(op_id, start_min, end_min)}
            lot_meta.append({
                'rows': rows, 'lits': lits, 'requires_op': True,
                's': start_min, 'e': end_min, 'elig': elig,
                'wo': getattr(wo, 'id', None), 'step': rep.step_id,
            })

        # Operator capacity: no two assigned lots overlap, and none overlap a break
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

        # Read the assignment, then run the coverage-preserving continuity polish.
        covered_map: dict = {}   # lot_index -> operator_id
        for idx, meta in enumerate(lot_meta):
            if not meta['requires_op']:
                continue
            for op_id, lit in meta['lits'].items():
                if solver.Value(lit) == 1:
                    covered_map[idx] = op_id
                    break
        covered_map = _improve_continuity(covered_map, lot_meta)

        attended_n = covered_n = 0
        to_update = []
        for idx, meta in enumerate(lot_meta):
            requires_op = meta['requires_op']
            chosen = covered_map.get(idx)
            if requires_op:
                attended_n += 1
                if chosen is not None:
                    covered_n += 1
            # Every part-row of the lot carries the same operator + attention flag.
            for t in meta['rows']:
                t.requires_operator = requires_op
                t.assigned_operator_id = chosen
                to_update.append(t)

        ScheduledTask.objects.bulk_update(to_update, ['requires_operator', 'assigned_operator'])

        return DispatchSummary(
            schedule_id=schedule.id, attended=attended_n,
            covered=covered_n, uncovered=attended_n - covered_n,
        )
