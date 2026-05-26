# Digital Work Instructions (Substep) Design

## Overview

Adds a substep layer below the existing `Steps` (Op) model to support Dozuki-style digital work instructions: rich content per substep, resource callouts, mandatory acknowledgment/signoff, per-substep measurement capture, and per-substep change control.

**Scope:** ORM models, serializers, viewsets, service layer. Frontend authoring/execution UI and blob storage are out of scope here.

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
| 1 | Execution snapshot policy | Snapshot at start; in-flight migration via existing `ProcessChangeMigrationDisposition` | Audit-defensible by default; reuses existing PCO-time disposition (KEEP_ALL / MIGRATE_ALL / MIGRATE_SELECTED) |
| 2 | Versioning unit | Process-level only | Matches existing versioning; no third axis |
| 3 | Content storage | Hybrid: JSON prose + FKs for queryables | Editor maps cleanly; measurements/resources/documents stay queryable |
| 4 | Resources | `SubstepResource` → `EquipmentType` / `MaterialType` / `PPEType` | Authoring references classes, execution binds instances |
| 5 | Execution grain | Per-substep `SubstepCompletion` rows | Per-substep timing, mandatory-ack, signoff tracking |
| 6 | Translations | `SubstepTranslation` rows now, no UI yet | Data model right from day one; avoids destructive migration later |
| 7 | Reuse | Op-owned + provenance fields now; `LibrarySubstep` deferred | Cheapest option that keeps the library door open |
| 8 | Substep ordering | Author chooses per Op (`sequencing_mode` on `Steps`) | Sequential vs. free-order picked at authoring time |
| 9 | PCN targeting | Three nullable FKs on `ProcessChangeRequest` | Explicit, easy joins, no GFK pain |
| 10 | Signoff | Per-substep `requires_signature` flag; `SubstepCompletion` reuses `signature_data`/`verification_method`/`ip_address` pattern from `CapaTasks` | Matches existing pattern operators see in CAPA closure; no new signature primitive |
| 11 | Conditionals | Defer; `is_optional` flag only | Avoids speculative rules engine |

---

## Data Model

### New Models

#### `Substep`

```python
class Substep(SecureModel):
    step = ForeignKey('Steps', related_name='substeps')           # parent Op
    order = PositiveIntegerField()                                # within the Op
    title = CharField(max_length=200)
    body_blocks = JSONField(default=list)                         # TipTap/BlockNote-style blocks
    is_optional = BooleanField(default=False)                     # operator may mark N/A
    requires_ack = BooleanField(default=False)                    # operator must acknowledge
    requires_signature = BooleanField(default=False)              # signature + verification on completion
    # Provenance (for future LibrarySubstep; nullable always)
    source_library_substep_id = PositiveIntegerField(null=True)   # forward-compatible
    source_library_version = PositiveIntegerField(null=True)
```

Versioning: substeps participate in the parent Process version. New versions are created via `Processes.create_new_version()` per existing versioning architecture.

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

### PCN propagation policy

In-flight work is handled by the existing PCO implementation flow
(`services/change_control/impact_analysis.py` + `ProcessChangeMigrationDisposition`):

- `KEEP_ALL`: in-flight WOs continue against the version they started; subsequent WOs use the new version. Existing `SubstepCompletion` rows are untouched.
- `MIGRATE_ALL`: in-flight WOs are migrated to the new Process version per existing migration logic. New `SubstepCompletion` rows on the new version are created from that point; the substep-design layer does not add new behavior here.
- `MIGRATE_SELECTED`: implementer chooses per-WO; substeps follow the WO's disposition.

No mid-execution version switch ("IMMEDIATE") is supported — by design.
The migration is always at WorkOrder boundaries, never mid-Op.

### Sequencing enforcement

- `SEQUENTIAL`: service layer rejects a `SubstepCompletion` for substep N if substep N-1 has no completion (or is optional and not yet marked N/A). Substep-scoped measurement gates (`StepMeasurementRequirement.substep` set) also block at substep completion time — operator can't proceed past a substep with an unsatisfied measurement requirement.
- `FREE_ORDER`: any substep may be completed in any order. Substep-scoped measurement gates block at Op completion only (no per-substep enforcement, since prerequisite ordering isn't meaningful here). Op signoff checks that all required (i.e. `not is_optional`) substeps have completions and that all gate requirements are satisfied.

---

## Service Layer

New module: `Tracker/services/mes/substeps.py`

Public functions:
- `complete_substep(step_execution_id, substep_id, user_id, *, signature_data=None, signature_meaning=None, password=None, ip_address=None, notes='', mark_not_applicable=False)` — validates sequencing, signature requirements, records `SubstepCompletion`. Signature/password flow mirrors `services.qms.capa.complete_capa_task`.
- `void_substep_completion(completion_id, user_id, reason)` — soft-delete via `VoidableModel.void()`.
- `can_complete_op(step_execution_id) -> bool` — checks that all required substeps are complete and all measurement gates satisfied; called by existing Op-completion service.

No new entry points in `Tracker/services/change_control/` — substep in-flight behavior rides the existing PCO migration disposition flow.

---

## Migration Plan

Single migration adds all new models + new fields. No data backfill required (substeps are net-new; existing `StepExecution`s simply have no substep completions).

Optional follow-on: a management command to materialize default substeps from any existing free-text instruction fields on `Steps`, if such fields exist.

---

## Deferred Items

Explicitly out of v1 scope; design accommodates future addition:

- `LibrarySubstep` model + "insert linked" authoring flow (provenance fields already present)
- Conditional / skip-rule substeps (no `condition` field; add when needed)
- Translation authoring UI (table exists; UI is later)
- `MaterialType`, `PPEType` (referenced as nullable FKs; can be added incrementally)
- Per-substep effectivity dates (PCN handles version transitions today)
- Operator-facing mobile execution UI (separate doc)

---

## Resolved Open Questions

1. **Signature format** — Resolved. Reuse the explicit-field pattern from `ApprovalResponse` and `CapaTasks` (`signature_data`, `signature_meaning`, `verification_method`, `verified_at`, `ip_address`). No new signature primitive. `DIGITAL_SIGNATURES.md` covers PDF report signing — a separate concern.
2. **Measurement gate enforcement** — Resolved. Block at substep when `sequencing_mode=SEQUENTIAL`; block at Op completion when `FREE_ORDER`. See Sequencing enforcement above.
3. **In-flight propagation** — Resolved. Reuse existing `ProcessChangeMigrationDisposition` and PCO implementer disposition flow. No new substep-level policy. Mid-execution version switch ("IMMEDIATE") explicitly not supported.
4. **Per-substep analytics / OEE** — Deferred to a separate `Documents/DWI_ANALYTICS_DESIGN.md` once the core system is in use. v1 ships raw `completed_at` timestamps only; aggregation, pause detection, and dashboards are follow-on work.

## Still Open

- **Signature blob format on the wire** — image data URI vs. SVG path? Recommend matching whatever `ApprovalResponse.signature_data` currently accepts (Base64 PNG per its help_text) for consistency.
- **CAPA-style password re-verification** — `complete_capa_task` accepts a `password` param. Should substep signoff require the same when `requires_signature=True`? Default to yes for parity, can relax later.