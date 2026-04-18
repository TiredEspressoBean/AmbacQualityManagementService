"""
CP-SAT Warm Start Test — How much faster is re-solving?

Simulates:
  1. Initial solve (cold start, no hints)
  2. Re-solve same problem (warm start, previous solution as hints)
  3. Re-solve after disruption (warm start + 1 machine goes down)
  4. Re-solve after rush order (warm start + 1 new WO added)

Uses the Aero 100 and Aero 200 scenarios from the stress test.
"""

import random
import math
import sys
import os
from ortools.sat.python import cp_model
from collections import defaultdict

MINUTES_PER_DAY = 10 * 60
SOLVE_TIME_LIMIT = 300


class Tracker(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.first_time = None
        self.count = 0
    def on_solution_callback(self):
        self.count += 1
        if self.first_time is None:
            self.first_time = self.WallTime()


def build_and_solve(name, equipment, workcenters, steps, work_orders, horizon_days,
                    hints=None, frozen_before=0, slushy_before=0, slushy_flex=30):
    """Build and solve with time fence zones.

    frozen_before:  tasks starting before this minute are PINNED (can't move at all)
    slushy_before:  tasks starting before this minute (but after frozen) can shift +-slushy_flex
    slushy_flex:    minutes of flexibility in slushy zone (default 30)
    Everything else is liquid (full optimization).
    """
    MAX_HORIZON = horizon_days * MINUTES_PER_DAY * 3

    model = cp_model.CpModel()
    op_equip = {eid: e for eid, e in equipment.items() if e["status"] == "IN_SERVICE"}

    task_starts, task_ends, task_intervals = {}, {}, {}
    all_keys = []
    task_meta = {}

    for wo in work_orders:
        for part in wo["parts"]:
            for step_id in part["routing"]:
                step = steps[step_id]
                key = (part["id"], step_id)
                all_keys.append(key)

                wc = workcenters[step["workcenter_id"]]
                eff = wc["efficiency"] / 100.0
                qty = part["quantity"]
                raw = step["setup"] + step["cycle"] * qty + step["load"] * qty
                dur = max(1, int(raw / eff))

                start = model.new_int_var(0, MAX_HORIZON, f"s_{key[0]}_{key[1]}")
                end = model.new_int_var(0, MAX_HORIZON, f"e_{key[0]}_{key[1]}")
                interval = model.new_interval_var(start, dur, end, f"iv_{key[0]}_{key[1]}")

                task_starts[key] = start
                task_ends[key] = end
                task_intervals[key] = interval
                task_meta[key] = {"dur": dur, "wo": wo, "step": step}

    # Apply warm start hints
    hints_applied = 0
    if hints:
        for key, hint_val in hints.items():
            if key in task_starts:
                model.AddHint(task_starts[key], hint_val)
                hints_applied += 1

    # Freeze tasks before cutoff (frozen zone: can't move at all)
    frozen_count = 0
    if frozen_before > 0 and hints:
        for key, hint_val in hints.items():
            if key in task_starts and hint_val < frozen_before:
                model.add(task_starts[key] == hint_val)
                frozen_count += 1

    # Slushy zone: tasks can shift +-flex but stay close to original time
    slushy_count = 0
    if slushy_before > 0 and hints:
        for key, hint_val in hints.items():
            if key in task_starts and hint_val >= frozen_before and hint_val < slushy_before:
                lo = max(0, hint_val - slushy_flex)
                hi = hint_val + slushy_flex
                model.add(task_starts[key] >= lo)
                model.add(task_starts[key] <= hi)
                slushy_count += 1

    # Precedence
    for wo in work_orders:
        for part in wo["parts"]:
            routing = part["routing"]
            for i in range(len(routing) - 1):
                fk = (part["id"], routing[i])
                tk = (part["id"], routing[i + 1])
                if fk in task_ends and tk in task_starts:
                    if part["quantity"] > 1:
                        step = steps[routing[i]]
                        fp = step["setup"] + step["cycle"] + step["load"]
                        model.add(task_starts[tk] >= task_starts[fk] + max(1, int(fp)))
                    else:
                        model.add(task_starts[tk] >= task_ends[fk])

    # Work center capacity
    for wc_id, wc in workcenters.items():
        wc_equip_up = sum(1 for eid in wc["equipment_ids"] if eid in op_equip)
        if wc_equip_up == 0:
            continue
        wc_tasks = [k for k in all_keys if k in task_intervals
                     and steps[k[1]]["workcenter_id"] == wc_id]
        if not wc_tasks:
            continue
        if wc_equip_up == 1:
            model.add_no_overlap([task_intervals[k] for k in wc_tasks])
        else:
            model.add_cumulative([task_intervals[k] for k in wc_tasks],
                                 [1] * len(wc_tasks), wc_equip_up)

    # Objective
    objective = []
    priority_cost = {1: 400, 2: 100, 3: 20}
    lateness_vars = {}
    for wo in work_orders:
        lateness = model.new_int_var(0, MAX_HORIZON, f"late_{wo['id']}")
        due = wo["due_day"] * MINUTES_PER_DAY
        for part in wo["parts"]:
            last_key = (part["id"], part["routing"][-1])
            if last_key in task_ends:
                model.add(lateness >= task_ends[last_key] - due)
        lateness_vars[wo["id"]] = lateness
        objective.append(lateness * priority_cost[wo["priority"]])

    makespan = model.new_int_var(0, MAX_HORIZON, "makespan")
    for key in task_ends:
        model.add(makespan >= task_ends[key])
    objective.append(makespan * 10)
    model.minimize(sum(objective))

    # Solve
    tracker = Tracker()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT
    solver.parameters.relative_gap_limit = 0.05
    solver.parameters.num_workers = os.cpu_count() or 8
    solver.parameters.extra_subsolvers.extend(['default_lp', 'default_lp'])
    status = solver.solve(model, tracker)

    status_names = {
        cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID",
    }

    solved = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    # Extract solution for warm starting next solve
    solution = {}
    if solved:
        for key in task_starts:
            solution[key] = solver.value(task_starts[key])

    late = sum(1 for v in lateness_vars.values() if solver.value(v) > 0) if solved else 0
    obj = solver.ObjectiveValue() if solved else 0

    first_str = f"{tracker.first_time:.1f}s" if tracker.first_time is not None else "--"
    zones = f"hints:{hints_applied} frozen:{frozen_count} slushy:{slushy_count}"
    print(f"    {name}")
    print(f"      {status_names.get(status):<10s} {solver.wall_time:>6.1f}s  "
          f"1st: {first_str:>6s}  sols: {tracker.count:>4d}  "
          f"obj: {obj:>12,.0f}  late: {late}/{len(work_orders)}  {zones}")
    sys.stdout.flush()

    return solution, solver.wall_time, status_names.get(status)


# =====================================================================
# SHOP BUILDER (same as stress test)
# =====================================================================

def build_aero_shop(num_machines, num_wos, seed):
    random.seed(seed)
    wc_defs = [
        ("CNC Milling", 0.40), ("CNC Turning", 0.20), ("Grinding", 0.10),
        ("Deburr/Finish", 0.10), ("Inspection/CMM", 0.10), ("Surface Treat", 0.10),
    ]
    equipment = {}
    workcenters = {}
    eid = 1
    for wc_id, (wc_name, pct) in enumerate(wc_defs, 1):
        count = max(2, round(num_machines * pct))
        eq_ids = []
        for _ in range(count):
            equipment[eid] = {"id": eid, "status": "IN_SERVICE"}
            eq_ids.append(eid)
            eid += 1
        workcenters[wc_id] = {"id": wc_id, "name": wc_name, "equipment_ids": eq_ids,
                               "efficiency": random.choice([90.0, 92.0, 95.0])}

    steps = {}
    op_wc_sequence = [1, 2, 1, 3, 1, 4, 5, 6, 1, 2, 3, 5]
    for op_idx, wc_id in enumerate(op_wc_sequence):
        step_id = op_idx + 1
        if wc_id in (1, 2, 3):
            steps[step_id] = {"id": step_id, "workcenter_id": wc_id,
                              "setup": random.randint(20, 45), "cycle": random.randint(5, 20),
                              "load": random.randint(1, 3)}
        elif wc_id == 4:
            steps[step_id] = {"id": step_id, "workcenter_id": wc_id,
                              "setup": random.randint(5, 10), "cycle": 0,
                              "load": random.randint(8, 20)}
        elif wc_id == 5:
            steps[step_id] = {"id": step_id, "workcenter_id": wc_id,
                              "setup": random.randint(5, 15), "cycle": 0,
                              "load": random.randint(10, 30)}
        else:
            steps[step_id] = {"id": step_id, "workcenter_id": wc_id,
                              "setup": random.randint(10, 20), "cycle": random.randint(30, 60),
                              "load": random.randint(2, 5)}

    wos = []
    pid = 1000
    for wo_idx in range(num_wos):
        priority = 1 if random.random() < 0.10 else (2 if random.random() < 0.45 else 3)
        due = random.randint(10, 30)
        parts = []
        for _ in range(random.randint(1, 5)):
            num_ops = random.randint(8, 12)
            routing = sorted(random.sample(range(1, 13), num_ops))
            qty = random.randint(1, 15)
            parts.append({"id": pid, "routing": routing, "quantity": qty})
            pid += 1
        wos.append({"id": wo_idx + 1, "priority": priority, "due_day": due, "parts": parts})

    return equipment, workcenters, steps, wos


def estimate_horizon(work_orders, steps, num_machines):
    total = sum(steps[sid]["setup"] + steps[sid]["cycle"] * p["quantity"] + steps[sid]["load"] * p["quantity"]
                for wo in work_orders for p in wo["parts"] for sid in p["routing"])
    days = total / MINUTES_PER_DAY / max(num_machines, 1)
    return max(10, int(days * 1.5) + 5)


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("WARM START TEST -- Cold vs Warm vs Disruption vs Rush Order")
    print(f"  Workers: {os.cpu_count()} | Limit: {SOLVE_TIME_LIMIT}s")
    print("=" * 80)

    for shop_name, num_machines, num_wos, seed in [
        ("AERO 100 people",  48,  75, 100),
        ("AERO 200 people",  96, 150, 300),
    ]:
        print(f"\n  {'='*70}")
        print(f"  {shop_name}")
        print(f"  {'='*70}")
        sys.stdout.flush()

        equip, wcs, steps, wos = build_aero_shop(num_machines, num_wos, seed)
        total_tasks = sum(len(p["routing"]) for wo in wos for p in wo["parts"])
        horizon = estimate_horizon(wos, steps, len(equip))
        print(f"  {len(wos)} WOs, {total_tasks} tasks, {len(equip)} machines, {horizon}d horizon\n")
        sys.stdout.flush()

        # Time fence boundaries:
        #   Frozen:  first 1 day  (current shift, locked down)
        #   Slushy:  days 1-3     (next 2 days, minor adjustments +-30 min)
        #   Liquid:  day 3+       (full optimization)
        frozen_cutoff = 1 * MINUTES_PER_DAY
        slushy_cutoff = 3 * MINUTES_PER_DAY
        slushy_flex = 30  # minutes

        # 1. Cold start (no hints, no fences — morning plan)
        solution, cold_time, cold_status = build_and_solve(
            "1. COLD START (morning plan, no hints)",
            equip, wcs, steps, wos, horizon)

        # 2. Warm start only (hints, no fences)
        _, warm_time, warm_status = build_and_solve(
            "2. WARM START (hints only, no fences)",
            equip, wcs, steps, wos, horizon,
            hints=solution)

        # 3. Warm + frozen only (day 1 pinned)
        _, frozen_time, frozen_status = build_and_solve(
            "3. WARM + FROZEN (day 1 pinned)",
            equip, wcs, steps, wos, horizon,
            hints=solution, frozen_before=frozen_cutoff)

        # 4. Warm + frozen + slushy (full time fence model)
        _, full_fence_time, full_fence_status = build_and_solve(
            "4. WARM + FROZEN + SLUSHY (day1 pin, day2-3 +-30m, rest liquid)",
            equip, wcs, steps, wos, horizon,
            hints=solution, frozen_before=frozen_cutoff,
            slushy_before=slushy_cutoff, slushy_flex=slushy_flex)

        # 5. Disruption: machine goes down, full fence model
        equip_disrupted = dict(equip)
        biggest_wc = max(wcs.values(), key=lambda w: len(w["equipment_ids"]))
        # Pick a machine NOT in frozen zone tasks (avoid infeasibility)
        # Use the last machine in the WC (less likely to have frozen tasks)
        down_eid = biggest_wc["equipment_ids"][-1]
        equip_disrupted[down_eid] = {"id": down_eid, "status": "IN_MAINTENANCE"}
        print(f"\n    [Machine {down_eid} in {biggest_wc['name']} goes DOWN]")
        sys.stdout.flush()

        _, disrupt_warm_time, disrupt_warm_status = build_and_solve(
            "5. DISRUPTION (machine down, warm only)",
            equip_disrupted, wcs, steps, wos, horizon,
            hints=solution)

        _, disrupt_fence_time, disrupt_fence_status = build_and_solve(
            "6. DISRUPTION + FULL FENCES (machine down, frozen+slushy+warm)",
            equip_disrupted, wcs, steps, wos, horizon,
            hints=solution, frozen_before=frozen_cutoff,
            slushy_before=slushy_cutoff, slushy_flex=slushy_flex)

        # 6. Rush order: add 1 urgent WO
        random.seed(seed + 999)
        rush_parts = []
        rush_pid = 99000
        for _ in range(3):
            routing = sorted(random.sample(range(1, 13), random.randint(8, 10)))
            rush_parts.append({"id": rush_pid, "routing": routing, "quantity": random.randint(5, 10)})
            rush_pid += 1
        rush_wo = {"id": 9999, "priority": 1, "due_day": 5, "parts": rush_parts}
        wos_with_rush = list(wos) + [rush_wo]

        rush_tasks = sum(len(p["routing"]) for p in rush_parts)
        print(f"\n    [RUSH ORDER: +1 WO, {rush_tasks} tasks, due Day 5]")
        sys.stdout.flush()

        _, rush_warm_time, rush_warm_status = build_and_solve(
            "7. RUSH ORDER (warm only)",
            equip, wcs, steps, wos_with_rush, horizon,
            hints=solution)

        _, rush_fence_time, rush_fence_status = build_and_solve(
            "8. RUSH + FULL FENCES (frozen+slushy+warm)",
            equip, wcs, steps, wos_with_rush, horizon,
            hints=solution, frozen_before=frozen_cutoff,
            slushy_before=slushy_cutoff, slushy_flex=slushy_flex)

        # Summary
        print(f"\n    {'Scenario':<55s}  {'Time':>7s}  {'Status':>10s}  {'Speedup':>8s}")
        print(f"    {'-'*55}  {'-'*7}  {'-'*10}  {'-'*8}")
        for label, t, s in [
            ("1. Cold start (morning plan)", cold_time, cold_status),
            ("2. Warm only", warm_time, warm_status),
            ("3. Warm + frozen", frozen_time, frozen_status),
            ("4. Warm + frozen + slushy (full fences)", full_fence_time, full_fence_status),
            ("5. Machine down (warm only)", disrupt_warm_time, disrupt_warm_status),
            ("6. Machine down + full fences", disrupt_fence_time, disrupt_fence_status),
            ("7. Rush order (warm only)", rush_warm_time, rush_warm_status),
            ("8. Rush order + full fences", rush_fence_time, rush_fence_status),
        ]:
            speedup = f"{cold_time / max(t, 0.01):.1f}x" if t < cold_time * 0.95 else "--"
            print(f"    {label:<55s}  {t:>6.1f}s  {s:>10s}  {speedup:>8s}")

        sys.stdout.flush()