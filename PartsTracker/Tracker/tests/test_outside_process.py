"""Outside-processing (subcontract) — Flow B.

Send parts out → receive back → return inspection (reusing the subject-agnostic
receiving runtime, subject = the shipment) → accept / reject. Also locks the
QualityReports at-most-one-subject constraint and the DWI osp_shipment promote branch.
"""
import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction

from Tracker.tests.base import TenantTestCase
from Tracker.models import (
    Companies, PartTypes, Steps, Processes, ProcessStep, WorkOrder, WorkOrderStatus,
    Parts, PartsStatus, MeasurementDefinition, StepMeasurementRequirement,
    SamplingRuleSet, SamplingRule, QualityReports, StepExecution, OutsideProcessShipment,
    MaterialLot, Substep,
)
from Tracker.services.mes import outside_process as osp
from Tracker.services.qms.inline_capture import record_dwi_measurement


class _OSPFixtureMixin:
    """Part type with an outside-process step (heat treat), a default vendor, a
    characteristic + C=0 sampling ruleset, a work order, and parts sitting at the step."""

    def _build_fixtures(self, n_parts=3):
        self.supplier = Companies.objects.create(
            tenant=self.tenant_a, name="HeatTreat Co", description="")
        self.part_type = PartTypes.objects.create(tenant=self.tenant_a, name="Shaft")
        self.process = Processes.objects.create(
            tenant=self.tenant_a, name="P", part_type=self.part_type)
        self.osp_step = Steps.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, name="Heat Treat",
            step_type="TASK", is_outside_process=True, outside_supplier=self.supplier)
        ProcessStep.objects.create(process=self.process, step=self.osp_step, order=1)
        self.char = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.osp_step, label="Hardness OK", type="PASS_FAIL")
        StepMeasurementRequirement.objects.get_or_create(step=self.osp_step, measurement=self.char)
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, step=self.osp_step, supplier=None,
            name="OSP C=0", active=True, aql=Decimal("1.0"),
            inspection_level="II", severity="NORMAL", strategy="C0")
        SamplingRule.objects.create(
            tenant=self.tenant_a, ruleset=self.ruleset, rule_type="C_ZERO", order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-OSP-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=n_parts, process=self.process)
        self.parts = [
            Parts.objects.create(
                tenant=self.tenant_a, ERP_id=f"P-OSP-{i}", part_type=self.part_type,
                work_order=self.wo, step=self.osp_step, part_status=PartsStatus.IN_PROGRESS)
            for i in range(n_parts)
        ]


class OutsideProcessSendReceiveTests(_OSPFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures()

    def test_send_out_creates_shipment_and_moves_parts(self):
        shipment = osp.send_parts_out(
            step=self.osp_step, parts=self.parts, reference="PO-42", user=self.user_a)
        self.assertEqual(shipment.status, "SENT")
        self.assertEqual(shipment.supplier_id, self.supplier.id)   # defaulted from step
        self.assertEqual(shipment.quantity, len(self.parts))
        self.assertTrue(shipment.shipment_number.startswith("OSP-"))
        for p in self.parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.AT_OUTSIDE_PROCESS)
        # Each part's execution is linked to the shipment.
        self.assertEqual(
            StepExecution.objects.filter(outside_process_shipment=shipment).count(),
            len(self.parts))

    def test_ready_to_ship_only_counts_in_progress(self):
        # Fixture puts 3 parts IN_PROGRESS at the OSP step → all ready to ship.
        # Flip statuses that must NOT count as ready:
        self.parts[0].part_status = PartsStatus.AWAITING_QA          # returned, awaiting return inspection
        self.parts[0].save(update_fields=["part_status"])
        self.parts[1].part_status = PartsStatus.READY_FOR_NEXT_STEP  # completed the OSP step
        self.parts[1].save(update_fields=["part_status"])
        groups = osp.build_ready_to_ship_groups()
        self.assertEqual(len(groups), 1)                              # one OSP step
        self.assertEqual(groups[0]["step_id"], str(self.osp_step.id))
        self.assertEqual(groups[0]["ready_count"], 1)                 # only the remaining IN_PROGRESS part

    def test_ready_to_ship_excludes_sent_parts(self):
        osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)
        # All 3 now AT_OUTSIDE_PROCESS → nothing ready to ship.
        self.assertEqual(osp.build_ready_to_ship_groups(), [])

    def test_send_out_rejects_non_osp_step(self):
        task = Steps.objects.create(
            tenant=self.tenant_a, part_type=self.part_type, name="Plain", step_type="TASK")
        with self.assertRaises(ValueError):
            osp.send_parts_out(step=task, parts=self.parts, user=self.user_a)

    def test_send_out_requires_a_supplier(self):
        self.osp_step.outside_supplier = None
        self.osp_step.save(update_fields=["outside_supplier"])
        with self.assertRaises(ValueError):
            osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)

    def test_receive_back_opens_return_inspection(self):
        shipment = osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)
        report = osp.receive_parts_back(shipment, self.user_a)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "RETURNED")
        self.assertIsNotNone(shipment.returned_at)
        self.assertEqual(report.osp_shipment_id, shipment.id)
        self.assertEqual(report.step_id, self.osp_step.id)
        self.assertEqual(report.status, "PENDING")
        self.assertIsNotNone(report.sample_size)
        self.assertEqual(report.accept_number, 0)   # C=0
        for p in self.parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.AWAITING_QA)

    def test_receive_back_twice_raises(self):
        shipment = osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)
        osp.receive_parts_back(shipment, self.user_a)
        with self.assertRaises(ValueError):
            osp.receive_parts_back(shipment, self.user_a)


