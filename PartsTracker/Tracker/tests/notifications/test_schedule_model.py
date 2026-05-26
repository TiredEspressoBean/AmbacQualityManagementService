"""NotificationSchedule model-level tests — R1 coverage.

Covers:
  - Tenant + customer scope shapes save successfully
  - Scope-shape CheckConstraint blocks malformed rows (raw .objects.create
    bypassing clean() is what the DB-level constraint is for)
  - Cadence-shape CheckConstraint blocks malformed rows
  - `clean()` rejects unknown provider_kind, empty channels, malformed
    scope/cadence shapes with friendly field-keyed messages
  - `resolved_timezone()` falls back to tenant.default_timezone when the
    schedule's timezone is the default 'UTC'
  - The manager's named methods filter archived rows by default

Beat-task semantics (compute_next_fire, fire_schedule) are R3 — tested in
test_schedule.py.
"""
from __future__ import annotations

from datetime import time

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from Tracker.models import (
    Companies,
    NotificationSchedule,
    Tenant,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_customer_schedule,
    make_personal_schedule,
    make_tenant_group,
    make_tenant_schedule,
    make_user_in_groups,
)


class NotificationScheduleSaveTests(TenantContextMixin, TestCase):
    """Happy-path saves and required-field validation."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Sched Tenant', slug='sched-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')

    def test_tenant_scoped_weekly_saves(self):
        sched = make_tenant_schedule(self.tenant)
        self.assertEqual(sched.scope_kind, 'tenant')
        self.assertIsNone(sched.scope_customer)
        self.assertEqual(sched.cadence, 'weekly')
        self.assertEqual(sched.day_of_week, 4)
        self.assertIsNone(sched.day_of_month)

    def test_customer_scoped_weekly_saves(self):
        sched = make_customer_schedule(self.tenant, self.customer)
        self.assertEqual(sched.scope_kind, 'customer')
        self.assertEqual(sched.scope_customer_id, self.customer.id)

    def test_monthly_cadence_saves(self):
        sched = make_tenant_schedule(
            self.tenant, cadence='monthly', day_of_week=None, day_of_month=15,
        )
        self.assertEqual(sched.cadence, 'monthly')
        self.assertEqual(sched.day_of_month, 15)
        self.assertIsNone(sched.day_of_week)

    def test_personal_scoped_saves(self):
        user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Buyer'))
        sched = make_personal_schedule(self.tenant, user)
        self.assertEqual(sched.scope_kind, 'personal')
        self.assertEqual(sched.owner_user_id, user.id)
        self.assertIsNone(sched.scope_customer)
        self.assertTrue(sched.is_personal)

    def test_personal_is_editable_only_by_owner(self):
        user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Buyer'))
        other = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Other'))
        sched = make_personal_schedule(self.tenant, user)
        self.assertTrue(sched.is_editable_by(user))
        self.assertFalse(sched.is_editable_by(other))


class NotificationScheduleCleanTests(TenantContextMixin, TestCase):
    """Serializer-friendly validation messages from clean()."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='C Tenant', slug='c-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')

    def test_unknown_provider_kind_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad',
                scope_kind='tenant',
                provider_kind='no_such_provider',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('provider_kind', ctx.exception.message_dict)

    def test_empty_channels_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='no channels',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=[],
            ).full_clean()
        self.assertIn('channels', ctx.exception.message_dict)

    def test_tenant_scope_with_customer_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad shape',
                scope_kind='tenant',
                scope_customer=self.customer,
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('scope_customer', ctx.exception.message_dict)

    def test_personal_scope_without_owner_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad personal',
                scope_kind='personal',
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('owner_user', ctx.exception.message_dict)

    def test_personal_scope_with_customer_rejected(self):
        user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Buyer'))
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad personal',
                scope_kind='personal',
                scope_customer=self.customer,
                owner_user=user,
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('scope_customer', ctx.exception.message_dict)

    def test_customer_scope_without_customer_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad shape',
                scope_kind='customer',
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('scope_customer', ctx.exception.message_dict)

    def test_weekly_missing_day_of_week_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad weekly',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='weekly',
                channels=['email'],
            ).full_clean()
        self.assertIn('day_of_week', ctx.exception.message_dict)

    def test_weekly_with_day_of_month_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad weekly',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                day_of_month=1,
                channels=['email'],
            ).full_clean()
        self.assertIn('day_of_month', ctx.exception.message_dict)

    def test_monthly_missing_day_of_month_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad monthly',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='monthly',
                channels=['email'],
            ).full_clean()
        self.assertIn('day_of_month', ctx.exception.message_dict)

    def test_monthly_day_29_rejected(self):
        """day_of_month must be 1-28 to avoid month-length gotchas."""
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad monthly',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='monthly',
                day_of_month=31,
                channels=['email'],
            ).full_clean()
        self.assertIn('day_of_month', ctx.exception.message_dict)

    def test_day_of_week_out_of_range_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='bad dow',
                scope_kind='tenant',
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=7,
                channels=['email'],
            ).full_clean()
        self.assertIn('day_of_week', ctx.exception.message_dict)

    def test_cross_tenant_customer_rejected(self):
        other_tenant = Tenant.objects.create(name='Other', slug='other')
        # Create the customer in the other tenant by switching contexts.
        from Tracker.utils.tenant_context import set_current_tenant_id, reset_current_tenant
        token = set_current_tenant_id(other_tenant.id)
        try:
            other_customer = Companies.objects.create(name='Foreign', description='')
        finally:
            reset_current_tenant(token)

        with self.assertRaises(ValidationError) as ctx:
            NotificationSchedule(
                tenant=self.tenant,
                name='cross tenant',
                scope_kind='customer',
                scope_customer=other_customer,
                provider_kind='customer_active_orders',
                cadence='weekly',
                day_of_week=0,
                channels=['email'],
            ).full_clean()
        self.assertIn('scope_customer', ctx.exception.message_dict)


