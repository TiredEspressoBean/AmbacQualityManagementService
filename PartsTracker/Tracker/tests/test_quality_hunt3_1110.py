"""Quality hunt round 3 (2026-11-10): regression tests. One class per finding."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    CalibrationRecord, CapaTasks, EquipmentType, Equipments, MeasurementDefinition, Parts,
    QualityReports, QuarantineDisposition, StepExecution,
)
from Tracker.services.core.clock import tenant_today
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_quality_hunt_1110 import _CapaFixture, _PartFixture


class TaskCompletedOnlyByTheActionTests(_CapaFixture):
    """#1: an edit set a task COMPLETED, skipping sign-off, assignees and stamps."""

    def test_an_edit_cant_complete_or_reopen_a_task(self):
        from Tracker.serializers.qms import CapaTasksSerializer
        task = self._task()
        ser = CapaTasksSerializer(task, data={'status': 'COMPLETED'}, partial=True)
        self.assertFalse(ser.is_valid())
        self.assertIn('status', ser.errors)
        done = self._task(status='COMPLETED', description="Done one")
        ser = CapaTasksSerializer(done, data={'status': 'NOT_STARTED'}, partial=True)
        self.assertFalse(ser.is_valid())


class CancelledTaskDoesntBlockTests(_CapaFixture):
    """#2: a cancelled task counted as open, so the CAPA could never close."""

    def test_cancelled_is_done_with(self):
        self._task(status='COMPLETED')
        self._task(status='CANCELLED', description="Not needed after all")
        self.assertTrue(self.capa.all_tasks_completed())
        self.assertFalse([b for b in self.capa.get_blocking_items() if "task" in b])
        self.assertEqual(self.capa.calculate_completion_percentage(), 75)


class NotEffectiveReopensTheRcaTests(_CapaFixture):
    """#3: "Not effective" left the RCA VERIFIED (locked, rca_verified() true)."""

    def test_the_rca_goes_back_to_unverified(self):
        from Tracker.models import CapaVerification
        from Tracker.services.qms.capa import verify_capa_effectiveness
        v = CapaVerification.objects.create(
            tenant=self.tenant_a, capa=self.capa, verification_method="Audit",
            verification_criteria="No recurrence")
        verify_capa_effectiveness(v, self.verifier, confirmed=False, notes="It came back")
        self.rca.refresh_from_db()
        self.assertEqual(self.rca.root_cause_verification_status, 'UNVERIFIED')
        self.assertEqual(self.rca.rca_review_status, 'REQUIRED')
        self.capa.refresh_from_db()
        self.assertFalse(self.capa.rca_verified())


class SecondFailureNewDecisionTests(_PartFixture):
    """#7: a second failure in the same visit joined the already-decided disposition."""

    def test_a_decided_disposition_isnt_joined(self):
        from Tracker.services.qms.disposition import open_disposition_for_failed_report
        part = self._part("D-7")
        StepExecution.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                     visit_number=1, status="IN_PROGRESS")
        first = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                              status="FAIL")
        d1 = QuarantineDisposition.objects.filter(quality_reports=first).first() \
            or open_disposition_for_failed_report(first)
        QuarantineDisposition.objects.filter(pk=d1.pk).update(  # tenant-safe: fixture, scoped by pk
            disposition_type="USE_AS_IS", current_state="IN_PROGRESS")
        second = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                               status="PENDING")
        d2 = open_disposition_for_failed_report(second)
        self.assertNotEqual(d2.pk, d1.pk, "the new finding gets its own decision")


class SecondBatchReportLinkedTests(_PartFixture):
    """#8: a second FAIL report on a load wasn't linked to its open disposition, so a
    later save re-contained the load (gap in N10)."""

    def test_the_second_report_joins_the_load_disposition(self):
        from Tracker.models import BatchExecution, Substep
        parts = [self._part("B8-1"), self._part("B8-2")]
        batch = BatchExecution.objects.create(tenant=self.tenant_a, work_order=self.wo,
                                              step=self.step, started_by=self.user_a)
        batch.parts.set(parts)
        s1 = Substep.objects.create(tenant=self.tenant_a, step=self.step, title="Temp", order=1)
        s2 = Substep.objects.create(tenant=self.tenant_a, step=self.step, title="Time", order=2)
        QualityReports.objects.create(tenant=self.tenant_a, batch_execution=batch, step=self.step,
                                      substep=s1, status="FAIL", detected_by=self.user_a)
        second = QualityReports.objects.create(tenant=self.tenant_a, batch_execution=batch,
                                               step=self.step, substep=s2, status="FAIL",
                                               detected_by=self.user_a)
        disp = QuarantineDisposition.objects.get(batch_execution=batch)
        self.assertIn(second, disp.quality_reports.all())
        QuarantineDisposition.objects.filter(pk=disp.pk).update(  # tenant-safe: fixture
            current_state="CLOSED")
        Parts.objects.filter(pk__in=[p.pk for p in parts]).update(  # tenant-safe: fixture
            part_status="IN_PROGRESS")
        second.refresh_from_db()
        second.save()
        self.assertEqual(QuarantineDisposition.objects.filter(batch_execution=batch).count(), 1)
        for p in parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, "IN_PROGRESS")


