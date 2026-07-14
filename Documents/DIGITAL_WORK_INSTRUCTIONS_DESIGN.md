# Digital Work Instructions (Substep) Design

> **Status (2026-07-13): implemented as designed.** `Substep`,
> `BatchExecution`, `SubstepCompletion`, `SubstepResponse`, `SamplingDecision`,
> gate completions, and translations live in `Tracker/models/dwi.py`, with
> `viewsets/dwi.py` and `services/dwi/`. Kept as the design record.

## Overview

Adds a substep layer below the existing `Steps` (Op) model to support Dozuki-style digital work instructions: rich content per substep, resource callouts, mandatory acknowledgment/signoff, per-substep measurement capture, and per-substep change control.

**Scope:** ORM models, serializers, viewsets, service layer, **and the frontend authoring editor + custom node library**. Blob storage uses the existing `Documents` model. Operator-facing execution UI (kiosk-style step runner) is covered separately under the homepage-widget / `/my-work` planning track.

**Vocabulary alignment:**
- `Processes` = Routing
- `Steps` = Op (Operation)
- `Substep` (new) = Work instruction unit within an Op
- `StepExecution` (existing) = Op-level execution record
- `SubstepCompletion` (new) = Substep-level execution record

---

## Existing Infrastructure Reused

| Component | File | Role |
|---|---|---|
| `Processes`, `Steps`, `ProcessStep`, `StepEdge` | `mes_lite.py` | Routing graph stays as-is |
| `StepExecution` | `mes_lite.py:1141` | Op execution; parent of new substep completions |
| `StepExecutionMeasurement` | `qms.py:2372` | Data capture; gains optional `substep` FK |
| `StepMeasurementRequirement` | `mes_lite.py:342` | Gates; gains optional `substep` FK |
| `StepRequirement` | `mes_lite.py:896` | Gates; gains optional `substep` FK |
| `ProcessChangeRequest/Order/Notice` | `change_control.py` | PCN flow extends to substeps |
| `ProcessChangeMigrationDisposition` | `change_control.py:47` | In-flight WO migration policy (MIGRATE_ALL / MIGRATE_SELECTED / KEEP_ALL); reused as-is |
| `impact_analysis.py` | `services/change_control/` | `snapshot_affected_workorders` / `list_affected_workorders`; substeps ride existing WO migration |
| `ApprovalResponse` / `CapaTasks` signature pattern | `core.py:2634`, `qms.py:1049` | `signature_data` + `verification_method` + `requires_signature` fields reused on `SubstepCompletion` |
| `VerificationMethod` enum | `core.py:2628` | PASSWORD / SSO / NONE; reused as-is |
| `EquipmentType` | `mes_standard.py:30` | Authoring-time tool reference target |
| Versioning architecture | `Documents/VERSIONING_ARCHITECTURE.md` | Substeps version with their parent Process |

---

## Architectural Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Execution snapshot policy | Process-version pin at WO start (no substep duplication); in-flight migration via existing `ProcessChangeMigrationDisposition` | Audit-defensible by default; reuses existing PCO-time disposition (KEEP_ALL / MIGRATE_ALL / MIGRATE_SELECTED). Operators see whichever substep version is pinned via the WO's Process version. |
| 2 | Versioning unit | Process-level only | Matches existing versioning; no third axis |
| 3 | Content storage | Hybrid: JSON prose + FKs for queryables | Editor maps cleanly; measurements/resources/documents stay queryable |
| 4 | Resources | `SubstepResource` → `EquipmentType` / `MaterialType` / `PPEType` | Authoring references classes, execution binds instances |
| 5 | Execution grain | Per-substep `SubstepCompletion` rows | Per-substep timing, mandatory-ack, signoff tracking |
| 6 | Translations | `SubstepTranslation` rows now, no UI yet | Data model right from day one; avoids destructive migration later |
| 7 | Reuse | Op-owned + provenance fields now; `LibrarySubstep` deferred | Cheapest option that keeps the library door open |
| 8 | Substep ordering | Author chooses per Op (`sequencing_mode` on `Steps`) | Sequential vs. free-order picked at authoring time |
| 9 | PCN targeting | Three nullable FKs on `ProcessChangeRequest` | Explicit, easy joins, no GFK pain |
| 10 | Signoff | Per-substep `requires_signature` flag; `SubstepCompletion` reuses `signature_data`/`verification_method`/`ip_address` pattern from `CapaTasks` | Matches existing pattern operators see in CAPA closure; no new signature primitive |
| 11 | Conditionals | Defer past Level 1 (`is_optional` flag + operator-marked N/A); Level-2 inspection-driven applicability sketched in Deferred Items with the `applies_when` JSON DSL | Avoids speculative rules engine; Level-2 design is documented so reman customers can pick up the work cleanly when they surface the need |
| 12 | Editor library | **Raw `@tiptap/react` + `@tiptap/starter-kit`**, MIT, with custom nodes for DWI-specific blocks | `reactjs-tiptap-editor` was evaluated and rejected — see "Editor & Custom Node Library" below |
| 13 | Template vs. execution data | Template (`Substep.body_blocks`) and operator responses are stored in **separate tables**, never inside the document JSON | Document is the engineer's authoring artifact; operator clicks/measurements/signatures belong on per-execution rows for audit, versioning, and multi-operator safety |
| 14 | Sampling routing model | **Block-based** (current state) — sampled parts pause at their work step until a passing `QualityReport` exists; no separate graph node for "QC inspection." Gate-based routing (auto-resolved `SAMPLING_GATE` step) is deferred. | SMB shop reality is "operator brings part to QC bench, QC inspects, operator continues" — same custody, same step record. Block-based matches the actual workflow; gate-based would model a "literal part diversion" flow that doesn't exist in our customer base. |
| 15 | Authoring approval granularity | **Per-Step**, via the existing `ProcessStep` through-table (which is already versioned with its parent Process). Each Step's substep changes get their own `ApprovalRequest`; the Process version becomes fully active when all of its `ProcessStep` rows are approved. | Engineers iterate on one Op at a time; reviewers want focused diffs ("here's what changed in Op 3") rather than whole-Process change-sets. Per-Step keeps reviews bounded and lets multiple Steps in the same version be approved in parallel. |
| 16 | Approval template resolution | **Most-specific-wins**: explicit `Processes.approval_template` FK → `PartTypes.approval_template` FK → tenant default `ApprovalTemplate(approval_type='PROCESS_APPROVAL')`. | Customers want sensible defaults out of the box plus the ability to override for specific high-risk part families or processes (e.g. aerospace parts requiring extra engineering sign-off). |
| 17 | Author≠approver enforcement | **General `ApprovalResponse` rule** — at create time, reject if `response.user_id == approval_request.requester_id`. Lives in `services/core/approval/`, applies uniformly to **every** `ApprovalRequest` type (substep authoring, CAPA closure, disposition, customer use-as-is, future types). Not DWI-specific. | ISO 9001 §7.5.3 / AS9100 §8.5.6 / 21 CFR 820.40 require segregation of duties on document approval. One server-side gate covers all approval types; emergency-bypass (Tenant Admin override) is a separately gated permission deferred until a customer surfaces the need. |
| 18 | `node_id` minting | **Client-side via `uuidv7()`**. Frontend mints at insert / paste regenerate / library template import using `uuidv7` (consistent with `SecureModel` PKs across the codebase). Server validates UUID format + intra-document uniqueness on `Substep.save()`. Cut-paste regenerates the ID and silently accepts loss of linkage to prior `SubstepResponse` rows on the old ID. | Authoring preview needs IDs synchronously (the operator-mode preview pane mounts immediately on insert); backend round-trip per insert is wasted latency for zero correctness benefit. UUIDv7 matches the rest of the system. Cut-paste regenerating IDs reflects the author's intent ("this is a new thing now"). |
| 19 | Mid-execution persistence | **Batch-on-complete.** All operator captures (`SubstepResponse` / `SubstepGateCompletion` / `SubstepCompletion`) stay in client memory while the operator works through the substep, then post in one transaction when **Complete Substep** is hit. Exceptions: photos / files upload eagerly to the existing `Documents` API (returns `document_id`, which lives in client state until batch); `Timer` captures finalize on Stop and batch on Complete. **Complete Substep waits for any in-flight uploads** (button shows a spinner; batch posts only when all `document_id`s exist server-side) — avoids dangling FK references with no reconciliation logic. Close-without-complete discards local state — no partial-substep resume in v1; this is an **authoring constraint**: engineers should size substeps so a typical interruption (5–10 minutes) doesn't represent meaningful work loss. | Simpler client state, atomic server transaction, one server-side validation pass via `can_complete_substep()`, consistent with the v1 "online-only" known limitation. Mid-substep tablet death loses captures — acceptable trade-off matched to existing scope. The "wait for uploads" rule for photo/file is the simplest correct behavior; the alternative (server-side reconciliation of pending document_ids) is more code for no operational benefit. |
| 20 | Authoring popover pattern | **Hover gear icon → shadcn `Popover` → debounced `updateAttributes` (250ms).** Per-node popover components live at `src/components/dwi/nodes/{NodeName}/edit-popover.tsx`. Linked-spec autocomplete on `MeasurementInput` / `MeasurementSpec` queries `MeasurementDefinition` rows in the tenant; picking one autofills label / unit / nominal / tolerances / characteristic via one atomic `updateAttributes` call. Popovers used uniformly across node types (no Sheet hybrid for big nodes — vertical scroll handles `ComputedValue`). Operator mode (`editable: false`) suppresses the gear entirely. | Hover-gear is predictable, doesn't fight selection/drag UX, matches Notion/Linear idioms. Debounced live-update keeps undo history sane vs. per-keystroke transactions. Per-node components stay simple — 12 nodes is a fixed surface, generic schema-driven form isn't worth the abstraction. Linked-spec picker eliminates re-keying for shops with established spec libraries. |
| 21 | Measurement data tier separation | **Two tiers, two writers.** DWI numeric captures (`MeasurementInput`) write to **`StepExecutionMeasurement`** (process data — feeds step-advancement gating + SPC after adapter update). When the parent substep has **`is_inspection_point=True`**, the capture service additionally creates `QualityReports` + `MeasurementResult` (inspection record — triggers `record_quality_report_side_effects`: auto-quarantine, `ncr.opened` notification, sampling fallback, NCR audit chain). No auto-promotion of routine captures. Engineer decides at authoring time which substeps are binding inspection events (FAI, hold-points, final inspection); most substeps are False. | Established MES/QMS systems (Plex, SAP QM with PP-PI, Aegis FactoryLogix, Siemens Opcenter, iBASEt) all separate process data from inspection records as first-class concepts. AS9100 §8.5.1 and 21 CFR 820.80 treat them as separate activities — the latter requires documented acceptance authority, the former does not. Auto-promoting every inline capture to a QualityReport would (a) cause auto-quarantine on routine setup adjustments, (b) generate notification spam to QA Manager that destroys the channel's signal-to-noise, and (c) dilute the audit meaning of "quality report" (an auditor reading "this lot had 847 quality reports" is reading garbage). The promotion flag on the substep keeps the meaning sharp. |

---

## Milestones (happy-path demo targets)

Implementation is structured around two end-to-end happy-path scenarios. Each milestone defines a concrete demoable user journey that exercises every architectural decision relevant to that phase. Feature ordering *within* each phase is driven by what the milestone needs.

### Milestone 1 — General Manufacturing (DWI core)

