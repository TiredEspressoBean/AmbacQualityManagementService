"""Working time: shifts, closures, overtime and people's time off, expanded to concrete
datetime windows over a horizon, plus the interval arithmetic they need.

Everything here is wall-clock time on the PLANT's clock (`core.clock.plant_tz`): a
shift that starts at six starts at six on the shop wall, whatever zone the server is
in. The machine and work data the solver reads live in `data`.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from Tracker.services.core.clock import plant_tz


# --- Interval arithmetic ------------------------------------------------------

def _merge_intervals(intervals: list[tuple]) -> list[tuple]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [intervals[0]]
    for s, e in intervals[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _subtract_intervals(base: list[tuple], holes: list[tuple]) -> list[tuple]:
    """Remove `holes` (e.g. downtime) from `base` free windows."""
    if not holes:
        return list(base)
    holes = _merge_intervals(holes)
    result: list[tuple] = []
    for b_start, b_end in base:
        cursor = b_start
        for h_start, h_end in holes:
            if h_end <= cursor or h_start >= b_end:
                continue
            if h_start > cursor:
                result.append((cursor, min(h_start, b_end)))
            cursor = max(cursor, h_end)
            if cursor >= b_end:
                break
        if cursor < b_end:
            result.append((cursor, b_end))
    return result


# --- Shifts -------------------------------------------------------------------

def _combine_in(tz, day, t):
    """A wall-clock (date, time) in `tz`, as an aware datetime.

    Built with the zone attached rather than via `make_aware`, so zoneinfo resolves the
    offset for that wall time — which is what makes a 06:00 shift stay 06:00 across a
    DST change instead of drifting an hour.
    """
    return datetime.combine(day, t).replace(tzinfo=tz)


def _parse_days(raw: str) -> set:
    if not raw:
        return set()
    return {int(x) for x in raw.split(',') if x.strip().isdigit()}


def _expand_shifts(shifts, start: datetime, end: datetime, tz=None) -> list[tuple]:
    """Expand recurring shifts into concrete [start, end] datetime windows over
    [start, end], clipped to that range. Overnight shifts (end_time <= start_time)
    roll into the next day. Returned sorted + merged.

    `tz` is the PLANT's zone (see `plant_tz`). Both the day loop and the wall-clock
    combine run in it: iterating UTC dates put the day boundary in the wrong place for
    any shop that isn't on UTC, so a Monday-only shift could be expanded onto Sunday.
    Defaults to the server zone, which is the old behaviour.
    """
    tz = tz or timezone.get_current_timezone()
    windows: list[tuple] = []
    day = timezone.localtime(start, tz).date()
    last = timezone.localtime(end, tz).date()
    while day <= last:
        weekday = day.weekday()  # 0=Monday
        for sh in shifts:
            active_days = _parse_days(sh.days_of_week)
            if active_days and weekday not in active_days:
                continue
            w_start = _combine_in(tz, day, sh.start_time)
            end_day = day + timedelta(days=1) if sh.end_time <= sh.start_time else day
            w_end = _combine_in(tz, end_day, sh.end_time)
            w_start = max(w_start, start)
            w_end = min(w_end, end)
            if w_start < w_end:
                windows.append((w_start, w_end))
        day += timedelta(days=1)
    return _merge_intervals(windows)


# --- Plant closures -------------------------------------------------------------

def _yearly_closure_occurrences(e, horizon) -> list[tuple]:
    """A YEARLY closure recurs on its stored month/day span every year. Emit the
    occurrence(s) landing in the horizon (a 30-day window touches at most two years)."""
    span = e.end_time - e.start_time
    out = []
    for year in {horizon.start.year, horizon.end.year}:
        try:
            occ_start = e.start_time.replace(year=year)
        except ValueError:
            continue  # Feb 29 in a non-leap year — skip this year
        occ_end = occ_start + span
        if occ_start < horizon.end and occ_end >= horizon.start:
            out.append((max(occ_start, horizon.start), min(occ_end, horizon.end)))
    return out


def get_calendar_closures(tenant, horizon) -> list[tuple]:
    """Tenant-wide plant closures — holidays / shutdowns / inventory days — overlapping the
    horizon, as merged [start, end] datetime intervals. The scheduler blocks EVERY machine
    during these and treats operators as absent. ONCE closures use their dated span; YEARLY
    closures recur on their month/day each year. Empty when none are configured."""
    from Tracker.models import PlantCalendarException

    out: list[tuple] = []
    for e in PlantCalendarException.objects.filter(archived=False, tenant=tenant, is_active=True):
        if e.recurrence == 'YEARLY':
            out.extend(_yearly_closure_occurrences(e, horizon))
        elif e.start_time < horizon.end and e.end_time >= horizon.start:
            out.append((max(e.start_time, horizon.start), min(e.end_time, horizon.end)))
    return _merge_intervals(out)


def get_working_windows(tenant, start: datetime, end: datetime) -> list[tuple]:
    """Tenant-wide working windows (merged, sorted) over [start, end] — the active
    shift calendar expanded to datetimes, PLUS overtime (extra/weekend runs), minus
    plant closures (holidays/shutdowns). The complement is non-working time
    (nights/weekends/holidays), which the Gantt shades. Overtime is unioned in so the
    Gantt doesn't shade an overtime day as non-working while the solver schedules
    operators on it (get_operator_shift_windows counts the same overtime). Empty when
    no shifts are configured (the solver treats that as always-available). Closures
    are the solver's own (`get_calendar_closures`), yearly ones included, so the Gantt
    shades exactly the days the solver keeps work off."""
    from Tracker.models import Shift
    from Tracker.services.scheduling.data import HorizonData

    shifts = list(Shift.objects.filter(archived=False, tenant=tenant, is_active=True, is_current_version=True))
    horizon = HorizonData(start=start, end=end, frozen_end=start, slushy_end=start)
    base = _merge_intervals(
        _expand_shifts(shifts, start, end, plant_tz(tenant))
        + get_overtime_machine_windows(tenant, horizon))
    return _subtract_intervals(base, get_calendar_closures(tenant, horizon))


# --- Overtime -------------------------------------------------------------------

def _overtime_intervals(o, shift, horizon, tz=None) -> list[tuple]:
    """Concrete datetime windows for one overtime entry: the shift's hours on the days
    it runs — ONCE across [start_date, end_date], WEEKLY on days_of_week — clipped to
    the horizon. Hours come from the referenced shift (overnight handled by the shift
    expander)."""
    from types import SimpleNamespace
    from datetime import time as _time

    if o.recurrence == 'WEEKLY':
        if not (o.days_of_week or '').strip():
            return []
        shim = SimpleNamespace(days_of_week=o.days_of_week,
                               start_time=shift.start_time, end_time=shift.end_time)
        return _expand_shifts([shim], horizon.start, horizon.end, tz)
    # ONCE — run the shift's hours on each date in [start_date, end_date]
    if not o.start_date or not o.end_date:
        return []
    # The overtime DATES are plant-local calendar days too: "Saturday the 4th" is a day
    # on the shop's wall calendar, not a UTC one.
    _tz = tz or timezone.get_current_timezone()
    lo = max(_combine_in(_tz, o.start_date, _time.min), horizon.start)
    hi = min(_combine_in(_tz, o.end_date, _time.max), horizon.end)
    if lo >= hi:
        return []
    shim = SimpleNamespace(days_of_week='',  # every date in the range
                           start_time=shift.start_time, end_time=shift.end_time)
    return _expand_shifts([shim], lo, hi, tz)


def get_overtime_windows(tenant, horizon) -> dict[int, list[tuple]]:
    """Extra runs of each shift over the horizon → {shift_id: [(s,e)] merged}. An
    `OvertimeWindow` names a Shift (its hours + crew); ONCE runs it on a date range,
    WEEKLY on weekdays. Operators rostered to a shift get that shift's overtime (so a
    'Night shift Saturday' pulls the night crew, not the whole company). Attended
    machines get the union — see get_overtime_machine_windows."""
    from Tracker.models import OvertimeWindow

    by_shift: dict[int, list[tuple]] = {}
    for o in (OvertimeWindow.objects.filter(archived=False, tenant=tenant, is_active=True)
              .select_related('shift')):
        sh = o.shift
        if sh is None or not sh.is_active:
            continue
        iv = _overtime_intervals(o, sh, horizon, plant_tz(tenant))
        if iv:
            by_shift.setdefault(sh.id, []).extend(iv)
    return {sid: _merge_intervals(v) for sid, v in by_shift.items()}


def get_overtime_machine_windows(tenant, horizon) -> list[tuple]:
    """Union of ALL overtime windows over the horizon (merged) — attended machines are
    open whenever any overtime shift is running (the shop is running)."""
    by_shift = get_overtime_windows(tenant, horizon)
    return _merge_intervals([iv for lst in by_shift.values() for iv in lst])


# --- People's time ----------------------------------------------------------------

def _labor_block_intervals(block, horizon, tz=None) -> list[tuple]:
    """Concrete [start, end] datetime intervals a LaborCalendarBlock covers over the
    horizon. ONCE = its clamped datetime span; WEEKLY = its time-of-day window on each
    matching day-of-week (reusing the shift expander). Malformed rows yield nothing."""
    from types import SimpleNamespace

    if block.recurrence == 'WEEKLY':
        if block.window_start is None or block.window_end is None:
            return []
        shim = SimpleNamespace(
            days_of_week=block.days_of_week or '',
            start_time=block.window_start, end_time=block.window_end)
        return _expand_shifts([shim], horizon.start, horizon.end, tz)
    # ONCE
    if block.start_time is None or block.end_time is None:
        return []
    if block.start_time >= horizon.end or block.end_time <= horizon.start:
        return []
    return [(max(block.start_time, horizon.start), min(block.end_time, horizon.end))]


def get_labor_calendar_blocks(tenant, horizon):
    """Operator non-working time over the horizon from `LaborCalendarBlock` — PTO,
    sick, training, meetings, ad-hoc breaks — one-off or weekly, company-wide or for
    one person. Returns `(company, by_user)`: `company` is merged intervals that apply
    to EVERY operator (user is null — e.g. an all-hands); `by_user` maps a user id to
    their own merged intervals. Machines are unaffected (a meeting doesn't stop a
    lights-out CNC — only PlantCalendarException does)."""
    from Tracker.models import LaborCalendarBlock

    company: list[tuple] = []
    by_user: dict[int, list[tuple]] = {}
    rows = LaborCalendarBlock.objects.filter(archived=False, tenant=tenant, is_active=True)
    for b in rows:
        intervals = _labor_block_intervals(b, horizon, plant_tz(tenant))
        if not intervals:
            continue
        if b.user_id is None:
            company.extend(intervals)
        else:
            by_user.setdefault(b.user_id, []).extend(intervals)
    return _merge_intervals(company), {u: _merge_intervals(iv) for u, iv in by_user.items()}


def get_operator_shift_windows(tenant, horizon) -> dict[int, list[tuple]]:
    """Per dispatchable operator, the concrete [start, end] datetime windows they are
    available over the horizon: their rostered `default_shift` expanded, PLUS company
    overtime (extra/weekend shifts), MINUS plant closures (closures always win), MINUS
    company-wide labor blocks (all-hands) and their own blocks (PTO/sick/training).
    Operators fully unavailable over the horizon are dropped. Shifts and overtime are
    expanded once and shared; blocks are subtracted per operator."""
    from Tracker.models import Shift, User
    from Tracker.services.scheduling.data import _shop_floor_user_ids

    roster = dict(
        User.objects.filter(tenant=tenant, is_active=True, user_type='INTERNAL',
                            default_shift__isnull=False)
        .values_list('id', 'default_shift_id')
    )
    shop_ids = _shop_floor_user_ids(tenant)  # gate to shop-floor groups when configured
    if shop_ids:
        roster = {uid: sid for uid, sid in roster.items() if uid in shop_ids}
    shift_ids = set(roster.values())
    closures = get_calendar_closures(tenant, horizon)
    by_shift = {
        s.id: _expand_shifts([s], horizon.start, horizon.end, plant_tz(tenant))
        for s in Shift.objects.filter(archived=False, tenant=tenant, id__in=shift_ids, is_active=True, is_current_version=True)
    }
    overtime_by_shift = get_overtime_windows(tenant, horizon)  # {shift_id: [(s,e)]}
    company_blocks, user_blocks = get_labor_calendar_blocks(tenant, horizon)
    out: dict[int, list[tuple]] = {}
    for uid, sid in roster.items():
        # Overtime is scoped to the shift's own crew — an operator only gets the extra
        # runs of the shift they're rostered to.
        overtime = overtime_by_shift.get(sid, [])
        windows = _merge_intervals(by_shift.get(sid, []) + overtime)  # shift + its overtime
        windows = _subtract_intervals(windows, closures)             # closures always win
        own = user_blocks.get(uid)
        blocks = _merge_intervals(company_blocks + own) if own else company_blocks
        if blocks:
            windows = _subtract_intervals(windows, blocks)
        if windows:
            out[uid] = windows
    return out


def get_operator_unavailability(tenant, horizon,
                                open_entry_minutes: int = 30) -> dict[int, list[tuple]]:
    """Per operator, [start, end] datetime intervals they are NOT available to be
    dispatched — actual clock-out breaks from `TimeEntry` (BREAK / LUNCH) overlapping
    the horizon. An open entry (no end yet = currently on break) is treated as lasting
    `open_entry_minutes` from its start, so a re-dispatch mid-shift won't hand work to
    someone who just clocked out for lunch."""
    from Tracker.models import TimeEntry

    out: dict[int, list[tuple]] = {}
    entries = (
        TimeEntry.objects.filter(archived=False, tenant=tenant, entry_type__in=['BREAK', 'LUNCH'])
        .filter(start_time__lt=horizon.end)
    )
    for e in entries:
        end = e.end_time or (e.start_time + timedelta(minutes=open_entry_minutes))
        if end <= horizon.start:
            continue
        out.setdefault(e.user_id, []).append((e.start_time, end))
    return {uid: _merge_intervals(iv) for uid, iv in out.items()}
