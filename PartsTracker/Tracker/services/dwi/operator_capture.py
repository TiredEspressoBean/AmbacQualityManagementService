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
        # Signatures live on their own blocks now — see services.dwi.gate_signature.
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

from dataclasses import dataclass, field
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
    # Recorded, but worth telling the operator (e.g. a gauge past its calibration due
    # date). Not refusals — those raise ValidationError.
    warnings: list[str] = field(default_factory=list)


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
    preverified: bool = False,
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

    # Server-side sequencing gate. `Steps.sequencing_mode='sequential'` means a
    # substep can't be completed until the earlier *required* substeps are done —
    # previously a UI-only convenience, now enforced here so an API caller can't
    # jump the sequence. See `_enforce_sequencing`.
    _enforce_sequencing(substep, step_execution, batch_execution)
    if step_execution is not None and step_execution.part_id:
        from Tracker.services.reman.core_steps import assert_workable
        assert_workable(step_execution.part)

    # Signatures are per BLOCK, not per substep. A substep's body may carry
    # attestation blocks; one whose kind is 'signature' is signed where it sits,
    # with a drawing and the signer's own password, before the substep is
    # submitted (services.dwi.gate_signature). `requires_signature` is derived
    # from those blocks, so submitting checks they were signed rather than asking
    # for a signature all over again — which is what made an operator sign twice
    # on three of the four substeps that had both.
    #
    # The method recorded here is the summary the review list reads; the evidence
    # itself (who, when, meaning, IP, the drawing) is on each block's row.
    # `preverified` is for server-side callers replaying history (the demo seed).
    verification_method = None
    if substep.requires_signature and not marked_not_applicable and not preverified:
        from Tracker.services.dwi.gate_signature import unsigned_signature_blocks

        unsigned = unsigned_signature_blocks(substep, step_execution, batch_execution)
        if unsigned:
            raise ValidationError(
                "Sign " + ", ".join(f"'{label}'" for label in unsigned)
                + " before completing this substep.")
        verification_method = "PASSWORD"
    elif signature_data:
        verification_method = "NONE"

    # Substep "Not applicable" is retired (user decision 2026-10-20): a substep that
    # doesn't apply to some units is authored optional, and an observation is a choice
    # inside the capture. N/A rows already recorded are read and honoured as before.
    if marked_not_applicable:
        raise ValidationError(
            "Not-applicable is no longer supported; author the substep as optional, or "
            "capture the observation as a choice.")
    else:
        # Required-field capture gate. A substep marked N/A skips it (the whole
        # substep is declared inapplicable); otherwise every engineer-required
        # capture node must carry a satisfactory value in this payload.
        missing = find_missing_required(substep, captures, step_execution=step_execution)
        if missing:
            detail = '; '.join(f"{m['type']} ({m['reason']})" for m in missing[:5])
            more = '' if len(missing) <= 5 else f" (+{len(missing) - 5} more)"
            raise ValidationError(
                f"Substep '{substep.title}' has required fields not captured: {detail}{more}."
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
        warnings: list[str] = []

        for cap in captures:
            kind = cap.get("kind")
            node_id = cap.get("node_id", "")
            if not node_id or not kind:
                continue

            if kind == "measurement":
                warning = _handle_measurement(
                    cap, substep, step_execution, user, sample_number,
                    batch_execution=batch_execution,
                )
                if warning and warning not in warnings:
                    warnings.append(warning)
                # MeasurementInput doesn't write SubstepResponse — its row
                # lives in StepExecutionMeasurement (+ MeasurementResult via
                # promotion). We still count it for the response total so
                # the API caller sees what was processed.
                measurement_count += 1
                continue

            if kind == "component_install":
                if is_batch:
                    raise ValidationError(
                        "Component-install capture is per-unit; not valid on a batch substep."
                    )
                # Reman rebuild capture — record what went into each slot via the
                # install service, then persist the created usage ids with the response.
                if _replayed_rows(substep, step_execution, node_id, cap):
                    continue
                from Tracker.services.dwi.component_install_capture import (
                    install_components_from_capture,
                )
                try:
                    result = install_components_from_capture(
                        step_execution=step_execution,
                        substep=substep,
                        rows=cap.get("rows") or [],
                        user=user,
                    )
                except ValueError as exc:
                    raise ValidationError(str(exc)) from exc
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

            if kind == "rebuild_finding":
                if is_batch:
                    raise ValidationError(
                        "A rebuild finding is per-unit; not valid on a batch substep."
                    )
                # Proposals only — a lead applies or dismisses each (services/reman/findings).
                if _replayed_rows(substep, step_execution, node_id, cap):
                    continue
                from Tracker.services.reman.findings import record_findings_from_capture
                result = record_findings_from_capture(
                    step_execution, cap.get("rows") or [], user)
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

            if kind == "harvested_components":
                if is_batch:
                    raise ValidationError(
                        "Harvested-component capture is per-part; not valid on a batch substep."
                    )
                # Reman teardown capture — write HarvestedComponent rows via
                # the dedicated service, then enrich the cap payload so the
                # SubstepResponse persists the created IDs for traceability.
                if _replayed_rows(substep, step_execution, node_id, cap):
                    continue
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

            if kind in ("attestation", "signatures"):
                cap = _stamp_signers(cap, user=user, substep=substep, step_execution=step_execution,
                                     batch_execution=batch_execution)
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
                    for warning in _apply_equipment_roles(report, cap):
                        if warning not in warnings:
                            warnings.append(warning)
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
            # A real save, not a queryset .update(): the disposition signal and the
            # FAIL consequences (quarantine, ncr.opened) must see the transition.
            from Tracker.services.qms.quality_report import on_report_failed
            report.status = "FAIL" if has_findings else "PASS"
            report.save(update_fields=["status"])
            on_report_failed(report, "PENDING")

        # The report's defects and readings are in now; its disposition was opened
        # the moment it went FAIL, before them, and said only "Failed <step>".
        if report is not None and report.status == "FAIL":
            from Tracker.services.qms.disposition import refresh_disposition_description
            for disp in report.dispositions.exclude(current_state="CLOSED"):
                refresh_disposition_description(disp)

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

        # Committed now, so it's no longer work in progress: drop it from the draft
        # (same transaction, so a failed commit keeps the draft to resume from).
        if step_execution is not None:
            _drop_from_draft(step_execution, substep.id)

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
            warnings=warnings,
        )


