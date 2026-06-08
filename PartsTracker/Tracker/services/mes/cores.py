"""
Core aggregate workflow services.

Mirrors `services/mes/parts.py` for the teardown side. State-machine operations
for routing a Core through teardown Steps. Parts and Cores diverge in places
(sampling, FPI, ITAR are Parts-only; condition grading is Core-only), so
sibling services rather than a shared abstraction.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from Tracker.models import Core
from Tracker.models.mes_lite import (
    EdgeType,
    StepEdge,
    StepExecution,
    WorkOrderStatus,
)


def _start_disassembly_if_needed(core: Core, operator) -> None:
    """If Core is RECEIVED, transition to IN_DISASSEMBLY (R5 auto-coordination)."""
    if core.status == 'RECEIVED':
        from Tracker.services.reman.core import start_core_disassembly
        start_core_disassembly(core, operator)


def _complete_disassembly_if_needed(core: Core, operator) -> None:
    """If Core is IN_DISASSEMBLY, transition to DISASSEMBLED (R5 auto-coordination)."""
    if core.status == 'IN_DISASSEMBLY':
        from Tracker.services.reman.core import complete_core_disassembly
        complete_core_disassembly(core, operator)


@transaction.atomic
def advance_core_step(core: Core, operator=None, decision_result=None) -> str:
    """Advance a Core to the next teardown Step.

    Mirrors `advance_part_step` for Cores. Auto-coordinates Core lifecycle (R5):
    - When the first teardown StepExecution is created and Core is RECEIVED,
      transitions Core → IN_DISASSEMBLY.
    - When the terminal teardown Step completes, transitions Core → DISASSEMBLED
      (unless already SCRAPPED).

    Args:
        core: Core to advance.
        operator: User performing the transition. None = system/automated.
        decision_result: For decision points — 'PASS'/'FAIL'/'DEFAULT'/'ALTERNATE'
            or a measurement value.

    Returns:
        "completed"  — terminal step reached, Core now DISASSEMBLED
        "advanced"   — Core moved to next step
        "escalated"  — routed via ESCALATION edge (max_visits exceeded or alt path)

    Raises:
        ValueError: when validation fails (no step set, advancement blocked).
    """
    from Tracker.models.qms import StepTransitionLog

    if not core.step or not core.core_type:
        raise ValueError("Current step or core type is missing.")

    work_order = core.work_order

    current_execution = (
        StepExecution.objects.filter(core=core, exited_at__isnull=True).first()  # tenant-safe: scoped by `core` FK
    )

    if current_execution and work_order:
        can_advance, blockers = core.step.can_advance_from_step(
            current_execution,
            work_order,
        )
        if not can_advance:
            raise ValueError(f"Cannot advance: {', '.join(blockers)}")

    if current_execution:
        current_execution.exited_at = timezone.now()
        current_execution.completed_by = operator
        current_execution.status = 'COMPLETED'
        current_execution.decision_result = str(decision_result) if decision_result else ''

    next_step = core.get_next_step(decision_result)

    if next_step is None:
        if current_execution:
            current_execution.save()

        # Reached terminal Step — auto-complete disassembly via R5 hook.
        _complete_disassembly_if_needed(core, operator)

        StepTransitionLog.objects.create(core=core, step=core.step, operator=operator)
        _cascade_work_order_completion_for_core(core)
        return "completed"

    # Determine if next step is via ALTERNATE / ESCALATION edge (for return value)
    was_escalated = False
    if core.step.is_decision_point or core.step.max_visits:
        process = core.process
        if process:
            alt_edge = StepEdge.objects.filter(
                process=process, from_step=core.step, edge_type=EdgeType.ALTERNATE
            ).first()
            esc_edge = StepEdge.objects.filter(
                process=process, from_step=core.step, edge_type=EdgeType.ESCALATION
            ).first()
            was_escalated = (
                (alt_edge and alt_edge.to_step == next_step)
                or (esc_edge and esc_edge.to_step == next_step)
            )

    if current_execution:
        current_execution.next_step = next_step
        current_execution.save()

    # First teardown StepExecution — auto-start disassembly via R5 hook.
    _start_disassembly_if_needed(core, operator)

    visit_number = StepExecution.objects.filter(core=core, step=next_step).count() + 1  # tenant-safe: scoped by `core` FK
    StepExecution.objects.create(
        core=core,
        step=next_step,
        visit_number=visit_number,
        status='PENDING',
    )

    core.step = next_step
    core.save(update_fields=['step'])

    StepTransitionLog.objects.create(core=core, step=next_step, operator=operator)

    return "escalated" if was_escalated else "advanced"


def _cascade_work_order_completion_for_core(core: Core) -> None:
    """Thin wrapper — delegates to the unified cascade in `services.mes.parts`.

    The cascade itself is subject-aware (Parts AND Cores); this exists so
    Core-side call sites have a symmetric entry point.
    """
    from Tracker.services.mes.parts import _cascade_work_order_completion_for_subject
    _cascade_work_order_completion_for_subject(core.work_order)


def begin_core_step_execution(step_execution: StepExecution, operator=None) -> StepExecution:
    """Transition a Core's StepExecution from PENDING/CLAIMED to IN_PROGRESS.

    Fires the R5 auto-coordination hook: if this is the first teardown
    StepExecution actually started for a Core (Core is RECEIVED), transitions
    Core → IN_DISASSEMBLY.

    Idempotent: if already IN_PROGRESS, this is a no-op.
    """
    if step_execution.core_id is None:
        raise ValueError("begin_core_step_execution called with a Parts execution")

    if step_execution.status == 'IN_PROGRESS':
        return step_execution

    step_execution.status = 'IN_PROGRESS'
    step_execution.started_at = timezone.now()
    if operator is not None and step_execution.assigned_to_id is None:
        step_execution.assigned_to = operator
    step_execution.save(update_fields=['status', 'started_at', 'assigned_to'])

    _start_disassembly_if_needed(step_execution.core, operator)
    return step_execution
