"""Phase 3 dispatcher tests — rule-driven recipient resolution.

Covers:
  - Tenant-scoped rule with recipient_users / recipient_groups → users get rows.
  - Customer-scoped rule fires only when payload references that customer.
  - Personal rule's owner_user becomes the recipient implicitly.
  - CEL conditions filter (severity == critical).
  - `min_gap_seconds` cooldown suppresses repeat fires.
  - Channel preferences (Phase 2) intersect with rule.channels.
  - (recipient, channel) dedup across rules.

Replaces the Phase 2 `test_dispatcher_phase2.py` which tested the
`default_recipient_groups` stub that Phase 3 retired.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Companies,
    ExternalContact,
    NotificationOutbox,
    Tenant,
)
from Tracker.services.core.notifications import emit
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_customer_rule,
    make_event_payload,
    make_personal_rule,
    make_tenant_group,
    make_tenant_rule,
    make_user_in_groups,
    set_tenant_default,
    set_user_preference,
)


class DispatcherRuleResolutionTests(TenantContextMixin, TestCase):
    """Rule-based recipient resolution for tenant-scoped rules."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Disp Tenant', slug='disp-tenant')
        self.set_tenant_context(self.tenant)
        self.qa_group = make_tenant_group(self.tenant, 'QA Manager')

    def test_no_rules_writes_no_rows(self):
        payload = make_event_payload('ncr.opened', tenant_id=str(self.tenant.id))
        emit('ncr.opened', tenant=self.tenant, payload=payload)
        self.assertEqual(NotificationOutbox.objects.count(), 0)

    def test_tenant_rule_with_group_fires_to_group_members(self):
        u1 = make_user_in_groups(self.tenant, self.qa_group)
        u2 = make_user_in_groups(self.tenant, self.qa_group)
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_groups=[self.qa_group],
            channels=['in_app', 'email'],
        )

        payload = make_event_payload('ncr.opened', tenant_id=str(self.tenant.id))
        emit('ncr.opened', tenant=self.tenant, payload=payload)

        rows = NotificationOutbox.objects.filter(event_code='ncr.opened')
        # 2 users × 2 channels = 4 rows
        self.assertEqual(rows.count(), 4)
        self.assertEqual(set(rows.values_list('user_id', flat=True)), {u1.id, u2.id})

    def test_tenant_rule_with_recipient_user_fires(self):
        u = make_user_in_groups(self.tenant, self.qa_group)
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[u],
            channels=['in_app'],
        )

        payload = make_event_payload('ncr.opened', tenant_id=str(self.tenant.id))
        emit('ncr.opened', tenant=self.tenant, payload=payload)

        rows = NotificationOutbox.objects.filter(event_code='ncr.opened')
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user_id, u.id)

    def test_dedup_across_user_and_group_membership(self):
        """User who's both in recipient_groups and recipient_users gets one row, not two."""
        u = make_user_in_groups(self.tenant, self.qa_group)
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[u],
            recipient_groups=[self.qa_group],
            channels=['in_app'],
        )

        payload = make_event_payload('ncr.opened', tenant_id=str(self.tenant.id))
        emit('ncr.opened', tenant=self.tenant, payload=payload)

        rows = NotificationOutbox.objects.filter(event_code='ncr.opened')
        self.assertEqual(rows.count(), 1)


class DispatcherCelFilterTests(TenantContextMixin, TestCase):
    """CEL conditions narrow which rules fire."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='CEL Tenant', slug='cel-tenant')
        self.set_tenant_context(self.tenant)
        self.qa_group = make_tenant_group(self.tenant, 'QA Manager')
        self.user = make_user_in_groups(self.tenant, self.qa_group)

    def test_cel_critical_only_fires_on_critical(self):
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user],
            conditions="payload.severity == 'critical'",
            channels=['in_app'],
        )

        # major severity → no fire
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', severity='major',
                                        tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 0)

        # critical severity → fires
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', severity='critical',
                                        tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 1)


class DispatcherPersonalScopeTests(TenantContextMixin, TestCase):
    """Personal rules deliver to the owner; CEL with owner_user.id works."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Personal Tenant', slug='personal-tenant')
        self.set_tenant_context(self.tenant)
        self.user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'QA'))

    def test_personal_rule_owner_is_implicit_recipient(self):
        make_personal_rule(
            self.tenant, self.user, 'ncr.opened',
            channels=['in_app'],
        )

        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))

        rows = NotificationOutbox.objects.filter(event_code='ncr.opened')
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user_id, self.user.id)

    def test_personal_rule_with_owner_user_cel(self):
        """`payload.opened_by_id == owner_user.id` → only fires when the
        opener is the rule's owner."""
        make_personal_rule(
            self.tenant, self.user, 'ncr.opened',
            conditions='payload.opened_by_id == owner_user.id',
            channels=['in_app'],
        )

        # Different opener → no fire
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', opened_by_id=999,
                                        tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 0)

        # Owner is the opener → fires
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', opened_by_id=self.user.id,
                                        tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 1)


