"""
WorkOrder aggregate services.

Functions:
- `create_parts_batch` — idempotent bulk part creation with sampling eval.
- `cascade_order_status` — auto-complete parent Order when all WOs are done.
- `cascade_schedule_slots` — mark ScheduleSlots completed when WO completes.
- `apply_calibration_result_to_equipment` — update equipment status from a
  CalibrationRecord result (lives here because Equipments is an MES model).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from django.db import IntegrityError

from Tracker.models import (
    Parts, PartsStatus, WorkOrder, WorkOrderHold, WorkOrderHoldReason,
    WorkOrderSplitReason, WorkOrderStatus, OrdersStatus, ScheduleSlot,
)

logger = logging.getLogger(__name__)


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


def create_parts_batch(
    work_order: WorkOrder,
    part_type,
    step,
    quantity: int | None = None,
    erp_id_start: int = 1,
    part_status: str = PartsStatus.PENDING,
) -> list:
    """Create parts for this work order idempotently and evaluate sampling.

    ERP_id pattern: `{work_order.ERP_id}-{part_type.ID_prefix}{seq:04d}`,
    where `seq` starts at `erp_id_start` and runs for `quantity` items.
    Running the service twice with overlapping ranges won't duplicate
    parts — already-present ERP_ids are skipped.

    Returns the full set of parts for (work_order, part_type, step) —
    existing + newly created.
    """
    quantity = quantity or work_order.quantity

    existing_erp_ids = set(
        Parts.objects.filter(work_order=work_order)
        .values_list('ERP_id', flat=True)
    )

    parts_to_create = []
    for i in range(quantity):
        erp_id = f"{work_order.ERP_id}-{part_type.ID_prefix or 'P'}{erp_id_start + i:04d}"
        if erp_id not in existing_erp_ids:
            parts_to_create.append(Parts(
                tenant=work_order.tenant,
                work_order=work_order,
                part_type=part_type,
                step=step,
                ERP_id=erp_id,
                part_status=part_status,
            ))

    if parts_to_create:
        Parts.objects.bulk_create(parts_to_create)

    fresh_parts = list(
        Parts.objects.filter(archived=False, work_order=work_order, part_type=part_type, step=step)
        .order_by('id')
    )

    # Delegate sampling eval to the work_order's existing helper — it's
    # also called from `_initialize_sampling`, so keeping it on the model
    # avoids a second copy of the bulk-update loop.
    work_order._bulk_evaluate_sampling(fresh_parts)

    return fresh_parts


def start_refusal(work_order) -> str | None:
    """Why work can't start on `work_order` now, naming the hold or how it ended, or
    None if it can. A held order waits for its hold to clear; an ended one takes no
    more work."""
    if work_order is None:
        return None
    status_ = work_order.workorder_status
    if status_ == WorkOrderStatus.ON_HOLD:
        hold = (WorkOrderHold.objects.filter(work_order=work_order, cleared_at__isnull=True,
                                             is_voided=False).first())
        why = ''
        if hold is not None:
            why = f" ({hold.get_reason_display()}" + (f": {hold.notes}" if hold.notes else '') + ")"
        return f"{work_order.ERP_id} is on hold{why} — clear the hold before starting work."
    if status_ == WorkOrderStatus.CANCELLED:
        return f"{work_order.ERP_id} was cancelled — it takes no more work."
    if status_ == WorkOrderStatus.COMPLETED:
        if work_order.short_closed:
            return (f"{work_order.ERP_id} was short-closed ({work_order.short_close_reason}) "
                    f"— it takes no more work.")
        return f"{work_order.ERP_id} is completed — it takes no more work."
    return None


def new_work_refusal(process) -> str | None:
    """Why new work can't be put on `process`, or None if it can (Processes.get_available
    is the same rule as a query)."""
    if process is None:
        return None
    if process.status != 'APPROVED':
        return (f"Process '{process.name}' is {process.get_status_display().upper()}, not "
                f"approved — approve it before releasing work against it.")
    if process.archived:
        return f"Process '{process.name}' v{process.version} has been superseded — use the version in force."
    if getattr(process, 'is_temporary', False):
        return ("That version is a temporary change, which applies only to the work orders "
                "its change order named. Use the current version.")
    return None


def plan_work_order(
    *,
    tenant,
    process,
    quantity: int,
    user=None,
    erp_id: str | None = None,
    priority: int | None = None,
    expected_start=None,
    expected_completion=None,
    auto_explode: bool = True,
    apply_yield: bool = False,
) -> WorkOrder:
    """Create a new work order for `process` and spawn its `quantity` parts at the
    process's first step — the scheduler's "add work" entry point.

    The WO is created PENDING (schedulable but not started) so a Solve picks it up
    immediately (the solver excludes only COMPLETED / CANCELLED / ON_HOLD). ERP_id is
    auto-generated from the process name when not supplied. Atomic: WO + parts commit
    together. Returns the created WorkOrder.

    When `auto_explode` (the default), the WO's released ASSEMBLY BOM is exploded into
    pegged in-house component WOs in the same transaction (see
    `services.mes.bom_explosion`); the resulting summary is attached as
    `wo.explosion_summary`. The explosion sets `auto_explode=False` on the child WOs it
    creates — it owns the multi-level recursion itself.
    """
    from Tracker.models import ProcessStep

    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    # Only build to an approved routing. A DRAFT process is one somebody is still
    # editing — its steps can change under a job that is already running, and releasing
    # production against an uncontrolled process is exactly what AS9100 §8.5.1 forbids.
    # `bom_explosion._build_process` already holds child components to this standard;
    # the top-level process had no such check, so the stricter rule applied to the
    # components of a job but not to the job itself.
    refusal = new_work_refusal(process)
    if refusal:
        raise ValueError(refusal)
    part_type = process.part_type
    if part_type is None:
        raise ValueError("process has no part type")

    # Yield gross-up: when apply_yield, `quantity` is the number of GOOD parts wanted; start
    # more so the route still finishes that many given expected scrap (release-11-to-ship-10).
    good_quantity = quantity
    yield_summary = None
    if apply_yield:
        from Tracker.services.mes.yield_planning import start_quantity_for_good
        started = start_quantity_for_good(process, quantity)
        if started != quantity:
            yield_summary = {'target_good': good_quantity, 'started': started}
        quantity = started
    first_ps = (
        ProcessStep.objects.filter(process=process).order_by('order').first()
    )
    if first_ps is None:
        raise ValueError("process has no steps to schedule")

    if not erp_id:
        slug = ''.join(ch for ch in (process.name or 'WO') if ch.isalnum())[:6].upper() or 'WO'
        base = f"WO-{slug}"
        n = WorkOrder.objects.filter(ERP_id__startswith=base).count() + 1
        erp_id = f"{base}-{n:03d}"

    fields = dict(
        tenant=tenant,
        ERP_id=erp_id,
        process=process,
        quantity=quantity,
        target_good_quantity=good_quantity,  # ordered good count; drives make-up planning
        workorder_status=WorkOrderStatus.PENDING,
        expected_start=expected_start,
        expected_completion=expected_completion,
    )
    if priority is not None:
        fields['priority'] = priority

    with transaction.atomic():
        # tenant-safe: `fields` sets tenant=tenant explicitly above.
        wo = WorkOrder.objects.create(**fields)
        bulk_add_parts_to_workorder(wo, part_type, first_ps.step, quantity)
        summary = None
        if auto_explode:
            from Tracker.services.mes.bom_explosion import explode_work_order
            summary = explode_work_order(wo, user=user, create=True).as_summary()
    wo.explosion_summary = summary
    wo.yield_summary = yield_summary  # {'target_good', 'started'} when yield grossed up, else None
    logger.info("Planned work order %s (%s parts on %s) by user=%s",
                wo.ERP_id, quantity, process.name, getattr(user, 'id', None))
    return wo


def reduce_work_order_quantity(work_order: WorkOrder, new_quantity: int, user=None) -> int:
    """Shrink a work order to `new_quantity` by CANCELLING its excess *unstarted* parts
    (PENDING, with no StepExecution) — never worked/terminal ones. The mirror of
    `bulk_add_parts_to_workorder`. Cancelled parts drop out of scheduling (a terminal
    status). Returns the number of parts cancelled. Raises ValueError if the reduction
    can't be met from unstarted parts.
    """
    from Tracker.models import StepExecution

    if new_quantity < 0:
        raise ValueError("quantity must be >= 0")
    live = Parts.objects.filter(archived=False, work_order=work_order).exclude(
        part_status__in=[PartsStatus.CANCELLED, PartsStatus.SCRAPPED])
    current = live.count()
    if new_quantity >= current:
        raise ValueError("new quantity is not a reduction; use bulk_add_parts to increase")
    to_remove = current - new_quantity

    worked_ids = set(
        StepExecution.objects.filter(part__work_order=work_order)
        .values_list('part_id', flat=True)
    )
    removable = [
        p for p in live.filter(part_status=PartsStatus.PENDING).order_by('-ERP_id')
        if p.id not in worked_ids
    ]
    if len(removable) < to_remove:
        raise ValueError(
            f"Can only remove {len(removable)} unstarted part(s); the rest have been "
            f"worked and can't be cancelled by a quantity change."
        )

    from Tracker.services.reman.core_part import release_from_order_if_core

    with transaction.atomic():
        for p in removable[:to_remove]:
            # A core is not cancelled — it goes back to the bank (core_part).
            if release_from_order_if_core(p):
                continue
            p.part_status = PartsStatus.CANCELLED
            p.save(update_fields=['part_status'])
        work_order.quantity = new_quantity
        work_order.save(update_fields=['quantity'])
    logger.info("Reduced WO %s to qty %s (cancelled %s unstarted parts) by user=%s",
                work_order.ERP_id, new_quantity, to_remove, getattr(user, 'id', None))
    return to_remove


def bulk_add_parts_to_workorder(
    work_order: WorkOrder,
    part_type,
    step,
    quantity: int,
    erp_id_start: int = 1,
    part_status: str = PartsStatus.PENDING,
) -> list:
    """Create N parts on `work_order` and return only the newly-created ones.

    Validates that `part_type` matches the WO's process part_type when the
    process is set. Wraps `create_parts_batch` (which is idempotent) and
    diffs the part_ids before/after to return only what was added in this
    call. Atomic via `transaction.atomic` so a failure mid-bulk rolls back
    the whole batch.
    """
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if work_order.process and work_order.process.part_type_id != part_type.id:
        raise ValueError(
            "part_type does not match the work order's process part_type"
        )

    with transaction.atomic():
        existing_ids = set(
            Parts.objects.filter(work_order=work_order).values_list('id', flat=True)
        )
        create_parts_batch(
            work_order,
            part_type,
            step,
            quantity=quantity,
            erp_id_start=erp_id_start,
            part_status=part_status,
        )
        new_parts = list(
            Parts.objects.filter(work_order=work_order)
            .exclude(id__in=existing_ids)
            .order_by('ERP_id')
        )
    return new_parts


def mark_started(work_order: WorkOrder) -> bool:
    """A work order is IN_PROGRESS once someone actually starts work on it.

    Nothing used to make this transition. Work ran perfectly well on a PENDING order
    (`try_advance_lot` accepts PENDING and IN_PROGRESS), so a job
    could be half-built and still read "Pending" on every board — and the only thing
    that moved it was a Control Center button mislabelled "Release", which flipped the
    status instead of authorizing the order.

    Status is now the FACT that work began. Authorization is `released_at` and belongs
    to `services/mes/release.py`; the two answer different questions and a planner needs
    both — released-but-not-started is exactly the queue workload control manages.

    Returns True when it moved the order. No-op for anything already past PENDING, so a
    held, cancelled or completed order is never resurrected by someone opening a step.
    """
    if work_order is None or work_order.workorder_status != WorkOrderStatus.PENDING:
        return False
    work_order.workorder_status = WorkOrderStatus.IN_PROGRESS
    work_order.save(update_fields=['workorder_status', 'updated_at'])
    return True


def cascade_order_status(work_order: WorkOrder) -> None:
    """Auto-complete the parent Order when all its WorkOrders are terminal.

    Terminal statuses are COMPLETED and CANCELLED. Called after a WorkOrder
    reaches one of those statuses. No-op when the WO has no parent order,
    when some WOs are still in progress, or when the order is already
    COMPLETED.

    **A cancelled work order ends a job; it does not fulfil an order.** Cancelling
    every WO on an order therefore leaves nothing incomplete, and this used to read
    that as "all done" and tell the customer their order was COMPLETED when nothing
    had been built. At least one WO must have actually completed.
    """
    order = work_order.related_order
    if not order:
        return

    incomplete_wos = order.related_orders.exclude(
        workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]
    )
    if incomplete_wos.exists():
        return

    if not order.related_orders.filter(
        workorder_status=WorkOrderStatus.COMPLETED
    ).exists():
        return  # every job was cancelled — the order was abandoned, not fulfilled

    if order.order_status != OrdersStatus.COMPLETED:
        order.order_status = OrdersStatus.COMPLETED
        order.save(update_fields=['order_status'])
        logger.info(
            "Order %s (%s) auto-completed: all %d work orders complete",
            order.name,
            order.id,
            order.related_orders.count(),
        )


def cascade_schedule_slots(work_order: WorkOrder) -> None:
    """Mark all open ScheduleSlots COMPLETED when a WorkOrder completes.

    Only transitions SCHEDULED or IN_PROGRESS slots; already-completed
    or cancelled slots are left untouched.
    """
    updated = ScheduleSlot.objects.filter(
        work_order=work_order,
        status__in=['SCHEDULED', 'IN_PROGRESS'],
    ).update(
        status='COMPLETED',
        actual_end=timezone.now(),
    )

    if updated > 0:
        logger.info(
            "Completed %d schedule slot(s) for WorkOrder %s",
            updated,
            work_order.ERP_id,
        )


def apply_calibration_result_to_equipment(calibration_record) -> None:
    """Update equipment status based on a CalibrationRecord result.

    FAIL  → equipment set to OUT_OF_SERVICE (if not already).
    PASS / LIMITED → equipment returned to IN_SERVICE (only when it was
        previously OUT_OF_SERVICE, to avoid clobbering other statuses).
    """
    from Tracker.models.mes_standard import EquipmentStatus

    equipment = calibration_record.equipment

    if calibration_record.result == 'FAIL':
        if equipment.status != EquipmentStatus.OUT_OF_SERVICE:
            old_status = equipment.status
            equipment.status = EquipmentStatus.OUT_OF_SERVICE
            equipment.save(update_fields=['status'])
            logger.info(
                "Equipment %s (%s) set to OUT_OF_SERVICE due to failed calibration (was: %s)",
                equipment.name,
                equipment.id,
                old_status,
            )

    elif calibration_record.result in ('PASS', 'LIMITED'):
        if equipment.status == EquipmentStatus.OUT_OF_SERVICE:
            equipment.status = EquipmentStatus.IN_SERVICE
            equipment.save(update_fields=['status'])
            logger.info(
                "Equipment %s (%s) returned to IN_SERVICE after %s calibration",
                equipment.name,
                equipment.id,
                'passing' if calibration_record.result == 'PASS' else 'limited',
            )


def change_priority(work_order: WorkOrder, new_priority: int, *, reason: str, user) -> bool:
    """Set a work order's priority, recording why.

    Expediting is a priority change — "Urgent" jumps the queue — and it is often a call
    someone is asked to justify weeks later, so like hold, scrap and reject it takes a
    reason. The reason goes on a RecordEdit (field, old, new, why, who, when) beside
    auditlog's who-and-when. Returns False when the priority is unchanged (nothing
    recorded); raises ValueError for no reason or an unknown level.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    from Tracker.models.mes_lite import WorkOrderPriority

    new_priority = int(new_priority)
    if new_priority not in WorkOrderPriority.values:
        raise ValueError(f"Unknown priority: {new_priority}")
    if new_priority == work_order.priority:
        return False
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Say why the priority is changing")
    with transaction.atomic():
        RecordEdit.objects.create(
            tenant=work_order.tenant,
            content_type=ContentType.objects.get_for_model(WorkOrder),
            object_id=work_order.id, field_name="priority",
            old_value=str(work_order.priority), new_value=str(new_priority),
            reason=reason, edited_by=user)
        work_order.priority = new_priority
        work_order.save(update_fields=["priority", "updated_at"])
    return True


