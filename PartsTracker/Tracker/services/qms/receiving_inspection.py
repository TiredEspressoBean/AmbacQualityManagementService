"""
Receiving-inspection orchestration (purchased material, Flow A).

Receiving inspection is modeled as a ``RECEIVING`` Step node in the part type's
process — there is no standalone plan model. A MaterialLot is inspected against
that step:
  - characteristics   = the step's ``required_measurements``
  - acceptance sampling = the step's ``SamplingRuleSet`` resolved by supplier
                          (``(step, supplier)`` → fallback ``(step, supplier=NULL)``)

The inspection is recorded as a ``QualityReports(material_lot=…, step=…)`` (config-only;
no StepExecution yet). Stock-state effects go through the ``services.mes.inventory``
seam; the sample plan comes from the ``acceptance_sampling`` calculator (Phase-1 stub).

Domain errors raise ``ValueError`` (the viewset maps to HTTP 400).
"""
from __future__ import annotations

import logging

from django.db import transaction

from Tracker.services.mes import inventory
from Tracker.services.qms.acceptance_sampling import compute_sample_plan

logger = logging.getLogger(__name__)

# MaterialLot.hold_reason vocabulary. A free CharField by design (shops invent
# reasons), but these codes are the ones the SYSTEM sets/reads — the inspection
# inbox sinks held rows and shows the code as the blocked chip. Keep new
# system-set reasons here so the FE can map them to labels.
HOLD_SUPPLIER_UNQUALIFIED = "SUPPLIER_UNQUALIFIED"  # set by check_supplier_qualification
HOLD_PART_UNAPPROVED = "PART_UNAPPROVED"            # set by check_part_approval
HOLD_AWAITING_COC = "AWAITING_COC"                  # manual: cert of conformance missing
HOLD_GAUGE_UNAVAILABLE = "GAUGE_UNAVAILABLE"        # manual: required gauge out for cal


def resolve_receiving_step(part_type):
    """The current RECEIVING step for a part type, or None."""
    from Tracker.models import Steps
    qs = Steps.objects.filter(part_type=part_type, step_type="RECEIVING")
    # Prefer the current version when the versioning flag is present.
    return qs.filter(is_current_version=True).first() or qs.first()


def resolve_sampling_ruleset(step, supplier):
    """Active sampling ruleset for (step, supplier), falling back to the
    supplier-agnostic ruleset for the step."""
    from Tracker.models import SamplingRuleSet
    base = SamplingRuleSet.objects.filter(step=step, active=True)
    return base.filter(supplier=supplier).first() or base.filter(supplier__isnull=True).first()


# ── Receiving Inspection Plans (RIPs) — purchased material, process-free ──────
# A RIP is a standalone RECEIVING step (no process membership): the incoming-
# inspection plan for purchased material, authored on the Supply page. RECEIVING
# steps that live ON a process (OSP returns, in-workflow receiving nodes) belong
# to that process and are authored in the flow editor — they are NOT RIPs here.

def create_standalone_receiving_plan(part_type, name="", user=None):
    """Create a process-free RECEIVING step (a purchased-material RIP) for a part type.
    Deliberately does NOT reuse an in-process RECEIVING step — those belong to their
    process; a RIP is always standalone."""
    from Tracker.models import Steps
    return Steps.objects.create(
        tenant=part_type.tenant,
        part_type=part_type,
        step_type="RECEIVING",
        name=name or f"Receiving - {part_type.name}",
        description="Incoming inspection plan for purchased material.",
    )


def _plan_for(lot, step):
    from Tracker.services.qms.severity_switching import effective_severity
    rs = resolve_sampling_ruleset(step, lot.supplier)
    return compute_sample_plan(
        lot_size=int(lot.quantity or 0),
        aql=float(rs.aql) if rs and rs.aql is not None else 1.0,
        inspection_level=(rs.inspection_level if rs and rs.inspection_level else "II"),
        # Effective (runtime) severity from the switching engine, not the ruleset's
        # static starting severity — a tightened/reduced supplier gets the right plan.
        severity=effective_severity(step, lot.supplier, rs),
        strategy=(rs.strategy if rs and rs.strategy else "C0"),
    )


