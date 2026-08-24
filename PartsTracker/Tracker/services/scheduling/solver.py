"""
CP-SAT machine scheduler (Phase 2, Layer 1).

Consumes the Phase-1 data-layer DTOs and produces a machine schedule
(`ScheduleResult` + `ScheduledTask`).

Layers built so far:
- Lot-based route-aware tasks: a WO's parts at the SAME current step form one lot that
  moves through the remaining nominal route together (DEFAULT edges; rework/scrap
  excluded), scheduled as one machine occupancy per operation sized by the lot's piece
  count (cycle × count). Parts stranded at different steps form separate lots; reman
  teardown cores schedule individually. Written back per part (each shares the lot's
  window) so tracking/pins stay part-grained. Merge-capable DAG precedence (see
  `routing.resolve_route`); cores write back as ScheduledTask.core.
- Lock-step batches: a WO's parts at one step schedule as one cohesive lot (one
  occupancy, one synchronized start). A part split off to rework (`split_from_lot`) is
  carved into its OWN lot so the cohort keeps progressing — the batch is NOT held for a
  straggler; the split part schedules its own rework path and re-converges later via
  `rejoin_part_to_lot` (`Parts.rejoined_at`), else at finished goods. Cores schedule
  individually (reman units).
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
  unattended. A step no rostered operator is trained for makes the solve refuse
  (`LaborInfeasible`) — that work can't be executed at all. Which operator takes each
  task is still a Layer-2 (dispatch) concern; breaks live there too.
- Secondary resources: a step's schedulable gauges (Keyence/CMM) are reserved
  one-at-a-time while the task runs.
- Fixtures: shared tooling as a cumulative resource (≤ quantity concurrent users).
- Setup/changeover: sequence-dependent transition gaps between machine neighbours.
- Continuous machines: throughput-based duration + recurring bar-change downtime.
- Time fences + warm-start: frozen-zone / planner-pinned tasks held to the previous
  schedule (time and machine) by a SOFT penalty — a re-solve after the world changed
  moves them the minimum instead of going INFEASIBLE, and reports the count
  (`relaxed_pin_count`); slushy/liquid tasks seeded as solver hints.
- Cross-WO pegs: a component WO must finish (+ staging buffer) before its parent
  assembly WO starts (WorkOrder.pegged_to_workorder; multi-level chains transitively).

Follow-ons: changeover-as-circuit (scalability), transfer-batching. Time is
discretized to integer minutes from `horizon.start`; results are written back as
absolute datetimes.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, time as dtime, timedelta
from decimal import Decimal

from django.utils import timezone

from Tracker.services.scheduling import data
from Tracker.services.scheduling.routing import resolve_route
from Tracker.utils.tenant_context import tenant_context

logger = logging.getLogger(__name__)

_PENALTY_FIELD = {1: 'late_penalty_urgent', 2: 'late_penalty_high',
                  3: 'late_penalty_normal', 4: 'late_penalty_low'}
_PENALTY_DEFAULT = {1: Decimal('1000'), 2: Decimal('500'),
                    3: Decimal('100'), 4: Decimal('25')}
_MINUTES_PER_DAY = 24 * 60

# Pin stickiness (objective weights, cents-equivalent). Pins are SOFT: honored by a
# large penalty, never a hard constraint — so a re-solve after the world changed
# (machine down, shift edited) never goes INFEASIBLE; the pin just moves the minimum
# needed and is reported. Weights dominate the lateness/makespan terms so a pin never
# drifts for cost reasons — only when a hard constraint forces it. Planner pins
# (is_pinned) are an order of magnitude stickier than frozen-zone auto-pins.
_FROZEN_PIN_WEIGHT = 10_000       # per minute of start deviation
_PLANNER_PIN_WEIGHT = 100_000     # per minute — planner-locked, near-immovable
_MACHINE_PIN_WEIGHT = 1_000_000   # flat, for moving a pin off its previous machine


def _pfd_factor(config) -> float:
    """PFD (personal/fatigue/delay) allowance as a duration multiplier. Inflates
    attended run time to account for the operator's unavoidable micro-stoppages;
    unattended machine time isn't extended by an operator allowance."""
    pct = float(getattr(config, 'pfd_allowance_pct', 0) or 0) if config else 0.0
    return 1.0 + max(0.0, pct) / 100.0


def _dur(timing, affinity, pfd_factor: float = 1.0, quantity: int = 1) -> int:
    """Machine minutes for a lot-operation: the per-piece cycle × the lot's piece
    count. Setup is NOT folded in here — it's charged separately as the changeover
    gap when a machine switches operations (see `_transition`)."""
    cycle = None
    if affinity is not None and affinity.cycle_time_override is not None:
        cycle = affinity.cycle_time_override
    elif timing is not None:
        cycle = timing.cycle_time_minutes
    if not cycle:
        return 1
    # PFD inflates ATTENDED time only (the field is "added to attended time"); a
    # load/unload step's machine runs unattended, so its cycle isn't stretched.
    attended = (timing is None) or (timing.attention_type == 'full')
    eff = cycle * pfd_factor if attended else cycle
    return max(1, round(eff * max(1, quantity)))


