"""Where things are, and moving them — recorded.

A location is a record (`StorageLocation`). Lots (`MaterialLot.location`), serialised
units (`Parts.location`) and machines (`Equipments.location`) point at one, so renaming
a location renames it everywhere and "Rack 3", "rack3" and "R3" can't be three places.
Locations nest (warehouse → area → rack → bin); the tree view rolls counts up.

Every move of a lot or unit is written as a `RecordEdit` on `storage_location` (old →
new name, who, why), so "what left bin A3 this week?" has an answer. Receiving sets a
lot's first location; after that, the location changes only by a move.

Controls on a location: `held_only` (only held or rejected stock may go there — an MRB
cage) and `receiving_dock` (where receiving puts things by default). An inactive location
takes nothing new.

A location label's barcode carries `LOC:<code or name>` so a scanner can tell a bin from
a lot or a serial; `resolve_location` accepts any of: the record, its id, its code, its
name, or a scanned label.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

LOCATION_PREFIX = "LOC:"
# Physically here — a lot in any of these can be moved.
MOVABLE_LOT_STATUSES = ("RECEIVED", "AWAITING_INSPECTION", "ACCEPTED", "IN_USE", "QUARANTINE", "REJECTED")
# Gone, or not ours to place.
UNMOVABLE_PART_STATUSES = ("SHIPPED", "SCRAPPED", "CANCELLED", "DISMANTLED", "AT_OUTSIDE_PROCESS")
# What may go in a held-only location.
HELD_LOT_STATUSES = ("QUARANTINE", "REJECTED")
HELD_PART_STATUSES = ("QUARANTINED", "ON_HOLD", "REWORK_NEEDED")


def _strip_prefix(text: str) -> str:
    text = (text or "").strip()
    if text.upper().startswith(LOCATION_PREFIX):
        text = text[len(LOCATION_PREFIX):].strip()
    return text


def find_location(tenant, value):
    """The tenant's location ``value`` names, or None. ``value`` may be a
    StorageLocation, its id, its code, its name (any case), or ``LOC:<code|name>``."""
    from Tracker.models import StorageLocation
    if value is None:
        return None
    if isinstance(value, StorageLocation):
        return value if value.tenant_id == tenant.id else None
    text = _strip_prefix(str(value))
    if not text:
        return None
    qs = StorageLocation.objects.filter(tenant=tenant, archived=False)  # tenant-safe: explicit tenant filter
    try:
        found = qs.filter(pk=uuid.UUID(text)).first()
        if found:
            return found
    except ValueError:
        pass
    return qs.filter(code__iexact=text).exclude(code="").first() or qs.filter(name__iexact=text).first()


def resolve_location(tenant, value, *, create: bool = False, parent=None):
    """Like ``find_location`` but required: raises ValueError when nothing matches or the
    location is inactive. With ``create``, an unknown name becomes a new location (under
    ``parent`` if given) — "add new" from a picker, or an import."""
    from Tracker.models import StorageLocation
    loc = find_location(tenant, value)
    if loc is None:
        name = _strip_prefix(str(value or ""))
        if not name:
            raise ValueError("Say where it's going.")
        if not create:
            raise ValueError(f"“{name}” isn't one of your locations.")
        return StorageLocation.objects.create(tenant=tenant, name=name[:100], parent=parent)
    if not loc.is_active:
        raise ValueError(f"{loc.name} is no longer in use.")
    return loc


def seed_location(tenant, name: str, **defaults):
    """Get or create the tenant's location called ``name`` (any case) — for seeds and
    fixtures."""
    from Tracker.models import StorageLocation
    found = StorageLocation.objects.filter(tenant=tenant, name__iexact=name).first()  # tenant-safe: explicit tenant filter
    return found or StorageLocation.objects.create(tenant=tenant, name=name, **defaults)


def check_accepts(loc, *, lot=None, part=None) -> None:
    """Raise ValueError if ``loc`` won't take this lot or unit (held-only cages)."""
    if loc is None or not loc.held_only:
        return
    if lot is not None and lot.status not in HELD_LOT_STATUSES and not (lot.hold_reasons or lot.hold_reason):
        raise ValueError(f"{loc.name} is for held stock only — lot {lot.lot_number} isn't held.")
    if part is not None and part.part_status not in HELD_PART_STATUSES:
        raise ValueError(f"{loc.name} is for held stock only — {part.ERP_id} isn't held.")


def in_use(loc) -> str:
    """What still points at ``loc`` ('' when nothing does) — a location in use can't be
    removed, only made inactive."""
    from Tracker.models import CycleCount, Equipments, MaterialLot, Parts, StorageLocation
    checks = [
        ("stock in it", MaterialLot.objects.filter(location=loc, archived=False)),  # tenant-safe: FK to a scoped location
        ("units in it", Parts.objects.filter(location=loc, archived=False)),  # tenant-safe: FK to a scoped location
        ("machines in it", Equipments.objects.filter(location=loc, archived=False)),  # tenant-safe: FK to a scoped location
        ("cycle counts", CycleCount.objects.filter(location=loc)),  # tenant-safe: FK to a scoped location
        ("locations inside it", StorageLocation.objects.filter(parent=loc, archived=False)),  # tenant-safe: FK to a scoped location
    ]
    return next((label for label, qs in checks if qs.exists()), "")


