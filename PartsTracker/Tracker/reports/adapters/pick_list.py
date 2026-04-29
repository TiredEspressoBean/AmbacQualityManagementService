"""
Pick List / Material Requisition adapter.

A Pick List is a shop-floor document printed at job release that lists every
component and raw material required to build a work order quantity.  The picker
works through the list, pulls each item from inventory, checks off the row, and
returns the signed sheet to production.

The PDF covers:
- Title block: work order number, part being built, qty to produce, due date
- Component table:
    Find # | Part Number | Description | Qty/Ea | Qty Required | UoM | Opt | Picked
  where "Picked" is a blank column for the picker's check/initials
- Footer note: "Return this list to production after picking."

Qty Required per line = BOMLine.quantity × WorkOrder.quantity.  This
multiplication is performed in build_context(); the template only displays the
pre-computed value.

Part type is resolved via WorkOrder → Process → PartType.  The released BOM for
that PartType is then fetched (status=RELEASED).

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check. See Documents/TYPST_MIGRATION_PLAN.md "SPC service methods
and tenant scoping" for the rationale.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class PickListItem(BaseModel):
    """One component row in the pick list table."""

    find_number: str
    component_part_number: str
    component_name: str
    qty_per_assembly: str     # Decimal serialized as string to avoid float noise
    qty_required: str         # qty_per_assembly × WO quantity, as string
    unit_of_measure: str
    is_optional: bool


class PickListContext(BaseModel):
    """Top-level shape passed to the pick_list.typ template."""

    # ---- Work order header ----
    wo_number: str
    part_number: str
    part_name: str
    qty_to_produce: int
    due_date: Optional[datetime.date]

    # ---- Pick items ----
    items: list[PickListItem] = Field(default_factory=list)
    total_line_count: int

    # ---- Document metadata ----
    tenant_name: str
    generated_date: datetime.date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_qty(d: Decimal) -> str:
    """
    Format a Decimal quantity as a human-readable string without
    scientific notation.  Integer values are rendered without a decimal
    point (e.g. Decimal('50.0000') → '50'); fractional values keep only
    significant digits (e.g. Decimal('12.5000') → '12.5').
    """
    normalized = d.normalize()
    if normalized == normalized.to_integral_value():
        return str(int(normalized))
    return str(normalized)


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class PickListParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} identifying the WorkOrder to pick for.
    Confirms the WorkOrder exists in the requesting user's tenant.
    The adapter re-queries with an explicit tenant filter for
    defense-in-depth.

    WorkOrder uses a UUID primary key (SecureModel default), so the
    id field is a UUIDField, not IntegerField.
    """

    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models.mes_lite import WorkOrder

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = WorkOrder.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"WorkOrder {value} not found.")
        return value


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class PickListAdapter(ReportAdapter):
    """
    Renders a Pick List / Material Requisition PDF for a given WorkOrder.

    The BOM is resolved via WorkOrder → Process → PartType → released BOM.
    If no released BOM exists the items list will be empty (the template
    handles this gracefully).
    """

    name = "pick_list"
    title = "Pick List / Material Requisition"
    template_path = "pick_list.typ"
    context_model_class = PickListContext
    param_serializer_class = PickListParamsSerializer

    def build_context(self, validated_params, user, tenant) -> PickListContext:
        from Tracker.models.mes_lite import WorkOrder
        from Tracker.models.mes_standard import BOM

        today = datetime.date.today()

        # tenant-safe: explicit tenant filter (defense-in-depth)
        wo = (
            WorkOrder.objects
            .filter(tenant=tenant)
            .select_related(
                "process__part_type",
                "tenant",
            )
            .get(id=validated_params["id"])
        )

        # Resolve the part type via the process link
        part_type = wo.process.part_type if (wo.process and wo.process.part_type) else None

        items: list[PickListItem] = []
        part_number = ""
        part_name = ""

        if part_type is not None:
            part_number = part_type.ERP_id or ""
            part_name = part_type.name

            # Fetch the released BOM for this part type (tenant-scoped)
            bom = (
                BOM.objects
                .filter(
                    tenant=tenant,
                    part_type=part_type,
                    status="RELEASED",
                )
                .prefetch_related("lines__component_type")
                .order_by("-revision")
                .first()
            )

            if bom is not None:
                wo_qty = Decimal(wo.quantity)
                for line in bom.lines.all():
                    qty_per = line.quantity
                    qty_req = qty_per * wo_qty
                    items.append(PickListItem(
                        find_number=line.find_number or "",
                        component_part_number=line.component_type.ERP_id or "",
                        component_name=line.component_type.name,
                        qty_per_assembly=_fmt_qty(qty_per),
                        qty_required=_fmt_qty(qty_req),
                        unit_of_measure=line.unit_of_measure,
                        is_optional=line.is_optional,
                    ))

        return PickListContext(
            wo_number=wo.ERP_id,
            part_number=part_number,
            part_name=part_name,
            qty_to_produce=wo.quantity,
            due_date=wo.expected_completion,
            items=items,
            total_line_count=len(items),
            tenant_name=tenant.name,
            generated_date=today,
        )

    def get_filename(self, validated_params) -> str:
        return f"pick_list_{validated_params.get('id', 'unknown')}.pdf"
