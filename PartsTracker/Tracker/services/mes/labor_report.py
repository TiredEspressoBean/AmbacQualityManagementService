"""Operator labor-hours reporting — how many shop hours operators have actually worked.

Sums `TimeEntry` durations per operator over a window:
  - `on_shift_hours` = Σ SHIFT entries (attendance clock-in→out; breaks are separate
    BREAK/LUNCH entries and already excluded by the clock state machine).
  - `direct_hours`   = Σ PRODUCTION / SETUP / REWORK (time clocked onto actual jobs).

Scoped to shop-floor operators (the Operator / Shift Lead groups) so office staff and
admins don't appear — see services.scheduling.data.SHOP_FLOOR_GROUPS.
"""
from __future__ import annotations

_DIRECT_TYPES = {'PRODUCTION', 'SETUP', 'REWORK'}


def operator_hours(tenant, start, end) -> list[dict]:
    """Per shop-floor operator, hours worked over [start, end] (aware datetimes).

    Open entries (no end yet) count up to `end` or now, whichever is earlier. Returns
    rows sorted by on-shift hours desc: {user_id, name, on_shift_hours, direct_hours}.
    """
    from django.utils import timezone
    from Tracker.models import TimeEntry, User
    from Tracker.services.scheduling.data import _shop_floor_user_ids

    cap = min(end, timezone.now())
    entries = (
        TimeEntry.objects.filter(tenant=tenant, start_time__lt=end)
        .exclude(end_time__lt=start)
        .values('user_id', 'entry_type', 'start_time', 'end_time')
    )

    agg: dict[int, list[float]] = {}  # user_id -> [shift_seconds, direct_seconds]
    for e in entries:
        s = max(e['start_time'], start)
        en = min(e['end_time'] or cap, cap)
        if en <= s:
            continue
        secs = (en - s).total_seconds()
        rec = agg.setdefault(e['user_id'], [0.0, 0.0])
        if e['entry_type'] == 'SHIFT':
            rec[0] += secs
        elif e['entry_type'] in _DIRECT_TYPES:
            rec[1] += secs

    shop_ids = _shop_floor_user_ids(tenant)  # limit to floor staff when configured
    # tenant-safe: ids sourced from the tenant-scoped TimeEntry rows above.
    users = {u.id: u for u in User.objects.filter(id__in=list(agg.keys()))}

    out = []
    for uid, (shift_s, direct_s) in agg.items():
        if shop_ids and uid not in shop_ids:
            continue
        u = users.get(uid)
        name = (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.get_username()) if u else f"User {uid}"
        out.append({
            'user_id': uid,
            'name': name,
            'on_shift_hours': round(shift_s / 3600, 2),
            'direct_hours': round(direct_s / 3600, 2),
        })
    out.sort(key=lambda r: r['on_shift_hours'], reverse=True)
    return out
