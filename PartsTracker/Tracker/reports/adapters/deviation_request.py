"""
Deviation Request / Use-As-Is adapter.

A Deviation Request is the formal document produced when engineering
determines that a nonconforming product may be accepted without rework
— i.e. the deviation does not affect form, fit, or function. In
AS9100D / IATF 16949 terminology this covers disposition types
USE_AS_IS and REPAIR (repair may deviate from the original spec, so
it also needs engineering sign-off).

This adapter is a filtered view of the `QuarantineDisposition` model.
Only dispositions whose `disposition_type` is USE_AS_IS or REPAIR are
valid inputs. Attempting to generate a deviation request for a REWORK
or SCRAP disposition is rejected in the param serializer.

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

VALID_DISPOSITION_TYPES = {"USE_AS_IS", "REPAIR"}


class DeviationRequestContext(BaseModel):
    """Top-level shape passed to the deviation_request.typ template."""

    # ---- Header ----
    disposition_number: str
    current_state: str              # OPEN / IN_PROGRESS / CLOSED
    severity: str                   # CRITICAL / MAJOR / MINOR
    disposition_type: str           # USE_AS_IS or REPAIR
    created_at: datetime

    # ---- Part identification ----
    part_erp_id: Optional[str] = None
    part_type_name: Optional[str] = None
    work_order_erp_id: Optional[str] = None
    step_name: Optional[str] = None

    # ---- Nonconformance ----
    description: str = ""

    # ---- Engineering justification ----
    resolution_notes: str = ""
    assigned_to: Optional[str] = None   # MRB reviewer

    # ---- Customer approval ----
    requires_customer_approval: bool = False
    customer_approval_received: bool = False
    customer_approval_reference: str = ""
    customer_approval_date: Optional[date] = None

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class DeviationRequestParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} and confirms that:
      1. The QuarantineDisposition exists in the requesting user's tenant.
      2. Its disposition_type is USE_AS_IS or REPAIR.

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
        try:
            qd = QuarantineDisposition.objects.get(id=value, tenant=tenant)
        except QuarantineDisposition.DoesNotExist:
            raise serializers.ValidationError(f"Disposition {value} not found.")

        if qd.disposition_type not in VALID_DISPOSITION_TYPES:
            raise serializers.ValidationError(
                f"Disposition {value} has type {qd.disposition_type!r}. "
                "Deviation requests only apply to USE_AS_IS and REPAIR dispositions."
            )

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


class DeviationRequestAdapter(ReportAdapter):
    """Renders a Deviation Request / Use-As-Is disposition as a PDF."""

    name = "deviation_request"
    title = "Deviation Request"
    template_path = "deviation_request.typ"
    context_model_class = DeviationRequestContext
    param_serializer_class = DeviationRequestParamsSerializer

    def build_context(self, validated_params, user, tenant) -> DeviationRequestContext:
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
                "tenant",
            )
            .get(id=validated_params["id"])
        )

        part = qd.part
        work_order = part.work_order if part else None
        part_type = part.part_type if part else None

        return DeviationRequestContext(
            disposition_number=qd.disposition_number,
            current_state=qd.current_state,
            severity=qd.severity,
            disposition_type=qd.disposition_type,
            created_at=qd.created_at,

            part_erp_id=part.ERP_id if part else None,
            part_type_name=part_type.name if part_type else None,
            work_order_erp_id=work_order.ERP_id if work_order else None,
            step_name=qd.step.name if qd.step else None,

            description=qd.description,

            resolution_notes=qd.resolution_notes,
            assigned_to=_user_name(qd.assigned_to),

            requires_customer_approval=qd.requires_customer_approval,
            customer_approval_received=qd.customer_approval_received,
            customer_approval_reference=qd.customer_approval_reference,
            customer_approval_date=qd.customer_approval_date,

            tenant_name=qd.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        return f"deviation_request_{validated_params.get('id', 'unknown')}.pdf"