class DispatcherCustomerScopeTests(TenantContextMixin, TestCase):
    """Customer-scoped rules fire only when payload references that customer."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Cust Tenant', slug='cust-tenant')
        self.set_tenant_context(self.tenant)
        self.customer_a = Companies.objects.create(name='Acme', description='')
        self.customer_b = Companies.objects.create(name='Beacon', description='')
        self.contact = ExternalContact.objects.create(
            tenant=self.tenant, customer=self.customer_a,
            name='Acme Buyer', email='buyer@acme.example',
        )

    def test_customer_rule_fires_only_for_matching_customer(self):
        # Use order.shipped which is in the registry.
        make_customer_rule(
            self.tenant, self.customer_a, 'order.shipped',
            recipient_external=[self.contact],
            channels=['email'],
        )

        # Payload for the other customer → no fire
        emit('order.shipped', tenant=self.tenant,
             payload=make_event_payload(
                 'order.shipped',
                 tenant_id=str(self.tenant.id),
                 customer_id=str(self.customer_b.id),
             ))
        self.assertEqual(NotificationOutbox.objects.count(), 0)

        # Payload for the matching customer → fires to external contact
        emit('order.shipped', tenant=self.tenant,
             payload=make_event_payload(
                 'order.shipped',
                 tenant_id=str(self.tenant.id),
                 customer_id=str(self.customer_a.id),
             ))
        rows = NotificationOutbox.objects.filter(event_code='order.shipped')
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertIsNone(row.user_id)
        self.assertEqual(row.external_contact_id, self.contact.id)


class DispatcherCooldownTests(TenantContextMixin, TestCase):
    """`min_gap_seconds` suppresses repeat fires within the window."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='CD Tenant', slug='cd-tenant')
        self.set_tenant_context(self.tenant)
        self.user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'QA'))

    def test_cooldown_suppresses_within_window(self):
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user],
            channels=['in_app'],
            min_gap_seconds=3600,  # 1h
        )

        # First fire writes a row.
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 1)

        # Second fire within window → suppressed.
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))
        self.assertEqual(NotificationOutbox.objects.count(), 1)

    def test_cooldown_zero_disables_dedup(self):
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user],
            channels=['in_app'],
            min_gap_seconds=0,
        )
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))
        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))
        # Both fire (idempotency_key changes each emit so the outbox unique
        # constraint allows the second insert).
        self.assertEqual(NotificationOutbox.objects.count(), 2)


class DispatcherChannelInteractionTests(TenantContextMixin, TestCase):
    """Channel resolver (Phase 2) intersects with rule.channels."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Ch Tenant', slug='ch-tenant')
        self.set_tenant_context(self.tenant)
        self.user = make_user_in_groups(self.tenant, make_tenant_group(self.tenant, 'QA'))

    def test_user_mute_suppresses_channel(self):
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user],
            channels=['in_app', 'email'],
        )
        set_user_preference(self.user, 'ncr.opened', 'email', enabled=False)

        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))

        channels = set(NotificationOutbox.objects.filter(event_code='ncr.opened')
                                                  .values_list('channel', flat=True))
        self.assertEqual(channels, {'in_app'})


class DispatcherScopePrecedenceTests(TenantContextMixin, TestCase):
    """Personal scope takes precedence over tenant in dedup races.

    When both a tenant rule and a personal rule target the same user/channel,
    the (recipient, channel) dedup logic produces one outbox row. That row
    must be attributed to the personal rule — the user's explicit opt-in
    beats the admin's broad fan-out.
    """

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Prec Tenant', slug='prec-tenant')
        self.set_tenant_context(self.tenant)
        self.qa_group = make_tenant_group(self.tenant, 'QA')
        self.user = make_user_in_groups(self.tenant, self.qa_group)

    def test_personal_rule_wins_over_tenant_on_dedup(self):
        # Tenant rule fans out to QA group (which includes user).
        tenant_rule = make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_groups=[self.qa_group],
            channels=['in_app'],
        )
        # Personal rule with the same channel.
        personal_rule = make_personal_rule(
            self.tenant, self.user, 'ncr.opened',
            channels=['in_app'],
        )

        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))

        rows = NotificationOutbox.objects.filter(user=self.user, channel='in_app')
        # Dedup: exactly one row for the user.
        self.assertEqual(rows.count(), 1)
        # Precedence: the row is attributed to the personal rule, not the tenant rule.
        self.assertEqual(rows.first().rule_id, personal_rule.id)

    def test_disjoint_channels_both_fire(self):
        # Tenant rule targets email, personal targets in_app — no overlap.
        # Both should produce rows.
        make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_groups=[self.qa_group],
            channels=['email'],
        )
        make_personal_rule(
            self.tenant, self.user, 'ncr.opened',
            channels=['in_app'],
        )

        emit('ncr.opened', tenant=self.tenant,
             payload=make_event_payload('ncr.opened', tenant_id=str(self.tenant.id)))

        channels = set(NotificationOutbox.objects.filter(user=self.user)
                                                  .values_list('channel', flat=True))
        self.assertEqual(channels, {'in_app', 'email'})
