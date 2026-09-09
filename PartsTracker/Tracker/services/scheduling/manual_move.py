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

from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from .data import EdgeData, StepNode
from .routing import resolve_route


def _step_setup_cycle(step_id):
    """(setup_minutes, cycle_minutes) for a step from its `StepTiming`, or None when
    there's no usable timing. Used to size batch bars in the merge/break PREVIEW: a lot
    of N ≈ setup + N×cycle (one setup); a broken part ≈ setup + cycle. Approximate — the
    solver refines the exact number (PFD / machine-override / continuous) on re-solve."""
    from Tracker.models import StepTiming
    # archived=False — a cleared timing is soft-deleted, not removed. See data.py.
    t = StepTiming.objects.filter(step_id=step_id, archived=False).first()
    if t is None or not t.cycle_time_minutes:
        return None
    return (float(t.setup_minutes or 0), float(t.cycle_time_minutes))


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


def reassign_machine(task, machine, user=None) -> dict:
    """Direct-manipulation machine reassignment: put `task` on `machine` and pin it so
    the solver keeps it there (machine-pin) on re-solve. Applies immediately; warns —
    but does NOT block — if `machine` isn't an authored-eligible machine for the step
    (planner override). Marks the schedule stale. Returns {'warning': str | None}."""
    from Tracker.models import StepEquipmentAffinity

    eligible = StepEquipmentAffinity.objects.filter(
        step_id=task.step_id, equipment=machine).exists()
    task.machine = machine
    task.is_pinned = True
    task.save(update_fields=['machine', 'is_pinned'])
    schedule = task.schedule
    schedule.is_stale = True
    schedule.save(update_fields=['is_stale'])
    warning = None if eligible else (
        f"{machine.name} isn't an authored machine for '{task.step.name}' — it'll run "
        f"there while pinned, but isn't in the step's eligible list."
    )
    return {'warning': warning}


def reassign_operator(task, operator, user=None) -> dict:
    """Direct-manipulation operator (re)assignment / manual coverage of an attended task.
    `operator=None` clears the assignment. Applies immediately; warns — but does NOT
    block — if the operator isn't qualified for the step. Marks the schedule stale.
    Returns {'warning': str | None}."""
    warning = None
    if operator is not None:
        from Tracker.services.training import get_qualified_users_for_step
        qualified = get_qualified_users_for_step(task.step, tenant=task.tenant)
        if not qualified.filter(pk=operator.pk).exists():
            name = operator.get_full_name() or operator.username
            warning = (f"{name} isn't trained for '{task.step.name}' — assigned anyway; "
                       f"verify qualification.")
    task.assigned_operator = operator
    task.save(update_fields=['assigned_operator'])
    schedule = task.schedule
    schedule.is_stale = True
    schedule.save(update_fields=['is_stale'])
    return {'warning': warning}


def _merge_group(schedule, group, wo_id, step_id) -> int:
    """Merge one WO+step cohort's selected parts: unpin them and snap them onto the
    cohort's existing slot so the cell collapses now; the solver forms the final lot on
    re-solve. `group` is pre-sorted by start_time."""
    from Tracker.models import ScheduledTask

    rep = group[0]
    sel_ids = {t.id for t in group}
    # Target = an unpinned, scheduled sibling of the same WO+step NOT in this selection.
    # Fall back to the earliest selected task when the whole cell is being merged.
    # tenant-safe: schedule/part FKs constrain to the tenant.
    cohort = (
        ScheduledTask.objects
        .filter(schedule=schedule, step_id=step_id,
                part__work_order_id=wo_id, is_pinned=False)
        .exclude(id__in=sel_ids).exclude(part__isnull=True)
        .order_by('start_time').first()
    )
    base = cohort.start_time if cohort else rep.start_time
    machine_id = cohort.machine_id if cohort else rep.machine_id
    # Preview length of the merged lot: one setup + N×cycle (saves the repeated setups).
    # Falls back to each task's own length when the step has no timing.
    sc = _step_setup_cycle(step_id)
    lot_dur = timedelta(minutes=sc[0] + sc[1] * len(group)) if sc else None
    for t in group:
        t.start_time = base
        t.end_time = base + (lot_dur if lot_dur is not None else (t.end_time - t.start_time))
        t.machine_id = machine_id
        t.is_pinned = False  # hand back to the solver — it batches the unpinned cohort
        t.save(update_fields=['start_time', 'end_time', 'machine_id', 'is_pinned'])
    return len(group)


def _break_group(schedule, group, step_id) -> int:
    """Break one WO+step cohort's selected parts into their own sequential, pinned slots
    (separate fixed bars). `group` is pre-sorted by start_time."""
    # Each broken-off part becomes its own lot → pays its own setup: preview length ≈
    # setup + cycle. Falls back to the task's own length without timing.
    sc = _step_setup_cycle(step_id)
    part_dur = timedelta(minutes=sc[0] + sc[1]) if sc else None
    cursor = group[0].start_time
    for t in group:
        dur = part_dur if part_dur is not None else (t.end_time - t.start_time)
        t.start_time = cursor
        t.end_time = cursor + dur
        t.is_pinned = True
        t.save(update_fields=['start_time', 'end_time', 'is_pinned'])
        cursor = t.end_time
    return len(group)


