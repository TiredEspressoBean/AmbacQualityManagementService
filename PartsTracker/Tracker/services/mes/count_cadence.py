"""ABC cycle-count cadence — what's due for counting, and how accurate the counts are.

Standard practice (user decision 2026-11-04): schedule by item, walk by location.

  - **Class.** Every Material and part type carries an A/B/C class (`abc_class`, C by
    default). How often each class is counted is a tenant setting, as is how far a
    count may differ from the record and still count as accurate.
  - **Due.** Counts stay per location, and a location count covers everything in it.
    So an item's stock at a location was last counted when that location last had a
    count applied; it's due again once that's older than the item's class interval
    (never counted: due now). An item is due when any location holding it is; the list
    names those locations, so counting them clears it.
  - **Tolerance.** A counted lot line is a *hit* when its difference is within its
    class's tolerance — a percentage of the record, or a minimum number of units,
    whichever is larger — and a *miss* otherwise. A unit (serialised part) is a hit
    only when found where expected; one missing, or found here from elsewhere, is a
    miss, as is a lot found here from elsewhere. A lead applying a count with misses
    must say why (warned, not blocked: recounting is the usual answer, but the lead may
    already know the difference is real).
  - **Accuracy.** Hits ÷ counted lines, per class, over applied counts in a window —
    the inventory record accuracy auditors read — and month by month as a trend. A line
    keeps the class and verdict it was applied under, so history doesn't shift when a
    class or tolerance changes later.

The class is set by hand (or by import). UQMES doesn't rank by value: that needs cost,
which is the ERP's.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

CLASSES = ('A', 'B', 'C')
DEFAULT_INTERVAL_DAYS = {'A': 30, 'B': 90, 'C': 365}
DEFAULT_TOLERANCE_PCT = {'A': 1.0, 'B': 3.0, 'C': 5.0}
DEFAULT_TOLERANCE_UNITS = 0.0
# Units that have left the floor for good aren't stock to count.
_GONE = ('SCRAPPED', 'CANCELLED', 'SHIPPED', 'DISMANTLED', 'RMA_CLOSED')


@dataclass(frozen=True)
class CountPolicy:
    interval_days: dict
    tolerance_pct: dict
    tolerance_units: float  # the least difference that still counts as a hit


def count_policy(tenant) -> CountPolicy:
    """The tenant's cadence and tolerances (`Tenant.settings['cycle_count']`), falling
    back to the common defaults for anything unset or unreadable: A monthly, B
    quarterly, C yearly; A ±1 %, B ±3 %, C ±5 %."""
    raw = ((getattr(tenant, 'settings', None) or {}).get('cycle_count') or {})

    def per_class(key, default, cast):
        given = raw.get(key) or {}
        out = {}
        for c in CLASSES:
            try:
                v = cast(given.get(c))
                out[c] = v if v >= 0 else default[c]
            except (TypeError, ValueError):
                out[c] = default[c]
        return out

    try:
        units = max(0.0, float(raw.get('tolerance_units', DEFAULT_TOLERANCE_UNITS)))
    except (TypeError, ValueError):
        units = DEFAULT_TOLERANCE_UNITS
    return CountPolicy(
        interval_days=per_class('interval_days', DEFAULT_INTERVAL_DAYS, int),
        tolerance_pct=per_class('tolerance_pct', DEFAULT_TOLERANCE_PCT, float),
        tolerance_units=units,
    )


# --- tolerance ----------------------------------------------------------------------

def line_classes(tenant, lines) -> dict:
    """{(kind, id): 'A'|'B'|'C'} for count lines: a lot by its material (or part type),
    a unit by its part type; C when unknown."""
    from Tracker.models import MaterialLot, Parts
    lot_ids = [l['id'] for l in lines if l.get('kind') == 'LOT']
    part_ids = [l['id'] for l in lines if l.get('kind') == 'PART']
    out = {}
    for lid, m_cls, t_cls in (MaterialLot.objects.filter(tenant=tenant, pk__in=lot_ids)  # tenant-safe: explicit tenant filter
                              .values_list('id', 'material__abc_class', 'material_type__abc_class')):
        out[('LOT', str(lid))] = m_cls or t_cls or 'C'
    for pid, cls in (Parts.objects.filter(tenant=tenant, pk__in=part_ids)  # tenant-safe: explicit tenant filter
                     .values_list('id', 'part_type__abc_class')):
        out[('PART', str(pid))] = cls or 'C'
    return out


def judge(line, cls, policy) -> tuple[bool, float]:
    """(within tolerance, the tolerance in units) for one counted line."""
    expected = float(line.get('expected') or 0)
    counted = float(line.get('counted') or 0)
    if line.get('found_here'):
        return counted == 0, 0.0
    if line.get('kind') == 'PART':
        return counted == expected, 0.0
    tol = max(abs(expected) * policy.tolerance_pct[cls] / 100.0, policy.tolerance_units)
    return abs(counted - expected) <= tol, tol


# --- due ----------------------------------------------------------------------------

@dataclass(frozen=True)
class DueLocation:
    location_id: object
    location: str
    last_counted: datetime | None
    due_on: date


@dataclass(frozen=True)
class DueItem:
    kind: str  # 'MATERIAL' | 'PART_TYPE'
    id: object
    name: str
    abc_class: str
    interval_days: int
    due_on: date  # the earliest of its locations
    days_overdue: int
    never_counted: bool
    locations: tuple = field(default_factory=tuple)  # DueLocation, the ones due


@dataclass(frozen=True)
class _Held:
    """An item's stock and when each location holding it was last counted."""
    name: str
    abc_class: str
    last: dict  # location id -> datetime | None
    locs: dict  # location id -> StorageLocation