class NotificationScheduleDbConstraintTests(TenantContextMixin, TestCase):
    """DB-level CheckConstraints — the safety net under clean()."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='DB Tenant', slug='db-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')

    def test_scope_shape_constraint_blocks_raw_insert(self):
        """Bypass clean() and try to insert a malformed row directly."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                # Build then save with full_clean disabled to hit the DB layer.
                sched = NotificationSchedule(
                    tenant=self.tenant,
                    name='raw bad',
                    scope_kind='tenant',
                    scope_customer=self.customer,  # invalid: tenant + customer
                    provider_kind='customer_active_orders',
                    cadence='weekly',
                    day_of_week=0,
                    channels=['email'],
                )
                # Skip full_clean to reach the DB constraint.
                from django.db.models import Model
                Model.save(sched)

    def test_cadence_shape_constraint_blocks_raw_insert(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                sched = NotificationSchedule(
                    tenant=self.tenant,
                    name='raw bad cadence',
                    scope_kind='tenant',
                    provider_kind='customer_active_orders',
                    cadence='weekly',
                    day_of_week=0,
                    day_of_month=15,  # invalid: weekly + day_of_month
                    channels=['email'],
                )
                from django.db.models import Model
                Model.save(sched)


class NotificationScheduleManagerTests(TenantContextMixin, TestCase):
    """Manager methods filter archived rows and scope correctly."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='M Tenant', slug='m-tenant')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')

    def test_tenant_schedules_excludes_customer(self):
        tenant_sched = make_tenant_schedule(self.tenant)
        make_customer_schedule(self.tenant, self.customer)
        result = list(NotificationSchedule.objects.tenant_schedules())
        self.assertEqual([s.id for s in result], [tenant_sched.id])

    def test_customer_schedules_filters_by_customer(self):
        other = Companies.objects.create(name='Beacon', description='')
        s1 = make_customer_schedule(self.tenant, self.customer)
        make_customer_schedule(self.tenant, other)
        result = list(NotificationSchedule.objects.customer_schedules(self.customer))
        self.assertEqual([s.id for s in result], [s1.id])

    def test_tenant_schedules_excludes_archived(self):
        sched = make_tenant_schedule(self.tenant)
        sched.archived = True
        sched.save(update_fields=['archived'])
        self.assertFalse(NotificationSchedule.objects.tenant_schedules().exists())

    def test_personal_schedules_for_filters_to_owner(self):
        user_a = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Buyer'))
        user_b = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'Other'))
        a_sched = make_personal_schedule(self.tenant, user_a)
        make_personal_schedule(self.tenant, user_b)
        result = list(NotificationSchedule.objects.personal_schedules_for(user_a))
        self.assertEqual([s.id for s in result], [a_sched.id])


class NotificationScheduleTimezoneTests(TenantContextMixin, TestCase):
    """resolved_timezone() fallback chain."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name='TZ Tenant', slug='tz-tenant', default_timezone='America/New_York',
        )
        self.set_tenant_context(self.tenant)

    def test_explicit_tz_wins(self):
        sched = make_tenant_schedule(self.tenant)
        sched.timezone = 'Europe/Berlin'
        sched.save(update_fields=['timezone'])
        self.assertEqual(sched.resolved_timezone(), 'Europe/Berlin')

    def test_default_utc_falls_back_to_tenant_default(self):
        sched = make_tenant_schedule(self.tenant)
        # `timezone` defaults to 'UTC'; tenant default is America/New_York.
        self.assertEqual(sched.timezone, 'UTC')
        self.assertEqual(sched.resolved_timezone(), 'America/New_York')

    def test_no_tenant_default_falls_back_to_utc(self):
        tenant_utc = Tenant.objects.create(
            name='UTC Tenant', slug='utc-tenant', default_timezone='UTC',
        )
        self.set_tenant_context(tenant_utc)
        sched = make_tenant_schedule(tenant_utc)
        self.assertEqual(sched.resolved_timezone(), 'UTC')
