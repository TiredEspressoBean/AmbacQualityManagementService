# Reman ↔ DWI Integration

> **Status (2026-07-13): implemented.** Teardown substep captures create
> `HarvestedComponent` rows via
> `Tracker/services/dwi/harvested_component_capture.py`; see also
> `services/reman/{teardown,harvested_component,core}.py`. Companion design:
> `DIGITAL_WORK_INSTRUCTIONS_DESIGN.md` (also implemented).

## Overview

Companion to `DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`. Captures the reman-specific design surface that surfaces when integrating Digital Work Instructions with the existing Core / HarvestedComponent / DisassemblyBOMLine models in `Tracker/models/reman.py`.

**Scope:** Make DWI substep capture work for reman teardown workflows. Specifically:
- Cores flow through teardown Steps the way Parts flow through manufacturing Steps
- Substep captures during teardown attribute to specific Cores
- `HarvestedComponent` rows are created from substep captures with full audit trail
- Single-Op and multi-Op teardown procedures both supported
- Core ↔ WorkOrder lifecycle stays coordinated through Step entry / completion

**Out of scope (handled elsewhere):**
- Core receipt UX (`CoreReceiveFormPage` — exists)
- Accept-component-to-inventory flow (`accept_to_inventory` service — exists; downstream from teardown)
- Customer-credit issuance (separate financial flow)
- The DWI editor + custom node library mechanics (covered in main DWI doc)

---

## Industry Context

The 2016 international remanufacturing definition (APRA / MERA / RIC / CLEPA / FIRM / ANRAP / CPRA, ratified Frankfurt):

> "A core is a previously sold, worn or non-functional product or part, intended for the remanufacturing process."

Cores are explicitly **not** material, **not** scrap, **not** a part — they are a named class of thing with their own accounting treatment (IRS Rev. Proc. 2003-20 — Core Alternative Valuation safe harbor), separate ledger account per GAAP best practice (RSM / ProCount West), and a distinct lifecycle. The current `Core` model reflects this consensus correctly.

**No major ERP/MES treats cores as first-class.** SAP overlays them on Returnable Packaging Management; Plex / Oracle / Epicor / NetSuite treat them as inventory variants. The trade press (Trucking Info, Heavy Duty Parts Report) documents this as a persistent industry pain point — "valuation of cores and the accounting for core liability are the areas of greatest contention," with documented cases of failed M&A and financial restatements caused by core mis-modeling.

UQMES's pre-existing first-class `Core` model is an architectural advantage; this integration extends that advantage to DWI without compromising it.

**Sub-vertical terminology to watch:**
- **Industrial electric motor reman** (EASA AR100): "core" means the iron laminations (a sub-component), not the returned unit. The returned unit is just "the motor for repair/rewind." Naming collision; do not target this vertical without a vocabulary review.
- **Aerospace MRO** (AS9110, FAA Part 145): vocabulary shifts to "rotable," "serviceable / unserviceable," "USM" (Used Serviceable Material). "Core" rare. Different regulatory regime; out of v1 scope.
- **Medical refurb** (FDA): "refurbished" or "reprocessed"; tracked per UDI/serial under FDA. Out of v1 scope.

v1 target verticals: auto reman, diesel engine reman, hydraulic reman, small/mid industrial reman where "core" is the operative term.

---

## Current State

`Tracker/models/reman.py`:

- `Core` — first-class model with `core_number`, `serial_number`, `core_type` FK to `PartTypes`, `customer` FK, `source_type`, `condition_grade`, `status` (RECEIVED → IN_DISASSEMBLY → DISASSEMBLED → SCRAPPED), `core_credit_value`, optional `work_order` FK.
- `HarvestedComponent` — FK to `Core`, FK to `component_type`, condition fields, scrap fields, optional `component_part` OneToOne FK to `Parts` (set on accept-to-inventory).
- `DisassemblyBOMLine` — versioned "reverse BOM" per (core_type, component_type) with `expected_qty` and `expected_fallout_rate`.

`Tracker/services/reman/`:
- `core.py` — `start_core_disassembly`, `complete_core_disassembly`, `scrap_core`, `issue_core_credit`
- `harvested_component.py` — `scrap_component`, `accept_component_to_inventory`

**Current canonical operator workflow** (from `test_reman.py` + `seed/reman.py`):

1. Core arrives → `CoreReceiveFormPage` creates a Core row (no WO).
2. Operator calls `Core.start_disassembly()` directly — no WorkOrder, no StepExecution, no DWI substeps.
3. Operator manually creates `HarvestedComponent` rows via existing reman UI (not DWI).
4. Operator calls `Core.complete_disassembly()` when done.
5. Accepted components become `Parts` rows via `accept_to_inventory`; those Parts then enter their own production WOs separately.

