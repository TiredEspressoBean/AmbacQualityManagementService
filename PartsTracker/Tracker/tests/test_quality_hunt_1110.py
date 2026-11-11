"""Quality hunt, 2026-11-10: regression tests for the fixes.

One class per finding; each docstring names the hunt id.
"""
import datetime
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    CAPA, CalibrationRecord, CapaTasks, CapaVerification, Companies, EquipmentType, Equipments,
    MaterialLot, MeasurementDefinition, MeasurementResult, Parts, PartTypes, QualityReports,
    QuarantineDisposition, RcaRecord, SPCBaseline, StepExecution, Steps, TrainingRecord,
    TrainingRequirement, TrainingType, User, WorkOrder,
)
from Tracker.services.core.clock import tenant_today
from Tracker.tests.base import TenantTestCase


# ---------------------------------------------------------------------------
# Shared CAPA fixture
# ---------------------------------------------------------------------------

class _CapaFixture(TenantTestCase):
    """A MINOR CAPA (no plan approval) with a verified root cause, owned by user_a,
    and a separate verifier so self-verification never applies."""

    def setUp(self):
        super().setUp()
        self.verifier = User.objects.create_user(
            username='hunt-qa', email='qa@hunt1110.test', password='x', tenant=self.tenant_a)
        self.capa = CAPA.objects.create(
            tenant=self.tenant_a, capa_type='CORRECTIVE', severity='MINOR',
            problem_statement="Bores oversize", initiated_by=self.user_a, assigned_to=self.user_a)
        self.rca = RcaRecord.objects.create(
            tenant=self.tenant_a, capa=self.capa, rca_method='FIVE_WHYS',
            problem_description="Bores oversize", root_cause_summary="Worn boring bar",
            root_cause_verification_status='VERIFIED')

    def _task(self, status='NOT_STARTED', description="Re-tool the bore"):
        return CapaTasks.objects.create(
            tenant=self.tenant_a, capa=self.capa, task_type='CORRECTIVE',
            description=description, assigned_to=self.user_a, status=status)

    def _verification(self, **extra):
        return CapaVerification.objects.create(
            tenant=self.tenant_a, capa=self.capa, verification_method="Audit 30 days",
            verification_criteria="No recurrence", **extra)


# ---------------------------------------------------------------------------
# N1 — archived CAPA tasks
# ---------------------------------------------------------------------------

