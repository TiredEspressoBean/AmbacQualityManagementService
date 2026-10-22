"""
"Returned as received" — the paperwork for a customer's own unit going back unrepaired.

A repair-and-return unit whose over-and-above scope the customer declined is shipped
back as it came. It gets no Certificate of Conformance: nothing was made or repaired to
certify (user decision 2026-10-22). This note says what happened instead: the unit (its
own serial, plus our core number), the findings behind the scope that was declined, and
the customer's answer — who, how, and their reference — from `record_authorisation`.

Offered beside the packing list for a shipment carrying such a unit; the CoC lists only
the units it can certify.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.adapters.shipment_documents import ShipmentParamsSerializer, _name
from Tracker.services.core.clock import tenant_today

# A customer's own unit going back without the repair (shipped, or ready to ship).
UNREPAIRED_STATUSES = ('DECLINED', 'RETURNED_UNREPAIRED')


class ReturnedUnit(BaseModel):
    serial: Optional[str] = None
    core_number: str
    part_type: str
    order: Optional[str] = None
    findings: list[str] = []          # "<repair name>: <why>" for each declined repair
    answered_on: Optional[date] = None
    answered_by: Optional[str] = None
    method: Optional[str] = None
    reference: Optional[str] = None


class ReturnedAsReceivedContext(BaseModel):
    our_org: str
    shipment_number: str
    shipped_date: Optional[date] = None
    customer_name: str
    units: list[ReturnedUnit] = []
    issued_by: Optional[str] = None
    issued_date: date


def unrepaired_cores(shipment):
    """The declined repair-and-return units on a shipment."""
    from Tracker.models import Core
    return list(Core.objects.filter(  # tenant-safe: scoped by the shipment's parts
        part__customer_shipment=shipment, status__in=UNREPAIRED_STATUSES)
        .select_related('part__part_type', 'part__work_order__related_order', 'part__order')
        .order_by('core_number'))


def _declined_findings(core) -> list[str]:
    """What the customer was asked about and said no to: each raised code not approved,
    named, with the finding behind it."""
    from Tracker.models import RepairCode
    from Tracker.services.reman.repair_routing import codes_needing_approval, raised_codes

    # Only what needed their approval: routine operations (a flow test, the base rebuild)
    # were never in the question.
    asked = set(codes_needing_approval(core))
    why = {c: w for c, w in raised_codes(core).items() if c in asked}
    names = dict(RepairCode.objects  # tenant-safe: .objects auto-scopes
                 .filter(code__in=list(why), archived=False).values_list('code', 'name'))
    out = []
    for code, reasons in why.items():
        label = names.get(code) or code
        out.append(f"{label}: {'; '.join(str(r) for r in reasons)}" if reasons else label)
    return out


def build_returned_as_received_context(shipment, tenant, user=None) -> ReturnedAsReceivedContext:
    units = []
    for core in unrepaired_cores(shipment):
        p = core.part
        wo = p.work_order
        order = p.order or (wo.related_order if wo is not None else None)
        units.append(ReturnedUnit(
            serial=core.serial_number or None,
            core_number=core.core_number,
            part_type=p.part_type.name if p.part_type_id else "Unit",
            order=(order.order_number or order.name) if order is not None else None,
            findings=_declined_findings(core),
            answered_on=(core.authorisation_answered_at.date()
                         if core.authorisation_answered_at else None),
            answered_by=core.authorisation_contact or None,
            method=core.authorisation_method or None,
            reference=core.authorisation_reference or None,
        ))
    return ReturnedAsReceivedContext(
        our_org=tenant.name,
        shipment_number=shipment.shipment_number,
        shipped_date=shipment.shipped_at.date() if shipment.shipped_at else None,
        customer_name=shipment.customer.name,
        units=units,
        issued_by=_name(user),
        issued_date=tenant_today(tenant),
    )


class ReturnedAsReceivedAdapter(ReportAdapter):
    """For a customer's unit returned without repair at their request."""

    name = "returned_as_received"
    title = "Returned As Received"
    template_path = "returned_as_received.typ"
    context_model_class = ReturnedAsReceivedContext
    param_serializer_class = ShipmentParamsSerializer

    def build_context(self, validated_params, user, tenant) -> ReturnedAsReceivedContext:
        from Tracker.models import CustomerShipment
        # tenant-safe: explicit tenant filter (defense-in-depth)
        shipment = (CustomerShipment.unscoped.filter(tenant=tenant)
                    .select_related("customer")
                    .get(id=validated_params["shipment_id"]))
        return build_returned_as_received_context(shipment, tenant, user)

    def get_filename(self, validated_params) -> str:
        return f"returned_as_received_{validated_params.get('shipment_id', 'unknown')}.pdf"