# -------------------------------------------------------------------------
# Required-field enforcement
# -------------------------------------------------------------------------

def find_missing_required(substep, captures: list[dict[str, Any]],
                          step_execution=None) -> list[dict[str, str]]:
    """Server-side mirror of the FE `findMissingRequired` (build-captures.ts).

    Walks the substep's `body_blocks`, and for every capture node the engineer
    marked ``required`` (plus inspection-signature ``require_detected`` /
    ``require_verified``), verifies the operator's submitted `captures` payload
    carries a satisfactory value for it. Returns a list of ``{node_id, type,
    reason}`` for the nodes still missing — empty when everything required is
    present. The FE blocks "Confirm & next" on the same rule; this is the
    authoritative backstop so an API caller can't complete a substep with a
    required field blank.
    """
    nodes: list = []
    _collect_capture_nodes(substep.body_blocks, nodes)
    cap_by_node = {c.get("node_id"): c for c in captures if c.get("node_id")}

    out: list[dict[str, str]] = []
    for node_type, attrs in nodes:
        required = attrs.get("required") is True
        is_sig = node_type == "inspectionSignatures"
        require_detected = attrs.get("require_detected") is True
        require_verified = attrs.get("require_verified") is True
        # Strict teardown capture binds even when the node is not "required" (FE parity).
        strict_harvest = (node_type == "harvestedComponentCapture"
                          and attrs.get("strict_enumeration") is True)
        if not required and not (is_sig and (require_detected or require_verified))                 and not strict_harvest:
            continue
        node_id = attrs.get("node_id")
        cap = cap_by_node.get(node_id)
        if strict_harvest:
            reason = _strict_harvest_reason(cap, step_execution)
        else:
            reason = _capture_missing_reason(node_type, attrs, cap)
        if reason is not None:
            out.append({"node_id": str(node_id), "type": node_type, "reason": reason})
    return out


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _capture_missing_reason(node_type, attrs, cap) -> Optional[str]:
    """Return None if the submitted `cap` satisfies this required node, else a
    short reason. `cap` is the capture dict for this node_id (or None if the
    operator submitted nothing for it). Mirrors FE `checkSatisfied` semantics
    against the `buildCaptures` payload shape."""
    if node_type in ("textInput", "choiceInput", "scanInput"):
        if cap and _nonempty_str(cap.get("value_text")):
            return None
        return "No value captured"

    if node_type in ("photoCapture", "fileCapture"):
        if cap and (cap.get("document_id") or _nonempty_str(cap.get("value_text"))):
            return None
        return "No file uploaded"

    if node_type == "measurementInput":
        if cap and (cap.get("value_numeric") is not None
                    or _nonempty_str(cap.get("value_string"))):
            return None
        return "No measurement recorded"

    if node_type == "timer":
        return None if (cap and isinstance(cap.get("value_json"), dict)) else "Timer not run"

    if node_type == "computedValue":
        payload = cap.get("value_json") if cap else None
        if not isinstance(payload, dict):
            return "Computation not run"
        variables = attrs.get("variables") or []
        inputs = payload.get("inputs") or {}
        missing = [v.get("name") for v in variables
                   if v.get("name") not in inputs or inputs.get(v.get("name")) == ""]
        return None if not missing else f"Missing variables: {', '.join(m for m in missing if m)}"

    if node_type == "attestationCheckpoint":
        if not cap:
            return "Not confirmed"
        if attrs.get("kind") == "signature":
            return None if isinstance(cap.get("signature"), dict) else "Not signed"
        return None if cap.get("confirm") is True else "Not confirmed"

    if node_type == "qualityStatusField":
        if cap and _nonempty_str(cap.get("status")):
            return None
        return "Status not picked"

    if node_type in ("equipmentRolesField", "personnelRolesField", "errorTypesField"):
        min_rows = attrs.get("min_rows")
        min_rows = min_rows if isinstance(min_rows, int) and min_rows >= 0 else 1
        rows = cap.get("rows") if cap and isinstance(cap.get("rows"), list) else []
        return None if len(rows) >= min_rows else f"Needs at least {min_rows} row(s)"

    if node_type == "inspectionSignatures":
        r = cap or {}
        if attrs.get("require_detected") is True and not r.get("detected"):
            return "Detected-by signature missing"
        if attrs.get("require_verified") is True and not r.get("verified"):
            return "Verified-by signature missing"
        return None

    if node_type in ("harvestedComponentCapture", "componentInstallCapture", "rebuildFindingCapture"):
        rows = cap.get("rows") if cap and isinstance(cap.get("rows"), list) else []
        return None if rows else "No components recorded"

    # partAnnotation and unknown nodes: treated as satisfied (FE parity).
    return None


