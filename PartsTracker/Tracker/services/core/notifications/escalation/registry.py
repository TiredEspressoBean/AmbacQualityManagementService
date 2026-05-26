"""
Acknowledgement registry — maps event codes to ack/cancel predicates.

Each event that can host an escalation chain registers a pair of callables:

- `is_acknowledged(source_record) -> bool` — domain-specific ack check.
  Examples: a QualityReportDisposition reached `CLOSED`; a
  CapaVerification has a final effectiveness_result; an
  ApprovalResponse exists for the request.

- `is_cancelled(source_record) -> bool` — "source no longer relevant"
  check. Defaults to `getattr(source, 'archived', False)`, which covers
  the SecureModel.void() soft-delete case for every SecureModel-backed
  source. Override only when an event has a domain-specific "closed
  without ack" state (e.g. ApprovalRequest with status='WITHDRAWN').

Events without a registration cannot host an escalation chain. The rule
editor's EscalationCard disables the toggle for those events via the
catalog endpoint (E6).

The registry is populated at module-import time, the same way the event
registry works. Domains (qms, mes, …) register their acks inside their
respective `services/<domain>/escalation_acks.py` modules, which are
imported via `Tracker.apps.TrackerConfig.ready()`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Registration record
# =============================================================================

def _default_cancel_predicate(source_record) -> bool:
    """Catch SecureModel.void() — `archived=True` means the source is gone.
    Domains that need stronger cancel semantics override at registration.
    """
    return bool(getattr(source_record, "archived", False))


def _default_skip_predicate(source_record, user) -> bool:
    """Default: never skip. Domains needing quorum-aware reminders (skip
    users who already responded) override at registration. Examples:

      - `approval.requested`: skip if user already submitted an ApprovalResponse
      - `capa.pcr_review_required`: skip board members who already approved
      - `document.review_required`: skip reviewers who already signed off
    """
    return False


@dataclass(frozen=True)
class AckRegistration:
    """One event's escalation lifecycle predicates and source-model binding.

    `source_model` is the Django model class of the source record this
    event refers to (e.g. `QualityReports` for `ncr.opened`). The
    dispatcher uses it at fire-time to construct the `EscalationInstance`'s
    `(content_type, object_id)` pair from the event payload's `.id` field.

    `skip_recipient` is consulted by the escalation runner at step-fire
    time to drop already-responded users from a step's outbox rows. Used
    for quorum-board / track-who-responded events.
    """

    event_code: str
    source_model: type
    is_acknowledged: Callable[[object], bool]
    is_cancelled: Callable[[object], bool] = _default_cancel_predicate
    skip_recipient: Callable[[object, object], bool] = _default_skip_predicate


# =============================================================================
# Registry storage + public API
# =============================================================================

_REGISTRY: dict[str, AckRegistration] = {}


def register_ack(
    event_code: str,
    *,
    source_model: type,
    is_acknowledged: Callable[[object], bool],
    is_cancelled: Callable[[object], bool] | None = None,
    skip_recipient: Callable[[object, object], bool] | None = None,
) -> AckRegistration:
    """Register the ack/cancel/skip predicates and source-model binding for an event.

    `source_model` is the Django model class of the source record (e.g.
    `QualityReports` for `ncr.opened`). The dispatcher looks this up to
    construct the `EscalationInstance.source_content_type` from the
    payload's `.id` field at rule-fire time.

    `skip_recipient(source, user) -> bool` is called by the escalation
    runner per candidate at step-fire time. Return True to drop that user's
    outbox row for the step. Use for quorum/board events where some
    recipients have already responded and shouldn't get a reminder.

    Idempotent on event_code — registering twice with the same code
    overwrites, which is convenient when a module is re-imported during
    autoreload. Logs a debug message on overwrite for traceability.

    Returns the registered AckRegistration (useful for tests).
    """
    if event_code in _REGISTRY:
        logger.debug(
            "register_ack: overwriting existing registration for %r",
            event_code,
        )
    reg = AckRegistration(
        event_code=event_code,
        source_model=source_model,
        is_acknowledged=is_acknowledged,
        is_cancelled=is_cancelled or _default_cancel_predicate,
        skip_recipient=skip_recipient or _default_skip_predicate,
    )
    _REGISTRY[event_code] = reg
    return reg


def get_ack_registration(event_code: str) -> AckRegistration | None:
    """Look up an event's ack registration. Returns None if the event has
    no registered escalation support — the rule editor surfaces this as
    "Escalation isn't supported for this event yet."
    """
    return _REGISTRY.get(event_code)


def list_acknowledged_events() -> list[str]:
    """Event codes that support escalation, sorted alphabetically.
    Used by the rule editor's catalog endpoint to enable/disable the
    escalation toggle per-event.
    """
    return sorted(_REGISTRY.keys())


def is_acknowledged(event_code: str, source_record) -> bool:
    """Run the registered ack predicate. False if no registration exists
    (an unsupported event can't be acked — the dispatcher would never
    create an instance for it anyway).
    """
    reg = _REGISTRY.get(event_code)
    if reg is None:
        return False
    try:
        return bool(reg.is_acknowledged(source_record))
    except Exception:
        logger.exception(
            "is_acknowledged: ack predicate raised for event=%s source=%r",
            event_code, source_record,
        )
        return False


def is_cancelled(event_code: str, source_record) -> bool:
    """Run the registered cancel predicate. False if no registration
    exists — same fallback rule as `is_acknowledged`.
    """
    reg = _REGISTRY.get(event_code)
    if reg is None:
        return False
    try:
        return bool(reg.is_cancelled(source_record))
    except Exception:
        logger.exception(
            "is_cancelled: cancel predicate raised for event=%s source=%r",
            event_code, source_record,
        )
        return False


def is_skipped(event_code: str, source_record, user) -> bool:
    """Run the registered skip-recipient predicate. False (don't skip) if no
    registration exists OR the predicate isn't set OR raises — defensive
    default keeps step firings reaching their recipients.
    """
    reg = _REGISTRY.get(event_code)
    if reg is None:
        return False
    try:
        return bool(reg.skip_recipient(source_record, user))
    except Exception:
        logger.exception(
            "is_skipped: skip predicate raised for event=%s source=%r user=%r",
            event_code, source_record, getattr(user, "id", user),
        )
        return False


# =============================================================================
# Test helper
# =============================================================================

def _reset_registry_for_tests() -> None:
    """Tests that re-import or stub the registry use this to start fresh.
    Not part of the public API; named with leading underscore."""
    _REGISTRY.clear()
