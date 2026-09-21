"""Undo for direct manipulation of the board.

Before rippling, every Gantt edit was self-reversing: a drag moved one bar and dragging
it back restored it. A cascade breaks that — one drag can move a dozen downstream
operations, and no planner can reconstruct twelve positions by hand.

So each edit records the prior state of every task it touched, and undo puts them back.
Scoped to the schedule, most-recent-first, and an undone edit is marked rather than
deleted: what somebody tried is part of the record.

Undo restores POSITIONS, not the solver's opinion. The schedule stays stale afterwards,
because reversing a manual edit does not re-derive the plan any more than making one did.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class NothingToUndo(Exception):
    """No un-undone edit on this schedule."""


def record_edit(schedule, tasks, *, user=None, kind: str) -> None:
    """Snapshot `tasks` as they are ON DISK, before the caller's writes land.

    Called inside the caller's transaction with the in-memory objects already mutated —
    their rows are not, so a fresh read is exactly the prior state. That is the whole
    trick, and it is why this must be called before `save()` rather than after.
    """
    from Tracker.models.scheduling import ScheduledTask, ScheduleEdit

    ids = [t.id for t in tasks if t.id]
    if not ids:
        return
    # tenant-safe: explicit tenant filter
    prior = (ScheduledTask.objects.filter(tenant=schedule.tenant, id__in=ids)
             .values('id', 'start_time', 'end_time', 'is_pinned'))
    payload = [{
        'task': str(r['id']),
        'start_time': r['start_time'].isoformat() if r['start_time'] else None,
        'end_time': r['end_time'].isoformat() if r['end_time'] else None,
        'is_pinned': r['is_pinned'],
    } for r in prior]
    if not payload:
        return
    ScheduleEdit.objects.create(
        tenant=schedule.tenant, schedule=schedule, kind=kind,
        payload=payload, created_by=user)


def last_undoable(schedule):
    """The most recent edit on this schedule that has not been undone, or None."""
    from Tracker.models.scheduling import ScheduleEdit
    # tenant-safe: reverse FK from an in-tenant ScheduleResult.
    return schedule.edits.filter(undone_at__isnull=True).order_by('-created_at').first()


def undo_last(schedule, *, user=None) -> dict:
    """Reverse the most recent edit. Returns `{kind, task_count}`.

    Tasks that no longer exist are skipped rather than failing the undo: a solve between
    the edit and the undo replaces the task rows wholesale, so some ids in an older
    payload may be gone. Restoring the ones that remain is better than refusing — and
    the schedule is marked stale either way, so the next solve reconciles.
    """
    from Tracker.models.scheduling import ScheduledTask

    edit = last_undoable(schedule)
    if edit is None:
        raise NothingToUndo("Nothing to undo on this schedule.")

    restored = 0
    with transaction.atomic():
        for row in (edit.payload or []):
            # tenant-safe: explicit tenant filter
            task = ScheduledTask.objects.filter(
                tenant=schedule.tenant, id=row['task']).first()
            if task is None:
                continue
            # Parse back to datetimes. Django would accept the ISO strings on the way
            # to the database, but the in-memory instance would keep them — and the
            # next `str(task)` (auditlog does one on every save) formats start_time
            # with a datetime spec and dies on a str.
            task.start_time = parse_datetime(row['start_time']) if row['start_time'] else None
            task.end_time = parse_datetime(row['end_time']) if row['end_time'] else None
            task.is_pinned = row['is_pinned']
            task.save(update_fields=['start_time', 'end_time', 'is_pinned'])
            restored += 1

        edit.undone_at = timezone.now()
        edit.save(update_fields=['undone_at'])
        schedule.is_stale = True
        schedule.save(update_fields=['is_stale'])

    return {'kind': edit.kind, 'task_count': restored}
