"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`).

Layers built so far:
- Per-(part, step) tasks; intra-part precedence.
- Machine choice: one of the step's eligible schedulable machines (optional intervals
  + exactly-one), honoring per-machine `cycle_time_override`; one task per machine.
- Cost objective (integer cents): Σ (part lateness × the WO's priority penalty) +
  makespan tiebreaker.
- Shift windows: tasks are confined to each machine's availability (shifts − downtime)
  by forbidding overlap with the gap intervals between windows.
- Secondary resources: a step's schedulable gauges (Keyence/CMM) are reserved
  one-at-a-time while the task runs.
- Fixtures: shared tooling as a cumulative resource (≤ quantity concurrent users).

Follow-ons: changeover (circuit), transfer-batching, time fences, continuous
machines, warm-start. Time is discretized to integer minutes from `horizon.start`;
results are written back as absolute datetimes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time as dtime, timedelta
from decimal import Decimal

from django.utils import timezone

from Tracker.services.scheduling import data
from Tracker.utils.tenant_context import tenant_context

_PENALTY_FIELD = {1: 'late_penalty_urgent', 2: 'late_penalty_high',
                  3: 'late_penalty_normal', 4: 'late_penalty_low'}
_PENALTY_DEFAULT = {1: Decimal('1000'), 2: Decimal('500'),
                    3: Decimal('100'), 4: Decimal('25')}
_MINUTES_PER_DAY = 24 * 60


def _dur(timing, affinity) -> int:
    cycle = None
    if affinity is not None and affinity.cycle_time_override is not None:
        cycle = affinity.cycle_time_override
    elif timing is not None:
        cycle = timing.cycle_time_minutes
    return max(1, round(cycle)) if cycle else 1


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


def _transition(changeover, equipment_id, from_step, to_step, to_setup) -> int:
    """Minutes between consecutive tasks on a machine: 0 for same step (piece after
    piece), else the WorkCenterChangeover value, falling back to the incoming step's
    setup when no specific changeover is configured."""
    if from_step == to_step:
        return 0
    val = changeover.get((equipment_id, from_step, to_step))
    return int(round(val)) if val is not None else to_setup


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


def solve_schedule(tenant, time_limit_seconds: int = 300):
    """Solve the Layer-1 machine schedule for a tenant and persist it as the new
    active `ScheduleResult`. Returns the ScheduleResult (empty + OPTIMAL when there
    is no work)."""
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import (
        FenceZone, OptimizationConfig, ScheduledTask, ScheduleResult,
    )

    with tenant_context(str(tenant.id)):
        horizon = data.get_schedule_horizon(tenant)
        H = max(1, int((horizon.end - horizon.start).total_seconds() // 60))
        wos = data.get_active_workorders(tenant)
        timings = data.get_step_timings(tenant)
        affinities = data.get_step_equipment_affinities(tenant)
        availability = data.get_machine_availability(tenant, horizon)
        secondary = data.get_step_secondary_resources(tenant)   # step_id -> {gauge_id}
        fixtures = data.get_fixture_availability(tenant)         # fixture_id -> FixtureData
        changeover = data.get_changeover_matrix(tenant)         # (equip, from, to) -> minutes
        config = OptimizationConfig.objects.filter(tenant=tenant).first()

        # Which steps need an unconditional occupancy interval (gauge and/or fixture).
        fixture_by_step: dict = defaultdict(list)
        for fx in fixtures.values():
            for step_id in fx.step_ids:
                fixture_by_step[step_id].append(fx.fixture_id)
        occupancy_steps = set(secondary) | set(fixture_by_step)

        model = cp_model.CpModel()

        # Scheduled breaks/lunch: attended (full-attention) work is kept out of them.
        break_mins = _to_minutes(data.get_break_windows(tenant, horizon), horizon.start, H)
        break_fixed = [model.NewFixedSizeIntervalVar(bs, be - bs, f"break_{bs}_{be}")
                       for bs, be in break_mins]

        tasks: list[dict] = []
        machine_intervals: dict = defaultdict(list)
        machine_tasks: dict = defaultdict(list)   # equip_id -> [(present, start, end, step_id, setup)]
        gauge_intervals: dict = defaultdict(list)
        fixture_intervals: dict = defaultdict(list)
        lateness_cost = []

        for wo in wos:
            sequence = [s for s in wo.steps if not s.is_terminal]
            due_minutes = _due_minutes(wo.expected_completion, horizon.start, H)
            penalty = _penalty_cents_per_min(config, wo.priority)
            for part in wo.parts:
                prev_end = None
                last_end = None
                for node in sequence:
                    timing = timings.get(node.step_id)
                    eligible = [a for a in affinities.get(node.step_id, []) if a.is_schedulable]
                    key = f"{part.part_id}_{node.step_id}"
                    start = model.NewIntVar(0, H, f"s_{key}")
                    end = model.NewIntVar(0, H, f"e_{key}")

                    setup_int = int(round(timing.setup_minutes)) if timing else 0
                    choices = []
                    if eligible:
                        for a in eligible:
                            dur = _dur(timing, a)
                            lit = model.NewBoolVar(f"m_{key}_{a.equipment_id}")
                            opt = model.NewOptionalFixedSizeIntervalVar(start, dur, lit, f"i_{key}_{a.equipment_id}")
                            machine_intervals[a.equipment_id].append(opt)
                            machine_tasks[a.equipment_id].append((lit, start, end, node.step_id, setup_int))
                            model.Add(end == start + dur).OnlyEnforceIf(lit)
                            choices.append((lit, a.equipment_id))
                        model.AddExactlyOne([lit for lit, _ in choices])
                    else:
                        dur = _dur(timing, None)
                        model.NewIntervalVar(start, dur, end, f"i_{key}")

                    # Unconditional occupancy interval for secondary/fixture resources
                    # and break avoidance. Attended (full-attention) steps can't run
                    # during a scheduled break; load_unload steps run unattended.
                    attended = (timing is None) or (timing.attention_type == 'full')
                    needs_break = attended and break_fixed
                    if node.step_id in occupancy_steps or needs_break:
                        size = model.NewIntVar(1, H, f"sz_{key}")
                        occ = model.NewIntervalVar(start, size, end, f"occ_{key}")
                        for gauge_id in secondary.get(node.step_id, ()):
                            gauge_intervals[gauge_id].append(occ)
                        for fixture_id in fixture_by_step.get(node.step_id, ()):
                            fixture_intervals[fixture_id].append(occ)
                        if needs_break:
                            model.AddNoOverlap([occ] + break_fixed)

                    tasks.append({'part_id': part.part_id, 'step_id': node.step_id,
                                  'start': start, 'end': end, 'choices': choices})
                    if prev_end is not None:
                        model.Add(start >= prev_end)
                    prev_end = end
                    last_end = end

                if due_minutes is not None and penalty > 0 and last_end is not None:
                    lateness = model.NewIntVar(0, 2 * H, f"late_{part.part_id}")
                    model.Add(lateness >= last_end - due_minutes)
                    lateness_cost.append(lateness * penalty)

        # Machine capacity + shift windows (gap intervals block unavailable time).
        for equipment_id, intervals in machine_intervals.items():
            gaps = _window_gaps(availability.get(equipment_id, []), horizon.start, H)
            blocked = [model.NewFixedSizeIntervalVar(gs, ge - gs, f"gap_{equipment_id}_{gs}")
                       for gs, ge in gaps]
            model.AddNoOverlap(intervals + blocked)

        # Sequence-dependent setup / changeover: for each pair of tasks that could
        # share a machine, insert the changeover gap in whichever order they run
        # (gated on both being assigned to that machine). Same-step neighbours cost
        # 0 (piece after piece); different-step neighbours pay the WorkCenterChangeover
        # (or the incoming step's setup as a fallback). NoOverlap already prevents
        # time overlap; this adds the transition gap on top.
        for equipment_id, mtasks in machine_tasks.items():
            for i in range(len(mtasks)):
                pi, si, ei, stepi, setupi = mtasks[i]
                for j in range(i + 1, len(mtasks)):
                    pj, sj, ej, stepj, setupj = mtasks[j]
                    t_ij = _transition(changeover, equipment_id, stepi, stepj, setupj)
                    t_ji = _transition(changeover, equipment_id, stepj, stepi, setupi)
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

        if tasks:
            makespan = model.NewIntVar(0, H, "makespan")
            model.AddMaxEquality(makespan, [t['end'] for t in tasks])
            model.Minimize(sum(lateness_cost) + makespan)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds

        cp_status = solver.Solve(model) if tasks else cp_model.OPTIMAL
        solved = cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
            is_active=False, is_stale=True)

        result = ScheduleResult.objects.create(
            tenant=tenant,
            horizon_start=horizon.start, horizon_end=horizon.end,
            solver_status=_map_status(cp_status),
            solve_time_ms=int(solver.WallTime() * 1000) if tasks else 0,
            objective_value_cents=int(solver.ObjectiveValue()) if (tasks and solved) else 0,
            is_active=True,
        )

        if tasks and solved:
            ScheduledTask.objects.bulk_create([
                ScheduledTask(
                    tenant=tenant, schedule=result,
                    part_id=t['part_id'], step_id=t['step_id'],
                    machine_id=_chosen_machine(t, solver),
                    start_time=horizon.start + timedelta(minutes=solver.Value(t['start'])),
                    end_time=horizon.start + timedelta(minutes=solver.Value(t['end'])),
                    fence_zone=FenceZone.LIQUID,
                )
                for t in tasks
            ])

        return result
