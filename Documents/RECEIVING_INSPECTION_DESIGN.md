# Receiving Inspection — Design

Status: **partially built** · Owner: cisherwood · Last updated: 2026-07-01

## Status & how to read this doc

**Read order.** §1–§13 are the original **proposed design** (2026-06-23), kept for
rationale. §14–§17 are the **current-state truth** (2026-07), written after Flow A, the
sampling engine, supplier qualification, the quality-gate engine, and a **DWI-based
receiving runtime** were built. **When the body and §16/§17 disagree, §16/§17 win.**

**Build-state index** — code-verified (grep/read); details in §16 (as-built) and §17 (seam audit).

| § | Topic | State (2026-07) |
|---|---|---|
| 1 | Acceptance-sampling calculator | **Built + table-verified (2026-07-06)** — C=0 / Z1.4 / **Z1.9**. API is `compute_sample_plan()` → 8-field `SamplePlan`. Z1.4 Table II-A transcribed from the MIL-STD-105E scan with **arrows preserved + followed** (fixed the prior bug where arrows were flattened to numbers — the bogus M/N `21`s). Z1.9 std-dev k **verified B–J**; **K–P fail closed** (raise, not guess) pending a purchased Z1.9-2003 copy. **Three-way severity switching (Normal/Tightened/Reduced, Tables II-A/B/C) built (2026-07-07)** — automatic from lot history via `services.qms.severity_switching`. |
| 2 | Flow A — purchased-material receiving | **Built** — but inspection runs through the **DWI runtime** (§16), not the bespoke page this section describes. |
| 3 | Flow B — outside processing (OSP) | **Built end-to-end** (2026-07-06). Backend: `Steps.is_outside_process`/`outside_supplier`, `OutsideProcessShipment` aggregate (SENT/RETURNED/CLOSED), `StepExecution.outside_process_shipment`, `PartsStatus.AT_OUTSIDE_PROCESS`, `QualityReports.osp_shipment` (subject constraint widened to at-most-one), `services/mes/outside_process.py`, viewset + endpoints. FE: send-out (quantity-first dialog) + receive-back on the WO control page (`OutsideProcessPanel`), OSP completion adapter (accept/reject on finish), detail-page badge, flow-editor "Outside process" toggle + vendor on RECEIVING nodes, and a shipper board at `/production/outside-processing` (Supply: *Ready to ship* / *At vendor*). Return inspection reuses the DWI runtime. **Nothing left.** |
| 4 | Unified incoming-inspection queue | **Built** (2026-07-06) — one worklist across both flows (lots + OSP returns) with a `source` column, SAP QM QA32-style. `GET /api/IncomingInspection/` + `/production/incoming`. Supersedes §4's "future unification" note. |
| 5a | Approval-engine receiving gate | **Built** (2026-07-04) — both halves: supplier-qualification soft-hold **and** `PartApproval` (PPAP/FAI) soft-hold + approval cascade. |
| 5b / 13 | Sampling-engine model | **Built** — `family` discriminator + registry (§13); Z1.9 included. |
| 6 | Receiving UI | **Built, DWI-based** — supersedes this section (§16). |
| 9 | Quality gates | **Engine built**; lot trigger + fire-without-actions **now wired** (2026-07-02, §9.4). |
| 10 | Supplier qualification / ASL | **Built** (model, service, UI, expiry task scheduled); `evaluate_supplier_standing` loop **built recommend-only** (2026-07-04, §10.3). |
| 14 | make-or-buy `PartTypes` | **Deferred** (scoped, §14). |
| 15 | Disposition consolidation | **Fixed** (2026-07-02) — auto-create signal skips receiving QRs (§15). |
| 16–18 | As-built additions · seam audit · **backlog** | **Current-state truth**; §18 is the single prioritized to-do. |

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
> trivial `100%` / `skip-lot`. Z1.4 tightened/reduced **severity switching is built**
> (automatic from lot history); double/multiple sampling stays additive. Confirm no
> customer mandates a different plan.

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
# AS BUILT (2026-07): the shipped API — this supersedes the original sketch below.
@dataclass(frozen=True)
class SamplePlan:
    sample_size: int        # n
    accept_number: int      # Ac (sentinel 0 for variables)
    reject_number: int      # Re (sentinel 1 for variables)
    strategy: str           # 'C0' | 'Z14' | 'Z19'
    inspection_level: str   # 'I' | 'II' | 'III'
    severity: str           # 'NORMAL' | 'TIGHTENED' | 'REDUCED'  (⚠ currently a passthrough label — not used to switch tables)
    method: str = ""        # '' | 'K_SINGLE'  (variables k-method)
    k: float | None = None  # Z1.9 acceptability constant