**Gaps blocking DWI substep flow for teardown:**

1. **`StepExecution.part` requires a Parts row.** Cores aren't Parts; current `StepExecution` model can't reference them. → blocks substep capture machinery for cores.
2. **No auto-coordination between Core lifecycle and linked WorkOrder.** `Core.work_order` is manually set; starting the WO doesn't auto-call `start_core_disassembly`. Operators must keep two state machines in sync by hand.
3. **`WorkOrderSerializer` doesn't accept Cores.** The serializer takes `parts: [...]` but no `cores: [...]`; teardown WO creation needs the serializer extended to validate Process eligibility (`is_disassembly=True` + matching core_type) and link Cores via `core.work_order = wo`. (No dedicated `start_teardown` service is needed — see R6.)
4. **Cores don't flow through multiple Steps.** Multi-Op teardown procedures (engine rebuild, transmission overhaul) need Cores to have a `step` field and an `advance_core_step` service mirroring `advance_part_step`.

The rest of this doc specifies how to close each gap.

---

## Architectural Decisions

### Decision R1 — Storage philosophy: per-unit rows always

Per the system-wide philosophy ("storage is cheap; per-unit clarity is the priority"), batch teardown (5–10 cores at one workstation) is modeled as **N independent per-Core flows**, not as a shared execution event. Each Core gets its own `StepExecution` row, its own substep capture rows, its own `HarvestedComponent` rows.

This avoids the "decompose execution from subject" refactor that would otherwise be needed for shared-resource Ops. The UX presents as batch (operator works through 5 cores at one bench in sequence); the data is fully per-unit.

### Decision R2 — `StepExecution` extension: two nullable FKs

Add a nullable `core` FK to `StepExecution` alongside the existing `part` FK. CheckConstraint enforces exactly one is set.

```python
class StepExecution(SecureModel):
    # Was: part = ForeignKey('Parts', on_delete=CASCADE, related_name='step_executions')
    part = ForeignKey('Parts', on_delete=CASCADE, related_name='step_executions',
                      null=True, blank=True)
    core = ForeignKey('Core', on_delete=CASCADE, related_name='step_executions',
                      null=True, blank=True)
    # ... existing fields ...

    class Meta:
        constraints = [
            CheckConstraint(
                check=(
                    Q(part__isnull=False, core__isnull=True) |
                    Q(part__isnull=True,  core__isnull=False)
                ),
                name='step_execution_one_subject',
            ),
        ]
```

**Rationale:** matches the codebase's established pattern (decision #9 in the main DWI doc — `ProcessChangeRequest` uses three nullable FKs with a CheckConstraint for the same reason). Explicit, easy joins, no GFK pain. Scales cleanly up to ~4–5 subject types; if a third subject type (e.g., `MaterialLot` consumption-style execution) ever surfaces, add a third nullable FK.

**Read sites needing update:** every existing `step_execution.part` access needs null-handling. Identified in `services/mes/parts.py`, the workflow engine code paths, sampling logic, FPI tracking, operator queues, dispatch. Estimated ~2–3 days of careful refactor + test coverage.

### Decision R3 — Mirror-pattern principle for Core flow

Where the existing model has Parts-specific plumbing that conceptually applies to Cores too, mirror the pattern rather than abstract. Specifically:

- `Core.step` field — direct mirror of `Parts.step` (FK to Steps, nullable)
- `advance_core_step(core, operator, decision_result=None)` service — copy of `advance_part_step`, swap Parts for Core throughout
- `StepTransitionLog` extension — same two-FK pattern as StepExecution (nullable `part`, add nullable `core`, CheckConstraint)
- `StepExecutionMeasurement` extension — same pattern when measurements apply to cores (likely at receipt-inspection and teardown-finding stages)

**Why mirror not abstract:** the codebase style favors explicit single-purpose services. Part and Core lifecycles will diverge in places (sampling, FPI, ITAR are Parts-only; customer credit, condition grading at receipt are Core-only) and forcing them through a common abstraction would either accumulate type-narrowing in every consumer or paper over real differences. Sibling services age better.

### Decision R4 — Core's lifecycle status stays coarse; routing position lives on `Core.step`

`Core.status` (RECEIVED → IN_DISASSEMBLY → DISASSEMBLED → SCRAPPED) stays as-is — it's the coarse-grained financial/inventory-facing state. Fine-grained routing position lives on the new `Core.step` FK.

This mirrors how Parts work: `Parts.part_status` is coarse (PENDING, IN_PROGRESS, COMPLETED, SCRAPPED, etc.); `Parts.step` carries the fine-grained "where in the routing." Same shape for Cores.

