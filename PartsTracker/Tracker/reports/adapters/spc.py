"""
SPC (Statistical Process Control) report adapter.

Renders a tenant-scoped SPC summary for a single MeasurementDefinition:
  - Header (process / step / measurement / spec limits)
  - Active baseline (frozen control limits) when present
  - Descriptive statistics over the chosen window
  - Process capability indices (Cp, Cpk, Pp, Ppk) + interpretation
  - The data points used (timestamp, part, value, in/out of spec)

Defense-in-depth: every ORM query in build_context() filters by tenant
explicitly, in addition to the param serializer's upstream check.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone
from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter


# Subgroup-size → d2 factor for within-subgroup σ estimation (AIAG SPC).
_D2_FACTORS: dict[int, float] = {
    2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534,
    7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078,
}


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class SpcSpec(BaseModel):
    nominal: Optional[float] = None
    upper_tol: Optional[float] = None
    lower_tol: Optional[float] = None
    usl: Optional[float] = None
    lsl: Optional[float] = None
    unit: str = ""


class SpcStatistics(BaseModel):
    count: int = 0
    mean: Optional[float] = None
    std_dev: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    within_spec_count: int = 0
    out_of_spec_count: int = 0


class SpcCapability(BaseModel):
    sample_size: int = 0
    subgroup_size: int = 0
    num_subgroups: int = 0
    std_dev_within: Optional[float] = None
    std_dev_overall: Optional[float] = None
    cp: Optional[float] = None
    cpk: Optional[float] = None
    pp: Optional[float] = None
    ppk: Optional[float] = None
    interpretation: str = ""


class SpcBaselineSummary(BaseModel):
    chart_type: str
    subgroup_size: int
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
    sample_count: int = 0
    notes: str = ""
    xbar_ucl: Optional[float] = None
    xbar_cl: Optional[float] = None
    xbar_lcl: Optional[float] = None
    range_ucl: Optional[float] = None
    range_cl: Optional[float] = None
    range_lcl: Optional[float] = None
    individual_ucl: Optional[float] = None
    individual_cl: Optional[float] = None
    individual_lcl: Optional[float] = None
    mr_ucl: Optional[float] = None
    mr_cl: Optional[float] = None


class SpcDataPoint(BaseModel):
    timestamp: datetime
    value: float
    part_erp_id: str = ""
    operator: Optional[str] = None
    is_within_spec: bool = True


class SpcReportContext(BaseModel):
    """Top-level shape passed to spc.typ."""

    # Header
    measurement_label: str
    process_name: str = ""
    step_name: str = ""
    chart_mode: str  # "xbar-r" / "xbar-s" / "i-mr" — display only
    window_days: int
    subgroup_size: int
    window_start: datetime
    window_end: datetime
    generated_at: datetime
    generated_by: Optional[str] = None
    tenant_name: str

    # Body
    spec: SpcSpec = Field(default_factory=SpcSpec)
    statistics: SpcStatistics = Field(default_factory=SpcStatistics)
    capability: SpcCapability = Field(default_factory=SpcCapability)
    baseline: Optional[SpcBaselineSummary] = None
    data_points: list[SpcDataPoint] = Field(default_factory=list)
    data_truncated: bool = False  # set when len(data_points) was capped


# ---------------------------------------------------------------------------
# Param serializer
# ---------------------------------------------------------------------------


_VALID_MODES = {"xbar-r", "xbar-s", "i-mr"}


class SpcReportParamsSerializer(serializers.Serializer):
    """
    Validates {measurement_id, days, subgroup_size, mode}.

    Also accepts the legacy keys {measurement, process_id, step_id, chart_mode}
    so a frontend mid-migration can call either shape — process_id and
    step_id are ignored (the measurement is the only required identifier).
    """

    measurement_id = serializers.UUIDField()
    days = serializers.IntegerField(required=False, default=90, min_value=1, max_value=3650)
    subgroup_size = serializers.IntegerField(required=False, default=5, min_value=2, max_value=25)
    mode = serializers.ChoiceField(
        required=False, default="xbar-r", choices=sorted(_VALID_MODES),
    )

    def validate_measurement_id(self, value):
        from Tracker.models import MeasurementDefinition

        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")

        exists = MeasurementDefinition.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"Measurement {value} not found.")
        return value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_name(user) -> Optional[str]:
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", None)


def _interpret_cpk(cp: Optional[float], cpk: Optional[float]) -> str:
    if cpk is None:
        return "Insufficient data for capability analysis."
    if cpk >= 1.33:
        text = "Process is capable and well-centered."
    elif cpk >= 1.0:
        text = "Process is marginally capable — monitor closely."
    elif cpk >= 0.67:
        text = "Process needs improvement — high defect risk."
    else:
        text = "Process is not capable — immediate action required."
    if cp is not None and cp > cpk + 0.2:
        text += " Process is not centered (Cp > Cpk)."
    return text


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class SpcAdapter(ReportAdapter):
    """Renders an SPC summary PDF for a single measurement definition."""

    name = "spc"
    title = "SPC Report"
    template_path = "spc.typ"
    context_model_class = SpcReportContext
    param_serializer_class = SpcReportParamsSerializer

    def build_context(self, validated_params, user, tenant) -> SpcReportContext:
        from Tracker.models import (
            MeasurementDefinition,
            MeasurementResult,
            ProcessStep,
        )
        from Tracker.models.spc import SPCBaseline

        measurement_id = validated_params["measurement_id"]
        days = validated_params.get("days", 90)
        subgroup_size = validated_params.get("subgroup_size", 5)
        mode = validated_params.get("mode", "xbar-r")

        # tenant-safe: explicit tenant filter (defense-in-depth)
        definition = (
            MeasurementDefinition.objects
            .filter(tenant=tenant)
            .select_related("step")
            .get(id=measurement_id)
        )

        end = timezone.now()
        start = end - timedelta(days=days)

        results = list(
            MeasurementResult.objects
            .filter(
                tenant=tenant,
                definition_id=measurement_id,
                value_numeric__isnull=False,
                report__created_at__gte=start,
                report__created_at__lte=end,
                archived=False,
            )
            .select_related("report", "report__part", "created_by")
            .order_by("report__created_at")
        )

        # Spec limits
        nominal = float(definition.nominal) if definition.nominal is not None else None
        upper_tol = float(definition.upper_tol) if definition.upper_tol is not None else None
        lower_tol = float(definition.lower_tol) if definition.lower_tol is not None else None
        usl = nominal + upper_tol if nominal is not None and upper_tol is not None else None
        lsl = nominal - lower_tol if nominal is not None and lower_tol is not None else None
        spec = SpcSpec(
            nominal=nominal,
            upper_tol=upper_tol,
            lower_tol=lower_tol,
            usl=usl,
            lsl=lsl,
            unit=definition.unit or "",
        )

        # Statistics
        values = [float(r.value_numeric) for r in results]
        stats = SpcStatistics()
        if values:
            n = len(values)
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / (n - 1) if n > 1 else 0.0
            std_dev = math.sqrt(variance)
            within = sum(1 for r in results if r.is_within_spec)
            stats = SpcStatistics(
                count=n,
                mean=round(mean, 6),
                std_dev=round(std_dev, 6),
                min=round(min(values), 6),
                max=round(max(values), 6),
                within_spec_count=within,
                out_of_spec_count=n - within,
            )

        # Capability
        capability = SpcCapability(
            sample_size=len(values), subgroup_size=subgroup_size,
        )
        if len(values) >= 2 and usl is not None and lsl is not None:
            n = len(values)
            mean = sum(values) / n
            std_overall = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
            d2 = _D2_FACTORS.get(subgroup_size, 2.326)
            ranges: list[float] = []
            for i in range(0, n - subgroup_size + 1, subgroup_size):
                sub = values[i:i + subgroup_size]
                if len(sub) == subgroup_size:
                    ranges.append(max(sub) - min(sub))
            std_within = (sum(ranges) / len(ranges)) / d2 if ranges else std_overall

            cp = cpk = pp = ppk = None
            if std_within > 0:
                cp = (usl - lsl) / (6 * std_within)
                cpk = min((usl - mean) / (3 * std_within), (mean - lsl) / (3 * std_within))
            if std_overall > 0:
                pp = (usl - lsl) / (6 * std_overall)
                ppk = min((usl - mean) / (3 * std_overall), (mean - lsl) / (3 * std_overall))

            capability = SpcCapability(
                sample_size=n,
                subgroup_size=subgroup_size,
                num_subgroups=len(ranges),
                std_dev_within=round(std_within, 6),
                std_dev_overall=round(std_overall, 6),
                cp=round(cp, 3) if cp is not None else None,
                cpk=round(cpk, 3) if cpk is not None else None,
                pp=round(pp, 3) if pp is not None else None,
                ppk=round(ppk, 3) if ppk is not None else None,
                interpretation=_interpret_cpk(cp, cpk),
            )

        # Active baseline (optional)
        baseline_obj = (
            SPCBaseline.objects
            .filter(tenant=tenant, measurement_definition_id=measurement_id, status="ACTIVE")
            .select_related("frozen_by")
            .first()
        )
        baseline = None
        if baseline_obj is not None:
            baseline = SpcBaselineSummary(
                chart_type=baseline_obj.chart_type,
                subgroup_size=baseline_obj.subgroup_size,
                frozen_at=baseline_obj.frozen_at,
                frozen_by=_user_name(baseline_obj.frozen_by),
                sample_count=baseline_obj.sample_count or 0,
                notes=baseline_obj.notes or "",
                xbar_ucl=_to_float(baseline_obj.xbar_ucl),
                xbar_cl=_to_float(baseline_obj.xbar_cl),
                xbar_lcl=_to_float(baseline_obj.xbar_lcl),
                range_ucl=_to_float(baseline_obj.range_ucl),
                range_cl=_to_float(baseline_obj.range_cl),
                range_lcl=_to_float(baseline_obj.range_lcl),
                individual_ucl=_to_float(baseline_obj.individual_ucl),
                individual_cl=_to_float(baseline_obj.individual_cl),
                individual_lcl=_to_float(baseline_obj.individual_lcl),
                mr_ucl=_to_float(baseline_obj.mr_ucl),
                mr_cl=_to_float(baseline_obj.mr_cl),
            )

        # Process name lookup (a Step can belong to multiple processes; take the first).
        # ProcessStep has no tenant column of its own — enforce the boundary by
        # filtering on the parent Process's tenant.
        process_name = ""
        if definition.step_id:
            ps = (
                ProcessStep.objects
                .filter(step_id=definition.step_id, process__tenant=tenant)
                .select_related("process")
                .first()
            )
            if ps and ps.process:
                process_name = ps.process.name

        # Cap data points to keep PDF size reasonable
        max_rows = 500
        truncated = len(results) > max_rows
        rows = results[:max_rows]
        data_points = [
            SpcDataPoint(
                timestamp=r.report.created_at,
                value=float(r.value_numeric),
                part_erp_id=(r.report.part.ERP_id if r.report.part else "") or "",
                operator=_user_name(r.created_by),
                is_within_spec=r.is_within_spec,
            )
            for r in rows
        ]

        return SpcReportContext(
            measurement_label=definition.label,
            process_name=process_name,
            step_name=definition.step.name if definition.step else "",
            chart_mode=mode,
            window_days=days,
            subgroup_size=subgroup_size,
            window_start=start,
            window_end=end,
            generated_at=timezone.now(),
            generated_by=_user_name(user),
            tenant_name=tenant.name,
            spec=spec,
            statistics=stats,
            capability=capability,
            baseline=baseline,
            data_points=data_points,
            data_truncated=truncated,
        )

    def get_filename(self, validated_params) -> str:
        return f"spc_{validated_params.get('measurement_id', 'unknown')}.pdf"


def _to_float(v) -> Optional[float]:
    return float(v) if v is not None else None
