"""Receiving either kind of stock (2026-09-30).

A lot is stock of a raw material (`material`) or a bought part (`material_type`, a
PartType). Expected receipts took only materials, so a bought part on order never
reached planning as incoming supply; batch receiving now sends whichever was picked.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class ReceivingItemsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, PartTypes, Tenant
        cls.tenant = Tenant.objects.create(name="Receiving", slug="receiving-items-0930")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="rcv", email="rcv@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", unit_of_measure="EA")
            cls.nozzle = PartTypes.objects.create(tenant=cls.tenant, name="Nozzle", preferred_supplier=cls.acme)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _expect(self, **item):
        return self.client.post("/api/MaterialLots/expected-receipt/", {
            **item, "quantity": "20", "promised_date": str(date.today() + timedelta(days=5)),
        }, format="json")

    def test_a_bought_part_can_be_expected(self):
        from Tracker.models import MaterialLot
        resp = self._expect(material_type=str(self.nozzle.id))
        self.assertEqual(resp.status_code, 201, resp.content)
        lot = MaterialLot.objects.get(pk=resp.json()["id"])
        self.assertEqual((lot.material_type_id, lot.material_id, lot.status), (self.nozzle.id, None, "ON_ORDER"))
        self.assertEqual(lot.supplier_id, self.acme.id)  # the part's preferred supplier

    def test_an_expected_receipt_is_of_one_thing(self):
        self.assertEqual(self._expect().status_code, 400)
        both = self._expect(material=str(self.seal.id), material_type=str(self.nozzle.id))
        self.assertEqual(both.status_code, 400)
        self.assertEqual(self._expect(material=str(self.seal.id)).status_code, 201)

    def test_batch_receiving_takes_a_material_or_a_part(self):
        from Tracker.models import MaterialLot
        resp = self.client.post("/api/MaterialLots/bulk_create/", {"lots": [
            {"lot_number": "B-1", "received_date": str(date.today()), "quantity": "5", "unit_of_measure": "EA", "material": str(self.seal.id)},
            {"lot_number": "B-2", "received_date": str(date.today()), "quantity": "3", "unit_of_measure": "EA", "material_type": str(self.nozzle.id)},
        ]}, format="json")
        self.assertIn(resp.status_code, (200, 201), resp.content)
        self.assertEqual(MaterialLot.objects.get(lot_number="B-1").material_id, self.seal.id)
        self.assertEqual(MaterialLot.objects.get(lot_number="B-2").material_type_id, self.nozzle.id)
