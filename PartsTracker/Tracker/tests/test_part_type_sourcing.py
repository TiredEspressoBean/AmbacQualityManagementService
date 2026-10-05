"""A part type's sourcing (2026-10-05): preferred supplier, its lead time and safety stock
— kept current by a buyer without the part-authoring permission, and edited in place
rather than as a new version of the part."""
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class PartTypeSourcingTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Permission
        from Tracker.models import Companies, PartTypes, Tenant, TenantGroup, UserRole
        cls.tenant = Tenant.objects.create(name="Sourcing", slug="part-type-sourcing-1005")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme", is_supplier=True)
            cls.fleet = Companies.objects.create(tenant=cls.tenant, name="Fleet",
                                                 is_supplier=False, is_customer=True)
            cls.nozzle = PartTypes.objects.create(tenant=cls.tenant, name="Nozzle", can_buy=True)
            cls.buyer = User.objects.create_user(username="buyer", email="buyer@x.test",
                                                 password="x", tenant=cls.tenant)
            group = TenantGroup.objects.create(tenant=cls.tenant, name="Buyers", is_custom=True)
            group.permissions.add(*Permission.objects.filter(
                codename__in=["view_parttypes", "change_parttype_sourcing", "full_tenant_access"]))
            UserRole.objects.create(user=cls.buyer, group=group)
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self._token = set_current_tenant_id(self.tenant.id)
        self.buyer.clear_permission_cache(self.tenant)
        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_a_buyer_sets_sourcing_without_editing_the_part(self):
        from Tracker.models import PartTypes
        resp = self.client.patch(f"/api/PartTypes/{self.nozzle.id}/sourcing/", {
            "preferred_supplier": str(self.acme.id), "purchase_lead_time_days": 21,
            "safety_stock": "12"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        pt = PartTypes.objects.get(pk=self.nozzle.id)
        self.assertEqual((pt.preferred_supplier_id, pt.purchase_lead_time_days, pt.safety_stock,
                          pt.version), (self.acme.id, 21, Decimal("12"), 1))  # same version
        # The part itself is still not theirs to edit.
        self.assertEqual(self.client.patch(f"/api/PartTypes/{self.nozzle.id}/",
                                           {"name": "Renamed"}, format="json").status_code, 403)

    def test_only_a_supplier_can_be_preferred(self):
        resp = self.client.patch(f"/api/PartTypes/{self.nozzle.id}/sourcing/",
                                 {"preferred_supplier": str(self.fleet.id)}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_without_the_permission_it_is_refused(self):
        from Tracker.models import UserRole
        UserRole.objects.filter(user=self.buyer).delete()
        self.buyer.clear_permission_cache(self.tenant)
        resp = self.client.patch(f"/api/PartTypes/{self.nozzle.id}/sourcing/",
                                 {"purchase_lead_time_days": 5}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_a_lead_time_edit_on_the_full_form_does_not_version_the_part(self):
        from Tracker.models import PartTypes
        admin = User.objects.create_user(username="pt-admin", email="pt-admin@x.test",
                                         password="x", tenant=self.tenant, is_staff=True)
        admin.is_superuser = True
        admin.save(update_fields=["is_superuser"])
        c = APIClient()
        c.force_authenticate(user=admin)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        resp = c.patch(f"/api/PartTypes/{self.nozzle.id}/", {"purchase_lead_time_days": 9},
                       format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(PartTypes.objects.filter(name="Nozzle").count(), 1)

    def test_planning_holds_the_safety_stock_back(self):
        from Tracker.services.mes.bom import buy_line_item
        self.nozzle.safety_stock = Decimal("7")
        self.nozzle.save(update_fields=["safety_stock"])
        line = SimpleNamespace(material_id=None, material=None, component_type=self.nozzle,
                               component_type_id=self.nozzle.id, source="BUY")
        item = buy_line_item(line)
        self.assertIsNotNone(item)
        self.assertEqual(item.safety_stock, 7.0)
