# WorkCenter — routing & surface-discriminator design

## What this is

Formalizing the WorkCenter concept from **skeleton** (the model exists, nothing binds to it) to **first-class routing anchor** — the primary discriminator between operator / QA / receiving surfaces and the foundation for future scheduling.

Ratifies rung 3 of the maturity ladder in `OPERATOR_EXPERIENCE_DESIGN.md` §10.

## Why now

The operator home ships with UP NEXT / THEN / In-progress tiles that ad-hoc filter on `part IS NULL` or `step.step_type = 'RECEIVING'` to separate operator work from receiving/OSP work. Both are proxies: `part IS NULL` is an incidental subject-shape (breaks the moment a tenant models receiving differently), and `step_type` is a UI/analytics hint that quietly grew into a routing signal.

The industry-consensus discriminator (across NetSuite, JD Edwards, Plex, Epicor, Business Central, SAP PP, ISA-95 — see the deep-research report referenced below) is the **work-center**. Every routing step binds to a work-center; every user is eligible at some set of work-centers; every dispatch surface (operator queue, QA inbox, receiving dock) is a filtered view scoped to a work-center or a set of them.

## The model shape

### `WorkCenter` — additions to the existing model

Existing fields kept: `name`, `code`, `description`, `capacity_units`, `default_efficiency`, `equipment` (M2M), `cost_center`.

**New field:**

- `kind` — enum: `PRODUCTION | INSPECTION | RECEIVING | OSP`. The primary surface discriminator: operator queue filters `kind=PRODUCTION`, QA inbox filters `kind=INSPECTION`, receiving inbox filters `kind=RECEIVING`, OSP dispatch filters `kind=OSP`. Default `PRODUCTION` on existing rows.

**Rationale for `kind` as enum (not FK, not capability array):**

- Enum is the smallest thing that solves the driving problem
- The four values map to the four surfaces UQMES already ships
- Migrating to a richer form later (FK to `WorkCenterKind` for tenant-configurable kinds, or an ArrayField of capability tags) is a one-migration operation if it ever becomes necessary
- Deep-research report couldn't identify a canonical "kind" pattern (no single-canonical rule survived verification) — this is a UQMES-specific choice; enum-first is defensible and reversible

**Deferred (YAGNI until proven needed):**

- `parent` FK — work-center hierarchy (Business Central: group > center > machine). Add when a customer needs it; the enum + M2M shape handles the current cases flat.
- Alternates M2M on Step — used when the "same step runs at any of N stations" case appears repeatedly. For v1, if a customer needs alternates, they can create a "cell"-shaped WorkCenter that groups the equipment.
- Capability matching (ISA-95 EquipmentClass / PersonnelClass) — more expressive, but a real product design surface. Skip until we have a customer whose shop demands it.
- `shift` FK — the Shift model exists but isn't wired. Wire it when scheduling lands.

### `Step.work_center` — new FK (nullable)

One FK per step, nullable during migration and for steps that haven't been mapped yet. Filterable everywhere the queue / my_workload / dispatch surfaces are computed.

**Why one FK, not M2M-first:**

Deep-research consensus: per-step FK is the canonical routing shape (JD Edwards, NetSuite, Plex, Epicor, Business Central — 20+ years of ERP/MES). M2M alternates get added when they become a real need; starting there is over-engineering for UQMES's current scale.

**Interaction with `Step.step_type`:**

`step_type='RECEIVING'` is currently load-bearing (`services/qms/receiving_inspection.py` filters on it). We do **not** remove it in this phase. Instead:

- `WorkCenter.kind=RECEIVING` and `step.step_type='RECEIVING'` say the same thing at different levels
- The receiving-inspection queue keeps using `step_type='RECEIVING'` for now
- The operator-facing surfaces use `work_center.kind` as the discriminator
- Deprecation path: once `work_center.kind` is proven, migrate the receiving service to filter on `step.work_center.kind='RECEIVING'` and step_type reverts to being what its docstring says — "visual type for flow editor"

`Step.is_outside_process=True` is analogous: it stays as-is for OSP-specific logic; surfaces route via `work_center.kind='OSP'`.

### `UserWorkCenterMembership` — new through-table

Fields: `user` (FK), `work_center` (FK), `is_primary` (bool), `created_at`.

**Rationale — M2M eligibility, not identity:**

