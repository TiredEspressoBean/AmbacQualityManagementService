"""Escalation ack registry tests — E2 coverage.

Covers:
  - register_ack stores the predicate; lookup by event_code returns it
  - is_acknowledged / is_cancelled run the registered predicates
  - Default cancel predicate handles SecureModel.archived
  - Unregistered events return False (don't escalate, don't crash)
  - Predicate exceptions are caught and logged (defense in depth — a
    buggy domain predicate shouldn't poison the beat task)
  - The v1 `ncr.opened` registration's predicate matches the QMS
    semantics (closed QuarantineDisposition = ack; OPEN = not ack)
"""
from __future__ import annotations

from django.test import TestCase

from Tracker.models import (
    Companies,
    QualityReports,
    QuarantineDisposition,
    Tenant,
)
from Tracker.services.core.notifications.escalation import (
    AckRegistration,
    get_ack_registration,
    is_acknowledged,
    is_cancelled,
    list_acknowledged_events,
    register_ack,
)
from Tracker.tests.base import TenantContextMixin


class _SourceModelStub:
    """Stand-in class for registry-mechanics tests. The registry stores
    source_model as a type but doesn't introspect it; tests can use this
    sentinel without needing a real Django model."""


class AckRegistryTests(TestCase):
    """Pure registry tests with stub predicates."""

    def test_register_and_lookup(self):
        register_ack(
            event_code='__test_register_lookup__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda src: True,
        )
        reg = get_ack_registration('__test_register_lookup__')
        self.assertIsNotNone(reg)
        self.assertIsInstance(reg, AckRegistration)
        self.assertEqual(reg.event_code, '__test_register_lookup__')
        self.assertIs(reg.source_model, _SourceModelStub)

    def test_lookup_unknown_returns_none(self):
        self.assertIsNone(get_ack_registration('__no_such_event__'))

    def test_is_acknowledged_runs_predicate(self):
        calls = []

        def pred(src):
            calls.append(src)
            return True

        register_ack(
            event_code='__test_ack_call__',
            source_model=_SourceModelStub,
            is_acknowledged=pred,
        )
        self.assertTrue(is_acknowledged('__test_ack_call__', "sentinel"))
        self.assertEqual(calls, ["sentinel"])

    def test_is_acknowledged_unregistered_event_returns_false(self):
        self.assertFalse(is_acknowledged('__no_registration__', object()))

    def test_predicate_exception_returns_false(self):
        def bad(src):
            raise RuntimeError("boom")

        register_ack(
            event_code='__test_bad_pred__',
            source_model=_SourceModelStub,
            is_acknowledged=bad,
        )
        # Should log + swallow, not propagate.
        self.assertFalse(is_acknowledged('__test_bad_pred__', object()))

    def test_default_cancel_predicate_checks_archived(self):
        class _Stub:
            archived = False

        stub = _Stub()
        register_ack(
            event_code='__test_default_cancel__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: False,
        )
        self.assertFalse(is_cancelled('__test_default_cancel__', stub))
        stub.archived = True
        self.assertTrue(is_cancelled('__test_default_cancel__', stub))

    def test_custom_cancel_predicate(self):
        register_ack(
            event_code='__test_custom_cancel__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: False,
            is_cancelled=lambda src: src == "cancel-me",
        )
        self.assertTrue(is_cancelled('__test_custom_cancel__', "cancel-me"))
        self.assertFalse(is_cancelled('__test_custom_cancel__', "other"))

    def test_overwrite_replaces_registration(self):
        register_ack(
            event_code='__test_overwrite__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: True,
        )
        self.assertTrue(is_acknowledged('__test_overwrite__', None))
        register_ack(
            event_code='__test_overwrite__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: False,
        )
        self.assertFalse(is_acknowledged('__test_overwrite__', None))

    def test_list_acknowledged_events_returns_sorted(self):
        register_ack(
            event_code='__zzz_test__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: True,
        )
        register_ack(
            event_code='__aaa_test__',
            source_model=_SourceModelStub,
            is_acknowledged=lambda _: True,
        )
        codes = list_acknowledged_events()
        # Both test events appear; the alphabetical order means aaa < zzz.
        self.assertIn('__aaa_test__', codes)
        self.assertIn('__zzz_test__', codes)
        self.assertLess(codes.index('__aaa_test__'), codes.index('__zzz_test__'))


class NCRAckPredicateTests(TenantContextMixin, TestCase):
    """The v1 `ncr.opened` registration must match QMS semantics:
    closed QuarantineDisposition = ack; OPEN disposition = not ack;
    no disposition = not ack."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name='NCR Tenant', slug='ncr-tenant')
        self.set_tenant_context(self.tenant)
        self.company = Companies.objects.create(name='Acme', description='')
        # QualityReports requires a Part. Build a minimal one inline.
        from Tracker.models import Orders, OrdersStatus, PartTypes, Parts
        self.order = Orders.objects.create(
            tenant=self.tenant, name='ORD-1', company=self.company,
            order_status=OrdersStatus.IN_PROGRESS,
        )
        self.part_type = PartTypes.objects.create(
            tenant=self.tenant, name='Test Part Type',
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id='P-1',
            work_order=None, order=self.order,
        )
        self.qr = QualityReports.objects.create(
            tenant=self.tenant, part=self.part, status='FAIL',
        )

    def test_no_disposition_is_not_acked(self):
        self.assertFalse(is_acknowledged('ncr.opened', self.qr))

    def test_open_disposition_is_not_acked(self):
        d = QuarantineDisposition.objects.create(
            tenant=self.tenant,
            disposition_type='REWORK',
            severity='MAJOR',
            current_state='OPEN',
        )
        d.quality_reports.add(self.qr)
        self.assertFalse(is_acknowledged('ncr.opened', self.qr))

    def test_closed_disposition_is_acked(self):
        d = QuarantineDisposition.objects.create(
            tenant=self.tenant,
            disposition_type='REWORK',
            severity='MAJOR',
            current_state='CLOSED',
        )
        d.quality_reports.add(self.qr)
        self.assertTrue(is_acknowledged('ncr.opened', self.qr))

    def test_archived_qr_is_cancelled_via_default_predicate(self):
        # QualityReports inherits SecureModel; void()/archived flips
        # the default cancel predicate.
        self.qr.archived = True
        self.qr.save(update_fields=['archived'])
        self.assertTrue(is_cancelled('ncr.opened', self.qr))
