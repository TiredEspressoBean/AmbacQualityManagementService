"""Cycle counting — a little at a time, all year, instead of one big stocktake.

A count's scope is one LOCATION (everything kept there) or one ITEM — a material or a
part type, wherever it's kept (user decision 2026-11-04). Scheduling is by item, the
walk by location (services/mes/count_cadence).

1. **Start**: UQMES snapshots what it expects — each lot and what's left of it, each
   serialised unit, and where each is kept.
2. **Count**: the counter enters what's there (a quantity per lot, present or not per
   unit) and scans anything found that isn't on the list — at this location, or, in an
   item count, at the location they name. A *blind* count hides the expected
   quantities while counting, so the counter counts rather than confirms.
3. **Submit**: the differences are worked out — short, over, missing, found.
4. **Apply** (a lead, `apply_cyclecount`): each difference gets a reason code (why the
   record was off); lines outside their class's tolerance also need a note. UQMES's own
   records are corrected — each lot's quantity moved by the difference counted (a
   recorded adjustment), and anything found moved to where it was found (a recorded
   move). A unit that wasn't found is reported, never changed: where it went is a
   question for a person, so it waits on the *missing units* list until it turns up or
   someone says what became of it.
5. **Key into Glovia**: Glovia is the stock register, bridged by hand. An applied
   count's differences wait on the *to key* list (one export across counts) until a
   person marks them keyed.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

# Why the record was off — the lead picks one per difference when applying, so accuracy
# can be read by cause, not just by how often.
REASONS = [
    ("NOT_BOOKED", "Used or moved without being booked"),
    ("SCRAPPED", "Damaged or scrapped, not booked"),
    ("MISPLACED", "Kept in the wrong place"),
    ("RECEIVED_WRONG", "Received wrong"),
    ("COUNT_ERROR", "An earlier count was wrong"),
    ("UNKNOWN", "Not known"),
]
REASON_CODES = {c for c, _ in REASONS}
# Units that have left for good aren't stock to count — or to chase.
GONE = ("SCRAPPED", "CANCELLED", "SHIPPED", "DISMANTLED", "RMA_CLOSED")


def _num(v):
    return None if v is None or v == "" else float(Decimal(str(v)))


def _who(user):
    return user if getattr(user, "is_authenticated", False) else None


def _lot_line(lot, *, found=False):
    loc = lot.location
    return {"kind": "LOT", "id": str(lot.id), "label": lot.lot_number, "item": lot.item_name or "",
            "unit": lot.unit_of_measure, "expected": 0 if found else float(lot.quantity_remaining),
            "counted": None, "found_here": found,
            "system_location": loc.name if loc else (lot.storage_location or ""),
            "location_id": str(loc.id) if loc else None, "found_at": None, "note": ""}


def _part_line(part, *, found=False):
    loc = part.location
    return {"kind": "PART", "id": str(part.id), "label": part.ERP_id,
            "item": part.part_type.name if part.part_type_id else "", "unit": "EA",
            "expected": 0 if found else 1, "counted": None, "found_here": found,
            "system_location": loc.name if loc else (part.storage_location or ""),
            "location_id": str(loc.id) if loc else None, "found_at": None, "note": ""}


def start_count(tenant, user, *, location=None, material=None, part_type=None, blind=False):
    """Start a count of a location (a name or id), or of a material or part type (an id)
    wherever it's kept. One open count per scope."""
    from Tracker.models import CycleCount, Material, MaterialLot, Parts, PartTypes
    from Tracker.services.mes.locations import resolve_location

    if sum(x is not None and x != "" for x in (location, material, part_type)) != 1:
        raise ValueError("Count one location, or one material or part type.")
    started_by = _who(user)
    if location:
        # One location exactly, not the ones inside it: a bin is counted as a bin, so what's
        # found here can be moved here without flattening the rack's bins into the rack.
        loc = resolve_location(tenant, location)
        if CycleCount.objects.filter(tenant=tenant, location=loc, status="OPEN").exists():  # tenant-safe: explicit tenant filter
            raise ValueError(f"{loc.name} already has a count open — finish or submit it first.")
        lots = (MaterialLot.objects.filter(tenant=tenant, archived=False, location=loc,  # tenant-safe: explicit tenant filter
                                           quantity_remaining__gt=0)
                .select_related("location").order_by("lot_number"))
        parts = (Parts.objects.filter(tenant=tenant, archived=False, location=loc)  # tenant-safe: explicit tenant filter
                 .exclude(part_status__in=GONE).select_related("part_type", "location").order_by("ERP_id"))
        scope = {"location": loc}
    elif material:
        mat = Material.objects.filter(tenant=tenant, pk=material).first()  # tenant-safe: explicit tenant filter
        if mat is None:
            raise ValueError("That material wasn't found.")
        if CycleCount.objects.filter(tenant=tenant, material=mat, status="OPEN").exists():  # tenant-safe: explicit tenant filter
            raise ValueError(f"{mat.name} already has a count open — finish or submit it first.")
        lots = (MaterialLot.objects.filter(tenant=tenant, archived=False, material=mat,  # tenant-safe: explicit tenant filter
                                           quantity_remaining__gt=0, location__isnull=False)
                .select_related("location").order_by("location__name", "lot_number"))
        parts = Parts.objects.none()
        scope = {"material": mat}
    else:
        pt = PartTypes.objects.filter(tenant=tenant, pk=part_type).first()  # tenant-safe: explicit tenant filter
        if pt is None:
            raise ValueError("That part type wasn't found.")
        if CycleCount.objects.filter(tenant=tenant, part_type=pt, status="OPEN").exists():  # tenant-safe: explicit tenant filter
            raise ValueError(f"{pt.name} already has a count open — finish or submit it first.")
        # Stock in a location: units on the floor in a work cell aren't stock to count.
        lots = (MaterialLot.objects.filter(tenant=tenant, archived=False, material_type=pt,  # tenant-safe: explicit tenant filter
                                           quantity_remaining__gt=0, location__isnull=False)
                .select_related("location").order_by("location__name", "lot_number"))
        parts = (Parts.objects.filter(tenant=tenant, archived=False, part_type=pt, location__isnull=False)  # tenant-safe: explicit tenant filter
                 .exclude(part_status__in=GONE).select_related("part_type", "location")
                 .order_by("location__name", "ERP_id"))
        scope = {"part_type": pt}
    lines = [_lot_line(l) for l in lots] + [_part_line(p) for p in parts]
    return CycleCount.objects.create(tenant=tenant, blind=blind, lines=lines, started_by=started_by,
                                     **scope)


