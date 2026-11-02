"""Volume forecast — the demand nobody has ordered yet, by part type and month.

The outlook beyond firm orders (user decisions 2026-11-02). One quantity per part type
per month, new builds only, no customer. Planning consumes it: firm orders and RFI deals
use it up, so a month plans max(forecast, firm + tentative) and the outlook shows the
unclaimed remainder apart (`unclaimed_forecast`).

Entered two ways, both writing through `set_forecast`:

- **A sheet** — Item × Month × Quantity, one row per cell. Re-runnable: each row
  replaces the forecast for the month it names; a month the sheet doesn't name is left
  alone, since a typed sheet is never complete. Items by the number a planner types —
  the part type's ERP id, falling back to its exact name — like every other sheet.
- **A grid** — part types down, months across, edited in place.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import date, timedelta

from Tracker.services.csv_utils import parse_date, parse_file

CREATED, UPDATED, UNCHANGED, CLEARED = 'CREATED', 'UPDATED', 'UNCHANGED', 'CLEARED'

TEMPLATE_COLUMNS = ["Item*", "Month*", "Quantity*"]
TEMPLATE_EXAMPLE = ["INJ-4410", "2027-03", "40"]

FIELD_MAP = {
    "item": "item", "part_type": "item", "part": "item", "part_number": "item",
    "erp_id": "item",
    "month": "month", "period": "month", "date": "month",
    "quantity": "quantity", "qty": "quantity", "forecast": "quantity", "volume": "quantity",
}

_MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, k: int) -> date:
    y, m = divmod(d.month - 1 + k, 12)
    return date(d.year + y, m + 1, 1)


def parse_month(value) -> date | None:
    """A month as a planner writes it: 2027-03, 03/2027, Mar 2027, March-27, or any date
    in the month (Excel turns "Mar 2027" into the 1st)."""
    if value is None:
        return None
    if isinstance(value, date):
        return month_start(value)
    text = str(value).strip()
    if not text:
        return None
    m = re.fullmatch(r'(\d{4})[-/.](\d{1,2})', text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return date(y, mo, 1) if 1 <= mo <= 12 else None
    m = re.fullmatch(r'(\d{1,2})[-/.](\d{4})', text)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        return date(y, mo, 1) if 1 <= mo <= 12 else None
    m = re.fullmatch(r'([A-Za-z]{3,9})[\s\-/.,]+(\d{2}|\d{4})', text)
    if m and m.group(1)[:3].lower() in _MONTHS:
        y = int(m.group(2))
        return date(y + 2000 if y < 100 else y, _MONTHS[m.group(1)[:3].lower()], 1)
    parsed = parse_date(text)
    return month_start(parsed.date() if hasattr(parsed, 'date') else parsed) if parsed else None


def resolve_part_type(tenant, text: str):
    """The current part type a planner typed — by ERP id, then exact name — or ValueError."""
    from Tracker.models import PartTypes
    text = (text or "").strip()
    if not text:
        raise ValueError("No item given")
    pts = PartTypes.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, is_current_version=True)
    found = list(pts.filter(ERP_id__iexact=text)[:2]) or list(pts.filter(name__iexact=text)[:2])
    if not found:
        raise ValueError(f"No part type '{text}'")
    if len(found) > 1:
        raise ValueError(f"'{text}' matches more than one part type — use its ERP id")
    return found[0]


def set_forecast(*, tenant, part_type, month: date, quantity: int | None) -> str:
    """Set one cell. None or 0 clears it (archives the row, so the trail keeps what the
    forecast said). Returns CREATED / UPDATED / UNCHANGED / CLEARED."""
    from Tracker.models import VolumeForecast
    month = month_start(month)
    if quantity is not None and quantity < 0:
        raise ValueError("A forecast can't be negative")
    row = VolumeForecast.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, part_type=part_type, month=month, archived=False).first()
    if not quantity:
        if row is None:
            return UNCHANGED
        row.archive(reason="user_request", notes="Forecast cell cleared")
        return CLEARED
    if row is None:
        VolumeForecast.objects.create(tenant=tenant, part_type=part_type, month=month,
                                      quantity=quantity)
        return CREATED
    if row.quantity == quantity:
        return UNCHANGED
    row.quantity = quantity
    row.save(update_fields=['quantity', 'updated_at'])
    return UPDATED


def forecast_by_month(tenant, first: date, last: date) -> dict:
    """{(part_type_id, month_start): quantity} for live rows in [first, last]."""
    from Tracker.models import VolumeForecast
    return {
        (r['part_type_id'], r['month']): r['quantity']
        for r in VolumeForecast.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, archived=False, month__gte=month_start(first), month__lte=last)
        .values('part_type_id', 'month', 'quantity')
    }


def claims_by_month(tenant, first: date, last: date) -> dict:
    """What orders already claim of each part type's forecast, by the month it is due:
    `{(part_type_id, month_start): {'firm': qty, 'tentative': qty}}`.

    Counted by what was ASKED for, not what is still to do — a line half-built this
    month still met that month's forecast. So:

    - every non-cancelled order line due in the window, at its full quantity —
      `tentative` when its order is still an RFI, `firm` otherwise;
    - plus work orders on no order line (stock builds, jobs entered straight from the
      ERP), at their quantity in the month they are due — their units are new builds
      the forecast was standing in for. Work pegged to a line is that line's units
      already, so counting it too would claim the month twice. Teardown work is a core
      coming back, not a new build, so it claims nothing.

    A REMAN line claims nothing either (2026-11-02): one whose units come in as the
    customer's cores — repair-and-return or exchange — recognised by cores received for
    that order of the line's part type. The forecast is of new builds only.
    """
    from Tracker.models import OrderLine, Parts, WorkOrder
    first, end = month_start(first), add_months(month_start(last), 1)
    out: dict = defaultdict(lambda: {'firm': 0, 'tentative': 0})
    lines = list(OrderLine.objects  # tenant-safe: explicit tenant filter
                 .filter(tenant=tenant, archived=False, order__archived=False,
                         due_date__gte=first, due_date__lt=end)
                 .exclude(status='CANCELLED').exclude(order__order_status='CANCELLED')
                 .values('order_id', 'part_type_id', 'due_date', 'quantity', 'order__order_status'))
    reman = set(Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, archived=False, core_role__isnull=False,
        order_id__in={r['order_id'] for r in lines}).values_list('order_id', 'part_type_id'))
    for r in lines:
        if (r['order_id'], r['part_type_id']) in reman:
            continue
        band = 'tentative' if r['order__order_status'] == 'RFI' else 'firm'
        out[(r['part_type_id'], month_start(r['due_date']))][band] += r['quantity']
    for r in (WorkOrder.objects  # tenant-safe: explicit tenant filter
              .filter(tenant=tenant, archived=False, order_line__isnull=True,
                      process__isnull=False, process__is_disassembly=False,
                      expected_completion__gte=first, expected_completion__lt=end)
              .exclude(workorder_status='CANCELLED')
              .values('process__part_type_id', 'expected_completion', 'quantity')):
        out[(r['process__part_type_id'], month_start(r['expected_completion']))]['firm'] += r['quantity'] or 0
    return dict(out)


def consumption_settings(tenant) -> tuple[int, int]:
    """(demand time fence in DAYS, consumption window in months) — the tenant's shop
    practice, kept on OptimizationConfig beside the other planning fences."""
    from Tracker.models import OptimizationConfig
    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()  # tenant-safe: explicit tenant filter
    if cfg is None:
        return 30, 1
    return cfg.demand_time_fence_days, cfg.forecast_consumption_window_months


def fence_end(tenant) -> date:
    """The first day OUTSIDE the demand time fence: the plant's today plus the fence."""
    from Tracker.services.core.clock import tenant_today
    return tenant_today(tenant) + timedelta(days=consumption_settings(tenant)[0])


