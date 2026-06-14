"""
Security-audit regression tests for the /media/ file-serving endpoint.

`serve_media_iframe_safe` previously served any file under MEDIA_ROOT with no
auth / tenant / classification check (an unauthenticated cross-tenant file
read). `_authorize_media_path` now gates every request by resolving the file to
its owning record and checking the requester against it.
"""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from Tracker.tests.base import TenantTestCase
from Tracker.viewsets.core import _authorize_media_path


class MediaPathAuthorizationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Documents

        self.rf = RequestFactory()

        # A document in the VICTIM tenant (B). user_a is not a member of B.
        self.victim_doc = self.create_for_tenant(
            Documents, self.tenant_b,
            file_name="secret.pdf",
            file="parts_docs/tenant-b/2026-06-10/uuidB/secret.pdf",
            classification="PUBLIC",
        )
        # A document in the attacker's OWN tenant (A).
        self.own_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="own.pdf",
            file="parts_docs/tenant-a/2026-06-10/uuidA/own.pdf",
            classification="PUBLIC",
        )
        # user_a can view documents in their own tenant.
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_documents", "full_tenant_access"]
        )

    def _req(self, user):
        req = self.rf.get("/media/x")
        req.user = user
        return req

    def test_cross_tenant_document_denied(self):
        self.assertFalse(
            _authorize_media_path(self._req(self.user_a), self.victim_doc.file.name),
            "tenant-A user must not read tenant-B's document file",
        )

    def test_own_tenant_document_allowed(self):
        self.assertTrue(
            _authorize_media_path(self._req(self.user_a), self.own_doc.file.name),
            "user must be able to read a document in their own tenant they can view",
        )

    def test_unauthenticated_denied(self):
        self.assertFalse(
            _authorize_media_path(self._req(AnonymousUser()), self.own_doc.file.name)
        )

    def test_public_logo_allowed_even_anonymous(self):
        self.assertTrue(
            _authorize_media_path(self._req(AnonymousUser()), "tenant_logos/acme.png")
        )

    def test_unknown_path_denied(self):
        self.assertFalse(
            _authorize_media_path(self._req(self.user_a), "random/not-a-record.pdf")
        )

    def test_superuser_cross_tenant_allowed(self):
        self.assertTrue(
            _authorize_media_path(self._req(self.superuser), self.victim_doc.file.name),
            "superuser/staff retain cross-tenant access (support)",
        )

    def test_view_returns_404_for_cross_tenant(self):
        """End-to-end: a logged-in tenant-A user hitting tenant-B's media path
        gets 404 (authorization denies before existence is disclosed)."""
        self.client.force_login(self.user_a)
        resp = self.client.get("/media/" + self.victim_doc.file.name)
        self.assertEqual(resp.status_code, 404, resp.status_code)
