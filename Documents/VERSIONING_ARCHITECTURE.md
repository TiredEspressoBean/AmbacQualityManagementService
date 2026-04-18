# Versioning Architecture

**Last Updated:** April 2026
**Status:** Pre-refactor planning — consolidates all findings from
architecture review sessions.

This document is the single source of truth for which models get
explicit versioning, which stay audit-log-only, and what
implementation concerns exist. Used as input for the services
refactor and for future review agent passes.

---

## Regulatory grounding

The versioning decisions are grounded in:

| Source | What it covers | Strength |
|--------|---------------|----------|
| ISO 9001 clause 4.4 | "Maintain documented information" for process descriptions, work instructions, specs | Strong — auditor-checkable |
| ISO 9001 clause 7.5 | Document control requirements for "maintained" info | Strong |
| IATF 16949 clause 8.5.6.1 | Change control for automotive production processes | Strong for auto |
| AS9100D clause 8.1.2 | Configuration management for aero (baselines, change control) | Strong for aero |
| MIL-STD-31000 (TDP) | Technical Data Package elements — drawings, BOMs, process specs, QA provisions, tooling | Strong for defense |
| EIA-649 / MIL-HDBK-61A | Configuration item identification, change control, status accounting | Strong for defense |
| AIAG PPAP manual | What's in a PPAP submission (implicitly defines controlled specs) | Strong for auto |
| NIST SP 800-53 CM-3 | "Organization determines what needs change control" — punts to org | Weak for app data |
| NIST SP 800-171 / CMMC L2 | IT system config management only — not applicable to app-level data | Not applicable |

**Key distinction (ISO 9001 7.5):**
- "Maintain documented information" = controlled specs (living documents, versioned)
- "Retain documented information" = records (evidence of what happened, audit-logged, not versioned)

**NIST/CMMC does NOT prescribe application-level data versioning.** Those frameworks cover IT infrastructure config management. Your customer applies CMMC controls to their deployment, not to your data models.

---

## Critical design issue: is_current_version conflation

**SEVERITY: CRITICAL — must resolve before implementing versioning on any more models.**

The existing `SecureModel` has `is_current_version` (bool) which gets set to `False` when a new version is created. But this conflates two concepts:

- **"Latest in chain"** — the newest version of this entity (may be DRAFT)
- **"Effective/approved"** — the version that production should use (APPROVED status)

When `Processes.create_new_version()` creates a draft v2 from approved v1, it sets v1's `is_current_version=False`. Code that filters `is_current_version=True` to find the approved process now returns nothing — the approved v1 is hidden.

**Resolution options:**
1. Separate `is_latest_version` (auto-managed) from `is_effective` (status-driven)
2. Status-aware query method: `Process.objects.effective()` returns latest with status=APPROVED
3. Keep `is_current_version` as "latest" and never use it alone — always pair with status filter

This affects: Processes, BOM, Steps, and any model with an approval lifecycle.

**Known locations that query `is_current_version=True` and will break:**
- `Processes.get_available()` at `mes_lite.py:460`
- `csv_import.py:488` — process lookup during import

---

## Critical: Bugs in the reference implementation (Processes.create_new_version)

**Found by third-pass review. These bugs will propagate to every new
override patterned after the Processes implementation.**

1. **`created_by=user` — field doesn't exist.** `Processes` and
   `SecureModel` have no `created_by` field. Passing it to
   `Processes.objects.create()` would raise `TypeError` at runtime
   if called with a non-None user. (mes_lite.py:368)

2. **`tenant` is not copied.** The new version gets `tenant=None`
   (SecureModel default). This is a data corruption bug — new
   versions silently lose their tenant scoping.

3. **`category` is not copied.** Gets the model default
   (`MANUFACTURING`) instead of the original's value.

4. **Archived models can still be versioned.** The
   `create_new_version()` check only looks at `is_current_version`,
   not `archived`. An archived (soft-deleted) model with
   `is_current_version=True` could be versioned, creating a new
   active version from a deleted parent.

