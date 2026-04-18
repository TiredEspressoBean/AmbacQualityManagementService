"""
Single scenario deep-dive: Mid-size Shop (35 people, 286 tasks)
How long until OPTIMAL? Track every improving solution.
"""

import random
import math
from ortools.sat.python import cp_model
from collections import defaultdict
import sys

random.seed(2026)

MINUTES_PER_DAY = 10 * 60
HORIZON_DAYS = 6
HORIZON = HORIZON_DAYS * MINUTES_PER_DAY
SOLVE_TIME_LIMIT = 86400  # 24 hours — effectively unlimited, run until OPTIMAL


# Reuse the mid-size profile from stress test
def generate_midsize():
    num_machines = 20
    num_wcs = 8
    num_wos = 30
    parts_per_wo = 3
    ops_per_routing = 5

    equipment = {}
    wc_equip = defaultdict(list)
    equip_id = 1
    machines_per_wc = max(2, num_machines // num_wcs)
    for wc_idx in range(num_wcs):
        count = machines_per_wc if wc_idx < num_wcs - 1 else max(2, num_machines - equip_id + 1)
        for _ in range(count):
            equipment[equip_id] = {"id": equip_id, "status": "IN_SERVICE"}
            wc_equip[wc_idx + 1].append(equip_id)
            equip_id += 1

    workcenters = {}
    for wc_id in range(1, num_wcs + 1):
        workcenters[wc_id] = {
            "id": wc_id, "equipment_ids": wc_equip[wc_id],
            "efficiency": random.choice([92.0, 95.0, 100.0]),
        }

    steps = {}
    for op_idx in range(ops_per_routing):
        step_id = op_idx + 1
        wc_id = (op_idx % num_wcs) + 1
        if random.random() > 0.4:
            cycle, load, attention = random.randint(5, 15), random.randint(1, 3), "load_unload"
        else:
            cycle, load, attention = 0, random.randint(8, 20), "full"
        steps[step_id] = {
            "id": step_id, "workcenter_id": wc_id,
            "setup_minutes": random.randint(3, 10), "cycle_time": cycle,
            "load_unload": load, "attention_type": attention,
            "requires_qa": random.random() > 0.8,
        }

    work_orders = []
    part_id = 100
    total_tasks = 0
    for wo_idx in range(num_wos):
        r = random.random()
        priority = 1 if r < 0.1 else (2 if r < 0.5 else 3)
        due_day = (random.randint(1, 2) if priority == 1 else
                   random.randint(2, 5) if priority == 2 else
                   random.randint(3, HORIZON_DAYS))
        num_parts = max(1, parts_per_wo + random.randint(-1, 1))
        parts = []
        for _ in range(num_parts):
            num_ops = random.randint(2, min(4, ops_per_routing))
            routing = sorted(random.sample(range(1, ops_per_routing + 1), num_ops))
            quantity = random.randint(1, 3)
            parts.append({"id": part_id, "routing": routing, "quantity": quantity})
            total_tasks += num_ops
            part_id += 1
        work_orders.append({
            "id": wo_idx + 1, "priority": priority,
            "due_day": due_day, "parts": parts,
        })

    return equipment, workcenters, steps, work_orders, total_tasks


class VerboseCallback(cp_model.CpSolverSolutionCallback):
    """Print every improving solution as it's found."""
    def __init__(self):
        super().__init__()
        self.count = 0
        self.first_time = None
        self.solutions = []

    def on_solution_callback(self):
        self.count += 1
        t = self.WallTime()
        obj = self.ObjectiveValue()
        best_bound = self.BestObjectiveBound()
        gap = abs(obj - best_bound) / max(abs(obj), 1) * 100

        if self.first_time is None:
            self.first_time = t

        self.solutions.append({"time": t, "objective": obj, "bound": best_bound, "gap": gap})

        # Improvement from previous
        if self.count > 1:
            prev = self.solutions[-2]["objective"]
            improvement = (prev - obj) / prev * 100
            print(f"    Solution #{self.count:3d}  at {t:8.1f}s  "
                  f"obj={obj:>12.0f}  bound={best_bound:>12.0f}  "
                  f"gap={gap:5.1f}%  improvement={improvement:5.2f}%",
                  flush=True)
        else:
            print(f"    Solution #{self.count:3d}  at {t:8.1f}s  "
                  f"obj={obj:>12.0f}  bound={best_bound:>12.0f}  "
                  f"gap={gap:5.1f}%  (first feasible)",
                  flush=True)


def solve(equipment, workcenters, steps, work_orders, total_tasks):
    model = cp_model.CpModel()
    op_equip = {eid: e for eid, e in equipment.items() if e["status"] == "IN_SERVICE"}

    task_starts, task_ends, task_intervals, task_durations = {}, {}, {}, {}
    all_keys = []

    for wo in work_orders:
        for part in wo["parts"]:
            for step_id in part["routing"]:
                step = steps[step_id]
                key = (part["id"], step_id)
                all_keys.append(key)
                wc = workcenters[step["workcenter_id"]]
                eff = wc["efficiency"] / 100.0
                qty = part["quantity"]
                raw = (step["setup_minutes"] + step["cycle_time"] * qty + step["load_unload"] * qty
                       if step["cycle_time"] > 0 else
                       step["setup_minutes"] + step["load_unload"] * qty)
                dur = max(1, int(raw / eff))
                start = model.new_int_var(0, HORIZON, f"s_{key[0]}_{key[1]}")
                end = model.new_int_var(0, HORIZON, f"e_{key[0]}_{key[1]}")
                interval = model.new_interval_var(start, dur, end, f"iv_{key[0]}_{key[1]}")
                task_starts[key] = start
                task_ends[key] = end
                task_intervals[key] = interval
                task_durations[key] = dur

    # Precedence with transfer batch
    for wo in work_orders:
        for part in wo["parts"]:
            routing = part["routing"]
            for i in range(len(routing) - 1):
                fk = (part["id"], routing[i])
                tk = (part["id"], routing[i + 1])
                if fk in task_ends and tk in task_starts:
                    if part["quantity"] > 1:
                        step = steps[routing[i]]
                        fp = step["setup_minutes"] + step["cycle_time"] + step["load_unload"]
                        model.add(task_starts[tk] >= task_starts[fk] + max(1, int(fp)))
                    else:
                        model.add(task_starts[tk] >= task_ends[fk])

    for key in all_keys:
        model.add(task_ends[key] <= HORIZON)

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

    # QA sign-off (same as stress test — adds 5min gap after QA-required steps)
    for key in all_keys:
        step = steps[key[1]]
        if not step.get("requires_qa", False):
            continue
        part = None
        for wo in work_orders:
            for p in wo["parts"]:
                if p["id"] == key[0]:
                    part = p
                    break
            if part:
                break
        if not part:
            continue
        routing = part["routing"]
        idx = routing.index(key[1]) if key[1] in routing else -1
        if 0 <= idx < len(routing) - 1:
            next_key = (part["id"], routing[idx + 1])
            if next_key in task_starts:
                model.add(task_starts[next_key] >= task_ends[key] + 5)

    # Objective
    objective = []
    priority_cost = {1: 400, 2: 100, 3: 20}
    lateness_vars = {}
    for wo in work_orders:
        lateness = model.new_int_var(0, HORIZON, f"late_{wo['id']}")
        due = wo["due_day"] * MINUTES_PER_DAY
        for part in wo["parts"]:
            last_key = (part["id"], part["routing"][-1])
            if last_key in task_ends:
                model.add(lateness >= task_ends[last_key] - due)
        lateness_vars[wo["id"]] = lateness
        objective.append(lateness * priority_cost[wo["priority"]])

    makespan = model.new_int_var(0, HORIZON, "makespan")
    for key in task_ends:
        model.add(makespan >= task_ends[key])
    objective.append(makespan * 10)

    model.minimize(sum(objective))

    print(f"\n  Solving {total_tasks} tasks, limit {SOLVE_TIME_LIMIT}s...")
    print(f"  Watching for every improving solution:\n", flush=True)

    callback = VerboseCallback()
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT
    solver.parameters.relative_gap_limit = 0.05
    solver.parameters.num_workers = 16
    status = solver.solve(model, callback)

    status_names = {
        cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID",
    }

    print(f"\n  {'=' * 70}")
    print(f"  Final: {status_names.get(status, str(status))} in {solver.wall_time:.1f}s")
    print(f"  Solutions found: {callback.count}")
    if callback.first_time is not None:
        print(f"  First feasible: {callback.first_time:.1f}s")
    if callback.solutions:
        first_obj = callback.solutions[0]["objective"]
        last_obj = callback.solutions[-1]["objective"]
        total_improvement = (first_obj - last_obj) / first_obj * 100
        print(f"  First objective:  {first_obj:,.0f}")
        print(f"  Final objective:  {last_obj:,.0f}")
        print(f"  Total improvement: {total_improvement:.1f}%")
        print(f"  Final gap: {callback.solutions[-1]['gap']:.1f}%")

        print(f"\n  Solution timeline:")
        for s in callback.solutions:
            bar_len = max(1, int(50 * s["objective"] / first_obj))
            bar = "#" * bar_len
            print(f"    {s['time']:>8.1f}s  {bar}  {s['objective']:>12,.0f}  gap={s['gap']:.1f}%")


if __name__ == "__main__":
    print("=" * 70)
    print("Mid-size Shop Deep Dive (35 people, ~286 tasks)")
    print("How long to reach OPTIMAL?")
    print("=" * 70, flush=True)

    equip, wcs, steps, wos, total_tasks = generate_midsize()
    print(f"\n  Generated: {len(wos)} WOs, {total_tasks} tasks, {len(equip)} machines", flush=True)
    solve(equip, wcs, steps, wos, total_tasks)
