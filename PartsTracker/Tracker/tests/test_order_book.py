"""Production › Orders: the order book and the staff order page (spec 2026-10-21)."""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    Companies, Core, CustomerShipment, OrderLine, Orders, Parts, PartTypes, Processes, ScheduledTask,
    ScheduleResult, Steps, WorkOrder, WorkOrderHold,
)
from Tracker.services.mes.order_book import order_book, order_detail
from Tracker.tests.base import TenantTestCase


class OrderBookTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Common Rail Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Machining", part_type=self.pt)
        self.ship = Steps.objects.create(tenant=self.tenant_a, name="Ship", part_type=self.pt,
                                         step_type="TERMINAL", is_terminal=True)
        self.process = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=self.pt)
        self.acme = Companies.objects.create(tenant=self.tenant_a, name="Great Lakes Diesel")
        self.today = timezone.localdate()
        # A planner: sees the whole tenant's demand and work.
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_orders', 'view_workorder', 'view_parts', 'view_customershipment',
            'full_tenant_access'])

    def _order(self, number, qty=6, due_in=20):
        o = Orders.objects.create(tenant=self.tenant_a, name=number, order_number=number, company=self.acme)
        line = OrderLine.objects.create(tenant=self.tenant_a, order=o, line_number=1, part_type=self.pt,
                                        quantity=qty, due_date=self.today + timedelta(days=due_in))
        return o, line

    def _wo(self, order, line, erp, n, step=None):
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id=erp, quantity=n, related_order=order,
                                      order_line=line, process=self.process,
                                      expected_completion=line.due_date)
        parts = [Parts.objects.create(tenant=self.tenant_a, ERP_id=f"{erp}-{i}", part_type=self.pt,
                                      work_order=wo, step=step or self.step, part_status="PENDING")
                 for i in range(n)]
        return wo, parts

    def _schedule(self, parts, end):
        now = timezone.now()
        s = ScheduleResult.objects.create(tenant=self.tenant_a, horizon_start=now,
                                          horizon_end=now + timedelta(days=60), is_active=True)
        for p in parts:
            ScheduledTask.objects.create(tenant=self.tenant_a, schedule=s, part=p, step=self.step,
                                         start_time=end - timedelta(hours=1), end_time=end)

    def _row(self, number):
        return next(r for r in order_book(self.user_a, self.tenant_a).rows if r.order_number == number)

    def test_an_order_with_no_work_orders_is_listed_as_needing_planning(self):
        self._order("ORD-0051", qty=6)
        row = self._row("ORD-0051")
        self.assertEqual(row.unplanned, 6)
        self.assertEqual(row.projection.state, "not_scheduled")

    def test_projected_against_promised(self):
        o, line = self._order("ORD-LATE", qty=2, due_in=5)
        _, parts = self._wo(o, line, "WO-LATE", 2)
        late_end = timezone.make_aware(timezone.datetime.combine(self.today + timedelta(days=8),
                                                                 timezone.datetime.min.time())) + timedelta(hours=12)
        self._schedule(parts, late_end)
        p = self._row("ORD-LATE").projection
        self.assertEqual((p.state, p.slip_days), ("late", 3))

        o2, line2 = self._order("ORD-OK", qty=1, due_in=30)
        _, parts2 = self._wo(o2, line2, "WO-OK", 1)
        ok_end = timezone.now() + timedelta(days=2)
        ScheduleResult.objects.update(is_active=False)
        self._schedule(parts2 + parts, ok_end)
        self.assertEqual(self._row("ORD-OK").projection.state, "on_track")

    def test_unscheduled_units_are_not_on_track(self):
        o, line = self._order("ORD-UNS", qty=2)
        self._wo(o, line, "WO-UNS", 2)
        self.assertEqual(self._row("ORD-UNS").projection.state, "not_scheduled")

    def test_blockers_hold_and_quarantine(self):
        o, line = self._order("ORD-BLK", qty=2)
        wo, parts = self._wo(o, line, "WO-BLK", 2)
        WorkOrderHold.objects.create(tenant=self.tenant_a, work_order=wo, reason="QUALITY")
        Parts.objects.filter(pk=parts[0].pk).update(part_status="QUARANTINED")
        kinds = {b.kind for b in self._row("ORD-BLK").blockers}
        self.assertEqual(kinds, {"on_hold", "quarantined"})
        self.assertTrue(self._row("ORD-BLK").at_risk)

    def test_shipments_are_judged_on_time_against_the_line(self):
        o, line = self._order("ORD-SHP", qty=2, due_in=-1)
        wo, parts = self._wo(o, line, "WO-SHP", 2, step=self.ship)
        shipment = CustomerShipment.objects.create(tenant=self.tenant_a, customer=self.acme,
                                                   shipment_number="SHP-1", shipped_at=timezone.now())
        Parts.objects.filter(pk__in=[p.pk for p in parts]).update(
            part_status="SHIPPED", customer_shipment=shipment)
        detail = order_detail(o, self.user_a)
        s, = detail.shipments
        self.assertEqual((s.quantity, s.on_time), (2, False))   # due yesterday, shipped today

    def test_a_work_order_with_no_units_is_not_on_track(self):
        """A WO for 8 with no parts has nothing on the schedule; that's not "on track"."""
        o = Orders.objects.create(tenant=self.tenant_a, name="ORD-0048", order_number="ORD-0048",
                                  company=self.acme)
        WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-0048-A", quantity=8, related_order=o,
                                 process=self.process, expected_completion=self.today + timedelta(days=10))
        row = self._row("ORD-0048")
        self.assertEqual(row.projection.state, "not_scheduled")
        self.assertEqual([b.kind for b in row.blockers], ["no_units"])
        # No lines: the work order says what the order is for.
        self.assertEqual((row.progress.ordered, row.earliest_due), (8, self.today + timedelta(days=10)))

    def test_cores_received_for_the_order_count_against_its_line(self):
        from Tracker.services.reman.core_part import create_core
        o, line = self._order("ORD-REP", qty=2)
        core = create_core(tenant=self.tenant_a, core_type=self.pt, customer=self.acme,
                           fulfilment_mode='REPAIR_RETURN', order=o, received_by=self.user_a,
                           received_date=self.today)
        labels = [b.label for b in self._row("ORD-REP").blockers]
        self.assertEqual(labels, ["L1: cores 1/2 received"])

        Core.objects.filter(pk=core.pk).update(status='AWAITING_AUTHORISATION')
        create_core(tenant=self.tenant_a, core_type=self.pt, customer=self.acme,
                    fulfilment_mode='REPAIR_RETURN', order=o, received_by=self.user_a,
                           received_date=self.today)
        labels = [b.label for b in self._row("ORD-REP").blockers]
        self.assertEqual(labels, [f"{core.core_number} awaiting authorisation"])

    def test_a_repair_core_worked_on_its_teardown_order_plans_and_projects_the_line(self):
        """The customer's unit is rebuilt on its teardown WO, which isn't pegged to the
        order. It covers the line, and its schedule is the order's projection."""
        from Tracker.services.reman.core_part import create_core
        o, line = self._order("ORD-RR", qty=1, due_in=20)
        teardown = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-TD-1", quantity=1,
                                            process=self.process)
        core = create_core(tenant=self.tenant_a, core_type=self.pt, customer=self.acme,
                           fulfilment_mode='REPAIR_RETURN', order=o, received_by=self.user_a,
                           received_date=self.today,
                           work_order=teardown, step=self.step, status='IN_REBUILD')
        line.refresh_from_db()
        self.assertEqual(line.remaining_quantity, 0)
        self.assertEqual(self._row("ORD-RR").projection.state, "not_scheduled")

        self._schedule([core.part], timezone.now() + timedelta(days=3))
        row = self._row("ORD-RR")
        self.assertEqual((row.unplanned, row.projection.state), (0, "on_track"))
        wo, = order_detail(o, self.user_a).work_orders
        self.assertEqual((wo.erp_id, wo.units), ("WO-TD-1", (core.core_number,)))

    def test_a_held_unit_is_not_on_track(self):
        """The solver skips a held unit, so it has no task — "not scheduled", never
        "on track" because nothing open was left to schedule."""
        o, line = self._order("ORD-HLD", qty=1)
        _, parts = self._wo(o, line, "WO-HLD", 1)
        Parts.objects.filter(pk=parts[0].pk).update(part_status="ON_HOLD")
        self.assertEqual(self._row("ORD-HLD").projection.state, "not_scheduled")
