# Reman ↔ DWI Integration

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
3. **No "start teardown" service.** There's no service that creates a teardown WO from a received Core and links them.
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

### Decision R6 — `start_teardown` service creates the WO from a received Core

A new service in `Tracker/services/reman/teardown.py`:

```python
def start_teardown(core: Core, user, process: Processes | None = None) -> WorkOrder:
    """Create a teardown WorkOrder for this Core and link them.

    If `process` is None, looks up the disassembly Process for `core.core_type`
    via `PartType.disassembly_process` FK (new field — see Schema Changes).
    Creates the WO with that Process, links via core.work_order = wo,
    creates the first StepExecution(core=core, step=process.start_step),
    and calls start_core_disassembly(core, user) in the same transaction.
    """
```

**Surfaced as an operator action** on `CoreDetailPage` ("Start Teardown" button) and as a viewset action on `CoreViewSet`. Explicit operator-initiated, not auto-signaled on Core receipt — many cores get inspected and scrapped before teardown is decided; auto-creating WOs at receipt would clutter the queue.

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
4. Each row: `condition_grade` dropdown (A/B/C/SCRAP), `position` text input, `condition_notes` textarea, optional `mark_missing` toggle.
5. "Add unexpected component" button for yield variance (operator found something not in the BOM).

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

**Inline acceptance to inventory: out of scope for v1.** The accept-to-inventory flow has its own gates (ERP id generation, life-tracking transfer, separate QA Inspector signoff). Different workflow, different role. The capture node only creates HarvestedComponent rows in default state.

**Photo capture per component: deferred.** Reman shops often want per-component photos for warranty / traceability. v1 ships without; add when a customer surfaces it. Schema addition would be a nullable `photo_document` FK on `HarvestedComponent`.

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

### `PartTypes`
- Add `disassembly_process`: nullable FK to `Processes`, on_delete=SET_NULL, related_name='disassembling_part_types'
- Used by `start_teardown` to resolve the right Process for a Core's type.

### `Substep` (no new fields)
- Existing `body_blocks` JSON accommodates the new `HarvestedComponentCapture` node.

---

## Service Layer Additions

### `Tracker/services/reman/teardown.py` (new module)

```python
def start_teardown(core: Core, user, process: Processes | None = None) -> WorkOrder:
    """Create a teardown WO from a received Core. Returns the WO."""

def can_complete_teardown(core: Core) -> tuple[bool, list[str]]:
    """Check if a Core's teardown is ready to complete (all teardown Steps done)."""

def complete_teardown(core: Core, user) -> Core:
    """Wrap complete_core_disassembly with WO-cascade and final validation."""
```

### `Tracker/services/mes/cores.py` (new module — mirrors `services/mes/parts.py`)

```python
def advance_core_step(core: Core, operator, decision_result=None) -> str:
    """Advance Core to next step. Mirrors advance_part_step."""

def _cascade_work_order_completion_for_core(core: Core) -> None:
    """When a Core reaches terminal state, check WO completion."""
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
    returns the created IDs."""
```

### Modified: `_cascade_work_order_completion` in `services/mes/parts.py`

Add Core-awareness: a WO is complete when all linked Parts AND all linked Cores reach terminal states.

---

## Frontend Touchpoints

### New
- `HarvestedComponentCapture` node component (`src/components/dwi/nodes/HarvestedComponentCapture/`)
- "Start Teardown" button on `CoreDetailPage`
- Core selector in the DWI substep view when the WO has multiple Cores (the "current core" picker)

### Modified
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
- Refactor every existing `step_execution.part` read site to handle the null case
- Service-layer helpers (`step_execution.subject` resolution helper that returns part-or-core)
- Test suite update for sampling / FPI / measurement paths

### Phase R2 — `Core.step` + `advance_core_step` + auto-coordination
- Add `Core.step` field
- Implement `advance_core_step` service (mirror of `advance_part_step`)
- Hook into StepExecution lifecycle: starting first teardown StepExecution → call `start_core_disassembly`
- Hook into completion: terminal teardown Step done → call `complete_core_disassembly`
- WO completion cascade includes Cores

### Phase R3 — `start_teardown` service + `PartTypes.disassembly_process` + frontend
- Add `PartTypes.disassembly_process` FK
- Implement `start_teardown` service
- Add "Start Teardown" action to `CoreViewSet` + button on `CoreDetailPage`

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

