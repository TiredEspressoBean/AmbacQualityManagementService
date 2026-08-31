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
    if step_execution.part_id:
        unit = {'part_id': step_execution.part_id}
    elif step_execution.core_id:
        unit = {'core_id': step_execution.core_id}
    else:
        return

    # all_tenants + explicit tenant_id: fired from a signal, so the tenant
    # ContextVar isn't set. Only the live committed schedule carries actuals —
    # drafts are what-ifs. A revisit (rework) overwrites with the latest times.
    ScheduledTask.all_tenants.filter(
        tenant_id=tenant_id, step_id=step_execution.step_id,
        schedule__is_active=True, schedule__is_draft=False, **unit,
    ).update(
        actual_start=step_execution.entered_at,
        actual_end=step_execution.exited_at,
    )
