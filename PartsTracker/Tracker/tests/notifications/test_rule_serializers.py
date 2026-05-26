"""Phase 3 rule serializer tests.

Covers per-scope field exposure, CEL save-time validation surfacing,
cross-tenant guards.
"""
from __future__ import annotations

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from Tracker.models import Companies, ExternalContact, NotificationRule, Tenant
from Tracker.serializers.notifications import (
    CustomerRuleSerializer,
    ExternalContactSerializer,
    PersonalRuleSerializer,
    TenantRuleSerializer,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_tenant_group,
    make_user_in_groups,
)


class _FakeRequest:
    """Minimal request stub for serializer context."""
    def __init__(self, user):
        self.user = user


class TenantRuleSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.set_tenant_context(self.tenant)
        self.group = make_tenant_group(self.tenant, 'QA')
        self.user = make_user_in_groups(self.tenant, self.group)

    def test_create_with_recipient_group(self):
        ser = TenantRuleSerializer(
            data={
                'name': 'Critical NCRs',
                'event_code': 'ncr.opened',
                'conditions_source': "payload.severity == 'critical'",
                'channels': ['in_app', 'email'],
                'recipient_groups': [self.group.id],
                'recipient_users': [],
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        self.assertEqual(rule.scope_kind, 'tenant')
        self.assertEqual(rule.created_by_id, self.user.id)
        self.assertIn(self.group, rule.recipient_groups.all())

    def test_cel_did_you_mean_surfaces_as_validation_error(self):
        ser = TenantRuleSerializer(
            data={
                'name': 'typo rule',
                'event_code': 'ncr.opened',
                'conditions_source': "payload.severty == 'critical'",  # typo
                'channels': ['in_app'],
                'recipient_groups': [self.group.id],
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        # CEL validation runs in model.clean() at save time
        with self.assertRaises(Exception) as cm:
            ser.save()
        msg = str(cm.exception)
        self.assertIn('severty', msg)
        self.assertIn('severity', msg)  # did-you-mean suggestion


class CustomerRuleSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')
        self.contact_a = ExternalContact.objects.create(
            tenant=self.tenant, customer=self.customer,
            name='Buyer', email='buyer@acme.example',
        )
        self.user = make_user_in_groups(
            self.tenant, make_tenant_group(self.tenant, 'QA'),
        )

    def test_create_with_external_contact(self):
        ser = CustomerRuleSerializer(
            data={
                'name': 'Notify Acme on shipments',
                'event_code': 'order.shipped',
                'scope_customer': self.customer.id,
                'channels': ['email'],
                'recipient_external': [self.contact_a.id],
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        self.assertEqual(rule.scope_kind, 'customer')
        self.assertEqual(rule.scope_customer_id, self.customer.id)
        self.assertIn(self.contact_a, rule.recipient_external.all())

    def test_external_contact_from_other_customer_rejected(self):
        other_customer = Companies.objects.create(name='Beacon', description='')
        other_contact = ExternalContact.objects.create(
            tenant=self.tenant, customer=other_customer,
            name='Beacon Buyer', email='buyer@beacon.example',
        )
        ser = CustomerRuleSerializer(
            data={
                'name': 'cross-customer attempt',
                'event_code': 'order.shipped',
                'scope_customer': self.customer.id,
                'channels': ['email'],
                'recipient_external': [other_contact.id],
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('recipient_external', ser.errors)


class PersonalRuleSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.set_tenant_context(self.tenant)
        self.user = make_user_in_groups(
            self.tenant, make_tenant_group(self.tenant, 'QA'),
        )

    def test_owner_user_stamped_from_request(self):
        ser = PersonalRuleSerializer(
            data={
                'name': 'My critical NCRs',
                'event_code': 'ncr.opened',
                'conditions_source': "payload.severity == 'critical'",
                'channels': ['in_app'],
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        self.assertEqual(rule.scope_kind, 'personal')
        self.assertEqual(rule.owner_user_id, self.user.id)

    def test_personal_rule_does_not_expose_recipient_fields(self):
        """`recipient_users`/`recipient_groups`/`recipient_external` are not
        in the serializer's fields list and silently ignored if sent."""
        self.assertNotIn('recipient_users', PersonalRuleSerializer().fields)
        self.assertNotIn('recipient_groups', PersonalRuleSerializer().fields)
        self.assertNotIn('recipient_external', PersonalRuleSerializer().fields)


class ExternalContactSerializerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='T', slug='t')
        self.set_tenant_context(self.tenant)
        self.customer = Companies.objects.create(name='Acme', description='')

    def test_create_external_contact(self):
        ser = ExternalContactSerializer(data={
            'customer': self.customer.id,
            'name': 'Buyer',
            'email': 'buyer@acme.example',
            'role': 'procurement',
        })
        self.assertTrue(ser.is_valid(), ser.errors)
        contact = ser.save()
        self.assertEqual(contact.customer_id, self.customer.id)
        self.assertTrue(contact.enabled)


class NestedEscalationSerializerTests(TenantContextMixin, TestCase):
    """E6 — nested `escalation` field on rule serializers (create/update/delete)."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Esc', slug='esc-t')
        self.set_tenant_context(self.tenant)
        self.group = make_tenant_group(self.tenant, 'QA')
        self.user = make_user_in_groups(self.tenant, self.group)

    def _base_data(self, **overrides):
        data = {
            'name': 'Critical NCRs',
            'event_code': 'ncr.opened',
            'conditions_source': "payload.severity == 'critical'",
            'channels': ['in_app'],
            'recipient_groups': [self.group.id],
            'recipient_users': [],
        }
        data.update(overrides)
        return data

    def test_create_with_escalation_persists_policy_and_steps(self):
        data = self._base_data(escalation={
            'enabled': True,
            'steps': [
                {'order': 0, 'delay_seconds': 600,
                 'recipient_groups': [self.group.id]},
                {'order': 1, 'delay_seconds': 1800,
                 'recipient_users': [self.user.id],
                 'subject_override': 'ESCALATED — 30 min unack'},
            ],
        })
        ser = TenantRuleSerializer(
            data=data, context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()

        policy = rule.escalation_policy
        self.assertTrue(policy.enabled)
        steps = list(policy.steps.all().order_by('order'))
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].delay_seconds, 600)
        self.assertIn(self.group, steps[0].recipient_groups.all())
        self.assertEqual(steps[1].subject_override, 'ESCALATED — 30 min unack')
        self.assertIn(self.user, steps[1].recipient_users.all())

    def test_create_without_escalation_leaves_no_policy(self):
        ser = TenantRuleSerializer(
            data=self._base_data(),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        from django.core.exceptions import ObjectDoesNotExist
        with self.assertRaises(ObjectDoesNotExist):
            _ = rule.escalation_policy

    def test_update_with_new_steps_replaces_existing(self):
        # First create with one step
        ser = TenantRuleSerializer(
            data=self._base_data(escalation={
                'enabled': True,
                'steps': [{'order': 0, 'delay_seconds': 600}],
            }),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        original_policy_id = rule.escalation_policy.id

        # PATCH with two steps — original step is wiped, new ones written
        ser2 = TenantRuleSerializer(
            rule,
            data={'escalation': {
                'enabled': True,
                'steps': [
                    {'order': 0, 'delay_seconds': 300},
                    {'order': 1, 'delay_seconds': 1200},
                ],
            }},
            partial=True,
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser2.is_valid(), ser2.errors)
        rule = ser2.save()
        # Same policy row (upsert), new steps
        self.assertEqual(rule.escalation_policy.id, original_policy_id)
        delays = list(rule.escalation_policy.steps.values_list(
            'delay_seconds', flat=True,
        ))
        self.assertEqual(sorted(delays), [300, 1200])

    def test_patch_without_escalation_key_leaves_policy_untouched(self):
        # Create with escalation
        ser = TenantRuleSerializer(
            data=self._base_data(escalation={
                'enabled': True,
                'steps': [{'order': 0, 'delay_seconds': 600}],
            }),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        original_policy_id = rule.escalation_policy.id

        # PATCH that doesn't mention escalation
        ser2 = TenantRuleSerializer(
            rule,
            data={'name': 'Renamed'},
            partial=True,
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser2.is_valid(), ser2.errors)
        rule = ser2.save()
        self.assertEqual(rule.name, 'Renamed')
        self.assertEqual(rule.escalation_policy.id, original_policy_id)

    def test_patch_with_null_escalation_deletes_policy(self):
        from Tracker.models import EscalationPolicy

        ser = TenantRuleSerializer(
            data=self._base_data(escalation={
                'enabled': True,
                'steps': [{'order': 0, 'delay_seconds': 600}],
            }),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        self.assertIsNotNone(rule.escalation_policy)

        ser2 = TenantRuleSerializer(
            rule,
            data={'escalation': None},
            partial=True,
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser2.is_valid(), ser2.errors)
        ser2.save()
        # Query via the manager — the OneToOne reverse descriptor caches
        # on the instance, so `rule.escalation_policy` still returns the
        # stale reference after delete.
        self.assertFalse(EscalationPolicy.objects.filter(rule=rule).exists())

    def test_to_representation_surfaces_nested_escalation(self):
        ser = TenantRuleSerializer(
            data=self._base_data(escalation={
                'enabled': True,
                'steps': [
                    {'order': 0, 'delay_seconds': 900,
                     'subject_override': 'first ping'},
                ],
            }),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        out = TenantRuleSerializer(rule).data
        self.assertEqual(out['escalation']['enabled'], True)
        self.assertEqual(len(out['escalation']['steps']), 1)
        self.assertEqual(out['escalation']['steps'][0]['delay_seconds'], 900)
        self.assertEqual(
            out['escalation']['steps'][0]['subject_override'], 'first ping',
        )

    def test_empty_steps_list_is_rejected(self):
        ser = TenantRuleSerializer(
            data=self._base_data(escalation={'enabled': True, 'steps': []}),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('escalation', ser.errors)

    def test_duplicate_step_orders_rejected(self):
        ser = TenantRuleSerializer(
            data=self._base_data(escalation={
                'enabled': True,
                'steps': [
                    {'order': 0, 'delay_seconds': 600},
                    {'order': 0, 'delay_seconds': 1200},
                ],
            }),
            context={'request': _FakeRequest(self.user)},
        )
        self.assertFalse(ser.is_valid())
        self.assertIn('escalation', ser.errors)

    def test_personal_rule_escalation_persists(self):
        # Coverage: personal-scope rule with single-step "if I don't ack" chain.
        ser = PersonalRuleSerializer(
            data={
                'name': 'Cover me',
                'event_code': 'ncr.opened',
                'conditions_source': '',
                'channels': ['in_app'],
                'escalation': {
                    'enabled': True,
                    'steps': [{'order': 0, 'delay_seconds': 14400}],
                },
            },
            context={'request': _FakeRequest(self.user)},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        rule = ser.save()
        self.assertEqual(rule.scope_kind, 'personal')
        self.assertEqual(rule.escalation_policy.steps.count(), 1)
