"""Correcting a false FAIL without rewriting the record (user decision 2026-10-22).

Walked: a FAIL that should have been a PASS. Voiding the capture and re-capturing
rewrote the recorded report FAIL → PASS in place, left its NCR OPEN over a report that
read PASS, and offered no way to close that NCR that fit a finding which was never real.

Now: the void supersedes the report (kept as recorded); the re-capture gets a new one;
the QA manager — not the inspector who recorded or voided it — closes the NCR as "not a
nonconformance", which releases the part.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    PartTypes, Parts, PartsStatus, Processes, ProcessStep, QualityReports,
    QuarantineDisposition, StepExecution, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class FalseFailCorrectionTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Substep, SubstepCompletion, SubstepScope
        self.tenant = Tenant.objects.create(name="FalseFail", slug="false-fail", tier="PRO")
        self.set_tenant_context(self.tenant)
        U = get_user_model()
        self.inspector = U.objects.create_user(username="sarah", email="s@x.test", password="x",
                                               tenant=self.tenant)
        self.manager = U.objects.create_user(username="maria", email="m@x.test", password="x",
                                             tenant=self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        process = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Body Inspection",
                                         step_type="TASK")
        ProcessStep.objects.create(process=process, step=self.step, order=1)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-FF",
                                      workorder_status=WorkOrderStatus.IN_PROGRESS,
                                      quantity=1, process=process)
        self.part = Parts.objects.create(tenant=self.tenant, ERP_id="P-FF", part_type=pt,
                                         work_order=wo, step=self.step,
                                         part_status=PartsStatus.QUARANTINED)
        self.execution = StepExecution.objects.create(tenant=self.tenant, part=self.part,
                                                      step=self.step, visit_number=1,
                                                      status="IN_PROGRESS")
        self.substep = Substep.objects.create(tenant=self.tenant, step=self.step, order=0,
                                              title="Visual body inspection",
                                              scope=SubstepScope.SAMPLED, is_inspection_point=True)
        self.completion = SubstepCompletion.objects.create(
            tenant=self.tenant, step_execution=self.execution, substep=self.substep,
            completed_by=self.inspector)
        self.fail = QualityReports.objects.create(
            tenant=self.tenant, part=self.part, step=self.step, step_execution=self.execution,
            substep=self.substep, status="FAIL", detected_by=self.inspector,
            description="Burr in bore")
        # The FAIL opens its own NCR, as in the real flow; use that one.
        self.ncr = QuarantineDisposition.objects.filter(quality_reports=self.fail).first()
        if self.ncr is None:
            self.ncr = QuarantineDisposition.objects.create(tenant=self.tenant, part=self.part,
                                                            step=self.step)
            self.ncr.quality_reports.add(self.fail)
        self.assertEqual(QuarantineDisposition.objects.filter(part=self.part).count(), 1)

    def _void(self):
        from Tracker.services.qms.report_supersede import void_completion
        void_completion(self.completion, self.inspector, "Misread: burr was a smudge")
        self.fail.refresh_from_db()

    def _recapture_pass(self):
        """The re-inspection, on record before the close (re-inspect first, then close)."""
        from Tracker.services.dwi.operator_capture import _apply_status, ensure_quality_report
        fresh = ensure_quality_report(self.substep, self.execution, self.inspector)
        _apply_status(fresh, {"status": "PASS"})
        return fresh

    def test_a_recorded_verdict_is_not_rewritten_in_place(self):
        from Tracker.services.dwi.operator_capture import _apply_status
        with self.assertRaises(ValidationError):
            _apply_status(self.fail, {"status": "PASS"})
        self.fail.refresh_from_db()
        self.assertEqual(self.fail.status, "FAIL")

    def test_the_void_supersedes_and_the_recapture_writes_a_new_report(self):
        from Tracker.services.dwi.operator_capture import _apply_status, ensure_quality_report
        self._void()
        self.assertEqual(self.fail.status, "FAIL", "kept exactly as recorded")
        self.assertIsNotNone(self.fail.superseded_at)
        self.assertEqual(self.fail.superseded_by, self.inspector)
        self.assertIn("smudge", self.fail.superseded_reason)

        fresh = ensure_quality_report(self.substep, self.execution, self.inspector)
        self.assertNotEqual(fresh.pk, self.fail.pk)
        _apply_status(fresh, {"status": "PASS"})
        fresh.refresh_from_db()
        self.fail.refresh_from_db()
        self.assertEqual(fresh.status, "PASS")
        self.assertEqual(self.fail.replaced_by, fresh)

    def test_the_manager_closes_it_as_not_a_nonconformance_and_the_part_carries_on(self):
        from Tracker.services.qms.disposition import decide_disposition
        self._void()
        self._recapture_pass()
        decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                           authorized_by=self.manager)
        self.ncr.refresh_from_db()
        self.part.refresh_from_db()
        self.assertEqual(self.ncr.current_state, "CLOSED")
        self.assertIn("smudge", self.ncr.resolution_notes)
        self.assertEqual(self.part.part_status, PartsStatus.IN_PROGRESS)

    def test_the_inspector_does_not_clear_their_own_ncr(self):
        from Tracker.services.qms.disposition import decide_disposition
        self._void()
        with self.assertRaisesMessage(ValueError, "someone else"):
            decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                               authorized_by=self.inspector)

    def test_a_standing_finding_cannot_be_closed_as_not_a_nonconformance(self):
        from Tracker.services.qms.disposition import decide_disposition
        with self.assertRaisesMessage(ValueError, "still stands"):
            decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                               authorized_by=self.manager)


class ReopenDispositionTests(FalseFailCorrectionTests):
    def test_a_closed_disposition_is_reopened_with_a_reason(self):
        """Corrections #41 (user decision 2026-10-26): reopened by the QA manager; the
        decision stands until re-decided; the reopen is on the record and in the notes."""
        from Tracker.models import RecordEdit
        from Tracker.services.qms.disposition import decide_disposition, reopen_disposition
        self._void()
        self._recapture_pass()
        decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE", authorized_by=self.manager)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.current_state, "CLOSED")
        with self.assertRaises(ValueError):
            reopen_disposition(self.ncr, self.manager, "")
        reopen_disposition(self.ncr, self.manager, "Closed the wrong NCR")
        self.ncr.refresh_from_db()
        self.assertEqual((self.ncr.current_state, self.ncr.resolution_completed), ("IN_PROGRESS", False))
        self.assertEqual(self.ncr.disposition_type, "NOT_NONCONFORMANCE")
        self.assertIn("reopened — Closed the wrong NCR", self.ncr.resolution_notes)
        self.assertTrue(RecordEdit.objects.filter(object_id=self.ncr.id, field_name="current_state").exists())
        with self.assertRaises(ValueError):
            reopen_disposition(self.ncr, self.manager, "again")


class ScrapRedecisionTests(FalseFailCorrectionTests):
    """Changing a Scrap decision while the disposition is open un-scraps the part, with
    a reason, and both decisions stay on the record (user decision 2026-10-22). It used
    to half-apply: moved to Rework but still SCRAPPED, the Scrap reasoning overwritten."""

    def _scrap(self):
        from Tracker.services.qms.disposition import decide_disposition
        decide_disposition(self.ncr, disposition_type="SCRAP", authorized_by=self.manager,
                           notes="Burr too deep to dress out.")
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, PartsStatus.SCRAPPED)

    def test_changing_scrap_needs_a_reason(self):
        from Tracker.services.qms.disposition import decide_disposition
        self._scrap()
        with self.assertRaisesMessage(ValueError, "say why"):
            decide_disposition(self.ncr, disposition_type="USE_AS_IS", authorized_by=self.manager,
                               customer_approval={"reference": "CONC-9"})

    def test_changing_scrap_unscraps_and_keeps_both_decisions(self):
        from Tracker.services.qms.disposition import decide_disposition
        self._scrap()
        decide_disposition(self.ncr, disposition_type="USE_AS_IS", authorized_by=self.manager,
                           notes="Engineering says the burr is cosmetic.",
                           customer_approval={"reference": "CONC-9"})
        self.part.refresh_from_db()
        self.ncr.refresh_from_db()
        self.assertNotEqual(self.part.part_status, PartsStatus.SCRAPPED)
        self.assertIn("too deep", self.ncr.resolution_notes)
        self.assertIn("changed from Scrap", self.ncr.resolution_notes)
        self.assertIn("cosmetic", self.ncr.resolution_notes)

    def test_an_edit_adds_to_the_notes_rather_than_replacing_them(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from Tracker.serializers.qms import QuarantineDispositionSerializer
        self._scrap()
        self.ncr.refresh_from_db()
        request = Request(APIRequestFactory().patch("/"))
        request.user = self.manager
        ser = QuarantineDispositionSerializer(
            self.ncr, data={"resolution_notes": "A new note."}, partial=True,
            context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        self.ncr.refresh_from_db()
        self.assertIn("too deep", self.ncr.resolution_notes)
        self.assertIn("A new note.", self.ncr.resolution_notes)


class SupersededReportGateTests(FalseFailCorrectionTests):
    def test_a_superseded_report_needs_no_annotation_to_close(self):
        """Closing as not a nonconformance must not demand the withdrawn defect be
        annotated — that would record a defect that wasn't there (re-walk 2026-10-22)."""
        from Tracker.models import QualityErrorsList, QualityReportDefect
        et = QualityErrorsList.objects.create(tenant=self.tenant, error_name="Burr",
                                              error_example="Burr in bore",
                                              part_type=self.part.part_type,
                                              requires_3d_annotation=True)
        QualityReportDefect.objects.create(report=self.fail, error_type=et)
        self.assertTrue(self.ncr.has_pending_annotations()[0])
        self._void()
        self.assertFalse(self.ncr.has_pending_annotations()[0])


