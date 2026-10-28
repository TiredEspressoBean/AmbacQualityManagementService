"""Step-level PERCENTAGE sampling uses the substep engine's per-part hash (user
decision 2026-10-28, B8). It used to take the first slice of the parts at the step:
the answer moved as parts arrived, and a 4-part lot at 20% sampled nothing."""
import uuid
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from Tracker.services.dwi.sampling_decisions import percentage_selects


class PercentageHashTests(SimpleTestCase):

    def test_roughly_value_percent_over_many_parts(self):
        rule = uuid.uuid4()
        picked = sum(percentage_selects(uuid.uuid4(), rule, 20) for _ in range(5000))
        self.assertTrue(850 <= picked <= 1150, picked)  # 20% of 5000, ±3 sd

    def test_zero_takes_none_and_hundred_takes_all(self):
        rule = uuid.uuid4()
        ids = [uuid.uuid4() for _ in range(2000)]
        self.assertFalse(any(percentage_selects(i, rule, 0) for i in ids))
        self.assertTrue(all(percentage_selects(i, rule, 100) for i in ids))

    def test_the_answer_is_the_parts_own(self):
        """Same part and rule, same answer, however many parts are at the step."""
        from Tracker.services.mes.sampling_applier import SamplingFallbackApplier
        part = SimpleNamespace(id=uuid.uuid4(), created_at=0)
        rule = SimpleNamespace(id=uuid.uuid4(), rule_type="PERCENTAGE", value=20)
        expected = percentage_selects(part.id, rule.id, 20)
        for crowd in (0, 3, 50):
            others = [SimpleNamespace(id=uuid.uuid4(), created_at=0) for _ in range(crowd)]
            applier = SamplingFallbackApplier.__new__(SamplingFallbackApplier)
            applier.part = part
            applier.work_order, applier.part_type, applier.step = None, None, None
            with mock.patch('Tracker.models.Parts') as P:
                P.objects.filter.return_value.order_by.return_value = others
                self.assertEqual(applier._should_sample(rule), expected)

    def test_step_and_substep_agree(self):
        from Tracker.models import SamplingOutcome
        from Tracker.services.dwi import sampling_decisions as sd
        part = SimpleNamespace(id=uuid.uuid4())
        rule = SimpleNamespace(id=uuid.uuid4(), rule_type="PERCENTAGE", value=37, ruleset=None)
        outcome, _ = sd._evaluate_rule(rule, part)
        self.assertEqual(outcome == SamplingOutcome.SELECTED.value,
                         percentage_selects(part.id, rule.id, 37))