def bulk_reassign_machine(tasks, machine, user=None) -> dict:
    """Reassign several tasks onto `machine` at once (planner override) + pin them, like
    `reassign_machine` applied across a multi-selection. Applies immediately; collects one
    warning per distinct step the machine isn't authored for (never blocks). Marks the
    affected schedule(s) stale. Returns {'changed': int, 'warnings': [str]}."""
    from Tracker.models import StepEquipmentAffinity

    tasks = list(tasks)
    if not tasks:
        return {'changed': 0, 'warnings': []}
    step_ids = {t.step_id for t in tasks}
    eligible_steps = set(
        StepEquipmentAffinity.objects
        .filter(equipment=machine, step_id__in=step_ids)
        .values_list('step_id', flat=True)
    )
    schedules, warned, warnings = {}, set(), []
    with transaction.atomic():
        for t in tasks:
            t.machine = machine
            t.is_pinned = True
            t.save(update_fields=['machine', 'is_pinned'])
            schedules[t.schedule_id] = t.schedule
            if t.step_id not in eligible_steps and t.step_id not in warned:
                warned.add(t.step_id)
                warnings.append(
                    f"{machine.name} isn't an authored machine for '{t.step.name}' — "
                    f"pinned there anyway."
                )
        for sched in schedules.values():
            sched.is_stale = True
            sched.save(update_fields=['is_stale'])
    return {'changed': len(tasks), 'warnings': warnings}


def bulk_reassign_operator(tasks, operator, user=None) -> dict:
    """Assign (or clear, `operator=None`) one operator across several tasks at once —
    manual coverage of a multi-selection. Applies immediately; warns once, listing the
    steps the operator isn't trained for (never blocks). Marks the affected schedule(s)
    stale. Returns {'changed': int, 'warnings': [str]}."""
    tasks = list(tasks)
    if not tasks:
        return {'changed': 0, 'warnings': []}
    warnings = []
    if operator is not None:
        from Tracker.services.training import get_qualified_users_for_step
        steps = {t.step_id: t.step for t in tasks}
        tenant = tasks[0].tenant
        unqualified = {
            step.name
            for sid, step in steps.items()
            if not get_qualified_users_for_step(step, tenant=tenant)
            .filter(pk=operator.pk).exists()
        }
        if unqualified:
            name = operator.get_full_name() or operator.username
            warnings.append(
                f"{name} isn't trained for: {', '.join(sorted(unqualified))} — assigned anyway."
            )
    schedules = {}
    with transaction.atomic():
        for t in tasks:
            t.assigned_operator = operator
            t.save(update_fields=['assigned_operator'])
            schedules[t.schedule_id] = t.schedule
        for sched in schedules.values():
            sched.is_stale = True
            sched.save(update_fields=['is_stale'])
    return {'changed': len(tasks), 'warnings': warnings}


def regroup_batch(tasks, merge: bool, user=None) -> int:
    """Direct-manipulation batch merge / break (Gantt), applied immediately like a drag.

    The batch key is the attribute (work order, step) — the cohort — matching how APS
    tools batch (by attribute/rule, engine-formed), not by hand-picking a target batch:
      `merge=True`  → REJOIN the WO+step cohort: UNPIN the parts so the solver batches
                      them with their cohort, and snap them onto the cohort's existing slot
                      (or the earliest selected, if the whole cell is selected) so the
                      cell collapses immediately. The solver forms the final batch on the
                      next Solve.
      `merge=False` → break the parts into their own sequential slots, PINNED → separate
                      fixed bars now. They stay apart while pinned; merge (unpin) hands
                      them back to the solver.

    A multi-select can span several WO+step cohorts (e.g. dragging a box over bars from
    two work orders); the selection is grouped by cohort and each group merges into — or
    breaks out of — its OWN cohort, never collapsed across work orders. Marks the
    schedule stale; the next Solve re-optimizes (soft pins). Cores are skipped (they carry
    no lot). Returns the number of tasks changed.
    """
    tasks = [t for t in tasks if t.part_id]  # cores carry no lot membership
    if not tasks:
        return 0
    schedule = tasks[0].schedule

    # Group the selection by cohort (work order + step) so a mixed multi-select stays
    # coherent — each cohort is regrouped independently.
    grouped: dict[tuple, list] = {}
    for t in tasks:
        grouped.setdefault((t.part.work_order_id, t.step_id), []).append(t)

    changed = 0
    with transaction.atomic():
        for (wo_id, step_id), group in grouped.items():
            group.sort(key=lambda t: t.start_time)
            if merge:
                changed += _merge_group(schedule, group, wo_id, step_id)
            else:
                changed += _break_group(schedule, group, step_id)
        schedule.is_stale = True
        schedule.save(update_fields=['is_stale'])
    return changed
