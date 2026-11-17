"""Doc audit 2026-11-17: an approval template auto-assigns a group by name, so renaming
the group left the template assigning nobody. The rename now carries the template."""
from Tracker.models import ApprovalTemplate, Approval_Type, TenantGroup
from Tracker.tests.base import TenantTestCase


class GroupRenameTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.group = TenantGroup.objects.create(tenant=self.tenant_a, name="Quality Leads",
                                                is_custom=True)
        self.template, _ = ApprovalTemplate.objects.get_or_create(
            tenant=self.tenant_a, approval_type=Approval_Type.PCR_APPROVAL,
            defaults={'template_name': 'PCR Approval'})
        ApprovalTemplate.objects.filter(pk=self.template.pk).update(
            auto_assign_by_role="Quality Leads")
        self.authenticate_superuser(self.tenant_a)

    def test_renaming_a_group_carries_its_templates(self):
        r = self.client.patch(f"/api/TenantGroups/{self.group.id}/",
                              {"name": "Quality Supervisors"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["name"], "Quality Supervisors")
        self.template.refresh_from_db()
        self.assertEqual(self.template.auto_assign_by_role, "Quality Supervisors")

    def test_another_tenants_template_with_the_same_name_is_left_alone(self):
        other, _ = ApprovalTemplate.unscoped.get_or_create(  # tenant-safe: test fixture
            tenant=self.tenant_b, approval_type=Approval_Type.PCR_APPROVAL, is_current_version=True,
            defaults={'template_name': 'PCR Approval'})
        ApprovalTemplate.unscoped.filter(pk=other.pk).update(  # tenant-safe: test fixture
            auto_assign_by_role="Quality Leads")
        self.client.patch(f"/api/TenantGroups/{self.group.id}/",
                          {"name": "Quality Supervisors"}, format="json")
        self.assertEqual(ApprovalTemplate.unscoped.get(pk=other.pk)  # tenant-safe: test read
                         .auto_assign_by_role, "Quality Leads")

    def test_a_description_edit_changes_no_template(self):
        r = self.client.patch(f"/api/TenantGroups/{self.group.id}/",
                              {"description": "Leads who sign off quality"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.template.refresh_from_db()
        self.assertEqual(self.template.auto_assign_by_role, "Quality Leads")