class ArchivedCapaTaskDoesNotCountTests(_CapaFixture):
    """N1: a deleted (archived) open task kept a CAPA from verification — every reader
    counted it."""

    def setUp(self):
        super().setUp()
        self.done = self._task(status='COMPLETED', description="Done")
        self.deleted = self._task(description="Deleted, never done")
        self.deleted.delete()  # soft delete: archives
        self.deleted.refresh_from_db()
        self.assertTrue(self.deleted.archived)

    def test_model_readers_ignore_it(self):
        self.assertTrue(self.capa.all_tasks_completed())
        self.assertFalse(any("task(s) still pending" in b for b in self.capa.get_blocking_items()))
        # 25 (RCA) + 50 (1 of 1 live task done); the archived one would make it 25 + 25.
        self.assertEqual(self.capa.calculate_completion_percentage(), 75)
        self.assertEqual(self.capa.computed_status, 'PENDING_VERIFICATION')

    def test_the_sql_annotation_agrees(self):
        row = CAPA.objects.annotate(_cs=CAPA.computed_status_annotation()).get(pk=self.capa.pk)
        self.assertEqual(row._cs, 'PENDING_VERIFICATION')

    def test_only_archived_tasks_is_no_tasks(self):
        self.done.delete()
        self.assertEqual(self.capa.computed_status, 'IN_PROGRESS')  # RCA exists, no live tasks
        row = CAPA.objects.annotate(_cs=CAPA.computed_status_annotation()).get(pk=self.capa.pk)
        self.assertEqual(row._cs, 'IN_PROGRESS')

    def test_the_api_nested_tasks_omit_it(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_capa', 'view_capatasks', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.get(f"/api/CAPAs/{self.capa.id}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        ids = {t['id'] for t in resp.json()['tasks']}
        self.assertEqual(ids, {str(self.done.id)})


# ---------------------------------------------------------------------------
# #5 / N6 — verify_capa_effectiveness
# ---------------------------------------------------------------------------

class ConfirmingWithOpenTasksTests(_CapaFixture):
    """#5: confirming effectiveness closed the CAPA past its open tasks."""

    def test_confirmed_with_an_open_task_is_refused(self):
        from Tracker.services.qms.capa import verify_capa_effectiveness
        self._task()
        verification = self._verification()
        with self.assertRaisesMessage(ValidationError, "still pending"):
            verify_capa_effectiveness(verification, self.verifier, confirmed=True,
                                      notes="Checked a month of production")
        self.capa.refresh_from_db()
        self.assertNotEqual(self.capa.status, 'CLOSED')

    def test_not_effective_is_still_allowed(self):
        from Tracker.services.qms.capa import verify_capa_effectiveness
        self._task()
        verification = self._verification()
        verify_capa_effectiveness(verification, self.verifier, confirmed=False, notes="Recurred")
        verification.refresh_from_db()
        self.assertEqual(verification.effectiveness_result, 'NOT_EFFECTIVE')

    def test_an_archived_open_task_does_not_block(self):
        from Tracker.services.qms.capa import verify_capa_effectiveness
        self._task(status='COMPLETED')
        self._task().delete()
        verification = self._verification()
        verify_capa_effectiveness(verification, self.verifier, confirmed=True,
                                  notes="Checked a month of production")
        self.capa.refresh_from_db()
        self.assertEqual(self.capa.status, 'CLOSED')


class VerificationDateTests(_CapaFixture):
    """N6: the verification may be recorded with the day it was done (not in the
    future, not before the CAPA was opened); omitted, it is today."""

    def setUp(self):
        super().setUp()
        self.today = tenant_today(self.tenant_a)
        CAPA.objects.filter(pk=self.capa.pk).update(  # tenant-safe: fixture, scoped by pk
            initiated_date=self.today - timedelta(days=30))
        self.capa.refresh_from_db()
        self._task(status='COMPLETED')
        self.verification = self._verification()

    def _verify(self, **kw):
        from Tracker.services.qms.capa import verify_capa_effectiveness
        return verify_capa_effectiveness(self.verification, self.verifier, confirmed=True,
                                         notes="Checked a month of production", **kw)

    def test_a_past_date_is_the_verification_and_closing_date(self):
        on = self.today - timedelta(days=10)
        self._verify(verification_date=on)
        self.verification.refresh_from_db()
        self.capa.refresh_from_db()
        self.assertEqual(self.verification.verification_date, on)
        self.assertEqual((self.capa.status, self.capa.completed_date), ('CLOSED', on))

    def test_the_opening_day_itself_is_allowed(self):
        self._verify(verification_date=self.capa.initiated_date)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.verification_date, self.capa.initiated_date)

    def test_a_future_date_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "future"):
            self._verify(verification_date=self.today + timedelta(days=1))

    def test_a_date_before_the_capa_opened_is_refused(self):
        with self.assertRaisesMessage(ValidationError, "before the CAPA was opened"):
            self._verify(verification_date=self.capa.initiated_date - timedelta(days=1))

    def test_omitted_is_today(self):
        self._verify()
        self.verification.refresh_from_db()
        self.capa.refresh_from_db()
        self.assertEqual(self.verification.verification_date, self.today)
        self.assertEqual(self.capa.completed_date, self.today)

    def test_the_api_takes_the_date(self):
        self.grant_tenant_permissions(self.verifier, self.tenant_a, [
            'view_capa', 'view_capaverification', 'verify_capa', 'change_capaverification',
            'add_capaverification', 'full_tenant_access'])
        self.authenticate_as(self.verifier, self.tenant_a)
        on = self.today - timedelta(days=5)
        url = f"/api/CapaVerifications/{self.verification.id}/verify/"
        bad = self.client.post(url, {'effectiveness_result': 'CONFIRMED', 'notes': 'clean',
                                     'verification_date': 'not-a-date'}, format='json')
        self.assertEqual(bad.status_code, 400, bad.content)
        future = self.client.post(url, {'effectiveness_result': 'CONFIRMED', 'notes': 'clean',
                                        'verification_date': str(self.today + timedelta(days=3))},
                                  format='json')
        self.assertEqual(future.status_code, 400, future.content)
        resp = self.client.post(url, {'effectiveness_result': 'CONFIRMED', 'notes': 'clean',
                                      'verification_date': str(on)}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.verification.refresh_from_db()
        self.capa.refresh_from_db()
        self.assertEqual(self.verification.verification_date, on)
        self.assertEqual(self.capa.completed_date, on)


# ---------------------------------------------------------------------------
# #11 / #17 — CAPA endpoints
# ---------------------------------------------------------------------------

class CapaStatsBySeverityTests(TenantTestCase):
    """#11: by_severity had lowercase keys that never matched a CAPA's severity."""

    def test_by_severity_counts_capas_under_uppercase_keys(self):
        for severity in ('MINOR', 'MINOR', 'MAJOR'):
            CAPA.objects.create(tenant=self.tenant_a, capa_type='CORRECTIVE', severity=severity,
                                problem_statement="Stats", initiated_by=self.user_a,
                                assigned_to=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_capa', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.get("/api/CAPAs/stats/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['by_severity'], {'CRITICAL': 0, 'MAJOR': 1, 'MINOR': 2})


class CapaCompletionPercentageEndpointTests(_CapaFixture):
    """#17: the completion-percentage action called a method that doesn't exist (500)."""

    def test_it_answers_with_the_percentage(self):
        self._task(status='COMPLETED')
        self._task()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_capa', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.get(f"/api/CAPAs/{self.capa.id}/completion-percentage/")
        self.assertEqual(resp.status_code, 200, resp.content)
        # 25 (RCA) + 1 of 2 tasks (25)
        self.assertEqual(resp.json(), {'completion_percentage': 50})


# ---------------------------------------------------------------------------
# N2 / #19 — CAPA report
# ---------------------------------------------------------------------------

class CapaReportStatusAndVerificationTests(_CapaFixture):
    """N2: the report printed the stored status (Open for a CAPA in progress).
    #19: it printed the oldest verification, not the latest."""

    def _context(self):
        from Tracker.reports.adapters.capa_report import CapaReportAdapter
        return CapaReportAdapter().build_context({"id": self.capa.id}, self.user_a, self.tenant_a)

    def test_status_is_the_computed_status(self):
        self._task()
        # The stored field lags the work: still OPEN with a task under way.
        CAPA.objects.filter(pk=self.capa.pk).update(status='OPEN')  # tenant-safe: fixture, scoped by pk
        self.assertEqual(self._context().status, 'IN_PROGRESS')

    def test_the_latest_verification_is_printed(self):
        today = tenant_today(self.tenant_a)
        newer = self._verification(verification_date=today - timedelta(days=2),
                                   verification_notes="second check")
        older = self._verification(verification_date=today - timedelta(days=40),
                                   verification_notes="first check")
        CapaVerification.objects.filter(pk=newer.pk).update(  # tenant-safe: fixture, scoped by pk
            verification_method="Second audit")
        CapaVerification.objects.filter(pk=older.pk).update(  # tenant-safe: fixture, scoped by pk
            verification_method="First audit")
        ctx = self._context()
        self.assertEqual(ctx.verification.verification_method, "Second audit")
        self.assertEqual(ctx.verification.verification_date, today - timedelta(days=2))

    def test_archived_tasks_are_left_off(self):
        kept = self._task(description="Kept")
        self._task(description="Deleted").delete()
        self.assertEqual([t.task_number for t in self._context().tasks], [kept.task_number])


# ---------------------------------------------------------------------------
# #20 — one-sided numeric spec
# ---------------------------------------------------------------------------

class OneSidedSpecTests(TenantTestCase):
    """#20: a NUMERIC definition with only one tolerance raised TypeError (None
    arithmetic) on every reading."""

    def _result(self, value, nominal=Decimal("10"), upper=Decimal("0.5"), lower=None):
        d = MeasurementDefinition(type="NUMERIC", label="Bore", nominal=nominal,
                                  upper_tol=upper, lower_tol=lower)
        return MeasurementResult(definition=d, value_numeric=value)

    def test_upper_only(self):
        self.assertTrue(self._result(10.4).evaluate_spec())
        self.assertTrue(self._result(10.5).evaluate_spec())
        self.assertFalse(self._result(10.6).evaluate_spec())
        self.assertTrue(self._result(2.0).evaluate_spec())  # no lower limit

    def test_lower_only(self):
        self.assertTrue(self._result(9.6, upper=None, lower=Decimal("0.5")).evaluate_spec())
        self.assertFalse(self._result(9.4, upper=None, lower=Decimal("0.5")).evaluate_spec())
        self.assertTrue(self._result(99.0, upper=None, lower=Decimal("0.5")).evaluate_spec())

    def test_two_sided_still_judges_both(self):
        lower = Decimal("0.5")
        self.assertTrue(self._result(10.0, lower=lower).evaluate_spec())
        self.assertFalse(self._result(9.4, lower=lower).evaluate_spec())
        self.assertFalse(self._result(10.6, lower=lower).evaluate_spec())

    def test_no_nominal_is_in_spec(self):
        self.assertTrue(self._result(123.0, nominal=None).evaluate_spec())

    def test_saved_reading_with_upper_only(self):
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        step = Steps.objects.create(tenant=self.tenant_a, name="Flow", part_type=pt)
        md = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, label="Leak", type="NUMERIC", unit="cc", nominal=0,
            upper_tol=Decimal("2"), lower_tol=None, step=step)
        md.refresh_from_db()
        qr = QualityReports.objects.create(tenant=self.tenant_a, step=step, status="PENDING",
                                           detected_by=self.user_a)
        r = MeasurementResult.objects.create(tenant=self.tenant_a, report=qr, definition=md,
                                             value_numeric=3.0, created_by=self.user_a)
        self.assertFalse(r.is_within_spec)


# ---------------------------------------------------------------------------
# N12 — SPC control limits of zero
# ---------------------------------------------------------------------------

class ZeroControlLimitTests(TenantTestCase):
    """N12: a limit of 0 (the range chart's LCL for small subgroups) came back None."""

    def test_xbar_r_zero_lcl(self):
        b = SPCBaseline(chart_type='XBAR_R', xbar_ucl=Decimal("10.5"), xbar_cl=Decimal("10"),
                        xbar_lcl=Decimal("9.5"), range_ucl=Decimal("1.2"), range_cl=Decimal("0.5"),
                        range_lcl=Decimal("0"))
        limits = b.control_limits
        self.assertEqual(limits['rangeLCL'], 0.0)
        self.assertIsNotNone(limits['rangeLCL'])
        self.assertEqual(limits['xBarUCL'], 10.5)

    def test_i_mr_zero_and_missing(self):
        b = SPCBaseline(chart_type='I_MR', individual_ucl=Decimal("1"), individual_cl=Decimal("0"),
                        individual_lcl=Decimal("-1"), mr_ucl=Decimal("0.8"), mr_cl=None)
        limits = b.control_limits
        self.assertEqual(limits['individualCL'], 0.0)
        self.assertIsNone(limits['mrCL'])


# ---------------------------------------------------------------------------
# Parts / work order fixture (N10, N15, N16, #18)
# ---------------------------------------------------------------------------

class _PartFixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Inspect", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-H1110", quantity=2,
                                           workorder_status="IN_PROGRESS")

    def _part(self, erp, step=None, status="IN_PROGRESS"):
        return Parts.objects.create(tenant=self.tenant_a, ERP_id=erp, part_type=self.pt,
                                    work_order=self.wo, step=step or self.step, part_status=status)


