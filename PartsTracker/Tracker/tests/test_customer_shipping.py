"""Shipping to the customer (2026-10-05): the Ship step is the queue, a shipment is
one consignment to one customer, partial shipments count per order line, and a
shipment recorded by mistake can be voided.

Also the terminal-status fix it depends on: Steps.terminal_status is stored upper-case,
and the advancement map was keyed lower-case, so a Ship step never produced SHIPPED."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import (
            Companies, OrderLine, Orders, PartTypes, Processes, ProcessStep, Steps, Tenant,
            WorkOrder, WorkOrderStatus,
        )
        from Tracker.services.core.clock import tenant_today
        cls.tenant = Tenant.objects.create(name="Ship", slug="customer-shipping")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="sh", email="sh@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet Co", is_supplier=False,
                                                 address="400 Harbor Rd", requires_coc_on_shipment=True)
            cls.other = Companies.objects.create(tenant=cls.tenant, name="Other Co", is_supplier=False)
            cls.vendor = Companies.objects.create(tenant=cls.tenant, name="Acme", is_customer=False)
            cls.pt = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
            proc = Processes.objects.create(tenant=cls.tenant, name="Build", part_type=cls.pt)
            cls.build = Steps.objects.create(tenant=cls.tenant, part_type=cls.pt, name="Build", step_type="TASK")
            cls.ship = Steps.objects.create(tenant=cls.tenant, part_type=cls.pt, name="Ship", step_type="TASK",
                                            is_terminal=True, terminal_status="SHIPPED")
            ProcessStep.objects.create(process=proc, step=cls.build, order=1)
            ProcessStep.objects.create(process=proc, step=cls.ship, order=2)
            cls.today = tenant_today(cls.tenant)
            cls.order = Orders.objects.create(tenant=cls.tenant, name="Fleet job", company=cls.fleet)
            cls.line = OrderLine.objects.create(tenant=cls.tenant, order=cls.order, line_number=1,
                                                part_type=cls.pt, quantity=3,
                                                due_date=cls.today + timedelta(days=5))
            cls.wo = WorkOrder.objects.create(
                tenant=cls.tenant, ERP_id="WO-S1", quantity=3, process=proc, related_order=cls.order,
                order_line=cls.line, workorder_status=WorkOrderStatus.IN_PROGRESS)
            other_order = Orders.objects.create(tenant=cls.tenant, name="Other job", company=cls.other)
            cls.other_wo = WorkOrder.objects.create(
                tenant=cls.tenant, ERP_id="WO-S2", quantity=1, process=proc, related_order=other_order,
                workorder_status=WorkOrderStatus.IN_PROGRESS)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _part(self, erp, step=None, status="IN_PROGRESS", wo=None):
        from Tracker.models import Parts, StepExecution
        wo = wo or self.wo
        step = step or self.ship
        p = Parts.objects.create(tenant=self.tenant, ERP_id=erp, part_type=self.pt, work_order=wo,
                                 step=step, part_status=status)
        StepExecution.objects.create(tenant=self.tenant, part=p, step=step, visit_number=1,
                                     status="IN_PROGRESS",
                                     training_authorization={"authorized": True, "missing": [], "verified": []})
        return p

    def _ship(self, parts, **body):
        return self.client.post("/api/CustomerShipments/ship/",
                                {"part_ids": [str(p.id) for p in parts], **body}, format="json")


class TerminalStatusTests(_Fixture):
    def test_a_ship_step_ends_the_part_shipped_and_the_work_order_completes(self):
        from Tracker.services.mes.parts import advance_part_step
        parts = [self._part(f"S-{i}") for i in range(3)]
        for p in parts:
            advance_part_step(p, operator=self.user)
        for p in parts:
            p.refresh_from_db()
            self.assertEqual(p.part_status, "SHIPPED")
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.workorder_status, "COMPLETED")

    def test_lower_case_terminal_status_still_maps(self):
        from Tracker.models import Steps
        from Tracker.services.mes.parts import advance_part_step
        stock = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Stock", step_type="TASK",
                                     is_terminal=True, terminal_status="stock")
        p = self._part("ST-1", step=stock)
        advance_part_step(p, operator=self.user)
        p.refresh_from_db()
        self.assertEqual(p.part_status, "IN_STOCK")


class ShipTests(_Fixture):
    def test_ready_lists_ship_step_and_stock_parts_by_order_not_held_or_mid_route(self):
        self._part("R-1")
        self._part("R-2", status="QUARANTINED")
        self._part("R-3", step=self.build)
        self._part("R-4", status="IN_STOCK", step=self.build)
        rows = self.client.get("/api/CustomerShipments/ready/").json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["customer_name"], "Fleet Co")
        self.assertTrue(rows[0]["requires_coc"])
        self.assertEqual(sorted((p["erp_id"], p["source"]) for p in rows[0]["parts"]),
                         [("R-1", "SHIP_STEP"), ("R-4", "STOCK")])

    @mock.patch("Tracker.services.core.notifications.emit")
    def test_ship_creates_one_shipment_and_counts_per_order_line(self, emit):
        a, b = self._part("P-1"), self._part("P-2")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._ship([a, b], carrier="UPS", tracking_number="1Z1", reference="SHPR-9")
        self.assertEqual(resp.status_code, 201, resp.content)
        s = resp.json()
        self.assertTrue(s["shipment_number"].startswith("SHP-"))
        self.assertEqual((s["customer_name"], s["quantity"], s["requires_coc"]), ("Fleet Co", 2, True))
        for p in (a, b):
            p.refresh_from_db()
            self.assertEqual((p.part_status, str(p.customer_shipment_id)), ("SHIPPED", s["id"]))
        self.assertEqual(emit.call_args.args[0], "order.shipped")

        line = self.client.get(f"/api/CustomerShipments/order-shipping/?order={self.order.id}").json()["lines"][0]
        self.assertEqual((line["ordered"], line["shipped"], line["state"]), (3, 2, "PART_SHIPPED"))
        self.assertTrue(line["shipments"][0]["on_time"])
        perf = self.client.get("/api/CustomerShipments/delivery-performance/").json()
        self.assertEqual((perf["deliveries"], perf["on_time"], perf["on_time_pct"]), (1, 1, 100.0))

    def test_refuses_mixed_customers_unready_parts_and_non_customers(self):
        mine, theirs = self._part("M-1"), self._part("T-1", wo=self.other_wo)
        self.assertIn("different customers", self._ship([mine, theirs]).json()["detail"])
        early = self._part("E-1", step=self.build)
        self.assertIn("not at a Ship step", self._ship([early]).json()["detail"])
        self.assertIn("isn't set up as a customer",
                      self._ship([mine], customer=str(self.vendor.id)).json()["detail"])
        mine.refresh_from_db()
        self.assertEqual(mine.part_status, "IN_PROGRESS")  # all or nothing

    def test_void_puts_parts_back_at_the_ship_step_and_reopens_the_work_order(self):
        parts = [self._part(f"V-{i}") for i in range(3)]
        s = self._ship(parts).json()
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.workorder_status, "COMPLETED")
        resp = self.client.post(f"/api/CustomerShipments/{s['id']}/void/", {"reason": "wrong truck"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["is_voided"])
        # The voided record still says what was on it.
        self.assertEqual(sorted(p["ERP_id"] for p in resp.json()["parts"]), ["V-0", "V-1", "V-2"])
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.workorder_status, "IN_PROGRESS")
        for p in parts:
            p.refresh_from_db()
            self.assertEqual((p.part_status, p.customer_shipment_id), ("IN_PROGRESS", None))
        again = self._ship(parts)  # the fresh Ship-step visit ships again
        self.assertEqual(again.status_code, 201, again.content)

    def test_void_rejoins_a_piece_split_off_to_ship(self):
        """Corrections #33 (user decision 2026-10-26): the split-off piece rejoins its
        parent — one lot again — and is retired, kept and pointing at the parent."""
        from decimal import Decimal
        from Tracker.models import MaterialLot
        from Tracker.services.mes.shipping import ship, void_shipment
        lot = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="SEAL-1", material_description="Seal kit",
            quantity=Decimal(10), quantity_remaining=Decimal(10), unit_of_measure="EA",
            status="ACCEPTED")
        shipment = ship(tenant=self.tenant, user=self.user, customer=self.fleet,
                        lots=[{"lot": lot, "quantity": Decimal(3)}])
        piece = MaterialLot.objects.get(parent_lot=lot)
        void_shipment(shipment, user=self.user, reason="wrong pallet")
        lot.refresh_from_db()
        piece.refresh_from_db()
        self.assertEqual((lot.status, lot.quantity_remaining), ("ACCEPTED", Decimal(10)))
        self.assertEqual((piece.status, piece.quantity_remaining), ("CONSUMED", Decimal(0)))
        self.assertEqual(piece.parent_lot_id, lot.id)

    def test_void_leaves_a_lot_that_shipped_whole_as_it_was(self):
        from decimal import Decimal
        from Tracker.models import MaterialLot
        from Tracker.services.mes.shipping import ship, void_shipment
        lot = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="SEAL-2", material_description="Seal kit",
            quantity=Decimal(5), quantity_remaining=Decimal(5), unit_of_measure="EA",
            status="ACCEPTED")
        shipment = ship(tenant=self.tenant, user=self.user, customer=self.fleet,
                        lots=[{"lot": lot, "quantity": None}])
        void_shipment(shipment, user=self.user, reason="wrong pallet")
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.quantity_remaining), ("ACCEPTED", Decimal(5)))
        self.assertFalse(MaterialLot.objects.filter(parent_lot=lot).exists())

    def test_paperwork_editable_after_shipping_but_customer_is_not(self):
        s = self._ship([self._part("E-9")]).json()
        resp = self.client.patch(f"/api/CustomerShipments/{s['id']}/",
                                 {"tracking_number": "1Z-LATE", "customer": str(self.other.id)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["tracking_number"], resp.json()["customer_name"]), ("1Z-LATE", "Fleet Co"))


class DocumentTests(_Fixture):
    def test_packing_list_groups_by_line_with_serials(self):
        from Tracker.models import CustomerShipment
        from Tracker.reports.adapters.shipment_documents import build_shipment_document_context
        s = self._ship([self._part("D-2"), self._part("D-1")], reference="SHPR-1").json()
        ctx = build_shipment_document_context(CustomerShipment.objects.get(pk=s["id"]), self.tenant, self.user)
        self.assertEqual((ctx.customer_name, ctx.customer_address, ctx.reference, ctx.total_units),
                         ("Fleet Co", "400 Harbor Rd", "SHPR-1", 2))
        self.assertEqual([(i.line, i.serials) for i in ctx.items], [(1, ["D-1", "D-2"])])

    def test_trace_row_says_where_the_part_went(self):
        from Tracker.services.mes.lot_trace import _part_row
        p = self._part("TR-1")
        s = self._ship([p]).json()
        p.refresh_from_db()
        row = _part_row(p)
        self.assertEqual((row["shipment"], row["shipment_id"]), (s["shipment_number"], s["id"]))


class DeliveryPerformanceTests(_Fixture):
    """On-time delivery (2026-10-15).

    It used to filter on `work_order__order_line__due_date__isnull=False` inside the
    query, so a work order raised without an order line never reached the count. The
    result was a confident percentage of a subset, with the rest of the shipping
    silently absent — worse than an empty figure, because it reads as complete.
    """

    def _deliver(self, *specs):
        """Ship one consignment: (erp, work_order) pairs, all for one customer."""
        parts = [self._part(erp, wo=wo) for erp, wo in specs]
        with self.captureOnCommitCallbacks(execute=True):
            resp = self._ship(parts)
        self.assertEqual(resp.status_code, 201, resp.content)
        return parts

    def test_an_order_line_due_date_is_still_what_is_measured(self):
        from Tracker.services.mes.shipping import delivery_performance
        self._deliver(("D-1", self.wo))
        perf = delivery_performance(self.tenant)
        self.assertEqual(perf["deliveries"], 1)
        self.assertEqual(perf["on_time"], 1)
        self.assertEqual(perf["unmeasured"], 0)

    def test_a_work_order_with_no_line_falls_back_to_its_expected_completion(self):
        from Tracker.services.mes.shipping import delivery_performance
        self.other_wo.expected_completion = self.today + timedelta(days=5)
        self.other_wo.save(update_fields=["expected_completion"])
        self._deliver(("D-2", self.other_wo))
        perf = delivery_performance(self.tenant)
        self.assertEqual(perf["deliveries"], 1, "the fallback did not measure it")
        self.assertEqual(perf["on_time"], 1)
        self.assertEqual(perf["unmeasured"], 0)

    def test_a_late_fallback_counts_late_rather_than_being_dropped(self):
        from Tracker.services.mes.shipping import delivery_performance
        self.other_wo.expected_completion = self.today - timedelta(days=5)
        self.other_wo.save(update_fields=["expected_completion"])
        self._deliver(("D-3", self.other_wo))
        perf = delivery_performance(self.tenant)
        self.assertEqual(perf["deliveries"], 1)
        self.assertEqual(perf["on_time"], 0)
        self.assertEqual(perf["on_time_pct"], 0.0)

    def test_a_work_order_with_no_date_at_all_is_reported_not_hidden(self):
        from Tracker.services.mes.shipping import delivery_performance
        self.other_wo.expected_completion = None
        self.other_wo.save(update_fields=["expected_completion"])
        self._deliver(("D-4", self.other_wo))
        perf = delivery_performance(self.tenant)
        self.assertEqual(perf["deliveries"], 0, "it cannot be judged, so it is not scored")
        self.assertEqual(perf["unmeasured"], 1, "but it must not vanish")
        self.assertIsNone(perf["on_time_pct"])

    def test_two_undated_work_orders_on_one_shipment_are_two_deliveries(self):
        """The dict keyed on (shipment, order_line); with no line both rows would
        collapse to one key and a shipment covering two work orders would score once."""
        from Tracker.models import Orders, WorkOrder, WorkOrderStatus
        from Tracker.services.mes.shipping import delivery_performance
        self.other_wo.expected_completion = self.today + timedelta(days=5)
        self.other_wo.save(update_fields=["expected_completion"])
        third_order = Orders.objects.create(tenant=self.tenant, name="Third", company=self.other)
        third = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-S3", quantity=1, process=self.wo.process,
            related_order=third_order, workorder_status=WorkOrderStatus.IN_PROGRESS,
            expected_completion=self.today + timedelta(days=5))
        self._deliver(("D-5", self.other_wo), ("D-6", third))
        perf = delivery_performance(self.tenant)
        self.assertEqual(perf["deliveries"], 2, "two work orders collapsed into one delivery")


class RemanShippingTests(_Fixture):
    """A finished reman unit leaves on a shipment like any part (2026-10-20), so it has a
    packing list and CoC. Before this a customer's unit went back with a status change
    and no paperwork, and rebuilt exchange stock had no way out at all."""

    def _core(self, number, status, mode="REPAIR_RETURN", customer=None, wo=None):
        from Tracker.services.reman.core_part import create_core
        return create_core(tenant=self.tenant, core_number=number, core_type=self.pt,
                           fulfilment_mode=mode, status=status, work_order=wo,
                           customer=customer if customer is not None else self.other,
                           received_date=self.today, received_by=self.user)

    def test_a_customers_finished_unit_is_on_the_board_under_them(self):
        self._core("C-R1", "REBUILT")
        self._core("C-D1", "DECLINED")
        self._core("C-W1", "IN_REBUILD")              # not finished
        self._core("C-X1", "REBUILT_TO_STOCK", mode="EXCHANGE")  # stock on no order
        rows = self.client.get("/api/CustomerShipments/ready/").json()
        theirs = [g for g in rows if g["customer_name"] == "Other Co"]
        self.assertEqual(len(theirs), 1, rows)
        self.assertIsNone(theirs[0]["order_id"])
        self.assertEqual(sorted((p["erp_id"], p["source"], p["status"]) for p in theirs[0]["parts"]),
                         [("C-D1", "REMAN", "Scope declined — to be returned unrepaired"),
                          ("C-R1", "REMAN", "Rebuilt — ready to return")])

    def test_a_unit_on_another_customers_order_still_goes_to_its_owner(self):
        core = self._core("C-R2", "REBUILT", wo=self.wo)   # the WO is Fleet Co's order
        s = self._ship([core.part]).json()
        self.assertEqual(s["customer_name"], "Other Co", s)

    def test_shipping_returns_the_unit_and_prints_it(self):
        from Tracker.models import Core, CustomerShipment
        from Tracker.reports.adapters.shipment_documents import build_shipment_document_context
        core = self._core("C-R3", "REBUILT")
        resp = self._ship([core.part], reference="SHPR-R")
        self.assertEqual(resp.status_code, 201, resp.content)
        core = Core.objects.get(pk=core.pk)
        self.assertEqual((core.status, core.part.part_status), ("RETURNED", "SHIPPED"))
        self.assertEqual(core.return_reference, resp.json()["shipment_number"])
        ctx = build_shipment_document_context(
            CustomerShipment.objects.get(pk=resp.json()["id"]), self.tenant, self.user)
        self.assertEqual([i.serials for i in ctx.items], [["C-R3"]])

    def test_exchange_stock_on_an_order_ships_and_ends_shipped(self):
        from Tracker.models import Core
        core = self._core("C-X2", "REBUILT_TO_STOCK", mode="EXCHANGE", wo=self.wo)
        rows = self.client.get("/api/CustomerShipments/ready/").json()
        fleet = next(g for g in rows if g["order_id"] == str(self.order.id))
        self.assertIn(("C-X2", "REMAN"), [(p["erp_id"], p["source"]) for p in fleet["parts"]])
        resp = self._ship([core.part])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["customer_name"], "Fleet Co")
        core = Core.objects.get(pk=core.pk)
        self.assertEqual((core.status, core.part.part_status, core.return_reference),
                         ("SHIPPED", "SHIPPED", ""))

    def test_an_unfinished_or_unready_unit_is_refused(self):
        wip = self._core("C-W2", "IN_REBUILD")
        self.assertIn("not finished", self._ship([wip.part]).json()["detail"])
        # An exchange unit is shop stock once rebuilt to stock, never "REBUILT".
        odd = self._core("C-X3", "REBUILT", mode="EXCHANGE")
        self.assertIn("exchange unit", self._ship([odd.part], customer=str(self.other.id)).json()["detail"])

    def test_void_puts_the_unit_back_at_the_stage_it_left_from(self):
        from Tracker.models import Core
        core = self._core("C-R4", "REBUILT")
        s = self._ship([core.part]).json()
        resp = self.client.post(f"/api/CustomerShipments/{s['id']}/void/", {"reason": "wrong unit"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([p["ERP_id"] for p in resp.json()["parts"]], ["C-R4"])
        core = Core.objects.get(pk=core.pk)
        self.assertEqual((core.status, core.return_reference, core.returned_at), ("REBUILT", "", None))
        self.assertIsNone(core.part.customer_shipment_id)
        self.assertEqual(self._ship([core.part]).status_code, 201)  # and it can go again

    def test_the_core_return_endpoint_ships_it(self):
        core = self._core("C-R5", "DECLINED")
        resp = self.client.post(f"/api/Cores/{core.id}/return_to_customer/",
                                {"reference": "SHPR-5", "carrier": "Pickup"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "RETURNED_UNREPAIRED")
        core.part.refresh_from_db()
        shipment = core.part.customer_shipment
        self.assertEqual((shipment.customer_id, shipment.reference, shipment.carrier),
                         (self.other.id, "SHPR-5", "Pickup"))
