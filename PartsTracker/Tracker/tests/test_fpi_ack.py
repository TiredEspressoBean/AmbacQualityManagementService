"""FPI acknowledge loop + request/decided notifications.

A pending FPI is an andon call: sent → seen (acknowledge) → verdict. The
middle state lives on the record so the operator surface can answer
"did QA see this?" without a floor walk.
"""
from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    FPIRecord, FPIStatus, PartTypes, Processes, Steps, WorkOrder, WorkOrderStatus,
)
from Tracker.services.qms.fpi import (
    acknowledge_fpi, notify_fpi_requested, pass_fpi,
)


class FpiAckTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        self.process = Processes.objects.create(
            tenant=self.tenant_a, name="Injector", part_type=self.part_type)
        self.step = Steps.objects.create(
            tenant=self.tenant_a, name="Final Test", part_type=self.part_type, step_type="TASK")
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-FPI-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process)
        self.fpi = FPIRecord.objects.create(
            tenant=self.tenant_a, work_order=self.wo, step=self.step,
            part_type=self.part_type, status=FPIStatus.PENDING)

    def _second_user(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(
            username='qa2', email='qa2@example.com', password='x', tenant=self.tenant_a)

    # -- service --------------------------------------------------------------

    def test_acknowledge_sets_seen_state(self):
        acknowledge_fpi(self.fpi, self.user_a)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.acknowledged_by, self.user_a)
        self.assertIsNotNone(self.fpi.acknowledged_at)
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)  # ack is not a verdict

    def test_acknowledge_is_idempotent_first_wins(self):
        acknowledge_fpi(self.fpi, self.user_a)
        first_at = FPIRecord.objects.get(pk=self.fpi.pk).acknowledged_at

        acknowledge_fpi(self.fpi, self._second_user())
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.acknowledged_by, self.user_a)
        self.assertEqual(self.fpi.acknowledged_at, first_at)

    def test_acknowledge_non_pending_raises(self):
        pass_fpi(self.fpi, self.user_a)
        with self.assertRaises(ValueError):
            acknowledge_fpi(self.fpi, self.user_a)

    def test_requested_and_decided_events_emit(self):
        from Tracker.services.core.notifications.emit import notification_event
        seen = []
        rcv = lambda sender, **kw: seen.append(kw.get("event_code"))
        notification_event.connect(rcv, weak=False)
        try:
            notify_fpi_requested(self.fpi)
            pass_fpi(self.fpi, self.user_a)
        finally:
            notification_event.disconnect(rcv)
        self.assertIn("fpi.requested", seen)
        self.assertIn("fpi.decided", seen)

    # -- API ------------------------------------------------------------------

    def _client(self, perms):
        from rest_framework.test import APIClient
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        return client

    def test_acknowledge_action(self):
        # add_fpirecord: the viewset-wide CRUD gate for POST actions (same as
        # pass/fail/waive); sign_off_fpi: the QA-authority layer on top.
        client = self._client(['view_fpirecord', 'add_fpirecord', 'sign_off_fpi', 'full_tenant_access'])
        response = client.post(f'/api/FPIRecords/{self.fpi.id}/acknowledge/')
        self.assertEqual(response.status_code, 200, response.content)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.acknowledged_by, self.user_a)

    def test_acknowledge_requires_sign_off_perm(self):
        client = self._client(['view_fpirecord', 'add_fpirecord', 'full_tenant_access'])
        response = client.post(f'/api/FPIRecords/{self.fpi.id}/acknowledge/')
        self.assertEqual(response.status_code, 403)
