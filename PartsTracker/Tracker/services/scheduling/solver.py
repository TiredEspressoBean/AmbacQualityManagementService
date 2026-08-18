"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`).

Layers built so far:
- Per-(part, step) tasks; intra-part precedence.
- **Machine choice**: the solver assigns each task to one of the step's eligible
  *schedulable* machines (optional intervals + exactly-one), honoring per-machine
  `cycle_time_override`; one task per machine at a time.
- **Cost objective** (integer cents): Σ (part lateness × the WO's priority penalty)
  + makespan as a tiebreaker.

Later layers: changeover, fixtures, transfer-batching, secondary resources, time
fences, continuous machines, warm-start. Time is discretized to integer minutes
from `horizon.start`; results are written back as absolute datetimes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time as dtime, timedelta
from decimal import Decimal

from django.utils import timezone

from Tracker.services.scheduling import data
from Tracker.utils.tenant_context import tenant_context

# Priority (WorkOrderPriority int) → OptimizationConfig penalty field.
_PENALTY_FIELD = {1: 'late_penalty_urgent', 2: 'late_penalty_high',
                  3: 'late_penalty_normal', 4: 'late_penalty_low'}
_PENALTY_DEFAULT = {1: Decimal('1000'), 2: Decimal('500'),
                    3: Decimal('100'), 4: Decimal('25')}
_MINUTES_PER_DAY = 24 * 60


def _dur(timing, affinity) -> int:
    """Integer per-part task duration on a machine: the affinity's cycle override
    if set, else the step's resolved cycle time. ≥1 so every task has size."""
    cycle = None
    if affinity is not None and affinity.cycle_time_override is not None:
        cycle = affinity.cycle_time_override
    elif timing is not None:
        cycle = timing.cycle_time_minutes
    return max(1, round(cycle)) if cycle else 1


def _penalty_cents_per_min(config, priority: int) -> int:
    """Lateness penalty in cents per minute for a WO's priority (from
    OptimizationConfig $/day, defaulting when no config)."""
    if config is not None:
        dollars_per_day = getattr(config, _PENALTY_FIELD.get(priority, 'late_penalty_normal'))
    else:
        dollars_per_day = _PENALTY_DEFAULT.get(priority, Decimal('100'))
    return max(0, round(float(dollars_per_day) * 100 / _MINUTES_PER_DAY))


def _due_minutes(due_date, horizon_start, H) -> int | None:
    """Due date → integer minutes from horizon_start (end of the due day, so a part
    finishing that day isn't late). Overdue is capped at one horizon back."""
    if due_date is None:
        return None
    due_dt = timezone.make_aware(datetime.combine(due_date, dtime.max))
    minutes = int((due_dt - horizon_start).total_seconds() // 60)
    return max(-H, minutes)


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
    """The machine literal the solver set for a machine-choice task, else None."""
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
        config = OptimizationConfig.objects.filter(tenant=tenant).first()

        model = cp_model.CpModel()
        tasks: list[dict] = []
        machine_intervals: dict = defaultdict(list)
        lateness_cost = []  # LinearExpr terms: lateness_var * penalty

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

                    choices = []
                    if eligible:
                        for a in eligible:
                            dur = _dur(timing, a)
                            lit = model.NewBoolVar(f"m_{key}_{a.equipment_id}")
                            opt = model.NewOptionalFixedSizeIntervalVar(start, dur, lit, f"i_{key}_{a.equipment_id}")
                            machine_intervals[a.equipment_id].append(opt)
                            model.Add(end == start + dur).OnlyEnforceIf(lit)
                            choices.append((lit, a.equipment_id))
                        model.AddExactlyOne([lit for lit, _ in choices])
                    else:
                        dur = _dur(timing, None)
                        model.NewIntervalVar(start, dur, end, f"i_{key}")  # enforces end == start+dur

                    tasks.append({'part_id': part.part_id, 'step_id': node.step_id,
                                  'start': start, 'end': end, 'choices': choices})
                    if prev_end is not None:
                        model.Add(start >= prev_end)   # intra-part precedence
                    prev_end = end
                    last_end = end

                if due_minutes is not None and penalty > 0 and last_end is not None:
                    lateness = model.NewIntVar(0, 2 * H, f"late_{part.part_id}")
                    model.Add(lateness >= last_end - due_minutes)
                    lateness_cost.append(lateness * penalty)

        for intervals in machine_intervals.values():
            model.AddNoOverlap(intervals)

        # Objective: lateness cost (cents) + makespan tiebreaker.
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
