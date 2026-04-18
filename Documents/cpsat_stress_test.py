"""
CP-SAT Stress Test -- Realistic shop scaling

Shop profiles based on industry data:
  - Typical machine:operator ratio is 1:1 to 2:1 (one operator tends 1-2 machines)
  - QC/QA: ~1 inspector per 6-12 machinists
  - Office/support: ~20-25% of headcount (engineering, planning, shipping, admin)
  - Shop floor: ~75-80% of headcount (operators, leads, QA, material handlers)
  - Active WOs per week: roughly 1-2x the number of machines (jobs rotate through)

Sources:
  - Practical Machinist forums (QC ratios, shop sizes)
  - Modern Machine Shop (Top Shops benchmark data)
  - BLS Occupational Outlook (machinist employment)
"""

import random
import math
import sys
from ortools.sat.python import cp_model
from collections import defaultdict

random.seed(2026)

MINUTES_PER_DAY = 10 * 60      # 4x10 schedule
HORIZON_DAYS = 10               # 2 work weeks of runway for large shops
HORIZON = HORIZON_DAYS * MINUTES_PER_DAY
SOLVE_TIME_LIMIT = 300  # 5 minutes per scenario


# =====================================================================
# REALISTIC SHOP PROFILES
# =====================================================================
# Each profile defines a complete shop: headcount, machines, and workload

PROFILES = [
    {
        "name": "Enterprise (500 ppl, ~1.7k tasks)",
        "total_employees": 500,
        "operators": 300,
        "machines": 250,
        "workcenters": 60,
        "active_wos": 200,
        "parts_per_wo": 3,
        "ops_per_routing": 7,
    },
    {
        "name": "Mega Plant (1000 ppl, ~3.5k tasks)",
        "total_employees": 1000,
        "operators": 600,
        "machines": 400,
        "workcenters": 80,
        "active_wos": 400,
        "parts_per_wo": 3,
        "ops_per_routing": 7,
    },
    {
        "name": "Multi-Site (2000 ppl, ~5k tasks)",
        "total_employees": 2000,
        "operators": 1200,
        "machines": 600,
        "workcenters": 100,
        "active_wos": 600,
        "parts_per_wo": 3,
        "ops_per_routing": 7,
    },
    {
        "name": "Target: 10k tasks",
        "total_employees": 3000,
        "operators": 2000,
        "machines": 800,
        "workcenters": 120,
        "active_wos": 1000,
        "parts_per_wo": 4,
        "ops_per_routing": 7,
    },
]


# =====================================================================
# SHOP GENERATOR
# =====================================================================

