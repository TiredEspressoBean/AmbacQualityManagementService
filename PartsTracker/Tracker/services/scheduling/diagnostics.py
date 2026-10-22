"""Why isn't this on the board? — unscheduled-work diagnosis.

The Gantt shows what the solver *placed*. It cannot show what it never saw, and that
gap is where planner time goes: a work order sits invisible and the only way to find
out why is to read the solver's input filters by hand. This module answers the
question directly — for every work order with open units, how many of those units the
active schedule actually covers, and when it covers fewer than all of them, the single
most actionable reason.

Reasons resolve in *fix-this-first* order, not in the order the solver applies them: a
held WO is also un-routed and un-timed, but "clear the hold" is the one action that
matters. First match wins, so each work order carries exactly one reason and one fix.

Read-only. Nothing here mutates a schedule — it re-derives the solver's inputs
(`data.get_*`) against the persisted result and reports the difference.
"""
from __future__ import annotations

from collections import defaultdict

# Fix-this-first order. Earlier entries shadow later ones for the same work order.
REASON_ORDER = (
    'on_hold',
    'not_released',
    'no_process',
    'no_units',
    'awaiting_shipment',
    'no_open_units',
    'no_routing',
    'no_timings',
    'unstaffable',
    'machine_down',
    'outside_horizon',
    'material_gated',
    'material_short',
    'stale_schedule',
    'not_solved',
)

REASON_LABELS = {
    'on_hold': "On hold",
    'not_released': "Not released",
    'no_process': "No process assigned",
    'no_units': "No units created yet",
    'awaiting_shipment': "Waiting to ship",
    'no_open_units': "Nothing left to work",
    'no_routing': "No routing to schedule",
    'no_timings': "No timings authored",
    'unstaffable': "No qualified operator rostered",
    'machine_down': "No machine available",
    'material_short': "Material short",
    'material_gated': "Waiting on material",
    'outside_horizon': "Starts past the horizon",
    'stale_schedule': "Added since the last solve",
    'not_solved': "Not placed by the last solve",
}


