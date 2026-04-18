# Scheduling System Implementation Plan

Step-by-step build plan for the OR-Tools scheduling system described in `OR_TOOLS_INTEGRATION.md`. Each phase is dependency-ordered, testable in isolation, and marked as internal or customer-facing.

**Existing models referenced:** `Steps`, `StepEdge`, `StepExecution`, `Parts`, `WorkOrder`, `Processes`, `Equipments`, `WorkCenter`, `Shift`, `ScheduleSlot`, `DowntimeEvent` (in `mes_lite.py` and `mes_standard.py`).

**Target file structure** (all within existing Tracker app):

```
Tracker/
  models/
    scheduling.py       # All new models: StepTiming, ScheduleResult, etc.
  services/
    scheduling/
      solver.py         # CP-SAT Layer 1
      dispatch.py       # Layer 2 heuristic
      data.py           # ORM → solver dataclasses
      allocator.py      # Component allocation (reman)
      scenarios.py      # What-if service
      capacity.py       # Bottleneck analysis
  viewsets/
    scheduling.py       # All scheduling/allocator/scenario endpoints
  serializers/
    scheduling.py       # All scheduling serializers
  tests/
    test_scheduling.py  # Solver, dispatch, allocator, scenario tests
```

**Total new files: ~10.** No new Django apps, no new urls.py/admin.py boilerplate. Models in existing models dir. Views in existing viewsets dir. Tasks in existing tasks.py.

---

## Phase 0: Foundation (Models + Migrations)

**Goal:** Create all new Django models the solver reads from and writes to. No solver code yet.

**Customer-facing:** No. Internal only.

**Dependencies:** None.

**Requires migration:** Yes.

### Models to Create

| Model | Location | Key Fields | FK / M2M Targets |
|---|---|---|---|
| `StepTiming` | `scheduling/models.py` | `step` (O2O→Steps), `setup_minutes`, `cycle_time_minutes`, `load_unload_per_piece`, `attention_type` (full/load_unload), `external_setup_minutes` | Steps |
| `StepEquipmentAffinity` | `scheduling/models.py` | `step` (FK→Steps), `equipment` (FK→Equipments), `affinity` (eligible/preferred/dialed_in), `cycle_time_override` | Steps, Equipments |
| `WorkCenterChangeover` | `scheduling/models.py` | `equipment` (FK→Equipments), `from_step` (FK→Steps), `to_step` (FK→Steps), `changeover_minutes` | Equipments, Steps |
| `Fixture` | `scheduling/models.py` | `name`, `quantity`, `steps` (M2M→Steps) | Steps |
| `OptimizationConfig` | `scheduling/models.py` | `tenant` (O2O), `shop_rate_per_hour`, `overtime_multiplier`, `late_penalty_urgent/high/normal/low`, `frozen_zone_days`, `slushy_zone_days`, `pfd_allowance_pct`, `relative_gap_limit` | Tenant |
| `ScheduleResult` | `scheduling/models.py` | `tenant`, `horizon_start/end`, `solver_status`, `solve_time_ms`, `objective_value_cents`, `is_stale`, `is_active`, `created_at` | Tenant |
| `ScheduledTask` | `scheduling/models.py` | `schedule` (FK→ScheduleResult), `part` (FK→Parts), `step` (FK→Steps), `machine` (FK→Equipments), `start_time`, `end_time`, `is_pinned`, `fence_zone` (frozen/slushy/liquid) | ScheduleResult, Parts, Steps, Equipments |
| `ContinuousMachine` | `scheduling/models.py` | `equipment` (O2O→Equipments), `parts_per_hour`, `bar_change_interval_hours`, `bar_change_duration_minutes` | Equipments |

### Fields to Add to Existing Models

| Model | Field | Type | Migration |
|---|---|---|---|
| `Steps` | `max_continuous_minutes` | IntegerField(null=True) | AlterModel |
| `StepEdge` | `tech_continuity` | CharField(max_length=10, default='ANY', choices=ANY/SAME/DIFFERENT) | AlterModel |

