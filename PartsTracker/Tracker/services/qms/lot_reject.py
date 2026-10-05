"""Rejecting received material, and what the decision does to the lot.

Before this, a rejected lot was a dead end: it went to REJECTED, a disposition was
opened beside it (linked only through the inspection report), and closing that
disposition did nothing to the lot — return-to-supplier, scrap and use-as-is all
left it REJECTED for ever.

Now:

- **A partial reject (the default).** The inspector says how many pieces are bad.
  Those are split into their own lot, which is rejected and dispositioned; the rest of
  the lot goes on to acceptance. The quantity is recorded in pieces.
- **A whole-lot reject (VDMR).** Takes the `reject_whole_lot` permission — granted to
  QA managers by default, and to inspectors where a tenant chooses. Without it, the
  request holds the whole lot (WHOLE_LOT_REJECT_REQUESTED) for someone with it to
  confirm, or to release so the good part can be accepted.
- **Escalating later.** Someone with the permission can reject what's left of a lot
  already accepted — the unconsumed remainder; anything used is not reversed.
- **The disposition drives the lot** (`apply_disposition_to_lot`): use-as-is accepts
  it on a concession, scrap scraps it, return-to-supplier leaves it rejected until the
  dock ships it back (`ship_back`, → RETURNED).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from Tracker.services.mes import inventory
from Tracker.services.qms import lot_holds

WHOLE_LOT_PERMISSION = "reject_whole_lot"
HOLD_WHOLE_LOT_REJECT_REQUESTED = "WHOLE_LOT_REJECT_REQUESTED"
# What an inspector can decide at the point of rejecting. Use-as-is is a later,
# separately authorized decision (it needs a concession reference) on the disposition.
REJECT_DISPOSITIONS = ("RETURN_TO_SUPPLIER", "SCRAP")


def can_reject_whole_lot(user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False)
                and user.has_tenant_perm(WHOLE_LOT_PERMISSION))


def _open_disposition(lot, *, user, disposition_type, quantity, description, report=None,
                      severity="MAJOR"):
    from Tracker.models import QuarantineDisposition
    disposition = QuarantineDisposition.objects.create(
        tenant=lot.tenant,
        material_lot=lot,
        quantity=quantity,
        disposition_type=disposition_type,
        description=description or "",
        severity=severity or "MAJOR",
        assigned_to=user if user and getattr(user, "is_authenticated", False) else None,
    )
    if report is not None:
        disposition.quality_reports.add(report)
    return disposition


def reject_lot(report, user, *, disposition_type: str = "RETURN_TO_SUPPLIER",
               rejected_quantity=None, whole_lot: bool = False, description: str = "",
               severity: str = "MAJOR"):
    """Reject a lot under receiving inspection. Returns ``(rejected_lot, disposition,
    outcome)`` where outcome is ``PARTIAL``, ``WHOLE_LOT`` or ``WHOLE_LOT_REQUESTED``.

    ``rejected_quantity`` (stock units) below the lot's quantity is a partial reject;
    at or above it, or ``whole_lot=True``, is a whole-lot reject."""
    from Tracker.services.qms import receiving_inspection as ri

    lot = report.material_lot
    if lot is None:
        raise ValueError("Report is not a receiving inspection (no material_lot).")
    if disposition_type not in REJECT_DISPOSITIONS:
        raise ValueError("At rejection, the lot goes back to the supplier or is scrapped.")
    if lot.status not in ("AWAITING_INSPECTION", "QUARANTINE"):
        raise ValueError(f"Lot {lot.lot_number} is {lot.status}; it is not under inspection.")

    total = Decimal(str(lot.quantity_remaining))
    qty = None if rejected_quantity is None else Decimal(str(rejected_quantity))
    if qty is not None and qty <= 0:
        raise ValueError("The rejected quantity must be greater than zero.")
    whole = whole_lot or qty is None or qty >= total

    with transaction.atomic():
        if not whole:
            from Tracker.services.mes.material_lot import split_material_lot
            child = split_material_lot(lot, qty, reason="Rejected at receiving inspection")
            # A held lot's pieces are split off already held.
            if child.status != "QUARANTINE":
                inventory.quarantine_lot(child)
            inventory.mark_lot_rejected(child)
            child.refresh_from_db()
            lot_holds.clear_holds(child)  # rejected now; the parent's holds aren't the child's
            disposition = _open_disposition(
                child, user=user, disposition_type=disposition_type, quantity=qty,
                description=description, report=report, severity=severity)
            # The rest of the lot carries on: accepted on this inspection. (A held lot's
            # remainder stays held — its hold is a separate decision.)
            lot.refresh_from_db()
            # An expired remainder is held for its shelf life instead — not a failure of
            # the reject: raised here, it rolled the reject back while its message still
            # said the lot was quarantined.
            if lot.status == "AWAITING_INSPECTION" and not ri.hold_if_expired(lot):
                ri.accept(report, user)
            apply_disposition_to_lot(disposition)
            return child, disposition, "PARTIAL"

        if not can_reject_whole_lot(user):
            # A request, not a decision: hold the whole lot for someone who may decide.
            # Added beside any hold the lot already has (an unqualified supplier, say):
            # it used to overwrite it, and releasing the request lost the other.
            lot_holds.hold(lot, HOLD_WHOLE_LOT_REJECT_REQUESTED)
            disposition = _open_disposition(
                lot, user=user, disposition_type=disposition_type, quantity=total,
                description=description, report=report, severity=severity)
            return lot, disposition, "WHOLE_LOT_REQUESTED"

        ri.reject(report, user)
        lot.refresh_from_db()
        lot_holds.clear_holds(lot)  # rejected: the decision supersedes every hold
        disposition = _open_disposition(
            lot, user=user, disposition_type=disposition_type, quantity=total,
            description=description, report=report, severity=severity)
        apply_disposition_to_lot(disposition)
        return lot, disposition, "WHOLE_LOT"


def confirm_whole_lot_reject(lot, user):
    """Someone with `reject_whole_lot` confirms an inspector's whole-lot request."""
    from Tracker.models import QuarantineDisposition
    if not can_reject_whole_lot(user):
        raise ValueError("Rejecting a whole lot needs the reject-whole-lot permission.")
    if lot.status != "QUARANTINE" or HOLD_WHOLE_LOT_REJECT_REQUESTED not in lot_holds.holds(lot):
        raise ValueError(f"Lot {lot.lot_number} has no whole-lot reject waiting.")
    with transaction.atomic():
        lot_holds.clear_holds(lot)  # rejected: the decision supersedes every hold
        inventory.mark_lot_rejected(lot)
        disposition = (QuarantineDisposition.objects  # tenant-safe: .objects auto-scopes
                       .filter(material_lot=lot).exclude(current_state="CLOSED")
                       .order_by("-created_at").first())
        if disposition is not None:
            apply_disposition_to_lot(disposition)
    lot.refresh_from_db()
    return lot, disposition