> Engineer authors "OD Turn — Spacer P/N 11782-3" with 3 substeps:
> 1. **Setup OD offsets** — `TextInput` (lot #) + `ScanInput` (tool barcode) + `AttestationCheckpoint` (cert verified)
> 2. **First piece + measure** — `MeasurementInput` linked to a `MeasurementDefinition` row; spec language renders in-spec / out-of-spec badge live
> 3. **Final inspection** — `PhotoCapture` + `AttestationCheckpoint(kind='signature')`
>
> Engineer submits the `ProcessStep` for approval → QA Manager approves → operator at the CNC workstation picks the WO from their queue → works through the 3 substeps in the substep editor → `MeasurementInput` captures persist to `StepExecutionMeasurement` → out-of-spec reading triggers the existing CAPA auto-create → WO advances.

**Architectural decisions this exercises:**

- Two-editor authoring + operator-view pattern (decision #12)
- Custom-node library with structured attrs (Editor & Custom Node Library section)
- Authoring popover (decision #20) including `MeasurementDefinition` autocomplete
- Spec language for measurements (`nominal` / `upper_tol` / `lower_tol`)
- Substep completion contract (per-node preconditions, scroll-to-blocked UX)
- Batch-on-complete persistence (decision #19)
- Author≠approver enforcement (decision #17)
- Per-Step approval workflow (decision #15)
- Permission model (Engineering authors, QA approves, Operator executes)
- Closed-loop measurement → SPC → CAPA pipeline (existing infrastructure)

**Required phases:** DWI Phase 1 + 2 + 3 + 4 (all four). No Reman phases.

**Required reman work:** none. Milestone 1 ships entirely on the DWI core.

### Milestone 2 — Reman Teardown (lighthouse vertical)

> Engineer authors "Teardown 6.7L Cummins injector" with 3 substeps:
> 1. **External inspection** — `PhotoCapture` + `ChoiceInput` (condition grade)
> 2. **Disassemble + harvest** — `HarvestedComponentCapture` node enumerates expected components from `DisassemblyBOMLine` for the core type
> 3. **Final sign-off** — `AttestationCheckpoint(kind='signature')`
>
> Engineer submits for approval → QA approves → operator opens a received Core → "Start Teardown" action creates the teardown WO and links the Core → operator works through the 3 substeps → `HarvestedComponent` rows persist with FK to Core → WO closes, Core transitions DISASSEMBLED.

**Additional architectural decisions this exercises (beyond M1):**

- `StepExecution.core` two-FK extension (Reman decision R2)
- Core flow through Steps (`Core.step` + `advance_core_step`, Reman decision R3)
- Auto-coordinate Core lifecycle with WO state (Reman decision R5)
- `start_teardown` service (Reman decision R6)
- `HarvestedComponentCapture` custom node (Reman decision R7)
- Per-unit storage philosophy (Reman decision R1) — each Core in a teardown batch has its own `StepExecution`

**Required phases:** Milestone 1 complete + Reman R1 + R2 + R3 + R4.

**Parallelism opportunity:** Reman R1–R3 can ship in parallel with DWI Phase 1–3 (R1 is fully independent of substep models). R4 (`HarvestedComponentCapture`) is the convergence point — needs both DWI substep machinery and `StepExecution.core` to land before it can build. If solo, ship M1 fully first; if parallel capacity, run a reman track alongside.

### Sequencing summary

```
DWI Phase 1 → 2 → 3 → frontend editor → Phase 4    → Milestone 1 demo
                                                          ↓
                                          Reman R1 → R2 → R3 → R4 → Milestone 2 demo
                                                          (R1 can start any time after DWI Phase 1)
```

### Frontend route placement for the substep editor

Per the URL convention captured in `CLAUDE.md` (lowercase + kebab-case + nested under a domain prefix):

```
/editor/processes/$processId/steps/$stepId/substeps          ← substep list + editor for a step
/editor/processes/$processId/steps/$stepId/substeps/$substepId ← single-substep detail/edit (if needed)
```

`/editor/` matches the existing process-editor surface (`/editor/processes`, `/editor/milestones`, `/editor/groups/$id`). Nesting under `processes/$processId/steps/$stepId` matches the data model — substeps belong to steps, which belong to a process version. Operator-side execution UX is a separate workstream and lives nested under work-order routes, not the editor namespace.

---

## Editor & Custom Node Library

### Library choice: raw TipTap

The editor is built on **`@tiptap/react`** + **`@tiptap/starter-kit`** (MIT). All custom blocks for DWI-specific content (measurement specs, callouts, attestations, signature gates, etc.) are written as TipTap custom nodes inside this project — not pulled from a third-party wrapper.

A wrapper library — `reactjs-tiptap-editor` — was evaluated. Rejected for these reasons:

- The library ships its own bundled `@tailwind base` reset in its `style.css` and consumes shadcn theme variables in the classic Tailwind 3 `hsl(var(--name))` HSL-channel-triple convention.
- This project uses Tailwind 4 / new shadcn convention where the same variable names hold full color values in `oklch()`. The two formats are mutually invalid.
- Theme leakage is a documented, recurring, unresolved bug in the library — issues #196, #263, #290 each closed with no fix, labeled `pr-welcome`.
- The library's "Pro" features (Word import/export, PDF export) wrap libraries we already control (`mammoth`, `docx`, `html2pdf.js`) — direct integration is cleaner than adopting the wrapper.
- Custom-node authoring is the dominant cost regardless of which wrapper is chosen.

Net: building directly on the TipTap primitives is less code, fewer integration conflicts, and zero vendor dependency on a single-maintainer wrapper.

### Document JSON shape

`Substep.body_blocks` stores a TipTap document — `{ "type": "doc", "content": [...] }` — produced via `editor.getJSON()` and loaded via `editor.commands.setContent()`. The same JSON is consumed by `generateHTML(json, extensions)` from `@tiptap/html` for non-interactive renders (PDFs, email, search indexing).

The `JSONField(default=list)` default is preserved for backward compatibility, but consumers must accept the doc-shaped object at runtime.

### Custom node library

The DWI-specific blocks below are built as TipTap custom nodes (`Node.create({ ... })` + `ReactNodeViewRenderer`). Each node's attrs schema matches the corresponding Django model field names where applicable, so the editor JSON round-trips cleanly with persistent state.

**Content nodes (display-only, no operator state):**

| Node | Purpose | Notes |
|---|---|---|
| `Callout` | Caution / Note / Reminder / Safety boxes | One node with `variant` attr; collapses Dozuki's four bullet variants |
| `Media` | Image / video / 3D-model embed (author-supplied) | `src` URL references `Documents` storage; multiple allowed (Dozuki caps at 3 images + 1 video, we don't) |
| `MeasurementSpec` | Passive reference to a target measurement | Attrs match `MeasurementDefinition` shape; ✅ **built in spike** |
| (StarterKit content) | Headings, paragraphs, lists, blockquote, code, hr, marks | ✅ built |

**Capture nodes (write to per-execution storage):**

| Node | Captures into | Notes |
|---|---|---|
| `AttestationCheckpoint` | `SubstepGateCompletion` (new lightweight model) | `kind: 'confirm' \| 'signature'`; required flag gates substep completion |
| `MeasurementInput` | `StepExecutionMeasurement` (always) + `QualityReports` + `MeasurementResult` (when `substep.is_inspection_point=True`) | Optional FK to `MeasurementDefinition`; range validation via existing model. Routine captures land as process data only — operator can adjust offsets and re-measure without tripping NCR notifications or auto-quarantine. Inspection-point substeps (FAI, hold-points, final) additionally create an inspection record, which fires `record_quality_report_side_effects()` (auto-quarantine on out-of-spec, `ncr.opened` notification to QA Manager, sampling fallback). See architectural decision #21. |
| `TextInput` | `SubstepResponse` (new lightweight model) | `kind: 'short' \| 'long'` covers Dozuki's Text + Multi-line |
| `ChoiceInput` | `SubstepResponse` | `kind: 'radio' \| 'select'` covers Dozuki's Radio + Drop-Down |
| `PhotoCapture` | `Documents` (FK on response row) | Operator-uploaded image |
| `VideoCapture` | `Documents` (FK on response row) | Operator-uploaded video (rare; defer) |
| `ScanInput` | `SubstepResponse` (kind: 'short' text) | Convenience alias for `TextInput` with HID-wedge hint; operator sees barcode-icon UX |
| `FileCapture` | `Documents` (FK on response row) | Operator-supplied file of any MIME type — CAD, PDF, datasheet, measurement spreadsheet. Sibling to `PhotoCapture` / `VideoCapture` without the format restriction. |
| `Timer` | `SubstepResponse` (kind: `'timer'`) | Hybrid display/capture node. Engineer sets `duration_seconds` and `direction: 'countdown' \| 'stopwatch'` (e.g., "wait 30s for cure" vs. "time how long this takes"). Operator clicks Start; node tracks `{started_at, completed_at, elapsed_seconds}` to the response store. Useful for cure times, dwell times, and any "wait N seconds before next step" pattern that's common in shop-floor procedures. |
| `ComputedValue` | `SubstepResponse` (kind: `'computed'`); raw inputs also writable to `StepExecutionMeasurement` rows if linked to a `MeasurementDefinition` | Variables-plus-formula node for shop-floor calculations (True Position, Concentricity, Runout, Mean, etc.). Engineer declares N variables `[{name, label, unit}]` and a formula string referencing them by name (`2 * sqrt(X^2 + Y^2)`). Operator sees one numeric input per variable; result evaluates live via `expr-eval` **wrapped in a ~100ms execution cap** (pathological formulas — runaway recursion, exponential blowups — return `null` + an error badge instead of locking the tablet). Spec check uses the same `nominal` / `upper_tol` / `lower_tol` language as `MeasurementInput` — in-spec iff `result ∈ [nominal - (lower_tol ?? ∞), nominal + (upper_tol ?? ∞)]`. Common spec shapes: True Position (positive-only max) → `nominal=0, upper_tol=N, lower_tol=0`; symmetric bilateral (`X ± tol`) → `nominal=X, upper_tol=tol, lower_tol=tol`; unilateral upper (≤ X) → `nominal=0, upper_tol=X, lower_tol=null`. `display_precision` attr controls result decimal places. Captured response: `{inputs, result, in_spec}`. One node type covers infinite calcs — no preset catalog to maintain. Ship with a starter template library (True Position, Concentricity, Runout, Mean, Diameter-from-radius, etc.) so engineers can click-to-pre-fill instead of memorizing formulas. |

`MeasurementSpec` (listed under content nodes above) is the read-only sibling of `MeasurementInput` — one shows the target tolerance, the other captures the actual reading. They're commonly used together in a substep: one block displays the spec, the next captures the operator's measurement.

Each capture node carries a stable `node_id` attribute (via `@tiptap/extension-unique-id` or assigned at creation time) so the per-execution response row can be joined back to the specific node in the document.

### Mapping to Dozuki's vocabulary

Reference for product comparison. Dozuki splits a step into a **content zone** (bullets + images + video) and a **form zone** (drag-drop data capture fields). Our approach interleaves both freely inline. See `apidocs.dozuki.com/Help/Guide_Steps` and `Help/Data_Capture` for the canonical Dozuki vocabulary.

| Dozuki primitive | Our node |
|---|---|
| Default / Caution / Note / Reminder bullets | `Callout` (variant) + StarterKit paragraph/list |
| Author-embedded image / video | `Media` |
| Visual callouts (image markup) | Existing `HeatMapAnnotations` + `PartAnnotator` (our edge) |
| Step title | StarterKit heading |
| Hierarchical bullet nesting | StarterKit nested lists |
| Text Input / Multi-line Text Field | `TextInput` |
| Numeric Input | `MeasurementInput` |
| Checkbox | `AttestationCheckpoint` (kind: confirm) |
| Radio Button / Drop-Down | `ChoiceInput` |
| Image Input / Video Input | `PhotoCapture` / `VideoCapture` |
| Work Order # | Captured at WO level already — no node |
| Supervisor Sign-Off | `AttestationCheckpoint` (kind: signature) + role gate |
| Stage-gated workflow | Service-layer `can_complete_op()` gating |
| Deviation escalation | `StepExecutionMeasurement` auto-eval + notifications subsystem |

Our advantages on top: native decision-point branching at the step graph (`Steps.is_decision_point`), 3D model annotation, tables, headings beyond a single step title.

### Editing UX for custom nodes

Per architectural decision #20:

- **Engineer authoring** (editable: true): hovering a capture node reveals a small gear icon (top-right of the card). Click opens a shadcn `Popover` anchored to the node containing the attr-edit form. Form fields write via `updateAttributes` from `NodeViewProps` with a 250ms debounce (one undo entry per logical edit, not per keystroke).
- **Operator running step** (editable: false): same card renders; capture nodes show the interactive form field. The hover gear is suppressed entirely. Operator clicks route to the per-execution response store via parent context, never into the document JSON.

**Popover structure conventions:**

- One popover component per node type, located at `src/components/dwi/nodes/{NodeName}/edit-popover.tsx`. Twelve nodes is a fixed surface; a generic schema-driven form isn't worth the abstraction overhead.
- Form uses `@tanstack/react-form` (project standard).
- Text and decimal inputs use local-state-plus-resync pattern: local `useState` for the raw input value (so cursor position and trailing-decimal characters like `"0."` survive), `useEffect` resyncs from `node.attrs.*` when external writes update the attr (e.g. linked-spec autofill below).
- Popovers used uniformly across node types; the larger ones (`ComputedValue`, `MeasurementInput` with full spec) scroll vertically. Sheet-hybrid layout was considered and rejected — inconsistent affordances are a real UX cost; the scroll is cheap.
- `Popover.onOpenAutoFocus={(e) => e.preventDefault()}` prevents the popover from stealing focus from the surrounding ProseMirror editor.

**Linked spec autocomplete** (decision #20): `MeasurementInput` and `MeasurementSpec` popovers expose an autocomplete that queries `MeasurementDefinition` rows scoped to the authoring engineer's tenant. Picking a definition fires one atomic `updateAttributes` call that fills label / unit / nominal / upper_tol / lower_tol / characteristic_number and stores the FK as `measurement_definition_id`. The engineer can still author inline (leaving the FK null) when they need a one-off spec that isn't in the library. This eliminates re-keying for shops with established spec libraries — the dominant authoring pattern in aerospace / medical / auto suppliers.

Spike validating the pattern lives at the `/dwi-spike` route — see `ambac-tracker-ui/src/pages/DwiSpikePage.tsx`. To be deleted after the production substep editor is wired up.

---

## Data Model

### New Models

#### `Substep`

```python
class Substep(SecureModel):
    step = ForeignKey('Steps', related_name='substeps')           # parent Op
    order = PositiveIntegerField()                                # within the Op
    title = CharField(max_length=200)
    body_blocks = JSONField(default=list)                         # TipTap document JSON — see "Editor & Custom Node Library" above for shape and node vocabulary
    is_optional = BooleanField(default=False)                     # operator may mark N/A
    requires_signature = BooleanField(default=False)              # final operator sign-off on substep completion (distinct from inline AttestationCheckpoint gates — see note below)
    is_inspection_point = BooleanField(default=False)             # MeasurementInput captures within this substep additionally create inspection records (QualityReports + MeasurementResult). Default False = process data only. Set True for FAI, in-process hold-points, final inspection. See decision #21.
    expected_duration = DurationField(null=True, blank=True)      # mirrors Steps.expected_duration at substep granularity
    # Sampling-driven applicability (substep-level sampling)
    sampling_rule = ForeignKey('SamplingRule', null=True, blank=True, on_delete=SET_NULL)
    # null = substep always applies to every part visiting the step
    # set  = substep only applies when this rule selects the visiting part
    # Provenance (for future LibrarySubstep; nullable always)
    source_library_substep_id = PositiveIntegerField(null=True)   # forward-compatible
    source_library_version = PositiveIntegerField(null=True)
```

Versioning: substeps participate in the parent Process version. New versions are created via `Processes.create_new_version()` per existing versioning architecture.

**`requires_signature` vs. inline signature gates.** Two distinct mechanisms, used for different purposes:

- **`Substep.requires_signature=True`** — operator must sign once *at substep completion* as a final acknowledgment that the whole substep is done. Stored on `SubstepCompletion.signature_data`. Typical use: FAI substep ("I performed the first-piece inspection"), critical step completion ("I confirm the part is ready to release").
- **Inline `AttestationCheckpoint(kind='signature')` nodes** — operator signs *at a specific point inside the substep* before they can proceed past that point. Stored on `SubstepGateCompletion` keyed by `node_id`. Typical use: multiple checkpoints within a long procedure ("I verified the tool offset"; later: "I verified the bar stock material cert"; later: "I verified the spindle is clean").

A substep can have neither, one, the other, or both. They don't overlap — different storage rows, different intent.

The `sampling_rule` FK points at a specific `SamplingRule` row (the same model the existing `Part.sampling_rule` references). The FK pattern mirrors `Part.sampling_rule` — substeps and parts both reference rules by their leaf row, and `SamplingRule.ruleset` provides the ruleset context transitively when needed. Ruleset versioning rides on the existing Process-level versioning: when a new Process version is created via `create_new_version()`, the engineer re-picks the rule from the active ruleset for that version. Older Process versions keep their FKs to the prior rule rows because the existing versioning architecture preserves old records.

#### `SubstepCompletion`

```python
class SubstepCompletion(SecureModel):
    step_execution = ForeignKey('StepExecution', related_name='substep_completions')
    substep = ForeignKey('Substep')
    completed_by = ForeignKey('User')
    completed_at = DateTimeField(auto_now_add=True)
    marked_not_applicable = BooleanField(default=False)           # only valid if substep.is_optional
    notes = TextField(blank=True)

    # Signature capture (reuses ApprovalResponse / CapaTasks pattern)
    signature_data = TextField(null=True, blank=True)             # Base64 PNG
    signature_meaning = CharField(max_length=200, null=True, blank=True)
    verified_at = DateTimeField(null=True, blank=True)
    verification_method = CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        default=VerificationMethod.NONE,
    )
    ip_address = GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = [('step_execution', 'substep')]
```

#### `SubstepResource`

```python
class SubstepResource(SecureModel):
    substep = ForeignKey('Substep', related_name='resources')
    equipment_type = ForeignKey('EquipmentType', null=True)
    material_type = ForeignKey('MaterialType', null=True)         # when MaterialType exists
    ppe_type = ForeignKey('PPEType', null=True)                   # when PPEType exists
    quantity = DecimalField(null=True)
    notes = CharField(max_length=200, blank=True)
    required = BooleanField(default=True)
    # Exactly one of equipment_type/material_type/ppe_type must be set (CheckConstraint)
```

#### `SubstepGateCompletion`

Per-node operator state for `AttestationCheckpoint` nodes. Storing this separately from `SubstepCompletion` lets a single substep have multiple required gates, each with its own completion record.

```python
class SubstepGateCompletion(SecureModel):
    step_execution = ForeignKey('StepExecution', related_name='gate_completions')
    substep = ForeignKey('Substep')
    node_id = CharField(max_length=64)                            # stable ID assigned to the node in body_blocks
    completed_by = ForeignKey('User')
    completed_at = DateTimeField(auto_now_add=True)
    # Signature pattern (reused when the gate node's kind == 'signature')
    signature_data = TextField(null=True, blank=True)
    signature_meaning = CharField(max_length=200, null=True, blank=True)
    verification_method = CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        default=VerificationMethod.NONE,
    )
    ip_address = GenericIPAddressField(null=True, blank=True)

    class Meta:
        unique_together = [('step_execution', 'substep', 'node_id')]
```

#### `SubstepResponse`

Generic per-node operator state for `TextInput`, `ChoiceInput`, and any future free-form capture node. Numeric measurement responses go through `StepExecutionMeasurement` (existing) instead — this table is for non-numeric responses.

```python
class SubstepResponse(SecureModel):
    step_execution = ForeignKey('StepExecution', related_name='substep_responses')
    substep = ForeignKey('Substep')
    node_id = CharField(max_length=64)                            # stable ID on the source node
    kind = CharField(max_length=20)                               # 'text' | 'choice' | 'photo' | 'video' | 'scan' | 'file' | 'timer' | 'computed'
    value_text = TextField(blank=True)                            # text / scan / chosen option key
    value_document = ForeignKey('Documents', null=True, blank=True) # photo / video / generic file upload
    responded_by = ForeignKey('User')
    responded_at = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('step_execution', 'substep', 'node_id')]
```

The `unique_together` assumes one operator records per node per execution. See Still Open for the team-based-step relaxation question.

#### `SubstepTranslation`

```python
class SubstepTranslation(SecureModel):
    substep = ForeignKey('Substep', related_name='translations')
    language = CharField(max_length=10)                           # BCP 47 (e.g. 'en', 'es-MX')
    title = CharField(max_length=200)
    body_blocks = JSONField(default=list)
    class Meta:
        unique_together = [('substep', 'language')]
```

### Modified Models

#### `Steps` — add ordering mode

```python
class SequencingMode(models.TextChoices):
    SEQUENTIAL = 'sequential', 'Sequential'
    FREE_ORDER = 'free_order', 'Free order'

sequencing_mode = CharField(choices=SequencingMode.choices, default=SequencingMode.SEQUENTIAL)
```

#### `StepExecutionMeasurement` — link to substep

```python
substep = ForeignKey('Substep', null=True, blank=True)            # optional; null = Op-level
```

#### `StepMeasurementRequirement` / `StepRequirement` — link to substep

Same pattern: nullable `substep` FK, null means the gate applies at Op level.

#### `ProcessChangeRequest` — add substep target

```python
target_process = ForeignKey('Processes', null=True, blank=True)   # may exist already
target_step = ForeignKey('Steps', null=True, blank=True)          # may exist already
target_substep = ForeignKey('Substep', null=True, blank=True)     # new
# CheckConstraint: exactly one of the three is non-null
```

#### `Processes` — approval template override

```python
approval_template = ForeignKey(
    'ApprovalTemplate', null=True, blank=True, on_delete=SET_NULL,
    related_name='processes_using_template',
)
# null = fall through to PartType / tenant default; see "Authoring Approval Workflow"
```

#### `PartTypes` — approval template override

```python
approval_template = ForeignKey(
    'ApprovalTemplate', null=True, blank=True, on_delete=SET_NULL,
    related_name='part_types_using_template',
)
# null = fall through to tenant default
```

#### `ProcessStep` — per-Step approval state

```python
class StepApprovalStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
    APPROVED = 'APPROVED', 'Approved'

approval_status = CharField(
    max_length=20, choices=StepApprovalStatus.choices,
    default=StepApprovalStatus.DRAFT,
)
approval_request = ForeignKey(
    'ApprovalRequest', null=True, blank=True, on_delete=SET_NULL,
    related_name='process_step_approvals',
)
approved_at = DateTimeField(null=True, blank=True)
```

#### `ApprovalTemplate` — relax uniqueness + add default flag

```python
is_default = BooleanField(default=False)
# Tenant default for its approval_type. One per (tenant, approval_type).

# Relax the existing unique_together from (tenant, approval_type)
# to (tenant, approval_type, name) so per-Process / per-PartType
# override templates can coexist with the default.
```

Migration: add `is_default`, change the unique constraint. Backfill: existing single template per (tenant, approval_type) becomes `is_default=True`.

#### `ProcessChangeNotice` — no new fields

In-flight WorkOrder handling is already covered by the existing
`ProcessChangeMigrationDisposition` enum (`change_control.py:47`) and the
PCO implementer's migration choice at PCO implementation time (see
`services/change_control/impact_analysis.py`). Substeps ride along with
their parent Process version; no separate substep-level in-flight policy
is needed.

---

## Execution Semantics

### Snapshot at start

When `StepExecution` transitions to `in_progress`, the service layer materializes substep references for that execution. Substeps themselves are not duplicated — `SubstepCompletion` rows are created lazily as the operator works. The Process version pinned to the `StepExecution` (via parent Process version on the work order) determines which substep version the operator sees.

At this same transition, the service evaluates each substep's `sampling_rule` (where set) against the current part — see "Sampling integration" below — and caches the per-substep applicability outcome on the `StepExecution` so the operator UI knows which substeps are live for this visit. The cached outcome is the only per-execution sampling state; substep templates themselves are read directly from the pinned Process version.

### PCN propagation policy

In-flight work is handled by the existing PCO implementation flow
(`services/change_control/impact_analysis.py` + `ProcessChangeMigrationDisposition`):

- `KEEP_ALL`: in-flight WOs continue against the version they started; subsequent WOs use the new version. Existing `SubstepCompletion` rows are untouched.
- `MIGRATE_ALL`: in-flight WOs are migrated to the new Process version per existing migration logic. New `SubstepCompletion` rows on the new version are created from that point; the substep-design layer does not add new behavior here.
- `MIGRATE_SELECTED`: implementer chooses per-WO; substeps follow the WO's disposition.

No mid-execution version switch ("IMMEDIATE") is supported — by design.
The migration is always at WorkOrder boundaries, never mid-Op.

**Substep completions across PCN migration.** When an in-flight WO migrates to a new Process version under `MIGRATE_ALL`, existing `SubstepCompletion` rows reference the **old** substep version. Those rows are never deleted — `SecureModel.hard_delete()` is explicitly disabled platform-wide (`core.py:1121`, "permanent deletion requires retention policy system with legal hold support"). The old completions persist as historical records; the new Process version's substep rows accumulate new completions from the migration point forward. No FK rewrite or completion-mapping is required; the historical chain is preserved by the soft-delete-only policy.

### Sequencing enforcement

- `SEQUENTIAL`: service layer rejects a `SubstepCompletion` for substep N if substep N-1 has no completion (or is optional and not yet marked N/A). Substep-scoped measurement gates (`StepMeasurementRequirement.substep` set) also block at substep completion time — operator can't proceed past a substep with an unsatisfied measurement requirement.
- `FREE_ORDER`: any substep may be completed in any order. Substep-scoped measurement gates block at Op completion only (no per-substep enforcement, since prerequisite ordering isn't meaningful here). Op signoff checks that all required (i.e. `not is_optional`) substeps have completions and that all gate requirements are satisfied.

### Substep completion contract

Per architectural decision #19, all operator captures for a substep are held in client memory and posted as a single transaction when the operator hits **Complete Substep**. The server runs `can_complete_substep()` against the batch payload before persisting.

`can_complete_substep(step_execution_id, substep_id, payload) -> tuple[bool, list[CompletionBlock]]` walks the substep's `body_blocks`, identifies every required capture / gate node, and verifies the matching response exists in the payload. Return shape:

```python
@dataclass(frozen=True)
class CompletionBlock:
    node_id: str | None   # which node blocks (None for substep-level blocks)
    kind: str             # "missing_required_value" | "missing_signature" | "incomplete_timer" | etc.
    label: str            # human-readable label for the operator UI
```

**Per-node preconditions (only enforced when the node has `required: true`):**

| Node type | Block unless... |
|---|---|
| `AttestationCheckpoint(kind='confirm')` | response value === `true` (checkbox checked) |
| `AttestationCheckpoint(kind='signature')` | response value is non-empty signature data |
| `MeasurementInput` | response value parses to a finite number |
| `TextInput` | `value.trim().length > 0` |
| `ChoiceInput` | response value is one of the declared options |
| `PhotoCapture` / `FileCapture` | response `value_document` FK is set (upload succeeded) |
| `ScanInput` | `value.trim().length > 0` |
| `Timer` | response has both `started_at` AND `completed_at` |
| `ComputedValue` | all declared variables have finite numeric values AND formula evaluates to a finite result |

**Substep-level gates:**

| Gate | Condition |
|---|---|
| `Substep.requires_signature=True` | Operator signature data submitted with the `SubstepCompletion` payload |
| `Substep.is_optional=True`, marked N/A | Skips all node-level checks; `marked_not_applicable=True` on the completion |
| `SEQUENTIAL` sequencing | Prior substep complete or marked N/A — checked at step level |

**Explicit non-gates** (do *not* block completion):

- **Out-of-spec readings** on `MeasurementInput` or `ComputedValue` do not block substep completion. Operator captured honestly; downstream SPC / quality pipeline handles disposition. Engineers who need "supervisor disposition before proceeding on out-of-spec" author a separate `AttestationCheckpoint(kind='signature')` gated by the deferred Level-2 `applies_when` SPC-state condition. **Special case for `substep.is_inspection_point=True`** (per decision #21): an out-of-spec reading at an inspection-point substep still doesn't block completion, but it does fire the inspection pipeline — auto-quarantines the part (`PartsStatus.QUARANTINED`), emits `ncr.opened` to QA Manager, triggers sampling fallback. The substep can still be marked complete (operator captured the truth), but the part is now flagged for QA review. This is the audit-defensible behavior for binding inspection points: capture is honest, but the part can't ship until QA reviews.
- **Optional substeps with no captures** — by definition skippable.
- **Substeps the sampling rule excluded** — never reach the completion check; their applicability is cached on the `StepExecution` at part entry.

**Error UX** (client-side, mirrors the server contract): the "Complete Substep" button stays enabled; clicking when blocked scrolls to the first blocked node, highlights it, and shows the `CompletionBlock.label` inline. A banner above the button shows the count of blocked nodes. Disabling the button creates a "why can't I click this?" UX trap; visible feedback on click is clearer.

### Part-level divergence

Already handled by existing primitives. The DWI design doesn't add or modify step-graph mechanics here.

- **Per-step batch flag**: `Steps.requires_batch_completion` (default False) controls whether the lot moves as a unit. When True, every part stops at `READY_FOR_NEXT_STEP` until the lot satisfies `Steps.can_advance_step()` — which checks the `pass_threshold` ratio of ready parts, quarantine state, QA signoff, and FPI status (`mes_lite.py:616`). When False, each part advances independently.
- **Per-step pass threshold**: `Steps.pass_threshold` (default 1.0) lets you advance the batch when N% of parts are ready, tolerating stragglers (`mes_lite.py:388`).
- **Per-step quarantine block**: `Steps.block_on_quarantine` halts the batch if any part is quarantined (`mes_lite.py:405`).

**For reman**: set `requires_batch_completion=False` on divergent steps. Parts move independently. The existing decision-point routing (`is_decision_point=True` + `StepEdge` with `ALTERNATE` edge type) sends each part down its own path based on inspection outcomes recorded against that part. The `Part.step` field is the canonical "where is this part right now."

**What's actually missing for clean reman DWI** is not in the step-graph layer:

1. **Conditional substep applicability** — needed so an engineer can author "if teardown finds scored bearing race, apply the regrind substep; else skip." Deferred per architectural decision #11; sketched as the Level-2 mechanism in Deferred Items.
2. **Per-part visualization** — operator views, traveler views, and WO progress indicators need to clearly communicate "8 cores at 8 different steps." Data exists (`Part.step`); UX work is separate from this doc.

### Sampling integration

Sampling fires at two layers and uses the existing sampling subsystem (`SamplingRuleSet`, `SamplingRule`, `SamplingFallbackApplier`, `SamplingAuditLog` — `mes_standard.py:349+`, `services/mes/sampling_applier.py`).

**Substep-level sampling** — in-line check at the same workstation. The operator stays at the machine; a substep (typically a `MeasurementInput` capture) fires only when the sampling rule selects this part.

- Modeled via `Substep.sampling_rule` FK to `SamplingRule` (nullable; null = always applies). Mirrors the FK pattern on `Part.sampling_rule` — substep references the leaf rule row, ruleset is reached transitively via `SamplingRule.ruleset`.
- Applies primarily to discrete-tracking WOs (`is_batch_work_order=False`). Lot-tracking WOs (`is_batch_work_order=True`, e.g. high-volume extruder runs without per-piece identity) use different sampling semantics that are out of scope for DWI.
- Evaluated on **per-part step entry** — when a part enters a step (whether via batch advance for synchronized lots or individual advance for divergent flows), the service walks the step's substeps and evaluates each substep's `sampling_rule` against the part. Result is cached on the `StepExecution` so the operator UI knows which substeps to show.
- Evaluator extension: `SamplingFallbackApplier` already has `_should_sample(rule)` (private) that does single-rule matching. For substep evaluation, promote it to a public entry point — e.g. `should_apply_for_substep(part, substep) -> bool` that handles the "substep.sampling_rule is null → True" shortcut and otherwise delegates to the existing match logic.
- A skipped (non-sampled) substep does not block substep advancement — it's simply not applicable for this part's visit.
- Common case: "every 25th part, measure OD with the gauge."

**Step-level sampling** — operator brings the part to QC bench for inspection; the part stays at its work step until QC clears it. This is the **block-based model** already wired in the codebase (`Steps.sampling_required`, `Steps.can_advance_from_step` at `mes_lite.py:802`, `FPIRecord` at `qms.py:2134`).

- Part is marked `requires_sampling=True` at part creation by `SamplingFallbackApplier.evaluate()`
- `can_advance_from_step()` blocks advancement until a passing `QualityReport` exists
- FPI lot-blocking is implicit via `Steps.get_fpi_status(work_order).blocked_parts_count` (no explicit `lot_released_at` flag today)
- Part custody never changes — it pauses at its current step record while QC inspects in-place

**The two layers coexist on the same step.** A CNC Op can have substep-level "every-25th" in-line checks and step-level "FPI" blocking on the same Process version, driven by different rules.

**No new routing primitive is needed for sampling.** The block-based model matches the actual SMB shop-floor workflow (operator + QC do the inspection in-place, same part record, same step). Gate-based routing — where a sampled part would route to a separate `SAMPLING_GATE` Step node and then a `QC Bench` step — is **deferred** because the underlying "literal part diversion" flow it models doesn't exist for our customer base. See "Deferred Items" for the migration path if a future customer needs it.

---

## Authoring Approval Workflow

Engineers author substeps; the result must be approved before reaching the shop floor. Most of this rides on the existing approval subsystem (`ApprovalRequest` / `ApprovalResponse` / `ApprovalTemplate` in `core.py`) — the work is configuration plus a small amount of new state on existing models.

### Granularity: per-Step

Approval is targeted at the **`ProcessStep`** through-table row (the existing model that links Steps to Processes per version, at `mes_lite.py:ProcessStep`). When an engineer edits substeps belonging to one Step within a Process version, only that Step's `ProcessStep` row needs approval. Other Steps in the same Process version aren't gated by the change.

A Process version becomes fully active for operators only when **all** of its `ProcessStep` rows are in `APPROVED` state. Until then, in-flight WOs continue against the prior Process version per the existing `ProcessChangeMigrationDisposition` flow.

This gives reviewers Step-bounded diffs ("here's what changed in Op 3") and lets multiple Step approvals proceed in parallel when one Process version touches several Steps.

### State machine

`Processes.status` (DRAFT / PENDING_APPROVAL / APPROVED / DEPRECATED) stays as-is. Step-level approval state lives on the through-table:

```python
# Modified: ProcessStep
class ProcessStep(SecureModel):
    # ... existing fields (process FK, step FK, order, etc.) ...

    class StepApprovalStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'

    approval_status = CharField(
        max_length=20,
        choices=StepApprovalStatus.choices,
        default=StepApprovalStatus.DRAFT,
    )
    approval_request = ForeignKey(
        'ApprovalRequest',
        null=True, blank=True,
        on_delete=SET_NULL,
        related_name='process_step_approvals',
    )
    approved_at = DateTimeField(null=True, blank=True)
```

A Process version transitions to ACTIVE only when every `ProcessStep` in it is `APPROVED`. Service-layer helper:

```python
def try_activate_process_version(process: Processes) -> bool:
    """Activate the version if all its ProcessStep rows are APPROVED."""
    if process.process_steps.exclude(approval_status='APPROVED').exists():
        return False
    process.status = ProcessStatus.APPROVED
    process.save()
    # Existing migration handling for in-flight WOs runs here.
    return True
```

### Approval template resolution

The `ApprovalTemplate` for a given Step's approval is resolved by walking from most-specific to tenant default:

```python
def resolve_approval_template(process_step: ProcessStep) -> ApprovalTemplate | None:
    process = process_step.process
    if process.approval_template:
        return process.approval_template
    if process.part_type.approval_template:
        return process.part_type.approval_template
    return ApprovalTemplate.objects.filter(
        tenant=process.tenant,
        approval_type='PROCESS_APPROVAL',
        deactivated_at__isnull=True,
    ).first()
```

#### New / modified models for resolution

```python
# Modified: Processes
class Processes(SecureModel):
    # ... existing fields ...
    approval_template = ForeignKey(
        'ApprovalTemplate',
        null=True, blank=True,
        on_delete=SET_NULL,
        related_name='processes_using_template',
        help_text="Override default approver routing for this specific Process.",
    )

# Modified: PartTypes
class PartTypes(SecureModel):
    # ... existing fields ...
    approval_template = ForeignKey(
        'ApprovalTemplate',
        null=True, blank=True,
        on_delete=SET_NULL,
        related_name='part_types_using_template',
        help_text="Override default approver routing for processes producing this part type.",
    )
```

The existing `ApprovalTemplate` uniqueness constraint may need to be relaxed (it's currently `unique on (tenant, approval_type)` per the agent's report) so a tenant can have multiple `PROCESS_APPROVAL` templates — one default plus per-Process / per-PartType overrides referenced via the FKs above. Confirm during implementation; one option is to add a `name` field and key on `(tenant, approval_type, name)` instead, marking one as `is_default=True`.

### Service layer

New module: `Tracker/services/mes/authoring_approval.py` (lives under `mes/` per the canonical service-layer locations in `CLAUDE.md` — no new top-level service dir is introduced).

```python
def submit_step_for_approval(process_step_id, requester_id) -> ApprovalRequest:
    """Create an ApprovalRequest targeting this ProcessStep."""
    # Resolves template, creates ApprovalRequest with content_object=ProcessStep,
    # updates ProcessStep.approval_status = PENDING_APPROVAL, stores FK,
    # delegates to existing services.core.approval.create_approval_from_template().

def on_step_approval_decision(approval_request, decision):
    """Hook from the ApprovalResponse signal — wraps existing approval cascade."""
    # On APPROVED: set ProcessStep.approval_status=APPROVED, approved_at=now,
    #              then call try_activate_process_version(process).
    # On REJECTED: set ProcessStep.approval_status=DRAFT, clear approval_request FK.

def withdraw_step_approval(process_step_id, requester_id):
    """Cancel a pending approval request and return the ProcessStep to DRAFT."""
```

The signal hook ties into the existing `update_approval_status_on_response()` signal at `signals.py:118` — when an `ApprovalResponse` flips an `ApprovalRequest` to APPROVED/REJECTED, the cascade routes to `on_step_approval_decision()` if the content_object is a `ProcessStep`.

### Default template seeding

New tenants get a default `PROCESS_APPROVAL` `ApprovalTemplate` seeded by `GroupSeeder.seed_for_tenant()` (or a sibling `setup_approval_templates` management command):

- `approval_type = 'PROCESS_APPROVAL'`
- `default_groups = [QA Manager, Production Manager]`
- `approval_flow_type = ALL_REQUIRED`
- `sequence_type = PARALLEL`
- `default_due_days = 5`
- `is_default = True` (new flag — see template uniqueness note above)

Customers can edit this template via the existing approval template editor UI, or create overrides attached to specific PartTypes / Processes.

### Frontend touchpoints

1. **Substep editor for a Step** — sticky banner showing approval state (DRAFT / PENDING_APPROVAL / APPROVED); when DRAFT, surfaces a "Submit for Approval" button hooked to `submit_step_for_approval`. Once PENDING_APPROVAL or APPROVED, edit fields are read-only (a new Process version is required to make further changes — uses existing `create_new_version()` flow).
2. **Existing `/approvals/overview`** page — already lists pending approvals by type. Add Step-context render for `PROCESS_APPROVAL` requests (show Process name, Step name, change description).
3. **Existing `ApprovalResponseModal`** — handles decision + signature + password capture. No changes needed.
4. **Process editor admin UI** — add an `approval_template` selector (the FK above). Same for PartType editor.

### What's wired vs. what's new

| Piece | State |
|---|---|
| `ApprovalRequest` model with `PROCESS_APPROVAL` enum value | Exists |
| `ApprovalTemplate` with role / user / group routing | Exists |
| `ApprovalResponse` capture (signature, password, comments) | Exists |
| `submit_process_for_approval()` service (Process-level) | Exists — to be replaced/supplemented with Step-level entry point |
| `Processes` DRAFT / PENDING_APPROVAL / APPROVED state machine | Exists — stays as-is |
| `ApprovalsOverviewPage` and `ApprovalsHistoryPage` | Exists — minor render additions for Step context |
| `ApprovalResponseModal` | Exists — no changes |
| Signal-driven status cascade on response | Exists — new hook for ProcessStep target |
| `ProcessStep.approval_status` + `approval_request` FK | **New** — small migration |
| `Processes.approval_template` FK | **New** — small migration |
| `PartTypes.approval_template` FK | **New** — small migration |
| `ApprovalTemplate` uniqueness relaxation + `is_default` flag | **New** — small migration |
| `submit_step_for_approval()` / `try_activate_process_version()` services | **New** — `Tracker/services/mes/authoring_approval.py` |
| Tenant default template seeding | **New** — add to `GroupSeeder.seed_for_tenant()` or new mgmt command |
| Substep editor banner + Submit-for-Approval button | **New** — frontend |
| Step-context render on existing approvals overview | **New** — frontend tweak |

**Total scope estimate**: 8–12 hours backend (model fields, services, seeding) + 6–10 hours frontend (editor banner, button, overview render) + tests. The bulk is wiring; the architecture all exists.

### Permission model

DWI rides the existing group / permission system (`Tracker/groups.py`, `Tracker/permissions.py`, `Tracker/presets.py`). The 11 group presets already in place cover the role surface; DWI adds new permission codenames and extends existing presets.

**New permission codenames** (follows the existing CRUD + custom-action convention used by CAPA / quality reports / approvals):

| Codename | Action |
|---|---|
| `add_substep`, `change_substep`, `delete_substep`, `view_substep` | Standard CRUD |
| `add_substepcompletion`, `change_substepcompletion`, `view_substepcompletion` | Standard CRUD |
| `view_substepresponse`, `view_substepgatecompletion` | Read-only views of operator captures |
| `submit_substep_for_approval` | Custom action — transitions `ProcessStep` to PENDING_APPROVAL |
| `complete_substep` | Custom action — operator completes a substep with its captures |
| `void_substepcompletion` | Custom action — soft-delete a completion (via `VoidableModel.void()`) |
| `mark_substep_na` | Custom action — operator marks an optional substep N/A |

**Preset extensions:**

| Group | Substep perms |
|---|---|
| `engineering` | `add_substep`, `change_substep`, `delete_substep`, `view_substep`, `submit_substep_for_approval` |
| `qa_manager` | `add_substep`, `change_substep`, `view_substep`, `submit_substep_for_approval`, `void_substepcompletion`, view perms on completions / responses |
| `document_controller` | `add_substep`, `change_substep`, `view_substep` (matches existing DC pattern of having `add_processes` / `change_processes`); retains `manage_approval_workflow` for substep approval template config |
| `production_manager` | `view_substep`, `void_substepcompletion`, view perms on completions / responses |
| `shift_lead` | `view_substep`, `void_substepcompletion`, view perms on completions / responses |
| `operator` | `view_substep`, `complete_substep`, `mark_substep_na`, `add_substepcompletion`, `add_substepresponse`, `add_substepgatecompletion` |
| `auditor` | `view_substep`, `view_substepcompletion`, `view_substepresponse`, `view_substepgatecompletion` |
| `tenant_admin` | all of the above |

**Author≠approver enforcement** (decision #17): general rule on `ApprovalResponse` create, not DWI-specific. Lives in `services/core/approval/`. The submitter of any `ApprovalRequest` (its `requester`) cannot be one of the approvers responding. Applies uniformly to substep authoring, CAPA closure, quarantine disposition, customer use-as-is, and every future `ApprovalRequest` type. Emergency-bypass (e.g. Tenant Admin override when the requester is the only available approver) is a deferred `bypass_self_approval_check` permission.

**Voiding scope** — flat grant. `void_substepcompletion` on `shift_lead` is not queryset-restricted to "their team's WO." Rationale (second/third-order):

- Shift boundaries are operationally fluid (coverage, swaps, end-of-shift overlap) — filtering by a stable "team" definition doesn't match shop-floor reality.
- Queryset filtering creates a UX trap (visible void button → click → denied) and either duplicates the filter on the frontend or surprises the user.
- `django-auditlog` records every void with who/when/reason — abuse detection happens at the audit-review layer, not by limiting the action permission.
- If a tenant wants stricter scope, the existing group customization removes `void_substepcompletion` from their `shift_lead` preset. Tenant Admin has the lever.

This differs from the `change_parts` queryset-filtering pattern (Operator) because parts are high-volume and operators routinely cross-WO; voiding completions is low-volume, high-trust, and the role boundary is appropriately wider.

### Deferred (configurable later, not v1)

- **Multi-stage approval per Step** — existing single-stage with `ALL_REQUIRED` / `THRESHOLD` (N-of-M) / sequential ordering covers most needs. Multi-stage gates ("Stage 1: engineering review → Stage 2: QA review") would require new model machinery; add when a customer surfaces it.
- **Auto-escalation scheduler** — `ApprovalRequest.escalation_day` + `escalate_to` fields exist; the periodic job to actually fire escalations is a Celery beat task we can add when needed.
- **Per-PartTypeFamily template inheritance** — current resolution is Process → PartType → Tenant. Family-level inheritance (PartType → PartTypeFamily → Tenant) is a small extension if part-type families exist as a concept; add when needed.
- **Approval bypass for emergency changes** — supervisor override that publishes without approval. Risky; defer until a customer asks and we can scope safeguards (e.g. requires Tenant Admin + post-hoc retroactive approval).

---

## Service Layer

New module: `Tracker/services/mes/substeps.py`

Public functions:
- `complete_substep(step_execution_id, substep_id, user_id, *, signature_data=None, signature_meaning=None, password=None, ip_address=None, notes='', mark_not_applicable=False)` — validates sequencing, gate-node satisfaction (walks `body_blocks` for required `AttestationCheckpoint` / `MeasurementInput` nodes and verifies completion records exist), signature requirements, then records `SubstepCompletion`. Signature/password flow mirrors `services.qms.capa.complete_capa_task`.
- `record_gate_completion(step_execution_id, substep_id, node_id, user_id, *, signature_data=None, ...)` — writes a `SubstepGateCompletion` row when an operator clicks an attestation checkbox or signs a gate node.
- `record_substep_response(step_execution_id, substep_id, node_id, user_id, *, kind, value_text='', value_document_id=None)` — writes a `SubstepResponse` row for text / choice / photo / video / scan inputs.
- `can_complete_substep(step_execution_id, substep_id) -> tuple[bool, list[str]]` — walks the substep's `body_blocks`, finds every required capture/gate node, checks that the matching `SubstepGateCompletion` / `SubstepResponse` / `StepExecutionMeasurement` row exists. Returns `(ok, reasons)`.
- `void_substep_completion(completion_id, user_id, reason)` — soft-delete via `VoidableModel.void()`.
- `can_complete_op(step_execution_id) -> bool` — checks that all required substeps are complete and all measurement gates satisfied; called by existing Step-completion service. ("Op" = `Steps` model in code, per vocabulary alignment at top of doc.)

New module: `Tracker/services/qms/inline_capture.py` (Phase 3 — per architectural decision #21)

Public functions:
- `record_dwi_measurement(step_execution, substep, measurement_definition, value, recorded_by, equipment=None, value_string=None) -> StepExecutionMeasurement` — the two-tier capture entry point. Always writes a `StepExecutionMeasurement` row (process data — Tier 1). If `substep.is_inspection_point` is True, additionally creates `QualityReports` + `MeasurementResult` (inspection record — Tier 2), which fires `record_quality_report_side_effects()` (auto-quarantine, NCR notification, sampling fallback). Idempotent on the Tier 2 QualityReports lookup: one report per `(step_execution, substep)` — subsequent captures during the same substep attach as additional `MeasurementResult` rows. Returns the Tier 1 row.

No new entry points in `Tracker/services/change_control/` — substep in-flight behavior rides the existing PCO migration disposition flow.

---

## Migration Plan

The scope grew past what one migration should carry. Splitting into focused phases — each independently shippable, each reversible (all additive), and the substep work isn't gated by the authoring-approval work.

### Phase 1 — Substep core models

**New tables:**
- `Substep`
- `SubstepCompletion`
- `SubstepResource`
- `SubstepTranslation`

**Modified:**
- `Steps` — add `sequencing_mode` (default `SEQUENTIAL`)

**Backfill:** none. Substeps are net-new; existing `StepExecution`s simply have no completions. Existing `Steps` rows pick up the `SEQUENTIAL` default — no behavior change because no substeps exist on them yet.

**Optional follow-on:** management command to materialize a default substep from any existing free-text `Steps.description` field on Steps that an engineer wants to "promote" — opt-in, per-Step, not part of the migration.

### Phase 2 — Per-node operator state

**New tables:**
- `SubstepGateCompletion`
- `SubstepResponse`

**Backfill:** none.

Can ship alongside Phase 1 or after; depends only on `Substep` and `StepExecution` existing.

### Phase 3 — Substep-aware measurements + two-tier capture pipeline

Per architectural decision #21, DWI numeric captures use a two-tier shape:

- **Tier 1 (always written):** `StepExecutionMeasurement` — process data. Feeds the existing step-advancement gate. SPC adapter is extended in this phase to UNION-read this table alongside `MeasurementResult`.
- **Tier 2 (conditional):** `QualityReports` + `MeasurementResult` — inspection record. Written only when the parent substep has `is_inspection_point=True`. Firing `QualityReports.save()` chains into `record_quality_report_side_effects()` which handles auto-quarantine on FAIL, `ncr.opened` notification, sampling fallback, and analytics updates.

**Modified:**
- `Substep` — add `is_inspection_point = BooleanField(default=False)` (the load-bearing field for the inspection promotion)
- `StepExecutionMeasurement` — add nullable `substep` FK (attribution for DWI captures)
- `StepMeasurementRequirement` — add nullable `substep` FK (substep-scoped measurement requirements)
- `StepRequirement` — add nullable `substep` FK (substep-scoped general requirements)
- ~~`ProcessChangeRequest` — `target_substep` FK + CheckConstraint~~ **Deferred** — the existing model has `target_process` as a required FK with a unique constraint built around it; adding a substep-targeted PCR requires restructuring those constraints (make `target_process` nullable, add `target_step` and `target_substep`, update the open-PCR-per-target uniqueness logic to handle three targets). Substep-targeted PCRs aren't on the M1 critical path — they're a Phase 4-ish concern (when someone wants to propose a change against a specific substep rather than the whole Process). Defer to a focused PR when that workflow surfaces.

**New service:**
- `services/qms/inline_capture.py::record_dwi_measurement(step_execution, substep, measurement_definition, value, recorded_by, equipment=None, value_string=None)` — always writes the Tier 1 row; if `substep.is_inspection_point`, additionally creates the Tier 2 chain (idempotent on `QualityReports` lookup — one report per `(step_execution, substep)` inspection event; subsequent captures during that same substep attach as additional `MeasurementResult` rows). Calls `record_quality_report_side_effects()` on the Tier 2 path.

**SPC adapter update:**
- `reports/adapters/spc.py` — extend the query to UNION read from `MeasurementResult` AND `StepExecutionMeasurement` keyed by the same `measurement_definition_id`. Each row contributes one data point to the control chart regardless of which tier it came from. ~30–45 min of careful adapter work + a test that mixes both sources.

**Backfill:** none — all new FKs are nullable; null means "applies at the parent Step level," matching today's behavior. `Substep.is_inspection_point` defaults to False so existing (Phase 1) substeps stay process-data-only.

Phase 3 is the largest single phase by scope because it touches code paths outside DWI — the existing measurement / requirement gate logic now optionally scopes to a substep, and the SPC adapter learns about a second source. Worth a focused PR.

### Phase 4 — Authoring approval

**Modified:**
- `ApprovalTemplate` — add `is_default = BooleanField(default=False)`; change `unique_together` from `(tenant, approval_type)` to `(tenant, approval_type, name)`
- `Processes` — add nullable `approval_template` FK
- `PartTypes` — add nullable `approval_template` FK
- `ProcessStep` — add `approval_status` (DRAFT / PENDING_APPROVAL / APPROVED, default DRAFT), nullable `approval_request` FK, nullable `approved_at`

**Backfill (in the same Django migration via `RunPython`):**
1. For each existing `ApprovalTemplate` row that's the sole template for its `(tenant, approval_type)`: set `is_default=True`. This must run **before** the new unique constraint is applied so the relaxed key holds.
2. For each existing `ProcessStep` row: set `approval_status='APPROVED'`. Existing data is presumed already in-production — operators are running against it today. Treating it as DRAFT would invalidate every active Process and freeze the floor.

**Seeding (not a migration — runtime):**
- New tenant signal: extend `GroupSeeder.seed_for_tenant()` to create a default `PROCESS_APPROVAL` `ApprovalTemplate` with `default_groups=[QA Manager, Production Manager]`, `flow_type=ALL_REQUIRED`, `is_default=True`.
- Existing tenants without a `PROCESS_APPROVAL` template: idempotent management command `setup_authoring_approval_templates` that creates the default for any tenant missing one. Safe to re-run.

### Operational notes

- **Order matters only inside Phase 4.** The `is_default` backfill must run before the new unique constraint is applied. Django handles this naturally when the data migration and schema migration are in the same migration file.
- **All phases are reversible** — every change is additive, no destructive drops.
- **Phases can be split across releases.** A reasonable shipping order is Phase 1 + 2 + 3 together (the DWI core that the frontend editor consumes), then Phase 4 (authoring approval) as a follow-on release once the approval template seeding is verified across tenants.
- **No frontend deploy-time coupling.** Backend changes are backward compatible with the existing frontend; new UI lights up as the editor + approval UX ships.
- **Service modules** (`services/mes/substeps.py`, `services/mes/authoring_approval.py`) ship with the corresponding phase but are pure Python — no migration impact.

---

## Deferred Items

Explicitly out of v1 scope; design accommodates future addition:

- `LibrarySubstep` model + "insert linked" authoring flow (provenance fields already present)
- **Conditional / skip-rule substeps** (no `condition_expr` field on v1):
  - **Level 1 (shipped today)**: `Substep.is_optional=True` + operator marks `SubstepCompletion.marked_not_applicable=True` with a `notes` reason. Most SMB reman cases work at this level — operator judgement with audit trail.
  - **Level 2 (sketched, deferred)**: per-part inspection-driven conditionals. Add `Substep.applies_when` JSON DSL:
    ```python
    applies_when = JSONField(null=True, blank=True)
    # Examples:
    # {"kind": "previous_response", "node_id": "abc-123", "operator": "equals", "value": "scored"}
    # {"kind": "measurement_result", "step_id": "...", "node_id": "...", "operator": ">", "value": 0.005}
    # {"kind": "and", "conditions": [...]}
    ```
    Service-layer evaluator in `services/mes/substeps.py` reads earlier `SubstepResponse` / `StepExecutionMeasurement` rows for this `StepExecution` and decides whether the substep applies. Most relevant for reman teardown branching ("if bearing race scored → regrind; else skip"). ~3–5 days of work when first reman customer surfaces the need.
  - **Level 3 (not planned)**: engineer-authored cross-execution rules / a real rules engine. Skip unless a customer genuinely needs it.
- Translation authoring UI (table exists; UI is later)
- `MaterialType`, `PPEType` (referenced as nullable FKs; can be added incrementally)
- Per-substep effectivity dates (PCN handles version transitions today)
- Operator-facing kiosk/mobile execution UI (separate workstream — see `/my-work` planning)
- **Excel template import** — customer-specific migration work, built per-customer against a real template. Importer lives in `Tracker/services/mes/dwi_import/` (per the canonical service-layer locations in `CLAUDE.md`), sources stored in `Documents` for traceability. Don't build speculatively.
- **Gate-based sampling routing** — auto-resolved `SAMPLING_GATE` step nodes that route sampled parts to a separate inspection step. Deferred per decision #14. Estimated cost when needed (~2 weeks of focused work):
  - Schema (trivial, additive): new `EdgeType.SAMPLED` value; `Steps.auto_resolve` boolean (default False); optional `Steps.sampling_rule` FK directly on `Steps`
  - Service: extend `advance_part_step()` (`parts.py:85`) with a gate-handling branch — on entry to a step with `auto_resolve=True`, evaluate rule, set `decision_result`, complete `StepExecution` immediately, recurse to advance further
  - Frontend: gate node rendering in the process flow visualizer; operator queue filters out `auto_resolve=True` steps
  - Admin UI: configure a gate step (link to sampling rule, configure outgoing edges)
  - Migration: strictly additive — existing block-based data is unaffected. Gate-based is opt-in per new Process version via `create_new_version()`. In-flight WOs continue on the old version via the existing `ProcessChangeMigrationDisposition` flow.
  - Gotchas to plan around:
    - Rule firing point semantics: `SamplingFallbackApplier` evaluates at part creation today. Gate-based routing wants evaluation at gate entry, which changes the "Nth" math for `EVERY_NTH_PART` (Nth-created vs. Nth-to-hit-the-gate). Decide whether to re-evaluate at gate entry or reuse pre-computed `Part.requires_sampling`.
    - Two architectures coexisting: block-based for old processes, gate-based for new — every behavior question gets asked twice during the transition. Maintenance discipline required.
    - FPI migration is optional and probably not worth it. Block-based FPI works; converting to a gate is architectural cleanup with no customer-visible gain.
    - The QC step needs a real operator queue (`Steps.step_type='WORK'` filtered to QC users) — currently QC inspection happens via `QualityReports` without a queue concept.
- **PDF export** — server-side via WeasyPrint or ReportLab, invoked from a toolbar button. Walks the same JSON `generateHTML` consumes.
- **Mermaid / Excalidraw inline diagrams** — custom node wrapping `mermaid` if a customer genuinely needs decision-tree visuals beyond the step graph.
- **`VideoCapture` operator-side** — Dozuki has it, low demand for SMB shop floor; build when asked.
- **`DateTimeInput` operator-side picker** — initially considered for v1; removed after evaluation. Most timestamps on the shop floor are auto-captured (`SubstepCompletion.completed_at`, `StepExecutionMeasurement.recorded_at`, step-execution entered/exited timestamps, `QualityReport` timestamps). The rare backdating case ("lot received yesterday, recording today") can use `TextInput` with a date-format placeholder until a customer surfaces a real need. Adding it back later is ~30 minutes — single custom node, `SubstepResponse.kind='datetime'` enum value, one toolbar button.
- **Explicit `FPIRecord.lot_released_at` timestamp** — current FPI release is implicit (reconstructed from "earliest passed `FPIRecord` for this WO+step"). An explicit nullable timestamp would make audit queries cleaner. Cost to add later is small (nullable field, no data backfill needed). Deferred until a customer surfaces an audit query the current model can't answer cleanly — SMB CNC and most ISO 9001 / AS9100 audits don't need it; FDA 21 CFR 820 or strict aerospace might. Don't add speculatively.
- **Supervisor-required substep attestations** — v1 only supports operator self-attestation on inline gate nodes (`AttestationCheckpoint`, `SignatureGate`). The operator signing is always the operator running the `StepExecution`. Cases where a *different* role (Shift Lead, QC Inspector, supervisor) needs to sign off on a substep gate are deferred. When the need arises:
  - Add `approver_role` attr to the gate node's TipTap attrs (e.g. `'shift_lead' | 'qc_inspector' | 'tenant_admin'`)
  - When the operator hits a gate with `approver_role` set, the service creates an `ApprovalRequest` (existing model) routed to that role instead of writing a `SubstepGateCompletion` immediately
  - The approval response handler writes the `SubstepGateCompletion` row with the approver's identity + signature
  - Substep advance is blocked while the approval is pending — operator sees "Awaiting [role] sign-off" state
  - Reuses the existing approval inbox / overview / history UI; no parallel queue needed
  - Estimated: ~3–5 days of work when first surfaced (mostly testing async state transitions)

---

## Resolved Open Questions

1. **Signature format** — Resolved. Reuse the explicit-field pattern from `ApprovalResponse` and `CapaTasks` (`signature_data`, `signature_meaning`, `verification_method`, `verified_at`, `ip_address`). No new signature primitive. `DIGITAL_SIGNATURES.md` covers PDF report signing — a separate concern.
2. **Measurement gate enforcement** — Resolved. Block at substep when `sequencing_mode=SEQUENTIAL`; block at Op completion when `FREE_ORDER`. See Sequencing enforcement above.
3. **In-flight propagation** — Resolved. Reuse existing `ProcessChangeMigrationDisposition` and PCO implementer disposition flow. No new substep-level policy. Mid-execution version switch ("IMMEDIATE") explicitly not supported.
4. **Per-substep analytics / OEE** — Deferred to a separate `Documents/DWI_ANALYTICS_DESIGN.md` once the core system is in use. v1 ships raw `completed_at` timestamps only; aggregation, pause detection, and dashboards are follow-on work.
5. **Editor library choice** — Resolved. Raw `@tiptap/react` + `@tiptap/starter-kit`, MIT. Wrapper libraries (`reactjs-tiptap-editor` evaluated) rejected — see Editor & Custom Node Library section for reasoning.
6. **Where operator-side data lives** — Resolved. Per-execution rows in `SubstepCompletion` / `SubstepGateCompletion` / `SubstepResponse` / `StepExecutionMeasurement`. Document JSON (`Substep.body_blocks`) is engineer-authored template only and never mutated by operator activity.
7. **Custom-node attribute editing UX** — Resolved per decision #20. Hover gear icon → shadcn `Popover` → debounced (250ms) `updateAttributes` from `NodeViewProps`. Per-node popover components at `src/components/dwi/nodes/{NodeName}/edit-popover.tsx`. `MeasurementInput` / `MeasurementSpec` popovers include a `MeasurementDefinition` autocomplete that autofills label/unit/nominal/tolerances/characteristic on pick. Operator view (editable: false) suppresses the gear entirely.
8. **Sampling architecture (block vs. gate)** — Resolved. Stay block-based for v1 (decision #14, see Sampling Integration section). Substep-level sampling adds `Substep.sampling_rule` FK and evaluates on substep entry; step-level sampling uses the existing `Steps.sampling_required` + `can_advance_from_step` block. Gate-based routing is deferred and additively cheap when needed.
9. **Explicit `FPIRecord.lot_released_at`** — Resolved. Not added in v1. Current implicit reconstruction is fine for SMB customer compliance needs. Adding later is cheap (nullable field, no backfill required). See Deferred Items.
10. **Part-level divergence support** — Resolved. Already handled by existing `Steps.requires_batch_completion` / `pass_threshold` / `block_on_quarantine` flags and decision-point routing. No DWI-layer changes needed. Reman-specific gap is conditional substep applicability (Level-2 deferred) and per-part visualization (separate UX workstream).
11. **Substep sampling FK target** — Resolved. `Substep.sampling_rule` FK to `SamplingRule` (leaf row), mirroring `Part.sampling_rule`. No separate `sampling_ruleset` FK on `Substep` — the ruleset is reachable via `SamplingRule.ruleset`. Ruleset versioning rides on existing Process-level versioning.
12. **Inline gate approval integration** — Resolved. v1 only supports **operator self-attestation** — the signer of an `AttestationCheckpoint` or `SignatureGate` is always the operator running the `StepExecution`. Gate completion writes a `SubstepGateCompletion` row immediately. Supervisor-required attestations (where a different role must sign) are deferred — see Deferred Items for the migration sketch (`approver_role` attr → `ApprovalRequest` integration).
13. **Authoring approval granularity** — Resolved per decision #15. Per-Step approval via `ProcessStep.approval_status` (DRAFT / PENDING_APPROVAL / APPROVED) and `ApprovalRequest` targeting the `ProcessStep` through-table row. Process version transitions to ACTIVE only when all its ProcessStep rows are APPROVED. See "Authoring Approval Workflow" section.
14. **Approval template resolution** — Resolved per decision #16. Most-specific-wins: `Processes.approval_template` (new FK, nullable) → `PartTypes.approval_template` (new FK, nullable) → tenant default `ApprovalTemplate(approval_type='PROCESS_APPROVAL', is_default=True)`. Seeded for new tenants with QA Manager + Production Manager as required approvers (ALL_REQUIRED parallel).
15. **Author≠approver enforcement** — Resolved per decision #17. General `ApprovalResponse`-create rule in `services/core/approval/`. Applies to every `ApprovalRequest` type (not DWI-specific). Emergency-bypass gated by a deferred `bypass_self_approval_check` permission.
16. **`node_id` minting** — Resolved per decision #18. Client-side `uuidv7()` at insert / paste regenerate / library template import. Server validates UUID format + intra-document uniqueness on `Substep.save()`. Cut-paste regenerates the ID; prior `SubstepResponse` rows on the old ID stay in the DB but no longer auto-link to the restored node — acceptable since cut-paste in approved-substep editing is rare (substeps are frozen post-approval; edits happen in a new Process version with cloned IDs).
17. **Mid-execution persistence** — Resolved per decision #19. Batch-on-complete: all captures held in client memory, posted in one transaction when operator hits Complete Substep. Photos / files upload eagerly to the existing `Documents` API. Timer captures finalize on Stop, batch on Complete. Close-without-complete discards local state — no partial-substep resume in v1.
18. **`can_complete_substep()` contract** — Resolved. Per-node precondition table in Execution Semantics → Substep completion contract. `Substep.requires_ack` removed from the model (only `requires_signature` remains for substep-level gating; `AttestationCheckpoint(kind='confirm')` covers inline checkbox needs). `ComputedValue` completes on "variables filled + formula evaluates" — out-of-spec doesn't block. Error UX: enabled "Complete Substep" button + scroll-to-first-blocked + count banner.
19. **Permission model** — Resolved. Rides existing `Tracker/groups.py` / `Tracker/presets.py` system. New substep permission codenames defined; preset extensions on `engineering` (full authoring), `qa_manager` (authoring + void), `document_controller` (authoring per existing process-authoring pattern), `production_manager` / `shift_lead` (void + view), `operator` (execute / complete / mark N/A), `auditor` (view only). Voiding is flat-granted on `shift_lead` rather than queryset-restricted — see "Permission model" subsection for rationale.
20. **Measurement data routing for DWI captures** — Resolved per decision #21. Two-tier with explicit inspection-point promotion. Routine `MeasurementInput` captures write to `StepExecutionMeasurement` only (process data — no auto-quarantine, no NCR event). `Substep.is_inspection_point=True` substeps additionally create `QualityReports` + `MeasurementResult` via `services/qms/inline_capture.py::record_dwi_measurement`, firing the existing `record_quality_report_side_effects()` (auto-quarantine, NCR notification to QA Manager via the Phase 5 notification rules, sampling fallback). The SPC adapter is extended in Phase 3 to UNION-read both `StepExecutionMeasurement` and `MeasurementResult` so every measurement reaches the control chart. This is the shape established MES/QMS systems (Plex / SAP QM / Aegis FactoryLogix) use; avoids the auto-quarantine spam and audit-meaning dilution that would result from promoting every inline capture to an inspection record. **(Shipped 2026-07-14, with a refinement: the UNION read was extracted to the shared `services/qms/spc_ingest.collect_spc_rows` collector — used by both the live chart endpoints and the PDF adapter — with a dedup rule. An inspection-point capture writes BOTH a SEM and a promoted MR for one physical reading; the collector counts a SEM only when its substep is not an inspection point, so the tiers are disjoint and readings aren't double-counted. This also brought batch/process-parameter measurements onto the live charts.)**

21. **Equipment capture: three models, one read — do NOT aggregate into one table.** Three surfaces reference `Equipments`, and they are three distinct ISA-95 concerns, not one concept recorded thrice: (a) `StepExecutionMeasurement.equipment` — *metrology*, "which gauge produced this reading" (belongs on the datum; needed for gauge R&R / MSA / calibration linkage of a data point); (b) `QualityReportEquipment` (role-tagged PRODUCTION/FIXTURE/TOOL/GAUGE) — *quality-event context*, "what equipment was involved in this nonconformance" (an 8D/CAPA root-cause artifact, scoped to an inspection record); (c) `EquipmentUsage` — *resource actuals / device-history*, "what touched this part, at this step, when" (the as-run genealogy). Merging them would conflate three questions with three different consumers (MSA, CAPA, recall/DHR). **Decision: keep the three models separate.** The real problems the split creates are handled two ways: (1) **duplication** — an inspection-point measurement writes the same gauge into both `SEM.equipment` and (via the report) `QualityReportEquipment`; when a consumer needs the union, do it in a **shared read collector with a dedup rule** (the SPC-collector pattern), NOT by merging tables; (2) **no single "as-run equipment" answer** — the cross-cutting query ("everything that touched part X" / "parts gauge G touched", i.e. **calibration escape/recall**) is satisfied by that same union read. `EquipmentUsage` has a genuine, non-redundant use — equipment traceability at *non-inspection* operations, which (a)/(b) structurally miss — but it has **no runtime writer** and its live consumer (the part traveler's equipment strip, `mes_lite.py` traveler) is therefore always empty in real use. **Building the `EquipmentUsage` writer is gated behind one product question: do we owe customers equipment traceability at non-inspection ops (AS9100/IATF tool-to-part traceability + calibration escape)?** If yes, `EquipmentUsage` becomes the canonical ISA-95 resource-actuals spine and the traveler strip + gauge nag light up as a side effect; if no, retarget the traveler strip to read from `QualityReportEquipment`/SEM and let `EquipmentUsage` go. **Agreed cleanup regardless (2026-07-14): retire the deprecated `QualityReports.machine` single-FK** — superseded by `QualityReportEquipment`; it is the ½ of "3½ equipment fields" that is genuine cruft. (Not yet executed — schema change, tracked as a discrete task.)

## Out of scope (belongs to other subsystems)

These are commonly mentioned features in DWI tools / connected-worker platforms that this design intentionally does **not** own. Each belongs to a separate subsystem.

- **Skill / certification gating** ("only operators with this training can perform this substep") — belongs in the Training tracking architecture. DWI substeps may reference `TrainingType` requirements, but the gating logic, training records, recertification cadence, and the skill matrix UI all live in the Training subsystem. Substep-level enforcement would call into a training service, not implement its own.
- **Tool / IO integration** (torque wrenches, scanners with feedback, andon lights, pick-to-light, vision-system signals) — belongs in the Equipment / IO integration layer. DWI gates can *consume* signals from this layer when present, but the device drivers, MQTT/OPC bridges, and equipment-state propagation live elsewhere.
- **Real-time SPC / control charts** — `MeasurementInput` writes process data to `StepExecutionMeasurement` (and inspection records to `MeasurementResult` when `substep.is_inspection_point=True`, per decision #21). Phase 3 updates the SPC adapter at `reports/adapters/spc.py` to UNION-read from both tables so every measurement reaches the control chart. Charts and rule alarms themselves remain an SPC subsystem concern, not DWI.
- **Operator analytics / cycle-time dashboards** — see `DWI_ANALYTICS_DESIGN.md` (deferred). DWI ships raw timestamps on completions and responses; aggregation, dashboards, and operator-comparison views are a separate workstream.
- **Calibration tracking** (gauges, fixtures) — DWI references equipment by class via `SubstepResource`; calibration state lives in the existing `CalibrationRecord` system.

## Known limitations of v1

Acknowledged but not addressed in this scope. Customer-visible if a real use case surfaces; not blocking.

- **v1 operator hardware target: 2-in-1 convertible laptops** (Surface-class). Real keyboards, larger screens (~13"+), full-spec browsers, mature touch. The desktop-tested UX is close to viable on this hardware class. Pure-tablet operator devices (iPad, Android tablet, ruggedized industrial tablet) are deferred — popover scroll behavior, virtual keyboard handling, and touch-target sizing on smaller screens haven't been validated and may surface fixes when a tablet-first customer ships.
- **Online-only.** v1 assumes the operator's tablet has live connectivity. There is no service worker, no offline document caching, no local response queue, no sync-on-reconnect. Most SMB shop floors have adequate WiFi for one-tablet-per-station; large or multi-bay facilities with thin coverage will eventually request offline-first. Migration would require: service worker for asset caching, IndexedDB-backed response store, optimistic ID generation for offline writes, server-side conflict-resolution (likely last-write-wins with an audit override). Architecturally significant; defer until a customer surfaces it.
- **No live diff between Process versions.** Approvers see "version 3 vs version 2" by name, not by content delta. They open both side-by-side to compare. A diff renderer for the TipTap JSON tree (showing inserted/removed/modified nodes) is feasible but not v1.
- **No full-text search across instructions.** Engineers and operators can't ask "which substeps reference part 11782-3?" or "where is the bearing-replacement procedure?" Postgres FTS over `generateHTML(body_blocks, ...)` is the natural path; not v1.
- **No nested / sub-guide embed.** Dozuki lets a guide reference another guide. We don't. Reuse across substeps is via duplication; eventual answer is the `LibrarySubstep` deferred concept.
- **No auto-fill from previous run.** Operator types the same lot number across multiple substeps. v1 has no "pre-fill from prior `SubstepResponse` on this WO" mechanism. Cheap to add later via service-layer pre-population.
- **SPC adapter UNION read is a Phase 3 deliverable.** The existing SPC adapter at `reports/adapters/spc.py:233` reads only `MeasurementResult` today. Phase 3 extends it to also read `StepExecutionMeasurement` so DWI process-data captures populate control charts (per decision #21). Until that adapter change ships, SPC sees only inspection-point captures. If Phase 3 is delayed past M1 demo, the closed-loop "operator captures → SPC chart updates" story only works for substeps with `is_inspection_point=True`.

---

## Investigation needed

- **Reman ↔ DWI integration.** Reman teardown adds enough surface (Core flow through Steps, per-Core substep captures, `HarvestedComponentCapture` custom node, auto-coordination between Core lifecycle and WO state, batch-of-cores UX) to warrant its own design doc. See `Documents/REMAN_DWI_INTEGRATION.md` for the full design — `StepExecution` two-FK extension, `Core.step` field, `advance_core_step` service mirror of `advance_part_step`, `start_teardown` service, the capture-node spec, and the 5-phase migration plan. Estimated 2–3 weeks of focused work for R1–R4 (the "ship reman DWI" milestone).

## Still Open

- **Signature blob format on the wire** — image data URI vs. SVG path? Recommend matching whatever `ApprovalResponse.signature_data` currently accepts (Base64 PNG per its help_text) for consistency.
- **CAPA-style password re-verification** — `complete_capa_task` accepts a `password` param. Should substep signoff require the same when `requires_signature=True`? Default to yes for parity, can relax later.
- **`SubstepResponse.unique_together` for team-based steps** — keep `(step_execution, substep, node_id)` as-is. `StepExecution` is per-part (`mes_lite.py:1141`: `part = ForeignKey('Parts')`), so per-part captures already work naturally — each part has its own `StepExecution` row, so different parts never collide on the composite key. The constraint only fires on accidental dual-tab / dual-tablet writes on the same part execution, where first-write-wins + visible 400 is the right behavior. If per-part captures from a single execution are ever needed (e.g. batch operations where one execution row handles multiple parts — not the current model), the fix is adding a nullable `part` FK rather than relaxing the constraint.
- **`generateHTML()` output quality for PDF / email** — each custom node's `renderHTML()` currently produces minimal text fallback. Either improve `renderHTML()` per node, or accept that PDF rendering goes through a different path. Decide before building the PDF export workstream.
- **`SubstepResource` UI placement** — equipment / tool / PPE list could be (a) a custom node inside the substep `body_blocks`, or (b) a separate panel rendered alongside the substep view. Data model leaves both options open; pick at production-UI time.

---

## Implementation Status (live state — kept current as work lands)

### Shipped end-to-end (backend + frontend)

**Phase 1 — Substep core models**: Substep, SubstepCompletion, SubstepResource, SubstepTranslation + `Steps.sequencing_mode` ✓

**Phase 2 — Per-node operator state**: SubstepGateCompletion, SubstepResponse ✓

**Phase 3 — Two-tier capture**: `Substep.is_inspection_point` + `services/qms/inline_capture.py::record_dwi_measurement` (Tier 1 always, Tier 2 conditional) + SPC UNION adapter across `MeasurementResult` and `StepExecutionMeasurement`. `ProcessChangeRequest.target_substep` deferred (constraint restructuring; not on critical path) ✓

**DRF surface**: `SubstepViewSet` + 5 sibling viewsets (Resource / Translation / Completion / GateCompletion / Response) registered under `/api/Substeps/` etc. Custom action `POST /api/Substeps/reorder/` does atomic two-phase reorder inside a transaction to dodge the `(step, order)` unique constraint. ✓

**Authoring frontend** (`/editor/processes/$processId/steps/$stepId/substeps`):
- 12 custom TipTap nodes extracted to `src/components/dwi/nodes/*` (MeasurementSpec, MeasurementInput, Callout, Media, AttestationCheckpoint, TextInput, ChoiceInput, PhotoCapture, ScanInput, FileCapture, Timer, ComputedValue)
- Shared infrastructure: `OperatorResponseContext`, `NodeCard`, `AuthoringPopover` (legacy compat — pass-through now), `useDebouncedAttrs`, attr-input rows, `FileLikeCapture`, mock `MeasurementDefinitions` (placeholder until autocomplete lands)
- Extension list at `src/lib/dwi/extensions.ts`; samples at `src/lib/dwi/samples.ts`
- **Properties-panel pattern** (selection-driven, right pane, sticky, replaces popover) — `src/components/dwi/NodePropertiesPanel.tsx`
- Save-Draft model (global header button, no autosave); reorder via drag is a draft change folded into the same global save; `beforeunload` warning when unsaved
- Drag-to-reorder with optimistic UI; commit via `POST /api/Substeps/reorder/`
- Navigation: React Flow's `StepEditorPanel` now has a "Substeps" row with a drill-down arrow into the substep editor; substep editor has a "Back to process flow" link on the header
- Diagnostic: `window.__errorLog()` captures both browser-level (`error`, `unhandledrejection`) and React Query queryCache / mutationCache errors with the raw error object stashed for inspection — useful for surfacing Zodios validation failures that otherwise stay inside query state

**DRAFT-only authoring guard** (Phase 4 prep — pulled forward):
- `Steps.is_editable` property — True iff every consuming Process (via `ProcessStep`) is in DRAFT; empty consumer list also editable. Substep delegates to `step.is_editable`.
- `SubstepViewSet` enforces via `_assert_step_editable` on create / partial_update / update / destroy / reorder. Returns `PermissionDenied` with a message pointing the user at the PCR flow.
- `SubstepSerializer.is_editable` exposed read-only so the UI flips to read-only when the parent Process is APPROVED / DEPRECATED.
- Read-only UX: header shows "Read-only · Process not in DRAFT" badge; Save / Discard / Add / drag / per-row title / flag switches / delete / TipTap body editor are all disabled.

**Naming cleanup**: `/api/ErrorReports/` URL alias renamed to `/api/QualityReports/` across backend router, schema, generated TS client, all frontend hooks (`useQualityReports`, etc.), `ModelEditorPage` model-name map, and `Documents/FEATURE_INVENTORY.csv`. Clean break — no backward-compat redirect (we own all producers and consumers).

### Decisions captured (this iteration, not yet shipped)

**Form-architecture choice for inspection / QA forms: Option A + door open for C.**

The system already has `QualityReports` as the formal inspection record (it's not separately also called "ErrorReports" — that was a naming bug, now fixed). The current DWI capture nodes only cover *some* `QualityReports` fields (measurement values via Tier 2 promotion). To support full QA-form capture inside a substep:

- **Add structured-capture nodes** that map 1:1 to `QualityReports` fields the existing nodes don't cover. The "QA form" then *is* a substep with these nodes + `is_inspection_point=True`. The existing `record_dwi_measurement` service already creates one `QualityReports` per `(step_execution, substep)`, so all these nodes contribute to the same report (idempotent).
- New node types planned:
  - `OperatorsField` — multi-select users → `QualityReports.operators` M2M
  - `MachineField` — FK select → `QualityReports.machine`
  - `ErrorTypesField` — multi-select with severity / location → `QualityReportDefect` rows
  - `QualityStatusField` — PASS / FAIL / PENDING → `QualityReports.status`
  - `InspectionSignatures` — detected_by + verified_by signoff
  - `PartAnnotation` — embeds the existing `PartAnnotator` 3D widget; writes to `HeatMapAnnotation`, links to the substep's `QualityReports`
- Templates (option C) are a deferred UX layer on top — engineers will be able to "new substep → from template → QA form" to pre-fill a substep with the right node skeleton. Just don't paint the model into a corner that prevents templates later.
- The work order page's **QA Forms tab** dissolves: that URL becomes the operator-runtime view, and operators reach inspection captures through DWI substeps rather than a parallel standalone form.

**`Substep.kind` enum was considered and rejected** as architectural over-fitting. Substeps stay composable; the "kind" of a substep is emergent from the nodes it contains + `is_inspection_point`.

**QualityReports equipment + personnel reshaped to M2M-with-role.** The legacy single `machine` FK and `detected_by` / `operators` / `verified_by` trio couldn't express cell ops, multi-station Steps, fixture/tool interactions, or the broader cast (inspector / witness / trainer / trainee). Two new through tables added (migration `0055_add_qualityreport_equipment_personnel_roles`):
- `QualityReportEquipment(quality_report, equipment, role, notes)` with `role ∈ {PRODUCTION, FIXTURE, TOOL, GAUGE, OTHER}` and a unique `(quality_report, equipment, role)` constraint.
- `QualityReportPersonnel(quality_report, user, role, signed_at, notes)` with `role ∈ {DETECTED_BY, OPERATOR, VERIFIED_BY, INSPECTOR, WITNESS, TRAINER, TRAINEE}` and a unique `(quality_report, user, role)` constraint.

The migration backfills existing data (machine FK → PRODUCTION row; detected_by → DETECTED_BY; verified_by → VERIFIED_BY; each operators M2M row → OPERATOR). Legacy fields are left in place during the transition window with DEPRECATED help_text so readers can migrate at their own pace; new canonical-read properties (`primary_machine`, `primary_detector`, `primary_verifier`, `operator_users`) prefer the new shape and fall back to the legacy field. Removal of the legacy fields is a follow-up once all readers and writers are switched.

The structured-capture nodes (`MachineField`, `OperatorsField`, `InspectionSignatures`) will write to the new through tables via the inspection capture endpoint when operator runtime lands. Read-only nested serializer fields (`equipment_links`, `personnel_links`) are already on the API so the UI can render the new shape today.

**In-process check cadence = sampling engine.** `Substep.sampling_rule` (already a field) is the runtime visibility gate. No new time-based cadence field — sampling rules carry the semantics. Two-axis model:

| | Always show | Sampled cadence |
|---|---|---|
| `is_inspection_point=False` | Work instruction | **In-process check** |
| `is_inspection_point=True` | Tollgate | Sampled tollgate (AQL) |

Runtime logic to consult `Substep.sampling_rule` for visibility is not yet wired (operator-runtime phase).

**Authoring UX: properties panel, not popover.** Industry analog: Tulip, FactoryLogix, no-code form builders. Selected-node ring + sticky panel are in. `AuthoringPopover` is reduced to a click-affordance wrapper for back-compat — the click selects the atom node, the right pane renders the form.

**SPA-aware navigation guard.** `beforeunload` only catches browser unload. In-app navigation (e.g. the "Back to process flow" link) needs to confirm before discarding unsaved changes. Wire into TanStack Router transitions.

### Day-one work list (ordered)

1. ~~**DRAFT-only guard**~~ ✓ Shipped above.
2. ~~**In-app SPA nav warning**~~ ✓ `useBlocker` from `@tanstack/react-router` wired in `SubstepEditorPage`; fires a `window.confirm` when `hasUnsavedChanges` and the user tries to navigate away (back link, sidebar, programmatic `navigate()`). Complements the existing `beforeunload` for browser close/refresh.
3. ~~**Structured-capture nodes**~~ ✓ Five new nodes shipped (`QualityStatusField`, `EquipmentRolesField`, `PersonnelRolesField`, `InspectionSignatures`, `ErrorTypesField`). Each follows the established Node.create + View + EditForm + sample pattern, registered in extensions / samples / NodePropertiesPanel / spike toolbar. Authoring forms use the properties-panel pattern. Operator-side responses land in `OperatorResponseContext` keyed by `node_id`; backend persistence wires up in the operator-runtime phase.

   **Kiosk-mode forward-compatibility (deferred wiring):** the system isn't kiosk-ready yet, but several of these nodes have obvious auto-fill candidates once a session is bound to a kiosk:
   - `InspectionSignatures` — current logged-in user prefilled (already reads `useAuthUser`)
   - `EquipmentRolesField` — kiosk's bound machine prefilled with `role=PRODUCTION`
   - `PersonnelRolesField` — current operator prefilled as `OPERATOR`
   - `MeasurementInput` — equipment FK on associated measurement auto-bound to kiosk gauge
   - `QualityStatusField` — could default to PASS pending operator action, depending on workflow

   The runtime layer (not the nodes themselves) will read kiosk session state and pre-seed `OperatorResponseContext` before the substep renders. Nodes don't need to know they're being prefilled — that's a clean separation. When kiosk lands, add a `KioskAutoFillProvider` above the operator-runtime that hydrates the response context from session bindings.

   **One-click QA template ("Insert all required elements"):** an engineer authoring an inspection substep no longer has to drop five nodes by hand. Two new affordances:
   - **Toolbar bundle insert** in `Toolbar` (spike + production substep editor) — `QUALITY_REPORT_BUNDLE` from `src/lib/dwi/samples.ts` is a pre-composed list of the minimum capture set (`QualityStatusField`, `EquipmentRolesField`, `InspectionSignatures`, `ErrorTypesField`). Inserting clones each entry with a fresh `node_id` to avoid collisions.
   - **"Add inspection substep" button** in `SubstepEditorPage` next to "Add substep" — creates a new substep with `is_inspection_point=true` and the bundle pre-seeded into the body. One click → a substep ready for QA capture.

   Templates beyond the QA bundle are deferred; the pattern (a named sample list + an "insert template" button) is established so future templates (first-piece inspection, final QA, dimensional check) are mechanical to add.
4. ~~**Signature node plumbing**~~ ✓ Shared `SignaturePayload` type (`src/components/dwi/shared/signature.ts`): `{ user_id, username, signed_at, data_uri? }`. Both `AttestationCheckpoint` (signature kind) and `InspectionSignatures` now capture this payload via `useAuthUser` rather than a bare timestamp string. The `data_uri` field is reserved for a future canvas widget — when (if) a Base64 PNG stroke is needed, it drops in without schema changes. Operator-runtime persistence writes the same payload to `QualityReportPersonnel` (inspection context) or `SubstepResponse` (non-inspection context) through one code path. Password re-verification (CAPA-style) is still open — design doc "Still Open" #2.
5. ~~**`PartAnnotation` node**~~ ✓ Wraps the existing `PartAnnotator` 3D widget. Engineer picks the model_id (from `useRetrieveThreeDModels`) + label + required. Operator-side embeds `PartAnnotator` directly when a part is bound — that widget owns its own persistence (writes `HeatMapAnnotation` rows linked to the part and any pending `QualityReports` ids). Authoring spike + any context where no part is bound shows a placeholder card. Operator runtime binds `part_id` / `work_order_id` / `quality_report_id` via the new `PartContext` provider at `src/components/dwi/shared/PartContext.tsx`.
6. ~~**Operator runtime page (day-one cut)**~~ ✓ New route `/operator/steps/$stepId/substeps?part=&workOrder=&execution=` mounted on `OperatorSubstepRuntimePage`. Lists the step's substeps in order, renders each through the new `SubstepOperatorView` (single-column read-only TipTap with capture nodes interactive), wraps the page in `PartContext` + per-substep `OperatorResponseContext`. Captures aggregate into a side pane for visibility. The existing work order page's QA Forms tab dissolution is follow-up work — the route stands alone for now so we can validate the UX before swapping the tab.

7. ~~**Backend persistence wiring**~~ ✓ Full operator submit path live end-to-end.
   - Service module `Tracker/services/dwi/operator_capture.py::submit_substep` — one transaction that fans the operator's submit payload out into the right writes per node kind:
     - All capture kinds → `SubstepResponse` row (upsert on `(step_execution, substep, node_id)` so re-submits replace rather than duplicate)
     - `MeasurementInput` → existing `record_dwi_measurement` (Tier 1 always, Tier 2 via promotion when inspection-point)
     - `QualityStatusField` → `QualityReports.status`
     - `EquipmentRolesField` → `QualityReportEquipment` rows
     - `PersonnelRolesField` → `QualityReportPersonnel` rows
     - `InspectionSignatures` → `QualityReportPersonnel` rows with role `DETECTED_BY` / `VERIFIED_BY` + `signed_at`
     - `AttestationCheckpoint` (signature mode) → `QualityReportPersonnel` row with role `WITNESS`
     - `ErrorTypesField` → `QualityReportDefect` rows
     - `PartAnnotation` → marker `SubstepResponse` only (the existing `PartAnnotator` widget already writes `HeatMapAnnotation` directly)
   - Service closes with an upserted `SubstepCompletion` row marking the substep done.
   - API: `POST /api/Substeps/{id}/submit/` action on `SubstepViewSet`. Body shape documented in the service module docstring.
   - Frontend: `useSubmitSubstep` mutation hook + `buildCaptures()` helper at `src/lib/dwi/build-captures.ts` walks the substep's `body_blocks` to translate raw `OperatorResponseContext` values into the typed `captures` array. Operator runtime page calls it when the user hits Submit; toast surfaces `{response_count, measurement_count, quality_report_id}`.
   - `SubstepResponseKind` enum extended with new kinds: `ATTESTATION`, `STATUS`, `EQUIPMENT_ROLES`, `PERSONNEL_ROLES`, `SIGNATURES`, `DEFECTS`, `ANNOTATION` (migration `0058_extend_substep_response_kinds`).
   - drf-spectacular schema cleaned: added `@extend_schema_field` + return-type annotations to `SubstepCompletionSerializer.get_completed_by_name`, `SubstepGateCompletionSerializer.get_completed_by_name`, `SubstepResponseSerializer.get_responded_by_name`. **All 9 actionable warnings resolved**; remaining 2 are allauth's own self-emitted deprecation noise (third-party — not ours to fix).

### Subsequent round — QMS shape refactor + operator runtime redesign + polish

The work below landed after the day-one list closed.

**QualityReports schema refactor — M2M-with-role through tables** (migration `0055_add_qualityreport_equipment_personnel_roles`):
- `QualityReportEquipment(quality_report, equipment, role, notes)` with `role ∈ {PRODUCTION, FIXTURE, TOOL, GAUGE, OTHER}`. Replaces the single `machine` FK so cell ops + multi-station Steps express their equipment-roster correctly. Unique on `(report, equipment, role)`.
- `QualityReportPersonnel(quality_report, user, role, signed_at, notes)` with `role ∈ {DETECTED_BY, OPERATOR, VERIFIED_BY, INSPECTOR, WITNESS, TRAINER, TRAINEE}`. Replaces the flat `detected_by` / `operators` M2M / `verified_by` trio with one role-tagged shape. Unique on `(report, user, role)`.
- Migration backfills existing data (legacy `machine` FK → `PRODUCTION` row, `detected_by` → `DETECTED_BY` row, etc.), idempotent via `get_or_create`.
- Legacy fields kept during transition with DEPRECATED help_text. Canonical-read properties (`primary_machine`, `primary_detector`, `primary_verifier`, `operator_users`) read the new shape with fallback to legacy.
- Read-only `equipment_links` / `personnel_links` nested fields exposed on `QualityReportsSerializer` so frontend can render the new shape without write-side wiring.

**`ErrorReports` → `QualityReports` URL alias rename**:
- `router.register(r'QualityReports', QualityReportViewSet, basename='QualityReports')` across both registrar sites.
- Frontend hooks + components migrated from `api_ErrorReports_*` to `api_QualityReports_*` (8 files).
- `Documents/FEATURE_INVENTORY.csv` updated to match.
- Clean break — no backward-compat alias. All producers and consumers are in-house.

**`Substep.scope` + `BatchExecution` model** (migration `0059_dwi_batch_execution_and_substep_scope`):
- `Substep.scope = SAMPLED | BATCH` (default `SAMPLED`). The realization that simplified the model: PER_PART = PER_SAMPLE with 100% rule. PER_PART, PER_BATCH, and PER_SAMPLE collapsed into two values.
- `BatchExecution(work_order, step, parts M2M, started_by, started_at, sealed_at, completed_at, notes)`. Per-batch analog of `StepExecution`. Created at runtime when an operator starts a batch on a Step with any BATCH-scope substep. Parts can be added until the first BATCH substep fires (`sealed_at` set), locked after.
- `SubstepCompletion` and `SubstepResponse` both gained nullable `batch_execution` FK + CheckConstraint enforcing "exactly one of step_execution / batch_execution is set." Unique constraints split by scope path. Per-part and per-batch substep audit rows now coexist cleanly.
- Backend `submit_substep` service still takes only `step_execution`; **`BatchExecution` write path is the next iteration** (frontend operator runtime is still singleton).

**Operator runtime — Tulip-style player redesign**:
- One substep per screen with full-bleed center pane (max-width 720px tablet) — replaces the scrolling stacked list
- Top progress rail with substep dots (filled / current / pending), jumps within step, end-of-step review chip
- Bottom fixed action bar: `Back` (h-14 ghost) + state caption + primary `Confirm & next` (h-14 wide), `Confirm & review` on last substep
- Per-substep client confirm (sealed in `confirmedIds` set) + auto-advance; end-of-step review screen lists each substep with capture count and Edit affordance; `Complete step` fires the server flush
- Required-field validation via `findMissingRequired()` — walks the substep body, applies kind-specific "satisfied" rules (text non-empty, timer ran, computed has all vars, signature signed, status picked, M2M nodes meet `min_rows`, etc.), blocks Confirm and lists missing labels in the action bar
- URL state: `?at=<idx>` carries current substep position so refresh / kiosk-handoff resume cleanly
- Debug pane (responses JSON) hidden behind `?debug=1` flag; out of the operator's way by default

**Steps.is_editable loosened** — from "every consuming Process must be DRAFT" to "at least one consuming Process is DRAFT (or no consumers)." With shared Steps across Process versions (lightweight versioning), the strict rule blocked authoring any time an APPROVED version coexisted with a DRAFT version — which is the normal state, not a violation. The change-control flow (PCR/PCO/PCN) remains the right gate for edits that need formal review.

**Properties panel isolation** — three event-isolation fixes on `NodePropertiesPanel`'s root:
- `draggable=false` + `onDragStart` stopPropagation → text selection in inputs doesn't trigger the parent SubstepRow's drag-to-reorder
- `onKeyDown` stopPropagation → Backspace/Delete in the form doesn't bubble to ProseMirror as "delete selected atom node"
- `onMouseDown` stopPropagation → clicks into the form don't flicker Tiptap selection
- Removed `.focus()` from the `updateAttributes` adapter — was yanking focus back to the editor mid-typing and causing the next keystroke to replace the selected atom node with text

**Authoring affordance trim** — `AuthoringPopover` was reduced months ago to a pure hover-ring wrapper (the popover surface was replaced by the selection-driven properties panel). The dead `form` and `contentClassName` props were still being passed at 10 call sites; both prop signature and call sites now cleaned up. Component is now a 12-line ring-on-hover div.

**`MeasurementInput` wired to real backend** — `MOCK_MEASUREMENT_DEFINITIONS` dropped; the node now calls `useRetrieveMeasurementDefinitions` (the same hook the measurement editor uses). One more piece of demo scaffolding gone.

**`Media` node renders real content** — `<img>` for image, `<video controls>` for video. Width is always 100% of the container; height is author-controlled via a `size` attr preset (`sm` / `md` / `lg` / `xl` / `full`). Empty-src state shows a dashed-border prompt; load-error state shows a red diagnostic card with the offending URL. **Known limit**: cross-origin URLs that 200 with a hotlink-protection placeholder image (Fandom / Wikia) load as a "valid" image from the browser's perspective and bypass `onError`. The fix is the deferred Documents-upload pipeline that lets us serve our own bytes.

**Cleanup landed in this round**:
- Orphan docstring on `Substep.requires_signature` was floating under `is_inspection_point` — restored to the right field
- `HarvestedComponentCapture` wired into `NodePropertiesPanel`'s FORMS + NODE_LABELS (was registered in extensions but not in the panel; knip flagged it)
- 17 stray screenshot PNGs deleted from repo root
- `part_type_name = CharField(source='part_type.name', read_only=True)` across 6 serializers gained `allow_null=True` — the model field IS nullable so the OpenAPI schema should reflect that; otherwise Zodios rejects the response when the FK is null
- Demo seeder data aligned: `DEMO_QUALITY_ERRORS` had `'part_type': 'Fuel Injector'` but `DEMO_PART_TYPES` defines `'Common Rail Injector'`. The mismatch was silently nulling `part_type` on every demo error type. Renamed to match.

**drf-spectacular schema warnings cleared**:
- Added `@extend_schema_field(serializers.CharField(allow_null=True))` + `-> str | None` return-type hints on `get_completed_by_name` (×2) and `get_responded_by_name` SerializerMethodFields
- 9 → 0 actionable warnings. The remaining 2 are allauth's own self-emitted deprecation noise on `USERNAME_REQUIRED` / `EMAIL_REQUIRED` (third-party — they access their own deprecated attrs internally, not actionable from our settings).

**Demo URLs** that work as of this round:
- Substep editor: `/editor/processes/019cc953-b939-7893-a318-c6036d0199b2/steps/019cc953-ba7c-7421-a28a-04aa21b57df8/substeps` (process flipped to DRAFT for demo)
- Operator runtime: `/operator/steps/019cc953-ba7c-7421-a28a-04aa21b57df8/substeps?part=019cc953-c565-7461-9901-bcf07e18ebca&execution=019dd9ad-ff32-7302-ab99-6ba5c432ee51&at=0` (real StepExecution + Part bound so Submit actually persists)

### Deferred (noted, not blocked)

- **First-piece flag** (`QualityReports.is_first_piece`) — modelling TBD; defer until form-shape is settled
- **Photo / file / video upload to real `Documents` FK** — today PhotoCapture/FileCapture store filenames only; the browser File object is discarded. `SubstepResponse.value_document` exists in the schema but nothing populates it. First customer who attaches a setup photo will find it doesn't survive. ~1 day of work once Documents upload endpoint is confirmed
- **Drawing / annotation overlay on images** — engineers want to circle bolts and arrow to gaskets on setup photos. Three viable paths: fabric.js modal editor (~1–2 days, +250KB bundle, recommended), custom `<canvas>` toolbar (~1–3 days, no big dep), tldraw/excalidraw embed (~1–2 days, +1–2MB bundle, polished)
- **Translation picker for operator runtime** — `SubstepTranslation` exists; planned alongside an AI-services workstream that auto-translates `body_blocks` to N target languages (capture nodes don't translate — already separated in the JSON shape)
- **Signature canvas widget** — placeholder UI is fine; not in regulated industries
- **`DwiSpikePage` deletion** — delete when production page is rock-solid
- **CAPA → Substep auto-closure** — pitched as integration win; not designed
- **`ProcessChangeRequest.target_substep`** — deferred from Phase 3 due to constraint restructuring
- **Phase 4 (Authoring Approval) vs operator runtime sequencing** — DRAFT guard already shipped (which is the highest-leverage piece of Phase 4); full approval workflow + template seeding can wait until operator runtime tells us what's most useful next
- **Step-advancement gate consuming `SubstepCompletion`** — today the gate is sampling-driven (parts can't advance until sampling completes); substep-completion-driven gating is a future refinement
- **Batch operator runtime** — backend (`Substep.scope`, `BatchExecution`, scoped audit FKs) is shipped; frontend page is still singleton-only. Closing the loop is 2–3 days of UX work: "Start batch" gesture, scope-aware traversal (PARTS_FIRST default, SUBSTEPS_FIRST when authored), BATCH substep barriers
- **`ComputedValue` node sourcing from real measurements / SPC** — today the formula's input variables are typed by the operator. They should be able to bind to actual `MeasurementDefinition` rows on the parent Step (so a "True Position" calc auto-reads X-deviation + Y-deviation from earlier `MeasurementInput` captures in the same substep / step) or to `StepExecutionMeasurement` / SPC data (so derived control-chart values — CPK, range, drift, last-N average — can be displayed live). The variable shape becomes `{ name, source: 'manual' | 'measurement_definition' | 'spc' , source_id?, label, unit }`. ~1 hour of focused work to wire — small node-attr extension + runtime resolver that reads from the existing measurement tables. Useful for closing the loop between operator capture and derived QA checks (True Position, CPK, geometric tolerancing math)
- **`Steps.batch_traversal = PARTS_FIRST | SUBSTEPS_FIRST`** field — needed alongside the batch operator runtime, not before
- **`submit_substep` service accepts `batch_execution`** — today only takes `step_execution`; needs the alternative branch for batch capture audit rows. Trivial extension once the frontend payload supports it
- **Work order page QA Forms tab dissolution** — promised but not done. The standalone `PartQualityForm` should redirect to or embed the operator runtime; out-of-band right now
- **Test coverage** — the new surface (DRAFT guard, role-tagged through tables, structured-capture node persistence, operator submit service, required-field validation, MediaPreview load handling, AuthoringPopover trim, BatchExecution model + migration backfill) has no automated tests. Worth a focused test-writing pass before declaring "done"

### Batch vs per-part substep scope

Real shop floors need both single-piece flow and batch operations on the same Process. The model that fell out of conversation:

**`Substep.scope = SAMPLED | BATCH`** (default `SAMPLED`):
- `SAMPLED` substeps run per part. `sampling_rule` controls cadence — null rule means "every part" (100% sample); a set rule means "only the parts the rule selects." Captures bind to the part's `StepExecution`.
- `BATCH` substeps run once for the whole batch. Captures bind to a new `BatchExecution` row shared by every part in the batch. `sampling_rule` is ignored.

The realization that simplified the model: per-part substeps are just per-sample substeps with a 100% rule. PER_PART, PER_BATCH, and PER_SAMPLE collapse into two: SAMPLED (with cadence via `sampling_rule`) or BATCH.

**`BatchExecution` model** (new in migration `0059`):
- One row per (WorkOrder, Step) when an operator starts a batch
- M2M to `Parts` — mutable until the first BATCH substep fires (`sealed_at` set), locked after
- Owns the audit semantics for batch-level captures: "what was the wash temp for part 17?" joins through the BatchExecution to pick up cycle data, instead of pretending it lives on part 1's StepExecution

**`SubstepCompletion` + `SubstepResponse`** both gained nullable `batch_execution` FKs and a check constraint enforcing "exactly one of step_execution / batch_execution is set." Per-part and per-batch substep audit rows now coexist cleanly.

**Traversal direction** for the operator UX between BATCH barriers (single-piece flow vs station-by-station) lives at the Step level, not the substep — `Steps.batch_traversal` is a follow-up field once the operator runtime is doing real batches. For now the runtime walks parts-first, which is the more common single-piece pattern.

**Mid-batch failure handling is deliberately not a platform concern.** Engineers compose Processes such that per-part inspection substeps catch failures before/after BATCH substeps; the platform doesn't need a `Substep.failure_scope` field. If a heat-treat cycle fails for the whole charge, the engineer's downstream substep (per-part outgoing inspection) catches it on each part naturally.

### Architectural unfair advantages worth leaning on

UQMES bundles DWI + QMS + MES in one schema; competitors sell integration. This unlocks:

- **Single audit chain** from operator gesture → `StepExecution` → `Substep` → `StepExecutionMeasurement` (always) + `QualityReports` (when inspection-point). One query, not a multi-system reconciliation
- **Two-tier measurement** with same-DB UNION into SPC charts — only possible because process data and inspection records share storage
- **Sampling rules drive both Tier 1 and Tier 2** from a single rule. Competitors split AQL between QMS and MES
- **Unified permissions / notifications / tenant scoping** via `SecureModel` + ContextVar across all three subsystems
- **PCR / PCO / PCN can target MES + QMS in one approval workflow**
- **Documents and training** plug directly into authoring (supersede a doc → see every Substep using it in one query)
- **CAPA closure** can validate against floor execution in the same DB (corrective action says "update Substep X" → next passing execution closes the loop automatically)
- **Reman compounds all of the above** — core teardown / harvest / regrade decisions touch MES routing + QMS judgment + DWI instructions in a single transaction

The user-facing pitch: *competitors sell integration; you don't have to.*

---

## Advancement Engine + Lot Cohesion (2026-06-03 → 2026-06-04)

Major workstream built on top of Phase 1-3 DWI substep persistence. Closes
the loop between operator capture and part advancement using a lot-cohesion
model. **Source of truth for behavior is `Documents/MES_BEHAVIOR_FLOWS.md`**
(13 Mermaid flow charts + audit checklist + deferred-items list).

### Models shipped

Migrations `0060_advancement_engine_phase_1` and
`0061_drop_expedite_customer_pull_split_reasons`:

- **`Parts.split_from_cohort` / `split_reason` / `split_at`** + `PartSplitReason`
  enum (`QUARANTINE | REWORK | SCRAP`). EXPEDITE / CUSTOMER_PULL deliberately
  excluded — those bump `WorkOrder.workorder_priority`, not split parts
  (avoids downstream packing/shipping pain when an expedited part has to
  rejoin its siblings at finished goods).
- **`Substep.is_critical`** (safety-critical; N/A impossible even with
  `allow_not_applicable=True`).
- **`Substep.allow_not_applicable`** (engineer-side opt-in for the N/A path).
- **`SubstepCompletion` inherits `VoidableModel`** + new `na_reason_code` field.
- **`SamplingDecision`** — append-only per (StepExecution, Substep) with
  `outcome` enum (SELECTED/DESELECTED/PENDING), `ruleset_version`,
  `decided_at`, `superseded_by` chain. Live-row uniqueness constraint.

### Services shipped

- `Tracker/services/dwi/sampling_decisions.py` — `evaluate_substep_sampling`
  writes per-substep decisions on StepExecution creation. Handles
  EVERY_NTH_PART, FIRST_N_PARTS, PERCENTAGE, RANDOM, LAST_N_PARTS/EXACT_COUNT
  (→ PENDING). Hooked into all three `advance_part_step` paths.
- `Tracker/services/dwi/advancement_gate.py` — `substep_completion_blockers`
  reads decisions + completions + sealed batches. Wired into
  `Steps.can_advance_from_step` as blocker #7. Re-validates N/A at gate
  time so retroactive `is_critical=True` edits invalidate prior N/A rows.
- `Tracker/services/mes/splits.py` — `split_part_from_lot` service. Reason-
  coded, audit-logged, one-way. Rework flavor closes current StepExecution
  as ROLLED_BACK, moves Part to `rework_target_step`, creates fresh
  StepExecution with bumped `visit_number`, writes fresh SamplingDecisions.
- `Tracker/services/mes/advancement.py` — `try_advance_lot(wo_id, step_id)`
  evaluates cohort all-or-none + split parts solo, returns structured
  result with per-part blockers.
- `Tracker/services/dwi/batch_lifecycle.py` — `seal_batch` validates
  one-WO invariant + required cohort completions, stamps `sealed_at`,
  fires advancement.

### Viewsets / endpoints shipped

- `POST /api/Parts/{id}/split_from_lot/` — manual split lever
- `POST /api/Parts/advance_lot/` — lot-cohesion advance
- `POST /api/BatchExecutions/{id}/seal/` — seal action
- `GET /api/BatchExecutions/` — list / retrieve
- `GET /api/SamplingDecisions/?step_execution=<id>` — read-only; live
  decisions by default; `?include_superseded=1` for audit trail
- `submit_substep` extended to accept `na_reason_code`; rejects invalid N/A
  at API boundary

### Frontend shipped

**Supervisor slice (WorkOrder Control page):**
- `useSplitPartFromLot` / `useAdvanceLot` hooks
- Per-part dropdown: Split for rework / Split — quarantine / Split — scrap
  (replaces the old status-only items)
- Force-advance affordances perm-gated to production_manager / qa_manager
  / tenant_admin / is_staff / is_superuser. Default operators see "N ready"
  chip instead of clickable button.
- Blocker visibility: failure banner surfaces engine's per-part blocker
  reasons (substep not completed, quarantine, FPI, etc.) deduplicated.

**Operator runtime slice:**
- `useSamplingDecisionsForExecution` + `buildOutcomeMap` hook
- DESELECTED substeps render with "Not in sample" badge + dimmed row
  (kept VISIBLE per IATF-audit defensibility — the operator sees what
  they didn't do, but not why they were sampled out; that's documented
  in the substep body if relevant).
- N/A reason-code dialog: button in SubstepStage header when
  `allow_not_applicable=True && !is_critical`; 5 common reason chips +
  free-text fallback; submits `marked_not_applicable=true` + `na_reason_code`.
- `BatchPanel` component renders when step has BATCH-scope substeps;
  shows open + sealed batches; "Start batch with cohort" button;
  per-batch Seal action.
- Photo / file uploads create real `Documents` rows via
  `useDocumentUpload` + `POST /api/Documents/`; SubstepResponse.value_document
  FK lands on real Documents IDs.

**Authoring slice:**
- Substep editor properties row: `Critical` + `Allow N/A` switches.
  Flipping Critical clears + disables Allow N/A so the UI can't contradict.

### Behavior spec — `MES_BEHAVIOR_FLOWS.md`

Source of truth for how UQMES *should* behave. Key design decisions:

1. Advancement is operator-driven and **synchronous** — no Celery
   cascade, no event fan-out. Operator's "Complete step" runs the gate
   in the same request and returns the result inline.
2. **Lot cohesion** by default — non-split parts at (WO, Step) advance
   together, all-or-none. Splits travel solo.
3. **Out-of-spec is a flag, not a forced action.** Operator sees toast,
   continues. System creates QualityReports row only when
   `is_inspection_point=True`. QA dispositions — operator is not
   authorized.
4. **DESELECTED substeps are visible** (badged, dimmed). Hiding them
   fails IATF audit defensibility.
5. **One BatchExecution per WO.** Multi-WO oven cycles produce N rows;
   cycle data is replicated; audit trail stays crisp.
6. **PENDING blocks at terminal steps only.** Mid-flow non-blocking;
   at `is_terminal=True` it's a hard blocker — supervisor reconciles
   before shipment.
7. **Containment is QA-driven via CAPA + QualityReports list page**,
   not an automatic cascade. Existing tooling covers it.
8. **AQL switching is ANSI/ASQ Z1.4** — 2 of 5 lots rejected →
   Tightened; 5 consecutive accepts → Normal. Modeled via
   `SamplingRuleSet.fallback_ruleset` + supersession chain.

### Audit findings (against MES_BEHAVIOR_FLOWS.md §13, performed 2026-06-04)

**Over-built (6 strips required) — Celery cascade was v0 over-engineering:**
- `Tracker/services/mes/advancement_tasks.py` — delete entirely
- `submit_substep` (`operator_capture.py:238-240`) fires `fire_for_part`
- `seal_batch` (`batch_lifecycle.py:97`) calls `.delay()` — make synchronous
- `split_part_from_lot` (`splits.py:133-134`) fires `fire_for_part`
- `approve_step_override` (`step_override.py:51-52`) fires `fire_for_part`
- `try_advance_lot_task` recursive cascade (`advancement_tasks.py:51-64`)

**Under-built (5 builds required):**
- **Flow #2:** Operator "Complete step" doesn't run the gate. Today
  advancement only happens via the (over-built) Celery cascade. After
  strip, "Complete step" needs to call `try_advance_lot()` directly.
- **Flow #3:** No out-of-spec operator toast.
- **Flow #9 blocker #8:** PENDING-at-terminal-step blocker missing
  in `advancement_gate.py`.
- **Flow #10:** No QA void affordance in the UI (model has the field).
- **Flow #11:** No supervisor-side review UI for PENDING reconciliation
  / superseded decisions at terminal steps.

**Aligned (verified correct):**
- Substep submit with N/A validation
- PartSplitReason enum trimmed correctly
- Rework split routes + visit_number bump
- Force-advance perm-gated
- One-WO-per-batch invariant validated
- SamplingDecision write logic per rule type; DESELECTED badged (not hidden)
- Gate blocker order
- VoidableModel inheritance + `is_voided` filter
- Append-only `superseded_by` chain

### Deferred items (real customer needs, scoped out)

| Item | Reason |
|---|---|
| OOS operator reason-code prompt | Awaiting customer pull |
| Pre-capture gauge calibration check | Separate calibration-gating push |
| Part reclassification / substitute PartType | Reman-specialized push |
| SPC analytics reading both measurement tables | Analytics-layer work |
| End-of-shift handoff / andon / kanban | Operational, outside DWI |
| External integrations (ERP, printers, andon broadcast) | Integrations track |

### Next-step plan (~5-6 days to clear audit checklist)

1. **Wire Flow #2** — "Complete step" calls `try_advance_lot()`
   synchronously; returns blockers inline (½ day)
2. **Strip 6 Celery cascade points** — replace `.delay()` and
   `fire_for_part` with synchronous calls; delete `advancement_tasks.py`
   (½ day)
3. **Add Flow #9 blocker #8** (PENDING at `is_terminal=True`) (¼ day)
4. **Add Flow #3 out-of-spec toast** (¼ day)
5. **Build Flow #10 QA void UI** — button on part traveler / step history;
   reason field; calls `completion.void(user, reason)` (½ day)
6. **Build Flow #11 supersession review UI** — supervisor reconciliation
   screen (1 day)
7. **Test coverage** — port 28 sandbox cases from
   `scratch_advancement_gate.py` as Django integration tests (2-3 days)

### Documentation pointers

- **Behavior spec (source of truth):** `Documents/MES_BEHAVIOR_FLOWS.md`
- **Sandbox (28 design cases):** `PartsTracker/scratch_advancement_gate.py` —
  throwaway when port lands
- **Reman integration:** `Documents/REMAN_DWI_INTEGRATION.md`
- **Feature inventory:** `Documents/FEATURE_INVENTORY.csv`