R1 must ship before R2 (Core can't have StepExecution without R1). R2 must ship before R3 (start_teardown requires the flow plumbing). R3 must ship before R4 (HarvestedComponentCapture needs StepExecution-with-Core to exist). R5 builds on R4 but is operator-UX-focused; the backend supports multi-Core WOs from R2 onward.

**Total estimated effort:** 2–3 weeks of focused work for R1–R4 (the "ship reman DWI" milestone). R5 (multi-Core UX polish) adds another ~3–5 days when needed.

---

## Open Questions

1. **`PartType.disassembly_process` vs. WO-time selection.** `start_teardown` resolves the teardown Process from `core.core_type.disassembly_process`. Alternative: let the operator pick a Process at WO creation time. The FK approach is more deterministic (one canonical Process per core_type) but less flexible (what if you have two teardown variants — quick teardown vs. full teardown?). Decide before R3.

2. **Single-Core vs. multi-Core teardown WOs.** R5 handles multi-Core WOs. Should the default be 1 Core per WO with an explicit "add Core to teardown batch" action, or N Cores per WO with operator picking from a queue? Lean toward 1-per-WO default with explicit batching; matches the smaller-shop reality and avoids surprising operators with WOs that have unexpected scope.

3. **Decision points on teardown routes.** A multi-Op teardown might have decision branches ("if cylinder head scored → regrind path; else → standard path"). Cores at decision points need `decision_result` handling. The existing Part decision-point routing in `advance_part_step` works; `advance_core_step` mirrors it. But the substep that captures the decision needs to write to the StepExecution's decision_result field. Probably covered by a future Level-2 `applies_when` DSL feature (deferred per main DWI doc) — confirm at R2 design time.

4. **`HarvestedComponent.position` standardization.** Currently free-text ("Cyl 1", "Position A"). For multi-cylinder engines, would a per-PartType `position_template` (JSON: `["Cyl 1", "Cyl 2", "Cyl 3", "Cyl 4"]`) reduce operator typos? Deferred unless a customer surfaces yield analytics that need clean position joins.

5. **Inline acceptance to inventory inside DWI.** Currently out of v1 scope. If a customer specifically wants the disassembly operator to also accept components inline (rather than having a separate QA Inspector flow), the `HarvestedComponentCapture` node would add an "Accept to inventory" action per row that calls `accept_component_to_inventory`. Add when surfaced; not v1.

6. **Photo capture per harvested component.** Schema addition `HarvestedComponent.photo_document` nullable FK + UI integration. Probably the first customer ask after v1 ships.

---

## Out of Scope

- **Inline acceptance to inventory** (downstream QA Inspector flow handles this)
- **Customer credit issuance** (separate financial transaction; existing `issue_core_credit` service)
- **Per-component photos at capture time** (deferred; schema addition is cheap when needed)
- **Aerospace MRO terminology / regulatory regime** (AS9110, FAA Part 145 — different vocabulary, different audit requirements; out of v1)
- **Industrial electric motor reman** (EASA AR100 — "core" naming collision; needs vocabulary work before targeting)
- **Medical device refurb** (FDA UDI regime — different traceability requirements; out of v1)
- **Shared-resource Ops** (furnace cycles processing 50 parts as one event — explicitly rejected per Decision R1; storage-cheap per-unit rows are the philosophy)

---

## Known limitations of v1

- **One disassembly Process per PartType.** `PartTypes.disassembly_process` is a single nullable FK. If a customer needs multiple teardown variants per part type (quick teardown vs. full overhaul), they pick at WO creation time and the FK is informational only. Re-evaluate if multiple variants surface.
- **No mid-teardown PCN handling.** If a teardown Process is updated mid-teardown, existing in-flight WOs ride the existing `ProcessChangeMigrationDisposition` flow per the main DWI doc. Cores in mid-teardown follow the same migration semantics as Parts in mid-Op.
- **No reman-specific approval template.** Teardown Process changes go through the same authoring approval flow as any other Process (per decision #15 in the main DWI doc). If reman customers want specialized approval routing (e.g., reman engineer + QA inspector), they configure a `Processes.approval_template` override for their teardown Processes — uses existing mechanism.

---

## Cross-references

- `Documents/DIGITAL_WORK_INSTRUCTIONS_DESIGN.md` — main DWI design (substep model, custom node library, authoring approval, permissions)
- `Documents/VERSIONING_ARCHITECTURE.md` — how Process versioning applies to teardown Processes
- `PartsTracker/Tracker/models/reman.py` — Core, HarvestedComponent, DisassemblyBOMLine
- `PartsTracker/Tracker/services/reman/` — existing Core / HarvestedComponent services
- `PartsTracker/Tracker/services/mes/parts.py` — `advance_part_step` (template for `advance_core_step`)
- `ambac-tracker-ui/src/pages/reman/` — existing reman frontend pages