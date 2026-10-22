"""Releasing and obsoleting a controlled document (Document Controller walk, 2026-10-21).

Approval stopped at APPROVED with no way in the product to put a document in force, so
review dates were never computed and "approved isn't released" couldn't be taught.
Release and obsolete are the document controller's acts, gated on `release_documents`
rather than on the upload permission a POST falls back to.
"""
from django.core.files.uploadedfile import SimpleUploadedFile

from Tracker.models import Documents
from Tracker.tests.base import TenantTestCase


class DocumentReleaseTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.doc = Documents.objects.create(
            tenant=self.tenant_a, file_name="WI-9001 Wash", classification="INTERNAL",
            status="APPROVED", file=SimpleUploadedFile("wi.pdf", b"%PDF-1.4 test"),
            uploaded_by=self.user_a)

    def _as(self, perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, perms)
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_uploading_is_not_enough_to_release(self):
        self._as(['view_documents', 'add_documents', 'change_documents', 'full_tenant_access'])
        r = self.client.post(f"/api/Documents/{self.doc.id}/release/", {}, format="json")
        self.assertEqual(r.status_code, 403, r.content)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "APPROVED")

    def test_the_document_controller_releases_then_obsoletes(self):
        self._as(['view_documents', 'release_documents', 'full_tenant_access'])
        r = self.client.post(f"/api/Documents/{self.doc.id}/release/",
                             {"effective_date": "2026-11-02"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "RELEASED")
        r = self.client.post(f"/api/Documents/{self.doc.id}/mark-obsolete/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.status, "OBSOLETE")
        self.assertIsNotNone(self.doc.obsolete_date)
