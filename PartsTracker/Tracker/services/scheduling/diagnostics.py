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
    'no_open_units',
    'no_routing',
    'no_timings',
    'unstaffable',
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
    'no_open_units': "Nothing left to work",
    'no_routing': "No routing to schedule",
    'no_timings': "No timings authored",
    'unstaffable': "No trained operator",
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

    schedule = (ScheduleResult.objects.filter(tenant=tenant, is_active=True)
                .order_by('-created_at').first())

    horizon = data.get_schedule_horizon(tenant, horizon_days)
    horizon_end_date = (schedule.horizon_end if schedule else horizon.end).date()

    # Units the active schedule actually placed, per work order.
    scheduled_parts: dict = defaultdict(set)
    scheduled_cores: dict = defaultdict(set)
    if schedule is not None:
        # tenant-safe: `schedule` is a tenant-scoped row; its tasks belong to the same tenant.
        for t in (ScheduledTask.objects.filter(schedule=schedule)
                  .values('part_id', 'part__work_order_id',
                          'core_id', 'core__work_order_id')):
            if t['part_id']:
                scheduled_parts[t['part__work_order_id']].add(t['part_id'])
            elif t['core_id']:
                scheduled_cores[t['core__work_order_id']].add(t['core_id'])

    # Everything still owed: finished/cancelled WOs are out, held ones stay in (being
    # held is the very thing we want to report).
    wos = list(
        WorkOrder.objects.filter(tenant=tenant)
        .exclude(workorder_status__in=[WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED])
        .select_related('process', 'process__part_type')
        .prefetch_related('parts', 'cores')
        .order_by('priority', 'expected_completion', 'ERP_id')
    )

    from Tracker.models.scheduling import ReleaseMode
    manual_release = data._release_mode(tenant) == ReleaseMode.MANUAL

    timings = data.get_step_timings(tenant)
    release_keys, short_keys, gate_detail = data.get_material_gates(tenant, horizon)
    # `find_unstaffable_steps` keys by str(step_id); route ids are UUIDs.
    unstaffable = {g['step_id']: g for g in find_unstaffable_steps(tenant)}

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
    for wo in wos:
        open_parts = [p for p in wo.parts.all()
                      if p.part_status not in data._UNSCHEDULABLE_PART_STATUSES]
        open_cores = [c for c in wo.cores.all()
                      if c.status not in data._UNSCHEDULABLE_CORE_STATUSES]
        open_units = len(open_parts) + len(open_cores)
        total_open += open_units

        covered = (len(scheduled_parts.get(wo.id, ())) + len(scheduled_cores.get(wo.id, ())))
        # An unreleased order under MANUAL is on borrowed time: its bars come from a
        # solve that predates the gate, and the next solve drops them. Report it even
        # while it still looks covered — "why did my work vanish?" asked in advance is
        # exactly what this panel is for.
        doomed = manual_release and wo.released_at is None
        if open_units and covered >= open_units and not doomed:
            continue  # fully on the board — nothing to explain

        reason, detail, fix = _classify(
            wo, open_parts, open_cores, open_units, covered, schedule, horizon_end_date,
            timings, unstaffable, short_by_wo, gated_by_wo, _graph, resolve_route,
            manual_release,
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
    }


def _classify(wo, open_parts, open_cores, open_units, covered, schedule, horizon_end_date,
              timings, unstaffable, short_by_wo, gated_by_wo, graph, resolve_route,
              manual_release):
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
    for u in list(open_parts) + list(open_cores):
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
        return ('unstaffable',
                f"“{g['step_name']}” needs {'/'.join(g['required_training'])} and no "
                f"rostered operator holds it{more}.",
                "Certify or roster a qualified operator, or set the step's labor model to off.")

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