def _dur_on_machine(timing, affinity, continuous, pfd_factor: float = 1.0,
                    quantity: int = 1) -> int:
    """Lot minutes on a machine. Continuous-feed machines use throughput
    (60 / parts_per_hour × count, lights-out — no PFD); everything else uses the step
    cycle / override × count, PFD-inflated when attended."""
    cm = continuous.get(affinity.equipment_id)
    if cm is not None and cm.parts_per_hour:
        return max(1, round(60.0 / cm.parts_per_hour * max(1, quantity)))
    return _dur(timing, affinity, pfd_factor, quantity)


# Machine-preference nudge: choosing a less-preferred machine costs a small objective
# penalty so the solver favors dialed_in > preferred > eligible when the schedule is
# otherwise equivalent. Kept tiny (a few makespan-minutes) so it only breaks ties and
# never makes a job late just to honor a preference.
_AFFINITY_PENALTY = {'dialed_in': 0, 'preferred': 3, 'eligible': 8}
_AFFINITY_PENALTY_DEFAULT = 8


def _affinity_penalty(affinity_level) -> int:
    return _AFFINITY_PENALTY.get(affinity_level, _AFFINITY_PENALTY_DEFAULT)


def _fence_zone(start_min, frozen_min, slushy_min):
    from Tracker.models.scheduling import FenceZone
    if start_min < frozen_min:
        return FenceZone.FROZEN
    if start_min < slushy_min:
        return FenceZone.SLUSHY
    return FenceZone.LIQUID


_JOB_CHANGE_DEFAULT = 10   # minutes — minor setup to switch work orders on the same op


def _job_change_minutes(config) -> int:
    """Setup charged when a resource switches to a different work order on the SAME
    operation — keeps a job's parts batched. Below op-change setups by design (op
    continuity outranks WO continuity)."""
    v = getattr(config, 'job_change_minutes', None) if config else None
    return int(v) if v is not None else _JOB_CHANGE_DEFAULT


def _penalty_cents_per_min(config, priority: int) -> int:
    if config is not None:
        dollars_per_day = getattr(config, _PENALTY_FIELD.get(priority, 'late_penalty_normal'))
    else:
        dollars_per_day = _PENALTY_DEFAULT.get(priority, Decimal('100'))
    return max(0, round(float(dollars_per_day) * 100 / _MINUTES_PER_DAY))