class FailedBatchContainedOnceTests(_PartFixture):
    """N10: any later save of a FAIL batch report whose disposition was closed
    re-quarantined the released load and opened a bare second disposition."""

    def test_a_resave_after_the_disposition_closed_does_nothing(self):
        from Tracker.models import BatchExecution
        parts = [self._part("BH-1"), self._part("BH-2")]
        batch = BatchExecution.objects.create(tenant=self.tenant_a, work_order=self.wo,
                                              step=self.step, started_by=self.user_a)
        batch.parts.set(parts)
        qr = QualityReports.objects.create(tenant=self.tenant_a, batch_execution=batch, step=self.step,
                                           status="FAIL", description="cycle fail",
                                           detected_by=self.user_a)
        disp = QuarantineDisposition.objects.get(batch_execution=batch)
        for p in parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, "QUARANTINED")
        # The disposition is decided and closed; the load released.
        QuarantineDisposition.objects.filter(pk=disp.pk).update(  # tenant-safe: fixture, scoped by pk
            current_state="CLOSED")
        Parts.objects.filter(pk__in=[p.pk for p in parts]).update(  # tenant-safe: fixture
            part_status="IN_PROGRESS")

        qr.refresh_from_db()
        qr.capa_decision_note = "No CAPA needed"
        qr.save()

        self.assertEqual(QuarantineDisposition.objects.filter(batch_execution=batch).count(), 1)
        for p in parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, "IN_PROGRESS")


