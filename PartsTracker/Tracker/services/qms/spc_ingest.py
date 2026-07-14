"""Shared SPC data ingestion — the single source of truth for "which
measurements feed a control chart", used by both the live chart endpoints
(`viewsets/spc.py`) and the PDF report (`reports/adapters/spc.py`).

Two-tier read (architectural decision #21 in DIGITAL_WORK_INSTRUCTIONS_DESIGN):
  - `MeasurementResult` — inspection records (QC bench, FPI, and DWI
    inspection-point captures, which promote a reading into a QualityReport).
  - `StepExecutionMeasurement` — process data (DWI MeasurementInput captures at
    routine substeps, batch cycle readings, and the legacy direct-record
    viewset).

Dedup rule (why this module exists): an inspection-point DWI capture writes
BOTH a StepExecutionMeasurement (Tier 1) AND a promoted MeasurementResult
(Tier 2) for the same physical reading. Counting both double-counts it. So a
SEM is included only when it was NOT promoted — i.e. its substep is not an
inspection point (or it has no substep: the legacy / direct-record path, which
never promotes). The tiers are therefore disjoint by construction:
  MeasurementResult = inspection captures,
  StepExecutionMeasurement = everything else.

Batch process parameters (a wash/heat-treat cycle reading, keyed to a
BatchExecution) flow through whichever tier applies — batch readings on an
inspection substep via their MR, batch readings on a routine substep via the
SEM — with no part attribution, which is correct: a cycle value belongs to the
load, not one part.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SpcRow:
    """Normalized SPC data point, source-agnostic."""
    timestamp: datetime
    value: float
    is_within_spec: bool
    part_erp_id: str
    operator_name: Optional[str]


def _display_name(user) -> Optional[str]:
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return full.strip() or getattr(user, "email", None) or getattr(user, "username", None)


def collect_spc_rows(*, tenant, measurement_id, start: datetime, end: datetime) -> list[SpcRow]:
    """Read both measurement tiers for the window, dedup, normalize, sort.

    Tenant filter is explicit on both queries (defense-in-depth). Rows whose
    spec evaluation didn't run (``is_within_spec is None``) are dropped — they
    indicate partial-state seed/test data, not a real reading.
    """
    from Tracker.models import MeasurementResult, StepExecutionMeasurement

    inspection_rows = (
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
    )

    # Process data: exclude inspection-point SEMs — those are the same physical
    # reading as a promoted MeasurementResult above, so counting them would
    # double the point. SEMs with a null substep (legacy / direct-record) are
    # kept: they never promote, so they have no MR twin.
    process_rows = (
        StepExecutionMeasurement.objects
        .filter(
            tenant=tenant,
            measurement_definition_id=measurement_id,
            value__isnull=False,
            is_within_spec__isnull=False,
            recorded_at__gte=start,
            recorded_at__lte=end,
            archived=False,
        )
        .exclude(substep__is_inspection_point=True)
        .select_related(
            "step_execution",
            "step_execution__part",
            "recorded_by",
        )
    )

    rows: list[SpcRow] = []
    for mr in inspection_rows:
        rows.append(SpcRow(
            timestamp=mr.report.created_at,
            value=float(mr.value_numeric),
            is_within_spec=bool(mr.is_within_spec),
            part_erp_id=(mr.report.part.ERP_id if mr.report.part else "") or "",
            operator_name=_display_name(mr.created_by),
        ))
    for sem in process_rows:
        rows.append(SpcRow(
            timestamp=sem.recorded_at,
            value=float(sem.value),
            is_within_spec=bool(sem.is_within_spec),
            part_erp_id=(
                sem.step_execution.part.ERP_id
                if sem.step_execution and sem.step_execution.part
                else ""
            ) or "",
            operator_name=_display_name(sem.recorded_by),
        ))
    rows.sort(key=lambda r: r.timestamp)
    return rows