# How a declined whole-lot request's disposition is marked: closed with no decision
# taken, so it is no reject (dock metrics leave it out of PPM).
DECLINED_NOTE = "Whole-lot reject declined"


def decline_whole_lot_request(lot, user, reason: str) -> None:
    """Close the pending disposition of a whole-lot request that QA has declined."""
    from django.utils import timezone
    from Tracker.models import QuarantineDisposition
    for d in (QuarantineDisposition.objects  # tenant-safe: .objects auto-scopes
              .filter(material_lot=lot).exclude(current_state="CLOSED")):
        note = f"{DECLINED_NOTE}: {reason}"
        d.resolution_notes = f"{d.resolution_notes}\n{note}".strip() if d.resolution_notes else note
        d.resolution_completed = True
        d.resolution_completed_by = user
        d.resolution_completed_at = timezone.now()
        d.current_state = "CLOSED"
        d.save()


def reject_remainder(lot, user, *, disposition_type: str = "RETURN_TO_SUPPLIER",
                     description: str = ""):
    """Escalate to the whole lot after the fact: reject what's left of a lot already
    accepted (what's been used stays used). Needs `reject_whole_lot`."""
    if not can_reject_whole_lot(user):
        raise ValueError("Rejecting a whole lot needs the reject-whole-lot permission.")
    if disposition_type not in REJECT_DISPOSITIONS:
        raise ValueError("The remainder goes back to the supplier or is scrapped.")
    remaining = Decimal(str(lot.quantity_remaining))
    if lot.status not in ("ACCEPTED", "IN_USE") or remaining <= 0:
        raise ValueError(f"Lot {lot.lot_number} has no accepted stock left to reject.")
    with transaction.atomic():
        inventory.reject_from_stock(lot)
        lot.refresh_from_db()
        report = lot.quality_reports.order_by("-created_at").first()
        disposition = _open_disposition(
            lot, user=user, disposition_type=disposition_type, quantity=remaining,
            description=description, report=report)
        apply_disposition_to_lot(disposition)
    lot.refresh_from_db()
    return lot, disposition