def _belongs(count, obj, kind) -> bool:
    """Is a found lot or unit the counted item (an item count only takes its own)?"""
    if count.location_id:
        return True
    if kind == "LOT":
        return (obj.material_id == count.material_id if count.material_id
                else obj.material_type_id == count.part_type_id)
    return bool(count.part_type_id) and obj.part_type_id == count.part_type_id


def record_count(count, entries: list[dict]):
    """Merge what was counted. Each entry is ``{kind, id, counted, note, found_at}``; an
    entry for a lot or unit not on the list is something found — at this location, or,
    in an item count, at `found_at` (a location name or id), which is then required."""
    from Tracker.models import MaterialLot, Parts
    from Tracker.services.mes.locations import resolve_location
    if count.status != "OPEN":
        raise ValueError(f"{count.count_number} is {count.get_status_display().lower()} — it can't be changed.")
    lines = list(count.lines)
    index = {(l["kind"], l["id"]): l for l in lines}
    for e in entries:
        key = (e["kind"], str(e["id"]))
        line = index.get(key)
        if line is None:
            if e["kind"] == "LOT":
                obj = (MaterialLot.objects.filter(tenant=count.tenant, pk=e["id"])  # tenant-safe: explicit tenant filter
                       .select_related("location").first())
                if obj is None:
                    raise ValueError("A lot in this count wasn't found.")
                line = _lot_line(obj, found=True)
            else:
                obj = (Parts.objects.filter(tenant=count.tenant, pk=e["id"])  # tenant-safe: explicit tenant filter
                       .select_related("part_type", "location").first())
                if obj is None:
                    raise ValueError("A unit in this count wasn't found.")
                line = _part_line(obj, found=True)
            if not _belongs(count, obj, e["kind"]):
                raise ValueError(f"{line['label']} isn't {count.scope_name} — count it in its own count.")
            if count.location_id:
                line["found_at"] = str(count.location_id)
            else:
                where = e.get("found_at")
                if not where:
                    raise ValueError(f"{line['label']}: say where it was found.")
                line["found_at"] = str(resolve_location(count.tenant, where).id)
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
    """Close counting. A line nobody counted stays uncounted: it is left out of the
    differences and never applied, so a skipped shelf isn't written off as missing (user
    decision 2026-10-26). A counter who finds a spot empty enters 0."""
    if count.status != "OPEN":
        raise ValueError(f"{count.count_number} is already {count.get_status_display().lower()}.")
    count.status = "SUBMITTED"
    count.submitted_by = _who(user)
    count.submitted_at = timezone.now()
    count.save(update_fields=["status", "submitted_by", "submitted_at", "updated_at"])
    return count


