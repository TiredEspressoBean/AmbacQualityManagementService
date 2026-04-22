"""
MaterialLot aggregate services.

MaterialLot is HYBRID versioned — spec edits (supplier cert, expiration,
material type) route via create_new_version; quantity_remaining changes do
not. This service handles the split flow (pure quantity operation — new lot is
a child, parent's quantity_remaining decrements). No versioning involved in
split.
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