def priority_changes(work_order: WorkOrder) -> list[dict]:
    """The work order's priority changes with their reasons, newest first."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    from Tracker.models.mes_lite import WorkOrderPriority

    labels = dict(WorkOrderPriority.choices)
    edits = (RecordEdit.objects  # tenant-safe: .objects auto-scopes to the request tenant
             .filter(content_type=ContentType.objects.get_for_model(WorkOrder),
                     object_id=work_order.id, field_name="priority")
             .select_related("edited_by").order_by("-edited_at"))

    def label(value):
        try:
            return labels.get(int(value), value)
        except (TypeError, ValueError):
            return value

    return [{
        "from_priority": label(e.old_value),
        "to_priority": label(e.new_value),
        "reason": e.reason,
        "changed_by": (e.edited_by.get_full_name() or e.edited_by.get_username()) if e.edited_by else None,
        "changed_at": e.edited_at,
    } for e in edits]


def place_on_hold(
    work_order: WorkOrder,
    reason: str,
    placed_by,
    notes: str = "",
    expected_clear_at=None,
) -> WorkOrderHold:
    """Open a new hold on the work order and transition WO status to ON_HOLD.

    Raises ValueError if an open hold already exists (caller should call clear_hold first).
    """
    if reason not in WorkOrderHoldReason.values:
        raise ValueError(f"Invalid hold reason: {reason}")

    if WorkOrderHold.unscoped.filter(
        tenant_id=work_order.tenant_id,
        work_order=work_order,
        cleared_at__isnull=True,
        is_voided=False,
    ).exists():
        raise ValueError("Work order already has an open hold")

    with transaction.atomic():
        try:
            hold = WorkOrderHold.objects.create(
                tenant=work_order.tenant,
                work_order=work_order,
                reason=reason,
                notes=notes,
                placed_by=placed_by,
                placed_at=timezone.now(),
                expected_clear_at=expected_clear_at,
            )
        except IntegrityError as exc:
            raise ValueError("Work order already has an open hold") from exc

        if work_order.workorder_status != WorkOrderStatus.ON_HOLD:
            work_order.workorder_status = WorkOrderStatus.ON_HOLD
            work_order.save(update_fields=['workorder_status', 'updated_at'])

    return hold


def clear_hold(work_order: WorkOrder, cleared_by) -> WorkOrderHold | None:
    """Close the open hold on a work order. Returns the cleared hold, or None if nothing was open.

    Does not auto-transition WO status — caller decides the post-hold status.
    """
    hold = WorkOrderHold.unscoped.filter(
        tenant_id=work_order.tenant_id,
        work_order=work_order,
        cleared_at__isnull=True,
        is_voided=False,
    ).first()
    if hold is None:
        return None

    hold.cleared_at = timezone.now()
    hold.cleared_by = cleared_by
    hold.save(update_fields=['cleared_at', 'cleared_by', 'updated_at'])
    # Back to what the order was doing. Clearing a hold used to leave the status at
    # ON_HOLD, so a cleared order still read "On hold" everywhere.
    if work_order.workorder_status == WorkOrderStatus.ON_HOLD:
        work_order.workorder_status = (WorkOrderStatus.IN_PROGRESS if _work_started(work_order)
                                       else WorkOrderStatus.PENDING)
        work_order.save(update_fields=['workorder_status', 'updated_at'])
    return hold


def _work_started(work_order: WorkOrder) -> bool:
    """Has work begun on any of the order's parts? (What `mark_started` records.)"""
    from Tracker.models import StepExecution
    return StepExecution.objects.filter(part__work_order=work_order).exists()  # tenant-safe: FK-scoped to the work order


