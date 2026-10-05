"""Recorded moves, location views and scan lookup (2026-10-05).

- A lot or a unit changes location only by a move, and every move is recorded.
- With a managed location list, a move must go to one of its locations; a scanned
  location label (`LOC:<name>`) names one.
- One resolver turns any scanned code into what it names.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Material, PartTypes, Parts, Tenant, WorkOrder
        cls.tenant = Tenant.objects.create(name="Locs", slug="locations-scan")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="lc", email="lc@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.shim = Material.objects.create(tenant=cls.tenant, name="Shim", unit_of_measure="EA")
            cls.pt = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
            cls.wo = WorkOrder.objects.create(tenant=cls.tenant, ERP_id="WO-LOC-77", quantity=1)
            cls.part = Parts.objects.create(tenant=cls.tenant, ERP_id="INJ-9001", part_type=cls.pt,
                                            work_order=cls.wo, part_status="IN_STOCK")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _lot(self, number="L-1", qty="100", where="Rack 1", status="ACCEPTED"):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=number, material=self.shim, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="EA", status=status, storage_location=where)

    def _managed(self, *names):
        from Tracker.models import StorageLocation
        for n in names:
            StorageLocation.objects.create(tenant=self.tenant, name=n)


class MoveTests(_Fixture):
    def test_whole_lot_move_is_recorded(self):
        from Tracker.models import RecordEdit
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Rack 2", "reason": "re-slot"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["storage_location"], "Rack 2")
        edit = RecordEdit.objects.get(object_id=lot.id, field_name="storage_location")
        self.assertEqual((edit.old_value, edit.new_value, edit.reason, edit.edited_by_id),
                         ("Rack 1", "Rack 2", "re-slot", self.user.id))

    def test_partial_move_splits_and_the_rest_stays(self):
        lot = self._lot(qty="100")
        moved = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Cage B", "quantity": "30"},
                                 format="json").json()
        lot.refresh_from_db()
        self.assertNotEqual(moved["id"], str(lot.id))
        self.assertEqual((moved["storage_location"], float(moved["quantity_remaining"])), ("Cage B", 30.0))
        self.assertEqual((lot.storage_location, lot.quantity_remaining), ("Rack 1", Decimal("70")))

    def test_managed_list_is_enforced_and_a_scanned_label_names_a_location(self):
        self._managed("Rack 3")
        lot = self._lot()
        bad = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Rack 9"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("isn't one of your storage locations", bad.json()["detail"])
        ok = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "LOC:rack 3"}, format="json")
        self.assertEqual(ok.json()["storage_location"], "Rack 3")  # the tenant's spelling

    def test_an_edited_location_is_recorded_too_and_gone_lots_dont_move(self):
        from Tracker.models import RecordEdit
        lot = self._lot()
        resp = self.client.patch(f"/api/MaterialLots/{lot.id}/", {"storage_location": "Elsewhere"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        edit = RecordEdit.objects.get(object_id=lot.id, field_name="storage_location")
        self.assertEqual((edit.old_value, edit.new_value), ("Rack 1", "Elsewhere"))
        used = self._lot(number="L-USED", status="CONSUMED")
        resp = self.client.post(f"/api/MaterialLots/{used.id}/move/", {"to": "Rack 2"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_units_move_and_shipped_ones_dont(self):
        from Tracker.models import Parts
        resp = self.client.post("/api/Parts/move/", {"part_ids": [str(self.part.id)], "to": "Yard"}, format="json")
        self.assertEqual((resp.status_code, resp.json()["moved"]), (200, 1))
        self.part.refresh_from_db()
        self.assertEqual(self.part.storage_location, "Yard")
        gone = Parts.objects.create(tenant=self.tenant, ERP_id="INJ-GONE", part_type=self.pt, part_status="SHIPPED")
        resp = self.client.post("/api/Parts/move/", {"part_ids": [str(gone.id)], "to": "Yard"}, format="json")
        self.assertEqual(resp.status_code, 400)


class LocationViewTests(_Fixture):
    def test_summary_contents_and_moves(self):
        lot = self._lot(where="Rack 1")
        self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Cage B", "quantity": "10"}, format="json")
        self.client.post("/api/Parts/move/", {"part_ids": [str(self.part.id)], "to": "Rack 1"}, format="json")
        self._managed("Rack 1", "Empty Shelf")  # the list set up afterwards
        summary = {r["name"]: r for r in self.client.get("/api/StorageLocations/summary/").json()}
        self.assertEqual((summary["Rack 1"]["lots"], summary["Rack 1"]["parts"]), (1, 1))
        self.assertTrue(summary["Empty Shelf"]["managed"])
        self.assertFalse(summary["Cage B"]["managed"])  # typed, never put on the list
        c = self.client.get("/api/StorageLocations/contents/?name=rack 1").json()
        self.assertEqual([l["lot_number"] for l in c["lots"]], ["L-1"])
        self.assertEqual([p["erp_id"] for p in c["parts"]], ["INJ-9001"])
        self.assertEqual({(m["direction"], m["label"]) for m in c["moves"]},
                         {("OUT", "L-1-01"), ("IN", "INJ-9001")})

    def test_renaming_a_location_carries_its_contents(self):
        from Tracker.models import StorageLocation
        self._managed("Rack 1")
        lot = self._lot(where="Rack 1")
        loc = StorageLocation.objects.get(name="Rack 1")
        resp = self.client.patch(f"/api/StorageLocations/{loc.id}/", {"name": "Rack 1A"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot.refresh_from_db()
        self.assertEqual(lot.storage_location, "Rack 1A")


class ScanTests(_Fixture):
    def _scan(self, code):
        return self.client.get("/api/scan/", {"code": code})

    def test_each_kind_of_code(self):
        lot = self._lot(number="LOT-2026-00042")
        self._managed("Rack 3")
        self.assertEqual(self._scan("lot-2026-00042").json()["id"], str(lot.id))
        self.assertEqual(self._scan("INJ-9001").json()["work_order_id"], str(self.wo.id))
        self.assertEqual(self._scan("WO-LOC-77").json()["kind"], "WORK_ORDER")
        self.assertEqual(self._scan("LOC:Rack 3").json()["label"], "Rack 3")
        self.assertEqual(self._scan("rack 3").json()["kind"], "LOCATION")
        qr = self._scan(f"https://uqmes.example/production/material-lots/{lot.id}").json()
        self.assertEqual((qr["kind"], qr["id"]), ("LOT", str(lot.id)))
        self.assertEqual(self._scan("LOC-77").json()["label"], "WO-LOC-77")  # one partial match
        self.assertEqual(self._scan("nothing-like-it").status_code, 404)
