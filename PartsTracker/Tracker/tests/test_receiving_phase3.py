"""Inspection (2026-09-30, receiving plan Phase 3).

- Receiving Inspection Plans for raw materials (bulk stock), not only part types: a
  RIP step carries `material` instead of `part_type`; a CheckConstraint keeps every
  other step on a part type.
- Supplier qualification for raw materials, by commodity.
- A Certification basis on supplier qualifications, naming the certificate.
- `once_per_lot` on a substep (asked on the first sampled unit only), carried across
  step versions.
- The receiving inspection record: the evidence of release, built from live records.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, Material, PartTypes, Tenant
        cls.tenant = Tenant.objects.create(name="Inspect", slug="receiving-phase3")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="qa3", email="qa3@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.bar = Material.objects.create(tenant=cls.tenant, name="Bar 4140", unit_of_measure="FT")
            cls.seal = Material.objects.create(
                tenant=cls.tenant, name="Seal", unit_of_measure="EA",
                requires_supplier_qualification=True, commodity="Elastomer seals")
            cls.housing = PartTypes.objects.create(tenant=cls.tenant, name="Housing", can_buy=True)
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
                "unit_of_measure": "FT", "supplier": str(self.acme.id), **fields}
        return self.client.post("/api/MaterialLots/", body, format="json")

    def _material_rip(self, material):
        resp = self.client.post("/api/Steps/create_receiving_plan/", {"material": str(material.id)},
                                format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.json()


class MaterialReceivingPlanTests(_Fixture):
    def test_a_material_plan_is_keyed_to_the_material(self):
        from Tracker.models import Steps
        body = self._material_rip(self.bar)
        self.assertEqual((body["material"], body["part_type"], body["material_name"]),
                         (str(self.bar.id), None, "Bar 4140"))
        step = Steps.objects.get(pk=body["id"])
        self.assertEqual((step.step_type, str(step)), ("RECEIVING", "Receiving - Bar 4140 (Bar 4140)"))

    def test_create_needs_exactly_one_item(self):
        self.assertEqual(self.client.post("/api/Steps/create_receiving_plan/", {}, format="json").status_code, 400)
        both = self.client.post("/api/Steps/create_receiving_plan/", {
            "material": str(self.bar.id), "part_type": str(self.housing.id)}, format="json")
        self.assertEqual(both.status_code, 400)

    def test_a_material_lot_with_a_plan_waits_for_inspection(self):
        self._material_rip(self.bar)
        lot = self._receive(material=str(self.bar.id), quantity="120").json()
        self.assertEqual(lot["status"], "AWAITING_INSPECTION")
        plan = self.client.get(f"/api/MaterialLots/{lot['id']}/sample_plan/")
        self.assertEqual(plan.status_code, 200, plan.content)

    def test_a_material_lot_without_a_plan_still_docks_to_stock(self):
        lot = self._receive(material=str(self.bar.id), quantity="120").json()
        self.assertEqual(lot["status"], "ACCEPTED")

    def test_plans_list_shows_material_plans(self):
        self._material_rip(self.bar)
        rows = self.client.get("/api/Steps/?step_type=RECEIVING&standalone=true").json()["results"]
        self.assertEqual([(r["material_name"], r["part_type_name"]) for r in rows], [("Bar 4140", None)])

    def test_only_a_receiving_step_may_belong_to_a_material(self):
        from Tracker.models import Steps
        with self.assertRaises(IntegrityError), transaction.atomic():
            Steps.objects.create(tenant=self.tenant, name="Cut", step_type="TASK", material=self.bar)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Steps.objects.create(tenant=self.tenant, name="Orphan", step_type="TASK")

    def test_clearing_a_normal_steps_part_type_is_a_400_not_a_500(self):
        from Tracker.models import Steps
        step = Steps.objects.create(tenant=self.tenant, name="Grind", part_type=self.housing)
        resp = self.client.patch(f"/api/Steps/{step.id}/", {"part_type": None}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_a_new_version_of_a_material_plan_keeps_its_material(self):
        from Tracker.models import Steps
        from Tracker.services.mes.steps import create_new_step_version
        step = Steps.objects.get(pk=self._material_rip(self.bar)["id"])
        new = create_new_step_version(step, user=self.user, change_description="Tighten the plan")
        self.assertEqual((new.material_id, new.part_type_id), (self.bar.id, None))


class MaterialSupplierQualificationTests(_Fixture):
    def _qualify(self, label):
        from Tracker.models import SupplierQualification
        return SupplierQualification.objects.create(
            tenant=self.tenant, supplier=self.acme, scope_type="COMMODITY", scope_label=label,
            status="APPROVED")

    def test_unqualified_for_the_commodity_holds(self):
        lot = self._receive(material=str(self.seal.id), quantity="50", unit_of_measure="EA").json()
        self.assertEqual((lot["status"], lot["hold_reason"]), ("QUARANTINE", "SUPPLIER_UNQUALIFIED"))

    def test_qualified_for_the_commodity_passes(self):
        self._qualify("elastomer SEALS")  # matched ignoring case
        lot = self._receive(material=str(self.seal.id), quantity="50", unit_of_measure="EA").json()
        self.assertEqual(lot["status"], "ACCEPTED")

    def test_another_commoditys_qualification_does_not_count(self):
        self._qualify("Fasteners")
        lot = self._receive(material=str(self.seal.id), quantity="50", unit_of_measure="EA").json()
        self.assertEqual(lot["hold_reason"], "SUPPLIER_UNQUALIFIED")

    def test_without_the_flag_nothing_is_checked(self):
        lot = self._receive(material=str(self.bar.id), quantity="5").json()
        self.assertEqual(lot["status"], "ACCEPTED")


class CertificationBasisTests(_Fixture):
    def _create(self, **extra):
        return self.client.post("/api/SupplierQualifications/", {
            "supplier": str(self.acme.id), "scope_type": "COMMODITY", "scope_label": "All",
            "basis": "CERTIFICATION", **extra}, format="json")

    def test_a_certification_says_which(self):
        self.assertEqual(self._create().status_code, 400)
        ok = self._create(certification_type="AS9100", expiry_date="2027-06-30")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()["certification_type"], "AS9100")

    def test_certificate_type_is_dropped_for_other_bases(self):
        ok = self.client.post("/api/SupplierQualifications/", {
            "supplier": str(self.acme.id), "scope_type": "COMMODITY", "scope_label": "All",
            "basis": "AUDIT", "certification_type": "ISO9001"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(ok.json()["certification_type"], "")


class OncePerLotTests(_Fixture):
    def test_serialized_and_carried_across_step_versions(self):
        from Tracker.models import Steps
        from Tracker.models.dwi import Substep
        from Tracker.services.mes.steps import create_new_step_version
        step = Steps.objects.get(pk=self._material_rip(self.bar)["id"])
        sub = Substep.objects.create(tenant=self.tenant, step=step, order=1,
                                     title="Is the CoC present and correct?", once_per_lot=True)
        body = self.client.get(f"/api/Substeps/{sub.id}/").json()
        self.assertTrue(body["once_per_lot"])
        new = create_new_step_version(step, user=self.user, change_description="v2")
        self.assertTrue(Substep.objects.get(step=new, order=1).once_per_lot)


class InspectionRecordTests(_Fixture):
    def test_record_carries_the_inspection_and_its_release(self):
        from Tracker.models import MaterialLot
        from Tracker.reports.adapters.receiving_inspection_record import (
            build_receiving_inspection_record_context,
        )
        self._material_rip(self.bar)
        lot = self._receive(material=str(self.bar.id), quantity="120", heat_number="H9",
                            lot_number="REC-1").json()
        self.assertEqual(self.client.post(f"/api/MaterialLots/{lot['id']}/record_bulk/",
                                          {"defectives_found": 0}, format="json").status_code, 200)
        self.assertEqual(self.client.post(f"/api/MaterialLots/{lot['id']}/accept/").status_code, 200)
        ctx = build_receiving_inspection_record_context(MaterialLot.objects.get(pk=lot["id"]), self.tenant)
        self.assertEqual((ctx.lot_number, ctx.heat_number, ctx.verdict), ("REC-1", "H9", "PASS"))
        self.assertEqual(ctx.plan_name, "Receiving - Bar 4140")
        self.assertIsNotNone(ctx.sample_size)
        self.assertIn("Accepted", [e.what for e in ctx.events])

    def test_a_dock_to_stock_lot_has_a_record_saying_so(self):
        from Tracker.models import MaterialLot
        from Tracker.reports.adapters.receiving_inspection_record import (
            build_receiving_inspection_record_context,
        )
        lot = self._receive(material=str(self.bar.id), quantity="5", lot_number="D2S-1").json()
        ctx = build_receiving_inspection_record_context(MaterialLot.objects.get(pk=lot["id"]), self.tenant)
        self.assertEqual((ctx.report_number, ctx.verdict), (None, None))

    def test_another_tenants_lot_is_refused(self):
        from Tracker.models import MaterialLot, Tenant
        from Tracker.reports.adapters.receiving_inspection_record import (
            ReceivingInspectionRecordParamsSerializer,
        )
        other = Tenant.objects.create(name="Other", slug="receiving-phase3-other")
        theirs = MaterialLot.all_tenants.create(
            tenant=other, lot_number="X-1", material_description="x", quantity=Decimal(1),
            quantity_remaining=Decimal(1), unit_of_measure="EA", status="ACCEPTED")
        ser = ReceivingInspectionRecordParamsSerializer(data={"lot_id": str(theirs.id)},
                                                        context={"user": self.user})
        self.assertFalse(ser.is_valid())
