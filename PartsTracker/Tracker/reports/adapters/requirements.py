"""Sourcing & Production Requirements adapter.

A purchasing/production buy-and-build list: what open demand needs — purchased materials
to buy (with order-by dates), in-house components to produce, and tooling to procure.
Reuses `services.mes.requirements.sourcing_requirements` so the PDF matches the on-screen
report exactly. Tenant-wide aggregate — no record ID.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


class SourceRow(BaseModel):
    material: str
    qty_short: int
    need_by: Optional[datetime.date] = None
    lead_time_days: Optional[int] = None
    order_by: Optional[datetime.date] = None
    incoming_date: Optional[datetime.date] = None


class ProduceRow(BaseModel):
    work_order: str
    component: str
    qty: int
    need_by: Optional[datetime.date] = None
    status: str


class ToolingRow(BaseModel):
    fixture: str
    kind: str
    need_by: Optional[datetime.date] = None
    lead_time_days: Optional[int] = None
    order_by: Optional[datetime.date] = None


class RequirementsContext(BaseModel):
    generated_date: datetime.date
    tenant_name: str
    source: list[SourceRow] = Field(default_factory=list)
    produce: list[ProduceRow] = Field(default_factory=list)
    tooling: list[ToolingRow] = Field(default_factory=list)


class RequirementsParamsSerializer(serializers.Serializer):
    """No record ID — aggregates open demand for the requesting user's tenant."""

    def validate(self, attrs):
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        return attrs


class RequirementsAdapter(ReportAdapter):
    """Source / produce / tooling requirement lanes with lead-time-driven order-by dates."""

    name = "requirements"
    title = "Sourcing & Production Requirements"
    template_path = "requirements.typ"
    context_model_class = RequirementsContext
    param_serializer_class = RequirementsParamsSerializer

    def build_context(self, validated_params, user, tenant) -> RequirementsContext:
        from Tracker.services.mes.requirements import sourcing_requirements

        req = sourcing_requirements(tenant)
        return RequirementsContext(
            generated_date=datetime.date.today(),
            tenant_name=tenant.name,
            source=[SourceRow(**r) for r in req["source"]],
            produce=[ProduceRow(**r) for r in req["produce"]],
            tooling=[ToolingRow(**r) for r in req["tooling"]],
        )

    def get_filename(self, validated_params) -> str:
        return f"requirements_{datetime.date.today().isoformat()}.pdf"