def not_counted(count) -> int:
    """Lines left blank — expected here, but nobody said whether they are."""
    return sum(1 for line in count.lines if line.get("counted") is None)


def send_back(count, user, reason: str):
    """A lead sends a submitted count back for a recount, before it's applied (user
    decision 2026-10-26, Corrections #29). It reopens with what was entered, for the
    counter to correct; the reason is kept on the count's record. An applied count is
    final."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import CycleCount, RecordEdit
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Say why it's going back for a recount.")
    if count.status != "SUBMITTED":
        raise ValueError(f"{count.count_number} is {count.get_status_display().lower()} — only a "
                         f"submitted count, not yet applied, can go back for a recount.")
    with transaction.atomic():
        RecordEdit.objects.create(
            tenant=count.tenant, content_type=ContentType.objects.get_for_model(CycleCount),
            object_id=count.id, field_name="status", old_value="SUBMITTED", new_value="OPEN",
            reason=reason, edited_by=user)
        count.status = "OPEN"
        count.submitted_by = None
        count.submitted_at = None
        count.save(update_fields=["status", "submitted_by", "submitted_at", "updated_at"])
    return count


def variances(count) -> list[dict]:
    """Every line that doesn't match, with what kind of difference it is — and, by its
    item's ABC class, whether that's still within tolerance (services/mes/count_cadence)."""
    from Tracker.services.mes.count_cadence import count_policy, judge, line_classes
    policy = count_policy(count.tenant)
    classes = line_classes(count.tenant, count.lines)
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
            cls = classes.get((line.get("kind"), str(line.get("id"))), "C")
            within, tol = judge(line, cls, policy)
            out.append({**line, "difference": counted - expected, "variance": kind,
                        "abc_class": cls, "tolerance": tol, "within_tolerance": within,
                        "reason": line.get("reason") or ""})
    return out


def outside_tolerance(count) -> list[dict]:
    """The differences beyond their class's tolerance — the ones a recount is for."""
    return [v for v in variances(count) if not v["within_tolerance"]]


def _line_key(v) -> str:
    return f"{v['kind']}:{v['id']}"


