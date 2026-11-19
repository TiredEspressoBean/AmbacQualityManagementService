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


# A piece split off a delivery before its decision (a partial move to the lab, say) is
# still that delivery: it waits for the same decision and takes it — accepted, rejected,
# returned or scrapped with the rest, held and released with it — and never opens an
# inspection of its own (user ruling 2026-11-19). These are the states a piece follows
# its parent out of. Stock that has been accepted splits into lots of its own, so a
# move of the parent's stock (shipped, rejected from stock) doesn't carry its pieces.
FOLLOW_FROM = ("RECEIVED", "AWAITING_INSPECTION", "QUARANTINE", "REJECTED")


def following_children(lot) -> list:
    """The pieces of ``lot`` still following it: split off, in the state it's in, and
    not decided on their own — a piece rejected in a partial reject has a disposition
    of its own and goes where that sends it, not where the rest of the lot goes."""
    from Tracker.models import MaterialLot
    if lot.status not in FOLLOW_FROM:
        return []
    return list(MaterialLot.all_tenants.filter(  # tenant-safe: scoped by the parent FK
        parent_lot_id=lot.pk, status=lot.status, archived=False, dispositions__isnull=True))


def delivery_quantity(lot):
    """What's left of the delivery ``lot`` heads: its own remaining and that of every
    piece still following it — what one decision on it covers."""
    return lot.quantity_remaining + sum(
        (delivery_quantity(child) for child in following_children(lot)), 0)


def _transition(lot, *, allowed_from, to):
    """Lock ``lot``, assert its status is in ``allowed_from``, set it to ``to`` — and
    take every piece still following it along (``FOLLOW_FROM``)."""
    from Tracker.models import MaterialLot

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        if locked.status not in allowed_from:
            raise ValueError(
                f"Lot {locked.lot_number} is {locked.status}; "
                f"expected one of {', '.join(allowed_from)}."
            )
        children = following_children(locked)
        locked.status = to
        locked.save(update_fields=["status", "updated_at"])
        for child in children:
            _transition(child, allowed_from=(child.status,), to=to)
        lot.refresh_from_db()
    return lot


def mark_expected_lot_received(lot):
    """ON_ORDER → RECEIVED (an expected receipt physically arrived).

    Deliberately lands at RECEIVED, not ACCEPTED: incoming inspection still owns the
    decision about whether the stock is usable."""
    return _transition(lot, allowed_from=("ON_ORDER",), to="RECEIVED")


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


def restore_after_hold(lot, to: str):
    """QUARANTINE → ACCEPTED / IN_USE: a manual hold on stock is lifted and the lot is
    what it was before — not received again."""
    if to not in ("ACCEPTED", "IN_USE"):
        raise ValueError(f"A held lot goes back to stock, not to {to}.")
    return _transition(lot, allowed_from=("QUARANTINE",), to=to)


def release_hold(lot):
    """QUARANTINE → RECEIVED: a receiving hold is lifted and the lot goes back through
    routing (inspection or dock-to-stock), exactly as if it had just arrived. Only a
    receiving soft-hold is released this way; a lot held by a disposition is not."""
    return _transition(lot, allowed_from=("QUARANTINE",), to="RECEIVED")


def cancel_expected(lot):
    """ON_ORDER -> CANCELLED: an expected receipt that won't come (see
    `material_lot.cancel_expected_receipt`, which records why)."""
    return _transition(lot, allowed_from=("ON_ORDER",), to="CANCELLED")


def return_to_inspection(lot):
    """QUARANTINE → AWAITING_INSPECTION: a declined whole-lot reject request. The lot
    goes back to the inspection that asked for it — its report and execution are
    still open — rather than through routing, which opened a second one."""
    return _transition(lot, allowed_from=("QUARANTINE",), to="AWAITING_INSPECTION")


def reject_from_stock(lot):
    """ACCEPTED/IN_USE → REJECTED: a quality decision taken after the lot reached stock
    — escalating a partial reject to the whole lot."""
    return _transition(lot, allowed_from=("ACCEPTED", "IN_USE"), to="REJECTED")


def accept_on_concession(lot):
    """REJECTED/QUARANTINE → ACCEPTED: a use-as-is disposition puts nonconforming stock
    into use, on a recorded concession."""
    return _transition(lot, allowed_from=("REJECTED", "QUARANTINE"), to="ACCEPTED")


def scrap_lot(lot):
    """REJECTED/QUARANTINE → SCRAPPED (a scrap disposition)."""
    return _transition(lot, allowed_from=("REJECTED", "QUARANTINE"), to="SCRAPPED")


def mark_lot_shipped(lot):
    """ACCEPTED/IN_USE → SHIPPED: sent to a customer on a shipment — their property going
    back, or our material sold or kitted. No longer stock."""
    return _transition(lot, allowed_from=("ACCEPTED", "IN_USE"), to="SHIPPED")


def unship_lot(lot):
    """SHIPPED → ACCEPTED: a shipment recorded by mistake was voided; the lot never left."""
    return _transition(lot, allowed_from=("SHIPPED",), to="ACCEPTED")


def mark_lot_returned(lot):
    """REJECTED → RETURNED: shipped back to the supplier on a return-to-supplier
    disposition. The goods exist, at the vendor; they are no longer stock."""
    return _transition(lot, allowed_from=("REJECTED",), to="RETURNED")


def mark_dock_to_stock(lot):
    """RECEIVED → ACCEPTED for material that needs no incoming inspection
    (dock-to-stock). The basis (no RECEIVING step / skip-lot exemption) is the
    caller's to record."""
    return _transition(lot, allowed_from=("RECEIVED",), to="ACCEPTED")
