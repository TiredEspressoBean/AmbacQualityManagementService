"""Work-order release — the planner's authorization gate.

Under `OptimizationConfig.release_mode = MANUAL` the scheduler only plans work a
planner has released. This module owns that act: the readiness evaluation that runs
*before* it, the release itself, and un-release.

Two design decisions worth stating, because both differ from what a large ERP does:

**The gate is advisory, not blocking.** Readiness checks are the same ones that make
work unschedulable downstream (routing, timings, staffing, material), so failing them
usually means the plan would be fiction. But a planner often knows something the data
doesn't — the shortage is covered by a hot delivery, the operator gets certified
Friday. So a failing check never refuses; it demands a written reason, which is stored
on the work order. Blocking here would just teach people to fake the data.

**There is no separate planned-order object.** Bigger systems convert planned → firm
planned → production order → released. At this facility size the planner and the
scheduler are the same person, and a second object to convert is overhead with no
reader. Release is a timestamp on the work order that already exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from Tracker.models import WorkOrder, WorkOrderStatus


class ReleaseBlocked(Exception):
    """Raised when a work order fails its readiness checks and no override reason was
    given. Carries the blockers so the caller can show them and re-offer with a reason."""

    def __init__(self, blockers: list[dict]):
        self.blockers = blockers
        summary = "; ".join(b['detail'] for b in blockers[:3])
        more = "" if len(blockers) <= 3 else f" (+{len(blockers) - 3} more)"
        super().__init__(f"Not ready to release: {summary}{more}")


@dataclass(frozen=True)
class ReleaseReadiness:
    """The verdict for one work order. `ok` false ⇒ release needs an override reason."""
    work_order_id: str
    erp_id: str
    ok: bool
    blockers: tuple = field(default_factory=tuple)   # hard problems (dicts)
    warnings: tuple = field(default_factory=tuple)   # worth seeing, not disqualifying

    def as_dict(self) -> dict:
        return {
            'work_order_id': self.work_order_id,
            'erp_id': self.erp_id,
            'ok': self.ok,
            'blockers': list(self.blockers),
            'warnings': list(self.warnings),
        }


@dataclass(frozen=True)
class _Context:
    """Tenant-wide inputs shared across a bulk evaluation. Building these costs a
    handful of queries each, so evaluating 40 work orders one at a time would issue
    them 40 times over; `build_release_context` builds them once."""
    timings: dict
    unstaffable: dict          # str(step_id) -> gap dict
    short_by_wo: dict          # wo_id -> [human shortage lines]
    gated_by_wo: dict          # wo_id -> [human gate lines]
    graphs: dict               # process_id -> (steps, edges)


def build_release_context(tenant, horizon_days: int = 30) -> _Context:
    """Tenant-wide readiness inputs, built once and reused across work orders."""
    from collections import defaultdict
    from Tracker.services.scheduling import data
    from Tracker.services.scheduling.preflight import find_unstaffable_steps

    horizon = data.get_schedule_horizon(tenant, horizon_days)
    release_keys, short_keys, detail = data.get_material_gates(tenant, horizon)

    short_by_wo: dict = defaultdict(list)
    for key in short_keys:
        if detail.get(key):
            short_by_wo[key[0]].append(detail[key])
    gated_by_wo: dict = defaultdict(list)
    for key in release_keys:
        if detail.get(key) and key[0] not in short_by_wo:
            gated_by_wo[key[0]].append(detail[key])

    return _Context(
        timings=data.get_step_timings(tenant),
        unstaffable={g['step_id']: g for g in find_unstaffable_steps(tenant)},
        short_by_wo=dict(short_by_wo),
        gated_by_wo=dict(gated_by_wo),
        graphs={},
    )


def _graph(ctx: _Context, process_id):
    """Steps + edges for a process, in the shape `resolve_route` expects (memoised)."""
    from Tracker.models import ProcessStep, StepEdge
    from Tracker.services.scheduling import data

    if process_id not in ctx.graphs:
        steps = tuple(
            data.StepNode(
                step_id=ps.step_id, is_terminal=ps.step.is_terminal,
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
        ctx.graphs[process_id] = (steps, edges)
    return ctx.graphs[process_id]


def evaluate_release(work_order: WorkOrder, ctx: _Context | None = None) -> ReleaseReadiness:
    """Can this work order be planned as written?

    Blockers are the conditions that would make the released plan fiction: nothing to
    schedule (no process, no routing, no open units), no timings to size operations
    with, or a step no rostered operator can run. Material sits in *warnings* — a
    shortage is a real problem but a routine one, and it usually resolves inside the
    lead time, so it informs the planner rather than demanding an override.
    """
    from Tracker.services.scheduling import data
    from Tracker.services.scheduling.diagnostics import _is_untimed
    from Tracker.services.scheduling.routing import resolve_route

    ctx = ctx or build_release_context(work_order.tenant)
    blockers: list[dict] = []
    warnings: list[dict] = []

    def _blk(code, detail):
        blockers.append({'code': code, 'detail': detail})

    if work_order.workorder_status in (WorkOrderStatus.COMPLETED,
                                       WorkOrderStatus.CANCELLED):
        _blk('closed', f"Work order is {work_order.get_workorder_status_display().lower()}.")
    if work_order.workorder_status == WorkOrderStatus.ON_HOLD:
        _blk('on_hold', "Work order is on hold — clear the hold first.")

    if work_order.process_id is None:
        _blk('no_process', "No process assigned, so there is no routing to schedule.")
        return ReleaseReadiness(str(work_order.id), work_order.ERP_id, not blockers,
                                tuple(blockers), tuple(warnings))

    open_parts = [p for p in work_order.parts.all()
                  if p.part_status not in data._UNSCHEDULABLE_PART_STATUSES]
    open_cores = [c for c in work_order.cores.all()
                  if c.status not in data._UNSCHEDULABLE_CORE_STATUSES]
    if not (open_parts or open_cores):
        _blk('no_open_units', "No units left to work — nothing to release.")
        return ReleaseReadiness(str(work_order.id), work_order.ERP_id, not blockers,
                                tuple(blockers), tuple(warnings))

    steps, edges = _graph(ctx, work_order.process_id)
    route_ids: set = set()
    for u in open_parts + open_cores:
        ids, _ = resolve_route(u.step_id, steps, edges)
        route_ids.update(ids)

    if not route_ids:
        _blk('no_routing',
             "No remaining route — the units sit at a terminal step, or off this "
             "process version's graph.")
    else:
        if all(_is_untimed(ctx.timings.get(sid)) for sid in route_ids):
            _blk('no_timings',
                 f"None of the {len(route_ids)} remaining step(s) have a cycle time, "
                 f"setup or expected duration.")
        for sid in route_ids:
            g = ctx.unstaffable.get(str(sid))
            if g:
                _blk('unstaffable',
                     f"“{g['step_name']}” needs {'/'.join(g['required_training'])} and "
                     f"no rostered operator holds it.")

    if work_order.id in ctx.short_by_wo:
        warnings.append({'code': 'material_short',
                         'detail': "; ".join(ctx.short_by_wo[work_order.id])})
    elif work_order.id in ctx.gated_by_wo:
        warnings.append({'code': 'material_gated',
                         'detail': "; ".join(ctx.gated_by_wo[work_order.id])})

    return ReleaseReadiness(str(work_order.id), work_order.ERP_id, not blockers,
                            tuple(blockers), tuple(warnings))


@transaction.atomic
def release_work_order(work_order: WorkOrder, user, override_reason: str = "",
                       ctx: _Context | None = None) -> ReleaseReadiness:
    """Authorize a work order for scheduling. Returns the readiness that was recorded.

    Raises `ReleaseBlocked` when it isn't ready and no `override_reason` was given.
    Re-releasing an already-released order is a no-op on the timestamp (the original
    release is the one that counts) but still refreshes the recorded reason.
    """
    readiness = evaluate_release(work_order, ctx)
    reason = (override_reason or "").strip()
    if not readiness.ok and not reason:
        raise ReleaseBlocked(list(readiness.blockers))

    fields = ['release_override_reason', 'updated_at']
    work_order.release_override_reason = "" if readiness.ok else reason
    if work_order.released_at is None:
        work_order.released_at = timezone.now()
        work_order.released_by = user if getattr(user, 'is_authenticated', False) else None
        fields += ['released_at', 'released_by']
    work_order.save(update_fields=fields)

    _mark_schedule_stale(work_order.tenant)
    return readiness


@transaction.atomic
def unrelease_work_order(work_order: WorkOrder, user=None) -> WorkOrder:
    """Withdraw authorization — the solver stops planning it under MANUAL mode.

    `released_by` is deliberately left in place: who authorized it is audit history,
    not current state, and clearing it would erase the trail on a re-release.
    """
    if work_order.released_at is None:
        return work_order
    work_order.released_at = None
    work_order.release_override_reason = ""
    work_order.save(update_fields=['released_at', 'release_override_reason', 'updated_at'])
    _mark_schedule_stale(work_order.tenant)
    return work_order


def bulk_release(tenant, work_order_ids, user, override_reason: str = "") -> list[dict]:
    """Release many work orders in one pass, sharing one readiness context.

    Per-order outcome, never all-or-nothing: releasing 12 orders where 2 aren't ready
    should release the 10 and report the 2, not refuse the batch.
    """
    ctx = build_release_context(tenant)
    wos = list(WorkOrder.objects.filter(tenant=tenant, id__in=list(work_order_ids))
               .prefetch_related('parts', 'cores'))
    out = []
    for wo in wos:
        try:
            readiness = release_work_order(wo, user, override_reason, ctx=ctx)
            out.append({'id': str(wo.id), 'erp_id': wo.ERP_id, 'ok': True,
                        'released': True, 'warnings': list(readiness.warnings),
                        'overridden': bool(wo.release_override_reason)})
        except ReleaseBlocked as exc:
            out.append({'id': str(wo.id), 'erp_id': wo.ERP_id, 'ok': False,
                        'released': False, 'blockers': exc.blockers})
    return out


def releasable_work_orders(tenant):
    """Open work orders awaiting release — the planning workbench's inbox."""
    return (WorkOrder.objects.filter(tenant=tenant, released_at__isnull=True)
            .exclude(workorder_status__in=[WorkOrderStatus.COMPLETED,
                                           WorkOrderStatus.CANCELLED])
            .select_related('process', 'process__part_type')
            .prefetch_related('parts', 'cores')
            .order_by('priority', 'expected_completion', 'ERP_id'))


def _mark_schedule_stale(tenant) -> None:
    """Releasing changes what the solver may plan, so the live schedule is now out of
    date — same signal a hold or a due-date edit raises."""
    from Tracker.services.scheduling.staleness import mark_active_schedule_stale
    mark_active_schedule_stale(getattr(tenant, 'id', tenant))
