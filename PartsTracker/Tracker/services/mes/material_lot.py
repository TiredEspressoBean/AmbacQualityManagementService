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


def record_expected_receipt(*, tenant, material, quantity: Decimal, promised_date,
                            unit_of_measure: str = "", supplier=None,
                            erp_po_number: str = "", lot_number: str = ""):
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
        supplier=supplier or getattr(material, "preferred_supplier", None),
        erp_po_number=erp_po_number,
        promised_date=promised_date,
        quantity=quantity,
        quantity_remaining=quantity,
        unit_of_measure=unit_of_measure or material.unit_of_measure,
        status="ON_ORDER",
        # received_date / received_by stay null — nothing has been received yet.
    )


def receive_expected_lot(lot, *, lot_number: str, received_by, received_date=None,
                         quantity: Decimal | None = None):
    """ON_ORDER → RECEIVED: the truck arrived. Stamps the supplier's real lot number,
    who took it in, and when.

    ``quantity`` is accepted because deliveries differ from orders — short shipments and
    overages are normal, and the received amount is the one that is true. Passing None
    keeps the ordered quantity.

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
        if quantity is not None:
            if Decimal(str(quantity)) <= Decimal("0"):
                raise ValueError("Received quantity must be greater than zero")
            locked.quantity = quantity
            locked.quantity_remaining = quantity

        locked.lot_number = lot_number
        locked.received_by = received_by
        locked.received_date = received_date or timezone.now().date()
        locked.save(update_fields=[
            "lot_number", "received_by", "received_date",
            "quantity", "quantity_remaining", "updated_at",
        ])
        # Status flip goes through the stock-state seam so the ledger swap stays contained.
        inventory.mark_expected_lot_received(locked)
        lot.refresh_from_db()

    return lot
