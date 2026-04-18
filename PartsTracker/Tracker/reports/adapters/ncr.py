"""
Non-Conformance Report (NCR) adapter.

An NCR is the formal document produced when a quality issue requires
a disposition decision (rework / repair / scrap / use-as-is / return-
to-supplier). In this codebase the NCR is represented by the
`QuarantineDisposition` model with its related `QualityReports` and
per-defect metadata.

The PDF covers:
- Header: NCR number, severity, current state, disposition type
- Identification: part, work order, step, machine
- Non-conformance description + per-report defect tables
- Containment actions
- Disposition / resolution narrative
- Customer approval status (when required)
- Scrap verification (when disposition = SCRAP)
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


class NcrContext(BaseModel):
    """Top-level shape passed to the ncr_report.typ template."""

    # ---- Header ----
    disposition_number: str
    current_state: str          # OPEN / IN_PROGRESS / CLOSED
    severity: str               # CRITICAL / MAJOR / MINOR
    disposition_type: Optional[str] = None  # REWORK / REPAIR / SCRAP / ...
    created_at: datetime

    # ---- Identification ----
    part_erp_id: Optional[str] = None
    part_type_name: Optional[str] = None
    work_order_erp_id: Optional[str] = None
    step_name: Optional[str] = None

    # ---- Non-conformance ----
    description: str = ""
    quality_reports: list[QualityReportRef] = Field(default_factory=list)

    # ---- Containment ----
    containment_action: str = ""
    containment_completed_by: Optional[str] = None
    containment_completed_at: Optional[datetime] = None

    # ---- Disposition ----
    rework_attempt_at_step: int = 1
    resolution_notes: str = ""
    assigned_to: Optional[str] = None

    # ---- Customer approval ----
    requires_customer_approval: bool = False
    customer_approval_received: bool = False
    customer_approval_reference: str = ""
    customer_approval_date: Optional[date] = None

    # ---- Scrap verification ----
    scrap_verified: bool = False
    scrap_verification_method: str = ""
    scrap_verified_by: Optional[str] = None
    scrap_verified_at: Optional[datetime] = None

    # ---- Closure ----
    resolution_completed: bool = False
    resolution_completed_by: Optional[str] = None
    resolution_completed_at: Optional[datetime] = None

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class NcrParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} and confirms the QuarantineDisposition exists
    in the requesting user's tenant. Returns the id as a UUID in
    validated_data — the adapter re-queries with an explicit tenant
    filter for defense-in-depth.

    QuarantineDisposition uses a UUID primary key (SecureModel default),
    so the id field is a UUIDField, not IntegerField.
    """
    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models import QuarantineDisposition

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = QuarantineDisposition.objects.filter(
            id=value, tenant=tenant
        ).exists()
        if not exists:
            raise serializers.ValidationError(f"NCR {value} not found.")
        return value


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
    """Renders an NCR / QuarantineDisposition as a PDF."""

    name = "ncr_report"
    title = "Non-Conformance Report"
    template_path = "ncr_report.typ"
    context_model_class = NcrContext
    param_serializer_class = NcrParamsSerializer

    def build_context(self, validated_params, user, tenant) -> NcrContext:
        from Tracker.models import QuarantineDisposition

        # tenant-safe: explicit tenant filter (defense-in-depth)
        qd = (
            QuarantineDisposition.objects
            .filter(tenant=tenant)
            .select_related(
                "part__work_order",
                "part__part_type",
                "step",
                "assigned_to",
                "containment_completed_by",
                "scrap_verified_by",
                "resolution_completed_by",
                "tenant",
            )
            .prefetch_related(
                "quality_reports__defects__error_type",
                "quality_reports__detected_by",
            )
            .get(id=validated_params["id"])
        )

        part = qd.part
        work_order = part.work_order if part else None
        part_type = part.part_type if part else None

        quality_reports = [
            QualityReportRef(
                report_number=qr.report_number or f"QR-{qr.id}",
                status=qr.status,
                detected_by=_user_name(qr.detected_by),
                detected_at=qr.created_at,
                description=qr.description or "",
                defects=[
                    DefectLine(
                        error_name=d.error_type.error_name,
                        count=d.count,
                        location=d.location,
                        severity=d.severity,
                        notes=d.notes,
                    )
                    for d in qr.defects.all()
                ],
            )
            for qr in qd.quality_reports.all()
        ]

        return NcrContext(
            disposition_number=qd.disposition_number,
            current_state=qd.current_state,
            severity=qd.severity,
            disposition_type=qd.disposition_type or None,
            created_at=qd.created_at,

            part_erp_id=part.ERP_id if part else None,
            part_type_name=part_type.name if part_type else None,
            work_order_erp_id=work_order.ERP_id if work_order else None,
            step_name=qd.step.name if qd.step else None,

            description=qd.description,
            quality_reports=quality_reports,

            containment_action=qd.containment_action,
            containment_completed_by=_user_name(qd.containment_completed_by),
            containment_completed_at=qd.containment_completed_at,

            rework_attempt_at_step=qd.rework_attempt_at_step,
            resolution_notes=qd.resolution_notes,
            assigned_to=_user_name(qd.assigned_to),

            requires_customer_approval=qd.requires_customer_approval,
            customer_approval_received=qd.customer_approval_received,
            customer_approval_reference=qd.customer_approval_reference,
            customer_approval_date=qd.customer_approval_date,

            scrap_verified=qd.scrap_verified,
            scrap_verification_method=qd.scrap_verification_method,
            scrap_verified_by=_user_name(qd.scrap_verified_by),
            scrap_verified_at=qd.scrap_verified_at,

            resolution_completed=qd.resolution_completed,
            resolution_completed_by=_user_name(qd.resolution_completed_by),
            resolution_completed_at=qd.resolution_completed_at,

            tenant_name=qd.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        # Prefer the disposition_number if we can look it up cheaply,
        # otherwise fall back to the id-based default.
        return f"ncr_{validated_params.get('id', 'unknown')}.pdf"
