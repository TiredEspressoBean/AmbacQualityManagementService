"""
Material Lot Label adapter — the tag a receiving clerk sticks on a lot at the dock.

Same 4"×2" stock and layout family as the Part ID label, so one thermal printer and
one roll of labels serve both. A shop with no label printer prints the ``sheet``
layout instead: ten 4"×2" labels to a US Letter page (Avery 5163 / 8163 geometry).

Compliance: ISO 9001 §8.5.2 — purchased material stays identified and traceable
from receipt. Like the part label this is PERMANENT: it carries what never changes
about the lot (what it is, where it came from, how much arrived, when) and never its
status — "Awaiting inspection" on a lot that was accepted last week is worse than no
label. Status is carried on the floor by hold tags and staging, as for parts.

Label content:
    - Item name (largest) and part number
    - Lot number, with a Code 128 barcode of it (any handheld scanner reads it)
    - QR code to the lot's page in UQMES (a phone camera reads it)
    - Supplier + supplier lot, heat number
    - Quantity received and unit, received date, use-by date when it has one
    - Tenant name + print date (footer, muted)

``copies`` prints several identical labels per lot — one lot arriving as six boxes.

Defense-in-depth: the ORM query in build_context() filters by tenant explicitly, in
addition to the param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from django.conf import settings
from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.services.barcodes import render_barcode_svg, render_qr_svg
from Tracker.services.core.clock import tenant_today

LAYOUTS = ("thermal", "sheet")


class MaterialLotLabelContext(BaseModel):
    item_name: str
    part_number: Optional[str] = None
    lot_number: str
    supplier_name: Optional[str] = None
    supplier_lot_number: Optional[str] = None
    heat_number: Optional[str] = None
    quantity: str               # "6000 EA" — formatted, trailing zeros dropped
    received_as: Optional[str] = None  # "3 boxes" when counted in the buying unit
    received_date: Optional[date] = None
    expiration_date: Optional[date] = None
    # Customer property: printed so nobody draws it into someone else's job.
    owner_name: Optional[str] = None

    barcode_svg: str
    qr_svg: str

    tenant_name: str
    print_date: date


class MaterialLotLabelBatchContext(BaseModel):
    layout: str
    labels: list[MaterialLotLabelContext]


class MaterialLotLabelParamsSerializer(serializers.Serializer):
    """{"lot_ids": [...], "copies": 1, "layout": "thermal" | "sheet"}"""

    lot_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, max_length=200)
    copies = serializers.IntegerField(min_value=1, max_value=50, default=1)
    layout = serializers.ChoiceField(choices=LAYOUTS, default="thermal")

    def validate_lot_ids(self, value):
        from Tracker.models import MaterialLot

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None))
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        found = set(MaterialLot.unscoped.filter(id__in=value, tenant=tenant)
                    .values_list("id", flat=True))
        missing = [str(v) for v in value if v not in found]
        if missing:
            raise serializers.ValidationError(f"Lots not found: {', '.join(missing)}")
        return value


def _qty(value) -> str:
    """6000.0000 → "6000"; 12.5000 → "12.5"."""
    if value is None:
        return ""
    text = f"{value:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def build_material_lot_label_context(lot, tenant) -> MaterialLotLabelContext:
    """One label for one lot. Caller is responsible for tenant filtering."""
    item = lot.item
    part_number = (getattr(item, "part_number", None) or getattr(item, "ERP_id", None)
                   or None) if item is not None else None
    received_as = None
    if lot.received_as_quantity is not None and lot.received_as_unit not in ("", "STOCK"):
        one, many = {"BOX": ("box", "boxes"), "LB": ("lb", "lb")}[lot.received_as_unit]
        received_as = f"{_qty(lot.received_as_quantity)} {one if lot.received_as_quantity == 1 else many}"
    qr_url = f"{settings.FRONTEND_URL.rstrip('/')}/production/material-lots/{lot.id}"
    return MaterialLotLabelContext(
        item_name=lot.item_name or "—",
        part_number=part_number,
        lot_number=lot.lot_number,
        supplier_name=lot.supplier.name if lot.supplier_id else None,
        supplier_lot_number=lot.supplier_lot_number or None,
        heat_number=lot.heat_number or None,
        quantity=f"{_qty(lot.quantity)} {lot.unit_of_measure}".strip(),
        received_as=received_as,
        received_date=lot.received_date,
        expiration_date=lot.expiration_date,
        owner_name=lot.owner.name if lot.owner_id else None,
        barcode_svg=render_barcode_svg(lot.lot_number or "UNKNOWN", module_height=6.0),
        qr_svg=render_qr_svg(qr_url),
        tenant_name=tenant.name,
        print_date=tenant_today(tenant),
    )


class MaterialLotLabelAdapter(ReportAdapter):
    """Lot labels for one or more material lots, ``copies`` of each, on thermal stock
    (one label per page) or a Letter sheet of ten."""

    name = "material_lot_label"
    title = "Material Lot Label"
    template_path = "material_lot_label.typ"
    context_model_class = MaterialLotLabelBatchContext
    param_serializer_class = MaterialLotLabelParamsSerializer

    def build_context(self, validated_params, user, tenant) -> MaterialLotLabelBatchContext:
        from Tracker.models import MaterialLot

        ids = validated_params["lot_ids"]
        # tenant-safe: explicit tenant filter (defense-in-depth)
        lots = {lot.id: lot for lot in MaterialLot.unscoped.filter(tenant=tenant, id__in=ids)
                .select_related("material", "material_type", "supplier")}
        copies = validated_params.get("copies", 1)
        labels = [build_material_lot_label_context(lots[i], tenant)
                  for i in ids if i in lots for _ in range(copies)]
        return MaterialLotLabelBatchContext(
            layout=validated_params.get("layout", "thermal"), labels=labels)

    def get_filename(self, validated_params) -> str:
        ids = validated_params.get("lot_ids") or []
        stem = f"lot_label_{ids[0]}" if len(ids) == 1 else f"lot_labels_{len(ids)}"
        return f"{stem}.pdf"
