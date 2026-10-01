"""Rejecting received material, and what the decision does (2026-09-30, Phase 4).

- Partial reject (default): the bad pieces split into their own rejected lot with a
  disposition in pieces; the rest of the lot is accepted.
- Whole-lot reject (VDMR) needs `reject_whole_lot`; without it the lot is held as a
  request, which someone with it confirms — or declines, sending it back to inspection.
- Escalation: reject the rest of an accepted lot.
- The disposition drives the lot: scrap scraps it, use-as-is accepts it on a concession,
  return-to-supplier waits for the dock to ship it back (→ RETURNED, no longer stock).
- Two-way trace, and the RTV sheet.
"""
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
        from Tracker.services.qms.receiving_inspection import create_standalone_receiving_plan
        cls.tenant = Tenant.objects.create(name="Reject", slug="receiving-phase4")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.qa = User.objects.create_user(username="qam", email="qam@x.test", password="x",
                                              tenant=cls.tenant, is_staff=True)
            cls.qa.is_superuser = True
            cls.qa.save(update_fields=["is_superuser"])
            # No groups: holds no tenant permissions, so cannot reject a whole lot.
            cls.inspector = User.objects.create_user(username="insp", email="insp@x.test",
                                                     password="x", tenant=cls.tenant)
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", unit_of_measure="EA")
            create_standalone_receiving_plan(cls.seal)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.qa)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _lot(self, qty="500", lot_number="L-1", **extra):
        resp = self.client.post("/api/MaterialLots/", {
            "lot_number": lot_number, "material": str(self.seal.id), "quantity": qty,
            "received_date": str(date.today()), "unit_of_measure": "EA", "supplier": str(self.acme.id),
            **extra}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["status"], "AWAITING_INSPECTION")
        from Tracker.models import MaterialLot
        return MaterialLot.objects.get(pk=resp.json()["id"])

    def _report(self, lot):
        return lot.quality_reports.order_by("-created_at").first()


class PartialRejectTests(_Fixture):
    def test_bad_pieces_split_off_and_the_rest_is_accepted(self):
        from Tracker.models import MaterialLot
        lot = self._lot(heat_number="H5")
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {
            "rejected_quantity": "20", "disposition_type": "RETURN_TO_SUPPLIER",
            "description": "Flash on the parting line"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(body["outcome"], "PARTIAL")
        child = MaterialLot.objects.get(pk=body["lot"]["id"])
        self.assertEqual((child.status, child.quantity, child.parent_lot_id, child.heat_number),
                         ("REJECTED", Decimal(20), lot.id, "H5"))
        d = child.dispositions.get()
        self.assertEqual((d.quantity, d.disposition_type), (Decimal(20), "RETURN_TO_SUPPLIER"))
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.quantity_remaining), ("ACCEPTED", Decimal(480)))

    def test_rejecting_all_the_pieces_is_a_whole_lot_reject(self):
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"rejected_quantity": "500"}, format="json")
        self.assertEqual(resp.json()["outcome"], "WHOLE_LOT")


class WholeLotTests(_Fixture):
    def test_with_the_permission_the_whole_lot_is_rejected(self):
        lot = self._lot()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"whole_lot": True}, format="json")
        self.assertEqual(resp.json()["outcome"], "WHOLE_LOT", resp.content)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "REJECTED")
        self.assertEqual(lot.dispositions.get().quantity, Decimal(500))

    def test_without_it_the_lot_is_held_as_a_request_then_confirmed(self):
        from Tracker.services.qms.lot_reject import confirm_whole_lot_reject, reject_lot
        lot = self._lot()
        rejected, disposition, outcome = reject_lot(self._report(lot), self.inspector, whole_lot=True)
        self.assertEqual(outcome, "WHOLE_LOT_REQUESTED")
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.hold_reason), ("QUARANTINE", "WHOLE_LOT_REJECT_REQUESTED"))
        with self.assertRaises(ValueError):
            confirm_whole_lot_reject(lot, self.inspector)
        confirm_whole_lot_reject(lot, self.qa)
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.hold_reason), ("REJECTED", ""))

    def test_declining_the_request_sends_the_lot_back_to_inspection(self):
        from Tracker.services.qms.lot_reject import reject_lot
        lot = self._lot()
        _, disposition, _ = reject_lot(self._report(lot), self.inspector, whole_lot=True)
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/release-hold/",
                                {"reason": "Sort it — most are fine"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "AWAITING_INSPECTION")
        disposition.refresh_from_db()
        self.assertEqual(disposition.current_state, "CLOSED")

    def test_rejecting_the_rest_of_an_accepted_lot(self):
        lot = self._lot()
        self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"rejected_quantity": "20"}, format="json")
        lot.refresh_from_db()
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/reject-remainder/", {
            "description": "Field failures traced to this lot"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot.refresh_from_db()
        self.assertEqual(lot.status, "REJECTED")
        self.assertEqual(lot.dispositions.get().quantity, Decimal(480))


