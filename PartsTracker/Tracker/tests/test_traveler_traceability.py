"""The traveler's per-serial traceability, built from live records (2026-10-08)."""
from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStep, QuarantineDisposition, StepExecution, Steps,
    WorkOrder, WorkOrderStatus,
)
from Tracker.reports.adapters.work_order_traveler import WorkOrderTravelerAdapter
from Tracker.tests.base import TenantTestCase


class TravelerTraceabilityTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Nozzle")
        self.process = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=pt)
        self.assembly = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Assembly")
        ProcessStep.objects.create(process=self.process, step=self.assembly, order=1)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-T", quantity=2,
                                           process=self.process,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.a = Parts.objects.create(tenant=self.tenant_a, ERP_id="SN-A", part_type=pt,
                                      work_order=self.wo, step=self.assembly)
        self.b = Parts.objects.create(tenant=self.tenant_a, ERP_id="SN-B", part_type=pt,
                                      work_order=self.wo, step=self.assembly)

    def _ctx(self, part=None):
        params = {"id": self.wo.id, **({"part": part.id} if part else {})}
        return WorkOrderTravelerAdapter().build_context(params, self.user_a, self.tenant_a)

    def test_a_line_per_serial_with_open_nonconformances(self):
        QuarantineDisposition.objects.create(tenant=self.tenant_a, part=self.b,
                                             description="Leak at seat")
        ctx = self._ctx()
        self.assertEqual([(s.serial, s.open_ncrs) for s in ctx.serials], [("SN-A", 0), ("SN-B", 1)])

    def test_the_printed_serial_shows_rework_visits_and_its_nonconformances(self):
        for visit in (1, 2):
            StepExecution.objects.create(tenant=self.tenant_a, part=self.a, step=self.assembly,
                                         visit_number=visit, status="COMPLETED")
        QuarantineDisposition.objects.create(tenant=self.tenant_a, part=self.a,
                                             description="Torque low")
        ctx = self._ctx(self.a)
        self.assertEqual(ctx.serial, "SN-A")
        self.assertEqual(ctx.operations[0].visits, 2)
        self.assertEqual(len(ctx.nonconformances), 1)

    def test_order_tracker_lists_shipments_and_their_serials_not_voided_ones(self):
        from Tracker.models import Companies, CustomerShipment, Orders
        from Tracker.serializers.mes_lite import CustomerOrderSerializer
        fleet = Companies.objects.create(tenant=self.tenant_a, name="Fleet", is_customer=True)
        order = Orders.objects.create(tenant=self.tenant_a, name="Fleet order", company=fleet)
        shipped = CustomerShipment.objects.create(tenant=self.tenant_a, customer=fleet,
                                                  shipment_number="SHP-1", carrier="UPS")
        voided = CustomerShipment.objects.create(tenant=self.tenant_a, customer=fleet,
                                                 shipment_number="SHP-2", is_voided=True)
        Parts.objects.filter(pk=self.a.pk).update(order=order, customer_shipment=shipped)
        Parts.objects.filter(pk=self.b.pk).update(order=order, customer_shipment=voided)

        rows = CustomerOrderSerializer(order).data["shipments"]
        self.assertEqual([(r["shipment_number"], r["carrier"], r["serials"]) for r in rows],
                         [("SHP-1", "UPS", ["SN-A"])])


