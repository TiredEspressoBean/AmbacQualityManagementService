"""A work order becomes IN_PROGRESS when work actually starts on it.

Nothing used to make this transition. `try_advance_lot` accepts PENDING, so a job could
be half-built and still read "Pending" on every board, and the only thing that moved it
was the Control Center's "Release" button — which flipped the status instead of
authorizing the order, ran no readiness check and recorded no releaser.

Splitting the two is the point: `workorder_status` is the FACT that work began,
`released_at` is the AUTHORIZATION that it may. A planner needs both, and
released-but-not-started is precisely the queue workload control manages.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    Companies, Orders, OrdersStatus, Parts, PartsStatus, Tenant, WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.work_order import mark_started
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class MarkStartedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Started", slug="wo-mark-started")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(
                username="starter", email="s@x.test", password="x", tenant=cls.tenant)
            cls.company = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.order = Orders.objects.create(
                tenant=cls.tenant, name="ORD-START", company=cls.company,
                order_status=OrdersStatus.IN_PROGRESS)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _wo(self, status=WorkOrderStatus.PENDING, erp="WO-START-1"):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, quantity=1,
            related_order=self.order, workorder_status=status)
        Parts.objects.create(tenant=self.tenant, ERP_id=f"P-{erp}", work_order=wo,
                             part_status=PartsStatus.IN_PROGRESS)
        return wo

    def test_a_pending_work_order_moves_to_in_progress(self):
        wo = self._wo()
        self.assertTrue(mark_started(wo))
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

    def test_it_is_idempotent_once_already_in_progress(self):
        wo = self._wo(status=WorkOrderStatus.IN_PROGRESS, erp="WO-START-2")
        self.assertFalse(mark_started(wo), "should report no change")
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)

    def test_a_held_work_order_is_not_resurrected(self):
        """Opening a step must not quietly clear a hold someone put on deliberately."""
        wo = self._wo(status=WorkOrderStatus.ON_HOLD, erp="WO-START-3")
        self.assertFalse(mark_started(wo))
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.ON_HOLD)

    def test_a_completed_work_order_is_not_reopened(self):
        wo = self._wo(status=WorkOrderStatus.COMPLETED, erp="WO-START-4")
        self.assertFalse(mark_started(wo))
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.COMPLETED)

    def test_a_cancelled_work_order_is_not_reopened(self):
        wo = self._wo(status=WorkOrderStatus.CANCELLED, erp="WO-START-5")
        self.assertFalse(mark_started(wo))
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.CANCELLED)

    def test_none_is_tolerated(self):
        """A step execution with no work order must not raise here."""
        self.assertFalse(mark_started(None))

    def test_starting_work_does_not_authorize_it(self):
        """The two are independent: starting work records no release.

        If these ever collapse back together, the audit question "who authorized this
        job, and on what basis?" loses its answer again.
        """
        wo = self._wo(erp="WO-START-6")
        mark_started(wo)
        wo.refresh_from_db()
        self.assertEqual(wo.workorder_status, WorkOrderStatus.IN_PROGRESS)
        self.assertIsNone(wo.released_at)
        self.assertIsNone(wo.released_by)
        self.assertEqual(wo.release_override_reason, "")
