"""
QuarantineDisposition aggregate services.

Complete-resolution flow. Part-status side effects currently live in
`QuarantineDisposition.save()` (via `_update_part_status`) and stay
there for now; this service only handles the top-level close.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from Tracker.models import QuarantineDisposition


def complete_disposition_resolution(
    disposition: QuarantineDisposition,
    user,
) -> QuarantineDisposition:
    """Mark resolution as completed and close the disposition if in progress.

    The blocker check + state mutation + save run inside a transaction
    with SELECT FOR UPDATE so a concurrent writer can't add a new blocker
    (e.g., a fresh quality report) between the check and the save.
    Without this, the disposition could close while a blocker is in flight,
    leaving the parts cascade in `QuarantineDisposition.save()` to act on
    a stale state.

    Raises:
        ValueError: blockers exist (pending annotations, etc.).
    """
    with transaction.atomic():
        # Lock the row so the blocker check below sees a consistent view.
        locked = (
            QuarantineDisposition.unscoped
            .select_for_update()
            .get(pk=disposition.pk)
        )

        blockers = locked.get_completion_blockers()
        if blockers:
            raise ValueError(
                f"Cannot complete disposition: {'; '.join(blockers)}"
            )

        locked.resolution_completed = True
        locked.resolution_completed_by = user
        locked.resolution_completed_at = timezone.now()

        if locked.current_state == 'IN_PROGRESS':
            locked.current_state = 'CLOSED'

        locked.save()

    disposition.refresh_from_db()
    return disposition
