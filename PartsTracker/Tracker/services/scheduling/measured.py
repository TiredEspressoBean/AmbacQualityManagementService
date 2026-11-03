"""Measured step timings — what the step records say each aspect of a step takes.

Step times are dynamic (lot size, crew, the job), so a measurement is made per ASPECT,
the same aspects a planner authors on `StepTiming`:

  - **Setup and per piece.** A *run* is one work order's first-pass work at the step:
    the merged worked time of its parts' executions there (merged, never summed — a
    lock-step lot puts N executions on the same minutes), against how many parts it
    covered. Across runs of different lot sizes, a least-squares line
    `duration ≈ setup + pieces × per_piece` separates the two. The fit is only made
    when there are enough runs (`FIT_MIN_RUNS`) over enough different lot sizes
    (`FIT_MIN_SIZES`, the largest at least `FIT_MIN_SPREAD`× the smallest), and only
    kept when it gives a positive per-piece time and a setup of zero or more. Otherwise
    the measurement is the plain average per piece (total time / total pieces), with
    `note` saying why setup could not be separated.
  - **Cycle per load** for a batch step (one with a BATCH-scope substep: a wash, an
    oven, a bar-fed lathe batching out): from `BatchExecution`, sealed (the machine
    starts its unattended run) to completed (the run finished and its completion
    checks done), per completed load. Beside it, the **load time** per load —
    started to sealed, the attended loading. A batch step is measured per load only,
    never per piece, since a load's cycle doesn't grow with the parts in it.
  - Cycle vs load/unload, external setup and attention are not separable from the
    records, so they stay authored only.

Worked time is counted the way Operator Hours counts it (services/mes/labor_report):
an execution stops at its operator's next clock-out, and time the work order sat on
hold or the part was out for outside processing is left out. Rework is excluded —
re-visits (visit_number > 1) and REWORK steps — since it is not the step's standard.
Only the last `LOOKBACK_DAYS` count, so a measurement follows the step as it is run now.

Nothing here is applied to the authored timing. The scheduler's fallback chain reads a
measurement where the authored aspect is unset (data.get_step_timings); a planner
copies one into the timing by hand ("Use measured"), as an ordinary edit.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

MIN_RUNS = 5
FIT_MIN_RUNS = 8
FIT_MIN_SIZES = 3
FIT_MIN_SPREAD = 2.0
LOOKBACK_DAYS = 365


@dataclass(frozen=True)
class MeasuredTiming:
    """One step's measured aspects. A value is None when there isn't enough history
    for it; `runs` / `loads` say how much there is either way."""
    step_id: UUID
    runs: int
    pieces: int
    per_piece_minutes: float | None
    setup_minutes: float | None  # only when the fit separated it
    method: str  # 'fit' | 'average' | 'batch' | 'none'
    note: str
    loads: int
    cycle_per_load_minutes: float | None
    load_per_load_minutes: float | None = None  # attended loading, started -> sealed


def measure_step_timings(tenant, step_ids=None) -> dict[UUID, MeasuredTiming]:
    """{step_id: MeasuredTiming} for every step with any measured history (or every
    step in `step_ids`, when given, history or not)."""
    from django.utils import timezone
    from Tracker.models import Substep, SubstepScope

    now = timezone.now()
    since = now - timedelta(days=LOOKBACK_DAYS)
    runs = _runs(tenant, since, now, step_ids)
    loads = _loads(tenant, since, now, step_ids)
    batch_qs = Substep.objects.filter(tenant=tenant, scope=SubstepScope.BATCH)
    if step_ids is not None:
        batch_qs = batch_qs.filter(step_id__in=step_ids)
    batch_steps = set(batch_qs.values_list('step_id', flat=True)) | set(loads)
    ids = set(step_ids) if step_ids is not None else set(runs) | set(loads)
    return {sid: _measure(sid, runs.get(sid, []), loads.get(sid, []), sid in batch_steps)
            for sid in ids}


def _measure(step_id, runs, loads, is_batch=False) -> MeasuredTiming:
    pieces = sum(n for n, _ in runs)
    per_piece = setup = None
    method, note = 'none', ''
    if is_batch:
        method = 'batch'
        if len(loads) < MIN_RUNS:
            note = (f"A batch step is measured per load: only {len(loads)} completed "
                    f"load{'s' if len(loads) != 1 else ''} recorded; {MIN_RUNS} needed.")
    elif len(runs) < MIN_RUNS:
        note = f"Only {len(runs)} run{'s' if len(runs) != 1 else ''} recorded; {MIN_RUNS} needed."
    else:
        fit, note = _fit(runs)
        if fit:
            setup, per_piece = fit
            method = 'fit'
        elif pieces:
            per_piece = sum(d for _, d in runs) / pieces
            method = 'average'
    cycle = load = None
    if len(loads) >= MIN_RUNS:
        cycle = sum(c for c, _ in loads) / len(loads)
        load = sum(ld for _, ld in loads) / len(loads)
    return MeasuredTiming(
        step_id=step_id, runs=len(runs), pieces=pieces,
        per_piece_minutes=_round(per_piece), setup_minutes=_round(setup),
        method=method, note=note,
        loads=len(loads), cycle_per_load_minutes=_round(cycle),
        load_per_load_minutes=_round(load),
    )


def _fit(runs):
    """((setup, per_piece), '') from a least-squares line through (pieces, minutes),
    or (None, why not)."""
    sizes = {n for n, _ in runs}
    if len(runs) < FIT_MIN_RUNS:
        return None, (f"Setup not separated: {FIT_MIN_RUNS} runs needed to fit it, "
                      f"{len(runs)} recorded. Shown as the average per piece.")
    if len(sizes) < FIT_MIN_SIZES or max(sizes) < FIT_MIN_SPREAD * min(sizes):
        return None, ("Setup not separated: the lot sizes are too alike to tell setup "
                      "from per-piece time. Shown as the average per piece.")
    k = len(runs)
    mean_n = sum(n for n, _ in runs) / k
    mean_d = sum(d for _, d in runs) / k
    sxx = sum((n - mean_n) ** 2 for n, _ in runs)
    sxy = sum((n - mean_n) * (d - mean_d) for n, d in runs)
    slope = sxy / sxx
    intercept = mean_d - slope * mean_n
    if slope <= 0 or intercept < 0:
        return None, ("Setup not separated: run times don't grow with lot size in a "
                      "way that splits into setup + per piece. Shown as the average per piece.")
    return (intercept, slope), ''


def _round(v):
    return None if v is None else round(v, 2)


def _runs(tenant, since, now, step_ids) -> dict:
    """{step_id: [(pieces, worked_minutes), ...]}, one entry per work order's
    first-pass work at the step."""
    from Tracker.models import StepExecution, WorkOrderHold
    from Tracker.services.mes.labor_report import (
        _NOT_WORK, _clock_outs, _merge, _subtract, _total,
    )

    qs = (StepExecution.objects
          .filter(tenant=tenant, archived=False, started_at__gte=since,
                  exited_at__isnull=False, part__work_order__isnull=False)
          .exclude(status__in=_NOT_WORK)
          .exclude(visit_number__gt=1)
          .exclude(step__step_type='REWORK'))
    if step_ids is not None:
        qs = qs.filter(step_id__in=step_ids)
    rows = list(qs.values(
        'step_id', 'part__work_order_id', 'started_at', 'exited_at',
        'assigned_to_id', 'completed_by_id',
        'outside_process_shipment__shipped_at', 'outside_process_shipment__returned_at',
    ))
    if not rows:
        return {}

    uids = {r['assigned_to_id'] or r['completed_by_id'] for r in rows} - {None}
    clock_outs = _clock_outs(tenant, min(r['started_at'] for r in rows), now, uids)
    holds = defaultdict(list)
    for h in (WorkOrderHold.objects
              .filter(tenant=tenant, is_voided=False,
                      work_order_id__in={r['part__work_order_id'] for r in rows})
              .values('work_order_id', 'placed_at', 'cleared_at')):
        holds[h['work_order_id']].append((h['placed_at'], h['cleared_at'] or now))

    worked = defaultdict(list)   # (step, wo) → intervals
    pieces = defaultdict(int)
    for r in rows:
        s, e = r['started_at'], r['exited_at']
        outs = clock_outs.get(r['assigned_to_id'] or r['completed_by_id'], [])
        i = bisect_right(outs, s)
        if i < len(outs):
            e = min(e, outs[i])  # stops at the operator's next clock-out
        if e <= s:
            continue
        cuts = list(holds.get(r['part__work_order_id'], []))
        if r['outside_process_shipment__shipped_at']:
            cuts.append((r['outside_process_shipment__shipped_at'],
                         r['outside_process_shipment__returned_at'] or now))
        key = (r['step_id'], r['part__work_order_id'])
        worked[key].extend(_subtract([(s, e)], cuts))
        pieces[key] += 1

    out = defaultdict(list)
    for (step_id, _wo), intervals in worked.items():
        minutes = _total(_merge(intervals)) / 60.0
        if minutes > 0:
            out[step_id].append((pieces[(step_id, _wo)], minutes))
    return out


def _loads(tenant, since, now, step_ids) -> dict:
    """{step_id: [(cycle_minutes, load_minutes), ...]}, one per completed batch load:
    the cycle sealed -> completed (the unattended run), the load started -> sealed
    (the attended loading), each less any hold on its work order."""
    from Tracker.models import BatchExecution, WorkOrderHold
    from Tracker.services.mes.labor_report import _subtract, _total

    qs = BatchExecution.objects.filter(tenant=tenant, archived=False, started_at__gte=since,
                                       sealed_at__isnull=False, completed_at__isnull=False)
    if step_ids is not None:
        qs = qs.filter(step_id__in=step_ids)
    rows = list(qs.values('step_id', 'work_order_id', 'started_at', 'sealed_at', 'completed_at'))
    if not rows:
        return {}
    holds = defaultdict(list)
    for h in (WorkOrderHold.objects
              .filter(tenant=tenant, is_voided=False,
                      work_order_id__in={r['work_order_id'] for r in rows})
              .values('work_order_id', 'placed_at', 'cleared_at')):
        holds[h['work_order_id']].append((h['placed_at'], h['cleared_at'] or now))
    out = defaultdict(list)
    for r in rows:
        cuts = holds.get(r['work_order_id'], [])
        cycle = _total(_subtract([(r['sealed_at'], r['completed_at'])], cuts)) / 60.0
        load = _total(_subtract([(r['started_at'], r['sealed_at'])], cuts)) / 60.0
        if cycle > 0:
            out[r['step_id']].append((cycle, load))
    return out


@dataclass(frozen=True)
class StepTimingComparison:
    """A step's authored and measured aspects side by side, with what the scheduler
    uses for each (`*_in_use`: 'authored' | 'measured' | 'expected' | 'none') and
    whether an authored value has drifted from its measurement."""
    step_id: UUID
    step_name: str
    measured: MeasuredTiming
    setup_in_use: str
    cycle_in_use: str
    setup_drift: bool
    cycle_drift: bool
    drift_pct: int


def compare_step_timings(tenant, step_ids=None) -> list[StepTimingComparison]:
    """One row per current step that has an authored timing or any measured history
    (narrowed to `step_ids` when given)."""
    from Tracker.models import OptimizationConfig, Steps, StepTiming
    from Tracker.services.scheduling.data import get_step_timings

    measured = measure_step_timings(tenant)
    resolved = get_step_timings(tenant, measured=measured)
    authored = {t.step_id: t for t in StepTiming.objects.filter(tenant=tenant, archived=False)}
    cfg = OptimizationConfig.objects.filter(tenant=tenant).only('timing_drift_pct').first()
    pct = cfg.timing_drift_pct if cfg else 25
    names = dict(Steps.objects.filter(tenant=tenant, is_current_version=True)
                 .values_list('id', 'name'))
    wanted = set(step_ids) if step_ids is not None else set(authored) | set(measured)

    def drifted(authored_v, measured_v):
        return bool(pct and authored_v and measured_v is not None
                    and abs(measured_v - authored_v) * 100 > pct * authored_v)

    in_use = {'timing': 'authored', 'measured': 'measured', 'expected': 'expected', 'none': 'none'}
    rows = []
    for sid in wanted:
        if sid not in names:
            continue  # an old version: the scheduler only plans current steps
        m = measured.get(sid) or _measure(sid, [], [])
        t, r = authored.get(sid), resolved.get(sid)
        cycle_m = m.cycle_per_load_minutes if m.cycle_per_load_minutes is not None else m.per_piece_minutes
        rows.append(StepTimingComparison(
            step_id=sid, step_name=names[sid], measured=m,
            setup_in_use=in_use[r.setup_source] if r else 'none',
            cycle_in_use=in_use[r.cycle_source] if r else 'none',
            setup_drift=drifted(t.setup_minutes if t else 0, m.setup_minutes),
            cycle_drift=drifted(t.cycle_time_minutes if t else 0, cycle_m),
            drift_pct=pct,
        ))
    return sorted(rows, key=lambda c: c.step_name.lower())
