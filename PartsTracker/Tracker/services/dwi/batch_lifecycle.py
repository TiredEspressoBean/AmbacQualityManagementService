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


@dataclass(frozen=True)
class SealResult:
    batch_id: str
    sealed_at: str
    problems: list[str]


def seal_batch(*, batch: "BatchExecution", user: "User") -> SealResult:
    """Seal a BatchExecution and trigger advancement retry. Raises
    ValidationError if the batch isn't ready to seal (missing
    completions, foreign parts, empty)."""
    from Tracker.models import Substep, SubstepCompletion, SubstepScope

    if batch.sealed_at is not None:
        return SealResult(
            batch_id=str(batch.id),
            sealed_at=batch.sealed_at.isoformat(),
            problems=[],
        )

    problems: list[str] = []
    parts = list(batch.parts.all())
    if not parts:
        problems.append("Batch has no parts.")

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

    with transaction.atomic():
        batch.sealed_at = timezone.now()
        batch.save(update_fields=['sealed_at'])
        logger.info("BatchExecution %s sealed by user %s", batch.id, user.id)

        # Seal IS the cohort's "Complete step" — synchronously run the
        # advancement gate in the same request. The cohort's BATCH
        # substep just got satisfied; member parts may now be ready.
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
