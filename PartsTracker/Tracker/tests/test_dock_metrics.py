"""Receiving's own numbers (2026-09-30, receiving plan Phase 6): receipts per day,
what is waiting and for how long, time to a decision, holds, and rejects in pieces."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class DockMetricsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, Tenant
        from Tracker.services.qms.receiving_inspection import create_standalone_receiving_plan
        cls.tenant = Tenant.objects.create(name="Dock6", slug="dock-metrics")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="d6", email="d6@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", unit_of_measure="EA")
            cls.bolt = Material.objects.create(tenant=cls.tenant, name="Bolt", unit_of_measure="EA")
            create_standalone_receiving_plan(cls.seal)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _receive(self, material, n, qty="100", received=None):
        return self.client.post("/api/MaterialLots/", {
            "lot_number": f"{material.name}-{n}", "material": str(material.id), "quantity": qty,
            "received_date": str(received or date.today()), "unit_of_measure": "EA",
            "supplier": str(self.acme.id)}, format="json").json()

    def test_counts_receipts_waits_decisions_and_rejects(self):
        from Tracker.services.core.clock import tenant_today
        today = tenant_today(self.tenant)
        self._receive(self.bolt, 1)                                     # dock-to-stock
        waiting = self._receive(self.seal, 2, received=today - timedelta(days=4))
        rejected = self._receive(self.seal, 3, qty="500")
        self.client.post(f"/api/MaterialLots/{rejected['id']}/reject/", {"rejected_quantity": "25"}, format="json")
        m = self.client.get("/api/MaterialLots/dock-metrics/?days=7").json()
        self.assertEqual(len(m["receipts"]), 7)
        self.assertEqual(m["lots_received"], 3)
        self.assertEqual((m["awaiting_decision"], m["oldest_wait_days"]), (1, 4))
        self.assertEqual(m["decided"], 1)                               # the partial reject's accept
        self.assertEqual((m["lots_rejected"], m["pieces_rejected"]), (1, 25.0))
        self.assertEqual(m["ppm_rejected"], round(25 / 700 * 1_000_000))
        self.assertTrue(waiting)

    def test_holds_now_by_reason(self):
        self.seal.requires_coc = True
        self.seal.save(update_fields=["requires_coc"])
        self._receive(self.seal, 9)
        m = self.client.get("/api/MaterialLots/dock-metrics/").json()
        self.assertEqual(m["held_now"], [{"reason": "AWAITING_COC", "lots": 1}])