ISA-95 PersonnelClass pattern (deep-research report): one class member gets any step needing that class. Operators in multi-station shops reassign several times per shift (per jitbase.com research). So user↔work-center is a membership, not a "current station."

**Why a through-table instead of plain M2M:**

- `is_primary` lets a user have a default/preferred station (useful for the operator home defaulting UP NEXT scope)
- Room to add fields later (e.g., `qualified_at`, `certification_level`) without a second migration
- Enables per-membership audit tracking if that becomes a compliance need

**Session vs membership:**

We're modeling *eligibility* (who CAN work at this station), not *presence* (who IS currently at this station). Kiosk-mode (login-at-terminal binds session to a station) is a natural future extension — session state layers on top of eligibility; it doesn't replace it.

## What this unlocks

- **Operator UP NEXT / THEN** scoped to production work-centers the user is a member of; station-scope combobox becomes live (currently Preview).
- **QA inspection inbox** naturally filters to `kind=INSPECTION` — reframes the existing inbox as work-center-scoped.
- **Receiving inbox** filters `kind=RECEIVING` — a real surface bound to Receiving-dock work-centers.
- **OSP dispatch board** (future) filters `kind=OSP`.
- **Retires the `part IS NULL` and `step_type='RECEIVING'` ad-hoc filters** on operator surfaces — replaced with the primary discriminator.
- **Foundation for scheduling** (rung 4/5) — scheduling wants to allocate work orders to work-centers with known capacity; the shape here doesn't preclude that.

## Phasing

**Phase 1 (this doc's target):**
- Model additions: `WorkCenter.kind` (enum), `Step.work_center` (nullable FK), `UserWorkCenterMembership` (through-table).
- Migration.
- Demo seed: create ~5 work-centers for the injector process (Assembly, Cleaning, Flow Test, Nozzle Inspection, Receiving Dock, OSP Dispatch). Map existing seeded steps by `step_type` + `is_outside_process`. `admin@demo` gets membership in all; role-scoped demo users get selective memberships.
- Endpoints (`WorkQueue`, `my_workload`) accept `?kind=` and `?work_center=` filters.
- Tests: filter correctness, seed produces expected splits, tenant isolation.
- Perms: reuse `view_workorder` on WorkQueue (no change); WorkCenter reads existing `view_workcenter` (already granted in `STAFF_VIEW_PERMISSIONS`).

Stopping point: backend green, no FE swap, no committed changes.

**Phase 2 (next; requires Phase 1 approved):**
- Frontend: operator home passes `?kind=PRODUCTION&work_center__in=<user's memberships>`.
- Station-scope combobox becomes live — user's memberships populate options, active station persists client-side (or as `is_primary` on the membership).
- Retire the `part__isnull=false` implicit filter on `WorkQueue` (superseded by `kind`).

**Phase 3 (later, opportunistic):**
- Migrate `services/qms/receiving_inspection.py` to `work_center.kind='RECEIVING'`.
- Migrate QA inspection inbox filtering.
- Update the design doc references to remove `step_type='RECEIVING'` as a routing signal.

**Deferred indefinitely (add when a customer needs it):**
- Work-center hierarchy / groups
- Step alternates M2M
- ISA-95 capability matching
- Shift binding on WorkCenter

## Open decisions (Phase 1 doesn't need to answer)

- Is `is_primary` on the membership enough, or does the operator home need a client-persisted "active station" separate from the primary? (Client-persisted feels right; the primary is the default and the operator picks a different station for the shift if needed.)
- When `Step.work_center` is null on a step, what does the operator surface do? (Option A: show it in a "no-work-center" bucket; Option B: hide it. Recommend A for v1 to make unmapped steps visible for admin to fix.)
- Do we allow a WorkCenter to have `kind` change over time (e.g., a bay converted from inspection to production)? For v1: editable, no history — audit log captures the change.

## Cross-references

- Deep-research report: 100-agent workflow run 2026-07-23; findings summary in the workflow transcript. Key confirmed patterns: per-step FK is canonical; hierarchy is standard (2- or 3-level); user↔WC is M2M eligibility; enforcement policy for gates is not canonical (UQMES decision).
- `OPERATOR_EXPERIENCE_DESIGN.md` §10 (maturity ladder rung 3) — this doc executes on that rung.
- `MES_FEATURE_TIERS.md` — scheduling depends on this shape (rungs 4–5).