class SupersededPassIsNoPassTests(_PartFixture):
    """N15: a superseded PASS (its capture voided, to be taken again) still counted as
    the part's QA pass at the step."""

    def test_neither_shape_counts_it(self):
        from Tracker.services.qms.qa_status import part_passed_qa_here, with_qa_passed
        part = self._part("QA-1")
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                           status="PASS", detected_by=self.user_a)
        self.assertTrue(part_passed_qa_here(part))
        self.assertTrue(with_qa_passed(Parts.objects.filter(pk=part.pk)).get()._qa_passed)

        QualityReports.objects.filter(pk=qr.pk).update(  # tenant-safe: fixture, scoped by pk
            superseded_at=timezone.now())
        self.assertFalse(part_passed_qa_here(part))
        self.assertFalse(with_qa_passed(Parts.objects.filter(pk=part.pk)).get()._qa_passed)


class VoidedFpiNamesAPartAtTheStepTests(_PartFixture):
    """N16: the re-inspection after a voided pass copied the old first piece, which had
    usually moved on — Pass needs the designated part at the step, so it could only be
    waived."""

    def test_the_fresh_fpi_names_a_part_still_at_the_step(self):
        from Tracker.models import FPIRecord, FPIStatus
        from Tracker.services.qms.fpi import void_fpi_pass
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step, requires_first_piece_inspection=True)
        self.step.refresh_from_db()
        later = Steps.objects.create(tenant=self.tenant_a, name="Pack", part_type=self.pt)
        moved_on = self._part("FP-1", step=later)
        here = self._part("FP-2")
        StepExecution.objects.create(tenant=self.tenant_a, part=here, step=self.step,
                                     visit_number=1, status="IN_PROGRESS")
        fpi = FPIRecord.objects.create(
            tenant=self.tenant_a, work_order=self.wo, step=self.step, part_type=self.pt,
            designated_part=moved_on, status=FPIStatus.PASSED, result="PASS",
            inspected_by=self.user_a, inspected_at=timezone.now())
        fresh = void_fpi_pass(fpi, self.user_a, "Read on the wrong gauge")
        self.assertEqual(fresh.status, FPIStatus.PENDING)
        self.assertEqual(fresh.designated_part_id, here.id)


