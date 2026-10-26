"""Plan vs actual — did the floor follow the schedule? (Planner track module 8.)

Each operation in the window, judged against the plan as it stood when it started
(`planned_*_at_start`, frozen when the actual start is stamped), never the current
re-solved plan — a re-solve pins a running op at "now" and would hide its slip.

Ops come from every schedule that was live, not only today's: a re-solve books only
the remaining work, so finished ops fall off the live schedule. Three kinds:

- done:    started and finished (actual start and end);
- running: started, not finished;
- missed:  due under the schedule that was live when it fell due, and never started.

Colouring (on time / early / late / very late) is the board's, from a tolerance the
planner sets; this returns the times only.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

MAX_DAYS = 31


def _unit(task) -> dict:
    part = task.part
    wo = part.work_order if part is not None and part.work_order_id else None
    return {
        'part_id': str(task.part_id) if task.part_id else None,
        'part_erp': part.ERP_id if part is not None else None,
        'work_order': wo.ERP_id if wo is not None else None,
        'step_name': task.step.name if task.step_id else None,
        'machine_name': task.machine.name if task.machine_id else None,
        'operator_name': (task.assigned_operator.get_full_name() or task.assigned_operator.username)
                         if task.assigned_operator_id else None,
    }


def adherence_ops(tenant, *, days: int = 7, now=None) -> list[dict]:
    """Every op started, running, or due-and-never-started in the last `days`."""
    from Tracker.models import StepExecution
    from Tracker.models.scheduling import ScheduledTask, ScheduleResult

    now = now or timezone.now()
    since = now - timedelta(days=max(1, min(days, MAX_DAYS)))
    base = (ScheduledTask.objects  # tenant-safe: explicit tenant filter
            .filter(tenant=tenant, schedule__is_draft=False, part_id__isnull=False)
            .select_related('part__work_order', 'step', 'machine', 'assigned_operator', 'schedule'))

    # Started in the window: the latest visit per part and step, a finished row first.
    started: dict[tuple, object] = {}
    for t in base.filter(actual_start__gte=since).order_by('actual_start', 'schedule__created_at'):
        key = (t.part_id, t.step_id)
        held = started.get(key)
        if held is None or t.actual_start > held.actual_start or (
                t.actual_start == held.actual_start and (t.actual_end is not None or held.actual_end is None)):
            started[key] = t

    out = []
    for t in started.values():
        out.append({
            'id': str(t.id), 'state': 'done' if t.actual_end else 'running',
            'planned_start': t.planned_start_at_start or t.start_time,
            'planned_end': t.planned_end_at_start or t.end_time,
            'actual_start': t.actual_start, 'actual_end': t.actual_end,
            **_unit(t),
        })

    # Due and never started: judged by the schedule live when the op fell due — from
    # its creation until the next one replaced it (now, for the live one).
    schedules = list(ScheduleResult.objects  # tenant-safe: explicit tenant filter
                     .filter(tenant=tenant, is_draft=False, created_at__lte=now)
                     .order_by('created_at').values_list('id', 'created_at'))
    entered = set(StepExecution.objects  # tenant-safe: explicit tenant filter
                  .filter(tenant=tenant, part_id__isnull=False, entered_at__lte=now)
                  .values_list('part_id', 'step_id'))
    missed: dict[tuple, object] = {}
    for i, (sid, created) in enumerate(schedules):
        retired = schedules[i + 1][1] if i + 1 < len(schedules) else now
        if retired < since:
            continue
        for t in base.filter(schedule_id=sid, actual_start__isnull=True,
                             end_time__gte=since, end_time__lt=min(retired, now)):
            key = (t.part_id, t.step_id)
            if key in entered or key in started:
                continue
            missed[key] = t   # a later schedule's miss replaces an earlier one
    for t in missed.values():
        out.append({
            'id': str(t.id), 'state': 'missed',
            'planned_start': t.start_time, 'planned_end': t.end_time,
            'actual_start': None, 'actual_end': None,
            **_unit(t),
        })
    return out
