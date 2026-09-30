"""The buyer's side of receiving (2026-09-30, receiving plan Phase 1).

- Late deliveries: an ON_ORDER lot against its promised date on the plant's day, and
  the open work orders whose BOM calls for the item.
- A PO line beside the PO number, so an import can match on (PO, line).
- The expected-receipts import: typed up from an ERP that can't send anything, so it
  only adds and updates — never closes, and never re-opens a received line.
- Shortage → expected receipt: requirements rows carry what a buyer needs to raise one
  without re-keying, and several can be raised at once, all or nothing.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import (
            BOM, BOMLine, Companies, Material, PartTypes, Processes, Tenant, WorkOrder,
            WorkOrderStatus,
        )
        cls.tenant = Tenant.objects.create(name="Buyer", slug="receiving-phase1")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="buyer", email="buyer@x.test",
                                                password="x", tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme Seals")
            cls.shim = Material.objects.create(
                tenant=cls.tenant, name="Shim 0.010", part_number="SHIM-0.010",
                unit_of_measure="EA", purchase_lead_time_days=10, preferred_supplier=cls.acme)
            cls.housing = PartTypes.objects.create(
                tenant=cls.tenant, name="Housing", ERP_id="HSG-1", can_buy=True,
                preferred_supplier=cls.acme)
            cls.asm = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
            proc = Processes.objects.create(tenant=cls.tenant, name="P", part_type=cls.asm,
                                            status="APPROVED", is_current_version=True)
            bom = BOM.objects.create(tenant=cls.tenant, part_type=cls.asm, revision="A",
                                     bom_type="ASSEMBLY", status="RELEASED",
                                     is_current_version=True)
            BOMLine.objects.create(tenant=cls.tenant, bom=bom, material=cls.shim,
                                   quantity=Decimal(4), source="BUY", line_number=1)
            cls.wo = WorkOrder.objects.create(
                tenant=cls.tenant, ERP_id="WO-100", workorder_status=WorkOrderStatus.PENDING,
                quantity=10, process=proc, expected_start=date.today() + timedelta(days=30))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _on_order(self, promised, **kw):
        from Tracker.services.mes.material_lot import record_expected_receipt
        return record_expected_receipt(tenant=self.tenant, quantity=Decimal(kw.pop("qty", 100)),
                                       promised_date=promised, material=kw.pop("material", self.shim),
                                       **kw)


class DeliveryStateTests(_Fixture):
    def test_overdue_due_soon_and_neither(self):
        from Tracker.services.mes.material_lot import delivery_state
        today = date(2026, 10, 1)
        lot = self._on_order(today - timedelta(days=1))
        self.assertEqual(delivery_state(lot, today), "OVERDUE")
        lot.promised_date = today
        self.assertEqual(delivery_state(lot, today), "DUE_SOON")  # due today isn't late yet
        lot.promised_date = today + timedelta(days=3)
        self.assertEqual(delivery_state(lot, today), "DUE_SOON")
        lot.promised_date = today + timedelta(days=4)
        self.assertIsNone(delivery_state(lot, today))

    def test_a_received_lot_has_no_delivery_state(self):
        from Tracker.services.mes.material_lot import delivery_state
        lot = self._on_order(date.today() - timedelta(days=5))
        lot.status = "RECEIVED"
        self.assertIsNone(delivery_state(lot, date.today()))

    def test_list_filter_and_field(self):
        from Tracker.services.core.clock import tenant_today
        today = tenant_today(self.tenant)
        late = self._on_order(today - timedelta(days=2), erp_po_number="P1")
        soon = self._on_order(today + timedelta(days=1), erp_po_number="P2")
        self._on_order(today + timedelta(days=20), erp_po_number="P3")
        ids = lambda q: {r["id"] for r in self.client.get(f"/api/MaterialLots/?delivery={q}").json()["results"]}
        self.assertEqual(ids("overdue"), {str(late.id)})
        self.assertEqual(ids("due_soon"), {str(soon.id)})
        self.assertEqual(ids("late"), {str(late.id), str(soon.id)})
        row = self.client.get(f"/api/MaterialLots/{late.id}/").json()
        self.assertEqual(row["delivery_state"], "OVERDUE")


class LateDeliveriesTests(_Fixture):
    def test_lists_late_lots_with_the_work_they_hold_up(self):
        from Tracker.services.core.clock import tenant_today
        today = tenant_today(self.tenant)
        self._on_order(today - timedelta(days=4), erp_po_number="P1", erp_po_line="10")
        self._on_order(today + timedelta(days=30))  # not late — excluded
        rows = self.client.get("/api/MaterialLots/late-deliveries/").json()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["state"], r["days_late"], r["erp_po_line"]), ("OVERDUE", 4, "10"))
        self.assertEqual(r["supplier_name"], "Acme Seals")
        self.assertEqual([w["erp_id"] for w in r["holding_up"]], ["WO-100"])

    def test_an_item_no_bom_calls_for_holds_nothing_up(self):
        from Tracker.services.core.clock import tenant_today
        self._on_order(tenant_today(self.tenant) - timedelta(days=1),
                       material=None, material_type=self.housing)
        rows = self.client.get("/api/MaterialLots/late-deliveries/").json()
        self.assertEqual((rows[0]["holding_up_count"], rows[0]["holding_up"]), (0, []))


class PoLineTests(_Fixture):
    def test_po_line_round_trips_and_follows_a_backorder(self):
        from Tracker.models import MaterialLot
        resp = self.client.post("/api/MaterialLots/expected-receipt/", {
            "material": str(self.shim.id), "quantity": "100",
            "promised_date": str(date.today() + timedelta(days=5)),
            "erp_po_number": "4500123", "erp_po_line": "20"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["erp_po_line"], "20")
        lot = MaterialLot.objects.get(pk=resp.json()["id"])
        from Tracker.services.mes.material_lot import receive_expected_lot
        receive_expected_lot(lot, lot_number="SUP-1", received_by=self.user,
                             quantity=Decimal(60), remainder="BACKORDERED")
        rest = MaterialLot.objects.get(status="ON_ORDER", erp_po_number="4500123")
        self.assertEqual((rest.erp_po_line, rest.quantity), ("20", Decimal(40)))


class ImportTests(_Fixture):
    def _upload(self, text):
        f = SimpleUploadedFile("open_pos.csv", text.encode("utf-8"), content_type="text/csv")
        return self.client.post("/api/MaterialLots/import-expected/", {"file": f}, format="multipart")

    HEAD = "PO Number*,PO Line*,Item*,Quantity*,Promised Date*,Supplier,Unit\n"

    def test_creates_then_updates_on_reimport_without_duplicates(self):
        from Tracker.models import MaterialLot
        r1 = self._upload(self.HEAD + "4500123,10,SHIM-0.010,5000,2026-10-15,Acme Seals,EA\n"
                                      "4500123,20,HSG-1,4,2026-10-20,,\n").json()
        self.assertEqual((r1["created"], r1["errors"]), (2, 0), r1)
        r2 = self._upload(self.HEAD + "4500123,10,SHIM-0.010,4000,2026-10-18,,\n"
                                      "4500123,20,Housing,4,2026-10-20,,\n").json()
        self.assertEqual((r2["created"], r2["updated"], r2["unchanged"]), (0, 1, 1), r2)
        lot = MaterialLot.objects.get(erp_po_number="4500123", erp_po_line="10")
        self.assertEqual((lot.quantity, lot.quantity_remaining, str(lot.promised_date)),
                         (Decimal(4000), Decimal(4000), "2026-10-18"))
        self.assertEqual(MaterialLot.objects.filter(erp_po_number="4500123").count(), 2)

    def test_never_closes_and_never_reopens_a_received_line(self):
        from Tracker.models import MaterialLot
        from Tracker.services.mes.material_lot import receive_expected_lot
        self._upload(self.HEAD + "P9,1,SHIM-0.010,10,2026-10-15,,\nP9,2,SHIM-0.010,10,2026-10-15,,\n")
        receive_expected_lot(MaterialLot.objects.get(erp_po_number="P9", erp_po_line="1"),
                             lot_number="R-1", received_by=self.user)
        # Line 2 missing from this sheet; line 1 already received.
        r = self._upload(self.HEAD + "P9,1,SHIM-0.010,10,2026-10-15,,\n").json()
        self.assertEqual(r["already_received"], 1, r)
        self.assertEqual(MaterialLot.objects.get(erp_po_number="P9", erp_po_line="2").status, "ON_ORDER")
        self.assertEqual(MaterialLot.objects.filter(erp_po_number="P9", status="ON_ORDER").count(), 1)

    def test_bad_rows_are_reported_and_the_rest_still_land(self):
        r = self._upload(self.HEAD + "P1,1,NOPE,10,2026-10-15,,\n"
                                     "P1,2,SHIM-0.010,ten,2026-10-15,,\n"
                                     ",3,SHIM-0.010,10,2026-10-15,,\n"
                                     "P1,4,SHIM-0.010,10,2026-10-15,,\n").json()
        self.assertEqual((r["errors"], r["created"]), (3, 1), r)
        self.assertEqual([row["outcome"] for row in r["rows"]], ["ERROR"] * 3 + ["CREATED"])

    def test_a_line_on_order_for_a_different_item_is_an_error(self):
        self._upload(self.HEAD + "P2,1,SHIM-0.010,10,2026-10-15,,\n")
        r = self._upload(self.HEAD + "P2,1,HSG-1,10,2026-10-15,,\n").json()
        self.assertEqual(r["errors"], 1, r)

    def test_template_downloads(self):
        resp = self.client.get("/api/MaterialLots/import-expected-template/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("PO Line*", resp.content.decode("utf-8-sig"))


class ShortageToExpectTests(_Fixture):
    def test_source_rows_carry_what_a_buyer_needs(self):
        from Tracker.services.mes.requirements import sourcing_requirements
        row = next(r for r in sourcing_requirements(self.tenant)["source"] if r["material"] == "Shim 0.010")
        self.assertEqual(row["item_id"], str(self.shim.id))
        self.assertEqual(row["part_number"], "SHIM-0.010")
        self.assertEqual(row["unit_of_measure"], "EA")
        self.assertEqual((row["preferred_supplier_id"], row["preferred_supplier_name"]),
                         (str(self.acme.id), "Acme Seals"))

    def test_bulk_expected_receipts_are_all_or_nothing(self):
        from Tracker.models import MaterialLot
        promised = str(date.today() + timedelta(days=10))
        ok = self.client.post("/api/MaterialLots/bulk-expected-receipt/", {"receipts": [
            {"material": str(self.shim.id), "quantity": "40", "promised_date": promised},
            {"material_type": str(self.housing.id), "quantity": "4", "promised_date": promised,
             "erp_po_number": "4500200", "erp_po_line": "1"},
        ]}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(len(ok.json()), 2)
        before = MaterialLot.objects.count()
        bad = self.client.post("/api/MaterialLots/bulk-expected-receipt/", {"receipts": [
            {"material": str(self.shim.id), "quantity": "40", "promised_date": promised},
            {"quantity": "4", "promised_date": promised},  # no item
        ]}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(MaterialLot.objects.count(), before)

    def test_an_expected_receipt_covers_the_shortage(self):
        from Tracker.services.mes.requirements import sourcing_requirements
        short = next(r for r in sourcing_requirements(self.tenant)["source"]
                     if r["material"] == "Shim 0.010")["qty_short"]
        self.assertEqual(short, 40)
        self._on_order(date.today() + timedelta(days=5), qty=40)
        self.assertFalse([r for r in sourcing_requirements(self.tenant)["source"]
                          if r["material"] == "Shim 0.010" and r["qty_short"] > 0])
