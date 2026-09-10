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
from Tracker.services.planning.material_load import material_series


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
    for wo in sched_data.get_active_workorders(tenant, within_horizon=False):
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
    osp_days: dict           # step_id -> planned vendor turnaround, CALENDAR days
    flow: dict               # wc_id -> {queue_hours, move_hours, samples}; absent = unmeasured
    wc_machine_hours: dict   # wc_id -> (lights_out_count, attended_count)
    crew_size: int
    wc_names: dict           # wc_id -> name
    wc_critical: set         # wc_ids a planner flagged worth watching (presentation only)


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
    wc_critical: set = set()
    for wc in WorkCenter.objects.filter(tenant=tenant, is_current_version=True).prefetch_related('equipment'):
        wc_names[wc.id] = wc.name
        if wc.is_critical:
            wc_critical.add(wc.id)
        lights_out = attended = 0
        for eq in wc.equipment.all():
            if not getattr(eq, 'is_schedulable', False):
                continue
            if eq.id in attended_only:
                attended += 1
            else:
                lights_out += 1
        wc_machine_hours[wc.id] = (lights_out, attended)
    # Vendor turnaround, resolved by the same four-tier chain the solver uses. It costs
    # no capacity but consumes calendar time, which is exactly what a back-scheduled
    # start date has to account for.
    from Tracker.models import OptimizationConfig
    # tenant-safe: explicit tenant filter
    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    osp_days = sched_data.get_outside_process_step_days(tenant, cfg)

    # Measured queue/move per work centre. Absent for a resource with too little
    # history — an unmeasured centre contributes nothing rather than a guessed constant,
    # so the estimate is short but never invented.
    from Tracker.services.planning.flow_times import measure_flow_times
    flow = measure_flow_times(tenant)

    return _RefData(timings, labor_models, step_wc, osp_steps, osp_days, flow,
                    wc_machine_hours, crew_size, wc_names, wc_critical)


def _step_hours(ref: _RefData, step_id, quantity: int) -> tuple[float, float]:
    """`(machine_hours, labor_hours)` for one step at `quantity` pieces.

    These are NOT the same number and used to be treated as one. A machine-tended step
    occupies the machine for setup + cycle × qty, but the operator only for setup + a
    touch per piece — they load it, press start and walk away. Charging the full machine
    run to the labor pool overstates the resource the module docstring calls the usual
    binding constraint, which is the one most likely to turn a CTP answer into a "no".

    The split is not a new policy: `TimingData.operator_attended_time` already implements
    it for the solver, keyed on `attention_type` (full / load_unload / unattended). RCCP
    simply hand-rolled `machine_wall_time` inline and reused it for both lanes.

    Rough-cut still ignores machine overrides / batching / PFD — the detailed scheduler
    owns that fidelity. Outside-process steps are vendor time, not our capacity → (0, 0);
    their ELAPSED calendar time is a lead-time concern, not a capacity one.
    """
    if step_id in ref.osp_steps:
        return 0.0, 0.0
    t = ref.timings.get(step_id)
    if t is None:
        return 0.0, 0.0
    return (t.machine_wall_time(quantity) / 60.0,
            t.operator_attended_time(quantity) / 60.0)


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
        machine_h, labor_h = _step_hours(ref, step_id, qty)
        if machine_h <= 0 and labor_h <= 0:
            continue
        wc = ref.step_wc.get(step_id)
        if wc and machine_h > 0:
            by_wc[wc[0]] = by_wc.get(wc[0], 0.0) + machine_h
        # `labor_model=off` drops the crew constraint entirely; attention_type then
        # governs how much of the run occupies an operator when it doesn't.
        if ref.labor_models.get(step_id, 'pool') != 'off':
            labor += labor_h
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


def _bucket_capacity(ref, bucket: Bucket, wc_id=None) -> float:
    """Hours a resource offers in one bucket. `wc_id=None` means the labor pool."""
    if wc_id is None:
        return ref.crew_size * bucket.working_hours
    lights_out, attended = ref.wc_machine_hours.get(wc_id, (0, 0))
    return lights_out * bucket.calendar_hours + attended * bucket.working_hours


