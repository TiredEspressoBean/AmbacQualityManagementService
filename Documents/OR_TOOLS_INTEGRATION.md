# OR-Tools Integration Plan

## Overview

Three separate services powered by Google OR-Tools CP-SAT:

| Service | Path | Purpose |
|---|---|---|
| **Component Allocator** | `/api/allocator/` | Which harvested component (or buy new) for each WO slot |
| **Machine Schedule** | `/api/scheduling/` | Operations x machines x time (Layer 1: CP-SAT) + operator dispatch (Layer 2: heuristic) |
| **Scenario Planner** | `/api/scenarios/` | What-if analysis -- clones state, runs both solvers, compares results |

The existing Django models (StepEdge DAG, StepExecution, QualityReports, MeasurementResults, TrainingRequirements, CalibrationRecords, reman models) provide nearly everything the solvers need without entering ERP territory.

### Design Principle: No ERP

uqmes knows **what happened on the shop floor**. This integration optimizes using that data. It does not build procurement, HR/payroll, or contract management.

Cost inputs are minimal: `shop_rate_per_hour` (one number per tenant), `overtime_multiplier` (1.5x default), and `late_penalty_per_day` by priority. Where ERP data would help, the architecture supports **integration** with existing systems rather than rebuilding.

---

## The Central Question

> For each component slot on a work order: **use a specific harvested component from inventory, or buy new?**

The right answer depends on condition grade, measurement centrality, historical quality outcomes, core source, schedule pressure, competing demand from other WOs, and technician capability. The solver handles the full picture simultaneously -- the tech currently does this in their head.

---

## Architecture: Two-Layer Scheduling

**Machines are the constraint. People flow to where work is.**

| Layer | What | How | Output |
|---|---|---|---|
| **Layer 1: Machine Schedule** | Which operation, which machine, what time | CP-SAT solver | `ScheduledTask` rows |
| **Layer 2: Operator Dispatch** | Which operator at which work center each shift | Heuristic (not solver) | Dispatch list per work center |

These are separate because coupling operator assignment into the solver makes the model unnecessarily large without improving solution quality. The solver decides machine assignments and timing; a simple heuristic assigns operators based on certifications, skills, and multi-machine tending capability.

### Objective Function (Layer 1)

All costs in cents (CP-SAT requires integers):

```
Minimize: SUM(lateness_days x late_penalty_per_day)
        + makespan
        + SUM(overtime_minutes x shop_rate x overtime_multiplier)
        + SUM(batching_spread x batching_weight)
```

| Priority | Late Penalty/Day |
|---|---|
| Urgent | $2,000 |
| High | $500 |
| Normal | $100 |
| Low | $50 |

---

## Time Elements

Task durations are decomposed into distinct elements (in `StepTiming` model) rather than a single `expected_duration` field.

| Element | Field | Description |
|---|---|---|
| Setup | `setup_minutes` | Sequence-dependent changeover (from `WorkCenterChangeover`) |
| Cycle time | `cycle_time_minutes` | Deterministic per machine cycle. CNC: from the program, not historical averages. |
| Load/unload | `load_unload_per_piece` | Operator touch time per piece |
| Attention type | `attention_type` | `'full'` vs `'load_unload'` -- controls multi-machine tending in Layer 2 |
| External setup | `external_setup_minutes` | SMED overlap with previous op run time |

**Transfer batches:** Next operation starts when the first piece is done, not the full batch. This significantly reduces flow time.

**PFD allowance:** Does NOT inflate task duration in the solver. It is a post-solve capacity validation only. Inflating durations creates artificially long schedules and hides the true critical path.

---

## Time Fence Model

Based on APICS S&OP fence conventions adapted for shop floor scheduling.

| Zone | Duration | What Can Change | Implementation |
|---|---|---|---|
| **Frozen** | 1-2 days | Nothing without management approval | Tasks PINNED (same machine, same time) |
| **Slushy** | 1-2 weeks | Sequence within the day. NOT time windows. | Same machine, same day, sequence free |
| **Liquid** | Everything else | Full optimization | No constraints beyond the model |

| Industry | Typical Frozen | Typical Slushy |
|---|---|---|
| Aerospace/reman | 1-2 days | 1-2 weeks |
| Automotive | 1 week | 2-4 weeks |

Boundaries configurable per tenant via `OptimizationConfig`. Rush orders can penetrate the slushy zone with management approval.

---

## Six Constraint Abstractions