def diagnose_unscheduled(tenant, horizon_days: int = 30) -> dict:
    """Explain every work order the active schedule doesn't fully cover.

    Returns ``{schedule, horizon, counts, work_orders[]}``. ``work_orders`` holds one
    entry per WO with ``open_units > scheduled_units``, each carrying ``reason``,
    ``reason_label``, ``detail`` (the specific thing that's wrong) and ``fix`` (what
    the planner does about it). Empty ⇒ every open unit is on the board.
    """
    from Tracker.models import (
        ProcessStep, ScheduledTask, ScheduleResult, StepEdge, WorkOrder, WorkOrderStatus,
    )
    from Tracker.services.scheduling import data
    from Tracker.services.scheduling.preflight import find_unstaffable_steps
    from Tracker.services.scheduling.routing import resolve_route

    schedule = (ScheduleResult.objects.filter(archived=False, tenant=tenant, is_active=True)
                .order_by('-created_at').first())

    horizon = data.get_schedule_horizon(tenant, horizon_days)
    horizon_end_date = (schedule.horizon_end if schedule else horizon.end).date()

    # Units the active schedule actually placed, per work order.
    # (A reman core is a part, so it is counted here with the rest.)
    scheduled_parts: dict = defaultdict(set)
    if schedule is not None:
        # tenant-safe: `schedule` is a tenant-scoped row; its tasks belong to the same tenant.
        for t in (ScheduledTask.objects.filter(schedule=schedule)
                  .values('part_id', 'part__work_order_id')):
            if t['part_id']:
                scheduled_parts[t['part__work_order_id']].add(t['part_id'])

    # Everything still owed: finished/cancelled WOs are out, held ones stay in (being
    # held is the very thing we want to report).
    wos = list(
        WorkOrder.objects.filter(archived=False, tenant=tenant)
        .exclude(workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED])
        .select_related('process', 'process__part_type')
        .prefetch_related('parts__core_role', 'parts__step')
        .order_by('priority', 'expected_completion', 'ERP_id')
    )

    from Tracker.models.scheduling import ReleaseMode
    manual_release = data._release_mode(tenant) == ReleaseMode.MANUAL

    timings = data.get_step_timings(tenant)
    release_keys, short_keys, gate_detail = data.get_material_gates(tenant, horizon)
    # `find_unstaffable_steps` keys by str(step_id); route ids are UUIDs.
    unstaffable = {g['step_id']: g for g in find_unstaffable_steps(tenant)}
    # Steps every eligible machine is down for the whole horizon: the solve plans up to them.
    unrunnable = data.get_unrunnable_steps(tenant, horizon)

    # Material gates key on (wo_id, step_id | None); collapse to per-WO for reporting.
    short_by_wo: dict = defaultdict(list)
    for key in short_keys:
        msg = gate_detail.get(key)
        if msg:
            short_by_wo[key[0]].append(msg)
    gated_by_wo: dict = defaultdict(list)
    for key in release_keys:
        msg = gate_detail.get(key)
        if msg and key[0] not in short_by_wo:
            gated_by_wo[key[0]].append(msg)

    graph_cache: dict = {}

    def _graph(process_id):
        """Steps + edges for a process, in the shape `resolve_route` expects."""
        if process_id not in graph_cache:
            steps = tuple(
                data.StepNode(step_id=ps.step_id, is_terminal=ps.step.is_terminal,
                              requires_first_piece_inspection=ps.step.requires_first_piece_inspection,
                              order=ps.order)
                for ps in ProcessStep.objects.filter(process_id=process_id)
                .select_related('step').order_by('order')
            )
            edges = tuple(
                data.EdgeData(from_step_id=e.from_step_id, to_step_id=e.to_step_id,
                              edge_type=e.edge_type, max_minutes=e.max_minutes)
                for e in StepEdge.objects.filter(process_id=process_id)
            )
            graph_cache[process_id] = (steps, edges)
        return graph_cache[process_id]

    rows = []
    total_open = 0
    open_route: set = set()   # every step some open unit still has to pass
    for wo in wos:
        live = [p for p in wo.parts.all()
                if p.part_status not in data._UNSCHEDULABLE_PART_STATUSES]
        # A unit at a terminal step (Ship) has no route left — nothing for the solver
        # to place. Counted as open, it read "not placed by the last solve → re-solve
        # longer" (PM walk 2026-10-21). It's waiting to ship, not to be scheduled.
        at_end = sum(1 for p in live if p.step_id and p.step.is_terminal)
        open_parts = [p for p in live if not (p.step_id and p.step.is_terminal)]
        open_units = len(open_parts)
        total_open += open_units

        covered = len(scheduled_parts.get(wo.id, ()))
        # An unreleased order under MANUAL is on borrowed time: its bars come from a
        # solve that predates the gate, and the next solve drops them. Report it even
        # while it still looks covered — "why did my work vanish?" asked in advance is
        # exactly what this panel is for.
        doomed = manual_release and wo.released_at is None
        wo_route: set = set()
        if wo.process_id is not None:
            for p in open_parts:
                wo_route.update(resolve_route(p.step_id, *_graph(wo.process_id))[0])
        open_route |= wo_route
        # The solve plans a unit only up to a step nobody rostered can run, so a unit
        # with tasks can still have the rest of its route waiting — report it.
        cut_short = any(str(sid) in unstaffable or sid in unrunnable for sid in wo_route)
        if open_units and covered >= open_units and not doomed and not cut_short:
            continue  # fully on the board — nothing to explain

        reason, detail, fix = _classify(
            wo, open_parts, open_units, covered, schedule, horizon_end_date,
            timings, unstaffable, short_by_wo, gated_by_wo, _graph, resolve_route,
            manual_release, at_end=at_end, unrunnable=unrunnable,
        )
        rows.append({
            'work_order_id': str(wo.id),
            'erp_id': wo.ERP_id,
            'part_type': (wo.process.part_type.name
                          if wo.process and wo.process.part_type else None),
            'process': wo.process.name if wo.process else None,
            'status': wo.workorder_status,
            'priority': wo.priority,
            'quantity': wo.quantity,
            'due_date': wo.expected_completion,
            'expected_start': wo.expected_start,
            'open_units': open_units,
            'scheduled_units': covered,
            'reason': reason,
            'reason_label': REASON_LABELS[reason],
            'detail': detail,
            'fix': fix,
        })

    order = {r: i for i, r in enumerate(REASON_ORDER)}
    rows.sort(key=lambda r: (order[r['reason']], r['priority'], r['erp_id']))

    counts: dict = defaultdict(int)
    for r in rows:
        counts[r['reason']] += 1

    return {
        'schedule_id': str(schedule.id) if schedule else None,
        'solved_at': schedule.created_at if schedule else None,
        'is_stale': bool(schedule.is_stale) if schedule else False,
        'horizon_start': schedule.horizon_start if schedule else horizon.start,
        'horizon_end': schedule.horizon_end if schedule else horizon.end,
        'open_work_orders': len(wos),
        'open_units': total_open,
        'unscheduled_work_orders': len(rows),
        'counts': dict(counts),
        'work_orders': rows,
        'lapsing': _lapsing_in_horizon(tenant, horizon, open_route),
    }