def compute_sample_plan(*, lot_size, aql, inspection_level='II', severity='NORMAL', strategy='C0') -> SamplePlan
def evaluate_variables(*, values, usl=None, lsl=None, k) -> dict   # Z1.9 x̄/s vs k verdict
```

> ⚠ **Table-verification status (2026-07):** Z1.4 code letters (all levels) and
> sample-sizes-by-letter are verified; Z1.9 sample sizes verified. **Outstanding:**
> the `_Z14_NORMAL_AC` M/N high-AQL cells are suspect (repeated `21` placeholders
> where the standard has up-arrows), and the full Z1.9 `k` table + C=0 columns need a
> controlled-copy QA sign-off. Un-tabulated cells fail closed (raise); non-standard
> AQLs snap up.

- Pure computation, **no DB / no tenant scope** — a stateless utility module.
- **Pluggable strategies, not Z1.4-only.** Encode both:
  - **C=0 (Squeglia)** — zero-acceptance-number plans. *Default*, because most
    auto (IATF customer-specific reqs) and aero primes prohibit AQL>0.
  - **Z1.4** (ANSI/ASQ, ex-MIL-STD-105E) — single sampling, levels S-1..S-4 + I/II/III,
    via the two standard tables (lot-size+level → code letter; code letter+AQL → n,Ac,Re)
    incl. arrow rules. **Severity switching (Normal/Tightened/Reduced) is built**;
    double/multiple sampling is a clean extension point.
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

## 2. Flow A — Purchased-material receiving (lot-centric)  ·  **[BUILT — inspection is DWI-based, see §16]**

**Work-order coupling: none.** The lot is inspected before it ever enters
production. The only WO touchpoint already exists downstream: an accepted lot is
consumed at a step via `MaterialUsage`.

### As built (2026-07) — supersedes the model/service/API sketch this section originally carried

> The original §2 proposed a standalone `ReceivingInspectionPlan` model, a
> `derive_sample_plan`/`open_receiving_inspection`/`record_receiving_result` service, and a
> `PartApproval` receiving gate. **None of those names/shapes match the code.** Accurate version:

- **No `ReceivingInspectionPlan` model.** A "RIP" is a **`RECEIVING` `Steps` node** (standalone
  /process-free or in a process) carrying its `MeasurementDefinition` characteristics + a
  step-scoped `SamplingRuleSet` (family LOT_ACCEPTANCE / VARIABLES). Resolution:
  `resolve_receiving_step(part_type)` + `resolve_sampling_ruleset(step, supplier)`.
- **`MaterialLot`** gained the status choices (fields, no new table):
  ```
  RECEIVED → AWAITING_INSPECTION → ACCEPTED → IN_USE → CONSUMED
                                ↘ QUARANTINE → REJECTED / SCRAPPED
  ```
  Status transitions mutate in place (documented exception to versioned-mutation — operational
  state, not spec edits).
- **`QualityReports` is the lot-acceptance record:** nullable `material_lot` FK + snapshot
  `sample_size`/`accept_number`/`reject_number` (+ `acceptability_constant_k`,
  `variables_characteristic` for Z1.9) + `defectives_found`; `CheckConstraint` exactly-one-of
  `part`/`material_lot`.
- **Service `services/qms/receiving_inspection.py`** (real names): `open_inspection(lot, user)`,
  `record_inspection` / `record_sample_units` / `record_bulk`, `evaluate_lot_acceptance`
  (family-correct: defective count vs Ac/Re, or Z1.9 x̄·s vs k), `accept`, `reject`.
  **`PartApproval` gate — BUILT (2026-07-04):** `_held_for_unapproved_part` soft-holds a lot
  whose `(part_type, supplier)` lacks an active PPAP/FAI `PartApproval` (gated by
  `PartTypes.requires_part_approval`), alongside the supplier-qualification soft-hold; grant
  rides the approval engine. See §5a.
- **API:** `MaterialLotViewSet` actions `open_inspection` / `record_inspection` / `record_units`
  / `record_bulk` / `sample_plan` / `evaluate_receiving` / `accept` / `reject`. No
  `ReceivingInspectionPlanViewSet` — the RIP is a `Steps` row via the standard step endpoints.
- **Inspection UX = the DWI runtime** (§16), not a bespoke page.

---

## 3. Flow B — Outside-processing / subcontract receiving (part/step-centric)  ·  **[BUILT end-to-end 2026-07-06 — see §16; this section is the original design]**

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

**Unification — BUILT (2026-07-06).** A single **Incoming Inspection** worklist surfaces both
lots awaiting inspection and OSP shipments (out / returned) in one list, keyed by a `source`
column (`PURCHASED_LOT` / `OUTSIDE_PROCESS`) — the SAP QM QA32 "inspection-lot origin" pattern.
`GET /api/IncomingInspection/` (`services/qms/incoming_inspection.build_incoming_rows`, read-only
aggregation) → `/production/incoming`, with Source + Status filters and one `Inspect` action that
dispatches to the correct runtime by source. This is a separate surface from **Materials**
(`/production/material-lots`, the full lot inventory) — worklist vs. material master, per the same
QMS split. Nav (Supply group): *Incoming Inspection*, *Materials*, *Receiving Inspection Plans*,
*Supplier Quality*.

---

## 5. Reusing existing engines (validated against the codebase)

Both gates below ride engines that already exist — confirmed by reading the code, not
assumed. This is why receiving inspection is mostly *extension*, not *greenfield*.

### 5a. Approval engine → ride it directly  ·  **[PARTIAL: `SupplierQualification` built (§10); `PartApproval` PPAP/FAI NOT built]**

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

> **As built:** **`SupplierQualification`** is built as the **§10** model (scope_type
> PART_TYPE/COMMODITY/SPECIAL_PROCESS, basis, effective/expiry, grant-via-approval), **not** the
> `qualification_type ASL/NADCAP` sketch above; §10 is authoritative. **`PartApproval` is now
> built too (2026-07-04)** — model (`part_type`, `supplier`, `approval_type` PPAP/FAI, status,
> effective/expiry, approval_request), service `services/qms/part_approval.py`, `Approval_Type`
> PPAP/FAI + cascade, `PartTypes.requires_part_approval`, the `_held_for_unapproved_part`
> receiving soft-hold, viewset (`PartApprovals`), expiry beat task, and tests. Approval-STATE
> only — PPAP-element/AS9102 form management stays external.

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

> **As built (2026-07):** items 1–3 are done (family discriminator + registry §13, incl.
> Z1.9; step-less `(part_type, supplier)` scoping). Item 4 landed **differently**: the
> lot-acceptance record is **`QualityReports`** itself (`material_lot` + `sample_size` /
> `accept_number` / `reject_number` / `defectives_found`, evaluated by
> `evaluate_lot_acceptance`) — **not a new table, and it does NOT reuse
> `SamplingAuditLog` / `SamplingAnalytics`** (those stay per-part). So the "grep confirms
> none exist today" notes above are historical — those fields now exist on `QualityReports`.

---

## 6. UI (under Production → new "Receiving" group)  ·  **[BUILT, but DWI-based — §16 supersedes the bespoke inspection page below]**

**As built (2026-07):**
- **Materials** hub (status-segmented) + bulk **Receive** paste-grid — built.
- **Receiving Inspection Plans** — RIP list + editor (standalone *and* in-process); authors
  characteristics / sampling / documents / **DWI substeps** — built.
- **Receiving inspection** — **runs through the DWI operator runtime** (§16): the inspector
  walks the step's substeps, then decides the lot in-runtime (family verdict + accept/reject +
  guided disposition). The bespoke "queue + detail page with a capture grid" originally
  sketched here is superseded.
- **(Phase B / OSP)** send-out + return-inspect — **built** (§3, §16).

---

## 7. Build sequence

> **Status (2026-07-06):** Phases 0–5 are **done.** Shared core, Flow A (backend + DWI
> frontend, §16), Flow B / OSP (backend + frontend, §3/§16), and the unified incoming-inspection
> queue (Phase 5, §4) are all built. Remaining follow-ups are narrow: the step-editor OSP toggle,
> sampling-table QA sign-off (§18 item 2), and the deferred enterprise-tier items (§11).

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
- **Phase 3 — B backend — done:** `Steps` OSP fields + `StepExecution`/`OutsideProcessShipment`
  send/return + `outside_process` service + `PartsStatus` + gating + schema. *(Nadcap per-spec
  scope on send-out not enforced — see §10.9 open item 1.)*
- **Phase 4 — B frontend — done:** send-out (quantity-first) + receive-back + DWI return
  inspection + `OSP_COMPLETION` accept/reject.
- **Phase 5 — done:** unified incoming-inspection queue (§4).

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

**Actions (closed set):**
`ROUTE_ALTERNATE`, `TIGHTEN_SAMPLING`, `HOLD_LOT`, `RAISE_CAPA_SCAR`, `REQUIRE_APPROVAL`.
No free-form scripting — each maps to an existing service.

> **Refined in §9.5 (this is the final model):** the five listed here are the *original*
> set. Routing (`ROUTE_ALTERNATE`) is **not** a gate action — it's edges + the `AGGREGATE`
> decision type; tightening (`TIGHTEN_SAMPLING`) is the per-family escalation section. Only
> **`RAISE_CAPA_SCAR`** and **`REQUIRE_APPROVAL`** remain **user-offered** gate actions.
> `ROUTE_ALTERNATE`/`TIGHTEN_SAMPLING`/`HOLD_LOT` stay in the enum (`quality_gate.py` still
> dispatches them) but aren't offered in the dialog. Read §9.5 for the rationale.

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

### 9.4 Remaining backend — gate trigger for lot/receiving steps (KNOWN TODO)

The gate engine and all five actions are **built and tested**, and the **in-process
trigger is wired**: a FAIL `QualityReport` runs `process_quality_report_side_effects →
evaluate_step_gate`, so gate actions fire on ordinary in-process steps today.

**The lot/receiving trigger is NOT wired yet.** `evaluate_step_gate` supports a
`material_lot` subject, but nothing calls it from the receiving path —
`evaluate_lot_acceptance` doesn't invoke the gate, and a lot `QualityReport` has no
`part`, so the in-process entry point bails. **Consequence:** a quality gate configured
on a **lot-acceptance / RECEIVING step** (e.g. via the flow-editor dialog) is **persisted
but inert** — its "actions when tripped" never fire.

**Backend task:** wire the lot entry point — call `evaluate_step_gate(ruleset, material_lot=…)`
from `evaluate_lot_acceptance` (and/or the receiving QR side-effects) so lot gates fire on
lot acceptance/rejection, mirroring the in-process path. Small, additive; until it lands,
the dialog's gate config for lot steps is configuration-only.

> **(2026-07)** Still not wired — grep-confirmed. Note the acceptance decision now runs
> through the **DWI runtime** (`ReceivingAcceptanceStage`) + the `evaluate_receiving`
> action, not the bespoke page this section assumed. Place the gate hook where the
> lot verdict is actually decided (inside/after `evaluate_lot_acceptance`, which both the
> `record_bulk` path and `evaluate_receiving` call) so it fires regardless of which UI drove it.

**Related — gate must fire on threshold-cross regardless of side-effect actions.**
Routing is NOT a gate action — post-inspection routing is the step's edges + its
decision type (`AGGREGATE` reads the `StepGateFiring`). `ROUTE_ALTERNATE` has been
removed from the gate's action menu accordingly; gate actions are now side-effects only
(hold / CAPA-SCAR / approval). **Consequence:** `evaluate_step_gate` currently no-ops
when `gate_actions` is empty (`if not gate_metric or not gate_actions: return None`), so a
**routing-only gate** (metric set, no side-effects, just drives the AGGREGATE edge) would
never record a firing and routing would never trigger. **Backend task:** record a
`StepGateFiring` whenever the metric crosses its threshold, independent of whether any
side-effect actions are configured — actions are optional consequences of a firing, not a
precondition for it.

### 9.5 Refined gate-action model (separation of concerns)

Through the dialog design the gate's responsibilities narrowed to a clean three-way split,
because routing and tightening each already have a home:

- **Routing — where the subject goes** (next / rework / quarantine-MRB / scrap /
  return-to-supplier): **edges → destination nodes**, chosen by the step's decision type.
  `AGGREGATE` reads the `StepGateFiring` to pick the edge. These are NOT gate actions —
  quarantine/scrap/etc. are *places the subject goes*, not side-effects performed in place.
- **Tightening — stricter inspection:** the **per-family Escalation section** (streaming =
  stricter rules + escalate-after-N; lot = severity switching, Z1.4 Normal→Tightened→Reduced).
  NOT a gate action.
- **Gate side-effects — parallel things that DON'T move the subject:** the only remaining
  gate actions — **Raise CAPA/SCAR** and **Require approval**.

So `ROUTE_ALTERNATE`, `TIGHTEN_SAMPLING`, and `HOLD_LOT` were removed from the dialog's
gate-action menu (kept in the engine/enum for now, just not user-offered). Quarantine/scrap
are modeled as nodes+edges: for **parts** this rides `get_next_step` + edges; for **lots** it
needs the lot-routing backend (RECEIVING node's reject edge → a disposition/scrap node) — the
same lot gap noted in §9.4 / §13.4.

---

## 10. Supplier Qualification / ASL  ·  **[BUILT: model + service + expiry task + UI. NOT built: §10.3 standing loop]**

> The SQM control that's structurally missing today. Current SQM can *measure*
> (scorecard) and *react* (SCAR) but cannot *gate* on approval status. This track
> adds qualification state, gates receiving on it, and closes the scorecard→standing
> loop. The "Approved Supplier List" is a **derived view** (suppliers with an active
> approved qualification), not a separate table.

### 10.0 Shape

One new aggregate, `SupplierQualification` (`SecureModel`, in `models/qms.py`): a
record that a supplier is approved for a **scope**, with a lifecycle and an expiry.
Re-qualification creates a **new row** (history preserved); status changes are
mutations tracked by auditlog — not `create_new_version`.

Fields:
- `supplier` (FK Companies)
- `scope_type` — `PART_TYPE` | `COMMODITY` | `SPECIAL_PROCESS`
- `part_type` (FK PartTypes, null) — when scope_type=PART_TYPE
- `scope_label` (char) — commodity or special-process name (e.g. "Castings",
  "Heat Treat AMS2750"); used for COMMODITY/SPECIAL_PROCESS scopes
- `status` — `PENDING` | `APPROVED` | `CONDITIONAL` | `SUSPENDED` | `EXPIRED` | `DISQUALIFIED`
- `basis` — `AUDIT` | `PPAP` | `FAI` | `SURVEY` | `HISTORICAL`
- `effective_date`, `expiry_date`
- `approval_request` (FK ApprovalRequest, null) — the grant rides the approval engine
- `qualified_by`, `notes`
- `documents` (GenericRelation) — audit report / cert / PPAP package attachments

ASL = `SupplierQualification.objects.filter(status__in=['APPROVED','CONDITIONAL'],
effective_date<=today, expiry_date>=today)`. No ASL table.

Enforcement flag: add `PartTypes.requires_supplier_qualification` (bool, default
False) — fields-over-tables; the part type declares whether a qualified source is
mandatory. (Optional tenant default later.)

### 10.1 Service — `services/qms/supplier_qualification.py`

- `qualifying_record_for(*, supplier, part_type=None, commodity=None, special_process=None)`
  → the active qualification covering that scope, or None. Scope match: part_type FK
  first, then `scope_label` for commodity/special-process.
- `is_supplier_qualified(...)` → bool wrapper.
- Lifecycle transitions (services, not `save()`): `open_qualification` (PENDING),
  `grant` (→ APPROVED/CONDITIONAL, creates the ApprovalRequest via
  `create_approval_from_template`; status flips on approval completion),
  `suspend`, `disqualify`, `expire`. `ValueError` on bad-state.
- `QualificationStatus` frozen dataclass DTO for the resolved standing
  (status, basis, expiry, days_to_expiry, covering_record_id).

### 10.2 Gate on receiving

In `services/qms/receiving_inspection.py:route_received_lot`, after resolving
supplier + part_type:
- If `part_type.requires_supplier_qualification` and no active qualification covers
  the scope → **soft hold**: route the lot to `QUARANTINE` (not `AWAITING_INSPECTION`),
  set a reason, and emit a `SUPPLIER_UNQUALIFIED` event (notification-rule eligible);
  optionally auto-open a SCAR. Receiving is physical reality, so this holds the lot
  from `ACCEPTED`/dock-to-stock rather than rejecting the receipt outright.
- Else proceed to normal routing.

Default enforcement = **soft hold** (hold, don't block the receipt). A hard pre-receipt
block is a later option behind the same flag.

### 10.3 Scorecard ↔ qualification loop  ·  **[BUILT recommend-only, 2026-07-04]**

> **As built:** `services/qms/supplier_standing.py` — `evaluate_supplier_standing(supplier)`
> reads the scorecard and returns a `StandingRecommendation`; `review_and_notify` emits
> `supplier.standing_review`; the `review_supplier_standings` beat task runs it daily
> cross-tenant. **RECOMMEND-ONLY: it never transitions the qualification** (auto-suspending a
> supplier on a metric is consequential — a human confirms via the SQ lifecycle). Tests assert
> the invariant (status unchanged after a SUSPEND/RESTORE recommendation). The recommendation
> maps the scorecard's own A/B/C rating (single source of thresholds) → REVIEW_CONDITIONAL /
> REVIEW_SUSPEND / REVIEW_RESTORE.

- `evaluate_supplier_standing(supplier)` (service): reads the existing scorecard
  rollup; on threshold breach (reject_rate / OTD / open-SCAR count over limits)
  ~~transitions APPROVED→CONDITIONAL or →SUSPENDED~~ **recommends** the review + emits an
  event. Opt-in, run from the scorecard refresh or a beat task.
- Connects to the gate engine's severity loop: a CONDITIONAL/SUSPENDED supplier can
  drive TIGHTENED sampling for its receiving step (set the supplier-scoped
  `SamplingRuleSet.severity`). ⚠ **Note:** setting `severity` is a **numeric no-op until Z1.4
  severity switching is built** (`compute_sample_plan` ignores `severity` today), so this half
  is advisory. A sustained-good standing earning skip-lot / dock-to-stock stays deferred (§11).

### 10.4 Expiry

Celery beat task (`(tenant_id)` arg, re-fetch in task) scans for
`status=APPROVED/CONDITIONAL` past `expiry_date` → `expire()` + notify. Surface
"expiring within N days" in the UI.

> **As built (2026-07):** `tasks.expire_supplier_qualifications` exists and works, **but
> is NOT registered in `CELERY_BEAT_SCHEDULE`** — so it never runs on its own. Add a beat
> entry to make the expiry loop live. (The "notify" side isn't wired either.)

### 10.5 Serializers / viewsets / perms

- `SupplierQualificationSerializer` (+ resolved `QualificationStatus` read field).
- `SupplierQualificationViewSet` (`TenantScopedMixin, ExcelExportMixin, ModelViewSet`),
  `filterset_fields=['supplier','scope_type','part_type','status']`,
  `search_fields=['scope_label','supplier__name']`; `@action`s `grant`/`suspend`/
  `disqualify` delegating to the service; `action_permissions` gating grant on
  `approve_supplierqualification` (group-eligibility marker per the 3-paradigm note).
- Regenerate `schema.yaml` + types.

### 10.6 UI

- **ASL page** (under Supplier Quality / Inventory): suppliers × scope with status
  badges; filters for status / commodity / special-process / **expiring soon**.
- **Qualification CRUD + detail**: create (supplier, scope, basis, dates), attach
  docs, **submit for approval** (rides the approval engine), status timeline.
- **Badges in context**: qualification status on the supplier scorecard card and a
  warning banner on the receiving inspection page when the lot's supplier isn't
  qualified for that part type.
- **Receiving queue**: flag/segregate lots soft-held for `SUPPLIER_UNQUALIFIED`.

### 10.7 Companion: disposition lot/supplier wiring (RTV loop)

Tightly related, small: add `material_lot` + `supplier` FKs to
`QuarantineDisposition`; a `RETURN_TO_SUPPLIER` disposition auto-links/opens a SCAR
against the supplier and feeds the scorecard. Turns reject → disposition(RTV) → SCAR
→ scorecard → standing into one connected flow instead of three hand-stitched records.

> **Note (2026-07):** the `material_lot` FK is a **query/UX convenience**, not a
> correctness requirement — a lot disposition is already reachable via
> `quality_reports → QualityReports.material_lot`. It's worth adding to power a
> filterable "Held lots" surface, but don't scope it as a blocker.

### 10.8 Build order
- **A (backend):** model + `requires_supplier_qualification` flag + migration; service
  (transitions + grant-via-approval + scope resolver); receiving soft-hold gate;
  serializer/viewset/perms; expiry beat task; schema/type regen; tests.
- **B (UI):** ASL list + qualification CRUD/detail + approval submit + context badges +
  expiring-soon view.
- **C (loop):** `evaluate_supplier_standing` + scorecard→severity wiring (ties to §9)
  + the §10.7 disposition RTV wiring.

### 10.9 Open items
1. **Scope granularity** — start with the three `scope_type`s above; confirm
   commodity/special-process is enough vs. per-spec rows (esp. Nadcap for Flow B).
2. **Enforcement** — soft hold (default) vs. hard pre-receipt block, per part type.
3. **PPAP/FAI depth** — `basis=PPAP/FAI` is a marker here; full AS9102/PPAP element
   management stays out of scope (separate track).
4. Whether `evaluate_supplier_standing` auto-suspends or only *recommends* (manual
   confirm) — auto-transition vs. flag-for-review.

---

## 11. Facility-size guardrails (read before building Tier 3)

**Target facility: < 200 heads** — small-to-mid job shops and lower-volume aero/auto
suppliers. This boundary is a scoping decision, not a capacity limit; it exists to
stop the receiving/SQM/quality-gate work from silently growing an enterprise tier.

**Governing principle.** AS9100 / IATF flowdowns mandate certain controls *regardless
of headcount* — a 30-person aero supplier needs them to pass audit as much as a
3,000-person one. So "small shop" does **not** mean "skip the control"; it means
**implement the audit-required floor, reuse existing aggregates, and don't add
machinery the standard doesn't force.**

### Right-sized for < 200 heads (in scope — already built/specced)
- Receiving inspection + **AQL / C=0** sampling (C=0 is the small-shop-friendly default).
- Disposition / MRB, the report→disposition→CAPA chain as the **NCR**, and **SCAR**
  (rides CAPA — no parallel system).
- **Supplier scorecard** (a few computed metrics, not a portal).
- **Quality-gate engine** — opt-in; the common case (tighten after N consecutive
  fails) must stay one-field-simple.
- **Lightweight ASL / SupplierQualification** — one table + a flag, simple lifecycle,
  grant rides the existing approval engine, soft-hold not hard-block. This is the
  audit-required floor, not an SQM suite.

### Deferred as enterprise-tier — DO NOT build speculatively
Build these **only when a specific named customer/standard requirement forces it**, and
record that requirement in the PR:
- PPAP element management / full AS9102 FAI form management.
- Scheduled **supplier-audit programs** with findings/CARs.
- **True PPM** (vs. the reject-rate proxy the scorecard uses).
- **Scorecard-driven skip-lot / dock-to-stock automation** (earning/reversion).
- Full **append-only inventory ledger** (the status-flip seam is sufficient until a
  real inventory/cost requirement appears). ✅ **(2026-07-06) Traceability defer verified:**
  `MaterialUsage` captures the full chain — `lot`/`harvested_component` → `part` → `step`
  (plus `work_order`, `qty_consumed`, `consumed_by`, `consumed_at`) and is exposed via a CRUD
  viewset + serializer, so "which lot was consumed at which step" / "which parts came from
  lot X" is answerable and recordable. The ledger defer **stands**. **But a real gap remains
  (NOT enterprise-tier, NOT the ledger):** nothing *writes* `MaterialUsage` automatically —
  there is no consumption service wired into the build/step flow, so the traceability chain is
  only as complete as manual data entry. Closing it is a small "record consumption at step"
  hook (a writer + a capture point), tracked as a follow-up — distinct from the ledger.

**Exception — Flow B (outside processing) is right-sized.** Sending parts out for
plating / heat-treat / grinding is *common* at small job shops, so OSP receiving is
in-scope and ranks **above** the SQM-depth items in priority.

### UI discipline (the real calibration point)
The risk isn't the backend — it's UIs that expose enterprise complexity to a 15-person
shop. Rule of thumb:
- **Default and preset the common case.** The quality-gate config must keep
  "tighten after N fails" as a single field; the full metric × window × 5-action
  matrix lives behind an **Advanced** disclosure.
- Don't make small-shop users configure a decision engine to get basic behavior.

### Guardrail check
Before starting any Tier-3 item (§8/§10.9 deferrals above), answer in one line:
*which customer or clause requires this at < 200 heads?* If there isn't one, it waits.

---

## 12. Competitive UI gaps (from a survey of comparable MES/QMS tools)

Surveyed ProShop ERP, QT9, uniPoint, Tulip, ETQ Reliance, MasterControl, Ideagen,
Net-Inspect / InspectionXpert / High QA / 1factory. We match the core loop (receiving
log → inspection queue → per-characteristic checklist → accept/reject → AQL/C=0 → hold;
scorecard; SCAR-via-CAPA; NCR→disposition→CAPA; ASL with status/scope/expiry; 5-why /
fishbone; approval engine; doc control; dashboard; inbox). Gaps, tiered against the §11
< 200-head boundary:

### Tier 1 — small, high-value, right-sized (build)
1. **Supplier rating tier + badge (A/B/C, green/amber/red)** with the action it implies.
   Universal (QT9, Ideagen, ETQ, uniPoint); we showed raw metrics only. *(Building now:
   `SupplierScorecard.rating`/`rating_reason` + a tier badge.)*
2. **Reject → one-click NCR/disposition.** Confirmed standard ("create NC from a failed
   record"). This is the §10.7 reject→disposition wiring — validated as expected, needs
   the `QuarantineDisposition.material_lot` FK first.
3. ~~**CoC capture at receipt.**~~ **DONE (2026-07-06):** dedicated CoC upload on the receiving
   inspection page populates `MaterialLot.certificate_of_conformance` (the FileField the
   scorecard's `coc_compliance` reads) via a multipart PATCH — distinct from the generic
   attached-Documents button, which does not feed that metric.
4. ~~**Proactive requalification reminders**~~ **DONE (2026-07-06):** `notify_expiring_qualifications`
   beat task (daily) emits `supplier.qualification_expiring_soon` at the 60- and 30-day marks
   (idempotent per window), alongside the existing expire-on-lapse notification.
5. **Print / PDF the inspection record + NCR/disposition** (audit packet). Excel export +
   ReportButton exist; a clean record PDF does not.
6. **Inline photo/defect capture** on inspection + NCR (Tulip Image widget benchmark).
   DWI attachments + QualityReport documents exist; per-defect capture on the
   inspection/reject screen should be confirmed/strengthened.

### Tier 2 — moderate, optional
7. **COPQ / cost capture** on NCR/disposition (QT9, uniPoint "assign dollars to poor quality").
8. **Barcode scan-to-start + label print** at the dock (uniPoint, Predator, Tulip) — tablet-first receiving.
9. **"My quality tasks" aggregation** — confirm the Inbox rolls up inspections-due + SCAR
   responses + CAPA tasks + approvals in one queue (the universal pattern).

### Tier 3 — large competitor features, deliberately deferred (§11 guardrail applies)
- **Supplier portal** for external SCAR/PPAP response (ETQ, QT9, 1factory) — the standout
  thing we lack; large build (external auth/tenancy) and small shops often use email.
  Conscious "later / maybe not for this segment" decision, not silent omission.
- **FAI / AS9102 form management + ballooned-drawing / CMM import** (Net-Inspect,
  InspectionXpert, High QA, 1factory) — expected in aero, but a large specialized module
  where dedicated tools dominate.
- **True PPM** and **fully automated earned/revocable skip-lot** — already deferred (§8/§10).

---

## 13. Sampling configuration model (first-principles)

Resolves the UX confusion of showing per-part streaming rules AND AQL on every step.
The flat `SamplingRuleType` enum conflates two orthogonal axes; the model below makes
**family** the discriminator and keeps the build minimal while reserving optionality.

### 13.1 Discriminator = `family` (one per ruleset)
- `STREAMING` — per-part selection ("inspect this part?"): every-Nth, percentage, random,
  first/last-N, exact-count, 100%. **Stacks** (a list of typed rules).
- `LOT_ACCEPTANCE` — accept/reject a whole lot from a sample: AQL single (Z1.4), C=0
  (Squeglia). **Terminal & singular** — a single `plan` object, no list.
- `VARIABLES` (Z1.9, measured mean/σ) — **BUILT (2026-07)**, not reserved. Its own
  family: measures one characteristic on n units → x̄/s vs `k`.
- *(reserved, not built)* `CONTINUOUS` (CSP) — an **in-process / production-flow**
  discipline (alternates 100% inspection with a sampling frequency over a continuous
  unit stream). It belongs to the `STREAMING` in-process domain, **not** receiving/SQM,
  which is inherently lot-based (there is no "lot" or supplier in a continuous stream).

Modeled as a discriminated union on `family`. A family selector at the top of the dialog
swaps the whole sub-form, so AQL never bleeds onto a streaming step and the two families
can't be mixed on one ruleset (forbidden structurally, not by validation).

### 13.2 Registry pattern (the optionality mechanism)
Each family — and each streaming rule type — is a **registry entry** declaring:
`{ id, label, cardinality: 'list'|'single', paramsSchema (zod), fields[] (declarative:
name/type/options/unit/showIf), defaults, evaluatorId }`. The dialog renders generically
from `fields`. **Adding a new kind (100% / Z1.9 / double) = one registry entry — no dialog
rewrite.** This replaces the scattered `rulesRequiringValue` / `unitFor` / coverage
switch-statements that today must be edited in three files per new type.

### 13.3 Params live with what they parameterize
- Streaming params stay on the `SamplingRule` row (one int is fine).
- **AQL params move OFF `SamplingRuleSet` (aql/inspection_level/severity/strategy) and onto
  a single `plan` object** owned by the lot-acceptance family. A streaming ruleset simply
  has no plan, so nothing AQL-shaped can render. The ruleset keeps only cross-family
  concerns: `family`, supplier scope, versioning, quality gate.
- *UI-first adapter:* the frontend serializes `{ family, rules[] | plan, gate }`; the
  current flat `aql/level/severity/strategy` map to `plan` on save until the columns move.

### 13.4 Lot-acceptance is SUBJECT-AGNOSTIC (OSP / shipment-back)
The acceptance **math is already decoupled** (stateless calculator: `lot_size → n/Ac/Re`).
The `plan` defines *how* to sample; the **subject** (what is being accepted) is a separate,
polymorphic binding:
- **Flow A — purchased `MaterialLot`** — the *only* subject wired up now.
- **Flow B — `OutsideProcessShipment` / part-batch** — our own parts grouped by the user,
  shipped to an external processor, received back, inspected on return. **Built
  end-to-end (2026-07-06)** — reuses the subject-agnostic calculator (§3 Flow B).

**Receiving states belong to the subject, not the engine.** Each subject owns its lifecycle
(`MaterialLot`: AWAITING_INSPECTION→ACCEPTED/REJECTED; an OSP shipment:
AT_OUTSIDE_PROCESS→RETURNED→AWAITING_INSPECTION→…) and fires the AQL evaluation when it
reaches "awaiting inspection." The engine is state-agnostic: handed a lot size + sample
results, it returns a verdict. So **do not bake `MaterialLot` into the sampling family** —
keep the plan pointing at a generic acceptance subject; Flow B plugs in later without
touching the sampling model (same way Z1.9 plugs in as a registry entry).

### 13.5 Scope now vs. reserved
- **Built:** `STREAMING` (existing rule types + explicit 100% optional),
  `LOT_ACCEPTANCE` (AQL single + C=0), `VARIABLES` (Z1.9), **Z1.4 three-way severity
  switching (2026-07-07)**, and the Flow B `OutsideProcessShipment` acceptance subject
  (2026-07-06) — on the `family` discriminator + registry.
- **Reserved (additive later, no refactor):** double/multiple sampling — lot
  acceptance, so it extends receiving/SQM (and OSP returns). `CONTINUOUS` (CSP) is
  also reserved but is an **in-process/`STREAMING`** discipline — a different domain
  from receiving/SQM, not a lot-acceptance plan.
- **Not doing:** free mode-string + if-blocks; schemaless JSON params; mixing families;
  keeping AQL as first-class ruleset columns long-term.

---

## 14. Deferred: purchased-vs-manufactured `PartTypes` classification (catalog)

**Observation.** `PartTypes` (the versioned part master: processes, `ID_prefix` autogen,
ITAR) is doing triple duty — it's also what `MaterialLot.material_type` FKs to for
**purchased** material, plus a `material_description` free-text fallback for raw stock.
There's no field distinguishing made / bought / raw. So a received supplier lot shows the
same part type that owns a manufacturing process, the Receive/RIP pickers can't filter to
purchasable types, and reporting can't slice purchased-vs-made.

**Decision: defer.** Fits the §11 small-shop guardrails (fields-over-tables, don't build
speculatively), and the fix is **cheaply reversible** — an additive, nullable/defaulted
field, not a fork. Make-or-buy is also genuinely *not binary* in reman (the same item is
both bought and remanufactured → "BOTH"), so forcing the split early would add friction
without signal.

**Safe to defer while:** the catalog stays small, raw materials use `material_description`,
and pickers show-all-with-search. **Trigger to stop deferring:** the first screen/report
that must *filter or slice* purchased-vs-made — Receive/RIP picker filtering, a purchased-
stock view, commodity/PPM reporting, or OSP send-out (which compounds the conflation:
"our parts sent out" vs "bought components" are both bare `PartTypes`).

**Scope when it lands (agent-scoped: Small).** Nothing breaks by adding the field — the
"PartType is manufactured" sites already degrade gracefully (`ID_prefix or 'P'` is null-safe;
a BUY-only type with no process → `resolve_receiving_step()` returns `None` → clean HTTP 400).
MVP slice:
- `PartTypes` enum `MakeOrBuy(MAKE/BUY/BOTH)` + `make_or_buy` CharField. **Name it
  `make_or_buy`, not `category`** (collides with `Processes.category` → enum-name clash).
  **Default `BOTH`** so no existing type drops out of any picker.
- migration (additive, no data migration) → add to `PartTypesSerializer` +
  `PartTypeSelectSerializer` fields → add to `PartTypeViewSet.filterset_fields` → regen
  `schema.yaml` + types.
- Frontend is nearly free: all pickers go through `useRetrievePartTypes` (query params typed
  from the spec), so they filter with `{ make_or_buy: 'BUY' }` and zero hook changes; the only
  hand edit is a dropdown on `EditPartTypeFormPage`. Filter the Receive grid + supplier-qual
  picker first; defer reman pickers, relational MaterialLot filter, reporting, and any
  order/WO guard rejecting BUY-only types from manufacturing flows.

---

## 15. Deferred (backend): disposition consolidation + lot wiring

> **FIXED (2026-07-02).** The auto-create signal (`signals.py:auto_create_disposition`) now
> **returns early for `material_lot` QRs** — receiving failures get their populated disposition
> from the reject flow, so the bare auto-create no longer duplicates it. In-process (part)
> auto-create is unchanged. Disposition + signals suites pass. The general "get-or-create +
> enrich per nonconformance" design below is still the right model if more creators ever appear;
> for receiving, "one creator (the reject flow), signal skips it" was the simpler correct fix.

**Confirmed defect (reproduced under the pre-DWI flow).** Rejecting a lot created **two**
`QuarantineDisposition` rows. Root cause = multiple independent creators for one
nonconformance — **corrected 2026-07 after re-reading the code:**
1. `signals.py:71` auto-creates a bare disposition on any failed `QualityReports`
   ("Auto-created for failed quality report"). ✔ real creator.
2. ~~`services/qms/receiving_inspection.py:reject` spawns one~~ — **NOT a creator.**
   The service `reject` only transitions the lot; it does not create a disposition.
   (Original doc claim was wrong.)
3. the receiving UI's reject dialog POSTs its own (populated) disposition. ✔ real creator.

So the duplicate is **#1 + #3 = two**, not three. ⚠ The reproduction predates the
DWI-based reject (`ReceivingAcceptanceStage.confirmReject`) — **re-verify the count/timing
under the current flow before fixing.**

**Fix = consolidate, not just prevent.** One **open** disposition **per nonconformance**
(key on the `QualityReports` row, which already carries `material_lot`); every entry point
**get-or-creates + enriches** the same record instead of minting its own. The receiving
reject accepts `{disposition_type, severity, description, quantity_affected}` and applies them
to that single record. Intentional MRB splits (e.g. 400 RTV + 100 scrap) stay possible as an
*explicit* action with distinct `quantity_affected` — consolidation only kills the accidental
duplicate.

**Bundle with §10.7:** add `QuarantineDisposition.material_lot` (+ `supplier`) FK so lot
dispositions (today `part=null`, QR-linked, invisible on the parts-centric Dispositions page)
can be listed/filtered directly and power a **lot-disposition surface** (Materials "Held" tab:
held lot → its disposition, View/Edit, RTV→supplier→scorecard loop).

**FE-only interim available now (no backend):** the reject dialog can **PATCH the auto-created
disposition** (find it by the lot's QR after reject) to enrich it, instead of POSTing a second
— kills the duplicate today and preserves captured intent; the backend consolidation later
makes it atomic/authoritative. Status: **deferred, UI-first** — logged, not yet built.

---

## 16. As-built additions (2026-07) — what we chose NOT to defer

Things built this session that go **beyond or against** the original design above. Listed
so the doc reflects reality, with honest built-vs-stub characterization.

**Receiving is DWI-based (supersedes the bespoke §6.2 inspection page).**
- The operator runs the receiving step's **substeps** in the DWI player (measurements /
  pass-fail authored on the RIP step), and the **acceptance decision + guided disposition
  happen in the runtime** (`ReceivingAcceptanceStage`), not on a separate page. Records to
  the lot's `QualityReports`. RIP authoring (standalone *and* in-process) now includes
  authoring the step's DWI substeps.
- **Completion-stage seam** (`pages/operator/completion-adapters.tsx`) — new architecture
  not in this doc: the DWI player's *ending* is a pluggable adapter resolved by subject
  (part-advancement = default; receiving-acceptance = footer). New endings (timed batch,
  OSP, FAI) drop in as adapters without touching the player.

**Z1.9 variables + unit-by-unit cadence (built).**
- The runtime walks **n sampled units**, stamping `sample_number` on each unit's promoted
  `MeasurementResult`; the verdict comes from the server-authoritative
  **`evaluate_receiving`** action (`MaterialLotViewSet`) via `evaluate_lot_acceptance`
  (attribute defective-unit count / Z1.9 x̄·s vs k). Backend `sample_number` threaded through
  `submit_substep → record_dwi_measurement → _promote_to_inspection_record`.

**Bulk (attribute) defects-by-characteristic (built).**
- The acceptance panel tallies defects **by RIP characteristic** (defect types = the plan's
  characteristics), summed vs Ac/Re; the breakdown flows into the disposition description.
  *(Structured per-characteristic persistence on accept-within-Ac is still description-only —
  a small follow-up.)*

**Reject → guided disposition (Tier-1 #2 / §10.7 UI) — built without waiting on the FK.**
- Wired via the existing `quality_reports` link, so it did **not** block on the
  `QuarantineDisposition.material_lot` FK (§10.7). `RejectDispositionDialog`: type / severity /
  quantity / RTV + open-SCAR.
- **Affected quantity is derived, not entered** — a sampling reject rejects the whole lot, so
  it's read from `lot.quantity` (we deliberately backed out a manual field *and* a model
  field; "we already know it").

**SCAR PDF (Tier-1 #5, partial).** Supplier-facing SCAR report adapter (Typst) renders a
CAPA(SUPPLIER) as an 8D request. The supplier *response* capture (Tier-3 portal) stays deferred.

**Supplier scorecard rating tier + badge (Tier-1 #1) — built** (A/B/C + `rating_reason`).

**OSP attaches to the receiving node (design decision, 2026-07) — BUILT end-to-end (2026-07-06).**
An OSP step is a node in the process; *send-out* and *receive-back* are states/actions on that
node; on receive-back the parts land pending inspection and run the **same DWI receiving-inspection
runtime** (measure → AQL verdict → accept/reject → guided disposition) as Flow A. The only
difference is the **subject** — an `OutsideProcessShipment` instead of a `MaterialLot` (lot size =
returned count) — dropping in via the subject-agnostic acceptance math (§13.4) + the
completion-stage adapter seam (`OSP_COMPLETION`). So OSP = "a receiving node with an outbound leg".

*As built:* send-out (quantity-first dialog, picks N of M ready) + receive-back live on the WO
**control page** (`OutsideProcessPanel` — send is a supervisor/lead batch action, mirroring the
per-step "advance ready"); the returned shipment surfaces in the unified **Incoming Inspection**
queue (§4) *and* on the control page with an `Inspect` action; the DWI runtime's `OSP_COMPLETION`
adapter runs accept (advance parts) / reject (quarantine) on finish; a detail-page badge links
back to `/control`. The one genuinely-new backend was the send-out / shipment / receive-back
modeling (§3); everything else reused the existing receiving pipeline.

*(Built vs. not-built vs. deferred is consolidated in §17's single backlog — not repeated here.)*

---

## 17. Backend seam audit (2026-07) — verified per file

Full read-through of the service layer to separate real code from stubs/gaps. Verdicts
are code-verified (grep/read), not inferred from the design intent above.

**Real & complete — no action:**
- `supplier_scorecard.py` — genuine aggregation → A/B/C rating. (PPM = deferred enhancement, now feasible with per-sample defect data.)
- `scar.py` — real `CAPA(SUPPLIER)` creation + QR link. (Supplier *response* capture = deferred portal.)
- `supplier_qualification.py` — scope resolution + full lifecycle (open/grant/submit-for-approval/suspend/disqualify/expire).
- `tasks.expire_supplier_qualifications` — cross-tenant expiry sweep, **now scheduled** (2026-07-02, daily in `CELERY_BEAT_SCHEDULE`). *(The "notify on expiry" side is still not wired.)*
- `events.py` `supplier.unqualified` + the receiving soft-hold gate (`_held_for_unqualified_supplier`) — built + emitted.
- `quality_gate.py` **engine** + all five actions — real (metric/threshold/idempotent `StepGateFiring`/dispatch).

**Real seam — intentional, correctly deferred:**
- `inventory.py` — status-flip seam (locks row, validates source state, `ValueError`). By design; append-only ledger is Phase 2, deferred per §11. Needs nothing now. *(Minor: locks via `.all_tenants.select_for_update()` by PK — confirm cross-tenant is intended.)*

**Real but needs a fix:**
- `quality_gate.py` — both §9.4 gaps **FIXED (2026-07-02):** the guard no longer requires `gate_actions` (routing-only gates now record a `StepGateFiring`), and `receiving_inspection.evaluate_lot_acceptance` now calls `evaluate_step_gate(material_lot=…)` so lot gates fire. *Remaining minor:* `DEFECTIVE_COUNT` for a lot reads `material_lot.defectives_found`, which the DWI unit-by-unit path doesn't set (uses per-unit `MeasurementResult`s) → under-reads — small follow-up.
- `inline_capture._promote_to_inspection_record` — **partly fixed (2026-07-02):** the unit-by-unit (`sample_number`) path is now idempotent (`update_or_create`); the part / single-pass path stays append-on-purpose (multiple/late readings are legitimate; the runtime's flush-once guard covers retries). **`osp_shipment` subject branch added (2026-07-05)** — a shipment-subject StepExecution's DWI captures now promote to the shipment's return-inspection QR, same as a lot's.
- `acceptance_sampling.py` — **table-verified (2026-07-06):** Z1.4 Table II-A transcribed from the
  MIL-STD-105E scan with arrows preserved + *followed* (the suspect M/N `21`s were the bug — up-arrows,
  not Ac=21); Z1.9 std-dev `k` verified B–J against MIL-STD-414, K–P **fail-closed** (raise, not guess);
  **three-way severity switching (Tables II-B/II-C) built 2026-07-07** (automatic from lot history).
  Tests lock arrow-following + fail-closed + tightened/reduced Ac + the switching transitions.
  *(Only residual: buy Z1.9-2003 for large-lot variables K–P if a customer needs it.)*

## 18. Backlog — single source of truth for remaining work

*(Supersedes the scattered "not built" lists; the top index and §16/§17 point here.)*

**In-scope — build these, in priority order:**
1. ~~**Cheap cluster**~~ — **DONE (2026-07-02):** lot gate trigger + fire-without-actions
   (§9.4) wired (`evaluate_lot_acceptance → _fire_lot_gate → evaluate_step_gate`; gate guard
   no longer requires actions); disposition consolidation (§15) fixed (auto-create signal now
   skips `material_lot` QRs — receiving's reject flow owns the populated disposition);
   measurement-flush idempotency (Tier-2 `update_or_create` for unit-by-unit readings);
   `expire_supplier_qualifications` scheduled (daily). *All covered by the existing suites.*
2. ~~**Sampling table QA sign-off**~~ — **DONE (2026-07-06):** Z1.4 Table II-A re-transcribed
   from the MIL-STD-105E scan with arrows preserved + followed (the M/N `21`s were the bug —
   they're up-arrows, not Ac=21; flattening arrows could accept lots the standard rejects);
   Z1.9 std-dev k **verified for B–J** against MIL-STD-414, **K–P fail-closed** (raise with an
   actionable message rather than ship unverified constants — pure Z1.9-2003, no standard mixing);
   `severity` was locked to NORMAL at sign-off; **three-way switching (Tables II-B/II-C)
   built 2026-07-07** — see §13.5 / the sampling row in the index. Tests lock
   arrow-following + the fail-closed path. *Remaining only if a customer needs large-lot variables:*
   buy ANSI/ASQ Z1.9-2003 and transcribe verified K–P (the free MIL-STD-414 values exist but use
   different high-letter sample sizes, so they'd mix standards — deliberately not used).
3. ~~**SQM depth**~~ — **DONE (2026-07-06):** backend was done 2026-07-04 (`evaluate_supplier_standing`
   recommend-only loop §10.3; `PartApproval` PPAP/FAI gate §2/§5a). FE now built, mirroring the ASL:
   **PartApproval CRUD/list/form** (`/production/part-approvals`, Supply nav) with grant/suspend/
   disqualify + PPAP/FAI package attach — *note: the PartApproval viewset existed but wasn't
   registered in `urls.py`, so it was never routed; fixed + regenerated the contract*; and a
   **standing-recommendation badge** on the Supplier Quality scorecard (the scorecard endpoint now
   returns `recommended_action`/`recommendation_reason` from `evaluate_supplier_standing`; the badge
   shows Review-suspend/conditional/restore only when a supplier is *approved* and the scorecard
   breaches, linking to the ASL to act).
4. ~~**OSP / Flow B**~~ — **DONE end-to-end (2026-07-06).** Backend (2026-07-05): `Steps` OSP
   fields + default vendor, `OutsideProcessShipment` aggregate (SENT/RETURNED/CLOSED; send/return
   timestamps + `quantity` = returned count = the AQL lot on return), `StepExecution.
   outside_process_shipment` membership, `PartsStatus.AT_OUTSIDE_PROCESS`, `QualityReports.
   osp_shipment` (subject constraint now "at most one of part / material_lot / osp_shipment"),
   `services/mes/outside_process.py` (`send_parts_out` / `receive_parts_back` / `accept_return` /
   `reject_return`, reusing `receiving_inspection.evaluate_lot_acceptance` for the subject-agnostic
   AQL verdict), `inline_capture` osp_shipment promote branch, `OutsideProcessShipmentViewSet` +
   endpoints, RLS/permission guards wired, `test_outside_process.py` (11 tests). FE (2026-07-06):
   send-out (quantity-first dialog) + receive-back on the WO control page (`OutsideProcessPanel`),
   `OSP_COMPLETION` runtime adapter (accept/reject on finish → advance / quarantine), detail-page
   "N at outside process" badge, and the unified **Incoming Inspection** queue (item 5). Return
   inspection runs the existing DWI runtime with the shipment as subject.
   **Also DONE (2026-07-06):** flow-editor OSP config — the step-editor panel exposes an
   "Outside process (subcontract)" toggle + default-vendor picker on a RECEIVING node
   (`is_outside_process`/`outside_supplier` persist through the graph-save); and a dedicated
   **shipper board** at `/production/outside-processing` (Supply nav): a *Ready to ship* lens
   (parts staged at OSP steps — `IN_PROGRESS` only — grouped by step/vendor across work orders,
   dispatch via the shared quantity-first dialog) + an *At vendor* lens. Send-out is a
   shipping/lead action (board + control panel), NOT the operator runtime — the operator's only
   OSP touchpoint is the return inspection. **Nothing left on OSP.**
5. ~~**Unified incoming-inspection queue**~~ — **DONE (2026-07-06):** `GET /api/IncomingInspection/`
   (`incoming_inspection.build_incoming_rows` merges lots + OSP shipments into `source`-keyed rows)
   → `/production/incoming` with Source/Status filters; supersedes §4's future-unification note and
   the earlier standalone OSP returns queue (removed). Separate from **Materials** (lot inventory).

**Missing / defect detail** (historical — feeds the above): `evaluate_supplier_standing` & `PartApproval` (missing models/services); disposition consolidation (defect — two creators, re-verify under DWI); `QuarantineDisposition.material_lot` FK (convenience, not a blocker); OSP; ASL expiry task unscheduled. *(All now built except the noted follow-ups.)*

**Genuinely deferred — enterprise-tier, needs a named customer/clause (§11):** inventory ledger, skip-lot / dock-to-stock earning, PPAP element mgmt, supplier portal (SCAR response).

**Reserved — additive when needed:** double/multiple sampling (lot acceptance — extends
receiving/SQM + OSP returns). *(Z1.4 tightened/reduced severity switching — **built 2026-07-07**,
no longer reserved.)* **CSP (continuous sampling)** is reserved but belongs to the
in-process/`STREAMING` domain, not receiving/SQM.