def sample_plan_for_lot(lot):
    """Resolve + compute the sample plan for a lot (read-only; used by the endpoint)."""
    step = resolve_receiving_step(lot.material_type)
    if step is None:
        raise ValueError("No RECEIVING step configured for this part type.")
    return _plan_for(lot, step)


def receiving_execution(lot):
    """The open StepExecution carrying a lot's receiving inspection (the DWI run), if any."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import StepExecution
    ct = ContentType.objects.get_for_model(lot.__class__)
    return (StepExecution.objects
            .filter(subject_content_type=ct, subject_id=lot.id,
                    status__in=["PENDING", "CLAIMED", "IN_PROGRESS"])
            .order_by("-entered_at").first())


def _finalize_execution(lot, user):
    from django.utils import timezone
    ex = receiving_execution(lot)
    if ex is not None:
        ex.status = "COMPLETED"
        ex.exited_at = timezone.now()
        if user is not None and user.is_authenticated:
            ex.completed_by = user
        ex.save(update_fields=["status", "exited_at", "completed_by", "updated_at"])


def route_received_lot(lot, user):
    """Auto-route a freshly RECEIVED lot (standards-compliant default: receipt never
    lands directly in usable stock without a decision).

    - Part type has a RECEIVING step → open inspection (→ AWAITING_INSPECTION).
    - No RECEIVING step (incoming inspection not required) → dock-to-stock (→ ACCEPTED).

    Resilient: if opening the inspection errors, the lot is left RECEIVED so it
    surfaces in the receiving queue for manual handling. (Full scorecard-driven
    skip-lot earning/reversion is a later SQM phase; this is the routing seam.)
    """
    if lot.status != "RECEIVED":
        return None
    # Supplier-qualification gate (soft hold): a lot from a supplier not qualified
    # for this part type is quarantined and flagged rather than flowing to stock.
    if _held_for_unqualified_supplier(lot):
        return None
    # Part-approval gate (soft hold): a lot whose (part type, supplier) has no
    # active part approval (PPAP / FAI) is quarantined and flagged.
    if _held_for_unapproved_part(lot):
        return None
    step = resolve_receiving_step(lot.material_type) if lot.material_type_id else None
    if step is None:
        inventory.mark_dock_to_stock(lot)
        return None
    try:
        return open_inspection(lot, user)
    except ValueError:
        return None  # leave RECEIVED → visible in the queue


def _held_for_unqualified_supplier(lot) -> bool:
    """Soft-hold a received lot whose part type requires supplier qualification and
    whose supplier has no active qualification covering it. Quarantines + emits
    `supplier.unqualified`. Returns True when the lot was held."""
    part_type = lot.material_type if lot.material_type_id else None
    if part_type is None or not getattr(part_type, "requires_supplier_qualification", False):
        return False

    from Tracker.services.qms.supplier_qualification import is_supplier_qualified
    if is_supplier_qualified(supplier=lot.supplier, part_type=part_type):
        return False

    inventory.quarantine_lot(lot)
    lot.hold_reason = HOLD_SUPPLIER_UNQUALIFIED
    lot.save(update_fields=["hold_reason"])
    _emit_supplier_unqualified(lot)
    return True


def _emit_supplier_unqualified(lot) -> None:
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import SupplierUnqualifiedPayload

    supplier = lot.supplier
    part_type = lot.material_type
    payload = SupplierUnqualifiedPayload(
        id=str(lot.id),
        tenant_id=str(lot.tenant_id) if lot.tenant_id else "",
        material_lot_id=str(lot.id),
        lot_number=lot.lot_number,
        supplier_id=str(supplier.id) if supplier else None,
        supplier_name=supplier.name if supplier else "",
        part_type_id=str(part_type.id) if part_type else None,
        part_type_name=part_type.name if part_type else "",
    )
    emit(
        "supplier.unqualified",
        tenant=lot.tenant,
        payload=payload,
        correlation_id=f"materiallot:{lot.id}",
        idempotency_key=f"supplier.unqualified:materiallot:{lot.id}",
    )


def _held_for_unapproved_part(lot) -> bool:
    """Soft-hold a received lot whose part type requires part approval and whose
    (part type, supplier) has no active part approval (PPAP / FAI). Quarantines +
    emits `part.unapproved`. Returns True when the lot was held."""
    part_type = lot.material_type if lot.material_type_id else None
    if part_type is None or not getattr(part_type, "requires_part_approval", False):
        return False

    from Tracker.services.qms.part_approval import is_part_approved
    if is_part_approved(part_type=part_type, supplier=lot.supplier):
        return False

    inventory.quarantine_lot(lot)
    lot.hold_reason = HOLD_PART_UNAPPROVED
    lot.save(update_fields=["hold_reason"])
    _emit_part_unapproved(lot)
    return True


def _emit_part_unapproved(lot) -> None:
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import PartUnapprovedPayload

    supplier = lot.supplier
    part_type = lot.material_type
    payload = PartUnapprovedPayload(
        id=str(lot.id),
        tenant_id=str(lot.tenant_id) if lot.tenant_id else "",
        material_lot_id=str(lot.id),
        lot_number=lot.lot_number,
        supplier_id=str(supplier.id) if supplier else None,
        supplier_name=supplier.name if supplier else "",
        part_type_id=str(part_type.id) if part_type else None,
        part_type_name=part_type.name if part_type else "",
    )
    emit(
        "part.unapproved",
        tenant=lot.tenant,
        payload=payload,
        correlation_id=f"materiallot:{lot.id}",
        idempotency_key=f"part.unapproved:materiallot:{lot.id}",
    )


def open_inspection(lot, user):
    """Open a receiving inspection for ``lot`` against its part type's RECEIVING step.

    Creates a ``StepExecution`` whose polymorphic subject is the lot (the carrier for
    the receiving DWI / substep runtime), a PENDING ``QualityReports`` keyed to the lot
    + step (snapshotting the sample plan), links ``user`` as INSPECTOR, and moves the
    lot to AWAITING_INSPECTION. The same report is appended to by either the bespoke
    capture flow or DWI inline capture.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import QualityReports, StepExecution

    if lot.status != "RECEIVED":
        raise ValueError(
            f"Lot {lot.lot_number} is {lot.status}; an inspection can only be "
            f"opened on a RECEIVED lot."
        )
    step = resolve_receiving_step(lot.material_type)
    if step is None:
        raise ValueError("No RECEIVING step configured for this part type.")

    sp = _plan_for(lot, step)
    # For a Z1.9 variables plan, snapshot k + the measured characteristic so the
    # evaluator can apply the x̄/s vs k rule. Resolve the ruleset for the characteristic.
    rs = resolve_sampling_ruleset(step, lot.supplier) if sp.method else None
    variables_char = rs.variables_characteristic if rs else None

    with transaction.atomic():
        StepExecution.objects.create(
            tenant=lot.tenant,
            step=step,
            subject_content_type=ContentType.objects.get_for_model(lot.__class__),
            subject_id=lot.id,
            status="IN_PROGRESS",
            assigned_to=user if (user and user.is_authenticated) else None,
        )
        report = QualityReports.objects.create(
            tenant=lot.tenant,
            material_lot=lot,
            step=step,
            status="PENDING",
            sampling_method="receiving_aql",
            sample_size=sp.sample_size,
            accept_number=sp.accept_number,
            reject_number=sp.reject_number,
            acceptability_constant_k=sp.k,
            variables_characteristic=variables_char,
        )
        if user is not None and user.is_authenticated:
            report.personnel_links.create(user=user, role="INSPECTOR")
        inventory.mark_awaiting_inspection(lot)

    return report


