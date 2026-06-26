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

from django.db import transaction

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


@transaction.atomic
def activate_sampling_ruleset(ruleset: SamplingRuleSet, user=None) -> None:
    """Deactivate peer rulesets for the same step/part_type, activate *ruleset*,
    then re-evaluate sampling for all in-flight parts at that step.

    Wrapped in a transaction so the three-step sequence (peer-deactivate,
    activate, re-evaluate parts) commits atomically — partial application
    would leave the system with no active ruleset for the (step, part_type)
    pair or leave parts evaluated against the wrong ruleset.
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
    """Execute the TIGHTEN_SAMPLING action: switch to ``ruleset.fallback_ruleset``
    and propagate fallback sampling to remaining parts in the work order.

    The *decision* to tighten is the quality-gate dispatcher's job
    (``services.qms.quality_gate``); this is the action executor and assumes the
    gate already tripped. Idempotent: if the fallback is already active for this
    (work_order, step), the existing trigger is returned rather than creating a
    duplicate (which the unique constraint would reject anyway).

    Atomic so the trigger row + the bulk part updates either both land or
    both roll back — otherwise a trigger could exist with no parts updated,
    leaving subsequent parts in the WO without their fallback flag.

    Returns the SamplingTriggerState (created or existing), or None if no
    fallback_ruleset is configured.
    """
    if not ruleset.fallback_ruleset:
        return None

    work_order = triggering_part.work_order
    step = ruleset.step

    # Already tightened for this work order at this step — nothing to do.
    existing = SamplingTriggerState.objects.filter(
        ruleset=ruleset.fallback_ruleset,
        work_order=work_order,
        step=step,
        active=True,
    ).first()
    if existing:
        return existing

    with transaction.atomic():
        trigger_state = SamplingTriggerState.objects.create(
            ruleset=ruleset.fallback_ruleset,
            work_order=work_order,
            step=step,
            triggered_by=quality_report,
        )

        _apply_fallback_to_remaining_parts_for_ruleset(ruleset, triggering_part)

    return trigger_state
