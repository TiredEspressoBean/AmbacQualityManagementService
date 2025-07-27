import random


class SamplingFallbackApplier:
    def __init__(self, part):
        self.part = part
        self.step = part.step
        self.work_order = part.work_order
        self.part_type = part.part_type

    def evaluate(self):
        """
        Determine if this part requires sampling at the current step.

        Returns:
            dict: {
                "requires_sampling": bool,
                "rule": SamplingRule | None,
                "ruleset": SamplingRuleSet | None,
                "context": dict (optional),
            }
        """
        from Tracker.models import SamplingRuleSet

        if not self.step or not self.part_type:
            return {"requires_sampling": False}

        ruleset = SamplingRuleSet.objects.filter(
            step=self.step,
            part_type=self.part_type,
            active=True
        ).order_by("version").last()

        if not ruleset:
            return {"requires_sampling": False}

        # Find a rule that applies (placeholder logic — customize per strategy)
        applicable_rules = ruleset.rules.order_by("order")  # assuming inline order
        for rule in applicable_rules:
            if self._should_sample(rule):
                return {
                    "requires_sampling": True,
                    "rule": rule,
                    "ruleset": ruleset,
                    "context": {"reason": "Matched rule by logic"}  # optional context
                }

        return {
            "requires_sampling": False,
            "rule": None,
            "ruleset": ruleset,
            "context": {"reason": "No rule triggered"}
        }

    def apply(self):
        """
        Activate fallback sampling rule for this step + work order if not already triggered.
        Triggered by the latest part error.
        """
        from Tracker.models import SamplingRuleSet, SamplingTriggerState

        if not self.step or not self.work_order:
            return

        base_ruleset = SamplingRuleSet.objects.filter(
            step=self.step,
            part_type=self.part_type,
            active=True
        ).order_by("version").last()

        fallback = base_ruleset.fallback_ruleset if base_ruleset else None
        if not fallback or not fallback.active:
            return

        already_triggered = SamplingTriggerState.objects.filter(
            ruleset=fallback,
            step=self.step,
            work_order=self.work_order,
            active=True
        ).exists()

        if already_triggered:
            return

        SamplingTriggerState.objects.create(
            ruleset=fallback,
            step=self.step,
            work_order=self.work_order,
            triggered_by=self.part.error_reports.last()  # if null is OK
        )

    def _should_sample(self, rule):
        from Tracker.models import Parts
        """
        Determine if the part should be sampled based on the rule type and value.
        """
        count = Parts.objects.filter(
            step=self.step,
            work_order=self.work_order,
            part_type=self.part_type
        ).count()

        if rule.rule_type == "every_nth_part":
            n = int(rule.value)
            return n > 0 and (count % n == 0)

        elif rule.rule_type == "percentage":
            try:
                percent = float(rule.value)
                return random.uniform(0, 100) < percent
            except ValueError:
                return False

        elif rule.rule_type == "random":
            probability = float(rule.value)  # value should be between 0.0 and 1.0
            return random.random() < probability

        elif rule.rule_type == "first_n_parts":
            n = int(rule.value)
            return count < n

        elif rule.rule_type == "last_n_parts":
            n = int(rule.value)
            # You'll need to know total expected parts in the work order
            total_parts = self.work_order.expected_quantity if hasattr(self.work_order,
                                                                       "expected_quantity") else None
            if total_parts is None:
                return False
            return count >= (total_parts - n)

        return False
