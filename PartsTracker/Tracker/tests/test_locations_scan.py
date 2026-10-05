"""Recorded moves, location views and scan lookup (2026-10-05).

- A location is a record; lots, units and machines point at one (migration 0218).
- A lot or a unit changes location only by a move, and every move is recorded.
- A move must go to one of the tenant's locations; a scanned label (`LOC:<code|name>`)
  names one. Held-only locations take held stock only.
- Locations nest; the summary rolls counts up the tree.
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

    def _loc(self, name, **kw):
        from Tracker.services.mes.locations import seed_location
        return seed_location(self.tenant, name, **kw)

    def _lot(self, number="L-1", qty="100", where="Rack 1", status="ACCEPTED", **kw):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=number, material=self.shim, quantity=Decimal(qty),
            quantity_remaining=Decimal(qty), unit_of_measure="EA", status=status,
            location=self._loc(where) if where else None, **kw)


class MoveTests(_Fixture):
    def test_whole_lot_move_is_recorded(self):
        from Tracker.models import RecordEdit
        lot = self._lot()
        self._loc("Rack 2")
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Rack 2", "reason": "re-slot"},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["storage_location"], "Rack 2")
        edit = RecordEdit.objects.get(object_id=lot.id, field_name="storage_location")
        self.assertEqual((edit.old_value, edit.new_value, edit.reason, edit.edited_by_id),
                         ("Rack 1", "Rack 2", "re-slot", self.user.id))

    def test_partial_move_splits_and_the_rest_stays(self):
        lot = self._lot(qty="100")
        cage = self._loc("Cage B")
        moved = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": str(cage.id), "quantity": "30"},
                                 format="json").json()
        lot.refresh_from_db()
        self.assertNotEqual(moved["id"], str(lot.id))
        self.assertEqual((moved["location"], float(moved["quantity_remaining"])), (str(cage.id), 30.0))
        self.assertEqual((lot.storage_location, lot.quantity_remaining), ("Rack 1", Decimal("70")))

    def test_only_real_locations_and_a_scanned_label_or_code_names_one(self):
        self._loc("Rack 3", code="R3")
        lot = self._lot()
        bad = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Rack 9"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("isn't one of your locations", bad.json()["detail"])
        ok = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "LOC:rack 3"}, format="json")
        self.assertEqual(ok.json()["storage_location"], "Rack 3")  # the tenant's spelling
        back = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Rack 1"}, format="json")
        self.assertEqual(back.status_code, 200)
        by_code = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "LOC:r3"}, format="json")
        self.assertEqual(by_code.json()["storage_location"], "Rack 3")

    def test_inactive_and_held_only_locations_refuse(self):
        lot = self._lot()
        self._loc("Old shelf", is_active=False)
        self._loc("MRB cage", held_only=True)
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Old shelf"}, format="json")
        self.assertIn("no longer in use", resp.json()["detail"])
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "MRB cage"}, format="json")
        self.assertIn("held stock only", resp.json()["detail"])
        held = self._lot(number="L-HELD", status="QUARANTINE")
        resp = self.client.post(f"/api/MaterialLots/{held.id}/move/", {"to": "MRB cage"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_an_edited_location_is_recorded_too_and_gone_lots_dont_move(self):
        from Tracker.models import RecordEdit
        lot = self._lot()
        elsewhere = self._loc("Elsewhere")
        resp = self.client.patch(f"/api/MaterialLots/{lot.id}/", {"location": str(elsewhere.id)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        edit = RecordEdit.objects.get(object_id=lot.id, field_name="storage_location")
        self.assertEqual((edit.old_value, edit.new_value), ("Rack 1", "Elsewhere"))
        used = self._lot(number="L-USED", status="CONSUMED")
        resp = self.client.post(f"/api/MaterialLots/{used.id}/move/", {"to": "Rack 1"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_units_move_and_shipped_ones_dont(self):
        from Tracker.models import Parts
        self._loc("Yard")
        resp = self.client.post("/api/Parts/move/", {"part_ids": [str(self.part.id)], "to": "Yard"}, format="json")
        self.assertEqual((resp.status_code, resp.json()["moved"]), (200, 1))
        self.part.refresh_from_db()
        self.assertEqual(self.part.storage_location, "Yard")
        gone = Parts.objects.create(tenant=self.tenant, ERP_id="INJ-GONE", part_type=self.pt, part_status="SHIPPED")
        resp = self.client.post("/api/Parts/move/", {"part_ids": [str(gone.id)], "to": "Yard"}, format="json")
        self.assertEqual(resp.status_code, 400)


class LocationViewTests(_Fixture):
    def test_tree_summary_contents_and_moves(self):
        from Tracker.models import Equipments
        stores = self._loc("Main Stores")
        rack = self._loc("Rack 1", parent=stores)
        self._loc("Cage B")
        self._loc("Empty Shelf", parent=stores)
        lot = self._lot(where="Rack 1")
        Equipments.objects.create(tenant=self.tenant, name="Press", location=stores)
        self.client.post(f"/api/MaterialLots/{lot.id}/move/", {"to": "Cage B", "quantity": "10"}, format="json")
        self.client.post("/api/Parts/move/", {"part_ids": [str(self.part.id)], "to": "Rack 1"}, format="json")
        rows = self.client.get("/api/StorageLocations/summary/").json()
        self.assertEqual([r["path"] for r in rows],
                         ["Cage B", "Main Stores", "Main Stores / Empty Shelf", "Main Stores / Rack 1"])
        by = {r["name"]: r for r in rows}
        self.assertEqual((by["Rack 1"]["lots"], by["Rack 1"]["parts"]), (1, 1))
        self.assertEqual((by["Main Stores"]["lots"], by["Main Stores"]["total_lots"],
                          by["Main Stores"]["total_parts"], by["Main Stores"]["equipment"]), (0, 1, 1, 1))
        c = self.client.get(f"/api/StorageLocations/{stores.id}/contents/").json()
        self.assertEqual([(l["lot_number"], l["sublocation"]) for l in c["lots"]], [("L-1", "Rack 1")])
        self.assertEqual([m["name"] for m in c["equipment"]], ["Press"])
        self.assertEqual([ch["name"] for ch in c["children"]], ["Empty Shelf", "Rack 1"])
        only = self.client.get(f"/api/StorageLocations/{stores.id}/contents/?include_children=false").json()
        self.assertEqual(only["lots"], [])
        c = self.client.get(f"/api/StorageLocations/{rack.id}/contents/").json()
        self.assertEqual([p["erp_id"] for p in c["parts"]], ["INJ-9001"])
        self.assertEqual({(m["direction"], m["label"]) for m in c["moves"]},
                         {("OUT", "L-1-01"), ("IN", "INJ-9001")})

    def test_renaming_a_location_renames_it_everywhere(self):
        lot = self._lot(where="Rack 1")
        loc = lot.location
        resp = self.client.patch(f"/api/StorageLocations/{loc.id}/", {"name": "Rack 1A"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot.refresh_from_db()
        self.assertEqual(lot.storage_location, "Rack 1A")

    def test_a_location_cant_sit_inside_itself_and_one_in_use_isnt_deleted(self):
        outer = self._loc("Outer")
        inner = self._loc("Inner", parent=outer)
        resp = self.client.patch(f"/api/StorageLocations/{outer.id}/", {"parent": str(inner.id)}, format="json")
        self.assertEqual(resp.status_code, 400)
        self._lot(where="Inner")
        resp = self.client.delete(f"/api/StorageLocations/{inner.id}/")
        self.assertEqual(resp.status_code, 400)

    def test_a_receiving_dock_cant_also_be_held_only(self):
        both = self.client.post("/api/StorageLocations/", {"name": "Dock X", "receiving_dock": True,
                                                           "held_only": True}, format="json")
        self.assertEqual(both.status_code, 400)
        self.assertIn("receiving_dock", both.json())
        cage = self._loc("MRB cage", held_only=True)
        resp = self.client.patch(f"/api/StorageLocations/{cage.id}/", {"receiving_dock": True}, format="json")
        self.assertEqual(resp.status_code, 400)  # the stored half counts too

    def test_receiving_puts_a_delivery_on_the_dock_by_default(self):
        from Tracker.models import MaterialLot
        from Tracker.services.mes.material_lot import receive_expected_lot
        dock = self._loc("Dock 1", receiving_dock=True)
        expected = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="EXP-1", material=self.shim, quantity=Decimal(5),
            quantity_remaining=Decimal(5), unit_of_measure="EA", status="ON_ORDER")
        lot = receive_expected_lot(expected, received_by=self.user)
        self.assertEqual(lot.location_id, dock.id)


class ScanTests(_Fixture):
    def _scan(self, code):
        return self.client.get("/api/scan/resolve/", {"code": code})

    def test_each_kind_of_code(self):
        lot = self._lot(number="LOT-2026-00042")
        rack = self._loc("Rack 3", code="R3")
        self.assertEqual(self._scan("lot-2026-00042").json()["id"], str(lot.id))
        self.assertEqual(self._scan("INJ-9001").json()["work_order_id"], str(self.wo.id))
        self.assertEqual(self._scan("WO-LOC-77").json()["kind"], "WORK_ORDER")
        self.assertEqual(self._scan("LOC:Rack 3").json()["label"], "Rack 3")
        self.assertEqual(self._scan("LOC:R3").json()["id"], str(rack.id))
        self.assertEqual(self._scan("rack 3").json()["path"], f"/production/locations/{rack.id}")
        qr = self._scan(f"https://uqmes.example/production/material-lots/{lot.id}").json()
        self.assertEqual((qr["kind"], qr["id"]), ("LOT", str(lot.id)))
        # A label printed while locations were names still finds the record.
        old = self._scan("https://uqmes.example/production/locations/Rack%203").json()
        self.assertEqual(old["id"], str(rack.id))
        self.assertEqual(self._scan("LOC-77").json()["label"], "WO-LOC-77")  # one partial match
        self.assertEqual(self._scan("nothing-like-it").status_code, 404)