def _lead_days(due: Bucket, ref, labor_hrs: float, wc_hrs: dict, counts: dict) -> float:
    """Elapsed days an order needs between release and its due date.

        work content / daily rate      the hours, at the resource that takes longest
      + vendor turnaround              calendar days, zero capacity
      + measured queue and move        per operation on the route

    Only the first term is work; the other two are waiting, and in a job shop the
    waiting is most of it. Sizing a release date on work content alone is the mistake
    this replaces — it says "start later" than is safe, which is the wrong direction to
    be wrong in for a surface whose job is preventing surprises.

    Every quantity-dependent term is computed (`_step_hours` already scales setup once
    plus cycle per piece); everything stored is quantity-independent. That is what makes
    the answer differ correctly between one unit and ten thousand — the reason a
    lead-time constant per part or per process cannot work.
    """
    import math

    days_in = max(1, (due.end - due.start).days)

    # Work content -> elapsed days at each resource's average daily rate. Worst resource
    # sets the pace; a zero-capacity resource can only mean "not inside this bucket".
    work_days = 0.0
    if labor_hrs > 0:
        rate = _bucket_capacity(ref, due) / days_in
        work_days = max(work_days, labor_hrs / rate if rate > 0 else days_in)
    for wc_id, hrs in wc_hrs.items():
        if hrs <= 0:
            continue
        rate = _bucket_capacity(ref, due, wc_id) / days_in
        work_days = max(work_days, hrs / rate if rate > 0 else days_in)

    # Vendor trips: `_step_hours` returns (0, 0) for an outside-process step, so this is
    # the only place the plating trip exists at all.
    osp_days = sum(ref.osp_days.get(sid, 0) for sid in (counts or {}))

    # Measured waiting. An unmeasured work centre contributes 0 — the estimate stays
    # short rather than becoming invented.
    wait_hours = 0.0
    for sid in (counts or {}):
        wc = ref.step_wc.get(sid)
        f = ref.flow.get(wc[0]) if wc else None
        if f:
            wait_hours += f['queue_hours'] + f['move_hours']

    return work_days + osp_days + wait_hours / 24.0


def _load_span(buckets, wo, ref, labor_hrs: float, wc_hrs: dict, now,
               counts: dict | None = None) -> tuple:
    """`(lo, hi, planned_start)` — the buckets an order occupies, and the DATE it must
    release to hit its due date.

    Placement matters as much as the hours. Spreading every undated order from TODAY to
    its due date puts a slice of a job due next year into next month, so near buckets
    read busy with work nobody will touch and the far view flattens into "uniformly
    loaded forever" — worst exactly when start dates are sparse, which is when this layer
    is most relied on.

    In order of what is actually known:

      1. `expected_start` set  — authoritative; a planner said when it releases.
      2. Work already started  — an OPEN StepExecution means hours are burning now,
                                 whatever the due date says.
      3. Otherwise             — back-schedule from the due date by `_lead_days`.

    `planned_start` is a date rather than a bucket label because a bucket is not
    actionable: "2027-03" cannot be put on a release list, and bucket placement falls out
    of the date for free. One derivation, two uses.

    Too little runway (needs three months, due in three weeks) clamps at today and the
    buckets read over capacity, which is the honest answer rather than a rounding of it.
    """
    import math

    today = now.date() if hasattr(now, 'date') else now
    hi = _bucket_index(buckets, wo.expected_completion or now)

    if wo.expected_start is not None:
        return _bucket_index(buckets, wo.expected_start), hi, wo.expected_start

    now_idx = _bucket_index(buckets, now)
    started = any(getattr(p, 'in_progress', False) for p in wo.parts)
    if started or hi is None:
        return now_idx, hi, today

    lead = _lead_days(buckets[hi], ref, labor_hrs, wc_hrs, counts or {})
    due_date = wo.expected_completion or today
    planned_start = due_date - timedelta(days=int(math.ceil(lead)))

    lo = _bucket_index(buckets, planned_start)
    if lo is None:
        # Before the horizon opens: it should already be running.
        lo = 0 if planned_start < buckets[0].start.date() else hi
    lo = max(0 if now_idx is None else now_idx, lo)
    return lo, hi, planned_start


