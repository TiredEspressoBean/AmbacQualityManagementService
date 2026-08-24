"""
Part-level split mechanism for the lot-cohesion advancement engine.

Splits remove a Part from its WorkOrder cohort so it advances
independently of its siblings. Quarantine, rework, and scrap all funnel
through the same `split_part_from_lot` service.

A split part re-converges with its siblings via `rejoin_part_to_lot`: a
reworked/cleared part that has caught back up to a step where its cohort
sits rejoins the lot's flow, while its quality genealogy (lot_split_reason,
lot_split_at) is retained — the split→rejoin pair is an immutable record of
the detour. Scrapped parts never rejoin (they leave the lot for good).

Rework is a flavored split: the part is moved to a configured rework
target step rather than continuing forward.

Design reference: `scratch_advancement_gate.py` (case 2, 4, 13, 14)
and `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
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


@dataclass(frozen=True)
class RejoinResult:
    part_id: str
    rejoined: bool          # False when the part wasn't split (nothing to do)
    prior_reason: str | None  # the retained split reason (genealogy), if any


def split_part_from_lot(
    *,
    part: "Parts",
    reason: str,
    user: "User",
    rework_target_step: "Steps | None" = None,
    notes: str = "",
) -> SplitResult:
    """Mark `part` as split from its WO cohort. Authorization is enforced at the
    viewset (TenantModelPermissions → change_parts); this service takes `user` for
    provenance/attribution (audit, StepExecution.assigned_to), not as an auth gate.
    Reason required (use a `PartSplitReason` enum value).

    For `reason=REWORK`, the part is moved to `rework_target_step`
    (explicit arg). When no rework target is provided and the reason is
    REWORK, the split is accepted but the part stays at its current
    step pending disposition.

    Returns a `SplitResult` describing what happened. Idempotent — a
    second call on an already-split part returns `already_split=True`
    without further changes.
    """
    from Tracker.models import Parts, PartSplitReason, PartsStatus, StepExecution, StepTransitionLog

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
                "substep - reworked parts must be re-inspected before they can advance."
            )

    with transaction.atomic():
        # Lock the part and re-check the idempotency guard under the lock: two
        # concurrent splits of the same part must not both proceed (which would
        # duplicate the rework StepExecution and double-split). The second call
        # blocks here, then sees split_from_lot set and returns already_split.
        part = Parts.objects.select_for_update().get(pk=part.id)
        if part.split_from_lot:
            return SplitResult(
                part_id=str(part.id),
                reason=part.lot_split_reason or reason,
                moved_to_step_id=None,
                already_split=True,
            )

        part.split_from_lot = True
        part.lot_split_reason = reason
        part.lot_split_at = timezone.now()
        update_fields = ['split_from_lot', 'lot_split_reason', 'lot_split_at']

        if reason == PartSplitReason.SCRAP:
            # A scrapped part is terminal: mark it SCRAPPED so it's excluded from
            # scheduling and can never rejoin. The split flag alone doesn't set status
            # (status is otherwise driven by the disposition cascade), so a scrap-split
            # made directly through this service must set it here to stay consistent.
            part.part_status = PartsStatus.SCRAPPED
            update_fields.append('part_status')

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

            visit_number = StepExecution.get_visit_count_for_update(part, rework_target_step) + 1
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
            # the part (lot_split_reason) and the disposition — just log the move.
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


def rejoin_part_to_lot(
    *,
    part: "Parts",
    user: "User",
    notes: str = "",
) -> RejoinResult:
    """Re-converge a previously-split part back into its WorkOrder cohort's flow.

    The inverse of `split_part_from_lot`, for a reworked/quarantine-cleared part
    that has caught back up to a step where its siblings sit. Genealogy-preserving:

      - `split_from_lot` is cleared, so cohort gating (`try_advance_lot`) counts
        the part again and the scheduler re-collapses it into the lot;
      - `lot_split_reason` / `lot_split_at` are RETAINED, and `rejoined_at` is stamped — the
        split→rejoin pair is a permanent audit record of the detour the part took.

    Precondition — you can only rejoin where your siblings are: the part must be at
    a step that holds at least one other schedulable sibling in this WO (split or
    not). Rejoining to a step where the part stands alone is rejected; there is no
    cohort there to rejoin.

    Authorization is enforced at the viewset (TenantModelPermissions → change_parts),
    not here. Idempotent — a call on a part that isn't split returns
    ``rejoined=False`` without changes. SCRAP splits never rejoin (a scrapped part
    is terminal and unschedulable, so it can't satisfy the sibling precondition).
    """
    from Tracker.models import Parts, PartsStatus

    with transaction.atomic():
        part = Parts.objects.select_for_update().get(pk=part.id)
        if not part.split_from_lot:
            # Not split (or already rejoined) — nothing to do.
            return RejoinResult(part_id=str(part.id), rejoined=False,
                                prior_reason=part.lot_split_reason or None)

        # You rejoin where your siblings are: require at least one other schedulable
        # part of this WO sitting at the same step. Terminal/unschedulable statuses
        # (scrapped, shipped, quarantined, …) aren't a cohort to rejoin.
        _terminal = {
            PartsStatus.SCRAPPED, PartsStatus.CANCELLED, PartsStatus.SHIPPED,
            PartsStatus.IN_STOCK, PartsStatus.AWAITING_PICKUP, PartsStatus.QUARANTINED,
            PartsStatus.COMPLETED, PartsStatus.CORE_BANKED,
        }
        has_sibling = (
            Parts.objects.filter(work_order_id=part.work_order_id, step_id=part.step_id)
            .exclude(pk=part.id)
            .exclude(part_status__in=[s.value for s in _terminal])
            .exists()
        )
        if not has_sibling:
            raise ValidationError(
                "Cannot rejoin: no cohort siblings sit at this part's current step. "
                "A part rejoins its lot only once it has caught back up to where its "
                "siblings are."
            )

        prior_reason = part.lot_split_reason or None
        part.split_from_lot = False   # re-enters cohort gating
        part.rejoined_at = timezone.now()
        # NB: lot_split_reason / lot_split_at are deliberately KEPT as the genealogy record.
        part.save(update_fields=['split_from_lot', 'rejoined_at'])

        logger.info(
            "Part %s rejoined cohort at step %s (prior split reason=%s, by=%s)",
            part.id, part.step_id, prior_reason, user.id,
        )

        # Cohort grew — re-evaluate advancement for the reunited lot in the same
        # request so the reunion (and any now-unblocked advance) is reflected inline.
        if part.work_order_id and part.step_id:
            from Tracker.services.mes.advancement import try_advance_lot
            try_advance_lot(
                work_order_id=str(part.work_order_id),
                step_id=str(part.step_id),
                tenant_id=str(part.tenant_id),
                operator=user,
            )

    return RejoinResult(part_id=str(part.id), rejoined=True, prior_reason=prior_reason)
