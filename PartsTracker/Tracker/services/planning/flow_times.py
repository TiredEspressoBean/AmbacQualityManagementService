"""Measured flow times — how long work actually waits, per work centre.

`StepTiming` says how long an operation *occupies* a resource. It says nothing about
how long the part *sits there*, and in a job shop the waiting dominates: queue is
routinely most of manufacturing lead time, run time a minority of it. Any date derived
from work content alone is therefore optimistic, and optimistic in the dangerous
direction — it tells a planner to release later than is safe.

The gap is measurable rather than guessable. `StepExecution` carries three timestamps:

    entered_at   part arrives at the step
    started_at   work actually begins        -> queue  = started_at - entered_at
    exited_at    part leaves                 -> move   = next.entered_at - prev.exited_at

which is exactly the interoperation decomposition (wait + queue + move) that MRP
systems ask you to type in by hand.

Deliberately measured, never configured. A stored per-operation queue constant inflates
short jobs (twelve operations of one day each on a three-hour job) and drives lead-time
syndrome: padded lead times release orders earlier, which raises WIP, which lengthens
queues, which appears to justify the padding. An observation cannot confirm itself that
way.

Aggregated per WORK CENTRE, not per step: queue is a property of the resource. The same
operation behind a busy machine and an idle one waits very differently.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

DEFAULT_LOOKBACK_DAYS = 90

# Planning to the MEDIAN queue means being late half the time, which is not a plan.
# The 75th percentile buys a reasonable service level without chasing the tail — a
# queue distribution is right-skewed, so the mean is dragged around by a handful of
# jobs that sat for a month and is worse than either.
DEFAULT_PERCENTILE = 0.75

# Below this many observations a work centre's number is noise. Callers get `None` and
# decide what to do rather than being handed a confident figure built on two samples.
MIN_SAMPLES = 5


def _percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile. No numpy, and it behaves on tiny samples."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round(p * (len(ordered) - 1)))))
    return ordered[idx]


def measure_flow_times(tenant, lookback_days: int = DEFAULT_LOOKBACK_DAYS,
                       percentile: float = DEFAULT_PERCENTILE) -> dict:
    """`{work_center_id: {'queue_hours', 'move_hours', 'samples'}}` from recent history.

    Work centres with fewer than `MIN_SAMPLES` observations are omitted entirely — an
    absent key means "not measured", which the caller must handle differently from a
    measured zero.
    """
    from django.utils import timezone
    from Tracker.models import StepExecution

    cutoff = timezone.now() - timedelta(days=max(1, lookback_days))

    queue_by_wc: dict = defaultdict(list)
    # Rows are ordered by part then arrival so consecutive pairs of the same part are
    # adjacent, which is what makes the move calculation a single pass.
    # tenant-safe: explicit tenant filter
    rows = list(
        StepExecution.objects
        .filter(tenant=tenant, part__isnull=False, entered_at__gte=cutoff)
        .order_by('part_id', 'entered_at')
        .values('part_id', 'step__work_center_id',
                'entered_at', 'started_at', 'exited_at')
    )

    move_by_wc: dict = defaultdict(list)
    prev = None
    for r in rows:
        wc = r['step__work_center_id']

        # Queue: arrival -> work started. Needs a started_at, so an execution that was
        # created and never worked contributes nothing rather than a fake zero.
        if wc and r['started_at'] and r['entered_at']:
            hours = (r['started_at'] - r['entered_at']).total_seconds() / 3600.0
            if hours >= 0:
                queue_by_wc[wc].append(hours)

        # Move: previous step's exit -> this step's arrival, charged to the DESTINATION
        # work centre, since that is the queue a lead-time calculation is walking into.
        if (prev is not None and prev['part_id'] == r['part_id']
                and prev['exited_at'] and r['entered_at'] and wc):
            hours = (r['entered_at'] - prev['exited_at']).total_seconds() / 3600.0
            if hours >= 0:
                move_by_wc[wc].append(hours)
        prev = r

    out: dict = {}
    for wc in set(queue_by_wc) | set(move_by_wc):
        q, m = queue_by_wc.get(wc, []), move_by_wc.get(wc, [])
        samples = max(len(q), len(m))
        if samples < MIN_SAMPLES:
            continue
        out[wc] = {
            'queue_hours': round(_percentile(q, percentile), 2),
            'move_hours': round(_percentile(m, percentile), 2),
            'samples': samples,
        }
    return out