def build_capacity_load(tenant, months: int = 24, critical_only: bool = False) -> dict:
    """Capacity vs load per (resource, monthly bucket) over `months`.

    Returns a JSON-friendly dict: buckets[], labor[], and work_centers[] each with
    per-bucket capacity/load/util.

    `critical_only` narrows the work-centre lane to the centres a planner flagged
    `is_critical`. Textbook RCCP is *defined* over critical resources only, and a shop
    with forty centres has a handful whose load anyone can act on — the rest are
    scenery a planner scrolls past. It filters the OUTPUT and nothing else: every
    centre still accrues load, the labor and material lanes are untouched, and the
    numbers on a filtered row are identical to the numbers on the same row unfiltered.
    Making it change the arithmetic would mean two views that disagree."""

    import collections

    ref = _load_reference(tenant)
    start = timezone.now()
    buckets = _month_buckets(tenant, start, months)
    n = len(buckets)

    labor_load = [0.0] * n
    wc_load: dict = collections.defaultdict(lambda: [0.0] * n)
    releases: list = []
    untimed_orders: list = []
    wo_starts: dict = {}   # wo_id -> bucket its work begins in (for the material lane)

    # `WorkOrderData` carries only what the solver needs and `released_at` isn't on it,
    # so read it once here rather than widening the DTO for one consumer.
    from Tracker.models import WorkOrder
    # tenant-safe: explicit tenant filter
    released_ids = set(
        WorkOrder.objects.filter(tenant=tenant, released_at__isnull=False)
        .values_list('id', flat=True))

    today = start.date()
    for wo in sched_data.get_active_workorders(tenant, within_horizon=False):
        counts = _route_counts(wo)
        labor_h, wc_h = _route_hours(ref, counts)
        lo, hi, planned_start = _load_span(buckets, wo, ref, labor_h, wc_h, start, counts)
        _add_spread_load(labor_h, wc_h, lo, hi, n, wc_load, labor_load)
        wo_starts[wo.wo_id] = lo

        # An operation nobody has timed contributes zero hours and zero lead days, so it
        # reads as FREE rather than as unknown — the order shows a confident utilisation
        # and a release date that assumes the work takes no time. `cycle_source` already
        # distinguishes "measured as zero" from "never measured"; without surfacing it
        # the page reports both identically.
        untimed = [sid for sid in counts
                   if getattr(ref.timings.get(sid), 'cycle_source', 'none') == 'none']
        if untimed:
            untimed_orders.append({'erp_id': wo.erp_id, 'step_count': len(untimed)})

        # The actionable half. A heatmap says WHERE it is tight; this says what to do
        # about it. Only work whose release is genuinely still ahead of us or already
        # overdue — an order that started is not a release decision any more.
        if planned_start and not any(getattr(p, 'in_progress', False) for p in wo.parts):
            releases.append({
                'work_order_id': str(wo.wo_id),
                'erp_id': wo.erp_id,
                'planned_start': planned_start,
                'due_date': wo.expected_completion,
                # Its release date has passed and nothing has started: it is late before
                # it begins, which is the one thing on this page worth acting on today.
                'overdue': planned_start < today,
                'is_estimate': wo.expected_start is None,
                # Already authorised: the row is then informational, not a decision.
                'released': wo.wo_id in released_ids,
            })
    releases.sort(key=lambda r: (r['planned_start'], r['erp_id']))

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
             'is_critical': wc_id in ref.wc_critical,
             'series': _series(lambda b, w=wc_id: _wc_cap(w, b),
                               wc_load.get(wc_id) or [0.0] * n)}
            for wc_id in sorted(set(ref.wc_names) | set(wc_load),
                                key=lambda k: ref.wc_names.get(k, str(k)))
            if not critical_only or wc_id in ref.wc_critical
        ],
        # How many centres exist at all, so a filtered view can say what it is hiding
        # instead of looking like a shop with two work centres.
        'work_center_total': len(set(ref.wc_names) | set(wc_load)),
        'critical_only': critical_only,
        # Back-scheduled release dates: what has to START, and what is already late to.
        # `is_estimate` distinguishes a derived date from one a planner actually set —
        # RCCP suggests, it never writes `expected_start` (that would make the next run
        # read back its own guess as authoritative and stop re-evaluating).
        'planned_releases': releases,
        # Orders whose routing contains an operation with no timing at all (no authored
        # cycle, no usable history, no expected_duration). Their hours and their release
        # dates are understated, so the numbers above are a floor, not an estimate.
        'untimed_orders': sorted(untimed_orders, key=lambda u: u['erp_id']),
        # The third lane. Placed at each order's planned START — material is consumed
        # while the job runs, so a January release for an April ship needs its parts in
        # January. Reuses `wo_starts` from the capacity pass so the two lanes cannot
        # disagree about when a job runs.
        'materials': material_series(tenant, buckets, wo_starts),
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
    for wo in sched_data.get_active_workorders(tenant, within_horizon=False):
        counts = _route_counts(wo)
        labor_h, wc_h = _route_hours(ref, counts)
        lo, hi, _ = _load_span(buckets, wo, ref, labor_h, wc_h, start, counts)
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

    # Candidate work content, once. Same machine/labor split as committed load — a quote
    # measured differently from the load it is quoted against is not a comparison.
    cand_labor = 0.0
    cand_wc: dict = collections.defaultdict(float)
    for s in cand_steps:
        machine_h, labor_h = _step_hours(ref, s, quantity)
        if ref.labor_models.get(s, 'pool') != 'off':
            cand_labor += labor_h
        wc = ref.step_wc.get(s)
        if wc and machine_h > 0:
            cand_wc[wc[0]] += machine_h

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
