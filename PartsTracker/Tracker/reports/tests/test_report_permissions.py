"""Report endpoint permission gate.

Reports are internal work-product (BOMs, travelers, labor hours, buy lists).
The endpoints previously required only tenant *membership* — which customer
portal accounts have — and the adapters scope by tenant, not by the
requesting user's row visibility. `CanExportReports` closes that: report
generation/download requires the staff `export_data` perm (granted via
STAFF_VIEW_PERMISSIONS; absent from the Customer preset).
"""
from Tracker.tests.base import TenantTestCase


class ReportPermissionGateTests(TenantTestCase):
    def _download(self):
        # hello_world takes no params — exercises the gate without fixtures.
        return self.client.get(
            "/api/reports/download/",
            {"report_type": "hello_world"},
        )

    def test_member_without_export_perm_is_403(self):
        """A tenant member with customer-shaped perms (view_workorder etc. but
        no export_data) must NOT be able to pull internal report PDFs."""
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_orders", "view_workorder", "view_parts"])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self._download()
        self.assertEqual(resp.status_code, 403)

    def test_staff_with_export_data_can_download(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ["export_data"])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self._download()
        # Past the gate: anything but 401/403 (200 PDF, or 500 if the Typst
        # binary is unavailable in this environment — still not a perm denial).
        self.assertNotIn(resp.status_code, (401, 403))

    def test_generate_is_gated_too(self):
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_orders", "view_workorder"])
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post(
            "/api/reports/generate/",
            {"report_type": "hello_world", "params": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
