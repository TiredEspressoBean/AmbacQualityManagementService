"""
Security-audit regression for cross-tenant DocChunk (RAG) leakage.

DocChunk is not a SecureModel and has no tenant field, so `DocChunk.objects`
spans all tenants. Previously, `for_user`'s full_tenant_access / staff /
superuser branches applied no tenant filter to chunks, so AI semantic search
returned other tenants' document text. The fix delegates DocChunk visibility to
the parent Document's `for_user` (tenant + classification + export-control).
"""

from django.conf import settings

from Tracker.tests.base import TenantTestCase


class DocChunkTenantIsolationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Documents, DocChunk

        dim = settings.AI_EMBED_DIM
        zero = [0.0] * dim

        # A document + chunk in the attacker's own tenant (A) and in the
        # victim tenant (B).
        own_doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="own.pdf",
            file="parts_docs/tenant-a/own.pdf",
            classification="PUBLIC",
        )
        victim_doc = self.create_for_tenant(
            Documents, self.tenant_b,
            file_name="secret.pdf",
            file="parts_docs/tenant-b/secret.pdf",
            classification="PUBLIC",
        )
        self.own_chunk = DocChunk.objects.create(
            doc=own_doc, embedding=zero,
            full_text="OWN-TENANT-CHUNK", preview_text="own",
        )
        self.victim_chunk = DocChunk.objects.create(
            doc=victim_doc, embedding=zero,
            full_text="VICTIM-TENANT-CHUNK", preview_text="victim",
        )

        # Attacker is a full-access staff user in their OWN tenant only.
        self.grant_tenant_permissions(
            self.user_a, self.tenant_a, ["view_documents", "view_docchunk", "full_tenant_access"]
        )

    def test_for_user_excludes_other_tenants_chunks(self):
        from Tracker.models import DocChunk

        # ContextVar is tenant_a (set in TenantTestCase.setUp); user_a is a
        # full_tenant_access member of tenant_a and nothing in tenant_b.
        texts = set(
            DocChunk.objects.for_user(self.user_a).values_list("full_text", flat=True)
        )
        self.assertIn("OWN-TENANT-CHUNK", texts)
        self.assertNotIn(
            "VICTIM-TENANT-CHUNK", texts,
            "CROSS-TENANT RAG LEAK: full_tenant_access user retrieved another "
            "tenant's document chunk text via DocChunk.for_user.",
        )