def cancel_work_order(work_order: WorkOrder) -> WorkOrder:
    """Cancel a work order — it drops out of scheduling.

    Refused once any part has shipped or completed: delivered work can't be undone.
    Cascades to the parent order, which completes once all its work orders are
    terminal (the cancel action used to skip this).
    """
    from Tracker.models import PartsStatus
    if work_order.workorder_status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
        raise ValueError(f"The work order is already {work_order.get_workorder_status_display().lower()}.")
    delivered = [PartsStatus.SHIPPED, PartsStatus.COMPLETED, PartsStatus.IN_STOCK,
                 PartsStatus.AWAITING_PICKUP, PartsStatus.CORE_BANKED]
    if work_order.parts.filter(part_status__in=delivered).exists():
        raise ValueError("Can't cancel — some parts have already shipped or completed.")
    work_order.workorder_status = WorkOrderStatus.CANCELLED
    work_order.save(update_fields=['workorder_status', 'updated_at'])
    cascade_order_status(work_order)
    return work_order


SHORT_CLOSE_SCRAP = 'SCRAP'
SHORT_CLOSE_MOVE = 'MOVE'


def _customer_key(work_order):
    """Whose work `work_order` is: its order's company, else the order's customer user;
    None for a work order on no order (stock work)."""
    order = work_order.related_order if work_order is not None else None
    if order is None:
        return None
    if order.company_id:
        return ('company', order.company_id)
    if order.customer_id:
        return ('user', order.customer_id)
    return None


