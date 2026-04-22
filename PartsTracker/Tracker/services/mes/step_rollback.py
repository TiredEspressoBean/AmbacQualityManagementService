"""
StepRollback aggregate services.

Approve / reject a part-step rollback request.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import RollbackStatus, StepRollback


def approve_step_rollback(rollback: StepRollback, user) -> StepRollback:
    """Approve a rollback request."""
    rollback.status = RollbackStatus.APPROVED
    rollback.approved_by = user
    rollback.approved_at = timezone.now()
    rollback.save(update_fields=['status', 'approved_by', 'approved_at'])
    return rollback


def reject_step_rollback(rollback: StepRollback, user) -> StepRollback:
    """Reject a rollback request."""
    rollback.status = RollbackStatus.REJECTED
    rollback.approved_by = user
    rollback.approved_at = timezone.now()
    rollback.save(update_fields=['status', 'approved_by', 'approved_at'])
    return rollback
