"""Operator Hours adapter.

A payroll-facing labor report: per shop-floor operator, hours worked over a date range —
on-shift (attendance) and direct (job) hours — from TimeEntry. Reuses the same
`services.mes.labor_report.operator_hours` logic the on-screen report uses, so the PDF and
the screen never diverge.

Params: `start` and `end` dates (the pay period / window). No record ID.
"""
from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


class LaborHoursRow(BaseModel):
    name: str
    on_shift_hours: float
    direct_hours: float


class LaborHoursContext(BaseModel):
    generated_date: datetime.date
    start_date: datetime.date
    end_date: datetime.date
    tenant_name: str
    rows: list[LaborHoursRow] = Field(default_factory=list)
    total_on_shift: float
    total_direct: float


class LaborHoursParamsSerializer(serializers.Serializer):
    """Date-range params. The window is tenant-wide over shop-floor operators."""
    start = serializers.DateField()
    end = serializers.DateField()

    def validate(self, attrs):
        if attrs["end"] < attrs["start"]:
            raise serializers.ValidationError("end must be on or after start.")
        return attrs


class LaborHoursAdapter(ReportAdapter):
    """Per-operator shop hours over a window — attendance + direct job time."""

    name = "labor_hours"
    title = "Operator Hours"
    template_path = "labor_hours.typ"
    context_model_class = LaborHoursContext
    param_serializer_class = LaborHoursParamsSerializer

    def build_context(self, validated_params, user, tenant) -> LaborHoursContext:
        from django.utils import timezone
        from Tracker.services.mes.labor_report import operator_hours

        start_d: datetime.date = validated_params["start"]
        end_d: datetime.date = validated_params["end"]
        # operator_hours takes aware datetimes; cover the full end day.
        start_dt = timezone.make_aware(datetime.datetime.combine(start_d, datetime.time.min))
        end_dt = timezone.make_aware(
            datetime.datetime.combine(end_d + datetime.timedelta(days=1), datetime.time.min))

        rows_raw = operator_hours(tenant, start_dt, end_dt)
        rows = [LaborHoursRow(name=r["name"], on_shift_hours=r["on_shift_hours"],
                              direct_hours=r["direct_hours"]) for r in rows_raw]
        return LaborHoursContext(
            generated_date=datetime.date.today(),
            start_date=start_d, end_date=end_d,
            tenant_name=tenant.name,
            rows=rows,
            total_on_shift=round(sum(r.on_shift_hours for r in rows), 2),
            total_direct=round(sum(r.direct_hours for r in rows), 2),
        )

    def get_filename(self, validated_params) -> str:
        s = validated_params.get("start")
        e = validated_params.get("end")
        return f"operator_hours_{s}_{e}.pdf"
