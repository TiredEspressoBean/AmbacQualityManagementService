"""Cycle counting — one location at a time, all year, instead of one big stocktake.

1. **Start** a count of a location: UQMES snapshots what it expects there — each lot and
   what's left of it, each serialised unit.
2. **Count**: the counter enters what's there (a quantity per lot, present or not per
   unit) and scans anything found that isn't on the list. A *blind* count hides the
   expected quantities while counting, so the counter counts rather than confirms.
3. **Submit**: the differences are worked out — short, over, missing, found here.
4. **Apply** (a lead, `apply_cyclecount`): UQMES's own records are corrected — each
   lot's quantity moved by the difference counted (a recorded adjustment), and anything
   found here that UQMES had elsewhere is moved here (a recorded move). A unit that
   wasn't found is reported, never changed: where it went is a question for a person.

Glovia is the stock register; the discrepancy report is what gets keyed into it.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone


def _num(v):
    return None if v is None or v == "" else float(Decimal(str(v)))


def start_count(tenant, location: str, user, *, blind: bool = False):
    from Tracker.models import CycleCount
    from Tracker.services.mes.locations import location_contents, resolve_location
    # One location exactly, not the ones inside it: a bin is counted as a bin, so what's
    # found here can be moved here without flattening the rack's bins into the rack.
    loc = resolve_location(tenant, location)
    name = loc.name
    if CycleCount.objects.filter(tenant=tenant, location=loc, status="OPEN").exists():  # tenant-safe: explicit tenant filter
        raise ValueError(f"{name} already has a count open — finish or submit it first.")
    contents = location_contents(tenant, loc, days=1, include_children=False)
    lines = [{"kind": "LOT", "id": l["id"], "label": l["lot_number"], "item": l["item_name"] or "",
              "unit": l["unit_of_measure"], "expected": l["quantity_remaining"], "counted": None,
              "found_here": False, "system_location": name, "note": ""} for l in contents["lots"]]
    lines += [{"kind": "PART", "id": p["id"], "label": p["erp_id"], "item": p["part_type"] or "",
               "unit": "EA", "expected": 1, "counted": None, "found_here": False,
               "system_location": name, "note": ""} for p in contents["parts"]]
    return CycleCount.objects.create(tenant=tenant, location=loc, blind=blind, lines=lines,
                                     started_by=user if getattr(user, "is_authenticated", False) else None)


def record_count(count, entries: list[dict]):
    """Merge what was counted. Each entry is ``{kind, id, counted, note}``; an entry for
    a lot or unit not on the list is something found here — added, with where UQMES
    thought it was."""
    from Tracker.models import MaterialLot, Parts
    if count.status != "OPEN":
        raise ValueError(f"{count.count_number} is {count.get_status_display().lower()} — it can't be changed.")
    lines = list(count.lines)
    index = {(l["kind"], l["id"]): l for l in lines}
    for e in entries:
        key = (e["kind"], str(e["id"]))
        line = index.get(key)
        if line is None:
            if e["kind"] == "LOT":
                lot = MaterialLot.objects.filter(tenant=count.tenant, pk=e["id"]).first()  # tenant-safe: explicit tenant filter
                if lot is None:
                    raise ValueError("A lot in this count wasn't found.")
                line = {"kind": "LOT", "id": str(lot.id), "label": lot.lot_number, "item": lot.item_name or "",
                        "unit": lot.unit_of_measure, "expected": 0, "found_here": True,
                        "system_location": lot.storage_location, "note": ""}
            else:
                part = (Parts.objects.filter(tenant=count.tenant, pk=e["id"])  # tenant-safe: explicit tenant filter
                        .select_related("part_type").first())
                if part is None:
                    raise ValueError("A unit in this count wasn't found.")
                line = {"kind": "PART", "id": str(part.id), "label": part.ERP_id,
                        "item": part.part_type.name if part.part_type_id else "", "unit": "EA",
                        "expected": 0, "found_here": True, "system_location": part.storage_location, "note": ""}
            lines.append(line)
            index[key] = line
        if "counted" in e:
            counted = _num(e["counted"])
            if counted is not None and counted < 0:
                raise ValueError(f"{line['label']}: a count can't be negative.")
            line["counted"] = counted
        if "note" in e:
            line["note"] = (e["note"] or "").strip()
    count.lines = lines
    count.save(update_fields=["lines", "updated_at"])
    return count


def submit_count(count, user):
    """Close counting. A line nobody counted is taken as not there (0) — the counter has
    walked the location, and what wasn't entered wasn't seen."""
    if count.status != "OPEN":
        raise ValueError(f"{count.count_number} is already {count.get_status_display().lower()}.")
    for line in count.lines:
        if line.get("counted") is None:
            line["counted"] = 0
    count.status = "SUBMITTED"
    count.submitted_by = user if getattr(user, "is_authenticated", False) else None
    count.submitted_at = timezone.now()
    count.save(update_fields=["lines", "status", "submitted_by", "submitted_at", "updated_at"])
    return count


def variances(count) -> list[dict]:
    """Every line that doesn't match, with what kind of difference it is."""
    out = []
    for line in count.lines:
        expected = float(line.get("expected") or 0)
        counted = line.get("counted")
        if counted is None:
            continue
        counted = float(counted)
        if line.get("found_here"):
            kind = "FOUND_HERE" if counted > 0 else None
        elif counted == expected:
            kind = None
        elif counted == 0:
            kind = "MISSING"
        else:
            kind = "SHORT" if counted < expected else "OVER"
        if kind:
            out.append({**line, "difference": counted - expected, "variance": kind})
    return out


