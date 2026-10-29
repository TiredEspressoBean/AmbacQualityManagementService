"""Several approval templates per type, one the default (user decision 2026-10-29)."""
from django.db import IntegrityError, transaction

from Tracker.models import ApprovalTemplate, TenantGroup
from Tracker.services.core.approval_template import make_default
from Tracker.tests.base import TenantTestCase


class DefaultTemplateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        ApprovalTemplate.objects.filter(tenant=self.tenant_a, approval_type="DOCUMENT_RELEASE").delete()
        self.a = ApprovalTemplate.objects.create(tenant=self.tenant_a, template_name="Docs A",
                                                 approval_type="DOCUMENT_RELEASE", is_default=True)
        self.b = ApprovalTemplate.objects.create(tenant=self.tenant_a, template_name="Drawings",
                                                 approval_type="DOCUMENT_RELEASE")

    def test_several_per_type_and_lookups_pick_the_default(self):
        self.assertEqual(ApprovalTemplate.default_for("DOCUMENT_RELEASE"), self.a)

    def test_only_one_current_default_per_type(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ApprovalTemplate.objects.filter(pk=self.b.pk).update(is_default=True)

    def test_making_another_default_moves_it(self):
        make_default(self.b)
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_default)
        self.assertEqual(ApprovalTemplate.default_for("DOCUMENT_RELEASE"), self.b)

    def test_the_api_moves_the_default_and_refuses_switching_it_off(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_approvaltemplate', 'change_approvaltemplate', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.patch(f"/api/ApprovalTemplates/{self.a.id}/", {"is_default": False}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.patch(f"/api/ApprovalTemplates/{self.b.id}/", {"is_default": True}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(ApprovalTemplate.default_for("DOCUMENT_RELEASE").template_name, "Drawings")

    def test_a_request_keeps_the_template_it_was_made_from(self):
        from Tracker.services.core.approval import create_approval_from_template
        group = TenantGroup.objects.create(tenant=self.tenant_a, name="Doc obj", is_custom=True)
        req = create_approval_from_template(group, self.b, self.user_a)
        self.assertEqual(req.get_template(), self.b)
