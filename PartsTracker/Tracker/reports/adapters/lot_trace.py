"""
Lot trace report — one material lot's two-way trace, as paper for an auditor or a recall.

Backward: where the lot came from (supplier, their lot, heat, PO, source, the lot it was
split from). Forward: every part a step drew it into, up through the assemblies those
went into, to the work order, order and customer — and whether each has shipped. Built
from services/mes/lot_trace.trace_lot, the same answer the lot page shows.

Forward trace is only as complete as consumption recording; the report says so.

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


class TraceUseRow(BaseModel):
    lot_number: str
    used: str
    step: Optional[str] = None
    part: Optional[str] = None
    built_into: Optional[str] = None
    work_order: Optional[str] = None
    order: Optional[str] = None
    customer: Optional[str] = None
    shipped: Optional[str] = None


class LotTraceContext(BaseModel):
    our_org: str
    lot_number: str
    item_name: str
    status: str
    quantity: str
    supplier: Optional[str] = None
    supplier_lot_number: Optional[str] = None
    heat_number: Optional[str] = None
    source_type: Optional[str] = None
    erp_po: Optional[str] = None
    received_date: Optional[date] = None
    parent_lot_number: Optional[str] = None
    split_lots: list[str] = []
    uses: list[TraceUseRow] = []
    customers: list[str] = []
    issued_by: Optional[str] = None
    issued_date: date


class LotTraceParamsSerializer(serializers.Serializer):
    """{"lot_id": <uuid>}"""
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
    text = f"{v:f}" if not isinstance(v, (int, float)) else str(v)
    return text.rstrip("0").rstrip(".") if "." in text else text


def build_lot_trace_context(lot, tenant, user=None) -> LotTraceContext:
    """Caller is responsible for tenant filtering on the MaterialLot query."""
    from Tracker.services.mes.lot_trace import trace_lot
    t = trace_lot(lot)
    b = t["backward"]
    unit = lot.unit_of_measure or ""
    uses = []
    for u in t["forward"]:
        top = u["built_into"][-1] if u["built_into"] else u["part"]
        uses.append(TraceUseRow(
            lot_number=u["lot_number"], used=f"{_num(u['quantity'])} {unit}".strip(), step=u["step"],
            part=(u["part"] or {}).get("erp_id"),
            built_into=" > ".join(a["erp_id"] for a in u["built_into"]) or None,
            work_order=(top or {}).get("work_order"), order=(top or {}).get("order"),
            customer=(top or {}).get("customer"),
            shipped=(f"{top['shipment']} · {top['shipped_at']:%Y-%m-%d}" if top and top.get("shipment") else None),
        ))
    name = None
    if user is not None:
        name = (user.get_full_name() or "").strip() or getattr(user, "email", None)
    return LotTraceContext(
        our_org=tenant.name, lot_number=lot.lot_number, item_name=lot.item_name or "—",
        status=lot.get_status_display(), quantity=f"{_num(lot.quantity)} {unit}".strip(),
        supplier=b["supplier"], supplier_lot_number=b["supplier_lot_number"],
        heat_number=b["heat_number"], source_type=b["source_type"], erp_po=b["erp_po"],
        received_date=b["received_date"], parent_lot_number=b["parent_lot_number"],
        split_lots=[s["lot_number"] for s in b["split_lots"]],
        uses=uses, customers=t["customers"], issued_by=name, issued_date=tenant_today(tenant))


class LotTraceAdapter(ReportAdapter):
    """One lot's backward and forward trace."""

    name = "lot_trace"
    title = "Lot Trace"
    template_path = "lot_trace.typ"
    context_model_class = LotTraceContext
    param_serializer_class = LotTraceParamsSerializer

    def build_context(self, validated_params, user, tenant) -> LotTraceContext:
        from Tracker.models import MaterialLot
        # tenant-safe: explicit tenant filter (defense-in-depth)
        lot = (MaterialLot.unscoped.filter(tenant=tenant)
               .select_related("material", "material_type", "supplier", "parent_lot")
               .get(id=validated_params["lot_id"]))
        return build_lot_trace_context(lot, tenant, user)

    def get_filename(self, validated_params) -> str:
        return f"lot_trace_{validated_params.get('lot_id', 'unknown')}.pdf"
