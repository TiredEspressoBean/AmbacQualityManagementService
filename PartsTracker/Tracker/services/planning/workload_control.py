"""Workload Control — deciding what to let onto the shop floor.

The release gate gives a tenant a pre-shop pool: work orders exist but aren't
schedulable until a planner releases them. This module answers the question that pool
poses — *which* orders should go now?

The mechanism is order release against workload norms: walk the pool in priority
order and admit each order while no resource it touches would exceed its ceiling.
Orders that would breach a ceiling stay in the pool for the next pass. That keeps the
committed load close to what the shop can actually absorb, which is what stops the
detailed scheduler being handed six weeks of work for a two-week window.

Two findings from the Workload Control literature shape the design, and both are
easy to get wrong:

**Premature idleness.** Holding an order back while a resource sits idle is strictly
worse than releasing it — the shop loses hours it can never recover, and the order is
late for nothing. So norms alone are not enough: `_starvation_releases` overrides them
for any gating resource with no committed work at all.

**Lead time syndrome.** The classic MRP failure is planned lead times that inflate to
cover queues, which releases work earlier, which lengthens queues, which inflates the
planned lead times again — actual lead time becomes a self-fulfilling consequence of
the planned one. Release here is driven by *measured load against capacity*, never by
a planned lead time, so there is no such quantity to spiral.

Advisory by design: this recommends a release set and says why. A planner accepts,
edits or ignores it. Enforcing it automatically is a later decision, and one that
should wait until time-in-system is being measured — the literature's warning is that
order release can improve shop-floor metrics while making total delivery worse, and
every dashboard we have today watches only the shop floor.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Capacity keys: work centres are keyed by their id, the crew pool by this sentinel.
# One namespace keeps the norm/committed/contribution dicts uniform.
LABOR = '__labor__'


@dataclass(frozen=True)
class ReleaseDecision:
    """One pool order's verdict, with the arithmetic that produced it."""
    work_order_id: str
    erp_id: str
    release: bool
    reason: str
    blocking_resource: str | None = None
    hours: dict = field(default_factory=dict)   # resource key -> hours this order adds

    def as_dict(self, names: dict) -> dict:
        return {
            'work_order_id': self.work_order_id,
            'erp_id': self.erp_id,
            'release': self.release,
            'reason': self.reason,
            'blocking_resource': self.blocking_resource,
            'hours': {names.get(k, k): round(v, 1) for k, v in self.hours.items() if v > 0},
        }


# --- release policies ------------------------------------------------------
#
# A policy answers exactly one question: which resources gate release, and what is
# each one's ceiling in hours? Everything else — the walk, starvation avoidance, the
# reporting — is shared. That is the seam a constraint-driven (drum-buffer-rope)
# policy plugs into without touching the machinery around it.

class ReleasePolicy:
    """Base: gate on every resource at `norm_pct` of its capacity in the window."""

    key = 'wlc'
    label = "Workload control (balance every resource)"

    def __init__(self, norm_pct: float = 100.0):
        self.norm_pct = max(1.0, float(norm_pct))

    def norms(self, ref, capacity: dict) -> dict:
        return {k: hours * self.norm_pct / 100.0 for k, hours in capacity.items()}


class ConstraintFocusPolicy(ReleasePolicy):
    """Gate ONLY on the work centres flagged `is_constraint`.

    For a shop with one resource that genuinely governs output, balancing every
    resource is wasted effort — the simulation literature finds load balancing loses
    its advantage entirely once a strong bottleneck exists, and constraint-driven
    release wins. This is the honest first half of drum-buffer-rope: the drum (release
    paced by the constraint). The rope's time buffer — releasing material a fixed lead
    ahead of the constraint rather than merely capping its queue — is not modelled yet,
    so this is constraint-focused release, not full DBR.

    Falls back to gating everything when no constraint is flagged, because a policy
    that gates on nothing would release the entire pool.
    """

    key = 'constraint'
    label = "Constraint-focused (pace release to the bottleneck)"

    def __init__(self, norm_pct: float = 100.0, constraint_ids: frozenset = frozenset()):
        super().__init__(norm_pct)
        self.constraint_ids = constraint_ids

    def norms(self, ref, capacity: dict) -> dict:
        gated = {k: v for k, v in capacity.items() if k in self.constraint_ids}
        if not gated:
            return super().norms(ref, capacity)
        return {k: hours * self.norm_pct / 100.0 for k, hours in gated.items()}


