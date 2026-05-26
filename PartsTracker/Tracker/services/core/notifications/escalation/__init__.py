"""
Escalation subsystem — Phase 4 add-on to the rule dispatcher.

Public API:
    register_ack(event_code, *, is_acknowledged, is_cancelled=..., skip_recipient=...)
        Register the ack/cancel/skip predicates for an event. Called at module
        import time by each domain (qms, etc.) that owns events able to
        host an escalation chain.

    get_ack_registration(event_code) -> AckRegistration | None
        Lookup. Returns None if the event has no ack registration — the
        rule editor disables escalation UI for such events.

    is_acknowledged(event_code, source_record) -> bool
        Convenience: True iff the source has been ack'd per the registered
        predicate. Used by the beat task at fire-time.

    is_cancelled(event_code, source_record) -> bool
        Convenience: True iff the source is voided/closed (default predicate
        checks `source.archived`).

    is_skipped(event_code, source_record, user) -> bool
        Convenience: True iff `user` should be dropped from a step's outbox
        rows (e.g., already responded in a quorum-board scenario). False
        when no skip predicate is registered.

Runtime semantics: `Documents/NOTIFICATION_SYSTEM_DESIGN.md` → Escalation.
"""
from .registry import (
    AckRegistration,
    get_ack_registration,
    is_acknowledged,
    is_cancelled,
    is_skipped,
    list_acknowledged_events,
    register_ack,
)
from .runner import fire_one, tick_due

__all__ = [
    "AckRegistration",
    "fire_one",
    "get_ack_registration",
    "is_acknowledged",
    "is_cancelled",
    "is_skipped",
    "list_acknowledged_events",
    "register_ack",
    "tick_due",
]
