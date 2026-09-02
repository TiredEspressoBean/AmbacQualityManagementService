"""Rough-Cut Capacity Planning (RCCP) + Capable-to-Promise (CTP).

Aggregate capacity-vs-load over monthly buckets — no sequencing, no solver, so it
scales to years. Two resources per bucket:
  - LABOR: dispatchable crew × working hours (operators are usually the binding
    constraint — see the scheduling work; ignoring labor would give falsely
    optimistic promises).
  - MACHINE, per work center: schedulable equipment × operating hours (calendar
    hours when lights-out, shift hours when attended — reuses the runs_unattended
    resolution).

Load is coarse and deliberately so (RCCP works off planned orders, not detailed
WIP): each active work order's full routing × quantity × cycle time, point-loaded
into the bucket of its due date. Refinements (back-scheduling across lead time,
skill-specific labor pools, BOM sub-assembly load, in-progress netting) are v2.

CTP explodes a candidate order's routing the same way, adds it to the load, and
checks whether any resource in the affected bucket crosses capacity — answering
"can we take 500 injectors in six months?" with yes/no + the binding resource +
the earliest bucket it fits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.utils import timezone

from Tracker.services.scheduling import data as sched_data


# --- buckets ---------------------------------------------------------------

@dataclass(frozen=True)
class Bucket:
    label: str          # "2026-09"
    start: datetime
    end: datetime       # exclusive
    working_hours: float   # per-person shift hours in the bucket (labor basis)
    calendar_hours: float  # wall-clock hours in the bucket (lights-out basis)


def _month_buckets(tenant, start: datetime, months: int) -> list[Bucket]:
    """`months` monthly buckets from the start of `start`'s month."""
    out: list[Bucket] = []
    y, m = start.year, start.month
    cur = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(months):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        nxt = cur.replace(year=ny, month=nm)
        windows = sched_data.get_working_windows(tenant, cur, nxt)
        working = sum((b - a).total_seconds() / 3600 for a, b in windows)
        calendar = (nxt - cur).total_seconds() / 3600
        out.append(Bucket(f"{y:04d}-{m:02d}", cur, nxt, working, calendar))
        y, m, cur = ny, nm, nxt
    return out


def window_bucket(tenant, start: datetime, end: datetime, label: str = "window") -> Bucket:
    """One arbitrary [start, end) bucket — the same capacity basis as a month bucket,
    for callers that need a single span (e.g. the solver's horizon) rather than a
    monthly series."""
    windows = sched_data.get_working_windows(tenant, start, end)
    working = sum((b - a).total_seconds() / 3600 for a, b in windows)
    calendar = (end - start).total_seconds() / 3600
    return Bucket(label, start, end, working, calendar)


def load_and_capacity(tenant, bucket: Bucket) -> dict:
    """Remaining work content vs available hours over one span, per resource.

    Shares `_load_reference` / `_route_hours` with the monthly view, so the coarse
    plan and any window-level check can never disagree about how much work an order
    represents. Returns `{'labor': {...}, 'work_centers': [...]}`, each entry
    `{name, required_hours, available_hours, overload_hours}`.
    """
    import collections

    ref = _load_reference(tenant)
    labor_req = 0.0
    wc_req: dict = collections.defaultdict(float)
    for wo in sched_data.get_active_workorders(tenant):
        labor_h, wc_h = _route_hours(ref, _route_counts(wo))
        labor_req += labor_h
        for wc_id, h in wc_h.items():
            wc_req[wc_id] += h

    def _entry(name, required, available):
        return {'name': name,
                'required_hours': round(required, 1),
                'available_hours': round(available, 1),
                'overload_hours': round(max(0.0, required - available), 1)}

    work_centers = []
    for wc_id, required in wc_req.items():
        lights_out, attended = ref.wc_machine_hours.get(wc_id, (0, 0))
        available = lights_out * bucket.calendar_hours + attended * bucket.working_hours
        work_centers.append(_entry(ref.wc_names.get(wc_id, str(wc_id)), required, available))
    work_centers.sort(key=lambda e: -e['overload_hours'])

    return {
        'labor': _entry(f"Labor ({ref.crew_size} crew)", labor_req,
                        ref.crew_size * bucket.working_hours),
        'work_centers': work_centers,
    }