def receiving_characteristics(step):
    """The measurement definitions to capture for a receiving step."""
    return list(step.required_measurements.all()) if step else []


def record_inspection(report, measurements, user):
    """Record measurement results against a receiving inspection and set PASS/FAIL.

    ``measurements`` is an iterable of ``{definition, value_numeric?, value_pass_fail?}``.
    PASS/FAIL derives from the measurements alone in Phase 1 (all within spec → PASS);
    AQL defective-count vs Ac is Phase 2.
    """
    from Tracker.models import MeasurementDefinition, MeasurementResult

    if report.material_lot_id is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")

    with transaction.atomic():
        any_recorded = False
        all_ok = True
        for m in measurements:
            defn = MeasurementDefinition.unscoped.get(pk=m["definition"])
            result = MeasurementResult.objects.create(
                tenant=report.tenant,
                report=report,
                definition=defn,
                value_numeric=m.get("value_numeric"),
                value_pass_fail=m.get("value_pass_fail"),
                created_by=user if (user and user.is_authenticated) else None,
            )
            any_recorded = True
            if not result.is_within_spec:
                all_ok = False

        if any_recorded:
            report.status = "PASS" if all_ok else "FAIL"
            report.save(update_fields=["status"])

    return report


def record_sample_units(report, units, user):
    """Record measurements for sampled units and evaluate the AQL decision.

    ``units`` = [{'sample_number': int, 'measurements': [{'definition',
    'value_numeric'?, 'value_pass_fail'?}]}]. Each sample_number is one inspected
    unit; a unit is *defective* if any of its measurements is out of spec.
    """
    from Tracker.models import MeasurementDefinition, MeasurementResult

    if report.material_lot_id is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")

    with transaction.atomic():
        for unit in units:
            sn = unit.get("sample_number")
            for m in unit.get("measurements", []):
                defn = MeasurementDefinition.unscoped.get(pk=m["definition"])
                MeasurementResult.objects.create(
                    tenant=report.tenant, report=report, definition=defn,
                    value_numeric=m.get("value_numeric"),
                    value_pass_fail=m.get("value_pass_fail"),
                    sample_number=sn,
                    created_by=user if (user and user.is_authenticated) else None,
                )
        evaluate_lot_acceptance(report)
    return report


