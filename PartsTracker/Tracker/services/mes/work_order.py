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
) -> list:
    """Create parts for this work order idempotently and evaluate sampling.

    ERP_id pattern: `{work_order.ERP_id}-{part_type.ID_prefix}{seq:04d}`.
    Running the service twice won't duplicate parts — already-present
    ERP_ids are skipped.

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
        erp_id = f"{work_order.ERP_id}-{part_type.ID_prefix or 'P'}{i + 1:04d}"
        if erp_id not in existing_erp_ids:
            parts_to_create.append(Parts(
                tenant=work_order.tenant,
                work_order=work_order,
                part_type=part_type,
                step=step,
                ERP_id=erp_id,
                part_status=PartsStatus.PENDING,
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

        part_pks = [p.pk for p in parts]
        update_qs = Parts.unscoped.filter(tenant_id=parent_wo.tenant_id, pk__in=part_pks)
        if reason == WorkOrderSplitReason.REWORK:
            update_qs.update(
                work_order=child,
                step=None,
                part_status=PartsStatus.PENDING,
                updated_at=now,
            )
        else:
            update_qs.update(work_order=child, updated_at=now)

    return child


def undo_split(child_wo: WorkOrder, actor) -> WorkOrder:
    """Reverse a split: reassign child's parts back to the parent and archive the child WO.

    Preserves audit trail — the original split entry on the child remains in django-auditlog.
    """
    if child_wo.parent_workorder_id is None:
        raise ValueError("Work order is not the result of a split")

    parent_wo = WorkOrder.unscoped.filter(
        tenant_id=child_wo.tenant_id, id=child_wo.parent_workorder_id,
    ).first()
    if parent_wo is None:
        raise ValueError("Parent work order not found")

    with transaction.atomic():
        now = timezone.now()
        Parts.unscoped.filter(
            tenant_id=child_wo.tenant_id, work_order=child_wo,
        ).update(work_order=parent_wo, updated_at=now)

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
