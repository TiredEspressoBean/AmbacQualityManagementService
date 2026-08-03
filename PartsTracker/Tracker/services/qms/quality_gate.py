"""
Step quality gates — the single evaluation path for aggregate-signal automatic
decisions.

A gate lives on a `SamplingRuleSet` (`gate_metric`/`gate_threshold`/`gate_window`/
`gate_actions`...). When an inspection result lands, `evaluate_step_gate` computes
the configured metric over its window and, if the threshold is crossed and the gate
hasn't already fired for this window, records a `StepGateFiring` (idempotency marker
+ audit trail) and dispatches each configured action to its existing service.

Two callers feed this one dispatcher:
  - in-process: `services/qms/quality_report.py` on each PASS/FAIL QualityReport;
  - receiving: `services/qms/receiving_inspection.py` on lot acceptance (lot path).

Actions are a closed set (`GateAction`); no free-form scripting. A single action
failing is isolated so it neither blocks the others nor the inspection flow.
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from Tracker.models import GateAction, GateMetric, GateWindow, SamplingRuleSet, StepGateFiring

logger = logging.getLogger(__name__)

_Q3 = Decimal("0.001")


def gate_ruleset_for_step(step, part_type):
    """The active primary (gate-bearing) ruleset for a (step, part_type)."""
    return (
        SamplingRuleSet.objects
        .filter(step=step, part_type=part_type, active=True, is_fallback=False)
        .order_by("version")
        .last()
    )


def evaluate_step_gate(*, ruleset, work_order=None, material_lot=None,
                       trigger=None, triggering_part=None, user=None):
    """Evaluate *ruleset*'s quality gate for the given window and fire its actions
    if tripped. No-op when the ruleset carries no gate *metric*. Idempotent per window.

    A gate is defined by its `gate_metric`; `gate_actions` are optional consequences.
    A **routing-only gate** (metric set, no actions) still records a `StepGateFiring`
    on threshold-cross — that firing is the signal `AGGREGATE` routing reads.

    Returns the `StepGateFiring` (created or pre-existing), or None.
    """
    if ruleset is None or not ruleset.gate_metric:
        return None

    step = ruleset.step

    existing = StepGateFiring.objects.filter(
        ruleset=ruleset, step=step, work_order=work_order, material_lot=material_lot,
    ).first()
    if existing:
        return existing

    metric_value = _compute_metric(ruleset, work_order=work_order, material_lot=material_lot)
    if metric_value is None or not _threshold_crossed(ruleset, metric_value):
        return None

    with transaction.atomic():
        firing = StepGateFiring.objects.create(
            tenant=ruleset.tenant,
            ruleset=ruleset,
            step=step,
            work_order=work_order,
            material_lot=material_lot,
            metric=ruleset.gate_metric,
            metric_value=metric_value,
            threshold=ruleset.gate_threshold,
            triggered_by_report=trigger if _looks_like_report(trigger) else None,
        )

        taken = []
        for action in (ruleset.gate_actions or []):
            try:
                _dispatch_action(
                    action, ruleset=ruleset, firing=firing, work_order=work_order,
                    material_lot=material_lot, triggering_part=triggering_part,
                    trigger=trigger, user=user,
                )
                taken.append(action)
            except Exception:  # one bad action must not block the rest or the QR flow
                logger.exception("Quality gate action %s failed (ruleset=%s)", action, ruleset.pk)

        firing.actions_taken = taken
        firing.save(update_fields=["actions_taken", "created_capa", "approval_request"])

    return firing


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def _report_window_qs(ruleset, work_order, material_lot):
    """Base QualityReports queryset for the gate's window, newest first."""
    from Tracker.models.qms import QualityReports

    qs = QualityReports.objects.filter(status__in=["PASS", "FAIL"])
    if material_lot is not None:
        qs = qs.filter(material_lot=material_lot)
    else:
        qs = qs.filter(part__work_order=work_order, step=ruleset.step)
    qs = qs.order_by("-created_at")
    if ruleset.gate_window == GateWindow.ROLLING_N and ruleset.gate_window_n:
        ids = list(qs.values_list("id", flat=True)[: ruleset.gate_window_n])
        qs = QualityReports.objects.filter(id__in=ids).order_by("-created_at")  # tenant-safe: ids come from the already-scoped qs above
    return qs


