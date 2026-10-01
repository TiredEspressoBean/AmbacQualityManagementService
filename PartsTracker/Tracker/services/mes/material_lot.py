"""
MaterialLot aggregate services.

MaterialLot is physical inventory and is NOT versioned (metadata edits are plain
audited updates; the CoC is a separate controlled Document). This service handles
the split flow — a pure quantity operation: the new lot is a child and the
parent's quantity_remaining decrements.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction


def split_material_lot(lot, quantity: Decimal, reason: str = ""):
    """Split ``quantity`` off ``lot`` into a new child MaterialLot.

    Uses SELECT FOR UPDATE to prevent concurrent splits from overdrawing the
    same lot. Returns the new child MaterialLot.

    Args:
        lot: The parent MaterialLot to split.
        quantity: Amount to split off. Must be positive and <= quantity_remaining.
        reason: Optional reason (retained for audit / future use).

    Raises:
        ValueError: quantity is not positive.
        ValueError: quantity exceeds lot.quantity_remaining.
        ValueError: lot status is not one that holds splittable stock.
    """
    from Tracker.models import MaterialLot

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)

        if quantity <= Decimal("0"):
            raise ValueError("Quantity must be greater than zero")

        if quantity > locked.quantity_remaining:
            raise ValueError(
                f"Cannot split {quantity}, only {locked.quantity_remaining} remaining"
            )

        # AWAITING_INSPECTION: a partial reject splits the bad pieces off mid-inspection.
        # QUARANTINE: the same, for a lot under a hold. ACCEPTED: stock divided across
        # locations or boxes.
        if locked.status not in ("RECEIVED", "AWAITING_INSPECTION", "QUARANTINE",
                                 "ACCEPTED", "IN_USE"):
            raise ValueError(f"Cannot split a {locked.status} lot")
        # The pieces are what the lot is: accepted stock splits into accepted stock
        # (consumption draws ACCEPTED/IN_USE only, so a RECEIVED child of good stock
        # could never be used), a held lot's pieces stay held for the same reason. A lot
        # still in receiving keeps its child at RECEIVED, as before.
        if locked.status in ("ACCEPTED", "IN_USE"):
            child_status, child_hold = "ACCEPTED", ""
        elif locked.status == "QUARANTINE":
            child_status, child_hold = "QUARANTINE", locked.hold_reason
        else:
            child_status, child_hold = "RECEIVED", ""

        child_count = locked.child_lots.count()
        child_lot_number = f"{locked.lot_number}-{child_count + 1:02d}"

        child = MaterialLot.objects.create(
            tenant=locked.tenant,
            lot_number=child_lot_number,
            parent_lot=locked,
            material_type=locked.material_type,
            material=locked.material,
            material_description=locked.material_description,
            supplier=locked.supplier,
            supplier_lot_number=locked.supplier_lot_number,
            received_date=locked.received_date,
            received_by=locked.received_by,
            quantity=quantity,
            quantity_remaining=quantity,
            unit_of_measure=locked.unit_of_measure,
            status=child_status,
            hold_reason=child_hold,
            manufacture_date=locked.manufacture_date,
            expiration_date=locked.expiration_date,
            storage_location=locked.storage_location,
            # Traceability travels with the pieces: same melt, same source, same PO,
            # same certificate.
            heat_number=locked.heat_number,
            source_type=locked.source_type,
            erp_po_number=locked.erp_po_number,
            erp_po_line=locked.erp_po_line,
            promised_date=locked.promised_date,
            certificate_of_conformance=locked.certificate_of_conformance,
            # Customer property stays the customer's, every piece of it.
            owner=locked.owner,
        )

        locked.quantity_remaining -= quantity
        if locked.quantity_remaining <= 0:
            locked.status = "CONSUMED"
        locked.save()

        # Sync the caller's in-memory instance.
        lot.refresh_from_db()

    return child


def record_expected_receipt(*, tenant, quantity: Decimal, promised_date, material=None,
                            material_type=None, unit_of_measure: str = "", supplier=None,
                            erp_po_number: str = "", erp_po_line: str = "",
                            lot_number: str = ""):
    """Record stock that is **ordered but not yet delivered** as an ON_ORDER lot.

    UQMES does not own purchasing — the PO lives in the ERP and we only reference it
    (`erp_po_number`). What planning needs is the *supply signal*: without it, netting sees
    only what has physically arrived, so the sourcing report tells you to order something
    that is already on a truck.

    ``promised_date`` is required, not optional. Both consumers of incoming supply filter
    on ``promised_date__isnull=False``, and rightly so: a receipt with no date cannot be
    time-phased into a bucket, so it would be counted as cover without ever being placed.
    An undated expectation is not planning information.

    ``lot_number`` is usually unknown at order time — the supplier assigns it. A placeholder
    is generated from the PO reference so the tenant-unique constraint holds; the real
    number replaces it at receipt.
    """
    from django.db.models import Q
    from Tracker.models import MaterialLot

    if (material is None) == (material_type is None):
        raise ValueError("An expected receipt is of a material or a part — one of the two")
    if quantity is None or Decimal(str(quantity)) <= Decimal("0"):
        raise ValueError("Expected quantity must be greater than zero")
    if promised_date is None:
        raise ValueError(
            "A promised delivery date is required — an expected receipt with no date "
            "cannot be placed in a planning bucket."
        )

    if not lot_number:
        stem = f"ONORDER-{erp_po_number}" if erp_po_number else "ONORDER"
        # tenant-safe: explicit tenant filter
        taken = set(
            MaterialLot.objects.filter(tenant=tenant)
            .filter(Q(lot_number=stem) | Q(lot_number__startswith=f"{stem}-"))
            .values_list("lot_number", flat=True)
        )
        lot_number = stem
        n = 1
        while lot_number in taken:
            n += 1
            lot_number = f"{stem}-{n:02d}"

    return MaterialLot.objects.create(
        tenant=tenant,
        lot_number=lot_number,
        material=material,
        material_type=material_type,
        supplier=supplier or getattr(material or material_type, "preferred_supplier", None),
        erp_po_number=erp_po_number,
        erp_po_line=erp_po_line,
        promised_date=promised_date,
        quantity=quantity,
        quantity_remaining=quantity,
        unit_of_measure=unit_of_measure or getattr(material, "unit_of_measure", "") or "EA",
        status="ON_ORDER",
        # received_date / received_by stay null — nothing has been received yet.
    )


def next_lot_number(tenant) -> str:
    """Our own lot number for a receipt: LOT-<year>-00001, per tenant.

    The standard practice (SAP's internal batch numbers, the traceability guides): the
    system numbers each receipt itself, and the supplier's batch number is kept beside
    it in `supplier_lot_number`. A supplier's number can't be ours — two vendors both
    print "240915", a back-order repeats the same lot — and ours is unique.
    """
    from Tracker.models import MaterialLot
    from Tracker.services.core.clock import tenant_today
    from Tracker.utils.sequences import generate_next_sequence
    return generate_next_sequence(
        queryset=MaterialLot.objects, number_field='lot_number',
        prefix=f"LOT-{tenant_today(tenant).year}-", padding=5, tenant=tenant)


def next_lot_numbers(tenant, count: int) -> list[str]:
    """`count` consecutive lot numbers from `next_lot_number` — for a batch numbered
    before any of it is saved."""
    if count <= 0:
        return []
    first = next_lot_number(tenant)
    stem, n = first.rsplit("-", 1)
    return [f"{stem}-{int(n) + i:0{len(n)}d}" for i in range(count)]


def receive_expected_lot(lot, *, received_by, lot_number: str = "",
                         supplier_lot_number: str | None = None, received_date=None,
                         quantity: Decimal | None = None, storage_location: str | None = None,
                         remainder: str | None = None, received_as_quantity=None,
                         received_as_unit: str = "", heat_number: str | None = None,
                         source_type: str | None = None):
    """ON_ORDER → RECEIVED: the truck arrived. Numbers the lot (ours, `next_lot_number`,
    unless ``lot_number`` gives one), records the supplier's lot number as printed,
    who took it in, and when.

    ``quantity`` is accepted because deliveries differ from orders — short shipments and
    overages are normal, and the received amount is the one that is true. Passing None
    keeps the ordered quantity.

    A delivery short of the order needs ``remainder`` — the clerk's call from the packing
    slip, never inferred (the ERP can't tell us): ``BACKORDERED`` keeps the rest on order
    as a new expected lot (same item, supplier, PO and promised date); ``CLOSED`` means
    nothing more is expected — UQMES's copy stops expecting the rest. It does not close the
    PO line, which is the ERP's (ISA-95 Level 4); if the ERP still shows it open, the next
    expected-receipts sheet expects it again. Either way the lot records what was ordered.

    ``received_as_quantity`` / ``received_as_unit`` take what the clerk counted in the
    item's buying unit ("3 boxes"); it converts to the stock quantity (`to_stock_quantity`)
    and both are kept. Given, it replaces ``quantity``.

    Leaves the lot at RECEIVED rather than ACCEPTED: routing to incoming inspection (or
    dock-to-stock) is `receiving_inspection.route_received_lot`'s decision, and this must
    not smuggle stock into usable status behind it.
    """
    from django.utils import timezone
    from Tracker.models import MaterialLot
    from Tracker.services.mes import inventory

    from django.db import IntegrityError

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        if locked.status != "ON_ORDER":
            raise ValueError(
                f"Lot {locked.lot_number} is {locked.status}; only an ON_ORDER lot can "
                f"be received this way."
            )
        ordered = Decimal(str(locked.quantity))
        short_by = Decimal("0")
        update_extra = []
        if received_as_quantity is not None and received_as_unit not in ("", "STOCK"):
            quantity = to_stock_quantity(locked.item, received_as_quantity, received_as_unit)
            locked.received_as_quantity = Decimal(str(received_as_quantity))
            locked.received_as_unit = received_as_unit
            update_extra += ["received_as_quantity", "received_as_unit"]
        if heat_number is not None:
            locked.heat_number = heat_number.strip()
            update_extra.append("heat_number")
        if source_type is not None:
            locked.source_type = source_type
            update_extra.append("source_type")
        if quantity is not None:
            if Decimal(str(quantity)) <= Decimal("0"):
                raise ValueError("Received quantity must be greater than zero")
            short_by = ordered - Decimal(str(quantity))
            locked.quantity = quantity
            locked.quantity_remaining = quantity
        update = ["lot_number", "received_by", "received_date",
                  "quantity", "quantity_remaining", "storage_location", "updated_at",
                  *update_extra]
        if short_by > 0:
            if remainder not in ("BACKORDERED", "CLOSED"):
                raise ValueError(
                    f"{quantity} of {ordered} arrived — say whether more is coming "
                    f"(back-ordered) or that's all (nothing more expected).")
            locked.ordered_quantity = ordered
            locked.short_receipt = remainder
            update += ["ordered_quantity", "short_receipt"]

        if supplier_lot_number is not None:
            locked.supplier_lot_number = supplier_lot_number.strip()
            update.append("supplier_lot_number")
        locked.lot_number = (lot_number or "").strip() or next_lot_number(locked.tenant)
        locked.received_by = received_by
        if storage_location is not None:
            locked.storage_location = storage_location.strip()
        # The shop floor's day (Tenant.default_timezone), not UTC's: a receipt at 8 pm
        # in a UTC-5 plant was dated tomorrow.
        from Tracker.services.core.clock import tenant_today
        locked.received_date = received_date or tenant_today(locked.tenant)
        try:
            with transaction.atomic():
                locked.save(update_fields=update)
        except IntegrityError:
            raise ValueError(f"Lot number {locked.lot_number} is already in use — leave it "
                             f"blank to have one assigned.")
        if short_by > 0 and remainder == "BACKORDERED":
            # The rest stays on order as its own expected lot, so planning still sees it.
            record_expected_receipt(
                tenant=locked.tenant, quantity=short_by, promised_date=locked.promised_date,
                material=locked.material, material_type=locked.material_type,
                unit_of_measure=locked.unit_of_measure, supplier=locked.supplier,
                erp_po_number=locked.erp_po_number, erp_po_line=locked.erp_po_line,
            )
        # Status flip goes through the stock-state seam so the ledger swap stays contained.
        inventory.mark_expected_lot_received(locked)
        lot.refresh_from_db()

    return lot


def record_expected_receipts(*, tenant, rows: list[dict]) -> list:
    """Several expected receipts at once — a buyer raising what they just ordered from a
    list of shortages. All or nothing: a half-recorded batch leaves the buyer unsure which
    rows made it, and re-submitting would double the ones that did.

    Each row takes `record_expected_receipt`'s keyword arguments (tenant excluded)."""
    with transaction.atomic():
        return [record_expected_receipt(tenant=tenant, **row) for row in rows]


# Outcomes of one row of an expected-receipts import.
IMPORT_CREATED = "CREATED"
IMPORT_UPDATED = "UPDATED"
IMPORT_UNCHANGED = "UNCHANGED"
# A line that had been received, expected again because the sheet shows it open: a
# replacement after a return, a blanket line released again — or a sheet the ERP hasn't
# caught up with, which is why it is flagged rather than refused.
IMPORT_REOPENED = "REOPENED"


def upsert_expected_receipt(*, tenant, erp_po_number: str, erp_po_line: str,
                            quantity: Decimal, promised_date, material=None,
                            material_type=None, supplier=None, unit_of_measure: str = ""):
    """One row of an expected-receipts import, matched on (PO, line). Returns
    ``(lot | None, outcome)``.

    The PO line is the ERP's (ISA-95 Level 4): whether it is open, done, released again
    or replaced after a return is its call, and the sheet is its word. UQMES holds a copy
    to plan against, so the import **mirrors** — it never rules a line finished. It is
    typed up by a person, never a complete snapshot, so it only adds and updates: a line
    missing from the file says nothing.

    - An open (ON_ORDER) lot on that PO line → quantity, promised date, supplier and unit
      are brought up to date. For a back-ordered remainder that is the open quantity.
    - None open, but the line was received before → expected again (``REOPENED``), and
      the caller says so: the sheet shows it open, which a replacement or a re-release
      means — or a sheet typed before the ERP caught up, which only its typist can tell.
    - Otherwise → a new expected receipt.
    """
    from Tracker.models import MaterialLot

    erp_po_number = (erp_po_number or "").strip()
    erp_po_line = (erp_po_line or "").strip()
    if not erp_po_number or not erp_po_line:
        raise ValueError("An imported expected receipt needs its PO number and line")

    on_line = MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, erp_po_number=erp_po_number, erp_po_line=erp_po_line)
    open_lot = on_line.filter(status="ON_ORDER").order_by("created_at").first()
    if open_lot is None:
        received_before = on_line.exists()
        lot = record_expected_receipt(
            tenant=tenant, quantity=quantity, promised_date=promised_date,
            material=material, material_type=material_type, supplier=supplier,
            unit_of_measure=unit_of_measure, erp_po_number=erp_po_number,
            erp_po_line=erp_po_line)
        return lot, IMPORT_REOPENED if received_before else IMPORT_CREATED

    if (material is not None and open_lot.material_id != material.id) or (
            material_type is not None and open_lot.material_type_id != material_type.id):
        raise ValueError(
            f"PO {erp_po_number} line {erp_po_line} is on order for {open_lot.item_name}, "
            f"not {(material or material_type).name}")
    if quantity is None or Decimal(str(quantity)) <= Decimal("0"):
        raise ValueError("Expected quantity must be greater than zero")
    if promised_date is None:
        raise ValueError("A promised delivery date is required")

    changes = {"quantity": Decimal(str(quantity)), "promised_date": promised_date}
    if supplier is not None:
        changes["supplier"] = supplier
    if unit_of_measure:
        changes["unit_of_measure"] = unit_of_measure
    changed = [f for f, v in changes.items() if getattr(open_lot, f) != v]
    if not changed:
        return open_lot, IMPORT_UNCHANGED
    for f in changed:
        setattr(open_lot, f, changes[f])
    if "quantity" in changed:
        # Nothing has been drawn from a lot that hasn't arrived.
        open_lot.quantity_remaining = open_lot.quantity
        changed.append("quantity_remaining")
    open_lot.save(update_fields=changed + ["updated_at"])
    return open_lot, IMPORT_UPDATED


# How far ahead an expected receipt counts as "due soon" on the late-deliveries list.
DUE_SOON_DAYS = 3
DELIVERY_OVERDUE = "OVERDUE"
DELIVERY_DUE_SOON = "DUE_SOON"


def delivery_state(lot, today) -> str | None:
    """OVERDUE (promised date passed), DUE_SOON (due within DUE_SOON_DAYS, today
    included), or None — for an ON_ORDER lot. Anything received has no delivery state.

    ``today`` is the plant's day (`services.core.clock.tenant_today`), passed in so a
    list can resolve it once rather than per row."""
    from datetime import timedelta
    if lot.status != "ON_ORDER" or lot.promised_date is None:
        return None
    if lot.promised_date < today:
        return DELIVERY_OVERDUE
    if lot.promised_date <= today + timedelta(days=DUE_SOON_DAYS):
        return DELIVERY_DUE_SOON
    return None


def to_stock_quantity(item, amount, unit: str) -> Decimal:
    """What a clerk counted, in the unit they counted it in, as a stock quantity.

    ``unit`` is a `PURCHASE_UNIT_CHOICES` code. STOCK (or blank) is already the stock
    unit. BOX / LB convert through the item's `units_per_purchase_unit` — and only
    when that is the unit the item is bought in, so "3 boxes" of something bought by
    the pound is refused rather than guessed at."""
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("The received amount must be greater than zero")
    if unit in ("", "STOCK"):
        return amount
    bought_in = getattr(item, "purchase_unit", "STOCK")
    factor = getattr(item, "units_per_purchase_unit", None)
    if unit != bought_in:
        raise ValueError(
            f"{getattr(item, 'name', 'This item')} is bought by "
            f"{dict(_purchase_units()).get(bought_in, bought_in).lower()}, not "
            f"{dict(_purchase_units()).get(unit, unit).lower()}")
    if not factor:
        raise ValueError(
            f"{getattr(item, 'name', 'This item')} has no stock units per "
            f"{dict(_purchase_units()).get(unit, unit).lower()} set — enter the count instead")
    return amount * Decimal(str(factor))


def _purchase_units():
    from Tracker.models.mes_standard import PURCHASE_UNIT_CHOICES
    return PURCHASE_UNIT_CHOICES


def adjust_quantity(lot, *, new_quantity: Decimal, reason: str, user):
    """Correct what's left of a lot to what's physically there — counted 1,940, not
    2,000; a box crushed in the rack. UQMES isn't the stock register (the ERP is), but
    the floor's figure is what planning nets against, so a known-wrong number has to be
    fixable, and fixable only with a reason on record.

    Sets `quantity_remaining` (what the lot has left), writing a RecordEdit with the
    reason. Raises ValueError for a negative quantity, no reason, or a lot not yet in
    stock (an ON_ORDER lot's quantity is the order, changed by re-expecting it)."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import MaterialLot, RecordEdit

    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Say why the quantity is being adjusted")
    new_quantity = Decimal(str(new_quantity))
    if new_quantity < 0:
        raise ValueError("A lot can't hold less than nothing")
    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        # Only stock on our shelf. A rejected lot's quantity is the disposition's, a
        # returned one is at the vendor.
        if locked.status in ("ON_ORDER", "CONSUMED", "SCRAPPED", "REJECTED", "RETURNED"):
            raise ValueError(f"Lot {locked.lot_number} is {locked.status}; there is no "
                             f"stock on hand to adjust.")
        old = locked.quantity_remaining
        if old == new_quantity:
            return locked
        # Counted down to nothing: the lot is used up, as consumption would leave it —
        # left ACCEPTED it was offered for picking at zero. Only stock is used up; a lot
        # still in receiving or held is dispositioned, not zeroed.
        update = ["quantity_remaining", "updated_at"]
        if new_quantity == 0:
            if locked.status not in ("ACCEPTED", "IN_USE"):
                raise ValueError(f"Lot {locked.lot_number} is {locked.status}; reject or "
                                 f"scrap it rather than counting it to zero.")
            locked.status = "CONSUMED"
            update.append("status")
        RecordEdit.objects.create(
            tenant=locked.tenant,
            content_type=ContentType.objects.get_for_model(MaterialLot),
            object_id=locked.id, field_name="quantity_remaining",
            old_value=str(old), new_value=str(new_quantity), reason=reason, edited_by=user)
        locked.quantity_remaining = new_quantity
        locked.save(update_fields=update)
    lot.refresh_from_db()
    return lot
