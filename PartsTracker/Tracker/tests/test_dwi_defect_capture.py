"""A defects capture on an inspection-point substep is recorded (QA walk, 2026-10-20).

`_apply_defects` filtered QualityReportDefect on `quality_report=` — the FK is `report` —
so every substep submit carrying defect rows was a 500: the Rework step's required
"Defects corrected" (no rework could be re-inspected) and every inspection's
"Defects found".
"""
from Tracker.models import QualityErrorsList, QualityReportDefect, Substep
from Tracker.tests.test_dwi import DwiPhase1BaseTestCase
from Tracker.utils.tenant_context import set_current_tenant_id


class DefectCaptureTests(DwiPhase1BaseTestCase):

    def setUp(self):
        set_current_tenant_id(self.tenant.id)
        self.err = QualityErrorsList.objects.create(tenant=self.tenant, error_name="Hole blockage", error_example="x")
        self.s_node = "44444444-4444-4444-4444-444444444444"
        self.d_node = "55555555-5555-5555-5555-555555555555"
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Repair and inspect",
            is_inspection_point=True,
            body_blocks={"type": "doc", "content": [
                {"type": "errorTypesField", "attrs": {"node_id": self.d_node, "required": True}},
                {"type": "qualityStatusField", "attrs": {"node_id": self.s_node, "required": True}},
            ]},
        )

    def _submit(self, rows):
        from Tracker.services.dwi.operator_capture import submit_substep
        return submit_substep(
            substep=self.substep, step_execution=self.step_execution, user=self.user,
            captures=[
                {"node_id": self.d_node, "kind": "defects", "rows": rows},
                {"node_id": self.s_node, "kind": "status", "status": "PASS"},
            ])

    def test_defect_rows_are_recorded_on_the_inspection_report(self):
        self._submit([{"error_type_id": str(self.err.id), "severity": "MAJOR",
                       "location": "spray hole 3", "count": 1}])
        defect = QualityReportDefect.objects.get(error_type=self.err)
        self.assertEqual((defect.severity, defect.location), ("MAJOR", "spray hole 3"))
        self.assertEqual(defect.report.part_id, self.step_execution.part_id)

    def test_an_inspectors_fail_quarantines_and_opens_a_disposition(self):
        """A visual-judgement FAIL on the status field: it was written with a queryset
        .update(), so no disposition and no quarantine (QA walk, 2026-10-20)."""
        from Tracker.models import Parts, QuarantineDisposition
        from Tracker.services.dwi.operator_capture import submit_substep
        submit_substep(substep=self.substep, step_execution=self.step_execution, user=self.user,
                       captures=[
                           {"node_id": self.d_node, "kind": "defects", "rows": [
                               {"error_type_id": str(self.err.id), "severity": "MAJOR"}]},
                           {"node_id": self.s_node, "kind": "status", "status": "FAIL"},
                       ])
        part = Parts.objects.get(pk=self.step_execution.part_id)
        self.assertEqual(part.part_status, "QUARANTINED")
        self.assertTrue(QuarantineDisposition.objects.filter(part=part).exists())

    def test_resubmitting_updates_the_row_rather_than_duplicating_it(self):
        row = {"error_type_id": str(self.err.id), "severity": "MAJOR", "location": "hole 3"}
        self._submit([row])
        self._submit([{**row, "severity": "MINOR"}])
        defect = QualityReportDefect.objects.get(error_type=self.err)
        self.assertEqual(defect.severity, "MINOR")


class EquipmentRosterRefusesUnusableGaugeTests(DwiPhase1BaseTestCase):
    """The equipment block skipped the out-of-service check a measurement capture
    makes, so a failed gauge could be recorded on an inspection (QA walk, 2026-10-20)."""

    def setUp(self):
        from Tracker.models import Equipments, EquipmentStatus, EquipmentType
        set_current_tenant_id(self.tenant.id)
        et = EquipmentType.objects.create(tenant=self.tenant, name="Micrometer", requires_calibration=True)
        self.gauge = Equipments.objects.create(tenant=self.tenant, name="MIC-2", serial_number="MIC-2",
                                               equipment_type=et, status=EquipmentStatus.OUT_OF_SERVICE)
        self.e_node = "66666666-6666-6666-6666-666666666666"
        self.s_node = "77777777-7777-7777-7777-777777777777"
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=0, title="Visual",
            is_inspection_point=True,
            body_blocks={"type": "doc", "content": [
                {"type": "equipmentRolesField", "attrs": {"node_id": self.e_node}},
                {"type": "qualityStatusField", "attrs": {"node_id": self.s_node, "required": True}},
            ]},
        )

    def test_an_out_of_service_gauge_is_refused(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.dwi.operator_capture import submit_substep
        with self.assertRaises(ValidationError) as ctx:
            submit_substep(substep=self.substep, step_execution=self.step_execution, user=self.user,
                           captures=[
                               {"node_id": self.e_node, "kind": "equipment_roles",
                                "rows": [{"equipment_id": str(self.gauge.id), "role": "GAUGE"}]},
                               {"node_id": self.s_node, "kind": "status", "status": "PASS"},
                           ])
        self.assertIn("OUT_OF_SERVICE", " ".join(ctx.exception.messages))

    def test_an_overdue_gauge_is_recorded_with_a_warning(self):
        import datetime
        from django.utils import timezone
        from Tracker.models import CalibrationRecord, Equipments, EquipmentStatus, QualityReportEquipment
        from Tracker.services.dwi.operator_capture import submit_substep
        overdue = Equipments.objects.create(tenant=self.tenant, name="MIC-1", serial_number="MIC-1",
                                            equipment_type=self.gauge.equipment_type,
                                            status=EquipmentStatus.IN_SERVICE)
        today = timezone.now().date()
        CalibrationRecord.objects.create(tenant=self.tenant, equipment=overdue,
                                         calibration_date=today - datetime.timedelta(days=400),
                                         due_date=today - datetime.timedelta(days=5), result='PASS')
        result = submit_substep(substep=self.substep, step_execution=self.step_execution, user=self.user,
                                captures=[
                                    {"node_id": self.e_node, "kind": "equipment_roles",
                                     "rows": [{"equipment_id": str(overdue.id), "role": "GAUGE"}]},
                                    {"node_id": self.s_node, "kind": "status", "status": "PASS"},
                                ])
        self.assertTrue(QualityReportEquipment.objects.filter(equipment=overdue).exists())
        self.assertTrue(any("past its calibration due date" in w for w in result.warnings), result.warnings)

    def test_the_equipment_api_reports_calibration_status(self):
        """The pickers mark an overdue gauge before the reading (user decision
        2026-10-20), so the equipment response carries calibration_status."""
        import datetime
        from django.utils import timezone
        from rest_framework.test import APIClient
        from Tracker.models import CalibrationRecord, Equipments, EquipmentStatus
        overdue = Equipments.objects.create(tenant=self.tenant, name="MIC-1", serial_number="MIC-1x",
                                            equipment_type=self.gauge.equipment_type,
                                            status=EquipmentStatus.IN_SERVICE)
        today = timezone.now().date()
        CalibrationRecord.objects.create(tenant=self.tenant, equipment=overdue,
                                         calibration_date=today - datetime.timedelta(days=400),
                                         due_date=today - datetime.timedelta(days=5), result='PASS')
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        c = APIClient()
        c.force_authenticate(user=self.user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        resp = c.get(f"/api/Equipment/{overdue.id}/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["calibration_status"], "OVERDUE")
