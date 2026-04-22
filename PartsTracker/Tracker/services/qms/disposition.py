"""
QuarantineDisposition aggregate services.

Complete-resolution flow. Part-status side effects currently live in
`QuarantineDisposition.save()` (via `_update_part_status`) and stay
there for now; this service only handles the top-level close.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import QuarantineDisposition


def complete_disposition_resolution(
    disposition: QuarantineDisposition,
    user,
) -> QuarantineDisposition:
    """Mark resolution as completed and close the disposition if in progress.

    Raises:
        ValueError: blockers exist (pending annotations, etc.).
    """
    blockers = disposition.get_completion_blockers()
    if blockers:
        raise ValueError(
            f"Cannot complete disposition: {'; '.join(blockers)}"
        )

    disposition.resolution_completed = True
    disposition.resolution_completed_by = user
    disposition.resolution_completed_at = timezone.now()

    if disposition.current_state == 'IN_PROGRESS':
        disposition.current_state = 'CLOSED'

    disposition.save()
    return disposition
