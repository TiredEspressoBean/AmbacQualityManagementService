"""
BOM Report adapter.

A BOM Report is a printed bill of materials used for shop floor reference or
customer submittal. It presents the hierarchical component structure of a
parent assembly, listing every child line with find number, part number,
description, quantity, unit of measure, and optional status.

The PDF covers:
- Title block: BOM header, status badge, effective date
- Header info table: parent part number/name, revision, BOM type
- Component table: Find # | Part Number | Description | Qty | UoM | Optional | Notes
- No signature block (shop reference document — engineering signs in PLM/ERP)

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check. See Documents/TYPST_MIGRATION_PLAN.md "SPC service methods
and tenant scoping" for the rationale.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class BOMLineContext(BaseModel):
    """One component row in the BOM table."""

    find_number: str
    component_part_number: str
    component_name: str
    quantity: str           # Decimal serialized as string to avoid float noise
    unit_of_measure: str
    is_optional: bool
    notes: str


class BOMReportContext(BaseModel):
    """Top-level shape passed to the bom_report.typ template."""

    # ---- BOM header ----
    parent_part_number: str
    parent_part_name: str
    revision: str
    bom_type: str           # ASSEMBLY / DISASSEMBLY
    status: str             # DRAFT / RELEASED / OBSOLETE
    effective_date: Optional[date]

    # ---- Lines ----
    lines: list[BOMLineContext] = Field(default_factory=list)
    total_line_count: int

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class BOMReportParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} and confirms the BOM exists in the
    requesting user's tenant. Returns the id as a UUID in
    validated_data — the adapter re-queries with an explicit tenant
    filter for defense-in-depth.

    BOM uses a UUID primary key (SecureModel default), so the id
    field is a UUIDField, not IntegerField.
    """

    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models.mes_standard import BOM

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = BOM.objects.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"BOM {value} not found.")
        return value


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class BOMReportAdapter(ReportAdapter):
    """Renders a BOM record as a printed Bill of Materials PDF."""

    name = "bom_report"
    title = "Bill of Materials"
    template_path = "bom_report.typ"
    context_model_class = BOMReportContext
    param_serializer_class = BOMReportParamsSerializer

    def build_context(self, validated_params, user, tenant) -> BOMReportContext:
        from Tracker.models.mes_standard import BOM

        # tenant-safe: explicit tenant filter (defense-in-depth)
        bom = (
            BOM.objects
            .filter(tenant=tenant)
            .select_related(
                "part_type",
                "tenant",
            )
            .prefetch_related(
                "lines__component_type",
            )
            .get(id=validated_params["id"])
        )

        lines = [
            BOMLineContext(
                find_number=line.find_number or "",
                component_part_number=line.component_type.ERP_id or "",
                component_name=line.component_type.name,
                quantity=str(line.quantity.normalize()),
                unit_of_measure=line.unit_of_measure,
                is_optional=line.is_optional,
                notes=line.notes or "",
            )
            for line in bom.lines.all()
        ]

        return BOMReportContext(
            parent_part_number=bom.part_type.ERP_id or "",
            parent_part_name=bom.part_type.name,
            revision=bom.revision,
            bom_type=bom.bom_type,
            status=bom.status,
            effective_date=bom.effective_date,
            lines=lines,
            total_line_count=len(lines),
            tenant_name=bom.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        return f"bom_{validated_params.get('id', 'unknown')}.pdf"
