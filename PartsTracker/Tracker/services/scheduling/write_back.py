"""Writing a solve back: the `ScheduleResult` with its fence report and figures, and —
when the solve found a plan — one `ScheduledTask` per part."""
from __future__ import annotations

import logging
from datetime import timedelta

from Tracker.services.scheduling.solver_terms import _chosen_machine, _fence_zone, _map_status

logger = logging.getLogger(__name__)


def _freed_report(freed: list) -> list[dict]:
    """Freed fence operations named for the planner: part serial(s), step, and why."""
    if not freed:
        return []
    from Tracker.models import Parts, Steps
    part_ids = {pid for f in freed for pid in f['part_ids']}
    erp = dict(Parts.objects.filter(id__in=part_ids).values_list('id', 'ERP_id'))  # tenant-safe: ids from this tenant's solve
    steps = dict(Steps.objects.filter(id__in={f['step_id'] for f in freed})  # tenant-safe: ids from this tenant's solve
                 .values_list('id', 'name'))
    out = []
    for f in freed:
        names = sorted(erp.get(pid, str(pid)) for pid in f['part_ids'])
        part = names[0] + (f" (+{len(names) - 1})" if len(names) > 1 else "")
        out.append({'part': part, 'step': steps.get(f['step_id'], ''),
                    'reason_code': f['reason_code'], 'reason': f['reason'],
                    'was_pinned': f['was_pinned']})
    return out