def build_policy(tenant, config=None) -> ReleasePolicy:
    """The tenant's configured release policy."""
    from Tracker.models import OptimizationConfig, WorkCenter

    cfg = config or OptimizationConfig.objects.filter(tenant=tenant).first()
    pct = float(cfg.workload_norm_pct) if cfg else 100.0
    policy = getattr(cfg, 'release_policy', ReleasePolicy.key) if cfg else ReleasePolicy.key
    if policy == ConstraintFocusPolicy.key:
        ids = frozenset(
            WorkCenter.objects.filter(tenant=tenant, is_constraint=True, is_current_version=True)
            .values_list('id', flat=True))
        return ConstraintFocusPolicy(pct, ids)
    return ReleasePolicy(pct)


# --- work content ----------------------------------------------------------

def _graph(cache: dict, process_id):
    """Steps + edges for a process in the shape `resolve_route` expects (memoised)."""
    from Tracker.models import ProcessStep, StepEdge
    from Tracker.services.scheduling import data as sched_data

    if process_id not in cache:
        steps = tuple(
            sched_data.StepNode(
                step_id=ps.step_id, is_terminal=ps.step.is_terminal,
                requires_first_piece_inspection=ps.step.requires_first_piece_inspection,
                order=ps.order)
            for ps in ProcessStep.objects.filter(process_id=process_id)
            .select_related('step').order_by('order'))
        edges = tuple(
            sched_data.EdgeData(from_step_id=e.from_step_id, to_step_id=e.to_step_id,
                                edge_type=e.edge_type, max_minutes=e.max_minutes)
            for e in StepEdge.objects.filter(process_id=process_id))
        cache[process_id] = (steps, edges)
    return cache[process_id]


def work_content(ref, work_order, cache: dict) -> dict:
    """Remaining work content of a POOL order, keyed like the capacity dict.

    Mirrors the coarse plan's arithmetic (`_route_hours` over `resolve_route`) so a
    release decision and the capacity view can never disagree about how much work an
    order represents. Unreleased orders aren't in `get_active_workorders`, so the
    route is walked from the model rather than the solver's DTOs.
    """
    from Tracker.services.planning.rccp import _route_hours
    from Tracker.services.scheduling import data as sched_data
    from Tracker.services.scheduling.routing import resolve_route

    if work_order.process_id is None:
        return {}
    steps, edges = _graph(cache, work_order.process_id)
    if not steps:
        return {}

    counts: dict = {}
    units = [p for p in work_order.parts.all()
             if p.part_status not in sched_data._UNSCHEDULABLE_PART_STATUSES]
    units += [c for c in work_order.cores.all()
              if c.status not in sched_data._UNSCHEDULABLE_CORE_STATUSES]
    for unit in units:
        if unit.step_id is None:
            continue
        route_ids, _ = resolve_route(unit.step_id, steps, edges)
        for sid in route_ids:
            counts[sid] = counts.get(sid, 0) + 1

    labor, by_wc = _route_hours(ref, counts)
    out = dict(by_wc)
    if labor > 0:
        out[LABOR] = labor
    return out


# --- the recommendation ----------------------------------------------------

