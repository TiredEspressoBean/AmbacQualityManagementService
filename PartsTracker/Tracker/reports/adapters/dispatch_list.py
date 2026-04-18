"""
Dispatch List adapter.

A Dispatch List is a shift-level planning document showing every open Work Order
grouped by their current production step (used as a "work center" proxy).
Within each group, WOs are sorted by due date ascending so the most urgent jobs
appear first.

The PDF covers:
- Title block with generated date and tenant name
- Summary bar: total open WOs, overdue count
- Per work-center section:
    Section heading: step name + WO count
    Table: WO # | Part | Qty Remaining | Due Date | Days | Priority | Status
- Overdue rows highlighted in red
- Footer note (planning document, not a quality record)

This report takes no record ID — it is a tenant-wide aggregate over all open
Work Orders.  The param serializer only verifies that the requesting user has a
tenant context.

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class DispatchWOItem(BaseModel):
    """One Work Order row within a work-center group."""

    wo_number: str
    part_name: str
    qty_remaining: int
    due_date: Optional[datetime.date] = None
    days_until_due: Optional[int] = None   # None when no due date; negative = overdue
    priority: str                           # "Urgent" / "High" / "Normal" / "Low"
    status: str                             # WorkOrderStatus label


class WorkCenterGroup(BaseModel):
    """All WOs currently at one work center (step)."""

    step_name: str
    wo_count: int
    items: list[DispatchWOItem]


class DispatchListContext(BaseModel):
    """Top-level shape passed to the dispatch_list.typ template."""

    generated_date: datetime.date
    groups: list[WorkCenterGroup] = Field(default_factory=list)
    total_open_wos: int
    overdue_count: int
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class DispatchListParamsSerializer(serializers.Serializer):
    """
    No record ID needed — this report aggregates all open Work Orders in the
    requesting user's tenant.  The only validation required is that the user
    has a tenant context; if they do, build_context() can proceed.
    """

    def validate(self, attrs):
        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        return attrs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Priority int → human label (matches WorkOrderPriority choices)
_PRIORITY_LABELS: dict[int, str] = {
    1: "Urgent",
    2: "High",
    3: "Normal",
    4: "Low",
}

# WorkOrderStatus values that count as "open" for this report
_OPEN_STATUSES = (
    "PENDING",
    "IN_PROGRESS",
    "ON_HOLD",
    "WAITING_FOR_OPERATOR",
)


def _priority_label(value: int) -> str:
    return _PRIORITY_LABELS.get(value, str(value))


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class DispatchListAdapter(ReportAdapter):
    """
    Generates a tenant-wide Dispatch List grouping open Work Orders by their
    current production step (work center).

    Query strategy:
    1. Fetch all Parts with an active/open status that have a current Step and
       a linked WorkOrder.
    2. For each WorkOrder appearing at a Step, compute qty_remaining as the
       count of non-terminal Parts still on that WO at that Step.
    3. Group by Step name, sort within group by expected_completion ascending.
    4. Deduplicate WOs that appear at more than one step (edge case) — each WO
       is placed under the step where the majority of its parts currently sit.
    """

    name = "dispatch_list"
    title = "Dispatch List"
    template_path = "dispatch_list.typ"
    context_model_class = DispatchListContext
    param_serializer_class = DispatchListParamsSerializer

    def build_context(self, validated_params, user, tenant) -> DispatchListContext:
        from Tracker.models.mes_lite import Parts, WorkOrder

        today = datetime.date.today()

        # tenant-safe: explicit tenant filter (defense-in-depth)
        # Fetch all Parts that are actively in production (non-terminal, non-complete)
        # and have both a current Step and a linked WorkOrder.
        active_parts = (
            Parts.objects
            .filter(
                tenant=tenant,
                part_status__in=[
                    "IN_PROGRESS",
                    "AWAITING_QA",
                    "READY_FOR_NEXT_STEP",
                    "REWORK_IN_PROGRESS",
                    "REWORK_NEEDED",
                    "PENDING",
                ],
                work_order__isnull=False,
                step__isnull=False,
                work_order__workorder_status__in=_OPEN_STATUSES,
            )
            .select_related("step", "work_order")
            .order_by("step__name", "work_order__expected_completion", "work_order__priority")
        )

        # Build a mapping: (step_name, wo_id) -> {wo, count}
        # We count how many parts of each WO are at each step to determine
        # the "primary" step for a WO. We also track all WOs seen so we can
        # deduplicate across steps.
        from collections import defaultdict

        # step_name -> {wo_id -> {"wo": WorkOrder, "count": int}}
        step_wo_map: dict[str, dict] = defaultdict(dict)
        # wo_id -> step_name with highest count (for deduplication)
        wo_best_step: dict = {}
        wo_best_count: dict[str, int] = {}

        for part in active_parts:
            step_name = part.step.name
            wo_id = str(part.work_order_id)
            wo = part.work_order

            if wo_id not in step_wo_map[step_name]:
                step_wo_map[step_name][wo_id] = {"wo": wo, "count": 0}
            step_wo_map[step_name][wo_id]["count"] += 1

            current_best = wo_best_count.get(wo_id, 0)
            if step_wo_map[step_name][wo_id]["count"] > current_best:
                wo_best_step[wo_id] = step_name
                wo_best_count[wo_id] = step_wo_map[step_name][wo_id]["count"]

        # Rebuild groups using only the "best" step for each WO (deduplication)
        # best_groups: step_name -> list of (wo, qty_remaining)
        best_groups: dict[str, list] = defaultdict(list)

        for step_name, wo_dict in step_wo_map.items():
            for wo_id, entry in wo_dict.items():
                if wo_best_step.get(wo_id) == step_name:
                    best_groups[step_name].append((entry["wo"], entry["count"]))

        # Build context groups, sorted by step name
        groups: list[WorkCenterGroup] = []
        overdue_count = 0

        for step_name in sorted(best_groups.keys()):
            wo_entries = best_groups[step_name]

            # Sort WO entries by due date ascending (None → end), then priority
            wo_entries.sort(
                key=lambda e: (
                    e[0].expected_completion is None,
                    e[0].expected_completion or datetime.date.max,
                    e[0].priority,
                )
            )

            items: list[DispatchWOItem] = []
            for wo, qty_remaining in wo_entries:
                due_date = wo.expected_completion
                days_until_due: Optional[int] = None
                if due_date is not None:
                    days_until_due = (due_date - today).days
                    if days_until_due < 0:
                        overdue_count += 1

                items.append(DispatchWOItem(
                    wo_number=wo.ERP_id,
                    part_name=(
                        wo.process.part_type.name
                        if (wo.process and wo.process.part_type)
                        else "—"
                    ),
                    qty_remaining=qty_remaining,
                    due_date=due_date,
                    days_until_due=days_until_due,
                    priority=_priority_label(wo.priority),
                    status=wo.workorder_status,
                ))

            groups.append(WorkCenterGroup(
                step_name=step_name,
                wo_count=len(items),
                items=items,
            ))

        total_open_wos = sum(g.wo_count for g in groups)

        return DispatchListContext(
            generated_date=today,
            groups=groups,
            total_open_wos=total_open_wos,
            overdue_count=overdue_count,
            tenant_name=tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        today = datetime.date.today()
        return f"dispatch_list_{today.isoformat()}.pdf"
