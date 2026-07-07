"""
Z1.4 inspection-severity switching (Normal ↔ Tightened ↔ Reduced).

The *effective* severity for a (receiving step, supplier) is runtime state
(`SamplingSeverityState`), driven by lot-acceptance history — not the versioned
`SamplingRuleSet.severity`, which is only the *starting* severity. This module
owns the transitions (the standard's switching procedures) and the resolver the
plan path reads.

Switching is a sampling-plan mechanic, safe to automate — distinct from the
recommend-only supplier-standing loop, which never auto-transitions an ASL record.
The one consequential endpoint, "discontinue inspection", is surfaced as a
recommendation (an event), never an automatic suspension.

Only applies to Z1.4 (`strategy='Z14'`) rulesets; C=0 escalates via the quality
gate's 100%/fallback path, and Z1.9 severity isn't tabulated.

Switching rules (ANSI/ASQ Z1.4 §):
  - Normal → Tightened: 2 of the last ≤5 lots rejected.
  - Tightened → Normal: 5 consecutive lots accepted.
  - Normal → Reduced: 10 consecutive lots accepted.
  - Reduced → Normal: a lot rejected, OR a lot lands in the reduced accept/reject
    gap (accepted but reduced discontinued).
  - Discontinue: tightened persists 5 consecutive lots without earning a return
    to normal → stop accepting the supplier's product (recommendation).
"""
from __future__ import annotations

from django.utils import timezone

# Switching thresholds (from the standard's procedures).
_NORMAL_TO_TIGHTENED_REJECTS = 2   # within the last _WINDOW lots
_WINDOW = 5
_TIGHTENED_TO_NORMAL_ACCEPTS = 5
_NORMAL_TO_REDUCED_ACCEPTS = 10
_DISCONTINUE_TIGHTENED_LOTS = 5


def effective_severity(step, supplier, ruleset) -> str:
    """The severity the plan should use: the runtime state if present, else the
    ruleset's starting severity. Non-Z14 rulesets always use their config severity
    (switching doesn't apply)."""
    if ruleset is None or (ruleset.strategy or "") != "Z14":
        return (ruleset.severity if ruleset and ruleset.severity else "NORMAL") or "NORMAL"
    state = _get_state(step, supplier)
    if state is None:
        return (ruleset.severity or "NORMAL") or "NORMAL"
    return state.severity


def _get_state(step, supplier):
    from Tracker.models import SamplingSeverityState
    return (SamplingSeverityState.objects
            .filter(step=step, supplier=supplier).first())


def _get_or_create_state(step, supplier, starting_severity):
    from Tracker.models import SamplingSeverityState
    state, _ = SamplingSeverityState.objects.get_or_create(
        step=step, supplier=supplier,
        defaults={"severity": starting_severity or "NORMAL", "severity_since": timezone.now()},
    )
    return state


def classify_lot(report) -> str:
    """One lot's outcome from its snapshot: 'R' reject | 'G' reduced accept/reject
    gap (accepted, but reduced discontinues) | 'A' clean accept."""
    from Tracker.services.qms.quality_gate import _report_defective_count
    ac = report.accept_number if report.accept_number is not None else 0
    re = report.reject_number if report.reject_number is not None else (ac + 1)
    d = _report_defective_count(report)
    if report.status == "FAIL" or d >= re:
        return "R"
    if d > ac:                # only reachable on reduced (re > ac + 1)
        return "G"
    return "A"


def _reset_regime(state, severity):
    state.severity = severity
    state.severity_since = timezone.now()
    state.recent_outcomes = []
    state.consecutive_accepts = 0
    state.lots_in_regime = 0
    state.discontinued = False


def update_after_lot(report) -> None:
    """Apply the Z1.4 switching procedures after a receiving lot is decided,
    incrementally (no reliance on timestamp ordering). No-op for non-Z14 plans."""
    if report.material_lot_id is None or report.step_id is None:
        return
    step = report.step
    supplier = report.material_lot.supplier
    from Tracker.services.qms.receiving_inspection import resolve_sampling_ruleset
    ruleset = resolve_sampling_ruleset(step, supplier)
    if ruleset is None or (ruleset.strategy or "") != "Z14":
        return

    state = _get_or_create_state(step, supplier, ruleset.severity)
    outcome = classify_lot(report)

    # Fold this lot into the running counters.
    window = (state.recent_outcomes or []) + [outcome]
    state.recent_outcomes = window[-_WINDOW:]
    state.consecutive_accepts = state.consecutive_accepts + 1 if outcome == "A" else 0
    state.lots_in_regime = state.lots_in_regime + 1

    transitioned = False
    emit_discontinue = False

    if state.severity == "NORMAL":
        if state.recent_outcomes.count("R") >= _NORMAL_TO_TIGHTENED_REJECTS:
            _reset_regime(state, "TIGHTENED"); transitioned = True
        elif state.consecutive_accepts >= _NORMAL_TO_REDUCED_ACCEPTS:
            _reset_regime(state, "REDUCED"); transitioned = True

    elif state.severity == "TIGHTENED":
        if state.consecutive_accepts >= _TIGHTENED_TO_NORMAL_ACCEPTS:
            _reset_regime(state, "NORMAL"); transitioned = True
        elif state.lots_in_regime >= _DISCONTINUE_TIGHTENED_LOTS and not state.discontinued:
            state.discontinued = True
            emit_discontinue = True

    elif state.severity == "REDUCED":
        if outcome in ("R", "G"):     # reject or gap reverts reduced → normal
            _reset_regime(state, "NORMAL"); transitioned = True

    state.save(update_fields=[
        "severity", "severity_since", "recent_outcomes", "consecutive_accepts",
        "lots_in_regime", "discontinued", "updated_at",
    ])
    if emit_discontinue:
        _emit_discontinued(state, supplier)


def _emit_discontinued(state, supplier) -> None:
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import InspectionDiscontinuedPayload

    payload = InspectionDiscontinuedPayload(
        id=str(state.id),
        tenant_id=str(state.tenant_id) if state.tenant_id else "",
        step_id=str(state.step_id),
        step_name=state.step.name,
        supplier_id=str(supplier.id) if supplier else "",
        supplier_name=supplier.name if supplier else "",
    )
    emit(
        "supplier.inspection_discontinued",
        tenant=state.tenant,
        payload=payload,
        correlation_id=f"severity_state:{state.id}",
        idempotency_key=f"supplier.inspection_discontinued:{state.id}:{state.severity_since.isoformat() if state.severity_since else ''}",
    )
