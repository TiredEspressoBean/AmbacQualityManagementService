"""Stock on hand — the opening balance of each lot, typed up at go-live.

Current balances only, no history: each row is a lot that is on the shelf today,
already accepted. It is created ACCEPTED directly, not routed through receiving
(`route_received_lot`), whose inspection plans would put holds on stock that was
inspected long before UQMES existed.

- **Matched on lot number.** Re-uploading the sheet updates a lot it created, as
  long as nothing has been drawn from it yet. A lot already in use is left alone —
  its balance is UQMES's now, and is adjusted on the lot's page.
- **Items match as the expected-receipts import matches them** (`resolve_item`),
  so the two sheets agree about what "SHIM-0.010" is.
- **No PO reference.** An opening lot carries none: a later expected-receipts
  import of that PO line would find it and report it already received.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from Tracker.services.csv_utils import ambiguous_day_month, parse_date
from Tracker.services.mes.expected_receipt_import import _resolve_supplier, _text, resolve_item

CREATED, UPDATED, UNCHANGED, IN_USE, ERROR = "CREATED", "UPDATED", "UNCHANGED", "IN_USE", "ERROR"

# Template columns, in order. `*` marks the required ones (stripped when matching).
TEMPLATE_COLUMNS = ["Lot Number*", "Item*", "Quantity*", "Unit", "Location", "Received Date",
                    "Supplier", "Supplier Lot Number", "Heat Number", "Manufacture Date",
                    "Expiration Date", "Owner"]
COLUMN_HELP = {
    "Lot Number*": "The number on the lot's label. Unique: one row per lot.",
    "Item*": "A material's part number, or a buyable part type's ERP id (or exact name).",
    "Quantity*": "What is on the shelf now, in the item's stock unit.",
    "Unit": "Blank takes the material's unit of measure (EA otherwise).",
    "Location": "Where it is kept. A managed storage location's name, or free text.",
    "Received Date": "Blank means today.",
    "Supplier": "The company it was bought from, by exact name.",
    "Expiration Date": "Use-by date from the supplier, if any. Starts the lot's shelf-life clock.",
    "Owner": "Only for customer property (a customer's free-issue stock): the customer's name.",
}

# Normalized header -> row key.
FIELD_MAP = {
    "lot_number": "lot_number", "lot": "lot_number", "lot_#": "lot_number",
    "item": "item", "part_number": "item", "material": "item", "part": "item",
    "quantity": "quantity", "qty": "quantity", "on_hand": "quantity",
    "unit": "unit", "uom": "unit", "unit_of_measure": "unit",
    "location": "location", "storage_location": "location", "bin": "location",
    "received_date": "received_date", "received": "received_date",
    "supplier": "supplier", "vendor": "supplier",
    "supplier_lot_number": "supplier_lot_number", "supplier_lot": "supplier_lot_number",
    "heat_number": "heat_number", "heat": "heat_number",
    "manufacture_date": "manufacture_date",
    "expiration_date": "expiration_date", "expiry": "expiration_date", "use_by": "expiration_date",
    "owner": "owner",
}


def _date(row, key, what):
    raw = row.get(key)
    if raw in (None, ""):
        return None
    parsed = parse_date(raw)
    if parsed is None:
        raise ValueError(f"{what} '{_text(raw)}' isn't a date")
    return parsed.date() if hasattr(parsed, "date") else parsed


def _owner(tenant, text):
    company = _resolve_supplier(tenant, text)
    if company is not None and not company.is_customer:
        raise ValueError(f"'{company.name}' isn't set up as a customer, so it can't own stock")
    return company


def _read(tenant, row) -> dict:
    """The lot's fields from one row, or ValueError naming what's wrong."""
    from Tracker.services.core.clock import tenant_today

    lot_number = _text(row.get("lot_number"))
    if not lot_number:
        raise ValueError("No lot number")
    material, part_type = resolve_item(tenant, _text(row.get("item")))
    try:
        quantity = Decimal(_text(row.get("quantity")))
    except InvalidOperation:
        raise ValueError(f"Quantity '{_text(row.get('quantity'))}' isn't a number")
    if quantity <= 0:
        raise ValueError("Quantity must be more than zero — leave a used-up lot off the sheet")
    return {
        "lot_number": lot_number,
        "material": material,
        "material_type": part_type,
        "quantity": quantity,
        "unit_of_measure": (_text(row.get("unit"))
                            or getattr(material, "unit_of_measure", "") or "EA"),
        "storage_location": _text(row.get("location")),
        "received_date": _date(row, "received_date", "Received date") or tenant_today(tenant),
        "supplier": _resolve_supplier(tenant, _text(row.get("supplier"))),
        "supplier_lot_number": _text(row.get("supplier_lot_number")),
        "heat_number": _text(row.get("heat_number")),
        "manufacture_date": _date(row, "manufacture_date", "Manufacture date"),
        "expiration_date": _date(row, "expiration_date", "Expiration date"),
        "owner": _owner(tenant, _text(row.get("owner"))),
    }


def _apply(tenant, fields: dict) -> str:
    from django.db import IntegrityError, transaction
    from Tracker.models import MaterialLot
    from Tracker.services.life_tracking.shelf_life import attach_shelf_life

    existing = MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, lot_number__iexact=fields["lot_number"]).first()
    if existing is None:
        try:
            with transaction.atomic():
                lot = MaterialLot.objects.create(
                    tenant=tenant, status="ACCEPTED",
                    quantity_remaining=fields["quantity"], **fields)
                attach_shelf_life(lot)
        except IntegrityError:
            raise ValueError(f"Lot number '{fields['lot_number']}' is already taken")
        return CREATED

    # An opening lot this sheet made, still untouched, follows the sheet. Anything
    # else — drawn from, received, on order — is UQMES's record now.
    untouched = (existing.status == "ACCEPTED" and not existing.erp_po_number
                 and existing.quantity_remaining == existing.quantity)
    changes = {k: v for k, v in fields.items()
               if k != "lot_number" and getattr(existing, k) != v}
    if not changes:
        return UNCHANGED
    if not untouched:
        return IN_USE
    if "expiration_date" in changes or "manufacture_date" in changes:
        raise ValueError("Its shelf life is already running; change the dates on the lot's page")
    for k, v in changes.items():
        setattr(existing, k, v)
    if "quantity" in changes:
        existing.quantity_remaining = changes["quantity"]
    existing.save()
    return UPDATED


def import_stock_rows(*, tenant, rows: list[dict]) -> dict:
    """Apply parsed rows (keys as `FIELD_MAP` maps them) as opening-balance lots. A bad
    row is reported and skipped. Returns counts plus a per-row report."""
    counts = {CREATED: 0, UPDATED: 0, UNCHANGED: 0, IN_USE: 0, ERROR: 0}
    report = []
    for n, row in enumerate(rows, start=1):
        if not any(_text(v) for v in row.values()):
            continue  # a blank line in the sheet
        entry = {"row": n, "lot_number": _text(row.get("lot_number")), "detail": ""}
        try:
            entry["outcome"] = _apply(tenant, _read(tenant, row))
            if entry["outcome"] == IN_USE:
                entry["detail"] = "Already in use in UQMES — left alone"
            else:
                odd = [k.replace("_", " ") for k in ("received_date", "manufacture_date", "expiration_date")
                       if ambiguous_day_month(row.get(k))]
                if odd:
                    entry["detail"] = (f"Read the {', '.join(odd)} month first (03/04 is 4 March). "
                                       f"If that's wrong, write dates as YYYY-MM-DD.")
        except ValueError as e:
            entry["outcome"], entry["detail"] = ERROR, str(e)
        counts[entry["outcome"]] += 1
        report.append(entry)
    return {
        "created": counts[CREATED], "updated": counts[UPDATED],
        "unchanged": counts[UNCHANGED], "in_use": counts[IN_USE],
        "errors": counts[ERROR], "rows": report,
    }
