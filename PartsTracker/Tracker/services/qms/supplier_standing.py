"""
Supplier standing — the scorecard → qualification-standing loop (RECOMMEND-ONLY).

Reads the read-only scorecard rollup (`supplier_scorecard.compute_supplier_scorecard`)
and, on a threshold breach, **recommends** a qualification-standing review
(conditional / suspend / restore). It deliberately does **NOT** transition the
qualification: auto-suspending a supplier on a metric is consequential, so a human
confirms via the SupplierQualification lifecycle (`grant` / `suspend`). The
recommendation is surfaced via the `supplier.standing_review` event
(notification-rule eligible) and returned for the UI.

The thresholds are the scorecard's own A/B/C rating — single source of truth — so
this module doesn't duplicate them; it maps rating + current standing → a recommended
review action.
"""
from __future__ import annotations

from dataclasses import dataclass

ACTION_NONE = 'NONE'
ACTION_REVIEW_CONDITIONAL = 'REVIEW_CONDITIONAL'
ACTION_REVIEW_SUSPEND = 'REVIEW_SUSPEND'
ACTION_REVIEW_RESTORE = 'REVIEW_RESTORE'


@dataclass(frozen=True)
class StandingRecommendation:
    """A recommend-only assessment of a supplier's qualification standing.
    `recommended_action` is a *review* suggestion; no state has changed."""
    supplier_id: str
    rating: str | None                  # scorecard tier
    rating_reason: str
    current_statuses: tuple[str, ...]    # statuses of the supplier's ACTIVE qualifications
    recommended_action: str
    reason: str


def _recommend(sc, active_statuses: list[str]) -> tuple[str, str]:
    """Map scorecard + current standing → a review recommendation. Pure."""
    has_approved = 'APPROVED' in active_statuses
    all_approved = bool(active_statuses) and all(s == 'APPROVED' for s in active_statuses)

    # Breach: scorecard C while the supplier is still approved for something.
    if sc.rating == 'C' and has_approved:
        if sc.open_scar_count > 0 or sc.reject_rate >= 0.10:
            return ACTION_REVIEW_SUSPEND, f"Scorecard C - {sc.rating_reason}. Recommend suspension review."
        return ACTION_REVIEW_CONDITIONAL, f"Scorecard C - {sc.rating_reason}. Recommend conditional-status review."

    # Recovery: metrics back to A but standing is still CONDITIONAL (not all APPROVED).
    if sc.rating == 'A' and active_statuses and not all_approved:
        return ACTION_REVIEW_RESTORE, f"Scorecard A - {sc.rating_reason}. Recommend restoring full approval."

    return ACTION_NONE, sc.rating_reason or "Standing within thresholds."


def evaluate_supplier_standing(supplier) -> StandingRecommendation:
    """Recommend-only: compute a standing recommendation from the supplier's
    scorecard + current active qualifications. **Makes no state change.**"""
    from Tracker.services.qms.supplier_scorecard import compute_supplier_scorecard
    from Tracker.models import SupplierQualification

    sc = compute_supplier_scorecard(supplier)
    active_statuses = list(
        SupplierQualification.objects
        .filter(supplier=supplier, status__in=SupplierQualification.ACTIVE_STATUSES)
        .values_list('status', flat=True)
    )
    action, reason = _recommend(sc, active_statuses)
    return StandingRecommendation(
        supplier_id=str(supplier.id),
        rating=sc.rating,
        rating_reason=sc.rating_reason,
        current_statuses=tuple(active_statuses),
        recommended_action=action,
        reason=reason,
    )


def review_and_notify(supplier) -> StandingRecommendation:
    """Evaluate a supplier's standing and, when a review is recommended, emit a
    `supplier.standing_review` event (notification-rule eligible). Recommend-only —
    never transitions the qualification. Returns the recommendation."""
    rec = evaluate_supplier_standing(supplier)
    if rec.recommended_action != ACTION_NONE:
        _emit_standing_review(supplier, rec)
    return rec


def _emit_standing_review(supplier, rec: StandingRecommendation) -> None:
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import SupplierStandingReviewPayload

    payload = SupplierStandingReviewPayload(
        id=str(supplier.id),
        tenant_id=str(supplier.tenant_id) if supplier.tenant_id else "",
        supplier_id=str(supplier.id),
        supplier_name=supplier.name,
        rating=rec.rating or "",
        recommended_action=rec.recommended_action,
        reason=rec.reason,
    )
    emit(
        "supplier.standing_review",
        tenant=supplier.tenant,
        payload=payload,
        correlation_id=f"supplier:{supplier.id}",
        # Keyed by action so a *changed* recommendation re-notifies, but a repeat
        # of the same recommendation doesn't spam.
        idempotency_key=f"supplier.standing_review:{supplier.id}:{rec.recommended_action}",
    )
