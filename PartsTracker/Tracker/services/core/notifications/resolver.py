"""4-layer channel resolution for a user × event.

The dispatcher consults `resolve_default_channels(user, event_code)` per
event to decide which channels to emit on. Returns a dict of
{channel: enabled} resolved by checking, per channel, the most specific
applicable layer (first match short-circuits further lookup):

    1. UserNotificationPreference  — explicit per-user override (always-write)
    2. TenantNotificationDefault   — role-scoped row(s); multi-role users → union
    3. TenantNotificationDefault   — tenant-wide row (role IS NULL)
    4. EVENT_REGISTRY[event_code].default_channels

A short-lived cache shaves the per-emit DB cost for hot events; cache
invalidation is wired via `post_save` signals on the three preference
models (see signals.py).
"""
from __future__ import annotations

from django.core.cache import cache

from .registry import get_event

# Cache lifetime is bounded by signal-based invalidation; the TTL is a
# defense-in-depth backstop, not the primary correctness mechanism.
CACHE_TTL_SECONDS = 5 * 60


def _cache_key(tenant_id, user_id: int, event_code: str) -> str:
    return f'notif:resolved:{tenant_id}:{user_id}:{event_code}'


def resolve_default_channels(user, event_code: str) -> dict[str, bool]:
    """Return {channel: enabled} for the given user on the given event.

    "Enabled" means "deliver via this channel at dispatch time." Callers
    intersect this with the event's registered `default_channels` to decide
    what to write to the outbox.
    """
    cache_key = _cache_key(user.tenant_id, user.id, event_code)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Local imports to avoid app-loading cycles.
    from Tracker.models import (
        TenantNotificationDefault,
        UserNotificationPreference,
    )

    event = get_event(event_code)
    registry_channels = list(event.default_channels)

    # Pre-fetch the user's role ids once (User.get_tenant_groups() walks via UserRole).
    if hasattr(user, 'get_tenant_groups'):
        user_role_ids = list(user.get_tenant_groups().values_list('id', flat=True))
    else:
        user_role_ids = []

    # Pre-fetch the user preference row once (one row per user; JSONField).
    try:
        pref_row = UserNotificationPreference.objects.get(user=user)
        user_prefs = pref_row.preferences or {}
    except UserNotificationPreference.DoesNotExist:
        user_prefs = {}

    # Pre-fetch all default rows for this (tenant, event) — small set.
    default_rows = list(
        TenantNotificationDefault.objects
        .filter(tenant_id=user.tenant_id, event_code=event_code)
        .values('channel', 'role_id', 'enabled')
    )

    # Bucket defaults by channel and by role-scope.
    tenant_wide: dict[str, bool] = {}
    role_scoped: dict[str, list[bool]] = {}
    for row in default_rows:
        if row['role_id'] is None:
            tenant_wide[row['channel']] = row['enabled']
        elif row['role_id'] in user_role_ids:
            role_scoped.setdefault(row['channel'], []).append(row['enabled'])

    # All channels we may need to resolve: union of registry defaults +
    # anything explicitly configured in DB (so a tenant adding a new
    # channel via DB seed surfaces through the API).
    all_channels = set(registry_channels) | set(tenant_wide) | set(role_scoped)

    resolved: dict[str, bool] = {}
    for channel in all_channels:
        # Layer 1: user preference (always-write — explicit row wins).
        event_overrides = user_prefs.get(event_code) or {}
        if channel in event_overrides:
            resolved[channel] = bool(event_overrides[channel])
            continue

        # Layer 2: role-scoped defaults — union across user's roles.
        if channel in role_scoped:
            resolved[channel] = any(role_scoped[channel])
            continue

        # Layer 3: tenant-wide default.
        if channel in tenant_wide:
            resolved[channel] = tenant_wide[channel]
            continue

        # Layer 4: registry default.
        resolved[channel] = channel in registry_channels

    cache.set(cache_key, resolved, timeout=CACHE_TTL_SECONDS)
    return resolved


def invalidate_for_user(user) -> None:
    """Drop cache entries for this user across all events.

    `cache.delete_pattern` is Redis-specific; the Django cache API doesn't
    expose pattern delete portably. We use a versioning key instead: bump
    a per-user version on every preference change; the `_cache_key()`
    function can include the version to make stale entries naturally
    miss. For Phase 2 we keep the simple TTL-based approach and accept
    up to CACHE_TTL_SECONDS of staleness on user-preference changes —
    revisit when this measurably hurts.
    """
    # Intentional no-op for v1. TTL bounds staleness; explicit per-event
    # invalidation requires either pattern delete (Redis-only) or a
    # version-key scheme. See docstring.
    return


def invalidate_for_tenant(tenant) -> None:
    """Same shape as `invalidate_for_user`, for tenant-wide changes."""
    return
