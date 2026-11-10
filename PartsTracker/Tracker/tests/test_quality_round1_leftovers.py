"""Round-1 quality bugs never sent before (2026-11-10): #7, #14, #15, #22, #25.

(#3 — a partial reject's remainder — is in test_receiving_hunt_1110.)
"""
from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from Tracker.models import (
    CalibrationRecord, EquipmentType, Equipments, QualityReports, QuarantineDisposition, Steps,
)
from Tracker.services.core.clock import tenant_today
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_quality_hunt_1110 import _PartFixture


class FpiReleasePerContextTests(_PartFixture):
    """#7: a Per Shift step's QA release is earned per shift. One shared release was
    overwritten by each pass, and voiding one shift's pass withdrew every shift's."""

    def setUp(self):
        super().setUp()
        Steps.objects.filter(pk=self.step.pk).update(  # tenant-safe: fixture, scoped by pk
            requires_first_piece_inspection=True, requires_qa_signoff=True, fpi_scope="PER_SHIFT")
        self.step.refresh_from_db()

    def _passed(self, shift_date, part):
        from Tracker.models import FPIRecord, FPIStatus
        from Tracker.services.qms.fpi import _ensure_qa_approval
        fpi = FPIRecord.objects.create(
            tenant=self.tenant_a, work_order=self.wo, step=self.step, part_type=self.pt,
            designated_part=part, shift_date=shift_date, status=FPIStatus.PASSED, result="PASS",
            inspected_by=self.user_a, inspected_at=timezone.now())
        _ensure_qa_approval(fpi, self.user_a)
        return fpi

    def test_voiding_one_shifts_pass_keeps_the_others_release(self):
        from Tracker.models import QaApproval
        from Tracker.services.qms.fpi import void_fpi_pass
        from Tracker.services.qms.fpi_scope import qa_released
        today = tenant_today(self.tenant_a)
        part = self._part("FP-7")
        yesterday_fpi = self._passed(today - timedelta(days=1), part)
        today_fpi = self._passed(today, part)
        self.assertEqual(QaApproval.objects.filter(step=self.step, work_order=self.wo,
                                                   archived=False).count(), 2,
                         "each shift's pass is its own release")
        void_fpi_pass(yesterday_fpi, self.user_a, "Wrong gauge on the night shift")
        self.assertTrue(qa_released(self.step, self.wo, part=part),
                        "today's shift keeps the release its own first piece earned")
        void_fpi_pass(today_fpi, self.user_a, "Wrong gauge on the day shift too")
        self.assertFalse(qa_released(self.step, self.wo, part=part))


class GateCapaTypeTests(_PartFixture):
    """#14: a gate raised CORRECTIVE whatever type it was set to, and its CAPA didn't
    link the report that tripped it."""

    def test_the_configured_type_and_the_report_link(self):
        from Tracker.services.qms.quality_gate import _raise_capa_or_scar
        part = self._part("G-14")
        report = QualityReports.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                               status="FAIL")
        ruleset = SimpleNamespace(
            tenant=self.tenant_a, name="Bore gate", step=self.step, gate_metric="FAIL_RATE",
            gate_capa_type="PREVENTIVE", gate_capa_severity="MINOR", supplier=None)
        firing = SimpleNamespace(metric_value=0.2, threshold=0.1, triggered_by_report=report)
        capa = _raise_capa_or_scar(ruleset, firing, material_lot=None, user=None)
        self.assertEqual(capa.capa_type, "PREVENTIVE")
        self.assertEqual((capa.step_id, capa.part_id, capa.work_order_id),
                         (self.step.id, part.id, self.wo.id))
        self.assertIn(report, capa.quality_reports.all())
        report.refresh_from_db()
        self.assertEqual(report.capa_decision, "PROMOTED")


class _GaugeFixture(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.today = tenant_today(self.tenant_a)
        gauge_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer",
                                                  requires_calibration=True)
        self.gauge = Equipments.objects.create(tenant=self.tenant_a, name="MIC-9",
                                               equipment_type=gauge_type)

    def _cal(self, result, days_ago, due_in):
        return CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=self.gauge, result=result,
            calibration_date=self.today - timedelta(days=days_ago),
            due_date=self.today + timedelta(days=due_in))


class CalibrationStatusFilterTests(_GaugeFixture):
    """#15: ?status= ran over every record, so a superseded FAIL still listed the gauge
    as failed after it passed again."""

    def test_status_is_the_latest_records(self):
        self._cal("FAIL", days_ago=40, due_in=300)
        current = self._cal("PASS", days_ago=10, due_in=355)
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_calibrationrecord', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

        def ids(status):
            body = self.client.get(f"/api/CalibrationRecords/?status={status}").json()
            rows = body["results"] if isinstance(body, dict) else body
            return {r["id"] for r in rows}
        self.assertEqual(ids("failed"), set())
        self.assertEqual(ids("current"), {str(current.id)})


class LatestCalibrationTests(_GaugeFixture):
    """#22: a deleted record still counted as the gauge's latest; same-day records
    picked arbitrarily."""

    def test_an_archived_record_isnt_the_latest(self):
        older = self._cal("PASS", days_ago=30, due_in=335)
        newer = self._cal("FAIL", days_ago=1, due_in=364)
        newer.archived = True
        newer.save(update_fields=["archived"])
        latest = list(CalibrationRecord.objects.filter(equipment=self.gauge).latest_per_equipment())
        self.assertEqual(latest, [older])

    def test_same_day_goes_to_the_later_entry(self):
        self._cal("FAIL", days_ago=0, due_in=0)
        repaired = self._cal("PASS", days_ago=0, due_in=365)
        latest = list(CalibrationRecord.objects.filter(equipment=self.gauge).latest_per_equipment())
        self.assertEqual(latest, [repaired])

    def test_the_due_report_says_failed_not_current(self):
        from Tracker.reports.adapters.calibration_due import CalibrationDueAdapter
        self._cal("FAIL", days_ago=1, due_in=364)
        ctx = CalibrationDueAdapter().build_context({}, self.user_a, self.tenant_a)
        item, = [i for i in ctx.items if i.equipment_name == "MIC-9"]
        self.assertEqual(item.status, "FAILED")


class OpenNcrCountTests(TenantTestCase):
    """#25: "Open NCRs" was created − closed within the window; an NCR opened before the
    window and still open wasn't counted."""

    def test_open_count_is_every_open_one(self):
        old = QuarantineDisposition.objects.create(tenant=self.tenant_a, description="Old, still open")
        QuarantineDisposition.objects.filter(pk=old.pk).update(  # tenant-safe: fixture, scoped by pk
            created_at=timezone.now() - timedelta(days=90))
        QuarantineDisposition.objects.create(tenant=self.tenant_a, description="New")
        QuarantineDisposition.objects.create(tenant=self.tenant_a, description="Closed",
                                             current_state="CLOSED")
        self.authenticate_as(self.superuser, self.tenant_a)
        body = self.client.get("/api/dashboard/ncr-aging/").json()
        self.assertEqual(body["open_count"], 2)