def apply_disposition_to_lot(disposition) -> None:
    """What a disposition's decision does to its lot. Idempotent.

    - USE_AS_IS → ACCEPTED (on the concession recorded on the disposition)
    - SCRAP → SCRAPPED, nothing left in stock
    - RETURN_TO_SUPPLIER → stays REJECTED until shipped back (`ship_back`)
    """
    lot = disposition.material_lot
    if lot is None or not disposition.disposition_type:
        return
    lot.refresh_from_db()
    if disposition.disposition_type == "USE_AS_IS" and lot.status in ("REJECTED", "QUARANTINE"):
        lot_holds.clear_holds(lot)  # accepted on concession: the decision covers its holds
        inventory.accept_on_concession(lot)
    elif disposition.disposition_type == "SCRAP" and lot.status in ("REJECTED", "QUARANTINE"):
        inventory.scrap_lot(lot)
        lot.refresh_from_db()
        lot.quantity_remaining = Decimal("0")
        lot.save(update_fields=["quantity_remaining", "updated_at"])


def ship_back(lot, user, *, note: str = "", rma_number: str = "", replacement_promised_date=None):
    """The dock ships a return-to-supplier lot back: REJECTED → RETURNED, and the
    disposition is complete. Raises ValueError for a lot not awaiting return.

    ``rma_number`` is the supplier's return authorisation. With
    ``replacement_promised_date`` the supplier is sending replacement goods: an expected
    receipt for the returned quantity is recorded (same item, supplier and PO line),
    pointing back at this lot, so planning sees it coming and the buyer can chase it."""
    from django.utils import timezone
    from Tracker.models import QuarantineDisposition
    disposition = (QuarantineDisposition.objects  # tenant-safe: .objects auto-scopes
                   .filter(material_lot=lot, disposition_type="RETURN_TO_SUPPLIER")
                   .exclude(current_state="CLOSED").order_by("-created_at").first())
    if lot.status != "REJECTED" or disposition is None:
        raise ValueError(f"Lot {lot.lot_number} is not waiting to go back to the supplier.")
    with transaction.atomic():
        returned_qty = lot.quantity_remaining
        inventory.mark_lot_returned(lot)
        lot.refresh_from_db()
        lot.quantity_remaining = Decimal("0")
        lot.rma_number = (rma_number or "").strip() or lot.rma_number
        lot.save(update_fields=["quantity_remaining", "rma_number", "updated_at"])
        if replacement_promised_date is not None and returned_qty > 0:
            from Tracker.services.mes.material_lot import record_expected_receipt
            record_expected_receipt(
                tenant=lot.tenant, quantity=returned_qty, promised_date=replacement_promised_date,
                material=lot.material, material_type=lot.material_type,
                unit_of_measure=lot.unit_of_measure, supplier=lot.supplier,
                erp_po_number=lot.erp_po_number, erp_po_line=lot.erp_po_line, replaces=lot)
        stamp = f"Shipped back to the supplier{': ' + note.strip() if note and note.strip() else ''}."
        disposition.resolution_notes = (f"{disposition.resolution_notes}\n{stamp}".strip()
                                        if disposition.resolution_notes else stamp)
        disposition.resolution_completed = True
        disposition.resolution_completed_by = user
        disposition.resolution_completed_at = timezone.now()
        disposition.current_state = "CLOSED"
        disposition.save()
    return lot, disposition
