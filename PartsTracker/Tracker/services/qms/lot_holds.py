"""Holds on a material lot — all of them at once.

A lot can be held for several reasons together: no CoC, no heat number, an unqualified
supplier. Each is cleared on its own (the paperwork arrives, a person releases the
supplier hold), and the lot leaves quarantine only when none is left.

`MaterialLot.hold_reasons` is the list; `hold_reason` mirrors its first entry so every
filter, badge and metric that reads a single reason keeps working. These functions are
the only writers of either, so the two never disagree.
"""
from __future__ import annotations


def holds(lot) -> list[str]:
    codes = list(lot.hold_reasons or [])
    if not codes and lot.hold_reason:  # a row from before the list existed
        codes = [lot.hold_reason]
    return codes


def _write(lot, codes: list[str]) -> None:
    lot.hold_reasons = codes
    lot.hold_reason = codes[0] if codes else ""
    lot.save(update_fields=["hold_reasons", "hold_reason", "updated_at"])


def add_hold(lot, code: str) -> None:
    codes = holds(lot)
    if code not in codes:
        _write(lot, codes + [code])


def remove_hold(lot, code: str) -> list[str]:
    """Drop ``code``; returns the holds that remain."""
    codes = [c for c in holds(lot) if c != code]
    _write(lot, codes)
    return codes


def clear_holds(lot) -> None:
    if holds(lot):
        _write(lot, [])


def hold(lot, code: str) -> None:
    """Put ``lot`` on hold for ``code``: quarantined (if it isn't already) and the
    reason added beside any it already has."""
    from Tracker.services.mes import inventory
    if lot.status != "QUARANTINE":
        inventory.quarantine_lot(lot)
        lot.refresh_from_db(fields=["status"])
    add_hold(lot, code)
