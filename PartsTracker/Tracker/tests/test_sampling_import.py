"""Sampling ruleset import: one sheet of rules, the file replaces each ruleset's rules,
and an import only ever makes an INACTIVE draft (Tracker/services/mes/sampling_import.py)."""
from decimal import Decimal

from Tracker.tests.io_base import ImportExportTestCase

HEADER = "part_type,step,ruleset,order,rule_type,value\n"
STEP = "Pump Build > Final Inspection"


class SamplingImportTests(ImportExportTestCase):
    endpoint = "Sampling-rules"
    tenant_slug = "io-sampling"

    @classmethod
    def build_fixtures(cls):
        from Tracker.models import (
            PartTypes, Processes, ProcessStep, SamplingRule, SamplingRuleSet, Steps,
        )
        cls.pump = PartTypes.objects.create(tenant=cls.tenant, name="Pump")
        cls.process = Processes.objects.create(tenant=cls.tenant, name="Pump Build",
                                               part_type=cls.pump, status="APPROVED")
        cls.step = Steps.objects.create(tenant=cls.tenant, part_type=cls.pump,
                                        name="Final Inspection")
        ProcessStep.objects.create(process=cls.process, step=cls.step, order=1)
        cls.live = SamplingRuleSet.objects.create(
            tenant=cls.tenant, part_type=cls.pump, process=cls.process, step=cls.step,
            name="Final rules", active=True, aql=Decimal("1.000"), inspection_level="II")
        SamplingRule.objects.create(tenant=cls.tenant, ruleset=cls.live,
                                    rule_type="FIRST_N_PARTS", value=3, order=0)
        SamplingRule.objects.create(tenant=cls.tenant, ruleset=cls.live,
                                    rule_type="EVERY_NTH_PART", value=5, order=1)

    def _rulesets(self):
        from Tracker.models import SamplingRuleSet
        return SamplingRuleSet.objects.filter(step=self.step, archived=False)

    def _rules(self, ruleset):
        return sorted(ruleset.rules.filter(archived=False)
                      .values_list("order", "rule_type", "value"))

    def test_a_changed_active_ruleset_becomes_an_inactive_draft(self):
        body = self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,FIRST_N_PARTS,3\n"
                                        f"Pump,{STEP},Final rules,1,EVERY_NTH_PART,10\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertEqual(body["summary"]["updated"], 2, body)
        draft = self._rulesets().get(active=False)
        self.assertEqual(draft.supersedes_id, self.live.id)
        self.assertEqual(draft.version, self.live.version + 1)
        self.assertEqual(self._rules(draft), [(0, "FIRST_N_PARTS", 3), (1, "EVERY_NTH_PART", 10)])
        # The plan settings come with it.
        self.assertEqual((draft.aql, draft.inspection_level), (Decimal("1.000"), "II"))
        # Still in force, unchanged, until someone activates the draft.
        self.live.refresh_from_db()
        self.assertTrue(self.live.active)
        self.assertEqual(self._rules(self.live), [(0, "FIRST_N_PARTS", 3), (1, "EVERY_NTH_PART", 5)])

    def test_a_second_import_edits_the_same_draft(self):
        self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,EVERY_NTH_PART,10\n")
        body = self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,PERCENTAGE,20\n")
        self.assertEqual(body["summary"]["updated"], 1, body)
        self.assertEqual(self._rulesets().count(), 2)
        self.assertEqual(self._rules(self._rulesets().get(active=False)),
                         [(0, "PERCENTAGE", 20)])

    def test_replace_removes_rules_the_file_leaves_out(self):
        self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,FIRST_N_PARTS,3\n")
        self.assertEqual(self._rules(self._rulesets().get(active=False)),
                         [(0, "FIRST_N_PARTS", 3)])

    def test_an_unchanged_file_changes_nothing(self):
        body = self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,FIRST_N_PARTS,3\n"
                                        f"Pump,{STEP},Final rules,1,EVERY_NTH_PART,5\n")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(self._rulesets().count(), 1)

    def test_a_new_ruleset_is_created_inactive(self):
        body = self.import_csv(HEADER + f"Pump,{STEP},Tight rules,0,PERCENTAGE,50\n")
        self.assertEqual(body["summary"]["created"], 1, body)
        new = self._rulesets().get(name="Tight rules")
        self.assertFalse(new.active)
        self.assertEqual(new.process_id, self.process.id)
        self.assertEqual(self._rules(new), [(0, "PERCENTAGE", 50)])

    def test_one_bad_rule_fails_its_whole_ruleset_only(self):
        body = self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,FIRST_N_PARTS,3\n"
                                        f"Pump,{STEP},Final rules,1,SOMETIMES,5\n"
                                        f"Pump,{STEP},Tight rules,0,PERCENTAGE,50\n")
        self.assertEqual(body["summary"]["errors"], 2, body)  # both Final-rules rows
        self.assertIn("SOMETIMES", str(body["results"]))
        self.assertFalse(self._rulesets().filter(name="Final rules", active=False).exists())
        self.assertTrue(self._rulesets().filter(name="Tight rules").exists())

    def test_a_rule_the_api_would_refuse_is_refused(self):
        """Rules are validated by the API's SamplingRuleSerializer: a value can't be negative."""
        body = self.import_csv(HEADER + f"Pump,{STEP},Final rules,0,EVERY_NTH_PART,-2\n")
        self.assert_row_errors(body, mentions="greater than or equal to 0")
        self.assertEqual(self._rulesets().count(), 1)

    def test_a_step_that_names_nothing_is_refused(self):
        body = self.import_csv(HEADER + "Pump,Pump Build > Paint,Final rules,0,RANDOM,\n")
        self.assert_row_errors(body, mentions="Paint")

    def test_an_export_writes_only_rulesets_in_force(self):
        from Tracker.models import SamplingRule, SamplingRuleSet
        draft = SamplingRuleSet.objects.create(
            tenant=self.tenant, part_type=self.pump, step=self.step, name="Final rules",
            active=False, supersedes=self.live, version=2)
        SamplingRule.objects.create(tenant=self.tenant, ruleset=draft,
                                    rule_type="RANDOM", order=0)
        text = self.export("csv").decode("utf-8-sig")
        self.assertIn(STEP, text)
        self.assertIn("EVERY_NTH_PART", text)
        self.assertNotIn("RANDOM", text)

    def test_an_export_imports_back_unchanged(self):
        from Tracker.models import SamplingRule
        before = self.snapshot(SamplingRule)
        body = self.import_file(self.export("xlsx"), "sampling.xlsx")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertEqual(body["summary"]["created"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(self._rulesets().count(), 1)
        self.assertEqual(self.snapshot(SamplingRule), before)

    def test_a_csv_export_imports_back_unchanged(self):
        body = self.import_file(self.export("csv"), "sampling.csv")
        self.assertEqual(body["summary"]["errors"], 0, body)
        self.assertIn("No change", str(body["results"]))
        self.assertEqual(self._rulesets().count(), 1)

    def test_the_template_offers_the_parent_columns(self):
        header = self.client.get(f"/api/{self.endpoint}/import-template/csv/").content.decode(
            "utf-8-sig").splitlines()[0]
        for col in ("part_type", "step", "ruleset", "rule_type", "value"):
            self.assertIn(col, header)
