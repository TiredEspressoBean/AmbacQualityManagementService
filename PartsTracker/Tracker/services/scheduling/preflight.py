"""Pre-solve labor feasibility.

A step gated by a `TrainingRequirement` can only be run by a certified operator. If no
DISPATCHABLE operator (active, internal, rostered to a shift) holds the certification,
that step is *unstaffable*: any part whose remaining route passes through it cannot
actually be produced, whatever the machine schedule claims. Surfacing this before the
solve lets the planner train/roster someone instead of shipping a plan with work that
can never be covered.
"""
from __future__ import annotations

from collections import defaultdict


class LaborInfeasible(Exception):
    """Raised to REFUSE a solve: a step in the active work requires a certification no
    rostered operator holds, so the plan could never be executed. Carries the gap list
    (from `find_unstaffable_steps`) so the caller can tell the planner what to fix."""

    def __init__(self, gaps: list[dict]):
        self.gaps = gaps
        summary = "; ".join(
            f"{g['step_name']} needs {'/'.join(g['required_training'])}" for g in gaps[:5]
        )
        more = "" if len(gaps) <= 5 else f" (+{len(gaps) - 5} more)"
        super().__init__(
            f"{len(gaps)} step(s) require training no rostered operator holds: "
            f"{summary}{more}"
        )


def find_unstaffable_steps(tenant) -> list[dict]:
    """Training-gated steps in the active work that no dispatchable operator can run.

    Returns one entry per (step, process) with a training requirement and zero qualified
    dispatchable operators: ``{step_id, step_name, process, required_training[],
    parts_affected}``. Empty list ⇒ every certification-gated step is staffable.
    """
    from Tracker.models import Processes, Steps
    from Tracker.services.scheduling import data
    from Tracker.services.scheduling.routing import resolve_route
    from Tracker.services.training import (
        get_qualified_users_for_step, get_required_training,
    )

    wos = data.get_active_workorders(tenant)
    op_ids = {o.user_id for o in data.get_dispatchable_operators(tenant)}
    # Effective labor model per step. A step set to OFF imposes no crew constraint —
    # the solver never models an operator for it — so a missing certification there must
    # NOT block the whole solve (that would contradict OFF's meaning).
    labor_models = data.get_step_labor_models(tenant)

    # (step_id, process_id) -> number of parts whose remaining route hits it. Reman
    # cores are parts, so they are counted here too.
    pairs: dict = defaultdict(int)
    for wo in wos:
        by_step: dict = defaultdict(int)
        for p in wo.parts:
            by_step[p.current_step_id] += 1
        for start_step, n in by_step.items():
            route_ids, _ = resolve_route(start_step, wo.steps, wo.edges)
            for sid in route_ids:
                pairs[(sid, wo.process_id)] += n

    steps = {s.id: s for s in Steps.objects.filter(tenant=tenant)}
    procs = {p.id: p for p in Processes.objects.filter(tenant=tenant)}

    gaps = []
    for (sid, pid), n in pairs.items():
        step = steps.get(sid)
        if step is None:
            continue
        if labor_models.get(sid) == 'off':
            continue  # OFF steps aren't crew-constrained — never a staffing blocker
        proc = procs.get(pid)
        required = get_required_training(step, process=proc)
        if not required:
            continue  # any operator can run it — not a *trained*-human gap
        qualified = {u.id for u in get_qualified_users_for_step(step, process=proc, tenant=tenant)}
        if not (qualified & op_ids):
            gaps.append({
                'step_id': str(sid),
                'step_name': step.name,
                'process': proc.name if proc else None,
                'process_id': pid,
                'required_training': sorted(tt.name for tt in required),
                'parts_affected': n,
                'holders': _holder_notes(tenant, required, op_ids),
            })
    gaps.sort(key=lambda g: -g['parts_affected'])
    return gaps


def _holder_notes(tenant, required: dict, op_ids: set) -> list[str]:
    """Everyone with a record against a required training, and why they don't count —
    "<name> (inactive)", "<name> (<cert> expired Oct 29)". The planner's fix is
    usually one of these people, so naming them beats naming only the cert."""
    from django.db.models import Q
    from Tracker.models import TenantMembership, TrainingRecord, User
    from Tracker.services.core.clock import tenant_today
    from Tracker.services.training import _lineage_ids, training_type_lineage

    today = tenant_today(tenant)
    lineage = training_type_lineage(tenant.id)
    active = set(TenantMembership.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, status='ACTIVE').values_list('user_id', flat=True))
    why: dict = {}
    for tt, min_level in required.items():
        recs = (TrainingRecord.objects.filter(  # tenant-safe: ids from the tenant-filtered lineage
                    archived=False, training_type_id__in=_lineage_ids(lineage, tt.id))
                .values('user_id', 'level', 'expires_date'))
        best: dict = {}
        for r in recs:
            cur = best.get(r['user_id'])
            in_date = r['expires_date'] is None or r['expires_date'] >= today
            key = (in_date, r['level'] >= min_level)
            if cur is None or key > cur[0]:
                best[r['user_id']] = (key, r)
        for uid, ((in_date, level_ok), r) in best.items():
            if not level_ok:
                reason = f"below the level {tt.name} requires"
            elif not in_date:
                reason = f"{tt.name} expired {r['expires_date']:%b %d}"
            else:
                reason = None   # holds it; the account or roster decides
            # First disqualifying reason across the required types wins.
            why[uid] = why.get(uid) or reason
    users = {u.id: u for u in User.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, id__in=why)}
    notes = []
    for uid, reason in why.items():
        u = users.get(uid)
        if u is None:
            continue
        if not u.is_active or uid not in active:
            reason = "inactive"
        elif reason is None and uid not in op_ids:
            reason = "not on the shop-floor roster"
        if reason:
            notes.append(f"{u.display_name} ({reason})")
    return sorted(notes)
