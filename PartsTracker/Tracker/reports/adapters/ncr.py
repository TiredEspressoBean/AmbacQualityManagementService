"""
Non-Conformance Report (NCR) adapter.

An NCR is the formal record of a nonconformance: what is wrong, where it was
found, its containment, and the decision on each part (or lot quantity) it
covers. In this codebase that is the `NCR` model, with its failed inspection
records (`QualityReports`) and the `QuarantineDisposition` decided for each
thing it covers.

The PDF covers:
- Header: NCR number, severity, state
- Where found: work order, step, the load for a failed batch cycle
- Non-conformance description + per-report defect tables
- Containment actions
- What it covers: one row per part / lot with its decision
- Each decision: who authorized it, notes, customer approval, scrap verification,
  completion
- Closure signatures

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check. See Documents/TYPST_MIGRATION_PLAN.md "SPC service methods
and tenant scoping" for the rationale.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class DefectLine(BaseModel):
    """One row in a quality report's defect breakdown."""
    error_name: str
    count: int = Field(ge=0)
    location: str = ""
    severity: str = ""
    notes: str = ""


class QualityReportRef(BaseModel):
    """A QualityReports row attached to the NCR, plus its defects."""
    report_number: str
    status: str  # PASS / FAIL / PENDING
    detected_by: Optional[str] = None
    detected_at: Optional[datetime] = None
    description: str = ""
    defects: list[DefectLine] = Field(default_factory=list)


class DecisionRef(BaseModel):
    """One thing the NCR covers — a part or a rejected lot quantity — and the decision
    on it (its disposition), if one has been made."""
    subject: str                       # the part's serial, or "Lot L-12 (40 pcs)"
    part_status: Optional[str] = None
    disposition_number: Optional[str] = None
    disposition_type: Optional[str] = None
    current_state: Optional[str] = None
    decision_authorized_by: Optional[str] = None
    decision_authorized_at: Optional[datetime] = None
    rework_attempt_at_step: int = 1
    resolution_notes: str = ""
    assigned_to: Optional[str] = None
    requires_customer_approval: bool = False
    customer_approval_received: bool = False
    customer_approval_reference: str = ""
    customer_approval_date: Optional[date] = None
    scrap_verified: bool = False
    scrap_verification_method: str = ""
    scrap_verified_by: Optional[str] = None
    scrap_verified_at: Optional[datetime] = None
    resolution_completed: bool = False
    resolution_completed_by: Optional[str] = None
    resolution_completed_at: Optional[datetime] = None


class NcrContext(BaseModel):
    """Top-level shape passed to the ncr_report.typ template."""

    # ---- Header ----
    ncr_number: str
    state: str                  # OPEN / CLOSED
    severity: str               # CRITICAL / MAJOR / MINOR
    created_at: datetime
    closed_at: Optional[datetime] = None
    raised_by: Optional[str] = None

    # ---- Where it was found ----
    work_order_erp_id: Optional[str] = None
    step_name: Optional[str] = None
    part_type_name: Optional[str] = None
    # A failed batch cycle's NCR covers the load.
    batch_load: Optional[str] = None

    # ---- Non-conformance ----
    description: str = ""
    quality_reports: list[QualityReportRef] = Field(default_factory=list)

    # ---- Containment ----
    containment_action: str = ""
    containment_completed_by: Optional[str] = None
    containment_completed_at: Optional[datetime] = None

    # ---- What it covers, and what was decided ----
    decisions: list[DecisionRef] = Field(default_factory=list)

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


def _resolve_ncr_id(value, tenant):
    """The NCR `value` names — an NCR's id, or a disposition's (printing from a
    disposition prints its NCR). None when neither is in the tenant."""
    from Tracker.models import NCR, QuarantineDisposition
    # tenant-safe: explicit tenant filter
    if NCR.unscoped.filter(id=value, tenant=tenant).exists():
        return value
    # tenant-safe: explicit tenant filter
    return (QuarantineDisposition.unscoped.filter(id=value, tenant=tenant)
            .exclude(ncr__isnull=True).values_list("ncr_id", flat=True).first())


class NcrParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} — an NCR, or a disposition under one — and confirms it
    exists in the requesting user's tenant. Returns the NCR's id in validated_data;
    the adapter re-queries with an explicit tenant filter for defense-in-depth.
    """
    id = serializers.UUIDField()

    def validate_id(self, value):
        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        ncr_id = _resolve_ncr_id(value, tenant)
        if ncr_id is None:
            raise serializers.ValidationError(f"NCR {value} not found.")
        return ncr_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_name(user) -> Optional[str]:
    """Render a User FK as 'Full Name' or fallback to email/username."""
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", None)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class NcrAdapter(ReportAdapter):
    """Renders an NCR, with every decision under it, as a PDF."""

    name = "ncr_report"
    title = "Non-Conformance Report"
    template_path = "ncr_report.typ"
    context_model_class = NcrContext
    param_serializer_class = NcrParamsSerializer

    def build_context(self, validated_params, user, tenant) -> NcrContext:
        from Tracker.models import NCR

        # tenant-safe: explicit tenant filter (defense-in-depth)
        ncr = (
            NCR.unscoped
            .filter(tenant=tenant)
            .select_related("step", "work_order", "raised_by", "containment_completed_by",
                            "batch_execution__step", "tenant")
            .get(id=validated_params["id"])
        )
        decisions = list(
            ncr.dispositions.filter(archived=False)
            .select_related("part__part_type", "material_lot", "assigned_to",
                            "decision_authorized_by", "scrap_verified_by", "resolution_completed_by")
            .order_by("created_at")
        )
        reports = list(
            ncr.reports.filter(archived=False)
            .prefetch_related("defects__error_type", "personnel_links__user")
            .select_related("detected_by")
            .order_by("created_at")
        )
        batch = ncr.batch_execution
        batch_load = None
        if batch is not None:
            step = batch.step.name if batch.step_id else "Batch"
            batch_load = f"{step} load of {batch.parts.count()} parts"
        part_types = {d.part.part_type.name for d in decisions if d.part_id and d.part.part_type_id}

        def subject(d):
            if d.part_id:
                return d.part.ERP_id
            if d.material_lot_id:
                qty = f" ({d.quantity:g} pcs)" if d.quantity is not None else ""
                return f"Lot {d.material_lot.lot_number}{qty}"
            return "—"

        return NcrContext(
            ncr_number=ncr.ncr_number,
            state=ncr.state,
            severity=ncr.severity,
            created_at=ncr.created_at,
            closed_at=ncr.closed_at,
            raised_by=_user_name(ncr.raised_by),

            work_order_erp_id=ncr.work_order.ERP_id if ncr.work_order_id else None,
            step_name=ncr.step.name if ncr.step_id else None,
            part_type_name=part_types.pop() if len(part_types) == 1 else None,
            batch_load=batch_load,

            description=ncr.description,
            quality_reports=[
                QualityReportRef(
                    report_number=qr.report_number or f"QR-{qr.id}",
                    status=qr.status,
                    detected_by=_user_name(qr.primary_detector),
                    detected_at=qr.created_at,
                    description=qr.description or "",
                    defects=[
                        DefectLine(error_name=d.error_type.error_name, count=d.count,
                                   location=d.location, severity=d.severity, notes=d.notes)
                        for d in qr.defects.all()
                    ],
                )
                for qr in reports
            ],

            containment_action=ncr.containment_action,
            containment_completed_by=_user_name(ncr.containment_completed_by),
            containment_completed_at=ncr.containment_completed_at,

            decisions=[
                DecisionRef(
                    subject=subject(d),
                    part_status=d.part.part_status if d.part_id else None,
                    disposition_number=d.disposition_number,
                    disposition_type=d.disposition_type or None,
                    current_state=d.current_state,
                    decision_authorized_by=_user_name(d.decision_authorized_by),
                    decision_authorized_at=d.decision_authorized_at,
                    rework_attempt_at_step=d.rework_attempt_at_step,
                    resolution_notes=d.resolution_notes,
                    assigned_to=_user_name(d.assigned_to),
                    requires_customer_approval=d.requires_customer_approval,
                    customer_approval_received=d.customer_approval_received,
                    customer_approval_reference=d.customer_approval_reference,
                    customer_approval_date=d.customer_approval_date,
                    scrap_verified=d.scrap_verified,
                    scrap_verification_method=d.scrap_verification_method,
                    scrap_verified_by=_user_name(d.scrap_verified_by),
                    scrap_verified_at=d.scrap_verified_at,
                    resolution_completed=d.resolution_completed,
                    resolution_completed_by=_user_name(d.resolution_completed_by),
                    resolution_completed_at=d.resolution_completed_at,
                )
                for d in decisions
            ],

            tenant_name=ncr.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        return f"ncr_{validated_params.get('id', 'unknown')}.pdf"
