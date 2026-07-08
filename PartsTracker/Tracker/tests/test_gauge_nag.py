"""Personal calibration nag: gauges I used recently that are due/overdue.

Usage links come from EquipmentUsage(operator) ∪ equipment on quality reports
I filed. The runtime EquipmentUsage writer is a named gap (capture-screen
binding); the service is honest about whatever links exist.
"""
import datetime

from django.utils import timezone

from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    CalibrationRecord, EquipmentType, Equipments, EquipmentUsage,
    QualityReportEquipment, QualityReports, PartTypes, Steps,
)
from Tracker.services.qms.gauge_nag import my_gauge_nag


class GaugeNagTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.eq_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer")
        self.gauge_due = self._gauge("Micrometer M-04", due_in_days=3)
        self.gauge_overdue = self._gauge("Bore gauge #12", due_in_days=-2)
        self.gauge_fine = self._gauge("Caliper C-01", due_in_days=200)
        self.gauge_unused = self._gauge("Height gauge H-9", due_in_days=1)

    def _gauge(self, name, due_in_days):
        eq = Equipments.objects.create(
            tenant=self.tenant_a, name=name, serial_number=name,
            equipment_type=self.eq_type)
        today = timezone.now().date()
        CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=eq,
            calibration_date=today - datetime.timedelta(days=180),
            due_date=today + datetime.timedelta(days=due_in_days),
            result='PASS')
        return eq

    def _use(self, gauge, user=None):
        EquipmentUsage.objects.create(
            tenant=self.tenant_a, equipment=gauge, operator=user or self.user_a)

    def test_only_my_recently_used_due_gauges(self):
        self._use(self.gauge_due)
        self._use(self.gauge_overdue)
        self._use(self.gauge_fine)          # used, but cal is far out
        # gauge_unused is due tomorrow but I never touched it — no nag.

        rows = my_gauge_nag(self.user_a)
        names = [r["equipment_name"] for r in rows]
        self.assertEqual(names, ["Bore gauge #12", "Micrometer M-04"])  # most urgent first
        self.assertTrue(rows[0]["overdue"])
        self.assertFalse(rows[1]["overdue"])
        self.assertEqual(rows[1]["days_until_due"], 3)

    def test_other_users_usage_does_not_nag_me(self):
        from django.contrib.auth import get_user_model
        other = get_user_model().objects.create_user(
            username='other', email='o@example.com', password='x', tenant=self.tenant_a)
        self._use(self.gauge_overdue, user=other)
        self.assertEqual(my_gauge_nag(self.user_a), [])

    def test_report_equipment_counts_as_usage(self):
        part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        step = Steps.objects.create(
            tenant=self.tenant_a, name="Final", part_type=part_type, step_type="TASK")
        report = QualityReports.objects.create(
            tenant=self.tenant_a, step=step, status="FAIL",
            detected_by=self.user_a)
        QualityReportEquipment.objects.create(
            quality_report=report, equipment=self.gauge_due)

        rows = my_gauge_nag(self.user_a)
        self.assertEqual([r["equipment_name"] for r in rows], ["Micrometer M-04"])

    def test_endpoint(self):
        from rest_framework.test import APIClient
        self._use(self.gauge_overdue)
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ['view_calibrationrecord', 'full_tenant_access'])
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

        response = client.get('/api/CalibrationRecords/my-gauge-nag/')
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["equipment_name"], "Bore gauge #12")
        self.assertTrue(body[0]["overdue"])