def fenced_share(month: date, today: date, end: date) -> float:
    """The share of `month`'s REMAINING days (from today on) that fall inside the fence
    [today, end): 1.0 when all of them are fenced, 0.0 when none are. A month straddling
    the fence is planned only for its days past it — its quantity pro-rated by days
    (2026-11-02). Days already past aren't "inside the fence": with the fence off, the
    current month's forecast is planned whole, as it always was."""
    nxt = add_months(month, 1)
    begin = max(month, today)
    days = (nxt - begin).days
    if days <= 0:
        return 0.0
    inside = max(0, (min(end, nxt) - begin).days)
    return inside / days


def unclaimed_forecast(tenant, first: date, last: date) -> dict:
    """`{(part_type_id, month_start): cell}` for every cell with a forecast, where a cell
    is `{'forecast', 'firm', 'tentative', 'unclaimed', 'fenced', 'claimed_from'}`.

    Orders consume forecast (2026-11-02), each in the standard order: its due month,
    then EARLIER months nearest first, then LATER months, within the consumption window
    — so an order due 2 March isn't left double-counted against February's forecast.
    Orders are taken in due-month order, firm before tentative within a month, and no
    cell goes below zero. `firm` / `tentative` are what a cell's forecast lost to orders,
    and `claimed_from` lists the part that spilled in from a neighbouring month.

    The demand time fence is measured in days from the plant's today (2026-11-02):
    forecast due inside it is shown but not planned, since unsold forecast that close in
    won't arrive — only orders count there. `fenced` marks a month wholly inside it; a
    month straddling it plans only the share of its days past the fence, its unclaimed
    quantity pro-rated by days — `fenced_quantity` is the part held back and `planned`
    what planning adds. So a month plans max(forecast, firm + tentative) for the part
    type, less what the fence holds back.
    """
    from Tracker.services.core.clock import tenant_today
    fence, window = consumption_settings(tenant)
    first, last = month_start(first), month_start(last)
    this_month = month_start(tenant_today(tenant))
    # Consumption is computed from a FIXED anchor — the current month — and then sliced,
    # so a cell reads the same whichever range is asked about (the grid and a quote
    # must not disagree). Past months drop out on both sides: a past-due order's work is
    # already in the load as overdue, and a past month's forecast is history (standard
    # practice). Up to `last + window` is enough: an order takes its own month, then
    # earlier months, before any later one, so nothing beyond that reaches `last`.
    lo, hi = this_month, add_months(last, window)
    if hi < lo:
        return {}
    fc = forecast_by_month(tenant, lo, hi)
    if not fc:
        return {}
    claims = claims_by_month(tenant, lo, hi)

    left = dict(fc)
    taken: dict = defaultdict(lambda: {'firm': 0, 'tentative': 0})
    spilled: dict = defaultdict(list)
    for (pt_id, due) in sorted(claims, key=lambda k: (k[1], str(k[0]))):
        reach = ([due] + [add_months(due, -k) for k in range(1, window + 1)]
                 + [add_months(due, k) for k in range(1, window + 1)])
        for band in ('firm', 'tentative'):
            qty = claims[(pt_id, due)][band]
            for m in reach:
                if qty <= 0:
                    break
                avail = left.get((pt_id, m), 0)
                if avail <= 0:
                    continue
                use = min(avail, qty)
                left[(pt_id, m)] -= use
                qty -= use
                taken[(pt_id, m)][band] += use
                if m != due:
                    spilled[(pt_id, m)].append(
                        {'band': band, 'quantity': use, 'from_month': f"{due:%Y-%m}"})

    today = tenant_today(tenant)
    end = today + timedelta(days=fence)
    out = {}
    for key, qty in fc.items():
        if not first <= key[1] <= last:
            continue
        t = taken.get(key, {'firm': 0, 'tentative': 0})
        share = fenced_share(key[1], today, end)
        held = round(left[key] * share)
        asked = claims.get(key, {'firm': 0, 'tentative': 0})
        out[key] = {'forecast': qty, 'firm': t['firm'], 'tentative': t['tentative'],
                    # What orders DUE this month ask for, in full — the true total
                    # ordered, which may exceed the forecast (`firm`/`tentative` above
                    # are what this cell's forecast lost, capped by it).
                    'ordered_firm': asked['firm'], 'ordered_tentative': asked['tentative'],
                    'unclaimed': left[key], 'fenced': share >= 1.0,
                    'fenced_quantity': held, 'planned': left[key] - held,
                    'claimed_from': spilled.get(key, [])}
    return out


