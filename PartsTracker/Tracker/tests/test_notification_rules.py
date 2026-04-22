"""
Phase 1 tests for the event-driven NotificationRule dispatcher.

Covers:
- GFK scope cross-tenant rejection (clean() invariant)
- notify() fan-out into NotificationTask rows
- Scope matching (null scope = tenant-wide, specific scope = exact match only)
- Per-(rule, recipient) cooldown dedup
- Resolver registry (unknown key is skipped, not raised)
- Static M2M recipients
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    NotificationRule,
    NotificationTask,
    Companies,
    Orders,
    OrdersStatus,
    PartTypes,
    Parts,
    PartsStatus,
    Processes,
    ProcessStep,
    QualityReports,
    StepExecution,
    Steps,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.core.notification import notify
from Tracker.services.core.notification_resolvers import (
    _RESOLVERS,
    register_resolver,
)
from Tracker.services.qms.quality_report import (
    record_quality_report_side_effects,
)
from Tracker.tests.base import TenantTestCase
from Tracker.utils.tenant_context import tenant_context


class NotificationRuleModelTests(TenantTestCase):
    """Model-level invariants: GFK tenant match."""

    def test_scope_in_same_tenant_is_allowed(self):
        process_a = Companies.objects.create(name='Co-A', description='x')
        rule = NotificationRule(
            name='same-tenant',
            event_type='STEP_FAILURE',
            scope_content_type=ContentType.objects.get_for_model(Companies),
            scope_object_id=str(process_a.pk),
        )
        # Should not raise
        rule.save()
        self.assertIsNotNone(rule.pk)

    def test_scope_in_other_tenant_is_rejected(self):
        # Create a Process in tenant_b
        token = self.switch_tenant_context(self.tenant_b)
        try:
            process_b = Companies.objects.create(name='Co-B', description='x')
        finally:
            self.switch_tenant_context(self.tenant_a)
            # Restore token cleanup
            from Tracker.utils.tenant_context import reset_current_tenant
            # Setting back to tenant_a above replaced the ContextVar already;
            # discard token.
            del token

        rule = NotificationRule(
            name='cross-tenant',
            event_type='STEP_FAILURE',
            scope_content_type=ContentType.objects.get_for_model(Companies),
            scope_object_id=str(process_b.pk),
        )
        with self.assertRaises(ValidationError):
            rule.save()

    def test_null_scope_is_allowed(self):
        rule = NotificationRule(
            name='tenant-wide',
            event_type='STEP_FAILURE',
        )
        rule.save()
        self.assertIsNone(rule.scope_content_type_id)


class NotifyDispatcherTests(TenantTestCase):
    """notify() creates NotificationTask rows from matching rules."""

    def _make_rule(self, **kwargs):
        defaults = dict(
            name='test rule',
            event_type='STEP_FAILURE',
            channel_type='EMAIL',
            min_gap_seconds=0,  # disable cooldown unless a test opts in
            is_active=True,
        )
        defaults.update(kwargs)
        return NotificationRule.objects.create(**defaults)

    def test_static_user_recipient_creates_task(self):
        rule = self._make_rule()
        rule.recipient_users.add(self.user_a)

        created = notify('STEP_FAILURE')

        self.assertEqual(len(created), 1)
        task = created[0]
        self.assertEqual(task.recipient, self.user_a)
        self.assertEqual(task.notification_type, 'STEP_FAILURE')
        self.assertEqual(task.source_rule, rule)
        self.assertEqual(task.status, 'PENDING')

    def test_inactive_rule_does_not_fire(self):
        rule = self._make_rule(is_active=False)
        rule.recipient_users.add(self.user_a)

        created = notify('STEP_FAILURE')

        self.assertEqual(created, [])

    def test_scope_matches_only_same_object(self):
        process_target = Companies.objects.create(name='target', description='x')
        process_other = Companies.objects.create(name='other', description='x')

        rule = self._make_rule(
            scope_content_type=ContentType.objects.get_for_model(Companies),
            scope_object_id=str(process_target.pk),
        )
        rule.recipient_users.add(self.user_a)

        self.assertEqual(notify('STEP_FAILURE', scope_obj=process_target).__len__(), 1)
        self.assertEqual(notify('STEP_FAILURE', scope_obj=process_other), [])

    def test_null_scope_rule_always_matches(self):
        process = Companies.objects.create(name='x', description='x')
        rule = self._make_rule()  # null scope
        rule.recipient_users.add(self.user_a)

        # Both with-scope and without-scope events hit it.
        self.assertEqual(len(notify('STEP_FAILURE', scope_obj=process)), 1)
        self.assertEqual(len(notify('STEP_FAILURE')), 1)

    def test_cooldown_suppresses_repeat(self):
        rule = self._make_rule(min_gap_seconds=3600)
        rule.recipient_users.add(self.user_a)

        first = notify('STEP_FAILURE')
        second = notify('STEP_FAILURE')  # within cooldown

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_cooldown_expires(self):
        rule = self._make_rule(min_gap_seconds=60)
        rule.recipient_users.add(self.user_a)

        first = notify('STEP_FAILURE')

        # Age the first task past the cooldown window
        NotificationTask.objects.filter(pk=first[0].pk).update(
            created_at=timezone.now() - timedelta(seconds=120)
        )

        second = notify('STEP_FAILURE')
        self.assertEqual(len(second), 1)

    def test_rule_from_other_tenant_does_not_fire(self):
        # Create rule + recipient in tenant_b
        token = self.switch_tenant_context(self.tenant_b)
        try:
            rule_b = NotificationRule.objects.create(
                name='b-rule',
                event_type='STEP_FAILURE',
                min_gap_seconds=0,
            )
            rule_b.recipient_users.add(self.user_b)
        finally:
            self.switch_tenant_context(self.tenant_a)
            del token

        # Fire from tenant_a context — only tenant_a rules should match
        created = notify('STEP_FAILURE')
        self.assertEqual(created, [])


class ResolverRegistryTests(TenantTestCase):
    """Resolver lookup, missing key handling, dynamic recipient injection."""

    def setUp(self):
        super().setUp()
        # Register a test-only resolver; snapshot the registry and restore
        # in tearDown so the starter resolvers aren't disturbed.
        self._registry_snapshot = dict(_RESOLVERS)

        def _echo_user(payload):
            uid = payload.get('user_id')
            if uid is None:
                return []
            from django.contrib.auth import get_user_model
            return get_user_model().objects.filter(pk=uid)

        _RESOLVERS['test_echo_user'] = _echo_user

    def tearDown(self):
        _RESOLVERS.clear()
        _RESOLVERS.update(self._registry_snapshot)
        super().tearDown()

    def test_resolver_injects_recipient(self):
        rule = NotificationRule.objects.create(
            name='resolver-rule',
            event_type='STEP_FAILURE',
            recipient_resolver_key='test_echo_user',
            min_gap_seconds=0,
        )

        created = notify('STEP_FAILURE', payload={'user_id': self.user_a.pk})

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].recipient, self.user_a)
        self.assertEqual(created[0].source_rule, rule)

    def test_unknown_resolver_key_is_logged_not_raised(self):
        rule = NotificationRule.objects.create(
            name='bad-resolver',
            event_type='STEP_FAILURE',
            recipient_resolver_key='no_such_resolver',
            min_gap_seconds=0,
        )
        # Also attach a static recipient so the rule still matches;
        # the unknown resolver should be skipped gracefully.
        rule.recipient_users.add(self.user_a)

        created = notify('STEP_FAILURE')

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].recipient, self.user_a)


class StepFailureIntegrationTests(TenantTestCase):
    """End-to-end: a failing QualityReport enqueues a STEP_FAILURE notification
    for each active rule scoped at the part's step."""

    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(
            name='Widget', ID_prefix='WG', ERP_id='WG-001',
        )
        self.process = Processes.objects.create(
            name='Test Process', part_type=self.part_type,
        )
        self.step = Steps.objects.create(
            name='Inspection', part_type=self.part_type, description='',
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.order = Orders.objects.create(
            name='Test Order', customer=self.user_a,
            order_status=OrdersStatus.IN_PROGRESS,
        )
        self.work_order = WorkOrder.objects.create(
            ERP_id='WO-001', related_order=self.order,
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
        )
        self.part = Parts.objects.create(
            ERP_id='P-001', part_type=self.part_type, step=self.step,
            order=self.order, work_order=self.work_order,
            part_status=PartsStatus.IN_PROGRESS,
        )

    def _create_fail_report(self):
        report = QualityReports.objects.create(
            part=self.part, status='FAIL',
        )
        record_quality_report_side_effects(report)
        return report

    def test_failing_report_fires_rule_scoped_at_step(self):
        rule = NotificationRule.objects.create(
            name='step-rule',
            event_type='STEP_FAILURE',
            scope_content_type=ContentType.objects.get_for_model(Steps),
            scope_object_id=str(self.step.pk),
            min_gap_seconds=0,
        )
        rule.recipient_users.add(self.user_a)

        self._create_fail_report()

        tasks = NotificationTask.objects.filter(
            notification_type='STEP_FAILURE',
            recipient=self.user_a,
            source_rule=rule,
        )
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        # related_object should be the Part (so the handler can read it)
        self.assertEqual(task.related_object, self.part)

    def test_failing_report_fires_tenant_wide_rule(self):
        rule = NotificationRule.objects.create(
            name='tenant-wide',
            event_type='STEP_FAILURE',
            min_gap_seconds=0,
        )
        rule.recipient_users.add(self.user_a)

        self._create_fail_report()

        self.assertEqual(
            NotificationTask.objects.filter(source_rule=rule).count(), 1
        )

    def test_failing_report_notifies_operator_via_resolver(self):
        """A rule using the step_execution_assignee resolver should
        notify the operator currently assigned to the part's step."""
        # Assign user_b to a StepExecution on this part
        StepExecution.objects.create(
            part=self.part,
            step=self.step,
            assigned_to=self.user_b,
        )

        rule = NotificationRule.objects.create(
            name='notify-operator',
            event_type='STEP_FAILURE',
            recipient_resolver_key='step_execution_assignee',
            min_gap_seconds=0,
        )

        self._create_fail_report()

        # Operator (user_b) got a task via the resolver
        tasks = NotificationTask.objects.filter(
            source_rule=rule, recipient=self.user_b,
        )
        self.assertEqual(tasks.count(), 1)

    def test_failing_report_skips_rule_scoped_at_other_step(self):
        other_step = Steps.objects.create(
            name='Other', part_type=self.part_type, description='',
        )
        rule = NotificationRule.objects.create(
            name='other-scope',
            event_type='STEP_FAILURE',
            scope_content_type=ContentType.objects.get_for_model(Steps),
            scope_object_id=str(other_step.pk),
            min_gap_seconds=0,
        )
        rule.recipient_users.add(self.user_a)

        self._create_fail_report()

        self.assertFalse(
            NotificationTask.objects.filter(source_rule=rule).exists()
        )