### Files to Create / Modify

| Action | File | What |
|---|---|---|
| Create | `Tracker/models/scheduling.py` | All 8 models above |
| Modify | `Tracker/models/__init__.py` | Import scheduling models |
| Modify | `Tracker/models/mes_lite.py` | Add `max_continuous_minutes` to Steps, `tech_continuity` to StepEdge |
| Create | `Tracker/tests/test_scheduling_models.py` | Model creation + method tests |
| Create | `Tracker/management/commands/seed_scheduling.py` | Seed script matching playground data |

**Estimated files:** 3 create, 2 modify. Plus 1 migration (auto-generated).

### Tests

- **Model CRUD:** Create each model, verify fields save and load.
- **StepTiming methods:** Implement and test `machine_wall_time()`, `first_piece_done()`, `operator_attended_time()` -- ported from playground's `OperationTiming`.
- **Migration reversibility:** Run `migrate` forward and backward.
- **Unique constraints:** Verify `StepEquipmentAffinity` unique_together on (step, equipment), `WorkCenterChangeover` unique_together on (equipment, from_step, to_step).
- **Seed script:** Populate sample data matching playground STEPS, EQUIPMENT, WORKCENTERS dicts. Print summary to verify counts.

### Smoke Test

```
python manage.py makemigrations Tracker
python manage.py migrate
python manage.py shell -c "from Tracker.models.scheduling import *; print(StepTiming.objects.count())"
python manage.py seed_scheduling
```

---

## Phase 1: Scheduling Data Layer

**Goal:** Django ORM to solver-ready dataclass translation. Pure queries, no OR-Tools imports.

**Customer-facing:** No. Internal only.

**Dependencies:** Phase 0.

**Requires migration:** No.

### Files to Create

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/data.py` | All `get_*` functions + dataclasses |

**Estimated files:** 1 create. Tests go in existing `test_scheduling_models.py` or a new `test_scheduling_data.py`.

### Functions in `data.py`

| Function | Returns | Source Models |
|---|---|---|
| `get_active_workorders(tenant)` | List of WO dataclasses with parts, steps, edges | WorkOrder, Parts, Steps, StepEdge |
| `get_step_timings(tenant)` | Dict[step_id, TimingData] with fallback chain | StepTiming → StepExecution avg → Steps.expected_duration |
| `get_machine_availability(tenant, horizon)` | Per-equipment shift windows minus downtime | Equipments, WorkCenter, Shift, DowntimeEvent |
| `get_step_equipment_affinities(tenant)` | Dict[step_id, List[AffinityData]] | StepEquipmentAffinity |
| `get_changeover_matrix(tenant)` | Dict[(equip_id, from_step, to_step), minutes] | WorkCenterChangeover |
| `get_fixture_availability(tenant)` | Dict[fixture_id, FixtureData] with quantity + step set | Fixture |
| `get_tech_certifications(tenant)` | Dict[user_id, Set[step_id]] | TrainingRequirement |
| `get_schedule_horizon(tenant)` | (start_dt, end_dt, frozen_end, slushy_end) | OptimizationConfig |
| `get_continuous_machines(tenant)` | List[ContinuousMachineData] | ContinuousMachine |
| `get_previous_schedule(tenant)` | Optional warm-start hints | ScheduleResult, ScheduledTask |

### Duration Fallback Chain

1. `StepTiming.cycle_time_minutes` (if StepTiming exists for this step)
2. `StepExecution` historical average (if 20+ completions exist)
3. `Steps.expected_duration` (always present, coarsest fallback)

### Tests

- **Each function against seeded data:** Use Phase 0 seed script, verify output structure and values.
- **Fallback chain:** Create step with no StepTiming, verify it falls through to history. Create step with no history, verify it falls through to expected_duration.
- **Performance:** Seed 100 WOs with 10 parts each, 5 steps per part. Data layer should complete in <1s.
- **Empty tenant:** Verify all functions return empty collections gracefully, no crashes.

### Smoke Test

```
python manage.py runscript scheduling.tests.seed_scheduling_data
python manage.py shell -c "
from Tracker.services.scheduling.data import *
wo = get_active_workorders(tenant=1)
print(f'{len(wo)} work orders loaded')
timings = get_step_timings(tenant=1)
print(f'{len(timings)} step timings (with fallbacks)')
"
```

---

## Phase 2: Machine Schedule Solver (Layer 1)

**Goal:** CP-SAT solver that takes data layer output and produces a machine schedule.

**Customer-facing:** No. Internal only. But this is the core -- everything after depends on it.

**Dependencies:** Phase 0, Phase 1.

**Requires migration:** No.

### Files to Create

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/solver.py` | CP-SAT model builder + solve + result writer |
| Create | `Tracker/tests/test_scheduling_solver.py` | Constraint and integration tests |
| Create | `Tracker/tests/test_scheduling_stress.py` | Stress test scenarios from playground |
| Modify | `requirements.txt` | Add `ortools>=9.9` |

