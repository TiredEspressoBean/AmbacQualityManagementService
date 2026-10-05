"""Receipts for the ERP — what the dock received, by PO line, to post back.

ISA-95's Level 3 → Level 4 direction: the PO is the ERP's, the receipt is ours, and the
ERP needs to hear what arrived and what passed so it can post the goods receipt and
match the invoice. The ERP here takes no feed (a person carries a sheet), so this is
that sheet: one row per delivery, with the quantities a buyer keys in.

A delivery is a lot as received (`parent_lot` null). A partial reject splits the bad
pieces into child lots, so they are counted back onto their delivery: received =
accepted + rejected + still waiting for a decision. No prices — UQMES holds none.

Posting: once a person has keyed a delivery into the ERP, it is marked posted
(`mark_posted`), with the numbers that were posted. Only a delivery whose decision is
final can be — posting one still under inspection would put numbers in the ERP that
the decision may change. Each row carries its ERP status: ready to post, awaiting a
decision, posted, or changed since posted (a reject or recount after posting).
"""
from __future__ import annotations

import io
from decimal import Decimal

COLUMNS = [
    "PO Number", "PO Line", "Received", "Item", "Item Name", "Supplier",
    "Our Lot", "Supplier Lot", "Unit", "Ordered", "Received Qty", "Accepted",
    "Rejected", "Awaiting Decision", "Short Delivery", "Decision", "ERP Status",
]

READY, NOT_READY, POSTED, CHANGED = "Ready to post", "Awaiting decision", "Posted", "Changed since posted"

# Where a lot's pieces stand, for the counts.
_REJECTED = ("REJECTED", "RETURNED", "SCRAPPED")
_PENDING = ("RECEIVED", "AWAITING_INSPECTION", "QUARANTINE")
_SHORT = {"BACKORDERED": "More coming", "CLOSED": "That's all"}


def _family(lot, by_parent):
    """The lot and every lot split off it."""
    out, todo = [], [lot]
    while todo:
        cur = todo.pop()
        out.append(cur)
        todo.extend(by_parent.get(cur.id, ()))
    return out


def _snapshot(row) -> dict:
    """What posting records: the quantities a buyer keyed in."""
    return {k: str(row[k]) for k in ("Received Qty", "Accepted", "Rejected")}


def receipt_rows(tenant, start, end, *, with_po_only: bool = False,
                 unposted_only: bool = False) -> list[dict]:
    """One row per delivery received from `start` to `end` (inclusive), oldest first.
    `unposted_only` leaves out deliveries posted with the numbers they still have."""
    from Tracker.models import MaterialLot

    deliveries = list(
        MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, archived=False, parent_lot__isnull=True, holds_cores=False,
            received_date__gte=start, received_date__lte=end)
        .exclude(status__in=("ON_ORDER", "CANCELLED"))
        .select_related("material", "material_type", "supplier", "erp_posted_by")
        .order_by("received_date", "erp_po_number", "erp_po_line", "lot_number"))
    if with_po_only:
        deliveries = [d for d in deliveries if d.erp_po_number]

    # Every descendant of these deliveries, in one pass per level.
    by_parent: dict = {}
    frontier = [d.id for d in deliveries]
    while frontier:
        kids = list(MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, parent_lot_id__in=frontier).only(
            "id", "parent_lot_id", "status", "quantity"))
        for k in kids:
            by_parent.setdefault(k.parent_lot_id, []).append(k)
        frontier = [k.id for k in kids]

    rows = []
    for d in deliveries:
        # Each lot in the family owns what it was received or split with, less what was
        # split off it in turn (a split lowers what's left, not the quantity), and that
        # share counts as its status says. Used-up stock was accepted stock.
        accepted = rejected = pending = Decimal("0")
        for piece in _family(d, by_parent):
            share = piece.quantity - sum((k.quantity for k in by_parent.get(piece.id, ())),
                                         Decimal("0"))
            if piece.status in _REJECTED:
                rejected += share
            elif piece.status in _PENDING:
                pending += share
            else:
                accepted += share
        decision = ("Awaiting decision" if pending == d.quantity
                    else "Rejected" if rejected == d.quantity
                    else "Partly rejected" if rejected > 0
                    else "Part awaiting decision" if pending > 0
                    else "Accepted")
        item = d.material or d.material_type
        row = {
            "PO Number": d.erp_po_number, "PO Line": d.erp_po_line,
            "Received": d.received_date,
            "Item": (getattr(d.material, "part_number", "") if d.material_id
                     else getattr(d.material_type, "ERP_id", "") if d.material_type_id else "") or "",
            "Item Name": item.name if item is not None else d.material_description,
            "Supplier": d.supplier.name if d.supplier_id else "",
            "Our Lot": d.lot_number, "Supplier Lot": d.supplier_lot_number,
            "Unit": d.unit_of_measure,
            "Ordered": d.ordered_quantity if d.ordered_quantity is not None else d.quantity,
            "Received Qty": d.quantity, "Accepted": accepted, "Rejected": rejected,
            "Awaiting Decision": pending,
            "Short Delivery": _SHORT.get(d.short_receipt, ""),
            "Decision": decision,
            "lot_id": str(d.id),
        }
        if d.erp_posted_at is None:
            status = NOT_READY if pending > 0 else READY
        else:
            status = POSTED if d.erp_posted_snapshot == _snapshot(row) else CHANGED
        row["ERP Status"] = (f"{POSTED} {d.erp_posted_at:%Y-%m-%d}" if status == POSTED else status)
        row["erp_status"] = status
        if unposted_only and status == POSTED:
            continue
        rows.append(row)
    return rows


