"""User decisions and walk findings, 2026-10-20.

1. An auto-opened disposition is unassigned — a queue QA takes from.
2. A quarantined part isn't started: its disposition decides what happens to it. Both
   start paths (claim / start_execution, and creating an execution IN_PROGRESS) refuse,
   and both now also refuse a held or ended work order.
3. Every annotation carries a quality report.
(v) Leaving the rework step (re-inspection passed) clears REWORK_NEEDED.
(w) A captured report records the operator on the job (personnel role OPERATOR), and
    reports read who did what from the role rows (2026-11-04).
"""
from django.core.exceptions import ValidationError
from django.utils import timezone

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


class CompletedByIsWhoDidTheWorkTests(_Fixture):
    """A visit is completed by whoever held it, not whoever triggered the move (a QA
    sign-off, an override approval, a cohort's Complete step) — the traveler prints
    completed_by as the Operator (bug hunt 2026-11-04)."""

    def _two_steps(self):
        process = Processes.objects.create(tenant=self.tenant_a, name="P2", part_type=self.pt)
        first = Steps.objects.create(tenant=self.tenant_a, name="Inspect", part_type=self.pt)
        second = Steps.objects.create(tenant=self.tenant_a, name="Pack", part_type=self.pt)
        ProcessStep.objects.create(process=process, step=first, order=1)
        ProcessStep.objects.create(process=process, step=second, order=2)
        StepEdge.objects.create(process=process, from_step=first, to_step=second,
                                edge_type=EdgeType.DEFAULT)
        WorkOrder.objects.filter(pk=self.wo.pk).update(process=process)
        Parts.objects.filter(pk=self.part.pk).update(step=first, part_status="IN_PROGRESS")
        self.part.refresh_from_db()
        return first

    def test_the_holder_is_credited_not_the_signer(self):
        from Tracker.models import StepTransitionLog, User
        from Tracker.services.mes.parts import advance_part_step
        first = self._two_steps()
        signer = User.objects.create_user(username="maria_s", email="maria_s@tenant-a.com",
                                          password="x", tenant=self.tenant_a)
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=first,
                                          visit_number=1, status="IN_PROGRESS", assigned_to=self.user_a)
        advance_part_step(self.part, operator=signer, skip_gate_check=True)
        ex.refresh_from_db()
        self.assertEqual(ex.completed_by_id, self.user_a.id)
        self.assertTrue(StepTransitionLog.objects.filter(part=self.part, operator=signer).exists(),
                        "who moved it stays on the transition log")

    def test_a_load_from_an_earlier_visit_doesnt_cover_this_one(self):
        """The batch gate took any completed load at the step with the part in it: a part
        back at a wash for another visit passed on its old cycle (hunt 2026-11-05)."""
        import datetime
        from Tracker.models import BatchExecution, SubstepCompletion
        from Tracker.services.dwi.advancement_gate import substep_completion_blockers
        sub = Substep.objects.create(tenant=self.tenant_a, step=self.step, order=0, title="Wash cycle",
                                     scope="BATCH", body_blocks={"type": "doc", "content": []})
        old = BatchExecution.objects.create(tenant=self.tenant_a, work_order=self.wo, step=self.step,
                                            started_by=self.user_a)
        old.parts.add(self.part)
        SubstepCompletion.objects.create(tenant=self.tenant_a, batch_execution=old, substep=sub,
                                         completed_by=self.user_a)
        BatchExecution.objects.filter(pk=old.pk).update(
            completed_at=timezone.now() - datetime.timedelta(days=2))
        visit = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                             visit_number=2, status="IN_PROGRESS")
        blockers = substep_completion_blockers(self.step, visit, self.wo)
        self.assertTrue(any("Wash cycle" in b for b in blockers), blockers)

    def test_rolling_back_a_held_part_settles_its_disposition(self):
        """A rollback may clear a hold (user decision 2026-11-05); it closes the part's
        open disposition with the rollback's reason, so the NCR doesn't say "awaiting
        decision" while the part is worked."""
        from Tracker.services.mes.parts import advance_part_step, rollback_part_step
        first = self._two_steps()
        # An undo inside the window, without approval (steps want approval by default).
        Steps.objects.filter(part_type=self.pt).update(rollback_requires_approval=False)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=first,
                                     visit_number=1, status="IN_PROGRESS", assigned_to=self.user_a)
        advance_part_step(self.part, operator=self.user_a, skip_gate_check=True)
        self.part.refresh_from_db()
        Parts.objects.filter(pk=self.part.pk).update(part_status="QUARANTINED")
        self.part.refresh_from_db()
        disp = QuarantineDisposition.objects.create(tenant=self.tenant_a, part=self.part,
                                                    step=self.part.step, description="Burr")
        rollback_part_step(self.part, self.user_a, reason="Advanced it by mistake")
        self.part.refresh_from_db()
        disp.refresh_from_db()
        self.assertEqual((self.part.step_id, self.part.part_status), (first.id, "IN_PROGRESS"))
        self.assertEqual(disp.current_state, "CLOSED")
        self.assertIn("Settled by a rollback", disp.resolution_notes)
        self.assertIn("Advanced it by mistake", disp.resolution_notes)

    def test_a_same_revisit_goes_back_to_who_worked_the_step_before(self):
        """revisit_assignment's choices are uppercase; this compared lowercase, so SAME
        never took effect. A revisit under SAME is handed to the previous visit's worker;
        a first visit, or any other rule, is unassigned."""
        from Tracker.services.mes.parts import _get_operator_for_step
        first = self._two_steps()
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=first, visit_number=1,
                                     status="COMPLETED", completed_by=self.user_a,
                                     exited_at=timezone.now())
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(first, revisit_assignment="SAME")
        self.assertEqual(_get_operator_for_step(self.part, first, 2), self.user_a)
        self.assertIsNone(_get_operator_for_step(self.part, first, 1), "a first visit isn't a revisit")
        set_gates_from_flags(first, revisit_assignment="ANY")
        self.assertIsNone(_get_operator_for_step(self.part, first, 2))

    def test_with_nobody_holding_it_the_mover_is_credited(self):
        from Tracker.services.mes.parts import advance_part_step
        first = self._two_steps()
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=first,
                                          visit_number=1, status="IN_PROGRESS")
        advance_part_step(self.part, operator=self.user_a, skip_gate_check=True)
        ex.refresh_from_db()
        self.assertEqual(ex.completed_by_id, self.user_a.id)


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
        # ...and the report reads it back: operators_info takes the OPERATOR link, not
        # only the deprecated M2M (which capture never writes).
        from Tracker.serializers.qms import QualityReportsSerializer
        info = QualityReportsSerializer(report, context={}).data["operators_info"]
        self.assertEqual([o["id"] for o in info], [self.user_a.id])