**Estimated files:** 3 create, 1 modify.

### Solver Structure

`solver.py` exposes one main function:

```python
def solve_schedule(
    tenant_id: int,
    warm_start: bool = True,
    time_limit_seconds: int = 300,
) -> ScheduleResult:
```

Internally organized as constraint builders:

| Builder Function | Constraint Type | Source |
|---|---|---|
| `_add_precedence_constraints()` | StepEdge DAG ordering, FPI ordering | StepEdge, Steps.requires_first_piece_inspection |
| `_add_time_window_constraints()` | Shift availability, calibration windows | Shift, CalibrationRecord |
| `_add_capacity_constraints()` | One task per machine at a time | Implicit (IntervalVar NoOverlap) |
| `_add_fixture_constraints()` | Shared tooling limits | Fixture (cumulative constraint) |
| `_add_changeover_constraints()` | Sequence-dependent setup | WorkCenterChangeover, CircuitConstraint |
| `_add_batching_constraints()` | Transfer batch (next op starts at first-piece-done) | StepTiming.first_piece_done() |
| `_add_affinity_constraints()` | Machine preference soft costs | StepEquipmentAffinity |
| `_add_continuous_machine_constraints()` | Lights-out feed rate | ContinuousMachine |
| `_add_time_fence_constraints()` | Frozen pins, slushy same-machine-same-day | OptimizationConfig, ScheduledTask.is_pinned |

Solver config: `num_workers = os.cpu_count()`, `extra_subsolvers = ['default_lp', 'default_lp']`.

### Tests

| Test | What It Verifies |
|---|---|
| Precedence unit test | Task B cannot start before Task A ends (from StepEdge) |
| Capacity unit test | No two tasks overlap on same machine |
| Fixture unit test | At most N tasks use fixture simultaneously |
| Changeover unit test | Setup time inserted between different step types on same machine |
| Playground integration test | Seed playground data, solve, verify makespan and assignments match |
| Stress test (100-person aero) | 2,280 tasks, 49 machines. OPTIMAL in <10s |
| Stress test (200-person aero) | 4,350 tasks, 97 machines. OPTIMAL in <30s |
| Warm start test | Solve once, re-solve with hints. Verify wall time drops 5x+ |
| Time fence test | Pin 3 tasks (frozen). Verify start_time unchanged after re-solve |
| Edge case: all machines down | Returns FEASIBLE with lateness, not INFEASIBLE |
| Edge case: empty WO list | Returns empty ScheduleResult, no crash |

### Smoke Test