def mark_posted(tenant, lot_ids, *, user) -> int:
    """Record that these deliveries were keyed into the ERP, with the numbers posted.
    Deliveries still awaiting a decision are skipped (their numbers aren't final); a
    delivery changed since it was posted is re-marked with its new numbers. Returns how
    many were marked."""
    from django.utils import timezone
    from Tracker.models import MaterialLot

    lots = {str(l.id): l for l in MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, id__in=list(lot_ids), parent_lot__isnull=True)}
    if not lots:
        return 0
    dates = [l.received_date for l in lots.values() if l.received_date]
    if not dates:
        return 0
    now, marked = timezone.now(), 0
    for row in receipt_rows(tenant, min(dates), max(dates)):
        lot = lots.get(row["lot_id"])
        if lot is None or row["erp_status"] not in (READY, CHANGED):
            continue
        lot.erp_posted_at, lot.erp_posted_by = now, user
        lot.erp_posted_snapshot = _snapshot(row)
        lot.save(update_fields=["erp_posted_at", "erp_posted_by", "erp_posted_snapshot",
                                "updated_at"])
        marked += 1
    return marked


def receipts_workbook(tenant, start, end, *, with_po_only: bool = False,
                      unposted_only: bool = False) -> bytes:
    """The rows as an .xlsx: a sheet of receipts, and a note on what it is."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from Tracker.services.spreadsheet_safety import write_cell
    from Tracker.services.template_generator import HEADER_FILL, HEADER_FONT

    rows = receipt_rows(tenant, start, end, with_po_only=with_po_only,
                        unposted_only=unposted_only)
    wb = Workbook()
    ws = wb.active
    ws.title = "Receipts"
    for c, name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        ws.column_dimensions[cell.column_letter].width = max(len(name), 12) + 2
    for r, row in enumerate(rows, start=2):
        for c, name in enumerate(COLUMNS, start=1):
            value = row[name]
            write_cell(ws, r, c, float(value) if isinstance(value, Decimal) else value)
    ws.freeze_panes = "A2"

    about = wb.create_sheet("About")
    lines = [
        (f"Receipts {start:%d %b %Y} – {end:%d %b %Y}", Font(size=13, bold=True)),
        ("What the dock received, one row per delivery, for posting the goods receipts in "
         "the ERP. Received Qty = Accepted + Rejected + Awaiting Decision.", None),
        ("Awaiting Decision is still under inspection or held: post it once decided, or as "
         "your ERP posts quality-inspection stock.", None),
        ("Short Delivery is the clerk's reading of the packing slip. 'That's all' means "
         "UQMES expects nothing more on the line; closing the PO line is done in the ERP.", None),
        ("Rows with no PO Number were received without one (a walk-in).", None),
        ("ERP Status: 'Ready to post' — key it in, then mark it posted in UQMES. 'Awaiting "
         "decision' — not final yet. 'Changed since posted' — its numbers moved after it "
         "was posted (a later reject, a recount): correct it in the ERP.", None),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        cell = about.cell(row=i, column=1, value=text)
        if font:
            cell.font = font
    about.column_dimensions["A"].width = 110
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