def generate_shop(profile):
    """Generate a balanced shop from a profile. Ensures capacity is feasible."""

    num_machines = profile["machines"]
    num_wcs = profile["workcenters"]
    num_wos = profile["active_wos"]
    parts_per_wo = profile["parts_per_wo"]
    ops_per_routing = profile["ops_per_routing"]

    # -- Equipment: distribute evenly, min 2 per WC --
    equipment = {}
    machines_per_wc = max(2, num_machines // num_wcs)
    equip_id = 1
    wc_equip = defaultdict(list)

    for wc_idx in range(num_wcs):
        count = machines_per_wc
        if wc_idx == num_wcs - 1:
            count = max(2, num_machines - equip_id + 1)
        for _ in range(count):
            equipment[equip_id] = {"id": equip_id, "status": "IN_SERVICE"}
            wc_equip[wc_idx + 1].append(equip_id)
            equip_id += 1
            if equip_id > num_machines * 2:  # safety valve
                break

    # -- Work Centers --
    workcenters = {}
    for wc_id in range(1, num_wcs + 1):
        workcenters[wc_id] = {
            "id": wc_id,
            "equipment_ids": wc_equip[wc_id],
            "efficiency": random.choice([92.0, 95.0, 100.0]),
        }

    # -- Steps: one per routing position, assigned to WCs round-robin --
    steps = {}
    for op_idx in range(ops_per_routing):
        step_id = op_idx + 1
        wc_id = (op_idx % num_wcs) + 1

        if random.random() > 0.4:
            # Machine-controlled
            cycle = random.randint(5, 15)
            load = random.randint(1, 3)
            attention = "load_unload"
        else:
            # Manual
            cycle = 0
            load = random.randint(8, 20)
            attention = "full"

        steps[step_id] = {
            "id": step_id,
            "workcenter_id": wc_id,
            "setup_minutes": random.randint(3, 10),
            "cycle_time": cycle,
            "load_unload": load,
            "attention_type": attention,
        }

    # -- Work Orders with realistic load --
    work_orders = []
    part_id = 100
    total_parts = 0
    total_tasks = 0

    for wo_idx in range(num_wos):
        r = random.random()
        priority = 1 if r < 0.1 else (2 if r < 0.5 else 3)

        if priority == 1:
            due_day = random.randint(1, 2)
        elif priority == 2:
            due_day = random.randint(2, min(5, HORIZON_DAYS))
        else:
            due_day = random.randint(3, HORIZON_DAYS)

        num_parts = max(1, parts_per_wo + random.randint(-1, 1))
        parts = []
        for _ in range(num_parts):
            num_ops = random.randint(2, min(4, ops_per_routing))
            routing = sorted(random.sample(range(1, ops_per_routing + 1), num_ops))
            quantity = random.randint(1, 3)
            parts.append({"id": part_id, "routing": routing, "quantity": quantity})
            total_tasks += num_ops
            part_id += 1

        total_parts += len(parts)
        work_orders.append({
            "id": wo_idx + 1,
            "name": f"WO-{wo_idx + 1:04d}",
            "priority": priority,
            "due_day": due_day,
            "parts": parts,
        })

    stats = {
        "total_employees": profile["total_employees"],
        "operators": profile["operators"],
        "work_orders": num_wos,
        "parts": total_parts,
        "tasks": total_tasks,
        "machines": len(equipment),
        "operational": sum(1 for e in equipment.values() if e["status"] == "IN_SERVICE"),
        "workcenters": num_wcs,
    }

    return equipment, workcenters, steps, work_orders, stats


# =====================================================================
# SOLVER
# =====================================================================

def solve_schedule(equipment, workcenters, steps, work_orders, stats, time_limit=SOLVE_TIME_LIMIT):
    model = cp_model.CpModel()
    op_equip = {eid: e for eid, e in equipment.items() if e["status"] == "IN_SERVICE"}

    task_starts, task_ends, task_intervals, task_durations = {}, {}, {}, {}
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

                if step["cycle_time"] > 0:
                    raw = step["setup_minutes"] + step["cycle_time"] * qty + step["load_unload"] * qty
                else:
                    raw = step["setup_minutes"] + step["load_unload"] * qty

                dur = max(1, int(raw / eff))

                start = model.new_int_var(0, HORIZON, f"s_{key[0]}_{key[1]}")
                end = model.new_int_var(0, HORIZON, f"e_{key[0]}_{key[1]}")
                interval = model.new_interval_var(start, dur, end, f"iv_{key[0]}_{key[1]}")

                task_starts[key] = start
                task_ends[key] = end
                task_intervals[key] = interval
                task_durations[key] = dur
                task_meta[key] = {"wo": wo, "part": part, "step": step}

    # Precedence with transfer batch
    for wo in work_orders:
        for part in wo["parts"]:
            routing = part["routing"]
            for i in range(len(routing) - 1):
                from_key = (part["id"], routing[i])
                to_key = (part["id"], routing[i + 1])
                if from_key in task_ends and to_key in task_starts:
                    if part["quantity"] > 1:
                        step = steps[routing[i]]
                        first_piece = step["setup_minutes"] + step["cycle_time"] + step["load_unload"]
                        model.add(task_starts[to_key] >= task_starts[from_key] + max(1, int(first_piece)))
                    else:
                        model.add(task_starts[to_key] >= task_ends[from_key])

    # Horizon constraint
    for key in all_keys:
        model.add(task_ends[key] <= HORIZON)

    # Work center capacity: no-overlap per WC (simplified — treat each WC as
    # having capacity = number of operational machines)
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
            model.add_cumulative(
                [task_intervals[k] for k in wc_tasks],
                [1] * len(wc_tasks),
                wc_equip_up)

    # Objective: minimize weighted lateness + makespan
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

    # Solution callback to track when first feasible is found
    class SolutionTracker(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__()
            self.first_solution_time = None
            self.solution_count = 0
            self.best_objective = None

        def on_solution_callback(self):
            self.solution_count += 1
            self.best_objective = self.ObjectiveValue()
            if self.first_solution_time is None:
                self.first_solution_time = self.WallTime()

    tracker = SolutionTracker()

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.relative_gap_limit = 0.05
    import os
    solver.parameters.num_workers = os.cpu_count() or 8
    # Ensure 3 default_lp instances for efficient optimality proofs.
    # CP-SAT defaults to 2 below 10 workers; 2 extra guarantees 3 at any thread count.
    solver.parameters.extra_subsolvers.extend(['default_lp', 'default_lp'])
    status = solver.solve(model, tracker)

    status_names = {
        cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE", cp_model.MODEL_INVALID: "MODEL_INVALID",
    }

    result = {
        "status": status_names.get(status, str(status)),
        "solve_time": solver.wall_time,
        "first_solution_time": tracker.first_solution_time,
        "solutions_found": tracker.solution_count,
        "solved": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
    }

    if result["solved"]:
        result["makespan"] = solver.value(makespan)
        result["makespan_days"] = solver.value(makespan) / MINUTES_PER_DAY
        result["total_lateness"] = sum(solver.value(v) for v in lateness_vars.values())
        result["late_orders"] = sum(1 for v in lateness_vars.values() if solver.value(v) > 0)

    return result


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    print("=" * 95)
    print("CP-SAT STRESS TEST — Realistic Shop Scaling")
    print(f"  Solve time limit: {SOLVE_TIME_LIMIT}s | Horizon: {HORIZON_DAYS} days x {MINUTES_PER_DAY // 60}hr | Gap: 5%")
    print("=" * 95)

    results = []

    for profile in PROFILES:
        print(f"\n  {'-' * 85}")
        print(f"  {profile['name']}")
        print(f"  {'-' * 85}")

        equip, wcs, steps, wos, stats = generate_shop(profile)

        print(f"    Employees: {stats['total_employees']} total, {stats['operators']} shop floor")
        print(f"    Equipment: {stats['machines']} machines, {stats['workcenters']} work centers")
        print(f"    Workload:  {stats['work_orders']} WOs, {stats['parts']} parts, {stats['tasks']} tasks")

        # Capacity check
        wc_load = defaultdict(int)
        for wo in wos:
            for part in wo["parts"]:
                for step_id in part["routing"]:
                    step = steps[step_id]
                    qty = part["quantity"]
                    if step["cycle_time"] > 0:
                        dur = step["setup_minutes"] + step["cycle_time"] * qty + step["load_unload"] * qty
                    else:
                        dur = step["setup_minutes"] + step["load_unload"] * qty
                    wc_load[step["workcenter_id"]] += dur

        max_util = 0
        for wc_id, load in wc_load.items():
            wc = wcs[wc_id]
            cap = HORIZON_DAYS * MINUTES_PER_DAY * len(wc["equipment_ids"])
            util = load / cap * 100 if cap > 0 else 0
            max_util = max(max_util, util)
        print(f"    Peak WC utilization: {max_util:.0f}%")

        result = solve_schedule(equip, wcs, steps, wos, stats)

        if result["solved"]:
            late_pct = result["late_orders"] / stats["work_orders"] * 100
            first = result["first_solution_time"]
            first_str = f"{first:.1f}s" if first is not None else "?"
            print(f"    OK: {result['status']} in {result['solve_time']:.1f}s | "
                  f"First feasible: {first_str} | "
                  f"Solutions found: {result['solutions_found']} | "
                  f"Makespan: {result['makespan_days']:.1f} days | "
                  f"Late: {result['late_orders']}/{stats['work_orders']} ({late_pct:.0f}%)")
        else:
            print(f"    FAIL: {result['status']} in {result['solve_time']:.1f}s")

        results.append({"profile": profile["name"], **stats, **result})
        sys.stdout.flush()

    # Summary
    print(f"\n\n{'=' * 95}")
    print("SUMMARY")
    print(f"{'=' * 95}")
    print(f"  {'Shop':<28s}  {'Ppl':>4s}  {'Tasks':>5s}  {'Mach':>4s}  "
          f"{'Status':>10s}  {'1st Sol':>8s}  {'Total':>7s}  {'#Sol':>4s}  {'Span':>5s}  {'Late':>8s}")
    print(f"  {'-'*28}  {'-'*4}  {'-'*5}  {'-'*4}  "
          f"{'-'*10}  {'-'*8}  {'-'*7}  {'-'*4}  {'-'*5}  {'-'*8}")

    for r in results:
        span = f"{r['makespan_days']:.1f}d" if r["solved"] else "--"
        late = f"{r.get('late_orders', '--')}/{r['work_orders']}" if r["solved"] else "--"
        first = r.get("first_solution_time")
        first_str = f"{first:.1f}s" if first is not None else "--"
        sols = r.get("solutions_found", 0)
        print(f"  {r['profile']:<28s}  {r['total_employees']:>4d}  {r['tasks']:>5d}  {r['machines']:>4d}  "
              f"{r['status']:>10s}  {first_str:>8s}  {r['solve_time']:>6.1f}s  {sols:>4d}  {span:>5s}  {late:>8s}")

    # Scaling
    solved = [r for r in results if r["solved"]]
    if len(solved) >= 2:
        print(f"\n  Scaling (relative to smallest):")
        base = solved[0]
        for r in solved[1:]:
            task_ratio = r["tasks"] / max(base["tasks"], 1)
            time_ratio = r["solve_time"] / max(base["solve_time"], 0.001)
            print(f"    {r['profile']:<30s}  {task_ratio:>5.1f}x tasks  "
                  f"{time_ratio:>8.1f}x time  "
                  f"({'OK' if r['solve_time'] < 5 else 'SLOW' if r['solve_time'] < 15 else 'AT LIMIT'})")
