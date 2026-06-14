"""
Security-audit regression for cross-tenant GenericForeignKey references.

Writable GFK serializers (Documents, ApprovalRequest, LifeTracking, …) let a
request set `content_type`/`object_id`. Without validation, a tenant-A user
could point a Document at a tenant-B object (a dangling cross-tenant reference
/ soft IDOR). SecureModelMixin.validate() now rejects a GFK target that isn't
in the current tenant.
"""

from django.contrib.contenttypes.models import ContentType

from Tracker.tests.base import TenantTestCase


class GenericFKTenantValidationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import Orders, Documents

        # ContextVar is tenant_a (TenantTestCase.setUp).
        self.order_a = self.create_for_tenant(Orders, self.tenant_a, name="A-ORDER")
        self.order_b = self.create_for_tenant(Orders, self.tenant_b, name="B-ORDER")
        self.doc = self.create_for_tenant(
            Documents, self.tenant_a,
            file_name="d.pdf", file="parts_docs/a/d.pdf", classification="PUBLIC",
        )
        self.order_ct = ContentType.objects.get_for_model(Orders)

    def _serializer(self, object_id):
        from Tracker.serializers.dms import DocumentsSerializer
        return DocumentsSerializer(
            instance=self.doc,
            data={"content_type": self.order_ct.pk, "object_id": str(object_id)},
            partial=True,
        )

    def test_cross_tenant_gfk_rejected(self):
        ser = self._serializer(self.order_b.id)  # tenant B's order
        self.assertFalse(ser.is_valid())
        self.assertIn(
            "object_id", ser.errors,
            "GFK pointing at another tenant's object must be rejected.",
        )

    def test_same_tenant_gfk_accepted(self):
        ser = self._serializer(self.order_a.id)  # own tenant's order
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_nonexistent_object_rejected(self):
        import uuid
        ser = self._serializer(uuid.uuid4())
        self.assertFalse(ser.is_valid())
        self.assertIn("object_id", ser.errors)