class DispositionOutcomeTests(_Fixture):
    def test_scrap_scraps_the_lot(self):
        lot = self._lot()
        self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"whole_lot": True, "disposition_type": "SCRAP"},
                         format="json")
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.quantity_remaining), ("SCRAPPED", Decimal(0)))

    def test_use_as_is_on_a_concession_accepts_it(self):
        from Tracker.services.qms.disposition import decide_disposition
        lot = self._lot()
        self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"whole_lot": True}, format="json")
        d = lot.dispositions.get()
        decide_disposition(d, disposition_type="USE_AS_IS", authorized_by=self.qa,
                           customer_approval={"reference": "DEV-2026-14"})
        lot.refresh_from_db()
        self.assertEqual(lot.status, "ACCEPTED")

    def test_shipping_back_returns_it_and_takes_it_out_of_supply(self):
        from Tracker.services.mes.requirements import _NOT_INCOMING_LOT_STATUSES
        lot = self._lot(erp_po_number="4500123")
        lot.promised_date = date.today() + timedelta(days=1)
        lot.save(update_fields=["promised_date"])
        self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {"whole_lot": True}, format="json")
        row = self.client.get(f"/api/MaterialLots/{lot.id}/").json()
        self.assertTrue(row["awaiting_return"])
        resp = self.client.post(f"/api/MaterialLots/{lot.id}/ship-back/", {"note": "UPS 1Z999"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        lot.refresh_from_db()
        self.assertEqual((lot.status, lot.quantity_remaining), ("RETURNED", Decimal(0)))
        self.assertEqual(lot.dispositions.get().current_state, "CLOSED")
        self.assertIn("RETURNED", _NOT_INCOMING_LOT_STATUSES)
        self.assertFalse(self.client.get(f"/api/MaterialLots/{lot.id}/").json()["awaiting_return"])

    def test_a_lot_not_awaiting_return_cannot_be_shipped_back(self):
        lot = self._lot()
        self.assertEqual(self.client.post(f"/api/MaterialLots/{lot.id}/ship-back/", {}, format="json").status_code, 400)


class TraceAndSheetTests(_Fixture):
    def test_forward_trace_reaches_the_customer_through_assemblies(self):
        from Tracker.models import (
            AssemblyUsage, MaterialUsage, Orders, Parts, PartTypes, WorkOrder, WorkOrderStatus,
        )
        lot = self._lot()
        self.client.post(f"/api/MaterialLots/{lot.id}/accept/")
        customer = self.acme
        pt_sub = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        pt_top = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        order = Orders.objects.create(tenant=self.tenant, name="Fleet 12", company=customer)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-7", quantity=1,
                                      workorder_status=WorkOrderStatus.IN_PROGRESS, related_order=order)
        sub = Parts.objects.create(tenant=self.tenant, ERP_id="N-1", part_type=pt_sub, work_order=wo)
        top = Parts.objects.create(tenant=self.tenant, ERP_id="I-1", part_type=pt_top, work_order=wo)
        MaterialUsage.objects.create(tenant=self.tenant, lot=lot, part=sub, work_order=wo,
                                     qty_consumed=Decimal(2), consumed_by=self.qa)
        AssemblyUsage.objects.create(tenant=self.tenant, assembly=top, component=sub, quantity=1,
                                     installed_by=self.qa)
        trace = self.client.get(f"/api/MaterialLots/{lot.id}/trace/").json()
        use = trace["forward"][0]
        self.assertEqual((use["part"]["erp_id"], [a["erp_id"] for a in use["built_into"]]), ("N-1", ["I-1"]))
        self.assertEqual(trace["customers"], ["Acme"])
        self.assertEqual(trace["backward"]["supplier"], "Acme")

    def test_rtv_sheet_names_the_lot_the_pieces_and_no_price(self):
        from Tracker.models import MaterialLot
        from Tracker.reports.adapters.rtv_sheet import build_rtv_sheet_context
        lot = self._lot(erp_po_number="4500123", erp_po_line="10")
        body = self.client.post(f"/api/MaterialLots/{lot.id}/reject/", {
            "rejected_quantity": "20", "description": "Flash"}, format="json").json()
        ctx = build_rtv_sheet_context(MaterialLot.objects.get(pk=body["lot"]["id"]), self.tenant, self.qa)
        self.assertEqual((ctx.quantity, ctx.erp_po, ctx.reason, ctx.supplier_name),
                         ("20 EA", "4500123 / 10", "Flash", "Acme"))
        self.assertNotIn("price", ctx.model_dump_json().lower())
