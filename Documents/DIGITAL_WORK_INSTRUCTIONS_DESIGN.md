# Digital Work Instructions (Substep) Design

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
| `MeasurementInput` | `StepExecutionMeasurement` | Optional FK to `MeasurementDefinition`; range validation via existing model |
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

- **Out-of-spec readings** on `MeasurementInput` or `ComputedValue`. Operator captured honestly; downstream SPC / CAPA pipeline handles disposition. Engineers who need "supervisor disposition before proceeding on out-of-spec" author a separate `AttestationCheckpoint(kind='signature')` gated by the deferred Level-2 `applies_when` SPC-state condition.
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

### Phase 3 — Substep-aware measurements & requirements

**Modified:**
- `StepExecutionMeasurement` — add nullable `substep` FK
- `StepMeasurementRequirement` — add nullable `substep` FK
- `StepRequirement` — add nullable `substep` FK
- `ProcessChangeRequest` — add nullable `target_substep` FK + `CheckConstraint(exactly one of target_process / target_step / target_substep)`

**Backfill:** none — all new FKs are nullable; null means "applies at the parent Step level," matching today's behavior.

Phase 3 has the only schema change that touches code paths outside DWI (the existing measurement / requirement gate logic now optionally scopes to a substep). Worth a focused PR even if shipping alongside Phase 1.

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

## Out of scope (belongs to other subsystems)

These are commonly mentioned features in DWI tools / connected-worker platforms that this design intentionally does **not** own. Each belongs to a separate subsystem.

- **Skill / certification gating** ("only operators with this training can perform this substep") — belongs in the Training tracking architecture. DWI substeps may reference `TrainingType` requirements, but the gating logic, training records, recertification cadence, and the skill matrix UI all live in the Training subsystem. Substep-level enforcement would call into a training service, not implement its own.
- **Tool / IO integration** (torque wrenches, scanners with feedback, andon lights, pick-to-light, vision-system signals) — belongs in the Equipment / IO integration layer. DWI gates can *consume* signals from this layer when present, but the device drivers, MQTT/OPC bridges, and equipment-state propagation live elsewhere.
- **Real-time SPC / control charts** — `MeasurementInput` writes to `StepExecutionMeasurement` which already feeds the existing SPC subsystem. Charts and rule alarms are SPC concerns, not DWI.
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

---

## Investigation needed

- **Reman ↔ DWI integration.** Reman teardown adds enough surface (Core flow through Steps, per-Core substep captures, `HarvestedComponentCapture` custom node, auto-coordination between Core lifecycle and WO state, batch-of-cores UX) to warrant its own design doc. See `Documents/REMAN_DWI_INTEGRATION.md` for the full design — `StepExecution` two-FK extension, `Core.step` field, `advance_core_step` service mirror of `advance_part_step`, `start_teardown` service, the capture-node spec, and the 5-phase migration plan. Estimated 2–3 weeks of focused work for R1–R4 (the "ship reman DWI" milestone).

## Still Open

- **Signature blob format on the wire** — image data URI vs. SVG path? Recommend matching whatever `ApprovalResponse.signature_data` currently accepts (Base64 PNG per its help_text) for consistency.
- **CAPA-style password re-verification** — `complete_capa_task` accepts a `password` param. Should substep signoff require the same when `requires_signature=True`? Default to yes for parity, can relax later.
- **`SubstepResponse.unique_together` for team-based steps** — keep `(step_execution, substep, node_id)` as-is. `StepExecution` is per-part (`mes_lite.py:1141`: `part = ForeignKey('Parts')`), so per-part captures already work naturally — each part has its own `StepExecution` row, so different parts never collide on the composite key. The constraint only fires on accidental dual-tab / dual-tablet writes on the same part execution, where first-write-wins + visible 400 is the right behavior. If per-part captures from a single execution are ever needed (e.g. batch operations where one execution row handles multiple parts — not the current model), the fix is adding a nullable `part` FK rather than relaxing the constraint.
- **`generateHTML()` output quality for PDF / email** — each custom node's `renderHTML()` currently produces minimal text fallback. Either improve `renderHTML()` per node, or accept that PDF rendering goes through a different path. Decide before building the PDF export workstream.
- **`SubstepResource` UI placement** — equipment / tool / PPE list could be (a) a custom node inside the substep `body_blocks`, or (b) a separate panel rendered alongside the substep view. Data model leaves both options open; pick at production-UI time.