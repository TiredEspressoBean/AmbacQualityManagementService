"""
Security-audit regression for the AI read-only query endpoint
(`QueryViewSet.execute_read_only`).

Previously it ran `model_class.objects.all()` with user filtering explicitly
disabled, so `User` (Django's UserManager, not SecureManager) returned every
tenant's users, and the endpoint dropped both tenant backstops. The fix scopes
SecureModels via `for_user`, scopes `User` to the current tenant's members, and
restores the tenant membership backstop.
"""

from Tracker.tests.base import TenantTestCase


class AIQueryTenantScopingTests(TenantTestCase):
    URL = "/api/ai/query/execute_read_only/"

    def test_user_query_scoped_to_current_tenant(self):
        """Querying the User model returns only the current tenant's members,
        never another tenant's users."""
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post(self.URL, {"model": "User"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        emails = {row.get("email") for row in resp.json()["results"]}
        self.assertIn(self.user_a.email, emails)
        self.assertNotIn(
            self.user_b.email, emails,
            "CROSS-TENANT LEAK: AI query returned another tenant's user.",
        )

    def test_secure_model_query_scoped_to_current_tenant(self):
        """Querying a SecureModel goes through for_user → only own-tenant rows."""
        from Tracker.models import Orders

        self.create_for_tenant(Orders, self.tenant_a, name="A-ORDER")
        self.create_for_tenant(Orders, self.tenant_b, name="B-ORDER")
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_orders", "full_tenant_access"]
        )
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post(self.URL, {"model": "Orders"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        names = {row.get("name") for row in resp.json()["results"]}
        self.assertIn("A-ORDER", names)
        self.assertNotIn("B-ORDER", names)

    def test_header_spoof_blocked(self):
        """The endpoint no longer drops the tenant backstop: a user spoofing
        X-Tenant-ID to a tenant they don't belong to is denied."""
        self.authenticate_as(self.user_a, self.tenant_b)
        resp = self.client.post(self.URL, {"model": "Orders"}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
