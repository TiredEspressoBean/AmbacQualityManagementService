# Refactor Plan

## Status

- Current phase: not started (plan drafting)
- Target branches: fresh branch per phase; Phase 5 uses one branch per aggregate
- Product: UQMES (Ambac International is the reference customer)
- Parallel sessions active: Reports, Labels & Scanning

## Goals

- Eliminate silent cross-tenant leak risk (Phase 2)
- Remove logic triplicated across model / viewset / serializer (Phases 3, 5)
- Eliminate N+1 from cascading SerializerMethodFields (Phase 5)
- Harden Celery dispatch against uncommitted-transaction races (Phase 1)
- Build characterization safety net (schema-diff) for ongoing refactor (Phase 0)

## Architectural Thesis

**Save is storage, services are behavior.** The Secure* family splits cleanly between reads+storage and writes+behavior:

| Class | Owns | Does NOT own |
|---|---|---|
| SecureModel | Schema, FKs, `__str__`, simple read-only properties, VersionMeta declaration | Business logic, state transitions, cross-aggregate writes, side effects |
| SecureManager | Auto-scoped query construction, tenant context enforcement | Anything that mutates |
| SecureQuerySet | Chainable filtered queries (`.for_user()`, `.active()`) | Anything that mutates |
| SecureService | Save-vs-version routing, state transitions, cross-aggregate writes, audit emission (RecordEdit), retention awareness | Schema, query construction |

SecureService mirrors the Secure* pattern: inherit and get tenant-aware mutation safety for free. Most aggregates use SecureService directly (generic save routing via VersionMeta). Custom subclasses (DocumentService, CapaService, StepOverrideService) add domain-specific operations.

**Method placement test:** if a model method only reads `self.field`, it stays on the model as a property. If it reaches into `self.related_manager.filter(...)` across aggregates or triggers side effects, it moves to SecureService.

**Serializer/viewset contract:** serializers validate shape and call `service.save(instance, validated_data)`. The service decides whether that's a plain `instance.save()` or a `create_new_version()` based on VersionMeta + what changed. The caller never knows or chooses.

## Plan vs. Emergent

Two categories of content live in this refactor:

- **Architectural** — decisions that must hold regardless of execution. Thesis, scope, hazards, phase ordering, layer rules, completion criteria. These are the plan's backbone and don't drift during execution.
- **Emergent** — artifacts captured as they're discovered: skills, CLAUDE.md entries, specific aggregate picks, detailed retention policies, Phase 3 extraction targets beyond the first 2-3, template aggregate selection.

Treating emergent content as planned content produces documentation that contradicts reality as soon as execution starts. Sections below marked *(emergent)* are running lists, not prescriptions — entries land as discovered and get pruned when they stop mattering.

## Not In Scope

- ULID primary keys (retrofit cost too high)
- django-ninja migration (DRF too deeply embedded)
- Pydantic adopted internally (DRF serializers + frozen dataclasses sufficient)
- `svcs` DI container (premature until services layer is built out)
- DTOs added to every endpoint prophylactically (only at N+1 / duplication sites)
- Rewriting Reports or Labels subsystems (owned by parallel sessions)
- Renaming Ambac → UQMES in folder / DB / cache names (cosmetic, separate effort)

## Known Hazards

- **django-auditlog manager interaction**: verify auditlog uses `_base_manager`, not the new `SecureManager`, before flipping auto-scoping on
- **Postgres RLS masks application-layer scoping bugs**: tests must run against RLS-bypassed connection (or assert SQL contains the WHERE clause), or app-layer bugs stay invisible
- **Manager must RAISE on missing tenant context, not silently filter**: silent filter produces false-green tests
- **Three distinct manager semantics required**:
  - `objects` — scoped, RAISES if contextvar unset
  - `unscoped` — no filter; for migrations, commands, shell
  - `all_tenants` — no filter; explicit cross-tenant (admin)
