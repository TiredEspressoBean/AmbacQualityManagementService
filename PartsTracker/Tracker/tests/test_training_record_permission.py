"""Who may write a training record (2026-10-06).

A training record certifies someone as qualified — what the training gate and ISO 9001
7.2 read. It sat in STAFF_OPERATIONAL_WRITE, so an operator could POST themselves an
expert certification (found by probing as an operator: 201). Now it is held by the
gate-override tier plus the authoring roles, and withheld from Operator, QA Inspector
and Purchasing.
"""
from django.test import SimpleTestCase

from Tracker.presets import GROUP_PRESETS, STAFF_OPERATIONAL_WRITE, TRAINING_RECORD_WRITE


class TrainingRecordWriteTests(SimpleTestCase):
    def _can_write(self, group):
        perms = set(GROUP_PRESETS[group].get("permissions", []))
        return {"add_trainingrecord", "change_trainingrecord"} <= perms

    def test_not_in_the_operational_bucket(self):
        self.assertFalse({"add_trainingrecord", "change_trainingrecord"} & set(STAFF_OPERATIONAL_WRITE))
        self.assertEqual(set(TRAINING_RECORD_WRITE), {"add_trainingrecord", "change_trainingrecord"})

    def test_operators_and_inspectors_cannot_certify(self):
        for group in ("operator", "qa_inspector", "purchasing", "customer", "auditor"):
            self.assertFalse(self._can_write(group), group)

    def test_managers_leads_and_authors_still_can(self):
        for group in ("tenant_admin", "qa_manager", "production_manager", "shift_lead",
                      "document_controller", "engineering"):
            self.assertTrue(self._can_write(group), group)

    def test_whoever_may_override_the_gate_may_also_certify(self):
        """The two controls line up: the one-time override never reaches further than
        standing certification."""
        for group, preset in GROUP_PRESETS.items():
            if "override_training_gate" in preset.get("permissions", []):
                self.assertTrue(self._can_write(group), group)


class QualityControlRecordWriteTests(SimpleTestCase):
    """Calibration records, sampling rules and life-limit definitions: proven writable
    by an operator (2026-10-06) — a PASS calibration even returns failed equipment to
    service. Withheld from Operator and Purchasing; each list can narrow later."""

    def test_operators_and_purchasing_cannot_write_them(self):
        from Tracker.presets import (CALIBRATION_RECORD_WRITE, LIFE_LIMIT_WRITE, SAMPLING_RULE_WRITE,
                                     SPC_BASELINE_WRITE)
        guarded = (set(CALIBRATION_RECORD_WRITE) | set(SAMPLING_RULE_WRITE) | set(LIFE_LIMIT_WRITE)
                   | set(SPC_BASELINE_WRITE))
        # Unlinking a limit from its part type defeats it as surely as raising it.
        self.assertIn("delete_parttypelifelimit", LIFE_LIMIT_WRITE)
        self.assertFalse(guarded & set(STAFF_OPERATIONAL_WRITE))
        for group in ("operator", "purchasing", "customer", "auditor"):
            self.assertFalse(guarded & set(GROUP_PRESETS[group].get("permissions", [])), group)

    def _holders(self, perms):
        return {g for g, p in GROUP_PRESETS.items() if set(perms) <= set(p.get("permissions", []))}

    def test_each_list_reaches_exactly_its_roles(self):
        from Tracker.presets import (CALIBRATION_RECORD_WRITE, LIFE_LIMIT_WRITE, SAMPLING_RULE_WRITE,
                                     SPC_BASELINE_WRITE)
        staff = {"tenant_admin", "qa_manager", "qa_inspector", "production_manager", "shift_lead",
                 "document_controller", "engineering"}
        quality = {"tenant_admin", "qa_manager", "qa_inspector"}
        self.assertEqual(self._holders(CALIBRATION_RECORD_WRITE), staff)
        self.assertEqual(self._holders(SPC_BASELINE_WRITE), staff)
        # Narrowed 2026-10-06: sampling is a quality decision, life limits an
        # engineering specification.
        self.assertEqual(self._holders(SAMPLING_RULE_WRITE), quality)
        self.assertEqual(self._holders(LIFE_LIMIT_WRITE), quality | {"engineering"})

    def test_grants_with_no_endpoint_are_gone(self):
        for perm in ("add_qaapproval", "add_steprequirement", "add_samplinganalytics",
                     "add_generatedreport", "change_measurementresult", "add_approvalresponse"):
            self.assertNotIn(perm, STAFF_OPERATIONAL_WRITE, perm)
