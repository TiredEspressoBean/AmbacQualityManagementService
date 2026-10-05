"""Where stock is, and moving it — recorded.

A location is a name. Lots (`MaterialLot.storage_location`) and serialised units
(`Parts.storage_location`) carry one as text, so a shop that never sets up a list still
works. A shop that keeps a managed list (`StorageLocation`) gets it enforced: a move's
destination must be one of its active locations, so "Rack 3", "rack3" and "R3" stop
being three places.

Every move is written as a `RecordEdit` on `storage_location` (old → new, who, why), so
"what left bin A3 this week?" has an answer. Receiving sets a lot's first location; after
that, the location changes only by a move.

A location label's barcode carries `LOC:<name>` so a scanner can tell a bin from a lot
or a serial; `canonical_location` accepts either form.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

LOCATION_PREFIX = "LOC:"
# Physically here — a lot in any of these can be moved.
MOVABLE_LOT_STATUSES = ("RECEIVED", "AWAITING_INSPECTION", "ACCEPTED", "IN_USE", "QUARANTINE", "REJECTED")
# Gone, or not ours to place.
UNMOVABLE_PART_STATUSES = ("SHIPPED", "SCRAPPED", "CANCELLED", "DISMANTLED", "AT_OUTSIDE_PROCESS")


def _managed(tenant) -> list[str]:
    from Tracker.models import StorageLocation
    return list(StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, is_active=True, archived=False).values_list("name", flat=True))


def canonical_location(tenant, text: str) -> str:
    """The location ``text`` names, spelled as the tenant spells it. Accepts a scanned
    label (``LOC:Rack 3``). With a managed list, the name must be on it."""
    name = (text or "").strip()
    if name.upper().startswith(LOCATION_PREFIX):
        name = name[len(LOCATION_PREFIX):].strip()
    if not name:
        raise ValueError("Say where it's going.")
    managed = _managed(tenant)
    if not managed:
        return name
    match = next((m for m in managed if m.casefold() == name.casefold()), None)
    if match is None:
        raise ValueError(f"“{name}” isn't one of your storage locations.")
    return match


def record_move(obj, old: str, new: str, user, reason: str) -> None:
    """Write the record of a location change made outside move_lot / move_parts."""
    _record(obj, old, new, user, reason)


def _record(obj, old: str, new: str, user, reason: str) -> None:
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    RecordEdit.objects.create(
        tenant=obj.tenant, content_type=ContentType.objects.get_for_model(type(obj)),
        object_id=obj.id, field_name="storage_location", old_value=old or "",
        new_value=new, reason=reason or "Moved", edited_by=user)


def move_lot(lot, *, to: str, user, quantity=None, reason: str = ""):
    """Move ``lot`` to ``to``. With ``quantity`` less than what's left, that much is
    split off into a child lot first and the child moves — the rest stays put.
    Returns the lot that moved."""
    from Tracker.models import MaterialLot
    from Tracker.services.mes.material_lot import split_material_lot

    dest = canonical_location(lot.tenant, to)
    with transaction.atomic():
        locked = MaterialLot.objects.select_for_update().get(pk=lot.pk)  # tenant-safe: pk of a scoped lot
        if locked.status not in MOVABLE_LOT_STATUSES:
            raise ValueError(f"Lot {locked.lot_number} is {locked.get_status_display().lower()} — "
                             "it isn't on the shelf to move.")
        if quantity is not None:
            qty = Decimal(str(quantity))
            if qty <= 0:
                raise ValueError("Move a quantity greater than zero.")
            if qty > locked.quantity_remaining:
                raise ValueError(f"Only {locked.quantity_remaining} left on lot {locked.lot_number}.")
            if qty < locked.quantity_remaining:
                locked = split_material_lot(locked, qty, reason=f"Moved {qty} to {dest}")
        if locked.storage_location == dest:
            raise ValueError(f"Lot {locked.lot_number} is already in {dest}.")
        _record(locked, locked.storage_location, dest, user, reason)
        locked.storage_location = dest
        locked.save(update_fields=["storage_location", "updated_at"])
    return locked


def move_parts(tenant, parts, *, to: str, user, reason: str = "") -> int:
    """Move serialised units to ``to``. All or nothing; returns how many moved
    (units already there are skipped)."""
    from Tracker.models import Parts
    dest = canonical_location(tenant, to)
    ids = [p.id for p in parts]
    if not ids:
        raise ValueError("Choose what's moving.")
    moved = 0
    with transaction.atomic():
        for p in (Parts.objects.select_for_update()  # tenant-safe: explicit tenant filter
                  .filter(tenant=tenant, id__in=ids)):
            if p.part_status in UNMOVABLE_PART_STATUSES:
                raise ValueError(f"{p.ERP_id} is {p.get_part_status_display().lower()} — it isn't here to move.")
            if p.storage_location == dest:
                continue
            _record(p, p.storage_location, dest, user, reason)
            p.storage_location = dest
            p.save(update_fields=["storage_location"])
            moved += 1
    return moved


def rename_location(tenant, old: str, new: str) -> int:
    """A managed location renamed: what's in it is still in it. Re-labels the lots and
    units filed under the old name (a rename isn't a move, so no move records); returns
    how many rows changed."""
    from Tracker.models import MaterialLot, Parts
    old, new = (old or "").strip(), (new or "").strip()
    if not old or not new or old == new:
        return 0
    n = MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, storage_location__iexact=old).update(storage_location=new)
    n += Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, storage_location__iexact=old).update(storage_location=new)
    return n


def location_summary(tenant) -> list[dict]:
    """Every location with something in it, plus every managed one (empty or not)."""
    from django.db.models import Count
    from Tracker.models import MaterialLot, Parts, StorageLocation
    lots = dict(MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, status__in=MOVABLE_LOT_STATUSES)
        .exclude(storage_location="").values("storage_location")
        .annotate(n=Count("id")).values_list("storage_location", "n"))
    parts = dict(Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False).exclude(part_status__in=UNMOVABLE_PART_STATUSES)
        .exclude(storage_location="").values("storage_location")
        .annotate(n=Count("id")).values_list("storage_location", "n"))
    managed = {s.name.casefold(): s for s in StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, is_active=True, archived=False)}
    rows: dict = {}
    for key, s in managed.items():
        rows[key] = {"name": s.name, "description": s.description, "managed": True, "lots": 0, "parts": 0}
    for source, field in ((lots, "lots"), (parts, "parts")):
        for name, n in source.items():
            row = rows.setdefault(name.casefold(), {"name": name, "description": "", "managed": False,
                                                    "lots": 0, "parts": 0})
            row[field] += n
    return sorted(rows.values(), key=lambda r: r["name"].casefold())


def location_contents(tenant, name: str, days: int = 7) -> dict:
    """What's in ``name`` now, and what moved in or out of it in the last ``days``."""
    from django.db.models import Q
    from Tracker.models import MaterialLot, Parts, RecordEdit
    name = (name or "").strip()
    if name.upper().startswith(LOCATION_PREFIX):
        name = name[len(LOCATION_PREFIX):].strip()
    lots = (MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, status__in=MOVABLE_LOT_STATUSES, storage_location__iexact=name)
        .select_related("material", "material_type", "owner").order_by("lot_number"))
    parts = (Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, storage_location__iexact=name)
        .exclude(part_status__in=UNMOVABLE_PART_STATUSES)
        .select_related("part_type", "work_order").order_by("ERP_id"))
    since = timezone.now() - timedelta(days=days)
    edits = list(RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, field_name="storage_location", edited_at__gte=since)
        .filter(Q(old_value__iexact=name) | Q(new_value__iexact=name))
        .select_related("edited_by", "content_type").order_by("-edited_at")[:100])
    labels = _labels_for(tenant, edits)
    return {
        "name": name,
        "lots": [{"id": str(l.id), "lot_number": l.lot_number, "item_name": l.item_name,
                  "quantity_remaining": float(l.quantity_remaining), "unit_of_measure": l.unit_of_measure,
                  "status": l.status, "owner_name": l.owner.name if l.owner_id else None} for l in lots],
        "parts": [{"id": str(p.id), "erp_id": p.ERP_id,
                   "part_type": p.part_type.name if p.part_type_id else None,
                   "work_order_id": str(p.work_order_id) if p.work_order_id else None,
                   "work_order": p.work_order.ERP_id if p.work_order_id else None,
                   "status": p.get_part_status_display()} for p in parts],
        "moves": [{"at": e.edited_at, "direction": "IN" if e.new_value.casefold() == name.casefold() else "OUT",
                   "kind": "LOT" if e.content_type.model == "materiallot" else "PART",
                   "object_id": str(e.object_id), "label": labels.get(e.object_id, "—"),
                   "other": e.old_value if e.new_value.casefold() == name.casefold() else e.new_value,
                   "by": ((e.edited_by.get_full_name() or "").strip() or e.edited_by.email) if e.edited_by_id else None}
                  for e in edits],
    }


def _labels_for(tenant, edits) -> dict:
    from Tracker.models import MaterialLot, Parts
    lot_ids = [e.object_id for e in edits if e.content_type.model == "materiallot"]
    part_ids = [e.object_id for e in edits if e.content_type.model == "parts"]
    out = dict(MaterialLot.objects.filter(tenant=tenant, id__in=lot_ids)  # tenant-safe: explicit tenant filter
               .values_list("id", "lot_number"))
    out.update(Parts.objects.filter(tenant=tenant, id__in=part_ids)  # tenant-safe: explicit tenant filter
               .values_list("id", "ERP_id"))
    return out
