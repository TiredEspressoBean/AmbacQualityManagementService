"""The dock (2026-09-30, receiving plan Phase 2).

- Buying units: a clerk counts "3 boxes" and the lot is booked as 6,000; both kept.
- Paperwork holds, opt-in per item: a lot waits for its CoC / heat number and clears
  itself when it's supplied.
- Releasing a hold: until now a held lot could only be rejected. QA releases a
  decision hold with a reason on record, and the lot routes on with that gate waived.
- Quantity adjustments with a reason, recorded as a RecordEdit.
- A managed list of storage locations replaces free-text suggestions once it exists.
- Lot labels are refused for another tenant's lots.
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
        from Tracker.models import Companies, Material, PartTypes, Tenant
        cls.tenant = Tenant.objects.create(name="Dock", slug="receiving-phase2")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="clerk", email="clerk@x.test",
                                                password="x", tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.shim = Material.objects.create(
                tenant=cls.tenant, name="Shim", part_number="SHIM", unit_of_measure="EA",
                purchase_unit="BOX", units_per_purchase_unit=Decimal(2000))
            cls.bar = Material.objects.create(tenant=cls.tenant, name="Bar 4140",
                                              unit_of_measure="FT", requires_heat_number=True)
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal",
                                               unit_of_measure="EA", requires_coc=True)
            cls.housing = PartTypes.objects.create(
                tenant=cls.tenant, name="Housing", can_buy=True,
                requires_supplier_qualification=True)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _receive(self, **fields):
        body = {"lot_number": fields.pop("lot_number", "L-1"), "received_date": str(date.today()),
                "unit_of_measure": "EA", "supplier": str(self.acme.id), **fields}
        return self.client.post("/api/MaterialLots/", body, format="json")


class BuyingUnitTests(_Fixture):
    def test_boxes_convert_to_the_stock_count_and_both_are_kept(self):
        resp = self._receive(material=str(self.shim.id), quantity="3",
                             received_as_quantity="3", received_as_unit="BOX")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(Decimal(body["quantity"]), Decimal(6000))
        self.assertEqual((Decimal(body["received_as_quantity"]), body["received_as_unit"]), (Decimal(3), "BOX"))
        self.assertEqual(Decimal(body["quantity_remaining"]), Decimal(6000))

    def test_a_unit_the_item_isnt_bought_in_is_refused(self):
        resp = self._receive(material=str(self.shim.id), quantity="3",
                             received_as_quantity="3", received_as_unit="LB")
        self.assertEqual(resp.status_code, 400)

    def test_no_conversion_on_file_is_refused(self):
        resp = self._receive(material=str(self.seal.id), quantity="3",
                             received_as_quantity="3", received_as_unit="BOX")
        self.assertEqual(resp.status_code, 400)

    def test_receiving_an_expected_lot_in_boxes(self):
        from Tracker.models import MaterialLot
        from Tracker.services.mes.material_lot import record_expected_receipt
        lot = record_expected_receipt(tenant=self.tenant, quantity=Decimal(6000), material=self.shim,
                                      promised_date=date.today() + timedelta(days=3))
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/receive/", {
            "lot_number": "SUP-9", "received_as_quantity": "3", "received_as_unit": "BOX",
            "heat_number": "H1", "source_type": "MANUFACTURER"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot = MaterialLot.objects.get(pk=lot.pk)
        self.assertEqual((lot.quantity, lot.received_as_quantity, lot.heat_number, lot.source_type),
                         (Decimal(6000), Decimal(3), "H1", "MANUFACTURER"))
        self.assertEqual(lot.short_receipt, "")  # 3 boxes is the 6,000 ordered — not short


class PaperworkHoldTests(_Fixture):
    def test_missing_heat_number_holds_then_entering_it_clears(self):
        resp = self._receive(material=str(self.bar.id), quantity="20", lot_number="BAR-1")
        lot = resp.json()
        self.assertEqual((lot["status"], lot["hold_reason"]), ("QUARANTINE", "AWAITING_HEAT_NUMBER"))
        patched = self.client.patch(f"/api/MaterialLots/{lot['id']}/", {"heat_number": "M88231"}, format="json")
        self.assertEqual(patched.status_code, 200, patched.content)
        after = self.client.get(f"/api/MaterialLots/{lot['id']}/").json()
        # No receiving plan for the bar, so once released it docks to stock.
        self.assertEqual((after["status"], after["hold_reason"]), ("ACCEPTED", ""))

    def test_heat_number_given_at_receipt_never_holds(self):
        lot = self._receive(material=str(self.bar.id), quantity="20", heat_number="M1").json()
        self.assertEqual(lot["status"], "ACCEPTED")

    def test_missing_coc_holds_then_uploading_it_clears(self):
        lot = self._receive(material=str(self.seal.id), quantity="50", lot_number="SEAL-1").json()
        self.assertEqual(lot["hold_reason"], "AWAITING_COC")
        coc = SimpleUploadedFile("coc.pdf", b"%PDF-1.4 coc", content_type="application/pdf")
        patched = self.client.patch(f"/api/MaterialLots/{lot['id']}/",
                                    {"certificate_of_conformance": coc}, format="multipart")
        self.assertEqual(patched.status_code, 200, patched.content)
        after = self.client.get(f"/api/MaterialLots/{lot['id']}/").json()
        self.assertEqual((after["status"], after["hold_reason"]), ("ACCEPTED", ""))

    def test_an_item_that_asks_for_nothing_just_books_in(self):
        lot = self._receive(material=str(self.shim.id), quantity="10").json()
        self.assertEqual((lot["status"], lot["hold_reason"]), ("ACCEPTED", ""))


class ReleaseHoldTests(_Fixture):
    def _held_housing(self):
        lot = self._receive(material_type=str(self.housing.id), quantity="4", lot_number="HSG-1").json()
        self.assertEqual(lot["hold_reason"], "SUPPLIER_UNQUALIFIED")
        return lot

    def test_release_records_the_reason_and_does_not_re_hold(self):
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import MaterialLot, RecordEdit
        lot = self._held_housing()
        resp = self.client.post(f"/api/MaterialLots/{lot['id']}/release-hold/",
                                {"reason": "Requalification in progress; QA accepts on CoC"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["hold_reason"], "")
        self.assertNotEqual(body["status"], "QUARANTINE")
        edit = RecordEdit.objects.get(content_type=ContentType.objects.get_for_model(MaterialLot),
                                      object_id=lot["id"], field_name="hold_reason")
        self.assertEqual((edit.old_value, edit.new_value, edit.edited_by_id),
                         ("SUPPLIER_UNQUALIFIED", "", self.user.id))

    def test_a_reason_is_required(self):
        lot = self._held_housing()
        resp = self.client.post(f"/api/MaterialLots/{lot['id']}/release-hold/", {"reason": "  "}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_a_lot_not_on_hold_cannot_be_released(self):
        lot = self._receive(material=str(self.shim.id), quantity="10").json()
        resp = self.client.post(f"/api/MaterialLots/{lot['id']}/release-hold/", {"reason": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_releasing_one_hold_still_applies_the_others(self):
        """A seal that also needs a CoC: waiving nothing but the CoC hold is not possible
        here, so release a CoC hold and check the lot moves on (no other gate applies)."""
        lot = self._receive(material=str(self.seal.id), quantity="5", lot_number="SEAL-9").json()
        resp = self.client.post(f"/api/MaterialLots/{lot['id']}/release-hold/",
                                {"reason": "Supplier emailed the cert; filed in the ERP"}, format="json")
        self.assertEqual(resp.json()["status"], "ACCEPTED")


class AdjustQuantityTests(_Fixture):
    def test_adjust_sets_remaining_and_records_why(self):
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import MaterialLot, RecordEdit
        lot = self._receive(material=str(self.shim.id), quantity="2000").json()
        resp = self.client.post(f"/api/MaterialLots/{lot['id']}/adjust-quantity/",
                                {"quantity": "1940", "reason": "Recount"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(Decimal(resp.json()["quantity_remaining"]), Decimal(1940))
        edit = RecordEdit.objects.get(content_type=ContentType.objects.get_for_model(MaterialLot),
                                      object_id=lot["id"], field_name="quantity_remaining")
        self.assertEqual((Decimal(edit.old_value), Decimal(edit.new_value), edit.reason),
                         (Decimal(2000), Decimal(1940), "Recount"))

    def test_needs_a_reason_and_stock_on_hand(self):
        from Tracker.services.mes.material_lot import record_expected_receipt
        lot = self._receive(material=str(self.shim.id), quantity="10").json()
        self.assertEqual(self.client.post(f"/api/MaterialLots/{lot['id']}/adjust-quantity/",
                                          {"quantity": "9", "reason": ""}, format="json").status_code, 400)
        on_order = record_expected_receipt(tenant=self.tenant, quantity=Decimal(5), material=self.shim,
                                           promised_date=date.today())
        self.assertEqual(self.client.post(f"/api/MaterialLots/{on_order.id}/adjust-quantity/",
                                          {"quantity": "4", "reason": "x"}, format="json").status_code, 400)


class StorageLocationTests(_Fixture):
    def test_a_receipt_points_at_a_location_and_another_tenants_is_refused(self):
        from Tracker.models import StorageLocation, Tenant
        rack = StorageLocation.objects.create(tenant=self.tenant, name="Rack 3")
        resp = self._receive(material=str(self.shim.id), quantity="1", location=str(rack.id))
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual((resp.json()["location"], resp.json()["storage_location"]), (str(rack.id), "Rack 3"))
        other = Tenant.objects.create(name="Other plant", slug="receiving-phase2-locs-fk")
        theirs = StorageLocation.all_tenants.create(tenant=other, name="Their rack")
        resp = self._receive(lot_number="L-2", material=str(self.shim.id), quantity="1", location=str(theirs.id))
        self.assertEqual(resp.status_code, 400)

    def test_crud_and_one_name_per_tenant(self):
        ok = self.client.post("/api/StorageLocations/", {"name": "Cage A"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        dup = self.client.post("/api/StorageLocations/", {"name": "cage a"}, format="json")
        self.assertEqual(dup.status_code, 400)  # a 400, not the database's 500; case ignored
        rename = self.client.patch(f"/api/StorageLocations/{ok.json()['id']}/", {"name": "Cage A"}, format="json")
        self.assertEqual(rename.status_code, 200)  # saving itself unchanged is not a clash

    def test_names_are_unique_per_tenant_not_across_tenants(self):
        from Tracker.models import StorageLocation, Tenant
        other = Tenant.objects.create(name="Other plant", slug="receiving-phase2-locs")
        StorageLocation.all_tenants.create(tenant=other, name="Rack 3")
        # Another tenant's "Rack 3" neither blocks this tenant's nor shows up in its list.
        ok = self.client.post("/api/StorageLocations/", {"name": "Rack 3"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual([r["name"] for r in self.client.get("/api/StorageLocations/").json()["results"]],
                         ["Rack 3"])
        self.assertEqual(StorageLocation.all_tenants.filter(name="Rack 3").count(), 2)


class LotLabelTests(_Fixture):
    def test_labels_for_another_tenants_lot_are_refused(self):
        from Tracker.models import MaterialLot, Tenant
        from Tracker.reports.adapters.material_lot_label import MaterialLotLabelParamsSerializer
        other = Tenant.objects.create(name="Other", slug="receiving-phase2-other")
        theirs = MaterialLot.all_tenants.create(
            tenant=other, lot_number="X-1", material_description="x", quantity=Decimal(1),
            quantity_remaining=Decimal(1), unit_of_measure="EA", status="ACCEPTED")
        mine = self._receive(material=str(self.shim.id), quantity="1").json()
        ser = MaterialLotLabelParamsSerializer(data={"lot_ids": [mine["id"], str(theirs.id)]},
                                               context={"user": self.user})
        self.assertFalse(ser.is_valid())
        self.assertTrue(MaterialLotLabelParamsSerializer(
            data={"lot_ids": [mine["id"]], "copies": 3}, context={"user": self.user}).is_valid())

    def test_label_context_carries_the_receipt(self):
        from Tracker.models import MaterialLot
        from Tracker.reports.adapters.material_lot_label import build_material_lot_label_context
        body = self._receive(material=str(self.shim.id), quantity="3", received_as_quantity="3",
                             received_as_unit="BOX", heat_number="H7", lot_number="LBL-1").json()
        ctx = build_material_lot_label_context(MaterialLot.objects.get(pk=body["id"]), self.tenant)
        self.assertEqual((ctx.lot_number, ctx.quantity, ctx.received_as, ctx.heat_number, ctx.part_number),
                         ("LBL-1", "6000 EA", "3 boxes", "H7", "SHIM"))
