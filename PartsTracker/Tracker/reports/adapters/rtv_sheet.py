"""
Return-to-Vendor (RTV) sheet adapter — the paper that travels with rejected material
going back to the supplier.

It says what is coming back and why, so the supplier's receiving can match it to their
records: our lot and theirs, the item, how much, the PO it came in on, the disposition
and any SCAR raised. It carries NO prices or values — credit for returned goods is
settled in the ERP, which owns money (UQMES is not an ERP).

Defense-in-depth: build_context() filters by tenant explicitly, in addition to the
param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.services.core.clock import tenant_today


class RtvSheetContext(BaseModel):
    our_org: str
    supplier_name: Optional[str] = None
    lot_number: str
    supplier_lot_number: Optional[str] = None
    item_name: str
    part_number: Optional[str] = None
    heat_number: Optional[str] = None
    quantity: str
    erp_po: Optional[str] = None
    received_date: Optional[date] = None
    disposition_number: Optional[str] = None
    reason: str = ""
    scar_numbers: list[str] = []
    issued_by: Optional[str] = None
    issued_date: date


class RtvSheetParamsSerializer(serializers.Serializer):
    """{"lot_id": <uuid>} — a lot rejected to go back to its supplier."""
    lot_id = serializers.UUIDField()

    def validate_lot_id(self, value):
        from Tracker.models import MaterialLot
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        if not MaterialLot.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"Lot {value} not found.")
        return value


def _num(v) -> str:
    text = f"{v:f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def build_rtv_sheet_context(lot, tenant, user=None) -> RtvSheetContext:
    """Caller is responsible for tenant filtering on the MaterialLot query."""
    from Tracker.models import CAPA, QuarantineDisposition
    item = lot.item
    disposition = (QuarantineDisposition.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, material_lot=lot, disposition_type="RETURN_TO_SUPPLIER")
        .order_by("-created_at").first())
    # A split-off lot of bad pieces shares its parent's inspection, and so its SCAR.
    lot_ids = [lot.id] + ([lot.parent_lot_id] if lot.parent_lot_id else [])
    scars = list(CAPA.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, capa_type="SUPPLIER", quality_reports__material_lot_id__in=lot_ids)
        .values_list("capa_number", flat=True).distinct())
    name = None
    if user is not None:
        name = (user.get_full_name() or "").strip() or getattr(user, "email", None)
    qty = lot.quantity if disposition is None or disposition.quantity is None else disposition.quantity
    return RtvSheetContext(
        our_org=tenant.name,
        supplier_name=lot.supplier.name if lot.supplier_id else None,
        lot_number=lot.lot_number,
        supplier_lot_number=lot.supplier_lot_number or None,
        item_name=lot.item_name or "—",
        part_number=(getattr(item, "part_number", None) or getattr(item, "ERP_id", None) or None)
        if item is not None else None,
        heat_number=lot.heat_number or None,
        quantity=f"{_num(qty)} {lot.unit_of_measure}".strip(),
        erp_po=(f"{lot.erp_po_number}{' / ' + lot.erp_po_line if lot.erp_po_line else ''}"
                if lot.erp_po_number else None),
        received_date=lot.received_date,
        disposition_number=disposition.disposition_number if disposition else None,
        reason=(disposition.description if disposition else "") or "",
        scar_numbers=sorted(scars),
        issued_by=name,
        issued_date=tenant_today(tenant),
    )


class RtvSheetAdapter(ReportAdapter):
    """The return-to-vendor sheet for one rejected lot. No prices."""

    name = "rtv_sheet"
    title = "Return to Vendor"
    template_path = "rtv_sheet.typ"
    context_model_class = RtvSheetContext
    param_serializer_class = RtvSheetParamsSerializer

    def build_context(self, validated_params, user, tenant) -> RtvSheetContext:
        from Tracker.models import MaterialLot
        # tenant-safe: explicit tenant filter (defense-in-depth)
        lot = (MaterialLot.unscoped.filter(tenant=tenant)
               .select_related("material", "material_type", "supplier")
               .get(id=validated_params["lot_id"]))
        return build_rtv_sheet_context(lot, tenant, user)

    def get_filename(self, validated_params) -> str:
        return f"rtv_{validated_params.get('lot_id', 'unknown')}.pdf"