def record_bulk(report, defectives_found, user):
    """Bulk/attribute capture: record the number of defectives found across the
    sample (units not measured individually), then evaluate the AQL decision."""
    if report.material_lot_id is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")
    if defectives_found < 0:
        raise ValueError("defectives_found must be non-negative.")
    with transaction.atomic():
        report.defectives_found = defectives_found
        report.save(update_fields=["defectives_found"])
        evaluate_lot_acceptance(report)
    return report


def evaluate_lot_acceptance(report):
    """Set report.status from defectives vs the snapshot Ac/Re.

    Per-unit capture → count defective sampled units. Bulk capture → use the
    recorded defectives_found (the full sample is assumed inspected).

    - defectives ≥ Re  → FAIL (immediate; for C=0 one defective rejects).
    - full sample inspected AND defectives ≤ Ac → PASS.
    - otherwise → PENDING (still inspecting).
    """
    from collections import defaultdict

    # Z1.9 variables: a non-null k means decide on x̄/s vs k, not defective-count.
    if report.acceptability_constant_k is not None:
        _evaluate_variables_lot(report)
        _fire_lot_gate(report)
        return report

    n = report.sample_size or 0
    results = list(report.measurements.all())
    if results:
        by_unit = defaultdict(list)
        for r in results:
            by_unit[r.sample_number].append(r)
        units_recorded = len(by_unit)
        defectives = sum(1 for unit_results in by_unit.values()
                         if any(r.is_within_spec is False for r in unit_results))
    elif report.defectives_found is not None:
        # Bulk/attribute: the whole sample of n was inspected as a batch.
        defectives = report.defectives_found
        units_recorded = n
    else:
        defectives, units_recorded = 0, 0

    ac = report.accept_number if report.accept_number is not None else 0
    re = report.reject_number if report.reject_number is not None else (ac + 1)
    n = report.sample_size or 0

    if defectives >= re:
        status = "FAIL"
    elif units_recorded >= n and defectives <= ac:
        status = "PASS"
    elif units_recorded >= n and defectives < re:
        # Reduced-inspection accept/reject gap (Re > Ac + 1): accept the lot, but
        # the switching engine reverts this (step, supplier) to normal inspection.
        status = "PASS"
    else:
        status = "PENDING"

    if status != report.status:
        report.status = status
        report.save(update_fields=["status"])
    _fire_lot_gate(report)
    if status in ("PASS", "FAIL"):
        from Tracker.services.qms.severity_switching import update_after_lot
        update_after_lot(report)
    return report


