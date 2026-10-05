"""Expected-receipts import — open purchase-order lines, typed up from the ERP.

The ERP can't send anything to UQMES; a person copies the open PO lines into a sheet
and uploads it. So the import is shaped for that:

- **Matched on (PO number, line).** Re-uploading the same sheet — or next week's,
  which repeats most of this week's lines — updates rather than duplicates.
- **Mirrors the ERP's open lines.** The PO line is the ERP's; the sheet is its word.
  A line missing from it means nothing (a typed sheet is never complete), and a line
  received before but shown open again is expected again, flagged. See
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

from Tracker.services.csv_utils import ambiguous_day_month, parse_date, parse_file
from Tracker.services.mes import material_lot as lot_svc

# Template columns, in order. `*` marks the required ones (stripped when matching).
# "Open Quantity": what is still to come on the line, as the ERP's open-PO report shows
# it — a line partly received carries only the rest. (Its ordered total would reset a
# back-ordered remainder to the full order on re-import.)
TEMPLATE_COLUMNS = ["PO Number*", "PO Line*", "Item*", "Open Quantity*", "Promised Date*",
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


def _reopened_note(tenant, po, line, quantity) -> str:
    """Why a received line is on order again — so whoever typed the sheet can tell a
    replacement or a re-release from an ERP that hadn't caught up."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import MaterialLot, RecordEdit
    on_line = MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, erp_po_number=po, erp_po_line=line)
    cancelled = on_line.filter(status="CANCELLED").order_by("-updated_at").first()
    if cancelled is not None:
        edit = (RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, content_type=ContentType.objects.get_for_model(MaterialLot),
            object_id=cancelled.id, field_name="status", new_value="CANCELLED")
            .select_related("edited_by").order_by("-edited_at").first())
        who = ""
        if edit is not None:
            name = edit.edited_by.display_name if edit.edited_by_id else "someone"
            who = f" on {edit.edited_at:%d %b %Y} by {name}"
        return (f"Line {line} was cancelled{who}; expected again because the sheet still "
                f"shows {quantity:g} open. If the ERP has cancelled it, cancel this one too.")
    last = on_line.filter(received_date__isnull=False).order_by("-received_date").first()
    when = f" on {last.received_date:%d %b %Y} (lot {last.lot_number})" if last else ""
    return (f"Line {line} was received{when}; expecting {quantity:g} more because the sheet "
            f"shows it open. If the ERP hasn't caught up, cancel this expected receipt.")


def import_expected_receipts(*, tenant, file, filename: str) -> dict:
    """Parse and apply a sheet of open PO lines. Returns the per-row report the
    `ExpectedReceiptImportResultSerializer` describes. Raises ValueError only for a file
    that can't be read at all."""
    rows, _headers = parse_file(file, filename, field_map=FIELD_MAP)
    return import_expected_rows(tenant=tenant, rows=rows)


def import_expected_rows(*, tenant, rows: list[dict]) -> dict:
    """Apply already-parsed rows (keys as `FIELD_MAP` maps them). The master migration
    workbook's "On order" sheet comes in this way, its sheet parsed with the rest."""
    report = []
    counts = {lot_svc.IMPORT_CREATED: 0, lot_svc.IMPORT_UPDATED: 0,
              lot_svc.IMPORT_UNCHANGED: 0, lot_svc.IMPORT_REOPENED: 0, "ERROR": 0}
    for n, row in enumerate(rows, start=1):
        po, line = _text(row.get("po")), _text(row.get("line"))
        if not any(_text(v) for v in row.values()):
            continue  # a blank line in the sheet
        entry = {"row": n, "erp_po_number": po, "erp_po_line": line,
                 "lot_number": None, "lot_id": None, "detail": ""}
        try:
            material, part_type = resolve_item(tenant, _text(row.get("item")))
            try:
                quantity = Decimal(_text(row.get("quantity")))
            except InvalidOperation:
                raise ValueError(f"Quantity '{_text(row.get('quantity'))}' isn't a number")
            promised = parse_date(row.get("promised"))
            if promised is None:
                raise ValueError("No promised date, or not a date")
            entry_date = promised.date() if hasattr(promised, "date") else promised
            lot, outcome = lot_svc.upsert_expected_receipt(
                tenant=tenant, erp_po_number=po, erp_po_line=line, quantity=quantity,
                promised_date=promised.date() if hasattr(promised, "date") else promised,
                material=material, material_type=part_type,
                supplier=_resolve_supplier(tenant, _text(row.get("supplier"))),
                unit_of_measure=_text(row.get("unit")))
            entry["outcome"] = outcome
            entry["lot_number"] = lot.lot_number if lot else None
            entry["lot_id"] = str(lot.id) if lot else None
            if outcome == lot_svc.IMPORT_REOPENED:
                entry["detail"] = _reopened_note(tenant, po, line, quantity)
            elif ambiguous_day_month(row.get("promised")):
                # 03/04 reads as March 4th (month first); said, so a day-first sheet
                # isn't swapped silently.
                entry["detail"] = (f"Promised date read as {entry_date:%d %b %Y} (month first). "
                                   f"If that's wrong, write dates as YYYY-MM-DD.")
        except ValueError as e:
            entry["outcome"] = "ERROR"
            entry["detail"] = str(e)
        counts[entry["outcome"]] += 1
        report.append(entry)
    return {
        "created": counts[lot_svc.IMPORT_CREATED],
        "updated": counts[lot_svc.IMPORT_UPDATED],
        "unchanged": counts[lot_svc.IMPORT_UNCHANGED],
        "reopened": counts[lot_svc.IMPORT_REOPENED],
        "errors": counts["ERROR"],
        "rows": report,
    }