def default_receiving_location(tenant):
    """Where receiving puts a delivery when nobody says: the first receiving dock."""
    from Tracker.models import StorageLocation
    return (StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, is_active=True, receiving_dock=True, held_only=False)
        .order_by("name").first())


def validate_parent(loc, parent) -> None:
    """A location can't sit inside itself or one of its own children."""
    node, hops = parent, 0
    while node is not None and hops < 50:
        if loc.pk is not None and node.pk == loc.pk:
            raise ValueError("A location can't be inside itself.")
        node, hops = node.parent, hops + 1


def _name(loc) -> str:
    return loc.name if loc is not None else ""


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


def move_lot(lot, *, to, user, quantity=None, reason: str = ""):
    """Move ``lot`` to ``to`` (anything ``resolve_location`` takes). With ``quantity``
    less than what's left, that much is split off into a child lot first and the child
    moves — the rest stays put. Returns the lot that moved."""
    from Tracker.models import MaterialLot
    from Tracker.services.mes.material_lot import split_material_lot

    dest = resolve_location(lot.tenant, to)
    with transaction.atomic():
        locked = MaterialLot.objects.select_for_update(of=("self",)).get(pk=lot.pk)  # tenant-safe: pk of a scoped lot
        if locked.status not in MOVABLE_LOT_STATUSES:
            raise ValueError(f"Lot {locked.lot_number} is {locked.get_status_display().lower()} — "
                             "it isn't on the shelf to move.")
        if locked.location_id == dest.id:
            raise ValueError(f"Lot {locked.lot_number} is already in {dest.name}.")
        check_accepts(dest, lot=locked)
        if quantity is not None:
            qty = Decimal(str(quantity))
            if qty <= 0:
                raise ValueError("Move a quantity greater than zero.")
            if qty > locked.quantity_remaining:
                raise ValueError(f"Only {locked.quantity_remaining} left on lot {locked.lot_number}.")
            if qty < locked.quantity_remaining:
                locked = split_material_lot(locked, qty, reason=f"Moved {qty} to {dest.name}")
        _record(locked, locked.storage_location, dest.name, user, reason)
        locked.location = dest
        locked.save(update_fields=["location", "updated_at"])
    return locked


def move_parts(tenant, parts, *, to, user, reason: str = "") -> int:
    """Move serialised units to ``to``. All or nothing; returns how many moved
    (units already there are skipped)."""
    from Tracker.models import Parts
    dest = resolve_location(tenant, to)
    ids = [p.id for p in parts]
    if not ids:
        raise ValueError("Choose what's moving.")
    moved = 0
    with transaction.atomic():
        for p in (Parts.objects.select_for_update(of=("self",))  # tenant-safe: explicit tenant filter
                  .filter(tenant=tenant, id__in=ids).select_related("location")):
            if p.part_status in UNMOVABLE_PART_STATUSES:
                raise ValueError(f"{p.ERP_id} is {p.get_part_status_display().lower()} — it isn't here to move.")
            if p.location_id == dest.id:
                continue
            check_accepts(dest, part=p)
            _record(p, p.storage_location, dest.name, user, reason)
            p.location = dest
            p.save(update_fields=["location"])
            moved += 1
    return moved


def _tree(tenant):
    """All the tenant's locations, and each one's children ids."""
    from Tracker.models import StorageLocation
    locs = {l.id: l for l in StorageLocation.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False)}
    children: dict = {}
    for l in locs.values():
        if l.parent_id in locs:
            children.setdefault(l.parent_id, []).append(l.id)
    return locs, children


def descendant_ids(tenant, loc) -> list:
    """``loc`` and everything inside it, at any depth."""
    _locs, children = _tree(tenant)
    out, stack, seen = [], [loc.id], set()
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        out.append(i)
        stack.extend(children.get(i, []))
    return out


def _path(locs: dict, loc) -> str:
    names, node, seen = [], loc, set()
    while node is not None and node.id not in seen and len(names) < 12:
        seen.add(node.id)
        names.append(node.name)
        node = locs.get(node.parent_id)
    return " / ".join(reversed(names))