5. **No `transaction.atomic()` AND no row-level lock.** Neither
   `SecureModel.create_new_version()` (core.py:1130) nor
   `Processes.create_new_version()` (mes_lite.py:326) wraps the
   two-step operation in a transaction, AND does not `SELECT FOR
   UPDATE` on the source row. Two failure modes:

   - **Partial failure:** Step 1 marks old version non-current. Step
     2 fails. Old version left with `is_current_version=False` and
     no new version exists. Data loss on failure.
   - **Concurrent write-skew:** Under Postgres default isolation
     (READ COMMITTED), two concurrent `create_new_version()` calls
     on the same v1 both observe `is_current_version=True`, both
     write False, both create v2. Result: two competing v2s, broken
     version chain.

   `transaction.atomic()` alone does NOT prevent the write-skew
   scenario. Fix requires `select_for_update()` on the source row
   inside the atomic block, or a conditional UPDATE with affected-
   rows check (optimistic lock on `is_current_version`).

   **Pattern already exists in the codebase:** `mes_lite.py:1534`
   and `mes_standard.py:1089` (`MaterialLot.consume`) use
   `select_for_update()`. Apply the same pattern to versioning.

6. **`archived` and `deleted_at` are copied to new versions.** The base
   `SecureModel.create_new_version()` exclusion list at core.py:1142 is
   `['id', 'created_at', 'version', 'previous_version', 'is_current_version']`.
   It does NOT exclude `archived` or `deleted_at`. If versioning is ever
   called on a record where `archived=True` (guarded against by bug #4
   but defense-in-depth), the new version inherits `archived=True` and
   `deleted_at=<timestamp>`, born soft-deleted. Add `'archived'` and
   `'deleted_at'` to the exclusion list.

7. **`get_version_history()` has O(N) queries and no cycle protection.**
   core.py:1152-1169 walks backward via `root.previous_version` (lazy FK
   loads = one query per version) then forward with
   `objects.filter(previous_version=current).first()` (one query per
   version). Total: 2N queries for a chain of N versions. Additionally,
   there is no cycle detection — a data corruption loop in
   `previous_version` causes an infinite loop. Add a `seen` set and
   consider prefetch or a single query with recursive CTE.

8. **UniqueConstraints block `create_new_version()` on 6+ models.**
   `create_new_version()` copies field values to a new row. If the
   model has a `UniqueConstraint` that doesn't include `version`,
   the new row raises `IntegrityError`. Affected models:
   - BOM: `UniqueConstraint(fields=['tenant', 'part_type', 'revision', 'bom_type'])`
   - LifeLimitDefinition: `UniqueConstraint(fields=['tenant', 'name'])`
   - DocumentType: `UniqueConstraint(fields=['tenant', 'name'])` AND `['tenant', 'code']`
   - ApprovalTemplate: `UniqueConstraint(fields=['tenant', 'template_name'])` AND `['tenant', 'approval_type']`
   - DisassemblyBOMLine: `unique_together = ['core_type', 'component_type']`
   - MilestoneTemplate: `UniqueConstraint(fields=['tenant', 'name'])`

   Fix: add `condition=Q(is_current_version=True)` to make them
   partial unique constraints (only enforce among current versions),
   or add `version` to every unique constraint on versioned models.

**All eight must be fixed in the refactor before extending the
pattern to other models.**

---

## Versioned models (23 total)

### Composite models (specialized create_new_version with child copy)

These have child rows that must be preserved as a set when the parent versions.

**All composite models must ALSO copy their `GenericRelation`
children** (Documents via `GenericRelation('Tracker.Documents')`,
ApprovalRequest instances via GFK `content_type + object_id`).
The existing `Processes` reference implementation does NOT do this —
it's a gap that applies to every composite. See Implementation
Concerns → "GenericRelation children not copied to new versions."