def _strict_harvest_reason(cap, step_execution) -> Optional[str]:
    """Strict teardown capture: every component the unit is EXPECTED to give up —
    its core type's disassembly BOM, per position — must be graded or marked missing.

    The authoritative check the FE mirrors, and the reason it has to live here: the
    client sends only the rows the operator recorded, so only the server can compare
    them against what was expected. Counted per (component, position), so two
    unpositioned nozzles need two rows.
    """
    from collections import Counter
    from Tracker.models import DisassemblyBOMLine
    from Tracker.services.reman.core_steps import core_of

    rows = cap.get("rows") if cap and isinstance(cap.get("rows"), list) else []
    core = core_of(step_execution.part) if (step_execution and step_execution.part_id) else None
    if core is None:
        return None if rows else "No components recorded"

    expected: Counter = Counter()
    for line in DisassemblyBOMLine.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            core_type_id=core.core_type_id, is_current_version=True, archived=False):
        positions = line.positions if isinstance(line.positions, list) else []
        for i in range(max(1, line.expected_qty or 1)):
            expected[(str(line.component_type_id), str(positions[i]) if i < len(positions) else '')] += 1
    recorded: Counter = Counter(
        (str(r.get("component_type_id") or ''), str(r.get("position") or ''))
        for r in rows
        if r.get("is_missing") is True or _nonempty_str(r.get("condition_grade"))
    )
    open_count = sum((expected - recorded).values())
    if open_count:
        return f"{open_count} expected component(s) not graded or marked missing"
    return None if (rows or not expected) else "No components recorded"


# -------------------------------------------------------------------------
# Sequencing enforcement
# -------------------------------------------------------------------------