class FailOnShippedPartTests(_PartFixture):
    """#18: a FAIL report on a shipped part put it back in quarantine."""

    def test_a_shipped_part_stays_shipped(self):
        from Tracker.services.qms.quality_report import on_report_failed
        part = self._part("SH-1", status="SHIPPED")
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                           status="PENDING", detected_by=self.user_a)
        qr.status = "FAIL"
        qr.save()
        self.assertTrue(on_report_failed(qr, "PENDING"))
        part.refresh_from_db()
        self.assertEqual(part.part_status, "SHIPPED")

    def test_a_part_in_production_is_still_quarantined(self):
        from Tracker.services.qms.quality_report import on_report_failed
        part = self._part("SH-2")
        qr = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                           status="PENDING", detected_by=self.user_a)
        qr.status = "FAIL"
        qr.save()
        on_report_failed(qr, "PENDING")
        part.refresh_from_db()
        self.assertEqual(part.part_status, "QUARANTINED")


# ---------------------------------------------------------------------------
# N8 — calibration overdue list
# ---------------------------------------------------------------------------

class FailedGaugeIsNotOverdueTests(TenantTestCase):
    """N8: a gauge whose latest calibration FAILED was listed as overdue as well as
    counted failed, so the list and the stats card disagreed."""

    def test_overdue_lists_only_the_passed_one(self):
        gauge_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer",
                                                  requires_calibration=True)
        today = tenant_today(self.tenant_a)
        records = {}
        for name, result in (("MIC-OK", "PASS"), ("MIC-BAD", "FAIL")):
            eq = Equipments.objects.create(tenant=self.tenant_a, name=name, equipment_type=gauge_type)
            records[name] = CalibrationRecord.objects.create(
                tenant=self.tenant_a, equipment=eq, result=result,
                calibration_date=today - timedelta(days=400), due_date=today - timedelta(days=35))
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_calibrationrecord', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        body = self.client.get("/api/CalibrationRecords/overdue/").json()
        rows = body["results"] if isinstance(body, dict) else body
        self.assertEqual({r["id"] for r in rows}, {str(records["MIC-OK"].id)})


