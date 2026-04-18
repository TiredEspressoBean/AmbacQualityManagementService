"""
Checking Aids Report adapter — PPAP Element 16.

A point-in-time snapshot of the measurement equipment used to verify
product conformance for a PPAP submission. Per AIAG PPAP, this establishes
**traceability** of the gages used — not a live calibration dashboard.

The listed gages are assumed to have been in calibration at the time the
PPAP measurements were taken; if they weren't, the PPAP submission would
be invalid. That means this report shows calibration *traceability*
(cert number, standards used, calibration date) rather than current status.

The PDF covers:
- Title: "Checking Aids / PPAP Element 16 — Measurement Equipment List"
- Header: part number + PPAP submission date + tenant
- Table: Gage ID | Description | Manufacturer | Model | Cal Cert # | Cal Date | Standards / Traceability
- Single signature block: Quality Manager attestation

For live calibration status (who's due, who's overdue), use the
Calibration Due Report instead.

This report takes no record ID — it is a tenant-wide aggregate. The param
serializer only verifies that the requesting user has a tenant context.

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream check.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class CheckingAidsItem(BaseModel):
    """One row in the checking aids table. Represents PPAP-time traceability,
    not live status."""

    gage_id: str                                 # serial number used as PPAP gage ID
    name: str                                    # equipment name
    equipment_type: Optional[str] = None         # equipment type name
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    cal_cert_number: Optional[str] = None        # certificate number for traceability
    cal_date: Optional[datetime.date] = None     # when it was calibrated (at PPAP time)
    standards_used: Optional[str] = None         # traceability statement (NIST etc.)


class CheckingAidsContext(BaseModel):
    """Top-level shape passed to the checking_aids.typ template."""

    submission_date: datetime.date              # PPAP submission date (defaults to today)
    tenant_name: str
    part_number: Optional[str] = None           # PPAP part number — optional
    items: list[CheckingAidsItem]
    total_count: int


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class CheckingAidsParamsSerializer(serializers.Serializer):
    """
    No record ID needed — this report aggregates all measurement equipment
    in the requesting user's tenant. Accepts an optional `part_number`
    query param to label the report for a specific PPAP submission.
    """

    part_number = serializers.CharField(required=False, allow_blank=True, default=None)

    def validate(self, attrs):
        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")

        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        return attrs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _today() -> datetime.date:
    return datetime.date.today()


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CheckingAidsAdapter(ReportAdapter):
    """
    Generates a PPAP-style Checking Aids list (Element 16) listing all
    measurement equipment in the tenant with calibration traceability info
    from the most recent calibration record.
    """

    name = "checking_aids"
    title = "Checking Aids"
    template_path = "checking_aids.typ"
    context_model_class = CheckingAidsContext
    param_serializer_class = CheckingAidsParamsSerializer

    def build_context(self, validated_params, user, tenant) -> CheckingAidsContext:
        from Tracker.models import CalibrationRecord
        from Tracker.models.mes_standard import Equipments

        today = _today()
        part_number = (validated_params or {}).get("part_number") or None
        if part_number == "":
            part_number = None

        # tenant-safe: explicit tenant filter (defense-in-depth)
        equipment_qs = (
            Equipments.objects
            .filter(tenant=tenant)
            .select_related("equipment_type")
            .order_by("name")
        )

        # Narrow to equipment types that require calibration (i.e. gages
        # used for measurement). Guard against deployments where the flag
        # doesn't exist on the schema.
        try:
            equipment_qs = equipment_qs.filter(
                equipment_type__requires_calibration=True
            )
        except Exception:
            pass

        items: list[CheckingAidsItem] = []

        for equip in equipment_qs:
            # Get the latest calibration record for this equipment
            # (defense-in-depth: filter by tenant again)
            latest_record: Optional[CalibrationRecord] = (
                CalibrationRecord.objects
                .filter(tenant=tenant, equipment=equip)
                .order_by("-calibration_date", "-id")
                .first()
            )

            cal_cert_number: Optional[str] = None
            cal_date: Optional[datetime.date] = None
            standards_used: Optional[str] = None

            if latest_record is not None:
                cal_cert_number = latest_record.certificate_number or None
                cal_date = latest_record.calibration_date
                standards_used = latest_record.standards_used or None

            items.append(CheckingAidsItem(
                gage_id=equip.serial_number or "",
                name=equip.name,
                equipment_type=(
                    equip.equipment_type.name
                    if equip.equipment_type else None
                ),
                manufacturer=equip.manufacturer or None,
                model=equip.model_number or None,
                cal_cert_number=cal_cert_number,
                cal_date=cal_date,
                standards_used=standards_used,
            ))

        # Sort alphabetically by equipment name
        items.sort(key=lambda r: r.name.lower())

        return CheckingAidsContext(
            submission_date=today,
            tenant_name=tenant.name,
            part_number=part_number,
            items=items,
            total_count=len(items),
        )

    def get_filename(self, validated_params) -> str:
        today = _today()
        part_number = (validated_params or {}).get("part_number") or None
        if part_number:
            safe_pn = part_number.replace("/", "-").replace(" ", "_")
            return f"checking_aids_{safe_pn}_{today.isoformat()}.pdf"
        return f"checking_aids_{today.isoformat()}.pdf"