def _enforce_sequencing(substep, step_execution=None, batch_execution=None) -> None:
    """Reject completing `substep` while an earlier *required* substep of the
    same Op is still incomplete, when the Op is in SEQUENTIAL mode.

    Design choices:
    - Only enforced when `Steps.sequencing_mode == 'sequential'`; FREE_ORDER Ops
      skip the gate (the Op-signoff completeness check catches gaps there).
    - Only *required* prior substeps (``is_optional=False``) block. An optional
      substep left undone never blocks a later one — that's what "optional" means.
      A completed-or-N/A prior satisfies the gate (both land a SubstepCompletion).
    - Scoped to the execution keying being submitted: a per-part (SAMPLED) submit
      is gated only by earlier SAMPLED substeps' per-part completions, and a
      per-batch (BATCH) submit only by earlier BATCH completions. Cross-scope
      ordering isn't well-defined (the two keyings live on different execution
      rows), so we don't invent it here.
    """
    from django.core.exceptions import ValidationError
    from Tracker.models import SequencingMode, SubstepScope

    step = substep.step
    if getattr(step, 'sequencing_mode', SequencingMode.SEQUENTIAL) != SequencingMode.SEQUENTIAL:
        return

    prior = Substep.objects.filter(archived=False,
        step=step, order__lt=substep.order, is_optional=False,
    ).exclude(pk=substep.pk)

    # A voided completion no longer satisfies its substep — that is what
    # voiding means, and both sibling gates (advancement_gate, batch_lifecycle)
    # already read it that way. Without `is_voided=False` here, QA could void
    # substep #2 and the operator could still complete #3, because the retracted
    # row still counted as done. The part would then block at the advancement
    # gate instead, one step downstream of the cause and looking unrelated.
    if batch_execution is not None:
        prior = prior.filter(scope=SubstepScope.BATCH)
        done_ids = set(
            SubstepCompletion.objects
            .filter(batch_execution=batch_execution, is_voided=False)
            .values_list('substep_id', flat=True)
        )
    else:
        prior = prior.exclude(scope=SubstepScope.BATCH)
        done_ids = set(
            SubstepCompletion.objects
            .filter(step_execution=step_execution, is_voided=False)
            .values_list('substep_id', flat=True)
        )

    missing = [s for s in prior.order_by('order') if s.id not in done_ids]
    if missing:
        names = ', '.join(f"'{s.title}'" for s in missing[:3])
        more = '' if len(missing) <= 3 else f" (+{len(missing) - 3} more)"
        raise ValidationError(
            f"Substep '{substep.title}' can't be completed yet: this Op runs in "
            f"sequential mode and earlier required substeps are still open — "
            f"{names}{more}."
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
        report, created = QualityReports.objects.get_or_create(
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
        # Who was working the part: the execution's operator, as the report's OPERATOR
        # (the personnel roster; the flat `operators` M2M is deprecated). The report
        # recorded only who detected, so "operator on the job" was blank on every
        # captured report.
        if created and step_execution.assigned_to_id:
            QualityReportPersonnel.objects.get_or_create(
                quality_report=report, user_id=step_execution.assigned_to_id,
                role=PersonnelRole.OPERATOR)
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
        .filter(archived=False, step=step_execution.step, **subject_filter)
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
    overdue_warning = None
    if equipment_id:
        from Tracker.models import Equipments, EquipmentStatus
        # A gauge id from another tenant resolves to None, so the capture
        # records no equipment rather than binding a foreign one.
        # tenant-safe: .objects auto-scopes via the tenant ContextVar (runs
        # under a request or a tenant_context()-wrapped task)
        equipment = Equipments.objects.filter(pk=equipment_id).first()
        # A measurement recorded against an OUT_OF_SERVICE gauge is
        # retroactively suspect product — refuse the write at the source
        # rather than let the reading commit and rely on someone spotting it
        # via the void-QR flow later. The apply_calibration_result_to_equipment
        # signal on a FAIL calibration is what sets this status; this is where
        # that flag becomes load-bearing.
        # The calibration result is checked too, not only the status flag: the
        # flag is a copy of it that an edit could get out of step with.
        if equipment and (equipment.status == EquipmentStatus.OUT_OF_SERVICE
                          or equipment.calibration_status == 'FAILED'):
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f"Equipment '{equipment.name}' is OUT_OF_SERVICE (failed or "
                f"missing calibration). Recalibrate or pick a different gauge."
            )
        # Overdue is a scheduling lapse, not evidence the gauge is wrong: record the
        # reading, but tell the operator (user decision 2026-10-07). A tenant setting
        # for strict refusal can come later. A FAILED calibration stays refused above.
        if equipment and equipment.calibration_status == 'OVERDUE':
            overdue_warning = (f"{equipment.name} is past its calibration due date — the reading "
                               f"was recorded; tell QA so the gauge gets recalibrated.")

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
    return overdue_warning


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
        SubstepResponseKind.COMPONENT_INSTALL,
        SubstepResponseKind.REBUILD_FINDING,
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
    """The inspector's own verdict. A real save, then the FAIL consequences on a move
    into FAIL — a queryset .update() fired neither the disposition signal nor the
    quarantine, so a visual-judgement FAIL left the part in production with no NCR."""
    raw = (cap.get("status") or "").upper()
    if raw not in {"PASS", "FAIL", "PENDING"}:
        return
    report.refresh_from_db(fields=["status"])
    prior = report.status
    if prior == raw:
        return
    report.status = raw
    report.save(update_fields=["status"])
    from Tracker.services.qms.quality_report import on_report_failed
    on_report_failed(report, prior)


def _apply_equipment_roles(report: QualityReports, cap) -> list[str]:
    """The inspection's equipment roster. An OUT_OF_SERVICE or failed-calibration gauge
    is refused here as it is on a measurement capture — this block was a second door
    onto the record that skipped the check. An OVERDUE one is recorded with a warning,
    as on a measurement (user decision 2026-10-07: any capture that names a gauge).
    Returns those warnings."""
    warnings: list[str] = []
    from django.core.exceptions import ValidationError
    from Tracker.models import Equipments, EquipmentStatus
    rows = cap.get("rows") or []
    valid_roles = {r.value for r in EquipmentRole}
    for row in rows:
        equipment_id = row.get("equipment_id")
        role = row.get("role")
        if not equipment_id or role not in valid_roles:
            continue
        # tenant-safe: .objects auto-scopes via the tenant ContextVar
        equipment = Equipments.objects.filter(pk=equipment_id).first()
        if equipment is None:
            continue  # another tenant's id: bind nothing
        if equipment.status == EquipmentStatus.OUT_OF_SERVICE or equipment.calibration_status == 'FAILED':
            raise ValidationError(
                f"Equipment '{equipment.name}' is OUT_OF_SERVICE (failed or "
                f"missing calibration). Recalibrate or pick a different gauge.")
        if equipment.calibration_status == 'OVERDUE':
            warnings.append(f"{equipment.name} is past its calibration due date — it was "
                            f"recorded; tell QA so the gauge gets recalibrated.")
        QualityReportEquipment.objects.update_or_create(
            quality_report=report,
            equipment_id=equipment_id,
            role=role,
            defaults={"notes": row.get("notes") or ""},
        )
    return warnings


# Roles that are an ATTESTATION, not a roster entry: someone vouching for the
# inspection. They are written only by the signature captures, which stamp the
# signer server-side (`_stamp_signers`). A personnel-roles capture is a roster —
# "who was on the job" — and naming a colleague there is legitimate, so it must
# not be a second door onto these.
_ATTESTING_ROLES = {PersonnelRole.DETECTED_BY.value, PersonnelRole.VERIFIED_BY.value,
                    PersonnelRole.WITNESS.value}


def _apply_personnel_roles(report: QualityReports, cap) -> None:
    """The inspection's roster. Unlike the signature captures this one may name
    OTHER people — that is the point of it — so it takes no signature meaning and
    cannot write the attesting roles, and the time is the server's.

    `signed_at` came from the request body, so an operator could record a
    colleague as VERIFIED_BY at a time of their choosing: the hole `_stamp_signers`
    closed for the attestation and signatures captures, still open on the third
    path into the same table.
    """
    rows = cap.get("rows") or []
    valid_roles = {r.value for r in PersonnelRole} - _ATTESTING_ROLES
    now = timezone.now()
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
                "signed_at": now,
                "notes": row.get("notes") or "",
            },
        )


