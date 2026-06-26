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

from django.db import transaction

from Tracker.services.mes import inventory
from Tracker.services.qms.acceptance_sampling import compute_sample_plan


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


def _plan_for(lot, step):
    rs = resolve_sampling_ruleset(step, lot.supplier)
    return compute_sample_plan(
        lot_size=int(lot.quantity or 0),
        aql=float(rs.aql) if rs and rs.aql is not None else 1.0,
        inspection_level=(rs.inspection_level if rs and rs.inspection_level else "II"),
        severity=(rs.severity if rs and rs.severity else "NORMAL"),
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
    step = resolve_receiving_step(lot.material_type) if lot.material_type_id else None
    if step is None:
        inventory.mark_dock_to_stock(lot)
        return None
    try:
        return open_inspection(lot, user)
    except ValueError:
        return None  # leave RECEIVED → visible in the queue


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
    else:
        status = "PENDING"

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
