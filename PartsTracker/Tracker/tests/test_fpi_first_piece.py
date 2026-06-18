"""First-piece designation + hard-gated Pass on FPI records.

- get-or-create designates the first piece (first part to ENTER the step,
  else lowest ERP_id).
- Pass is hard-gated: it cannot be recorded until the designated first piece
  has actually completed this step's inspection (has an active StepExecution
  and clears can_advance_from_step). Waive stays ungated (the skip escape hatch).
"""
from Tracker.models import (
    FPIRecord,
    FPIStatus,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    StepExecution,
    Steps,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class FpiFirstPieceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        # user_a = approver (holds sign_off_fpi). full_tenant_access: internal
        # staff see all tenant rows (for_user otherwise restricts to
        # order-related records, hiding the FPI).
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['full_tenant_access', 'view_fpirecord', 'add_fpirecord',
             'change_fpirecord', 'sign_off_fpi'],
        )
        # operator = can initiate + run the first piece, but NOT sign off.
        from django.contrib.auth import get_user_model
        self.operator = get_user_model().objects.create_user(
            username='op-fp', email='op-fp@t.test', password='x', tenant=self.tenant_a,
        )
        self.grant_tenant_permissions(
            self.operator, self.tenant_a,
            ['full_tenant_access', 'view_fpirecord', 'add_fpirecord', 'change_fpirecord'],
        )
        self.authenticate_as(self.user_a, self.tenant_a)

        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant_a, name="P", part_type=self.pt)
        # Bare TASK step (no substeps) so can_advance_from_step is True once a
        # part has an active execution — isolates the FPI first-piece gate.
        self.step = Steps.objects.create(
            tenant=self.tenant_a, part_type=self.pt, name="Op1", step_type="TASK",
            requires_first_piece_inspection=True,
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-FP-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2, process=self.process,
        )
        self.p1 = Parts.objects.create(
            tenant=self.tenant_a, ERP_id="P-001", part_type=self.pt,
            work_order=self.wo, step=self.step,
        )
        self.p2 = Parts.objects.create(
            tenant=self.tenant_a, ERP_id="P-002", part_type=self.pt,
            work_order=self.wo, step=self.step,
        )

    def _get_or_create(self):
        return self.client.post(
            "/api/FPIRecords/get-or-create/",
            {"work_order": str(self.wo.id), "step": str(self.step.id)},
            format="json",
        )

    def _start(self, part):
        return StepExecution.objects.create(
            tenant=self.tenant_a, part=part, step=self.step,
            visit_number=1, status="IN_PROGRESS",
        )

    def test_designates_lowest_erp_when_none_started(self):
        resp = self._get_or_create()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["fpi"]["designated_part"], self.p1.id)

    def test_designates_first_to_enter_step(self):
        # p2 enters first → it is the first piece even though p1 has a lower ERP.
        self._start(self.p2)
        resp = self._get_or_create()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["fpi"]["designated_part"], self.p2.id)

    def test_pass_blocked_until_first_piece_starts(self):
        resp = self._get_or_create()
        fpi_id = resp.data["fpi"]["id"]  # designated p1, which has no execution
        r = self.client.post(f"/api/FPIRecords/{fpi_id}/pass/", {}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("not started", r.data["detail"].lower())
        self.assertEqual(FPIRecord.objects.get(id=fpi_id).status, FPIStatus.PENDING)

    def test_pass_succeeds_once_first_piece_complete(self):
        resp = self._get_or_create()
        fpi_id = resp.data["fpi"]["id"]
        self._start(self.p1)  # designated first piece now in progress on a bare step
        r = self.client.post(f"/api/FPIRecords/{fpi_id}/pass/", {}, format="json")
        self.assertEqual(r.status_code, 200, getattr(r, "data", None))
        self.assertEqual(r.data["designated_part"], str(self.p1.id))
        self.assertEqual(FPIRecord.objects.get(id=fpi_id).status, FPIStatus.PASSED)

    def test_operator_cannot_sign_off(self):
        # Operator initiates + runs the first piece, but lacks sign_off_fpi.
        resp = self._get_or_create()
        fpi_id = resp.data["fpi"]["id"]
        self._start(self.p1)
        self.authenticate_as(self.operator, self.tenant_a)
        r = self.client.post(f"/api/FPIRecords/{fpi_id}/pass/", {}, format="json")
        self.assertEqual(r.status_code, 403, getattr(r, "data", None))
        self.assertEqual(FPIRecord.objects.get(id=fpi_id).status, FPIStatus.PENDING)

    def test_check_status_reports_signoff_authority(self):
        self._get_or_create()
        # approver
        r = self.client.get(
            "/api/FPIRecords/check-status/",
            {"work_order": str(self.wo.id), "step": str(self.step.id)},
        )
        self.assertTrue(r.data["can_sign_off"])
        self.assertEqual(r.data["designated_part_id"], str(self.p1.id))
        # operator
        self.authenticate_as(self.operator, self.tenant_a)
        r2 = self.client.get(
            "/api/FPIRecords/check-status/",
            {"work_order": str(self.wo.id), "step": str(self.step.id)},
        )
        self.assertFalse(r2.data["can_sign_off"])

    def test_waive_is_not_gated_on_first_piece(self):
        resp = self._get_or_create()
        fpi_id = resp.data["fpi"]["id"]  # p1 never starts
        r = self.client.post(
            f"/api/FPIRecords/{fpi_id}/waive/",
            {"reason": "Setup verified offline per deviation MRB-12"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, getattr(r, "data", None))
        self.assertEqual(FPIRecord.objects.get(id=fpi_id).status, FPIStatus.WAIVED)