- **`transaction.on_commit()` does not fire in `TestCase`**, only `TransactionTestCase` — tests verifying Celery dispatch must use the latter after Phase 1
- **Phase 4 file splits conflict with any session touching the same models** — coordinate merge window with Reports / Labels before splitting
- **Phase 5 template aggregate must NOT be Integrations** (mid-rewrite); pick a stable aggregate (Calibration or Training)
- **Existing tenant-scoping lint becomes partially redundant after Phase 2** — delete or narrow, don't leave two half-working systems
- **Solo-dev workflow: no CI currently** — verification happens via manual test runs before merging to master; keep Phase 0 scripts runnable locally, not CI-gated
- **Versioning architecture being designed in parallel session** (`Documents/VERSIONING_ARCHITECTURE.md`) — Phase 3 service extraction must align with that doc's design; do not commit to a versioning pattern unilaterally in this refactor

## Services Directory Layout

Grouped by module, mirroring the existing `models/` organization. `Tracker/services/<module>/<aggregate>/`.

```
Tracker/services/
├── _shared/                   # SecureService base, VoidableModel helpers, RecordEdit utilities
├── core/
│   ├── orders/                # Orders, OrderViewer
│   ├── parts/                 # Parts, PartTypes
│   ├── companies/             # Companies
│   ├── users/                 # User, UserInvitation, TenantGroup, TenantGroupMembership, UserRole, Facility
│   ├── documents/             # Documents, DocumentType
│   ├── approvals/             # ApprovalTemplate, ApprovalRequest, ApprovalResponse, approver/group assignments
│   └── milestones/            # Milestone, MilestoneTemplate
├── mes/
│   ├── work_orders/           # WorkOrder
│   ├── processes/             # Processes, ProcessStep, Steps, StepEdge, StepRequirement, StepMeasurementRequirement
│   ├── step_execution/        # StepExecution, StepOverride, StepRollback, BatchRollback, StepExecutionMeasurement, StepTransitionLog
│   ├── equipment/             # Equipments, EquipmentType, EquipmentUsage
│   ├── scheduling/            # Shift, ScheduleSlot, WorkCenter, TimeEntry, DowntimeEvent
│   ├── materials/             # MaterialLot, MaterialUsage, AssemblyUsage, BOM, BOMLine
│   ├── sampling/              # SamplingRuleSet, SamplingRule, SamplingAnalytics, SamplingAuditLog, SamplingTriggerState
│   └── measurements/          # MeasurementDefinition
├── qms/
│   ├── quality/               # QualityReports, QualityReportDefect, MeasurementResult, QualityErrorsList, QaApproval
│   ├── dispositions/          # QuarantineDisposition
│   ├── capa/                  # CAPA, CapaTasks, CapaStatusTransition, CapaVerification, CapaTaskAssignee, RcaRecord, FiveWhys, Fishbone, RootCause
│   ├── calibration/           # CalibrationRecord
│   ├── training/              # TrainingType, TrainingRecord, TrainingRequirement
│   ├── fpi/                   # FPIRecord
│   ├── three_d/               # ThreeDModel, HeatMapAnnotations
│   └── reports/               # GeneratedReport
├── life_tracking/             # LifeLimitDefinition, LifeTracking, PartTypeLifeLimit
├── reman/                     # Core, HarvestedComponent, DisassemblyBOMLine
├── spc/                       # SPCBaseline
└── dms/                       # ChatSession, DocChunk
```

**Judgment calls:**
- `processes/` owns routing *specs*; `step_execution/` owns runtime state. StepOverride/Rollback go with step_execution, not quality, because they're operations at step time rather than quality records.
- EquipmentUsage goes with `quality/` — primarily a traceability record for quality events.
- RCA models (FiveWhys, Fishbone, RootCause) fold into `capa/` — they only exist in CAPA context.
- `_shared/` holds cross-cutting utilities (SecureService base, RecordEdit helpers), not an aggregate.
- `life_tracking`, `reman`, `spc`, `dms` stay top-level — not naturally part of Core/MES/QMS.

**Note:** this structure fills in during Phase 3 and Phase 5 as aggregates get migrated. Day-one state has maybe 5-7 directories under `services/`; growth to the full tree is over months. Individual aggregate splits (e.g., pulling `rca/` out of `capa/` if it gets too big) are find-and-replace level, not refactoring.

