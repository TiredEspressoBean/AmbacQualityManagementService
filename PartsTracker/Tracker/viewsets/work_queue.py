"""Work-queue aggregate — the keystone endpoint the operator home is built on.

Serves ranked WO × step rows to UP NEXT / THEN and (later) the shop queue page.
Grain: one row per (WorkOrder, Step) with open StepExecutions, with distinct-
parts qty_ready + aging + a is_held flag. Ranked priority → due → aging.

v1 readiness = 'blocked' when the WO has an active hold, else 'ready'. Upstream-
done is implicit for open executions. Cert / calibration / downtime / manual-
blocker predicates layer on later as those systems mature (see design doc §9).
"""
from datetime import timedelta

from django.db.models import Count, Exists, Min, OuterRef, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from Tracker.models import (
    Parts, ScheduledTask, ScheduleResult, StepExecution, WorkOrder, WorkOrderHold,
)
from Tracker.serializers.work_queue import WorkQueueRowSerializer
from Tracker.viewsets.base import TenantScopedMixin


class WorkQueueViewSet(TenantScopedMixin, viewsets.GenericViewSet):
    """Ranked ready-or-blocked work rows on the floor.

    Read-only; permissioned on `view_workorder` (already granted broadly — the
    row is a view onto WorkOrder work, not a first-class model). Filters:
      - `readiness=ready|blocked` (default: both, blocked sunk last)
      - `wo=<uuid>` — rows for a single WO
      - `machine=<uuid>` / `machine__in=<csv>` — station pull: only rows the live
        schedule assigned to that machine (unscheduled rows drop out)
      - `search=<term>` — matches WO ERP id or step name
      - standard `?limit=&offset=` pagination
    """

    serializer_class = WorkQueueRowSerializer
    # queryset drives TenantModelPermissions' perm derivation (view_{model});
    # WorkOrder is the natural gate (broad grant). The actual rows are computed
    # by _rows() below — no queryset filtering paths from DRF are used.
    queryset = WorkOrder.unscoped.none()
    # Additive gate: `view_workorder` alone also belongs to customer-portal
    # accounts, whose WO visibility is relationship-filtered (for_user) — but
    # _rows() computes tenant-wide floor rows with no row scoping. `view_steps`
    # is staff-wide and absent from the Customer preset, keeping the floor
    # queue an internal surface.
    action_permissions = {'list': ['view_steps']}

    def _scheduled_meta(self):
        """Map (work_order_id, step_id) -> {start, machine_id, machine_name} on the live
        committed schedule — the earliest planned start for the cohort and the machine that
        start is assigned to (so the floor sees *which machine* to run it on). Empty when
        there is no active schedule, so the queue falls back to the heuristic order. Bulk
        read outside a request path uses `.unscoped` with an explicit tenant filter."""
        tenant = self.tenant
        active = (
            ScheduleResult.unscoped
            .filter(tenant=tenant, is_active=True, is_draft=False)
            .order_by("-created_at").first()
        )
        if active is None:
            return {}
        meta: dict = {}
        # Ordered by start_time, so the first row seen per (WO, step) is the earliest —
        # its machine is the representative one to label (a cohort normally runs together).
        for r in (
            ScheduledTask.unscoped
            .filter(tenant=tenant, schedule=active, part__isnull=False)
            .values("part__work_order_id", "step_id", "start_time",
                    "machine_id", "machine__name")
            .order_by("start_time")
        ):
            key = (r["part__work_order_id"], r["step_id"])
            if key not in meta:
                meta[key] = {
                    "start": r["start_time"],
                    "machine_id": r["machine_id"],
                    "machine_name": r["machine__name"],
                }
        return meta

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

        def _scoped(qs, p):
            """The request's filters, for rows reached through `p` ("part__" from an
            execution, "" from a part)."""
            wo = params.get("wo")
            if wo:
                qs = qs.filter(**{f"{p}work_order_id": wo})
            # Surface routing: filter by the step's work-center kind (e.g.
            # PRODUCTION for the operator queue) and/or a specific work-center or
            # set of work-centers (e.g. the current operator's memberships). Rows
            # with no work-center set (unmapped steps) drop out of the kind filter
            # but appear when no filter is set — see Documents/WORK_CENTER_DESIGN.md.
            kind = params.get("kind")
            if kind:
                qs = qs.filter(step__work_center__kind=kind)
            wc = params.get("work_center")
            if wc:
                qs = qs.filter(step__work_center_id=wc)
            wcs_csv = params.get("work_center__in")
            if wcs_csv:
                wc_ids = [w for w in wcs_csv.split(",") if w]
                if wc_ids:
                    qs = qs.filter(step__work_center_id__in=wc_ids)
            term = (params.get("search") or "").strip()
            if term:
                qs = qs.filter(
                    Q(**{f"{p}work_order__ERP_id__icontains": term})
                    | Q(step__name__icontains=term)
                )
            return qs

        rows_qs = _scoped(rows_qs, "part__")

        # Fallback rank (rows the planner hasn't scheduled): blocked sink last;
        # then priority (1=Urgent .. 4=Low), due date, aging.
        rows_qs = rows_qs.order_by(
            "is_held",
            "part__work_order__priority",
            "part__work_order__expected_completion",
            "earliest_entered_at",
        )

        # APS schedule order: the earliest planned start per (WO, step) on the
        # live committed schedule. Scheduled rows lead in planned order; anything
        # the solver didn't place keeps the heuristic order above. So the floor
        # works the plan when there is one and degrades gracefully when there
        # isn't. (Assignment-driven "your work today" is a later, bigger shift.)
        sched_meta = self._scheduled_meta()

        def _meta(wo_id, step_id):
            return sched_meta.get((wo_id, step_id)) or {}

        # Unstarted parts at their current step on a RELEASED order: a new part waits
        # at its first step with no StepExecution until someone starts it (that is
        # what "unstarted" means — reduce_work_order_quantity cancels exactly these),
        # so a freshly released order was in nobody's queue and new work could only
        # be started from the WO page (Operator walk 2026-10-20). Counted as ready.
        open_here = StepExecution.unscoped.filter(  # tenant-safe: correlated to the scoped outer part
            part=OuterRef("pk"), step=OuterRef("step_id"), exited_at__isnull=True)
        active_holds_part = WorkOrderHold.unscoped.filter(
            tenant=tenant, work_order=OuterRef("work_order_id"),
            cleared_at__isnull=True, is_voided=False)
        unstarted_qs = _scoped(
            Parts.unscoped.filter(  # tenant-safe: tenant=tenant explicitly
                tenant=tenant, archived=False, part_status="PENDING", step__isnull=False,
                work_order__released_at__isnull=False,
            ).exclude(work_order__workorder_status__in=["COMPLETED", "CANCELLED"])
            .exclude(Exists(open_here)),
            "",
        ).values(
            "work_order_id", "work_order__ERP_id", "work_order__priority",
            "work_order__expected_completion", "part_type__name", "step_id", "step__name",
            "step__work_center_id", "step__work_center__kind",
        ).annotate(
            qty_ready=Count("id", distinct=True),
            earliest_entered_at=Min("work_order__released_at"),
            is_held=Exists(active_holds_part),
        )
        merged = {(r["part__work_order_id"], r["step_id"]): dict(r) for r in rows_qs}
        for u in unstarted_qs:
            key = (u["work_order_id"], u["step_id"])
            if key in merged:
                merged[key]["qty_ready"] += u["qty_ready"]
                continue
            merged[key] = {
                "part__work_order_id": u["work_order_id"],
                "part__work_order__ERP_id": u["work_order__ERP_id"],
                "part__work_order__priority": u["work_order__priority"],
                "part__work_order__expected_completion": u["work_order__expected_completion"],
                "part__part_type__name": u["part_type__name"],
                "step_id": u["step_id"], "step__name": u["step__name"],
                "step__work_center_id": u["step__work_center_id"],
                "step__work_center__kind": u["step__work_center__kind"],
                "qty_ready": u["qty_ready"], "earliest_entered_at": u["earliest_entered_at"],
                "is_held": u["is_held"],
            }
        # Same fallback rank as the query's order_by, now over both sources.
        _far = timezone.now() + timedelta(days=36500)
        ranked = sorted(merged.values(), key=lambda r: (
            r["is_held"],
            r["part__work_order__priority"] if r["part__work_order__priority"] is not None else 99,
            r["part__work_order__expected_completion"] or _far.date(),
            r["earliest_entered_at"] or _far,
        ))

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
                "scheduled_start": _meta(r["part__work_order_id"], r["step_id"]).get("start"),
                # The machine the schedule assigned this cohort to (null = none / unscheduled).
                "machine": _meta(r["part__work_order_id"], r["step_id"]).get("machine_id"),
                "machine_name": _meta(r["part__work_order_id"], r["step_id"]).get("machine_name"),
            }
            for r in ranked
        ]

        # Stable re-rank onto the schedule: blocked still sink last; scheduled
        # rows lead, ordered by planned start; unscheduled rows keep their
        # heuristic order (Python sort is stable). The mixed int/datetime third
        # key is safe — it's only compared within a same-`scheduled?` group.
        rows.sort(key=lambda row: (
            row["is_held"],
            0 if row["scheduled_start"] is not None else 1,
            row["scheduled_start"] if row["scheduled_start"] is not None else 0,
        ))

        readiness = params.get("readiness")
        if readiness in ("ready", "blocked"):
            rows = [row for row in rows if row["readiness"] == readiness]

        # Machine scoping (station pull): the assigned machine comes from the schedule map,
        # not the StepExecution grain, so filter in Python after the rows are built. A row
        # the solver didn't place (machine=None) is excluded by a machine filter.
        machine = params.get("machine")
        if machine:
            rows = [row for row in rows if row["machine"] and str(row["machine"]) == machine]
        machines_csv = params.get("machine__in")
        if machines_csv:
            mids = {m for m in machines_csv.split(",") if m}
            rows = [row for row in rows if row["machine"] and str(row["machine"]) in mids]

        return rows

    @extend_schema(responses=WorkQueueRowSerializer(many=True))
    def list(self, request, *args, **kwargs):
        rows = self._rows()
        page = self.paginate_queryset(rows)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(rows, many=True).data)
