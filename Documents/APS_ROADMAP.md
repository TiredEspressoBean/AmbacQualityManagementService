# APS Build Roadmap

Working plan for taking the UQMES scheduling module to a full, well-integrated APS.
Living doc — check items off as they land. Companion to `VERSIONING_ARCHITECTURE.md`.

## Goal

A complete Advanced Planning & Scheduling capability **as a module of the
MES/QMS/DWI product** (not a standalone APS, not an ERP replacement) for a
50–200-person discrete + reman shop under AS9100 / ITAR. The scheduling *engine*
is already advanced; the remaining work is overwhelmingly about **keeping the
schedule true to reality and getting it to the floor.**

## Scope decisions (what we are NOT building)

- **No inventory / warehouse management.** Stock lives in the ERP the APS reads
  from. The APS's job with materials is to **gate and flag** (net vs on-hand +
  promised receipts, warn on shortage) — not to run a reservation ledger, safety
  stock, reorder points, or kitting/pick lists. The existing soft material gate
  is the right APS-level behavior.
- **No ERP/MRP connectors.** Integration to ERP is out of scope for this product.
- **No multi-plant.** Single site. Multi-line within the plant is already covered
  by the resource model.

Consequences: the material **reservation ledger (was the only XL item)**, safety
stock, time-phased planned orders, and kitting all drop off. Harvested-component
handling (reman) stays, but as a lightweight **expected-yield gate**, not a ledger.

## The baseline is already strong (do NOT rebuild)

Finite-capacity CP-SAT (2-layer machine + operator), forward + due-date-driven
placement, precedence/branch-merge routing, sequence-dependent changeover matrix,
machine/material/tooling/labor constraints, machine selection + affinity,
skills/cert gating (preflight), in-progress hard-pinning, working calendars +
time fences, manual pin/drag + reassign machine/operator, multi-select bulk edits,
WO create/cancel/hold/qty/priority/due edits, lot split/merge, multi-level
pegging, what-if drafts + compare + commit, late-cause attribution. Tenant
isolation + permissions solid.

## Need vs nicety (scoped)

**True needs (7)** — the product is broken or incomplete without these. Almost
all are integration/trust, not scheduling horsepower.

**Should-haves (3)** — operable without, but expected / painful to lack.

**Niceties (8)** — real value, but pure improvement on an already-working schedule.

---

## Build order