# ---------------------------------------------------------------------------
# #13 — SCAR from a report
# ---------------------------------------------------------------------------

class ScarStampsTheReportTests(TenantTestCase):
    """#13: a SCAR raised from a report left the report's CAPA decision undecided."""

    def test_the_report_reads_promoted(self):
        from Tracker.services.qms.scar import open_scar
        supplier = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Seals")
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="GL-1", material_description="Seal kit",
            quantity=Decimal(10), quantity_remaining=Decimal(10), unit_of_measure="EA",
            supplier=supplier)
        qr = QualityReports.objects.create(tenant=self.tenant_a, material_lot=lot, status="FAIL",
                                           detected_by=self.user_a)
        capa = open_scar(supplier=supplier, problem_statement="Seals torn on receipt",
                         severity="MINOR", quality_report=qr, user=self.user_a)
        qr.refresh_from_db()
        self.assertEqual(qr.capa_decision, "PROMOTED")
        self.assertIn(capa.capa_number, qr.capa_decision_note)


# ---------------------------------------------------------------------------
# #24 — NCR report names who decided, and the lot
# ---------------------------------------------------------------------------

class NcrDecisionAndLotTests(TenantTestCase):
    """#24: the NCR printed neither who authorized the disposition nor the receiving
    lot it was about."""

    def test_context_has_the_decider_and_the_lot(self):
        from Tracker.reports.adapters.ncr import NcrAdapter
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-NCR-7", material_description="Nozzle blanks",
            quantity=Decimal(5), quantity_remaining=Decimal(5), unit_of_measure="EA")
        at = timezone.now()
        qd = QuarantineDisposition.objects.create(
            tenant=self.tenant_a, material_lot=lot, severity="MAJOR",
            disposition_type="RETURN_TO_SUPPLIER", description="Blanks out of spec",
            decision_authorized_by=self.user_a, decision_authorized_at=at)
        ctx = NcrAdapter().build_context({"id": qd.id}, self.user_a, self.tenant_a)
        self.assertEqual(ctx.lot_number, "LOT-NCR-7")
        self.assertEqual(ctx.decision_authorized_by, self.user_a.email)
        self.assertEqual(ctx.decision_authorized_at, at)
        self.assertIsNone(ctx.batch_load)


