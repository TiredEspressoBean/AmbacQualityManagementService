"""Tenant seeding for notification defaults.

On tenant creation, walk EVENT_REGISTRY and write one tenant-wide
TenantNotificationDefault row per (event, channel) using the event's
declared `default_channels` to decide `enabled`.

Role-scoped rows (role != NULL) are NOT seeded — those are authored by
admins via the matrix UI's role selector when they want to specialize a
role's defaults beyond the tenant-wide value.
"""
from __future__ import annotations

from django.db import transaction

from .registry import EVENT_REGISTRY


@transaction.atomic
def seed_tenant_notification_defaults(tenant) -> int:
    """Write tenant-wide TenantNotificationDefault rows for every registered
    (event, channel) pair. Idempotent — re-running on the same tenant
    won't duplicate or overwrite existing rows.

    Returns the number of rows created.
    """
    from Tracker.models import TenantNotificationDefault

    # Use `unscoped` because the post_save Tenant signal fires before any
    # request-bound ContextVar is set; auto-scoping would raise.
    existing = set(
        TenantNotificationDefault.unscoped
        .filter(tenant=tenant, role__isnull=True)
        .values_list('event_code', 'channel')
    )

    to_create = []
    for event in EVENT_REGISTRY.values():
        # Anchor on the event's declared default_channels — those are the
        # channels the dispatcher will actually consider for this event.
        # `enabled=True` for channels in default_channels; absent channels
        # don't get a row (resolver falls through to registry default).
        for channel in event.default_channels:
            if (event.code, channel) in existing:
                continue
            to_create.append(TenantNotificationDefault(
                tenant=tenant,
                event_code=event.code,
                channel=channel,
                role=None,
                enabled=event.default_on,
            ))

    if to_create:
        # tenant-safe: each row's tenant FK is set explicitly above; unscoped is used
        # because the post_save Tenant signal fires before request ContextVar is set.
        TenantNotificationDefault.unscoped.bulk_create(to_create, ignore_conflicts=True)
    return len(to_create)
