"""A draft whose document type needs no approval is released directly (user decision
2026-10-28, B17). Submit refused such a draft and release refused anything not
APPROVED, so 19 starter types (CoC, test reports, calibration certificates…) were
stuck in Draft."""
from django.core.files.uploadedfile import SimpleUploadedFile

from Tracker.models import Documents, DocumentType
from Tracker.tests.base import TenantTestCase


class ReleaseDraftTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.free = DocumentType.objects.create(tenant=self.tenant_a, name="Certificate of Conformance",
                                                code="COC", requires_approval=False,
                                                default_review_period_days=365, default_retention_days=3650)
        self.controlled = DocumentType.objects.create(tenant=self.tenant_a, name="Work Instruction",
                                                      code="WI", requires_approval=True)
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_documents', 'release_documents', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _doc(self, doc_type, status="DRAFT"):
        return Documents.objects.create(
            tenant=self.tenant_a, file_name="doc.pdf", classification="INTERNAL", status=status,
            document_type=doc_type, file=SimpleUploadedFile("doc.pdf", b"%PDF-1.4"), uploaded_by=self.user_a)

    def _release(self, doc):
        return self.client.post(f"/api/Documents/{doc.id}/release/", {}, format="json")

    def test_a_no_approval_draft_releases_with_its_dates(self):
        doc = self._doc(self.free)
        r = self._release(doc)
        self.assertEqual(r.status_code, 200, r.content)
        doc.refresh_from_db()
        self.assertEqual(doc.status, "RELEASED")
        self.assertIsNotNone(doc.effective_date)
        self.assertIsNotNone(doc.review_date)
        self.assertIsNotNone(doc.retention_until)

    def test_an_approval_required_draft_is_still_refused(self):
        doc = self._doc(self.controlled)
        r = self._release(doc)
        self.assertEqual(r.status_code, 400, r.content)
        doc.refresh_from_db()
        self.assertEqual(doc.status, "DRAFT")

    def test_releasing_a_new_draft_obsoletes_the_prior_release(self):
        v1 = self._doc(self.free)
        self.assertEqual(self._release(v1).status_code, 200)
        v1.refresh_from_db()
        v2 = v1.create_new_version(user=self.user_a, change_description="rev B")
        Documents.objects.filter(pk=v2.pk).update(status="DRAFT")
        r = self._release(v2)
        self.assertEqual(r.status_code, 200, r.content)
        v1.refresh_from_db()
        self.assertEqual(v1.status, "OBSOLETE")
