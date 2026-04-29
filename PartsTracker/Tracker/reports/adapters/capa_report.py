"""
CAPA Report adapter.

A CAPA (Corrective and Preventive Action) report is the formal document
that captures the full lifecycle of a quality problem from problem
identification through root cause analysis, corrective/preventive actions,
effectiveness verification, and closure.

This is a general CAPA dump — NOT 8D structured. It covers:
- Header: CAPA number, type, severity, status, key dates
- Problem statement + immediate action
- Root cause analysis (method, summary, 5-Why Q&A pairs or Fishbone 6M)
- Action items grouped by type (CONTAINMENT / CORRECTIVE / PREVENTIVE)
- Effectiveness verification results
- Approval workflow status
- Signature block: Initiator, Quality Manager, Approver

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


class WhyPair(BaseModel):
    """A single Why question + answer pair in a 5-Why analysis."""
    question: str
    answer: str


class FiveWhysContext(BaseModel):
    """Rendered 5-Why analysis data attached to an RCA record."""
    whys: list[WhyPair] = Field(default_factory=list)
    identified_root_cause: str = ""


class FishboneContext(BaseModel):
    """Rendered Fishbone (Ishikawa) 6M data attached to an RCA record."""
    man_causes: list[str] = Field(default_factory=list)
    machine_causes: list[str] = Field(default_factory=list)
    material_causes: list[str] = Field(default_factory=list)
    method_causes: list[str] = Field(default_factory=list)
    measurement_causes: list[str] = Field(default_factory=list)
    environment_causes: list[str] = Field(default_factory=list)
    identified_root_cause: str = ""


class RcaContext(BaseModel):
    """Root cause analysis section."""
    method: str                   # FIVE_WHYS / FISHBONE / FAULT_TREE / PARETO
    problem_description: str = ""
    root_cause_summary: str = ""
    conducted_by: Optional[str] = None
    conducted_date: Optional[date] = None
    five_whys: Optional[FiveWhysContext] = None
    fishbone: Optional[FishboneContext] = None


class CapaTaskLine(BaseModel):
    """One row in the action items table."""
    task_number: str
    task_type: str                # CONTAINMENT / CORRECTIVE / PREVENTIVE
    description: str
    owner: Optional[str] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: str                   # NOT_STARTED / IN_PROGRESS / COMPLETED / CANCELLED


class VerificationContext(BaseModel):
    """Effectiveness verification section."""
    verification_method: str = ""
    verification_criteria: str = ""
    verification_date: Optional[date] = None
    verified_by: Optional[str] = None
    effectiveness_result: str = ""   # CONFIRMED / NOT_EFFECTIVE / INCONCLUSIVE
    verification_notes: str = ""


class ApprovalContext(BaseModel):
    """Approval workflow section."""
    approval_required: bool = False
    approval_status: str = "NOT_REQUIRED"   # NOT_REQUIRED / PENDING / APPROVED / REJECTED
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class CapaReportContext(BaseModel):
    """Top-level shape passed to the capa_report.typ template."""

    # ---- Header ----
    capa_number: str
    capa_type: str              # CORRECTIVE / PREVENTIVE / CUSTOMER_COMPLAINT / ...
    severity: str               # CRITICAL / MAJOR / MINOR
    status: str                 # OPEN / IN_PROGRESS / PENDING_VERIFICATION / CLOSED / CANCELLED
    initiated_date: date
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    initiated_by: Optional[str] = None
    assigned_to: Optional[str] = None

    # ---- Problem ----
    problem_statement: str = ""
    immediate_action: str = ""

    # ---- Root cause analysis ----
    rca: Optional[RcaContext] = None

    # ---- Action items ----
    tasks: list[CapaTaskLine] = Field(default_factory=list)

    # ---- Verification ----
    verification: Optional[VerificationContext] = None

    # ---- Approval ----
    approval: ApprovalContext = Field(default_factory=ApprovalContext)

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class CapaReportParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} and confirms the CAPA exists in the
    requesting user's tenant. Returns the id as a UUID in
    validated_data — the adapter re-queries with an explicit tenant
    filter for defense-in-depth.

    CAPA uses a UUID primary key (SecureModel default), so the id
    field is a UUIDField, not IntegerField.
    """
    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models.qms import CAPA

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = CAPA.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"CAPA {value} not found.")
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


