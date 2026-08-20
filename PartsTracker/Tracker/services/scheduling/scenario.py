"""What-if scenarios (Phase 5).

A solve can produce a **draft** schedule the planner reviews against the live one,
then **commits** (promotes it to the active schedule, superseding the old one) or
**discards** it. The live schedule is never disturbed until commit — the market's
top APS ask. Cross-aggregate state changes live here, not in the viewset.
"""
from __future__ import annotations

from django.db import transaction


def _latest_draft(tenant):
    from Tracker.models.scheduling import ScheduleResult
    return (ScheduleResult.objects.filter(tenant=tenant, is_draft=True)
            .order_by('-created_at').first())


def _active(tenant):
    from Tracker.models.scheduling import ScheduleResult
    return (ScheduleResult.objects.filter(tenant=tenant, is_active=True)
            .order_by('-created_at').first())


def commit_draft(tenant):
    """Promote the current draft to the live schedule, superseding the previous live
    one. Returns the promoted ScheduleResult, or None when there's no draft."""
    from Tracker.models.scheduling import ScheduleResult

    draft = _latest_draft(tenant)
    if draft is None:
        return None
    with transaction.atomic():
        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
            is_active=False, is_stale=True)
        # Any stray older drafts are dropped on commit (scratch, cascade-deletes tasks).
        ScheduleResult.objects.filter(tenant=tenant, is_draft=True).exclude(pk=draft.pk).delete()
        draft.is_draft = False
        draft.is_active = True
        draft.is_stale = False
        draft.save(update_fields=['is_draft', 'is_active', 'is_stale'])
    return draft


def discard_draft(tenant) -> int:
    """Delete the current draft(s) — scratch data, cascade-deletes their tasks.
    Returns how many schedules were removed."""
    from Tracker.models.scheduling import ScheduleResult
    n, _ = ScheduleResult.objects.filter(tenant=tenant, is_draft=True).delete()
    return n


def _summarize(sched) -> dict | None:
    if sched is None:
        return None
    tasks = list(sched.tasks.all())
    if tasks:
        makespan = int(
            (max(t.end_time for t in tasks) - min(t.start_time for t in tasks)).total_seconds() // 60
        )
    else:
        makespan = 0
    uncovered = sum(1 for t in tasks if t.requires_operator and t.assigned_operator_id is None)
    return {
        'schedule_id': str(sched.id),
        'solver_status': sched.solver_status,
        'weighted_lateness': sched.weighted_lateness,
        'makespan_minutes': makespan,
        'task_count': len(tasks),
        'uncovered': uncovered,
    }


def _moved_task_count(live, draft) -> int:
    """Tasks the draft reschedules vs live — matched by unit+step, counting a change
    of start time or machine (and any task the draft adds)."""
    def key(t):
        return (t.part_id, t.core_id, t.step_id)

    live_map = {key(t): t for t in live.tasks.all()}
    moved = 0
    for t in draft.tasks.all():
        prev = live_map.get(key(t))
        if prev is None or prev.start_time != t.start_time or prev.machine_id != t.machine_id:
            moved += 1
    return moved


def compare_draft(tenant) -> dict:
    """Live vs draft: each schedule's summary plus how many tasks the draft moves."""
    live = _active(tenant)
    draft = _latest_draft(tenant)
    return {
        'live': _summarize(live),
        'draft': _summarize(draft),
        'moved': _moved_task_count(live, draft) if (live and draft) else 0,
    }