def _held(tenant, only: tuple | None = None) -> dict:
    """(kind, id) -> _Held, for every item with stock in a location (or just `only`)."""
    from django.db.models import Max
    from Tracker.models import CycleCount, MaterialLot, Parts, StorageLocation

    lots = MaterialLot.objects.filter(tenant=tenant, archived=False, quantity_remaining__gt=0,  # tenant-safe: explicit tenant filter
                                      location__isnull=False)
    parts = (Parts.objects.filter(tenant=tenant, archived=False, location__isnull=False,  # tenant-safe: explicit tenant filter
                                  part_type__isnull=False).exclude(part_status__in=_GONE))
    item_counts = CycleCount.objects.filter(tenant=tenant, status='APPLIED', location__isnull=True)  # tenant-safe: explicit tenant filter
    if only is not None:
        kind, oid = only
        if kind == 'MATERIAL':
            lots, parts = lots.filter(material_id=oid), parts.none()
            item_counts = item_counts.filter(material_id=oid)
        else:
            lots = lots.filter(material__isnull=True, material_type_id=oid)
            parts = parts.filter(part_type_id=oid)
            item_counts = item_counts.filter(part_type_id=oid)

    held = defaultdict(set)  # (kind, id) -> location ids
    names, classes = {}, {}
    for (m_id, m_name, m_cls, t_id, t_name, t_cls, loc) in (
            lots.values_list('material_id', 'material__name', 'material__abc_class',
                             'material_type_id', 'material_type__name', 'material_type__abc_class',
                             'location_id')):
        key = ('MATERIAL', m_id) if m_id else ('PART_TYPE', t_id) if t_id else None
        if key is None:
            continue
        held[key].add(loc)
        names[key] = m_name if m_id else t_name
        classes[key] = (m_cls if m_id else t_cls) or 'C'
    for (t_id, t_name, t_cls, loc) in parts.values_list(
            'part_type_id', 'part_type__name', 'part_type__abc_class', 'location_id'):
        key = ('PART_TYPE', t_id)
        held[key].add(loc)
        names[key] = t_name
        classes[key] = t_cls or 'C'

    loc_ids = {l for ls in held.values() for l in ls}
    last = dict(CycleCount.objects.filter(tenant=tenant, status='APPLIED',  # tenant-safe: explicit tenant filter
                                          location_id__in=loc_ids)
                .values('location_id').annotate(at=Max('applied_at')).values_list('location_id', 'at'))
    # An item count counted that item wherever its lines were (and wherever something was
    # found): it credits those (item, location) pairs as a location count credits a place.
    credit = {}
    for c in item_counts.only('material_id', 'part_type_id', 'applied_at', 'lines'):
        key = ('MATERIAL', c.material_id) if c.material_id else ('PART_TYPE', c.part_type_id)
        for line in c.lines or []:
            for where in (line.get('location_id'), line.get('found_at')):
                if where:
                    pair = (key, str(where))
                    credit[pair] = max(credit.get(pair, c.applied_at), c.applied_at)
    locs = {l.id: l for l in StorageLocation.objects.filter(tenant=tenant, pk__in=loc_ids)}  # tenant-safe: explicit tenant filter
    return {key: _Held(name=names[key] or '—', abc_class=classes[key], locs=locs,
                       last={loc: max((t for t in (last.get(loc), credit.get((key, str(loc)))) if t), default=None)
                             for loc in loc_set})
            for key, loc_set in held.items()}