def apply_count(count, user):
    """Correct UQMES from a submitted count. Lots: quantity moved by the difference
    counted — applied to what's left *now*, so anything drawn while the count was open
    isn't undone — and anything found here is moved here. Units: found here are moved
    here; missing ones are only reported."""
    from Tracker.models import MaterialLot, Parts
    from Tracker.services.mes.locations import move_lot, move_parts
    from Tracker.services.mes.material_lot import adjust_quantity
    if count.status != "SUBMITTED":
        raise ValueError(f"{count.count_number} has to be submitted before it's applied.")
    reason = f"Cycle count {count.count_number} at {count.location.name}"
    with transaction.atomic():
        for v in variances(count):
            if v["kind"] == "LOT":
                lot = MaterialLot.objects.filter(tenant=count.tenant, pk=v["id"]).first()  # tenant-safe: explicit tenant filter
                if lot is None:
                    continue
                if v["variance"] == "FOUND_HERE":
                    if lot.location_id != count.location_id:
                        lot = move_lot(lot, to=count.location, user=user, reason=reason)
                    new = Decimal(str(v["counted"]))
                else:
                    new = max(Decimal("0"), lot.quantity_remaining + Decimal(str(v["difference"])))
                if new != lot.quantity_remaining:
                    adjust_quantity(lot, new_quantity=new, reason=reason, user=user)
            elif v["variance"] == "FOUND_HERE":
                part = Parts.objects.filter(tenant=count.tenant, pk=v["id"]).first()  # tenant-safe: explicit tenant filter
                if part is not None:
                    move_parts(count.tenant, [part], to=count.location, user=user, reason=reason)
        count.status = "APPLIED"
        count.applied_by = user if getattr(user, "is_authenticated", False) else None
        count.applied_at = timezone.now()
        count.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    return count


COLUMNS = ["Location", "Lot / serial", "Item", "Unit", "Expected", "Counted", "Difference",
           "What", "UQMES had it at", "Note"]
_WHAT = {"SHORT": "Short", "OVER": "Over", "MISSING": "Not found", "FOUND_HERE": "Found here"}


def discrepancy_workbook(count) -> bytes:
    """The count's differences as an .xlsx, for keying into the stock register (Glovia)."""
    from io import BytesIO
    from openpyxl import Workbook
    from Tracker.services.spreadsheet_safety import write_cell
    from Tracker.services.template_generator import HEADER_FILL, HEADER_FONT
    wb = Workbook()
    ws = wb.active
    ws.title = "Differences"
    for c, name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        ws.column_dimensions[cell.column_letter].width = max(len(name), 12) + 2
    for r, v in enumerate(variances(count), start=2):
        row = [count.location.name, v["label"], v.get("item", ""), v.get("unit", ""), v.get("expected"),
               v.get("counted"), v.get("difference"), _WHAT[v["variance"]],
               v.get("system_location") if v["variance"] == "FOUND_HERE" else "", v.get("note", "")]
        for c, value in enumerate(row, start=1):
            write_cell(ws, r, c, value)
    ws.freeze_panes = "A2"
    out = BytesIO()
    wb.save(out)
    return out.getvalue()