def grid(tenant, start: date, months: int) -> dict:
    """Part types down, months across: every part type with a forecast in the window,
    each cell carrying what orders already claim of it beside the forecast itself."""
    from Tracker.models import PartTypes
    first = month_start(start)
    labels = [add_months(first, k) for k in range(months)]
    cells: dict = defaultdict(dict)
    for (pt_id, m), c in unclaimed_forecast(tenant, first, labels[-1]).items():
        cells[pt_id][f"{m:%Y-%m}"] = c
    pts = PartTypes.objects.filter(tenant=tenant, id__in=list(cells))  # tenant-safe: explicit tenant filter
    rows = [{'part_type_id': str(pt.id), 'part_type': pt.name, 'erp_id': pt.ERP_id or "",
             'cells': cells[pt.id]} for pt in pts]
    rows.sort(key=lambda r: r['part_type'].lower())
    from Tracker.services.core.clock import tenant_today
    today, end = tenant_today(tenant), fence_end(tenant)
    return {'months': [f"{m:%Y-%m}" for m in labels], 'rows': rows,
            # Wholly inside the fence; a straddling month's cells say how much is held.
            'fenced_months': [f"{m:%Y-%m}" for m in labels if fenced_share(m, today, end) >= 1.0],
            'fence_ends': end.isoformat()}


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS)
    w.writerow(TEMPLATE_EXAMPLE)
    return "﻿" + buf.getvalue()  # BOM so Excel opens it as UTF-8


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def import_forecast(*, tenant, file, filename: str) -> dict:
    """Parse and apply a forecast sheet. Row by row: a bad row is reported and skipped,
    the rest still land. Raises ValueError only for a file that can't be read."""
    rows, _headers = parse_file(file, filename, field_map=FIELD_MAP)
    counts = {CREATED: 0, UPDATED: 0, UNCHANGED: 0, CLEARED: 0, 'ERROR': 0}
    report = []
    seen: dict = {}
    for n, row in enumerate(rows, start=1):
        if not any(_text(v) for v in row.values()):
            continue
        entry = {'row': n, 'item': _text(row.get('item')), 'month': '', 'quantity': None,
                 'detail': ''}
        try:
            pt = resolve_part_type(tenant, entry['item'])
            month = parse_month(row.get('month'))
            if month is None:
                raise ValueError(f"Month '{_text(row.get('month'))}' isn't a month — write it as YYYY-MM")
            entry['month'] = f"{month:%Y-%m}"
            raw = _text(row.get('quantity'))
            try:
                qty = int(float(raw)) if raw else 0
            except ValueError:
                raise ValueError(f"Quantity '{raw}' isn't a number")
            if raw and float(raw) != qty:
                raise ValueError(f"Quantity '{raw}' isn't a whole number")
            entry['quantity'] = qty
            key = (pt.id, month)
            if key in seen:
                # Two rows for one cell: the later one wins, said so nobody wonders.
                entry['detail'] = f"Replaces row {seen[key]} for the same item and month."
            seen[key] = n
            entry['outcome'] = set_forecast(tenant=tenant, part_type=pt, month=month, quantity=qty)
        except ValueError as e:
            entry['outcome'] = 'ERROR'
            entry['detail'] = str(e)
        counts[entry['outcome']] += 1
        report.append(entry)
    return {'created': counts[CREATED], 'updated': counts[UPDATED],
            'unchanged': counts[UNCHANGED], 'cleared': counts[CLEARED],
            'errors': counts['ERROR'], 'rows': report}
