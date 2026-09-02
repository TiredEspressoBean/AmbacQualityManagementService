"""Periodic auto-resolve eligibility (Tracker/services/scheduling/auto_resolve.py).

Two independent triggers, and the tests keep them separate:

- **drift** — the staleness signals flagged a schedule the world moved under;
- **the roll** — nothing happened, but the detailed window is anchored at the solve,
  so coverage shrinks with time and work that was beyond it has come into scope.

Both are gated by LIVE mode and the anti-churn interval. `_schedule` therefore
builds a plan with FULL remaining coverage by default, so a test about staleness
isn't quietly also a test about rolling.
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

    def _config(self, mode=AutoResolveMode.LIVE, interval=30, horizon_days=30):
        cfg, _ = OptimizationConfig.objects.update_or_create(
            tenant=self.tenant,
            defaults={'auto_resolve': mode,
                      'auto_resolve_min_interval_minutes': interval,
                      'horizon_days': horizon_days})
        return cfg

    def _stale_schedule(self, *, age_minutes=60, is_stale=True, covers_days=30):
        """An active schedule. `covers_days` is how far its window still reaches from
        NOW — the default leaves full coverage so the roll trigger stays quiet and the
        test isolates staleness."""
        now = timezone.now()
        s = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now,
            horizon_end=now + timedelta(days=covers_days),
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

    def test_not_stale_with_full_coverage_is_not_due(self):
        """Neither trigger firing: nothing drifted, and the window still reaches."""
        self._config()
        self._stale_schedule(age_minutes=60, is_stale=False, covers_days=30)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    # --- the roll ----------------------------------------------------------

    def test_a_rolled_window_is_due_even_though_nothing_went_stale(self):
        """The plan didn't go wrong — it ran out. A 30-day horizon with 5 days left
        has work that entered scope since the solve and nobody scheduled it."""
        self._config(horizon_days=30)
        self._stale_schedule(age_minutes=60, is_stale=False, covers_days=5)
        self.assertIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_coverage_just_above_the_threshold_is_not_due(self):
        """2/3 of 30 days is 20; 25 days of coverage still has room to run."""
        self._config(horizon_days=30)
        self._stale_schedule(age_minutes=60, is_stale=False, covers_days=25)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_widening_the_horizon_rolls_the_plan(self):
        """Coverage is judged against the CONFIGURED window, not the schedule's own
        span — asking for a longer horizon should itself pull the far work in."""
        self._config(horizon_days=30)
        self._stale_schedule(age_minutes=60, is_stale=False, covers_days=28)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

        self._config(horizon_days=90)  # same plan, now falls well short
        self.assertIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_the_roll_still_respects_the_anti_churn_interval(self):
        """A rolled window must not stampede: a plan solved minutes ago waits, so a
        roll landing right after a re-solve doesn't immediately re-solve again."""
        self._config(interval=30, horizon_days=30)
        self._stale_schedule(age_minutes=5, is_stale=False, covers_days=1)
        self.assertNotIn(self.tenant.id, due_auto_resolve_tenant_ids())

    def test_a_rolled_window_is_ignored_when_auto_resolve_is_off(self):
        self._config(mode=AutoResolveMode.OFF, horizon_days=30)
        self._stale_schedule(age_minutes=60, is_stale=False, covers_days=1)
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
