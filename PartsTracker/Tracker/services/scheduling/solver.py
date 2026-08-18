"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`). This is the **minimal slice**: per-(part,
step) tasks, intra-part precedence, one-task-per-machine capacity, and a makespan
objective. Later layers add changeover, fixtures, transfer-batching, time fences,
continuous machines, warm-start, and the full cost objective.

Time is discretized to integer **minutes from `horizon.start`** (CP-SAT needs
integers); results are written back as absolute datetimes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from Tracker.services.scheduling import data
from Tracker.utils.tenant_context import tenant_context


def _pick_machine(affinities) -> object | None:
    """The machine a step runs on for this slice: the highest-priority *schedulable*
    affinity (dialed_in > preferred > eligible). None when the step has no
    schedulable machine (the task is then precedence-only, no capacity constraint).
    Machine *choice* by the solver is a later layer."""
    order = {'dialed_in': 0, 'preferred': 1, 'eligible': 2}
    schedulable = [a for a in affinities if a.is_schedulable]
    if not schedulable:
        return None
    return min(schedulable, key=lambda a: order.get(a.affinity, 3)).equipment_id


def _duration_minutes(timing) -> int:
    """Integer task duration. Per-part cycle time; ≥1 so every task has positive
    size (setup/batching fold in with the batching layer)."""
    if timing is None:
        return 1
    return max(1, round(timing.cycle_time_minutes))


def _map_status(cp_status) -> str:
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import SolverStatus
    return {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.MODEL_INVALID: SolverStatus.MODEL_INVALID,
    }.get(cp_status, SolverStatus.UNKNOWN)


def solve_schedule(tenant, time_limit_seconds: int = 300):
    """Solve the Layer-1 machine schedule for a tenant and persist it as the new
    active `ScheduleResult`. Returns the ScheduleResult (empty + OPTIMAL when there
    is no work)."""
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import FenceZone, ScheduledTask, ScheduleResult, SolverStatus

    with tenant_context(str(tenant.id)):
        horizon = data.get_schedule_horizon(tenant)
        H = max(1, int((horizon.end - horizon.start).total_seconds() // 60))
        wos = data.get_active_workorders(tenant)
        timings = data.get_step_timings(tenant)
        affinities = data.get_step_equipment_affinities(tenant)

        model = cp_model.CpModel()
        tasks: list[dict] = []
        machine_intervals: dict = defaultdict(list)

        for wo in wos:
            sequence = [s for s in wo.steps if not s.is_terminal]  # linear order (ProcessStep)
            for part in wo.parts:
                prev_end = None
                for node in sequence:
                    dur = _duration_minutes(timings.get(node.step_id))
                    key = f"{part.part_id}_{node.step_id}"
                    start = model.NewIntVar(0, H, f"s_{key}")
                    end = model.NewIntVar(0, H, f"e_{key}")
                    interval = model.NewIntervalVar(start, dur, end, f"i_{key}")
                    machine_id = _pick_machine(affinities.get(node.step_id, []))
                    if machine_id is not None:
                        machine_intervals[machine_id].append(interval)
                    tasks.append({
                        'part_id': part.part_id, 'step_id': node.step_id,
                        'machine_id': machine_id, 'start': start, 'end': end,
                    })
                    if prev_end is not None:
                        model.Add(start >= prev_end)   # intra-part precedence
                    prev_end = end

        # One task per machine at a time.
        for intervals in machine_intervals.values():
            model.AddNoOverlap(intervals)

        # Objective (minimal): minimize makespan. Cost/lateness terms come later.
        if tasks:
            makespan = model.NewIntVar(0, H, "makespan")
            model.AddMaxEquality(makespan, [t['end'] for t in tasks])
            model.Minimize(makespan)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds

        cp_status = solver.Solve(model) if tasks else cp_model.OPTIMAL
        solver_status = _map_status(cp_status)

        # Supersede the prior active schedule.
        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
            is_active=False, is_stale=True)

        result = ScheduleResult.objects.create(
            tenant=tenant,
            horizon_start=horizon.start, horizon_end=horizon.end,
            solver_status=solver_status,
            solve_time_ms=int(solver.WallTime() * 1000) if tasks else 0,
            objective_value_cents=int(solver.ObjectiveValue()) if (tasks and cp_status in
                (cp_model.OPTIMAL, cp_model.FEASIBLE)) else 0,
            is_active=True,
        )

        if tasks and cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            ScheduledTask.objects.bulk_create([
                ScheduledTask(
                    tenant=tenant, schedule=result,
                    part_id=t['part_id'], step_id=t['step_id'], machine_id=t['machine_id'],
                    start_time=horizon.start + timedelta(minutes=solver.Value(t['start'])),
                    end_time=horizon.start + timedelta(minutes=solver.Value(t['end'])),
                    fence_zone=FenceZone.LIQUID,
                )
                for t in tasks
            ])

        return result