def _bucket_index(buckets: list[Bucket], when: date | datetime) -> int | None:
    """Index of the bucket containing `when`, or None if outside the horizon."""
    dt = when if isinstance(when, datetime) else datetime(when.year, when.month, when.day)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    for i, b in enumerate(buckets):
        if b.start <= dt < b.end:
            return i
    return None


# --- shared reference data -------------------------------------------------

@dataclass
class _RefData:
    timings: dict            # step_id -> TimingData
    labor_models: dict       # step_id -> 'off'|'pool'|'named'
    step_wc: dict            # step_id -> (wc_id, wc_name)
    osp_steps: set           # outside-process steps: vendor time, not our capacity
    wc_machine_hours: dict   # wc_id -> (lights_out_count, attended_count)
    crew_size: int
    wc_names: dict           # wc_id -> name


def _load_reference(tenant) -> _RefData:
    from Tracker.models import Steps, WorkCenter

    timings = sched_data.get_step_timings(tenant)
    labor_models = sched_data.get_step_labor_models(tenant)
    crew_size = len(sched_data.get_dispatchable_operators(tenant))
    attended_only = sched_data.get_attended_only_machines(tenant)

    step_wc: dict = {}
    osp_steps: set = set()
    for s in Steps.objects.filter(tenant=tenant, is_current_version=True).values(
            'id', 'work_center_id', 'work_center__name', 'is_outside_process'):
        if s['work_center_id']:
            step_wc[s['id']] = (s['work_center_id'], s['work_center__name'])
        if s['is_outside_process']:
            osp_steps.add(s['id'])

    # Per work center: split its schedulable equipment into lights-out vs attended
    # so machine capacity uses calendar vs shift hours correctly.
    wc_machine_hours: dict = {}
    wc_names: dict = {}
    for wc in WorkCenter.objects.filter(tenant=tenant, is_current_version=True).prefetch_related('equipment'):
        wc_names[wc.id] = wc.name
        lights_out = attended = 0
        for eq in wc.equipment.all():
            if not getattr(eq, 'is_schedulable', False):
                continue
            if eq.id in attended_only:
                attended += 1
            else:
                lights_out += 1
        wc_machine_hours[wc.id] = (lights_out, attended)
    return _RefData(timings, labor_models, step_wc, osp_steps, wc_machine_hours, crew_size, wc_names)


def _step_hours(ref: _RefData, step_id, quantity: int) -> float:
    """Work content of one step for `quantity` pieces: setup once + cycle per piece.
    Rough-cut deliberately ignores machine overrides / batching / PFD — the detailed
    scheduler owns that fidelity. Outside-process steps are vendor time, not our
    capacity → 0."""
    if step_id in ref.osp_steps:
        return 0.0
    t = ref.timings.get(step_id)
    if t is None:
        return 0.0
    cycle = t.cycle_time_minutes or 0.0
    setup = t.setup_minutes or 0.0
    if cycle <= 0 and setup <= 0:
        return 0.0
    return (setup + cycle * quantity) / 60.0


# --- load accumulation -----------------------------------------------------

def _route_counts(wo) -> dict:
    """step_id -> number of units whose REMAINING nominal route passes through it.
    Uses the same `resolve_route` as the solver: from each unit's current step,
    following default edges only (no conditional rework branch), stopping before
    terminal states — so a finished-state dwell time can't masquerade as work, and
    completed operations are netted out."""
    from Tracker.services.scheduling.routing import resolve_route

    counts: dict = {}
    for unit in list(wo.parts) + list(wo.cores):
        if unit.current_step_id is None:
            continue
        route_ids, _ = resolve_route(unit.current_step_id, wo.steps, wo.edges)
        for sid in route_ids:
            counts[sid] = counts.get(sid, 0) + 1
    return counts


