"""
LifeTracking aggregate services.

Increment usage, reset after overhaul, or apply per-instance
engineering overrides to service limits.
"""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from Tracker.models import LifeTracking


def increment_life_tracking(tracking: LifeTracking, value) -> LifeTracking:
    """Add to accumulated value. `value` may be negative for corrections."""
    tracking.accumulated += Decimal(str(value))
    tracking.save(update_fields=['accumulated', 'updated_at', 'cached_status'])
    return tracking


def reset_life_tracking(
    tracking: LifeTracking,
    user=None,
    reason: str = '',
) -> LifeTracking:
    """Zero the accumulated value (e.g. after rebuild/overhaul).

    Appends an entry to `reset_history` for audit. django-auditlog also
    captures the change automatically.
    """
    history_entry = {
        'at': timezone.now().isoformat(),
        'from_value': float(tracking.accumulated),
        'reason': reason,
        'user_id': str(user.pk) if user else None,
    }
    tracking.reset_history = tracking.reset_history + [history_entry]
    tracking.accumulated = Decimal('0')
    tracking.source = LifeTracking.Source.RESET
    tracking.save()
    return tracking


def apply_life_override(
    tracking: LifeTracking,
    hard_limit=None,
    soft_limit=None,
    reason: str = '',
    approved_by=None,
) -> LifeTracking:
    """Set per-instance limit overrides (engineering-approved extended service).

    Pass None to clear an override.
    """
    tracking.hard_limit_override = hard_limit
    tracking.soft_limit_override = soft_limit
    tracking.override_reason = reason
    tracking.override_approved_by = approved_by
    tracking.save()
    return tracking