## Versioning Conventions

**Authoritative source:** `Documents/VERSIONING_ARCHITECTURE.md` (designed in parallel session). Categorization of models, `VersionMeta` shape, copy-and-remap logic, and the "records not specs" record list all live there.

**This plan's responsibility:** define how *services* interact with versioning, not what versioning itself is.

**Service implications:**
- Services mutating versioned models use the versioning method defined in the architecture doc — never bypass it with a raw `.save()`
- Services never directly write to junction tables for versioned parents; always go through the parent's version method
- Services on "records not specs" models use plain `.save()` + django-auditlog / RecordEdit for audit, no versioning
- Phase 3 service extraction checks `VERSIONING_ARCHITECTURE.md` for the target model's category before writing mutation logic
- Edge cases discovered during extraction (model doesn't fit a category cleanly) feed back to the versioning doc as questions, not decided unilaterally in this refactor

## Skills *(emergent)*

Skills get written when a pattern solidifies during execution, not planned in advance. Writing aspirational skills produces documentation that contradicts the code.

Claude Code native format (YAML frontmatter + prose body). Skills describe forward-facing patterns ("how to write new X correctly"), not refactor transitions. Transitional work lives in phase checklists, not skills.

**Candidates identified so far** (write when the pattern is real, not before):
- `uq-new-aggregate` — scaffolding a new feature area end-to-end
- `uq-new-service` — adding a service within an existing aggregate
- `uq-new-endpoint` — adding an endpoint with the thin-viewset + service + DTO pattern
- `uq-new-integration` — scaffolding an integration adapter

Simple one-off rules (Celery task conventions, model conventions, signal patterns, tenant scoping, test structure) stay as CLAUDE.md one-liners instead of skills — they don't warrant skill ceremony.

## CLAUDE.md *(emergent, running document)*

CLAUDE.md is a living artifact, not a phase deliverable. Entries land when a cross-session invariant is discovered and get pruned when they stop mattering. Don't front-load; don't hoard. ≤25 lines is a pruning trigger, not a hard cap.

Entries marked *(post-Phase N)* wait for that phase to ship before they land — an entry whose statement isn't actually true yet is worse than no entry.

**Candidates identified so far:**

**Context:**
- Product is UQMES; Ambac International is the reference customer (paths still read "Ambac" — rename is a separate effort)
- Integration framework lives in `PartsTracker/integrations/`, not `Tracker/integrations/` (deleted)
- Parallel sessions active on Reports and Labels & Scanning — do not modify their files
- django-auditlog is in use — do not propose new models for audit-trail reasons
- Solo-dev workflow: no CI; verification via manual test runs before merge to master

**Rules (always-on):**
- Opportunistic refactor discipline: scope changes to files already touched; commit refactor separately from feature; ask before deleting files or top-level symbols

**Rules (post-Phase 1):**
- Celery: `@shared_task` args must be IDs + `tenant_id`, never model instances
- Celery: `.delay()` / `.apply_async()` inside ORM writes must be wrapped in `transaction.on_commit`

**Rules (post-Phase 2):**
- Tenant scoping: `SecureModel.objects` auto-scopes by ContextVar and RAISES if unset
- Tenant scoping escape hatches: use `Model.unscoped` (migrations, commands, shell) or `Model.all_tenants` (admin, explicit cross-tenant) — never query with a reset contextvar

**Rules (post-Phase 3):**
- Business logic lives in `Tracker/services/<aggregate>/`, not in model methods or viewset actions
- Model methods should be simple `@property` accessors and `__str__` — no cross-aggregate writes, no state machines

**Rules (post-Phase 5):**
- Architecture: layered (api → service → repo → model); services do not import models from outside their aggregate
- Tests: repo tests use real DB; service tests use fake repos; API tests use DRF `APIClient`

## Phase 0 — Prep

**Goal:** establish the minimal safety net later phases depend on.

**Work:**
- Commit `CLAUDE.md` with the Context + always-on rules from the section above (phase-gated rules land when their phase ships)
- Add `scripts/check_schema.py` — diffs current `schema.yaml` against a committed baseline; exits non-zero on non-additive change; run manually before merging to master
- Commit current `schema.yaml` as baseline
- No query-count baselines yet — code is about to move, baselines would invalidate
- No linters, type-checkers, or CI changes — separate concern from the refactor

**Completion:**
- `CLAUDE.md` at repo root with context + always-on rules
- `scripts/check_schema.py` runs cleanly against current baseline
- Usage documented in a short comment at top of the script

## Phase 1 — Celery In Transaction

**Goal:** remove the race between ORM writes and task dispatch.

**Work:**
- Audit `@shared_task` definitions — any taking model-instance args converted to `(id, tenant_id)` + repo fetch
- Audit `.delay()` / `.apply_async()` call sites — wrap in `transaction.on_commit(lambda: task.delay(...))` when inside ORM writes
- Add `TransactionTestCase`-based tests for task dispatch paths where coverage is missing

**Completion:**
- Grep returns zero `@shared_task` functions taking model instances
- Task dispatch inside transactions is wrapped
- Existing test suite passes

**Rollback:**
- Pure code change, no schema impact — `git revert` the PR

## Phase 2 — SecureModel Auto-Scoping

**Goal:** make tenant leaks impossible at the ORM layer.

**Reference:** `Documents/SECURE_MODEL_TENANT_AUTO_SCOPING.md` contains the original design notes. This plan section is authoritative for execution; the reference doc is context for rationale.

**Prerequisites:**
- Phase 0 complete (schema-diff script in place)
- Phase 1 complete (Celery safe — simpler reasoning about what sets context)

**Work:**
- Audit `SecureModel` subclasses for missing tenant FK; resolve stragglers (add FK, or stop inheriting `SecureModel`)
- Define three managers on `SecureModel`:
  - `objects = SecureManager()` — scoped, RAISES if contextvar unset
  - `unscoped = models.Manager()` — no filter, explicit no-tenant-context
  - `all_tenants = models.Manager()` — no filter, explicit cross-tenant
- Confirm django-auditlog uses `_base_manager` and is unaffected
- Extend `TenantMiddleware.__call__` to set contextvar with `try/finally` reset
- Extend Celery `tenant_context()` helper to set the same contextvar
- Audit management commands — wrap in `unscoped()` context or accept the raise
- Audit data migrations — same
- Audit admin — superuser admin uses `all_tenants` explicitly via `ModelAdmin.get_queryset`
- Add tests asserting the manager RAISES on unset context (not silently empty)
- Add tests asserting application-layer scoping works with RLS bypassed

**Completion:**
- All `SecureModel` subclasses have a tenant FK OR no longer inherit `SecureModel`
- Manager raises on missing context, verified by test
- Full test suite passes with tenant-context fixtures where required
- Existing tenant-scoping lint still passes (or is explicitly retired)
- Management commands and migrations verified under new semantics

**Halt (stop and ask):**
- Any test fails with something other than "missing tenant context" — unexpected behavior change
- Auditlog produces unexpected entries (auto-scoping leaked into it)
- RLS rejection rate spikes (app-layer and DB-layer disagree)

**Rollback:**
- Revert the manager swap (one commit); middleware change may remain without effect
- If rollback happens after downstream code has started relying on RAISE semantics, re-enable via feature flag rather than full revert

## Phase 3 — Service Extraction (worst offenders)

*Skeleton — detail finalized after Phase 2 ships.*

**Dependencies:** Phase 2 complete.

**Work items:**
- Establish `Tracker/services/<aggregate>/` layout
- Extract state-changing logic from model methods + viewset actions where duplicated
- Both callers (model method and viewset action) delegate to the service

**Initial target list** *(emergent — scope and priority adjust as Phase 2 completes and real pain surfaces):*
- `StepOverride.approve` / `reject`
- `CAPA.transition_to`
- `QuarantineDisposition.complete_resolution` + `_update_part_status`
- `CapaTasks.mark_completed`
- `CapaVerification.verify_effectiveness`

**Retention policy groundwork:**
While establishing services and signal patterns, lay the foundation for record retention (MES Feature Tiers §28 — currently unbuilt). Scope is groundwork only, not the full feature:
- Define a `RETENTION_POLICIES` config mapping model/aggregate → retention period + action (e.g., `{'QualityReports': {'period': '7y', 'action': 'void'}}`)
- Retention action convention: reuse `VoidableModel.void()` for soft-void with `reason="retention policy"` rather than hard-delete — preserves audit trail
- Periodic Celery beat task pattern that queries each policy and applies the action, using Phase 1's `transaction.on_commit` dispatch
- The "Explicitly NOT versioned" list in Versioning Conventions identifies the accumulating records this applies to
- NOT in scope for this phase: per-tenant retention UI, compliance reporting, hard deletion, anonymization

**RecordEdit as signal-driven audit:**
`RecordEdit` (field-level edit tracking with mandatory reason) is distinct from django-auditlog's automatic change tracking — auditlog captures *what* changed; RecordEdit captures *why*. During service extraction, consider wiring RecordEdit creation via the reliable-signals pattern (Phase 1's `transaction.on_commit` + Celery) rather than inline in each service. A signal-based approach means any service that mutates a regulated record gets edit-with-reason tracking without every service manually creating RecordEdit rows. Design the signal contract during this phase; the specific models that emit it are identified by the "Explicitly NOT versioned" list in Versioning Conventions (records, not specs — the models where edit-with-reason matters most).