def _report_defective_count(report) -> int:
    """Defective *units* attributable to a single report — mirrors
    ``receiving_inspection.evaluate_lot_acceptance``. Per-unit (DWI) capture
    counts sampled units where any measurement is out of spec; bulk/attribute
    capture uses the recorded ``defectives_found``; otherwise a FAIL report
    contributes 1."""
    from collections import defaultdict

    results = list(report.measurements.all())
    if results:
        by_unit = defaultdict(list)
        for r in results:
            by_unit[r.sample_number].append(r)
        return sum(1 for unit_results in by_unit.values()
                   if any(r.is_within_spec is False for r in unit_results))
    if report.defectives_found is not None:
        return report.defectives_found
    return 1 if report.status == "FAIL" else 0


def _compute_metric(ruleset, *, work_order, material_lot):
    """Return the gate metric value as a Decimal, or None when it can't fire
    (e.g. FAIL_RATE_PCT below the minimum sample)."""
    reports = list(_report_window_qs(ruleset, work_order, material_lot))
    statuses = [r.status for r in reports]

    if ruleset.gate_metric == GateMetric.CONSECUTIVE_FAILS:
        streak = 0
        for status in statuses:  # newest first; stop at the first non-FAIL
            if status == "FAIL":
                streak += 1
            else:
                break
        return Decimal(streak)

    if ruleset.gate_metric == GateMetric.DEFECTIVE_COUNT:
        # Sum defective units across the window's reports. `defectives_found`
        # lives on QualityReports, not MaterialLot — the DWI unit-by-unit path
        # records per-unit MeasurementResults on the report, so counting from the
        # reports is the only source (an empty window means nothing inspected yet).
        return Decimal(sum(_report_defective_count(r) for r in reports))

    if ruleset.gate_metric == GateMetric.FAIL_RATE_PCT:
        total = len(statuses)
        if total == 0 or (ruleset.gate_min_sample and total < ruleset.gate_min_sample):
            return None
        fails = sum(1 for s in statuses if s == "FAIL")
        return (Decimal(fails) / Decimal(total) * Decimal(100)).quantize(_Q3, rounding=ROUND_HALF_UP)

    return None


def _threshold_crossed(ruleset, metric_value: Decimal) -> bool:
    if ruleset.gate_threshold is None:
        return False
    return metric_value >= ruleset.gate_threshold


# ---------------------------------------------------------------------------
# Action dispatch — each maps to an existing service
# ---------------------------------------------------------------------------

def _dispatch_action(action, *, ruleset, firing, work_order, material_lot,
                     triggering_part, trigger, user):
    if action == GateAction.ROUTE_ALTERNATE:
        # No imperative effect here: the StepGateFiring record IS the signal that
        # Parts.get_next_step (decision_type='AGGREGATE', Phase 2b) routes on.
        return

    if action == GateAction.TIGHTEN_SAMPLING:
        if triggering_part is None:
            return  # streaming-only action; nothing to tighten on a lot
        from Tracker.services.mes.sampling_ruleset import create_sampling_fallback_trigger
        create_sampling_fallback_trigger(ruleset, triggering_part, trigger)
        return

    if action == GateAction.HOLD_LOT:
        _hold(ruleset, work_order=work_order, material_lot=material_lot)
        return

    if action == GateAction.RAISE_CAPA_SCAR:
        firing.created_capa = _raise_capa_or_scar(ruleset, firing, material_lot=material_lot, user=user)
        return

    if action == GateAction.REQUIRE_APPROVAL:
        firing.approval_request = _require_approval(ruleset, firing, user=user)
        return

    logger.warning("Unknown quality gate action: %s", action)


def _hold(ruleset, *, work_order, material_lot):
    if material_lot is not None:
        from Tracker.services.mes.inventory import quarantine_lot
        quarantine_lot(material_lot)
        return
    # In-process: quarantine the not-yet-advanced parts in the window.
    from Tracker.models import Parts, PartsStatus
    Parts.objects.filter(
        work_order=work_order, step=ruleset.step,
        part_status__in=[PartsStatus.PENDING, PartsStatus.IN_PROGRESS],
    ).update(part_status=PartsStatus.QUARANTINED)


