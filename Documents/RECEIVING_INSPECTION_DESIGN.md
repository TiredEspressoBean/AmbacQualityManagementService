# Receiving Inspection — Design

Status: **proposed** · Owner: cisherwood · Last updated: 2026-06-23

Covers two distinct receiving-inspection flows that share an inspection core but
attach to different aggregates and have opposite work-order coupling:

- **A. Purchased-material receiving** — incoming lots from suppliers (gears, raw
  stock, purchased components). No work order exists yet. *Lot-centric.*
- **B. Outside-processing (subcontract) receiving** — our own parts, already in a
  WorkOrder at a Step, sent out to a vendor for an operation (heat treat, plating,
  grinding) and inspected on return. *Part/step-centric, heavy WO coupling.*

Decisions locked with product: lot-quantity tracking (not per-unit serial) for A;
full disposition **+ AQL sampling**; receiving/materials live under **Production**;
design both, build A first.

> **Sampling standard:** pluggable, **C=0 (Squeglia) as default** (most auto/aero
> customer requirements prohibit AQL>0), **ANSI/ASQ Z1.4** single sampling (ex
> MIL-STD-105E, general level **II**, normal severity) selectable per plan, plus
> trivial `100%` / `skip-lot`. Built so Z1.4 tightened/reduced severity and
> double/multiple sampling are additive. Confirm no customer mandates a different plan.

---

## 1. Shared inspection core (used by both A and B)

These already exist and are reused unchanged except where noted:

| Primitive | Role | File |
|---|---|---|
| `MeasurementDefinition` | acceptance criteria (numeric tol / pass-fail) | `models/mes_standard.py` |
| `QualityReports` + `MeasurementResult` | the inspection record + captured values; `INSPECTOR` personnel role | `models/qms.py` |
| `QuarantineDisposition` | NCR/disposition; `RETURN_TO_SUPPLIER` already a type | `models/qms.py` |
| `Companies` | supplier | `models/core.py` |

**New shared calculator — acceptance sampling** (`Tracker/services/qms/acceptance_sampling.py`):

```python
@dataclass(frozen=True)
class SamplePlan:
    strategy: str         # 'Z14' | 'C0'
    code_letter: str      # 'A'..'R' (Z1.4); '' for C=0
    sample_size: int      # n
    accept: int           # Ac
    reject: int           # Re

def derive_sample_plan(lot_size, aql, level='II', severity='normal', strategy='C0') -> SamplePlan
```

- Pure computation, **no DB / no tenant scope** — a stateless utility module.
- **Pluggable strategies, not Z1.4-only.** Encode both:
  - **C=0 (Squeglia)** — zero-acceptance-number plans. *Default*, because most
    auto (IATF customer-specific reqs) and aero primes prohibit AQL>0.
  - **Z1.4** (ANSI/ASQ, ex-MIL-STD-105E) — single sampling, levels S-1..S-4 + I/II/III,
    via the two standard tables (lot-size+level → code letter; code letter+AQL → n,Ac,Re)
    incl. arrow rules. Severity switching and double/multiple sampling are clean
    extension points.
- Plus `'100%'` and `'skip-lot'` as trivial strategies.
- **Test this hard** against published table values before anything depends on it —
  it is the piece most likely to be subtly wrong.

Both flows feed this calculator a lot size and read back (n, Ac, Re): flow A uses
`MaterialLot.quantity`; flow B uses the count of parts in the returned shipment.

> **How this relates to the existing sampling engine (important).** The current
> engine (`SamplingRuleSet`/`SamplingRule`, `services/mes/sampling_applier.py`,
> `services/dwi/sampling_decisions.py`) is **per-part streaming**: it answers
> *"sample THIS part?"* at step entry (`EVERY_NTH`, `PERCENTAGE`, `RANDOM`, …).
> AQL/C=0 is **lot-terminal**: needs lot size N up front → (n, Ac, Re) → accumulate
> defectives → accept/reject the whole lot. Grep confirms **no `lot_size` /
> `sample_size` / `accept_number` / `reject_number` exist today**, and the CSP
> fallback is consecutive-fail tightening, not AQL severity switching. So we
> **extend the one engine** rather than fork it:
> 1. the stateless calculator above is the shared math;
> 2. add `AQL` / `C_ZERO` to `SamplingRuleType` + AQL params (aql, level, severity, strategy);
> 3. **relax ruleset scoping** so a ruleset can bind to `(part_type, supplier)` with
>    **no step** (today `SamplingRuleSet.step` is a non-null FK; receiving has no step);
> 4. add a **lot-acceptance record** (`sample_size`, `Ac`, `Re`, `defectives_found`,
>    status PENDING/ACCEPTED/REJECTED) evaluated by a new lot evaluator, reusing the
>    existing `SamplingAuditLog` / `SamplingAnalytics` tables for trail + metrics.
> The per-part evaluator is untouched; AQL gets its own lot evaluator beside it.

