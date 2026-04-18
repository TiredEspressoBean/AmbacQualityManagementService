"""
Calibration Due Report adapter.

A Calibration Due Report is a planning document listing all equipment in the
tenant that is due or overdue for calibration. It is sorted by due date
ascending so overdue items appear first, giving the calibration coordinator
an immediate action list.

The PDF covers:
- Title block with generated date and tenant name
- Summary bar: total equipment tracked, overdue count, due-soon count
- Table: Equipment | Serial | Type | Location | Last Cal | Due Date | Days | Status
- Status badges: OVERDUE (red), DUE_SOON (amber), CURRENT (green)

This report takes no record ID — it is a tenant-wide aggregate. The param
serializer only verifies that the requesting user has a tenant context.

Defense-in-depth: every ORM query in build_context() filters by
tenant explicitly, in addition to the param serializer's upstream
check. See Documents/TYPST_MIGRATION_PLAN.md "SPC service methods
and tenant scoping" for the rationale.
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


class CalibrationDueItem(BaseModel):
    """One row in the calibration due table."""

    equipment_name: str
    equipment_serial: str
    equipment_type: Optional[str] = None
    location: str
    last_cal_date: datetime.date
    due_date: datetime.date
    days_until_due: int          # negative = overdue
    status: str                  # CURRENT / DUE_SOON / OVERDUE
    last_result: str             # PASS / FAIL / LIMITED


class CalibrationDueContext(BaseModel):
    """Top-level shape passed to the calibration_due.typ template."""

    generated_date: datetime.date
    items: list[CalibrationDueItem]
    total_equipment: int
    overdue_count: int
    due_soon_count: int          # due within 30 days (but not yet overdue)
    tenant_name: str


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class CalibrationDueParamsSerializer(serializers.Serializer):
    """
    No record ID needed — this report aggregates all equipment in the
    requesting user's tenant.  The only validation required is that the
    user has a tenant context; if they do, build_context() can proceed.
    """

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

_DUE_SOON_THRESHOLD = 30  # days


def _calibration_status(days_until_due: int) -> str:
    if days_until_due < 0:
        return "OVERDUE"
    if days_until_due <= _DUE_SOON_THRESHOLD:
        return "DUE_SOON"
    return "CURRENT"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CalibrationDueAdapter(ReportAdapter):
    """
    Generates a tenant-wide Calibration Due Report listing all equipment
    with an outstanding or upcoming calibration requirement.
    """

    name = "calibration_due"
    title = "Calibration Due Report"
    template_path = "calibration_due.typ"
    context_model_class = CalibrationDueContext
    param_serializer_class = CalibrationDueParamsSerializer

    def build_context(self, validated_params, user, tenant) -> CalibrationDueContext:
        from Tracker.models import CalibrationRecord
        from Tracker.models.mes_standard import Equipments

        today = datetime.date.today()

        # tenant-safe: explicit tenant filter (defense-in-depth)
        # Fetch all equipment in this tenant that have at least one
        # CalibrationRecord, so we only surface tracked instruments.
        equipment_qs = (
            Equipments.objects
            .filter(tenant=tenant)
            .select_related("equipment_type")
            .order_by("name")
        )

        items: list[CalibrationDueItem] = []

        for equip in equipment_qs:
            # Get the latest calibration record for this equipment
            latest_record: Optional[CalibrationRecord] = (
                CalibrationRecord.objects
                .filter(tenant=tenant, equipment=equip)
                .order_by("-calibration_date", "-id")
                .first()
            )

            if latest_record is None:
                # Equipment has never been calibrated — skip it;
                # the scheduler/planner manages first-time calibrations.
                continue

            days_until_due = (latest_record.due_date - today).days
            status = _calibration_status(days_until_due)

            items.append(CalibrationDueItem(
                equipment_name=equip.name,
                equipment_serial=equip.serial_number or "",
                equipment_type=(
                    equip.equipment_type.name
                    if equip.equipment_type else None
                ),
                location=equip.location or "",
                last_cal_date=latest_record.calibration_date,
                due_date=latest_record.due_date,
                days_until_due=days_until_due,
                status=status,
                last_result=latest_record.result,
            ))

        # Sort overdue items first (most overdue to least), then due-soon,
        # then current — all sorted by due_date ascending within each group.
        items.sort(key=lambda r: r.due_date)

        overdue_count = sum(1 for r in items if r.status == "OVERDUE")
        due_soon_count = sum(1 for r in items if r.status == "DUE_SOON")

        return CalibrationDueContext(
            generated_date=today,
            items=items,
            total_equipment=len(items),
            overdue_count=overdue_count,
            due_soon_count=due_soon_count,
            tenant_name=tenant.name,
        )

    def get_filename(self, validated_params) -> str:
        today = datetime.date.today()
        return f"calibration_due_report_{today.isoformat()}.pdf"
