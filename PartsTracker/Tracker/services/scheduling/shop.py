"""What a solve reads: the shop as the solver sees it, loaded once per solve.

`Shop` gathers the work, machines and their calendars, the crew, the live plan and the
tenant's settings from the data layer — already converted to integer minutes from the
horizon start where the model needs them — and answers the questions the model builder
asks of them (when a machine can't run, who is on shift, whether held work can stay).
"""
from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from Tracker.services.scheduling import calendars, data
from Tracker.services.scheduling.solver_terms import (
    _SLUSHY_MACHINE_MINUTES, SLUSHY_STICKINESS, _OTWindow, _covered, _earliest_slot,
    _job_change_minutes, _minute, _overlaps, _peak_with, _penalty_cents_per_min,
    _pfd_factor, _staffing_segments, _to_minutes, _window_gaps,
)


class Shop:
    """Everything a solve reads, shared by every phase."""

    def __init__(self, tenant):
        from Tracker.models.scheduling import OptimizationConfig

        self.tenant = tenant
        # A step in the active work that needs a certification no rostered operator
        # holds can't be executed, so nothing is planned from it onward — but the rest
        # of the shop still gets a plan (user decision 2026-10-22: one leaver or one
        # lapsed cert used to refuse every solve). Not scheduled reports the cut work
        # with who holds the cert and why they don't count. (Scarce-but-present skills
        # are handled by the labor capacity: they serialize and push work late.)
        from Tracker.services.scheduling.preflight import find_unstaffable_steps
        self.unstaffable = {(UUID(g['step_id']), g['process_id'])
                            for g in find_unstaffable_steps(tenant)}

        horizon = self.horizon = data.get_schedule_horizon(tenant)
        self.unrunnable = data.get_unrunnable_steps(tenant, horizon)  # every machine down
        H = self.H = max(1, _minute(horizon.end, horizon.start))
        # Room past the horizon end. More work than the horizon holds used to make the
        # whole solve infeasible; now the excess lands out here, isn't written to the
        # board, and is reported in Not scheduled (standard APS overload handling).
        # Calendars, downtime and crew aren't modelled past H — it only has to hold the
        # overflow long enough to say what didn't fit.
        self.H_ext = 3 * H
        self.wos = data.get_active_workorders(tenant)
        self.timings = data.get_step_timings(tenant)
        self.affinities = data.get_step_equipment_affinities(tenant)
        self.availability = data.get_machine_availability(tenant, horizon)
        self.attended_only = data.get_attended_only_machines(tenant)  # shift-confined machines
        self.overtime_windows = calendars.get_overtime_machine_windows(tenant, horizon)  # extra/weekend shifts (union)
        self.machine_downtime = data.get_machine_downtime(tenant, horizon)  # eq -> [(s,e)]
        closures = calendars.get_calendar_closures(tenant, horizon)  # plant holidays/shutdowns
        (self.material_release, self.material_short,
         self.material_detail) = data.get_material_gates(tenant, horizon)  # buy-side
        self.op_windows = calendars.get_operator_shift_windows(tenant, horizon)  # rostered crew
        self.skill_pools = data.get_step_operator_pools(tenant)  # gated step -> qualified crew
        # step -> {op: minute their cert for it lapses}, for lapses inside the horizon.
        self.qual_lapse = {
            sid: {uid: max(0, _minute(lapse, horizon.start))
                  for uid, (lapse, _name) in by_op.items()}
            for sid, by_op in data.get_operator_qualification_lapses(tenant, horizon).items()}
        self.labor_models = data.get_step_labor_models(tenant)  # step -> off|pool|named
        self.all_op_ids = frozenset(o.user_id for o in data.get_dispatchable_operators(tenant))
        self.secondary = data.get_step_secondary_resources(tenant)   # step_id -> {gauge_id}
        self.fixtures = data.get_fixture_availability(tenant)         # fixture_id -> FixtureData
        self.changeover = data.get_changeover_matrix(tenant)         # (equip, from, to) -> minutes
        self.continuous = {cm.equipment_id: cm for cm in data.get_continuous_machines(tenant)}
        prev = data.get_previous_schedule(tenant)                   # for pins + warm-start
        config = self.config = OptimizationConfig.objects.filter(tenant=tenant).first()
        # Outside processing: subcontract steps schedule as elapsed calendar time (no machine/
        # crew); parts already at the vendor pin to their expected return. {step_id: minutes},
        # {part_id: return-minute}.
        osp = data.get_outside_process_data(tenant, config, horizon)
        self.osp_minutes = osp['step_minutes']
        self.osp_return = osp['return_min']
        # Batch/process resources. concurrent_cap → up to N jobs at once (cumulative);
        # cycle_cap → furnace: one load at a time, ceil(count/cap) loads at a fixed cycle time.
        _bc = data.get_machine_batch_capacities(tenant)
        self.concurrent_cap = _bc['concurrent']
        self.cycle_cap = _bc['cycle']

        self.prev_map = {}
        if prev is not None:
            self.prev_map = {(t.part_id, t.step_id): t for t in prev.tasks}
        self.frozen_min = _minute(horizon.frozen_end, horizon.start)
        self.slushy_min = _minute(horizon.slushy_end, horizon.start)
        self.staging_buffer = config.staging_buffer_minutes if config else 0
        self.move_min = config.default_move_minutes if config else 0  # inter-op transfer/queue gap
        # Plant closures (holidays/shutdowns) block EVERY machine, in minute space.
        # Convert conservatively — floor the start, CEIL the end — so a closure is always
        # covered in full (flooring the end would leave its final sub-minute schedulable).
        self.closure_gaps = []
        for _cs, _ce in closures:
            ms = max(0, _minute(_cs, horizon.start))
            me = min(H, -(-int((_ce - horizon.start).total_seconds()) // 60))  # ceil to minute
            if ms < me:
                self.closure_gaps.append((ms, me))
        self.job_change_min = _job_change_minutes(config)   # WO-change setup on the same op
        self.pfd_factor = _pfd_factor(config)               # attended-time allowance multiplier

        self.op_minutes = {u: _to_minutes(w, horizon.start, H) for u, w in self.op_windows.items()}
        _crew_cap, self.crew_segs = _staffing_segments(self.op_windows, horizon.start, H)
        normal_per_min = max(1, _penalty_cents_per_min(config, 3))
        self.slushy_per_min = max(1, round(normal_per_min * SLUSHY_STICKINESS))
        self.slushy_machine_cost = normal_per_min * _SLUSHY_MACHINE_MINUTES

        # Which steps need an unconditional occupancy interval (gauge and/or fixture).
        self.fixture_by_step: dict = defaultdict(list)
        for fx in self.fixtures.values():
            for step_id in fx.step_ids:
                self.fixture_by_step[step_id].append(fx.fixture_id)
        self.occupancy_steps = set(self.secondary) | set(self.fixture_by_step)
        self._gap_cache: dict = {}

    def machine_gaps(self, equipment_id) -> list[tuple]:
        """Minutes a machine can't run: downtime (lights-out machines) or outside the
        shift calendar plus overtime (attended-only ones), and plant closures for
        every machine. Merged, so a NoOverlap over them is well-formed."""
        horizon, H = self.horizon, self.H
        if equipment_id in self.attended_only:
            avail = list(self.availability.get(equipment_id, []))
            avail += [_OTWindow(s, e) for (s, e) in self.overtime_windows]
            gaps = _window_gaps(avail, horizon.start, H)
        else:
            gaps = []
        # Downtime blocks every machine. For an attended one it is also netted out of
        # its shift windows — but with no shift calendar those windows are empty,
        # read as "always available", and a machine down for days stayed bookable.
        gaps += _to_minutes(self.machine_downtime.get(equipment_id, []), horizon.start, H)
        # Merged, so the blocked intervals fed to one AddNoOverlap never overlap.
        return calendars._merge_intervals(gaps + self.closure_gaps)

    def crew_on_shift(self, a, b) -> int:
        """The fewest operators on shift at any point in [a, b)."""
        counts = [c for sa, sb, c in self.crew_segs if sa < b and a < sb]
        return min(counts) if counts else 0

    def frozen_refusal(self, *, prev_raw, **kw):
        """Why a frozen or planner-pinned operation can't be held where the live plan
        put it, as `(code, text)` — or None, when it is held exactly.

        A slot already gone by slides to "now", and everything whose slot went by slides
        there together — so the crew (or its operator) running out at "now" is really
        the slot having passed unstarted, and is reported as that (user decision
        2026-10-27). A machine down or the plant closed still says so."""
        why = self._refusal(prev_raw=prev_raw, **kw)
        if why and prev_raw < 0 and why[0] in ('crew_full', 'operator_unavailable'):
            return ('slot_passed', "its slot passed unstarted")
        return why

    def _refusal(self, *, prev_raw, rep, release_min, mat_lb, choices, durs, dur_free,
                 step_id, lm, front_len, fixed_attended=()):
        """The reason itself, before `frozen_refusal` names a passed slot as such.

        Only reasons it CAN'T happen there: its order may not start yet or its material
        isn't in; its machine is out of service, no longer eligible or blocked
        (downtime, closure, off-shift); the crew on shift is already taken; or its
        operator is off the crew, no longer qualified or not on shift then. A slot that
        has passed, or a predecessor running late, is not a reason: held work slides
        later in its order. A part that moved on, was scrapped or shipped, or whose
        order is held or cancelled, simply isn't in this solve, so its old slot isn't
        consulted at all."""
        ps = max(0, prev_raw)   # a slot already passed slides to now
        if release_min and ps < release_min:
            return ('not_released', "its order can't start that early")
        if mat_lb and ps < mat_lb:
            return ('material', "its material doesn't arrive in time for that slot")
        eq = rep.machine_id
        if choices:
            if eq is None or eq not in durs:
                return ('machine_unavailable',
                        "its machine is out of service or no longer eligible for the step")
            op_dur = durs[eq]
            if _overlaps(ps, ps + op_dur, self.machine_gaps(eq)):
                return ('machine_blocked',
                        "its machine is down, closed or off-shift in that slot")
        else:
            op_dur = dur_free or 1
            if _overlaps(ps, ps + op_dur, self.closure_gaps):
                return ('closure', "the plant is closed in that slot")
        att_len = front_len if front_len is not None else op_dur
        if lm != 'off' and att_len and self.crew_segs:
            # The crew on shift is a hard cap on attended work at once. Held work
            # that would exceed it (another plan's double-booking, the crew shrinking
            # under it) can't all hold; this one goes back to planning.
            if _peak_with(ps, ps + att_len, fixed_attended) > self.crew_on_shift(ps, ps + att_len):
                return ('crew_full', "the crew on shift then is already taken by other "
                        "fixed work")
        op = getattr(rep, 'assigned_operator_id', None)
        if op is not None and lm != 'off':
            if op not in self.all_op_ids:
                return ('operator_off_crew', "its operator is no longer on the crew")
            pool = self.skill_pools.get(step_id)
            if pool is not None and op not in pool:
                return ('operator_unqualified', "its operator is no longer qualified for it")
            att = front_len if front_len is not None else op_dur
            if att and not _covered(ps, ps + att, self.op_minutes.get(op, ())):
                return ('operator_unavailable',
                        "its operator isn't on shift then (rota, leave or training)")
        return None

    def greedy_plan(self, tasks) -> list:
        """A quick dispatch-rule plan: `[(task, (start, end, machine))]`.

        Operations are placed once their predecessors are, earliest due date first
        (higher late penalty breaking ties), each on the eligible machine where it
        finishes soonest — clear of that machine's downtime, closures and off-shift
        time and of whatever is already on it. Held, running and at-vendor work
        stays where it is. Crew limits, changeovers, gauges and fixtures are left to
        CP-SAT, which repairs the hint where it doesn't fit; the point is a good
        first plan in milliseconds, not a feasible one."""
        plan: dict = {}
        busy: dict = defaultdict(list)
        by_id = {id(t): t for t in tasks}
        for t in tasks:
            if t.get('fixed_pos') is not None:
                plan[id(t)] = t['fixed_pos']
                if t['fixed_pos'][2] is not None:
                    busy[t['fixed_pos'][2]].append(t['fixed_pos'][:2])
        pending = [t for t in tasks if id(t) not in plan]
        while pending:
            ready = [t for t in pending if all(id(p) in plan for p in t['preds'])]
            if not ready:          # a cycle can't happen on a resolved route; be safe
                ready = pending
            t = min(ready, key=lambda x: (x['due'] if x['due'] is not None else 10 * self.H,
                                          -(x['prio'] or 0)))
            pending.remove(t)
            est = max([t['est'] or 0] + [plan[id(p)][1] + self.move_min for p in t['preds']])
            if t['durs']:
                best = None
                for eq, d in t['durs'].items():
                    if eq not in self._gap_cache:
                        self._gap_cache[eq] = self.machine_gaps(eq)
                    st = _earliest_slot(est, d, self._gap_cache[eq] + busy[eq])
                    if best is None or st + d < best[1]:
                        best = (st, st + d, eq)
                plan[id(t)] = best
                busy[best[2]].append(best[:2])
            else:
                d = t['dur_free'] or 1
                plan[id(t)] = (est, est + d, None)
        return [(by_id[k], v) for k, v in plan.items()]
