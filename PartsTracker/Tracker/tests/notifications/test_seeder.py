"""Tenant seeder tests — walking EVENT_REGISTRY into TenantNotificationDefault rows."""
from __future__ import annotations

from django.test import TestCase

from Tracker.models import Tenant, TenantNotificationDefault
from Tracker.services.core.notifications.registry import EVENT_REGISTRY
from Tracker.services.core.notifications.seeder import seed_tenant_notification_defaults
from Tracker.tests.base import TenantContextMixin


def expected_seeded_rows() -> int:
    """Sum of len(default_channels) across all registered events."""
    return sum(len(e.default_channels) for e in EVENT_REGISTRY.values())


class SeederTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        # Tenant.post_save signal already seeds; use a manual tenant created
        # via .unscoped to control the count cleanly.
        self.tenant = Tenant.objects.create(name='Seed Tenant', slug='seed-tenant')
        self.set_tenant_context(self.tenant)

    def test_post_save_signal_seeds_on_tenant_create(self):
        """Creating a Tenant triggers the seeder via post_save."""
        count = TenantNotificationDefault.objects.filter(
            tenant=self.tenant, role__isnull=True,
        ).count()
        self.assertEqual(count, expected_seeded_rows())

    def test_seed_is_idempotent(self):
        """Re-running the seeder on the same tenant adds no new rows."""
        before = TenantNotificationDefault.objects.filter(tenant=self.tenant).count()
        created = seed_tenant_notification_defaults(self.tenant)
        after = TenantNotificationDefault.objects.filter(tenant=self.tenant).count()

        self.assertEqual(created, 0)
        self.assertEqual(before, after)

    def test_seeded_rows_use_default_on_flag(self):
        """Each seeded row's `enabled` mirrors its event's default_on."""
        for event in EVENT_REGISTRY.values():
            for channel in event.default_channels:
                row = TenantNotificationDefault.objects.filter(
                    tenant=self.tenant,
                    event_code=event.code,
                    channel=channel,
                    role__isnull=True,
                ).first()
                self.assertIsNotNone(
                    row,
                    f'missing seeded row for {event.code}/{channel}',
                )
                self.assertEqual(
                    row.enabled, event.default_on,
                    f'{event.code}/{channel}: enabled mismatch',
                )

    def test_seeder_only_writes_tenant_wide_rows(self):
        """No role-scoped rows should be seeded automatically."""
        role_scoped = TenantNotificationDefault.objects.filter(
            tenant=self.tenant, role__isnull=False,
        ).count()
        self.assertEqual(role_scoped, 0)
