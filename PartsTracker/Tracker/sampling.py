class SamplingFallbackApplier:
    """
    Queryset-based sampling system for clarity and auditability.

    Evaluates sampling rules using queryset logic instead of hashes.
    Prioritizes readability and audit trail over performance.
    """

    def __init__(self, part):
        self.part = part
        self.work_order = part.work_order
        self.step = part.step
        self.part_type = part.part_type

    def evaluate(self):
        from Tracker.models import SamplingRuleSet, SamplingTriggerState

        if not self.step or not self.part_type:
            return {"requires_sampling": False}

        # Fallback rules take priority if present
        active_fallback = SamplingTriggerState.objects.filter(
            step=self.step,
            work_order=self.work_order,
            active=True
        ).first()

        if active_fallback:
            ruleset = active_fallback.ruleset
            context_info = "Using fallback ruleset"
            ruleset_type = "FALLBACK"
        else:
            ruleset = SamplingRuleSet.objects.filter(
                step=self.step,
                part_type=self.part_type,
                active=True,
                is_fallback=False
            ).order_by("version").last()
            context_info = "Using primary ruleset"
            ruleset_type = "PRIMARY"

        if not ruleset:
            return {"requires_sampling": False}

        applicable_rules = ruleset.rules.order_by("order")

        for rule in applicable_rules:
            if self._should_sample(rule):
                self._log_sampling_decision(rule, True, ruleset_type)
                return {
                    "requires_sampling": True,
                    "rule": rule,
                    "ruleset": ruleset,
                    "context": {"reason": f"{context_info} - matched {rule.rule_type}"}
                }

            if rule.rule_type in ["first_n_parts", "last_n_parts"]:
                self._log_sampling_decision(rule, False, ruleset_type)
                return {
                    "requires_sampling": False,
                    "rule": None,
                    "ruleset": ruleset,
                    "context": {"reason": f"{context_info} - excluded by {rule.rule_type}"}
                }

        if applicable_rules.exists():
            self._log_sampling_decision(applicable_rules.first(), False, ruleset_type)

        return {
            "requires_sampling": False,
            "rule": None,
            "ruleset": ruleset,
            "context": {"reason": f"{context_info} - no rules triggered"}
        }

    def _should_sample(self, rule):
        from Tracker.models import Parts

        if not rule.value:
            return False

        qs = Parts.objects.filter(
            work_order=self.work_order,
            part_type=self.part_type,
            step=self.step
        ).order_by('created_at', 'id')

        if rule.rule_type == "every_nth_part":
            parts = list(qs)
            try:
                index = parts.index(self.part)
                return (index + 1) % rule.value == 0
            except ValueError:
                return False

        elif rule.rule_type == "percentage":
            parts = list(qs)
            threshold = int(len(parts) * (rule.value / 100))
            return self.part in parts[:threshold]

        elif rule.rule_type == "random":
            import random
            random.seed(self.part.created_at.timestamp())  # use timestamp as deterministic seed
            return random.random() < (rule.value / 100.0)

        elif rule.rule_type == "first_n_parts":
            return qs.filter(created_at__lte=self.part.created_at).count() <= rule.value

        elif rule.rule_type == "last_n_parts":
            total = qs.count()
            index = qs.filter(created_at__lte=self.part.created_at).count()
            return index > (total - rule.value)

        elif rule.rule_type == "exact_count":
            return self._evaluate_exact_count_rule(rule, qs)

        return False

    def _evaluate_exact_count_rule(self, rule, qs):
        """Select exactly N parts based on created_at timestamp (deterministic)"""
        if rule.value <= 0:
            return False

        all_parts = list(qs)
        if rule.value >= len(all_parts):
            return True

        selected_parts = all_parts[:rule.value]
        return self.part in selected_parts

    def _log_sampling_decision(self, rule, decision, ruleset_type):
        from Tracker.models import SamplingAuditLog

        SamplingAuditLog.objects.create(
            part=self.part,
            rule=rule,
            sampling_decision=decision,
            ruleset_type=ruleset_type
        )

    def apply(self):
        if not self.work_order or not self.step:
            return
        self._reevaluate_remaining_parts()

    def _reevaluate_remaining_parts(self):
        from Tracker.models import Parts, PartsStatus

        remaining_parts = Parts.objects.filter(
            work_order=self.work_order,
            step=self.step,
            part_type=self.part_type,
            part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
            id__gt=self.part.id
        )

        updates = []
        for part in remaining_parts:
            evaluator = SamplingFallbackApplier(part)
            result = evaluator.evaluate()

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        Parts.objects.bulk_update(
            updates,
            ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"]
        )