def apply_count(count, user, note: str = "", reasons: dict | None = None):
    """Correct UQMES from a submitted count. Lots: quantity moved by the difference
    counted — applied to what's left *now*, so anything drawn while the count was open
    isn't undone — and anything found moved to where it was found. Units: found ones are
    moved there; missing ones are only reported (and wait on the missing-units list).

    Every difference needs a reason code (`reasons`: {"LOT:<id>"/"PART:<id>": code}).
    Lines outside their class's tolerance are usually sent back for a recount; a lead
    applying them anyway also says why (`note`, kept on the count) — warned, not blocked
    (user decision 2026-11-04)."""
    from Tracker.models import MaterialLot, Parts, StorageLocation
    from Tracker.services.mes.locations import move_lot, move_parts
    from Tracker.services.mes.material_lot import adjust_quantity
    if count.status != "SUBMITTED":
        raise ValueError(f"{count.count_number} has to be submitted before it's applied.")
    note = (note or "").strip()
    reasons = reasons or {}
    diffs = variances(count)
    unreasoned = [v["label"] for v in diffs if reasons.get(_line_key(v)) not in REASON_CODES]
    if unreasoned:
        raise ValueError(f"Give each difference a reason ({', '.join(unreasoned[:5])}"
                         f"{' and more' if len(unreasoned) > 5 else ''}).")
    misses = [v for v in diffs if not v["within_tolerance"]]
    if misses and not note:
        raise ValueError(
            f"{len(misses)} line{'s are' if len(misses) != 1 else ' is'} outside tolerance — "
            "send the count back for a recount, or say why the difference is real.")
    why = f"Cycle count {count.count_number} of {count.scope_name}"
    places = {str(l.id): l for l in StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=count.tenant, pk__in={v.get("found_at") for v in diffs if v.get("found_at")})}
    with transaction.atomic():
        for v in diffs:
            to = places.get(v.get("found_at") or "") if v["variance"] == "FOUND_HERE" else None
            if v["kind"] == "LOT":
                lot = MaterialLot.objects.filter(tenant=count.tenant, pk=v["id"]).first()  # tenant-safe: explicit tenant filter
                if lot is None:
                    continue
                if v["variance"] == "FOUND_HERE":
                    if to is not None and lot.location_id != to.id:
                        lot = move_lot(lot, to=to, user=user, reason=why)
                    new = Decimal(str(v["counted"]))
                else:
                    new = max(Decimal("0"), lot.quantity_remaining + Decimal(str(v["difference"])))
                if new != lot.quantity_remaining:
                    adjust_quantity(lot, new_quantity=new, reason=why, user=user)
            elif v["variance"] == "FOUND_HERE" and to is not None:
                part = Parts.objects.filter(tenant=count.tenant, pk=v["id"]).first()  # tenant-safe: explicit tenant filter
                if part is not None:
                    move_parts(count.tenant, [part], to=to, user=user, reason=why)
        lines = list(count.lines)
        for line in lines:
            code = reasons.get(f"{line['kind']}:{line['id']}")
            if code in REASON_CODES:
                line["reason"] = code
        count.lines = lines
        count.status = "APPLIED"
        count.applied_by = _who(user)
        count.applied_at = timezone.now()
        count.apply_note = note
        count.save(update_fields=["lines", "status", "applied_by", "applied_at", "apply_note",
                                  "updated_at"])
    return count


# --- missing units: found again, or someone says what became of them -------------------

def missing_units(tenant) -> list[dict]:
    """Units a count didn't find, still unresolved — newest first. One stops being
    missing when it turns up (moved or placed since, or found in a later count), when it
    has left for good (scrapped, shipped…), or when someone resolves it with a note."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import CycleCount, Parts, RecordEdit

    rows = []
    for c in (CycleCount.objects.filter(tenant=tenant, status="APPLIED")  # tenant-safe: explicit tenant filter
              .select_related("location", "material", "part_type").order_by("-applied_at")):
        for line in c.lines or []:
            if (line.get("kind") == "PART" and not line.get("found_here")
                    and line.get("counted") is not None and float(line["counted"]) == 0
                    and float(line.get("expected") or 0) > 0 and not line.get("chase")):
                rows.append((c, line))
    if not rows:
        return []
    ids = {l["id"] for _, l in rows}
    parts = {str(p.id): p for p in Parts.objects.filter(tenant=tenant, pk__in=ids)  # tenant-safe: explicit tenant filter
             .select_related("location")}
    part_ct = ContentType.objects.get_for_model(Parts)
    moved = {}
    for oid, at in (RecordEdit.objects.filter(tenant=tenant, content_type=part_ct,  # tenant-safe: explicit tenant filter
                                              object_id__in=ids, field_name="storage_location")
                    .values_list("object_id", "edited_at")):
        moved[str(oid)] = max(moved.get(str(oid), at), at)
    seen_later = {}
    for c in CycleCount.objects.filter(tenant=tenant, status="APPLIED"):  # tenant-safe: explicit tenant filter
        for line in c.lines or []:
            if line.get("kind") == "PART" and line.get("id") in ids and (line.get("counted") or 0) > 0:
                seen_later[line["id"]] = max(seen_later.get(line["id"], c.applied_at), c.applied_at)
    out = []
    for c, line in rows:
        p = parts.get(line["id"])
        if p is None or p.part_status in GONE:
            continue
        if moved.get(line["id"]) and moved[line["id"]] > c.applied_at:
            continue
        if seen_later.get(line["id"]) and seen_later[line["id"]] > c.applied_at:
            continue
        out.append({"count_id": c.id, "count_number": c.count_number, "scope": c.scope_name,
                    "applied_at": c.applied_at, "part_id": p.id, "serial": p.ERP_id,
                    "item": line.get("item") or "", "expected_at": line.get("system_location") or "",
                    "reason": line.get("reason") or "", "status": p.get_part_status_display()})
    return out


def resolve_missing(count, part_id, user, note: str):
    """Someone says what became of a unit a count didn't find — taking it off the
    missing list. The note stays on the count's line."""
    note = (note or "").strip()
    if not note:
        raise ValueError("Say what became of it.")
    lines = list(count.lines)
    line = next((l for l in lines if l.get("kind") == "PART" and l.get("id") == str(part_id)), None)
    if line is None:
        raise ValueError("That unit isn't on this count.")
    line["chase"] = {"by": getattr(user, "id", None),
                     "by_name": (user.get_full_name() or user.get_username()) if user else "",
                     "at": timezone.now().isoformat(), "note": note}
    count.lines = lines
    count.save(update_fields=["lines", "updated_at"])
    return count


