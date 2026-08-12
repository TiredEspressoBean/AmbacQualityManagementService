# Workbook Import/Export Design

> **Status (2026-08-10): design — not started.** Captures the positioning and
> build order for a whole-workbook (multi-sheet) Excel import/export layer,
> built on the existing per-model import/export framework. Primary driver is
> **onboarding/migration off a paper-only 1996 ERP** (see the migration notes
> in this doc). Not a general "edit everything in Excel" feature — see
> §Positioning for the deliberate scope limits.

## Why this exists

Target customers (SMB aerospace/reman shops; Ambac is the reference customer)
are Excel-native and often migrating off legacy systems that only produce
**printed reports**. The interchange format for getting their data into UQMES
is therefore a **master Excel workbook** — human-keyed off the printouts (or
dumped by a vendor extract), one sheet per entity. This doc scopes a combined,
dependency-ordered importer over that workbook, plus a whole-dataset exporter.

The migration that motivated this brings across **master data + open work
orders / current state** — **not** historical execution times. Consequence:
this effort does **nothing** for scheduler timing honesty (`StepTiming` /
duration learning stays empty; standard times arrive as whatever manual numbers
are on the routing sheets). Scheduler honesty is a separate going-forward
capture problem. See `SCHEDULING_IMPLEMENTATION_PLAN.md` and
`DURATION_ESTIMATION.md`.

## What already exists (reuse, don't rebuild)

The per-model machinery is built and wired. The combined layer is a conductor
over it, not a rewrite.

| Component | Location | What it does |
|---|---|---|
| `CSVImportMixin` | `Tracker/viewsets/mixins/csv_import.py` | Per-viewset `import` / `import-preview` / `import-template` / `import-status` endpoints. CSV+xlsx, modes create/update/upsert, inline < 100 rows, Celery-queued above. |
| `DataExportMixin` | `Tracker/viewsets/mixins/data_export.py` | Per-viewset `export/{csv,xlsx}`. Excel export already builds a **fillable template**: FK reference sheets, dropdown validation, `INDEX/MATCH` name→id formulas, required-field highlighting, Instructions sheet. |
| `TenantScopedModelViewSet` | `Tracker/viewsets/base.py:216` | Bundles both mixins — any viewset on this base gets import/export for free. |
| Import serializers | `Tracker/serializers/csv_import.py` | `BaseCSVImportSerializer` (FK resolution by natural key, upsert). Custom serializers for PartTypes, Parts, Orders, **WorkOrder**, Equipment, QualityReports; auto-generation for the rest. |
| `WorkOrderCSVImportSerializer` | `serializers/csv_import.py:456` | **Already ERP-aware**: maps planner-spreadsheet columns, silently drops known-legacy ERP columns (`PC`, `Dept`, `WC Desc.`, `Line`, …), warns on unknown columns, append-and-dedupe on `notes` re-import, `create_parts()` on create. |

Wired today on: Parts, Orders, WorkOrder, PartType (`viewsets/mes_lite.py`).

## Positioning — three cohorts, deliberately bounded

The value is real but concentrated. Keeping the scope bounded is what keeps this
both cheap to build and safe for the compliance/audit story
(`django-auditlog` + versioned models + soft-delete).

| Cohort | Use | Value | Risk | Decision |
|---|---|---|---|---|
| **Onboarding / migration** | One-time-ish bulk load | Very high (sales wedge) | Low (bounded, occasional) | **Primary build.** Optimize for forgiveness + dry-run + legible errors. |
| **Occasional re-imports** | Periodic feed for ERP-owned domains | Medium | Highest of the three | Gate behind the **authoritative-boundary marker** (below) + idempotent natural-key upsert. |
| **Native-Excel power users** | A few planners who genuinely work faster in Excel | Medium, concentrated | Creep risk | Serve with the **existing round-trip template** — no Office add-in. Keep the path **scoped** to planning entities/fields. |

**The line to hold:** cohort #3 is how daily-round-trip creep starts — a feature
justified for three planners becomes how everyone dodges the UI. The UI stays
the primary editing surface. The power-user path is scoped, dry-run'd,
versioning-safe, and carries real attribution on import — not a blanket
"re-import any entity" door. It overlaps the scheduling feature (bulk WO
planning), so build it there, later.

## Build order

1. **Whole-workbook export** — all of a tenant's entities into one workbook.
   Cheapest (≈90% exists in `DataExportMixin`); pure upside; ship first.
