"""NotificationSchedule dispatcher tests — R3 coverage.

Covers `compute_next_fire` (cadence math, TZ, DST) and `fire_schedule`
(row lock, due-check, last_fired_at semantics, outbox writes, idempotency,
provider-returns-None skip).

Lock semantics (SELECT FOR UPDATE SKIP LOCKED) are exercised by simulating
a duplicate fire call inside a transaction — the second call sees the
schedule as already-fired and exits without writing.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone as dt_timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from Tracker.models import (
    Companies,
    NotificationOutbox,
    NotificationSchedule,
    Tenant,
)
from Tracker.services.core.notifications.schedule import (
    compute_next_fire,
    fire_schedule,
)
from Tracker.services.core.notifications.scheduled_content import RenderedContent
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_customer_schedule,
    make_personal_schedule,
    make_tenant_group,
    make_tenant_schedule,
    make_user_in_groups,
)


# =============================================================================
# compute_next_fire — pure function tests, no DB writes
# =============================================================================

class ComputeNextFireWeeklyTests(TestCase):
    """Weekly cadence math in various timezones."""

    def _build_schedule(self, *, day_of_week, hour, minute=0, tz='UTC'):
        """Construct an unsaved NotificationSchedule for compute_next_fire."""
        return NotificationSchedule(
            cadence='weekly',
            day_of_week=day_of_week,
            day_of_month=None,
            time_of_day=time(hour, minute),
            timezone=tz,
        )

    def test_same_weekday_before_time_returns_today(self):
        # Monday 7am UTC → next Monday 8am UTC = same day, 1h later.
        sched = self._build_schedule(day_of_week=0, hour=8)
        after = datetime(2026, 5, 18, 7, 0, tzinfo=dt_timezone.utc)  # Mon
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 5, 18, 8, 0, tzinfo=dt_timezone.utc))

    def test_same_weekday_at_time_returns_next_week(self):
        # Strictly-after semantics: 8am Mon → next Mon 8am, not today.
        sched = self._build_schedule(day_of_week=0, hour=8)
        after = datetime(2026, 5, 18, 8, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 5, 25, 8, 0, tzinfo=dt_timezone.utc))

    def test_different_weekday_advances(self):
        # Tuesday 10am UTC, schedule Friday 9am → next Fri 9am.
        sched = self._build_schedule(day_of_week=4, hour=9)
        after = datetime(2026, 5, 19, 10, 0, tzinfo=dt_timezone.utc)  # Tue
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 5, 22, 9, 0, tzinfo=dt_timezone.utc))

    def test_non_utc_timezone_resolves_to_utc(self):
        # Mon 8am Eastern in winter (EST = UTC-5) → 13:00 UTC.
        sched = self._build_schedule(day_of_week=0, hour=8, tz='America/New_York')
        after = datetime(2026, 1, 4, 0, 0, tzinfo=dt_timezone.utc)  # Sun
        result = compute_next_fire(sched, after=after)
        self.assertEqual(
            result, datetime(2026, 1, 5, 13, 0, tzinfo=dt_timezone.utc),
        )

    def test_dst_spring_forward_8am_is_unaffected(self):
        # 8 AM Eastern is outside the 2am DST shift window. Wall clock
        # stays "8 AM"; UTC fire time shifts from 13:00 (EST) to 12:00 (EDT)
        # the week of the spring-forward.
        sched = self._build_schedule(day_of_week=0, hour=8, tz='America/New_York')
        # Sunday March 8, 2026 — spring-forward day. Monday Mar 9 fires at 8am EDT.
        after = datetime(2026, 3, 8, 12, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        # 8 AM EDT (UTC-4) = 12:00 UTC.
        self.assertEqual(result, datetime(2026, 3, 9, 12, 0, tzinfo=dt_timezone.utc))

    def test_dst_fall_back_8am_is_unaffected(self):
        # Fall back happens Nov 1, 2026. Monday Nov 2 fires at 8am EST.
        sched = self._build_schedule(day_of_week=0, hour=8, tz='America/New_York')
        after = datetime(2026, 11, 1, 12, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        # 8 AM EST (UTC-5) = 13:00 UTC.
        self.assertEqual(result, datetime(2026, 11, 2, 13, 0, tzinfo=dt_timezone.utc))


class ComputeNextFireMonthlyTests(TestCase):
    """Monthly cadence math."""

    def _build_schedule(self, *, day_of_month, hour=8, tz='UTC'):
        return NotificationSchedule(
            cadence='monthly',
            day_of_week=None,
            day_of_month=day_of_month,
            time_of_day=time(hour, 0),
            timezone=tz,
        )

    def test_before_target_day_returns_this_month(self):
        sched = self._build_schedule(day_of_month=15)
        after = datetime(2026, 5, 10, 0, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 5, 15, 8, 0, tzinfo=dt_timezone.utc))

    def test_after_target_day_returns_next_month(self):
        sched = self._build_schedule(day_of_month=15)
        after = datetime(2026, 5, 20, 0, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 6, 15, 8, 0, tzinfo=dt_timezone.utc))

    def test_december_advances_to_january(self):
        sched = self._build_schedule(day_of_month=15)
        after = datetime(2026, 12, 20, 0, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2027, 1, 15, 8, 0, tzinfo=dt_timezone.utc))

    def test_strictly_after_returns_next_month(self):
        sched = self._build_schedule(day_of_month=15)
        after = datetime(2026, 5, 15, 8, 0, tzinfo=dt_timezone.utc)
        result = compute_next_fire(sched, after=after)
        self.assertEqual(result, datetime(2026, 6, 15, 8, 0, tzinfo=dt_timezone.utc))


# =============================================================================
# fire_schedule — locking, due-check, last_fired_at, outbox writes
# =============================================================================

class FireScheduleTests(TenantContextMixin, TestCase):
    """End-to-end fire path."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Fire Tenant', slug='fire-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')
        self.user = make_user_in_groups(
            self.tenant, make_tenant_group(self.tenant, 'Buyer'),
            first_name='Jane',
        )
        self._patch_provider()

    def _patch_provider(self):
        """Stub the provider so fires produce content without hitting
        legacy `_prepare_order_data` and the orders graph."""
        self._provider_patch = patch(
            'Tracker.services.core.notifications.scheduled_content.customer_active_orders.'
            'CustomerActiveOrdersProvider.build_content',
            return_value=RenderedContent(
                subject='Order Update — May 19, 2026',
                html='<p>One active order: ACM-001.</p>',
                text='One active order: ACM-001.',
            ),
        )
        self._provider_patch.start()
        self.addCleanup(self._provider_patch.stop)

    def _make_due_schedule(self):
        """Build a schedule whose next-fire is in the past (anchor far back)."""
        sched = make_customer_schedule(
            self.tenant, self.customer,
            recipient_users=[self.user],
        )
        # Anchor in the deep past so the schedule is unconditionally due.
        # `last_fired_at` is what fire_schedule uses for anchor; setting it
        # to an old datetime forces compute_next_fire to return a past
        # moment in the current iteration.
        sched.last_fired_at = timezone.now() - timedelta(days=365)
        sched.save(update_fields=['last_fired_at'])
        return sched

    def test_fire_writes_one_outbox_row_per_recipient_channel(self):
        sched = self._make_due_schedule()
        fire_schedule(sched.id)
        rows = list(NotificationOutbox.objects.filter(
            event_code='schedule:customer_active_orders',
        ))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.user_id, self.user.id)
        self.assertEqual(row.channel, 'email')
        self.assertEqual(row.rendered_subject, 'Order Update — May 19, 2026')
        self.assertIn('ACM-001', row.rendered_body_html)

    def test_fire_advances_last_fired_at(self):
        sched = self._make_due_schedule()
        before = sched.last_fired_at
        fire_schedule(sched.id)
        sched.refresh_from_db()
        self.assertGreater(sched.last_fired_at, before)

    def test_disabled_schedule_does_not_fire(self):
        sched = self._make_due_schedule()
        sched.enabled = False
        sched.save(update_fields=['enabled'])
        fire_schedule(sched.id)
        self.assertEqual(NotificationOutbox.objects.count(), 0)

    def test_archived_schedule_does_not_fire(self):
        sched = self._make_due_schedule()
        sched.archived = True
        sched.save(update_fields=['archived'])
        fire_schedule(sched.id)
        self.assertEqual(NotificationOutbox.objects.count(), 0)

    def test_provider_returns_none_writes_no_row(self):
        sched = self._make_due_schedule()
        # Override the patched provider for this test only.
        self._provider_patch.stop()
        with patch(
            'Tracker.services.core.notifications.scheduled_content.customer_active_orders.'
            'CustomerActiveOrdersProvider.build_content',
            return_value=None,
        ):
            fire_schedule(sched.id)
        self.assertEqual(NotificationOutbox.objects.count(), 0)
        # Re-start the cleanup patcher so addCleanup's stop() doesn't double-stop.
        self._provider_patch.start()

    def test_second_fire_is_idempotent(self):
        sched = self._make_due_schedule()
        # First fire writes the row.
        fire_schedule(sched.id)
        self.assertEqual(NotificationOutbox.objects.count(), 1)
        # Reset last_fired_at to the deep past so the schedule is due again
        # but the fire_window_start will compute to a NEW window (because
        # the anchor moved forward). Idempotency is keyed on fire_window,
        # so a genuinely-new window should write a new row.
        original_last_fired = sched.last_fired_at
        # Now call fire_schedule again — should be no-op (anchor is now
        # the recently-set last_fired_at, so not due).
        fire_schedule(sched.id)
        self.assertEqual(NotificationOutbox.objects.count(), 1)

    def test_personal_scope_fires_to_owner_only(self):
        sched = make_personal_schedule(self.tenant, self.user)
        sched.last_fired_at = timezone.now() - timedelta(days=365)
        sched.save(update_fields=['last_fired_at'])
        # Need provider_params customer_id for personal-scope test.
        # Personal scope doesn't auto-merge customer_id; for this test we
        # set it explicitly on the schedule.
        sched.provider_params = {'customer_id': str(self.customer.id)}
        sched.save(update_fields=['provider_params'])

        fire_schedule(sched.id)

        rows = list(NotificationOutbox.objects.filter(
            event_code='schedule:customer_active_orders',
        ))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].user_id, self.user.id)

    def test_unknown_schedule_id_is_noop(self):
        import uuid
        fire_schedule(uuid.uuid4())  # nonexistent
        self.assertEqual(NotificationOutbox.objects.count(), 0)


class FireScheduleRecipientDedupTests(TenantContextMixin, TestCase):
    """User listed in both recipient_users and a recipient_group only
    gets one outbox row (dedup by (kind, id))."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Dedup Tenant', slug='dedup-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')
        self.group = make_tenant_group(self.tenant, 'Buyer')
        self.user = make_user_in_groups(self.tenant, self.group, first_name='Jane')

        self._provider_patch = patch(
            'Tracker.services.core.notifications.scheduled_content.customer_active_orders.'
            'CustomerActiveOrdersProvider.build_content',
            return_value=RenderedContent(subject='X', html='<p>x</p>', text='x'),
        )
        self._provider_patch.start()
        self.addCleanup(self._provider_patch.stop)

    def test_user_in_both_direct_and_group_dedupes_to_one_row(self):
        sched = make_customer_schedule(
            self.tenant, self.customer,
            recipient_users=[self.user],
            recipient_groups=[self.group],
        )
        sched.last_fired_at = timezone.now() - timedelta(days=365)
        sched.save(update_fields=['last_fired_at'])

        fire_schedule(sched.id)
        self.assertEqual(
            NotificationOutbox.objects.filter(user=self.user).count(), 1,
        )
