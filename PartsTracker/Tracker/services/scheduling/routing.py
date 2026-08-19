"""
Route resolution for the scheduler (Layer 1).

Turns a process routing graph (`StepNode`s + `EdgeData`s) plus a part's current
step into the part's *remaining nominal route* — the steps it will run if
everything passes — and the precedence among them. Pure graph logic; no ORM, no
OR-Tools. Consumed by `solver.py`.

Design (see the routing discussion in SCHEDULING_IMPLEMENTATION_PLAN.md):
- The nominal route follows **DEFAULT** edges only. ALTERNATE (rework/fail) and
  ESCALATION (max-visits) branches are exceptions — not scheduled up front; a
  re-solve handles a part that actually fails. This keeps the scheduled subgraph
  acyclic even though the full routing graph has rework cycles.
- Scheduling starts at the part's **current step**, so a part mid-process only
  books its remaining work (staggered batches don't re-book completed steps).
- Precedence is returned as edges, not a chain, so genuine convergence/divergence
  (assembly merges, split→parallel→merge) schedule correctly once they appear —
  a node with several predecessors waits for the latest.
- Fallback: a process with no DEFAULT edges is scheduled linearly by
  `ProcessStep.order` from the current step onward.
"""
from __future__ import annotations

from collections import defaultdict

_DEFAULT = 'DEFAULT'


def resolve_route(current_step_id, nodes, edges):
    """Return `(route_step_ids, precedence_edges)` for one part.

    `route_step_ids` is the list of non-terminal steps to schedule (the remaining
    nominal route); `precedence_edges` is a list of `(from_step_id, to_step_id)`
    among them. Empty when there is nothing to schedule.
    """
    node_by_id = {n.step_id: n for n in nodes}
    if not node_by_id:
        return [], []

    # Entry: the part's current step, or the lowest-order node when it is unknown
    # (not started) or no longer on this process version's graph.
    start_id = current_step_id
    if start_id is None or start_id not in node_by_id:
        start_id = min(nodes, key=lambda n: n.order).step_id

    default_adj = defaultdict(list)
    for e in edges:
        if e.edge_type == _DEFAULT:
            default_adj[e.from_step_id].append(e.to_step_id)

    if not default_adj:
        # Linear fallback: ProcessStep.order from the current step onward.
        start_order = node_by_id[start_id].order
        ordered = sorted((n for n in nodes if n.order >= start_order),
                         key=lambda n: n.order)
        sched = [n.step_id for n in ordered if not n.is_terminal]
        prec = list(zip(sched, sched[1:]))
        return sched, prec

    # Walk DEFAULT edges from the current step (cycle-guarded — a well-formed
    # nominal path is acyclic, but a stray back-edge must not loop forever).
    seen: set = set()
    visited: list = []
    stack = [start_id]
    while stack:
        nid = stack.pop()
        if nid in seen or nid not in node_by_id:
            continue
        seen.add(nid)
        visited.append(nid)
        for succ in default_adj.get(nid, ()):
            if succ not in seen:
                stack.append(succ)

    sched_set = {nid for nid in visited if not node_by_id[nid].is_terminal}
    sched_ids = [nid for nid in visited if nid in sched_set]
    prec = [
        (e.from_step_id, e.to_step_id) for e in edges
        if e.edge_type == _DEFAULT
        and e.from_step_id in sched_set and e.to_step_id in sched_set
    ]
    return sched_ids, prec
