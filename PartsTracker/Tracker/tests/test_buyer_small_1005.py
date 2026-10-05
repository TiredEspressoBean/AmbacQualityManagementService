"""Small buyer and dock fixes (2026-10-05).

- A re-promise moves the promised date but keeps the first; on-time delivery is judged
  against the first, so a supplier who slipped twice doesn't score as on time.
- A chase records what the supplier said, and a new promise if they gave one.
- An over-receipt keeps what was ordered, so the overage shows.
- Materials can be found by item, supplier, PO and heat number.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class BuyerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        cls.tenant = Tenant.objects.create(name="Buy", slug="buyer-small-1005")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="by", email="by@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme Seals")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal ring", unit_of_measure="EA")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        from Tracker.services.core.clock import tenant_today
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)
        self.today = tenant_today(self.tenant)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _expect(self, promised, qty="100", po="4500", line="1"):
        from Tracker.services.mes.material_lot import record_expected_receipt
        return record_expected_receipt(tenant=self.tenant, quantity=Decimal(qty), material=self.seal,
                                       supplier=self.acme, promised_date=promised,
                                       erp_po_number=po, erp_po_line=line)

    def test_a_chase_keeps_the_first_promise_and_on_time_is_judged_against_it(self):
        from Tracker.models import RecordEdit
        from Tracker.services.mes.material_lot import receive_expected_lot
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        first = self.today - timedelta(days=5)
        lot = self._expect(first)
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/chase/",
                                {"note": "Ships Thursday", "promised_date": str(self.today)}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual((body["promised_date"], body["original_promised_date"], body["chase_note"]),
                         (str(self.today), str(first), "Ships Thursday"))
        self.assertTrue(RecordEdit.objects.filter(object_id=lot.id, field_name="promised_date").exists())
        late = self.client.get("/api/MaterialLots/late-deliveries/").json()[0]
        self.assertEqual((late["original_promised_date"], late["chase_note"]), (str(first), "Ships Thursday"))
        # Arrives on the new promise: late against the first.
        receive_expected_lot(lot, received_by=self.user, received_date=self.today)
        self.assertEqual(compute_supplier_scorecard(self.acme).on_time_rate, 0.0)

    def test_a_chase_needs_a_note_and_an_open_line(self):
        lot = self._expect(self.today)
        self.assertEqual(self.client.post(f"/api/MaterialLots/{lot.id}/chase/", {"note": " "},
                                          format="json").status_code, 400)

    def test_a_reimported_promise_keeps_the_first_and_the_backorder_inherits_it(self):
        from Tracker.services.mes.material_lot import receive_expected_lot, upsert_expected_receipt
        first = self.today + timedelta(days=2)
        lot = self._expect(first)
        upsert_expected_receipt(tenant=self.tenant, erp_po_number="4500", erp_po_line="1",
                                quantity=Decimal("100"), promised_date=first + timedelta(days=7),
                                material=self.seal, supplier=self.acme)
        lot.refresh_from_db()
        self.assertEqual((lot.original_promised_date, lot.promised_date), (first, first + timedelta(days=7)))
        receive_expected_lot(lot, received_by=self.user, quantity=Decimal("60"), remainder="BACKORDERED")
        from Tracker.models import MaterialLot
        rest = MaterialLot.objects.get(erp_po_number="4500", status="ON_ORDER")
        self.assertEqual(rest.original_promised_date, first)

    def test_an_over_receipt_keeps_what_was_ordered(self):
        from Tracker.services.mes.material_lot import receive_expected_lot
        lot = self._expect(self.today, qty="100")
        receive_expected_lot(lot, received_by=self.user, quantity=Decimal("110"))
        lot.refresh_from_db()
        self.assertEqual((lot.quantity, lot.ordered_quantity, lot.short_receipt), (Decimal("110"), Decimal("100"), ""))

    def test_materials_search_by_supplier_po_item_and_heat(self):
        lot = self._expect(self.today, po="4500777")
        lot.heat_number = "H-31337"
        lot.save(update_fields=["heat_number"])
        for q in ("Acme", "4500777", "Seal ring", "H-31337"):
            ids = [r["id"] for r in self.client.get("/api/MaterialLots/", {"search": q}).json()["results"]]
            self.assertIn(str(lot.id), ids, q)

    def test_a_customers_core_lot_is_not_queued_for_supplier_inspection(self):
        from Tracker.models import MaterialLot, PartTypes
        core_type = PartTypes.objects.create(tenant=self.tenant, name="Injector core")
        cores = MaterialLot.objects.create(
            tenant=self.tenant, lot_number="CORELOT-T-1", material_type=core_type, supplier=self.acme,
            quantity=Decimal(5), quantity_remaining=Decimal(5), unit_of_measure="EA",
            status="RECEIVED", holds_cores=True)
        queued = [r["id"] for r in self.client.get("/api/MaterialLots/", {"inspection_pending": "true"}).json()["results"]]
        self.assertNotIn(str(cores.id), queued)
        from Tracker.services.qms.incoming_inspection import build_incoming_rows
        self.assertNotIn(str(cores.id), [r["id"] for r in build_incoming_rows()])
