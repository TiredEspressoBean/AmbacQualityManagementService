"""
SCAR (Supplier Corrective Action Request) report adapter.

A SCAR is a CAPA of type ``SUPPLIER`` raised against a supplier and *sent to
them*: it states the nonconformance we found and requests a structured
(8D-style) corrective-action response by a due date. This is the supplier-
facing artifact — our problem statement + immediate containment, followed by
a response form the supplier completes and returns.

Distinct from the internal ``capa_report`` (which dumps our own RCA, tasks,
and verification): the SCAR shows the request and a blank response section,
not our internal action plan.

Defense-in-depth: build_context() filters by tenant explicitly, in addition
to the param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


class ScarContext(BaseModel):
    """Top-level shape passed to the scar.typ template."""
    scar_number: str
    supplier_name: str
    issued_by_org: str
    issued_by_person: Optional[str] = None
    issued_date: date
    response_due_date: Optional[date] = None
    severity: str
    status: str
    problem_statement: str = ""
    immediate_action: str = ""


class ScarParamsSerializer(serializers.Serializer):
    """Accepts {"id": <uuid>} and confirms the CAPA exists in the requesting
    user's tenant. The adapter re-queries with an explicit tenant filter."""
    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models.qms import CAPA

        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        if not CAPA.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"CAPA {value} not found.")
        return value


def _user_name(user) -> Optional[str]:
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", None)


class ScarReportAdapter(ReportAdapter):
    """Renders a supplier CAPA as a supplier-facing SCAR (request + response form)."""

    name = "scar"
    title = "Supplier Corrective Action Request"
    template_path = "scar.typ"
    context_model_class = ScarContext
    param_serializer_class = ScarParamsSerializer
    classification_default = "CONFIDENTIAL"

    def build_context(self, validated_params, user, tenant) -> ScarContext:
        from Tracker.models.qms import CAPA

        capa = (
            CAPA.unscoped
            .filter(tenant=tenant)
            .select_related("supplier", "initiated_by", "tenant")
            .get(id=validated_params["id"])
        )
        # Present the supplier-facing number as SCAR-… (the canonical record stays
        # the CAPA; supplier CAPA numbers are "CAPA-SU-YYYY-NNN").
        scar_number = capa.capa_number.replace("CAPA-SU-", "SCAR-").replace("CAPA-", "SCAR-")
        return ScarContext(
            scar_number=scar_number,
            supplier_name=capa.supplier.name if capa.supplier_id else "-",
            issued_by_org=capa.tenant.name,
            issued_by_person=_user_name(capa.initiated_by),
            issued_date=capa.initiated_date,
            response_due_date=capa.due_date,
            severity=capa.severity,
            status=capa.status,
            problem_statement=capa.problem_statement or "",
            immediate_action=capa.immediate_action or "",
        )

    def get_filename(self, validated_params) -> str:
        return f"scar_{validated_params.get('id', 'unknown')}.pdf"
