"""Phase 6b — `capa.assigned` cutover tests.

Validates the engine extensions (recipient_strategy='from_payload') against
a real domain event. CAPA creation/reassignment emits `capa.assigned` with
`recipient_user_ids=[assignee.id]`; a tenant rule with strategy='from_payload'
routes to the actual assignee at fire time.
"""
from __future__ import annotations

from django.core.cache import cache
from django.test import TransactionTestCase

from Tracker.models import CAPA, NotificationOutbox, Tenant
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_tenant_group,
    make_tenant_rule,
    make_user_in_groups,
)


class CapaAssignedEventTests(TenantContextMixin, TransactionTestCase):
    """TransactionTestCase used so signal `on_commit` callbacks fire — the
    notify_assignment handler wraps emit() in on_commit, which is a no-op
    under regular TestCase transaction rollback."""
    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='CAPA Test', slug='capa-assigned-test')
        self.set_tenant_context(self.tenant)
        self.qa_group = make_tenant_group(self.tenant, 'QA Manager')
        self.assignee = make_user_in_groups(
            self.tenant, self.qa_group,
            first_name='Tina', last_name='Engineer',
        )
        self.other_user = make_user_in_groups(self.tenant, self.qa_group)

    def test_creating_capa_with_assignee_fires_emit(self):
        rule = make_tenant_rule(
            self.tenant, 'capa.assigned',
            recipient_strategy='from_payload',
            channels=['in_app'],
        )

        CAPA.objects.create(
            tenant=self.tenant,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test problem',
            assigned_to=self.assignee,
            initiated_by=self.other_user,
        )

        rows = NotificationOutbox.objects.filter(
            rule=rule, event_code='capa.assigned',
        )
        self.assertEqual(rows.count(), 1)
        row = rows.first()
        self.assertEqual(row.user_id, self.assignee.id)
        self.assertEqual(row.channel, 'in_app')
        self.assertIn('CAPA', row.rendered_subject)

    def test_payload_carries_recipient_user_ids(self):
        """The signal must populate recipient_user_ids correctly so the
        from_payload strategy can resolve recipients."""
        rule = make_tenant_rule(
            self.tenant, 'capa.assigned',
            recipient_strategy='from_payload',
            channels=['in_app'],
        )

        capa = CAPA.objects.create(
            tenant=self.tenant,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test problem',
            assigned_to=self.assignee,
            initiated_by=self.other_user,
        )

        row = NotificationOutbox.objects.filter(rule=rule).first()
        self.assertIsNotNone(row)
        self.assertEqual(
            row.payload.get('recipient_user_ids'), [self.assignee.id]
        )
        self.assertEqual(row.payload.get('capa_number'), capa.capa_number)
        self.assertEqual(row.payload.get('severity'), 'MAJOR')
        self.assertFalse(row.payload.get('is_reassignment'))

    def test_capa_without_assignee_does_not_fire(self):
        make_tenant_rule(
            self.tenant, 'capa.assigned',
            recipient_strategy='from_payload',
            channels=['in_app'],
        )

        CAPA.objects.create(
            tenant=self.tenant,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Unassigned CAPA',
            initiated_by=self.other_user,
            # no assigned_to
        )

        self.assertFalse(
            NotificationOutbox.objects.filter(event_code='capa.assigned').exists()
        )

    def test_reassignment_fires_with_is_reassignment_true(self):
        rule = make_tenant_rule(
            self.tenant, 'capa.assigned',
            recipient_strategy='from_payload',
            channels=['in_app'],
        )

        capa = CAPA.objects.create(
            tenant=self.tenant,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test problem',
            assigned_to=self.assignee,
            initiated_by=self.other_user,
        )
        # First fire is on create
        self.assertEqual(
            NotificationOutbox.objects.filter(rule=rule).count(), 1
        )

        # Reassign — CAPA.save() snapshots the prior assignee via
        # `_old_assigned_to_id`, which the signal handler reads to detect
        # reassignment in production. Setting `_changed_fields` manually
        # (an earlier approach) was a test-only contract that broke the
        # behavior outside tests.
        capa.assigned_to = self.other_user
        capa.save()

        rows = NotificationOutbox.objects.filter(rule=rule).order_by('created_at')
        self.assertEqual(rows.count(), 2)
        # Second fire is reassignment, targeted at the new assignee
        new_row = rows.last()
        self.assertEqual(new_row.user_id, self.other_user.id)
        self.assertTrue(new_row.payload.get('is_reassignment'))

    def test_union_rule_combines_payload_and_static_cc(self):
        """A union-strategy rule layered on top should CC a static recipient."""
        cc_user = make_user_in_groups(self.tenant, self.qa_group)
        cc_group = make_tenant_group(self.tenant, 'Compliance')
        cc_user.user_roles.create(group=cc_group)

        rule = make_tenant_rule(
            self.tenant, 'capa.assigned',
            recipient_strategy='union',
            recipient_groups=[cc_group],   # static CC
            channels=['in_app'],
        )

        CAPA.objects.create(
            tenant=self.tenant,
            capa_type='CORRECTIVE',
            severity='MAJOR',
            problem_statement='Test problem',
            assigned_to=self.assignee,
            initiated_by=self.other_user,
        )

        recipients = set(
            NotificationOutbox.objects.filter(rule=rule).values_list('user_id', flat=True)
        )
        # Assignee (from payload) + CC user (static via group). Both fired.
        self.assertIn(self.assignee.id, recipients)
        self.assertIn(cc_user.id, recipients)