def recommend_release(tenant, horizon_days: int | None = None) -> dict:
    """Which pool orders to release now, and why.

    Returns `{policy, norm_pct, resources, decisions, released_count, held_count}`.
    `resources` carries each gating resource's committed / norm / capacity hours so
    the planner sees the arithmetic rather than a verdict.
    """
    from Tracker.models import OptimizationConfig
    from Tracker.services.mes.release import releasable_work_orders
    from Tracker.services.planning.rccp import (
        _load_reference, _route_counts, _route_hours, window_bucket,
    )
    from Tracker.services.scheduling import data as sched_data

    cfg = OptimizationConfig.objects.filter(tenant=tenant).first()
    horizon = sched_data.get_schedule_horizon(tenant, horizon_days)
    ref = _load_reference(tenant)
    bucket = window_bucket(tenant, horizon.start, horizon.end, label="release-window")
    policy = build_policy(tenant, cfg)

    # Capacity of the window, per resource.
    capacity: dict = {LABOR: ref.crew_size * bucket.working_hours}
    for wc_id, (lights_out, attended) in ref.wc_machine_hours.items():
        capacity[wc_id] = (lights_out * bucket.calendar_hours
                           + attended * bucket.working_hours)

    # Committed load = work already released and not finished. Under manual release
    # `get_active_workorders` is exactly the released set, so this is the shop's real
    # current commitment rather than an estimate.
    committed: dict = {k: 0.0 for k in capacity}
    for wo in sched_data.get_active_workorders(tenant):
        labor, by_wc = _route_hours(ref, _route_counts(wo))
        committed[LABOR] = committed.get(LABOR, 0.0) + labor
        for wc_id, hrs in by_wc.items():
            committed[wc_id] = committed.get(wc_id, 0.0) + hrs

    norms = policy.norms(ref, capacity)
    names = {LABOR: f"Labor ({ref.crew_size} crew)", **ref.wc_names}

    cache: dict = {}
    decisions: list[ReleaseDecision] = []
    for wo in releasable_work_orders(tenant):
        hours = work_content(ref, wo, cache)
        blocking = _first_breach(hours, committed, norms)
        if blocking is None:
            for k, v in hours.items():
                committed[k] = committed.get(k, 0.0) + v
            decisions.append(ReleaseDecision(
                str(wo.id), wo.ERP_id, True, "Fits within the workload norms.",
                hours=hours))
        else:
            decisions.append(ReleaseDecision(
                str(wo.id), wo.ERP_id, False,
                f"Would push {names.get(blocking, blocking)} past its workload norm.",
                blocking_resource=names.get(blocking, str(blocking)), hours=hours))

    _starvation_releases(decisions, committed, norms, names)

    return {
        'policy': policy.key,
        'policy_label': policy.label,
        'norm_pct': policy.norm_pct,
        'window_days': round((horizon.end - horizon.start).total_seconds() / 86400),
        'resources': [
            {'name': names.get(k, str(k)),
             'committed_hours': round(committed.get(k, 0.0), 1),
             'norm_hours': round(norms[k], 1),
             'capacity_hours': round(capacity.get(k, 0.0), 1),
             'utilization': (round(committed.get(k, 0.0) / norms[k], 3)
                             if norms[k] > 0 else None)}
            for k in sorted(norms, key=lambda k: names.get(k, str(k)))
        ],
        'decisions': [d.as_dict(names) for d in decisions],
        'released_count': sum(1 for d in decisions if d.release),
        'held_count': sum(1 for d in decisions if not d.release),
    }


def _first_breach(hours: dict, committed: dict, norms: dict):
    """The first gating resource this order would push past its norm, or None.

    Only GATING resources count: a policy that watches one constraint must not hold an
    order because some ungated resource is busy.
    """
    for key, add in hours.items():
        if key not in norms or add <= 0:
            continue
        if committed.get(key, 0.0) + add > norms[key]:
            return key
    return None


def _starvation_releases(decisions, committed, norms, names) -> None:
    """Release held work into any gating resource that has NO committed load.

    Premature idleness — holding an order back while a resource sits idle — is the
    documented failure mode of order release, and it is strictly worse than releasing:
    the shop loses hours it cannot recover and the order is late for nothing. A norm
    is a ceiling on commitment, never a reason to leave a resource starving.

    Mutates `decisions` in place, flipping the first held order that loads each idle
    resource and recording that the norm was deliberately overridden.
    """
    candidates = [k for k, norm in norms.items() if norm > 0]
    for key in candidates:
        # Re-checked per resource, not computed once up front: one order usually feeds
        # several resources at once (its work centre AND the crew pool), so a single
        # release can end two starvations. Deciding the whole set in advance releases a
        # second order for a resource that is no longer idle.
        if committed.get(key, 0.0) > 0:
            continue
        for i, d in enumerate(decisions):
            if d.release or d.hours.get(key, 0.0) <= 0:
                continue
            for k, v in d.hours.items():
                committed[k] = committed.get(k, 0.0) + v
            decisions[i] = ReleaseDecision(
                d.work_order_id, d.erp_id, True,
                f"Released to keep {names.get(key, key)} from standing idle — "
                f"holding work while a resource starves costs hours that can't be "
                f"recovered.",
                hours=d.hours)
            break
