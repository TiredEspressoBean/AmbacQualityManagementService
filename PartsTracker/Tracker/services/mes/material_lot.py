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
        ValueError: lot status is not RECEIVED or IN_USE.
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

        if locked.status not in ("RECEIVED", "IN_USE"):
            raise ValueError(f"Cannot split a {locked.status} lot")

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
            status="RECEIVED",
            manufacture_date=locked.manufacture_date,
            expiration_date=locked.expiration_date,
            storage_location=locked.storage_location,
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


def receive_expected_lot(lot, *, lot_number: str, received_by, received_date=None,
                         quantity: Decimal | None = None, storage_location: str | None = None,
                         remainder: str | None = None):
    """ON_ORDER → RECEIVED: the truck arrived. Stamps the supplier's real lot number,
    who took it in, and when.

    ``quantity`` is accepted because deliveries differ from orders — short shipments and
    overages are normal, and the received amount is the one that is true. Passing None
    keeps the ordered quantity.

    A delivery short of the order needs ``remainder`` — the clerk's call from the packing
    slip, never inferred (the ERP can't tell us): ``BACKORDERED`` keeps the rest on order
    as a new expected lot (same item, supplier, PO and promised date); ``CLOSED`` closes the
    order at what arrived. Either way the lot records what had been ordered.

    Leaves the lot at RECEIVED rather than ACCEPTED: routing to incoming inspection (or
    dock-to-stock) is `receiving_inspection.route_received_lot`'s decision, and this must
    not smuggle stock into usable status behind it.
    """
    from django.utils import timezone
    from Tracker.models import MaterialLot
    from Tracker.services.mes import inventory

    if not lot_number:
        raise ValueError("A lot number is required to receive an expected lot")

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        if locked.status != "ON_ORDER":
            raise ValueError(
                f"Lot {locked.lot_number} is {locked.status}; only an ON_ORDER lot can "
                f"be received this way."
            )
        ordered = Decimal(str(locked.quantity))
        short_by = Decimal("0")
        if quantity is not None:
            if Decimal(str(quantity)) <= Decimal("0"):
                raise ValueError("Received quantity must be greater than zero")
            short_by = ordered - Decimal(str(quantity))
            locked.quantity = quantity
            locked.quantity_remaining = quantity
        update = ["lot_number", "received_by", "received_date",
                  "quantity", "quantity_remaining", "storage_location", "updated_at"]
        if short_by > 0:
            if remainder not in ("BACKORDERED", "CLOSED"):
                raise ValueError(
                    f"{quantity} of {ordered} arrived — say whether more is coming "
                    f"(back-ordered) or that's all (closed).")
            locked.ordered_quantity = ordered
            locked.short_receipt = remainder
            update += ["ordered_quantity", "short_receipt"]

        locked.lot_number = lot_number
        locked.received_by = received_by
        if storage_location is not None:
            locked.storage_location = storage_location.strip()
        # The shop floor's day (Tenant.default_timezone), not UTC's: a receipt at 8 pm
        # in a UTC-5 plant was dated tomorrow.
        from Tracker.services.core.clock import tenant_today
        locked.received_date = received_date or tenant_today(locked.tenant)
        locked.save(update_fields=update)
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
IMPORT_ALREADY_RECEIVED = "ALREADY_RECEIVED"


def upsert_expected_receipt(*, tenant, erp_po_number: str, erp_po_line: str,
                            quantity: Decimal, promised_date, material=None,
                            material_type=None, supplier=None, unit_of_measure: str = ""):
    """One row of an expected-receipts import, matched on (PO, line). Returns
    ``(lot | None, outcome)``.

    The import is typed up by a person from the ERP — the ERP can't send it — so it is
    never a complete snapshot. It therefore **only adds and updates**: a PO line missing
    from the file says nothing, and nothing here closes or cancels an order. Closing is
    a person's act (receiving short with "that's all").

    - An open (ON_ORDER) lot on that PO line → quantity, promised date, supplier and unit
      are brought up to date. For a back-ordered remainder that is the open quantity.
    - None open, but the line was already received → left alone (``ALREADY_RECEIVED``):
      re-importing last week's sheet must not put a delivered order back on order.
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
        if on_line.exists():
            return None, IMPORT_ALREADY_RECEIVED
        lot = record_expected_receipt(
            tenant=tenant, quantity=quantity, promised_date=promised_date,
            material=material, material_type=material_type, supplier=supplier,
            unit_of_measure=unit_of_measure, erp_po_number=erp_po_number,
            erp_po_line=erp_po_line)
        return lot, IMPORT_CREATED

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