class _Gauge(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.today = tenant_today(self.tenant_a)
        gt = EquipmentType.objects.create(tenant=self.tenant_a, name="Caliper",
                                          requires_calibration=True)
        self.gauge = Equipments.objects.create(tenant=self.tenant_a, name="CAL-19", equipment_type=gt)

    def _cal(self, result, days_ago, gauge=None):
        return CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=gauge or self.gauge, result=result,
            calibration_date=self.today - timedelta(days=days_ago),
            due_date=self.today + timedelta(days=365 - days_ago))


class EditedGaugeKeepsItsHistoryTests(_Gauge):
    """#19: editing a gauge (a new version) cut it off from its calibrations."""

    def test_the_new_version_reads_its_history(self):
        self._cal("FAIL", days_ago=5)
        new = self.gauge.create_new_version(name="CAL-19 (relabelled)")
        self.assertEqual(new.get_latest_calibration().result, "FAIL")
        self.assertEqual(new.calibration_status, "FAILED")
        latest = list(CalibrationRecord.objects.filter(
            equipment_id__in=[self.gauge.pk, new.pk]).latest_per_equipment())
        self.assertEqual(len(latest), 1, "one gauge, one latest")


class OldRecordDoesntRestoreServiceTests(_Gauge):
    """#20: saving an old PASS record put a failed gauge back in service."""

    def test_only_the_latest_decides(self):
        from Tracker.models.mes_standard import EquipmentStatus
        old_pass = self._cal("PASS", days_ago=200)
        self._cal("FAIL", days_ago=2)
        self.gauge.refresh_from_db()
        self.assertEqual(self.gauge.status, EquipmentStatus.OUT_OF_SERVICE)
        old_pass.notes = "Cert scanned"
        old_pass.save()
        self.gauge.refresh_from_db()
        self.assertEqual(self.gauge.status, EquipmentStatus.OUT_OF_SERVICE)


class OneSidedStepReadingTests(_PartFixture):
    """#14: a step reading against a max-only spec never got a verdict."""

    def test_max_only(self):
        from Tracker.models import StepExecutionMeasurement
        d = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.step, label="Runout", type="NUMERIC",
            nominal=Decimal("0"), upper_tol=Decimal("0.05"), lower_tol=None)
        over = StepExecutionMeasurement(measurement_definition=d, value=0.08)
        under = StepExecutionMeasurement(measurement_definition=d, value=0.01)
        self.assertIs(over.evaluate_spec(), False)
        self.assertIs(under.evaluate_spec(), True)


class GateIgnoresSupersededTests(_PartFixture):
    """#18: a voided FAIL and its replacement PASS both counted toward a gate."""

    def test_window_leaves_out_superseded(self):
        from types import SimpleNamespace
        from Tracker.services.qms.quality_gate import _report_window_qs
        part = self._part("G-18")
        voided = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                               status="FAIL")
        QualityReports.objects.filter(pk=voided.pk).update(  # tenant-safe: fixture
            superseded_at=timezone.now())
        kept = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                             status="PASS")
        rs = SimpleNamespace(step=self.step, gate_window="ALL", gate_window_n=None)
        self.assertEqual(list(_report_window_qs(rs, self.wo, None)), [kept])


class C0AqlTests(TenantTestCase):
    """#10: C=0 had no column for AQL 0.10–0.40 / 10; the lot sat RECEIVED. Refused
    on the rule now (not reconstructed)."""

    def test_refusal(self):
        from Tracker.services.qms.acceptance_sampling import aql_refusal
        self.assertIsNotNone(aql_refusal("C0", Decimal("0.25")))
        self.assertIsNotNone(aql_refusal("", Decimal("10")))
        self.assertIsNone(aql_refusal("C0", Decimal("1.0")))
        self.assertIsNone(aql_refusal("Z14", Decimal("0.25")))


class CapabilitySubgroupTests(_PartFixture):
    """#15: d2 stopped at n=10 (fell back to n=5); n=1 read capable; n=0 crashed."""

    def test_d2_table_and_bounds(self):
        from Tracker.services.qms.spc_factors import D2_FACTORS
        self.assertEqual((D2_FACTORS[15], D2_FACTORS[20], D2_FACTORS[25]), (3.472, 3.735, 3.931))
        d = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.step, label="Bore", type="NUMERIC",
            nominal=Decimal("10"), upper_tol=Decimal("0.1"), lower_tol=Decimal("0.1"))
        self.authenticate_as(self.superuser, self.tenant_a)
        for n in (0, 1, 26):
            r = self.client.get(f"/api/spc/capability/?measurement_id={d.id}&subgroup_size={n}")
            self.assertEqual(r.status_code, 400, (n, r.content))
