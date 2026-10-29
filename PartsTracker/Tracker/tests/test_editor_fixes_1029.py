"""Editor review fixes (2026-10-29).

- Step sampling is authored with the sampling permissions (QA), not add_steps.
- Editor list pages that had no metadata endpoint now have one, so the page can tell
  who may add or import.
"""
from Tracker.models import PartTypes, Steps
from Tracker.tests.base import TenantTestCase


class StepSamplingGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=self.tenant_a, part_type=self.pt, name="Turn",
                                         step_type="TASK")
        self.url = f"/api/Steps/{self.step.id}/update_sampling_rules/"
        self.body = {"rules": [{"rule_type": "EVERY_NTH_PART", "value": 2, "order": 1}]}

    def test_add_steps_alone_no_longer_authors_sampling(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_steps', 'add_steps', 'change_steps', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_sampling_permissions_author_it_without_add_steps(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_steps', 'add_samplingruleset', 'change_samplingruleset',
            'add_samplingrule', 'change_samplingrule', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post(self.url, self.body, format="json")
        self.assertEqual(r.status_code, 200, r.content)


class EditorMetadataTests(TenantTestCase):

    def test_former_metadata_less_lists_now_report_their_add_permission(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_repaircode', 'view_materiallot', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        for endpoint, perm in (("RepairCodes", "add_repaircode"), ("MaterialLots", "add_materiallot")):
            r = self.client.get(f"/api/{endpoint}/metadata/")
            self.assertEqual(r.status_code, 200, (endpoint, r.content))
            self.assertEqual(r.json()["permissions"]["add"], perm, endpoint)