def _detected_assurance(substep, node_id) -> str:
    """How this inspection block's author said the finder signs."""
    found = {"value": "confirm"}

    def walk(node):
        if isinstance(node, dict):
            attrs = node.get("attrs") or {}
            if (node.get("type") == "inspectionSignatures"
                    and str(attrs.get("node_id")) == str(node_id)):
                found["value"] = attrs.get("detected_assurance") or "confirm"
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(substep.body_blocks)
    return found["value"]


def _check_detected_assurance(cap, *, user, substep, stored=None):
    """Make the finder's signature as strong as the author asked for.

    `confirm` is a click under their login — the default, and enough for most
    findings. `signature` means they draw and re-enter their own password, for a
    finding whose authorship has to be provable: it is still their own signature,
    so it is their password, not a second person's.
    """
    from django.core.exceptions import ValidationError
    from Tracker.services.core.second_person import verify_own_password

    if _detected_assurance(substep, cap.get("node_id")) != "signature":
        return cap
    detected = dict(cap["detected"])
    password = detected.pop("password", "") or ""
    # Already signed by this person and unchanged: don't ask again on a re-save.
    if (isinstance(stored, dict) and str(stored.get("user_id")) == str(user.pk)
            and not password):
        return {**cap, "detected": stored}
    if not detected.get("data_uri"):
        raise ValidationError(
            "Draw your signature for the finding, then confirm with your password.")
    refusal = verify_own_password(tenant=substep.tenant, user=user, password=password)
    if refusal:
        raise ValidationError(refusal)
    return {**cap, "detected": detected}