# --- keying into Glovia ---------------------------------------------------------------

def to_key(tenant):
    """Applied counts whose differences haven't been marked keyed into the ERP yet."""
    from Tracker.models import CycleCount
    counts = (CycleCount.objects.filter(tenant=tenant, status="APPLIED", erp_keyed_at__isnull=True)  # tenant-safe: explicit tenant filter
              .select_related("location", "material", "part_type", "applied_by").order_by("applied_at"))
    return [c for c in counts if variances(c)]


def mark_keyed(counts, user) -> int:
    """Mark counts' differences as keyed into the ERP."""
    now = timezone.now()
    done = 0
    for c in counts:
        if c.status == "APPLIED" and c.erp_keyed_at is None:
            c.erp_keyed_at = now
            c.erp_keyed_by = _who(user)
            c.save(update_fields=["erp_keyed_at", "erp_keyed_by", "updated_at"])
            done += 1
    return done


COLUMNS = ["Count", "Location", "Lot / serial", "Item", "Unit", "Expected", "Counted", "Difference",
           "What", "Reason", "UQMES had it at", "Note"]
_WHAT = {"SHORT": "Short", "OVER": "Over", "MISSING": "Not found", "FOUND_HERE": "Found"}
_REASON = dict(REASONS)


def discrepancy_workbook(counts) -> bytes:
    """Counts' differences as one .xlsx, for keying into the stock register (Glovia).
    `counts` is one count or several."""
    from io import BytesIO
    from openpyxl import Workbook
    from Tracker.models import StorageLocation
    from Tracker.services.spreadsheet_safety import write_cell
    from Tracker.services.template_generator import HEADER_FILL, HEADER_FONT
    counts = counts if isinstance(counts, (list, tuple)) else [counts]
    wb = Workbook()
    ws = wb.active
    ws.title = "Differences"
    for c, name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=c, value=name)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        ws.column_dimensions[cell.column_letter].width = max(len(name), 12) + 2
    r = 2
    for count in counts:
        diffs = variances(count)
        names = {str(l.id): l.name for l in StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=count.tenant, pk__in={v.get("found_at") for v in diffs if v.get("found_at")})}
        for v in diffs:
            where = (names.get(v.get("found_at") or "") if v["variance"] == "FOUND_HERE"
                     else v.get("system_location")) or ""
            row = [count.count_number, where, v["label"], v.get("item", ""), v.get("unit", ""),
                   v.get("expected"), v.get("counted"), v.get("difference"), _WHAT[v["variance"]],
                   _REASON.get(v.get("reason") or "", ""),
                   v.get("system_location") if v["variance"] == "FOUND_HERE" else "", v.get("note", "")]
            for c, value in enumerate(row, start=1):
                write_cell(ws, r, c, value)
            r += 1
    ws.freeze_panes = "A2"
    out = BytesIO()
    wb.save(out)
    return out.getvalue()