def _lapsing_in_horizon(tenant, horizon, route_step_ids: set) -> list[dict]:
    """Certifications and calibrations that run out inside the horizon on resources
    the open work needs: an operator's training for a gated step, a machine's or a
    measurement gauge's calibration. Past that date the solver can't use them, so
    work there goes late or uncovered — this names the cause.
    `[{kind, name, what, lapses_on, steps[]}]`, soonest first."""
    from datetime import timedelta
    from Tracker.models import Equipments, MeasurementDefinition, Steps, StepEquipmentAffinity, User
    from Tracker.services.core.clock import tenant_today
    from Tracker.services.scheduling import data

    if not route_step_ids:
        return []
    today = tenant_today(tenant)
    end = horizon.end.date()
    step_names = dict(Steps.objects.filter(tenant=tenant, id__in=route_step_ids)  # tenant-safe: explicit tenant filter
                      .values_list('id', 'name'))
    out: dict = {}

    def add(kind, key, name, what, lapses_on, step_id):
        row = out.setdefault((kind, key, what), {
            'kind': kind, 'name': name, 'what': what, 'lapses_on': lapses_on, 'steps': set()})
        row['steps'].add(step_names.get(step_id, ''))

    lapses = data.get_operator_qualification_lapses(tenant, horizon)
    names = {u.id: u.display_name for u in User.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, id__in={uid for by in lapses.values() for uid in by})}
    for sid, by_op in lapses.items():
        if sid in route_step_ids:
            for uid, (lapse, training) in by_op.items():
                add('operator', uid, names.get(uid, ''), training,
                    (lapse - timedelta(days=1)).date(), sid)

    # Machines eligible for the open steps, and the gauges those steps measure with.
    eq_steps: dict = defaultdict(set)
    for a in StepEquipmentAffinity.objects.filter(  # tenant-safe: explicit tenant filter
            archived=False, tenant=tenant, step_id__in=route_step_ids).values('equipment_id', 'step_id'):
        eq_steps[('machine', a['equipment_id'])].add(a['step_id'])
    for md in MeasurementDefinition.objects.filter(  # tenant-safe: explicit tenant filter
            archived=False, tenant=tenant, step_id__in=route_step_ids,
            default_equipment__isnull=False).values('default_equipment_id', 'step_id'):
        eq_steps[('gauge', md['default_equipment_id'])].add(md['step_id'])
    # `requires_calibration` is a property (type default + per-unit override).
    eqs = {e.id: e for e in Equipments.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, id__in={k[1] for k in eq_steps}).select_related('equipment_type')}
    for (kind, eid), sids in eq_steps.items():
        e = eqs.get(eid)
        if e is None or not e.requires_calibration:
            continue
        due = e.next_calibration_due
        if due is None or not (today <= due < end):
            continue
        for sid in sids:
            add(kind, eid, e.name, "calibration", due, sid)

    rows = [{**r, 'steps': sorted(s for s in r['steps'] if s)} for r in out.values()]
    rows.sort(key=lambda r: (r['lapses_on'], r['kind'], r['name']))
    return rows


