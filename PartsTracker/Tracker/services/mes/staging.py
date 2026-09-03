"""Staging pick list — what to put at each bench before the operator gets there.

The scheduler makes time-specific promises: Teardown Bay runs WO-101 at 08:00, Test
Cell at 11:30, and every downstream time chains off those. If the material isn't at
the bench at 08:00 the promise breaks in the first hour and the rest of the plan is
wrong by lunchtime — at which point people stop trusting the board, and the solver,
the workload control and the capable-to-promise quietly become decoration.

This is the surface that makes the schedule true rather than aspirational. For a
station, over the next few hours of *scheduled* work: which jobs are coming, what
material each one consumes there, whether it's on hand, and which fixtures are needed.
A materials handler works it before the shift; the operator finds the bench ready.

Distinct from `work_order_material_requirements`, which answers "what does this JOB
need" across its whole route. This answers "what does this STATION need next", which
is a different question with a different reader — and it can only be asked at all
because the schedule knows when work arrives.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

DEFAULT_WINDOW_HOURS = 8


def staging_list(tenant, work_center_id=None, hours: int = DEFAULT_WINDOW_HOURS) -> dict:
    """Material and tooling to stage per station over the next `hours` of the plan.

    `work_center_id` narrows to one station (a handler working a single cell);
    omitted, every station with upcoming work is returned.
    """
    from django.db.models import Sum
    from django.utils import timezone
    from Tracker.models import MaterialLot, ScheduledTask, ScheduleResult
    from Tracker.services.mes.consumption import _released_bom_lines

    now = timezone.now()
    until = now + timedelta(hours=hours)

    schedule = (ScheduleResult.objects.filter(tenant=tenant, is_active=True)
                .order_by('-created_at').first())
    if schedule is None:
        return _empty(now, until, hours, "No active schedule — solve first.")

    # tenant-safe: `schedule` is a tenant-scoped row; its tasks share its tenant.
    tasks = (ScheduledTask.objects.filter(
                schedule=schedule, start_time__lt=until, end_time__gt=now)
             .select_related('part__part_type', 'part__work_order',
                             'step__work_center', 'machine')
             .order_by('start_time'))
    if work_center_id:
        tasks = tasks.filter(step__work_center_id=work_center_id)

    # The solver writes one task per PART; a handler stages per JOB at a station, so
    # collapse to (work order, step) and count the units that land there.
    jobs: dict = {}
    for t in tasks:
        if t.part_id is None or t.step is None or t.step.work_center_id is None:
            continue                      # cores and unstationed steps aren't staged
        if t.step.is_outside_process:
            continue                      # goes to a vendor, not to a bench
        wo = t.part.work_order
        if wo is None:
            continue
        key = (wo.id, t.step_id)
        job = jobs.get(key)
        if job is None:
            job = jobs[key] = {
                'work_order_id': str(wo.id), 'erp_id': wo.ERP_id,
                'part_type': t.part.part_type.name if t.part.part_type else None,
                'step_id': str(t.step_id), 'step_name': t.step.name,
                'work_center_id': str(t.step.work_center_id),
                'work_center': t.step.work_center.name,
                'starts_at': t.start_time, 'units': 0,
                'machine': t.machine.name if t.machine else None,
                '_part_type_id': t.part.part_type_id,
            }
        job['units'] += 1
        job['starts_at'] = min(job['starts_at'], t.start_time)

    # On-hand per material, one query rather than one per line.
    onhand = {
        row['material']: Decimal(str(row['q'] or 0))
        for row in MaterialLot.objects.filter(
            tenant=tenant, status__in=('ACCEPTED', 'IN_USE'))
        .values('material').annotate(q=Sum('quantity_remaining'))
    }

    bom_cache: dict = {}
    fixtures = _fixtures_by_step(tenant)
    stations: dict = defaultdict(list)
    unmapped: dict = {}
    for job in sorted(jobs.values(), key=lambda j: j['starts_at']):
        pt_id = job.pop('_part_type_id')
        job['materials'] = _materials_for(pt_id, job['step_id'], job['units'],
                                          onhand, bom_cache, tenant)
        job['fixtures'] = sorted(fixtures.get(job['step_id'], ()))
        job['short_count'] = sum(1 for m in job['materials'] if m['short'] > 0)
        stations[(job['work_center_id'], job['work_center'])].append(job)
        # A BUY line with no consumed-at-step can't be staged anywhere: we know the
        # job needs it, not WHERE. Reporting that beats an empty bench list that
        # looks like "nothing to pick" — the same reason the solver explains an
        # infeasible run instead of showing a blank board.
        missing = _unmapped_components(pt_id, bom_cache)
        if missing and job['erp_id'] not in unmapped:
            unmapped[job['erp_id']] = {'erp_id': job['erp_id'],
                                       'part_type': job['part_type'],
                                       'components': missing}

    return {
        'from': now, 'to': until, 'window_hours': hours,
        'schedule_id': str(schedule.id), 'is_stale': bool(schedule.is_stale),
        'note': None,
        'unmapped': sorted(unmapped.values(), key=lambda u: u['erp_id']),
        'stations': [
            {'work_center_id': wc_id, 'name': name, 'jobs': jobs_,
             'short_count': sum(j['short_count'] for j in jobs_)}
            for (wc_id, name), jobs_ in sorted(stations.items(), key=lambda kv: kv[0][1])
        ],
    }


def _materials_for(part_type_id, step_id, units: int, onhand: dict,
                   bom_cache: dict, tenant) -> list:
    """BOM lines consumed at this step, scaled to the units landing here.

    Scaled to the UNITS AT THIS STATION, not the work order's quantity — a lot that
    arrives in two batches shouldn't have its whole order's material staged for the
    first one.
    """
    from Tracker.services.mes.consumption import _released_bom_lines, plan_draw

    out = []
    for line in _released_bom_lines(part_type_id, bom_cache):
        if str(line.consumed_at_step_id) != str(step_id):
            continue
        if line.source != 'BUY' or line.material_id is None:
            continue
        needed = Decimal(str(line.quantity)) * units
        have = onhand.get(line.material_id, Decimal('0'))
        out.append({
            'material': line.material.name if line.material else str(line.material_id),
            'needed': float(needed),
            'on_hand': float(have),
            'short': float(max(Decimal('0'), needed - have)),
            'optional': bool(line.is_optional),
            # The lots consumption WILL draw, so the picker pulls those and the
            # traceability record matches what physically went in.
            'lots': plan_draw(line.material_id, tenant, needed),
        })
    return sorted(out, key=lambda m: (-m['short'], m['material']))


def _unmapped_components(part_type_id, bom_cache: dict) -> list:
    """BUY components the BOM never says WHERE to consume.

    These can't appear on any bench list — the job needs them, but nothing records at
    which operation. Surfaced so the gap reads as a BOM to fix rather than as a
    station with nothing to pick.
    """
    from Tracker.services.mes.consumption import _released_bom_lines

    return sorted(
        (line.material.name if line.material else str(line.material_id))
        for line in _released_bom_lines(part_type_id, bom_cache)
        if line.source == 'BUY' and line.material_id is not None
        and line.consumed_at_step_id is None
    )


def _fixtures_by_step(tenant) -> dict:
    """step_id (str) -> fixture names the step needs."""
    from Tracker.models import Fixture

    by_step: dict = defaultdict(set)
    for f in Fixture.objects.filter(tenant=tenant).prefetch_related('steps'):
        for s in f.steps.all():
            by_step[str(s.id)].add(f.name)
    return by_step


def _empty(now, until, hours, note) -> dict:
    return {'from': now, 'to': until, 'window_hours': hours, 'schedule_id': None,
            'is_stale': False, 'note': note, 'unmapped': [], 'stations': []}
