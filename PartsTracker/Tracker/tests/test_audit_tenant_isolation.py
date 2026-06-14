"""
Security-audit regression tests for cross-tenant isolation.

Finding A (header-spoof leak) — and its fix — are documented here. The
attack: a token-authenticated user of tenant A spoofs `X-Tenant-ID` to a
victim tenant B. DRF token auth resolves inside the view (after
TenantMiddleware), so `request.user` is anonymous during middleware and the
header is trusted unconditionally; the request tenant + ContextVar + RLS GUC
are all set to B.

The backstop is `TenantAccessPermission` (in the global
DEFAULT_PERMISSION_CLASSES). The bug was that every tenant-scoped viewset
overrode `permission_classes` and dropped it — `TenantScopedMixin` used
`[IsAuthenticated, TenantModelPermissions]`, and several viewsets used
`[IsAuthenticated]`. `TenantModelPermissions` doesn't fill the gap because
`has_tenant_perm` resolves against the user's HOME tenant (where they hold
the perm), while the queryset is filtered to the SPOOFED tenant.

Fix: restore `TenantAccessPermission` to `TenantScopedMixin` and to the
viewsets that override `permission_classes`. It re-checks tenant membership
against the *authenticated* user, so a spoofed tenant the user has no role
in is rejected with 403.

These tests assert the secure (post-fix) behaviour and should stay green.
"""

from Tracker.tests.base import TenantTestCase


class HeaderSpoofTenantIsolationTests(TenantTestCase):
    ORDERS_URL = "/api/Orders/"

    def setUp(self):
        super().setUp()
        from Tracker.models import Orders

        # Attacker is an ordinary staff user in their OWN tenant A.
        self.grant_full_staff_access(self.user_a, self.tenant_a)

        # Victim data lives in tenant B. Attacker has no role in tenant B.
        self.victim_order = self.create_for_tenant(
            Orders, self.tenant_b, name="VICTIM-SECRET-ORDER"
        )
        # A decoy order in the attacker's own tenant.
        self.own_order = self.create_for_tenant(
            Orders, self.tenant_a, name="ATTACKER-OWN-ORDER"
        )

    def _order_names(self, response):
        data = response.json()
        results = data["results"] if isinstance(data, dict) and "results" in data else data
        return {row.get("name") for row in results}

    def _assert_no_leak(self, resp):
        """A spoofed cross-tenant request must be denied (403) or, at worst,
        expose none of the victim tenant's rows."""
        if resp.status_code == 403:
            return
        self.assertEqual(resp.status_code, 200, resp.content)
        names = self._order_names(resp)
        self.assertNotIn(
            "VICTIM-SECRET-ORDER",
            names,
            "CROSS-TENANT LEAK: attacker from tenant A read tenant B's order "
            "by spoofing the X-Tenant-ID header.",
        )

    def test_control_attacker_sees_own_tenant(self):
        """Sanity check: with their real tenant header the attacker sees
        their own order and NOT tenant B's."""
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.get(self.ORDERS_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        names = self._order_names(resp)
        self.assertIn("ATTACKER-OWN-ORDER", names)
        self.assertNotIn("VICTIM-SECRET-ORDER", names)

    def test_header_spoof_blocked_force_auth(self):
        """force_authenticate leaves request.user anonymous during
        middleware (same timing as a token client), so this exercises the
        spoof path. Must be blocked."""
        self.authenticate_as(self.user_a, self.tenant_b)
        resp = self.client.get(self.ORDERS_URL)
        self.assertEqual(
            resp.status_code, 403,
            f"expected TenantAccessPermission to deny the spoof, got "
            f"{resp.status_code}",
        )
        self._assert_no_leak(resp)

    def test_header_spoof_blocked_real_token(self):
        """Same leak path driven by a REAL DRF TokenAuthentication flow
        (no force_authenticate). Must be blocked."""
        from rest_framework.authtoken.models import Token
        from rest_framework.test import APIClient

        token = Token.objects.create(user=self.user_a)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
            HTTP_X_TENANT_ID=str(self.tenant_b.id),
        )
        resp = client.get(self.ORDERS_URL)
        self.assertEqual(
            resp.status_code, 403,
            f"expected TenantAccessPermission to deny the spoof, got "
            f"{resp.status_code}",
        )

    def test_dashboard_header_spoof_blocked(self):
        """DashboardViewSet (TenantAwareMixin + qs_for_user) previously
        leaked aggregated tenant-B quality KPIs under a spoofed header.
        TenantAccessPermission must now deny it before any query runs."""
        self.authenticate_as(self.user_a, self.tenant_b)
        resp = self.client.get("/api/dashboard/kpis/")
        self.assertEqual(
            resp.status_code, 403,
            f"expected dashboard spoof to be denied, got {resp.status_code}",
        )