class TravelerPerSerialCreditTests(TenantTestCase):
    """A serial's as-built row shows only what happened to THAT serial (2026-10-20).

    The docs walk found serial 012's Flow Calibration row signed "insp Sarah C. · ACC"
    with "10/20" as its operator — the work order's first-piece buy-off (done on 011)
    credited to a serial still pending there — and its Nitride Coating row blank though
    the shipment it went out on was return-inspected and accepted."""

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=pt)
        self.cal = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Flow Calibration")
        self.osp = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Nitride Coating")
        ProcessStep.objects.create(process=self.process, step=self.cal, order=1)
        ProcessStep.objects.create(process=self.process, step=self.osp, order=2)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-QA", quantity=2,
                                           process=self.process,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.first = Parts.objects.create(tenant=self.tenant_a, ERP_id="INJ-011", part_type=pt,
                                          work_order=self.wo, step=self.cal)
        self.second = Parts.objects.create(tenant=self.tenant_a, ERP_id="INJ-012", part_type=pt,
                                           work_order=self.wo, step=self.cal)

    def _row(self, part, step):
        ctx = WorkOrderTravelerAdapter().build_context(
            {"id": self.wo.id, "part": part.id}, self.user_a, self.tenant_a)
        return next(o for o in ctx.operations if o.step_name == step.name)

    def test_the_jobs_buy_off_is_not_credited_to_a_serial_still_pending_there(self):
        from Tracker.models import QaApproval
        StepExecution.objects.create(tenant=self.tenant_a, part=self.first, step=self.cal,
                                     visit_number=1, status="COMPLETED", completed_by=self.user_a)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                     visit_number=1, status="PENDING")
        QaApproval.objects.create(tenant=self.tenant_a, step=self.cal, work_order=self.wo,
                                  qa_staff=self.user_a)

        pending = self._row(self.second, self.cal)
        self.assertEqual((pending.operator, pending.inspector, pending.acc_rej), (None, None, None))
        done = self._row(self.first, self.cal)
        self.assertIsNotNone(done.inspector)
        self.assertEqual(done.acc_rej, "ACC")

    def test_an_outside_process_row_shows_the_return_inspection_of_its_shipment(self):
        from Tracker.models import Companies, OutsideProcessShipment, QualityReports
        apex = Companies.objects.create(tenant=self.tenant_a, name="Apex Plating", is_supplier=True)
        shipment = OutsideProcessShipment.objects.create(
            tenant=self.tenant_a, supplier=apex, step=self.osp, work_order=self.wo)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.osp,
                                     visit_number=1, status="COMPLETED",
                                     outside_process_shipment=shipment)
        QualityReports.objects.create(tenant=self.tenant_a, osp_shipment=shipment, step=self.osp,
                                      status="PASS", detected_by=self.user_a,
                                      description="Case depth in spec")

        row = self._row(self.second, self.osp)
        self.assertIsNotNone(row.inspector)
        self.assertEqual((row.acc_rej, row.remarks), ("ACC", "Case depth in spec"))

    def test_a_failed_report_on_the_visit_is_not_masked_by_a_later_pass(self):
        """013: a FAIL then a PASS on one Flow Calibration visit printed ACC."""
        from Tracker.models import QualityReports
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                          visit_number=1, status="ROLLED_BACK",
                                          assigned_to=self.user_a)
        for status in ("FAIL", "PASS"):
            QualityReports.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                          step_execution=ex, status=status, detected_by=self.user_a)
        self.assertEqual(self._row(self.second, self.cal).acc_rej, "REJ")

    def test_an_out_of_spec_reading_rejects_the_row(self):
        from decimal import Decimal
        from Tracker.models import MeasurementDefinition, QaApproval, StepExecutionMeasurement
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                          visit_number=1, status="COMPLETED", completed_by=self.user_a)
        QaApproval.objects.create(tenant=self.tenant_a, step=self.cal, work_order=self.wo,
                                  qa_staff=self.user_a)
        # Limits on the definition: saving a reading recomputes is_within_spec from them.
        flow = MeasurementDefinition.objects.create(
            tenant=self.tenant_a, step=self.cal, label="Flow Rate", unit="mL/min", type="NUMERIC",
            nominal=Decimal("120"), upper_tol=Decimal("20"), lower_tol=Decimal("20"))
        StepExecutionMeasurement.objects.create(tenant=self.tenant_a, step_execution=ex,
                                                measurement_definition=flow, value=Decimal("98"),
                                                recorded_by=self.user_a)
        self.assertEqual(self._row(self.second, self.cal).acc_rej, "REJ")

    def test_a_return_inspection_naming_nobody_credits_who_completed_it(self):
        """The shipment's report had no detected_by; the shipment's inspection was
        completed by the inspector, and the row printed a bare "10/20"."""
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import Companies, OutsideProcessShipment, QualityReports
        apex = Companies.objects.create(tenant=self.tenant_a, name="Apex", is_supplier=True)
        shipment = OutsideProcessShipment.objects.create(
            tenant=self.tenant_a, supplier=apex, step=self.osp, work_order=self.wo)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.osp,
                                     visit_number=1, status="COMPLETED",
                                     outside_process_shipment=shipment)
        StepExecution.objects.create(
            tenant=self.tenant_a, step=self.osp, visit_number=1, status="COMPLETED",
            subject_content_type=ContentType.objects.get_for_model(OutsideProcessShipment),
            subject_id=shipment.id, completed_by=self.user_a)
        QualityReports.objects.create(tenant=self.tenant_a, osp_shipment=shipment, step=self.osp,
                                      status="PASS")
        row = self._row(self.second, self.osp)
        self.assertIsNotNone(row.inspector)
        self.assertNotRegex(row.inspector, r"^\s*·")   # a name, not a bare date

    def test_a_needs_repair_result_prints_rpr_and_ranks_between_fail_and_pass(self):
        from Tracker.models import QualityReports
        ex = StepExecution.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                          visit_number=1, status="COMPLETED", completed_by=self.user_a)
        for status in ("REPAIR", "PASS"):
            QualityReports.objects.create(tenant=self.tenant_a, part=self.second, step=self.cal,
                                          step_execution=ex, status=status, detected_by=self.user_a)
        self.assertEqual(self._row(self.second, self.cal).acc_rej, "RPR")