def location_summary(tenant) -> list[dict]:
    """Every location, ordered as a tree (by path), with what is in it directly and in
    total (itself plus everything inside it)."""
    from django.db.models import Count
    from Tracker.models import Equipments, MaterialLot, Parts
    locs, children = _tree(tenant)
    lots = dict(MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, status__in=MOVABLE_LOT_STATUSES, location__isnull=False)
        .values("location").annotate(n=Count("id")).values_list("location", "n"))
    parts = dict(Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, location__isnull=False).exclude(part_status__in=UNMOVABLE_PART_STATUSES)
        .values("location").annotate(n=Count("id")).values_list("location", "n"))
    machines = dict(Equipments.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, location__isnull=False)
        .values("location").annotate(n=Count("id")).values_list("location", "n"))

    def total(i, counts, seen=None):
        seen = seen or set()
        if i in seen:
            return 0
        seen.add(i)
        return counts.get(i, 0) + sum(total(c, counts, seen) for c in children.get(i, []))

    rows = []
    for l in locs.values():
        path = _path(locs, l)
        rows.append({
            "id": l.id, "name": l.name, "path": path, "depth": path.count(" / "),
            "parent": l.parent_id if l.parent_id in locs else None,
            "kind": l.kind, "code": l.code, "description": l.description,
            "is_active": l.is_active, "held_only": l.held_only, "receiving_dock": l.receiving_dock,
            "lots": lots.get(l.id, 0), "parts": parts.get(l.id, 0), "equipment": machines.get(l.id, 0),
            "total_lots": total(l.id, lots), "total_parts": total(l.id, parts),
            "total_equipment": total(l.id, machines),
        })
    return sorted(rows, key=lambda r: r["path"].casefold())


def location_contents(tenant, value, days: int = 7, *, include_children: bool = True) -> dict:
    """What's in a location now (and, by default, in everything inside it), and what
    moved in or out of it in the last ``days``."""
    from django.db.models import Q
    from Tracker.models import Equipments, MaterialLot, Parts, RecordEdit
    loc = find_location(tenant, value)
    if loc is None:
        raise ValueError(f"“{_strip_prefix(str(value or ''))}” isn't one of your locations.")
    locs, _children = _tree(tenant)
    ids = descendant_ids(tenant, loc) if include_children else [loc.id]
    lots = (MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, status__in=MOVABLE_LOT_STATUSES, location_id__in=ids)
        .select_related("material", "material_type", "owner", "location").order_by("lot_number"))
    parts = (Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, location_id__in=ids)
        .exclude(part_status__in=UNMOVABLE_PART_STATUSES)
        .select_related("part_type", "work_order", "location").order_by("ERP_id"))
    machines = (Equipments.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, location_id__in=ids)
        .select_related("equipment_type", "location").order_by("name"))
    names = {locs[i].name.casefold() for i in ids if i in locs}
    since = timezone.now() - timedelta(days=days)
    q = Q()
    for n in names:
        q |= Q(old_value__iexact=n) | Q(new_value__iexact=n)
    edits = list(RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, field_name="storage_location", edited_at__gte=since).filter(q)
        .select_related("edited_by", "content_type").order_by("-edited_at")[:100]) if names else []
    labels = _labels_for(tenant, edits)

    def where(obj):
        return obj.location.name if obj.location_id != loc.id else None

    def into(e):
        return e.new_value.casefold() in names

    return {
        "id": loc.id, "name": loc.name, "path": _path(locs, loc), "kind": loc.kind, "code": loc.code,
        "description": loc.description, "is_active": loc.is_active, "held_only": loc.held_only,
        "receiving_dock": loc.receiving_dock,
        "parent": loc.parent_id if loc.parent_id in locs else None,
        "children": [{"id": c.id, "name": c.name} for c in sorted(
            (l for l in locs.values() if l.parent_id == loc.id), key=lambda l: l.name.casefold())],
        "lots": [{"id": str(l.id), "lot_number": l.lot_number, "item_name": l.item_name,
                  "quantity_remaining": float(l.quantity_remaining), "unit_of_measure": l.unit_of_measure,
                  "status": l.status, "owner_name": l.owner.name if l.owner_id else None,
                  "sublocation": where(l)} for l in lots],
        "parts": [{"id": str(p.id), "erp_id": p.ERP_id,
                   "part_type": p.part_type.name if p.part_type_id else None,
                   "work_order_id": str(p.work_order_id) if p.work_order_id else None,
                   "work_order": p.work_order.ERP_id if p.work_order_id else None,
                   "status": p.get_part_status_display(), "sublocation": where(p)} for p in parts],
        "equipment": [{"id": str(m.id), "name": m.name, "serial_number": m.serial_number or "",
                       "equipment_type": m.equipment_type.name if m.equipment_type_id else None,
                       "sublocation": where(m)} for m in machines],
        "moves": [{"at": e.edited_at, "direction": "IN" if into(e) else "OUT",
                   "kind": "LOT" if e.content_type.model == "materiallot" else "PART",
                   "object_id": str(e.object_id), "label": labels.get(e.object_id, "—"),
                   "other": e.old_value if into(e) else e.new_value,
                   "by": ((e.edited_by.get_full_name() or "").strip() or e.edited_by.email) if e.edited_by_id else None}
                  for e in edits if not (e.old_value.casefold() in names and into(e))],
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