| # | Model | Children to copy | Grounding | Notes |
|---|-------|-----------------|-----------|-------|
| 1 | **Processes** | ProcessStep, StepEdge, documents (GenericRelation) | ISO 9001 4.4, MIL-STD-31000 | Reference implementation exists but does NOT copy GenericRelation children — gap must be fixed. |
| 2 | **Steps** | StepMeasurementRequirement, StepRequirement, TrainingRequirement (step-linked) | ISO 9001 4.4, MIL-STD-31000 | Agent review found StepRequirement and TrainingRequirement must be copied too — not just StepMeasurementRequirement. |
| 3 | **BOM** | BOMLine | ISO 9001 4.4, MIL-STD-31000 | BOMLine.component_type FK to PartTypes — historical BOMs will reference old PartType versions. Queries must not filter `is_current_version=True` when resolving BOMLine components. |
| 4 | **ApprovalTemplate** | default_approvers M2M, default_groups M2M | MIL-HDBK-61A (CCB process definition) | Defines who approves what. **Children are M2M relationships** (not FK rows like other composites). Copying requires M2M through-table copy, not FK row copy. ApproverAssignment and GroupApproverAssignment are children of ApprovalRequest, NOT ApprovalTemplate. |
| 5 | **SamplingRuleSet** | SamplingRule | ISO 9001 4.4, AIAG PPAP #7 | Has FKs to PartTypes, Processes, Steps — all versioned. Versioning a parent does NOT auto-version the SamplingRuleSet. **CAUTION: Has its own supersession mechanism** (`supersedes` OneToOneField, `active` flag, `supersede_with()` method at mes_standard.py:415) — same dual-versioning problem as SPCBaseline. Must unify. |
| 6 | **LifeLimitDefinition** | PartTypeLifeLimit | AS9100D (aero) | Aero-specific life-limit specs. |
| 7 | **MilestoneTemplate** | Milestone children | Engineering judgment | Agent review found this is composite — Milestone instances reference the template. Orders reference Milestones. If template versions without copying Milestones, Orders lose milestone tracking. |

### Leaf controlled documents

No meaningful child relationships — versioning the row itself is sufficient.

| # | Model | Grounding | Notes |
|---|-------|-----------|-------|
| 8 | **PartTypes** | ISO 9001 4.4, MIL-STD-31000 | Part master definition. Version field from SecureModel serves as revision. |
| 9 | **MeasurementDefinition** | ISO 9001 4.4, MIL-STD-31000 | Measurement spec (nominal, tolerances, unit). Note: also FK'd from StepMeasurementRequirement which crosses two versioned parents. See implementation concerns. |
| 10 | **EquipmentType** | MIL-STD-31000 (special tooling/inspection equipment) | Equipment type master. |
| 11 | **Equipments** | MIL-STD-31000 (special tooling/inspection equipment), AIAG PPAP #16 | Individual asset records. Important for PPAP Checking Aids traceability. |
| 12 | **QualityErrorsList** | Engineering judgment | Defect catalog. "When did you add this defect code?" is a real audit question. |
| 13 | **TrainingType** | Engineering judgment | Training curriculum spec. "What training was required when this part was made?" |
| 14 | **SPCBaseline** | AIAG PPAP #11 | **CAUTION: Has its own supersession mechanism** (superseded_by, superseded_at, status=ACTIVE/SUPERSEDED) that conflicts with SecureModel versioning. The create_new_version() override MUST call the existing supersession logic, or one mechanism should be chosen and the other removed. |
| 15 | **DisassemblyBOMLine** | Engineering judgment | Reman yield specs. |
| 16 | **Companies** | Engineering judgment | Customer/supplier master. Supplier qualification status changes matter for ASL. |
| 17 | **WorkCenter** | Engineering judgment | Work center definitions. Capacity/routing master data. |
| 18 | **MaterialLot** | Engineering judgment | **CAUTION: Hybrid model.** Spec fields (supplier cert, expiration, material type) should trigger versioning. quantity_remaining changes on every consumption and should NOT trigger a new version. Needs selective trigger. |
| 19 | **ThreeDModel** | Engineering judgment | Part of product definition. See HeatMapAnnotations concern below. |
| 20 | **DocumentType** | IATF 7.5.3, AS9100D 7.5.3.2 | Defines requires_approval, retention periods. Silent toggle of requires_approval is a document control gap. Added by first agent review. |
| 21 | **Shift** | Engineering judgment (DCAS labor audits) | Shift start/end times referenced by ScheduleSlot and TimeEntry. On cost-plus defense contracts, auditors review labor charging against shift definitions. Added by first agent review. |

### Models that moved from leaf to junction (corrections from agent reviews)

These were originally listed as leaf models but are actually children of composite parents:

