"""Work-queue aggregate — the keystone endpoint the operator home is built on.

Serves ranked WO × step rows to UP NEXT / THEN and (later) the shop queue page.
Grain: one row per (WorkOrder, Step) with open StepExecutions, with distinct-
parts qty_ready + aging + a is_held flag. Ranked priority → due → aging.

v1 readiness = 'blocked' when the WO has an active hold, else 'ready'. Upstream-
done is implicit for open executions. Cert / calibration / downtime / manual-
blocker predicates layer on later as those systems mature (see design doc §9).
"""
from django.db.models import Count, Exists, Min, OuterRef, Q
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from Tracker.models import StepExecution, WorkOrder, WorkOrderHold
from Tracker.serializers.work_queue import WorkQueueRowSerializer
from Tracker.viewsets.base import TenantScopedMixin


class WorkQueueViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """Ranked ready-or-blocked work rows on the floor.

    Read-only; permissioned on `view_workorder` (already granted broadly — the
    row is a view onto WorkOrder work, not a first-class model). Filters:
      - `readiness=ready|blocked` (default: both, blocked sunk last)
      - `wo=<uuid>` — rows for a single WO
      - `search=<term>` — matches WO ERP id or step name
      - standard `?limit=&offset=` pagination
    """

    serializer_class = WorkQueueRowSerializer
    # queryset drives TenantModelPermissions' perm derivation (view_{model});
    # WorkOrder is the natural gate (broad grant). The actual rows are computed
    # by _rows() below — no queryset filtering paths from DRF are used.
    queryset = WorkOrder.unscoped.none()

    def _rows(self):
        """Compute the ranked aggregate as a Python list of row dicts."""
        tenant = self.tenant
        params = self.request.query_params

        # Active-hold subquery: hold row exists, not cleared, not voided (matches
        # WorkOrderHold's unique-open-per-WO constraint condition).
        active_holds = WorkOrderHold.unscoped.filter(
            tenant=tenant,
            work_order=OuterRef("part__work_order_id"),
            cleared_at__isnull=True,
            is_voided=False,
        )

        rows_qs = (
            StepExecution.unscoped.filter(
                tenant=tenant,
                exited_at__isnull=True,
                status__in=["PENDING", "IN_PROGRESS"],
                # Null-part rows are receiving / OSP-return inspections — not
                # part of the operator's work queue.
                part__isnull=False,
            )
            .values(
                "part__work_order_id",
                "part__work_order__ERP_id",
                "part__work_order__priority",
                "part__work_order__expected_completion",
                "part__part_type__name",
                "step_id",
                "step__name",
                "step__work_center_id",
                "step__work_center__kind",
            )
            .annotate(
                qty_ready=Count("part_id", distinct=True),
                earliest_entered_at=Min("entered_at"),
                is_held=Exists(active_holds),
            )
        )

        wo = params.get("wo")
        if wo:
            rows_qs = rows_qs.filter(part__work_order_id=wo)

        # Surface routing: filter by the step's work-center kind (e.g.
        # PRODUCTION for the operator queue) and/or a specific work-center or
        # set of work-centers (e.g. the current operator's memberships). Rows
        # with no work-center set (unmapped steps) drop out of the kind filter
        # but appear when no filter is set — see Documents/WORK_CENTER_DESIGN.md.
        kind = params.get("kind")
        if kind:
            rows_qs = rows_qs.filter(step__work_center__kind=kind)
        wc = params.get("work_center")
        if wc:
            rows_qs = rows_qs.filter(step__work_center_id=wc)
        wcs_csv = params.get("work_center__in")
        if wcs_csv:
            wc_ids = [w for w in wcs_csv.split(",") if w]
            if wc_ids:
                rows_qs = rows_qs.filter(step__work_center_id__in=wc_ids)

        term = (params.get("search") or "").strip()
        if term:
            rows_qs = rows_qs.filter(
                Q(part__work_order__ERP_id__icontains=term)
                | Q(step__name__icontains=term)
            )

        # Rank: blocked rows sink last; then priority (1=Urgent .. 4=Low), then
        # due date, then aging.
        rows_qs = rows_qs.order_by(
            "is_held",
            "part__work_order__priority",
            "part__work_order__expected_completion",
            "earliest_entered_at",
        )

        rows = [
            {
                "work_order": r["part__work_order_id"],
                "work_order_erp_id": r["part__work_order__ERP_id"],
                "step": r["step_id"],
                "step_name": r["step__name"],
                "part_type_name": r["part__part_type__name"],
                "priority": r["part__work_order__priority"],
                "expected_completion": r["part__work_order__expected_completion"],
                "qty_ready": r["qty_ready"],
                "earliest_entered_at": r["earliest_entered_at"],
                "is_held": r["is_held"],
                "readiness": "blocked" if r["is_held"] else "ready",
                "work_center": r["step__work_center_id"],
                "work_center_kind": r["step__work_center__kind"],
            }
            for r in rows_qs
        ]

        readiness = params.get("readiness")
        if readiness in ("ready", "blocked"):
            rows = [row for row in rows if row["readiness"] == readiness]

        return rows

    @extend_schema(responses=WorkQueueRowSerializer(many=True))
    def list(self, request, *args, **kwargs):
        rows = self._rows()
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(rows, many=True).data)