Every constraint the solver handles maps to one of these:

| Abstraction | Examples | Source Models |
|---|---|---|
| **Precedence** | DAG ordering, FPI ordering, decision point branching | `StepEdge`, `Steps.requires_first_piece_inspection` |
| **Time Windows** | Shifts, calibration windows, SPC blocks, ITAR | `CalibrationRecord`, `SPCBaseline`, `Parts.itar_controlled` |
| **Setup/Changeover** | Sequence-dependent machine reconfiguration, SMED | `WorkCenterChangeover`, `StepTiming.external_setup_minutes` |
| **Minimum Gap** | Cure times, drying, transport, max continuous minutes | `Steps.max_continuous_minutes` |
| **Secondary Resource** | QA sign-off, shared fixtures, limited tooling | `Fixture` (cumulative constraint) |
| **Soft Preferences** | Customer batching, machine affinity (dialed-in) | `StepEquipmentAffinity`, objective function terms |

Additional constraint sources: due dates (soft via lateness penalty), no-machine-overlap (implicit), pinned tasks (hard user override), work order HOLD (excluded from model), sampling (probabilistic).

---

## Solver Configuration

### Critical Finding: LP Subsolver Instances

```python
solver.parameters.num_workers = os.cpu_count()
solver.parameters.extra_subsolvers.extend(['default_lp', 'default_lp'])
```

Without 3 LP instances, the solver gets stuck at FEASIBLE indefinitely -- it finds a good solution but cannot prove optimality. The default config only provides enough LP workers at 10+ threads. `extra_subsolvers` fixes this for any thread count.

### Warm Starting

Previous schedule used as hints via `model.AddHint()`. Provides **5-13x speedup**. Combined with frozen zone pins: **6-13x speedup**.

### Solution Streaming

`CpSolverSolutionCallback` pushes improving solutions to the Gantt chart via WebSocket as the solver runs.

---

## Scaling: Stress Test Results

All results with `num_workers = os.cpu_count()` + `extra_subsolvers: ['default_lp', 'default_lp']`.

| Scenario | Tasks | Machines | Status | Time |
|---|---|---|---|---|
| Aero 100 people | 2,280 | 49 | OPTIMAL | 3-8s |
| Aero 200 people | 4,350 | 97 | OPTIMAL | 20-27s |
| Auto 200 people (117k pieces) | 1,575 | 120 | OPTIMAL | 8-14s |
| Mixed auto+aero 200 | 5,296 | -- | OPTIMAL | 28s |
| Enterprise 500 people | 1,762 | 250 | OPTIMAL | 1.1s |

**Scaling tiers:**
- Under 5,000 tasks: single solve, OPTIMAL in under 30 seconds
- 5,000-10,000 tasks: single solve + warm start, OPTIMAL in 30-60s
- 10,000+ tasks: rolling horizon decomposition (2-3 days full detail, 4-7 days aggregate, 8+ capacity buckets)

---

## Continuous Machines

Bar-fed lathes, grinders, and other 24/7 equipment are NOT scheduled task-by-task. They are **capacity sources**. The solver computes when parts will be available based on production rate and uses that as material availability for downstream operations. Operator touch is limited to bar changes and changeovers.

---

## Component Allocator Scoring

The allocator uses CP-SAT to optimize component allocation across all active work orders simultaneously. Scoring factors are objective function terms, not standalone scores:

- **Grade baseline:** A=90, B=70, C=40
- **Measurement centrality:** How centered within tolerance band
- **Component flags:** DISCOLORATION=-15, CORROSION=-20, SEAL_DAMAGE=-25, TIGHT_TOLERANCE=-10, CONTAMINATION=-15, PREV_REPAIR=-20, CLEAN_UNIT=+15, WEAR_PATTERN=-10
- **Historical pass rate:** Per component type, per grade, from QualityReports
- **Core source type:** Some sources historically yield better components
- **Schedule pressure:** Urgent orders penalize risk more heavily
- **FIFO / inventory age:** Preference bonus for older stock (seals dry out, inventory costs money). Soft, not hard FIFO.

---

## Integrated Decision Support: Rework/Scrap

When a part enters quarantine, disposition is coupled to the scheduler. Options (REWORK, SCRAP+NEW, USE AS IS, RETURN) are evaluated with both quality history and schedule impact. A rework decision that looks good in isolation ("85% success rate!") might be wrong when the scheduler shows it pushes three other orders past their due dates.

