"""
Outbound shipment paperwork — the packing list and the Certificate of Conformance.

Both are built from one `CustomerShipment`: what left, grouped by order line and part
type, with every serial listed. Neither carries prices: invoicing belongs to the ERP,
whose paperwork number the shipment records as `reference`. Some customers' own
packing slips come from the ERP; the packing list here is for the ones that don't.

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


class ShipmentItem(BaseModel):
    order: Optional[str] = None
    line: Optional[int] = None
    part_type: str
    quantity: int
    serials: list[str] = []


class ShipmentDocumentContext(BaseModel):
    our_org: str
    shipment_number: str
    shipped_date: date
    customer_name: str
    customer_address: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    reference: Optional[str] = None
    expected_delivery: Optional[date] = None
    orders: list[str] = []
    items: list[ShipmentItem] = []
    total_units: int = 0
    shipped_by: Optional[str] = None
    issued_by: Optional[str] = None
    issued_date: date


class ShipmentParamsSerializer(serializers.Serializer):
    """{"shipment_id": <uuid>}"""
    shipment_id = serializers.UUIDField()

    def validate_shipment_id(self, value):
        from Tracker.models import CustomerShipment
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        if not CustomerShipment.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"Shipment {value} not found.")
        return value


def _name(user) -> Optional[str]:
    if user is None:
        return None
    return (user.get_full_name() or "").strip() or getattr(user, "email", None)


def build_shipment_document_context(shipment, tenant, user=None) -> ShipmentDocumentContext:
    """Caller is responsible for tenant filtering on the shipment query."""
    groups: dict = {}
    orders: list[str] = []
    for p in (shipment.parts.select_related(  # tenant-safe: reverse FK from a scoped shipment
            "part_type", "order", "work_order__related_order", "work_order__order_line")
            .order_by("ERP_id")):
        wo = p.work_order
        order = p.order or (wo.related_order if wo is not None else None)
        order_no = (order.order_number or order.name) if order is not None else None
        line = wo.order_line.line_number if wo is not None and wo.order_line_id else None
        key = (order_no or "", line or 0, p.part_type.name if p.part_type_id else "—")
        groups.setdefault(key, []).append(p.ERP_id)
        if order_no and order_no not in orders:
            orders.append(order_no)
    items = [ShipmentItem(order=k[0] or None, line=k[1] or None, part_type=k[2],
                          quantity=len(v), serials=v)
             for k, v in sorted(groups.items())]
    customer = shipment.customer
    return ShipmentDocumentContext(
        our_org=tenant.name,
        shipment_number=shipment.shipment_number,
        shipped_date=shipment.shipped_at.date(),
        customer_name=customer.name,
        customer_address=customer.address or None,
        carrier=shipment.carrier or None,
        tracking_number=shipment.tracking_number or None,
        reference=shipment.reference or None,
        expected_delivery=shipment.expected_delivery,
        orders=orders,
        items=items,
        total_units=sum(i.quantity for i in items),
        shipped_by=_name(shipment.shipped_by),
        issued_by=_name(user),
        issued_date=tenant_today(tenant),
    )


class _ShipmentAdapter(ReportAdapter):
    context_model_class = ShipmentDocumentContext
    param_serializer_class = ShipmentParamsSerializer

    def build_context(self, validated_params, user, tenant) -> ShipmentDocumentContext:
        from Tracker.models import CustomerShipment
        # tenant-safe: explicit tenant filter (defense-in-depth)
        shipment = (CustomerShipment.unscoped.filter(tenant=tenant)
                    .select_related("customer", "shipped_by")
                    .get(id=validated_params["shipment_id"]))
        return build_shipment_document_context(shipment, tenant, user)


class PackingListAdapter(_ShipmentAdapter):
    """What is in the box, for the customer's receiving. No prices."""

    name = "packing_list"
    title = "Packing List"
    template_path = "packing_list.typ"

    def get_filename(self, validated_params) -> str:
        return f"packing_list_{validated_params.get('shipment_id', 'unknown')}.pdf"


class ShipmentCocAdapter(_ShipmentAdapter):
    """Certificate of Conformance for everything on one shipment."""

    name = "shipment_coc"
    title = "Certificate of Conformance"
    template_path = "shipment_coc.typ"

    def get_filename(self, validated_params) -> str:
        return f"coc_{validated_params.get('shipment_id', 'unknown')}.pdf"