Legend — **Need:** N = true need · S = should-have · n = nicety.
**Effort:** S ≈ ½–1d · M ≈ 2–4d · L ≈ 1–2wk. **Status:** ☐ todo · ◐ in progress · ☑ done.
Ordered **needs-first**. Item IDs (#1–#18) are stable across re-orderings. A `⤷`
item is a should-have/nicety *pulled in* because it directly serves the need it
sits under (rides on the same work, or surfaces/validates it). Everything above
Wave F is a need or serves one; Wave F is the pure niceties.

### Wave A — Trust the schedule
- [x] **#1. Quality-hold staleness bug** — N · S · ☑
  Bulk `.update()`/`bulk_update` quarantine in `quality_gate._hold` and
  `batch_disposition.contain_failed_batch` bypass `post_save`, so the schedule
  keeps planning quarantined parts. Fixed: shared helper
  `services/scheduling/staleness.py::mark_active_schedule_stale`, called from both
  QMS paths (and from `_hold`'s material-lot branch); `signals.py` delegates to
  it. Tests in `test_schedule_stale_signals.py` (bypass guard + both paths).
- [x] **#2. Staleness trigger completeness** — N · S–M · ☑
  Added receivers in `signals.py`: unconditional group (Shift, PlantCalendarException,
  StepTiming, StepEquipmentAffinity, WorkCenterChangeover, Fixture — save + delete);
  Equipments gated on capacity fields {status, is_schedulable, runs_unattended,
  calibration_interval_days} + operating_shifts M2M; MaterialLot gated on
  {status, promised_date} + receipt (create), deliberately NOT quantity_remaining
  (avoids churn on routine consumption). 11 tests in `test_schedule_stale_signals.py`.
- [x] **#5. Event-driven / periodic re-solve** — N · M · ☑
  `tick_auto_resolve` beat (every 15 min, celery_app.py) →
  `services/scheduling/auto_resolve.py`: re-solves live for tenants opted into
  `OptimizationConfig.auto_resolve = LIVE`, anti-churn via
  `auto_resolve_min_interval_minutes` (compared to the active schedule's last-solve
  `created_at`). **Default OFF** — nothing on the floor auto-changes without opt-in
  (the one product decision, made a per-tenant config). Migration 0148; fields
  exposed in the serializer + Settings dialog ("Automatic rescheduling"); schema +
  FE types regenerated, typecheck clean. Tests: `test_auto_resolve.py` (6).
  Note: `run_due_auto_resolves(queue=…)` has an injectable seam so tests don't
  patch the Celery task (patching it corrupts eager-result state for the run).

### Wave B — Close the loop with reality
- [x] **#6. Actuals → schedule** — N · L · ☑ **(capture-only, per decision)**
  `ScheduledTask.actual_start/actual_end` (migration 0149) stamped from the
  StepExecution entry/exit via a signal → `services/scheduling/actuals.py`
  (bulk update — no stale, no re-solve trigger; the solver already pins in-progress
  ops). Serializer + FE types regenerated; detail dialog shows an "Actual" row with
  a late/early-vs-plan delta. Tests: `test_actuals.py` (5).
  Decision (2026-08-25): capture-only — do NOT feed the loop / mark stale on step
  advance (preserves the deliberate no-churn-on-advance design). Escalating to
  loop-feeding later would be a separate, explicit change.
- [x] ⤷ **#11. Scrap → make-up re-plan** — S · M–L · ☑
  Decision (2026-08-26): **planner-confirmed**, parts flagged as replacements.
  `WorkOrder.target_good_quantity` (the ordered good count; set at plan time) +
  `Parts.is_makeup` (migration 0153). `services/mes/makeup.py`: shortfall =
  max(0, target − alive), `create_makeup_parts` spawns `-MU####` PENDING parts at the
  first step, flags them `is_makeup`, marks the schedule stale (re-solve picks them up).
  Actions `WorkOrders/{id}/makeup_status` (GET) + `create_makeup` (POST). UI: make-up
  section in EditWorkOrderDialog ("N short of M good — Create N make-up parts") + a
  ⟳ marker + legend on the Gantt (`ScheduledTask.is_makeup`). Tests: `test_makeup.py`
  (6). Iterative rule — a replacement that later scraps is covered by the next top-up.
- [~] ⤷ **#17. Planned-vs-actual variance** — n · M · ◐ **(per-task slice shipped)**
  Per-task variance (late/early vs plan) now shows in the Gantt detail dialog
  (rode in free on #6). Remaining: aggregate adherence (overlaps #18 dashboard).

### Wave C — Get it to the floor
- [x] **#8. Dispatch list / operator sequence + DWI linkage** — N · L · ☑ **(schedule-ordering shipped; Instructions preview deferred by design)**
  The operator home (`OperatorHomePage`) already had UP NEXT / THEN — but it
  ranked by a standalone priority→due→aging heuristic, ignoring the APS plan.
  Shipped: `WorkQueueViewSet` now re-ranks by the live schedule's planned start
  (`_scheduled_starts()`): scheduled rows lead in planned order, unscheduled fall
  back to the heuristic, blocked still sink last; `scheduled_start` exposed on the
  row + shown as "planned HH:MM" on the hero/Then tiles. Already work-center
  scoped (step.work_center + operator memberships). Tests:
  `test_work_queue_schedule_order.py` (3). Decision (2026-08-25): schedule-ordered
  flavor (station-pull in plan order), not assignment-driven ("your work today").
  Instructions button → DWI is intentionally a **preview** (deferred by design,
  2026-08-25) — NOT a #8 gap. So #8 as scoped (schedule-ordered queue) is complete.
  **Later refinements** (optional, not gaps):
    - [x] **Machine-level scoping** (2026-08-26) — the work queue now carries the machine the
      live schedule assigned each (WO, step) cohort to: `WorkQueueViewSet._scheduled_meta`
      surfaces `machine` + `machine_name` on every row, the operator-home tiles show it
      ("… · on CNC-03"), and `?machine=`/`?machine__in=` scopes the queue to a station
      (station pull; unscheduled rows drop out). Tests +2 in `test_work_queue_schedule_order`.
      Populates once a schedule is committed (needs a solve). Serializer + schema/FE regen.
    - Assignment-driven queue ("your work today") as an alternative flavor.
  **Env note**: adding `scheduled_start` to the serializer + regenerating the zod
  client requires the Django dev server to reload so it sends the field; a stale
  server makes the zod client reject `/api/WorkQueue/` (browser-only empty queue).
  Restart the API server after this change.
- [ ] ⤷ **#7. Scheduler notifications** — S · M · ☐
  Pulled in: surfaces what the loop (#5/#6) detects — late / material-short /
  uncovered — so planners manage by exception instead of watching the Gantt.

### Wave D — Capacity authoring (independent; can pull forward for a quick visible win)
- [x] **#4. Scheduling calendar (closures + labor blocks)** — N · M · ☑ **(expanded)**
  Grew from "plant closures" into a full labor calendar (2026-08-26):
  - `PlantCalendarException` CRUD (dated plant closures — block machines + operators).
  - **New `LaborCalendarBlock`** model (migration 0150): operator non-working time —
    PTO / sick / training / meeting / break — **one-off (ONCE) or weekly (WEEKLY)**,
    **company-wide (user null) or per person**. Operators only (machines keep running).
  - Engine tie-in: `data.get_labor_calendar_blocks` + `get_operator_shift_windows`
    subtracts company + per-user blocks (ONCE dated; WEEKLY expanded via the shift
    expander) → absent operators drop from Layer-1 pooled headcount and Layer-2
    dispatch. Blocks mark the schedule stale (capacity-master signal group).
  - CRUD viewsets (`PlantCalendarExceptions`, `LaborCalendarBlocks`) + serializers
    with recurrence validation; schema + FE types regenerated.
  - **kibo-ui calendar** vendored (extended with additive `onDayClick`/`selectedDates`
    for single + multi-day selection) at `/production/calendar`: month grid of one-off
    items, click day(s) → Add closure / absence / meeting, weekly recurrence editor,
    side lists to manage/delete. Live + endpoints verified (200).
  - Tests: `test_labor_calendar.py` (16). Everything uncommitted.

  **Calendar follow-ons (from the MES-calendar review, 2026-08-26):**
  - [x] **Overtime / additive capacity** — N — ☑ new `OvertimeWindow` model (migration
    0152). **References a Shift** (its hours + crew), ONCE (date range) or WEEKLY
    (weekdays) — answers "what kind of shift." Solver ADDS it to **that shift's
    operators** (`get_operator_shift_windows`, per-shift) AND to attended-machine
    availability (`get_overtime_machine_windows`, union in the solver's `_window_gaps`);
    lights-out machines already 24/7; **plant closures win**. CRUD + serializer +
    `/production/calendar` UI ("Add overtime" → pick a shift). Enum-name collision on
    `recurrence` fixed via `ENUM_NAME_OVERRIDES`. (Also fixed a latent one-off-range bug:
    the ONCE payload was spreading `start`/`end` instead of `start_time`/`end_time`.)
  - [x] **Yearly-repeating holidays** — S — ☑ `PlantCalendarException.recurrence`
    ONCE/YEARLY (migration 0151); engine expands yearly occurrences; UI "repeats every
    year" + grid shows recurring holidays on the viewed year.
  - Deferred by decision (2026-08-26): **calibration/PM auto-block** (calibration-as-
    window already exists in `get_machine_availability`; PM-recurring not built) ·
    **time-off request/approval** (lives in HRIS — managers handle it; direct entry
    stays) · **work-center/cell calendar tier**, **rotating-crew shift patterns**,
    **reduced-capacity days / conflict-detection / ICS** (out of scope for this UI).
- [~] ⤷ **#3. Per-machine operating-shifts UI** — S (conditional) · **DROPPED** (2026-08-26)
  User confirmed machines won't run on different schedules — not needed.

### Wave E — Reman correctness
- [~] **#15. Harvested-yield gate (reman)** — N · **DROPPED** (2026-08-26)
  User decision: not worrying about reman harvested-yield gating.

### Wave G — First-push finishers (operator scoping & hours, 2026-08-26)
- [x] **Shop-floor operator gate** — the scheduler now treats only users in the
  `Operator` / `Shift Lead` `TenantGroup`s as dispatchable operators
  (`data.SHOP_FLOOR_GROUPS` + `_shop_floor_user_ids`, gating `get_dispatchable_operators`
  + `get_operator_shift_windows`), so admins/office staff aren't scheduled. Falls back
  to internal+shift when no one is grouped yet. No new model — reuses the existing
  UserRole→TenantGroup permission structure.
- [x] **Operator hours report** — `services/mes/labor_report.py::operator_hours` sums
  `TimeEntry` per operator (on-shift attendance vs direct/job hours, breaks excluded),
  scoped to shop-floor operators. `Schedules/operator_hours` GET action +
  `/production/labor-hours` page (date range + table). Tests: `test_operator_scoping.py` (5).

### Wave H — Purchased-material split + lead time / sourcing (2026-08-26, in progress)
Decision: `PartTypes` is **in-house SKUs only**; purchased components (O-rings, seals) are
their own thing. No data migration (dev reseeds).
- [x] **`Material` model** (migration 0154) — purchased item master (name, part_number,
  UoM, `purchase_lead_time_days`, preferred_supplier). `BOMLine` now dual-refs:
  `component_type` (PartType, MAKE) **or** `material` (Material, BUY), exactly-one DB
  constraint. `MaterialLot.material_type` retargeted PartTypes→Material. Material gate +
  BOM explosion updated (MAKE on-hand nets finished Parts IN_STOCK, not lots). `Material`
  CRUD API. Tests updated + constraint test. Schema/FE/typecheck green.
- [x] **Seeds (Material touchpoints)** — demo seed converted: showcase BOM (2 assemblies
  MAKE/PartType, 3 purchased BUY/Material), receiving + supplier-quality lots receive a
  `Material`. Receiving-inspection service guarded: purchased Materials dock-to-stock
  (RIPs are PartTypes-keyed; RIP-for-Material is a follow-on). Only the *demo* seed
  creates these; reman uses `DisassemblyBOMLine` (PartTypes, untouched).
  ⚠️ `seed_demo` also hits a **pre-existing** duplicate-versioned-`Shift` error on a dirty
  DB (from partial re-runs) — needs a clean reseed (flush) to verify end-to-end.
- [x] **Lead time + sourcing/production report** — `Fixture.lead_time_days` + `Material.
  purchase_lead_time_days`; `services/mes/requirements.py` (source / produce / tooling
  lanes, order-by = need-by − lead time; need-by = scheduled consuming-step start, WO-start
  fallback) + `Schedules/operator_hours`-style `Schedules/requirements` GET action. Tests:
  `test_requirements.py` (3). **Report UI page still to build.**
- [x] **UI** — shipped this pass:
  - **Materials editor** — `/editor/materials` (list) + create/edit form (name, part #, UoM,
    lead time, preferred supplier, active); card in the Data-Management hub. Hooks in
    `useMaterials.ts`.
  - **Sourcing & production requirements report** — `/production/requirements` (source / produce
    / tooling lanes, order-by dates, past-due "order now" flag). `useRequirements` hook.
  - **Receiving** — the batch receive form (`ReceiveLotsBatchPage`) now lists **Materials**
    (was PartTypes) for `material_type`; the Materials lot table already displays
    `material_type_name`. RIP / part-approval / supplier-qualification forms stay PartType-keyed
    by design (those qualify in-house SKUs; RIP-for-Material is a documented follow-on).
  - **BOM display** — the (read-only) BOM panel on the Part Type form now renders BUY (Material)
    vs MAKE (PartType) lines with a Make/Buy source badge (BUY lines used to show "—").
  - **Tooling** — the fixture form now edits `lead_time_days` (feeds the requirements tooling
    lane); added to `FixtureSerializer` + schema/FE regen.
  - **Nav** — new collapsible **Scheduling** sidebar group (Gantt / Calendar / Labor Hours /
    Requirements) — these pages were previously URL-only.
  - **BOM authoring (inline)** — the Part Type form's BOM panel is now editable: create a DRAFT
    BOM when none exists; add / edit / remove lines via a dialog with a **Make (Part Type) / Buy
    (Material)** source toggle + component picker (exactly-one enforced client- and server-side);
    **Release** (DRAFT→RELEASED) and **New revision** (RELEASED→fresh DRAFT copy). Released BOMs
    stay read-only. Hooks in `useBom.ts`; dialog in `components/bom/BomLineDialog.tsx`. Verified
    end-to-end through the serializers (BOM + BUY/MAKE lines + exactly-one guard).
  - **Component→operation allocation** — each BOM line has a **"Consumed at step"** picker (the
    assembly's own process steps) = the standard ERP component-allocation model (`BOMLine.
    consumed_at_step`). The BOM header stays on the Part Type (the assembly recipe); the line
    pegs to the op that consumes it. Serializer gained `consumed_at_step_name`; shown as a column
    and edited in the line dialog. This is what the scheduler already reads to gate only that op
    on the component WO, and what the sourcing report reads for need-by. Verified via serializer
    round-trip.
  - **Polish** — `BOMLine.save()` auto-sequences `line_number` (gap-numbered 10/20/30…) for new
    lines that don't specify one (explicit values preserved); `MaterialViewSet` gained
    `ListMetadataMixin` so the Materials editor renders search/filter metadata like the others.
  - **Per-WO material requirements ("picklist-lite")** — a **Materials** tab on the work-order
    detail page: top-level BOM components × WO qty, bucketed by consumed-at-step, flagged
    On hand / Building / Short vs on-hand + promised, **with an order-by date** (need-by − lead
    time, past-due "now" flag) on short purchased lines — so purchasing/material-handlers see
    what a job needs and when to order it. NOT a WMS pick list (no bins / lot picking /
    reservations — that's the ERP's job; decided with the user). `work_order_material_
    requirements` + `WorkOrders/{id}/material_requirements`; `WorkOrderMaterialsPanel`. Tests +2.
  - **Bug fix — open draft revision no longer hides the live BOM.** `create_new_bom_version`
    (the "New revision" button) flips the RELEASED row to `is_current_version=False`, but
    `bom_explosion._released_bom`, the scheduler's material gate (`data.py`), and the sourcing
    report all resolved the BOM as `RELEASED AND is_current_version=True` — so drafting the next
    rev silently erased the in-force production BOM from MRP, the solver's material gate, and the
    sourcing report. All four sites now take the **latest RELEASED** (order by `-version`,
    no is_current_version gate) — the effective-vs-head distinction standard change control
    requires (AS9100 8.5.6: Rev A stays in force until Rev B is released). Regression tests in
    `test_bom_explosion` + `test_requirements`.
  - **Material-split report ripple fix** — `bom_report` + `pick_list` PDF adapters dereferenced
    `line.component_type.ERP_id` on every line → crashed on BUY lines (`component_type` is null;
    the component is `material`). Both now read from whichever the line carries.

### Wave I — Aerospace/reman scheduler gaps (from two fresh-eyes reviews, 2026-08-27)
Independent domain reviews (needs-review + gap-from-inventory) converged: the engine is
strong, but the real remaining *needs* are aerospace special-process + reman realities that
the scheduler didn't model. (Perturbation/nervousness was flagged but is already covered by
the frozen/slushy/liquid fences + warm-start — verified, not a gap.)
- [x] **G1. Outside processing as a scheduled elapsed operation** — N · M · ☑ (2026-08-27)
  The MES already models OSP fully (Flow B: `Steps.is_outside_process`, `OutsideProcessShipment`,
  `services/mes/outside_process.py`), but the **scheduler ignored it**. Now: `Steps.outside_
  process_lead_days` (+ `Companies.default_outside_process_turnaround_days` + `OptimizationConfig.
  default_outside_process_turnaround_days` — 3-level fallback) drive an **elapsed, no-machine,
  no-crew, 24/7 calendar interval** (`data.get_outside_process_data` → solver op branch) that
  gates downstream via precedence. Parts already at the vendor (open SENT shipment) pin to
  expected return (`shipped_at + turnaround`). Migration 0156; serializers (Steps, Companies,
  OptimizationConfig) + step-editor turnaround field; schema/FE regen. Test in
  `test_scheduling_solver` (elapsed + no machine + gates downstream). 71-test sweep green.
- [x] **G2. Batch/process resources (furnace, tank, wash line)** — N · ☑ (concurrent + within-WO cycle)
  - [x] **Phase 1 — concurrent capacity** (2026-08-27): `Equipments.batch_capacity` (migration
    0157); solver uses `AddCumulative(capacity)` instead of `AddNoOverlap` for capacity>1
    machines (downtime/closure gaps demand full capacity so they still block), and skips
    pairwise changeover on batch resources. Serializer + schema/FE regen. Test: cap=3 → 3 loads
    co-run. **Models "up to N concurrent jobs" (parallel stations / a bank of tanks).**
  - [x] **Phase 2 — furnace batch cycles (within-WO, Option A)** (2026-08-27): `Equipments.
    batch_mode` CONCURRENT|CYCLE (migration 0158). CYCLE = a furnace/oven: one load at a time
    (no-overlap), fixed cycle time per load — a job of N parts takes `ceil(N/capacity)` loads
    (`_batch_cycle_dur` = setup + cycle × ceil(count/cap)), NOT per-part time and NOT one
    impossible over-capacity load. Serializer + equipment-editor fields (capacity + mode);
    schema/FE regen. Test: 10 parts / cap 4 → 3×120-min loads = 360.
    **Decided (2026-08-27, after real-world frequency analysis):** within-WO only. Cross-WO
    co-firing (packing parts from *different* WOs into one load) + min-load enforcement is
    deferred — for this shop the big furnaces are outsourced (G1/OSP) and reman is qty-light,
    so simultaneous same-recipe jobs on a fill-limited in-house oven are rare. Revisit only if
    a specific in-house batch resource proves to be a fill-limited bottleneck.
- [~] **G3. Reman disposition-driven routing + recovery yield** — **RESOLVED as adequate**
  (2026-08-27). Decision: **plan the nominal (happy) path, re-plan on disposition** — the
  standard reman model, and already what the system does: the solver plans each core from its
  current step along the DEFAULT route; ALTERNATE/rework edges + re-entry exist; staleness +
  re-solve pick up the actual route once grading dispositions the core (reuse/rework/scrap→
  make-up). The only thing NOT built is **probabilistic yield reservation** (pre-holding
  capacity for the expected rework %), an advanced capacity/promising-accuracy refinement —
  deferred; revisit only if a specific reman bottleneck proves it out. Not a need.
- [x] **G4. Max-time-between-ops / cure windows** — N (AS9100 process control) · ☑ (2026-08-27)
  `StepEdge.max_minutes` = max elapsed from_step-end → to_step-start (cure/coat/pot-life/
  passivation dwell). Solver adds a **soft upper bound** `start_to ≤ end_from + max` alongside
  the precedence lower bound — met when capacity allows, else the op is flagged
  (`ScheduledTask.cure_window_violation`, `_CURE_WINDOW_WEIGHT` penalty) rather than a hard
  INFEASIBLE. Migration 0159; StepEdge + ScheduledTask serializers; schema/FE regen. Tests:
  window met → not flagged; in-progress clean + coater downtime → forced violation → flagged.
  Follow-on: a visual flow-editor edge field for max_minutes (currently API-settable, same
  status as the pre-existing `tech_continuity` edge prop); a Gantt marker for the violation flag.
- [ ] **Compliance should-haves:** FAI/first-article release gate, time-windowed cert/cal
  eligibility, ITAR person-eligibility dispatch gate, machine PM / gage-cal downtime as
  capacity holes, DPAS priority ratings.

### Wave J — Three trust/usability adds (2026-08-27)
Answering "can we know the schedule is optimal / do buyers know when to order / does
clocking + payroll reporting work." All three shipped.
- [x] **Optimality gap %** — `ScheduleResult.relative_gap` (solver best-bound vs objective;
  migration 0160). Gantt status badge now shows "OPTIMAL · proven best" or "FEASIBLE ·
  within X%". Tells the planner how close to optimal the schedule is proven to be.
- [x] **Operator-Hours screen — polished + PDF + CSV** — `/production/labor-hours` reworked
  as a first-class screen (header, stat cards, totals). PDF via new `labor_hours` report
  adapter + Typst template (reuses `operator_hours`); CSV export (`lib/csv.ts`). Payroll gets
  a signed-record PDF and an importable spreadsheet. Fixture + template-compile tests.
- [x] **Requirements screen — polished + PDF + CSV** — `/production/requirements` reworked;
  PDF via new `requirements` report adapter + Typst template (reuses `sourcing_requirements`,
  3 lanes, past-due flag); CSV export. Purchasing's buy-list to work from. Fixture + tests.
  (Concluded: buyers being "informed" = they work the report/buy-list — the standard MRP
  mechanism; a push-notification is only exception-alerting, not required. Real dependency is
  data hygiene: lead times set + schedule re-solved.)

### Wave F — Pure niceties (no need depends on these; sequence by value later)
- [ ] **#14. Alternate routings / rework re-entry** — n (rework half → S) · L · ☐
- [ ] **#16. CTP/ATP capacity promising** — n · M · ☐  Schedule-derived promise date; reuses draft engine.
- [ ] **#9. Cost objective** — n · S–M · ☐  Wire existing overtime/shop-rate into the objective.
- [ ] **#10. Order release gate / firm-planned** — n · M · ☐
- [ ] **#12. Campaign batching** — n · M · ☐
- [ ] **#13. Capacity leveling / bottleneck (DBR)** — n · L · ☐  Guard vs lateness regressions.
- [ ] **#18. KPI dashboard** — n · M–L · ☐  OTD, adherence, utilization, WIP (extends #17).

### Deferred (ADVANCED, not for this shop)
Transfer batching / lot streaming · tool-life tracking · inter-op max-wait ·
co-products · schedule version rollback · learned cycle-time standards ·
multi-plant (N/A).

---

## Dependencies

- **#5 (re-solve loop)** makes #1 & #2 actually matter — without it `is_stale`
  just lights up and nobody acts. First unchecked item for that reason.
- **#6 (actuals)** unlocks **#11** and **#17** — both ride on it.
- **#8 (dispatch to floor)** is only worth it on a trustworthy schedule → after #5.
- **#18 (dashboard)** extends **#17** (variance).
- Independent (no hard deps, pull forward anytime): **#4, #3** (Wave D), plus the
  Wave F niceties #9, #10, #12, #13.

## Verification checklist (per item)

- Backend: `cd PartsTracker && python manage.py test <suite> --keepdb`; full
  `--parallel 4 --noinput` sweep before a checkpoint (scheduling parallel flakes
  are known — re-run serially to confirm).
- `makemigrations --check` clean; new migrations committed with their change.
- serializers/viewsets touched → `spectacular --file schema.yaml --fail-on-warn`
  + `bun run generate-api` + `bun run typecheck`.
- Tenant lint (`test_tenant_scoping_lint`) green — new `.objects` need
  `tenant=` / FK-scope / `# tenant-safe:`; cross-tenant reads use
  `.unscoped` / `.all_tenants` with a documented reason.
- Solver/model change → restart the Celery worker (no hot-reload) before FE test.
- Nothing committed without an explicit ask.
