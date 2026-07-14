"""
DWI inline measurement capture — two-tier write per architectural decision #21.

Routine `MeasurementInput` substep captures land as process data
(`StepExecutionMeasurement`). When the parent substep has
`is_inspection_point=True`, the capture additionally creates an inspection
record (`QualityReports` + `MeasurementResult`), firing the existing
`record_quality_report_side_effects()` pipeline: auto-quarantine on out-of-
spec, `ncr.opened` notification to QA Manager, sampling fallback,
analytics updates.

Design references:
- `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md` (decision #21)
- `services/qms/quality_report.py::record_quality_report_side_effects`

The semantic distinction (process data vs. inspection record) matches the
shape established MES/QMS systems (Plex, SAP QM, Aegis FactoryLogix, Siemens
Opcenter, iBASEt) use — AS9100 §8.5.1 and 21 CFR 820.80 treat in-process
monitoring and inspection-with-acceptance as separate activities. The
inspection-point flag on the substep keeps the audit meaning of
`QualityReports` sharp; auto-promoting every inline capture would dilute it.
"""
from __future__ import annotations

from typing import Optional

from django.db import transaction

from Tracker.models import (
    Equipments,
    MeasurementDefinition,
    MeasurementResult,
    QualityReports,
    StepExecution,
    StepExecutionMeasurement,
    Substep,
)
from Tracker.services.qms.quality_report import record_quality_report_side_effects


def record_dwi_measurement(
    step_execution: Optional[StepExecution] = None,
    substep: Substep = None,
    measurement_definition: MeasurementDefinition = None,
    value: Optional[float] = None,
    value_string: str = "",
    recorded_by=None,
    equipment: Optional[Equipments] = None,
    sample_number: Optional[int] = None,
    batch_execution=None,
) -> StepExecutionMeasurement:
    """Record a DWI MeasurementInput capture.

    Always writes a `StepExecutionMeasurement` row (Tier 1 — process data).
    If `substep.is_inspection_point` is True, additionally finds or creates a
    `QualityReports` row for this (step_execution, substep) tuple and attaches
    a `MeasurementResult` (Tier 2 — inspection record). The Tier 2 path fires
    `record_quality_report_side_effects()` when the report is created OR when
    a new measurement transitions the report into FAIL status.

    Args:
        step_execution: The StepExecution the operator is working when the
            measurement is captured. Per-part-per-step-per-visit, so per-part
            captures fall out naturally without needing a separate `part`
            argument.
        substep: The Substep the MeasurementInput node lives in. The
            `is_inspection_point` flag on this row drives the Tier 2 decision.
        measurement_definition: The spec the value is being compared to.
        value: Numeric reading. Either `value` or `value_string` should be set.
        value_string: Pass/fail or text-style reading. Set to "PASS" or "FAIL"
            for PASS_FAIL definitions.
        recorded_by: User capturing the measurement. Defaults to None (use the
            caller's request.user when invoked from a viewset).
        equipment: Optional gauge / fixture / instrument used.

    Returns:
        The `StepExecutionMeasurement` row that was created. Callers that need
        the Tier 2 report can query
        `QualityReports.objects.filter(step=..., part=...)` themselves.

    Raises:
        ValueError: If neither `value` nor `value_string` is provided.
    """
    if value is None and not value_string:
        raise ValueError(
            "record_dwi_measurement requires either `value` or `value_string`."
        )

    with transaction.atomic():
        # Tier 1: always write process data. SecureModel.save() auto-fills
        # tenant from the ContextVar; StepExecutionMeasurement.save() then
        # auto-evaluates is_within_spec from the definition. A reading targets
        # exactly one of step_execution / batch_execution (BATCH-scope readings
        # belong to the cycle, not to any one part).
        sem = StepExecutionMeasurement.objects.create(
            step_execution=step_execution,
            batch_execution=batch_execution,
            measurement_definition=measurement_definition,
            value=value,
            string_value=value_string,
            recorded_by=recorded_by,
            equipment=equipment,
            substep=substep,
        )

        # Tier 2: only when the substep is a binding inspection point.
        if substep.is_inspection_point:
            _promote_to_inspection_record(
                sem=sem,
                step_execution=step_execution,
                substep=substep,
                measurement_definition=measurement_definition,
                value=value,
                value_string=value_string,
                recorded_by=recorded_by,
                equipment=equipment,
                sample_number=sample_number,
                batch_execution=batch_execution,
            )

    return sem


