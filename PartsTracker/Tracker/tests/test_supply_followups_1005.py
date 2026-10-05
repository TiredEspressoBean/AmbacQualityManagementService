"""Supply follow-ups (2026-10-05): RMA + replacement on a return, material lots on
shipments, more than one hold at a time, and cycle counting."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        cls.tenant = Tenant.objects.create(name="Follow", slug="supply-followups-1005")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="fu", email="fu@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme Seals", is_customer=False)
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet Co", is_supplier=False)
            cls.other = Companies.objects.create(tenant=cls.tenant, name="Other Co", is_supplier=False)
            cls.bar = Material.objects.create(tenant=cls.tenant, name="Bar stock 4140", unit_of_measure="ft")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _lot(self, number, qty="100", status="ACCEPTED", owner=None, where="Rack 1", **kw):
        from Tracker.models import MaterialLot
        from Tracker.services.mes.locations import seed_location
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=number, material=self.bar, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="ft", status=status, supplier=self.acme,
            owner=owner, location=seed_location(self.tenant, where) if where else None,
            received_date=date.today(), **kw)


class RmaTests(_Fixture):
    def test_ship_back_keeps_the_rma_and_expects_the_replacement(self):
        from Tracker.models import MaterialLot, QuarantineDisposition
        bad = self._lot("RTV-1", qty="40", status="REJECTED", erp_po_number="4500", erp_po_line="3")
        QuarantineDisposition.objects.create(tenant=self.tenant, material_lot=bad,
                                             disposition_type="RETURN_TO_SUPPLIER", quantity=Decimal(40))
        due = date.today() + timedelta(days=10)
        resp = self.client.post(f"/api/MaterialLots/{bad.id}/ship-back/",
                                {"rma_number": "RMA-77", "replacement_promised_date": str(due)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["status"], resp.json()["rma_number"]), ("RETURNED", "RMA-77"))
        rep = MaterialLot.objects.get(replaces=bad)
        self.assertEqual((rep.status, rep.quantity, rep.promised_date, rep.erp_po_line), ("ON_ORDER", Decimal(40), due, "3"))
        self.assertEqual([r["lot_number"] for r in resp.json()["replacement_lots"]], [rep.lot_number])

    def test_rtv_sheet_prints_the_rma(self):
        from Tracker.reports.adapters.rtv_sheet import build_rtv_sheet_context
        bad = self._lot("RTV-2", status="REJECTED")
        self.assertEqual(build_rtv_sheet_context(bad, self.tenant, self.user, "RMA-9").rma_number, "RMA-9")


class LotShippingTests(_Fixture):
    def _ship(self, lots, **body):
        return self.client.post("/api/CustomerShipments/ship/", {"lots": lots, **body}, format="json")

    def test_a_customers_lot_goes_back_to_them_whole(self):
        theirs = self._lot("THEIRS", owner=self.fleet)
        ready = self.client.get("/api/CustomerShipments/ready/").json()
        self.assertIn(str(theirs.id), [l["id"] for g in ready for l in g["lots"]])
        resp = self._ship([{"lot_id": str(theirs.id)}])
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["customer_name"], "Fleet Co")
        theirs.refresh_from_db()
        self.assertEqual((theirs.status, theirs.quantity_remaining), ("SHIPPED", Decimal(0)))

    def test_part_of_our_own_lot_ships_split_and_void_puts_it_back(self):
        ours = self._lot("OURS", qty="100")
        resp = self._ship([{"lot_id": str(ours.id), "quantity": "36"}], customer=str(self.fleet.id))
        self.assertEqual(resp.status_code, 201, resp.content)
        shipped = resp.json()["lots"][0]
        self.assertEqual(shipped["quantity"], 36.0)
        ours.refresh_from_db()
        self.assertEqual((ours.status, ours.quantity_remaining), ("ACCEPTED", Decimal(64)))
        void = self.client.post(f"/api/CustomerShipments/{resp.json()['id']}/void/", {"reason": "wrong truck"},
                                format="json")
        self.assertEqual(void.status_code, 200, void.content)
        from Tracker.models import MaterialLot
        child = MaterialLot.objects.get(pk=shipped["id"])
        self.assertEqual((child.status, child.quantity_remaining), ("ACCEPTED", Decimal(36)))

    def test_a_customers_lot_cant_go_to_someone_else_and_shipped_stock_is_not_supply(self):
        theirs = self._lot("THEIRS-2", owner=self.fleet)
        bad = self._ship([{"lot_id": str(theirs.id)}], customer=str(self.other.id))
        self.assertEqual(bad.status_code, 400)
        from Tracker.services.mes.requirements import _TERMINAL_LOT_STATUSES
        self.assertIn("SHIPPED", _TERMINAL_LOT_STATUSES)


class HoldTests(_Fixture):
    def _received(self, **item_flags):
        from Tracker.services.qms.receiving_inspection import route_received_lot
        for k, v in item_flags.items():
            setattr(self.bar, k, v)
        self.bar.save()
        lot = self._lot("H-1", status="RECEIVED")
        route_received_lot(lot, self.user)
        lot.refresh_from_db()
        return lot

    def test_every_failing_gate_holds_and_each_clears_on_its_own(self):
        from Tracker.services.qms.receiving_inspection import reevaluate_hold
        lot = self._received(requires_coc=True, requires_heat_number=True)
        self.assertEqual((lot.status, lot.hold_reasons), ("QUARANTINE", ["AWAITING_COC", "AWAITING_HEAT_NUMBER"]))
        self.assertEqual(lot.hold_reason, "AWAITING_COC")
        lot.heat_number = "H9"
        lot.save(update_fields=["heat_number"])
        reevaluate_hold(lot, self.user)
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.hold_reasons, lot.hold_reason), ("QUARANTINE", ["AWAITING_COC"], "AWAITING_COC"))

    def test_releasing_one_of_several_needs_its_code_and_leaves_the_rest(self):
        lot = self._received(requires_coc=True, requires_heat_number=True)
        vague = self.client.post(f"/api/MaterialLots/{lot.id}/release-hold/", {"reason": "ok"}, format="json")
        self.assertEqual(vague.status_code, 400)
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/release-hold/",
                                {"reason": "Cert waived for this lot", "code": "AWAITING_COC"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual((resp.json()["status"], resp.json()["hold_reasons"]), ("QUARANTINE", ["AWAITING_HEAT_NUMBER"]))
        m = self.client.get("/api/MaterialLots/dock-metrics/").json()
        self.assertEqual(m["held_now"], [{"reason": "AWAITING_HEAT_NUMBER", "lots": 1}])

    def test_a_split_carries_every_hold(self):
        from Tracker.services.mes.material_lot import split_material_lot
        lot = self._received(requires_coc=True, requires_heat_number=True)
        child = split_material_lot(lot, Decimal(10))
        self.assertEqual(child.hold_reasons, ["AWAITING_COC", "AWAITING_HEAT_NUMBER"])


class CycleCountTests(_Fixture):
    def test_count_submit_apply(self):
        from Tracker.models import MaterialLot, RecordEdit
        short = self._lot("CC-A", qty="100", where="Rack 3")
        exact = self._lot("CC-B", qty="50", where="Rack 3")
        stray = self._lot("CC-C", qty="20", where="Rack 7")
        start = self.client.post("/api/CycleCounts/", {"location": "Rack 3", "blind": True}, format="json")
        self.assertEqual(start.status_code, 201, start.content)
        c = start.json()
        self.assertTrue(all(l["expected"] is None for l in c["lines"]))  # blind while counting
        rec = self.client.post(f"/api/CycleCounts/{c['id']}/record/", {"entries": [
            {"kind": "LOT", "id": str(short.id), "counted": "94"},
            {"kind": "LOT", "id": str(exact.id), "counted": "50"},
            {"kind": "LOT", "id": str(stray.id), "counted": "20"},
        ]}, format="json")
        self.assertEqual(rec.status_code, 200, rec.content)
        sub = self.client.post(f"/api/CycleCounts/{c['id']}/submit/", format="json").json()
        found = {v["label"]: v["variance"] for v in sub["variances"]}
        self.assertEqual(found, {"CC-A": "SHORT", "CC-C": "FOUND_HERE"})
        # A draw while the count waited isn't undone: the difference is applied to what's left now.
        short.quantity_remaining = Decimal(90)
        short.save(update_fields=["quantity_remaining"])
        done = self.client.post(f"/api/CycleCounts/{c['id']}/apply/", format="json")
        self.assertEqual((done.status_code, done.json()["status"]), (200, "APPLIED"))
        short.refresh_from_db()
        stray.refresh_from_db()
        self.assertEqual(short.quantity_remaining, Decimal(84))
        self.assertEqual(stray.storage_location, "Rack 3")
        self.assertTrue(RecordEdit.objects.filter(object_id=short.id, reason__startswith="Cycle count").exists())
        xlsx = self.client.get(f"/api/CycleCounts/{c['id']}/differences-xlsx/")
        self.assertEqual(xlsx.status_code, 200)

    def test_one_open_count_per_location_and_apply_needs_the_permission(self):
        self._lot("CC-D", where="Rack 4")
        first = self.client.post("/api/CycleCounts/", {"location": "Rack 4"}, format="json").json()
        self.assertEqual(self.client.post("/api/CycleCounts/", {"location": "Rack 4"}, format="json").status_code, 400)
        self.client.post(f"/api/CycleCounts/{first['id']}/submit/", format="json")
        clerk = User.objects.create_user(username="clerk", email="clerk@x.test", password="x", tenant=self.tenant)
        from Tracker.models import Tenant  # noqa: F401  (tenant membership comes with tenant=)
        self.client.force_authenticate(user=clerk)
        self.assertEqual(self.client.post(f"/api/CycleCounts/{first['id']}/apply/", format="json").status_code, 403)
