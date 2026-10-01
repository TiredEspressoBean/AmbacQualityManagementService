"""Suppliers and ownership (2026-09-30, receiving plan Phase 5).

- Companies say what they are to us (customer / supplier) and have an address; pickers
  filter on it.
- Outside contacts carry a role: SCARs go to quality, late deliveries are chased with
  expediting.
- Customer property (ISO 9001 §8.5.3): a lot a customer sent in for their own job skips
  the supplier gates and scorecard, is drawn only into that customer's work, and covers
  only that customer's demand in planning.
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
        from Tracker.models import (
            BOM, BOMLine, Companies, Material, Orders, PartTypes, Processes, Tenant, WorkOrder,
            WorkOrderStatus,
        )
        cls.tenant = Tenant.objects.create(name="Owners", slug="receiving-phase5")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="p5", email="p5@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.vendor = Companies.objects.create(tenant=cls.tenant, name="Acme Seals", is_customer=False,
                                                  address="1 Mill Rd, Erie PA")
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet Co", is_supplier=False)
            cls.other = Companies.objects.create(tenant=cls.tenant, name="Other Co", is_supplier=False)
            cls.seal = Material.objects.create(tenant=cls.tenant, name="Seal", unit_of_measure="EA",
                                               requires_supplier_qualification=True)
            asm = PartTypes.objects.create(tenant=cls.tenant, name="Injector")
            proc = Processes.objects.create(tenant=cls.tenant, name="P", part_type=asm,
                                            status="APPROVED", is_current_version=True)
            bom = BOM.objects.create(tenant=cls.tenant, part_type=asm, revision="A", bom_type="ASSEMBLY",
                                     status="RELEASED", is_current_version=True)
            BOMLine.objects.create(tenant=cls.tenant, bom=bom, material=cls.seal, quantity=Decimal(10),
                                   source="BUY", line_number=1)
            order = Orders.objects.create(tenant=cls.tenant, name="Fleet job", company=cls.fleet)
            cls.fleet_wo = WorkOrder.objects.create(
                tenant=cls.tenant, ERP_id="WO-F", quantity=1, workorder_status=WorkOrderStatus.PENDING,
                process=proc, related_order=order, expected_start=date.today() + timedelta(days=20))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def _receive(self, **fields):
        body = {"lot_number": fields.pop("lot_number", "L-1"), "material": str(self.seal.id),
                "quantity": fields.pop("quantity", "10"), "received_date": str(date.today()),
                "unit_of_measure": "EA", **fields}
        resp = self.client.post("/api/MaterialLots/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()


class CompanyTests(_Fixture):
    def test_pickers_can_ask_for_suppliers_or_customers(self):
        sup = {c["name"] for c in self.client.get("/api/Companies/?is_supplier=true").json()["results"]}
        cus = {c["name"] for c in self.client.get("/api/Companies/?is_customer=true").json()["results"]}
        self.assertIn("Acme Seals", sup)
        self.assertNotIn("Fleet Co", sup)
        self.assertEqual(cus & {"Acme Seals", "Fleet Co"}, {"Fleet Co"})


class ContactTests(_Fixture):
    def _contact(self, company, role, email):
        return User.objects.create_user(username=email, email=email, password="x", tenant=self.tenant,
                                        parent_company=company, contact_role=role,
                                        user_type=User.UserType.PORTAL, first_name=email.split("@")[0])

    def test_late_deliveries_name_who_to_chase(self):
        from Tracker.services.mes.material_lot import record_expected_receipt
        self._contact(self.vendor, "QUALITY", "qual@acme.test")
        self._contact(self.vendor, "EXPEDITING", "ship@acme.test")
        record_expected_receipt(tenant=self.tenant, quantity=Decimal(5), material=self.seal,
                                supplier=self.vendor, promised_date=date.today() - timedelta(days=2))
        row = self.client.get("/api/MaterialLots/late-deliveries/").json()[0]
        self.assertEqual((row["supplier_contact"], row["supplier_contact_email"]), ("ship", "ship@acme.test"))

    def test_scar_goes_to_the_quality_contact_at_the_address(self):
        from Tracker.models import CAPA
        from Tracker.reports.adapters.scar import ScarReportAdapter
        self._contact(self.vendor, "QUALITY", "qual@acme.test")
        capa = CAPA.objects.create(tenant=self.tenant, capa_type="SUPPLIER", supplier=self.vendor,
                                   problem_statement="x", initiated_by=self.user, severity="MAJOR")
        ctx = ScarReportAdapter().build_context({"id": capa.id}, self.user, self.tenant)
        self.assertEqual((ctx.supplier_contact, ctx.supplier_contact_email, ctx.supplier_address),
                         ("qual", "qual@acme.test", "1 Mill Rd, Erie PA"))


class CustomerPropertyTests(_Fixture):
    def test_skips_the_supplier_gate_and_the_scorecard(self):
        from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
        bought = self._receive(supplier=str(self.vendor.id), lot_number="BOUGHT")
        self.assertEqual(bought["hold_reason"], "SUPPLIER_UNQUALIFIED")  # ours: gated
        theirs = self._receive(supplier=str(self.fleet.id), owner=str(self.fleet.id), lot_number="FREE")
        self.assertEqual((theirs["status"], theirs["owner_name"]), ("ACCEPTED", "Fleet Co"))
        self.assertEqual(compute_supplier_scorecard(self.fleet).lots_received, 0)

    def test_drawn_only_into_the_owners_work(self):
        from Tracker.services.mes.bom import buy_line_item
        from Tracker.models import BOMLine
        from Tracker.services.mes.consumption import _usable_lots
        self._receive(owner=str(self.fleet.id), lot_number="FREE", supplier=str(self.fleet.id))
        key = buy_line_item(BOMLine.objects.get(material=self.seal)).key
        self.assertEqual([l.lot_number for l in _usable_lots(key, self.tenant, self.fleet.id)], ["FREE"])
        self.assertEqual(_usable_lots(key, self.tenant, self.other.id), [])
        self.assertEqual(_usable_lots(key, self.tenant), [])

    def test_covers_only_the_owners_demand_in_planning(self):
        from Tracker.services.mes.requirements import sourcing_requirements
        short = lambda: next((r["qty_short"] for r in sourcing_requirements(self.tenant)["source"]
                              if r["material"] == "Seal"), 0)
        self.assertEqual(short(), 10)
        self._receive(owner=str(self.other.id), lot_number="NOT-YOURS", supplier=str(self.other.id))
        self.assertEqual(short(), 10)  # another customer's stock covers nothing here
        self._receive(owner=str(self.fleet.id), lot_number="FREE", supplier=str(self.fleet.id), quantity="6")
        self.assertEqual(short(), 4)   # the owner's own stock covers the owner's job

    def test_label_says_whose_it_is(self):
        from Tracker.models import MaterialLot
        from Tracker.reports.adapters.material_lot_label import build_material_lot_label_context
        lot = self._receive(owner=str(self.fleet.id), lot_number="FREE", supplier=str(self.fleet.id))
        ctx = build_material_lot_label_context(MaterialLot.objects.get(pk=lot["id"]), self.tenant)
        self.assertEqual(ctx.owner_name, "Fleet Co")