2. **Combined onboarding importer** — one workbook, many sheets, dependency-
   ordered, atomic, with dry-run. The migration wedge. Reuses the per-model
   `import_row` serializers unchanged.
3. **Versioning-safe writes + authoritative-boundary handling** — the
   governance layer that makes re-imports safe.
4. **Scoped planning round-trip** — layered on later, tied to scheduling.

The hard per-entity mappers (routings DAG, open-WO step placement) live under
step 2 regardless of whether the workbook is combined.

## Combined importer — design

**Home: a management command**, not a DRF endpoint.
`import_master_workbook --file X.xlsx --tenant <slug> --dry-run`. Matches the
one-analyst-runs-the-migration reality; skips permission/schema-regen overhead;
gives `--dry-run` naturally.

**Mechanics:**
- **Multi-sheet reader** — `openpyxl.load_workbook`, iterate `wb.sheetnames`
  (today's `parse_file` reads a single sheet). openpyxl is already a dependency.
- **Sheet→model registry** — static dict (`"WorkCenters" → WorkCenter`).
  Resolve serializer via existing `get_or_create_import_serializer(model)`.
- **Dependency order** — a hardcoded ordered list (minimum-viable; no
  topological auto-detection):
  `PartTypes → Equipment → WorkCenter → Shift → routings → WorkOrders`.
- **Cross-sheet FKs resolve for free** — `resolve_fk` hits the DB, so writing
  sheets in order **inside one `transaction.atomic()`** makes earlier rows
  visible to later sheets. The transaction is the reference-stitching; no
  in-memory graph needed.
- **Dry-run** — run the whole ordered import in a transaction, aggregate the
  per-sheet `ImportResult`s, then **roll back**. True "everything that would
  happen / every error" preview (richer than today's column-mapping-only
  `import-preview`).
- **Per-row savepoints (do not skip)** — today's `_process_import_inline`
  catches per-row errors inside a *single* `atomic()`. Fine for
  `ValidationError`, but a DB-level `IntegrityError` inside an atomic block
  poisons the whole transaction. The combined importer wraps each row (or
  sheet) in its own savepoint so one bad row doesn't torch the run.

**Effort:** the conductor is ≈1–2 days and low-risk. The migration's real weight
(≈1–2 weeks) is the per-entity mappers below.

## The hard parts (independent of combining)

1. **Versioning-safe writes.** `BaseCSVImportSerializer.create_instance` uses
   `.objects.create()` and `update_instance` uses `.save()` — **neither routes
   through `create_new_version()`**. Fine for non-versioned data (Parts,
   WorkOrder, Orders, Equipment) and for creating v1 of a versioned row.
   **Re-importing updates to versioned masters** (`WorkCenter`, `Shift`,
   `Processes`/routings) bypasses versioning — a `VERSIONING_ARCHITECTURE.md`
   violation. Since re-imports are in scope, these serializers need a
   versioning-aware `update_instance` override (or a create-once policy where
   UQMES owns subsequent versions).
2. **Routings import** (`Processes` + `Steps` + `StepEdge`). More than a flat
   serializer: a routing is many rows per part that assemble into a **DAG**.
   The one genuinely new mapper.
3. **Open-WO current-step placement.** `create_parts()` makes the parts but does
   not advance them to "currently at Op 40 of 70." Resolving a printed
   step number/name to a specific `Steps` row and advancing each part is the
   hardest domain bit.

## Authoritative-boundary marker

Because the 1996 ERP **stays authoritative for some domains**, re-import is a
repeatable feed for those entities. Without a boundary, a user edit in UQMES
gets silently overwritten by the next import (or vice-versa). Minimum-viable:
an `is_erp_managed` flag (or convention) marking ERP-owned rows read-only in the
UI and owned by the importer. **Open decision:** which specific domains the 1996
system keeps (finance / inventory / purchasing?) — that draws the exact
UQMES-owns vs UQMES-mirrors line. Prefer a field over a new table
(per CLAUDE.md defaults).

## Related docs

- `SCHEDULING_IMPLEMENTATION_PLAN.md` — consumer of the migrated master data.
- `OR_TOOLS_INTEGRATION.md` — the scheduling design the masters feed.
- `DURATION_ESTIMATION.md` — why this migration does not make the scheduler honest.
- `VERSIONING_ARCHITECTURE.md` — the `create_new_version()` rule the versioned-master mappers must respect.
- `WORK_CENTER_DESIGN.md` — WorkCenter/Shift/membership semantics.
