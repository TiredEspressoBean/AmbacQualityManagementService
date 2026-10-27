"""
Over-and-above scope — what the shop sends a customer when teardown finds work beyond
the rebuild level they bought.

One repair-and-return unit: each repair awaiting their answer (or that a request would
ask about, while the unit is in rebuild), the work it is, the parts it needs, and the
finding behind each. Built from `release.over_and_above_scope`, which reads the same
services the authorisation flow does, so the paper and the hold agree on what is asked.

Scope only. UQMES does not price, quote or raise purchase orders: pricing happens in
the system that owns it. The customer's answer is recorded on the core
(`record_authorisation`) — the sheet leaves room for it and their reference, nothing more.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.reports.adapters.shipment_documents import _name
from Tracker.services.core.clock import tenant_today

# Where a unit can have a scope to ask about: in rebuild (before the request is sent) or
# waiting on the answer.
SCOPE_STATUSES = ('IN_REBUILD', 'AWAITING_AUTHORISATION')


class ScopePartRow(BaseModel):
    component: str
    part_number: Optional[str] = None
    position: Optional[str] = None
    finding: str
    source: str


class ScopeLineRow(BaseModel):
    code: str
    name: Optional[str] = None
    work: list[str] = []
    findings: list[str] = []
    parts: list[ScopePartRow] = []


class OverAndAboveScopeContext(BaseModel):
    our_org: str
    core_number: str
    serial: Optional[str] = None
    unit: str
    customer_name: Optional[str] = None
    order: Optional[str] = None
    received_date: Optional[date] = None
    entry_scope: Optional[str] = None
    awaiting: bool = False
    lines: list[ScopeLineRow] = []
    issued_by: Optional[str] = None
    issued_date: date


class CoreParamsSerializer(serializers.Serializer):
    """{"core_id": <uuid>} — a repair-and-return core in the requesting user's tenant."""
    core_id = serializers.UUIDField()

    def validate_core_id(self, value):
        from Tracker.models import Core
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        core = Core.unscoped.filter(id=value, tenant=tenant, archived=False).first()
        if core is None:
            raise serializers.ValidationError(f"Core {value} not found.")
        if not core.returns_to_customer:
            raise serializers.ValidationError(
                f"{core.core_number} is an exchange unit — it has no customer to ask.")
        if core.status not in SCOPE_STATUSES:
            raise serializers.ValidationError(
                f"{core.core_number} is {core.get_status_display()} — a scope is sent "
                "while the unit is in rebuild or awaiting the customer's answer.")
        return value


def build_over_and_above_scope_context(core, tenant, user=None) -> OverAndAboveScopeContext:
    """Raises ReportParamError when the unit has nothing to ask about."""
    from Tracker.reports.services.pdf_generator import ReportParamError
    from Tracker.services.reman.release import over_and_above_scope

    scope = over_and_above_scope(core)
    if scope is None:
        msg = (f"Every repair raised on {core.core_number} is pre-approved or was sold "
               "with its rebuild level, so there is nothing to authorise.")
        raise ReportParamError(msg, {"core_id": [msg]})

    part = core.part
    wo = part.work_order if part is not None else None
    order = (part.order or (wo.related_order if wo is not None else None)) if part else None
    return OverAndAboveScopeContext(
        our_org=tenant.name,
        core_number=core.core_number,
        serial=core.serial_number or None,
        unit=core.core_type.name,
        customer_name=core.customer.name if core.customer_id else None,
        order=(order.order_number or order.name) if order is not None else None,
        received_date=core.received_date,
        entry_scope=scope.entry_scope,
        awaiting=scope.awaiting,
        lines=[ScopeLineRow(
            code=line.code, name=line.name or None, work=line.work,
            findings=line.findings,
            parts=[ScopePartRow(component=p.component, part_number=p.part_number or None,
                                position=p.position or None, finding=p.finding,
                                source=p.source) for p in line.parts],
        ) for line in scope.lines],
        issued_by=_name(user),
        issued_date=tenant_today(tenant),
    )


class OverAndAboveScopeAdapter(ReportAdapter):
    """For a customer's unit whose teardown found work beyond what they bought."""

    name = "over_and_above_scope"
    title = "Over-and-Above Scope"
    template_path = "over_and_above_scope.typ"
    context_model_class = OverAndAboveScopeContext
    param_serializer_class = CoreParamsSerializer

    def build_context(self, validated_params, user, tenant) -> OverAndAboveScopeContext:
        from Tracker.models import Core
        # tenant-safe: explicit tenant filter (defense-in-depth)
        core = (Core.unscoped.filter(tenant=tenant)
                .select_related("customer", "core_type", "part__order",
                                "part__work_order__related_order")
                .get(id=validated_params["core_id"]))
        return build_over_and_above_scope_context(core, tenant, user)

    def get_filename(self, validated_params) -> str:
        return f"over_and_above_scope_{validated_params.get('core_id', 'unknown')}.pdf"