```
python manage.py runscript scheduling.tests.seed_scheduling_data
python manage.py shell -c "
from Tracker.services.scheduling.solver import solve_schedule
result = solve_schedule(tenant_id=1)
print(f'Status: {result.solver_status}, Time: {result.solve_time_ms}ms')
print(f'Tasks scheduled: {result.tasks.count()}')
"
```

---

## Phase 3: Operator Dispatch (Layer 2)

**Goal:** Heuristic that assigns operators to work centers per shift, given the machine schedule.

**Customer-facing:** No. Internal only.

**Dependencies:** Phase 2.

**Requires migration:** No.

### Files to Create

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/dispatch.py` | Dispatch heuristic + scoring |
| Create | `Tracker/tests/test_scheduling_dispatch.py` | Scoring and assignment tests |

**Estimated files:** 2 create.

### Dispatch Logic

```python
def generate_dispatch(
    schedule: ScheduleResult,
    tenant_id: int,
) -> dict:
    """Returns {work_center_id: {shift: [DispatchAssignment]}}"""
```

**Scoring factors per operator-to-work-center assignment:**

| Factor | Weight | Source |
|---|---|---|
| Certification coverage | 40% | TrainingRequirement (covers steps in WC that shift) |
| QA capability | 20% | User.groups includes QA (for steps needing signoff) |
| Step preference / speed | 15% | StepExecution history (operator's avg time vs global avg) |
| Work center stickiness | 15% | Yesterday's assignment (reduces context switching) |
| Multi-machine tending fit | 10% | StepTiming.attention_type='load_unload' (operator can tend 2+ machines) |

**Output:** Dispatch list per work center per shift. Tasks sorted by scheduled start time. Unassigned tasks flagged with reason.

### Tests

| Test | What It Verifies |
|---|---|
| Scoring unit test | Given known inputs, verify score components calculate correctly |
| No double-booking | Operator assigned to at most 1 work center per shift |
| All tasks covered | Every scheduled task in shift has an operator or is flagged UNASSIGNED |
| Operator callout | Remove operator, re-dispatch. Tasks reassigned or flagged |
| tech_continuity=SAME | Same operator assigned to consecutive steps on same part |
| Playground comparison | Given Phase 2 schedule, dispatch matches playground output |

### Smoke Test

```
python manage.py shell -c "
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.services.scheduling.dispatch import generate_dispatch
result = solve_schedule(tenant_id=1)
dispatch = generate_dispatch(result, tenant_id=1)
for wc, shifts in dispatch.items():
    print(f'WC {wc}: {sum(len(s) for s in shifts.values())} assignments')
