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
        Parts.objects.filter(work_order=work_order, part_type=part_type, step=step)
        .order_by('id')
    )

    # Delegate sampling eval to the work_order's existing helper — it's
    # also called from `_initialize_sampling`, so keeping it on the model
    # avoids a second copy of the bulk-update loop.
    work_order._bulk_evaluate_sampling(fresh_parts)

    return fresh_parts


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
    live = Parts.objects.filter(work_order=work_order).exclude(
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

    with transaction.atomic():
        for p in removable[:to_remove]:
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


def cascade_order_status(work_order: WorkOrder) -> None:
    """Auto-complete the parent Order when all its WorkOrders are terminal.

    Terminal statuses are COMPLETED and CANCELLED. Called after a WorkOrder
    reaches one of those statuses. No-op when the WO has no parent order,
    when some WOs are still in progress, or when the order is already
    COMPLETED.
    """
    order = work_order.related_order
    if not order:
        return

    incomplete_wos = order.related_orders.exclude(
        workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]
    )
    if incomplete_wos.exists():
        return

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
    return hold


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


def bulk_transition(
    tenant_id,
    work_order_ids: list,
    new_status: str,
    actor,
    notes: str | None = None,
) -> list[BulkResult]:
    """Transition each listed WorkOrder to `new_status`. Matches single-WO behavior (no legality gate)."""
    if new_status not in WorkOrderStatus.values:
        raise ValueError(f"Invalid work order status: {new_status}")

    results: list[BulkResult] = []
    wos = {
        wo.id: wo for wo in WorkOrder.unscoped.filter(
            tenant_id=tenant_id, id__in=work_order_ids,
        )
    }
    with transaction.atomic():
        for wo_id in work_order_ids:
            wo = wos.get(wo_id)
            if wo is None:
                results.append(BulkResult(id=wo_id, ok=False, error="Work order not found"))
                continue
            sid = transaction.savepoint()
            try:
                wo.workorder_status = new_status
                update_fields = ['workorder_status', 'updated_at']
                if notes:
                    existing = wo.notes or ""
                    wo.notes = f"{existing}\n{notes}".strip()[:500]
                    update_fields.append('notes')
                wo.save(update_fields=update_fields)
                transaction.savepoint_commit(sid)
                results.append(BulkResult(id=wo_id, ok=True))
            except Exception as exc:
                transaction.savepoint_rollback(sid)
                results.append(BulkResult(id=wo_id, ok=False, error=str(exc)))
    return results