def _fire_lot_gate(report):
    """Fire the receiving step's quality gate for this lot (auto-SCAR / hold /
    require-approval), mirroring the in-process trigger in `quality_report.py`.
    Best-effort — a gate failure never breaks the acceptance evaluation; idempotent
    per (ruleset, step, lot) via `StepGateFiring`."""
    lot = report.material_lot if report.material_lot_id else None
    step = report.step
    if lot is None or step is None:
        return
    rs = resolve_sampling_ruleset(step, getattr(lot, "supplier", None))
    if rs is None:
        return
    try:
        from Tracker.services.qms.quality_gate import evaluate_step_gate
        evaluate_step_gate(ruleset=rs, material_lot=lot, trigger=report)
    except Exception:
        logger.exception("Lot quality gate failed (report=%s)", report.pk)


def _evaluate_variables_lot(report):
    """Z1.9 verdict: gather the sample's readings for the measured characteristic,
    derive USL/LSL from its tolerances, and apply x̄/s vs k. Stays PENDING until the
    full sample of n is recorded."""
    from Tracker.services.qms.acceptance_sampling import evaluate_variables

    n = report.sample_size or 0
    char = report.variables_characteristic
    if char is None:
        return report  # misconfigured Z1.9 plan (no characteristic) → leave PENDING

    values = [float(r.value_numeric) for r in report.measurements.all()
              if r.definition_id == char.id and r.value_numeric is not None]

    usl = (float(char.nominal) + float(char.upper_tol)) if (char.nominal is not None and char.upper_tol is not None) else None
    lsl = (float(char.nominal) - float(char.lower_tol)) if (char.nominal is not None and char.lower_tol is not None) else None

    if len(values) < max(n, 2) or (usl is None and lsl is None):
        status = "PENDING"
    else:
        res = evaluate_variables(values=values, usl=usl, lsl=lsl, k=report.acceptability_constant_k)
        status = "PASS" if res["accept"] else "FAIL"

    if status != report.status:
        report.status = status
        report.save(update_fields=["status"])
    return report


def accept(report, user):
    """Accept the inspected lot (AWAITING_INSPECTION → ACCEPTED) + close the execution."""
    if report.material_lot_id is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")
    inventory.mark_lot_accepted(report.material_lot)
    _finalize_execution(report.material_lot, user)
    if report.status == "PENDING":
        report.status = "PASS"
        report.save(update_fields=["status"])
    return report


def reject(report, user):
    """Reject the inspected lot (→ REJECTED).

    Phase 2 TODO: route through QUARANTINE and spawn a ``QuarantineDisposition``
    (RETURN_TO_SUPPLIER / USE_AS_IS / SCRAP) instead of going straight to REJECTED.
    """
    if report.material_lot_id is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")
    inventory.mark_lot_rejected(report.material_lot)
    _finalize_execution(report.material_lot, user)
    if report.status == "PENDING":
        report.status = "FAIL"
        report.save(update_fields=["status"])
    return report
