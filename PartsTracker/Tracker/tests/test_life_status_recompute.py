"""Periodic recompute of calendar-based LifeTracking `cached_status`.

Calendar (shelf-life) status is wall-clock-derived; `cached_status` is only
written on save()/increment, so it goes stale as time passes with no write. The
`recompute_life_status` beat task refreshes it so the `.expired()` / `.warning()`
querysets (and their API endpoints) don't miss time-expired records.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from Tracker.models import PartTypes, Tenant
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking
from Tracker.tasks import recompute_life_status
from Tracker.tests.base import TenantContextMixin


class LifeStatusRecomputeTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="LifeR", slug="life-recompute", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Seal")
        self.shelf_def = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Shelf Life", unit="days",
            unit_label="Days", is_calendar_based=True, hard_limit=Decimal("365"),
        )

    def test_recompute_flips_stale_calendar_status_to_expired(self):
        tracking, _ = LifeTracking.for_object(
            self.pt, self.shelf_def,
            reference_date=timezone.now().date() - timedelta(days=400),
        )
        # Simulate staleness: cache says OK though the record is calendar-expired.
        LifeTracking.objects.filter(pk=tracking.pk).update(cached_status="OK")
        result = recompute_life_status()
        tracking.refresh_from_db()
        self.assertEqual(tracking.cached_status, "EXPIRED")
        self.assertEqual(result["updated"], 1)

    def test_recompute_noop_when_cache_fresh(self):
        # Within limit → status OK; cache already OK (set on create) → no update.
        LifeTracking.for_object(
            self.pt, self.shelf_def,
            reference_date=timezone.now().date() - timedelta(days=10),
        )
        result = recompute_life_status()
        self.assertEqual(result["updated"], 0)