For a Core mid-teardown:
- `Core.status` = IN_DISASSEMBLY
- `Core.step` = Step 3 of 6 (current teardown Op)

When the Core completes its last teardown Step, services transition `Core.status` to DISASSEMBLED in lockstep.

### Decision R5 — Auto-coordinate Core lifecycle with linked WO state

Add service-layer hooks that auto-transition Core in response to WO / Step events:

- When a Core's first teardown `StepExecution` enters `IN_PROGRESS`: auto-call `start_core_disassembly(core, user)` if status is RECEIVED.
- When a Core completes its terminal teardown Step: auto-call `complete_core_disassembly(core, user)`.
- When a Core is scrapped mid-teardown: auto-call `scrap_core(core, reason)` (already exists).

This closes the "two parallel state machines kept in sync by operator discipline" gap the codebase audit surfaced.

### Decision R6 — Teardown WO creation is generic WO creation + serializer validation; no dedicated service

The original framing proposed a `start_teardown` service that owned validation, WO creation, Core linking, StepExecution creation, and status transition in one transaction. On review, almost all of that is either generic WO machinery, serializer validation, or auto-coordination hooks defined elsewhere (R5):

- **Validation** (shared core_type, all RECEIVED, none already linked, Process is_disassembly + matching core_type): serializer-level — `clean()` or DRF validators.
- **WO creation + Core linking**: generic `WorkOrderViewSet.create` accepting `cores: [...]` alongside the existing `parts: [...]` shape. Mirrors how Parts WOs are created today — there is no `start_parts_workorder` service, so adding `start_teardown` would diverge from the established pattern for no benefit.
- **StepExecution creation**: deferred to when the operator opens the first step, not at WO creation time. Same as Parts.
- **Status transition (RECEIVED → IN_DISASSEMBLY)**: fires automatically per R5 — when the first teardown StepExecution enters IN_PROGRESS, an existing-service hook calls `start_core_disassembly(core, user)`. No call at WO creation needed.

What remains is a serializer with one extra validator (`Process must be is_disassembly=True for the shared core_type`) and a query helper for the picker.

```python
# Query helper, lives as a Processes queryset method or thin function:
def eligible_disassembly_processes_for(core_type) -> QuerySet[Processes]:
    return Processes.objects.filter(
        part_type=core_type,
        is_disassembly=True,
        status=APPROVED,
    )
```

**Surfaced as an operator action**: the existing `start_teardown_batch` viewset action (shipped in WS3) collapses into `WorkOrderViewSet.create` with `cores: [...]` and `process_id`. The bulk-teardown dialog gains a Process picker populated from `eligible_disassembly_processes_for(core_type)`, preselecting the default. Single-core teardown is just N=1; same code path.

The verb "Start Teardown" stays in the UI as a button label and in the API as the `WorkOrderViewSet.create` call site — naming clarity is preserved where users encounter it. What disappears is the service-layer wrapper.

Explicit operator-initiated, not auto-signaled on Core receipt — many cores get inspected and scrapped before teardown is decided; auto-creating WOs at receipt would clutter the queue.

**Q1 resolution: shape D.** `Processes.is_disassembly` boolean gates eligibility; `PartTypes.default_disassembly_process` nullable FK carries the canonical preference. Picker shows all eligible, preselects default. See "Resolved Questions" for the D→E migration path when join-model metadata becomes necessary.

**Q2 resolution: N-per-WO default.** WO is complete when every linked Core is in a terminal state (DISASSEMBLED or SCRAPPED — scrapped counts as terminal work done). No "split into N separate WOs" toggle in v1.

### Decision R7 — `HarvestedComponentCapture` custom DWI node

A capture node in the DWI node library specific to reman teardown.

**Engineer attrs:**
```ts
{
  node_id: string,
  label: string,
  required: boolean,
  enumerate_from: 'disassembly_bom' | 'manual',
  manual_component_types: PartTypeId[],
  strict_enumeration: boolean,
}
```

**Operator-side runtime behavior:**

1. Resolves Core via `step_execution.core` (now possible per R2).
2. If `enumerate_from === 'disassembly_bom'`: queries current-version `DisassemblyBOMLine` rows where `core_type = core.core_type`. Renders one row per `(component_type × expected_qty)`. A 4-cylinder injector with `expected_qty=4` for "Nozzle" gets four nozzle rows.
3. If `enumerate_from === 'manual'`: enumerates from `manual_component_types`.
4. Each row: `condition_grade` dropdown (A/B/C/SCRAP), `position` field, `condition_notes` textarea, optional `mark_missing` toggle. The `position` field reads from the BOM line's optional `positions` JSON array (see Q4 / Schema Changes); when populated, renders as a pre-filled label or Select with the canonical position labels; when null, renders as free-text input (backward compatible).
5. "Add unexpected component" button for yield variance (operator found something not in the BOM).
6. Per-row "Accept to inventory" action (Q5): when the operator has the existing `accept_harvestedcomponent` permission, the row exposes an "Accept to inventory" button that calls the existing `accept_component_to_inventory` service. When the permission is absent, the button is hidden / disabled with tooltip — separation-of-duties shops fall back to the existing out-of-band QA Inspector flow. No new service or schema change; permission expresses the policy.