"
```

---

## Phase 4: Schedule API + Celery Tasks

**Goal:** REST API endpoints and background task infrastructure.

**Customer-facing:** YES. First customer-facing deliverable. API is live, Celery runs nightly. No UI yet.

**Dependencies:** Phase 2, Phase 3.

**Requires migration:** No (models already exist from Phase 0).

### Files to Create / Modify

| Action | File | What |
|---|---|---|
| Create | `Tracker/viewsets/scheduling.py` | DRF viewsets for all endpoints |
| Create | `Tracker/serializers/scheduling.py` | Request/response serializers |
| Modify | `Tracker/tasks.py` | Add scheduling Celery tasks |
| Modify | `PartsTrackerApp/urls.py` | Register scheduling viewsets |
| Modify | `PartsTrackerApp/settings.py` | Celery beat schedule entries |

**Estimated files:** 2 create, 3 modify.

### API Endpoints

| Method | Path | Permission | Description |
|---|---|---|---|
| POST | `/api/scheduling/solve/` | Planner | Trigger full solve, return ScheduleResult |
| POST | `/api/scheduling/replan/` | Planner | Warm-start re-solve |
| GET | `/api/scheduling/current/` | Authenticated | Active schedule summary |
| GET | `/api/scheduling/dispatch/{wc}/` | Authenticated | Dispatch list for work center |
| GET | `/api/scheduling/gantt/` | Authenticated | Gantt JSON (format from architecture doc) |
| POST | `/api/scheduling/pin/{task_id}/` | Planner | Pin/unpin a scheduled task |

### Celery Tasks

| Task | Schedule | Time Limit | What |
|---|---|---|---|
| `run_schedule_optimization` | Nightly 2am | 300s | Full solve per active tenant |
| `run_dispatch_generation` | Morning 6am | 60s | Dispatch per active tenant |

### Signal-Based Cache Invalidation

On save/delete of WorkOrder, Parts, StepExecution, DowntimeEvent:
- Set `ScheduleResult.is_stale = True` for that tenant's active result.

### Tests

| Test | What It Verifies |
|---|---|
| POST /solve/ returns 202 | Solve triggers, result stored |
| GET /current/ returns active schedule | Serialized ScheduleResult with task count |
| GET /gantt/ matches schema | JSON structure matches architecture doc format |
| POST /pin/ toggles is_pinned | Task.is_pinned flipped, result marked stale |
| GET /dispatch/{wc}/ returns list | Grouped by shift, ordered by start_time |
| Permission: operator cannot POST /solve/ | Returns 403 |
| Celery task mocked | Verify task calls solver and stores result |
| Cache invalidation | Create WO, verify is_stale flipped on active ScheduleResult |

### Smoke Test

```
curl -X POST http://localhost:8000/api/scheduling/solve/ -H "Authorization: Token ..."
curl http://localhost:8000/api/scheduling/gantt/ -H "Authorization: Token ..."
```

---

## Phase 5: Gantt UI

**Goal:** Frontend interactive Gantt chart connected to the schedule API.

**Customer-facing:** YES. The big planning feature.

**Dependencies:** Phase 4.

**Requires migration:** No.

### Files to Create

| Action | File | What |
|---|---|---|
| Create | `ambac-tracker-ui/src/pages/scheduling/GanttPage.tsx` | Main Gantt page |
| Create | `ambac-tracker-ui/src/pages/scheduling/GanttChart.tsx` | Kibo UI Gantt wrapper |
| Create | `ambac-tracker-ui/src/pages/scheduling/GanttToolbar.tsx` | View switcher, solve button, filters |
| Create | `ambac-tracker-ui/src/hooks/useScheduleGantt.ts` | GET /scheduling/gantt/ hook |
| Create | `ambac-tracker-ui/src/hooks/usePinTask.ts` | POST /scheduling/pin/ hook |
| Create | `ambac-tracker-ui/src/hooks/useSolveSchedule.ts` | POST /scheduling/solve/ hook |
| Modify | `ambac-tracker-ui/src/router.tsx` | Add /scheduling/gantt route |

**Estimated files:** 6 create, 1 modify.

### Gantt Features

| Feature | Implementation |
|---|---|
| Views: by WO, by machine, by work center | Y-axis grouping toggle, re-fetch with `?view=machine` |
| Drag-and-drop pin | `@dnd-kit/core` center-drag fires POST /pin/ with new start_time |
| Time fence zones | Background shading: red (frozen), amber (slushy), white (liquid) |
| Due date markers | Vertical red lines at WO due dates |
| Priority coloring | Red=urgent, orange=high, blue=normal, gray=low |
| Auto-refresh | Poll GET /gantt/ every 30s, or WebSocket in Phase 9 |

### Kibo UI Components

```
npx kibo-ui add gantt
npx kibo-ui add banner        # "Schedule is stale" alert
npx kibo-ui add spinner       # Solver running indicator
npm install @dnd-kit/core date-fns
```

### Tests

- Component renders with mock Gantt JSON without crashing.
- View switching re-groups tasks on Y-axis.
- Drag fires pin API with correct task_id and new start_time.
- Time fence zones render correct background colors.

### Smoke Test

Navigate to `/scheduling/gantt`. Verify tasks render on timeline. Drag a task bar, confirm pin API fires in network tab.

---

## Phase 6: Dispatch UI

**Goal:** Frontend dispatch board for operators and supervisors.

**Customer-facing:** YES. Operators see their daily work queue.

**Dependencies:** Phase 4.

**Requires migration:** No.

### Files to Create

| Action | File | What |
|---|---|---|
| Create | `ambac-tracker-ui/src/pages/scheduling/DispatchPage.tsx` | Supervisor dispatch board (Kanban) |
| Create | `ambac-tracker-ui/src/pages/scheduling/OperatorQueuePage.tsx` | Individual operator work queue (List) |
| Create | `ambac-tracker-ui/src/hooks/useDispatchList.ts` | GET /scheduling/dispatch/{wc}/ hook |
| Modify | `ambac-tracker-ui/src/router.tsx` | Add /scheduling/dispatch + /operator/queue routes |

**Estimated files:** 3 create, 1 modify.

### Kibo UI Components

```
npx kibo-ui add kanban         # Supervisor dispatch board (columns = work centers, cards = tasks)
npx kibo-ui add list           # Operator personal queue (tasks by status, ranked by priority)
npx kibo-ui add relative-time  # "Started 23 min ago" on task cards
```

### Features

| Feature | Component | Implementation |
|---|---|---|
| Supervisor dispatch board | Kanban | Columns = work centers, cards = tasks for the day |
| Operator personal queue | List | "What do I run next?" grouped by status, priority-ranked |
| Shift assignment whiteboard | Kanban header | Operator name per column header |
| Unassigned task warnings | Kanban + Banner | Red cards for unassigned, banner if any exist |
| Operator workload summary | List footer | Hours assigned today |

### Tests

- Component renders dispatch data grouped by work center.
- Unassigned tasks show warning badge.
- Day filter switches between dates.

### Smoke Test

Navigate to `/scheduling/dispatch`. Verify work centers listed with tasks. Click a date, confirm tasks update.

---

## Phase 7: Component Allocator

**Goal:** CP-SAT reman component allocation solver.

**Customer-facing:** YES. Reman shops get allocation recommendations.

**Dependencies:** Phase 0 (for OptimizationConfig), Phase 2 (for schedule coupling in disposition).

**Requires migration:** Yes.

### Files to Create / Modify

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/allocator.py` | CP-SAT allocator solver |
| Modify | `Tracker/models/scheduling.py` | Add ComponentCost, ComponentSelectionLog, ComponentFlag, AllocationResult, ComponentDecision |
| Modify | `Tracker/viewsets/scheduling.py` | Add allocator endpoints |
| Modify | `Tracker/serializers/scheduling.py` | Add allocator serializers |