**Completion:**
- Each target has a single implementation in services
- Model methods + viewset actions are thin wrappers that delegate
- RecordEdit signal contract designed (which events emit, what payload)

**Halt:**
- Unrelated test failure during extraction — revert and flag

## Phase 4 — File Splits

*Skeleton — detail finalized after Phase 3 ships.*

**Dependencies:** Phase 3 complete (splits land into target structure, not intermediate).

**Work items:**
- Coordinate merge window with Reports and Labels sessions
- Split `Tracker/models/core.py`, `qms.py`, `mes_lite.py` by aggregate
- Re-export from `Tracker/models/__init__.py` to preserve external imports

**Completion:**
- No model file exceeds agreed line cap
- All imports resolve
- Test suite passes

**Rollback:**
- Mechanical revert of the split PR

## Phase 5 — Repo+DTO Migration

*Skeleton — detail finalized per aggregate as each turn comes.*

**Dependencies:** Phases 2 + 3 complete. Phase 4 preferred but not strict.

**Template aggregate selection criteria:**
- Stable — not actively being rewritten
- Small — < 500 LoC of model code
- Representative — has a state machine and at least one cross-aggregate write
- **Excluded:** Integrations (mid-rewrite on current branch)
- **Pick** *(emergent — real choice made when Phase 5 starts based on what's actually stable at that point; current candidates: Calibration, Training)*

**Per-aggregate work items:**
- Build `domain/<aggregate>.py` (DTOs — frozen dataclasses)
- Build `repositories/<aggregate>.py` (owns ORM + query plan)
- Move services to `services/<aggregate>/` (DTO in, DTO or event out)
- Migrate list endpoint first (worst-N+1), detail endpoints second
- Add query-count test for the aggregate's list endpoint (introduced in this phase, not earlier)
- Viewset becomes thin translator

**Aggregate order** *(emergent — speculative ordering; real order set by measured N+1 severity after characterization. Best current guess: QMS (`QuarantineDisposition`, `CAPA` list) → Orders → WorkOrders → Milestones → remainder.)*

**Completion (per aggregate):**
- Schema unchanged (verified by `scripts/check_schema.py`)
- Query count on list endpoint ≤ pre-migration baseline
- All tests pass
- Layer discipline verified by review: no `.objects.` outside the aggregate's repo, viewset action bodies are thin translators

**Halt:**
- Schema would need to change — means DTO shape doesn't match the existing API contract; stop and decide which is right
- Query count regresses — prefetching didn't match what the DTO accesses
- Viewset action can't become thin — means there's logic still to extract; loop back to Phase 3 for that aggregate

**Rollback (per aggregate):**
- Revert the aggregate's PR — self-contained, no cross-aggregate impact
- Old viewset / serializer path is preserved until the PR is merged, so rollback is atomic