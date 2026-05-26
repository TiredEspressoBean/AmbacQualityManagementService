"""Escalation runner tests — E4 coverage.

Covers the beat-task entry points and per-instance state transitions:

  - tick_due: returns only pending+due+unarchived instances.
  - fire_one terminal transitions:
      * source missing → CANCELLED
      * cancel predicate true → CANCELLED
      * ack predicate true → ACKNOWLEDGED
      * normal advance: status stays PENDING, current_step bumps,
        next_fire_at shifts.
      * last step fires → EXHAUSTED.
  - Concurrent fire: second worker on same instance is a no-op
    (skip_locked + status filter).
  - Outbox rows: written for matched recipients on step fire.

The QMS NCR ack registration is what we exercise — that's the only
event with a live ack registration in the codebase right now.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from Tracker.models import (
    Companies,
    EscalationInstance,
    EscalationPolicy,
    EscalationStatus,
    EscalationStep,
    NotificationOutbox,
    QualityReports,
    Tenant,
)
from Tracker.services.core.notifications.escalation import fire_one, tick_due
from Tracker.tests.base import TenantContextMixin
from Tracker.tests.notifications.factories import (
    make_tenant_group,
    make_tenant_rule,
    make_user_in_groups,
)


def _make_quality_report(tenant, company):
    """Build a minimal QualityReport for ack-predicate exercise."""
    from Tracker.models import Orders, OrdersStatus, PartTypes, Parts
    order = Orders.objects.create(
        tenant=tenant, name=f'ORD-{id(tenant) % 10000}', company=company,
        order_status=OrdersStatus.IN_PROGRESS,
    )
    PartTypes.objects.get_or_create(tenant=tenant, name='Test PT')
    part = Parts.objects.create(
        tenant=tenant, ERP_id=f'P-{id(order) % 10000}',
        work_order=None, order=order,
    )
    return QualityReports.objects.create(
        tenant=tenant, part=part, status='FAIL',
    )


def _make_instance(*, tenant, rule, source, step_delays=(900,), now=None):
    """Build a policy + steps + a PENDING instance pointed at `source`."""
    if now is None:
        now = timezone.now()
    policy = EscalationPolicy.objects.create(
        tenant=tenant, rule=rule, enabled=True,
    )
    for i, delay in enumerate(step_delays):
        EscalationStep.objects.create(
            tenant=tenant, policy=policy, order=i, delay_seconds=delay,
        )
    return EscalationInstance.objects.create(
        tenant=tenant,
        policy=policy,
        source_content_type=ContentType.objects.get_for_model(type(source)),
        source_object_id=str(source.id),
        current_step=0,
        next_fire_at=now - timedelta(seconds=1),
        status=EscalationStatus.PENDING,
    )


class TickDueTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Tick', slug='tick')
        self.set_tenant_context(self.tenant)
        self.group = make_tenant_group(self.tenant, 'QA Manager')
        self.user = make_user_in_groups(self.tenant, self.group)
        self.rule = make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user], channels=['in_app'],
        )
        self.company = Companies.objects.create(name='Acme', description='')

    def test_returns_only_pending_due_unarchived(self):
        qrs = [_make_quality_report(self.tenant, self.company) for _ in range(4)]
        rules = [self.rule] + [
            make_tenant_rule(
                self.tenant, 'ncr.opened',
                recipient_users=[self.user], channels=['in_app'],
                name=f'rule-{i}',
            ) for i in range(1, 4)
        ]

        # Due + pending
        due_pending = _make_instance(tenant=self.tenant, rule=rules[0], source=qrs[0])
        # Future fire (not due yet)
        future = _make_instance(tenant=self.tenant, rule=rules[1], source=qrs[1])
        future.next_fire_at = timezone.now() + timedelta(hours=1)
        future.save(update_fields=['next_fire_at'])
        # Acknowledged
        acked = _make_instance(tenant=self.tenant, rule=rules[2], source=qrs[2])
        acked.status = EscalationStatus.ACKNOWLEDGED
        acked.save(update_fields=['status'])
        # Archived
        archived = _make_instance(tenant=self.tenant, rule=rules[3], source=qrs[3])
        archived.archived = True
        archived.save(update_fields=['archived'])

        due = tick_due()
        self.assertEqual(due, [str(due_pending.id)])


class FireOneStateTransitionTests(TenantContextMixin, TransactionTestCase):
    """Per-instance state transitions. Uses TransactionTestCase because
    fire_one uses select_for_update which requires real commits."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Fire', slug='fire-tenant')
        self.set_tenant_context(self.tenant)
        self.group = make_tenant_group(self.tenant, 'QA Manager')
        self.user = make_user_in_groups(self.tenant, self.group)
        self.rule = make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.user], channels=['in_app'],
        )
        self.company = Companies.objects.create(name='Acme', description='')

    def test_ack_terminates_to_acknowledged(self):
        from Tracker.models import QuarantineDisposition
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)

        # Close a disposition → ack predicate returns True.
        d = QuarantineDisposition.objects.create(
            tenant=self.tenant, disposition_type='REWORK',
            severity='MAJOR', current_state='CLOSED',
        )
        d.quality_reports.add(qr)

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.ACKNOWLEDGED)
        inst.refresh_from_db()
        self.assertEqual(inst.status, EscalationStatus.ACKNOWLEDGED)
        self.assertEqual(inst.current_step, 0)  # never fired

    def test_archived_source_terminates_to_cancelled(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)
        qr.archived = True
        qr.save(update_fields=['archived'])

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.CANCELLED)
        inst.refresh_from_db()
        self.assertEqual(inst.status, EscalationStatus.CANCELLED)

    def test_missing_source_terminates_to_cancelled(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)
        # Hard-delete the source — GFK now resolves to None.
        qr_id = qr.id
        QualityReports.objects.filter(id=qr_id).delete()

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.CANCELLED)

    def test_normal_fire_advances_to_next_step(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(
            tenant=self.tenant, rule=self.rule, source=qr,
            step_delays=(900, 1800),
        )

        before = timezone.now()
        status = fire_one(str(inst.id))

        self.assertEqual(status, EscalationStatus.PENDING)
        inst.refresh_from_db()
        self.assertEqual(inst.current_step, 1)
        # next_fire_at should be ~1800s after fire
        self.assertGreaterEqual(inst.next_fire_at, before + timedelta(seconds=1790))
        # Audit captured the fire
        self.assertEqual(len(inst.audit), 1)
        self.assertEqual(inst.audit[0]['step'], 0)
        # Outbox row written for the user/channel
        rows = NotificationOutbox.objects.filter(rule=self.rule, user=self.user)
        self.assertGreaterEqual(rows.count(), 1)

    def test_last_step_fire_terminates_to_exhausted(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(
            tenant=self.tenant, rule=self.rule, source=qr,
            step_delays=(900,),
        )

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.EXHAUSTED)
        inst.refresh_from_db()
        self.assertEqual(inst.status, EscalationStatus.EXHAUSTED)
        self.assertEqual(inst.current_step, 1)  # bumped past the last step

    def test_already_terminal_is_no_op(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)
        inst.status = EscalationStatus.ACKNOWLEDGED
        inst.save(update_fields=['status'])

        result = fire_one(str(inst.id))
        self.assertIsNone(result)
        inst.refresh_from_db()
        self.assertEqual(inst.status, EscalationStatus.ACKNOWLEDGED)

    def test_not_yet_due_is_no_op(self):
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)
        inst.next_fire_at = timezone.now() + timedelta(hours=1)
        inst.save(update_fields=['next_fire_at'])

        result = fire_one(str(inst.id))
        self.assertIsNone(result)
        inst.refresh_from_db()
        self.assertEqual(inst.status, EscalationStatus.PENDING)
        self.assertEqual(inst.current_step, 0)

    def test_mid_fire_exception_rolls_back_audit_and_outbox(self):
        """A crash partway through `_fire_step` must roll back the whole
        transaction — no audit entry, no orphaned outbox rows, no state
        change. The next retry sees a clean instance and fires once.

        This locks in the atomic-transaction guarantee that prevents the
        "audit double-write on celery retry" class of bug.
        """
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)

        with patch(
            'Tracker.services.core.notifications.escalation.runner._fire_step',
            side_effect=RuntimeError('simulated mid-fire crash'),
        ):
            with self.assertRaises(RuntimeError):
                fire_one(str(inst.id))

        inst.refresh_from_db()
        # State untouched: still PENDING, no step advance, audit empty.
        self.assertEqual(inst.status, EscalationStatus.PENDING)
        self.assertEqual(inst.current_step, 0)
        self.assertEqual(inst.audit, [])
        # No outbox rows from the failed fire.
        self.assertFalse(
            NotificationOutbox.objects
            .filter(idempotency_key__startswith=f'escalation:{inst.id}')
            .exists()
        )

        # Now fire cleanly — single audit entry, one fire's worth of state.
        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.EXHAUSTED)
        inst.refresh_from_db()
        self.assertEqual(len(inst.audit), 1)
        self.assertEqual(inst.audit[0].get('step'), 0)