Margin calculation includes remaining labor cost via `StepTiming` time elements and `shop_rate_per_hour`.

---

## New Django Models

| Model | Key Fields | Purpose | Phase |
|---|---|---|---|
| `StepTiming` | setup_minutes, cycle_time_minutes, load_unload_per_piece, attention_type, external_setup_minutes | Time element decomposition (replaces single expected_duration) | 1 |
| `StepEquipmentAffinity` | step, equipment, affinity (eligible/preferred/dialed_in), cycle_time_override | Machine eligibility and preference per step | 1 |
| `WorkCenterChangeover` | equipment, from_step, to_step, changeover_minutes | Sequence-dependent setup times | 1 |
| `Fixture` | name, quantity, steps (M2M) | Shared tooling with limited quantity | 1 |
| `ComponentCost` | component_type, source (NEW/HARVESTED_A/B/C), unit_cost, lead_time_days | Material cost per source. Only NEW row required at launch. | 1 |
| `ComponentSelectionLog` | work_order, selected_component, solver_recommendation, override_reason, passed_quality | Decision + outcome tracking. Encodes tech instinct over time. | 1 |
| `ComponentFlag` | component, flag (DISCOLORATION/CORROSION/etc), flagged_by | One-tap tags during grading. Become quality predictors after 6mo. | 1 |
| `OptimizationConfig` | shop_rate_per_hour, overtime_multiplier, late_penalty_per_day (by priority), frozen/slushy zone days, pfd_allowance_pct, relative_gap_limit | Per-tenant solver tuning | 1 |
| `ScheduleResult` | horizon, solver_status, solve_time_ms, objective_value_cents, pinned_tasks, is_stale | Cached solver output | 2 |
| `ScheduledTask` | schedule, part, step, machine, start_time, end_time, is_pinned, fence_zone | Individual task from solver. NOTE: no tech field -- tech from Layer 2 dispatch. | 2 |
| `AllocationResult` | solver_status, solve_time_ms, is_stale | Cached allocator output | 2 |
| `ComponentDecision` | allocation, work_order, component_type, selected_component, use_new, score, reasoning | Individual allocation decision | 2 |
| `Scenario` | name, base_schedule, modifications, schedule_result, allocation_result, status | What-if scenario | 3 |
| `ScenarioComparison` | scenario_a, scenario_b, comparison_data | Side-by-side delta analysis | 3 |
| `ContinuousMachine` | equipment, parts_per_hour, bar_change_interval/duration | Lights-out equipment capacity source | 4 |

### Changes to Existing Models

| Model | Field | Purpose |
|---|---|---|
| `Core` | `customer_reported_hours` (IntegerField, null) | Optional scoring enrichment |
| `Core` | `customer_reported_condition` (TextField, blank) | Optional from customer/logbook |
| `Steps` | `max_continuous_minutes` (IntegerField, null) | Epoxy pot life, fatigue limits |
| `StepEdge` | `tech_continuity` (CharField: ANY/SAME/DIFFERENT) | Controls Layer 2 dispatch preference for same/different tech across transitions |

---

## File Structure

```
Tracker/
  scheduling/
    solver.py          # CP-SAT Layer 1 (operations x machines x time)
    dispatch.py         # Layer 2 heuristic (operator-to-work-center)
    models.py           # ScheduleResult, ScheduledTask, OptimizationConfig,
                        #   StepTiming, StepEquipmentAffinity, WorkCenterChangeover,
                        #   Fixture, ContinuousMachine
    views.py
    data.py             # Django ORM --> solver-ready dataclasses
    capacity.py         # Capacity planning + what-if
    disposition.py      # Coupled rework/scrap decisions
  allocator/
    solver.py           # CP-SAT component allocation
    models.py           # ComponentCost, ComponentSelectionLog, ComponentFlag,
                        #   AllocationResult, ComponentDecision
    views.py
  scenarios/
    service.py          # Clone, modify, solve, compare
    models.py           # Scenario, ScenarioComparison
    views.py
  signals/
    optimization_signals.py
```

---

## API Endpoints

### Machine Schedule (`/api/scheduling/`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scheduling/solve/` | Run machine schedule (Layer 1) |
| `POST` | `/api/scheduling/replan/` | Warm-start re-solve |
| `GET` | `/api/scheduling/current/` | Active schedule |
| `GET` | `/api/scheduling/dispatch/{work_center}/` | Dispatch list (Layer 2) |
| `GET` | `/api/scheduling/gantt/` | Gantt data (schedule + dispatch) |
| `POST` | `/api/scheduling/pin/{task}/` | Pin/unpin task |

