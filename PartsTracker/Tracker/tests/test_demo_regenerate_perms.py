"""Regenerating the demo: the demo's Tenant Admin may, platform staff may, nobody else
(bug 2026-11-18: the viewset's staff-only gate refused the demo Tenant Admin before the
action's own check ran)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model

from Tracker.tests.base import TenantTestCase


class DemoRegeneratePermissionTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Tenant
        self.demo = Tenant.objects.create(name="Demo", slug="demo", tier="PRO")
        User = get_user_model()
        self.demo_admin = User.objects.create_user(username="demo_admin", email="a@demo.test",
                                                   password="x", tenant=self.demo)
        self.demo_operator = User.objects.create_user(username="demo_op", email="o@demo.test",
                                                      password="x", tenant=self.demo)
        self._tenant_admin(self.demo_admin, self.demo)
        # A Tenant Admin, but of another tenant.
        self._tenant_admin(self.user_b, self.tenant_b)

    @staticmethod
    def _tenant_admin(user, tenant):
        from Tracker.models import TenantGroup, UserRole
        group, _ = TenantGroup.objects.get_or_create(tenant=tenant, name="Tenant Admin")
        UserRole.objects.get_or_create(user=user, group=group)

    def _regenerate(self, user, tenant, slug="demo"):
        self.authenticate_as(user, tenant)
        with patch("Tracker.tasks.regenerate_demo_data_task.apply_async"):
            return self.client.post(f"/api/Tenants/{slug}/regenerate-demo-data/")

    def test_the_demo_tenant_admin_may_regenerate(self):
        r = self._regenerate(self.demo_admin, self.demo)
        self.assertEqual(r.status_code, 202, r.content)
        poll = self.client.get(f"/api/Tenants/demo/regenerate-demo-status/{r.json()['task_id']}/")
        self.assertEqual(poll.status_code, 200, poll.content)

    def test_another_tenants_admin_and_a_demo_non_admin_may_not(self):
        r = self._regenerate(self.user_b, self.tenant_b)
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(r.json()["detail"], "Tenant Admin role required.")
        r = self._regenerate(self.demo_operator, self.demo)
        self.assertEqual(r.status_code, 403, r.content)
        r = self.client.get("/api/Tenants/demo/regenerate-demo-status/abc/")
        self.assertEqual(r.status_code, 403, r.content)

    def test_only_the_demo_slug_is_regenerated(self):
        # Refused by slug before any lookup: another tenant isn't touched or revealed.
        r = self._regenerate(self.user_b, self.tenant_b, slug="tenant-b")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertIn("only supported on slug='demo'", r.json()["detail"])
        r = self._regenerate(self.user_b, self.tenant_b, slug="no-such-tenant")
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_rest_of_tenants_stays_staff_only(self):
        self.authenticate_as(self.demo_admin, self.demo)
        self.assertEqual(self.client.get("/api/Tenants/").status_code, 403)
