"""
Calibration Certificate adapter.

A Calibration Certificate is the formal document produced after a calibration
event is performed on a piece of equipment. It records the result (PASS / FAIL /
LIMITED), traceability to national standards, and the identity of the instrument
under test.

The PDF covers:
- Header: certificate number, result badge, calibration date
- Equipment section: name, serial, manufacturer, model, type, location
- Calibration details: date, type, due date, performed by, external lab
- As-found / as-left: in-tolerance status, adjustments made
- Standards used (NIST traceability statement)
- Notes
- Signature block (Calibration Technician + Reviewing Authority)
- "End of Certificate" footer (ISO 17025 requirement)

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check. See Documents/TYPST_MIGRATION_PLAN.md "SPC service methods
and tenant scoping" for the rationale.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context model
# ---------------------------------------------------------------------------


class CalibrationCertificateContext(BaseModel):
    """Top-level shape passed to the calibration_certificate.typ template."""

    # ---- Certificate identity ----
    certificate_number: str

    # ---- Calibration event ----
    calibration_date: date
    due_date: date
    result: str                          # PASS / FAIL / LIMITED
    calibration_type: str                # SCHEDULED / INITIAL / AFTER_REPAIR / ...
    performed_by: str
    external_lab: str
    standards_used: str

    # ---- As-found / as-left ----
    as_found_in_tolerance: Optional[bool]
    adjustments_made: bool

    # ---- Notes ----
    notes: str

    # ---- Equipment under test ----
    equipment_name: str
    equipment_serial: str
    equipment_type: Optional[str]
    equipment_manufacturer: str
    equipment_model: str
    equipment_location: str

    # ---- Document metadata ----
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class CalibrationCertificateParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} and confirms the CalibrationRecord exists in
    the requesting user's tenant. Returns the id as a UUID in
    validated_data — the adapter re-queries with an explicit tenant
    filter for defense-in-depth.

    CalibrationRecord uses a UUID primary key (SecureModel default),
    so the id field is a UUIDField, not IntegerField.
    """

    id = serializers.UUIDField()

    def validate_id(self, value):
        from Tracker.models import CalibrationRecord

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        # tenant-safe: explicit tenant filter
        exists = CalibrationRecord.unscoped.filter(
            id=value, tenant=tenant
        ).exists()
        if not exists:
            raise serializers.ValidationError(
                f"Calibration record {value} not found."
            )
        return value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_name(user) -> Optional[str]:
    """Render a User FK as 'Full Name' or fallback to email/username."""
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", None)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CalibrationCertificateAdapter(ReportAdapter):
    """Renders a CalibrationRecord as a Calibration Certificate PDF."""

    name = "calibration_certificate"
    title = "Calibration Certificate"
    template_path = "calibration_certificate.typ"
    context_model_class = CalibrationCertificateContext
    param_serializer_class = CalibrationCertificateParamsSerializer

    def build_context(self, validated_params, user, tenant) -> CalibrationCertificateContext:
        from Tracker.models import CalibrationRecord

        # tenant-safe: explicit tenant filter (defense-in-depth)
        record = (
            CalibrationRecord.objects
            .filter(tenant=tenant)
            .select_related(
                "equipment__equipment_type",
                "tenant",
            )
            .get(id=validated_params["id"])
        )

        equipment = record.equipment
        equipment_type = equipment.equipment_type if equipment else None

        return CalibrationCertificateContext(
            certificate_number=record.certificate_number or f"CERT-{record.id}",

            calibration_date=record.calibration_date,
            due_date=record.due_date,
            result=record.result,
            calibration_type=record.calibration_type,
            performed_by=record.performed_by,
            external_lab=record.external_lab,
            standards_used=record.standards_used,

            as_found_in_tolerance=record.as_found_in_tolerance,
            adjustments_made=record.adjustments_made,

            notes=record.notes,

            equipment_name=equipment.name if equipment else "",
            equipment_serial=equipment.serial_number if equipment else "",
            equipment_type=equipment_type.name if equipment_type else None,
            equipment_manufacturer=equipment.manufacturer if equipment else "",
            equipment_model=equipment.model_number if equipment else "",
            equipment_location=equipment.location if equipment else "",

            tenant_name=record.tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        return f"calibration_certificate_{validated_params.get('id', 'unknown')}.pdf"
