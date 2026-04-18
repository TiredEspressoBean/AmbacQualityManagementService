"""
CP-SAT Auto/Aero Worst Case Stress Test v3 — Research-Corrected

Based on industry research:
  Aerospace (AS9100):
    - Lot sizes: 1-50 (typically 1-10 for complex)
    - Operations per routing: 8-15 (mill, turn, grind, deburr, inspect, treat, etc.)
    - Lead times: 2-6 weeks (10-30 working days)
    - Machine mix: 60% mills, 25% lathes, 15% other
    - Machine:employee ratio ~1:2-3 shop floor
    - Setup: 15-45 min, ~2 setups/machine/week
    - Utilization target: 80%

  Automotive (IATF 16949):
    - Batch sizes: 200-1000 per production release
    - Operations per routing: 3-6 (optimized lines)
    - Lead times: weekly releases (3-10 working days)
    - Cycle times: 0.5-3 min/piece
    - Setup: 20-60 min
    - Machines often dedicated to part families
    - Machine:employee ratio ~1:1.5-2 shop floor
"""

import random
import math
import sys
import os
from ortools.sat.python import cp_model
from collections import defaultdict

MINUTES_PER_DAY = 10 * 60
SOLVE_TIME_LIMIT = 300


# =====================================================================
# SOLVER (always returns a schedule — due dates are soft)
# =====================================================================

def solve(name, work_orders, steps, workcenters, equipment, horizon_days):
    PLANNED_HORIZON = horizon_days * MINUTES_PER_DAY
    MAX_HORIZON = PLANNED_HORIZON * 3

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
                task_meta[key] = {"wo": wo, "part": part, "step": step, "dur": dur}

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

    # Objective: all soft
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
    class Tracker(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__()
            self.first_time = None
            self.count = 0
        def on_solution_callback(self):
            self.count += 1
            if self.first_time is None:
                self.first_time = self.WallTime()

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

    total_machine_min = sum(task_meta[k]["dur"] for k in all_keys)
    total_pieces = sum(p["quantity"] for wo in work_orders for p in wo["parts"])

    # Capacity analysis against planned horizon
    wc_load = defaultdict(int)
    for k in all_keys:
        wc_load[steps[k[1]]["workcenter_id"]] += task_meta[k]["dur"]
    peak_util = 0
    for wc_id, load in wc_load.items():
        cap = horizon_days * MINUTES_PER_DAY * len(workcenters[wc_id]["equipment_ids"])
        peak_util = max(peak_util, load / cap * 100 if cap > 0 else 999)

    result = {
        "name": name, "tasks": len(all_keys), "total_pieces": total_pieces,
        "machine_hours": total_machine_min / 60, "peak_util": peak_util,
        "planned_horizon": horizon_days,
        "status": status_names.get(status, str(status)),
        "solve_time": solver.wall_time,
        "first_time": tracker.first_time,
        "solutions": tracker.count,
        "solved": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
        "wos": len(work_orders),
    }
    if result["solved"]:
        result["makespan_days"] = solver.value(makespan) / MINUTES_PER_DAY
        result["late"] = sum(1 for v in lateness_vars.values() if solver.value(v) > 0)
        result["lateness_hrs"] = sum(solver.value(v) for v in lateness_vars.values()) / 60

    return result


def print_result(r):
    overload = " ** OVERLOADED **" if r["peak_util"] > 100 else ""
    print(f"\n    Tasks: {r['tasks']}  Pieces: {r['total_pieces']:,}  "
          f"Machine hrs: {r['machine_hours']:,.0f}h  Peak util: {r['peak_util']:.0f}%{overload}")
    if r["solved"]:
        first = f"{r['first_time']:.1f}s" if r.get('first_time') else "?"
        span = r["makespan_days"]
        overflow = f"  ** overflow +{span - r['planned_horizon']:.0f}d **" if span > r["planned_horizon"] else ""
        late_str = f"Late: {r['late']}/{r['wos']}"
        if r.get("lateness_hrs", 0) > 0:
            late_str += f" ({r['lateness_hrs']:,.0f}h)"
        print(f"    {r['status']} in {r['solve_time']:.1f}s | 1st: {first} | "
              f"Sol: {r['solutions']} | Span: {span:.1f}d / {r['planned_horizon']}d{overflow}")
        print(f"    {late_str}")
    else:
        print(f"    {r['status']} in {r['solve_time']:.1f}s")
    sys.stdout.flush()


def estimate_horizon(work_orders, steps, num_machines):
    total = sum(steps[sid]["setup"] + steps[sid]["cycle"] * p["quantity"] + steps[sid]["load"] * p["quantity"]
                for wo in work_orders for p in wo["parts"] for sid in p["routing"])
    days = total / MINUTES_PER_DAY / max(num_machines, 1)
    return max(10, int(days * 1.5) + 5)


# =====================================================================
# REALISTIC SHOP BUILDERS
# =====================================================================

def build_aero_shop(num_machines, num_wos, seed):
    """Aerospace job shop: high mix, low volume, deep routings.

    Work center distribution (realistic):
      40% CNC Milling (multiple machines)
      20% CNC Turning
      10% Grinding
      10% Deburr/Finishing
      10% Inspection/CMM
      10% Surface Treatment/Other
    """
    random.seed(seed)

    # Work centers sized proportional to workload
    wc_defs = [
        ("CNC Milling",    0.40),
        ("CNC Turning",    0.20),
        ("Grinding",       0.10),
        ("Deburr/Finish",  0.10),
        ("Inspection/CMM", 0.10),
        ("Surface Treat",  0.10),
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
        workcenters[wc_id] = {
            "id": wc_id, "name": wc_name, "equipment_ids": eq_ids,
            "efficiency": random.choice([90.0, 92.0, 95.0]),
        }

    # Operations: each maps to a WC. Aero parts visit most of them.
    # Typical aero routing: mill -> turn -> mill -> grind -> deburr -> inspect -> treat
    steps = {}
    op_wc_sequence = [1, 2, 1, 3, 1, 4, 5, 6, 1, 2, 3, 5]  # 12 ops, milling-heavy
    for op_idx, wc_id in enumerate(op_wc_sequence):
        step_id = op_idx + 1
        if wc_id in (1, 2, 3):  # machine ops
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(20, 45),
                "cycle": random.randint(5, 20),
                "load": random.randint(1, 3),
            }
        elif wc_id == 4:  # deburr (manual)
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(5, 10),
                "cycle": 0,
                "load": random.randint(8, 20),
            }
        elif wc_id == 5:  # inspection
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(5, 15),
                "cycle": 0,
                "load": random.randint(10, 30),
            }
        else:  # surface treatment (batch process)
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(10, 20),
                "cycle": random.randint(30, 60),  # long batch cycle
                "load": random.randint(2, 5),
            }

    # Work orders
    wos = []
    pid = 1000
    for wo_idx in range(num_wos):
        priority = 1 if random.random() < 0.10 else (2 if random.random() < 0.45 else 3)
        due = random.randint(10, 30)  # 2-6 weeks
        parts = []
        for _ in range(random.randint(1, 5)):
            num_ops = random.randint(8, 12)
            routing = sorted(random.sample(range(1, 13), num_ops))
            qty = random.randint(1, 15)
            parts.append({"id": pid, "routing": routing, "quantity": qty})
            pid += 1
        wos.append({"id": wo_idx + 1, "priority": priority, "due_day": due, "parts": parts})

    return equipment, workcenters, steps, wos


