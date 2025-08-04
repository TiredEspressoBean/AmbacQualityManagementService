import hashlib


class SamplingFallbackApplier:
    """
    Hash-based sampling system for compliance, performance, and auditability.

    Replaces position-based calculations with deterministic hash functions that provide:
    - Consistent Results: Same inputs always produce same outputs
    - Audit Trail: Clear documentation of sampling decisions  
    - Performance: O(1) calculations instead of O(n) queries
    - Compliance: Cryptographically sound randomness
    - Bias Prevention: No human or timing dependencies
    """

    def __init__(self, part):
        self.part = part
        self.work_order = part.work_order
        self.step = part.step
        self.part_type = part.part_type

    def evaluate(self):
        """Determine if this part requires sampling at the current step."""
        from Tracker.models import SamplingRuleSet, SamplingTriggerState

        if not self.step or not self.part_type:
            return {"requires_sampling": False}

        # Check for active fallback first
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

        # Evaluate rules in order using hash-based approach
        applicable_rules = ruleset.rules.order_by("order")
        for rule in applicable_rules:
            if self._should_sample(rule):
                # Log sampling decision for audit trail
                self._log_sampling_decision(rule, True, ruleset_type)

                return {
                    "requires_sampling": True,
                    "rule": rule,
                    "ruleset": ruleset,
                    "context": {"reason": f"{context_info} - matched {rule.rule_type}"}
                }

        # Log negative sampling decision for the first rule (representative)
        if applicable_rules.exists():
            self._log_sampling_decision(applicable_rules.first(), False, ruleset_type)

        return {
            "requires_sampling": False,
            "rule": None,
            "ruleset": ruleset,
            "context": {"reason": f"{context_info} - no rules triggered"}
        }

    def _should_sample(self, rule):
        """Hash-based sampling for compliance and consistency"""
        if not rule.value:
            return False

        # Create deterministic hash input using ERP IDs for external system compatibility
        hash_input = f"{self.work_order.ERP_id}-{self.part.ERP_id}-{rule.id}"
        hash_value = self._get_hash(hash_input)

        if rule.rule_type == "every_nth_part":
            return (hash_value % rule.value) == 0

        elif rule.rule_type == "percentage":
            return (hash_value % 100) < rule.value

        elif rule.rule_type == "random":
            probability = rule.value if rule.value <= 1 else rule.value / 100.0
            return (hash_value % 10000) < (probability * 10000)

        elif rule.rule_type == "first_n_parts":
            # Keep position-based for logical first/last rules where position matters
            return self._get_work_order_position() <= rule.value

        elif rule.rule_type == "last_n_parts":
            position = self._get_work_order_position()
            total = self.work_order.quantity
            return position > (total - rule.value)

        return False

    def _get_hash(self, input_string):
        """SHA-256 hash for compliance and auditability"""
        return int(hashlib.sha256(input_string.encode()).hexdigest()[:8], 16)

    def _get_work_order_position(self):
        """Get position only when needed for first/last rules (minimizes O(n) operations)"""
        from Tracker.models import Parts

        parts_in_sequence = Parts.objects.filter(
            work_order=self.work_order,
            part_type=self.part_type,
            created_at__lte=self.part.created_at
        ).order_by('created_at')

        return list(parts_in_sequence).index(self.part) + 1

    def _log_sampling_decision(self, rule, decision, ruleset_type):
        """Log sampling decision for audit trail and compliance"""
        from Tracker.models import SamplingAuditLog

        hash_input = f"{self.work_order.ERP_id}-{self.part.ERP_id}-{rule.id}"
        hash_output = self._get_hash(hash_input)

        SamplingAuditLog.objects.create(
            part=self.part,
            rule=rule,
            hash_input=hash_input,
            hash_output=hash_output,
            sampling_decision=decision,
            ruleset_type=ruleset_type
        )

    def apply(self):
        """Apply fallback sampling to remaining parts in work order"""
        if not self.work_order or not self.step:
            return

        # Re-evaluate remaining parts using fallback rules
        self._reevaluate_remaining_parts()

    def _reevaluate_remaining_parts(self):
        """Re-evaluate sampling for remaining parts using fallback rules"""
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
            result = evaluator.evaluate()  # Will use fallback rules if active

            part.requires_sampling = result.get("requires_sampling", False)
            part.sampling_rule = result.get("rule")
            part.sampling_ruleset = result.get("ruleset")
            part.sampling_context = result.get("context", {})
            updates.append(part)

        # Bulk update for efficiency
        Parts.objects.bulk_update(
            updates,
            ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"]
        )