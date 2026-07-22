"""
BatchExecution lifecycle service.

Today the model has `sealed_at` but no service writes to it. This module
is the only sanctioned write path for sealing a batch. Sealing:

  1. Validates every required BATCH-scope substep has a non-voided
     SubstepCompletion on this batch.
  2. Validates membership integrity (all parts share the batch's WO —
     multi-WO batches are modeled as one BatchExecution per WO, see
     `scratch_advancement_gate.py` case 9).
  3. Stamps `sealed_at = now()`.
  4. Fires the advancement retry task for the (WO, Step) the batch
     covers, since every member part may now be ready to advance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from Tracker.models import BatchExecution, User


logger = logging.getLogger(__name__)

# Cohorts at or below this size advance synchronously in the seal request so
# the operator sees the move immediately; larger cohorts defer advancement to
# Celery (3d) to keep the seal request bounded.
ASYNC_ADVANCE_THRESHOLD = 50


@dataclass(frozen=True)
class SealResult:
    batch_id: str
    sealed_at: str
    problems: list[str]


def assert_no_open_batch_overlap(*, step, parts) -> None:
    """3c — disjoint-membership invariant for open batches.

    A part may be a member of at most one OPEN (unsealed) batch at a given
    step. Multiple concurrent open batches per (WO, step) are allowed — a
    fixed-capacity op (furnace/wash/autoclave) legitimately splits one lot
    into several loads — but their membership must be disjoint, else it's
    ambiguous which load's cycle data covers the part.

    Sealed batches don't count: once a load is sealed its parts have their
    capture recorded, so a part may later join a new batch (rare, but valid).

    Raises ValidationError naming the overlapping part count.
    """
    from Tracker.models import BatchExecution

    part_ids = [getattr(p, 'id', p) for p in parts]
    if not part_ids:
        return
    in_open_batch = set(
        BatchExecution.objects.filter(
            step=step, sealed_at__isnull=True, parts__id__in=part_ids,
        ).values_list('parts__id', flat=True)
    )
    overlapping = in_open_batch & set(part_ids)
    if overlapping:
        raise ValidationError(
            f"{len(overlapping)} selected part(s) are already in an open batch "
            "at this step. Seal or finish that batch before starting another."
        )


def seal_batch(*, batch: "BatchExecution", user: "User") -> SealResult:
    """Seal a BatchExecution and trigger advancement retry. Raises
    ValidationError if the batch isn't ready to seal (missing
    completions, foreign parts, empty)."""
    from Tracker.models import BatchExecution, Substep, SubstepCompletion, SubstepScope
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

    # One transaction holds a row lock on the batch across the whole check →
    # validate → seal → fire-advancement sequence, so two concurrent seals
    # can't both pass the already-sealed check, double-stamp sealed_at, and
    # double-fire advancement. The second seal blocks on the lock, then sees
    # sealed_at set and returns the idempotent result.
    with transaction.atomic():
        batch = BatchExecution.objects.select_for_update().get(pk=batch.id)

        if batch.sealed_at is not None:
            return SealResult(
                batch_id=str(batch.id),
                sealed_at=batch.sealed_at.isoformat(),
                problems=[],
            )

        problems: list[str] = []
        members = list(batch.parts.all())

        # 3c — membership reconciliation: a member that went terminal
        # (scrapped/cancelled) after batch start is no longer a live cohort
        # member. Drop it from the batch so seal doesn't validate against — or
        # later try to advance — a dead part. Split parts stay (Case-19: the
        # batch substep still covers a split-out part's operation).
        dropped = [p for p in members if p.part_status in TERMINAL_PART_STATUSES]
        if dropped:
            batch.parts.remove(*dropped)
            logger.info(
                "Seal reconcile: dropped %d terminal part(s) from batch %s: %s",
                len(dropped), batch.id, [str(p.id) for p in dropped],
            )
        parts = [p for p in members if p.part_status not in TERMINAL_PART_STATUSES]

        if not parts:
            problems.append("Batch has no live parts (all members are scrapped/cancelled).")

        foreign = [p for p in parts if p.work_order_id != batch.work_order_id]
        if foreign:
            problems.append(
                f"Batch contains parts from other WOs: {[str(p.id) for p in foreign]}. "
                "One BatchExecution per WO is invariant."
            )

        required_subs = list(
            Substep.objects.filter(
                step_id=batch.step_id,
                scope=SubstepScope.BATCH,
                is_optional=False,
                archived=False,
            )
        )
        if required_subs:
            completed_ids = set(
                SubstepCompletion.objects.filter(
                    batch_execution_id=batch.id,
                    substep_id__in=[s.id for s in required_subs],
                    is_voided=False,
                ).values_list('substep_id', flat=True)
            )
            for s in required_subs:
                if s.id not in completed_ids:
                    problems.append(
                        f"Batch substep '{s.title}' has no completion on this batch."
                    )

        if problems:
            raise ValidationError(problems)

        batch.sealed_at = timezone.now()
        batch.save(update_fields=['sealed_at'])
        logger.info("BatchExecution %s sealed by user %s", batch.id, user.id)

        # Seal IS the cohort's "Complete step" — the BATCH substep just got
        # satisfied, so member parts may now be ready to advance.
        #
        # Small cohorts advance synchronously so the operator sees the move
        # immediately. Large cohorts (3d) would make the seal request gate +
        # advance hundreds of parts inline and risk a timeout, so dispatch the
        # advancement to Celery after commit; the batch is sealed regardless.
        if len(parts) > ASYNC_ADVANCE_THRESHOLD:
            from Tracker.tasks import advance_lot_task
            wo_id = str(batch.work_order_id)
            step_id = str(batch.step_id)
            tenant_id = str(batch.tenant_id)
            operator_id = getattr(user, 'id', None)
            transaction.on_commit(
                lambda: advance_lot_task.delay(
                    work_order_id=wo_id,
                    step_id=step_id,
                    tenant_id=tenant_id,
                    operator_id=operator_id,
                )
            )
            logger.info(
                "Batch %s seal: %d-part cohort - advancement dispatched async.",
                batch.id, len(parts),
            )
        else:
            from Tracker.services.mes.advancement import try_advance_lot
            try_advance_lot(
                work_order_id=str(batch.work_order_id),
                step_id=str(batch.step_id),
                tenant_id=str(batch.tenant_id),
                operator=user,
            )

    return SealResult(
        batch_id=str(batch.id),
        sealed_at=batch.sealed_at.isoformat(),
        problems=[],
    )
