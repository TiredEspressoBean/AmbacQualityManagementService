"""
SamplingDecision writer: persists per-substep sampling outcomes when a
part enters a step.

Contract with the advancement gate: every Substep belonging to a Step
that a part enters gets a `SamplingDecision` row written here. The gate
reads those rows; this module is the only thing that creates them.

For the rule evaluation we lean on the existing `SamplingRule` model
(rule_type + value) rather than introducing a new one. The decisions
this module writes correspond to substep-level cadence — independent
from the legacy Step-level `Steps.sampling_required` flag that drives
QualityReports / inspection sampling.

LAST_N_PARTS and EXACT_COUNT can't be evaluated at entry — they need
the cohort closed first. We write them as PENDING; a follow-up
cohort-close worker (Phase 7+) re-evaluates them and supersedes.
"""

from __future__ import annotations

import hashlib
import logging
import random
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from Tracker.models import Parts, SamplingRule, StepExecution, Substep


logger = logging.getLogger(__name__)


def evaluate_substep_sampling(step_execution: "StepExecution") -> None:
    """Write one SamplingDecision per Substep on the StepExecution's
    parent Step. Idempotent: re-running on the same execution is safe
    because each substep enforces a live-row uniqueness constraint.

    Called from `Tracker.services.mes.parts.advance_part_step` after the
    new StepExecution is created.
    """
    from Tracker.models import (
        SamplingDecision,
        SamplingOutcome,
        Substep,
        SubstepScope,
    )

    if step_execution.part_id is None:
        # Cores (reman) don't run the per-part substep gate yet.
        return

    substeps = list(Substep.objects.filter(step_id=step_execution.step_id))
    if not substeps:
        return

    # Skip substeps that already have a live decision (idempotent).
    already = set(
        SamplingDecision.objects.filter(
            step_execution=step_execution,
            substep_id__in=[s.id for s in substeps],
            superseded_by__isnull=True,
        ).values_list('substep_id', flat=True)
    )

    new_rows: list[SamplingDecision] = []
    for substep in substeps:
        if substep.id in already:
            continue

        if substep.scope == SubstepScope.BATCH:
            outcome = SamplingOutcome.SELECTED
            ruleset_version = 1
        elif substep.sampling_rule_id is None:
            outcome = SamplingOutcome.SELECTED
            ruleset_version = 1
        else:
            outcome, ruleset_version = _evaluate_rule(
                substep.sampling_rule,
                step_execution.part,
            )

        new_rows.append(SamplingDecision(
            step_execution=step_execution,
            substep=substep,
            outcome=outcome,
            ruleset_version=ruleset_version,
        ))

    if new_rows:
        SamplingDecision.objects.bulk_create(new_rows)  # tenant-safe: each row carries tenant-scoped step_execution + substep FKs populated above


