"""The requirements report's Ship lane: what customers are owed, by when.

One row per open order line still to ship. Overdue first, then by due date, no due
date last; RFI lines tentative; a fully shipped line drops out; what is left to ship
splits into covered by work orders and not yet planned.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    OrderLine, Orders, Parts, PartTypes, Processes, ProcessStatus, ProcessStep, Steps,
    Tenant, WorkOrder,
)
from Tracker.services.core.clock import tenant_today
from Tracker.services.mes.requirements import ship_lane
from Tracker.tests.base import TenantContextMixin


class ShipLaneTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Ship", slug="ship-lane", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="ship", email="ship@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector", ERP_id="INJ-1")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Build", part_type=self.pt, status=ProcessStatus.APPROVED)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Assemble",
                                         step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.today = tenant_today(self.tenant)

    def _line(self, qty, due, status="PENDING", name="O"):
        order = Orders.objects.create(tenant=self.tenant, name=name, order_status=status)
        return OrderLine.objects.create(tenant=self.tenant, order=order, line_number=1,
                                        part_type=self.pt, quantity=qty, due_date=due)

    @staticmethod
    def _name(row):
        """The test's own label for a row's order (the lane shows its order number)."""
        return Orders.objects.get(id=row["order_id"]).name

    def _work(self, line, qty, shipped=0):
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id=f"WO-{line.order.name}",
                                      quantity=qty, process=self.process, order_line=line,
                                      related_order=line.order)
        for i in range(qty):
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{wo.ERP_id}-{i}", part_type=self.pt,
                                 work_order=wo, step=self.step,
                                 part_status="SHIPPED" if i < shipped else "IN_PROGRESS")
        return wo

    def test_overdue_first_then_by_due_date_and_no_due_date_last(self):
        self._line(1, self.today + timedelta(days=40), name="LATER")
        self._line(1, None, name="UNDATED")
        self._line(1, self.today - timedelta(days=5), name="OVERDUE")
        self._line(1, self.today + timedelta(days=10), name="SOON")
        rows = ship_lane(self.tenant)
        self.assertEqual([self._name(r) for r in rows], ["OVERDUE", "SOON", "LATER", "UNDATED"])
        self.assertTrue(rows[0]["overdue"])
        self.assertIsNone(rows[-1]["month"])

    def test_rfi_lines_are_marked_tentative(self):
        self._line(3, self.today + timedelta(days=30), status="RFI", name="DEAL")
        self._line(2, self.today + timedelta(days=30), name="FIRM")
        by = {self._name(r): r["tentative"] for r in ship_lane(self.tenant)}
        self.assertEqual(by, {"DEAL": True, "FIRM": False})

    def test_a_fully_shipped_line_drops_out(self):
        line = self._line(2, self.today + timedelta(days=5), name="DONE")
        self._work(line, 2, shipped=2)
        self.assertEqual(ship_lane(self.tenant), [])

    def test_still_to_ship_splits_into_covered_and_not_yet_planned(self):
        line = self._line(10, self.today + timedelta(days=20), name="SPLIT")
        self._work(line, 6, shipped=2)
        row = ship_lane(self.tenant)[0]
        self.assertEqual((row["quantity"], row["shipped"], row["to_ship"]), (10, 2, 8))
        self.assertEqual((row["planned"], row["unplanned"]), (4, 4))
        self.assertEqual(row["note"], "in work")

    def _unit_worked_elsewhere(self, line, status):
        """A unit received FOR the order, worked on its own teardown work order — the
        way a repair-and-return core is — that `planned_quantity` counts as coverage."""
        teardown = Processes.objects.create(tenant=self.tenant, name="Tear", part_type=self.pt,
                                            status=ProcessStatus.APPROVED, is_disassembly=True)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id=f"TD-{status}", quantity=1,
                                      process=teardown)
        return Parts.objects.create(tenant=self.tenant, ERP_id=f"CORE-{status}", part_type=self.pt,
                                    work_order=wo, step=self.step, order=line.order,
                                    part_status=status)

    def test_a_repair_and_return_unit_shipped_elsewhere_clears_the_line(self):
        line = self._line(1, self.today + timedelta(days=5), name="RR")
        self._unit_worked_elsewhere(line, "SHIPPED")
        self.assertEqual(ship_lane(self.tenant), [])

    def test_a_repair_and_return_unit_awaiting_pickup_reads_ready(self):
        line = self._line(2, self.today + timedelta(days=5), name="RR")
        self._unit_worked_elsewhere(line, "AWAITING_PICKUP")
        row = ship_lane(self.tenant)[0]
        self.assertEqual((row["to_ship"], row["ready"], row["note"]), (2, 1, "1 ready to ship"))

    def test_a_unit_worked_elsewhere_covers_one_line_not_every_line(self):
        """planned_quantity deals the order's units out once across its lines of the part
        type — counted against every line, a two-line order read covered twice."""
        line1 = self._line(1, self.today + timedelta(days=5), name="TWO")
        line2 = OrderLine.objects.create(tenant=self.tenant, order=line1.order, line_number=2,
                                         part_type=self.pt, quantity=1,
                                         due_date=self.today + timedelta(days=9))
        self._unit_worked_elsewhere(line1, "IN_PROGRESS")
        self.assertEqual((line1.planned_quantity, line2.planned_quantity), (1, 0))
        self.assertEqual((line1.remaining_quantity, line2.remaining_quantity), (0, 1))

    def test_an_untouched_line_is_not_started_and_wholly_unplanned(self):
        self._line(4, self.today + timedelta(days=20), name="NEW")
        row = ship_lane(self.tenant)[0]
        self.assertEqual((row["planned"], row["unplanned"], row["note"]), (0, 4, "not started"))
