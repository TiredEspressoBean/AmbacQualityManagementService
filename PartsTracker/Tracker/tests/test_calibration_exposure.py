"""What a gauge measured while it may have been out of tolerance (2026-10-06, ISO 9001
7.1.5.2): the quality reports between its last good calibration and the one that found
it unfit — not its whole history, and not after the check."""
import datetime

from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.models import (
    CalibrationRecord, EquipmentType, Equipments, QualityReportEquipment, QualityReports,
)
from Tracker.services.qms.calibration_exposure import NotFoundUnfit, exposure_for
from Tracker.tests.base import TenantTestCase

D = datetime.date


class CalibrationExposureTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        eq_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Torque wrench")
        self.gauge = Equipments.objects.create(
            tenant=self.tenant_a, name="TW-25", serial_number="TW-25", equipment_type=eq_type)
        self.other_gauge = Equipments.objects.create(
            tenant=self.tenant_a, name="TW-30", serial_number="TW-30", equipment_type=eq_type)
        self._cal(D(2025, 6, 1), 'PASS')
        self.last_pass = self._cal(D(2026, 1, 4), 'PASS')
        self.before = self._report("QR-BEFORE", D(2025, 12, 20))
        self.early = self._report("QR-FEB", D(2026, 2, 10))
        self.late = self._report("QR-JUN", D(2026, 6, 30))
        self.after = self._report("QR-AFTER", D(2026, 7, 5))
        self._report("QR-OTHER-GAUGE", D(2026, 3, 3), gauge=self.other_gauge)

    def _cal(self, on, result, as_found=None):
        return CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=self.gauge, calibration_date=on,
            due_date=on + datetime.timedelta(days=180), result=result,
            as_found_in_tolerance=as_found)

    def _report(self, number, on, gauge=None):
        report = QualityReports.objects.create(
            tenant=self.tenant_a, status="PASS", detected_by=self.user_a, report_number=number)
        # Midday, so the plant timezone can't move it across a day boundary.
        QualityReports.objects.filter(pk=report.pk).update(created_at=timezone.make_aware(
            datetime.datetime.combine(on, datetime.time(12))))
        QualityReportEquipment.objects.create(
            quality_report=report, equipment=gauge or self.gauge, role='GAUGE')
        return report

    def _numbers(self, record):
        return [r.report_number for r in exposure_for(record).reports]

    def test_the_window_runs_from_the_last_good_calibration_to_the_failed_one(self):
        fail = self._cal(D(2026, 7, 1), 'FAIL')
        exp = exposure_for(fail)
        self.assertEqual((exp.window_start, exp.window_end), (D(2026, 1, 4), D(2026, 7, 1)))
        self.assertEqual(exp.window_start_calibration_id, str(self.last_pass.pk))
        # Not the June 2025 pass, nothing after the check, nothing from another gauge.
        self.assertEqual(self._numbers(fail), ["QR-FEB", "QR-JUN"])

    def test_limited_use_counts_as_good(self):
        self._cal(D(2026, 3, 1), 'LIMITED')
        fail = self._cal(D(2026, 7, 1), 'FAIL')
        exp = exposure_for(fail)
        self.assertEqual((exp.window_start, exp.window_start_result), (D(2026, 3, 1), 'LIMITED'))
        self.assertEqual(self._numbers(fail), ["QR-JUN"])

    def test_with_no_earlier_good_calibration_the_window_opens_at_first_use(self):
        CalibrationRecord.objects.filter(equipment=self.gauge).delete()
        fail = self._cal(D(2026, 7, 1), 'FAIL')
        exp = exposure_for(fail)
        self.assertIsNone(exp.window_start)
        self.assertEqual(self._numbers(fail), ["QR-BEFORE", "QR-FEB", "QR-JUN"])

    def test_found_out_of_tolerance_then_adjusted_is_unfit_too(self):
        adjusted = self._cal(D(2026, 7, 1), 'PASS', as_found=False)
        self.assertEqual(self._numbers(adjusted), ["QR-FEB", "QR-JUN"])

    def test_a_calibration_that_found_the_gauge_fit_has_no_exposure(self):
        with self.assertRaises(NotFoundUnfit):
            exposure_for(self._cal(D(2026, 7, 1), 'PASS', as_found=True))

    def test_endpoint_and_export(self):
        fail = self._cal(D(2026, 7, 1), 'FAIL')
        fit = self._cal(D(2026, 7, 2), 'PASS', as_found=True)
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

        group = self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                              ['view_calibrationrecord', 'full_tenant_access'])
        # The list names parts and their results: quality-report access is needed too.
        self.assertEqual(client.get(f'/api/CalibrationRecords/{fail.pk}/exposure/').status_code, 403)

        from django.contrib.auth.models import Permission
        group.permissions.add(Permission.objects.get(codename='view_qualityreports'))
        self.user_a.clear_permission_cache(self.tenant_a)
        resp = client.get(f'/api/CalibrationRecords/{fail.pk}/exposure/')
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["count"], 2)
        self.assertEqual(body["window_sentence"], "Measured between 2026-01-04 (last passing "
                                                  "calibration) and 2026-07-01 (failed check).")
        self.assertEqual([r["report_number"] for r in body["reports"]], ["QR-FEB", "QR-JUN"])

        xlsx = client.get(f'/api/CalibrationRecords/{fail.pk}/exposure-export/')
        self.assertEqual(xlsx.status_code, 200)
        self.assertIn("spreadsheetml", xlsx["Content-Type"])

        self.assertEqual(client.get(f'/api/CalibrationRecords/{fit.pk}/exposure/').status_code, 400)