class OutsideProcessInspectionTests(_OSPFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures(n_parts=3)
        self.inspection_substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.osp_step, order=0,
            title="Verify hardness", is_inspection_point=True)
        self.shipment = osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)
        self.report = osp.receive_parts_back(self.shipment, self.user_a)

    def _return_execution(self):
        return osp._return_execution(self.shipment)

    def test_dwi_capture_promotes_to_shipment_report(self):
        # DWI capture on the shipment-subject execution appends to the osp report.
        ex = self._return_execution()
        self.assertIsNotNone(ex)
        record_dwi_measurement(
            step_execution=ex, substep=self.inspection_substep,
            measurement_definition=self.char, value_string="PASS",
            recorded_by=self.user_a, sample_number=1)
        self.report.refresh_from_db()
        # No new report was minted — the capture rode the existing shipment report.
        self.assertEqual(
            QualityReports.objects.filter(osp_shipment=self.shipment).count(), 1)
        self.assertTrue(self.report.measurements.filter(definition=self.char).exists())

    def test_accept_return_advances_parts(self):
        report = osp.accept_return(self.report, self.user_a)
        self.assertEqual(report.status, "PASS")
        for p in self.parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.READY_FOR_NEXT_STEP)
        # The batch inspection execution is closed.
        self.assertIsNone(self._return_execution())

    def test_reject_return_quarantines_parts(self):
        report = osp.reject_return(self.report, self.user_a)
        self.assertEqual(report.status, "FAIL")
        for p in self.parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, PartsStatus.QUARANTINED)

    def test_evaluate_all_pass_units_accepts(self):
        n = self.report.sample_size
        for i in range(n):
            self.report.measurements.create(
                tenant=self.tenant_a, definition=self.char,
                value_pass_fail="PASS", sample_number=i + 1)
        osp.evaluate_return_acceptance(self.report)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "PASS")

    def test_evaluate_defective_unit_rejects(self):
        # C=0 → a single defective unit rejects.
        self.report.measurements.create(
            tenant=self.tenant_a, definition=self.char,
            value_pass_fail="FAIL", sample_number=1)
        osp.evaluate_return_acceptance(self.report)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, "FAIL")


class QualityReportSubjectConstraintTests(_OSPFixtureMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self._build_fixtures(n_parts=1)

    def test_cannot_set_lot_and_osp_shipment(self):
        shipment = osp.send_parts_out(step=self.osp_step, parts=self.parts, user=self.user_a)
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-X", received_date=datetime.date(2026, 1, 1),
            received_by=self.user_a, quantity=Decimal("1"), quantity_remaining=Decimal("1"),
            unit_of_measure="EA", status="RECEIVED", material_type=self.part_type)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QualityReports.objects.create(
                    tenant=self.tenant_a, step=self.osp_step,
                    material_lot=lot, osp_shipment=shipment, status="PENDING")
