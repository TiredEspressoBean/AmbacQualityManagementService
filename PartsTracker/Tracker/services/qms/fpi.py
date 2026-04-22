"""
FPI (First Piece Inspection) aggregate services.

Pass / fail / waive flows for FPIRecord.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import FPIRecord, FPIResult, FPIStatus


def pass_fpi(fpi: FPIRecord, user, notes: str = '') -> FPIRecord:
    """Mark FPI as passed."""
    fpi.status = FPIStatus.PASSED
    fpi.result = FPIResult.PASS
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    fpi.save()
    return fpi


def fail_fpi(fpi: FPIRecord, user, notes: str = '') -> FPIRecord:
    """Mark FPI as failed."""
    fpi.status = FPIStatus.FAILED
    fpi.result = FPIResult.FAIL
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    fpi.save()
    return fpi


def waive_fpi(fpi: FPIRecord, user, reason: str) -> FPIRecord:
    """Waive the FPI requirement.

    Raises:
        ValueError: reason shorter than 10 characters.
    """
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Waive reason must be at least 10 characters")
    fpi.status = FPIStatus.WAIVED
    fpi.waived = True
    fpi.waived_by = user
    fpi.waive_reason = reason
    fpi.save()
    return fpi