def _raise_capa_or_scar(ruleset, firing, *, material_lot, user):
    """Auto-raise the CAPA/SCAR a tripped gate calls for.

    ``user`` is deliberately NOT used as the initiator. This path is
    machine-triggered: the gate fires because a threshold crossed, and the
    user in scope is merely whoever happened to save the record that tripped
    it — often an operator who does not hold ``initiate_capa``. Attributing
    the CAPA to them produces an audit trail that claims an unauthorized user
    initiated a governance record, and (via
    ``verify_capa_effectiveness``'s ``user == capa.initiated_by`` check)
    would silently mark them ineligible to verify unrelated work.

    So ``initiated_by`` stays NULL, which every consumer already treats as
    "System" (see the ``|default:'System'`` fallback in the capa.opened
    notification templates, and the ``_user_name(None) -> None`` report
    adapters).

    The acting user is not lost: ``StepGateFiring.triggered_by_report``
    links the QualityReport, whose ``detected_by`` is the person who filed
    it. The trail is CAPA <- firing.created_capa, firing ->
    triggered_by_report -> detected_by.

    Note this is attribution, not authorization — the gate must still fire
    regardless of who tripped it. Permission-checking here would let an
    operator's lack of ``initiate_capa`` suppress a quality gate, which is
    strictly worse than a mis-attributed record.
    """
    capa_type = ruleset.gate_capa_type or "CORRECTIVE"
    severity = ruleset.gate_capa_severity or "MAJOR"
    problem = (
        f"Auto-raised by quality gate '{ruleset.name}' at step "
        f"{ruleset.step.name}: {ruleset.gate_metric} = {firing.metric_value} "
        f"crossed threshold {firing.threshold}."
    )
    assignee = _default_capa_owner(ruleset.tenant)

    if capa_type == "SUPPLIER":
        supplier = getattr(material_lot, "supplier", None) or ruleset.supplier
        if supplier is None:
            raise ValueError("RAISE_CAPA_SCAR as SCAR needs a supplier (lot or ruleset).")
        from Tracker.services.qms.scar import open_scar
        report = firing.triggered_by_report
        return open_scar(
            supplier=supplier,
            problem_statement=problem,
            severity=severity, quality_report=report, material_lot=material_lot,
            user=None,  # system-raised — see docstring
            assigned_to=assignee,
        )

    from Tracker.models import CAPA
    return CAPA.objects.create(
        tenant=ruleset.tenant,
        capa_type="CORRECTIVE",
        severity=severity,
        status="OPEN",
        problem_statement=problem,
        initiated_by=None,  # system-raised — see docstring
        assigned_to=assignee,
    )


def _default_capa_owner(tenant):
    """Pick an owner for a machine-raised CAPA, preferring a QA Manager.

    Without an assignee a gate-raised CAPA is silent: `notify_assignment`
    returns early when `assigned_to_id` is unset, so nothing emits
    `capa.assigned`. The only other notification path is
    `trigger_approval_for_critical_capa`, which fires solely for
    MAJOR/CRITICAL and then only when the tenant has a current
    CAPA_APPROVAL ApprovalTemplate. A MINOR gate on a tenant without that
    template would create the record and tell nobody.

    Mirrors the QA-owner lookup the FAIL-QR auto-disposition signal already
    uses (Tracker/signals.py), but prefers QA Manager over QA Inspector
    since closing a CAPA is manager-gated (`verify_capa`). Returns None if
    the tenant has neither, which leaves the record unassigned rather than
    blocking the gate — the gate firing must not fail over staffing.
    """
    from Tracker.models import User
    for group_name in ('QA Manager', 'QA Inspector'):
        owner = User.objects.filter(
            user_roles__group__name=group_name,
            user_roles__group__tenant=tenant,
        ).first()
        if owner is not None:
            return owner
    return None


def _require_approval(ruleset, firing, *, user):
    """Open the approval a tripped gate demands.

    ``user`` is deliberately NOT recorded as the requester, for the same
    reason `_raise_capa_or_scar` doesn't record it as the initiator: the
    gate fired on an aggregate, and the user in scope is merely whoever
    saved the record that crossed the threshold.

    Here it has a second, sharper consequence. `submit_approval_response`
    treats ``requested_by == approver`` as self-approval and blocks it
    unless the template sets ``allow_self_approval`` *and* the approver
    writes a 10-character justification. With the tripping user recorded
    as requester, that guard fires on coincidence: if Mike happens to be
    an approver on this template and happens to be the one who saved the
    failing report, he's forced through the self-approval path on an
    approval he did not request. If Sarah had saved it instead, Sarah
    would be. A conflict-of-interest check that keys on who was standing
    nearby is worse than no check, because it looks deliberate.

    With no requester there is no self-approval relationship to police —
    ``can_approve()`` still governs who may respond at all.
    """
    template = ruleset.gate_approval_template
    if template is None:
        raise ValueError("REQUIRE_APPROVAL needs gate_approval_template set.")
    from Tracker.services.core.approval import create_approval_from_template
    return create_approval_from_template(
        content_object=firing,
        template=template,
        requested_by=None,  # system-raised — see docstring
        reason=f"Quality gate '{ruleset.name}' tripped at step {ruleset.step.name}.",
    )


def _looks_like_report(obj) -> bool:
    return obj is not None and obj.__class__.__name__ == "QualityReports"
