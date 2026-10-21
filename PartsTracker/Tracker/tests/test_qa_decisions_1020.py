"""User decisions and walk findings, 2026-10-20.

1. An auto-opened disposition is unassigned — a queue QA takes from.
2. A quarantined part isn't started: its disposition decides what happens to it. Both
   start paths (claim / start_execution, and creating an execution IN_PROGRESS) refuse,
   and both now also refuse a held or ended work order.
3. Every annotation carries a quality report.
(v) Leaving the rework step (re-inspection passed) clears REWORK_NEEDED.
(w) A captured report records the operator on the job (personnel role OPERATOR).
"""
from django.core.exceptions import ValidationError

from Tracker.models import (
    Parts, PartTypes, PersonnelRole, Processes, ProcessStep, QualityReportPersonnel,
    QualityReports, QuarantineDisposition, StepEdge, StepExecution, Steps, Substep,
    ThreeDModel, WorkOrder,
)
from Tracker.models.mes_lite import EdgeType
from Tracker.services.mes.lifecycle import start_execution
from Tracker.tests.base import TenantTestCase


class _Fixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Assemble", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-DEC-1", quantity=1,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="DEC-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step, part_status="IN_PROGRESS")


class UnassignedDispositionTests(_Fixture):

    def test_a_fail_report_opens_an_unassigned_disposition_in_the_queue(self):
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="FAIL", detected_by=self.user_a)
        disp = QuarantineDisposition.objects.get(quality_reports=qr)
        self.assertIsNone(disp.assigned_to_id)
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_quarantinedisposition', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        ids = [r["id"] for r in self.client.get(
            "/api/QuarantineDispositions/", {"assigned_to__isnull": "true"}).json()["results"]]
        self.assertIn(str(disp.id), ids)


class OneFindingOneDispositionTests(_Fixture):
    """Two failed reports on one visit (a visual with a defect, a measurement out)
    are one finding: the second joins the open disposition (walk 2026-10-20). A new
    visit is a new finding."""

    def _fail(self):
        return QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                             status="FAIL", detected_by=self.user_a)

    def test_a_second_failure_on_the_same_visit_joins_the_open_disposition(self):
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     visit_number=1, status="IN_PROGRESS")
        visual, bore = self._fail(), self._fail()
        disp, = QuarantineDisposition.objects.filter(part=self.part)
        self.assertEqual(set(disp.quality_reports.all()), {visual, bore})

    def test_a_new_visit_opens_its_own(self):
        from datetime import timedelta
        from django.utils import timezone
        first = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                             visit_number=1, status="COMPLETED")
        self._fail()
        StepExecution.objects.filter(pk=first.pk).update(
            entered_at=timezone.now() - timedelta(hours=2), exited_at=timezone.now() - timedelta(hours=1))
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     visit_number=2, status="IN_PROGRESS")
        self._fail()
        self.assertEqual(QuarantineDisposition.objects.filter(part=self.part).count(), 2)


class DecidingADispositionTests(_Fixture):
    """QA Manager module 2 walk (2026-10-20)."""

    def _disposition(self, step=None):
        return QuarantineDisposition.objects.create(
            tenant=self.tenant_a, part=self.part, step=step or self.step, assigned_to=self.user_a)

    def test_releasing_waits_for_every_open_decision_on_the_part(self):
        from Tracker.services.qms.disposition import decide_disposition
        Parts.objects.filter(pk=self.part.pk).update(part_status="QUARANTINED")
        other_step = Steps.objects.create(tenant=self.tenant_a, name="Test", part_type=self.pt)
        first, second = self._disposition(), self._disposition(other_step)
        decide_disposition(first, disposition_type="USE_AS_IS", authorized_by=self.user_a,
                           customer_approval={"reference": "ENG-CONC-0041"})
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "QUARANTINED")   # the second is undecided
        decide_disposition(second, disposition_type="USE_AS_IS", authorized_by=self.user_a,
                           customer_approval={"reference": "ENG-CONC-0042"})
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "IN_PROGRESS")

    def test_an_edit_does_not_clear_the_recorded_approval_date(self):
        from Tracker.services.qms.disposition import decide_disposition
        disp = self._disposition()
        decide_disposition(disp, disposition_type="USE_AS_IS", authorized_by=self.user_a,
                           customer_approval={"reference": "ENG-CONC-0041", "date": None})
        disp.refresh_from_db()
        self.assertIsNotNone(disp.customer_approval_date)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_quarantinedisposition', 'change_quarantinedisposition', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.patch(f"/api/QuarantineDispositions/{disp.id}/",
                                 {"customer_approval_date": None, "resolution_notes": "Concession on file"},
                                 format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        disp.refresh_from_db()
        self.assertIsNotNone(disp.customer_approval_date)

    def test_the_description_names_the_failing_reading(self):
        from Tracker.models import MeasurementDefinition, MeasurementResult
        bore = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, label="Bore Diameter", type="NUMERIC", unit="mm",
            nominal=4.0, upper_tol=0.005, lower_tol=0.005, step=self.step)
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="PENDING", detected_by=self.user_a)
        MeasurementResult.objects.create(tenant=self.tenant_a, report=qr, definition=bore,
                                         value_numeric=4.007, created_by=self.user_a)
        qr.status = "FAIL"
        qr.save()
        disp = QuarantineDisposition.objects.get(quality_reports=qr)
        self.assertEqual(disp.description, "Failed Assemble: Bore Diameter 4.007 mm (limits 3.995–4.005)")


