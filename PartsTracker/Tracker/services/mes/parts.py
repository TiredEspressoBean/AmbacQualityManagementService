"""
Parts aggregate services.

State-machine operations for the Parts model. Model methods delegate here
so step advancement, rollback, and work-order cascade logic live in one place.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from Tracker.models.mes_lite import (
    EdgeType,
    Parts,
    PartsStatus,
    StepEdge,
    StepExecution,
    WorkOrderStatus,
)
from Tracker.services.mes.sampling_applier import SamplingFallbackApplier


@dataclass(frozen=True)
class BulkResult:
    id: UUID
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict:
        d = {"id": str(self.id), "ok": self.ok}
        if self.error is not None:
            d["error"] = self.error
        return d


def _get_operator_for_step(part: Parts, step, previous_operator):
    """
    Determine operator assignment based on step's revisit_assignment rule.
    Returns User or None (unassigned, anyone can pick up).
    """
    if step.revisit_assignment == 'same':
        return previous_operator
    elif step.revisit_assignment in ('different', 'role'):
        return None
    else:  # 'any'
        return None


def _cascade_work_order_completion(part: Parts) -> None:
    """
    Check if all parts in work order have reached terminal status.
    If so, auto-complete the WorkOrder.

    Called after a part reaches a terminal step.
    """
    wo = part.work_order
    if not wo:
        return

    terminal_statuses = [
        PartsStatus.COMPLETED,
        PartsStatus.SCRAPPED,
        PartsStatus.CANCELLED,
    ]

    non_terminal_parts = wo.parts.exclude(part_status__in=terminal_statuses)
    if non_terminal_parts.exists():
        return

    all_parts_count = wo.parts.count()
    scrapped_count = wo.parts.filter(part_status=PartsStatus.SCRAPPED).count()

    if scrapped_count == all_parts_count:
        wo.workorder_status = WorkOrderStatus.CANCELLED
    else:
        wo.workorder_status = WorkOrderStatus.COMPLETED

    wo.true_completion = timezone.now().date()
    wo.save(update_fields=['workorder_status', 'true_completion'])


def advance_part_step(part: Parts, operator=None, decision_result=None) -> str:
    """
    Advance part to next step using workflow engine logic.

    Supports:
    - Linear flow (legacy order+1)
    - Decision branching (qa_result, measurement, manual)
    - Cycle limits with escalation
    - StepExecution lifecycle tracking
    - Batch advancement for work orders

    Args:
        part: Parts instance to advance.
        operator: User who performed the transition. If None, logged as system/automated.
        decision_result: For decision points — 'PASS', 'FAIL', 'DEFAULT', 'ALTERNATE',
            or a measurement value.

    Returns:
        "completed"    — terminal/final step reached
        "marked_ready" — waiting for other parts in batch
        "advanced"     — step advanced
        "escalated"    — routed to escalation due to cycle limit

    Raises:
        ValueError: If step advancement is blocked by validation requirements.
    """
    from Tracker.models.qms import StepTransitionLog

    if not part.step or not part.part_type:
        raise ValueError("Current step or part type is missing.")

    current_execution = StepExecution.get_current_execution(part)

    if current_execution and part.work_order:
        can_advance, blockers = part.step.can_advance_from_step(
            current_execution,
            part.work_order,
        )
        if not can_advance:
            raise ValueError(f"Cannot advance: {', '.join(blockers)}")

    if current_execution:
        current_execution.exited_at = timezone.now()
        current_execution.completed_by = operator
        current_execution.status = 'COMPLETED'
        current_execution.decision_result = str(decision_result) if decision_result else ''

    next_step = part.get_next_step(decision_result)

    if next_step is None:
        if part.step.is_terminal:
            status_map = {
                'completed': PartsStatus.COMPLETED,
                'shipped': PartsStatus.SHIPPED,
                'stock': PartsStatus.IN_STOCK,
                'scrapped': PartsStatus.SCRAPPED,
                'returned': PartsStatus.CANCELLED,
                'awaiting_pickup': PartsStatus.AWAITING_PICKUP,
                'core_banked': PartsStatus.CORE_BANKED,
                'rma_closed': PartsStatus.RMA_CLOSED,
            }
            part.part_status = status_map.get(
                part.step.terminal_status,
                PartsStatus.COMPLETED,
            )
        else:
            part.part_status = PartsStatus.COMPLETED

        if current_execution:
            current_execution.save()

        part.save()

        StepTransitionLog.objects.create(part=part, step=part.step, operator=operator)

        _cascade_work_order_completion(part)

        return "completed"

    # Check if next step is via an alternate or escalation edge
    was_escalated = False
    if part.step.is_decision_point or part.step.max_visits:
        process = part.work_order.process if part.work_order else None
        if process:
            alt_edge = StepEdge.objects.filter(
                process=process, from_step=part.step, edge_type=EdgeType.ALTERNATE
            ).first()
            esc_edge = StepEdge.objects.filter(
                process=process, from_step=part.step, edge_type=EdgeType.ESCALATION
            ).first()
            was_escalated = (
                (alt_edge and alt_edge.to_step == next_step) or
                (esc_edge and esc_edge.to_step == next_step)
            )

    if current_execution:
        current_execution.next_step = next_step
        current_execution.save()

    if part.work_order and getattr(part.step, 'requires_batch_completion', False):
        part.part_status = PartsStatus.READY_FOR_NEXT_STEP
        part.save()

        other_parts_pending = Parts.objects.filter(
            work_order=part.work_order,
            part_type=part.part_type,
            step=part.step,
        ).exclude(part_status=PartsStatus.READY_FOR_NEXT_STEP)

        if other_parts_pending.exists():
            return "marked_ready"

        if hasattr(part.step, 'can_advance_step') and not part.step.can_advance_step(
            work_order=part.work_order, step=part.step
        ):
            return "marked_ready"

        ready_parts = list(Parts.objects.filter(
            work_order=part.work_order,
            part_type=part.part_type,
            step=part.step,
            part_status=PartsStatus.READY_FOR_NEXT_STEP,
        ))

        transition_logs = []
        step_executions = []

        for p in ready_parts:
            p.step = next_step
            p.part_status = PartsStatus.IN_PROGRESS
            evaluator = SamplingFallbackApplier(part=p)
            result = evaluator.evaluate()
            p.requires_sampling = result.get("requires_sampling", False)
            p.sampling_rule = result.get("rule")
            p.sampling_ruleset = result.get("ruleset")
            p.sampling_context = result.get("context", {})

            transition_logs.append(StepTransitionLog(part=p, step=next_step, operator=operator))

            visit_number = StepExecution.get_visit_count(p, next_step) + 1
            assigned_operator = _get_operator_for_step(p, next_step, operator)
            step_executions.append(StepExecution(
                part=p,
                step=next_step,
                visit_number=visit_number,
                assigned_to=assigned_operator,
                status='PENDING',
            ))

        Parts.objects.bulk_update(ready_parts, [
            "step", "part_status", "requires_sampling",
            "sampling_rule", "sampling_ruleset", "sampling_context",
        ])

        StepTransitionLog.objects.bulk_create(transition_logs)
        StepExecution.objects.bulk_create(step_executions)

        return "escalated" if was_escalated else "advanced"

    # Individual part advancement
    visit_number = StepExecution.get_visit_count(part, next_step) + 1
    assigned_operator = _get_operator_for_step(part, next_step, operator)

    StepExecution.objects.create(
        part=part,
        step=next_step,
        visit_number=visit_number,
        assigned_to=assigned_operator,
        status='PENDING',
    )

    part.step = next_step
    part.part_status = PartsStatus.IN_PROGRESS

    evaluator = SamplingFallbackApplier(part=part)
    result = evaluator.evaluate()
    part.requires_sampling = result.get("requires_sampling", False)
    part.sampling_rule = result.get("rule")
    part.sampling_ruleset = result.get("ruleset")
    part.sampling_context = result.get("context", {})
    part.save()

    StepTransitionLog.objects.create(part=part, step=next_step, operator=operator)

    return "escalated" if was_escalated else "advanced"


def rollback_part_step(
    part: Parts,
    operator,
    reason: str | None = None,
    override_id=None,
) -> dict:
    """
    Roll back this part to the previous step in the workflow.

    This is configurable per step via:
    - undo_window_minutes: Time window during which rollback is allowed
    - rollback_requires_approval: Whether supervisor approval is required

    Args:
        part: Parts instance to roll back.
        operator: User performing the rollback.
        reason: Justification for the rollback (required if no override).
        override_id: ID of pre-approved StepOverride (optional).

    Returns:
        dict: {
            'success': bool,
            'message': str,
            'previous_step': Steps instance if successful,
            'requires_approval': bool (if rollback needs approval)
        }

    Raises:
        ValueError: If rollback is not allowed or required data is missing.
    """
    from Tracker.models.qms import StepTransitionLog, StepOverride, OverrideStatus, BlockType

    can_rollback, message, requires_approval = part.can_rollback_step(operator)

    if not can_rollback:
        raise ValueError(f"Cannot rollback: {message}")

    current_execution = StepExecution.objects.filter(
        part=part,
        step=part.step,
        status='COMPLETED',
    ).order_by('-exited_at').first()

    previous_execution = StepExecution.objects.filter(
        part=part,
        next_step=part.step,
        status='COMPLETED',
    ).order_by('-exited_at').first()

    if not current_execution or not previous_execution:
        raise ValueError("Cannot determine step execution history for rollback")

    previous_step = previous_execution.step

    if requires_approval:
        if override_id:
            try:
                override = StepOverride.objects.get(
                    id=override_id,
                    step_execution=current_execution,
                    block_type=BlockType.ROLLBACK,
                    status=OverrideStatus.APPROVED,
                    used=False,
                )
                if override.expires_at and override.expires_at < timezone.now():
                    raise ValueError("Rollback approval has expired")

                override.used = True
                override.used_at = timezone.now()
                override.save(update_fields=['used', 'used_at'])

            except StepOverride.DoesNotExist:
                raise ValueError("Invalid or expired rollback override")
        else:
            if not reason or len(reason.strip()) < 10:
                raise ValueError(
                    "Reason required for rollback approval request (minimum 10 characters)"
                )

            override_expiry_hours = getattr(part.step, 'override_expiry_hours', 24)
            expires_at = timezone.now() + timezone.timedelta(hours=override_expiry_hours)

            StepOverride.objects.create(
                step_execution=current_execution,
                block_type=BlockType.ROLLBACK,
                requested_by=operator,
                reason=reason,
                status=OverrideStatus.PENDING,
                expires_at=expires_at,
            )

            return {
                'success': False,
                'message': 'Rollback request submitted for approval',
                'requires_approval': True,
                'previous_step': previous_step,
            }

    # Perform the rollback
    current_execution.status = 'ROLLED_BACK'
    current_execution.save(update_fields=['status'])

    visit_number = StepExecution.get_visit_count(part, previous_step) + 1
    StepExecution.objects.create(
        part=part,
        step=previous_step,
        visit_number=visit_number,
        assigned_to=operator,
        status='IN_PROGRESS',
        started_at=timezone.now(),
    )

    old_step = part.step
    part.step = previous_step
    part.part_status = PartsStatus.IN_PROGRESS

    evaluator = SamplingFallbackApplier(part=part)
    result = evaluator.evaluate()
    part.requires_sampling = result.get("requires_sampling", False)
    part.sampling_rule = result.get("rule")
    part.sampling_ruleset = result.get("ruleset")
    part.sampling_context = result.get("context", {})

    part.save()

    StepTransitionLog.objects.create(
        part=part,
        step=previous_step,
        operator=operator,
    )

    return {
        'success': True,
        'message': f'Rolled back from "{old_step.name}" to "{previous_step.name}"',
        'previous_step': previous_step,
        'requires_approval': False,
    }


TERMINAL_PART_STATUSES = frozenset([
    PartsStatus.COMPLETED,
    PartsStatus.SCRAPPED,
    PartsStatus.CANCELLED,
    PartsStatus.SHIPPED,
    PartsStatus.IN_STOCK,
    PartsStatus.AWAITING_PICKUP,
    PartsStatus.CORE_BANKED,
    PartsStatus.RMA_CLOSED,
])


def _load_parts_scoped(tenant_id, part_ids: list) -> dict:
    """Fetch parts for the given tenant, keyed by id. Missing ids are absent."""
    qs = Parts.unscoped.filter(tenant_id=tenant_id, id__in=part_ids)
    return {p.id: p for p in qs}


def bulk_increment(tenant_id, part_ids: list, operator) -> list[BulkResult]:
    """Advance each listed part one step. Per-id errors are captured, not raised."""
    results: list[BulkResult] = []
    parts = _load_parts_scoped(tenant_id, part_ids)
    with transaction.atomic():
        for pid in part_ids:
            part = parts.get(pid)
            if part is None:
                results.append(BulkResult(id=pid, ok=False, error="Part not found"))
                continue
            sid = transaction.savepoint()
            try:
                advance_part_step(part, operator=operator, decision_result=None)
                transaction.savepoint_commit(sid)
                results.append(BulkResult(id=pid, ok=True))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=pid, ok=False, error=str(exc)))
    return results


def bulk_rollback(
    tenant_id,
    part_ids: list,
    operator,
    reason: str = "",
    override_id=None,
) -> list[BulkResult]:
    """Rollback each listed part one step. Parts needing approval are reported as not ok."""
    results: list[BulkResult] = []
    parts = _load_parts_scoped(tenant_id, part_ids)
    with transaction.atomic():
        for pid in part_ids:
            part = parts.get(pid)
            if part is None:
                results.append(BulkResult(id=pid, ok=False, error="Part not found"))
                continue
            sid = transaction.savepoint()
            try:
                result = rollback_part_step(
                    part, operator=operator, reason=reason, override_id=override_id,
                )
                if result.get('success'):
                    transaction.savepoint_commit(sid)
                    results.append(BulkResult(id=pid, ok=True))
                else:
                    transaction.savepoint_commit(sid)
                    results.append(BulkResult(
                        id=pid, ok=False,
                        error=result.get('message') or "Rollback requires approval",
                    ))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=pid, ok=False, error=str(exc)))
    return results


def bulk_set_status(
    tenant_id,
    part_ids: list,
    new_status: str,
    operator,
    reason: str | None = None,
) -> list[BulkResult]:
    """Directly set part_status on each listed part. Cascades WO completion on terminal transitions."""
    if new_status not in PartsStatus.values:
        raise ValueError(f"Invalid part status: {new_status}")

    results: list[BulkResult] = []
    parts = _load_parts_scoped(tenant_id, part_ids)
    with transaction.atomic():
        for pid in part_ids:
            part = parts.get(pid)
            if part is None:
                results.append(BulkResult(id=pid, ok=False, error="Part not found"))
                continue
            sid = transaction.savepoint()
            try:
                part.part_status = new_status
                part.save(update_fields=['part_status', 'updated_at'])
                if new_status in TERMINAL_PART_STATUSES:
                    _cascade_work_order_completion(part)
                transaction.savepoint_commit(sid)
                results.append(BulkResult(id=pid, ok=True))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=pid, ok=False, error=str(exc)))
    return results
