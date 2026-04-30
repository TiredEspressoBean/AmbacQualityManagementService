"""
StepOverride aggregate services.

Covers the override-approval workflow: approve / reject a pending
override on a StepExecution. The viewset actions (and the model
methods, kept as thin delegates) funnel through here so status-gate
checks and expiry computation live in one place.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import OverrideStatus, StepOverride


def approve_step_override(
    override: StepOverride,
    user,
    expiry_hours: int | None = None,
) -> StepOverride:
    """Approve a pending override.

    If `expiry_hours` is not supplied, fall back to the step's
    `override_expiry_hours` (default 24).

    Raises:
        ValueError: override is not in PENDING state.
    """
    if override.status != OverrideStatus.PENDING:
        raise ValueError(
            f"Cannot approve override with status '{override.status}'"
        )

    if expiry_hours is None:
        step = override.step_execution.step if override.step_execution else None
        expiry_hours = getattr(step, 'override_expiry_hours', 24)

    override.status = OverrideStatus.APPROVED
    override.approved_by = user
    override.approved_at = timezone.now()
    override.expires_at = timezone.now() + timedelta(hours=expiry_hours)
    override.save(update_fields=[
        'status', 'approved_by', 'approved_at', 'expires_at',
    ])
    return override


def reject_step_override(
    override: StepOverride,
    user,
    reason: str = '',
) -> StepOverride:
    """Reject a pending override. Appends the reason to the existing
    justification text for audit trail.

    Raises:
        ValueError: override is not in PENDING state.
    """
    if override.status != OverrideStatus.PENDING:
        raise ValueError(
            f"Cannot reject override with status '{override.status}'"
        )

    override.status = OverrideStatus.REJECTED
    override.approved_by = user
    override.approved_at = timezone.now()
    if reason:
        override.reason = f"{override.reason}\n\n[REJECTED]: {reason}"
    override.save(update_fields=[
        'status', 'approved_by', 'approved_at', 'reason',
    ])
    return override


def mark_override_used(override: StepOverride) -> StepOverride:
    """Record that an approved override was consumed.

    Locks the row with SELECT FOR UPDATE inside a transaction so two
    concurrent callers can't both pass the status / expiry checks and
    each think they consumed the override. The first caller commits with
    used=True; the second reads used=True and raises.

    Raises:
        ValueError: override is not APPROVED, is already used, or is
            past expiry (flips status to EXPIRED and persists before
            raising).
    """
    with transaction.atomic():
        locked = StepOverride.unscoped.select_for_update().get(pk=override.pk)
        if locked.status != OverrideStatus.APPROVED:
            raise ValueError("Only approved overrides can be used")
        if locked.used:
            raise ValueError("Override has already been used")
        if locked.expires_at and timezone.now() > locked.expires_at:
            locked.status = OverrideStatus.EXPIRED
            locked.save(update_fields=['status'])
            raise ValueError("Override has expired")

        locked.used = True
        locked.used_at = timezone.now()
        locked.save(update_fields=['used', 'used_at'])
    # Refresh the caller's instance so they see the new state.
    override.refresh_from_db()
    return override
