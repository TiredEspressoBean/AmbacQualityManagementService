"""
DWI operator-submit service.

When an operator completes a substep at runtime, the frontend POSTs a
single payload describing every capture they made (text, choice, photo,
measurement, status, signatures, defect findings, …). This service fans
that payload out into the right writes:

- Always writes a `SubstepResponse` row per capture (per-substep audit
  trail, keyed by `node_id`).
- For `MeasurementInput` captures: routes through `record_dwi_measurement`
  so the existing two-tier (StepExecutionMeasurement + optional
  QualityReports/MeasurementResult) logic fires.
- For QA-bundle captures (status / equipment_roles / personnel_roles /
  signatures / defects) when `substep.is_inspection_point=True`: finds or
  creates the substep's `QualityReports` row and populates the matching
  through tables (`QualityReportEquipment`, `QualityReportPersonnel`,
  `QualityReportDefect`).
- `PartAnnotation` is a marker — the existing `PartAnnotator` widget
  writes `HeatMapAnnotation` rows directly, so we only persist a
  `SubstepResponse` to record that the capture happened.
- Closes with a `SubstepCompletion` row marking the substep done.

Everything runs in a single transaction so partial submits don't leave the
substep half-captured.

Submit shape (frontend → backend):

    {
        "step_execution": "<uuid>",
        "notes": "optional operator notes",
        "signature_data": "base64png",          # if substep.requires_signature
        "verification_method": "PASSWORD",       # optional
        "marked_not_applicable": false,
        "captures": [
            {"node_id": "...", "kind": "text", "value_text": "..."},
            {"node_id": "...", "kind": "choice", "value_text": "..."},
            {"node_id": "...", "kind": "scan", "value_text": "..."},
            {"node_id": "...", "kind": "timer", "value_json": {...}},
            {"node_id": "...", "kind": "computed", "value_json": {...}},
            {"node_id": "...", "kind": "photo", "document_id": <id>},
            {"node_id": "...", "kind": "video", "document_id": <id>},
            {"node_id": "...", "kind": "file", "document_id": <id>},

            {"node_id": "...", "kind": "measurement",
                "measurement_definition_id": <id>,
                "value_numeric": 1.247, "value_string": "",
                "equipment_id": <id|null>},

            {"node_id": "...", "kind": "attestation",
                "confirm": true,
                "signature": {"user_id": .., "username": .., "signed_at": ..,
                              "data_uri": ".."}},

            {"node_id": "...", "kind": "status", "status": "PASS"},
            {"node_id": "...", "kind": "equipment_roles",
                "rows": [{"equipment_id": .., "role": "PRODUCTION", "notes": ".."}]},
            {"node_id": "...", "kind": "personnel_roles",
                "rows": [{"user_id": .., "role": "OPERATOR", "notes": ".."}]},
            {"node_id": "...", "kind": "signatures",
                "detected": {...}, "verified": {...}},
            {"node_id": "...", "kind": "defects",
                "rows": [{"error_type_id": .., "severity": "MAJOR",
                          "location": "..", "notes": "..", "count": 1}]},
            {"node_id": "...", "kind": "annotation",
                "model_id": "..", "annotation_count": 3}
        ]
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    BatchExecution,
    EquipmentRole,
    MeasurementDefinition,
    PersonnelRole,
    QualityReportDefect,
    QualityReportEquipment,
    QualityReportPersonnel,
    QualityReports,
    QualityErrorsList,
    StepExecution,
    Substep,
    SubstepCompletion,
    SubstepResponse,
    SubstepResponseKind,
)
from Tracker.services.qms.inline_capture import record_dwi_measurement


# -------------------------------------------------------------------------
# Public entrypoint
# -------------------------------------------------------------------------

@dataclass
class SubmitResult:
    """Lightweight return shape so callers (viewsets) don't need to import
    every model. Frontend rarely needs the full objects back — just
    confirmation that everything landed."""

    completion_id: str
    response_count: int
    quality_report_id: Optional[str]
    measurement_count: int


def submit_substep(
    *,
    substep: Substep,
    step_execution: Optional[StepExecution] = None,
    batch_execution: Optional[BatchExecution] = None,
    user,
    captures: list[dict[str, Any]],
    notes: str = "",
    signature_data: Optional[str] = None,
    signature_meaning: Optional[str] = None,
    verification_method: Optional[str] = None,
    marked_not_applicable: bool = False,
    na_reason_code: str = "",
    ip_address: Optional[str] = None,
    sample_number: Optional[int] = None,
) -> SubmitResult:
    """Persist an operator's submission for a single substep.

    See module docstring for the `captures` payload shape. All writes run in
    a single transaction.

    N/A validation: when `marked_not_applicable=True`, the substep config and
    the reason code are checked at the API boundary. Failures raise
    `ValidationError` so the operator gets a 400 instead of a silently-
    blocked lot at advancement time.
    """
    from django.core.exceptions import ValidationError

    # Exactly one execution target: per-part (step_execution) for SAMPLED
    # substeps, or per-batch (batch_execution) for BATCH-scope substeps (3a).
    if (step_execution is None) == (batch_execution is None):
        raise ValidationError(
            "submit_substep requires exactly one of step_execution / batch_execution."
        )
    is_batch = batch_execution is not None

    if marked_not_applicable:
        if substep.is_critical:
            raise ValidationError(
                f"Substep '{substep.title}' is critical; N/A is not permitted."
            )
        if not substep.allow_not_applicable:
            raise ValidationError(
                f"Substep '{substep.title}' is not configured to allow N/A."
            )
        if not (na_reason_code and na_reason_code.strip()):
            raise ValidationError(
                f"Substep '{substep.title}' requires an N/A reason code."
            )

    with transaction.atomic():
        # An inspection-point substep gets a QualityReports either way; the
        # keying mode differs. Batch → one report for the whole load (keyed on
        # batch_execution); per-part → one report per visit (keyed on
        # step_execution). ensure_quality_report picks the mode.
        if substep.is_inspection_point:
            report = ensure_quality_report(
                substep, step_execution, user, batch_execution=batch_execution,
            )
        else:
            report = None
        response_count = 0
        measurement_count = 0

        for cap in captures:
            kind = cap.get("kind")
            node_id = cap.get("node_id", "")
            if not node_id or not kind:
                continue

            if kind == "measurement":
                _handle_measurement(
                    cap, substep, step_execution, user, sample_number,
                    batch_execution=batch_execution,
                )
                # MeasurementInput doesn't write SubstepResponse — its row
                # lives in StepExecutionMeasurement (+ MeasurementResult via
                # promotion). We still count it for the response total so
                # the API caller sees what was processed.
                measurement_count += 1
                continue

            if kind == "harvested_components":
                if is_batch:
                    raise ValidationError(
                        "Harvested-component capture is per-part; not valid on a batch substep."
                    )
                # Reman teardown capture — write HarvestedComponent rows via
                # the dedicated service, then enrich the cap payload so the
                # SubstepResponse persists the created IDs for traceability.
                from Tracker.services.dwi.harvested_component_capture import (
                    create_harvested_components_from_capture,
                )
                result = create_harvested_components_from_capture(
                    step_execution=step_execution,
                    substep=substep,
                    rows=cap.get("rows") or [],
                    user=user,
                )
                cap = {**cap, **result}
                sr = _write_substep_response(
                    substep=substep,
                    step_execution=step_execution,
                    batch_execution=batch_execution,
                    user=user,
                    cap=cap,
                )
                if sr is not None:
                    response_count += 1
                continue

            sr = _write_substep_response(
                substep=substep,
                step_execution=step_execution,
                batch_execution=batch_execution,
                user=user,
                cap=cap,
            )
            if sr is not None:
                response_count += 1

            # Inspection-point side effects: structured-capture nodes
            # additionally populate the QualityReports / through tables.
            if report is not None:
                if kind == "status":
                    _apply_status(report, cap)
                elif kind == "equipment_roles":
                    _apply_equipment_roles(report, cap)
                elif kind == "personnel_roles":
                    _apply_personnel_roles(report, cap)
                elif kind == "signatures":
                    _apply_inspection_signatures(report, cap)
                elif kind == "defects":
                    _apply_defects(report, cap)
                elif kind == "attestation":
                    # Attestation signatures contribute to the QR personnel
                    # roster too — generic AttestationCheckpoint signatures
                    # land as WITNESS rows so we have an audit lineage.
                    _apply_attestation_signature(report, cap)

        # If the inspection-point QR is still PENDING after the capture
        # loop (i.e. no explicit InspectionStatus capture was submitted),
        # derive the status from annotation findings: any linked
        # HeatMapAnnotation rows → FAIL, else PASS. This keeps the
        # one-QR-per-substep "inspection session" model consistent — the
        # operator drops findings on the part and the report's pass/fail
        # falls out of the data instead of requiring a separate toggle.
        # Re-read status from the DB first: a measurement capture above may have
        # already resolved this QR to PASS/FAIL via record_dwi_measurement (and
        # an OOS reading may have fired auto_create_disposition). The in-memory
        # `report` is stale from ensure_quality_report, so without this refresh
        # the rollup would clobber that FAIL back to PASS — an NCR on a
        # PASS-reading report.
        if report is not None:
            report.refresh_from_db(fields=["status"])
        if report is not None and report.status == "PENDING":
            has_findings = (
                report.annotations.exists()
                or QualityReportDefect.objects.filter(report=report).exists()
            )
            QualityReports.objects.filter(pk=report.pk).update(
                status="FAIL" if has_findings else "PASS",
            )

        completion = _record_completion(
            substep=substep,
            step_execution=step_execution,
            batch_execution=batch_execution,
            user=user,
            notes=notes,
            signature_data=signature_data,
            signature_meaning=signature_meaning,
            verification_method=verification_method,
            marked_not_applicable=marked_not_applicable,
            na_reason_code=na_reason_code,
            ip_address=ip_address,
        )

        # NOTE: substep submit does NOT trigger advancement. Per the
        # MES behavior spec (Flow #1 + #12), captures are recorded and
        # this call returns. The operator's deliberate "Complete step"
        # action is THE advancement trigger — it runs the gate via
        # `try_advance_lot` synchronously from the complete_step viewset
        # action.

        return SubmitResult(
            completion_id=str(completion.id),
            response_count=response_count,
            quality_report_id=str(report.id) if report else None,
            measurement_count=measurement_count,
        )


# -------------------------------------------------------------------------
# QualityReports lifecycle
# -------------------------------------------------------------------------

def ensure_quality_report(substep, step_execution=None, user=None, *, batch_execution=None) -> QualityReports:
    """Find or create the QualityReports for this inspection event.

    Three keying modes, mutually exclusive:
    - **batch** (`batch_execution` set): one report per (batch_execution, substep)
      — BATCH-scope inspection substeps (a wash/heat-treat cycle inspected once
      for the whole load).
    - **part** (`step_execution` on a part): one report per (step_execution,
      substep). `record_dwi_measurement` finds-or-creates against the same pair,
      so both capture paths converge on one row — the partial unique constraints
      are what make that convergence a guarantee rather than a hope.
    - **receiving/OSP** (`step_execution` on a MaterialLot / shipment subject):
      converge on the subject-keyed report opened up front.

    `batch_execution` is keyword-only so the existing positional callers
    (`ensure_inspection_qr` viewset, part-path callers) keep working unchanged.

    Exposed via `POST /api/Substeps/{id}/ensure_inspection_qr/` so the
    operator runtime can pre-bind a QR to capture nodes (PartAnnotation,
    EquipmentRolesField, etc.) that need a known QR id before the
    operator finishes the substep. Idempotent — safe to call eagerly on
    substep open.
    """
    if batch_execution is not None:
        # BATCH-scope inspection — one report per (batch_execution, substep).
        report, _ = QualityReports.objects.get_or_create(
            batch_execution=batch_execution,
            substep=substep,
            defaults={
                "step": batch_execution.step,
                "detected_by": user,
                "sampling_method": "dwi_substep_submit",
                "status": "PENDING",
            },
        )
        return report

    if step_execution is None:
        return None  # type: ignore[return-value]

    if step_execution.part_id is not None:
        # Part DWI — one report per (step_execution, substep).
        report, _ = QualityReports.objects.get_or_create(
            step_execution=step_execution,
            substep=substep,
            defaults={
                "step": step_execution.step,
                "part": step_execution.part,
                "detected_by": user,
                "sampling_method": "dwi_substep_submit",
                "status": "PENDING",
            },
        )
        return report

    # Receiving-style DWI — the subject is a MaterialLot (Flow A incoming) or an
    # OutsideProcessShipment (Flow B subcontract return). Converge on the
    # subject-keyed inspection report (opened by receiving_inspection.
    # open_inspection / outside_process.receive_parts_back) — same row the
    # inline-capture path uses.
    from Tracker.models import MaterialLot, OutsideProcessShipment
    subj = step_execution.subject_object
    if isinstance(subj, MaterialLot):
        subject_filter = {"material_lot": subj}
    elif isinstance(subj, OutsideProcessShipment):
        subject_filter = {"osp_shipment": subj}
    else:
        # Cores and other subjects have no QualityReports promotion path.
        return None  # type: ignore[return-value]
    report = (
        QualityReports.objects
        .filter(step=step_execution.step, **subject_filter)
        .order_by("-created_at").first()
    )
    if report is None:
        report = QualityReports.objects.create(
            step=step_execution.step, detected_by=user,
            sampling_method="dwi_substep_submit", status="PENDING",
            **subject_filter,
        )
    return report


# -------------------------------------------------------------------------
# Per-kind handlers
# -------------------------------------------------------------------------

def _handle_measurement(cap, substep, step_execution, user, sample_number=None, *, batch_execution=None):
    """Route MeasurementInput captures through the existing two-tier service
    so Tier 1 (StepExecutionMeasurement) and Tier 2 (QualityReports +
    MeasurementResult) stay in lockstep with non-substep capture paths.

    ``sample_number`` tags the promoted MeasurementResult with which sampled
    unit (1..n) this reading belongs to — set by the receiving unit-by-unit
    runtime so the lot-acceptance evaluators (attribute defective-unit count,
    Z1.9 per-reading) can group/gather correctly. None for per-part DWI.

    ``batch_execution`` routes a BATCH-scope reading (one cycle measurement for
    the whole load) to the batch keying instead of step_execution."""
    md_id = cap.get("measurement_definition_id")
    if not md_id:
        return
    md = MeasurementDefinition.objects.filter(pk=md_id).first()
    if md is None:
        return

    value = cap.get("value_numeric")
    value_string = cap.get("value_string") or ""
    equipment_id = cap.get("equipment_id")
    equipment = None
    if equipment_id:
        from Tracker.models import Equipments
        equipment = Equipments.objects.filter(pk=equipment_id).first()

    record_dwi_measurement(
        step_execution=step_execution,
        substep=substep,
        measurement_definition=md,
        value=value,
        value_string=value_string,
        recorded_by=user,
        equipment=equipment,
        sample_number=sample_number,
        batch_execution=batch_execution,
    )


def _write_substep_response(*, substep, step_execution=None, batch_execution=None, user, cap) -> Optional[SubstepResponse]:
    """Generic per-node audit row. Upserts on (step_execution|batch_execution,
    substep, node_id) so re-submits replace the prior capture rather than
    duplicating. Exactly one of step_execution / batch_execution is set."""
    kind_raw = cap.get("kind")
    kind = _normalize_kind(kind_raw)
    if kind is None:
        return None

    document_id = cap.get("document_id")
    value_text = cap.get("value_text", "") or ""
    value_json: Optional[dict[str, Any]] = None

    # Structured captures store the full payload as JSON.
    if kind in {
        SubstepResponseKind.TIMER,
        SubstepResponseKind.COMPUTED,
        SubstepResponseKind.ATTESTATION,
        SubstepResponseKind.STATUS,
        SubstepResponseKind.EQUIPMENT_ROLES,
        SubstepResponseKind.PERSONNEL_ROLES,
        SubstepResponseKind.SIGNATURES,
        SubstepResponseKind.DEFECTS,
        SubstepResponseKind.ANNOTATION,
        SubstepResponseKind.HARVESTED_COMPONENTS,
    }:
        # Drop bookkeeping fields the model doesn't need; keep everything
        # else as a generic blob.
        value_json = {k: v for k, v in cap.items() if k not in {"node_id", "kind"}}

    sr, _ = SubstepResponse.objects.update_or_create(
        step_execution=step_execution,
        batch_execution=batch_execution,
        substep=substep,
        node_id=cap.get("node_id"),
        defaults={
            "kind": kind.value,
            "value_text": value_text,
            "value_document_id": document_id,
            "value_json": value_json,
            "responded_by": user,
        },
    )
    return sr


def _apply_status(report: QualityReports, cap) -> None:
    raw = (cap.get("status") or "").upper()
    if raw in {"PASS", "FAIL", "PENDING"}:
        QualityReports.objects.filter(pk=report.pk).update(status=raw)


def _apply_equipment_roles(report: QualityReports, cap) -> None:
    rows = cap.get("rows") or []
    valid_roles = {r.value for r in EquipmentRole}
    for row in rows:
        equipment_id = row.get("equipment_id")
        role = row.get("role")
        if not equipment_id or role not in valid_roles:
            continue
        QualityReportEquipment.objects.update_or_create(
            quality_report=report,
            equipment_id=equipment_id,
            role=role,
            defaults={"notes": row.get("notes") or ""},
        )


def _apply_personnel_roles(report: QualityReports, cap) -> None:
    rows = cap.get("rows") or []
    valid_roles = {r.value for r in PersonnelRole}
    for row in rows:
        user_id = row.get("user_id")
        role = row.get("role")
        if not user_id or role not in valid_roles:
            continue
        QualityReportPersonnel.objects.update_or_create(
            quality_report=report,
            user_id=user_id,
            role=role,
            defaults={
                "signed_at": row.get("signed_at"),
                "notes": row.get("notes") or "",
            },
        )


def _apply_inspection_signatures(report: QualityReports, cap) -> None:
    """Map the InspectionSignatures payload (detected / verified) to
    QualityReportPersonnel rows with the matching role + signed_at."""
    for which, role in (("detected", PersonnelRole.DETECTED_BY),
                        ("verified", PersonnelRole.VERIFIED_BY)):
        sig = cap.get(which)
        if not isinstance(sig, dict):
            continue
        user_id = sig.get("user_id")
        signed_at = sig.get("signed_at")
        if not user_id or not signed_at:
            continue
        QualityReportPersonnel.objects.update_or_create(
            quality_report=report,
            user_id=user_id,
            role=role.value,
            defaults={
                "signed_at": signed_at,
                # `data_uri` (signature stroke) stays in the SubstepResponse
                # JSON blob; we don't have a column for it on the through
                # table by design — keeps the role table light.
            },
        )


def _apply_attestation_signature(report: QualityReports, cap) -> None:
    """AttestationCheckpoint in signature mode contributes a WITNESS row.
    Confirm-mode attestations stay in SubstepResponse only — they're a
    boolean acknowledgement, not a personnel role."""
    sig = cap.get("signature")
    if not isinstance(sig, dict):
        return
    user_id = sig.get("user_id")
    signed_at = sig.get("signed_at")
    if not user_id or not signed_at:
        return
    QualityReportPersonnel.objects.update_or_create(
        quality_report=report,
        user_id=user_id,
        role=PersonnelRole.WITNESS.value,
        defaults={"signed_at": signed_at},
    )


def _apply_defects(report: QualityReports, cap) -> None:
    rows = cap.get("rows") or []
    for row in rows:
        error_type_id = row.get("error_type_id")
        if not error_type_id:
            continue
        if not QualityErrorsList.objects.filter(pk=error_type_id).exists():
            continue
        QualityReportDefect.objects.update_or_create(
            quality_report=report,
            error_type_id=error_type_id,
            defaults={
                "severity": row.get("severity") or "MAJOR",
                "location": row.get("location") or "",
                "notes": row.get("notes") or "",
                "count": row.get("count") or 1,
            },
        )


# -------------------------------------------------------------------------
# SubstepCompletion
# -------------------------------------------------------------------------

def _record_completion(
    *,
    substep,
    step_execution=None,
    batch_execution=None,
    user,
    notes,
    signature_data,
    signature_meaning,
    verification_method,
    marked_not_applicable,
    na_reason_code="",
    ip_address,
) -> SubstepCompletion:
    """Upsert the substep's completion row. Idempotent — re-submitting
    just updates the existing row in place rather than duplicating."""
    defaults = {
        "completed_by": user,
        "marked_not_applicable": marked_not_applicable,
        "na_reason_code": na_reason_code or "",
        "notes": notes or "",
    }
    if signature_data:
        defaults["signature_data"] = signature_data
        defaults["signature_meaning"] = signature_meaning or ""
        defaults["verified_at"] = timezone.now()
        if verification_method:
            defaults["verification_method"] = verification_method
        if ip_address:
            defaults["ip_address"] = ip_address

    completion, _ = SubstepCompletion.objects.update_or_create(
        step_execution=step_execution,
        batch_execution=batch_execution,
        substep=substep,
        defaults=defaults,
    )
    return completion


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

_KIND_MAP = {k.value: k for k in SubstepResponseKind}


def _normalize_kind(raw) -> Optional[SubstepResponseKind]:
    if not isinstance(raw, str):
        return None
    return _KIND_MAP.get(raw)
