"""Correcting a recorded calibration or training needs a reason, kept beside the change
(walk 2026-10-22: the edits took none)."""
import datetime

from Tracker.models import (
    CalibrationRecord, EquipmentType, Equipments, RecordEdit, TrainingRecord, TrainingType,
)
from Tracker.tests.base import TenantTestCase


class ReasonedRecordEditTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        eq_type = EquipmentType.objects.create(tenant=self.tenant_a, name="Micrometer")
        self.gauge = Equipments.objects.create(tenant=self.tenant_a, name="MIC-9", serial_number="MIC-9",
                                               equipment_type=eq_type)
        on = datetime.date(2026, 10, 1)
        self.cal = CalibrationRecord.objects.create(
            tenant=self.tenant_a, equipment=self.gauge, calibration_date=on,
            due_date=on + datetime.timedelta(days=180), result='FAIL')
        self.ttype = TrainingType.objects.create(tenant=self.tenant_a, name="Torque", validity_period_days=365)
        self.training = TrainingRecord.objects.create(
            tenant=self.tenant_a, user=self.user_a, training_type=self.ttype, completed_date=on)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_calibrationrecord', 'change_calibrationrecord',
            'view_trainingrecord', 'change_trainingrecord', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_a_calibration_result_is_corrected_with_a_reason(self):
        url = f"/api/CalibrationRecords/{self.cal.id}/"
        self.assertEqual(self.client.patch(url, {"result": "PASS"}, format="json").status_code, 400)
        resp = self.client.patch(url, {"result": "PASS", "edit_reason": "Read the wrong gauge block"},
                                 format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(RecordEdit.objects.filter(object_id=self.cal.id, field_name="result",
                                                  old_value="FAIL", new_value="PASS").exists())
        # A note alone needs no reason.
        self.assertEqual(self.client.patch(url, {"notes": "Recheck in 90 days"}, format="json").status_code, 200)

    def test_a_training_record_is_corrected_with_a_reason(self):
        url = f"/api/TrainingRecords/{self.training.id}/"
        new = "2026-09-30"
        self.assertEqual(self.client.patch(url, {"completed_date": new}, format="json").status_code, 400)
        resp = self.client.patch(url, {"completed_date": new, "edit_reason": "Course was the day before"},
                                 format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(RecordEdit.objects.filter(object_id=self.training.id, field_name="completed_date").exists())
