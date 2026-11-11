"""
LifeTracking aggregate services.

Increment usage, reset after overhaul, or apply per-instance
engineering overrides to service limits.
"""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from Tracker.models import LifeTracking


def amount(value) -> str:
    """A count or limit as people write it: 2, 2.5 — not 2.00."""
    if value is None:
        return ''
    text = f"{Decimal(str(value)).normalize():f}"
    return text


def carried_count(obj, definition):
    """What `obj` has used against earlier versions of `definition`: the newest earlier
    version's tracking's count, or None. A revised limit (raised, say) is the same
    limit, so its count carries over rather than starting again from zero."""
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(obj)
    previous = definition.previous_version
    while previous is not None:
        old = LifeTracking.objects.filter(  # tenant-safe: generic FK to a scoped object
            content_type=ct, object_id=obj.pk, definition=previous).first()
        if old is not None:
            return old.accumulated
        previous = previous.previous_version
    return None


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
        # Shown on the item's Life section ("reset by … — why").
        'by': (user.get_full_name() or user.get_username()) if user else '',
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