def _evaluate_rule(rule: "SamplingRule", part: "Parts") -> tuple[str, int]:
    """Evaluate a SamplingRule for a single Part. Returns
    (outcome_value, ruleset_version)."""
    from Tracker.models import SamplingOutcome
    from Tracker.models.mes_standard import SamplingRuleType

    ruleset = rule.ruleset
    ruleset_version = getattr(ruleset, 'version', 1) if ruleset else 1
    rule_type = rule.rule_type
    value = rule.value

    if rule_type == SamplingRuleType.EVERY_NTH_PART and value:
        pos = _cohort_position(part)
        return (
            SamplingOutcome.SELECTED.value if pos % value == 0
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    if rule_type == SamplingRuleType.FIRST_N_PARTS and value:
        pos = _cohort_position(part)
        return (
            SamplingOutcome.SELECTED.value if pos <= value
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    if rule_type == SamplingRuleType.LAST_N_PARTS and value:
        # Use WO.quantity (planned cohort size, set at WO creation) +
        # cohort_position to decide eagerly. This avoids the "can't know
        # until cohort closes" problem by trusting the planned quantity
        # — splits/scrap shrink the actual cohort but don't shift which
        # parts were planned to be last.
        quantity = _planned_cohort_size(part)
        if quantity <= 0:
            return (SamplingOutcome.PENDING.value, ruleset_version)
        pos = _cohort_position(part)
        return (
            SamplingOutcome.SELECTED.value if pos > quantity - value
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    if rule_type == SamplingRuleType.EXACT_COUNT and value:
        # Evenly-spaced deterministic selection of N parts from the
        # planned cohort. Uses the fence-post trick: a part is selected
        # when its position crosses an N-way partition boundary in the
        # 1..Q sequence. Audit-defensible (reproducible from
        # cohort_position alone, no per-part hashing needed), unbiased
        # across the run, and resolves at part entry so PENDING never
        # gets written.
        quantity = _planned_cohort_size(part)
        if quantity <= 0:
            return (SamplingOutcome.PENDING.value, ruleset_version)
        if value >= quantity:
            # Asking for >= cohort size — sample everyone.
            return (SamplingOutcome.SELECTED.value, ruleset_version)
        pos = _cohort_position(part)
        # Fence-post: select if this position crosses a partition boundary.
        crossed = (pos * value) // quantity != ((pos - 1) * value) // quantity
        return (
            SamplingOutcome.SELECTED.value if crossed
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    if rule_type == SamplingRuleType.PERCENTAGE and value:
        digest = hashlib.sha256(
            f"{part.id}:{rule.id}".encode('utf-8')
        ).digest()
        bucket = digest[0]  # 0-255
        threshold = int(255 * value / 100)
        return (
            SamplingOutcome.SELECTED.value if bucket < threshold
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    if rule_type == SamplingRuleType.RANDOM and value:
        # `value` is treated as a percentage (1-100) for RANDOM, same as
        # PERCENTAGE but non-deterministic. Use random.random() so audit
        # can't reconstruct; deterministic random should be PERCENTAGE.
        return (
            SamplingOutcome.SELECTED.value
            if random.random() * 100 < value
            else SamplingOutcome.DESELECTED.value,
            ruleset_version,
        )

    logger.warning(
        "Unknown SamplingRule rule_type=%s value=%s for part=%s; treating as SELECTED.",
        rule_type, value, part.id,
    )
    return (SamplingOutcome.SELECTED.value, ruleset_version)


def _planned_cohort_size(part: "Parts") -> int:
    """Planned size of this Part's WorkOrder cohort. Pulled from
    `WorkOrder.quantity` (fixed at WO creation). Used by LAST_N_PARTS /
    EXACT_COUNT to resolve at part entry — they trust the planned size
    rather than waiting for the cohort to close, because splits/scrap
    after the fact don't change which parts were *planned* to be in the
    sampling positions."""
    wo = getattr(part, 'work_order', None)
    if wo is None:
        return 0
    qty = getattr(wo, 'quantity', None)
    try:
        return int(qty) if qty is not None else 0
    except (TypeError, ValueError):
        return 0


def _cohort_position(part: "Parts") -> int:
    """Position of this Part within its WorkOrder cohort (1-indexed),
    ordered by id (UUIDv7 is time-ordered, so this gives WO-creation
    order). Used by EVERY_NTH_PART / FIRST_N_PARTS / LAST_N_PARTS."""
    from Tracker.models import Parts

    if part.work_order_id is None:
        return 1
    # `unscoped` is a separate manager on SecureModel (not chained through
    # `objects`). Used here because the evaluator needs to count siblings
    # regardless of whether the current request's tenant context is set;
    # the explicit tenant_id filter below preserves multi-tenant safety.
    earlier = Parts.unscoped.filter(  # tenant-safe: explicit tenant_id kwarg
        work_order_id=part.work_order_id,
        id__lte=part.id,
        tenant_id=part.tenant_id,
    ).count()
    return max(1, earlier)


def reconcile_pending_decisions(work_order, step=None) -> dict:
    """Re-evaluate live PENDING SamplingDecisions for a WorkOrder.

    Called at terminal-step gate blocker resolution (Flow #11). The
    cohort is now closed (either WO is moving to terminal or supervisor
    explicitly triggered), so rules like LAST_N_PARTS / EXACT_COUNT that
    couldn't decide at part entry can now resolve deterministically.

    For each PENDING decision:
    - Re-evaluate the rule with the cohort-closed context
    - Write a new SamplingDecision row with the resolved outcome
    - Mark the PENDING row as superseded_by the new one

    The gate picks up the new outcomes on next evaluation. PENDING →
    SELECTED on a part with no completion becomes a new blocker the
    supervisor sees; PENDING → DESELECTED simply removes the PENDING
    blocker.

    Returns a summary dict: { reconciled, now_selected, now_deselected,
    still_pending }. The supervisor UI uses this to surface the result.
    """
    from Tracker.models import SamplingDecision, SamplingOutcome

    live_pending = SamplingDecision.objects.filter(
        step_execution__part__work_order=work_order,
        outcome=SamplingOutcome.PENDING,
        superseded_by__isnull=True,
    ).select_related('step_execution__part', 'substep')
    if step is not None:
        live_pending = live_pending.filter(step_execution__step=step)

    summary = {
        'reconciled': 0,
        'now_selected': 0,
        'now_deselected': 0,
        'still_pending': 0,
    }

    for old_decision in live_pending:
        substep = old_decision.substep
        part = old_decision.step_execution.part
        if substep.sampling_rule_id is None:
            # Should not have been PENDING; degrade gracefully.
            new_outcome = SamplingOutcome.SELECTED.value
            ruleset_version = old_decision.ruleset_version
        else:
            new_outcome, ruleset_version = _evaluate_rule(
                substep.sampling_rule, part,
            )

        # Two-phase supersession to satisfy the
        # dwi_samplingdecision_live_uniq partial index
        # (UNIQUE(step_execution, substep) WHERE superseded_by IS NULL).
        # If we created `new_decision` first, two live rows would exist for
        # the (step_execution, substep) pair momentarily → IntegrityError.
        # Instead: (1) temporarily self-supersede the old row so it drops
        # out of the live partial index, (2) create the new live row,
        # (3) repoint the old row's superseded_by at the new row.
        with transaction.atomic():
            old_decision.superseded_by_id = old_decision.id
            old_decision.save(update_fields=['superseded_by'])

            new_decision = SamplingDecision.objects.create(
                step_execution=old_decision.step_execution,
                substep=substep,
                outcome=new_outcome,
                ruleset_version=ruleset_version,
            )

            old_decision.superseded_by = new_decision
            old_decision.save(update_fields=['superseded_by'])

        summary['reconciled'] += 1
        if new_outcome == SamplingOutcome.SELECTED.value:
            summary['now_selected'] += 1
        elif new_outcome == SamplingOutcome.DESELECTED.value:
            summary['now_deselected'] += 1
        else:
            summary['still_pending'] += 1

    return summary
