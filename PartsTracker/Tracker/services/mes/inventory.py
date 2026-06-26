"""
Inventory stock-state seam.

This is the deliberate boundary between receiving-inspection orchestration and
how stock state is actually represented. **Phase 1 implementation simply flips
`MaterialLot.status`** (status is a non-versioning operational field, so flips do
not mint new versions). **Phase 2 replaces these bodies with postings to the
append-only inventory ledger** — callers and signatures stay fixed, so the swap is
contained here and nowhere else.

Functions take a MaterialLot instance (matching `services/mes/material_lot.py`),
lock the row, validate the source state, and persist. Domain errors raise
``ValueError`` (the viewset translates to HTTP 400).
"""
from __future__ import annotations

from django.db import transaction


def _transition(lot, *, allowed_from, to):
    """Lock ``lot``, assert its status is in ``allowed_from``, set it to ``to``."""
    from Tracker.models import MaterialLot

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        if locked.status not in allowed_from:
            raise ValueError(
                f"Lot {locked.lot_number} is {locked.status}; "
                f"expected one of {', '.join(allowed_from)}."
            )
        locked.status = to
        locked.save(update_fields=["status", "updated_at"])
        lot.refresh_from_db()
    return lot


def mark_awaiting_inspection(lot):
    """RECEIVED → AWAITING_INSPECTION (an inspection has been opened for the lot)."""
    return _transition(lot, allowed_from=("RECEIVED",), to="AWAITING_INSPECTION")


def mark_lot_accepted(lot):
    """AWAITING_INSPECTION → ACCEPTED (passed receiving inspection; available to use)."""
    return _transition(lot, allowed_from=("AWAITING_INSPECTION",), to="ACCEPTED")


def mark_lot_rejected(lot):
    """AWAITING_INSPECTION/QUARANTINE → REJECTED (failed; pending disposition in Phase 2)."""
    return _transition(lot, allowed_from=("AWAITING_INSPECTION", "QUARANTINE"), to="REJECTED")


def quarantine_lot(lot):
    """Any non-terminal state → QUARANTINE (hold pending disposition)."""
    return _transition(
        lot,
        allowed_from=("RECEIVED", "AWAITING_INSPECTION", "ACCEPTED", "IN_USE"),
        to="QUARANTINE",
    )


def mark_dock_to_stock(lot):
    """RECEIVED → ACCEPTED for material that needs no incoming inspection
    (dock-to-stock). The basis (no RECEIVING step / skip-lot exemption) is the
    caller's to record."""
    return _transition(lot, allowed_from=("RECEIVED",), to="ACCEPTED")
