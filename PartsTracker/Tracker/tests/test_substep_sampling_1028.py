"""A substep's own sampling rule, authored in the substep editor (user decision
2026-10-28, B7). A SamplingRule needs a rule set, and a substep's rule is no part of its
step's plan, so it lives in an inactive set of its own the step engine never applies."""
from Tracker.models import PartTypes, SamplingRuleSet, Steps, Substep
from Tracker.services.dwi.substep_sampling import SUBSTEP_ORIGIN, create_substep_rule
from Tracker.tests.base import TenantTestCase


class SubstepSamplingRuleTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.pt = PartTypes.objects.create(tenant=self.tenant_a, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=self.tenant_a, part_type=self.pt, name="Inspect")

    def test_the_rule_lives_in_an_inactive_set_of_the_steps_own(self):
        rule = create_substep_rule(self.step, "PERCENTAGE", 20, user=self.user_a)
        self.assertEqual((rule.rule_type, rule.value), ("PERCENTAGE", 20))
        self.assertEqual(rule.ruleset.origin, SUBSTEP_ORIGIN)
        self.assertFalse(rule.ruleset.active)
        again = create_substep_rule(self.step, "EVERY_NTH_PART", 5)
        self.assertEqual(again.ruleset_id, rule.ruleset_id)  # one set per step
        # The step's own plan never resolves to it.
        self.assertIsNone(self.step.get_active_sampling_ruleset(self.pt))
        self.assertFalse(SamplingRuleSet.objects.filter(step=self.step, active=True).exists())

    def test_bad_types_and_values_are_refused(self):
        for rule_type, value in (("AQL", 1), ("PERCENTAGE", 0), ("PERCENTAGE", 101), ("FIRST_N_PARTS", 0)):
            with self.assertRaises(ValueError, msg=(rule_type, value)):
                create_substep_rule(self.step, rule_type, value)

    def test_the_editor_creates_one_and_sets_it_on_the_substep(self):
        substep = Substep.objects.create(tenant=self.tenant_a, step=self.step, order=1, title="Gauge bore")
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['view_substep', 'change_substep', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/Substeps/sampling-rule/",
                             {"step": str(self.step.id), "rule_type": "PERCENTAGE", "value": 20}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        r = self.client.patch(f"/api/Substeps/{substep.id}/", {"sampling_rule": r.json()["id"]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["sampling_rule_info"], {"rule_type": "PERCENTAGE", "value": 20})