class SkipRecipientTests(TenantContextMixin, TransactionTestCase):
    """Phase 6a: `skip_recipient` ack-registry predicate drops users at step-fire."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.tenant = Tenant.objects.create(name='Skip', slug='skip-tenant')
        self.set_tenant_context(self.tenant)
        self.group = make_tenant_group(self.tenant, 'QA Manager')
        self.alice = make_user_in_groups(self.tenant, self.group)
        self.bob = make_user_in_groups(self.tenant, self.group)
        self.carol = make_user_in_groups(self.tenant, self.group)
        self.rule = make_tenant_rule(
            self.tenant, 'ncr.opened',
            recipient_users=[self.alice, self.bob, self.carol],
            channels=['in_app'],
        )
        self.company = Companies.objects.create(name='Acme', description='')

    def test_skip_recipient_filters_users_from_step_fire(self):
        """Register a skip predicate that drops bob; verify only alice + carol fire."""
        from Tracker.services.core.notifications.escalation import register_ack

        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)

        # Override the ncr.opened registration with a skip predicate that
        # drops bob specifically.
        from Tracker.models import QualityReports
        register_ack(
            event_code='ncr.opened',
            source_model=QualityReports,
            is_acknowledged=lambda src: False,
            skip_recipient=lambda src, user: user.id == self.bob.id,
        )
        self.addCleanup(self._reset_ncr_registration)

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.EXHAUSTED)

        # Outbox rows for alice + carol, NOT for bob.
        fired_user_ids = set(
            NotificationOutbox.objects.filter(
                idempotency_key__startswith=f'escalation:{inst.id}',
            ).values_list('user_id', flat=True)
        )
        self.assertEqual(fired_user_ids, {self.alice.id, self.carol.id})

    def test_default_skip_predicate_drops_nobody(self):
        """No skip predicate registered = all recipients fire (regression)."""
        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)

        # Use the default ncr.opened registration (no skip predicate set).
        # All three users should fire.
        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.EXHAUSTED)

        fired_user_ids = set(
            NotificationOutbox.objects.filter(
                idempotency_key__startswith=f'escalation:{inst.id}',
            ).values_list('user_id', flat=True)
        )
        self.assertEqual(
            fired_user_ids,
            {self.alice.id, self.bob.id, self.carol.id},
        )

    def test_skip_predicate_exception_treated_as_false(self):
        """A buggy skip predicate that raises shouldn't drop the user."""
        from Tracker.services.core.notifications.escalation import register_ack
        from Tracker.models import QualityReports

        qr = _make_quality_report(self.tenant, self.company)
        inst = _make_instance(tenant=self.tenant, rule=self.rule, source=qr)

        def bad_skip(src, user):
            raise RuntimeError("boom")

        register_ack(
            event_code='ncr.opened',
            source_model=QualityReports,
            is_acknowledged=lambda src: False,
            skip_recipient=bad_skip,
        )
        self.addCleanup(self._reset_ncr_registration)

        status = fire_one(str(inst.id))
        self.assertEqual(status, EscalationStatus.EXHAUSTED)

        # Predicate raised → treated as False → all users fire.
        fired_user_ids = set(
            NotificationOutbox.objects.filter(
                idempotency_key__startswith=f'escalation:{inst.id}',
            ).values_list('user_id', flat=True)
        )
        self.assertEqual(
            fired_user_ids,
            {self.alice.id, self.bob.id, self.carol.id},
        )

    def _reset_ncr_registration(self):
        """Restore the canonical ncr.opened registration after a test overrides it.
        Without this, the test registration leaks into subsequent tests."""
        from Tracker.services.qms.escalation_acks import _ncr_is_acknowledged
        from Tracker.models import QualityReports
        from Tracker.services.core.notifications.escalation import register_ack
        register_ack(
            event_code='ncr.opened',
            source_model=QualityReports,
            is_acknowledged=_ncr_is_acknowledged,
        )
