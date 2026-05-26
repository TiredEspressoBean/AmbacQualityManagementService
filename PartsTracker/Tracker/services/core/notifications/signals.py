"""Django signal handlers for the notification system.

- `post_save` on Tenant → seed tenant-wide notification defaults
- `post_save` / `post_delete` on TenantNotificationDefault → invalidate resolver cache
- `post_save` / `post_delete` on UserNotificationPreference → invalidate resolver cache
- `post_save` on TenantNotificationBranding → no cache impact (read at render time)

Imported by `Tracker.services.core.notifications.dispatcher` so registration
runs at app startup via the existing apps.ready() chain.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _connect():
    """Late binding — connect signals after models are loaded.

    Called from `apps.ready()` via the dispatcher module import chain.
    """
    from Tracker.models import (
        Tenant,
        TenantNotificationDefault,
        UserNotificationPreference,
    )
    from .seeder import seed_tenant_notification_defaults
    from .resolver import invalidate_for_tenant, invalidate_for_user

    @receiver(post_save, sender=Tenant)
    def _seed_on_tenant_create(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            count = seed_tenant_notification_defaults(instance)
            logger.info(
                'notification seeder: created %d tenant-wide default rows for tenant %s',
                count, instance.id,
            )
        except Exception:
            logger.exception('notification seeder failed for tenant %s', instance.id)

    @receiver([post_save, post_delete], sender=TenantNotificationDefault)
    def _invalidate_on_tenant_default_change(sender, instance, **kwargs):
        invalidate_for_tenant(instance.tenant)

    @receiver([post_save, post_delete], sender=UserNotificationPreference)
    def _invalidate_on_user_preference_change(sender, instance, **kwargs):
        invalidate_for_user(instance.user)


_connect()
