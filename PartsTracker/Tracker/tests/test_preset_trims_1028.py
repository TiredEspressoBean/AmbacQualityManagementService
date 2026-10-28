"""Preset trims, user decisions 2026-10-28.

B9: removing a sampling rule follows authoring, QA-led — Tenant Admin and QA Manager
only. It came with the manager-tier deletes, so Production Manager and Document
Controller could delete a rule they can't write.
B10: delete_measurementresult was a dead grant (no endpoint deletes a result).
"""
import uuid

from Tracker.presets import GROUP_PRESETS
from Tracker.tests.base import TenantTestCase


def _perms(name):
    return next(p['permissions'] for p in GROUP_PRESETS.values() if p['name'] == name)


class SamplingRuleDeleteTests(TenantTestCase):

    def test_only_tenant_admin_and_qa_manager_delete_sampling_rules(self):
        holders = sorted(p['name'] for p in GROUP_PRESETS.values()
                         if 'delete_samplingrule' in p['permissions'])
        self.assertEqual(holders, ['QA Manager', 'Tenant Admin'])
        for name in ('QA Manager', 'Tenant Admin'):
            self.assertIn('delete_samplingruleset', _perms(name))

    def test_no_preset_grants_delete_measurementresult(self):
        self.assertFalse([p['name'] for p in GROUP_PRESETS.values()
                          if 'delete_measurementresult' in p['permissions']])

    def _delete(self, group, route):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, list(_perms(group)))
        self.authenticate_as(self.user_a, self.tenant_a)
        # The permission is checked before the row is looked up: 403 when refused,
        # 404 for an unknown id once allowed.
        return self.client.delete(f"/api/{route}/{uuid.uuid4()}/").status_code

    def test_a_production_manager_is_refused(self):
        self.assertEqual(self._delete('Production Manager', 'Sampling-rules'), 403)

    def test_a_production_manager_is_refused_a_rule_set(self):
        self.assertEqual(self._delete('Production Manager', 'Sampling-rule-sets'), 403)

    def test_a_qa_manager_passes_the_gate(self):
        self.assertEqual(self._delete('QA Manager', 'Sampling-rules'), 404)
