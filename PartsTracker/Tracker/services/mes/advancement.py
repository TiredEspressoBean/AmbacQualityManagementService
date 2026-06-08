"""
Lot-cohesion advancement engine.

`try_advance_lot(work_order_id, step_id)` is the new public surface for
moving parts forward. It's idempotent and fired reactively from every
state-changing event (substep completion, batch seal, part split,
override approval). The legacy `advance_part_step(part)` stays as the
private helper that actually performs per-part advancement; this engine
sequences cohort-vs-split decisions on top of it.

Lot-cohesion rule: non-split parts at the same (WorkOrder, Step) advance
together or not at all. Split parts at the same (WO, Step) each advance
solo when their own gate clears. The two paths are evaluated
independently in one engine call.

Design reference: `scratch_advancement_gate.py` (all 28 cases) and
`Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.db import transaction

from Tracker.utils.tenant_context import tenant_context

if TYPE_CHECKING:
    from Tracker.models import Parts, Steps, WorkOrder

logger = logging.getLogger(__name__)


@dataclass
class LotAdvanceResult:
    status: str  # 'advanced' | 'blocked' | 'noop' | 'halted'
    reason: str = ''
    parts_advanced: list[str] = field(default_factory=list)
    blockers_by_part: dict[str, list[str]] = field(default_factory=dict)
    split_parts_advanced: list[str] = field(default_factory=list)
    split_parts_blocked: dict[str, list[str]] = field(default_factory=dict)


_MAX_CASCADE_DEPTH = 10


def try_advance_lot(
    *,
    work_order_id: str,
    step_id: str,
    tenant_id: str,
    operator=None,
    _depth: int = 0,
) -> LotAdvanceResult:
    """Idempotent advancement attempt for the lot at (work_order, step).

    Synchronous. Handles both the cohort (non-split parts at this WO+step,
    advanced all-or-none) and split parts at the same (WO, step) (each
    evaluated individually).

    Bounded synchronous cascade: after a successful cohort advance, if
    the next step has no substeps and isn't terminal, recurse to advance
    further in the same request. Cap at `_MAX_CASCADE_DEPTH` to prevent
    runaway in a misconfigured process flow. This lets pass-through
    steps (release-to-next-station, in-transit, etc.) advance without
    requiring a separate operator action.

    Safe to call multiple times; no-op when the lot has already moved
    or no parts are present.
    """
    from Tracker.models import Steps, WorkOrder, WorkOrderStatus

    with tenant_context(tenant_id):
        try:
            wo = WorkOrder.objects.get(id=work_order_id)
        except WorkOrder.DoesNotExist:
            return LotAdvanceResult(status='noop', reason='work_order_not_found')

        if wo.workorder_status not in (
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.PENDING,
            WorkOrderStatus.WAITING_FOR_OPERATOR,
        ):
            return LotAdvanceResult(
                status='halted',
                reason=f"workorder_status={wo.workorder_status}",
            )

        try:
            step = Steps.objects.get(id=step_id)
        except Steps.DoesNotExist:
            return LotAdvanceResult(status='noop', reason='step_not_found')

        result = _evaluate_and_advance(wo=wo, step=step, operator=operator)

        # Bounded synchronous cascade: if the cohort advanced, walk
        # forward through any pass-through steps until we hit one that
        # needs operator work. Each iteration runs the full gate; the
        # cascade halts naturally when blockers appear.
        if (
            result.status == 'advanced'
            and result.parts_advanced
            and _depth < _MAX_CASCADE_DEPTH
        ):
            from Tracker.models import Parts
            # All advanced parts moved to the same next step (cohort
            # all-or-none). Pick any one to find the new step id.
            advanced_part = Parts.objects.filter(
                id=result.parts_advanced[0]
            ).first()
            if advanced_part and advanced_part.step_id:
                next_result = try_advance_lot(
                    work_order_id=work_order_id,
                    step_id=str(advanced_part.step_id),
                    tenant_id=tenant_id,
                    operator=operator,
                    _depth=_depth + 1,
                )
                if next_result.status == 'advanced':
                    # Accumulate the cascaded advances into the original
                    # result so the caller sees the full walk.
                    result.parts_advanced = list(
                        set(result.parts_advanced) | set(next_result.parts_advanced)
                    )

        return result


def _evaluate_and_advance(
    *,
    wo: "WorkOrder",
    step: "Steps",
    operator,
) -> LotAdvanceResult:
    from Tracker.models import Parts
    from Tracker.services.mes.parts import advance_part_step

    parts_at_step = list(
        Parts.objects.filter(work_order=wo, step=step).select_related('step')
    )
    if not parts_at_step:
        return LotAdvanceResult(status='noop', reason='no_parts_at_step')

    cohort = [p for p in parts_at_step if not p.split_from_cohort]
    split_parts = [p for p in parts_at_step if p.split_from_cohort]

    result = LotAdvanceResult(status='noop')

    # ----- Cohort path: all-or-none -----
    if cohort:
        per_part_blockers: dict[str, list[str]] = {}
        from Tracker.models import StepExecution
        for p in cohort:
            se = StepExecution.get_current_execution(p)
            if se is None:
                per_part_blockers[str(p.id)] = ['No active StepExecution']
                continue
            can_advance, blockers = step.can_advance_from_step(se, wo)
            if not can_advance:
                per_part_blockers[str(p.id)] = blockers

        if per_part_blockers:
            result.status = 'blocked'
            result.blockers_by_part = per_part_blockers
        else:
            with transaction.atomic():
                for p in cohort:
                    advance_part_step(p, operator=operator)
                    result.parts_advanced.append(str(p.id))
            result.status = 'advanced'

    # ----- Split path: each part evaluated solo -----
    for p in split_parts:
        from Tracker.models import StepExecution
        se = StepExecution.get_current_execution(p)
        if se is None:
            result.split_parts_blocked[str(p.id)] = ['No active StepExecution']
            continue
        can_advance, blockers = step.can_advance_from_step(se, wo)
        if not can_advance:
            result.split_parts_blocked[str(p.id)] = blockers
            continue
        try:
            with transaction.atomic():
                advance_part_step(p, operator=operator)
            result.split_parts_advanced.append(str(p.id))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Split-part advance failed for %s: %s", p.id, exc)
            result.split_parts_blocked[str(p.id)] = [str(exc)]

    # Status disambiguation when both paths were tried.
    if result.status == 'noop':
        if result.split_parts_advanced:
            result.status = 'advanced'
        elif result.split_parts_blocked:
            result.status = 'blocked'

    return result
