"""
SamplingRuleSet lifecycle services.

Extracted from SamplingRuleSet model methods. The model retains thin
delegates for backward compatibility; new callers should import from here.

Three public functions mirror the former model methods:
  supersede_sampling_ruleset  — create a successor version
  activate_sampling_ruleset   — deactivate peers, activate, re-evaluate parts
  create_sampling_fallback_trigger — create SamplingTriggerState and propagate
"""
from __future__ import annotations

from Tracker.models.mes_standard import SamplingRuleSet, SamplingTriggerState


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _reevaluate_active_parts_for_ruleset(ruleset: SamplingRuleSet, user=None) -> None:
    """Re-evaluate sampling assignment for parts currently at the ruleset's step."""
    from Tracker.models.mes_lite import Parts, PartsStatus
    from Tracker.services.mes.sampling_applier import SamplingFallbackApplier

    active_parts = Parts.objects.filter(
        step=ruleset.step,
        part_type=ruleset.part_type,
        part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
    )

    updates = []
    for part in active_parts:
        evaluator = SamplingFallbackApplier(part=part)
        result = evaluator.evaluate()

        part.requires_sampling = result.get("requires_sampling", False)
        part.sampling_rule = result.get("rule")
        part.sampling_ruleset = result.get("ruleset")
        part.sampling_context = result.get("context", {})
        updates.append(part)

    Parts.objects.bulk_update(
        updates,
        ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"],
    )


def _apply_fallback_to_remaining_parts_for_ruleset(
    ruleset: SamplingRuleSet, triggering_part
) -> None:
    """Apply fallback sampling to parts in the same work order that follow the triggering part."""
    from Tracker.models.mes_lite import Parts, PartsStatus
    from Tracker.services.mes.sampling_applier import SamplingFallbackApplier

    remaining_parts = Parts.objects.filter(
        work_order=triggering_part.work_order,
        step=ruleset.step,
        part_type=ruleset.part_type,
        part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
        id__gt=triggering_part.id,
    )

    updates = []
    for part in remaining_parts:
        evaluator = SamplingFallbackApplier(part=part)
        result = evaluator.evaluate()

        part.requires_sampling = result.get("requires_sampling", False)
        part.sampling_rule = result.get("rule")
        part.sampling_ruleset = result.get("ruleset")
        part.sampling_context = result.get("context", {})
        updates.append(part)

    Parts.objects.bulk_update(
        updates,
        ["requires_sampling", "sampling_rule", "sampling_ruleset", "sampling_context"],
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def supersede_sampling_ruleset(
    ruleset: SamplingRuleSet, *, name: str, rules, user
) -> SamplingRuleSet:
    """Create a successor SamplingRuleSet that supersedes *ruleset*.

    Inherits part_type, process, and step from the existing ruleset.
    Returns the newly created ruleset (inactive until activated).
    """
    return SamplingRuleSet.create_with_rules(
        part_type=ruleset.part_type,
        process=ruleset.process,
        step=ruleset.step,
        name=name,
        rules=rules,
        supersedes=ruleset,
        created_by=user,
    )


def activate_sampling_ruleset(ruleset: SamplingRuleSet, user=None) -> None:
    """Deactivate peer rulesets for the same step/part_type, activate *ruleset*,
    then re-evaluate sampling for all in-flight parts at that step.
    """
    SamplingRuleSet.objects.filter(
        step=ruleset.step,
        part_type=ruleset.part_type,
        active=True,
        is_fallback=ruleset.is_fallback,
    ).exclude(pk=ruleset.pk).update(active=False)

    ruleset.active = True
    ruleset.modified_by = user
    ruleset.save()

    _reevaluate_active_parts_for_ruleset(ruleset, user)


def create_sampling_fallback_trigger(
    ruleset: SamplingRuleSet, triggering_part, quality_report
):
    """Create a SamplingTriggerState for the fallback ruleset and propagate
    fallback sampling to remaining parts in the work order.

    Returns the created SamplingTriggerState, or None if no fallback_ruleset
    is configured.
    """
    if not ruleset.fallback_ruleset:
        return None

    trigger_state = SamplingTriggerState.objects.create(
        ruleset=ruleset.fallback_ruleset,
        work_order=triggering_part.work_order,
        step=ruleset.step,
        triggered_by=quality_report,
    )

    _apply_fallback_to_remaining_parts_for_ruleset(ruleset, triggering_part)

    return trigger_state
