"""Labour time entry approval.

A shift lead or production manager signs off the hours clocked on their floor
(`approve_timeentry`). Nobody approves their own time, and an entry still running
(no end time) has no hours to approve yet.
"""
from __future__ import annotations

from django.utils import timezone


def approve_time_entry(entry, user):
    """Approve one time entry. Raises ValueError naming why it can't be."""
    if entry.approved:
        raise ValueError("This time entry is already approved.")
    if entry.end_time is None:
        raise ValueError("This time entry is still running - it can be approved once it ends.")
    if entry.user_id == user.id:
        raise ValueError("You can't approve your own time.")
    entry.approved = True
    entry.approved_by = user
    entry.approved_at = timezone.now()
    entry.save(update_fields=['approved', 'approved_by', 'approved_at', 'updated_at'])
    return entry
