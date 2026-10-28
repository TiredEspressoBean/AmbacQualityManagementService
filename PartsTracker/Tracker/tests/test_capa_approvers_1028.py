"""Only a QA Manager approves a Major or Critical CAPA's plan (user decision
2026-10-28, B3). The starter templates also listed Production Manager under an ANY
flow, so a Production Manager could approve alone."""
import importlib

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from Tracker.models import CAPA, ApprovalRequest, ApprovalTemplate, TenantGroup, UserRole
from Tracker.services.defaults_service import seed_approval_templates
from Tracker.tests.base import TenantTestCase

User = get_user_model()


class CapaPlanApproverTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.qa_group, _ = TenantGroup.objects.get_or_create(tenant=t, name="QA Manager")
        self.pm_group, _ = TenantGroup.objects.get_or_create(tenant=t, name="Production Manager")
        self.qa = User.objects.create_user(username="qa-b3", email="qa-b3@x.test", password="x", tenant=t)
        self.pm = User.objects.create_user(username="pm-b3", email="pm-b3@x.test", password="x", tenant=t)
        UserRole.objects.create(user=self.qa, group=self.qa_group)
        UserRole.objects.create(user=self.pm, group=self.pm_group)

    def _groups(self, approval_type):
        template = ApprovalTemplate.objects.get(approval_type=approval_type, is_current_version=True)
        return sorted(template.default_groups.values_list('name', flat=True))

    def test_starter_templates_name_only_the_qa_manager(self):
        seed_approval_templates(tenant=self.tenant_a, update_existing=True)
        self.assertEqual(self._groups('CAPA_MAJOR'), ["QA Manager"])
        self.assertEqual(self._groups('CAPA_CRITICAL'), ["QA Manager"])

    def test_a_production_manager_cannot_approve_a_major_capa_plan(self):
        seed_approval_templates(tenant=self.tenant_a, update_existing=True)
        capa = CAPA.objects.create(capa_type='CORRECTIVE', severity='MAJOR', problem_statement="Burrs",
                                   initiated_by=self.user_a, assigned_to=self.user_a)
        request = ApprovalRequest.objects.get(content_type=ContentType.objects.get_for_model(CAPA),
                                              object_id=str(capa.pk))
        self.assertEqual(request.approval_type, 'CAPA_MAJOR')
        self.assertFalse(request.can_approve(self.pm))
        self.assertTrue(request.can_approve(self.qa))

    def test_existing_templates_get_a_new_version_without_production_manager(self):
        seed_approval_templates(tenant=self.tenant_a, update_existing=True)
        old = ApprovalTemplate.objects.get(approval_type='CAPA_MAJOR', is_current_version=True)
        old.default_groups.add(self.pm_group)  # as the old starter set it
        mig = importlib.import_module('Tracker.migrations.0269_capa_plan_approvers_qa_manager_only')
        from django.apps import apps
        mig.drop_production_manager(apps, None)
        self.assertEqual(self._groups('CAPA_MAJOR'), ["QA Manager"])
        old.refresh_from_db()
        self.assertFalse(old.is_current_version)
        self.assertIn("Production Manager", old.default_groups.values_list('name', flat=True))