def _route_hours(ref, counts: dict) -> tuple[float, dict]:
    """A route's work content: (labor_hours, {wc_id: machine_hours})."""
    labor = 0.0
    by_wc: dict = {}
    for step_id, qty in counts.items():
        hrs = _step_hours(ref, step_id, qty)
        if hrs <= 0:
            continue
        wc = ref.step_wc.get(step_id)
        if wc:
            by_wc[wc[0]] = by_wc.get(wc[0], 0.0) + hrs
        if ref.labor_models.get(step_id, 'pool') != 'off':
            labor += hrs
    return labor, by_wc


def _add_spread_load(labor_hrs, wc_hrs: dict, lo, hi, n_buckets, wc_load, labor_load):
    """Spread hours evenly over buckets lo..hi inclusive (clipped to the horizon).
    An order's work doesn't all land in its due month — it accrues over the run-up.
    Point-loading into the due bucket asked 'can it ALL happen in one month?', which
    made any sizeable order read as impossible."""
    if lo is None and hi is None:
        return
    lo = 0 if lo is None else max(0, lo)
    hi = (n_buckets - 1) if hi is None else min(n_buckets - 1, hi)
    if hi < lo:
        lo, hi = hi, lo
    span = hi - lo + 1
    for i in range(lo, hi + 1):
        labor_load[i] += labor_hrs / span
        for wc_id, h in wc_hrs.items():
            wc_load[wc_id][i] += h / span


def build_capacity_load(tenant, months: int = 24) -> dict:
    """Capacity vs load per (resource, monthly bucket) over `months`.

    Returns a JSON-friendly dict: buckets[], labor[], and work_centers[] each with
    per-bucket capacity/load/util."""
    import collections

    ref = _load_reference(tenant)
    start = timezone.now()
    buckets = _month_buckets(tenant, start, months)
    n = len(buckets)

    labor_load = [0.0] * n
    wc_load: dict = collections.defaultdict(lambda: [0.0] * n)

    for wo in sched_data.get_active_workorders(tenant):
        labor_h, wc_h = _route_hours(ref, _route_counts(wo))
        lo = _bucket_index(buckets, wo.expected_start or start)
        hi = _bucket_index(buckets, wo.expected_completion or start)
        _add_spread_load(labor_h, wc_h, lo, hi, n, wc_load, labor_load)

    def _labor_cap(b: Bucket) -> float:
        return ref.crew_size * b.working_hours

    def _wc_cap(wc_id, b: Bucket) -> float:
        lights_out, attended = ref.wc_machine_hours.get(wc_id, (0, 0))
        return lights_out * b.calendar_hours + attended * b.working_hours

    def _series(cap_fn, load):
        rows = []
        for i, b in enumerate(buckets):
            cap = cap_fn(b)
            ld = load[i]
            rows.append({'bucket': b.label, 'capacity_hours': round(cap, 1),
                         'load_hours': round(ld, 1),
                         'utilization': round(ld / cap, 3) if cap > 0 else None})
        return rows

    return {
        'buckets': [b.label for b in buckets],
        'labor': {'name': 'Labor (dispatchable crew)', 'crew_size': ref.crew_size,
                  'series': _series(_labor_cap, labor_load)},
        # Every work center with capacity OR load — an IDLE center must still appear,
        # since "where do we have room?" is half the question this view answers.
        'work_centers': [
            {'id': str(wc_id), 'name': ref.wc_names.get(wc_id, str(wc_id)),
             'series': _series(lambda b, w=wc_id: _wc_cap(w, b),
                               wc_load.get(wc_id) or [0.0] * n)}
            for wc_id in sorted(set(ref.wc_names) | set(wc_load),
                                key=lambda k: ref.wc_names.get(k, str(k)))
        ],
    }


# --- capable-to-promise ----------------------------------------------------

