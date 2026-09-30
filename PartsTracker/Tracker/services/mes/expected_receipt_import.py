"""Expected-receipts import — open purchase-order lines, typed up from the ERP.

The ERP can't send anything to UQMES; a person copies the open PO lines into a sheet
and uploads it. So the import is shaped for that:

- **Matched on (PO number, line).** Re-uploading the same sheet — or next week's,
  which repeats most of this week's lines — updates rather than duplicates.
- **Only adds and updates, never closes.** A typed sheet is never a complete
  snapshot, so a line missing from it means nothing. See
  `material_lot.upsert_expected_receipt`.
- **Row by row.** A bad row is reported and skipped; the rest still land. One typo
  should not throw away the other ninety lines someone just keyed in.
- **Items by the number a buyer types:** a material's part number or a part type's
  ERP id, falling back to the exact name.
"""
from __future__ import annotations

import csv
import io
from decimal import Decimal, InvalidOperation

from Tracker.services.csv_utils import parse_date, parse_file
from Tracker.services.mes import material_lot as lot_svc

# Template columns, in order. `*` marks the required ones (stripped when matching).
TEMPLATE_COLUMNS = ["PO Number*", "PO Line*", "Item*", "Quantity*", "Promised Date*",
                    "Supplier", "Unit"]
TEMPLATE_EXAMPLE = ["4500123", "10", "SHIM-0.010", "5000", "2026-10-15", "Acme Seals", "EA"]

# Normalized header -> row key. Common spellings of the same column are accepted.
FIELD_MAP = {
    "po_number": "po", "po": "po", "po_#": "po", "erp_po_number": "po",
    "po_line": "line", "line": "line", "line_#": "line", "erp_po_line": "line",
    "item": "item", "part_number": "item", "material": "item", "part": "item",
    "quantity": "quantity", "qty": "quantity", "open_quantity": "quantity",
    "promised_date": "promised", "promised": "promised", "due_date": "promised",
    "supplier": "supplier", "vendor": "supplier",
    "unit": "unit", "uom": "unit", "unit_of_measure": "unit",
}


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS)
    w.writerow(TEMPLATE_EXAMPLE)
    return "﻿" + buf.getvalue()  # BOM so Excel opens it as UTF-8


def _text(value) -> str:
    """A cell as text. Excel hands a PO line of 10 back as 10.0."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def resolve_item(tenant, text: str):
    """(material, part_type) for what a buyer typed — exactly one set — or ValueError."""
    from Tracker.models import Material, PartTypes

    text = (text or "").strip()
    if not text:
        raise ValueError("No item given")
    mats = Material.objects.filter(tenant=tenant, is_active=True)  # tenant-safe: explicit tenant filter
    pts = PartTypes.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, is_current_version=True, can_buy=True)
    mat = list(mats.filter(part_number__iexact=text)[:2]) or list(mats.filter(name__iexact=text)[:2])
    pt = list(pts.filter(ERP_id__iexact=text)[:2]) or list(pts.filter(name__iexact=text)[:2])
    if len(mat) + len(pt) == 0:
        raise ValueError(f"No material or buyable part '{text}'")
    if len(mat) + len(pt) > 1:
        raise ValueError(f"'{text}' matches more than one item — use its part number")
    return (mat[0], None) if mat else (None, pt[0])


def _resolve_supplier(tenant, text: str):
    from Tracker.models import Companies
    if not text:
        return None
    found = list(Companies.objects.filter(tenant=tenant, name__iexact=text)[:2])  # tenant-safe: explicit tenant filter
    if not found:
        raise ValueError(f"No company named '{text}'")
    if len(found) > 1:
        raise ValueError(f"More than one company named '{text}'")
    return found[0]


def import_expected_receipts(*, tenant, file, filename: str) -> dict:
    """Parse and apply a sheet of open PO lines. Returns the per-row report the
    `ExpectedReceiptImportResultSerializer` describes. Raises ValueError only for a file
    that can't be read at all."""
    rows, _headers = parse_file(file, filename, field_map=FIELD_MAP)
    report = []
    counts = {lot_svc.IMPORT_CREATED: 0, lot_svc.IMPORT_UPDATED: 0,
              lot_svc.IMPORT_UNCHANGED: 0, lot_svc.IMPORT_ALREADY_RECEIVED: 0, "ERROR": 0}
    for n, row in enumerate(rows, start=1):
        po, line = _text(row.get("po")), _text(row.get("line"))
        if not any(_text(v) for v in row.values()):
            continue  # a blank line in the sheet
        entry = {"row": n, "erp_po_number": po, "erp_po_line": line,
                 "lot_number": None, "detail": ""}
        try:
            material, part_type = resolve_item(tenant, _text(row.get("item")))
            try:
                quantity = Decimal(_text(row.get("quantity")))
            except InvalidOperation:
                raise ValueError(f"Quantity '{_text(row.get('quantity'))}' isn't a number")
            promised = parse_date(row.get("promised"))
            if promised is None:
                raise ValueError("No promised date, or not a date")
            lot, outcome = lot_svc.upsert_expected_receipt(
                tenant=tenant, erp_po_number=po, erp_po_line=line, quantity=quantity,
                promised_date=promised.date() if hasattr(promised, "date") else promised,
                material=material, material_type=part_type,
                supplier=_resolve_supplier(tenant, _text(row.get("supplier"))),
                unit_of_measure=_text(row.get("unit")))
            entry["outcome"] = outcome
            entry["lot_number"] = lot.lot_number if lot else None
            if outcome == lot_svc.IMPORT_ALREADY_RECEIVED:
                entry["detail"] = "Already received — left alone"
        except ValueError as e:
            entry["outcome"] = "ERROR"
            entry["detail"] = str(e)
        counts[entry["outcome"]] += 1
        report.append(entry)
    return {
        "created": counts[lot_svc.IMPORT_CREATED],
        "updated": counts[lot_svc.IMPORT_UPDATED],
        "unchanged": counts[lot_svc.IMPORT_UNCHANGED],
        "already_received": counts[lot_svc.IMPORT_ALREADY_RECEIVED],
        "errors": counts["ERROR"],
        "rows": report,
    }