**Completion criterion (per `can_complete_substep` contract):**

- With `strict_enumeration=true`: every expected row must have a grade OR be marked missing.
- With `strict_enumeration=false`: only the rows the operator filled get persisted; unfilled rows are skipped silently.

**Backend (Complete Substep):**

For each filled row, create a `HarvestedComponent` row with:
- `core` = resolved Core
- `component_type` from row
- `condition_grade`, `position`, `condition_notes` from row
- `disassembled_at = now`, `disassembled_by = operator` (from `SubstepCompletion`)

For `condition_grade='SCRAP'`: call `scrap_component(component, user, reason=condition_notes)` in the same transaction.

For non-SCRAP: leaves component in default state, awaiting downstream `accept_to_inventory` flow (handled separately, not v1 DWI scope).

Returns created `HarvestedComponent` IDs. Stored in the corresponding `SubstepResponse.value_text` as JSON:
```json
{
  "kind": "harvested_components",
  "harvested_component_ids": ["uuid1", "uuid2", ...],
  "missing_component_types": ["partype-id-a", "partype-id-b"]
}
```

**Inline acceptance to inventory (Q5 resolved):** in-scope via per-row button gated by the existing `accept_harvestedcomponent` permission. Shops with separation-of-duties leave the permission off the disassembling operator's group; the button is hidden and the existing out-of-band QA flow runs. Shops where one role does both grant the permission and the button works inline. No new service, no schema change — the platform already has the gate.

**Photo capture per component (Q6 resolved):** the `HarvestedComponentCapture` node does *not* carry a per-row photo FK. Photos ride the existing step-level media-attachment pattern — a media-upload node is co-located alongside the capture node within the same teardown substep, and uploaded documents attach to the step / substep response. Lookup goes "media → substep response → step execution → core" via the per-core flow, rather than "media → HarvestedComponent" directly. Operators caption photos at upload time when component-level precision matters. If a customer later surfaces yield-photo-by-serial analytics or per-component warranty requirements, add a nullable `HarvestedComponent.media` FK (or M2M) at that point — backfillable, cheap.

---

## Schema Changes

### `StepExecution`
- `part`: make nullable
- Add `core`: nullable FK to `Core`, on_delete=CASCADE, related_name='step_executions'
- Add CheckConstraint: exactly one of (part, core) is non-null

### `StepTransitionLog`
- `part`: make nullable
- Add `core`: nullable FK to `Core`, on_delete=CASCADE, related_name='step_transition_logs'
- Add CheckConstraint: exactly one of (part, core) is non-null

### `StepExecutionMeasurement`
- `part`: make nullable (if not already)
- Add `core`: nullable FK to `Core`, on_delete=CASCADE, related_name='measurements'
- Add CheckConstraint: exactly one of (part, core) is non-null
- (Note: measurements at receipt-inspection stage attribute to Core; measurements on extracted components attribute to the resulting Parts via existing accept-to-inventory flow.)

### `Core`
- Add `step`: nullable FK to `Steps`, on_delete=SET_NULL, related_name='active_cores'

### `Processes`
- Add `is_disassembly`: boolean, default False. Flags a Process as eligible for teardown of its `part_type`. The eligibility query is `Processes.objects.filter(part_type=core_type, is_disassembly=True, status=APPROVED)`.

### `PartTypes`
- Add `default_disassembly_process`: nullable FK to `Processes`, on_delete=SET_NULL, related_name='default_for_disassembly'. Canonical preference for the teardown picker. Optional — when null, the picker has no preselection and (for automation paths) WO creation refuses to resolve a default and surfaces a "pick one" task.
- (Q1 shape D — see Decision R6 and the D→E migration note in Resolved Questions.)

### `DisassemblyBOMLine`
- Add `positions`: JSONField(default=list, blank=True). Optional ordered list of position labels of length matching `expected_qty`. When populated, the `HarvestedComponentCapture` node pre-fills each row's position; when empty/null, position is free-text. Backward compatible with all existing rows. (Q4 resolution.)

### `Substep` (no new fields)
- Existing `body_blocks` JSON accommodates the new `HarvestedComponentCapture` node.

---

## Service Layer Additions

### `Tracker/services/mes/cores.py` (new module — mirrors `services/mes/parts.py`)