class ReportPersonnelReadsOneRecordTests(_Fixture):
    """Who did what on a report reads from the role rows (QualityReportPersonnel), the
    deprecated detected_by / verified_by / operators columns folded in (2026-11-04)."""

    def _other(self, name="qa_b"):
        from Tracker.models import User
        return User.objects.create_user(username=name, email=f"{name}@tenant-a.com",
                                        password="x", tenant=self.tenant_a)

    def _report(self, **kw):
        return QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                             status="FAIL", **kw)

    def test_an_inspector_is_the_detector_when_no_one_else_is(self):
        from Tracker.serializers.qms import QualityReportsSerializer
        report = self._report()  # e.g. a receiving inspection opened before the column was set
        QualityReportPersonnel.objects.create(quality_report=report, user=self.user_a,
                                              role=PersonnelRole.INSPECTOR)
        self.assertEqual(report.primary_detector, self.user_a)
        self.assertEqual(QualityReportsSerializer(report, context={}).data["detected_by_info"]["id"],
                         self.user_a.id)

    def test_a_signed_second_signature_reads_as_the_verifier(self):
        from django.utils import timezone
        from Tracker.serializers.qms import QualityReportsSerializer
        verifier = self._other()
        report = self._report(detected_by=self.user_a)
        QualityReportPersonnel.objects.create(quality_report=report, user=verifier,
                                              role=PersonnelRole.VERIFIED_BY, signed_at=timezone.now())
        self.assertEqual(QualityReportsSerializer(report, context={}).data["verified_by_info"]["id"],
                         verifier.id, "the column is empty; the signature is the record")

    def test_changing_the_detector_moves_the_role_but_keeps_a_signature(self):
        from django.utils import timezone
        from Tracker.services.qms.quality_report import sync_personnel
        other = self._other()
        report = self._report(detected_by=self.user_a)
        sync_personnel(report)
        signer = self._other("signer")
        QualityReportPersonnel.objects.create(quality_report=report, user=signer,
                                              role=PersonnelRole.DETECTED_BY, signed_at=timezone.now())
        report.detected_by = other
        report.save(update_fields=["detected_by"])
        sync_personnel(report)
        rows = set(QualityReportPersonnel.objects.filter(quality_report=report, role=PersonnelRole.DETECTED_BY)
                   .values_list("user_id", flat=True))
        self.assertEqual(rows, {other.id, signer.id}, "the old unsigned row goes; the signed one stays")
        self.assertEqual(report.primary_detector, signer, "a signed detection reads first")

    def test_filters_find_what_an_inspector_detected(self):
        from Tracker.services.qms.quality_report import detected_by_q
        report = self._report()
        QualityReportPersonnel.objects.create(quality_report=report, user=self.user_a,
                                              role=PersonnelRole.INSPECTOR)
        self._report(detected_by=self.user_a)
        self.assertEqual(QualityReports.objects.filter(detected_by_q(self.user_a)).distinct().count(), 2)