| Model | Originally listed as | Corrected to | Parent |
|-------|---------------------|-------------|--------|
| **StepRequirement** | Leaf #17 | Junction — copied by Steps | Steps |
| **TrainingRequirement** | Leaf #13 | Junction — copied by parent Step/Process | Steps, Processes (cross-cutting) |

TrainingRequirement is complex: it links TrainingType to Step OR Process OR EquipmentType via FK. All three targets are versioned. When Steps or Processes version, TrainingRequirement rows pointing at the old version need to be copied. Ownership rules must be defined — probably copy when the Step versions (since that's the most specific context).

### Junction tables (versioned via parent, not independently)

**Note:** ProcessStep, StepEdge, and StepMeasurementRequirement are
**plain `models.Model`**, not SecureModel. They have no `version`,
`previous_version`, `is_current_version`, `tenant`, or `archived`
fields. This is fine for bulk-copy junctions — they're created fresh
when the parent versions. But they don't participate in SecureModel's
versioning infrastructure directly.

| Junction | Parent | Notes |
|----------|--------|-------|
| ProcessStep | Processes | Already implemented. Plain models.Model. |
| StepEdge | Processes | Already implemented. Plain models.Model. |
| StepMeasurementRequirement | Steps | Plain models.Model. Crosses two versioned parents (Steps AND MeasurementDefinition). See implementation concerns. |
| StepRequirement | Steps | Added by second agent review. |
| BOMLine | BOM | BOMLine.component_type FK to PartTypes — references old PartType version, which is correct. |
| SamplingRule | SamplingRuleSet | If SamplingRule has FK to other versioned models (PartTypes), copied rules should reference the same PartType version that was current at copy time. |
| PartTypeLifeLimit | LifeLimitDefinition | — |
| TrainingRequirement (step-linked) | Steps | Cross-cutting junction — also linked to TrainingType and EquipmentType. |
| Milestone | MilestoneTemplate | Added by second agent review. |

---

## Already has own versioning — leave alone

- **Documents** — custom `create_new_version()` wired into file upload flows in viewsets/core.py

---

## NOT versioned (audit-log only)

These are records of what happened, not controlled specs. django-auditlog captures changes.

### Event/workflow records
- QualityReports, QualityReportDefect, MeasurementResult
- StepExecution, StepExecutionMeasurement, StepTransitionLog
- QuarantineDisposition (**add immutability enforcement on closed records** — prevent disposition_type changes after closure)
- CAPA, CapaTasks, CapaVerification, RcaRecord, FiveWhys, Fishbone, RootCause, CapaStatusTransition, CapaTaskAssignee (**add immutability enforcement on closed CAPAs** — prevent problem_statement/immediate_action changes after closure)
- FPIRecord, QaApproval, EquipmentUsage
- CalibrationRecord (**should snapshot equipment_version integer at recording time**)
- TrainingRecord
- LifeTracking
- Core (reman — receipt/teardown record)
- HarvestedComponent (reman — component-level teardown record)

### Transaction records
- Parts, WorkOrder, Orders
- Milestone (instance — template is versioned)
- ScheduleSlot, DowntimeEvent, TimeEntry
- MaterialUsage, AssemblyUsage

### Audit/meta records
- StepOverride, RecordEdit, StepRollback, BatchRollback
- SamplingTriggerState, SamplingAuditLog, SamplingAnalytics
- HeatMapAnnotations (**should store model_version integer** to detect geometry mismatch when ThreeDModel versions)
- GeneratedReport
- ApprovalRequest, ApprovalResponse (signed records — should be append-only)
- ArchiveReason
- ExternalAPIOrderIdentifier

### Identity/config
- User (**export_control field changes should require approval workflow** per ITAR — currently mutable without formal review)
- Tenant, TenantGroup
- PermissionChangeLog (**currently a plain Model, not SecureModel** — can be hard-deleted, destroying the audit trail. Should be append-only with no delete capability. CMMC gap.)
- NotificationTask (plain Model, not SecureModel — operational, no versioning concern)

### Integrations app (out of scope for versioning)

The `integrations/` app contains models that are NOT SecureModel
subclasses and do not participate in the versioning system:

- IntegrationConfig — **credential rotation leaves no audit trail** since it's not SecureModel and not registered with django-auditlog. For CMMC, credential lifecycle should be logged.
- IntegrationSyncLog, ProcessedWebhook — operational logs
- HubSpotPipelineStage, HubSpotOrderLink, HubSpotCompanyLink — link/sync models
- HubSpotOrderSync (in Tracker/models/integrations/) — sync state

None need versioning. IntegrationConfig needs auditlog registration.

---

## Implementation concerns

### FK version-pinning at execution time

When execution records (StepExecution, StepExecutionMeasurement, WorkOrder, CalibrationRecord) reference versioned specs, the FK must point to the **specific version** that was current at execution time, not "the latest."

| Execution record | FK to versioned model | Current state | Recommendation |
|-----------------|----------------------|---------------|----------------|
| WorkOrder.process | Processes | FK only — no version snapshot | Add `process_version` integer field |
| StepExecutionMeasurement.measurement_definition | MeasurementDefinition | FK only | Add `measurement_definition_version` integer |
| CalibrationRecord.equipment | Equipments | FK only | Add `equipment_version` integer |

### StepMeasurementRequirement crosses two versioned parents

StepMeasurementRequirement links Steps (versioned) to MeasurementDefinition (versioned). It also has its own override fields (tolerance overrides, characteristic_number).

Options:
1. Always copy when EITHER parent versions (complex, potentially noisy)
2. MeasurementDefinition cannot version independently — always version the parent Step when measurement specs change (simpler but couples the two)
3. StepMeasurementRequirement carries both version references and execution records snapshot both

Recommendation: Option 2 is simplest. A tolerance change IS a Step change.

### SPCBaseline dual versioning

SPCBaseline has its own supersession mechanism (superseded_by, superseded_at, status=ACTIVE/SUPERSEDED) plus SecureModel's versioning fields. These will conflict.

Options:
1. Remove SPCBaseline from the SecureModel versioning list — rely on its existing supersession mechanism
2. Migrate the supersession mechanism to use SecureModel's versioning — replace superseded_by/at with previous_version/is_current_version
3. Override create_new_version() to call the existing supersession logic

Recommendation: Option 2 — unify on one mechanism during the refactor.

### SamplingRuleSet dual versioning

**Same problem as SPCBaseline.** SamplingRuleSet (mes_standard.py:380)
also has its own `supersedes` OneToOneField, `active` flag, and
`supersede_with()` method (line 415). This is the same conflation
of two versioning mechanisms on one model. Must unify alongside
SPCBaseline.

### MaterialLot selective versioning

MaterialLot is a hybrid: spec fields (supplier cert, expiration, material type) should trigger versioning; quantity_remaining changes on every consumption and should NOT.

Options:
1. List of "version-exempt fields" on the model (checked in create_new_version or save override)
2. Separate the spec fields into a MaterialLotSpec model; MaterialLot references it via FK

Recommendation: Option 1 is simpler for now. Same pattern as what was proposed for the SecureModel save override's VERSION_EXEMPT_FIELDS.

### ApprovalRequest version cross-check

Nothing currently prevents using a newer unapproved version of a Process/BOM after an older version was approved. The approval system must verify that the version being used matches the approved version.

### get_available() / is_current_version bug

Processes.get_available() filters for `status=APPROVED, is_current_version=True`. Creating a draft v2 sets v1's is_current_version=False, making the approved v1 invisible. Must resolve the is_current_version conflation before expanding versioning.

### Queryset .update() bypass vectors

Existing code that uses queryset `.update()` on models that will be
versioned. These calls bypass `save()`, django-auditlog, and any
future versioning logic. Each needs review during the refactor.

1. **`SPCBaseline.save()` at spc.py:176-184** — uses `.update()` to
   supersede active baselines. When versioning is added, supersession
   must go through the versioning system.

2. **`SamplingRuleSet` archival at mes_lite.py:759** — uses
   `.update(active=False, archived=True)` which bypasses
   `SecureModel.delete()` soft-delete. `deleted_at` never gets set,
   django-auditlog won't capture it. Once versioning is added, this
   won't create version records.

3. **`fix_enum_case.py` management command** — uses raw `.update()`
   on potentially versioned models to fix enum case mismatches. This
   is a data repair tool — acceptable but should be documented as
   intentionally bypassing versioning.

4. **`SamplingRuleSet.activate()` at mes_standard.py:460-465** —
   uses `.update(active=False)` on other SamplingRuleSet records
   (versioned model #5) to deactivate competing rulesets during
   activation. Bypasses save(), auditlog, and versioning. Distinct
   from the archival bypass at mes_lite.py:759.

**Note:** `bulk_soft_delete()` and `bulk_restore()` on
`SecureQuerySet` (core.py:714, 727) use raw `.update()` for
performance. When called on versioned models, these bypass
versioning. This is intentional (soft-delete is not a spec change)
but should be explicitly documented as a design decision.

### ThreeDModel VERSION_EXEMPT_FIELDS

Celery task `process_3d_model` calls `.save()` on ThreeDModel
(versioned model #19) to update processing metadata fields
(`processing_status`, `processing_error`, `processed_at`,
`face_count`, `vertex_count`). These are operational metadata, not
spec changes. Once versioning is added, these fields need to be in
a VERSION_EXEMPT_FIELDS list to avoid spurious versioning on every
3D model processing run.

Same pattern applies to MaterialLot (quantity changes).

**Equipment.status** also needs VERSION_EXEMPT_FIELDS. The
`handle_calibration_result` signal at signals.py:385/395 changes
`equipment.status` and calls `equipment.save(update_fields=['status'])`
after every calibration. Without exemption, every calibration creates
a spurious equipment version.

The VERSION_EXEMPT_FIELDS concept is cross-cutting — at least three
models need it: MaterialLot (quantity), ThreeDModel (processing
metadata), and Equipments (status).

### Approval signals must not trigger versioning

`signals.py:181-187`: when an ApprovalRequest is APPROVED for a
Process, the signal calls `content_object.approve(user=...)`. When
REJECTED, `content_object.reject_approval()`. These call `.save()`
on the Process. These must only update status fields, never trigger
`create_new_version()`. Document this explicitly so future
developers don't accidentally add versioning to approval transitions.

### Serializer direct .save() calls

`ProcessGraphSerializer.update()` at `serializers/mes_lite.py:1130`
calls `instance.save()` directly on Processes. It has an
`is_editable` guard that blocks modifications on approved processes.
This is correct by design (edit drafts in-place, version only for
approved), but the guard depends on `is_editable` returning `False`
for non-DRAFT statuses. Verify this during refactor.

### API PATCH/PUT guard gap

Only 1 of 20+ versioned-model viewsets (`ProcessWithStepsViewSet`)
has an editability guard for PATCH/PUT. All other versioned-model
viewsets inherit `ModelViewSet` which includes `update()` and
`partial_update()` — these go through `serializer.save()` →
`model.save()` which currently does NOT trigger versioning.

**When versioning is active, every ModelViewSet on a versioned model
needs a decision:** (a) edit in-place for DRAFT only, (b)
auto-create new version, or (c) block PATCH/PUT entirely. Currently
none of these guards exist except on Processes.

### Reverse related_name accessors break silently on versioning

FKs point to a specific row UUID. When a versioned parent creates a
new version, reverse `related_name` accessors return only rows tied
to that specific version's UUID.

**Example:** `Parts.part_type = FK(PartTypes, related_name='parts')`.

- `part_type_v1.parts.all()` returns parts linked to v1 (correct for
  historical context — "what parts were made under v1 of this spec?")
- `part_type_v2.parts.all()` returns **zero parts** until new parts
  are created against v2

This breaks "current state of this part type" UIs that use reverse
accessors. Same pattern on:
- `Processes.part_type` → `related_name='processes'` (mes_lite.py:161)
- `Steps.part_type` → `related_name='steps'` (mes_lite.py:554)
- `ThreeDModel.part_type` → `related_name='three_d_models'`

**Particularly concerning call site:** `serializers/mes_lite.py:360`
uses `obj.part_type.processes.filter(status__in=['APPROVED',
'DEPRECATED']).first()` to resolve the active process for a part.
If the part's `part_type` FK points to v1 but the approved process
was created under v2, this returns None or the wrong process.

**Fix:** either (a) traverse the version chain when resolving
reverse accessors (helper method that walks `previous_version` and
unions related sets), or (b) store the "root" version UUID on the
parent and have children FK to root — then reverse accessor returns
all rows regardless of version. Option (b) is simpler but requires
a schema change.

Affected call sites (not exhaustive): `serializers/mes_lite.py:360,
423, 431, 432, 591`. Full audit needed during refactor.

### GenericRelation children not copied to new versions

Versioned models with `GenericRelation` declarations silently lose
their related records on versioning:

- `Processes.documents = GenericRelation('Tracker.Documents')` at mes_lite.py:81
- `BOM.documents` (same pattern)
- `CAPA.documents`, `MilestoneTemplate.documents`, `PartTypes.documents`, etc.
- ApprovalRequest instances attached via GFK (`content_type + object_id`)

When `create_new_version()` creates a new row with a new UUID,
`new_version.documents.all()` returns empty because all existing
Documents have `object_id=old_version.id`. No step in the existing
composite overrides copies GenericRelation children.

**Fix:** each composite `create_new_version()` override must also
copy GenericRelation-linked rows. Either:
- Duplicate the related rows with `object_id=new_version.id`
- Or decide that Documents stay with the original version
  (historical attachment semantics) and document this explicitly

Recommendation: copy Documents to the new version. Historical versions
retain their own copies. Auditor expectation: "show me the drawing
attached to this Control Plan v3" should return the drawing.

**Object_id typing inconsistency:** some GFK models declare
`object_id = UUIDField` (life_tracking.py:186, qms.py:2922), others
`object_id = CharField(max_length=36)` (ArchiveReason, NotificationTask,
ApprovalRequest, Documents at core.py:1348, 2157, 2463, 3217). Not a
versioning bug per se but cross-model GFK queries will behave
inconsistently. Worth standardizing during the refactor.

### PrimaryKeyRelatedField querysets expose all versions

`SecureManager.get_queryset()` does NOT filter `is_current_version=True`
or `archived=False` by default. Current-version filtering is opt-in
via `.current_versions()`.

15+ `PrimaryKeyRelatedField(queryset=PartTypes.objects.all())` sites
across serializers (`serializers/mes_lite.py:322-325, 1358-1359`;
`serializers/mes_standard.py:222-226`; and more) expose **every
version** in API FK-selection dropdowns. Users can create new Parts
or WorkOrders pointing at stale or archived versions.

Currently harmless because no dual-versioning state exists (every
model has version=1). Once versioning activates, these dropdowns
become actively misleading.

**Fix:** audit every `PrimaryKeyRelatedField` queryset on a versioned
model target. Replace `.objects.all()` with `.objects.active_current()`
(active + current version) where the field expects a selection for
new records.

---

## Migration path for existing data

All existing rows should already have `version=1`,
`is_current_version=True`, `previous_version=None` — these are
SecureModel defaults. The migration should be a **verification pass**,
not a bulk update, unless there are rows where version=0 or version=NULL.

**Exception: SPCBaseline and SamplingRuleSet** — their existing
supersession chains need reconciliation with SecureModel versioning
fields. Superseded records should get `is_current_version=False` and
their `previous_version` linked up to match the `supersedes` /
`superseded_by` chain. This is a data migration, not just a schema
migration.

---

## Models that don't exist yet but will need versioning decisions

| Future model | Version? | Notes |
|-------------|----------|-------|
| NonConformanceReport | No — event record | Should snapshot Process, Step, PartType versions at time of NC |
| PPAPSubmission | No — immutable once submitted | Should capture version references to all PPAP element specs |
| EngineeringChangeOrder | No — transaction record | But IS the mechanism that triggers versioning of controlled docs. Every version change should trace to an ECO. |

---

## Summary counts

- **Composite versioned models:** 7
- **Leaf versioned models:** 14 (was 16, minus 2 moved to junction)
- **Junction tables (versioned via parent):** 9
- **Already has own versioning:** 1 (Documents)
- **Audit-log only (not versioned):** ~45
- **Total models needing create_new_version():** 21

---

## Approach decision: specialized vs simple-history

For the refactor, the recommended approach is:

- **Composite models (7):** Specialized create_new_version() overrides, following the Processes pattern. Each knows how to copy its children.
- **Leaf models (14):** Either base SecureModel.create_new_version() or django-simple-history. Both work. simple-history gives free as-of queries, admin UI, and diff views. Base method gives fewer dependencies.
- **Customer preference:** Auto/aero customers care about status-aware locking and approval linkage (favors specialized). "Easy rollback" UI features (favors simple-history) are less important to compliance-focused shops.

Final choice deferred to the refactor session. Both paths are viable. The model list and implementation concerns are the same regardless.

---

## Signal and query concerns

### HubSpot signal depends on stable Milestone PKs

`integrations/signals.py` has `push_stage_change_to_hubspot` which
fires on `HubSpotOrderLink.post_save`. If MilestoneTemplate versions
and its child Milestone instances get new PKs (via copy), any
`HubSpotPipelineStage.mapped_milestone` FK pointing to the old
Milestone becomes stale. The signal would push the wrong stage.

### csv_import.py queries is_current_version=True

`csv_import.py:488` queries `is_current_version=True` to find
processes during import. Same bug as `Processes.get_available()` —
will break when a draft version exists.

---

## Minimum test matrix

These test scenarios validate the versioning system works correctly.
Each should be a test case during or after the refactor.

1. **Round-trip version chain integrity** — Create v1, version to
   v2, version to v3. Verify `get_version_history()` returns all
   three in order. Verify `previous_version` chain is correct.

2. **is_current_version conflation** — Create approved Process v1.
   Create draft v2. Verify `get_available()` still returns v1.
   (Currently fails — known bug, test documents the expected fix.)

3. **Composite child copy fidelity** — Version a Process. Verify
   new ProcessStep and StepEdge rows exist with correct references.
   Verify old version's children are untouched.

4. **FK stability after versioning** — Create WorkOrder referencing
   Process v1. Version to v2. Verify WorkOrder still points to v1
   (not v2).

5. **Tenant propagation** — Version any SecureModel. Verify new
   version inherits tenant from old version. (Currently broken in
   Processes — see reference implementation bugs above.)

6. **M2M copy for ApprovalTemplate** — Version an ApprovalTemplate.
   Verify `default_approvers` and `default_groups` M2M rows are
   copied to new version.

7. **SamplingRuleSet / SPCBaseline dual mechanism** — Verify
   `supersede_with()` and `create_new_version()` don't create
   inconsistent state when both are available on the same model.

8. **SPCBaseline.save() + versioning interaction** — SPCBaseline
   save() auto-supersedes active baselines. Verify this doesn't
   conflict with create_new_version() setting is_current_version.

9. **Soft-delete + versioning interaction** — Archive v1 (soft
   delete). Attempt to create v2 from v1. Should raise ValueError
   (archived model should not be versionable). Currently the check
   only looks at `is_current_version`, not `archived`.

10. **Cross-parent junction (StepMeasurementRequirement)** — Version
    a Step. Verify StepMeasurementRequirement rows are copied.
    Independently version the MeasurementDefinition referenced by
    one of those rows. Verify the old Step's junction rows still
    reference the old MeasurementDefinition version.

11. **TrainingRequirement cross-cutting copy** — Version a Step that
    has TrainingRequirement rows. Verify the requirements are copied
    to the new Step version.

12. **MilestoneTemplate composite copy** — Version a
    MilestoneTemplate. Verify child Milestone rows are handled
    (copied or re-linked) and Orders.current_milestone is not
    orphaned.

13. **MaterialLot selective versioning** — Change a spec field
    (supplier cert) — verify new version created. Change
    quantity_remaining — verify NO new version created.

14. **Concurrent versioning race condition** — Two users
    simultaneously call `create_new_version()` on the same Process
    v1. Without `select_for_update()` or `transaction.atomic()`,
    both could read `is_current_version=True`, both set it to
    `False`, and both create a v2 pointing to v1. Result: two
    competing v2s. Validates the `transaction.atomic()` fix.

15. **Partial failure rollback** — Call `create_new_version()` on a
    Process where the new version would fail to create (e.g., field
    validation error). Verify the old version is NOT left with
    `is_current_version=False`. Validates `transaction.atomic()`.

16. **Version chain performance + cycle detection** — Create a chain
    of 20+ versions. Verify `get_version_history()` returns all in
    order without excessive query count. Also verify behavior when
    `previous_version` chain has a cycle (should not hang — needs
    `seen` set).
