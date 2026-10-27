"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`).

Layers built so far:
- Lot-based route-aware tasks: a WO's parts at the SAME current step form one lot that
  moves through the remaining nominal route together (DEFAULT edges; rework/scrap
  excluded), scheduled as one machine occupancy per operation sized by the lot's piece
  count (cycle × count). Parts stranded at different steps form separate lots. Written
  back per part (each shares the lot's window) so tracking/pins stay part-grained.
  Merge-capable DAG precedence (see `routing.resolve_route`). A reman core is a part
  (Documents/CORE_AS_PART_DESIGN.md): teardown cores batch like any part, and a core
  under rebuild schedules on its own (`PartData.individual`) since its scope is its own.
- Lock-step batches: a WO's parts at one step schedule as one cohesive lot (one
  occupancy, one synchronized start). A part split off to rework (`split_from_lot`) is
  carved into its OWN lot so the cohort keeps progressing — the batch is NOT held for a
  straggler; the split part schedules its own rework path and re-converges later via
  `rejoin_part_to_lot` (`Parts.rejoined_at`), else at finished goods.
- Machine choice: one of the step's eligible schedulable machines (optional intervals
  + exactly-one), honoring per-machine `cycle_time_override`; one task per machine.
- Cost objective (integer cents): Σ (lot lateness × the WO's priority penalty) +
  makespan tiebreaker + a small preferred/dialed-in machine nudge.
- Durations carry a PFD (personal/fatigue/delay) allowance on attended run time.
- Calendars: machines run lights-out (24/7, blocked only by downtime) by default, so a
  lot-operation may span nights/weekends; machines flagged `runs_unattended=False` are
  confined to the shift calendar instead.
- Labor capacity: concurrent attended operations are capped at the crew on shift (one
  operator per lot-op) AND, for training-gated steps, at the qualified crew on shift —
  so a scarce skill (e.g. one assembler) serializes and pushes work late instead of
  piling up uncoverable, and attended work is kept to staffed hours while machines run
  unattended. A step no rostered operator is trained for — or whose every machine is
  down for the whole horizon — is planned up to, not past: that lot's route stops
  there and Not scheduled says why. Breaks are not modelled here; dispatch honours
  actual break clock-outs.
- Secondary resources: a step's schedulable gauges (Keyence/CMM) are reserved
  one-at-a-time while the task runs.
- Fixtures: shared tooling as a cumulative resource (≤ quantity concurrent users).
- Setup/changeover: sequence-dependent transition gaps between machine neighbours.
- Continuous machines: throughput-based duration + recurring bar-change downtime.
- Time fences + warm-start: frozen-zone and planner-pinned operations are HELD (hard,
  decided 2026-10-21) — same machine, same operator where possible, same order on the
  machine, start only sliding later. One that can't happen there any more is freed
  and reported with its reason; held ops that collide slide in order. The solver
  never loosens the fence: a solve that still finds no plan fails, and the live plan
  stays on the board with the reason.
  Slushy operations carry a stickiness cost on the lateness scale; liquid ones are
  only warm-start hints.
- Cross-WO pegs: a component WO must finish (+ staging buffer) before its parent
  assembly WO starts (WorkOrder.pegged_to_workorder; multi-level chains transitively).

Follow-ons: changeover-as-circuit (scalability), transfer-batching. Time is
discretized to integer minutes from `horizon.start`; results are written back as
absolute datetimes.

Shape: `shop.Shop` loads the inputs once; `_Phase` builds and solves one CP-SAT model
over them; `_solve_with_fence` runs the phases;
`write_back.persist` writes the result back. The pure terms (durations, penalties,
minute arithmetic) are in `solver_terms`.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta

from Tracker.services.scheduling.routing import resolve_route
from Tracker.services.scheduling.shop import Shop
from Tracker.services.scheduling.solver_terms import (
    _AFFINITY_PENALTY_DEFAULT, _CURE_WINDOW_WEIGHT, _SLIDE_WEIGHT_FACTOR,
    _affinity_penalty, _batch_cycle_dur, _chosen_machine, _due_minutes, _dur,
    _dur_on_machine, _overlaps, _penalty_cents_per_min, _release_minutes,
    _cp_solve, _staffing_segments, _transition,
)
from Tracker.services.scheduling.write_back import persist
from Tracker.utils.tenant_context import tenant_context

logger = logging.getLogger(__name__)


def solve_schedule(tenant, time_limit_seconds: int | None = None, draft: bool = False):
    """Solve the Layer-1 machine schedule for a tenant and persist it as the new
    active `ScheduleResult`. Returns the ScheduleResult (empty + OPTIMAL when there
    is no work).

    `time_limit_seconds` None = the planner's Solve time limit from Scheduling
    settings — how long a run takes is theirs to choose."""
    with tenant_context(str(tenant.id)):
        shop = Shop(tenant)
        if time_limit_seconds is None:
            time_limit_seconds = int(
                getattr(shop.config, 'solver_time_limit_seconds', None) or 180)
        final, machine_solve_ms, operator_solve_ms = _solve_with_fence(shop, time_limit_seconds)
        return persist(shop, final, machine_solve_ms, operator_solve_ms, draft)


def _lots(wo, prev_map) -> list[dict]:
    """A work order's parts grouped into lots, each moving its remaining route together.

    Lot-based scheduling: a WO's parts sitting at the SAME current step form one
    cohesive lot that moves the remaining route together — one machine occupancy per
    operation, sized by the lot's piece count (cycle × count; setup is the changeover
    gap). Lock-step lives HERE: co-located cohort parts schedule as one lot with a
    single start.
    Carve-out: a part split off to rework (`split_from_lot`) is grouped into its OWN lot
    (keyed by split-state) so it never drags the cohort — the cohort keeps progressing,
    and the split part schedules its own rework path and re-converges later via
    rejoin_part_to_lot. Cores schedule individually.
    The solver only ever *batches* — it groups the UNPINNED cohort into one lot
    (lock-step, within this WO) and never breaks a lot on its own. A planner PIN is what
    fixes a part in place, so each distinct pinned (start, machine) becomes its own fixed
    lot — that's how a manual "break apart" (pin the parts to separate slots) holds, and
    how a manual "merge" (pin them onto one slot) locks a batch. Quality stragglers
    (`split_from_lot`) keep their own lot as before. Unpinned → the cohort lot the
    solver places freely and batches."""
    def _group_key(p):
        if p.individual:
            # A core under rebuild: its scope is its own, so it never moves in
            # lock-step with another unit. (Teardown cores batch like parts.)
            return ('u', p.part_id)
        if p.split_from_lot:
            return ('q',)  # quality carve-out → its own lot
        prev = prev_map.get((p.part_id, p.current_step_id))
        if prev is not None and prev.is_pinned:
            return ('p', prev.start_time, prev.machine_id)  # planner-fixed slot
        return ('c',)  # unpinned cohort → one solver-batched lot

    pdata = {p.part_id: p for p in wo.parts}
    part_batches: dict = defaultdict(list)
    for p in wo.parts:
        part_batches[(p.current_step_id, _group_key(p))].append(p.part_id)
    lots = []
    for (step, gk), pids in part_batches.items():
        # A lot is in-progress if any of its parts has already started this step;
        # elapsed = the longest-running part (earliest start → most elapsed), so
        # the solver schedules only the remaining duration of the running lot.
        ip_parts = [pdata[pid] for pid in pids if pdata[pid].in_progress]
        lots.append({'label': f"b{wo.wo_id}:{step}:{gk[0]}", 'step': step,
                     'part_ids': tuple(pids), 'count': len(pids),
                     'in_progress': bool(ip_parts),
                     'elapsed': max((p.elapsed_minutes for p in ip_parts), default=0.0)})
    return lots


class _Phase:
    """One solve phase: a CP-SAT model over the shop, built then solved.

    `labor_override`: None keeps each step's own labor_model; 'pool' forces non-off
    steps to the cheap cumulative (the fast MACHINE phase); 'named' forces exact
    per-operator assignment (the OPERATOR phase).

    NB: scheduled breaks/lunch are NOT enforced here. In the lights-out model a
    machine keeps running through a break; operator presence for the attended
    portions is a Layer-2 concern, and dispatch already honors break TimeEntries."""

    def __init__(self, shop: Shop, labor_override=None):
        from ortools.sat.python import cp_model

        self.shop = shop
        self.labor_override = labor_override
        self.model = cp_model.CpModel()
        self.tasks: list[dict] = []
        self.machine_intervals: dict = defaultdict(list)
        self.machine_tasks: dict = defaultdict(list)   # equip_id -> [(present, start, end, step_id, setup, wo_id)]
        self.gauge_intervals: dict = defaultdict(list)
        self.fixture_intervals: dict = defaultdict(list)
        self.lateness_cost = []
        self.lateness_terms = []   # (lateness_var, penalty) — for the isolated lateness total
        self.affinity_cost = []    # small penalties nudging toward preferred/dialed-in machines
        self.labor_intervals = []  # (attended_interval, step_id, model) per attended lot-op
        self.named_op_intervals: dict = defaultdict(list)  # user_id -> [optional intervals]
        self.named_uncovered = []  # soft penalty terms for unassignable NAMED lots
        self.warm_hints = []   # (start_var, minute) warm-start hints from the previous schedule
        self.max_time_penalty = []  # soft penalty terms for blown max-time-between-ops windows
        self.max_time_viols = []    # (viol_bool, task_dict) — flag the op post-solve if relaxed
        self.stick_terms = []   # ('dev', var, weight) | ('mach', lit, weight) — the slushy term
        self.freed = []         # frozen/pinned operations sent back to planning, with why
        self.kept = 0           # frozen/pinned operations held exactly
        self.fixed_by_operator: dict = defaultdict(list)  # user_id -> [(s, e)] attended, fixed
        self.fixed_attended: list = []   # [(s, e)] attended spans of held work (crew cap)
        self.slide_terms: list = []   # minutes each held operation slid past its planned start
        self.held_on_machine: dict = defaultdict(list)  # equip -> [(planned_raw, start, end, step, setup, wo)]
        self.wo_starts: dict = defaultdict(list)   # wo_id -> [start vars] (for peg gating)
        self.wo_ends: dict = defaultdict(list)     # wo_id -> [end vars]   (for peg completion)
        self.wo_step_starts: dict = defaultdict(list)  # (wo_id, step_id) -> [start vars]

    def labor_model(self, step_id) -> str:
        base = self.shop.labor_models.get(step_id, 'pool')
        return 'off' if base == 'off' else (self.labor_override or base)

    # --- building --------------------------------------------------------------

    def build(self, machine_hints=None):
        for wo in self.shop.wos:
            self._add_work_order(wo)
        self._add_pegs()
        self._add_held_order()
        self._add_machine_capacity()
        self._add_changeovers()
        self._add_gauges_and_fixtures()
        self._add_labor_capacity()
        self._set_objective()
        self._add_hints(machine_hints)

    def _add_work_order(self, wo):
        shop = self.shop
        due_minutes = _due_minutes(wo.expected_completion, shop.horizon.start, shop.H)
        release_min = _release_minutes(wo.expected_start, shop.horizon.start, shop.H)
        penalty = _penalty_cents_per_min(shop.config, wo.priority)
        for lot in _lots(wo, shop.prev_map):
            self._add_lot(wo, lot, due_minutes, release_min, penalty)

    def _add_lot(self, wo, lot, due_minutes, release_min, penalty):
        shop, model, H = self.shop, self.model, self.shop.H
        # The lot's remaining NOMINAL route from its current step (DEFAULT
        # edges; rework/scrap branches excluded), with merge-capable DAG
        # precedence so convergence/divergence nodes schedule correctly.
        # A core under rebuild books the main line like any part: nothing on
        # it is skipped (services/reman/repair_routing).
        route_ids, prec = resolve_route(lot['step'], wo.steps, wo.edges)
        # Plan up to a step nobody rostered can run, not past it: that step
        # and everything after it on this lot wait, and Not scheduled says why
        # (diagnostics). A running op is already staffed, so it stays.
        # Same for a step whose every machine is down for the whole horizon.
        cut = {sid for sid in route_ids
               if ((sid, wo.process_id) in shop.unstaffable or sid in shop.unrunnable)
               and not (lot.get('in_progress') and sid == lot['step'])}
        if cut:
            frontier = list(cut)
            while frontier:
                here = frontier.pop()
                for a, b in prec:
                    if a == here and b not in cut:
                        cut.add(b)
                        frontier.append(b)
            route_ids = [sid for sid in route_ids if sid not in cut]
            prec = [(a, b) for a, b in prec if a not in cut and b not in cut]
        node_start: dict = {}
        node_end: dict = {}
        node_task: dict = {}   # step_id -> task dict (to flag cure-window violations)
        lot_ends = []
        for step_id in route_ids:
            timing = shop.timings.get(step_id)
            eligible = [a for a in shop.affinities.get(step_id, []) if a.is_schedulable]
            key = f"{lot['label']}_{step_id}"
            # Up to H_ext, not H: work that doesn't fit the horizon overflows past it
            # (reported, not written) instead of making the whole solve infeasible.
            start = model.NewIntVar(0, shop.H_ext, f"s_{key}")
            end = model.NewIntVar(0, shop.H_ext, f"e_{key}")
            op = dict(wo=wo, lot=lot, step_id=step_id, timing=timing, eligible=eligible,
                      key=key, start=start, end=end, release_min=release_min,
                      due_minutes=due_minutes, penalty=penalty)
            # Outside processing first, so a sent-out part isn't treated as a machine op;
            # only the first route step (== lot['step']) can be in progress.
            if step_id in shop.osp_minutes:
                task = self._outside_op(**op)
            elif lot.get('in_progress') and step_id == lot['step']:
                task = self._running_op(**op)
            else:
                task = self._planned_op(**op)
            node_start[step_id] = start
            node_end[step_id] = end
            node_task[step_id] = task
            lot_ends.append(end)

        # Merge-capable precedence: for each DEFAULT edge
        # start[to] >= end[from] + move_min (inter-op transport/queue gap);
        # a node with several predecessors waits for the latest (max) of them.
        # Max-time-between-ops (cure/coat/pot-life): a SOFT upper bound
        # start[to] <= end[from] + max_minutes — met unless capacity can't, then
        # the op is flagged (cure_violation) and penalized, never hard-INFEASIBLE.
        max_by_edge = {(e.from_step_id, e.to_step_id): e.max_minutes
                       for e in wo.edges if e.max_minutes}
        for from_id, to_id in prec:
            if from_id in node_task and to_id in node_task:
                node_task[to_id]['preds'].append(node_task[from_id])
            if from_id in node_end and to_id in node_start:
                model.Add(node_start[to_id] >= node_end[from_id] + shop.move_min)
                max_m = max_by_edge.get((from_id, to_id))
                if max_m is not None:
                    viol = model.NewBoolVar(f"cure_{lot['label']}_{from_id}_{to_id}")
                    model.Add(
                        node_start[to_id] <= node_end[from_id] + max_m
                    ).OnlyEnforceIf(viol.Not())
                    self.max_time_penalty.append(viol * _CURE_WINDOW_WEIGHT)
                    if to_id in node_task:
                        self.max_time_viols.append((viol, node_task[to_id]))

        self.wo_starts[wo.wo_id].extend(node_start.values())
        self.wo_ends[wo.wo_id].extend(node_end.values())
        for sid, s in node_start.items():
            self.wo_step_starts[(wo.wo_id, sid)].append(s)

        # Lateness is per-LOT (the lot is late or not) — not per piece, so a big
        # WO no longer swamps the objective with count-many identical late terms.
        if due_minutes is not None and penalty > 0 and lot_ends:
            lot_done = model.NewIntVar(0, shop.H_ext, f"done_{lot['label']}")
            model.AddMaxEquality(lot_done, lot_ends)   # DAG completion = last sink
            # Due can be up to H in the past (`_due_minutes`).
            lateness = model.NewIntVar(0, shop.H_ext + H, f"late_{lot['label']}")
            model.Add(lateness >= lot_done - due_minutes)
            self.lateness_cost.append(lateness * penalty)
            self.lateness_terms.append((lateness, penalty))  # for the isolated total

    def _outside_op(self, *, wo, lot, step_id, timing, eligible, key, start, end,
                    release_min, due_minutes, penalty) -> dict:
        """Outside processing: a subcontract op runs OFF-SITE — no machine, no crew, on
        calendar (24/7) time, for the vendor turnaround. Precedence alone gates
        downstream on its return. Parts already at the vendor pin to their expected
        return (shipped_at + turnaround)."""
        shop, model, H = self.shop, self.model, self.shop.H
        dur = shop.osp_minutes[step_id]
        if release_min:
            model.Add(start >= release_min)
        ret = min((shop.osp_return[pid] for pid in lot['part_ids']
                   if pid in shop.osp_return), default=None)
        if ret is not None:
            ret = max(1, min(H, ret))
            model.Add(end == ret)
            model.Add(start == max(0, ret - dur))
        else:
            model.Add(end == start + dur)
            # Frozen and not yet sent: like any held op it may slide
            # later but never earlier — shipping out sooner is a shop
            # act (packing, a truck) the fence promised not to move.
            osp_prev = [shop.prev_map[(pid, step_id)] for pid in lot['part_ids']
                        if (pid, step_id) in shop.prev_map]
            if osp_prev:
                first = min(pt.start_time for pt in osp_prev)
                raw = -int(-(first - shop.horizon.start).total_seconds() // 60)
                if 0 <= raw < shop.frozen_min:
                    model.Add(start >= min(raw, max(0, H - dur)))
        self.tasks.append({'part_ids': lot['part_ids'], 'wo_id': wo.wo_id,
                           'step_id': step_id, 'start': start, 'end': end,
                           'choices': [], 'pinned': ret is not None,
                           'planner_pinned': False, 'named_assign': [],
                           'requires_operator': False, 'in_progress': False,
                           'durs': {}, 'dur_free': dur, 'est': release_min,
                           'due': due_minutes, 'prio': penalty, 'preds': [],
                           'fixed_pos': ((max(0, ret - dur), ret, None)
                                         if ret is not None else None)})
        return self.tasks[-1]

    def _running_op(self, *, wo, lot, step_id, timing, eligible, key, start, end,
                    release_min, due_minutes, penalty) -> dict:
        """In-progress: the lot's CURRENT step is physically running. Pin it to start
        "now" (0) with only its REMAINING duration, on the machine it's on, so a re-solve
        can't shove a running op later or re-charge time already spent. Setup is done
        (charge none); no soft pin needed (it's hard-fixed); labor for the remainder
        isn't re-demanded."""
        shop, model, H = self.shop, self.model, self.shop.H
        full_dur = _dur(timing, None, shop.pfd_factor, lot['count'])
        remaining = max(1, min(H, full_dur - int(round(lot['elapsed']))))
        model.Add(start == 0)
        model.Add(end == remaining)
        prev_here = [shop.prev_map[(pid, step_id)] for pid in lot['part_ids']
                     if (pid, step_id) in shop.prev_map]
        fixed_m = None
        if prev_here:
            repm = min(prev_here, key=lambda pt: pt.start_time).machine_id
            if repm and any(a.equipment_id == repm for a in eligible):
                fixed_m = repm
        # The machine it's running on went down: it isn't running
        # there any more, so don't hold the remainder on it (that
        # made the whole model infeasible — walk 2026-10-22).
        if fixed_m is not None:
            run_end = shop.horizon.start + timedelta(minutes=remaining)
            if any(s < run_end and e > shop.horizon.start
                   for s, e in shop.machine_downtime.get(fixed_m, ())):
                fixed_m = None
        choices = []
        if fixed_m is not None:
            lit = model.NewBoolVar(f"ip_{key}_{fixed_m}")
            model.Add(lit == 1)
            iv = model.NewOptionalFixedSizeIntervalVar(start, remaining, lit, f"ipi_{key}")
            self.machine_intervals[fixed_m].append(iv)
            self.machine_tasks[fixed_m].append((lit, start, end, step_id, 0, wo.wo_id))
            choices.append((lit, fixed_m))
        else:
            model.NewIntervalVar(start, remaining, end, f"ipi_{key}")
        self.tasks.append({'part_ids': lot['part_ids'], 'wo_id': wo.wo_id,
                           'step_id': step_id, 'start': start, 'end': end,
                           'choices': choices, 'pinned': True,
                           'planner_pinned': False, 'named_assign': [],
                           'requires_operator': False, 'in_progress': True,
                           'durs': {}, 'dur_free': remaining, 'est': 0,
                           'due': due_minutes, 'prio': penalty, 'preds': [],
                           'fixed_pos': (0, remaining, fixed_m)})
        return self.tasks[-1]

    def _planned_op(self, *, wo, lot, step_id, timing, eligible, key, start, end,
                    release_min, due_minutes, penalty) -> dict:
        """An operation still to plan: its gates, its machine, the gauges/fixtures and
        crew it ties up, and the time fence from the live plan."""
        shop, model = self.shop, self.model
        if release_min:
            model.Add(start >= release_min)   # earliest-release gate
        # Buy-side material availability: gate the consuming op on the
        # earliest incoming receipt when purchased material is short; flag
        # the op when it's short with no known receipt date.
        mat_lb = max(shop.material_release.get((wo.wo_id, step_id), 0),
                     shop.material_release.get((wo.wo_id, None), 0))
        if mat_lb:
            model.Add(start >= mat_lb)
        mat_short = ((wo.wo_id, step_id) in shop.material_short
                     or (wo.wo_id, None) in shop.material_short)
        mat_detail = (shop.material_detail.get((wo.wo_id, step_id))
                      or shop.material_detail.get((wo.wo_id, None)) or "")

        choices, durs, dur_free = self._machine_choice(
            wo, step_id, timing, eligible, key, start, end, lot['count'])
        self._occupancy(step_id, key, start, end)
        lm, named_assign, front_len = self._labor(step_id, timing, key, start, end, lot['count'])
        fence = self._fence(wo, lot, step_id, timing, key, start, end, release_min, mat_lb,
                            choices, durs, dur_free, lm, named_assign, front_len)

        self.tasks.append({'part_ids': lot['part_ids'], 'wo_id': wo.wo_id,
                           'step_id': step_id,
                           'start': start, 'end': end, 'choices': choices,
                           'pinned': fence['pinned'], 'planner_pinned': fence['planner_pinned'],
                           'fixed_start_dt': fence['fixed_start_dt'],
                           'held_minute': fence['held_minute'],
                           'op_unfixed': fence['op_unfixed'],
                           'named_assign': named_assign,
                           'requires_operator': lm != 'off',
                           'material_short': mat_short,
                           'material_detail': mat_detail,
                           'durs': durs, 'dur_free': dur_free,
                           'est': max(release_min, mat_lb), 'due': due_minutes,
                           'prio': penalty, 'preds': [], 'fixed_pos': fence['held_pos'],
                           'warm': fence['warm_start']})
        return self.tasks[-1]

    def _machine_choice(self, wo, step_id, timing, eligible, key, start, end, count):
        """One of the step's eligible machines (optional intervals + exactly-one), or a
        machine-free interval. Returns `(choices, durs, dur_free)`."""
        shop, model = self.shop, self.model
        setup_int = int(round(timing.setup_minutes)) if timing else 0
        choices = []
        durs: dict = {}     # equip_id -> lot minutes on that machine
        dur_free = None     # lot minutes when the step uses no machine
        if eligible:
            for a in eligible:
                if a.equipment_id in shop.cycle_cap:
                    # Furnace/oven: fixed cycle time per load, ceil(count/cap)
                    # loads back-to-back (not per-part time).
                    dur = _batch_cycle_dur(timing, shop.cycle_cap[a.equipment_id], count)
                else:
                    dur = _dur_on_machine(timing, a, shop.continuous, shop.pfd_factor, count)
                durs[a.equipment_id] = dur
                lit = model.NewBoolVar(f"m_{key}_{a.equipment_id}")
                opt = model.NewOptionalFixedSizeIntervalVar(start, dur, lit, f"i_{key}_{a.equipment_id}")
                self.machine_intervals[a.equipment_id].append(opt)
                self.machine_tasks[a.equipment_id].append(
                    (lit, start, end, step_id, setup_int, wo.wo_id))
                model.Add(end == start + dur).OnlyEnforceIf(lit)
                choices.append((lit, a.equipment_id))
                penalty_lvl = _affinity_penalty(a.affinity)
                if penalty_lvl:
                    self.affinity_cost.append(lit * penalty_lvl)  # pay iff this machine is chosen
            model.AddExactlyOne([lit for lit, _ in choices])
        else:
            dur = _dur(timing, None, shop.pfd_factor, count)
            dur_free = dur
            model.NewIntervalVar(start, dur, end, f"i_{key}")
        return choices, durs, dur_free

    def _occupancy(self, step_id, key, start, end):
        """Occupancy interval for the finite secondary resources the lot ties up while
        it runs — measurement gauges and shared fixtures."""
        shop, model = self.shop, self.model
        if step_id in shop.occupancy_steps:
            size = model.NewIntVar(1, shop.H, f"sz_{key}")
            occ = model.NewIntervalVar(start, size, end, f"occ_{key}")
            for gauge_id in shop.secondary.get(step_id, ()):
                self.gauge_intervals[gauge_id].append(occ)
            for fixture_id in shop.fixture_by_step.get(step_id, ()):
                self.fixture_intervals[fixture_id].append(occ)

    def _labor(self, step_id, timing, key, start, end, count):
        """Labor demand: ONE operator tends the lot at this operation (not one per
        piece). Full-attention → tied to the whole run; otherwise only the front touch,
        the machine then running on its own: setup + a load/unload per piece, or setup
        alone when a robot does the handling (`TimingData.operator_attended_time` — the
        same rule dispatch and capacity planning use). Feeds the crew-capacity
        cumulative. Returns `(lm, named_assign, front_len)`."""
        shop, model = self.shop, self.model
        lm = self.labor_model(step_id)
        named_assign: list = []  # (op_id, assign_lit) chosen in the NAMED phase
        front_len = None         # attended minutes for a load/unload step
        if lm != 'off':
            full = timing is None or timing.attention_type == 'full'
            if full:
                asz = model.NewIntVar(0, shop.H, f"asz_{key}")
                att_iv = model.NewIntervalVar(start, asz, end, f"att_{key}")
            else:
                front = int(round(timing.operator_attended_time(count)))
                front_len = front
                att_iv = (model.NewFixedSizeIntervalVar(start, front, f"att_{key}")
                          if front > 0 else None)
            if att_iv is not None:
                self.labor_intervals.append((att_iv, step_id, lm))
                if lm == 'named':
                    # Assign a SPECIFIC qualified operator to this lot (exact
                    # dual-resource): optional per-operator intervals a
                    # per-operator NoOverlap serialises, so a scarce specialist
                    # pushes the work late rather than leaving it uncovered.
                    # Coverage is HARD (exactly one operator) whenever someone
                    # qualified is on shift in the horizon with a cert that lasts it
                    # (user decision 2026-10-27): the old soft fallback needed a
                    # weight above everything else in the objective, which wrecked
                    # CP-SAT's bound. Only an op whose qualified people all lapse or
                    # are never on shift keeps the soft `uncov` escape.
                    pool = shop.skill_pools.get(step_id)
                    qualified = (pool if pool is not None else shop.all_op_ids) & shop.all_op_ids
                    assign_lits = []
                    lapses = shop.qual_lapse.get(step_id, {})
                    for op in qualified:
                        lit = model.NewBoolVar(f"na_{key}_{op}")
                        if op in lapses:
                            # Their cert runs out mid-horizon: only work
                            # finished by then is theirs to take.
                            model.Add(end <= lapses[op]).OnlyEnforceIf(lit)
                        if full:
                            oiv = model.NewOptionalIntervalVar(start, asz, end, lit, f"noi_{key}_{op}")
                        else:
                            oiv = model.NewOptionalFixedSizeIntervalVar(start, front, lit, f"noi_{key}_{op}")
                        self.named_op_intervals[op].append(oiv)
                        assign_lits.append(lit)
                        named_assign.append((op, lit))
                    if assign_lits and any(op not in lapses and shop.op_minutes.get(op)
                                           for op in qualified):
                        model.AddExactlyOne(assign_lits)
                    elif assign_lits:
                        uncov = model.NewBoolVar(f"nunc_{key}")
                        model.Add(sum(assign_lits) + uncov == 1)
                        self.named_uncovered.append(uncov)   # weighted coverage-first below
        return lm, named_assign, front_len

    def _fence(self, wo, lot, step_id, timing, key, start, end, release_min, mat_lb,
               choices, durs, dur_free, lm, named_assign, front_len) -> dict:
        """Time fence from the live plan. A lot inherits the state of its parts:
        planner-pinned if ANY part was, else frozen if its earliest part started inside
        the frozen zone. Frozen/pinned -> held EXACTLY (start, machine, operator) unless
        it can't happen there any more; slushy -> a stickiness cost on the lateness
        scale; liquid -> only a warm-start hint."""
        shop, model, H = self.shop, self.model, self.shop.H
        out = {'pinned': False,          # held fixed this solve
               'planner_pinned': False,  # the DB is_pinned flag — planner lock ONLY
               'fixed_start_dt': None,   # the live plan's exact start, for write-back
               'held_minute': None,      # the held minute, for exact write-back
               'held_pos': None,         # (start, end, machine) when held, for the greedy hint
               'op_unfixed': None,       # held op whose operator couldn't be kept
               'warm_start': None}       # the live plan's start when only hinted
        prevts = [shop.prev_map[(pid, step_id)] for pid in lot['part_ids']
                  if (pid, step_id) in shop.prev_map]
        if not prevts:
            return out
        rep = min(prevts, key=lambda pt: pt.start_time)
        any_pinned = any(pt.is_pinned for pt in prevts)
        # Ceiling, not floor: the horizon starts at "now", so an
        # operation the last plan put at "now" is a few seconds in the
        # past on the next solve. Flooring read that as minute -1 — a
        # passed slot — and freed it and everything after it.
        prev_raw = -int(-(rep.start_time - shop.horizon.start).total_seconds() // 60)
        prev_start = max(0, min(H, prev_raw))
        fence_held = any_pinned or prev_raw < shop.frozen_min
        why = None
        if fence_held:
            why = shop.frozen_refusal(
                prev_raw=prev_raw, rep=rep, release_min=release_min,
                mat_lb=mat_lb, choices=choices, durs=durs,
                dur_free=dur_free, step_id=step_id, lm=lm, front_len=front_len,
                fixed_attended=self.fixed_attended)
        if fence_held and why is None:
            # Held: same machine, start no earlier than its slot. Held work on a
            # machine keeps its order and slides back together (`_add_held_order`),
            # so held work colliding with held work is never infeasible — it slides.
            fixed_m = rep.machine_id if choices else None
            op_dur = durs.get(fixed_m) if fixed_m else dur_free
            model.Add(start >= prev_start)
            slide = model.NewIntVar(0, shop.H_ext, f"slide_{key}")
            model.Add(slide >= start - prev_start)
            self.slide_terms.append(slide)
            if fixed_m is not None:
                # Ordered by the planned minute itself — negative for a slot gone
                # by. Clamped to "now", every passed slot tied at 0 and could be
                # put in any order, e.g. a part's second op ahead of its first:
                # a cycle with the route, so no plan at all.
                self.held_on_machine[fixed_m].append(
                    (prev_raw, start, end, step_id,
                     int(round(timing.setup_minutes)) if timing else 0,
                     wo.wo_id))
            for lit, eqid in choices:
                model.Add(lit == (1 if eqid == fixed_m else 0))
            # Keep its operator too — unless that person is already held
            # on other fixed work then. Operators on the live plan may
            # come from Dispatch, which models attention differently
            # from this solve; fixing every one exactly double-booked
            # people and made the whole fixed set infeasible (walk
            # 2026-10-21). Nor someone whose cert for the step lapses in
            # the horizon: held work may slide, and sliding past the lapse
            # would leave no way to finish it. Time and machine still hold;
            # the solve picks the operator.
            op_id = rep.assigned_operator_id
            if op_id is not None and named_assign:
                att = front_len if front_len is not None else op_dur
                span = (prev_start, prev_start + (att or 0))
                if (att and op_id not in shop.qual_lapse.get(step_id, {})
                        and not _overlaps(span[0], span[1],
                                          self.fixed_by_operator.get(op_id, ()))):
                    for op, lit in named_assign:
                        model.Add(lit == (1 if op == op_id else 0))
                    self.fixed_by_operator[op_id].append(span)
                else:
                    # Reported if the plan does give it to someone else.
                    out['op_unfixed'] = op_id
            held_att = front_len if front_len is not None else op_dur
            if lm != 'off' and held_att:
                self.fixed_attended.append((prev_start, prev_start + held_att))
            if op_dur is not None:
                out['held_pos'] = (prev_start, prev_start + op_dur, fixed_m)
            out['pinned'] = True
            out['planner_pinned'] = any_pinned
            out['fixed_start_dt'] = rep.start_time
            # Exact write-back only for a slot still ahead: one already
            # passed was held at "now", and writing its old time back
            # would put the plan in the past.
            out['held_minute'] = prev_start if prev_raw >= 0 else None
            self.kept += 1
        else:
            if fence_held:
                self.freed.append({'part_ids': lot['part_ids'], 'step_id': step_id,
                                   'reason_code': why[0], 'reason': why[1],
                                   'was_pinned': any_pinned})
            if 0 <= prev_raw < shop.slushy_min:
                # Slushy (or a freed frozen op): prefer staying put,
                # priced against lateness so moving saves real time.
                dev = model.NewIntVar(0, shop.H_ext, f"stick_{key}")
                model.AddAbsEquality(dev, start - prev_start)
                self.stick_terms.append(('dev', dev, shop.slushy_per_min))
                if rep.machine_id:
                    for lit, eqid in choices:
                        if eqid == rep.machine_id:
                            self.stick_terms.append(('mach', lit, shop.slushy_machine_cost))
            self.warm_hints.append((start, prev_start))
            out['warm_start'] = prev_start
        return out

    def _add_pegs(self):
        """Cross-WO assembly-convergence pegs (plan #9): a component WO must finish
        (+ staging buffer) before its parent assembly WO may start. Both WOs are in
        this solve; multi-level BOMs chain transitively (A waits on B waits on C).
        When the BOM line names the consuming step, only that assembly step waits —
        pre-assembly parent work can overlap the component build; otherwise (no
        consumed_at_step authored) the whole parent waits, conservatively."""
        model = self.model
        for wo in self.shop.wos:
            parent_id = wo.pegged_to_wo_id
            if not parent_id or parent_id == wo.wo_id:
                continue
            child_ends = self.wo_ends.get(wo.wo_id)
            if not child_ends:
                continue
            if wo.pegged_consumes_step_id is not None:
                gated = self.wo_step_starts.get((parent_id, wo.pegged_consumes_step_id))
            else:
                gated = self.wo_starts.get(parent_id)
            if not gated:
                continue   # parent produced no (matching) tasks — e.g. already past it
            child_done = model.NewIntVar(0, self.shop.H_ext, f"child_done_{wo.wo_id}")
            model.AddMaxEquality(child_done, child_ends)
            for ps in gated:
                model.Add(ps >= child_done + self.shop.staging_buffer)

    def _add_held_order(self):
        """Held work keeps its order on its machine: each held operation starts after
        the one planned before it (plus the changeover between them), so a slide
        carries the queue along instead of reshuffling it."""
        shop = self.shop
        for equipment_id, held in self.held_on_machine.items():
            held.sort(key=lambda h: h[0])
            for a, b in zip(held, held[1:]):
                gap = _transition(shop.changeover, equipment_id, a[3], b[3], b[4],
                                  a[5], b[5], shop.job_change_min)
                self.model.Add(b[1] >= a[2] + gap)

    def _add_machine_capacity(self):
        """Machine capacity. Lights-out machines (the default) run 24/7 and are blocked
        only by their downtime — a lot-operation may span nights/weekends. Machines
        flagged attended-only (`runs_unattended=False`) are instead confined to the
        shift calendar plus company overtime (operator must be present), so their
        unavailable gaps are the complement of the shift windows. Plant closures block
        every machine (`machine_gaps`). Continuous-feed machines also periodically stop
        for a bar change; those are recurring fixed downtime over the horizon."""
        shop, model, H = self.shop, self.model, self.shop.H
        for equipment_id, intervals in self.machine_intervals.items():
            gaps = shop.machine_gaps(equipment_id)
            blocked = [model.NewFixedSizeIntervalVar(gs, ge - gs, f"gap_{equipment_id}_{i}")
                       for i, (gs, ge) in enumerate(gaps)]
            cm = shop.continuous.get(equipment_id)
            if cm is not None and cm.bar_change_interval_hours and cm.bar_change_duration_minutes:
                step = int(cm.bar_change_interval_hours * 60)
                dur_bc = max(1, int(round(cm.bar_change_duration_minutes)))
                t = step
                while t < H:
                    blocked.append(model.NewFixedSizeIntervalVar(
                        t, min(dur_bc, H - t), f"bar_{equipment_id}_{t}"))
                    t += step + dur_bc
            cap = shop.concurrent_cap.get(equipment_id)
            if cap:
                # CONCURRENT batch resource: up to `cap` jobs run at once. Downtime/closure
                # gaps demand the full capacity so they still block it entirely. (CYCLE
                # furnaces stay no-overlap — one load at a time — with a per-load duration.)
                model.AddCumulative(intervals + blocked,
                                    [1] * len(intervals) + [cap] * len(blocked), cap)
            else:
                model.AddNoOverlap(intervals + blocked)

    def _add_changeovers(self):
        """Sequence-dependent setup / changeover: for each pair of tasks that could
        share a machine, insert the changeover gap in whichever order they run (gated on
        both being assigned to that machine). Same-step neighbours cost 0 (piece after
        piece); different-step neighbours pay the WorkCenterChangeover (or the incoming
        step's setup as a fallback). NoOverlap already prevents time overlap; this adds
        the transition gap on top."""
        shop, model = self.shop, self.model
        for equipment_id, mtasks in self.machine_tasks.items():
            # Batch/process resources (either mode) don't do pairwise "consecutive"
            # changeover — concurrent jobs overlap; a furnace cycle bakes setup into its
            # per-load duration.
            if equipment_id in shop.concurrent_cap or equipment_id in shop.cycle_cap:
                continue
            for i in range(len(mtasks)):
                pi, si, ei, stepi, setupi, woi = mtasks[i]
                for j in range(i + 1, len(mtasks)):
                    pj, sj, ej, stepj, setupj, woj = mtasks[j]
                    t_ij = _transition(shop.changeover, equipment_id, stepi, stepj, setupj,
                                       woi, woj, shop.job_change_min)
                    t_ji = _transition(shop.changeover, equipment_id, stepj, stepi, setupi,
                                       woj, woi, shop.job_change_min)
                    if not t_ij and not t_ji:
                        continue
                    i_before_j = model.NewBoolVar(f"seq_{equipment_id}_{i}_{j}")
                    model.Add(sj >= ei + t_ij).OnlyEnforceIf([pi, pj, i_before_j])
                    model.Add(si >= ej + t_ji).OnlyEnforceIf([pi, pj, i_before_j.Not()])

    def _add_gauges_and_fixtures(self):
        # Secondary gauges: one task at a time per gauge.
        for intervals in self.gauge_intervals.values():
            self.model.AddNoOverlap(intervals)
        # Fixtures: cumulative — at most `quantity` concurrent users.
        for fixture_id, intervals in self.fixture_intervals.items():
            capacity = self.shop.fixtures[fixture_id].quantity
            self.model.AddCumulative(intervals, [1] * len(intervals), capacity)

    def _add_capacity(self, intervals, windows, tag):
        """Cumulative capping `intervals` at the headcount on shift in `windows`,
        with deficit blockers so low-staff (and zero-staff) stretches are respected."""
        model = self.model
        cap, segs = _staffing_segments(windows, self.shop.horizon.start, self.shop.H)
        if not intervals or cap <= 0:
            return
        ivs = list(intervals)
        dems = [1] * len(intervals)
        for a, b, count in segs:
            deficit = cap - count
            if deficit > 0 and b > a:
                ivs.append(model.NewFixedSizeIntervalVar(a, b - a, f"{tag}_{a}_{b}"))
                dems.append(deficit)
        model.AddCumulative(ivs, dems, cap)

    def _add_labor_capacity(self):
        """Labor capacity (Layer-1 crew constraint): the attended operations may not
        demand more operators at once than the crew on shift — a cumulative resource
        whose capacity varies by shift. Deficit "blocker" intervals consume the gap
        between each segment's headcount and the peak, so an off-shift stretch (count
        0) is fully blocked — attended work is pushed into staffed hours while machines
        keep running lights-out. Skipped entirely when no crew is rostered (cap 0), so
        a tenant without shift/roster data schedules unconstrained as before."""
        shop = self.shop
        # Total crew: no more concurrent attended work than operators on shift (applies
        # to POOL and NAMED lots alike — every attended op needs one of the crew).
        self._add_capacity([iv for iv, _, _ in self.labor_intervals], shop.op_windows, "crew")

        # Per-skill (POOL model only): each training-gated step's attended work is capped
        # at ITS qualified crew on shift, so a scarce skill runs limited-at-a-time and the
        # excess pushes later. NAMED steps are handled exactly below instead.
        pool_intervals: dict = defaultdict(list)
        for iv, sid, m in self.labor_intervals:
            if m == 'pool':
                pool = shop.skill_pools.get(sid)
                if pool:
                    pool_intervals[pool].append(iv)
        for i, (pool, intervals) in enumerate(pool_intervals.items()):
            pool_windows = {u: w for u, w in shop.op_windows.items() if u in pool}
            self._add_capacity(intervals, pool_windows, f"skill{i}")

        # NAMED model: a specific operator runs each lot and can't be in two places — a
        # per-operator NoOverlap over their assigned intervals, blocked outside their
        # shift. This is the exact dual-resource assignment for specialist steps.
        for op, intervals in self.named_op_intervals.items():
            _, off_segs = _staffing_segments({op: shop.op_windows.get(op, [])},
                                             shop.horizon.start, shop.H)
            blockers = [self.model.NewFixedSizeIntervalVar(a, b - a, f"noff_{op}_{a}")
                        for a, b, c in off_segs if c == 0 and b > a]
            self.model.AddNoOverlap(intervals + blockers)

    def _set_objective(self):
        if not self.tasks:
            return
        shop, model = self.shop, self.model
        H = shop.H_ext   # every bound below reaches past the horizon too
        stick_terms = self.stick_terms
        makespan = model.NewIntVar(0, H, "makespan")
        model.AddMaxEquality(makespan, [t['end'] for t in self.tasks])
        stickiness = (sum(w * v for kind, v, w in stick_terms if kind == 'dev')
                      + sum(w * (1 - v) for kind, v, w in stick_terms if kind == 'mach'))
        urgent_per_min = max(1, _penalty_cents_per_min(shop.config, 1))
        slide_cost = _SLIDE_WEIGHT_FACTOR * urgent_per_min * sum(self.slide_terms)
        obj = (sum(self.lateness_cost) + makespan + stickiness + slide_cost
               + sum(self.affinity_cost) + sum(self.max_time_penalty))
        if self.named_uncovered:
            # Coverage-first (lexicographic-by-weight): one uncovered attended op is
            # priced ABOVE the largest the rest of the objective could ever reach, so
            # the solver NEVER trades coverage for less lateness/makespan — pushing
            # work late is always preferred to leaving it unstaffed.
            max_pen = max((_penalty_cents_per_min(shop.config, w.priority) for w in shop.wos),
                          default=0)
            stick_max = (sum(w * (H if kind == 'dev' else 1) for kind, _v, w in stick_terms)
                         + _SLIDE_WEIGHT_FACTOR * max(1, _penalty_cents_per_min(shop.config, 1))
                         * H * len(self.slide_terms))
            w_unc = (len(self.tasks) * (H + shop.H) * max_pen + H + stick_max
                     + len(self.affinity_cost) * _AFFINITY_PENALTY_DEFAULT
                     + len(self.max_time_penalty) * _CURE_WINDOW_WEIGHT + 1)
            obj = obj + w_unc * sum(self.named_uncovered)
        model.Minimize(obj)

    def _add_hints(self, machine_hints):
        model = self.model
        for var, minute in self.warm_hints:            # warm-start from the previous schedule
            model.AddHint(var, minute)

        if machine_hints is None and self.tasks:
            # A dispatch-rule starting plan for every operation the live plan doesn't
            # already hint (`greedy_plan`) — CP-SAT then improves on it rather than
            # searching from nothing, which is where run-to-run swings came from.
            for t, (gs, ge, geq) in self.shop.greedy_plan(self.tasks):
                if t['fixed_pos'] is not None or t.get('warm') is not None:
                    continue
                model.AddHint(t['start'], gs)
                model.AddHint(t['end'], ge)
                for lit, eqid in t['choices']:
                    model.AddHint(lit, 1 if eqid == geq else 0)

        if machine_hints:
            # Hint the MACHINE choice from the machine phase (that layout is good),
            # but NOT the start time — leaving times free lets the operator phase push
            # attended work out into idle capacity to cover it, instead of clinging to
            # the machine phase's compact makespan and parking lots as uncovered.
            for _i, _t in enumerate(self.tasks):
                _h = machine_hints.get(_i)
                if not _h:
                    continue
                for _lit, _eqid in _t['choices']:
                    if _eqid == _h[1]:
                        model.AddHint(_lit, 1)

    # --- solving ---------------------------------------------------------------

    def solve(self, tlimit) -> dict:
        from ortools.sat.python import cp_model

        solver = cp_model.CpSolver()
        # The planner's stopping rules, both from Scheduling settings: the time limit
        # (split across phases by the caller) and the relative gap at which a plan
        # is proven good enough. Nothing else stops the search.
        solver.parameters.max_time_in_seconds = tlimit
        gap = getattr(self.shop.config, 'relative_gap_limit', None)
        if gap is not None:
            solver.parameters.relative_gap_limit = float(gap)
        cp_status = _cp_solve(solver, self.model) if self.tasks else cp_model.OPTIMAL
        solved = cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        return {'cp_status': cp_status, 'solver': solver, 'tasks': self.tasks,
                'lateness_terms': self.lateness_terms, 'solved': solved,
                'max_time_viols': self.max_time_viols, 'stick_terms': self.stick_terms,
                'freed': self.freed, 'kept': self.kept}


def _solve_phase(shop, labor_override, machine_hints, tlimit) -> dict:
    phase = _Phase(shop, labor_override)
    phase.build(machine_hints)
    return phase.solve(tlimit)


def _wall_ms(phase_result) -> int:
    return int(phase_result['solver'].WallTime() * 1000) if phase_result['tasks'] else 0


def _solve_with_fence(shop, time_limit_seconds):
    """The phases, with the frozen fence held. Returns
    `(final_phase_result, machine_solve_ms, operator_solve_ms)`.

    Two-phase when operator matching is on AND a crew is rostered: solve machines
    (pooled labor, ~40% of the budget), then re-solve assigning specific operators
    warm-started from that layout (~60%). Else a single fast machine solve. The
    per-phase wall-clock is surfaced to the planner: how long the machine (Layer-1)
    vs named-operator (Layer-2 in-solve) side each took.

    The fence is never loosened by the solver (user decision 2026-10-27, standard
    time-fence practice: only a person moves frozen work). Held work that can't happen
    where it is isn't held (`Shop.frozen_refusal`, with its reason), and held work
    colliding with held work slides in order. If a solve still finds no plan, it
    fails: the live plan stays on the board, stale, with the reason
    (`write_back.persist`)."""
    if bool(getattr(shop.config, 'match_operators', False)) and bool(shop.all_op_ids):
        _ta = max(1, int(time_limit_seconds * 0.4))
        _pa = _solve_phase(shop, 'pool', None, _ta)
        if not _pa['solved']:
            return _pa, _wall_ms(_pa), 0
        _sa = _pa['solver']
        _hints = {i: (_sa.Value(t['start']), _chosen_machine(t, _sa))
                  for i, t in enumerate(_pa['tasks'])}
        _pb = _solve_phase(shop, 'named', _hints, max(1, time_limit_seconds - _ta))
        return (_pb if _pb['solved'] else _pa), _wall_ms(_pa), _wall_ms(_pb)
    out = _solve_phase(shop, None, None, time_limit_seconds)
    return out, _wall_ms(out), 0