# ---------------------------------------------------------------------------
# Training: N5, N7, #16
# ---------------------------------------------------------------------------

class _TrainingFixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.cmm = TrainingType.objects.create(tenant=self.tenant_a, name="CMM Operation",
                                               validity_period_days=365)
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Measure", part_type=pt)


class RequirementAddedBackAfterRemovalTests(_TrainingFixture):
    """N5: removing a requirement archives it, and the archived row blocked adding the
    same requirement back for good."""

    def test_the_service_adds_it_back(self):
        from Tracker.services.training import create_training_requirement
        first = create_training_requirement(tenant=self.tenant_a, training_type=self.cmm,
                                            step=self.step)
        first.delete()
        again = create_training_requirement(tenant=self.tenant_a, training_type=self.cmm,
                                            step=self.step)
        self.assertNotEqual(again.pk, first.pk)
        self.assertEqual(TrainingRequirement.objects.filter(
            training_type=self.cmm, step=self.step, archived=False).count(), 1)

    def test_a_live_duplicate_is_still_refused(self):
        from Tracker.services.training import create_training_requirement
        create_training_requirement(tenant=self.tenant_a, training_type=self.cmm, step=self.step)
        with self.assertRaises(ValidationError):
            create_training_requirement(tenant=self.tenant_a, training_type=self.cmm,
                                        step=self.step)

    def test_the_api_adds_it_back(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_trainingrequirement', 'add_trainingrequirement', 'delete_trainingrequirement',
            'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        body = {"training_type": str(self.cmm.id), "step": str(self.step.id)}
        first = self.client.post("/api/TrainingRequirements/", body, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        gone = self.client.delete(f"/api/TrainingRequirements/{first.json()['id']}/")
        self.assertIn(gone.status_code, (200, 204), gone.content)
        again = self.client.post("/api/TrainingRequirements/", body, format="json")
        self.assertEqual(again.status_code, 201, again.content)
        dup = self.client.post("/api/TrainingRequirements/", body, format="json")
        self.assertEqual(dup.status_code, 400, dup.content)


class TrainingRecordReportSkipsDeletedTests(_TrainingFixture):
    """N7: the training record PDF listed deleted (archived) records."""

    def test_archived_records_are_not_in_the_context(self):
        from Tracker.reports.adapters.training_record import TrainingRecordAdapter
        safety = TrainingType.objects.create(tenant=self.tenant_a, name="Safety")
        today = tenant_today(self.tenant_a)
        TrainingRecord.objects.create(tenant=self.tenant_a, user=self.user_a, training_type=self.cmm,
                                      completed_date=today)
        TrainingRecord.objects.create(tenant=self.tenant_a, user=self.user_a, training_type=safety,
                                      completed_date=today).delete()
        ctx = TrainingRecordAdapter().build_context({"user_id": self.user_a.id}, self.user_a,
                                                    self.tenant_a)
        self.assertEqual([r.topic for r in ctx.records], ["CMM Operation"])
        self.assertEqual(ctx.total_count, 1)


class RenewalOnANewerTypeVersionTests(_TrainingFixture):
    """#16: a renewal recorded against a newer version of the training type left the
    old record expiring beside it."""

    def test_the_old_versions_record_is_superseded(self):
        from Tracker.services.training import create_new_training_type_version
        from Tracker.viewsets.training import _not_superseded
        today = tenant_today(self.tenant_a)
        old = TrainingRecord.objects.create(
            tenant=self.tenant_a, user=self.user_a, training_type=self.cmm,
            completed_date=today - timedelta(days=360), expires_date=today + timedelta(days=5))
        v2 = create_new_training_type_version(self.cmm, user=self.user_a,
                                              change_description="Rev B curriculum")
        self.assertNotEqual(v2.pk, self.cmm.pk)
        new = TrainingRecord.objects.create(
            tenant=self.tenant_a, user=self.user_a, training_type=v2,
            completed_date=today, expires_date=today + timedelta(days=365))
        kept = set(_not_superseded(TrainingRecord.objects.filter(pk__in=[old.pk, new.pk]))
                   .values_list('pk', flat=True))
        self.assertEqual(kept, {new.pk})

    def test_another_persons_renewal_does_not_supersede(self):
        from Tracker.services.training import create_new_training_type_version
        from Tracker.viewsets.training import _not_superseded
        other = User.objects.create_user(username='hunt-other', email='o@hunt1110.test',
                                         password='x', tenant=self.tenant_a)
        today = tenant_today(self.tenant_a)
        old = TrainingRecord.objects.create(
            tenant=self.tenant_a, user=self.user_a, training_type=self.cmm,
            completed_date=today - timedelta(days=360), expires_date=today + timedelta(days=5))
        v2 = create_new_training_type_version(self.cmm, user=self.user_a)
        TrainingRecord.objects.create(tenant=self.tenant_a, user=other, training_type=v2,
                                      completed_date=today, expires_date=today + timedelta(days=365))
        kept = set(_not_superseded(TrainingRecord.objects.filter(pk=old.pk))
                   .values_list('pk', flat=True))
        self.assertEqual(kept, {old.pk})


# ---------------------------------------------------------------------------
# R2 — receiving readings in the calibration exposure
# ---------------------------------------------------------------------------

class ReceivingReadingExposureTests(TenantTestCase):
    """R2: a gauge reading taken at receiving (the visit's subject is a lot, not a part)
    was listed with no lot and no report."""

    def test_the_reading_names_its_lot(self):
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import StepExecutionMeasurement
        from Tracker.services.qms.calibration_exposure import exposure_for
        eq_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Bore gauge")
        gauge = Equipments.objects.create(tenant=self.tenant_a, name="BG-1", serial_number="BG-1",
                                          equipment_type=eq_type)
        CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=gauge, result='PASS',
                                         calibration_date=datetime.date(2026, 1, 4),
                                         due_date=datetime.date(2026, 7, 4))
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Blank")
        receiving = Steps.objects.create(tenant=self.tenant_a, name="Receiving inspection",
                                         part_type=pt)
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-R2-1", material_description="Blanks",
            quantity=Decimal(5), quantity_remaining=Decimal(5), unit_of_measure="EA")
        visit = StepExecution.objects.create(
            tenant=self.tenant_a, step=receiving, status="COMPLETED",
            subject_content_type=ContentType.objects.get_for_model(MaterialLot), subject_id=lot.id)
        md = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, label="OD", type="NUMERIC", unit="mm",
            nominal=10, upper_tol=Decimal("0.1"), lower_tol=Decimal("0.1"), step=receiving)
        reading = StepExecutionMeasurement.objects.create(
            tenant=self.tenant_a, step_execution=visit, measurement_definition=md, value=10.02,
            recorded_by=self.user_a, equipment=gauge)
        StepExecutionMeasurement.objects.filter(pk=reading.pk).update(  # tenant-safe: fixture
            recorded_at=timezone.make_aware(datetime.datetime(2026, 3, 3, 12)))
        fail = CalibrationRecord.objects.create(tenant=self.tenant_a, equipment=gauge, result='FAIL',
                                                calibration_date=datetime.date(2026, 7, 1),
                                                due_date=datetime.date(2026, 12, 28))
        rows = exposure_for(fail).reports
        self.assertEqual([(r.part, r.material_lot_id, r.step) for r in rows],
                         [("LOT-R2-1", str(lot.id), "Receiving inspection")])
