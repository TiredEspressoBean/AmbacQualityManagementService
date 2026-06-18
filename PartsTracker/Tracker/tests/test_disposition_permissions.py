"""API-level permission tests for the disposition close action (Phase 0b).

Closing a disposition is gated by the `close_disposition` permission via
`action_permissions` (and CRUD-exempt, so `add_quarantinedisposition` is NOT
also required). A user without the perm is rejected; one with it can close.
"""
from django.urls import reverse

from Tracker.models import QuarantineDisposition
from Tracker.tests.base import TenantTestCase


class DispositionClosePermissionTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        # IN_PROGRESS, completable (no part, no linked quality reports -> no
        # pending annotations) disposition owned by tenant_a.
        # MINOR severity → no containment requirement, keeping this test focused
        # on the close *permission* (containment gating is covered in 2f tests).
        self.disp = QuarantineDisposition.unscoped.create(
            tenant=self.tenant_a,
            disposition_type="USE_AS_IS",
            severity="MINOR",
            description="permission test",
        )
        self.assertEqual(self.disp.current_state, "IN_PROGRESS")

    def _close_url(self):
        return reverse("QuarantineDispositions-close", kwargs={"pk": str(self.disp.id)})

    def test_close_denied_without_close_permission(self):
        # User can SEE dispositions (view + full_tenant_access) but lacks the
        # close_disposition perm — the close action must be rejected. This
        # isolates close_disposition as the gate (not a visibility 404).
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ["view_quarantinedisposition", "full_tenant_access"],
        )
        self.authenticate_as(self.user_a, self.tenant_a)
        resp = self.client.post(self._close_url())
        self.assertEqual(resp.status_code, 403)

        self.disp.refresh_from_db()
        self.assertEqual(self.disp.current_state, "IN_PROGRESS")  # unchanged
        self.assertFalse(self.disp.resolution_completed)

    def test_close_allowed_with_close_permission(self):
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a,
            ["view_quarantinedisposition", "full_tenant_access", "close_disposition"],
        )
        self.authenticate_as(self.user_a, self.tenant_a)

        resp = self.client.post(self._close_url())
        self.assertEqual(resp.status_code, 200)

        self.disp.refresh_from_db()
        self.assertEqual(self.disp.current_state, "CLOSED")
        self.assertTrue(self.disp.resolution_completed)
        self.assertEqual(self.disp.resolution_completed_by, self.user_a)
