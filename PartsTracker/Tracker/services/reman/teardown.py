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
from Tracker.services.reman.core_part import move_core

logger = logging.getLogger(__name__)


def eligible_disassembly_processes_for(core_type):
    """Return APPROVED disassembly Processes eligible for a given core_type.

    Drives the operator-facing teardown Process picker (Q1 shape D). When the
    list is empty, no teardown WO can be created for this core_type until an
    engineer flags at least one Process with `is_disassembly=True`.
    """
    return (
        Processes.objects
        .filter(  # tenant-safe: .objects auto-scopes to the request tenant
            part_type=core_type,
            is_disassembly=True,
            status=ProcessStatus.APPROVED,
            # `.objects` scopes by tenant but does NOT exclude soft-deleted rows, so
            # without this a voided teardown process stayed in the operator's picker.
            archived=False,
        )
        .order_by('name')
    )


def _resolve_teardown_process(core_type, explicit: Processes | None) -> Processes:
    """Pick the process to use for the teardown WO.

    Resolution order (Q1 shape D):
    1. `explicit` if supplied (after validating eligibility).
    2. `core_type.default_disassembly_process` if set (canonical preference).
    3. Single-match shortcut — if exactly one eligible Process exists, use it.
    4. Otherwise: refuse and ask the caller to pick (automation paths surface
       a "pick one" task; UI flows route to the picker dialog).
    """
    if explicit is not None:
        if explicit.part_type_id != core_type.id:
            raise ValueError(
                "Provided process part_type does not match the cores' core_type",
            )
        if not explicit.is_disassembly:
            raise ValueError(
                f"Process {explicit.name} is not flagged as a disassembly process",
            )
        if explicit.status != ProcessStatus.APPROVED:
            raise ValueError(
                f"Process {explicit.name} is not APPROVED (status={explicit.status})",
            )
        return explicit

    default = core_type.default_disassembly_process
    if default is not None and default.is_disassembly and default.status == ProcessStatus.APPROVED:
        return default

    eligible = list(eligible_disassembly_processes_for(core_type)[:2])
    if len(eligible) == 1:
        return eligible[0]
    if len(eligible) == 0:
        raise ValueError(
            f"No eligible disassembly Process found for core_type {core_type.name}; "
            "flag a Process with is_disassembly=True or pass process explicitly",
        )
    raise ValueError(
        f"Multiple eligible disassembly Processes for core_type {core_type.name}; "
        "operator must pick one or set core_type.default_disassembly_process",
    )


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
    shared_core_type, target_process = _validate_batch(cores, process)
    tenant = cores[0].tenant

    with transaction.atomic():
        wo = _create_teardown_work_order(
            tenant, shared_core_type, target_process, len(cores),
            status=WorkOrderStatus.IN_PROGRESS,
            notes=f"Teardown batch of {len(cores)} cores",
        )
        entry = _entry_step(target_process)
        for core in cores:
            # A core's position is its part's: put the UNIT on the work order, at the
            # route's first step — or there is nowhere to open it in the DWI runtime.
            move_core(core, work_order=wo, step=entry)
            start_core_disassembly(core, user)

        logger.info(
            "Teardown batch WO %s created with %d cores (core_type=%s)",
            wo.ERP_id, len(cores), shared_core_type.name,
        )
    return wo


def _validate_batch(cores, process):
    """The rules any teardown batch obeys, planned or started: one core type, every
    core RECEIVED and on no work order. Returns (core_type, process)."""
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
        if core.part.work_order_id is not None:
            raise ValueError(
                f"Core {core.core_number} is already linked to a work order",
            )
    return shared_core_type, _resolve_teardown_process(shared_core_type, process)


def _entry_step(process):
    """Where a unit enters this route: its authored entry point, else its first step
    by order — the rule ordinary work orders use. A teardown once linked its cores to
    the work order with NO step, which left the DWI runtime nothing to open."""
    from Tracker.models import ProcessStep
    entry = process.get_entry_step()
    if entry is not None:
        return entry
    first = (ProcessStep.objects.filter(process=process)  # tenant-safe: scoped by `process` FK
             .select_related('step').order_by('order').first())
    if first is None:
        raise ValueError(f"Process {process} has no steps to tear down on")
    return first.step


def _create_teardown_work_order(tenant, core_type, process, quantity, *, status,
                                notes, expected_start=None):
    now = timezone.now()
    # Microseconds as well as seconds: two batches accepted in the same second would
    # otherwise mint the same ERP id.
    erp_id = f"TEARDOWN-{now.strftime('%Y%m%d-%H%M%S-%f')}-{core_type.ID_prefix or 'CORE'}"
    return WorkOrder.objects.create(
        tenant=tenant,
        ERP_id=erp_id,
        workorder_status=status,
        quantity=quantity,
        process=process,
        expected_start=expected_start,
        notes=notes,
    )


def plan_teardown(cores: list[Core], user, *, start_by=None,
                  process: Processes | None = None) -> WorkOrder:
    """Commit cores to a teardown that starts later — what "accept" on a teardown
    proposal does.

    The same checks as `start_teardown_batch`, but nothing is started: the work order
    is PENDING and dated to `start_by`, and the cores stay RECEIVED. The scheduler
    places it like any other job (a unit with no current step enters at the process's
    first step), and disassembly begins on its own when an operator starts that first
    step (`services.reman.core_steps.on_step_started`). Starting now is still
    `start_teardown_batch`.

    Linking the cores is the commitment: from here they count as teardown already on
    its way, so the proposal that suggested them stops suggesting them.
    """
    shared_core_type, target_process = _validate_batch(cores, process)
    tenant = cores[0].tenant

    with transaction.atomic():
        wo = _create_teardown_work_order(
            tenant, shared_core_type, target_process, len(cores),
            status=WorkOrderStatus.PENDING,
            expected_start=start_by,
            notes=f"Planned teardown of {len(cores)} cores"
                  + (f", start by {start_by}" if start_by else ""),
        )
        entry = _entry_step(target_process)
        for core in cores:
            # A core's position is its part's: put the UNIT on the work order, at the
            # route's first step, where an operator will start it.
            move_core(core, work_order=wo, step=entry)

        logger.info(
            "Planned teardown WO %s: %d cores (core_type=%s), start by %s",
            wo.ERP_id, len(cores), shared_core_type.name, start_by,
        )
    return wo
