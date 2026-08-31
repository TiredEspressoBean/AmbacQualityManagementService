"""Periodic auto-resolve eligibility (Tracker/services/scheduling/auto_resolve.py).

The staleness signals flag a drifted schedule; the auto-resolve beat re-solves it
for tenants opted into LIVE mode, past an anti-churn interval. These cover which
tenants the beat picks up, and that it queues one solve each.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Tracker.models import OptimizationConfig, ScheduleResult, Tenant
from Tracker.models.scheduling import AutoResolveMode
from Tracker.services.scheduling.auto_resolve import (
    due_auto_resolve_tenant_ids, run_due_auto_resolves,
)
from Tracker.tests.base import TenantContextMixin


class AutoResolveEligibilityTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="AR", slug="auto-resolve", tier="PRO")
        self.set_tenant_context(self.tenant)

    def _config(self, mode=AutoResolveMode.LIVE, interval=30):
        cfg, _ = OptimizationConfig.objects.update_or_create(
            tenant=self.tenant,
            defaults={'auto_resolve': mode,
                      'auto_resolve_min_interval_minutes': interval})
        return cfg

    def _stale_schedule(self, *, age_minutes=60, is_stale=True):
        now = timezone.now()
        s = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_draft=False, is_stale=is_stale)
        # created_at is auto-set; push it into the past to model "solved a while ago"
        # (update() bypasses auto_now_add).
        ScheduleResult.all_tenants.filter(pk=s.pk).update(
            created_at=now - timedelta(minutes=age_minutes))
        return s

    def test_live_stale_and_past_interval_is_due(self):
        self._config()
        self._stale_schedule(age_minutes=60)
        self.assertIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_off_is_never_due(self):
        self._config(mode=AutoResolveMode.OFF)
        self._stale_schedule(age_minutes=60)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_not_stale_is_not_due(self):
        self._config()
        self._stale_schedule(age_minutes=60, is_stale=False)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_recent_solve_within_interval_not_due(self):
        """Anti-churn: a schedule solved 5 min ago with a 30-min floor waits."""
        self._config(interval=30)
        self._stale_schedule(age_minutes=5)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_default_off_not_due(self):
        """A tenant that never opted in (default OFF / no config) is never picked."""
        self._stale_schedule(age_minutes=60)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_run_due_queues_one_solve_per_tenant(self):
        # Inject a fake queue (the seam) rather than patching the Celery task —
        # patching the registered task corrupts eager-result state for the run.
        self._config()
        self._stale_schedule(age_minutes=60)
        queued = []
        ids = run_due_auto_resolves(queue=queued.append)
        self.assertEqual(ids, [self.tenant.id])
        self.assertEqual(queued, [str(self.tenant.id)])