**Estimated files:** 1 create, 3 modify. Plus 1 migration.

### Kibo UI Components

```
npx kibo-ui add tags           # ComponentFlag display on part cards (CORROSION, CLEAN_UNIT chips)
```

### Allocator Models

| Model | Key Fields |
|---|---|
| `ComponentCost` | `component_type` (FK→PartTypes), `source` (NEW/HARVESTED_A/B/C), `unit_cost`, `lead_time_days` |
| `ComponentSelectionLog` | `work_order`, `selected_component`, `solver_recommendation`, `override_reason`, `passed_quality` |
| `ComponentFlag` | `component` (FK→Parts), `flag` (DISCOLORATION/CORROSION/etc), `flagged_by` |
| `AllocationResult` | `tenant`, `solver_status`, `solve_time_ms`, `is_stale`, `created_at` |
| `ComponentDecision` | `allocation` (FK→AllocationResult), `work_order`, `component_type`, `selected_component`, `use_new`, `score`, `reasoning` |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/allocator/allocate/` | Run allocation solver |
| GET | `/api/allocator/recommendations/{wo}/` | Ranked options for a WO |
| POST | `/api/allocator/override/{decision}/` | Override with reason |
| GET | `/api/allocator/disposition/{part_id}/` | Disposition recommendation (coupled to scheduler) |

### Tests

| Test | What It Verifies |
|---|---|
| Grade A allocated to urgent WO | When only 1 Grade A exists and urgent WO needs it |
| Override logging | Override saves reason, original recommendation preserved |
| Disposition includes schedule impact | Rework option shows delay to other WOs |
| FIFO preference | Older inventory preferred over newer (soft) |
| Playground scenarios | Port component decision scenarios, verify same output |

### Smoke Test

```
curl -X POST http://localhost:8000/api/allocator/allocate/ -H "Authorization: Token ..."
curl http://localhost:8000/api/allocator/recommendations/42/ -H "Authorization: Token ..."
```

---

## Phase 8: Scenario Planner

**Goal:** What-if analysis using both solvers.

**Customer-facing:** YES. Planners test "what if?" before committing.

**Dependencies:** Phase 2, Phase 7.

**Requires migration:** Yes.

### Kibo UI Components

```
npx kibo-ui add dialog-stack   # Multi-step scenario wizard (pick template → configure → review → solve)
```

### Files to Create / Modify

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/scenarios.py` | Clone, modify, solve, compare logic |
| Modify | `Tracker/models/scheduling.py` | Add Scenario, ScenarioComparison |
| Modify | `Tracker/viewsets/scheduling.py` | Add scenario endpoints |
| Modify | `Tracker/serializers/scheduling.py` | Add scenario serializers |