class RevisitRuleEnforcedTests(_Fixture):
    """A step's repeat-visit rule is enforced when the visit is started (user decisions
    2026-11-04): a per-step option (ANY constrains nothing), DIFFERENT / ROLE refuse,
    and a supervisor can authorize past it with a reason, on the record."""

    def _visits(self, rule, *, role=None):
        from Tracker.models import User
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step, revisit_assignment=rule, revisit_role=role)
        self.step.refresh_from_db()
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step, visit_number=1,
                                     status="COMPLETED", completed_by=self.user_a, assigned_to=self.user_a,
                                     exited_at=timezone.now())
        repeat = StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                              visit_number=2, status="PENDING")
        other = User.objects.create_user(username="op_b", email="op_b@tenant-a.com", password="x",
                                         tenant=self.tenant_a)
        sup = User.objects.create_user(username="sup_b", email="sup_b@tenant-a.com", password="x",
                                       tenant=self.tenant_a)
        return repeat, other, sup

    def test_different_refuses_whoever_worked_it_before_unless_a_supervisor_authorizes(self):
        from Tracker.services.mes.lifecycle import OverrideReasonRequired, RevisitRefused, start_execution
        repeat, other, sup = self._visits("DIFFERENT")
        with self.assertRaises(RevisitRefused):
            start_execution(repeat, self.user_a)
        with self.assertRaises(OverrideReasonRequired):
            start_execution(repeat, self.user_a, authorizer=sup, reason="")
        start_execution(repeat, self.user_a, authorizer=sup, reason="Only trained hand on shift")
        repeat.refresh_from_db()
        snap = repeat.training_authorization["revisit_override"]
        self.assertEqual((snap["rule"], snap["authorized_by"], snap["reason"]),
                         ("DIFFERENT", sup.id, "Only trained hand on shift"))
        self.assertNotIn("override", repeat.training_authorization, "not a training override")

    def test_resuming_your_own_visit_keeps_its_start_record(self):
        """A re-claim by the holder re-ran the gates and replaced the snapshot: the
        override given at the real start was lost (hunt 2026-11-05)."""
        from Tracker.services.mes.lifecycle import start_execution
        repeat, other, sup = self._visits("DIFFERENT")
        start_execution(repeat, self.user_a, authorizer=sup, reason="Only trained hand on shift")
        repeat.refresh_from_db()
        before = repeat.training_authorization
        start_execution(repeat, self.user_a)  # Start Work again on the part they hold
        repeat.refresh_from_db()
        self.assertEqual(repeat.training_authorization, before)
        self.assertIn("revisit_override", repeat.training_authorization)

    def test_different_lets_someone_else_start_it(self):
        from Tracker.services.mes.lifecycle import start_execution
        repeat, other, _ = self._visits("DIFFERENT")
        start_execution(repeat, other)
        repeat.refresh_from_db()
        self.assertEqual((repeat.status, repeat.assigned_to_id), ("IN_PROGRESS", other.id))

    def test_role_needs_the_role(self):
        from Tracker.models import TenantGroup, UserRole
        from Tracker.services.mes.lifecycle import RevisitRefused, start_execution
        role = TenantGroup.objects.create(tenant=self.tenant_a, name="Rework Lead")
        repeat, other, _ = self._visits("ROLE", role=role)
        with self.assertRaises(RevisitRefused):
            start_execution(repeat, other)
        UserRole.objects.create(user=other, group=role)
        start_execution(repeat, other)

    def test_any_and_a_first_visit_are_unconstrained(self):
        from Tracker.services.mes.lifecycle import check_revisit_rule
        self._visits("ANY")
        self.assertIsNone(check_revisit_rule(self.part, self.step, self.user_a, visit_number=2))
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step, revisit_assignment="DIFFERENT")
        self.step.refresh_from_db()
        self.assertIsNone(check_revisit_rule(self.part, self.step, self.user_a, visit_number=1))
