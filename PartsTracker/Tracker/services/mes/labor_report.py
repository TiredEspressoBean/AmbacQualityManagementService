"""Operator labour hours — attendance from the clock, direct time from the step records.

Decision 2026-10-29 (option 1): direct hours are DERIVED from `StepExecution`, not clocked.
Nothing in the product creates PRODUCTION/SETUP/REWORK `TimeEntry` rows, so a clock-based
direct figure was always 0 on a real shop.

  - **On-shift** = the operator's SHIFT time minus BREAK/LUNCH (`TimeEntry`).
  - **Direct**   = the operator's step-execution time (started_at → exited_at, or now /
    the window end while open), with three rules:
      1. *Merged, never summed.* A lock-step lot puts N executions on near-identical
         times; summing would bill the operator N times over. Concurrent executions
         share each moment between them instead.
      2. *Clipped to attendance.* Only time inside on-shift counts, so direct can never
         exceed on-shift. An operator who didn't clock in has no direct time.
      3. *Not while waiting.* Time the part's work order sat on hold
         (`WorkOrderHold`), or the part was out for outside processing (the
         execution's `outside_process_shipment`, shipped → returned), is left out.
  - **Rework** = the part of direct spent on a re-visit (visit_number > 1) or at a
    REWORK step. Shown beside direct; it is included in it.
  - **Unallocated** = on-shift − direct.

Attribution: whoever claimed/started the execution (`assigned_to`), else whoever completed
it (`completed_by`). No handover timestamp exists, so a handed-over job stays with its
claimant. Setup isn't separated: direct = setup + run.

Splitting concurrent work: each moment of an operator's merged time is shared EVENLY
across the executions open at that moment. An execution is one part, so this is
proportional to parts — two parts of WO-A and one of WO-B open together give A two
thirds and B one third. Nothing is double-counted.

Scoped to shop-floor operators (the Operator / Shift Lead groups) where configured — see
services.scheduling.data.SHOP_FLOOR_GROUPS. The Operator Hours screen, its PDF, the
work-order panel and the operator's own "My hours" all read this module, so they agree.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict

_ATTENDANCE = 'SHIFT'
_BREAKS = {'BREAK', 'LUNCH'}
# The clock entries a lead approves; job time is derived, so it has no lines to approve.
ATTENDANCE_TYPES = ('SHIFT', 'BREAK', 'LUNCH')
# Executions that never represent work done.
_NOT_WORK = ('PENDING', 'SKIPPED', 'CANCELLED')


# --- interval helpers (lists of (start, end) datetimes) ---------------------------------

def _merge(intervals):
    out = []
    for s, e in sorted(i for i in intervals if i[1] > i[0]):
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def _subtract(intervals, cuts):
    """`intervals` minus `cuts` (both any order; result merged)."""
    cuts = _merge(cuts)
    out = []
    for s, e in _merge(intervals):
        cur = s
        for cs, ce in cuts:
            if ce <= cur or cs >= e:
                continue
            if cs > cur:
                out.append((cur, cs))
            cur = max(cur, ce)
            if cur >= e:
                break
        if cur < e:
            out.append((cur, e))
    return out


def _overlap_seconds(seg_s, seg_e, merged, starts) -> float:
    """Seconds of [seg_s, seg_e) inside the merged, sorted intervals (`starts` = their
    start times, for bisect)."""
    total = 0.0
    i = max(0, bisect_right(starts, seg_s) - 1)
    while i < len(merged) and merged[i][0] < seg_e:
        s, e = merged[i]
        lo, hi = max(s, seg_s), min(e, seg_e)
        if hi > lo:
            total += (hi - lo).total_seconds()
        i += 1
    return total


def _total(intervals) -> float:
    return sum((e - s).total_seconds() for s, e in intervals)


# --- the allocation ---------------------------------------------------------------------

def _attendance(tenant, start, cap, user_ids=None) -> dict:
    """{user_id: merged on-shift intervals} — SHIFT minus BREAK/LUNCH, within [start, cap]."""
    from Tracker.models import TimeEntry

    qs = (TimeEntry.objects.filter(archived=False, tenant=tenant, start_time__lt=cap,
                                   entry_type__in=[_ATTENDANCE, *_BREAKS])
          .exclude(end_time__lt=start))
    if user_ids is not None:
        qs = qs.filter(user_id__in=user_ids)
    shifts, breaks = defaultdict(list), defaultdict(list)
    for e in qs.values('user_id', 'entry_type', 'start_time', 'end_time'):
        s = max(e['start_time'], start)
        en = min(e['end_time'] or cap, cap)
        if en <= s:
            continue
        (shifts if e['entry_type'] == _ATTENDANCE else breaks)[e['user_id']].append((s, en))
    return {uid: _subtract(iv, breaks.get(uid, [])) for uid, iv in shifts.items()}


def _work_intervals(tenant, start, cap, user_ids=None) -> dict:
    """{user_id: [(start, end, work_order_id, is_rework), ...]} — each execution's worked
    time inside [start, cap], with hold and outside-processing time removed."""
    from django.db.models import Q
    from Tracker.models import StepExecution, WorkOrderHold

    qs = (StepExecution.objects.filter(tenant=tenant, archived=False, started_at__isnull=False,
                                       started_at__lt=cap)
          .exclude(status__in=_NOT_WORK)
          .exclude(exited_at__lte=start)
          .filter(Q(assigned_to__isnull=False) | Q(completed_by__isnull=False)))
    if user_ids is not None:
        qs = qs.filter(Q(assigned_to_id__in=user_ids)
                       | Q(assigned_to__isnull=True, completed_by_id__in=user_ids))
    rows = list(qs.values(
        'assigned_to_id', 'completed_by_id', 'started_at', 'exited_at', 'visit_number',
        'step__step_type', 'part__work_order_id',
        'outside_process_shipment__shipped_at', 'outside_process_shipment__returned_at',
    ))

    wo_ids = {r['part__work_order_id'] for r in rows if r['part__work_order_id']}
    holds = defaultdict(list)
    for h in (WorkOrderHold.objects.filter(tenant=tenant, work_order_id__in=wo_ids,
                                           is_voided=False, placed_at__lt=cap)
              .values('work_order_id', 'placed_at', 'cleared_at')):
        holds[h['work_order_id']].append((h['placed_at'], h['cleared_at'] or cap))

    out = defaultdict(list)
    for r in rows:
        uid = r['assigned_to_id'] or r['completed_by_id']
        if user_ids is not None and uid not in user_ids:
            continue
        s = max(r['started_at'], start)
        e = min(r['exited_at'] or cap, cap)
        if e <= s:
            continue
        cuts = list(holds.get(r['part__work_order_id'], []))
        shipped = r['outside_process_shipment__shipped_at']
        if shipped:
            cuts.append((shipped, r['outside_process_shipment__returned_at'] or cap))
        rework = (r['visit_number'] or 1) > 1 or r['step__step_type'] == 'REWORK'
        for ps, pe in _subtract([(s, e)], cuts):
            out[uid].append((ps, pe, r['part__work_order_id'], rework))
    return out


def allocate(tenant, start, end, user_ids=None) -> dict:
    """The allocation everything here reads.

    Returns {user_id: {'on_shift': s, 'direct': s, 'rework': s,
                       'by_wo': {wo_id: [direct_s, rework_s]}}} in seconds.
    `user_ids` (a set) narrows to those operators; None = everyone with time.
    """
    from django.utils import timezone

    cap = min(end, timezone.now())
    if cap <= start:
        return {}
    attendance = _attendance(tenant, start, cap, user_ids)
    work = _work_intervals(tenant, start, cap, user_ids)

    result = {}
    for uid in set(attendance) | set(work):
        att = attendance.get(uid, [])
        att_starts = [s for s, _ in att]
        rec = {'on_shift': _total(att), 'direct': 0.0, 'rework': 0.0,
               'by_wo': defaultdict(lambda: [0.0, 0.0])}
        # Sweep the operator's executions: between consecutive boundaries the set of
        # open executions is constant, and that stretch (clipped to attendance) is
        # shared evenly among them.
        events = []
        for i, (s, e, _, _) in enumerate(work.get(uid, [])):
            events.append((s, 1, i))
            events.append((e, -1, i))
        events.sort(key=lambda ev: (ev[0], ev[1]))
        items = work.get(uid, [])
        active: set[int] = set()
        prev = None
        for t, kind, i in events:
            if prev is not None and active and t > prev:
                secs = _overlap_seconds(prev, t, att, att_starts)
                if secs > 0:
                    share = secs / len(active)
                    rec['direct'] += secs
                    for j in active:
                        _, _, wo, rework = items[j]
                        slot = rec['by_wo'][wo]
                        slot[0] += share
                        if rework:
                            slot[1] += share
                            rec['rework'] += share
            if kind == 1:
                active.add(i)
            else:
                active.discard(i)
            prev = t
        rec['by_wo'] = dict(rec['by_wo'])
        result[uid] = rec
    return result


def _names(user_ids) -> dict:
    from Tracker.models import User
    # tenant-safe: ids come from the tenant-scoped TimeEntry / StepExecution rows.
    return {u.id: (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.get_username())
            for u in User.objects.filter(id__in=list(user_ids))}


def _h(seconds: float) -> float:
    return round(seconds / 3600, 2)


def _shop_filter(tenant, uids):
    from Tracker.services.scheduling.data import _shop_floor_user_ids
    shop_ids = _shop_floor_user_ids(tenant)  # limit to floor staff when configured
    return [u for u in uids if not shop_ids or u in shop_ids]


def operator_hours(tenant, start, end, user_ids=None) -> list[dict]:
    """Per shop-floor operator over [start, end) (aware datetimes): on-shift, direct,
    rework and unallocated hours, sorted by on-shift desc. `user_ids` narrows (the
    operator's own "My hours" passes just theirs, skipping the shop-floor filter)."""
    alloc = allocate(tenant, start, end, user_ids)
    uids = list(alloc) if user_ids is not None else _shop_filter(tenant, alloc)
    names = _names(uids)
    out = []
    for uid in uids:
        a = alloc[uid]
        out.append({
            'user_id': uid,
            'name': names.get(uid, f"User {uid}"),
            'on_shift_hours': _h(a['on_shift']),
            'direct_hours': _h(a['direct']),
            'rework_hours': _h(a['rework']),
            'unallocated_hours': _h(max(0.0, a['on_shift'] - a['direct'])),
        })
    out.sort(key=lambda r: r['on_shift_hours'], reverse=True)
    return out


def work_order_hours(tenant, start, end) -> list[dict]:
    """Operator × work order × hours over [start, end) — the costing hand-off. Rows with
    no work order (an execution whose part has none) are labelled as such."""
    from Tracker.models import WorkOrder

    alloc = allocate(tenant, start, end)
    uids = _shop_filter(tenant, alloc)
    names = _names(uids)
    wo_ids = {wo for uid in uids for wo in alloc[uid]['by_wo'] if wo}
    wos = {w['id']: w['ERP_id'] for w in
           WorkOrder.objects.filter(tenant=tenant, id__in=wo_ids).values('id', 'ERP_id')}
    out = []
    for uid in uids:
        for wo, (d, r) in alloc[uid]['by_wo'].items():
            if d <= 0:
                continue
            out.append({
                'user_id': uid, 'name': names.get(uid, f"User {uid}"),
                'work_order_id': str(wo) if wo else None,
                'work_order': wos.get(wo) or ('No work order' if not wo else str(wo)),
                'direct_hours': _h(d), 'rework_hours': _h(r),
            })
    out.sort(key=lambda r: (r['work_order'], r['name']))
    return out


def work_order_labor(work_order) -> dict:
    """Actual direct and rework hours to date on one work order, per operator, beside the
    routing's planned operator hours where its steps carry time standards.

    Uses the same allocation (clip to attendance, share concurrent work), over the span
    from the WO's first started execution to now, for the operators who worked it.
    """
    from django.utils import timezone
    from django.db.models import Min
    from Tracker.models import StepExecution

    tenant = work_order.tenant
    execs = StepExecution.objects.filter(tenant=tenant, part__work_order=work_order,
                                         started_at__isnull=False).exclude(status__in=_NOT_WORK)
    first = execs.aggregate(m=Min('started_at'))['m']
    rows = []
    if first:
        uids = set(execs.exclude(assigned_to__isnull=True).values_list('assigned_to_id', flat=True))
        uids |= set(execs.filter(assigned_to__isnull=True, completed_by__isnull=False)
                    .values_list('completed_by_id', flat=True))
        alloc = allocate(tenant, first, timezone.now(), uids)
        names = _names(uids)
        for uid in uids:
            d, r = alloc.get(uid, {}).get('by_wo', {}).get(work_order.id, (0.0, 0.0))
            rows.append({'user_id': uid, 'name': names.get(uid, f"User {uid}"),
                         'direct_hours': _h(d), 'rework_hours': _h(r)})
        rows.sort(key=lambda x: x['direct_hours'], reverse=True)
    planned = planned_operator_hours(work_order)
    return {
        'rows': rows,
        'direct_hours': round(sum(x['direct_hours'] for x in rows), 2),
        'rework_hours': round(sum(x['rework_hours'] for x in rows), 2),
        'planned_hours': planned,
    }


def planned_operator_hours(work_order):
    """Planned operator hours for the work order's main route, from the steps' time
    standards (`StepTiming`, operator-attended time for the WO quantity). Rework steps
    and branches off the default path are not planned work. None when no step on the
    route carries a standard."""
    from Tracker.models import StepTiming
    from Tracker.services.scheduling.data import TimingData

    process = work_order.process
    if process is None:
        return None
    step, seen, route = process.get_entry_step(), set(), []
    while step is not None and step.id not in seen:
        seen.add(step.id)
        if step.step_type != 'REWORK':
            route.append(step.id)
        step = process.get_next_step(step)
    timings = {t.step_id: t for t in StepTiming.objects.filter(tenant=work_order.tenant,
                                                                step_id__in=route)}
    if not timings:
        return None
    qty = work_order.quantity or 0
    minutes = sum(
        TimingData(step_id=t.step_id, cycle_time_minutes=t.cycle_time_minutes,
                   setup_minutes=t.setup_minutes, load_unload_per_piece=t.load_unload_per_piece,
                   attention_type=t.attention_type, cycle_source='timing',
                   ).operator_attended_time(qty)
        for t in timings.values())
    return round(minutes / 60, 2)