```python
def advance_core_step(core: Core, operator, decision_result=None) -> str:
    """Advance Core to next step. Mirrors advance_part_step — distinct service
    because Part and Core lifecycles diverge in places (sampling, FPI are
    Parts-only; condition grading is Core-only). Same shape, different specifics."""
```

### Existing services extended (not new)

- **`_cascade_work_order_completion`** (in `services/mes/parts.py` or wherever it lives): extend to be subject-aware. A WO is complete when every linked subject — Parts AND Cores — reaches terminal state. One cascade function, two subject types. No new `_cascade_..._for_core` companion needed.
- **`start_core_disassembly`** (existing): unchanged. The R5 hook on StepExecution start calls it when a Core's first teardown StepExecution enters IN_PROGRESS. No wrapper.
- **`complete_core_disassembly`** (existing): unchanged. The R5 hook on StepExecution complete calls it when a Core's terminal teardown Step finishes. No wrapper.
- **`scrap_core`** (existing): unchanged. Surfaces the same way it does today.

### Query helper (not a service module)

```python
# Lives as a Processes queryset method or thin function in services/reman/eligibility.py:
def eligible_disassembly_processes_for(core_type) -> QuerySet[Processes]:
    return Processes.objects.filter(
        part_type=core_type,
        is_disassembly=True,
        status=APPROVED,
    )
```

### `Tracker/services/dwi/harvested_component_capture.py` (new module)

```python
def create_harvested_components_from_capture(
    step_execution: StepExecution,
    substep: Substep,
    capture_node_id: str,
    rows: list[HarvestedComponentRow],
    user,
) -> list[HarvestedComponent]:
    """Called by the substep batch-complete handler. Creates HarvestedComponent
    rows, calls scrap_component for SCRAP grade rows in the same transaction,
    returns the created IDs. Genuinely necessary: bridges DWI substep response
    shape to HarvestedComponent rows + dispatches scrap for SCRAP-graded rows
    in one transaction. Not a candidate for collapse into generic substep
    completion handling."""
```

---

## Frontend Touchpoints

### New
- `HarvestedComponentCapture` node component (`src/components/dwi/nodes/HarvestedComponentCapture/`)
- Process picker in the existing bulk-teardown dialog (shipped in WS3 as `CoresBulkActionsBar.tsx`)
- Core selector in the DWI substep view when the WO has multiple Cores (the "current core" picker)

### Modified
- `CoresBulkActionsBar` (shipped WS3): add Process picker preselecting the default, pass `process_id` to the (now-collapsed) WorkOrder create call.
- `CoreDisassemblyPage` either retires in favor of DWI substep flow, or coexists as an alternate path. Recommend coexistence during transition: shops using DWI for teardown migrate; shops keeping the dedicated page keep it.
- Operator queue / WIP views gain Core-aware listings (alongside Part-aware ones).

### Unchanged
- `CoreReceiveFormPage` — Core creation flow stays as-is.
- `RemanDashboardPage` — list views update to include Cores at teardown Steps but no structural change.
- `accept_to_inventory` flow — fully separate from teardown DWI capture; QA Inspector workflow downstream.

---

## Migration Plan

### Phase R1 — `StepExecution` + `StepTransitionLog` + `StepExecutionMeasurement` extensions
- Schema migrations (additive: nullable Core FKs + CheckConstraints + null-relax existing Part FKs)
- Refactor every existing `step_execution.part` read site to handle the null case — prefer explicit `if step_execution.part:` / `if step_execution.core:` checks at call sites over a generic helper
- Optional: a `step_execution.subject` resolution helper if cross-cutting code paths (audit logging, traveler PDF rendering, generic operator-queue formatting) end up needing one. Avoid adding it preemptively — most call sites naturally know which subject type they're handling, and the helper papers over a real distinction.
- Test suite update for sampling / FPI / measurement paths

### Phase R2 — `Core.step` + `advance_core_step` + auto-coordination
- Add `Core.step` field
- Implement `advance_core_step` service (mirror of `advance_part_step`)
- Hook into StepExecution lifecycle: starting first teardown StepExecution → call `start_core_disassembly`
- Hook into completion: terminal teardown Step done → call `complete_core_disassembly`
- WO completion cascade includes Cores

### Phase R3 — Eligibility model + WorkOrder serializer extension + picker UI
- Add `Processes.is_disassembly` boolean and `PartTypes.default_disassembly_process` nullable FK (Q1 shape D).
- Add `eligible_disassembly_processes_for(core_type)` queryset helper.
- Extend `WorkOrderSerializer` to accept `cores: [...]` and `process_id`; add validator that requires the Process to be `is_disassembly=True` with matching `part_type` when `cores` is non-empty.
- Refactor existing `start_teardown_batch` viewset action (shipped in WS3) to collapse into `WorkOrderViewSet.create`.
- Add Process picker to bulk-teardown dialog (preselects default; surfaces all eligible).
- No new service module — the proposed `start_teardown` collapses to serializer validation + generic WO creation + R5 auto-coordination hooks (defined in R2).

