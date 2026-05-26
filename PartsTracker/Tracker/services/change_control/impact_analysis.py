"""
Impact analysis for process change requests.

Snapshots the in-flight WorkOrders affected by a proposed change. Used
at PCR submission to capture which WOs were known to be running on the
target process at proposal time, and at PCO implementation to populate
the migration disposition UI.
"""
from __future__ import annotations

from typing import Iterable

from Tracker.models import Processes, WorkOrder, WorkOrderStatus

# WorkOrder statuses considered "in flight" for change-control impact.
# Excludes COMPLETED and CANCELLED — those are settled and unaffected
# by future process changes.
IN_FLIGHT_WORKORDER_STATUSES: tuple[str, ...] = (
    WorkOrderStatus.PENDING,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.ON_HOLD,
    WorkOrderStatus.WAITING_FOR_OPERATOR,
)


def snapshot_affected_workorders(target_process: Processes) -> list[dict]:
    """Return a JSON-safe snapshot of in-flight WOs on the target process.

    Each entry: {wo_id, erp_id, status, priority, quantity}.

    The snapshot is taken at PCR submission and stored on the PCR's
    `affected_workorders_snapshot` JSONField. It serves two purposes:

    1. Pre-approval review — gives reviewers visibility into how much
       in-flight production this change would affect if approved.
    2. Implementation reference — the PCO migration UI re-fetches
       affected WOs at implementation time but compares against the
       snapshot to flag WOs that have entered or exited in-flight
       status since submission.
    """
    qs = WorkOrder.objects.filter(
        process=target_process,
        workorder_status__in=IN_FLIGHT_WORKORDER_STATUSES,
        archived=False,
    ).order_by('priority', 'expected_completion', 'created_at')

    return [_serialize_workorder(wo) for wo in qs]


def list_affected_workorders(target_process: Processes) -> Iterable[WorkOrder]:
    """Return an iterable of in-flight WorkOrder model instances on the
    target process. Used by the PCO implementation panel to drive the
    actual migration actions (snapshot is for record; this is for action).
    """
    return WorkOrder.objects.filter(
        process=target_process,
        workorder_status__in=IN_FLIGHT_WORKORDER_STATUSES,
        archived=False,
    ).order_by('priority', 'expected_completion', 'created_at')


def _serialize_workorder(wo: WorkOrder) -> dict:
    return {
        'wo_id': str(wo.id),
        'erp_id': wo.ERP_id,
        'status': wo.workorder_status,
        'priority': wo.priority,
        'quantity': wo.quantity,
    }