def persist(shop, final, machine_solve_ms, operator_solve_ms, draft):
    """Write the solve back and return the new `ScheduleResult`."""
    from Tracker.models.scheduling import ScheduledTask, ScheduleResult

    tenant, horizon = shop.tenant, shop.horizon
    solver = final['solver']
    tasks = final['tasks']
    lateness_terms = final['lateness_terms']
    cp_status = final['cp_status']
    solved = final['solved']

    # The fence report: what was held, and what had to be re-planned and why.
    frozen_kept = final['kept']
    # A held op keeps its time and machine, and its operator unless that person is
    # already held on other fixed work then. When the plan does hand it to someone
    # else, say so — a held op quietly changing hands read as the fence leaking.
    reassigned = []
    if tasks and solved:
        for t in tasks:
            was = t.get('op_unfixed')
            if was is None or not t['pinned']:
                continue
            now = next((op for op, lit in t['named_assign'] if solver.Value(lit)), None)
            if now != was:
                reassigned.append({
                    'part_ids': t['part_ids'], 'step_id': t['step_id'],
                    'reason_code': 'operator_changed',
                    'reason': "kept its time and machine, but its operator is already "
                              "held on other fixed work then, so someone else takes it",
                    'was_pinned': t['planner_pinned']})
    frozen_freed = _freed_report(final['freed'] + reassigned)
    stickiness_cost = 0
    if tasks and solved:
        for kind, v, w in final['stick_terms']:
            stickiness_cost += w * (solver.Value(v) if kind == 'dev' else 1 - solver.Value(v))

    # Flag ops whose max-time-between-ops (cure) window the solver had to relax.
    if tasks and solved:
        for viol, task in final.get('max_time_viols', []):
            if solver.Value(viol):
                task['cure_violation'] = True

    # The lateness term on its own — priority-weighted late-minutes, isolated from
    # the makespan + pin-stickiness terms that dominate the raw objective.
    weighted_lateness = (
        sum(solver.Value(var) * penalty for var, penalty in lateness_terms)
        if (tasks and solved) else 0
    )

    # Proven optimality gap: how far the found objective is from the solver's best
    # bound. 0.0 when OPTIMAL; small positive on a time-limited FEASIBLE result.
    relative_gap = None
    if tasks and solved:
        obj_v = solver.ObjectiveValue()
        bound = solver.BestObjectiveBound()
        relative_gap = abs(obj_v - bound) / max(1.0, abs(obj_v))

    # An INFEASIBLE solve returns no plan and no reason. Say why in the planner's
    # terms before writing the (empty) result — an unexplained blank board is the
    # worst thing this can produce. Diagnosis must never itself break the solve.
    infeasible_reason = ''
    if not (tasks and solved):
        try:
            from Tracker.services.scheduling.infeasibility import diagnose_infeasible
            infeasible_reason = diagnose_infeasible(tenant, horizon)['summary']
        except Exception:  # noqa: BLE001 - advisory only
            logger.exception("Infeasibility diagnosis failed; reporting without it.")

    # A solve that found no plan never replaces the live one: the floor keeps the
    # last good plan (marked stale), and the failed result is kept beside it with
    # its reason (walk 2026-10-22 — one downtime emptied the board).
    failed = bool(tasks) and not solved
    if draft:
        # A draft is a reviewable what-if; it never supersedes the live schedule.
        # Replace only the prior draft (scratch — cascade-deletes its tasks).
        ScheduleResult.objects.filter(tenant=tenant, is_draft=True).delete()
    elif failed:
        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(is_stale=True)
    else:
        ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
            is_active=False, is_stale=True)

    result = ScheduleResult.objects.create(
        tenant=tenant,
        horizon_start=horizon.start, horizon_end=horizon.end,
        solver_status=_map_status(cp_status),
        solve_time_ms=(machine_solve_ms + operator_solve_ms) if tasks else 0,
        machine_solve_ms=machine_solve_ms,
        operator_solve_ms=operator_solve_ms,
        objective_value_cents=int(solver.ObjectiveValue()) if (tasks and solved) else 0,
        weighted_lateness=weighted_lateness,
        relaxed_pin_count=len(final['freed']),
        frozen_kept=frozen_kept,
        frozen_freed=frozen_freed,
        stickiness_cost=stickiness_cost,
        relative_gap=relative_gap,
        infeasible_reason=infeasible_reason,
        is_active=not draft and not failed,
        is_draft=draft,
    )

    if tasks and solved:
        # Write back per PART (and per core) so tracking, pins, and pegging stay
        # part-grained: every part in a lot gets its own ScheduledTask sharing the
        # lot-operation's machine/time window. The Gantt merges contiguous same-WO
        # bars, so a lot renders as one bar.
        rows = []
        for t in tasks:
            machine_id = _chosen_machine(t, solver)
            start_dt = horizon.start + timedelta(minutes=solver.Value(t['start']))
            end_dt = horizon.start + timedelta(minutes=solver.Value(t['end']))
            if (t.get('fixed_start_dt') is not None
                    and t.get('held_minute') == solver.Value(t['start'])):
                # Held operations keep their exact time. Minutes are counted from a
                # horizon that starts "now", so writing the minute back would creep
                # each held task up to a minute earlier on every re-solve.
                span = end_dt - start_dt
                start_dt = t['fixed_start_dt']
                end_dt = start_dt + span
            fence = _fence_zone(solver.Value(t['start']), shop.frozen_min, shop.slushy_min)
            # Persist the NAMED phase's operator choice (the one assign lit set to 1),
            # so a match_operators solve produces a covered schedule directly instead of
            # leaving assigned_operator for a separate Dispatch pass.
            assigned_op_id = next(
                (op for op, lit in t.get('named_assign', ()) if solver.Value(lit) == 1),
                None)
            common = dict(
                tenant=tenant, schedule=result, step_id=t['step_id'],
                machine_id=machine_id, start_time=start_dt, end_time=end_dt,
                is_pinned=t['planner_pinned'], fence_zone=fence,
                requires_operator=t.get('requires_operator', True),
                assigned_operator_id=assigned_op_id,
                material_shortage=t.get('material_short', False),
                material_detail=t.get('material_detail', ''),
                cure_window_violation=t.get('cure_violation', False),
                in_progress=t.get('in_progress', False),
            )
            for part_id in t['part_ids']:
                rows.append(ScheduledTask(part_id=part_id, **common))
        # tenant-safe: every row is constructed with tenant=tenant via `common` above.
        ScheduledTask.objects.bulk_create(rows)
        # A running op keeps its real start and the plan it started on across the
        # re-solve, so plan-vs-actual still sees it (and judges it fairly).
        if not draft:
            from Tracker.services.scheduling.actuals import carry_running_actuals
            carry_running_actuals(result)
        # Attribute a binding-constraint reason to any late task (heuristic, E7).
        from Tracker.services.scheduling.late_cause import attribute_late_causes
        attribute_late_causes(result)

    return result