class NotNonconformanceCloseTests(FalseFailCorrectionTests):
    def test_a_major_withdrawn_finding_needs_no_containment_to_close(self):
        """Re-walk 2026-10-22: the close demanded a containment action for a
        nonconformance that never existed."""
        from Tracker.services.qms.disposition import decide_disposition
        self.ncr.severity = "MAJOR"
        self.ncr.containment_action = ""
        self.ncr.save(update_fields=["severity", "containment_action"])
        self._void()
        self._recapture_pass()
        decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                           authorized_by=self.manager)
        self.ncr.refresh_from_db()
        self.assertEqual(self.ncr.current_state, "CLOSED")
        self.assertNotIn("..", self.ncr.resolution_notes)


class ReinspectFirstTests(FalseFailCorrectionTests):
    def test_not_a_nonconformance_waits_for_the_re_inspection(self):
        from Tracker.services.qms.disposition import decide_disposition
        from Tracker.serializers.mes_lite import PartsSerializer
        from django.core.exceptions import ValidationError
        from Tracker.services.mes.lifecycle import assert_startable
        # Held and not voided: the start gate refuses.
        with self.assertRaises(ValidationError):
            assert_startable(self.part, None)
        self._void()
        # Held, but startable for its re-capture — the UI flag and the server gate agree
        # (re-walk: the UI ticked it and the claim refused).
        self.assertTrue(PartsSerializer(self.part).data["awaiting_recapture"])
        assert_startable(self.part, None)
        with self.assertRaisesMessage(ValueError, "Re-inspect first"):
            decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                               authorized_by=self.manager)
        self._recapture_pass()
        self.assertFalse(PartsSerializer(self.part).data["awaiting_recapture"])
        decide_disposition(self.ncr, disposition_type="NOT_NONCONFORMANCE",
                           authorized_by=self.manager)