class QuarantinedPartIsNotStartedTests(_Fixture):

    def test_start_names_the_disposition(self):
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="FAIL", detected_by=self.user_a)
        disp = QuarantineDisposition.objects.get(quality_reports=qr)
        Parts.objects.filter(pk=self.part.pk).update(part_status="QUARANTINED")
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                          visit_number=1, status="PENDING")
        ex = StepExecution.objects.get(pk=ex.pk)  # as the claim action loads it: fresh part
        with self.assertRaises(ValidationError) as ctx:
            start_execution(ex, self.user_a)
        self.assertIn(disp.disposition_number, " ".join(ctx.exception.messages))

    def test_the_create_path_refuses_too(self):
        Parts.objects.filter(pk=self.part.pk).update(part_status="QUARANTINED")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_stepexecution', 'add_stepexecution', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post("/api/StepExecutions/", {
            "part": str(self.part.id), "step": str(self.step.id), "status": "IN_PROGRESS"},
            format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("quarantined", str(resp.json()))

    def test_the_create_path_refuses_a_held_work_order(self):
        WorkOrder.objects.filter(pk=self.wo.pk).update(workorder_status="CANCELLED")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_stepexecution', 'add_stepexecution', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post("/api/StepExecutions/", {
            "part": str(self.part.id), "step": str(self.step.id), "status": "IN_PROGRESS"},
            format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("cancelled", str(resp.json()))


class AnnotationNeedsAReportTests(_Fixture):

    def setUp(self):
        super().setUp()
        self.model = ThreeDModel.objects.create(tenant=self.tenant_a, name="Body", file="", part_type=self.pt,
                                                processing_status="COMPLETED")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_heatmapannotations', 'add_heatmapannotations', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _post(self, reports):
        return self.client.post("/api/HeatMapAnnotation/", {
            "model": str(self.model.id), "part": str(self.part.id), "quality_reports": reports,
            "position_x": 0, "position_y": 0, "position_z": 0,
            "defect_type": "crack", "severity": "LOW"}, format="json")

    def test_an_annotation_without_a_report_is_refused(self):
        resp = self._post([])
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("quality_reports", resp.json())

    def test_an_annotation_with_its_report_is_accepted(self):
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                           status="FAIL", detected_by=self.user_a)
        self.assertEqual(self._post([str(qr.id)]).status_code, 201)


class LeavingReworkTests(_Fixture):

    def test_leaving_the_rework_step_clears_the_rework_status(self):
        from Tracker.services.mes.parts import advance_part_step
        process = Processes.objects.create(tenant=self.tenant_a, name="P", part_type=self.pt)
        rework = Steps.objects.create(tenant=self.tenant_a, name="Rework", part_type=self.pt,
                                      step_type="REWORK")
        nozzle = Steps.objects.create(tenant=self.tenant_a, name="Nozzle", part_type=self.pt)
        ProcessStep.objects.create(process=process, step=rework, order=1)
        ProcessStep.objects.create(process=process, step=nozzle, order=2)
        StepEdge.objects.create(process=process, from_step=rework, to_step=nozzle,
                                edge_type=EdgeType.DEFAULT)
        WorkOrder.objects.filter(pk=self.wo.pk).update(process=process)
        Parts.objects.filter(pk=self.part.pk).update(step=rework, part_status="REWORK_NEEDED")
        self.part.refresh_from_db()
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=rework,
                                     visit_number=1, status="IN_PROGRESS")
        advance_part_step(self.part, operator=self.user_a, skip_gate_check=True)
        self.part.refresh_from_db()
        self.assertEqual((self.part.step_id, self.part.part_status), (nozzle.id, "IN_PROGRESS"))


class CapturedReportRecordsTheOperatorTests(_Fixture):

    def test_the_operator_on_the_job_is_on_the_report(self):
        from Tracker.services.dwi.operator_capture import ensure_quality_report
        sub = Substep.objects.create(tenant=self.tenant_a, step=self.step, order=0, title="Inspect",
                                     is_inspection_point=True, body_blocks={"type": "doc", "content": []})
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                          visit_number=1, status="IN_PROGRESS", assigned_to=self.user_a)
        report = ensure_quality_report(sub, ex, user=self.user_a)
        self.assertTrue(QualityReportPersonnel.objects.filter(
            quality_report=report, user=self.user_a, role=PersonnelRole.OPERATOR).exists())