### Component Allocator (`/api/allocator/`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/allocator/allocate/` | Run allocation solver |
| `GET` | `/api/allocator/current/` | Active allocation |
| `GET` | `/api/allocator/recommendations/{work_order}/` | Ranked options for a WO |
| `POST` | `/api/allocator/override/{decision}/` | Override decision (logs reason) |
| `GET` | `/api/allocator/disposition/{part_id}/` | Disposition recommendation (coupled) |

### Scenario Planner (`/api/scenarios/`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scenarios/create/` | Create what-if scenario |
| `POST` | `/api/scenarios/{id}/solve/` | Solve (runs allocator + scheduler) |
| `GET` | `/api/scenarios/{id}/` | Get results |
| `POST` | `/api/scenarios/compare/` | Side-by-side comparison |
| `POST` | `/api/scenarios/{id}/promote/` | Promote to live schedule |

### Shared

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/scheduling/capacity/` | Capacity analysis (bottlenecks) |
| `POST` | `/api/scheduling/capacity/what-if/` | What-if capacity analysis |
| `GET` | `/api/scheduling/data-readiness/` | Data sufficiency report |

---

## Gantt Chart (Kibo UI)

The Gantt renders `ScheduleResult` + dispatch data using [Kibo UI](https://www.kibo-ui.com/components/gantt). Dependencies: `@dnd-kit/core`, `date-fns`, `jotai`, `lodash/throttle`. Install: `npx kibo-ui add gantt`.

### Solver <-> Gantt Loop

1. Layer 1 solver generates machine schedule --> `ScheduleResult` + `ScheduledTask` rows
2. Layer 2 dispatch assigns operators --> dispatch annotations
3. Frontend groups tasks into `GanttFeatureRow` by selected view
4. Planner drags task bar (center drag = move in time, edges disabled)
5. `POST /api/scheduling/pin/{task}/` with new start time
6. Solver re-optimizes around the pin, dispatch re-runs
7. Gantt re-renders

### Views

| View | Y-axis | Primary User |
|------|--------|---|
| By Work Order | Steps in DAG | Production planner |
| By Machine | Equipment | Maintenance / planner |
| By Work Center | Work centers | Shop supervisor |
| By Part | Steps | Engineer |

### Gantt Data Format

```json
{
  "horizon": {"start": "2026-03-14T06:00:00Z", "end": "2026-03-21T18:00:00Z"},
  "solver_status": "OPTIMAL",
  "solve_time_ms": 2400,
  "time_fences": {"frozen_end": "2026-03-16T06:00:00Z", "slushy_end": "2026-03-24T06:00:00Z"},
  "tasks": [{
    "id": "part_42_step_7",
    "work_order": "WO-2026-0042-A",
    "step": "Flow Testing",
    "machine": {"id": 3, "name": "Test Bench A"},
    "operator": {"id": 5, "name": "Sarah"},
    "start": "2026-03-14T09:30:00Z",
    "end": "2026-03-14T09:55:00Z",
    "is_pinned": false,
    "on_critical_path": true,
    "priority": 2,
    "fence_zone": "slushy",
    "component_source": "HARVESTED_A"
  }],
  "dispatch": [{"work_center": "CNC Bay 1", "operator": {"id": 5, "name": "Sarah"}, "machines": [{"id": 1, "name": "Lathe-01"}]}],
  "warnings": ["Carlos's flow testing cert expires 2026-03-19"],
  "unschedulable": []
}
```

Color coding: priority-based (red/orange/blue/gray) or component source (green/blue/amber/red). Time fence zones as background shading (red=frozen, amber=slushy, white=liquid).

---

## Background Tasks

| Task | Schedule | Time Limit |
|---|---|---|
| `run_schedule_optimization` | Nightly 2am | 300s |
| `run_dispatch_generation` | Morning 6am | 60s |
| `get_disposition_recommendation` | On quarantine (signal) | 30s |
| `run_capacity_analysis` | Weekly Monday 3am | 120s |

All tasks iterate over active tenants. Time limits per-tenant via `OptimizationConfig`.

### Signal-Based Cache Invalidation

Changes to `WorkOrder`, `Parts`, `StepExecution`, `QuarantineDisposition`, `CalibrationRecord`, or `TrainingRecord` mark `ScheduleResult.is_stale = True`. Quarantine events also trigger disposition recommendation.

---

## Data Layer

`scheduling/data.py` -- pure Django ORM, no OR-Tools imports. All functions accept `tenant` for multi-tenancy.

Key functions: `get_step_timings`, `get_machine_availability`, `get_step_equipment_affinities`, `get_changeover_matrix`, `get_fixture_availability`, `get_tech_certifications` (Layer 2), `get_active_workorders`, `get_reman_supply`, `get_component_costs`, `get_spc_status`, `get_schedule_horizon`, `get_data_readiness`.

Duration fallback chain: `StepTiming.cycle_time_minutes` --> `StepExecution` historical average (20+ samples) --> `Steps.expected_duration`.

---

## Extensibility: Reman vs Discrete

| Aspect | Reman | Discrete |
|---|---|---|
| Component selection | Allocator optimizes Grade A/B/C vs new | Not applicable (all new) |
| Setup/changeover | Minimal | Dominates scheduling |
| Batch sizing | Fixed (core yield) | Variable (solver optimizes) |
| Quality risk | Per-grade pass rates | Per-process Cpk |
| Continuous machines | Rare | Common (bar-fed lathes) |

Same solver, same constraints, different data. Discrete uses scheduler heavily but skips the allocator.

[PyJobShop](https://github.com/PyJobShop/PyJobShop) worth evaluating as abstraction layer for scheduling. Allocator stays as direct CP-SAT.

---

## Build Phases

| Phase | Deliverables |
|---|---|
| **1: Data + Allocator** | `scheduling/data.py`, `allocator/solver.py`, StepTiming/StepEquipmentAffinity/WorkCenterChangeover/Fixture/ComponentCost/ComponentSelectionLog/ComponentFlag/OptimizationConfig models, allocator API |
| **2: Machine Schedule + Gantt** | `scheduling/solver.py` (Layer 1), `scheduling/dispatch.py` (Layer 2), ScheduleResult/ScheduledTask/AllocationResult/ComponentDecision models, schedule API, time fences, Celery tasks, Gantt frontend (Kibo UI) |
| **3: Scenarios + Capacity** | `scenarios/service.py`, `scheduling/capacity.py`, `scheduling/disposition.py`, Scenario/ScenarioComparison models, what-if endpoints |
| **4: Continuous Machines + Learning** | ContinuousMachine model, outcome tracking, flag correlation feedback, override analysis |
| **5: Refinement** | Solution streaming, warm start tuning, data readiness dashboard, capacity planner page |

---

## Data Minimum Requirements

| Data Point | Minimum | Fallback |
|---|---|---|
| StepExecution per step | 20+ completions | `StepTiming.cycle_time_minutes` |
| QualityReports per step | 10+ reports | Assume 95% pass rate |
| Per-tech StepExecution | 5+ per tech per step | Overall step average |
| Reman vs new quality split | 10+ each | Don't split |
| HarvestedComponent by grade | 20+ per grade per type | `expected_fallout_rate` |
| StepTiming per step | 1 (manual entry) | StepExecution average |
| StepEquipmentAffinity | 1+ per step | All machines eligible (warn) |

Progressive enhancement: "Limited data" badge first month, high-confidence after 3+ months.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Insufficient data for new tenants | Graceful fallbacks at every level |
| Solver too slow | OPTIMAL under 30s for 5,000 tasks with proper LP config. Warm start 5-13x. |
| Techs don't trust recommendations | Start as suggestions, track outcomes, learn from overrides |
| Gantt pins create infeasibility | Solver reports conflicts, UI shows why |
| Solver stuck at FEASIBLE | `extra_subsolvers: ['default_lp', 'default_lp']` guarantees optimality proofs |
| Schedule churn | Frozen (1-2 days) + slushy (1-2 weeks) fences prevent near-term instability |

---

## Frontend Pages

| Page | What Shows |
|------|-----------|
| Component Selection | Allocator-ranked options + "buy new" comparison |
| Schedule / Gantt | Interactive Gantt with drag-and-drop, time fences, views |
| Dispatch Board | Per-work-center task board (Layer 2 output) |
| Scenario Planner | Create, solve, compare what-if scenarios |
| Capacity Planner | What-if: "Add a test bench --> +83% throughput" |
| Dispositions | Coupled recommendation with schedule impact |
| Data Readiness (admin) | Readiness scores and data gaps |

---

## Dependencies

```
ortools>=9.9
```

No other new dependencies. NumPy and Pandas already installed.