def capable_to_promise(tenant, part_type_id, quantity: int, target_date: date,
                       months: int = 24) -> dict:
    """Can we take `quantity` of `part_type_id` due `target_date`? Explode its routing,
    add to the existing load, and check whether any resource in the target bucket
    crosses capacity. Returns feasibility + the binding resource + earliest-fit bucket."""
    from Tracker.models import Processes
    import collections

    ref = _load_reference(tenant)
    start = timezone.now()
    buckets = _month_buckets(tenant, start, months)
    n = len(buckets)

    # existing committed load
    labor_load = [0.0] * n
    wc_load: dict = collections.defaultdict(lambda: [0.0] * n)
    for wo in sched_data.get_active_workorders(tenant):
        labor_h, wc_h = _route_hours(ref, _route_counts(wo))
        lo = _bucket_index(buckets, wo.expected_start or start)
        hi = _bucket_index(buckets, wo.expected_completion or start)
        _add_spread_load(labor_h, wc_h, lo, hi, n, wc_load, labor_load)

    # candidate routing: the part type's current process, walked from its head along
    # DEFAULT edges (same resolver as the solver — no rework branch, no terminal state)
    proc = Processes.objects.filter(tenant=tenant, part_type_id=part_type_id).order_by('-created_at').first()
    if proc is None:
        return {'feasible': False, 'reason': 'No process/routing defined for that part type.'}
    from Tracker.services.scheduling.manual_move import _process_graph
    from Tracker.services.scheduling.routing import resolve_route
    nodes, edges = _process_graph(proc.id)
    if not nodes:
        return {'feasible': False, 'reason': 'The part type has a process but no routing steps.'}
    head = min(nodes, key=lambda nd: nd.order).step_id
    cand_steps, _ = resolve_route(head, nodes, edges)
    if not cand_steps:
        return {'feasible': False, 'reason': 'The routing has no schedulable (non-terminal) steps.'}

    # Candidate work content, once.
    cand_labor = sum(_step_hours(ref, s, quantity) for s in cand_steps
                     if ref.labor_models.get(s, 'pool') != 'off')
    cand_wc: dict = collections.defaultdict(float)
    for s in cand_steps:
        wc = ref.step_wc.get(s)
        if wc:
            cand_wc[wc[0]] += _step_hours(ref, s, quantity)

    def _fits(upto: int) -> tuple[bool, list]:
        """Can the whole order be absorbed by the free capacity between now and bucket
        `upto` (inclusive)? CUMULATIVE, not per-bucket: an order due in March may use
        every free hour between now and March — asking whether it fits in the due month
        alone would reject any order bigger than one month of capacity."""
        binding = []
        if cand_labor > 0:
            free = sum(max(0.0, ref.crew_size * buckets[i].working_hours - labor_load[i])
                       for i in range(upto + 1))
            if cand_labor > free:
                binding.append({'resource': 'Labor', 'need': round(cand_labor, 1),
                                'free_through_target': round(free, 1)})
        for wc_id, need in cand_wc.items():
            if need <= 0:
                continue
            lights_out, attended = ref.wc_machine_hours.get(wc_id, (0, 0))
            free = sum(
                max(0.0, lights_out * buckets[i].calendar_hours
                    + attended * buckets[i].working_hours - wc_load[wc_id][i])
                for i in range(upto + 1))
            if need > free:
                binding.append({'resource': ref.wc_names.get(wc_id, str(wc_id)),
                                'need': round(need, 1), 'free_through_target': round(free, 1)})
        # Worst shortfall first. An order that badly overruns the shop trips EVERY
        # resource, and an unordered list of seven buries the actual constraint — the
        # one a planner would add a shift or subcontract to relieve.
        binding.sort(key=lambda b: -(b['need'] / b['free_through_target']
                                     if b['free_through_target'] > 0 else float('inf')))
        return (not binding, binding)

    tgt = _bucket_index(buckets, target_date)
    if tgt is None:
        return {'feasible': False, 'reason': 'Target date is outside the planning horizon.'}

    fits, binding = _fits(tgt)
    # Earliest fit: cumulative free capacity only grows with time, so scan forward for
    # the first bucket whose running total absorbs the order.
    earliest = next((buckets[i].label for i in range(tgt, n) if _fits(i)[0]), None)

    return {
        'feasible': fits,
        'target_bucket': buckets[tgt].label,
        'binding_resources': binding,
        'earliest_feasible_bucket': earliest,
        'quantity': quantity,
        # Zero-hour resources (e.g. an outside-process step — vendor time, not ours)
        # are omitted rather than listed as 0.
        'work_content_hours': {'labor': round(cand_labor, 1),
                               **{ref.wc_names.get(k, str(k)): round(v, 1)
                                  for k, v in sorted(cand_wc.items()) if v > 0}},
    }
