"""Downtime event rules.

`EquipmentType.track_downtime` is the per-type opt-out: a crib of calipers or
torque wrenches is not a production resource, so a broken one is a calibration
or replacement matter, not lost machine time. Equipment with no type is
treated as tracked — nothing has opted it out.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q


def downtime_refusal(equipment) -> str | None:
    """Why downtime cannot be recorded against `equipment`, or None if it can."""
    if equipment is None:
        return None
    equipment_type = equipment.equipment_type
    if equipment_type is None or equipment_type.track_downtime:
        return None
    return (f"{equipment.name} is a {equipment_type.name}, and that equipment type "
            f"does not track downtime.")


@dataclass(frozen=True)
class DowntimeBucket:
    key: str            # category code; equipment id, or 'wc:<id>' / '' when no machine
    label: str
    hours: float
    events: int


@dataclass(frozen=True)
class DowntimeSummary:
    start: datetime
    end: datetime
    total_hours: float
    total_events: int
    open_events: int
    by_category: tuple[DowntimeBucket, ...]    # largest first — the Pareto
    by_equipment: tuple[DowntimeBucket, ...]   # largest first


def downtime_summary(*, start: datetime, end: datetime) -> DowntimeSummary:
    """Downtime between `start` and `end`, by category and by machine, largest first.

    Each event counts only for the part of it inside the window, and an event still
    open counts up to `end` (normally now) — a machine down since Tuesday is down
    today. This is lost time, not OEE: availability needs the time the machine was
    scheduled to run, and performance and quality need run-rate and yield data this
    does not read.
    """
    from collections import defaultdict
    from Tracker.models import DowntimeEvent

    labels = dict(DowntimeEvent.DOWNTIME_CATEGORY_CHOICES)
    events = (DowntimeEvent.objects  # tenant-safe: .objects auto-scopes to the current tenant
              .filter(archived=False, start_time__lt=end)
              .filter(Q(end_time__isnull=True) | Q(end_time__gt=start))
              .select_related('equipment', 'work_center'))

    cat_hours, cat_count = defaultdict(float), defaultdict(int)
    eq_hours, eq_count, eq_label = defaultdict(float), defaultdict(int), {}
    total, n, open_n = 0.0, 0, 0
    for e in events:
        lo = max(e.start_time, start)
        hi = min(e.end_time or end, end)
        hours = max((hi - lo).total_seconds(), 0) / 3600
        total += hours
        n += 1
        open_n += e.end_time is None
        cat_hours[e.category] += hours
        cat_count[e.category] += 1
        if e.equipment_id:
            key = str(e.equipment_id)
            eq_label[key] = e.equipment.name
        elif e.work_center_id:
            key = f"wc:{e.work_center_id}"
            eq_label[key] = e.work_center.name
        else:
            key = ''
            eq_label[key] = 'No machine'
        eq_hours[key] += hours
        eq_count[key] += 1

    def buckets(hours, counts, label):
        return tuple(sorted(
            (DowntimeBucket(k, label(k), round(h, 2), counts[k]) for k, h in hours.items()),
            key=lambda b: (-b.hours, b.label)))

    return DowntimeSummary(
        start=start, end=end, total_hours=round(total, 2), total_events=n, open_events=open_n,
        by_category=buckets(cat_hours, cat_count, lambda k: labels.get(k, k)),
        by_equipment=buckets(eq_hours, eq_count, lambda k: eq_label[k]),
    )