def move_refusal(part, source, target) -> str | None:
    """Why `part` can't move from work order `source` to `target` at a short-close, or
    None. A customer's own unit (a repair-and-return core) moves only to work for that
    customer — customer property stays ringfenced (ISO 9001 8.5.3). Any other unit moves
    to work for the same customer, or to work on no order (stock); never to another
    customer's job (user decision 2026-10-19)."""
    from Tracker.services.reman.core_steps import core_of
    core = core_of(part)
    if core is not None and core.returns_to_customer:
        owner = ('company', core.customer_id) if core.customer_id else _customer_key(source)
        if owner is not None and _customer_key(target) != owner:
            return (f"{part.ERP_id} is the customer's own unit (repair & return) — it can only "
                    f"move to a work order for that customer.")
        return None
    src, dst = _customer_key(source), _customer_key(target)
    if src is not None and dst is not None and src != dst:
        return (f"{target.ERP_id} is for a different customer — {part.ERP_id} can only move to a "
                f"work order for the same customer, or one on no order.")
    return None


def short_close_targets(work_order) -> dict:
    """Where each unfinished unit of `work_order` may move at a short-close: open work
    orders on the same process, narrowed per unit by `move_refusal`."""
    from Tracker.services.mes.parts import _part_has_ended
    targets = list(
        WorkOrder.objects.filter(process_id=work_order.process_id, tenant=work_order.tenant)
        .exclude(pk=work_order.pk)
        .exclude(workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED])
        .select_related('related_order', 'related_order__company', 'related_order__customer')
        .order_by('ERP_id')
    ) if work_order.process_id else []
    allowed = {}
    for p in Parts.objects.filter(work_order=work_order):
        if _part_has_ended(p):
            continue
        allowed[str(p.id)] = [str(t.id) for t in targets if move_refusal(p, work_order, t) is None]

    def customer_name(wo):
        order = wo.related_order
        if order is None:
            return None
        if order.company_id:
            return order.company.name
        if order.customer_id:
            return order.customer.get_full_name() or order.customer.username
        return None

    return {
        'targets': [{'id': str(t.id), 'ERP_id': t.ERP_id, 'quantity': t.quantity or 0,
                     'order_line': str(t.order_line_id) if t.order_line_id else None,
                     'customer_name': customer_name(t)} for t in targets],
        'allowed': allowed,
    }