def build_auto_shop(num_machines, num_orders, seed):
    """Automotive production shop: low mix, high volume, short routings.

    Work center distribution:
      50% CNC Milling/Machining Centers (production)
      25% CNC Turning/Lathes
      15% Grinding/Finishing
      10% Inspection/Gauging
    """
    random.seed(seed)

    wc_defs = [
        ("Machining Center", 0.50),
        ("CNC Lathe",        0.25),
        ("Grind/Finish",     0.15),
        ("Inspection",       0.10),
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
        workcenters[wc_id] = {
            "id": wc_id, "name": wc_name, "equipment_ids": eq_ids,
            "efficiency": random.choice([92.0, 95.0, 98.0]),  # auto lines are more efficient
        }

    # 6 operations, machining-heavy
    op_wc_sequence = [1, 2, 1, 3, 4, 1]
    steps = {}
    for op_idx, wc_id in enumerate(op_wc_sequence):
        step_id = op_idx + 1
        if wc_id in (1, 2):  # CNC machining
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(20, 60),  # longer setups, but amortized over big runs
                "cycle": random.randint(1, 3),     # fast cycle per piece
                "load": random.randint(1, 2),      # quick load/unload
            }
        elif wc_id == 3:  # grinding
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(15, 30),
                "cycle": random.randint(1, 4),
                "load": 1,
            }
        else:  # inspection
            steps[step_id] = {
                "id": step_id, "workcenter_id": wc_id,
                "setup": random.randint(5, 10),
                "cycle": 0,
                "load": random.randint(2, 5),
            }

    # Orders -> batched WOs
    # Real auto: blanket order for 10,000 parts, released weekly as batches
    wos = []
    pid = 50000
    wo_id = 1
    for order_idx in range(num_orders):
        priority = 1 if random.random() < 0.05 else (2 if random.random() < 0.5 else 3)
        total_qty = random.randint(1000, 5000)
        batch_size = random.randint(200, 500)  # realistic daily/shift batch
        num_batches = math.ceil(total_qty / batch_size)
        base_due = random.randint(3, 10)  # weekly releases, tight deadlines

        for batch_idx in range(num_batches):
            qty = min(batch_size, total_qty - batch_idx * batch_size)
            due = base_due + batch_idx * 5  # weekly stagger
            num_ops = random.randint(3, 6)
            routing = sorted(random.sample(range(1, 7), num_ops))
            parts = [{"id": pid, "routing": routing, "quantity": qty}]
            pid += 1
            wos.append({"id": wo_id, "priority": priority, "due_day": due, "parts": parts})
            wo_id += 1

    return equipment, workcenters, steps, wos


