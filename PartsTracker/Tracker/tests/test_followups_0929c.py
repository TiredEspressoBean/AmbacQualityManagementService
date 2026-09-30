"""Fixes found alongside the composite imports and the new UI pages (2026-09-29)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from Tracker.tests.base import TenantContextMixin
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class SupersedeLeavesOneActiveRulesetTests(TenantContextMixin, TestCase):
    """Superseding a ruleset created the successor ACTIVE beside a predecessor that
    stayed active — two rulesets sampling one step — and dropped its settings."""

    def setUp(self):
        super().setUp()
        from Tracker.models import Companies, PartTypes, Processes, ProcessStep, Steps, Tenant
        self.tenant = Tenant.objects.create(name="Sampling", slug="supersede-one-active")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, name="Inspect", part_type=self.pt)
        ProcessStep.objects.create(process=self.proc, step=self.step, order=1)
        self.supplier = Companies.objects.create(tenant=self.tenant, name="Acme")

    def _active(self):
        from Tracker.models import SamplingRuleSet
        return list(SamplingRuleSet.objects.filter(step=self.step, part_type=self.pt,
                                                   active=True, archived=False))

    def test_editing_a_steps_rules_leaves_exactly_one_active_ruleset(self):
        from Tracker.services.mes.steps import update_step_sampling_rules
        update_step_sampling_rules(self.step, [{'rule_type': 'EVERY_NTH_PART', 'value': 5,
                                                'order': 1}], user=None, process=self.proc)
        update_step_sampling_rules(self.step, [{'rule_type': 'EVERY_NTH_PART', 'value': 2,
                                                'order': 1}], user=None, process=self.proc)
        active = self._active()
        self.assertEqual(len(active), 1, active)
        self.assertEqual(active[0].rules.filter(archived=False).first().value, 2)

    def test_a_successor_is_inactive_and_keeps_its_settings(self):
        from Tracker.models import SamplingRuleSet
        from Tracker.services.mes.sampling_ruleset import supersede_sampling_ruleset
        old = SamplingRuleSet.create_with_rules(
            part_type=self.pt, process=self.proc, step=self.step, name="R",
            rules=[{'rule_type': 'EVERY_NTH_PART', 'value': 5, 'order': 1}],
            supplier=self.supplier)
        new = supersede_sampling_ruleset(old, name="R v2", rules=[], user=None)
        self.assertFalse(new.active)
        self.assertEqual(new.supplier_id, self.supplier.id)
        old.refresh_from_db()
        self.assertTrue(old.active)  # still in force until the successor is activated


class MilestoneRevisionSkipsDeletedTests(TenantContextMixin, TestCase):
    def test_a_deleted_milestone_does_not_come_back_on_revision(self):
        from Tracker.models import Milestone, MilestoneTemplate, Tenant
        from Tracker.services.mes.milestone_template import create_new_milestone_template_version
        tenant = Tenant.objects.create(name="Milestones", slug="milestone-revision")
        self.set_tenant_context(tenant)
        tpl = MilestoneTemplate.objects.create(tenant=tenant, name="Standard")
        Milestone.objects.create(tenant=tenant, template=tpl, name="Received", display_order=1)
        gone = Milestone.objects.create(tenant=tenant, template=tpl, name="Old", display_order=2)
        gone.delete()
        new = create_new_milestone_template_version(tpl, user=None,
                                                    change_description="Rename")
        self.assertEqual(list(new.milestones.filter(archived=False)
                              .values_list('name', flat=True)), ["Received"])


class ReAddingDeletedRowsTests(APITestCase):
    """A deleted contact or life-limit link still held its unique key, so it could
    never be added again. Adding it again now revives the same row."""

    @classmethod
    def setUpTestData(cls):
        from Tracker.models import Companies, LifeLimitDefinition, PartTypes, Tenant
        cls.tenant = Tenant.objects.create(name="Re-add", slug="re-add-deleted")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.user = User.objects.create_user(username="readd", email="readd@x.test",
                                                password="x", tenant=cls.tenant, is_staff=True)
            cls.user.is_superuser = True
            cls.user.save(update_fields=["is_superuser"])
            cls.acme = Companies.objects.create(tenant=cls.tenant, name="Acme")
            cls.pt = PartTypes.objects.create(tenant=cls.tenant, name="Seal kit")
            cls.shelf = LifeLimitDefinition.objects.create(
                tenant=cls.tenant, name="Shelf", unit="days", unit_label="Days",
                is_calendar_based=True, hard_limit=Decimal(365))
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self.client.force_authenticate(user=self.user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        self._token = set_current_tenant_id(self.tenant.id)

    def tearDown(self):
        reset_current_tenant(self._token)

    def test_a_deleted_contact_can_be_added_again(self):
        from Tracker.models import ExternalContact
        url = "/api/notifications/external-contacts/"
        body = {"customer": str(self.acme.id), "name": "Buyer", "email": "buyer@acme.test",
                "role": "procurement", "enabled": True}
        first = self.client.post(url, body, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        cid = first.json()["id"]
        self.assertEqual(self.client.delete(f"{url}{cid}/").status_code, 204)
        again = self.client.post(url, {**body, "name": "Buyer (back)"}, format="json")
        self.assertEqual(again.status_code, 201, again.content)
        row = ExternalContact.unscoped.get(pk=cid)  # tenant-safe: one known pk
        self.assertFalse(row.archived)
        self.assertEqual(row.name, "Buyer (back)")

    def test_a_removed_life_limit_link_can_be_linked_again(self):
        from Tracker.models import PartTypeLifeLimit
        url = "/api/PartTypeLifeLimits/"
        body = {"part_type": str(self.pt.id), "definition": str(self.shelf.id),
                "is_required": True}
        first = self.client.post(url, body, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        lid = first.json()["id"]
        self.assertEqual(self.client.delete(f"{url}{lid}/").status_code, 204)
        again = self.client.post(url, body, format="json")
        self.assertEqual(again.status_code, 201, again.content)
        self.assertFalse(PartTypeLifeLimit.unscoped.get(pk=lid).archived)  # tenant-safe: one known pk
