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


def affected_workorders_with_impact(
    target_process: Processes,
    proposed_change_diff: dict | None,
) -> list[dict]:
    """Per-WO impact summary for the PCO migration picker.

    For each in-flight WO on the target process, return:
        wo_id, erp_id, status, priority,
        total_parts            -- non-completed/scrapped/cancelled parts on the WO
        affected_parts         -- parts currently at a step touched by the diff
                                  (modified or removed)

    "Affected" parts are the ones whose current step is part of the
    diff's change surface. Parts not yet started, parts past the diff
    region, and parts at unchanged steps are all "unaffected" — they
    can be migrated trivially. The split helps the operator decide
    whether to move a WO across (`MIGRATE_*`) or hold it on the old
    version (`KEEP_ALL`).
    """
    from Tracker.models import Parts, PartsStatus

    diff = proposed_change_diff or {}
    touched_step_ids: set[str] = set()
    for entry in (diff.get('steps') or {}).get('modified', []):
        if 'id' in entry:
            touched_step_ids.add(str(entry['id']))
    for entry in (diff.get('steps') or {}).get('removed', []):
        if 'id' in entry:
            touched_step_ids.add(str(entry['id']))

    settled_statuses = (
        PartsStatus.COMPLETED,
        PartsStatus.SCRAPPED,
        PartsStatus.CANCELLED,
    )

    rows: list[dict] = []
    for wo in list_affected_workorders(target_process):
        in_flight_parts = Parts.objects.filter(work_order=wo).exclude(
            part_status__in=settled_statuses,
        )
        total_parts = in_flight_parts.count()
        if touched_step_ids:
            affected_parts = in_flight_parts.filter(step_id__in=touched_step_ids).count()
        else:
            affected_parts = 0
        rows.append({
            'wo_id': str(wo.id),
            'erp_id': wo.ERP_id,
            'status': wo.workorder_status,
            'priority': wo.priority,
            'quantity': wo.quantity,
            'total_parts': total_parts,
            'affected_parts': affected_parts,
        })
    return rows


def _serialize_workorder(wo: WorkOrder) -> dict:
    return {
        'wo_id': str(wo.id),
        'erp_id': wo.ERP_id,
        'status': wo.workorder_status,
        'priority': wo.priority,
        'quantity': wo.quantity,
    }