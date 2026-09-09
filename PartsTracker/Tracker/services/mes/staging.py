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
    # Net out stock already pulled to a bench and not yet consumed. `quantity_remaining`
    # doesn't move until consumption, so without this a loaded cart still reads as
    # available and the same units get promised to a second job.
    from Tracker.models import MaterialStagingLine
    # tenant-safe: explicit tenant filter
    for row in (MaterialStagingLine.objects
                .filter(tenant=tenant, issued_at__isnull=True)
                .values('material').annotate(q=Sum('qty_picked'))):
        if row['material'] in onhand:
            onhand[row['material']] = max(
                Decimal('0'), onhand[row['material']] - Decimal(str(row['q'] or 0)))

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

    # Staged state for exactly the jobs on this list, in one query.
    staged = _staged_map(
        tenant, [(j['work_order_id'], j['step_id'])
                 for js in stations.values() for j in js])
    picked = _picked_map(tenant, [(j['work_order_id'], j['step_id'])
                                  for js in stations.values() for j in js])
    for js in stations.values():
        for j in js:
            st = staged.get((j['work_order_id'], j['step_id']), {})
            j['staged_at'] = st.get('staged_at')
            j['staged_by'] = st.get('staged_by')
            j['staging_note'] = st.get('note', '')
            # Per-material pick state, so the sheet shows what's already been
            # confirmed instead of asking again — and so a deviation stays visible
            # rather than being overwritten by the next render of the plan.
            for m in j['materials']:
                p = picked.get((j['work_order_id'], j['step_id'], m['material_id']))
                m['picked_qty'] = float(p['qty_picked']) if p else None
                m['picked_lots'] = p['picked_lots'] if p else []
                # A pick whose lots differ from the plan is the case worth seeing: the
                # named lot was empty, short, or already taken.
                m['deviated'] = bool(
                    p and {l.get('lot_id') for l in (p['picked_lots'] or [])}
                    != {l.get('lot_id') for l in m.get('lots', [])})

    return {
        'from': now, 'to': until, 'window_hours': hours,
        'schedule_id': str(schedule.id), 'is_stale': bool(schedule.is_stale),
        'note': None,
        'unmapped': sorted(unmapped.values(), key=lambda u: u['erp_id']),
        'stations': [
            {'work_center_id': wc_id, 'name': name, 'jobs': jobs_,
             'short_count': sum(j['short_count'] for j in jobs_),
             'staged_count': sum(1 for j in jobs_ if j.get('staged_at'))}
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
        # Raw materials only. A BUY line pointing at a purchased *part* is procured
        # and planned like any other bought item, but MaterialStagingLine is keyed to
        # Material, so parts aren't kitted through staging yet — they're omitted here
        # the same way MAKE lines are, rather than half-shown with no pick plan.
        if line.source != 'BUY' or line.material_id is None:
            continue
        needed = Decimal(str(line.quantity)) * units
        have = onhand.get(line.material_id, Decimal('0'))
        out.append({
            # Confirming a pick has to name the material, not just show it.
            'material_id': str(line.material_id),
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


def set_staged(tenant, work_order_id, step_id, staged: bool, user, note: str = ""):
    """Mark a job's material staged (or not) at one step.

    Idempotent by design — a handler double-tapping the same row, or two people
    working the same cart, must not produce a second record or move the timestamp
    on already-staged work.
    """
    from django.utils import timezone
    from Tracker.models import MaterialStaging

    row, _ = MaterialStaging.objects.get_or_create(
        tenant=tenant, work_order_id=work_order_id, step_id=step_id)
    if staged:
        if row.staged_at is None:
            row.staged_at = timezone.now()
            row.staged_by = user if getattr(user, 'is_authenticated', False) else None
    else:
        row.staged_at = None
        row.staged_by = None
    row.note = note or ""
    row.save(update_fields=['staged_at', 'staged_by', 'note', 'updated_at'])
    return row


def _staged_map(tenant, keys) -> dict:
    """(work_order_id, step_id) -> {staged_at, staged_by, note} for the jobs shown.

    One query for the whole list rather than one per job.
    """
    from Tracker.models import MaterialStaging

    if not keys:
        return {}
    wo_ids = {k[0] for k in keys}
    step_ids = {k[1] for k in keys}
    out = {}
    for r in (MaterialStaging.objects
              .filter(tenant=tenant, work_order_id__in=wo_ids, step_id__in=step_ids)
              .select_related('staged_by')):
        out[(str(r.work_order_id), str(r.step_id))] = {
            'staged_at': r.staged_at,
            'staged_by': (r.staged_by.get_full_name() or r.staged_by.username
                          if r.staged_by else None),
            'note': r.note,
        }
    return out


def consolidated_pick(tenant, work_center_id=None, hours: int = DEFAULT_WINDOW_HOURS) -> dict:
    """The shelf sweep: everything to pull from stores for the next `hours`, by material.

    The companion to `staging_list`, not a rival. `staging_list` answers "what goes to
    each bench" (the put); this answers "what do I pull from the shelves" (the pull).
    Batch-picking one material for six jobs beats six trips to the same bin, and the
    literature puts the travel saving at 27-40%.

    The whole cost of batching is sortation, so every row carries its `drops` — which
    kit each portion belongs to. Without that the picker ends up holding 200 seals and
    no way to split them.

    Lots are planned ONCE against the combined total rather than per job. Per-job
    planning hands the same lot to every job that needs the material, because nothing
    reserves; planning against the total at least makes one sheet internally consistent.
    """
    data = staging_list(tenant, work_center_id, hours)
    if data.get('note'):
        return {**data, 'materials': []}

    from Tracker.services.mes.consumption import plan_draw
    from Tracker.models import Material

    rows: dict = {}
    for st in data['stations']:
        for job in st['jobs']:
            for m in job['materials']:
                row = rows.get(m['material'])
                if row is None:
                    row = rows[m['material']] = {
                        'material': m['material'], 'needed': 0.0, 'on_hand': m['on_hand'],
                        'material_id': None, 'drops': [],
                    }
                row['needed'] += m['needed']
                # `material_id` isn't on the staging row; recover it from the lot plan
                # when there is one so the combined draw can be re-planned below.
                row['drops'].append({
                    'qty': m['needed'], 'station': st['name'], 'erp_id': job['erp_id'],
                    'step_name': job['step_name'], 'staged': bool(job.get('staged_at')),
                })

    # Re-plan each material's lots against the combined quantity.
    by_name = {}
    if rows:
        # tenant-safe: explicit tenant filter
        by_name = {m.name: m.id for m in Material.objects.filter(
            tenant=tenant, name__in=list(rows))}
    out = []
    for name, row in rows.items():
        mid = by_name.get(name)
        needed = Decimal(str(row['needed']))
        plan = plan_draw(mid, tenant, needed) if mid else []
        planned = sum(Decimal(str(p['take'])) for p in plan)
        out.append({
            'material': name,
            'needed': float(needed),
            'on_hand': row['on_hand'],
            'short': float(max(Decimal('0'), needed - planned)),
            'lots': plan,
            'storage_location': next(
                (p['storage_location'] for p in plan if p['storage_location']), ''),
            'drops': sorted(row['drops'], key=lambda d: (d['station'], d['erp_id'])),
        })

    # Grouped by where it lives, so the sheet reads as a walk rather than a list.
    # With one storage location this degrades to a single group, which is today's
    # behaviour and costs nothing.
    out.sort(key=lambda r: (r['storage_location'], r['material']))
    return {**data, 'materials': out}


def _picked_map(tenant, keys) -> dict:
    """(work_order_id, step_id, material_id) -> the recorded pick, for the jobs shown.

    One query for the whole sheet rather than one per material.
    """
    from Tracker.models import MaterialStagingLine

    if not keys:
        return {}
    wo_ids = {k[0] for k in keys}
    step_ids = {k[1] for k in keys}
    out = {}
    # tenant-safe: explicit tenant filter
    for r in (MaterialStagingLine.objects
              .filter(tenant=tenant, staging__work_order_id__in=wo_ids,
                      staging__step_id__in=step_ids)
              .select_related('staging')):
        out[(str(r.staging.work_order_id), str(r.staging.step_id),
             str(r.material_id))] = {
            'qty_picked': r.qty_picked,
            'picked_lots': r.picked_lots or [],
        }
    return out


def record_pick(tenant, work_order_id, step_id, material_id, qty, lots, user,
                qty_required=None):
    """Record what a picker actually pulled for one material on one job-operation.

    `lots` is `[{lot_id, lot_number, qty}]` — what physically went in the tote, which is
    routinely NOT what the sheet named: the printed lot is empty, short, or someone got
    there first. Recording it does two things at once.

    It reserves: until consumption draws the line down, `qty_picked` is netted out of
    on-hand everywhere, so a second sheet can't promise the same units.

    And it corrects the traceability record: `consume_for_step` reads these lots instead
    of re-deriving FEFO, so what the system says went into the unit is what did.
    """
    from django.utils import timezone
    from Tracker.models import MaterialStaging, MaterialStagingLine

    staging, _ = MaterialStaging.objects.get_or_create(
        tenant=tenant, work_order_id=work_order_id, step_id=step_id)

    line, _ = MaterialStagingLine.objects.update_or_create(
        tenant=tenant, staging=staging, material_id=material_id,
        defaults={
            'qty_picked': Decimal(str(qty)),
            # What the picker was working to, as the sheet presented it. Without this
            # the line records what was taken but not what was asked for, so a short
            # pick and a complete one look identical — which is the one comparison the
            # line exists to make.
            'qty_required': Decimal(str(qty_required if qty_required is not None else qty)),
            'picked_lots': list(lots or []),
            'picked_by': user,
            # A re-pick after issue starts a fresh reservation rather than silently
            # topping up a line the system already believes was consumed.
            'issued_at': None,
        })

    # Picking IS staging for this job-operation — the handler shouldn't have to say so
    # twice, and a sheet reprinted mid-shift must show the work already done.
    if staging.staged_at is None:
        staging.staged_at = timezone.now()
        staging.staged_by = user
        staging.save(update_fields=['staged_at', 'staged_by'])
    return line