# =====================================================================
# SCENARIOS
# =====================================================================

if __name__ == "__main__":
    print("=" * 90)
    print("WORST CASE STRESS TEST v3 -- Research-Corrected Auto & Aero")
    print(f"  Solve limit: {SOLVE_TIME_LIMIT}s | Workers: {os.cpu_count()}")
    print("=" * 90)

    results = []

    # ---- 1. Aero 100 people (25 machines, 75 WOs) ----
    print(f"\n  {'='*80}")
    print(f"  1. AEROSPACE 100 people")
    print(f"  {'='*80}")
    sys.stdout.flush()

    equip, wcs, steps, wos = build_aero_shop(num_machines=48, num_wos=75, seed=100)
    total_tasks = sum(len(p["routing"]) for wo in wos for p in wo["parts"])
    total_pieces = sum(p["quantity"] for wo in wos for p in wo["parts"])
    machines = len(equip)
    print(f"    {len(wos)} WOs, {total_pieces:,} pieces, {total_tasks} tasks, {machines} machines")
    horizon = estimate_horizon(wos, steps, machines)
    print(f"    Horizon: {horizon} days")
    sys.stdout.flush()
    r = solve("Aero 100ppl", wos, steps, wcs, equip, horizon)
    print_result(r)
    results.append(r)

    # ---- 2. Auto 100 people (45 machines, 20 orders batched) ----
    print(f"\n  {'='*80}")
    print(f"  2. AUTOMOTIVE 100 people")
    print(f"  {'='*80}")
    sys.stdout.flush()

    equip, wcs, steps, wos = build_auto_shop(num_machines=105, num_orders=20, seed=200)
    total_tasks = sum(len(p["routing"]) for wo in wos for p in wo["parts"])
    total_pieces = sum(p["quantity"] for wo in wos for p in wo["parts"])
    machines = len(equip)
    print(f"    20 orders -> {len(wos)} batched WOs, {total_pieces:,} pieces, "
          f"{total_tasks} tasks, {machines} machines")
    horizon = estimate_horizon(wos, steps, machines)
    print(f"    Horizon: {horizon} days")
    sys.stdout.flush()
    r = solve("Auto 100ppl", wos, steps, wcs, equip, horizon)
    print_result(r)
    results.append(r)

    # ---- 3. Aero 200 people (50 machines, 150 WOs) ----
    print(f"\n  {'='*80}")
    print(f"  3. AEROSPACE 200 people")
    print(f"  {'='*80}")
    sys.stdout.flush()

    equip, wcs, steps, wos = build_aero_shop(num_machines=96, num_wos=150, seed=300)
    total_tasks = sum(len(p["routing"]) for wo in wos for p in wo["parts"])
    total_pieces = sum(p["quantity"] for wo in wos for p in wo["parts"])
    machines = len(equip)
    print(f"    {len(wos)} WOs, {total_pieces:,} pieces, {total_tasks} tasks, {machines} machines")
    horizon = estimate_horizon(wos, steps, machines)
    print(f"    Horizon: {horizon} days")
    sys.stdout.flush()
    r = solve("Aero 200ppl", wos, steps, wcs, equip, horizon)
    print_result(r)
    results.append(r)

    # ---- 4. Auto 200 people (80 machines, 40 orders batched) ----
    print(f"\n  {'='*80}")
    print(f"  4. AUTOMOTIVE 200 people")
    print(f"  {'='*80}")
    sys.stdout.flush()

    equip, wcs, steps, wos = build_auto_shop(num_machines=120, num_orders=40, seed=400)
    total_tasks = sum(len(p["routing"]) for wo in wos for p in wo["parts"])
    total_pieces = sum(p["quantity"] for wo in wos for p in wo["parts"])
    machines = len(equip)
    print(f"    40 orders -> {len(wos)} batched WOs, {total_pieces:,} pieces, "
          f"{total_tasks} tasks, {machines} machines")
    horizon = estimate_horizon(wos, steps, machines)
    print(f"    Horizon: {horizon} days")
    sys.stdout.flush()
    r = solve("Auto 200ppl", wos, steps, wcs, equip, horizon)
    print_result(r)
    results.append(r)

    # ---- 5. Mixed 200 people ----
    print(f"\n  {'='*80}")
    print(f"  5. MIXED AUTO+AERO 200 people")
    print(f"  {'='*80}")
    sys.stdout.flush()

    # Build both and combine
    random.seed(500)
    equip_a, wcs_a, steps_a, wos_a = build_aero_shop(num_machines=55, num_wos=80, seed=501)
    equip_b, wcs_b, steps_b, wos_b = build_auto_shop(num_machines=80, num_orders=25, seed=502)

    # Merge: offset auto WC/step/equip IDs to avoid collision
    offset_wc = max(wcs_a.keys())
    offset_step = max(steps_a.keys())
    offset_equip = max(equip_a.keys())
    offset_pid = 90000

    equipment = dict(equip_a)
    workcenters = dict(wcs_a)
    steps_merged = dict(steps_a)

    for eid, e in equip_b.items():
        new_eid = eid + offset_equip
        equipment[new_eid] = {"id": new_eid, "status": e["status"]}

    for wc_id, wc in wcs_b.items():
        new_wc_id = wc_id + offset_wc
        workcenters[new_wc_id] = {
            "id": new_wc_id, "name": wc["name"] + " (Auto)",
            "equipment_ids": [eid + offset_equip for eid in wc["equipment_ids"]],
            "efficiency": wc["efficiency"],
        }

    for sid, s in steps_b.items():
        new_sid = sid + offset_step
        steps_merged[new_sid] = {
            "id": new_sid, "workcenter_id": s["workcenter_id"] + offset_wc,
            "setup": s["setup"], "cycle": s["cycle"], "load": s["load"],
        }

    # Re-map auto WOs to new step IDs
    wos_merged = list(wos_a)
    wo_id = max(wo["id"] for wo in wos_a) + 1
    pid = offset_pid
    for wo in wos_b:
        new_parts = []
        for p in wo["parts"]:
            new_routing = [sid + offset_step for sid in p["routing"]]
            new_parts.append({"id": pid, "routing": new_routing, "quantity": p["quantity"]})
            pid += 1
        wos_merged.append({"id": wo_id, "priority": wo["priority"],
                           "due_day": wo["due_day"], "parts": new_parts})
        wo_id += 1

    total_tasks = sum(len(p["routing"]) for wo in wos_merged for p in wo["parts"])
    total_pieces = sum(p["quantity"] for wo in wos_merged for p in wo["parts"])
    machines = len(equipment)
    print(f"    {len(wos_merged)} WOs (80 aero + batched auto), {total_pieces:,} pieces, "
          f"{total_tasks} tasks, {machines} machines")
    horizon = estimate_horizon(wos_merged, steps_merged, machines)
    print(f"    Horizon: {horizon} days")
    sys.stdout.flush()
    r = solve("Mixed 200ppl", wos_merged, steps_merged, workcenters, equipment, horizon)
    print_result(r)
    results.append(r)

    # ---- SUMMARY ----
    print(f"\n\n{'='*90}")
    print("SUMMARY")
    print(f"{'='*90}")
    print(f"  {'Scenario':<18s}  {'Tasks':>6s}  {'Pieces':>8s}  {'Mach':>4s}  {'Util':>5s}  "
          f"{'Status':>10s}  {'1st':>6s}  {'Total':>7s}  {'Sol':>4s}  {'Late':>10s}")
    print(f"  {'-'*18}  {'-'*6}  {'-'*8}  {'-'*4}  {'-'*5}  "
          f"{'-'*10}  {'-'*6}  {'-'*7}  {'-'*4}  {'-'*10}")

    for r in results:
        first = f"{r['first_time']:.1f}s" if r.get('first_time') else "--"
        late = f"{r.get('late','--')}/{r['wos']}" if r["solved"] else "--"
        machines = int(r["machine_hours"] / max(r.get("planned_horizon", 1) * 10, 1))  # rough
        print(f"  {r['name']:<18s}  {r['tasks']:>6d}  {r['total_pieces']:>8,}  "
              f"     {r['peak_util']:>4.0f}%  "
              f"{r['status']:>10s}  {first:>6s}  {r['solve_time']:>6.1f}s  "
              f"{r['solutions']:>4d}  {late:>10s}")
