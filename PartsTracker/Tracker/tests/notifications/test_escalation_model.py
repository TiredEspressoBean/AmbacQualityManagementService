"""Escalation model tests — E1 coverage.

Covers:
  - Policy / step / instance happy-path saves
  - Step order < MAX_ESCALATION_STEPS enforced at clean() and DB
  - Unique (policy, order) enforced
  - Unique (policy, source_ct, source_oid) enforced — no duplicate instance per source
  - GenericForeignKey to source record resolves correctly
  - `is_pending` / `is_terminal` properties
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Companies,
    EscalationInstance,
    EscalationPolicy,
    EscalationStatus,
    EscalationStep,
    MAX_ESCALATION_STEPS,
    Tenant,
)
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import make_tenant_rule


class EscalationPolicyTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Esc Tenant', slug='esc-tenant')
        self.set_tenant_context(self.tenant)
        self.rule = make_tenant_rule(self.tenant, 'ncr.opened')

    def test_one_to_one_with_rule(self):
        policy = EscalationPolicy.objects.create(tenant=self.tenant, rule=self.rule)
        self.assertEqual(self.rule.escalation_policy, policy)

    def test_one_policy_per_rule(self):
        EscalationPolicy.objects.create(tenant=self.tenant, rule=self.rule)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EscalationPolicy.objects.create(tenant=self.tenant, rule=self.rule)


class EscalationStepTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Step Tenant', slug='step-tenant')
        self.set_tenant_context(self.tenant)
        self.rule = make_tenant_rule(self.tenant, 'ncr.opened')
        self.policy = EscalationPolicy.objects.create(tenant=self.tenant, rule=self.rule)

    def _make_step(self, order, delay=3600):
        return EscalationStep.objects.create(
            tenant=self.tenant,
            policy=self.policy,
            order=order,
            delay_seconds=delay,
        )

    def test_three_steps_save(self):
        for i in range(MAX_ESCALATION_STEPS):
            self._make_step(i)
        self.assertEqual(self.policy.steps.count(), MAX_ESCALATION_STEPS)

    def test_step_order_max_rejected_by_clean(self):
        with self.assertRaises(ValidationError) as ctx:
            EscalationStep(
                tenant=self.tenant,
                policy=self.policy,
                order=MAX_ESCALATION_STEPS,  # 3 is out of range (max 0-2)
                delay_seconds=3600,
            ).full_clean()
        self.assertIn('order', ctx.exception.message_dict)

    def test_step_order_max_blocked_by_db_constraint(self):
        """Bypass clean() to confirm the CheckConstraint catches it at the DB."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                from django.db.models import Model
                step = EscalationStep(
                    tenant=self.tenant,
                    policy=self.policy,
                    order=MAX_ESCALATION_STEPS,
                    delay_seconds=3600,
                )
                Model.save(step)

    def test_unique_order_per_policy(self):
        self._make_step(0)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_step(0)

    def test_zero_delay_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            EscalationStep(
                tenant=self.tenant,
                policy=self.policy,
                order=0,
                delay_seconds=0,
            ).full_clean()
        self.assertIn('delay_seconds', ctx.exception.message_dict)

    def test_steps_ordered_by_order(self):
        # Insert out-of-order to verify Meta.ordering kicks in.
        self._make_step(2, delay=24 * 3600)
        self._make_step(0, delay=3600)
        self._make_step(1, delay=4 * 3600)
        orders = list(self.policy.steps.values_list('order', flat=True))
        self.assertEqual(orders, [0, 1, 2])


class EscalationInstanceTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='Inst Tenant', slug='inst-tenant')
        self.set_tenant_context(self.tenant)
        self.rule = make_tenant_rule(self.tenant, 'ncr.opened')
        self.policy = EscalationPolicy.objects.create(tenant=self.tenant, rule=self.rule)
        # Use Companies as the stand-in source record — it's a SecureModel
        # already imported in tests.
        self.source = Companies.objects.create(name='Acme', description='')
        self.source_ct = ContentType.objects.get_for_model(Companies)

    def _make_instance(self, *, next_fire_at=None):
        return EscalationInstance.objects.create(
            tenant=self.tenant,
            policy=self.policy,
            source_content_type=self.source_ct,
            source_object_id=str(self.source.id),
            current_step=0,
            next_fire_at=next_fire_at or timezone.now() + timedelta(hours=1),
            status=EscalationStatus.PENDING,
        )

    def test_happy_path_save(self):
        inst = self._make_instance()
        self.assertEqual(inst.status, EscalationStatus.PENDING)
        self.assertTrue(inst.is_pending)
        self.assertFalse(inst.is_terminal)
        # GenericForeignKey resolves back to the source.
        self.assertEqual(inst.source_record, self.source)

    def test_unique_per_source(self):
        self._make_instance()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._make_instance()

    def test_terminal_statuses(self):
        inst = self._make_instance()
        for status in (
            EscalationStatus.ACKNOWLEDGED,
            EscalationStatus.EXHAUSTED,
            EscalationStatus.CANCELLED,
        ):
            inst.status = status
            self.assertTrue(inst.is_terminal)
            self.assertFalse(inst.is_pending)

    def test_audit_is_appendable_json_list(self):
        inst = self._make_instance()
        inst.audit.append({
            "step": 0,
            "fired_at": timezone.now().isoformat(),
            "recipient_count": 3,
        })
        inst.save(update_fields=['audit'])
        inst.refresh_from_db()
        self.assertEqual(len(inst.audit), 1)
        self.assertEqual(inst.audit[0]["step"], 0)
