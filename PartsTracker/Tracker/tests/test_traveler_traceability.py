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