def _build_rca(rca_record) -> RcaContext:
    """Convert an RcaRecord ORM object into an RcaContext Pydantic model."""
    five_whys_ctx = None
    fishbone_ctx = None

    if hasattr(rca_record, "five_whys"):
        fw = rca_record.five_whys
        pairs = []
        for i in range(1, 6):
            q = getattr(fw, f"why_{i}_question", None) or ""
            a = getattr(fw, f"why_{i}_answer", None) or ""
            if q or a:
                pairs.append(WhyPair(question=q, answer=a))
        five_whys_ctx = FiveWhysContext(
            whys=pairs,
            identified_root_cause=fw.identified_root_cause or "",
        )

    if hasattr(rca_record, "fishbone"):
        fb = rca_record.fishbone
        fishbone_ctx = FishboneContext(
            man_causes=fb.man_causes or [],
            machine_causes=fb.machine_causes or [],
            material_causes=fb.material_causes or [],
            method_causes=fb.method_causes or [],
            measurement_causes=fb.measurement_causes or [],
            environment_causes=fb.environment_causes or [],
            identified_root_cause=fb.identified_root_cause or "",
        )

    return RcaContext(
        method=rca_record.rca_method,
        problem_description=rca_record.problem_description or "",
        root_cause_summary=rca_record.root_cause_summary or "",
        conducted_by=_user_name(rca_record.conducted_by),
        conducted_date=rca_record.conducted_date,
        five_whys=five_whys_ctx,
        fishbone=fishbone_ctx,
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CapaReportAdapter(ReportAdapter):
    """Renders a CAPA record as a PDF report."""

    name = "capa_report"
    title = "CAPA Report"
    template_path = "capa_report.typ"
    context_model_class = CapaReportContext
    param_serializer_class = CapaReportParamsSerializer

    def build_context(self, validated_params, user, tenant) -> CapaReportContext:
        from Tracker.models.qms import CAPA

        # tenant-safe: explicit tenant filter (defense-in-depth)
        capa = (
            CAPA.unscoped
            .filter(tenant=tenant)
            .select_related(
                "initiated_by",
                "assigned_to",
                "approved_by",
                "tenant",
            )
            .prefetch_related(
                "tasks__assigned_to",
                "tasks__completed_by",
                "rca_records__conducted_by",
                "rca_records__five_whys",
                "rca_records__fishbone",
                "verifications__verified_by",
            )
            .get(id=validated_params["id"])
        )

        # ---- Tasks ----
        tasks = [
            CapaTaskLine(
                task_number=t.task_number,
                task_type=t.task_type,
                description=t.description,
                owner=_user_name(t.assigned_to),
                due_date=t.due_date,
                completed_date=t.completed_date,
                status=t.status,
            )
            for t in capa.tasks.all()
        ]

        # ---- RCA — use the most recent record ----
        rca_ctx = None
        rca_record = capa.rca_records.first()
        if rca_record is not None:
            rca_ctx = _build_rca(rca_record)

        # ---- Verification — use the most recent record ----
        verification_ctx = None
        verification = capa.verifications.first()
        if verification is not None:
            verification_ctx = VerificationContext(
                verification_method=verification.verification_method or "",
                verification_criteria=verification.verification_criteria or "",
                verification_date=verification.verification_date,
                verified_by=_user_name(verification.verified_by),
                effectiveness_result=verification.effectiveness_result,
                verification_notes=verification.verification_notes or "",
            )

        # ---- Approval ----
        approval_ctx = ApprovalContext(
            approval_required=capa.approval_required,
            approval_status=capa.approval_status,
            approved_by=_user_name(capa.approved_by),
            approved_at=capa.approved_at,
        )

        return CapaReportContext(
            capa_number=capa.capa_number,
            capa_type=capa.capa_type,
            severity=capa.severity,
            status=capa.status,
            initiated_date=capa.initiated_date,
            due_date=capa.due_date,
            completed_date=capa.completed_date,
            initiated_by=_user_name(capa.initiated_by),
            assigned_to=_user_name(capa.assigned_to),
            problem_statement=capa.problem_statement,
            immediate_action=capa.immediate_action or "",
            rca=rca_ctx,
            tasks=tasks,
            verification=verification_ctx,
            approval=approval_ctx,
            tenant_name=capa.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        return f"capa_{validated_params.get('id', 'unknown')}.pdf"