### Phase R4 — `HarvestedComponentCapture` custom node
- Frontend node component + popover form
- Operator runtime that queries DisassemblyBOMLine and renders rows
- Backend `create_harvested_components_from_capture` service
- Hook into substep batch-complete to invoke the capture service

### Phase R5 — Multi-Core WO support
- "Current Core" switcher on the substep view
- WO progress UI that shows N cores at various teardown Steps
- Operator queue Core-aware filtering

**Phasing dependencies:**

R1 must ship before R2 (Core can't have StepExecution without R1). R2 must ship before R3 (the picker UX depends on `advance_core_step` + auto-coordination hooks existing). R3 must ship before R4 (HarvestedComponentCapture needs StepExecution-with-Core to exist). R5 builds on R4 but is operator-UX-focused; the backend supports multi-Core WOs from R2 onward.

**Total estimated effort:** 2–3 weeks of focused work for R1–R4 (the "ship reman DWI" milestone). R5 (multi-Core UX polish) adds another ~3–5 days when needed.

---

## Resolved Questions

The six originally-open questions resolved in a design session. Four (Q3–Q6) collapsed onto existing infrastructure rather than needing new concepts.

### Q1 — Eligibility model: shape D (boolean flag + default FK)

`Processes.is_disassembly` (boolean) gates eligibility per Process. `PartTypes.default_disassembly_process` (nullable FK) carries the canonical preference. The teardown picker shows all eligible Processes for the core_type, preselects the default when set, and requires explicit choice when default is null.

**Why D over the originally-proposed single canonical FK:** core_types in practice have multiple legitimate teardown variants (quick teardown, full overhaul, failure-analysis). A single FK forces a schema change to support variants. D supports unlimited variants with a small data cost.

**Why not shape E (explicit join model) yet:** E (`DisassemblyProcessAssignment(part_type, process, is_default, label, sort_order)`) buys per-assignment metadata (sort order, custom labels, per-pair authoring history) but costs an extra ~10 hrs of frontend authoring UI — tenants can't reach Django admin in UQMES (the platform operator runs admin; tenant engineers use the regular UI), so the "ship backend + admin for now" middle path doesn't exist. D ships in ~3 hrs and is the durable middle until a customer surfaces enough variants to need ordered picker / per-assignment labels.

**D → E migration path** (cheap when needed): write a data migration creating one `DisassemblyProcessAssignment` row per existing `(PartType, Process)` pair where `Processes.is_disassembly=True` and `Processes.part_type=PartType`. Set `is_default=True` on the row matching `PartTypes.default_disassembly_process`. Drop the boolean and FK after migration. The frontend picker contract (`eligible_disassembly_processes_for(core_type)`) stays the same — only the resolver implementation changes. No data loss; existing teardown WOs unaffected.

**Open sub-question deferred:** whether to remember the last-used Process per (operator × core_type) for picker convenience. Cheap to add later if operators surface it.

### Q2 — Multi-Core vs. single-Core WOs: N-per-WO default

The existing WS3 bulk-teardown action (already shipped) creates one WO linking N Cores. This matches physical reality (operators batch-tear-down at one bench in a session), matches Parts WO semantics (Parts already batch N-per-WO), and keeps the WO queue at session-scale instead of growing 1:1 with received cores.

**WO completion semantics:** a teardown WO is complete when every linked Core is in a terminal state — DISASSEMBLED *or* SCRAPPED. Scrapped counts as terminal work done; the operator performed disassembly labor even if yield was zero.

**No "split into N separate WOs" option in v1.** No customer has surfaced a need; adds UX surface for a hypothetical preference. Single-core teardown is just N=1 through the same flow.

**Mid-batch divergence** (some cores route to standard path, others to regrind via Q3 decision branching) shows up in the WO Control Center cores card (designed in companion session) as per-row status pills, sorted active-first. The data model commits to per-Core state anyway (R2, R3), so divergence is a UI presentation problem, not a model problem.

### Q3 — Decision points on teardown routes: mirror Parts DAG, no new fields

The existing DAG infrastructure covers teardown decision-point branching without schema changes:

- `Steps.is_decision_point` (boolean) + `Steps.decision_type` ('QA_RESULT' | 'MEASUREMENT' | 'MANUAL') — `mes_lite.py:519–527`
- `StepEdge.edge_type` ('DEFAULT' | 'ALTERNATE' | 'ESCALATION') with `condition_measurement` / `condition_operator` / `condition_value` for threshold-based branching — `mes_lite.py:1079, 1120–1137`
- `StepExecution.decision_result` already persists operator or system decision — `mes_lite.py:1211`
- `advance_part_step(part, operator, decision_result)` consumes the result and delegates to `Parts.get_next_step()`, which evaluates edges and conditions — `parts.py:85`, `mes_lite.py:2504`

**What Cores need (per R3 mirror-pattern decision):**
- `Core.get_next_step(decision_result)` — copy of `Parts.get_next_step`, references `Core.step` and the linked WO's Process. ~100 LOC.
- `advance_core_step(core, operator, decision_result)` service — copy of `advance_part_step`. ~80 LOC.

**No new decision types.** "Scored head → regrind path else → standard path" maps onto existing `decision_type='MANUAL'` (operator picks) or `decision_type='MEASUREMENT'` (a measurement crosses a threshold on the StepEdge). The grade is captured on `HarvestedComponent` as data; if grade-driven *automatic* routing becomes desirable later, add a `CORE_CONDITION` decision_type at that point.

**Rework loops come for free.** `Steps.max_visits` and `StepExecution.visit_number` already exist — a Core can revisit an inspection step after regrind within the existing cap.

**Substep wiring:** the substep that captures the operator's decision uses an existing manual-choice or measurement node; the batch-complete handler writes the chosen value into the parent StepExecution's `decision_result`. Generic substep-response-to-StepExecution wiring, not reman-specific.

### Q4 — `HarvestedComponent.position` standardization: optional positions on DisassemblyBOMLine

Add an optional `positions: JSONField(default=list)` to `DisassemblyBOMLine`. When populated with a list of length `expected_qty`, the `HarvestedComponentCapture` node pre-fills each enumerated row's position field with `positions[row_index]`. When empty/null, position renders as free-text (current behavior). Backward compatible.

**Why DisassemblyBOMLine and not the originally-proposed `PartTypes.position_template`:** positions vary per (core_type × component_type). A 4-cylinder injector's Nozzle positions are `["Cyl 1", "Cyl 2", "Cyl 3", "Cyl 4"]`; the same core's Head Bolt positions are entirely different. PartType is the wrong scope. DisassemblyBOMLine is already keyed on (core_type, component_type) and already drives the capture node's row count via `expected_qty`. Co-locating positions there mirrors the existing data shape.

**Authoring UI:** the existing BOM editor gains an optional positions array editor; form validation enforces `len(positions) == expected_qty` when both are set.

**Total cost:** ~2 hrs (5 LOC schema + 30 LOC frontend pre-fill + 40 LOC BOM editor + migration). Gets you clean yield-analytics joins ("which cylinder position fails most often?") whenever a customer asks.

### Q5 — Inline acceptance to inventory: in-scope via existing permission gate

The `HarvestedComponentCapture` node renders a per-row "Accept to inventory" button. Visibility/enablement is gated by the existing `accept_harvestedcomponent` permission. Clicking calls the existing `accept_component_to_inventory` service — same code path as the out-of-band reman UI. No new service, no schema change.

**Role boundary resolves itself.** Separation-of-duties shops don't grant the permission to the disassembling operator's group; the button is hidden and the existing out-of-band QA Inspector flow handles acceptance. Small shops where one role does both grant the permission and the button works inline.

**Caveats** (operational, not feature):
- Accept requires the PartType to have stocking-process configuration (ERP id prefix, life-tracking attribution). Failures surface as actionable errors.
- The accept event is already audited via existing services.
- High-quantity components (e.g., strict-enumeration of 16-valve components) hit the accept service N times in quick succession; a bulk-accept service is a future optimization, not v1.

### Q6 — Photo capture per harvested component: ride existing step-level media, no per-component FK

Drop the originally-proposed `HarvestedComponent.photo_document` nullable FK. Photos taken during teardown attach via the existing step-level media-attachment pattern — a media-upload node co-located alongside the `HarvestedComponentCapture` node within the same teardown substep. Uploaded documents attach to the step / substep response; lookup goes "media → substep response → step execution → core" via the per-core flow.

**Trade-off:** loses "photo of this specific HarvestedComponent row" precision. One photo of an engine head with damaged cylinders 1 and 3 doesn't tag two specific component rows; operator caption disambiguates. Adequate for most reman shops.

**Upgrade path:** if a customer surfaces yield-photo-by-serial analytics or per-component warranty requirements, add a nullable `HarvestedComponent.media` FK (or M2M to Documents). Backfillable from existing step-level media via the substep response → harvested-component-id link.

**Why this is the right call:** the platform already has a complete media-attachment story (retention, permissions, audit, document types). Inventing a parallel per-component photo surface duplicates that infrastructure for a precision few shops need at v1.

---

## Newly-open sub-questions (raised by the resolutions above)

These are smaller and tactical, not blocking R1–R4 implementation:

1. **Picker preselection persistence.** Should the bulk-teardown dialog remember the last-used Process per (operator × core_type)? Cheap localStorage addition if operators ask; skip otherwise.
2. **Eligibility query for superseded versions.** `Processes.is_disassembly=True` on an old version: should the picker auto-walk to the current version of the same parent chain, or refuse and force engineers to re-flag the new version? Lean: auto-walk to current version on read, since `is_disassembly` is intent-level and intent doesn't change across version bumps. Confirm at R3 design time.
3. **Mid-WO permission revocation for inline accept.** If a tenant revokes `accept_harvestedcomponent` from an operator mid-teardown, the in-flight capture node hides the Accept button on its next render. Acceptable — no need to surface explicit feedback.
4. **`positions` array validation on `expected_qty` change.** If engineering edits a BOM line's `expected_qty` from 4 → 6, what happens to a 4-entry `positions` array? Options: refuse the change until positions is updated; clear positions; pad with nulls. Lean: refuse with a clear validation error so engineers don't accidentally lose position labels.

---

## Out of Scope

- **Customer credit issuance** (separate financial transaction; existing `issue_core_credit` service)
- **Per-component direct photo FK** (Q6 resolution: ride existing step-level media instead; per-component FK is the upgrade path if customers surface it)
- **Per-(operator × core_type) picker memory** (Q1 sub-question; cheap to add later)
- **`DisassemblyProcessAssignment` join model with per-assignment metadata** (Q1 shape E; D→E migration path documented when sort order / labels / per-pair authoring history are needed)
- **Bulk-accept service for high-quantity components** (Q5 caveat; N sequential accept calls work for v1)
- **Aerospace MRO terminology / regulatory regime** (AS9110, FAA Part 145 — different vocabulary, different audit requirements; out of v1)
- **Industrial electric motor reman** (EASA AR100 — "core" naming collision; needs vocabulary work before targeting)
- **Medical device refurb** (FDA UDI regime — different traceability requirements; out of v1)
- **Shared-resource Ops** (furnace cycles processing 50 parts as one event — explicitly rejected per Decision R1; storage-cheap per-unit rows are the philosophy)

---

## Known limitations of v1

- **No per-assignment metadata on (PartType, Process) eligibility pairs.** Shape D (boolean + default FK) doesn't carry sort order, custom labels, or per-pair authoring history. The picker orders eligible Processes alphabetically with the default preselected. Upgrade to shape E when a customer needs ordered pickers or per-pair labels — migration path documented in Q1 resolution.
- **Default Process ambiguity at automation time.** When `PartTypes.default_disassembly_process` is null and multiple Processes are flagged eligible, automation paths (scheduled receipt-to-teardown, ERP imports) cannot resolve a Process deterministically; they refuse and surface a "pick one" task to the operator queue. Acceptable for v1.
- **One photo upload surface per substep, not per HarvestedComponent.** A photo of a multi-cylinder engine head doesn't tag specific component rows; operator captions disambiguate. Upgrade to per-component `HarvestedComponent.media` FK when surfaced.
- **No bulk-accept for high-quantity components.** Inline acceptance from a strict-enumeration capture node fires N sequential `accept_component_to_inventory` calls. Optimize when a customer reports perceptible UI latency.
- **No mid-teardown PCN handling specific to Cores.** If a teardown Process is updated mid-teardown, in-flight WOs ride the existing `ProcessChangeMigrationDisposition` flow per the main DWI doc. Cores in mid-teardown follow the same migration semantics as Parts in mid-Op.
- **No reman-specific approval template.** Teardown Process changes go through the same authoring approval flow as any other Process (per decision #15 in the main DWI doc). If reman customers want specialized approval routing (e.g., reman engineer + QA inspector), they configure a `Processes.approval_template` override for their teardown Processes — uses existing mechanism.

---

## Cross-references

- `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md` — main DWI design (substep model, custom node library, authoring approval, permissions)
- `Documents/VERSIONING_ARCHITECTURE.md` — how Process versioning applies to teardown Processes
- `PartsTracker/Tracker/models/reman.py` — Core, HarvestedComponent, DisassemblyBOMLine
- `PartsTracker/Tracker/services/reman/` — existing Core / HarvestedComponent services
- `PartsTracker/Tracker/services/mes/parts.py` — `advance_part_step` (template for `advance_core_step`)
- `ambac-tracker-ui/src/pages/reman/` — existing reman frontend pages