def _promote_to_inspection_record(
    *,
    sem: StepExecutionMeasurement,
    step_execution: Optional[StepExecution],
    substep: Substep,
    measurement_definition: MeasurementDefinition,
    value: Optional[float],
    value_string: str,
    recorded_by,
    equipment: Optional[Equipments],
    sample_number: Optional[int] = None,
    batch_execution=None,
) -> None:
    """Find or create the QualityReports + create a MeasurementResult.

    Idempotent on the QualityReports lookup: one report per (step_execution,
    substep) — or (batch_execution, substep) for BATCH-scope readings —
    inspection event. Subsequent captures during the same substep attach as
    additional MeasurementResult rows under the existing report.

    Side effects (`record_quality_report_side_effects`) fire when:
    1. The QualityReports is created for the first time, OR
    2. A new MeasurementResult transitions the report's status into FAIL.

    Auto-quarantine, NCR notification, and sampling fallback are idempotent
    at the system level (setting same state again is a no-op; the
    `ncr.opened` event uses the QualityReports id as its idempotency key so
    repeated emits dedupe).
    """
    from Tracker.models import MaterialLot, OutsideProcessShipment

    if batch_execution is not None:
        # BATCH-scope reading: one report per (batch_execution, substep). The
        # cycle measurement (wash temp, cure time) belongs to the load, not a
        # part — so no auto-quarantine of an individual part here.
        step = batch_execution.step
        report_fields = {
            'batch_execution': batch_execution,
            'substep': substep,
        }
        report = (
            QualityReports.objects
            .filter(batch_execution=batch_execution, substep=substep)
            .first()
        )
    elif step_execution is not None and step_execution.part_id is not None:
        step = step_execution.step
        # Part DWI: one report per (step_execution, substep) inspection event.
        part = step_execution.part
        report_fields = {
            'part': part,
            'step_execution': step_execution,
            'substep': substep,
        }
        report = (
            QualityReports.objects
            .filter(step_execution=step_execution, substep=substep)
            .first()
        )
    else:
        # Receiving-style DWI: the subject is a MaterialLot (Flow A incoming) or
        # an OutsideProcessShipment (Flow B subcontract return). One inspection
        # per subject is opened up front (receiving_inspection.open_inspection /
        # outside_process.receive_parts_back), so reuse that subject-keyed report —
        # DWI captures append to it. Cores and other subjects have no
        # inspection-record promotion path in v1.
        step = step_execution.step
        subj = step_execution.subject_object
        if isinstance(subj, MaterialLot):
            report_fields = {'material_lot': subj}
            report = (
                QualityReports.objects
                .filter(step=step, material_lot=subj)
                .order_by('-created_at').first()
            )
        elif isinstance(subj, OutsideProcessShipment):
            report_fields = {'osp_shipment': subj}
            report = (
                QualityReports.objects
                .filter(step=step, osp_shipment=subj)
                .order_by('-created_at').first()
            )
        else:
            return

    is_new_report = report is None

    if is_new_report:
        # The measuring instrument is recorded on the StepExecutionMeasurement
        # (SEM.equipment) created by the caller — its metrology home; the report
        # carries equipment only via role-tagged QualityReportEquipment.
        report = QualityReports.objects.create(
            step=step,
            detected_by=recorded_by,
            sampling_method="inline_dwi",
            status="PENDING",  # set properly after the MeasurementResult is in
            **report_fields,
        )

    # Capture the report's status BEFORE adding the new measurement so we
    # can detect a PASS/PENDING → FAIL transition.
    prior_status = report.status

    # Auto-evaluates is_within_spec in MeasurementResult.save().
    if sample_number is not None:
        # Receiving unit-by-unit: exactly one reading per (report, definition, unit).
        # Idempotent — a re-flush (network retry, or an operator correcting a unit's
        # reading and re-submitting) UPDATES rather than appending a duplicate, which
        # would double-count the lot verdict.
        MeasurementResult.objects.update_or_create(
            report=report,
            definition=measurement_definition,
            sample_number=sample_number,
            defaults={
                "value_numeric": value,
                "value_pass_fail": value_string if value_string in ("PASS", "FAIL") else None,
                "created_by": recorded_by,
            },
        )
    else:
        # Part / single-pass DWI: multiple readings of one characteristic are legitimate
        # (re-measure, a late failing reading that flips the report to FAIL), so append.
        # (The operator runtime's flush-once guard covers retry duplication here.)
        MeasurementResult.objects.create(
            report=report,
            definition=measurement_definition,
            value_numeric=value,
            value_pass_fail=value_string if value_string in ("PASS", "FAIL") else None,
            created_by=recorded_by,
            sample_number=sample_number,
        )

    # Recompute report.status from the cumulative measurements: any out-of-
    # spec MeasurementResult → FAIL; otherwise PASS once any measurements
    # exist.
    new_status = _compute_report_status(report)
    if new_status != prior_status:
        report.status = new_status
        report.save(update_fields=["status"])

    # Fire side effects on first creation OR when the status transitions
    # into FAIL (auto-quarantine, ncr.opened, sampling fallback). Subsequent
    # measurements that keep the report in FAIL don't re-fire (would be
    # noise even though events are idempotent).
    #
    # Batch-cycle reports are excluded: every side effect here is part-scoped
    # (sampling-trigger state, auto-quarantine, sibling fallback-sampling), and
    # a batch report has no single part to react on — SamplingTriggerManager
    # would dereference a null part. A failed batch cycle is recorded as a FAIL
    # on the report (visible in the inbox); reacting to it is not v1 behavior.
    transitioning_into_fail = (prior_status != "FAIL" and new_status == "FAIL")
    if (is_new_report or transitioning_into_fail) and batch_execution is None:
        record_quality_report_side_effects(report)


def _compute_report_status(report: QualityReports) -> str:
    """Determine the QualityReports.status from its child MeasurementResults.

    - Any out-of-spec measurement → 'FAIL'
    - All in-spec, at least one present → 'PASS'
    - No measurements yet → 'PENDING' (shouldn't happen by the time we call
      this, but safe default)
    """
    measurements = list(report.measurements.all())
    if not measurements:
        return "PENDING"
    if any(m.is_within_spec is False for m in measurements):
        return "FAIL"
    return "PASS"