**Estimated files:** 1 create, 3 modify. Plus 1 migration.

### Scenario Models

| Model | Key Fields |
|---|---|
| `Scenario` | `name`, `tenant`, `base_schedule` (FK→ScheduleResult), `modifications` (JSONField), `schedule_result` (FK→ScheduleResult, null), `allocation_result` (FK→AllocationResult, null), `status` (draft/solving/solved/promoted) |
| `ScenarioComparison` | `scenario_a` (FK), `scenario_b` (FK), `comparison_data` (JSONField: makespan delta, lateness delta, cost delta) |

### Scenario Templates

| Template | Modifications JSON |
|---|---|
| Rush order | `{"add_work_order": {"priority": "URGENT", "due_date": "+3d", ...}}` |
| Machine down | `{"disable_equipment": [machine_id], "duration_days": N}` |
| Operator out | `{"remove_operator": [user_id], "duration_days": N}` |
| Add capacity | `{"add_equipment": {"work_center": wc_id, "count": N}}` |

### API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/scenarios/create/` | Create scenario from template or custom |
| POST | `/api/scenarios/{id}/solve/` | Solve (runs scheduler + optionally allocator) |
| GET | `/api/scenarios/{id}/` | Get scenario with results |
| POST | `/api/scenarios/compare/` | Compare two scenarios |
| POST | `/api/scenarios/{id}/promote/` | Promote scenario to live schedule |

### Tests

| Test | What It Verifies |
|---|---|
| Rush order scenario | Makespan increases, urgent WO on time, some others slip |
| Machine down scenario | Tasks reassigned to remaining machines, lateness increases |
| Promote scenario | ScheduleResult.is_active updated, old result deactivated |
| Compare | Delta shows correct makespan/lateness/cost differences |

### Smoke Test

```
curl -X POST http://localhost:8000/api/scenarios/create/ \
  -d '{"name": "Rush order test", "template": "rush_order", "params": {...}}'
curl -X POST http://localhost:8000/api/scenarios/1/solve/
curl http://localhost:8000/api/scenarios/1/
```

---

## Phase 9: Capacity Planning + Refinement

**Goal:** Capacity analysis, data readiness, solution streaming, polish.

**Customer-facing:** YES. Full scheduling suite complete.

**Dependencies:** All previous phases.

**Requires migration:** No.

### Kibo UI Components

