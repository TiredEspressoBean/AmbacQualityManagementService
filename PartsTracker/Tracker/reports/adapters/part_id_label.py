"""
Part ID Label / WIP Tag adapter.

Produces a 4"×2" thermal label for a single Part, suitable for Zebra-style
thermal printers at high daily volume.

Compliance: ISO 9001 §8.5.2 — product identification must be maintained
throughout the production process. This is a PERMANENT label — it stays
with the part for the part's whole life. Inspection status and current
process step are explicitly NOT included because they change over time;
a label that says "In Progress" on a part that's already shipped is
worse than no label at all.

Inspection status is conveyed separately on the shop floor via:
    - Stickers/stamps applied to the label as the part passes QC gates
    - Color-coded containers (standard shop floor convention)
    - Quarantine/Hold Tags (separate report) for failed inspections

Label content:
    - Part number / type name  (largest text)
    - Revision (version from SecureModel)
    - Serial number (ERP_id)
    - Code 128 barcode (encodes the serial; scanner-readable)
    - Work order number (for traceability back to the WO)
    - QR code (URL pointer for phone scan to part detail)
    - Tenant name + print date (footer, muted)

No signature block, page headers, or footers — this is a shop label.

Defense-in-depth: every ORM query in build_context() filters by tenant
explicitly, in addition to the param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.barcodes import render_barcode_svg, render_qr_svg


# ---------------------------------------------------------------------------
# Pydantic context model
# ---------------------------------------------------------------------------


class PartIdLabelContext(BaseModel):
    """Top-level shape passed to the part_id_label.typ template."""

    # ---- Part identification (permanent) ----
    part_number: str           # from part_type.name
    revision: Optional[str] = None  # from part_type.version — e.g. "Rev 3"
    serial: str                # ERP_id
    work_order_number: Optional[str] = None

    # ---- Encoded media ----
    barcode_svg: str           # Code 128 SVG encoding the serial
    qr_svg: str                # QR SVG pointing to part detail URL

    # ---- Document metadata ----
    tenant_name: str
    print_date: date


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class PartIdLabelParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} identifying the Parts row to label.
    Confirms the Part exists in the requesting user's tenant.
    The adapter re-queries with an explicit tenant filter for
    defense-in-depth.

    Parts uses a UUID primary key (SecureModel default), so the
    id field is a UUIDField, not IntegerField.
    """

    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models.mes_lite import Parts

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = Parts.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"Part {value} not found.")
        return value


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class PartIdLabelAdapter(ReportAdapter):
    """
    Renders a 4"×2" thermal Part ID / WIP label for a single Part.

    The barcode encodes the serial number (ERP_id) for scanner capture.
    The QR code encodes a URL pointing to the part's detail page so shop
    floor personnel with phones can pull up full context instantly.
    """

    name = "part_id_label"
    title = "Part ID Label / WIP Tag"
    template_path = "part_id_label.typ"
    context_model_class = PartIdLabelContext
    param_serializer_class = PartIdLabelParamsSerializer

    def build_context(self, validated_params, user, tenant) -> PartIdLabelContext:
        from Tracker.models.mes_lite import Parts

        # tenant-safe: explicit tenant filter (defense-in-depth)
        part = (
            Parts.objects
            .filter(tenant=tenant)
            .select_related(
                "part_type",
                "work_order",
                "tenant",
            )
            .get(id=validated_params["id"])
        )
        return build_part_id_label_context(part, tenant)

    def get_filename(self, validated_params) -> str:
        return f"part_label_{validated_params.get('id', 'unknown')}.pdf"


def build_part_id_label_context(part, tenant) -> PartIdLabelContext:
    """Build a PartIdLabelContext for a single Parts instance.

    Shared by PartIdLabelAdapter (single) and PartIdLabelBatchAdapter
    (multi-page) so label appearance stays in lockstep.
    Caller is responsible for tenant filtering on the Parts query.
    """
    serial = part.ERP_id or ""
    part_number = part.part_type.name if part.part_type else "—"
    work_order_number = part.work_order.ERP_id if part.work_order else None

    revision: Optional[str] = None
    if part.part_type and getattr(part.part_type, "version", None):
        revision = f"Rev {part.part_type.version}"

    tenant_slug = getattr(tenant, "slug", None) or "example"
    qr_url = f"https://{tenant_slug}.ambactracker.example/parts/{part.id}"

    barcode_svg = render_barcode_svg(
        serial if serial else "UNKNOWN",
        module_height=6.0,
    )
    qr_svg = render_qr_svg(qr_url)

    return PartIdLabelContext(
        part_number=part_number,
        revision=revision,
        serial=serial,
        work_order_number=work_order_number,
        barcode_svg=barcode_svg,
        qr_svg=qr_svg,
        tenant_name=tenant.name,
        print_date=date.today(),
    )