def _due_on(at, interval, today, tz) -> date:
    return today if at is None else at.astimezone(tz).date() + timedelta(days=interval)


def due_for_count(tenant, *, today: date | None = None) -> list[DueItem]:
    """Items with stock in a location that's due for counting under their class —
    never-counted first, then most overdue."""
    from Tracker.services.core.clock import plant_tz, tenant_today

    policy = count_policy(tenant)
    today = today or tenant_today(tenant)
    tz = plant_tz(tenant)

    rows = []
    for key, h in _held(tenant).items():
        cls = h.abc_class
        interval = policy.interval_days[cls]
        due = []
        for loc, at in h.last.items():
            due_on = _due_on(at, interval, today, tz)
            if due_on <= today:
                due.append(DueLocation(location_id=loc, location=_place(h.locs.get(loc)),
                                       last_counted=at, due_on=due_on))
        if not due:
            continue
        due.sort(key=lambda d: (d.last_counted is not None, d.due_on, d.location))
        earliest = min(d.due_on for d in due)
        rows.append(DueItem(
            kind=key[0], id=key[1], name=h.name, abc_class=cls, interval_days=interval,
            due_on=earliest, days_overdue=(today - earliest).days,
            never_counted=any(d.last_counted is None for d in due), locations=tuple(due)))
    rows.sort(key=lambda r: (not r.never_counted, r.due_on, r.abc_class, r.name.lower()))
    return rows


@dataclass(frozen=True)
class ItemCountStatus:
    """Where one item stands for counting — what its form shows."""
    abc_class: str
    interval_days: int
    on_hand: bool  # no stock in a location: nothing to count, nothing due
    last_counted: datetime | None  # the most recent count of any location holding it
    next_due: date | None  # the earliest location due (today if one was never counted)
    never_counted: bool  # some location holding it has never been counted
    locations: tuple = field(default_factory=tuple)  # DueLocation for each, soonest first


def count_status(tenant, kind: str, item_id, *, abc_class: str = 'C',
                 today: date | None = None) -> ItemCountStatus:
    """When `kind` ('MATERIAL' | 'PART_TYPE') `item_id` was last counted and is next due,
    on the same terms as the due list. `abc_class` is the item's own, for when it has no
    stock to read it from."""
    from Tracker.services.core.clock import plant_tz, tenant_today

    policy = count_policy(tenant)
    today = today or tenant_today(tenant)
    tz = plant_tz(tenant)
    h = _held(tenant, only=(kind, item_id)).get((kind, item_id))
    cls = h.abc_class if h else (abc_class or 'C')
    interval = policy.interval_days[cls]
    if h is None:
        return ItemCountStatus(abc_class=cls, interval_days=interval, on_hand=False,
                               last_counted=None, next_due=None, never_counted=False)
    places = sorted((DueLocation(location_id=loc, location=_place(h.locs.get(loc)), last_counted=at,
                                 due_on=_due_on(at, interval, today, tz))
                     for loc, at in h.last.items()), key=lambda d: (d.due_on, d.location))
    counted = [d.last_counted for d in places if d.last_counted]
    return ItemCountStatus(
        abc_class=cls, interval_days=interval, on_hand=True,
        last_counted=max(counted) if counted else None, next_due=places[0].due_on,
        never_counted=any(d.last_counted is None for d in places), locations=tuple(places))


