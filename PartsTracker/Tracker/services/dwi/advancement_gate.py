"""
Substep-completion gate for step advancement.

This is the new blocker #8 inside `Steps.can_advance_from_step`. It walks
the Step's Substeps and returns blocker strings for any required-and-
unsatisfied substep.

Source-of-truth design: `scratch_advancement_gate.py` (engine sandbox)
and `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`.

What the gate enforces (per substep):

- Optional substeps with no completion are skipped (operator declined).
- SAMPLED substeps: read the live SamplingDecision for (step_execution,
  substep). If absent (programming bug — entry hook didn't fire), we
  log + skip rather than break legacy callers. If DESELECTED or PENDING,
  the substep is satisfied automatically. If SELECTED, a non-voided
  SubstepCompletion must exist; the N/A path is re-validated at gate
  time so retroactive `is_critical=True` edits properly block.
- BATCH substeps: the part must be covered by a sealed BatchExecution
  that has a non-voided SubstepCompletion for the substep. Split parts
  inherit batch completions from any sealed BatchExecution they were a
  member of.

The gate runs only when `feature_flags.substep_gate_enabled(tenant)`
returns True. Existing tenants default to legacy behavior.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Tracker.models import StepExecution, Steps, WorkOrder


logger = logging.getLogger(__name__)


def substep_completion_blockers(step: "Steps", step_execution: "StepExecution",
                                work_order: "WorkOrder") -> list[str]:
    """Return blocker strings for any required-and-unsatisfied substep.

    Empty list means the substep-completion gate passes for this part.
    """
    from Tracker.models import (
        BatchExecution,
        SamplingDecision,
        SamplingOutcome,
        Substep,
        SubstepCompletion,
        SubstepScope,
    )

    part = getattr(step_execution, 'part', None)
    if part is None:
        # Cores don't carry per-part substep completions yet; defer to the
        # reman-specific gate. Substep gate is part-only for now.
        return []

    # Exclude archived (soft-deleted) substeps — a voided substep definition
    # must not gate advancement.
    substeps = list(Substep.objects.filter(step=step, archived=False))
    if not substeps:
        return []

    substep_ids = [s.id for s in substeps]

    # Pre-fetch live completions for this StepExecution.
    completions_by_substep: dict[int, SubstepCompletion] = {
        c.substep_id: c
        for c in SubstepCompletion.objects.filter(
            step_execution=step_execution,
            substep_id__in=substep_ids,
            is_voided=False,
        )
    }

    # Pre-fetch live SamplingDecisions.
    decisions_by_substep: dict[int, SamplingDecision] = {
        d.substep_id: d
        for d in SamplingDecision.objects.filter(
            step_execution=step_execution,
            substep_id__in=substep_ids,
            superseded_by__isnull=True,
        )
    }

    # Pre-fetch sealed batches that cover this part for this step
    # (regardless of current cohort-split status — see Case 19 in the
    # sandbox).
    sealed_batches_for_part = list(
        BatchExecution.objects.filter(
            step=step,
            parts=part,
            sealed_at__isnull=False,
        )
    )
    cohort_completions_index: dict[tuple[int, int], SubstepCompletion] = {}
    if sealed_batches_for_part:
        # tenant-safe: batch_execution and substep are both tenant-scoped FKs;
        # __in lookup passes tenant-scoped instances/ids from the same context.
        for c in SubstepCompletion.objects.filter(
            batch_execution__in=sealed_batches_for_part,
            substep__in=substep_ids,
            is_voided=False,
        ):
            cohort_completions_index[(c.batch_execution_id, c.substep_id)] = c

    def _sealed_batch_with_completion(substep: Substep) -> tuple[BatchExecution | None, bool]:
        """Return (covering batch, has_completion). batch=None means no
        sealed batch covers this part."""
        for b in sealed_batches_for_part:
            if (b.id, substep.id) in cohort_completions_index:
                return b, True
        return (sealed_batches_for_part[0] if sealed_batches_for_part else None), False

    blockers: list[str] = []

    for substep in substeps:
        # Optional substeps with no completion are skipped (operator
        # explicitly declined). Completions on optional substeps still
        # get re-validated below.
        completion = completions_by_substep.get(substep.id)
        if substep.is_optional and completion is None:
            continue

        if substep.scope == SubstepScope.SAMPLED:
            decision = decisions_by_substep.get(substep.id)
            if decision is None:
                # No persisted decision — either the entry hook hasn't
                # run for this StepExecution (Phase 3 backfill pending)
                # or the substep was added after this exec started.
                # Degrade conservatively: substeps with a sampling_rule
                # behave as DESELECTED (rule absence = not required);
                # rule-less substeps fall through as SELECTED.
                if substep.sampling_rule_id is not None:
                    logger.warning(
                        "SamplingDecision missing for step_execution=%s substep=%s; "
                        "treating as DESELECTED. Backfill needed.",
                        step_execution.id, substep.id,
                    )
                    continue
                # rule-less SAMPLED substep — proceed as SELECTED below
                outcome = SamplingOutcome.SELECTED
            else:
                outcome = decision.outcome

            if outcome == SamplingOutcome.DESELECTED:
                continue
            if outcome == SamplingOutcome.PENDING:
                # Non-blocking. Cohort-close re-evaluation may retroactively
                # flag this part if the decision flips to SELECTED, but the
                # gate itself doesn't hold the part now.
                continue

            # SELECTED → must have a non-voided completion
            if completion is None:
                blockers.append(f"Substep '{substep.title}' not completed for this part")
                continue

            # Re-check N/A validity at gate time (write-time enforcement
            # is best-effort; substeps may flip to is_critical after the
            # row was written).
            na_problems = _na_problems(substep, completion)
            if na_problems:
                blockers.append(
                    f"Substep '{substep.title}' N/A no longer valid: "
                    + "; ".join(na_problems)
                )

        else:  # BATCH
            batch, has_completion = _sealed_batch_with_completion(substep)
            if batch is None:
                blockers.append(
                    f"Batch substep '{substep.title}' requires a sealed "
                    "batch covering this part"
                )
                continue
            if not has_completion:
                blockers.append(
                    f"Batch substep '{substep.title}' has no completion "
                    f"on sealed batch #{batch.id}"
                )

    # Terminal-step reconciliation gate. Flow #9 blocker #8: if this is
    # a terminal step (shipment / finished goods), refuse to advance any
    # part whose WO has live PENDING SamplingDecisions upstream. Forces
    # supervisor reconciliation before product leaves the system —
    # prevents shipping unverified parts when rules like LAST_N_PARTS
    # couldn't decide at step entry.
    if getattr(step, 'is_terminal', False) and work_order is not None:
        pending_count = SamplingDecision.objects.filter(
            step_execution__part__work_order=work_order,
            outcome=SamplingOutcome.PENDING,
            superseded_by__isnull=True,
        ).count()
        if pending_count:
            blockers.append(
                f"Terminal step: {pending_count} PENDING sampling "
                "decision(s) require reconciliation before shipment."
            )

    return blockers


def _na_problems(substep, completion) -> list[str]:
    """Re-validate an N/A completion at gate time. Returns problem strings
    if the N/A row is no longer valid under the current substep config."""
    problems: list[str] = []
    if not completion.marked_not_applicable:
        return problems
    if substep.is_critical:
        problems.append(f"Substep '{substep.title}' is critical; cannot be marked N/A")
    elif not substep.allow_not_applicable:
        problems.append(f"Substep '{substep.title}' does not allow N/A")
    elif not completion.na_reason_code:
        problems.append(f"N/A on '{substep.title}' requires a reason code")
    return problems