def _due_minutes(due_date, horizon_start, H) -> int | None:
    if due_date is None:
        return None
    due_dt = timezone.make_aware(datetime.combine(due_date, dtime.max))
    minutes = int((due_dt - horizon_start).total_seconds() // 60)
    return max(-H, minutes)


def _release_minutes(start_date, horizon_start, H) -> int:
    """Earliest a WO's work may begin: start-of-day of its expected_start, clamped
    to [0, H]. 0 (already releasable) when unset or in the past."""
    if start_date is None:
        return 0
    rel_dt = timezone.make_aware(datetime.combine(start_date, dtime.min))
    return max(0, min(H, int((rel_dt - horizon_start).total_seconds() // 60)))


def _to_minutes(intervals, horizon_start, H) -> list[tuple]:
    """Datetime intervals → clipped integer-minute [start, end] tuples from H0."""
    out = []
    for s, e in intervals:
        ms = max(0, int((s - horizon_start).total_seconds() // 60))
        me = min(H, int((e - horizon_start).total_seconds() // 60))
        if ms < me:
            out.append((ms, me))
    return out


def _window_gaps(windows, horizon_start, H) -> list[tuple]:
    """Unavailable [start, end] minute intervals between a machine's availability
    windows, within [0, H]. Empty when the machine has no windows (treated as
    always-available so a tenant with no shift config still schedules)."""
    if not windows:
        return []
    mins = []
    for w in windows:
        s = max(0, int((w.start - horizon_start).total_seconds() // 60))
        e = min(H, int((w.end - horizon_start).total_seconds() // 60))
        if s < e:
            mins.append((s, e))
    mins.sort()
    gaps = []
    cursor = 0
    for s, e in mins:
        if s > cursor:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < H:
        gaps.append((cursor, H))
    return gaps


def _staffing_segments(op_windows, horizon_start, H):
    """Piecewise operator headcount over [0, H] from the rostered shift windows:
    a list of (start_min, end_min, count) covering the whole horizon (count 0 where
    nobody is on shift), plus the peak count. Drives the labor-capacity cumulative —
    concurrent attended work is capped at the crew on hand, and attended work is barred
    from unstaffed hours (count 0) while machines keep running lights-out."""
    delta: dict = defaultdict(int)
    for windows in op_windows.values():
        for s, e in windows:
            ms = max(0, int((s - horizon_start).total_seconds() // 60))
            me = min(H, int((e - horizon_start).total_seconds() // 60))
            if ms < me:
                delta[ms] += 1
                delta[me] -= 1
    if not delta:
        return 0, []
    points = sorted(set([0, H]) | set(delta))
    segs, count = [], 0
    for i in range(len(points) - 1):
        count += delta.get(points[i], 0)
        a, b = points[i], points[i + 1]
        if a < b:
            segs.append((a, b, count))
    cap_max = max((c for _, _, c in segs), default=0)
    return cap_max, segs


def _transition(changeover, equipment_id, from_step, to_step, to_setup,
                from_wo=None, to_wo=None, job_change=0) -> int:
    """Minutes between consecutive tasks on a machine — the setup the solver pays to
    switch, so it prefers to keep a resource on the same work:
    - same step AND same work order → 0 (piece after piece within one job's batch);
    - same step, DIFFERENT work order → `job_change` (a job change on the same
      operation: paperwork, re-fixturing, first-off — keeps a WO's parts together);
    - different step → the WorkCenterChangeover value, or the incoming step's setup
      as a fallback (an operation change).
    These costs push switching later, so minimizing makespan/lateness batches work."""
    if from_step == to_step:
        return 0 if from_wo == to_wo else job_change
    # Operation change. Keeping the same OPERATION matters more than keeping the same
    # work order, so an op change never costs less than a job change (floor at
    # job_change); a configured changeover/setup above that is used as-is.
    val = changeover.get((equipment_id, from_step, to_step))
    op_change = int(round(val)) if val is not None else to_setup
    return max(op_change, job_change)


def _map_status(cp_status) -> str:
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import SolverStatus
    return {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.MODEL_INVALID: SolverStatus.MODEL_INVALID,
    }.get(cp_status, SolverStatus.UNKNOWN)


def _chosen_machine(task, solver) -> object | None:
    if not task['choices']:
        return None
    for lit, equipment_id in task['choices']:
        if solver.Value(lit) == 1:
            return equipment_id
    return None


def solve_schedule(tenant, time_limit_seconds: int = 300, draft: bool = False):
    """Solve the Layer-1 machine schedule for a tenant and persist it as the new
    active `ScheduleResult`. Returns the ScheduleResult (empty + OPTIMAL when there
    is no work)."""
    from ortools.sat.python import cp_model
    from Tracker.models.scheduling import (
        OptimizationConfig, ScheduledTask, ScheduleResult,
    )

    with tenant_context(str(tenant.id)):
        # Refuse up front if any step in the active work requires a certification no
        # rostered operator holds — that work could never be executed, so we don't emit
        # a plan pretending it can. (Scarce-but-present skills are handled by the labor
        # capacity below: they serialize and push work late, not blocked.)
        from Tracker.services.scheduling.preflight import (
            LaborInfeasible, find_unstaffable_steps,
        )
        gaps = find_unstaffable_steps(tenant)
        if gaps:
            raise LaborInfeasible(gaps)

        horizon = data.get_schedule_horizon(tenant)
        H = max(1, int((horizon.end - horizon.start).total_seconds() // 60))
        wos = data.get_active_workorders(tenant)
        timings = data.get_step_timings(tenant)
        affinities = data.get_step_equipment_affinities(tenant)
        availability = data.get_machine_availability(tenant, horizon)
        attended_only = data.get_attended_only_machines(tenant)  # shift-confined machines
        machine_downtime = data.get_machine_downtime(tenant, horizon)  # eq -> [(s,e)]
        op_windows = data.get_operator_shift_windows(tenant, horizon)  # rostered crew
        skill_pools = data.get_step_operator_pools(tenant)  # gated step -> qualified crew
        labor_models = data.get_step_labor_models(tenant)  # step -> off|pool|named
        all_op_ids = frozenset(o.user_id for o in data.get_dispatchable_operators(tenant))
        secondary = data.get_step_secondary_resources(tenant)   # step_id -> {gauge_id}
        fixtures = data.get_fixture_availability(tenant)         # fixture_id -> FixtureData
        changeover = data.get_changeover_matrix(tenant)         # (equip, from, to) -> minutes
        continuous = {cm.equipment_id: cm for cm in data.get_continuous_machines(tenant)}
        prev = data.get_previous_schedule(tenant)               # for pins + warm-start
        config = OptimizationConfig.objects.filter(tenant=tenant).first()

        prev_map = {}
        if prev is not None:
            prev_map = {(t.part_id, t.step_id): t for t in prev.tasks}
        frozen_min = int((horizon.frozen_end - horizon.start).total_seconds() // 60)
        slushy_min = int((horizon.slushy_end - horizon.start).total_seconds() // 60)
        staging_buffer = config.staging_buffer_minutes if config else 0
        job_change_min = _job_change_minutes(config)   # WO-change setup on the same op
        pfd_factor = _pfd_factor(config)               # attended-time allowance multiplier

        # Which steps need an unconditional occupancy interval (gauge and/or fixture).
        fixture_by_step: dict = defaultdict(list)
        for fx in fixtures.values():
            for step_id in fx.step_ids:
                fixture_by_step[step_id].append(fx.fixture_id)
        occupancy_steps = set(secondary) | set(fixture_by_step)

        # One solve phase. `labor_override`: None keeps each step's own labor_model;
        # 'pool' forces non-off steps to the cheap cumulative (the fast MACHINE phase);
        # 'named' forces exact per-operator assignment (the OPERATOR phase).
        # `machine_hints` {task_index: (start_min, machine_id)} warm-starts the operator
        # phase from the machine phase — CP-SAT refines a good layout, not a cold search.
        def _build_and_solve(labor_override, machine_hints, tlimit):
            def _eff(step_id):
                base = labor_models.get(step_id, 'pool')
                return 'off' if base == 'off' else (labor_override or base)

            model = cp_model.CpModel()

            # NB: scheduled breaks/lunch are NOT enforced here. In the lights-out model a
            # machine keeps running through a break; operator presence for the attended
            # portions is a Layer-2 concern, and dispatch already honors break TimeEntries.

            tasks: list[dict] = []
            machine_intervals: dict = defaultdict(list)
            machine_tasks: dict = defaultdict(list)   # equip_id -> [(present, start, end, step_id, setup, wo_id)]
            gauge_intervals: dict = defaultdict(list)
            fixture_intervals: dict = defaultdict(list)
            lateness_cost = []
            lateness_terms = []   # (lateness_var, penalty) — for the isolated lateness total
            affinity_cost = []    # small penalties nudging toward preferred/dialed-in machines
            labor_intervals = []  # (attended_interval, step_id, model) per attended lot-op
            named_op_intervals: dict = defaultdict(list)  # user_id -> [optional intervals]
            named_uncovered = []  # soft penalty terms for unassignable NAMED lots
            warm_hints = []   # (start_var, minute) warm-start warm_hints from the previous schedule
            pin_penalty = []   # soft-pin objective terms (deviation from the frozen plan)
            pins = []          # (start_var, prev_start, prev_machine_id, choices) for the moved report
            wo_starts: dict = defaultdict(list)   # wo_id -> [start vars] (for peg gating)
            wo_ends: dict = defaultdict(list)     # wo_id -> [end vars]   (for peg completion)
            wo_step_starts: dict = defaultdict(list)  # (wo_id, step_id) -> [start vars]

            for wo in wos:
                due_minutes = _due_minutes(wo.expected_completion, horizon.start, H)
                release_min = _release_minutes(wo.expected_start, horizon.start, H)
                penalty = _penalty_cents_per_min(config, wo.priority)
                # Lot-based scheduling: a WO's parts sitting at the SAME current step form
                # one cohesive lot that moves the remaining route together — one machine
                # occupancy per operation, sized by the lot's piece count (cycle × count;
                # setup is the changeover gap). Lock-step lives HERE: co-located cohort
                # parts schedule as one lot with a single start.
                # Carve-out: a part split off to rework (`split_from_lot`) is grouped into
                # its OWN lot (keyed by split-state) so it never drags the cohort — the
                # cohort keeps progressing, and the split part schedules its own rework path
                # and re-converges later via rejoin_part_to_lot. Cores schedule individually.
                part_batches: dict = defaultdict(list)
                for p in wo.parts:
                    part_batches[(p.current_step_id, p.split_from_lot)].append(p.part_id)
                lots = [{'label': f"b{wo.wo_id}:{step}:{'r' if split else 'c'}", 'step': step,
                         'part_ids': tuple(pids), 'core_id': None, 'count': len(pids)}
                        for (step, split), pids in part_batches.items()]
                lots += [{'label': f"c{c.core_id}", 'step': c.current_step_id,
                          'part_ids': (), 'core_id': c.core_id, 'count': 1}
                         for c in wo.cores]
                for lot in lots:
                    is_core = lot['core_id'] is not None
                    count = lot['count']
                    # The lot's remaining NOMINAL route from its current step (DEFAULT
                    # edges; rework/scrap branches excluded), with merge-capable DAG
                    # precedence so convergence/divergence nodes schedule correctly.
                    route_ids, prec = resolve_route(lot['step'], wo.steps, wo.edges)
                    node_start: dict = {}
                    node_end: dict = {}
                    lot_ends = []
                    for step_id in route_ids:
                        timing = timings.get(step_id)
                        eligible = [a for a in affinities.get(step_id, []) if a.is_schedulable]
                        key = f"{lot['label']}_{step_id}"
                        start = model.NewIntVar(0, H, f"s_{key}")
                        end = model.NewIntVar(0, H, f"e_{key}")
                        if release_min:
                            model.Add(start >= release_min)   # earliest-release gate

                        setup_int = int(round(timing.setup_minutes)) if timing else 0
                        choices = []
                        if eligible:
                            for a in eligible:
                                dur = _dur_on_machine(timing, a, continuous, pfd_factor, count)
                                lit = model.NewBoolVar(f"m_{key}_{a.equipment_id}")
                                opt = model.NewOptionalFixedSizeIntervalVar(start, dur, lit, f"i_{key}_{a.equipment_id}")
                                machine_intervals[a.equipment_id].append(opt)
                                machine_tasks[a.equipment_id].append(
                                    (lit, start, end, step_id, setup_int, wo.wo_id))
                                model.Add(end == start + dur).OnlyEnforceIf(lit)
                                choices.append((lit, a.equipment_id))
                                penalty_lvl = _affinity_penalty(a.affinity)
                                if penalty_lvl:
                                    affinity_cost.append(lit * penalty_lvl)  # pay iff this machine is chosen
                            model.AddExactlyOne([lit for lit, _ in choices])
                        else:
                            dur = _dur(timing, None, pfd_factor, count)
                            model.NewIntervalVar(start, dur, end, f"i_{key}")

                        # Occupancy interval for the finite secondary resources the lot ties
                        # up while it runs — measurement gauges and shared fixtures.
                        if step_id in occupancy_steps:
                            size = model.NewIntVar(1, H, f"sz_{key}")
                            occ = model.NewIntervalVar(start, size, end, f"occ_{key}")
                            for gauge_id in secondary.get(step_id, ()):
                                gauge_intervals[gauge_id].append(occ)
                            for fixture_id in fixture_by_step.get(step_id, ()):
                                fixture_intervals[fixture_id].append(occ)

                        # Labor demand: ONE operator tends the lot at this operation (not one
                        # per piece). Full-attention → tied to the whole run; load/unload →
                        # only the front touch (setup + a load/unload per piece), the machine
                        # then running unattended. Feeds the crew-capacity cumulative below.
                        lm = _eff(step_id)
                        if lm != 'off':
                            full = timing is None or timing.attention_type == 'full'
                            if full:
                                asz = model.NewIntVar(0, H, f"asz_{key}")
                                att_iv = model.NewIntervalVar(start, asz, end, f"att_{key}")
                            else:
                                front = int(round(timing.setup_minutes + timing.load_unload_per_piece * count))
                                att_iv = (model.NewFixedSizeIntervalVar(start, front, f"att_{key}")
                                          if front > 0 else None)
                            if att_iv is not None:
                                labor_intervals.append((att_iv, step_id, lm))
                                if lm == 'named':
                                    # Assign a SPECIFIC qualified operator to this lot (exact
                                    # dual-resource): optional per-operator intervals a
                                    # per-operator NoOverlap serialises, so a scarce specialist
                                    # pushes the work late rather than leaving it uncovered. A
                                    # soft `uncov` fallback keeps the model feasible.
                                    pool = skill_pools.get(step_id)
                                    qualified = (pool if pool is not None else all_op_ids) & all_op_ids
                                    assign_lits = []
                                    for op in qualified:
                                        lit = model.NewBoolVar(f"na_{key}_{op}")
                                        if full:
                                            oiv = model.NewOptionalIntervalVar(start, asz, end, lit, f"noi_{key}_{op}")
                                        else:
                                            oiv = model.NewOptionalFixedSizeIntervalVar(start, front, lit, f"noi_{key}_{op}")
                                        named_op_intervals[op].append(oiv)
                                        assign_lits.append(lit)
                                    if assign_lits:
                                        uncov = model.NewBoolVar(f"nunc_{key}")
                                        model.Add(sum(assign_lits) + uncov == 1)
                                        named_uncovered.append(uncov)   # weighted coverage-first below

                        # Time fences / warm-start from the previous active schedule. Cores
                        # schedule fresh each solve. A lot inherits the pin/frozen state of
                        # its parts: if ANY part was planner-pinned it's held (planner
                        # weight), else if the earliest part sat in the frozen zone it's
                        # frozen-held — always a SOFT penalty so a re-solve after the world
                        # changed moves it the minimum instead of going INFEASIBLE.
                        pinned = False
                        prevts = ([prev_map[(pid, step_id)] for pid in lot['part_ids']
                                   if (pid, step_id) in prev_map] if not is_core else [])
                        if prevts:
                            rep = min(prevts, key=lambda pt: pt.start_time)
                            any_pinned = any(pt.is_pinned for pt in prevts)
                            prev_start = max(0, min(H, int((rep.start_time - horizon.start).total_seconds() // 60)))
                            if any_pinned or prev_start < frozen_min:
                                weight = _PLANNER_PIN_WEIGHT if any_pinned else _FROZEN_PIN_WEIGHT
                                dev = model.NewIntVar(0, H, f"pindev_{key}")
                                model.AddAbsEquality(dev, start - prev_start)   # |start - prev_start|
                                pin_penalty.append(dev * weight)
                                if rep.machine_id and choices:
                                    for lit, eqid in choices:
                                        if eqid == rep.machine_id:
                                            pin_penalty.append((1 - lit) * _MACHINE_PIN_WEIGHT)
                                pins.append((start, prev_start, rep.machine_id, choices))
                                pinned = True
                            else:
                                warm_hints.append((start, prev_start))           # slushy/liquid: warm-start hint

                        tasks.append({'part_ids': lot['part_ids'],
                                      'core_id': lot['core_id'],
                                      'step_id': step_id,
                                      'start': start, 'end': end, 'choices': choices, 'pinned': pinned})
                        node_start[step_id] = start
                        node_end[step_id] = end
                        lot_ends.append(end)

                    # Merge-capable precedence: for each DEFAULT edge start[to] >= end[from];
                    # a node with several predecessors waits for the latest (max) of them.
                    for from_id, to_id in prec:
                        if from_id in node_end and to_id in node_start:
                            model.Add(node_start[to_id] >= node_end[from_id])

                    wo_starts[wo.wo_id].extend(node_start.values())
                    wo_ends[wo.wo_id].extend(node_end.values())
                    for sid, s in node_start.items():
                        wo_step_starts[(wo.wo_id, sid)].append(s)

                    # Lateness is per-LOT (the lot is late or not) — not per piece, so a big
                    # WO no longer swamps the objective with count-many identical late terms.
                    if due_minutes is not None and penalty > 0 and lot_ends:
                        lot_done = model.NewIntVar(0, H, f"done_{lot['label']}")
                        model.AddMaxEquality(lot_done, lot_ends)   # DAG completion = last sink
                        lateness = model.NewIntVar(0, 2 * H, f"late_{lot['label']}")
                        model.Add(lateness >= lot_done - due_minutes)
                        lateness_cost.append(lateness * penalty)
                        lateness_terms.append((lateness, penalty))  # for the isolated total

            # Cross-WO assembly-convergence pegs (plan #9): a component WO must finish
            # (+ staging buffer) before its parent assembly WO may start. Both WOs are in
            # this solve; multi-level BOMs chain transitively (A waits on B waits on C).
            # When the BOM line names the consuming step, only that assembly step waits —
            # pre-assembly parent work can overlap the component build; otherwise (no
            # consumed_at_step authored) the whole parent waits, conservatively.
            for wo in wos:
                parent_id = wo.pegged_to_wo_id
                if not parent_id or parent_id == wo.wo_id:
                    continue
                child_ends = wo_ends.get(wo.wo_id)
                if not child_ends:
                    continue
                if wo.pegged_consumes_step_id is not None:
                    gated = wo_step_starts.get((parent_id, wo.pegged_consumes_step_id))
                else:
                    gated = wo_starts.get(parent_id)
                if not gated:
                    continue   # parent produced no (matching) tasks — e.g. already past it
                child_done = model.NewIntVar(0, H, f"child_done_{wo.wo_id}")
                model.AddMaxEquality(child_done, child_ends)
                for ps in gated:
                    model.Add(ps >= child_done + staging_buffer)

            # Machine capacity. Lights-out machines (the default) run 24/7 and are blocked
            # only by their downtime — a lot-operation may span nights/weekends. Machines
            # flagged attended-only (`runs_unattended=False`) are instead confined to the
            # shift calendar (operator must be present), so their unavailable gaps are the
            # complement of the shift windows. Continuous-feed machines also periodically
            # stop for a bar change; those are recurring fixed downtime over the horizon.
            for equipment_id, intervals in machine_intervals.items():
                if equipment_id in attended_only:
                    gaps = _window_gaps(availability.get(equipment_id, []), horizon.start, H)
                else:
                    gaps = _to_minutes(machine_downtime.get(equipment_id, []), horizon.start, H)
                blocked = [model.NewFixedSizeIntervalVar(gs, ge - gs, f"gap_{equipment_id}_{gs}")
                           for gs, ge in gaps]
                cm = continuous.get(equipment_id)
                if cm is not None and cm.bar_change_interval_hours and cm.bar_change_duration_minutes:
                    step = int(cm.bar_change_interval_hours * 60)
                    dur_bc = max(1, int(round(cm.bar_change_duration_minutes)))
                    t = step
                    while t < H:
                        blocked.append(model.NewFixedSizeIntervalVar(
                            t, min(dur_bc, H - t), f"bar_{equipment_id}_{t}"))
                        t += step + dur_bc
                model.AddNoOverlap(intervals + blocked)

            # Sequence-dependent setup / changeover: for each pair of tasks that could
            # share a machine, insert the changeover gap in whichever order they run
            # (gated on both being assigned to that machine). Same-step neighbours cost
            # 0 (piece after piece); different-step neighbours pay the WorkCenterChangeover
            # (or the incoming step's setup as a fallback). NoOverlap already prevents
            # time overlap; this adds the transition gap on top.
            for equipment_id, mtasks in machine_tasks.items():
                for i in range(len(mtasks)):
                    pi, si, ei, stepi, setupi, woi = mtasks[i]
                    for j in range(i + 1, len(mtasks)):
                        pj, sj, ej, stepj, setupj, woj = mtasks[j]
                        t_ij = _transition(changeover, equipment_id, stepi, stepj, setupj,
                                           woi, woj, job_change_min)
                        t_ji = _transition(changeover, equipment_id, stepj, stepi, setupi,
                                           woj, woi, job_change_min)
                        if not t_ij and not t_ji:
                            continue
                        i_before_j = model.NewBoolVar(f"seq_{equipment_id}_{i}_{j}")
                        model.Add(sj >= ei + t_ij).OnlyEnforceIf([pi, pj, i_before_j])
                        model.Add(si >= ej + t_ji).OnlyEnforceIf([pi, pj, i_before_j.Not()])

            # Secondary gauges: one task at a time per gauge.
            for intervals in gauge_intervals.values():
                model.AddNoOverlap(intervals)

            # Fixtures: cumulative — at most `quantity` concurrent users.
            for fixture_id, intervals in fixture_intervals.items():
                capacity = fixtures[fixture_id].quantity
                model.AddCumulative(intervals, [1] * len(intervals), capacity)

            # Labor capacity (Layer-1 crew constraint): the attended operations may not
            # demand more operators at once than the crew on shift — a cumulative resource
            # whose capacity varies by shift. Deficit "blocker" intervals consume the gap
            # between each segment's headcount and the peak, so an off-shift stretch (count
            # 0) is fully blocked — attended work is pushed into staffed hours while machines
            # keep running lights-out. Skipped entirely when no crew is rostered (cap 0), so
            # a tenant without shift/roster data schedules unconstrained as before.
            def _add_capacity(intervals, windows, tag):
                """Cumulative capping `intervals` at the headcount on shift in `windows`,
                with deficit blockers so low-staff (and zero-staff) stretches are respected."""
                cap, segs = _staffing_segments(windows, horizon.start, H)
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

            # Total crew: no more concurrent attended work than operators on shift (applies
            # to POOL and NAMED lots alike — every attended op needs one of the crew).
            _add_capacity([iv for iv, _, _ in labor_intervals], op_windows, "crew")

            # Per-skill (POOL model only): each training-gated step's attended work is capped
            # at ITS qualified crew on shift, so a scarce skill runs limited-at-a-time and the
            # excess pushes later. NAMED steps are handled exactly below instead.
            pool_intervals: dict = defaultdict(list)
            for iv, sid, m in labor_intervals:
                if m == 'pool':
                    pool = skill_pools.get(sid)
                    if pool:
                        pool_intervals[pool].append(iv)
            for i, (pool, intervals) in enumerate(pool_intervals.items()):
                pool_windows = {u: w for u, w in op_windows.items() if u in pool}
                _add_capacity(intervals, pool_windows, f"skill{i}")

            # NAMED model: a specific operator runs each lot and can't be in two places — a
            # per-operator NoOverlap over their assigned intervals, blocked outside their
            # shift. This is the exact dual-resource assignment for specialist steps.
            for op, intervals in named_op_intervals.items():
                _, off_segs = _staffing_segments({op: op_windows.get(op, [])}, horizon.start, H)
                blockers = [model.NewFixedSizeIntervalVar(a, b - a, f"noff_{op}_{a}")
                            for a, b, c in off_segs if c == 0 and b > a]
                model.AddNoOverlap(intervals + blockers)

            if tasks:
                makespan = model.NewIntVar(0, H, "makespan")
                model.AddMaxEquality(makespan, [t['end'] for t in tasks])
                obj = sum(lateness_cost) + makespan + sum(pin_penalty) + sum(affinity_cost)
                if named_uncovered:
                    # Coverage-first (lexicographic-by-weight): one uncovered attended op is
                    # priced ABOVE the largest the rest of the objective could ever reach, so
                    # the solver NEVER trades coverage for less lateness/makespan — pushing
                    # work late is always preferred to leaving it unstaffed.
                    max_pen = max((_penalty_cents_per_min(config, w.priority) for w in wos), default=0)
                    w_unc = (len(tasks) * 2 * H * max_pen + H
                             + len(pins) * (H * _PLANNER_PIN_WEIGHT + _MACHINE_PIN_WEIGHT)
                             + len(affinity_cost) * _AFFINITY_PENALTY_DEFAULT + 1)
                    obj = obj + w_unc * sum(named_uncovered)
                model.Minimize(obj)

            for var, minute in warm_hints:            # warm-start from the previous schedule
                model.AddHint(var, minute)

            if machine_hints:
                # Hint the MACHINE choice from the machine phase (that layout is good),
                # but NOT the start time — leaving times free lets the operator phase push
                # attended work out into idle capacity to cover it, instead of clinging to
                # the machine phase's compact makespan and parking lots as uncovered.
                for _i, _t in enumerate(tasks):
                    _h = machine_hints.get(_i)
                    if not _h:
                        continue
                    for _lit, _eqid in _t['choices']:
                        if _eqid == _h[1]:
                            model.AddHint(_lit, 1)
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = tlimit

            cp_status = solver.Solve(model) if tasks else cp_model.OPTIMAL
            solved = cp_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            return {'cp_status': cp_status, 'solver': solver, 'tasks': tasks,
                    'pins': pins, 'lateness_terms': lateness_terms, 'solved': solved}

        # Two-phase when operator matching is on AND a crew is rostered: solve machines
        # (pooled labor, ~40% of the budget), then re-solve assigning specific operators
        # warm-started from that layout (~60%). Else a single fast machine solve.
        _match = bool(getattr(config, 'match_operators', False)) and bool(all_op_ids)
        if _match:
            _ta = max(1, int(time_limit_seconds * 0.4))
            _pa = _build_and_solve('pool', None, _ta)
            _hints = None
            if _pa['solved']:
                _sa = _pa['solver']
                _hints = {i: (_sa.Value(t['start']), _chosen_machine(t, _sa))
                          for i, t in enumerate(_pa['tasks'])}
            _pb = _build_and_solve('named', _hints, max(1, time_limit_seconds - _ta))
            _final = _pb if _pb['solved'] else _pa
        else:
            _final = _build_and_solve(None, None, time_limit_seconds)

        solver = _final['solver']
        tasks = _final['tasks']
        pins = _final['pins']
        lateness_terms = _final['lateness_terms']
        cp_status = _final['cp_status']
        solved = _final['solved']

        # How many pins the world forced off their frozen time/machine.
        relaxed = 0
        if tasks and solved:
            for start_var, prev_start, prev_machine_id, choices in pins:
                moved = solver.Value(start_var) != prev_start
                if prev_machine_id:
                    chosen = next((eqid for lit, eqid in choices if solver.Value(lit) == 1), None)
                    if chosen != prev_machine_id:
                        moved = True
                if moved:
                    relaxed += 1

        # The lateness term on its own — priority-weighted late-minutes, isolated from
        # the makespan + pin-stickiness terms that dominate the raw objective.
        weighted_lateness = (
            sum(solver.Value(var) * penalty for var, penalty in lateness_terms)
            if (tasks and solved) else 0
        )

        if draft:
            # A draft is a reviewable what-if; it never supersedes the live schedule.
            # Replace only the prior draft (scratch — cascade-deletes its tasks).
            ScheduleResult.objects.filter(tenant=tenant, is_draft=True).delete()
        else:
            ScheduleResult.objects.filter(tenant=tenant, is_active=True).update(
                is_active=False, is_stale=True)

        result = ScheduleResult.objects.create(
            tenant=tenant,
            horizon_start=horizon.start, horizon_end=horizon.end,
            solver_status=_map_status(cp_status),
            solve_time_ms=int(solver.WallTime() * 1000) if tasks else 0,
            objective_value_cents=int(solver.ObjectiveValue()) if (tasks and solved) else 0,
            weighted_lateness=weighted_lateness,
            relaxed_pin_count=relaxed,
            is_active=not draft,
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
                fence = _fence_zone(solver.Value(t['start']), frozen_min, slushy_min)
                common = dict(
                    tenant=tenant, schedule=result, step_id=t['step_id'],
                    machine_id=machine_id, start_time=start_dt, end_time=end_dt,
                    is_pinned=t['pinned'], fence_zone=fence,
                )
                if t['core_id'] is not None:
                    rows.append(ScheduledTask(core_id=t['core_id'], part_id=None, **common))
                else:
                    for part_id in t['part_ids']:
                        rows.append(ScheduledTask(part_id=part_id, core_id=None, **common))
            # tenant-safe: every row is constructed with tenant=tenant via `common` above.
            ScheduledTask.objects.bulk_create(rows)

        return result