def _classify(wo, open_parts, open_units, covered, schedule, horizon_end_date,
              timings, unstaffable, short_by_wo, gated_by_wo, graph, resolve_route,
              manual_release, at_end: int = 0, unrunnable=None):
    """The single most actionable reason this WO isn't (fully) on the board.

    Returns `(reason_code, detail, fix)`. Order matters — see `REASON_ORDER`.
    """
    from Tracker.models import WorkOrderStatus

    if wo.workorder_status == WorkOrderStatus.ON_HOLD:
        return ('on_hold',
                "The solver skips held work orders.",
                "Clear the hold to put it back in the plan.")

    # Only a gate under MANUAL release mode; `manual_release` is False under AUTO, so
    # an unreleased order there falls through to whatever the real cause is.
    if manual_release and wo.released_at is None:
        return ('not_released',
                "Not released for scheduling — this tenant plans released work only.",
                "Release it from the planning queue.")

    if wo.process_id is None:
        return ('no_process',
                "No process is assigned, so there's no routing to schedule.",
                "Assign a process to the work order.")

    # No parts at all is not "all finished": the work order form creates none, and
    # "close it" would throw away real demand (PM walk 2026-10-21).
    if not wo.parts.filter(archived=False).exists():
        return ('no_units',
                f"No units have been created for this work order yet (quantity {wo.quantity}).",
                "Add its parts to the work order.")

    if open_units == 0 and at_end:
        step = next((p.step for p in wo.parts.all() if p.step_id and p.step.is_terminal), None)
        return ('awaiting_shipment',
                f"{at_end} unit(s) are at {step.name if step else 'the last step'}, the end of "
                f"the route — nothing left to schedule.",
                "Ship them from Shipping.")

    if open_units == 0:
        return ('no_open_units',
                f"All {wo.quantity} unit(s) are finished, shipped, scrapped or quarantined.",
                "Close the work order, or release the quarantined units.")

    steps, edges = graph(wo.process_id)
    if not steps:
        return ('no_routing',
                f"Process “{wo.process.name}” has no steps.",
                "Author the process routing.")

    # Union of the remaining route across every open unit — that's what the solver
    # would have to place.
    route_ids: set = set()
    unroutable = 0
    for u in open_parts:
        ids, _ = resolve_route(u.step_id, steps, edges)
        if ids:
            route_ids.update(ids)
        else:
            unroutable += 1
    if not route_ids:
        return ('no_routing',
                f"{unroutable} unit(s) sit at a step with no remaining route "
                f"(terminal step, or off this process version's graph).",
                "Check the unit's current step against the process routing.")

    untimed = [sid for sid in route_ids
               if _is_untimed(timings.get(sid))]
    if len(untimed) == len(route_ids):
        return ('no_timings',
                f"None of the {len(route_ids)} remaining step(s) have a cycle time, "
                f"setup or expected duration — every operation would size to zero.",
                "Author StepTiming (or an expected duration) for the route.")

    blocked = [unstaffable[str(sid)] for sid in route_ids if str(sid) in unstaffable]
    if blocked:
        g = blocked[0]
        more = f" (+{len(blocked) - 1} more step(s))" if len(blocked) > 1 else ""
        holders = (f" Holders: {', '.join(g['holders'])}." if g.get('holders')
                   else " Nobody holds it.")
        return ('unstaffable',
                f"No qualified operator rostered: “{g['step_name']}” needs "
                f"{'/'.join(g['required_training'])}{more}. Planned up to the step before "
                f"it; it and what follows wait.{holders}",
                "Certify or roster a qualified operator, or set the step's labor model to off.")

    down = [(sid, (unrunnable or {})[sid]) for sid in route_ids if sid in (unrunnable or {})]
    if down:
        from Tracker.models import Steps
        sid, why = down[0]
        name = Steps.objects.filter(pk=sid).values_list('name', flat=True).first() or 'A step'  # tenant-safe: pk from this tenant's routing
        return ('machine_down',
                f"“{name}” has no machine to run on: {why}. Planned up to the step before "
                f"it; it and what follows wait.",
                "Bring the machine back (close the downtime), or make another machine "
                "eligible for the step.")

    # Release date beyond the horizon is a harder cause than a material gate: the work
    # has nowhere to go regardless of stock, so report it first.
    if wo.expected_start and wo.expected_start > horizon_end_date:
        return ('outside_horizon',
                f"Releases {wo.expected_start:%b %d}, past the "
                f"{horizon_end_date:%b %d} horizon.",
                "Pull the release date in, or widen the planning horizon.")

    if wo.id in gated_by_wo:
        return ('material_gated',
                "; ".join(gated_by_wo[wo.id]),
                "The operation can't start before the promised receipt — expedite it "
                "to pull the work in.")

    if wo.id in short_by_wo:
        return ('material_short',
                "; ".join(short_by_wo[wo.id]),
                "Raise a purchase order, or receive the outstanding stock.")

    if schedule is None:
        return ('not_solved',
                "There is no active schedule yet.",
                "Run a solve.")

    if schedule.is_stale or wo.created_at > schedule.created_at:
        return ('stale_schedule',
                f"The active schedule was solved {schedule.created_at:%b %d %H:%M}, "
                f"before this work order's current state.",
                "Re-solve to pick it up.")

    return ('not_solved',
            f"{open_units - covered} unit(s) have no task on the active schedule and "
            f"nothing above explains it — the solve most likely ran out of horizon "
            f"or time.",
            "Re-solve with a longer time limit, or widen the horizon.")


def _is_untimed(t) -> bool:
    """A step the solver would size to zero minutes: no authored cycle, no setup."""
    if t is None:
        return True
    return (t.cycle_source == 'none' and not t.setup_minutes
            and not t.load_unload_per_piece)