def _resolve_verifier(cap, *, user, substep, stored=None):
    """Resolve the inspection's verifying signature to a real second person.

    The operator is signed in; the verifier is standing next to them. They supply
    `cosign_email` / `cosign_password` in the capture, checked and throttled the way
    every other second-person act here is. A verification already stored is carried
    over untouched, so re-saving a substep QA has verified doesn't ask again.
    """
    from django.core.exceptions import ValidationError
    from Tracker.services.core.second_person import verify_second_person

    verified = dict(cap["verified"])
    email = (verified.pop("cosign_email", "") or "").strip()
    password = verified.pop("cosign_password", "") or ""
    # Already verified, and this submit isn't changing it: leave the record alone
    # rather than asking that person to stand at the terminal again.
    if (isinstance(stored, dict) and stored.get("user_id") is not None
            and not (email or password)
            and str(verified.get("user_id") or stored.get("user_id")) == str(stored.get("user_id"))):
        return {**cap, "verified": stored}
    if not (email or password):
        raise ValidationError(
            "A verifying signature is a second person's: they enter their own email "
            "and password here. It can't be the person who did the work.")
    verifier, failure = verify_second_person(
        tenant=substep.tenant, actor=user, email=email, password=password,
        permission='sign_off_fpi',
        throttle_prefix='inspection_verify', code_prefix='verify',
        messages={
            'self': "The verifying signature has to be a different person from the "
                    "one who found it — that is what makes it a second check.",
            'not_permitted': "That user isn't qualified to verify an inspection.",
        },
    )
    if failure:
        raise ValidationError(failure[0])
    return {**cap, "verified": {
        **verified,
        "user_id": verifier.pk,
        "username": verifier.get_username(),
        # A name for the record to show — the username is a login (an email).
        "display_name": verifier.get_full_name().strip() or verifier.get_username(),
        "signed_at": timezone.now().isoformat(),
    }}