def short_close_work_order(work_order: WorkOrder, *, reason: str, user,
                           dispositions: dict, return_shortfall: bool | None = None,
                           raise_targets: dict | None = None) -> WorkOrder:
    """Close a work order with fewer built than planned, on purpose.

    Every unit that hasn't ended is dispositioned: scrapped, or moved to another open
    work order running the same process (it keeps its step and carries on there).
    `dispositions` maps part id -> {'action': 'SCRAP' | 'MOVE', 'target_work_order': id}.
    The order reads COMPLETED with `short_closed` and the reason, and its customer
    order completes once its other work orders are terminal.

    Two consequences are the closer's to decide, never defaulted:
    - `return_shortfall` (asked when the work order is on an order line and closes
      short): give the unbuilt units back to the line as unplanned demand. Units moved
      to a work order on the same line whose quantity is raised are already planned
      there, so they aren't given back twice.
    - `raise_targets` maps each receiving work order id -> bool: raise its quantity by
      the units moved in, or leave it.

    Refused: an order already ended or on hold; one where nothing finished (that is a
    cancel); a unit left without a disposition; a decision left unanswered; scrapping
    a unit that's quarantined (that's a disposition decision) or out at a vendor.

    Raises:
        ValueError: naming why.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction
    from Tracker.models import RecordEdit
    from Tracker.models.mes_lite import PROGRESS_DONE_STATUSES
    from Tracker.services.core.clock import tenant_today
    from Tracker.services.mes.parts import _part_has_ended
    from Tracker.services.reman.core_part import scrap_if_core

    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Short-closing needs a reason.")
    if work_order.workorder_status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
        raise ValueError(f"The work order is already {work_order.get_workorder_status_display().lower()}.")
    if work_order.workorder_status == WorkOrderStatus.ON_HOLD:
        raise ValueError("The work order is on hold — clear the hold first.")

    with transaction.atomic():
        parts = list(Parts.objects.select_for_update().filter(work_order=work_order))
        open_parts = [p for p in parts if not _part_has_ended(p)]
        built = [p for p in parts if p.part_status in PROGRESS_DONE_STATUSES]
        if not built:
            raise ValueError("Nothing on this work order has finished — cancel it instead.")
        missing = [p.ERP_id for p in open_parts if str(p.id) not in dispositions]
        if missing:
            raise ValueError(f"Choose scrap or move for every unfinished unit: {', '.join(missing[:5])}"
                             + (f" and {len(missing) - 5} more." if len(missing) > 5 else "."))

        targets = {}
        for p in open_parts:
            d = dispositions[str(p.id)] or {}
            action = (d.get('action') or '').upper()
            if action == SHORT_CLOSE_SCRAP:
                if p.part_status == PartsStatus.QUARANTINED:
                    raise ValueError(f"{p.ERP_id} is quarantined — disposition it, or move it, rather than scrap it here.")
                if p.part_status == PartsStatus.AT_OUTSIDE_PROCESS:
                    raise ValueError(f"{p.ERP_id} is out at a vendor — it can be moved, not scrapped, until it's back.")
            elif action == SHORT_CLOSE_MOVE:
                tid = str(d.get('target_work_order') or '')
                if tid not in targets:
                    target = WorkOrder.objects.filter(pk=tid, tenant=work_order.tenant).first() if tid else None
                    if target is None or target.pk == work_order.pk:
                        raise ValueError(f"Choose another work order to move {p.ERP_id} to.")
                    if target.workorder_status in (WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED):
                        raise ValueError(f"{target.ERP_id} has ended — move units to an open work order.")
                    if target.process_id != work_order.process_id:
                        raise ValueError(f"{target.ERP_id} runs a different process — a unit can only move "
                                         f"to a work order on the same process, where its step exists.")
                    targets[tid] = target
                crossing = move_refusal(p, work_order, targets[tid])
                if crossing:
                    raise ValueError(crossing)
            else:
                raise ValueError(f"Unknown choice for {p.ERP_id}: scrap or move.")

        # The two decisions: answered, not assumed.
        raise_targets = {str(k): v for k, v in (raise_targets or {}).items()}
        moved_into = {tid: sum(1 for p in open_parts
                               if str(dispositions[str(p.id)].get('target_work_order') or '') == tid
                               and dispositions[str(p.id)]['action'].upper() == SHORT_CLOSE_MOVE)
                      for tid in targets}
        unanswered = [t.ERP_id for tid, t in targets.items() if not isinstance(raise_targets.get(tid), bool)]
        if unanswered:
            raise ValueError(f"Say whether to raise the quantity of {', '.join(unanswered)} "
                             f"for the units moved onto it.")
        shortfall = max(0, (work_order.quantity or 0) - len(built))
        covered = sum(n for tid, n in moved_into.items()
                      if raise_targets[tid] and work_order.order_line_id
                      and targets[tid].order_line_id == work_order.order_line_id)
        returnable = max(0, shortfall - covered)
        if work_order.order_line_id and returnable and not isinstance(return_shortfall, bool):
            raise ValueError("Say whether the units it didn't build go back to the order line "
                             "as demand still to plan.")

        part_ct = ContentType.objects.get_for_model(Parts)
        wo_ct = ContentType.objects.get_for_model(WorkOrder)
        for tid, target in targets.items():
            if raise_targets[tid] and moved_into[tid]:
                old_qty = target.quantity or 0
                target.quantity = old_qty + moved_into[tid]
                target.save(update_fields=['quantity', 'updated_at'])
                RecordEdit.objects.create(
                    tenant=target.tenant, content_type=wo_ct, object_id=target.id, field_name='quantity',
                    old_value=str(old_qty), new_value=str(target.quantity),
                    reason=f"{moved_into[tid]} unit(s) moved in from the short-close of {work_order.ERP_id}: {reason}",
                    edited_by=user)
        for p in open_parts:
            d = dispositions[str(p.id)]
            if d['action'].upper() == SHORT_CLOSE_SCRAP:
                old = p.part_status
                if not scrap_if_core(p, reason=f"short-close: {reason}"):
                    p.part_status = PartsStatus.SCRAPPED
                    p.step = None
                    p.save(update_fields=['part_status', 'step', 'updated_at'])
                RecordEdit.objects.create(
                    tenant=p.tenant, content_type=part_ct, object_id=p.id, field_name='part_status',
                    old_value=old, new_value=PartsStatus.SCRAPPED,
                    reason=f"Short-close of {work_order.ERP_id}: {reason}", edited_by=user)
            else:
                target = targets[str(d['target_work_order'])]
                p.work_order = target
                p.order = target.related_order
                p.save(update_fields=['work_order', 'order', 'updated_at'])
                RecordEdit.objects.create(
                    tenant=p.tenant, content_type=part_ct, object_id=p.id, field_name='work_order',
                    old_value=work_order.ERP_id, new_value=target.ERP_id,
                    reason=f"Short-close of {work_order.ERP_id}: {reason}", edited_by=user)

        work_order.workorder_status = WorkOrderStatus.COMPLETED
        work_order.short_closed = True
        work_order.short_close_reason = reason
        work_order.short_closed_by = user
        work_order.short_closed_at = timezone.now()
        work_order.short_close_returned_quantity = (
            returnable if (work_order.order_line_id and return_shortfall) else 0)
        work_order.true_completion = tenant_today(work_order.tenant)
        work_order.save(update_fields=[
            'workorder_status', 'short_closed', 'short_close_reason', 'short_closed_by',
            'short_closed_at', 'short_close_returned_quantity', 'true_completion', 'updated_at'])
        cascade_order_status(work_order)
    return work_order


def manual_status_refusal(current: str, new: str) -> str | None:
    """Why `current` → `new` can't be written as a plain field edit, or None if it can.

    None of the moves can. Each has an action that does what the move means:
    a hold carries a reason (place_on_hold), resuming restores the right status
    (clear_hold), cancelling checks nothing has shipped and cascades to the order
    (cancel). In progress and Completed are facts the product derives — work started,
    every part finished — not choices. A plain PATCH used to write any of them.
    """
    if new == current:
        return None
    label = dict(WorkOrderStatus.choices)
    move = f"{label.get(current, current)} → {label.get(new, new)}"
    if new == WorkOrderStatus.ON_HOLD:
        return f"{move}: place the work order on hold, with a reason, instead of setting the status."
    if current == WorkOrderStatus.ON_HOLD:
        return f"{move}: clear the hold instead; the status returns to where the work is."
    if new == WorkOrderStatus.CANCELLED:
        return f"{move}: use Cancel, which checks nothing has shipped."
    return (f"{move} isn't a status you set: In progress follows the first work started, "
            f"and Completed follows every part finishing.")


def bulk_place_on_hold(
    tenant_id,
    work_order_ids: list,
    reason: str,
    placed_by,
    notes: str = "",
    expected_clear_at=None,
) -> list[BulkResult]:
    if reason not in WorkOrderHoldReason.values:
        raise ValueError(f"Invalid hold reason: {reason}")

    results: list[BulkResult] = []
    wos = {wo.id: wo for wo in WorkOrder.unscoped.filter(
        tenant_id=tenant_id, id__in=work_order_ids,
    )}
    with transaction.atomic():
        for wo_id in work_order_ids:
            wo = wos.get(wo_id)
            if wo is None:
                results.append(BulkResult(id=wo_id, ok=False, error="Work order not found"))
                continue
            sid = transaction.savepoint()
            try:
                place_on_hold(wo, reason, placed_by, notes=notes, expected_clear_at=expected_clear_at)
                transaction.savepoint_commit(sid)
                results.append(BulkResult(id=wo_id, ok=True))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=wo_id, ok=False, error=str(exc)))
    return results


def bulk_clear_hold(tenant_id, work_order_ids: list, cleared_by) -> list[BulkResult]:
    results: list[BulkResult] = []
    wos = {wo.id: wo for wo in WorkOrder.unscoped.filter(
        tenant_id=tenant_id, id__in=work_order_ids,
    )}
    with transaction.atomic():
        for wo_id in work_order_ids:
            wo = wos.get(wo_id)
            if wo is None:
                results.append(BulkResult(id=wo_id, ok=False, error="Work order not found"))
                continue
            sid = transaction.savepoint()
            try:
                hold = clear_hold(wo, cleared_by)
                if hold is None:
                    transaction.savepoint_rollback(sid)
                    results.append(BulkResult(id=wo_id, ok=False, error="No open hold"))
                else:
                    transaction.savepoint_commit(sid)
                    results.append(BulkResult(id=wo_id, ok=True))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=wo_id, ok=False, error=str(exc)))
    return results


def _select_parts_for_split(
    parent_wo: WorkOrder,
    reason: str,
    part_ids: list | None,
    quantity: int | None,
) -> list[Parts]:
    base = Parts.unscoped.filter(tenant_id=parent_wo.tenant_id, work_order=parent_wo)
    if reason == WorkOrderSplitReason.QUANTITY:
        if not quantity or quantity <= 0:
            raise ValueError("quantity is required and must be > 0 for QUANTITY split")
        unstarted = list(base.filter(part_status=PartsStatus.PENDING).order_by('ERP_id', 'id')[:quantity])
        if len(unstarted) < quantity:
            raise ValueError(
                f"Only {len(unstarted)} unstarted parts available; requested {quantity}"
            )
        return unstarted
    if reason in (WorkOrderSplitReason.OPERATION, WorkOrderSplitReason.REWORK):
        if not part_ids:
            raise ValueError("part_ids is required for OPERATION/REWORK split")
        parts = list(base.filter(id__in=part_ids))
        if reason == WorkOrderSplitReason.REWORK:
            # A rework split restarts a part from nothing (PENDING, no step). A core's
            # part follows its reman stage, which that would leave behind; a core is
            # reworked inside its teardown or rebuild instead.
            from Tracker.models import Core
            cores = list(Core.unscoped.filter(tenant_id=parent_wo.tenant_id, part__in=parts)  # tenant-safe: explicit tenant filter
                         .values_list('core_number', flat=True))
            if cores:
                raise ValueError(
                    f"{', '.join(cores)} {'is a core' if len(cores) == 1 else 'are cores'}; "
                    "rework a core within its teardown or rebuild, not by a rework split"
                )
        if len(parts) != len(set(part_ids)):
            raise ValueError("One or more part_ids do not belong to this work order")
        return parts
    raise ValueError(f"Invalid split reason: {reason}")


def split_work_order(
    parent_wo: WorkOrder,
    reason: str,
    actor,
    new_erp_id: str,
    part_ids: list | None = None,
    quantity: int | None = None,
    target_process_id=None,
    notes: str = "",
) -> WorkOrder:
    """Move parts from `parent_wo` into a freshly-created child WorkOrder.

    QUANTITY: move first N PENDING parts, same process.
    OPERATION: move the given part_ids, same process.
    REWORK: move the given part_ids onto `target_process_id`; parts reset to PENDING with step cleared.

    Parent retains provenance via child.parent_workorder. No merges. Parts keep their identity.

    Idempotency: guarded by `new_erp_id` uniqueness — a double-submit with the same
    new_erp_id is rejected (no duplicate child), so retries are safe; a different erp_id
    is a distinct, intentional split.

    Authorization is enforced at the viewset (IsAuthenticated + TenantModelPermissions →
    add_workorder), not here — the service takes `actor` only for provenance/audit.
    """
    if reason not in WorkOrderSplitReason.values:
        raise ValueError(f"Invalid split reason: {reason}")
    if not new_erp_id:
        raise ValueError("new_erp_id is required")

    from Tracker.models import Processes

    target_process = parent_wo.process
    if reason == WorkOrderSplitReason.REWORK:
        if not target_process_id:
            raise ValueError("target_process_id is required for REWORK split")
        target_process = Processes.unscoped.filter(
            tenant_id=parent_wo.tenant_id, id=target_process_id,
        ).first()
        if target_process is None:
            raise ValueError("target_process_id not found in tenant")
        refusal = new_work_refusal(target_process)
        if refusal:
            raise ValueError(refusal)

    with transaction.atomic():
        parts = _select_parts_for_split(parent_wo, reason, part_ids, quantity)
        if not parts:
            raise ValueError("No parts selected for split")

        if WorkOrder.unscoped.filter(
            tenant_id=parent_wo.tenant_id, ERP_id=new_erp_id,
        ).exists():
            raise ValueError(f"ERP_id '{new_erp_id}' already exists")

        now = timezone.now()
        child = WorkOrder.objects.create(
            tenant=parent_wo.tenant,
            ERP_id=new_erp_id,
            workorder_status=WorkOrderStatus.PENDING,
            priority=parent_wo.priority,
            quantity=len(parts),
            related_order=parent_wo.related_order,
            process=target_process,
            notes=notes or "",
            parent_workorder=parent_wo,
            split_reason=reason,
            split_at=now,
            split_by=actor,
        )

        # Reassign per-instance via save() rather than a bulk .update(): bulk update
        # fires no signals, so django-auditlog would record NO LogEntry for parts moving
        # between work orders (or their step/status reset) — a traceability hole for an
        # AS9100 product. A split moves a subset of the lot, not the whole thing, so one
        # save per moved part is acceptable. Parts has no custom post_save receiver
        # (only auditlog's), so this adds auditing without triggering other cascades.
        for p in parts:
            p.work_order = child
            p.updated_at = now
            fields = ['work_order', 'updated_at']
            if p.split_from_lot:
                # The part is a fresh member of the CHILD's cohort now; the parent-cohort
                # split flag is meaningless here (it would otherwise orphan the part out of
                # the child's cohort gating). Clear the functional flag; the genealogy
                # (lot_split_reason / lot_split_at) is retained on the record + in auditlog.
                p.split_from_lot = False
                fields.append('split_from_lot')
            if reason == WorkOrderSplitReason.REWORK:
                p.step = None
                p.part_status = PartsStatus.PENDING
                fields += ['step', 'part_status']
            p.save(update_fields=fields)

    return child


def undo_split(child_wo: WorkOrder, actor) -> WorkOrder:
    """Reverse a split: reassign child's parts back to the parent and archive the child WO.

    Preserves audit trail — the original split entry on the child remains in django-auditlog.
    Authorization is enforced at the viewset (TenantModelPermissions), not here.
    """
    if child_wo.parent_workorder_id is None:
        raise ValueError("Work order is not the result of a split")

    parent_wo = WorkOrder.unscoped.filter(
        tenant_id=child_wo.tenant_id, id=child_wo.parent_workorder_id,
    ).first()
    if parent_wo is None:
        raise ValueError("Parent work order not found")

    with transaction.atomic():
        from Tracker.models import ProcessStep
        now = timezone.now()
        child_parts = list(Parts.unscoped.filter(
            tenant_id=child_wo.tenant_id, work_order=child_wo))

        # MES rule: a split is reversible only while the split-off units are UNTOUCHED.
        # A REWORK split reroutes parts onto a DIFFERENT process; once a part has been
        # worked there, its current step is foreign to the parent's routing and can't be
        # cleanly restored (cross-routing step identity doesn't transfer). Refuse the undo
        # rather than fabricate a position — the shop should complete the rework and rejoin,
        # or disposition those parts. (QUANTITY/OPERATION splits keep parent-process steps,
        # and an untouched REWORK part is step=None → returns as unstarted; both pass.)
        parent_step_ids = set(
            ProcessStep.objects.filter(process=parent_wo.process)
            .values_list('step_id', flat=True)
        )
        worked = [p for p in child_parts
                  if p.step_id is not None and p.step_id not in parent_step_ids]
        if worked:
            raise ValueError(
                f"Cannot undo split: {len(worked)} part(s) have been worked in the child "
                f"work order's routing (e.g. {worked[0].ERP_id}). Complete the rework and "
                f"rejoin, or disposition those parts, instead of undoing the split."
            )

        # Per-instance save() so django-auditlog logs each part's return to the parent
        # (bulk .update() would bypass the signal and leave the move untraced).
        for p in child_parts:
            p.work_order = parent_wo
            p.updated_at = now
            fields = ['work_order', 'updated_at']
            if p.split_from_lot:
                p.split_from_lot = False   # back in the parent cohort
                fields.append('split_from_lot')
            p.save(update_fields=fields)

        child_wo.archived = True
        child_wo.save(update_fields=['archived', 'updated_at'])

    return parent_wo
