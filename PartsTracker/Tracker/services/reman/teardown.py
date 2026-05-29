"""
Teardown batch services.

Creates a single Work Order that owns N RECEIVED cores and transitions them all
to IN_DISASSEMBLY in one atomic step. Used when an operator selects a batch of
cores on the inventory page and starts disassembly together.
"""
from __future__ import annotations

import logging
from django.db import transaction
from django.utils import timezone

from Tracker.models import Core, Processes, ProcessStatus, WorkOrder, WorkOrderStatus
from Tracker.services.reman.core import start_core_disassembly

logger = logging.getLogger(__name__)


def _resolve_teardown_process(core_type, explicit: Processes | None) -> Processes:
    """Pick the process to use for the teardown WO.

    Returns `explicit` when provided (after validating part_type matches).
    Otherwise falls back to the first APPROVED `Processes` row whose
    `part_type` matches the cores' shared core_type. This fallback is a
    temporary lookup until `PartTypes.disassembly_process` FK lands per
    REMAN_DWI_INTEGRATION.md — at that point this function should consult
    `core_type.disassembly_process` directly.
    """
    if explicit is not None:
        if explicit.part_type_id != core_type.id:
            raise ValueError(
                "Provided process part_type does not match the cores' core_type",
            )
        return explicit

    process = (
        Processes.objects
        .filter(part_type=core_type, status=ProcessStatus.APPROVED)
        .order_by('-is_remanufactured', '-created_at')
        .first()
    )
    if process is None:
        raise ValueError(
            f"No APPROVED Process found for core_type {core_type.name}; "
            "pass process_id explicitly",
        )
    return process


def start_teardown_batch(
    cores: list[Core],
    user,
    process: Processes | None = None,
) -> WorkOrder:
    """Create a teardown WO that owns the given cores and start disassembly.

    All `cores` must:
      - Share the same `core_type`.
      - Be in status RECEIVED.
      - Not currently be linked to a WorkOrder.

    Atomic: any validation failure or per-core transition error rolls back
    the whole batch including the WO creation.
    """
    if not cores:
        raise ValueError("cores list is empty")

    core_types = {c.core_type_id for c in cores}
    if len(core_types) > 1:
        raise ValueError("All cores must share the same core_type")
    shared_core_type = cores[0].core_type

    for core in cores:
        if core.status != 'RECEIVED':
            raise ValueError(
                f"Core {core.core_number} is not RECEIVED (status={core.status})",
            )
        if core.work_order_id is not None:
            raise ValueError(
                f"Core {core.core_number} is already linked to a work order",
            )

    target_process = _resolve_teardown_process(shared_core_type, process)
    tenant = cores[0].tenant

    with transaction.atomic():
        now = timezone.now()
        erp_id = f"TEARDOWN-{now.strftime('%Y%m%d-%H%M%S')}-{shared_core_type.ID_prefix or 'CORE'}"
        wo = WorkOrder.objects.create(
            tenant=tenant,
            ERP_id=erp_id,
            workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=len(cores),
            process=target_process,
            notes=f"Teardown batch of {len(cores)} cores",
        )
        for core in cores:
            core.work_order = wo
            core.save(update_fields=['work_order', 'updated_at'])
            start_core_disassembly(core, user)

        logger.info(
            "Teardown batch WO %s created with %d cores (core_type=%s)",
            wo.ERP_id, len(cores), shared_core_type.name,
        )
    return wo