def _stamp_signers(cap, *, user, substep, step_execution, batch_execution):
    """Record each signature in an attestation / inspection-signatures capture as the
    person submitting it, at the server's clock.

    The client used to supply `user_id` and `signed_at`, and they were stored as sent
    — into the response and into the QR personnel roster (DETECTED_BY / VERIFIED_BY /
    WITNESS). Any operator could record anyone as an inspection's verifier, and the
    time was the browser's. A signature naming someone else is accepted only as the
    unchanged carry-over of what is already stored (re-saving a substep QA has
    already verified); anything else is refused.
    """
    from django.core.exceptions import ValidationError
    # "Verified by" is the model's own words for a *second* signature, and a shop
    # terminal only ever has one person signed in. So the verifying slot is never
    # stamped from the session: the verifier identifies themselves at the operator's
    # keyboard with their own email and password, the same second-person act as an
    # FPI co-sign or a disposition authorisation. Nothing used to stop the operator
    # filling both slots and being recorded as the independent check on their own
    # finding.
    stored = (SubstepResponse.objects  # tenant-safe: keyed to a tenant-scoped execution
              .filter(step_execution=step_execution, batch_execution=batch_execution,
                      substep=substep, node_id=cap.get("node_id"))
              .values_list("value_json", flat=True).first()) or {}
    if cap.get("kind") != "attestation":
        if isinstance(cap.get("detected"), dict):
            cap = _check_detected_assurance(cap, user=user, substep=substep,
                                            stored=stored.get("detected"))
        if isinstance(cap.get("verified"), dict):
            cap = _resolve_verifier(cap, user=user, substep=substep,
                                    stored=stored.get("verified"))
    slots = ("signature",) if cap.get("kind") == "attestation" else ("detected",)
    now = timezone.now().isoformat()
    out = dict(cap)
    for slot in slots:
        sig = cap.get(slot)
        if not isinstance(sig, dict):
            continue
        claimed = sig.get("user_id")
        if claimed in (None, "") or str(claimed) == str(user.pk):
            prior = stored.get(slot) if isinstance(stored.get(slot), dict) else {}
            if str(prior.get("user_id")) == str(user.pk):
                out[slot] = prior  # already signed by this person: keep the original time
            else:
                out[slot] = {**sig, "user_id": user.pk, "username": user.get_username(),
                             "display_name": user.get_full_name().strip() or user.get_username(),
                             "signed_at": now}
            continue
        prior = stored.get(slot)
        if isinstance(prior, dict) and str(prior.get("user_id")) == str(claimed):
            out[slot] = prior
            continue
        raise ValidationError("You can only sign as yourself.")

    return out


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
            report=report,
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
    # Independent of a drawing: with per-block signing the drawings live on the
    # block rows, and the completion carries only the summary the review list
    # reads. Gating this on `signature_data` left a substep whose every block was
    # password-signed recorded as unverified.
    if verification_method:
        defaults["verification_method"] = verification_method
        defaults["verified_at"] = timezone.now()
        if ip_address:
            defaults["ip_address"] = ip_address

    # A voided completion is the record of a wrong capture, and void means
    # "capture it again". The uniqueness constraint ignores is_voided, so
    # update_or_create used to rewrite the voided row in place — it stayed
    # voided, the gate skips voided rows, and the re-capture never counted. Retire
    # the voided row (soft-delete keeps it as history) and let this one be new.
    voided = SubstepCompletion.objects.filter(  # tenant-safe: keyed to a scoped execution
        step_execution=step_execution, batch_execution=batch_execution, substep=substep,
        is_voided=True, deleted_at__isnull=True)
    voided.update(deleted_at=timezone.now(), archived=True)
    completion, _ = SubstepCompletion.objects.update_or_create(
        step_execution=step_execution,
        batch_execution=batch_execution,
        substep=substep,
        deleted_at__isnull=True,
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


# ---------------------------------------------------------------------------
# Capture-state hydration — the read-side inverse of submit_substep
# ---------------------------------------------------------------------------
#
# Rebuild an execution's captured state as {substep_id: {node_id: response}} from
# the persisted SubstepResponse + StepExecutionMeasurement rows, so the operator
# runtime can hydrate from the server (the source of truth) when it opens an
# execution whose operator already did the work — instead of starting blank and
# re-deriving nothing. Response shapes mirror the capture vocabulary the runtime
# submits (the FE `buildCaptures` contract), so the runtime can drop them
# straight into its per-substep response map and its existing readiness check.

_CAPTURE_NODE_TYPES = {
    'textInput', 'choiceInput', 'scanInput', 'photoCapture', 'fileCapture',
    'timer', 'computedValue', 'attestationCheckpoint', 'measurementInput',
    'qualityStatusField', 'equipmentRolesField', 'personnelRolesField',
    'errorTypesField', 'inspectionSignatures', 'partAnnotation',
    # Reman teardown and rebuild capture. The harvest node was missing here, so the
    # server's required check never saw it — only the client enforced it.
    'harvestedComponentCapture', 'componentInstallCapture', 'rebuildFindingCapture',
}


def _collect_capture_nodes(node, out):
    """Walk a TipTap `body_blocks` doc, collecting (type, attrs) for capture nodes."""
    if isinstance(node, dict):
        node_type = node.get('type')
        attrs = node.get('attrs') or {}
        if node_type in _CAPTURE_NODE_TYPES and attrs.get('node_id'):
            out.append((node_type, attrs))
        for value in node.values():
            _collect_capture_nodes(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_capture_nodes(value, out)


def _replayed_rows(substep, step_execution, node_id, cap) -> bool:
    """Whether this teardown/rebuild capture was already recorded for this visit.

    These two captures have side effects beyond their SubstepResponse — each row
    becomes a HarvestedComponent or an installed AssemblyUsage — so a resubmit must not
    run them again. The runtime reseeds a resumed substep from the stored rows, so an
    identical resubmit is a replay and is a no-op (True). A resubmit with DIFFERENT rows
    is refused: what came out of or went into a unit is corrected on the unit's own
    records, not by re-recording the capture over them.
    """
    from django.core.exceptions import ValidationError
    from Tracker.models import SubstepResponse

    prior = SubstepResponse.objects.filter(archived=False,   # tenant-safe: .objects auto-scopes to the request tenant
        step_execution=step_execution, substep=substep, node_id=node_id,
    ).first()
    if prior is None:
        return False
    if ((prior.value_json or {}).get('rows') or []) == (cap.get('rows') or []):
        return True
    raise ValidationError(
        "These components were already recorded for this unit at this step. "
        "Correct them on the core's record rather than recording the capture again."
    )


def _response_from_stored(node_type, attrs, sr):
    """Reconstruct one node's response from its SubstepResponse row, matching the
    shape the runtime's input widget writes and its `checkSatisfied` reads."""
    payload = sr.value_json or {}
    if node_type in ('textInput', 'choiceInput', 'scanInput'):
        return sr.value_text or ''
    if node_type in ('photoCapture', 'fileCapture'):
        if sr.value_document_id:
            return {'document_id': str(sr.value_document_id),
                    'file_name': payload.get('file_name') or ''}
        return sr.value_text or ''
    if node_type in ('timer', 'computedValue'):
        return payload
    if node_type == 'attestationCheckpoint':
        # Confirm-mode wants boolean true; signature-mode wants the payload object.
        return payload if attrs.get('kind') == 'signature' else True
    if node_type == 'qualityStatusField':
        return payload.get('status') or sr.value_text or ''
    if node_type in ('equipmentRolesField', 'personnelRolesField', 'errorTypesField'):
        return payload.get('rows') or []
    if node_type == 'inspectionSignatures':
        return {'detected': payload.get('detected'), 'verified': payload.get('verified')}
    if node_type == 'partAnnotation':
        return payload
    if node_type in ('harvestedComponentCapture', 'componentInstallCapture', 'rebuildFindingCapture'):
        # Both runtimes read `{rows: [...]}`; resuming a half-done teardown or rebuild
        # reseeds them from what was recorded rather than from the BOM.
        return {'rows': payload.get('rows') or []}
    return sr.value_text or payload


def build_capture_state(step_execution) -> dict:
    """Return {substep_id: {node_id: response}} for a step execution's stored
    captures — the read-side inverse of `submit_substep`."""
    from Tracker.models import Substep, SubstepCompletion, SubstepResponse, StepExecutionMeasurement

    # A substep voided for re-capture comes back empty, not with the wrong values it
    # was voided for — those pre-filled read "1 of 1 confirmed", as if nothing needed
    # doing (Operator walk 2026-10-21). Its draft, if any, still overlays below.
    done = SubstepCompletion.objects.filter(  # tenant-safe: keyed to a scoped execution
        step_execution=step_execution)
    reopened = (set(done.filter(is_voided=True).values_list('substep_id', flat=True))
                - set(done.filter(is_voided=False).values_list('substep_id', flat=True)))

    sr_by_key = {
        (str(sr.substep_id), str(sr.node_id)): sr
        for sr in SubstepResponse.objects.filter(archived=False, step_execution=step_execution)
    }
    meas_by_key = {
        (str(m.substep_id), str(m.measurement_definition_id)): m
        for m in StepExecutionMeasurement.objects.filter(archived=False, step_execution=step_execution)
        if m.substep_id and m.measurement_definition_id
    }

    out: dict = {}
    for substep in Substep.objects.filter(archived=False, step=step_execution.step):
        if substep.id in reopened:
            continue
        nodes: list = []
        _collect_capture_nodes(substep.body_blocks, nodes)
        node_map: dict = {}
        for node_type, attrs in nodes:
            node_id = attrs.get('node_id')
            if not node_id:
                continue
            if node_type == 'measurementInput':
                def_id = attrs.get('measurement_definition_id')
                measurement = meas_by_key.get((str(substep.id), str(def_id))) if def_id else None
                if measurement is None:
                    continue
                value = (str(measurement.value) if measurement.value is not None
                         else (measurement.string_value or ''))
                if value == '':
                    continue
                node_map[node_id] = (
                    {'value': value, 'equipment_id': str(measurement.equipment_id)}
                    if measurement.equipment_id else {'value': value}
                )
                continue
            sr = sr_by_key.get((str(substep.id), str(node_id)))
            if sr is not None:
                node_map[node_id] = _response_from_stored(node_type, attrs, sr)
        if node_map:
            out[str(substep.id)] = node_map

    # Work in progress overlays what's committed: a substep the operator re-entered
    # after an earlier commit shows what they last typed, not the stale record.
    for substep_id, responses in (step_execution.capture_draft or {}).items():
        if isinstance(responses, dict):
            out[str(substep_id)] = responses
    return out


# -------------------------------------------------------------------------
# Drafts — work in progress between substeps
# -------------------------------------------------------------------------

def save_capture_draft(step_execution, substep, responses: dict) -> dict:
    """Save one substep's in-progress responses on its step execution.

    Nothing official happens: no completion, measurement or report. Those are
    `submit_substep`'s, at "Complete step". This is only so the work survives a
    closed tablet or a handover — the player hydrates it via `build_capture_state`.

    Raises:
        ValidationError: the substep isn't on this execution's step, or is
            batch-scope (those are recorded once per load, not drafted per part).
    """
    from django.core.exceptions import ValidationError
    from Tracker.models import SubstepScope

    if substep.step_id != step_execution.step_id:
        raise ValidationError("That substep isn't part of this step.")
    if substep.scope == SubstepScope.BATCH:
        raise ValidationError("Batch substeps are recorded for the load, not drafted per part.")
    if not isinstance(responses, dict):
        raise ValidationError("`responses` must be an object of {node_id: response}.")

    with transaction.atomic():
        locked = StepExecution.objects.select_for_update().get(pk=step_execution.pk)  # tenant-safe: by pk of an already-scoped row
        draft = dict(locked.capture_draft or {})
        if responses:
            draft[str(substep.id)] = responses
        else:
            draft.pop(str(substep.id), None)
        locked.capture_draft = draft
        locked.save(update_fields=['capture_draft'])
    return draft


def _drop_from_draft(step_execution, substep_id) -> None:
    locked = StepExecution.objects.select_for_update().get(pk=step_execution.pk)  # tenant-safe: by pk of an already-scoped row
    draft = dict(locked.capture_draft or {})
    if draft.pop(str(substep_id), None) is not None:
        locked.capture_draft = draft
        locked.save(update_fields=['capture_draft'])