---

## 2. Flow A — Purchased-material receiving (lot-centric)

**Work-order coupling: none.** The lot is inspected before it ever enters
production. The only WO touchpoint already exists downstream: an accepted lot is
consumed at a step via `MaterialUsage`.

### Models

**New: `ReceivingInspectionPlan` (the "RIP")** — versioned quality spec
(`_is_versioned = True`, `SecureModel`), `Tracker/models/qms.py`:

- `part_type` FK → `PartTypes`
- `supplier` FK → `Companies`, nullable (null = applies to all suppliers)
- **sampling**: a FK to the (step-less) `SamplingRuleSet` from §5b carrying
  `strategy` (`C_ZERO` default / `Z14`), `aql`, `inspection_level`
  (`S1`..`S4`,`I`,`II`,`III`, default `II`), `severity` (default `NORMAL`). The RIP
  owns the *what/criteria*; the ruleset owns the *how-many*. (If a tenant never needs
  per-rule reuse, these can collapse onto the RIP directly — decide at build time.)
- `characteristics` M2M → `MeasurementDefinition` (the things to check; if empty,
  fall back to the part-type's defined measurements)
- `active` bool

  **Plan resolution precedence** for an incoming lot:
  `(part_type + supplier)` > `(part_type, supplier=null)` > inactive/none → manual.

**Extend `MaterialLot.LOT_STATUS_CHOICES`** (`models/mes_standard.py`) — fields, no
new table. Add: `AWAITING_INSPECTION`, `ACCEPTED`, `REJECTED`. Lifecycle:

```
RECEIVED → AWAITING_INSPECTION → ACCEPTED → IN_USE → CONSUMED
                              ↘ QUARANTINE → REJECTED / SCRAPPED
```

> **Versioning note:** `MaterialLot._is_versioned = True`. Receiving *status*
> transitions are operational state (like `Parts.part_status`, which mutates in
> place on a non-versioned model), **not** spec edits — they should mutate in place,
> not spawn `create_new_version()`. Calling this out explicitly so the status
> service is a documented exception to the versioned-mutation rule. Confirm.

**Extend `QualityReports`** (`models/qms.py`):

- add nullable `material_lot` FK (alongside the existing nullable `part`)
- add sample-plan snapshot fields: `sample_size`, `accept_number`, `reject_number`
- `CheckConstraint`: exactly one of `part` / `material_lot` is set
- PASS/FAIL = observed defectives (from `QualityReportDefect` counts / failed
  `MeasurementResult`s) ≤ `accept_number`

### Service — `Tracker/services/qms/receiving_inspection.py`

- `open_receiving_inspection(lot, plan=None, inspector=None)` — **gate** on an
  APPROVED, non-expired `PartApproval` for `(part_type, supplier)` (PPAP/FAI) and an
  approved `SupplierQualification` for the supplier (ASL) — see §6; resolve RIP, call
  `derive_sample_plan(lot.quantity, ...)`, create `QualityReports(material_lot=lot,
  sample_size, accept_number, reject_number, status=PENDING)`, set lot →
  `AWAITING_INSPECTION`. (Missing/expired approval → block or flag per tenant policy.)
- `record_receiving_result(qr, defective_count, results=...)` — evaluate vs Ac →
  PASS/FAIL.
- `accept_lot(lot)` → `ACCEPTED`.
- `reject_lot(lot, disposition_type)` → `QUARANTINE` + spawn `QuarantineDisposition`
  (`RETURN_TO_SUPPLIER` / `USE_AS_IS` / `SCRAP`); terminal → `REJECTED`/`SCRAPPED`.

### API

- `ReceivingInspectionPlanViewSet` — CRUD, versioned via `create_new_version()`.
- `MaterialLotViewSet` (exists) — add actions `open_inspection`, `record_inspection`,
  `accept`, `reject`. Auto-set inspector to request user.
- Regenerate `schema.yaml` + frontend types in the same PR.

---

## 3. Flow B — Outside-processing / subcontract receiving (part/step-centric)

**Work-order coupling: heavy.** Parts are already `Parts` in a `WorkOrder` at a
`Step`. The return inspection reuses the **existing part-centric path**
(`QualityReports(part=...)`, step sampling, `can_advance_from_step`,
`QuarantineDisposition`). What's missing is the outside-process modeling around it.

### Models

**Extend `Steps`** (`models/mes_lite.py`) — fields, no new table:

- `is_outside_process` bool (or add `OUTSIDE_PROCESS` to `STEP_TYPE_CHOICES`)
- `outside_supplier` FK → `Companies`, nullable (default vendor for the op)

**Extend `StepExecution`** (the per-part-visit record already exists) with send/return
stamps: `sent_out_at`, `sent_to` (Companies), `sent_reference` (PO/packing slip),
`returned_at`. OSP send-out/return is then just operational state on the visit.

**New (recommended): `OutsideProcessShipment`** — a genuine new aggregate: one
physical shipment of N parts to one vendor under one PO. Links the `StepExecution`s,
`supplier`, `shipped_at`, `reference`, `returned_at`. Gives one-PO / one-packing-slip
traceability and a natural batch for AQL on return. (Could be skipped for a barebones
v1 by stamping `StepExecution` fields per part via a bulk action, but the shipment
record is worth it.)

**Extend `PartsStatus`** (`models/mes_lite.py`) — add `AT_OUTSIDE_PROCESS` (parts
that have left the building) so they're visibly distinct from `IN_PROGRESS`. Confirm
naming.

### Service — `Tracker/services/mes/outside_process.py`

- `send_parts_out(step_executions, supplier, reference, user)` — stamp send fields /
  create shipment, set parts → `AT_OUTSIDE_PROCESS`.
- `receive_parts_back(shipment, user)` — stamp `returned_at`, set parts → `AWAITING_QA`,
  open a return inspection over the returned batch.
- Return inspection: part-centric `QualityReports` at the OSP step; AQL sample size
  from the shared service using the returned-batch count; gate advancement via
  existing `block_on_quarantine` / `can_advance_from_step`.

---

## 4. Where the two converge / diverge

| | A. Purchased material | B. Outside processing |
|---|---|---|
| Aggregate | `MaterialLot` | `StepExecution` / `Parts` |
| WO coupling | none (downstream `MaterialUsage` only) | heavy (mid-WO, step gating) |
| Plan source | `ReceivingInspectionPlan` per part-type/supplier | step's `required_measurements` + step sampling |
| AQL lot size | `lot.quantity` | parts in the returned shipment |
| Inspection record | `QualityReports(material_lot=…)` | `QualityReports(part=…)` |
| Disposition | `QuarantineDisposition` (RTS/scrap/use-as-is) | `QuarantineDisposition` (rework/scrap) |
| **Shared** | acceptance-sampling calculator (C=0 + Z1.4) · `MeasurementDefinition` · `QualityReports` · `QuarantineDisposition` · INSPECTOR role · approval engine (§6) | |

**Future unification:** a single "Incoming Inspection" queue in the UI surfacing both
lots `AWAITING_INSPECTION` and OSP shipments pending return inspection, even though the
backing records differ. Defer until both exist.

---

## 5. Reusing existing engines (validated against the codebase)

Both gates below ride engines that already exist — confirmed by reading the code, not
assumed. This is why receiving inspection is mostly *extension*, not *greenfield*.

### 5a. Approval engine → ride it directly ✅

`ApprovalRequest` (`models/core.py`) is **generic** (`GenericForeignKey`), with
`ApprovalTemplate` (sequencing, ALL/ANY/THRESHOLD flows, delegation, escalation) and
`ApprovalResponse` (e-signature + signature-meaning + verification method). Documents,
CAPA, Processes, PCR/PCO already ride it. Two seeds of intent already in-tree:
`Companies._is_versioned = True` is commented *"engineering judgment — supplier
qualification"*, and change_control has `customer_notification_required` =
*"Flag PPAP / customer-flow-down triggers. The actual submission is handled outside
this system."*

So model the **automotive PPAP / aerospace FAI (AS9102)** part-approval gate and the
**ASL / Nadcap** supplier-qualification gate as thin content models the existing
engine approves — **no new approval state machine, and PPAP/FAI document submission
stays external** (consistent with the existing flag; we track approval *state* only):

- **`PartApproval`** (`SecureModel`): `part_type` FK, `supplier` FK,
  `approval_type` (`PPAP` / `FAI`), `status`, `reference`, `expires_at`,
  `GenericRelation(Documents)` for evidence. Receiving gate = "is there an APPROVED,
  non-expired row for `(part_type, supplier)`?"
- **`SupplierQualification`** (`SecureModel`): `supplier` FK, `qualification_type`
  (`ASL` / `NADCAP`), `scope` (which processes/specs — matters for Nadcap special
  processes on Flow B), `status`, `certified_at`, `expires_at`.
- Add `Approval_Type` values `PPAP`, `FAI`, `SUPPLIER_QUALIFICATION`, `NADCAP`; wire the
  cascade in `apply_approval_decision_to_content_object()` to flip these to APPROVED.

### 5b. Sampling engine → extend the one engine (don't fork)

The existing engine (`SamplingRuleSet`/`SamplingRule`,
`services/mes/sampling_applier.py`, `services/dwi/sampling_decisions.py`) is
**per-part streaming** (`_should_sample(part)→bool` at step entry). AQL/C=0 is
**lot-terminal**. Grep confirms no `lot_size`/`sample_size`/`accept_number`/
`reject_number` today, and the CSP fallback is consecutive-fail tightening, not AQL
severity switching. Extension plan (also in §1's callout):

1. shared **stateless calculator** = the math (C=0 + Z1.4);
2. add `AQL` / `C_ZERO` to `SamplingRuleType` + AQL params;
3. **relax ruleset scoping** so a ruleset can bind `(part_type, supplier)` with **no
   step** (`SamplingRuleSet.step` is a non-null FK today — receiving has no step);
4. new **lot-acceptance record** (`sample_size`, `Ac`, `Re`, `defectives_found`,
   status) + a lot evaluator beside the per-part one; reuse `SamplingAuditLog` /
   `SamplingAnalytics`.

---

## 6. UI (under Production → new "Receiving" group)

1. **Material Lots** — list (`ModelEditorPage`) + bulk **Receive** form cloning the
   reman `CoreReceiveBatchPage` paste-grid pattern. (`MaterialLot` has zero UI today.)
2. **Receiving Inspections** — queue of lots `AWAITING_INSPECTION`; detail page shows
   derived sample size + Ac/Re from the RIP, measurement-capture grid, accept/reject,
   disposition-on-fail.
3. **Receiving Inspection Plans** — RIP CRUD (likely `/editor`).
4. **(Phase B)** Send-out action from the work-order / WO control center; return +
   inspect from the receiving queue.

---

## 7. Build sequence

- **Phase 0 — shared core:** the stateless **acceptance-sampling calculator**
  (C=0 + Z1.4) with exhaustive table tests; the sampling-engine extensions (§5b:
  new rule types, ruleset scope relaxation, lot-acceptance record). This is the
  riskiest, most-reused code — land it first, fully tested.
- **Phase 1 — A backend:** `ReceivingInspectionPlan` + `MaterialLot` status +
  `QualityReports.material_lot` + `PartApproval` / `SupplierQualification` + approval-type
  enum & cascade (§5a) + receiving service (with approval gate) + viewset actions +
  migration; regen `schema.yaml` + types. *Settle the API contract before any frontend.*
- **Phase 2 — A frontend:** Material Lots list + Receive paste-grid + inspection
  queue/detail + RIP editor + part/supplier-approval surfaces.
- **Phase 3 — B backend:** `Steps` OSP fields + `StepExecution` send/return +
  `OutsideProcessShipment` + `outside_process` service + `PartsStatus` + Nadcap-scope
  check on send-out + gating + schema.
- **Phase 4 — B frontend:** send-out action + return/inspect.
- **Phase 5 — (optional)** unified incoming-inspection queue.

## 8. Open items to confirm

1. **Sampling:** C=0 (Squeglia) as default, Z1.4 selectable — confirmed direction;
   verify no customer mandates a different specific plan.
2. `MaterialLot` status transitions as in-place operational mutations (documented
   exception to versioned-mutation rule).
3. **Approval gates depth:** is the §5a lightweight state-gate enough, or is fuller
   PPAP element / AS9102 form management wanted later? (Submission stays external for now.)
4. **Supplier-qualification scope** granularity — free-text vs. structured
   (process/spec rows), esp. for Nadcap special processes consumed by Flow B.
5. `PartsStatus.AT_OUTSIDE_PROCESS` naming.
6. `OutsideProcessShipment` as a real aggregate vs. bare `StepExecution` stamping.

---

## 9. Quality Gates — aggregate-signal automatic decisions

> Separate workstream from the §7 receiving build sequence. Numbered here as its
> own Phase 1 / Phase 2 because it generalizes machinery the receiving work already
> leans on (sampling fallback, AQL accept/reject). **Phase 1 is done** (see below).

### 9.0 The unifying observation

Four things in the system are the same shape — **observe a quality signal over a
window → cross a threshold → take an action** — modeled three different ways today:

| Instance | Signal / window | Threshold | Action | Lives in |
|---|---|---|---|---|
| Decision-point routing | one part's own QA/measurement | pass/fail or value | route to DEFAULT/ALTERNATE edge | `Parts.get_next_step` (`mes_lite.py`) |
| AQL lot accept/reject | defectives over a sample | Ac/Re | disposition the lot | `services/qms/receiving_inspection.py` |
| Sampling fallback (tighten/revert) | consecutive fails per (WO, step) | `fallback_threshold` | switch ruleset | `services/mes/sampling*.py` |

Quality Gates makes that one pattern explicit and lets a step react to an
**aggregate** signal (fail-rate / defective count over a window) with **one or more
of five actions**.

### 9.1 Phase 1 — sampling fallback, both directions ✅ (shipped)

Pure service-layer; no schema change.

- **Tighten** (`services/mes/sampling_ruleset.py:create_sampling_fallback_trigger`) now
  gates on the **consecutive-failure streak** (derived from `QualityReports`, so a PASS
  resets it) reaching `fallback_threshold`, and is **idempotent** (no duplicate
  `SamplingTriggerState`; also fixes a latent unique-constraint `IntegrityError`).
- **Revert** (`services/mes/sampling.py:update_sampling_trigger_state`) reads the revert
  duration from the **primary** ruleset (`used_as_fallback_for`), resets the good run on
  any failure, and **re-evaluates in-flight parts back to the primary ruleset** on
  deactivation (not just flips `active`).
- Tests: `Tracker/tests/test_sampling_fallback.py` (6).

### 9.2 Phase 2 — the aggregate gate (spec)

**Actions (closed set, all five in scope):**
`ROUTE_ALTERNATE`, `TIGHTEN_SAMPLING`, `HOLD_LOT`, `RAISE_CAPA_SCAR`, `REQUIRE_APPROVAL`.
No free-form scripting — each maps to an existing service.

**Config — additive fields on `SamplingRuleSet`** (already the per-`(step, supplier)`
versioned quality-policy object; the step-editor "Sampling Rules" dialog already loads
it). All nullable / blank so existing rulesets are unaffected:
- `gate_metric` — `FAIL_RATE_PCT` | `CONSECUTIVE_FAILS` | `DEFECTIVE_COUNT` (blank = no gate).
- `gate_threshold` (Decimal) — pct for `FAIL_RATE_PCT`, count for the others.
- `gate_window` (`WORK_ORDER` | `ROLLING_N` | `LOT`) + `gate_window_n` (for `ROLLING_N`).
- `gate_min_sample` — guard so `1/1 = 100%` doesn't fire `FAIL_RATE_PCT` early.
- `gate_actions` — JSON list of the five codes (multi-select).
- action params: `gate_approval_template` (FK, nullable), `gate_capa_type`
  (`CORRECTIVE`/`SUPPLIER`), `gate_capa_severity`.

The existing `fallback_threshold` / `fallback_ruleset` / `fallback_duration` stay and keep
working: **`CONSECUTIVE_FAILS` + `TIGHTEN_SAMPLING` is the same thing they already
express.** The dispatcher treats a ruleset with those set (and no `gate_metric`) as an
implicit `{metric: CONSECUTIVE_FAILS, actions: [TIGHTEN_SAMPLING]}` gate — no destructive
migration; legacy config keeps firing. (Opportunistic later cleanup: fold them into the
gate fields.)

**One new table — `StepGateFiring`** (`SecureModel`): the **idempotency marker + audit
trail** of an automated decision. Fields: `ruleset`, `step`, `work_order` (nullable),
`material_lot` (nullable), `metric`, `metric_value`, `threshold`, `fired_at`,
`actions_taken` (JSON), `triggered_by_report` / `triggered_by_lot`, and result FKs
(`created_capa`, `approval_request`) for traceability. Unique on
`(tenant, ruleset, work_order, step)` (and the lot variant) ⇒ one fire per window.
Justified as a genuine new aggregate (record of an automatic quality decision: what
fired, on what signal, with what value) — not merely audit-trail duplication.

**Engine — new `services/qms/quality_gate.py`:**
`evaluate_step_gate(*, ruleset, work_order=None, material_lot=None, trigger)` →
1. resolve the gate (explicit `gate_*` or the implicit legacy fallback gate);
2. compute the metric over the window from `QualityReports` (or the lot sample for
   receiving), honoring `gate_min_sample`;
3. if below threshold or a `StepGateFiring` already exists for the window → return;
4. else create the `StepGateFiring`, then dispatch each action to its existing service:
   - `ROUTE_ALTERNATE` → mark the window so routing diverts (see below);
   - `TIGHTEN_SAMPLING` → `create_sampling_fallback_trigger` (Phase 1, already gated);
   - `HOLD_LOT` → `services/mes/inventory.quarantine_lot` / hold the WO batch;
   - `RAISE_CAPA_SCAR` → `services/qms/scar.open_scar` (SUPPLIER) or CAPA (CORRECTIVE);
   - `REQUIRE_APPROVAL` → `services/core/approval.create_approval_request`.

**Two entry points feed the one dispatcher** (no new firing locations):
- in-process → from `process_quality_report_side_effects` (already runs on every PASS/FAIL);
- receiving → from `evaluate_lot_acceptance` (reject path can now also auto-SCAR + hold +
  require approval via the same config).

**Routing integration (`ROUTE_ALTERNATE`)** — add `decision_type = 'AGGREGATE'` to
`Steps`. In `Parts.get_next_step`, an `AGGREGATE` decision point routes to the
`ALTERNATE` edge when a `StepGateFiring` exists for the part's `(work_order, step)`, else
`DEFAULT`. Reuses the existing `_get_edge` / `StepEdge` machinery — no new routing code.

**UI — recast the step-editor "Sampling Rules" dialog as "Acceptance & escalation"**
(`step-sampling-editor.tsx`): the **AQL** header fields (for `RECEIVING` steps; answers the
open "set AQL in the process editor" gap) **and** the gate config — metric/window/threshold,
the five-action multi-select, and conditional param fields (approval template, CAPA
type/severity). One surface, in the process editor, for a step's whole acceptance policy.

**Build order:** 2a backend (fields + `StepGateFiring` + dispatcher + the deferred
`FAIL_RATE_PCT`; migration; regen schema/types) → 2b `decision_type='AGGREGATE'` routing →
2c the step-editor "Acceptance & escalation" UI. Tests at each.

### 9.3 Open items (Quality Gates)

1. `StepGateFiring` as a new table vs. a JSON/flag on `SamplingTriggerState` — leaning new
   table for the audit value; confirm.
2. `ROUTE_ALTERNATE` semantics for **in-flight parts already past the gate step** — divert
   only parts not yet advanced, or also pull back? (Default: only not-yet-advanced.)
3. `HOLD_LOT` target when the signal is in-process (no `MaterialLot`): hold the WorkOrder
   batch vs. quarantine the affected parts.
4. Whether to refactor the legacy `fallback_*` fields into `gate_*` now or leave the
   implicit-gate shim (default: leave it, clean up opportunistically).
