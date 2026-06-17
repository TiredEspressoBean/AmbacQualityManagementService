"""
Part-level split mechanism for the lot-cohesion advancement engine.

Splits remove a Part from its WorkOrder cohort so it advances
independently of its siblings. Quarantine, rework, expedite, customer
pull, and scrap all funnel through the same `split_part_from_lot`
service. Once split, a part travels solo for the rest of its life in
this WorkOrder — no re-merging in v1.

Rework is a flavored split: the part is moved to a configured rework
target step rather than continuing forward.

Design reference: `scratch_advancement_gate.py` (case 2, 4, 13, 14)
and `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from Tracker.models import Parts, Steps, User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SplitResult:
    part_id: str
    reason: str
    moved_to_step_id: str | None  # set when rework reroutes the part
    already_split: bool


def split_part_from_lot(
    *,
    part: "Parts",
    reason: str,
    user: "User",
    rework_target_step: "Steps | None" = None,
    notes: str = "",
) -> SplitResult:
    """Mark `part` as split from its WO cohort. Permission-gated.
    Reason required (use a `PartSplitReason` enum value).

    For `reason=REWORK`, the part is moved to `rework_target_step`
    (explicit arg). When no rework target is provided and the reason is
    REWORK, the split is accepted but the part stays at its current
    step pending disposition.

    Returns a `SplitResult` describing what happened. Idempotent — a
    second call on an already-split part returns `already_split=True`
    without further changes.
    """
    from Tracker.models import PartSplitReason, StepExecution, StepTransitionLog

    if not user or not user.is_authenticated:
        raise PermissionDenied("Authenticated user required to split a part.")

    valid_reasons = {r.value for r in PartSplitReason}
    if reason not in valid_reasons:
        raise ValidationError(f"Unknown split reason: {reason!r}. Expected one of {valid_reasons}.")

    # 2d: a reworked part must be re-inspected. Re-inspection lives on the rework
    # step as an inspection-point substep (Decision #7), so a rework target must
    # carry one — otherwise the part could pass straight through unverified.
    if reason == PartSplitReason.REWORK and rework_target_step is not None:
        from Tracker.models import Substep
        has_inspection = Substep.objects.filter(
            step=rework_target_step, is_inspection_point=True, archived=False,
        ).exists()
        if not has_inspection:
            raise ValidationError(
                f"Rework target step '{rework_target_step.name}' has no inspection "
                "substep — reworked parts must be re-inspected before they can advance."
            )

    if part.split_from_cohort:
        return SplitResult(
            part_id=str(part.id),
            reason=part.split_reason or reason,
            moved_to_step_id=None,
            already_split=True,
        )

    with transaction.atomic():
        part.split_from_cohort = True
        part.split_reason = reason
        part.split_at = timezone.now()
        update_fields = ['split_from_cohort', 'split_reason', 'split_at']

        moved_to_step_id: str | None = None
        if reason == PartSplitReason.REWORK and rework_target_step is not None:
            # Close out the current StepExecution as ROLLED_BACK (part
            # didn't pass), then create a new StepExecution at the
            # rework target with a bumped visit_number.
            current_exec = StepExecution.objects.filter(
                part=part,
                step=part.step,
                status__in=['PENDING', 'CLAIMED', 'IN_PROGRESS'],
            ).order_by('-visit_number').first()
            if current_exec is not None:
                current_exec.status = 'ROLLED_BACK'
                current_exec.save(update_fields=['status'])

            part.step = rework_target_step
            update_fields.append('step')

            visit_number = StepExecution.get_visit_count(part, rework_target_step) + 1
            new_exec = StepExecution.objects.create(
                part=part,
                step=rework_target_step,
                visit_number=visit_number,
                assigned_to=user,
                status='PENDING',
            )

            # Write SamplingDecisions for the new exec.
            from Tracker.services.dwi.sampling_decisions import evaluate_substep_sampling
            evaluate_substep_sampling(new_exec)

            # StepTransitionLog has no `reason` field; the rework reason lives on
            # the part (split_reason) and the disposition — just log the move.
            StepTransitionLog.objects.create(
                part=part,
                step=rework_target_step,
                operator=user,
            )
            moved_to_step_id = str(rework_target_step.id)

        part.save(update_fields=update_fields)

        logger.info(
            "Part %s split from cohort (reason=%s, moved_to=%s, by=%s)",
            part.id, reason, moved_to_step_id, user.id,
        )

        # Cohort shrunk (or split-part landed at a new step).
        # Synchronously re-evaluate advancement in the same request so
        # the supervisor sees the result inline.
        if part.work_order_id and part.step_id:
            from Tracker.services.mes.advancement import try_advance_lot
            try_advance_lot(
                work_order_id=str(part.work_order_id),
                step_id=str(part.step_id),
                tenant_id=str(part.tenant_id),
                operator=user,
            )

    return SplitResult(
        part_id=str(part.id),
        reason=reason,
        moved_to_step_id=moved_to_step_id,
        already_split=False,
    )
