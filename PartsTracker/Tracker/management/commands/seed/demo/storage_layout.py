"""The demo's storage: one facility, two sets of racks (user go 2026-11-18, for the
shipping/receiving director's demo).

- **Main Stores** (warehouse) → Rack A–D → shelves A-1…D-3: bought parts and material.
  The building keeps the name the training tracks use; the stock sits on its shelves.
- **Finished Goods** (warehouse) → Rack F1, F2 → shelves F1-1…F2-3: finished units
  waiting to ship.

Shelf names are unique and are their label codes. The dock, Shipping, Tool Crib, QA Lab
and the machines' locations are the other seeders' and stay as they are.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

LAYOUT = {
    "Main Stores": ["A", "B", "C", "D"],
    "Finished Goods": ["F1", "F2"],
}
SHELVES_PER_RACK = 3

# Which shelf each opening stock lot is put away on (by lot number). Several shelves per
# rack hold something; the rest are empty, as a real store's are.
STOCK_SHELF = {
    "STOCK-CRI-SEAL": "A-1",    # the Receiving track's count: Seal & O-Ring Kit, 400
    "STOCK-CRI-SOL": "A-1",
    "STOCK-CRI-SPR": "A-2",
    "STOCK-CRI-VLV": "B-1",
    "STOCK-CRI-NZL": "B-3",     # the count waiting for a lead (one short on the shelf)
    "STOCK-CRI-NZL-B": "B-3",
    # Newer lots of the same bought items (draws take the older lot first).
    "STOCK-CRI-SOL-B": "C-1",
    "STOCK-CRI-SEAL-B": "C-3",
    "STOCK-CRI-SPR-B": "D-2",
}
# The count left submitted for a lead (dark_exhibits.seed_cycle_count).
WAITING_COUNT_SHELF = "B-3"

# Finished units on the shelf by the dock, waiting for their shipment (by serial).
FINISHED_SHELF = {
    "INJ-0042-011": "F1-1", "INJ-0042-012": "F1-1",
    "INJ-0042-013": "F1-2", "INJ-0042-014": "F1-2",
    "INJ-0042-015": "F2-1", "INJ-0042-016": "F2-1",
}

# Newer opening lots (material, quantity, days since received), so the racks' roll-ups
# read like a store, not one lot per item.
EXTRA_LOTS = {
    "STOCK-CRI-SOL-B": ("Solenoid Coil", Decimal("200"), 5),
    "STOCK-CRI-SEAL-B": ("Seal & O-Ring Kit", Decimal("300"), 8),
    "STOCK-CRI-SPR-B": ("Injector Spring", Decimal("150"), 3),
}


def build_layout(tenant) -> dict:
    """The warehouses, racks and shelves, each made once. Returns them by name."""
    from Tracker.models import StorageLocation
    from Tracker.services.mes.locations import seed_location

    made = {}
    for warehouse, racks in LAYOUT.items():
        top = seed_location(tenant, warehouse, kind="WAREHOUSE")
        if top.kind != "WAREHOUSE":
            StorageLocation.objects.filter(pk=top.pk).update(kind="WAREHOUSE")  # tenant-safe: own pk
        made[warehouse] = top
        for rack in racks:
            rack_loc = seed_location(tenant, f"Rack {rack}", kind="RACK", parent=top, code=f"R-{rack}")
            made[rack_loc.name] = rack_loc
            for n in range(1, SHELVES_PER_RACK + 1):
                name = f"{rack}-{n}"
                made[name] = seed_location(tenant, name, kind="SHELF", parent=rack_loc, code=name)
    return made


def shelf_for_lot(tenant, lot_number: str):
    """Where an opening stock lot is put away (the warehouse itself for one not listed)."""
    layout = build_layout(tenant)
    return layout.get(STOCK_SHELF.get(lot_number, ""), layout["Main Stores"])


def seed_extra_stock(tenant, received_by, today) -> int:
    """Newer accepted lots of the bought materials, each on its shelf."""
    from Tracker.models import Material, MaterialLot
    made = 0
    for lot_number, (material_name, qty, days) in EXTRA_LOTS.items():
        material = Material.objects.filter(tenant=tenant, name=material_name).first()  # tenant-safe: explicit tenant filter
        if material is None:
            continue
        _, created = MaterialLot.objects.get_or_create(
            tenant=tenant, lot_number=lot_number,
            defaults=dict(
                material=material, material_description=f"On-hand stock: {material_name}",
                supplier_lot_number=f"{material.part_number}-{days:02d}", erp_po_number="PO-STOCK",
                received_date=(today - timedelta(days=days)).date(), received_by=received_by,
                quantity=qty, quantity_remaining=qty, unit_of_measure=material.unit_of_measure or "EA",
                hold_reason="", location=shelf_for_lot(tenant, lot_number), status="ACCEPTED"))
        made += int(created)
    return made


def shelve_finished_units(tenant, user) -> int:
    """Put the finished units waiting to ship on the Finished Goods shelves — as recorded
    moves, the way the shipping clerk would."""
    from Tracker.models import Parts
    from Tracker.services.mes.locations import move_parts
    layout = build_layout(tenant)
    moved = 0
    by_shelf: dict = {}
    for serial, shelf in FINISHED_SHELF.items():
        part = Parts.objects.filter(tenant=tenant, ERP_id=serial).first()  # tenant-safe: explicit tenant filter
        if part is not None and part.part_status != "SHIPPED" and part.location_id != layout[shelf].id:
            by_shelf.setdefault(shelf, []).append(part)
    for shelf, parts in by_shelf.items():
        moved += move_parts(tenant, parts, to=layout[shelf], user=user,
                            reason="Finished and boxed; waiting for its shipment")
    return moved