def _place(loc) -> str:
    if loc is None:
        return '—'
    return getattr(loc, 'path', None) or loc.name


# --- accuracy -----------------------------------------------------------------------

def _scored(tenant, lines) -> list[tuple[str, bool]]:
    """(class, hit) per counted line: as judged when the count was applied, or — for a
    count applied before verdicts were kept — judged now under today's class and policy."""
    policy = count_policy(tenant)
    classes = line_classes(tenant, [l for l in lines if 'within_tolerance' not in l])
    out = []
    for l in lines:
        if 'within_tolerance' in l:
            out.append((l.get('abc_class') or 'C', bool(l['within_tolerance'])))
        else:
            cls = classes.get((l.get('kind'), str(l.get('id'))), 'C')
            out.append((cls, judge(l, cls, policy)[0]))
    return out


def _tally(scored) -> dict:
    tally = {c: {'counted': 0, 'hits': 0} for c in CLASSES}
    for cls, hit in scored:
        tally[cls]['counted'] += 1
        tally[cls]['hits'] += hit
    return {c: {**t, 'pct': round(100.0 * t['hits'] / t['counted'], 1) if t['counted'] else None}
            for c, t in tally.items()}


def accuracy_trend(tenant, *, months: int = 12) -> list[dict]:
    """Accuracy per class for each of the last `months` calendar months (plant time),
    oldest first, by the month a count was applied — every month listed, counted or not:
    [{'month': 'YYYY-MM', 'A': {'counted', 'hits', 'pct'}, …}]."""
    from Tracker.models import CycleCount
    from Tracker.services.core.clock import plant_tz, tenant_today

    tz = plant_tz(tenant)
    today = tenant_today(tenant)
    y, m = today.year, today.month
    keys = []
    for _ in range(months):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    keys.reverse()
    start = datetime(int(keys[0][:4]), int(keys[0][5:]), 1, tzinfo=tz)
    by_month = defaultdict(list)
    for c in (CycleCount.objects.filter(tenant=tenant, status='APPLIED', applied_at__gte=start)  # tenant-safe: explicit tenant filter
              .only('applied_at', 'lines')):
        key = c.applied_at.astimezone(tz).strftime('%Y-%m')
        by_month[key].extend(l for l in (c.lines or []) if l.get('counted') is not None)
    return [{'month': k, **_tally(_scored(tenant, by_month.get(k, [])))} for k in keys]


def accuracy(tenant, *, days: int = 90) -> dict:
    """{'A': {'counted', 'hits', 'pct'}, …, 'by_reason': {code: n}} over counts applied in
    the last `days`: each counted line a hit when within its class's tolerance (pct None
    with nothing counted), and the differences by the reason the lead gave."""
    from django.utils import timezone
    from Tracker.models import CycleCount

    counts = list(CycleCount.objects.filter(tenant=tenant, status='APPLIED',  # tenant-safe: explicit tenant filter
                                            applied_at__gte=timezone.now() - timedelta(days=days)))
    lines = [l for c in counts for l in (c.lines or []) if l.get('counted') is not None]
    out = _tally(_scored(tenant, lines))
    # Why the records were off: the lead's reason on each difference applied.
    by_reason = defaultdict(int)
    for l in lines:
        if l.get('reason'):
            by_reason[l['reason']] += 1
    out['by_reason'] = dict(by_reason)
    return out
