"""Manual task move (Gantt drag-to-reschedule) — Layer 1.

Hybrid guard. On a drag-drop we re-check only the three *cheap, local* hard
constraints — horizon bounds, the work order's earliest-release gate, and route
precedence against this unit's already-scheduled neighbours — so an obviously
bad drop snaps back instantly with a reason. If those pass we pin the task at
the new time and mark the schedule stale; the next Solve is the authority on the
*global* constraints (machine no-overlap, sequence-dependent changeover,
cumulative capacity, operator shifts), relaxing the pin via the soft-pin
machinery if the move turns out infeasible.

Why not validate everything here: the solver already encodes those global
constraints (see solver.py); duplicating them in a standalone validator would
drift as the model evolves. Precedence reuses the solver's own `resolve_route`
for exactly that reason.
"""
from __future__ import annotations

from datetime import datetime, time

from django.db import transaction
from django.utils import timezone

from .data import EdgeData, StepNode
from .routing import resolve_route


class MoveRejected(Exception):
    """A drag-drop violated a cheap local constraint; the move is refused."""


def _aware_start_of_day(d) -> datetime:
    """Midnight on date `d`, tz-aware (matching the schedule's datetimes)."""
    dt = datetime.combine(d, time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _process_graph(process_id):
    """(nodes, edges) for a process — the same shape `resolve_route` consumes,
    mirroring data.get_active_workorders._graph."""
    from Tracker.models import ProcessStep, StepEdge

    nodes = [
        StepNode(
            step_id=ps.step_id,
            is_terminal=ps.step.is_terminal,
            requires_first_piece_inspection=ps.step.requires_first_piece_inspection,
            order=ps.order,
        )
        for ps in ProcessStep.objects.filter(process_id=process_id).select_related('step')
    ]
    edges = [
        EdgeData(from_step_id=e.from_step_id, to_step_id=e.to_step_id, edge_type=e.edge_type)
        for e in StepEdge.objects.filter(process_id=process_id)
    ]
    return nodes, edges


def _unit_sibling_tasks(task):
    """This unit's other scheduled tasks in the same schedule, keyed by step id."""
    from Tracker.models.scheduling import ScheduledTask

    qs = ScheduledTask.objects.filter(schedule_id=task.schedule_id).exclude(pk=task.pk)
    if task.part_id:
        qs = qs.filter(part_id=task.part_id)
    elif task.core_id:
        qs = qs.filter(core_id=task.core_id)
    else:
        return {}
    return {t.step_id: t for t in qs.select_related('step')}


def _validate_move(task, new_start: datetime, schedule) -> datetime:
    """Run the three cheap local checks (horizon, release, route precedence against
    this unit's already-scheduled neighbours) for a proposed move of `task` to
    `new_start`. Returns the resulting end time. Raises `MoveRejected(reason)`."""
    duration = task.end_time - task.start_time
    new_end = new_start + duration

    # 1) Horizon bounds.
    if new_start < schedule.horizon_start:
        raise MoveRejected("That start is before the schedule horizon.")
    if new_end > schedule.horizon_end:
        raise MoveRejected("That would push the task past the schedule horizon.")

    unit = task.part or task.core
    wo = getattr(unit, 'work_order', None) if unit else None

    # 2) Earliest-release gate: nothing starts before its work order is released.
    if wo and wo.expected_start and new_start < _aware_start_of_day(wo.expected_start):
        raise MoveRejected(
            f"That start is before the work order's release date ({wo.expected_start:%b %d})."
        )

    # 3) Route precedence against this unit's already-scheduled neighbours.
    if wo and wo.process_id and task.step_id:
        nodes, edges = _process_graph(wo.process_id)
        _, prec = resolve_route(None, nodes, edges)  # full nominal-route adjacency
        preds = {f for (f, t) in prec if t == task.step_id}
        succs = {t for (f, t) in prec if f == task.step_id}
        siblings = _unit_sibling_tasks(task)
        for sid in preds:
            nb = siblings.get(sid)
            if nb and nb.end_time and new_start < nb.end_time:
                raise MoveRejected(
                    f"That would start before its predecessor step "
                    f"'{nb.step.name}' finishes."
                )
        for sid in succs:
            nb = siblings.get(sid)
            if nb and nb.start_time and new_end > nb.start_time:
                raise MoveRejected(
                    f"That would finish after its successor step "
                    f"'{nb.step.name}' starts."
                )
    return new_end


def move_task(task, new_start: datetime):
    """Validate a drag-drop of `task` to `new_start`; on success pin it there,
    mark the schedule stale, and return the saved task. The task keeps its
    processing duration (a move shifts it, it does not resize). Raises
    `MoveRejected(reason)` on a local-constraint violation."""
    schedule = task.schedule
    new_end = _validate_move(task, new_start, schedule)
    # Passed the local checks — pin at the new time; the next Solve judges the rest.
    task.start_time = new_start
    task.end_time = new_end
    task.is_pinned = True
    task.save(update_fields=['start_time', 'end_time', 'is_pinned'])
    schedule.is_stale = True
    schedule.save(update_fields=['is_stale'])
    return task


def move_batch(tasks, new_start: datetime):
    """Re-anchor a work-order batch (many parts of one WO at one operation) so its
    earliest part starts at `new_start`; every part shifts by the same delta, keeping
    the batch's internal spacing. Validates each part against its own neighbours and
    rejects the WHOLE move if any part fails (atomic). Pins the parts and marks the
    schedule stale. Returns the number of parts moved. Raises `MoveRejected`."""
    tasks = list(tasks)
    if not tasks:
        raise MoveRejected("No tasks in the batch.")
    schedule = tasks[0].schedule
    delta = new_start - min(t.start_time for t in tasks)

    # Validate every part at its shifted time before touching anything.
    planned = []
    for task in tasks:
        ns = task.start_time + delta
        ne = _validate_move(task, ns, schedule)
        planned.append((task, ns, ne))

    with transaction.atomic():
        for task, ns, ne in planned:
            task.start_time = ns
            task.end_time = ne
            task.is_pinned = True
            task.save(update_fields=['start_time', 'end_time', 'is_pinned'])
        schedule.is_stale = True
        schedule.save(update_fields=['is_stale'])
    return len(planned)


def pin_batch(tasks, is_pinned: bool):
    """Pin or unpin every part of a batch and mark the schedule stale. Returns the
    count."""
    tasks = list(tasks)
    if not tasks:
        return 0
    schedule = tasks[0].schedule
    with transaction.atomic():
        for task in tasks:
            task.is_pinned = is_pinned
            task.save(update_fields=['is_pinned'])
        schedule.is_stale = True
        schedule.save(update_fields=['is_stale'])
    return len(tasks)
