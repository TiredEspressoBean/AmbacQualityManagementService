"""Capture execution actuals onto the schedule (capture-only).

When a part/core enters or exits a step, stamp the matching active-schedule
`ScheduledTask` with the real start/end. This is planned-vs-actual data for the
board and variance reporting — it deliberately does NOT re-time the plan or mark
the schedule stale: the solver already pins in-progress ops at solve time, and
routine step advances are intentionally not a re-solve trigger (see the reactive
signals in `Tracker/signals.py`).
"""
from __future__ import annotations


def record_execution_actuals(step_execution) -> None:
    """Stamp `actual_start` / `actual_end` on the live schedule's task for this
    part/core + step, from the StepExecution's entry/exit times.

    No-op when there is no live schedule or no matching task. Bulk `.update()`
    (so no ScheduledTask post_save / auditlog / staleness) — capture only.
    """
    from Tracker.models.scheduling import ScheduledTask

    tenant_id = step_execution.tenant_id
    if not tenant_id or not step_execution.step_id:
        return
    if not step_execution.part_id:
        return
    unit = {'part_id': step_execution.part_id}

    # all_tenants + explicit tenant_id: fired from a signal, so the tenant
    # ContextVar isn't set. Only the live committed schedule carries actuals —
    # drafts are what-ifs. A revisit (rework) overwrites with the latest times.
    live = ScheduledTask.all_tenants.filter(
        tenant_id=tenant_id, step_id=step_execution.step_id,
        schedule__is_active=True, schedule__is_draft=False, **unit,
    )
    live.update(
        actual_start=step_execution.entered_at,
        actual_end=step_execution.exited_at,
    )
    # Freeze the plan as it stood when the op started: the task in the schedule that was
    # live at its start, which a re-solve since may have replaced — a running op is
    # re-pinned at "now" with a new end, and the finish is judged against the old one.
    if step_execution.entered_at is not None:
        started_on = (ScheduledTask.all_tenants
                      .filter(tenant_id=tenant_id, step_id=step_execution.step_id,
                              schedule__is_draft=False,
                              schedule__created_at__lte=step_execution.entered_at, **unit)
                      .order_by('-schedule__created_at')
                      .values('start_time', 'end_time').first())
        if started_on is None:
            # Started before any plan had it (or the plan was solved after): the live one.
            started_on = live.values('start_time', 'end_time').first()
        if started_on is not None:
            live.filter(planned_end_at_start__isnull=True).update(
                planned_start_at_start=started_on['start_time'],
                planned_end_at_start=started_on['end_time'])


def carry_running_actuals(schedule) -> None:
    """After a re-solve: a task the solver marked running (`in_progress`) gets its real
    start, and the plan it started on, from the schedule it ran under — otherwise the new
    task has no actuals until the op finishes, and plan-vs-actual loses it meanwhile."""
    from Tracker.models.scheduling import ScheduledTask

    for task in ScheduledTask.all_tenants.filter(  # tenant-safe: one schedule's own rows
            schedule=schedule, in_progress=True, part_id__isnull=False):
        prior = (ScheduledTask.all_tenants
                 .filter(tenant_id=task.tenant_id, part_id=task.part_id, step_id=task.step_id,
                         schedule__is_draft=False, actual_start__isnull=False)
                 .exclude(schedule=schedule)
                 .order_by('-schedule__created_at')
                 .values('actual_start', 'planned_start_at_start', 'planned_end_at_start')
                 .first())
        if prior is None:
            continue
        ScheduledTask.all_tenants.filter(pk=task.pk).update(  # tenant-safe: by pk of a scoped row
            actual_start=prior['actual_start'],
            planned_start_at_start=prior['planned_start_at_start'],
            planned_end_at_start=prior['planned_end_at_start'])
