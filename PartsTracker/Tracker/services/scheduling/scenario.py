"""What-if scenarios (Phase 5).

A solve can produce a **draft** schedule the planner reviews against the live one,
then **commits** (promotes it to the active schedule, superseding the old one) or
**discards** it. The live schedule is never disturbed until commit — the market's
top APS ask. Cross-aggregate state changes live here, not in the viewset.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction


def _latest_draft(tenant):
    from Tracker.models.scheduling import ScheduleResult
    return (ScheduleResult.objects.filter(archived=False, tenant=tenant, is_draft=True)
            .order_by('-created_at').first())


def _active(tenant):
    from Tracker.models.scheduling import ScheduleResult
    return (ScheduleResult.objects.filter(archived=False, tenant=tenant, is_active=True)
            .order_by('-created_at').first())


def commit_draft(tenant):
    """Promote the current draft to the live schedule, superseding the previous live
    one. Returns the promoted ScheduleResult, or None when there's no draft."""
    from Tracker.models.scheduling import ScheduleResult

    draft = _latest_draft(tenant)
    if draft is None:
        return None
    with transaction.atomic():
        live = _active(tenant)
        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
            is_active=False, is_stale=True)
        # Any stray older drafts are dropped on commit (scratch, cascade-deletes tasks).
        ScheduleResult.objects.filter(tenant=tenant, is_draft=True).exclude(pk=draft.pk).delete()
        draft.is_draft = False
        draft.is_active = True
        draft.is_stale = False
        draft.superseded = live
        draft.save(update_fields=['is_draft', 'is_active', 'is_stale', 'superseded'])
    return draft


def restore_previous(tenant, user, reason: str):
    """A what-if committed by mistake: the live schedule it replaced goes live again,
    and the committed one goes back to being a draft to review (user decision
    2026-10-26, Corrections #38). One step back only. The reason is kept as an edit of
    the restored schedule's `is_active`.

    Raises ValueError when there's nothing to restore, or no reason."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    from Tracker.models.scheduling import ScheduleResult

    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Say why the previous plan is being restored.")
    with transaction.atomic():
        live = _active(tenant)
        previous = live.superseded if live is not None else None
        if previous is None or previous.archived:
            raise ValueError("The live schedule wasn't committed over another one — there's "
                             "no previous plan to restore.")
        if _latest_draft(tenant) is not None:
            raise ValueError("A what-if draft is waiting — commit or discard it first.")
        RecordEdit.objects.create(
            tenant=tenant, content_type=ContentType.objects.get_for_model(ScheduleResult),
            object_id=previous.id, field_name='is_active', old_value='False', new_value='True',
            reason=reason, edited_by=user)
        live.is_active = False
        live.is_draft = True
        live.superseded = None  # one step back: the restored plan isn't undone again
        live.save(update_fields=['is_active', 'is_draft', 'superseded'])
        previous.is_active = True
        previous.is_stale = False
        # One step back: restoring again would reach further into the past.
        previous.superseded = None
        previous.save(update_fields=['is_active', 'is_stale', 'superseded'])
    return previous


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
        # Both solves stop within a proven gap of optimal; a difference smaller than
        # that may be the solver, not the change — the comparison shows it.
        'relative_gap': sched.relative_gap,
        'weighted_lateness': sched.weighted_lateness,
        'makespan_minutes': makespan,
        'task_count': len(tasks),
        'uncovered': uncovered,
    }


def _moved_task_count(live, draft) -> int:
    """Tasks the draft reschedules vs live — matched by unit+step, counting a change
    of start time or machine (and any task the draft adds).

    A start counts as changed only past the gap between the two solves' horizon starts
    (plus a minute): both are anchored on "now", so a draft solved two minutes after
    live shifts every early task by those minutes without anyone moving it. Counting
    that jitter reported every task on the board as moved."""
    def key(t):
        return (t.part_id, t.step_id)

    slack = abs(draft.horizon_start - live.horizon_start) + timedelta(minutes=1)
    live_map = {key(t): t for t in live.tasks.all()}
    moved = 0
    for t in draft.tasks.all():
        prev = live_map.get(key(t))
        if (prev is None or prev.machine_id != t.machine_id
                or abs(prev.start_time - t.start_time) > slack):
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