```
npx kibo-ui add tree           # WO hierarchy / BOM tree / genealogy viewer
npx kibo-ui add calendar       # Shift/maintenance/holiday calendar editor
```

### Files to Create / Modify

| Action | File | What |
|---|---|---|
| Create | `Tracker/services/scheduling/capacity.py` | Bottleneck ID, utilization projections, what-if |
| Create | `Tracker/tests/test_scheduling_capacity.py` | Capacity analysis tests |
| Create | `ambac-tracker-ui/src/pages/scheduling/CapacityPage.tsx` | Capacity dashboard |
| Create | `ambac-tracker-ui/src/pages/scheduling/DataReadinessPage.tsx` | Data readiness admin |
| Create | `ambac-tracker-ui/src/pages/scheduling/CalendarPage.tsx` | Shift/maintenance/holiday calendar |
| Modify | `Tracker/viewsets/scheduling.py` | Add capacity + data-readiness endpoints |
| Modify | `Tracker/services/scheduling/solver.py` | Add CpSolverSolutionCallback for streaming |
| Modify | `ambac-tracker-ui/src/router.tsx` | Add capacity + data-readiness routes |

**Estimated files:** 4 create, 3 modify.

### Capacity Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/scheduling/capacity/` | Current bottleneck analysis + utilization by WC |
| POST | `/api/scheduling/capacity/what-if/` | "Add a machine" or "add a shift" impact analysis |
| GET | `/api/scheduling/data-readiness/` | Per-model data sufficiency scores |

### Solution Streaming

`CpSolverSolutionCallback` pushes improving solutions to frontend via WebSocket (Django Channels). Gantt re-renders as solver finds better solutions. Falls back to polling if Channels not configured.

### Data Readiness Report

| Data Point | Threshold | Status |
|---|---|---|
| StepTiming coverage | >80% of steps | Green/Yellow/Red |
| StepExecution per step | 20+ completions | Green/Yellow/Red |
| StepEquipmentAffinity coverage | >90% of steps | Green/Yellow/Red |
| Shift definitions | At least 1 active | Green/Red |
| WorkCenter with equipment | >0 | Green/Red |

### Tests

| Test | What It Verifies |
|---|---|
| Bottleneck identification | Most-utilized work center flagged as bottleneck |
| What-if: add machine | Utilization drops, throughput increases |
| Data readiness | Reports gaps accurately for seeded data |

### Smoke Test

```
curl http://localhost:8000/api/scheduling/capacity/
curl http://localhost:8000/api/scheduling/data-readiness/
```

---

## Phase Summary

| Phase | Description | Customer-Facing | Migration | Depends On | New Files | Modified |
|---|---|---|---|---|---|---|
| **0** | Models + migrations | No | Yes | -- | 3 | 2 |
| **1** | Data layer | No | No | 0 | 1 | 0 |
| **2** | CP-SAT solver (Layer 1) | No | No | 0, 1 | 1 | 1 |
| **3** | Operator dispatch (Layer 2) | No | No | 2 | 1 | 0 |
| **4** | REST API + Celery | **Yes** | No | 2, 3 | 2 | 3 |
| **5** | Gantt UI | **Yes** | No | 4 | 6 | 1 |
| **6** | Dispatch UI | **Yes** | No | 4 | 4 | 1 |
| **7** | Component allocator | **Yes** | Yes | 0, 2 | 1 | 3 |
| **8** | Scenario planner | **Yes** | Yes | 2, 7 | 1 | 3 |
| **9** | Capacity + refinement | **Yes** | No | All | 3 | 3 |
| | **Total** | | | | **~23 new** | **~17 modify** |

### Critical Path

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
                                                  ↘ Phase 6
                          Phase 2 → Phase 7 → Phase 8
                                                       ↘ Phase 9
```

Phases 5 and 6 can be built in parallel. Phase 7 can start after Phase 2 (does not need Phase 3 or 4). Phase 9 is the final convergence point.
