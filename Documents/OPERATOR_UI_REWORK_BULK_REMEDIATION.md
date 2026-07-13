# Operator UI Audit & Remediation Plan — Rework and Bulk Axes

> **Status (2026-07-13): Complete — Phases 0–4 shipped** (see the ✅ markers per
> phase; migrations, services, and tests landed). Originally a read-only audit
> (2026-06-16); retained as the finished-work record and design rationale
> (esp. the disposition/NCR decisions and the per-load batch pivot).
> **Scope:** How operators experience (a) **bulk/batch steps** and (b) **rework steps**, traced
> across the two authoring surfaces (the process flow map and the DWI editor), the operator runtime,
> the supervisor control surface, and the backing services.
>
> **One-line conclusion:** The backend state machine for both axes is essentially complete. The
> **rework** axis is *authorable but not observable, and its routing is only half-wired*. The
> **bulk** axis is *backend-only* — it cannot be authored or captured anywhere in the UI.
>
> **⚠️ Correction (verified post-review) — NOW FIXED:** a quality disposition did **not** change part
> status — `QuarantineDisposition._update_part_status()` was dead code due to a case mismatch
> (`qms.py:805`, see §3.7a). This corrected an earlier ✅ in this audit. **The casing has since been fixed**
> and locked in by `Tracker/tests/test_disposition_cascade.py` (6 tests, passing). The deeper
> service-extraction (logic out of `save()`) remains as Phase 0a follow-up.
>
> **Domain note (per product owner):** a **failing `QualityReports` record *is* the NCR**; the
> **disposition is the decision recorded against that NCR**. Only failing quality reports are NCRs.
>
> **⚠️ Two corrections (verified) to earlier findings in this doc:**
> 1. **A disposition IS auto-created on QR fail.** The `auto_create_disposition` signal (`signals.py:21`,
>    wired via `apps.py:108`) creates a `QuarantineDisposition` assigned to a QA user on every `QualityReports`
>    save with `status='FAIL'`. Earlier text saying "no disposition is created" was wrong. **Caveats:** it's
>    created with **no `disposition_type`** (empty OPEN NCR awaiting QA's decision — the intended SoD behavior),
>    and it dedups **per-QR** — which is the *correct* granularity (one NCR = one failed report = one decision).
>    A part with two distinct defects legitimately carries two dispositions; the real concern is **conflict
>    precedence** across them, not deduplication (§3.7k).
> 2. **The sanctioned close service is dead** (new P0): `get_completion_blockers()`/`can_be_completed()`
>    (`qms.py:855,873`) carry the *same* lowercase bug the cascade had → `complete_disposition_resolution()`
>    raises every time (§3.7j). Today closing only works via a raw PATCH that bypasses the check.

---

## 1. How to read this document

Each finding is tagged with a confidence/state marker:

- ✅ wired & working
- ⚠️ wired but broken or fragile (e.g. mock data feeding a real endpoint)
- ✋ deliberate manual handoff (role boundary — *not* a bug)
- ❌ missing / not surfaced / unauthorable
- ··> automatic side-effect (fires asynchronously / as a downstream consequence)

File references use `path:line` against the repo root (`PartsTracker/` = Django backend,
`ambac-tracker-ui/` = React frontend).

---

## 2. System map (current state)

### 2.1 Rework axis — authorable, not observable, routing half-wired

```
            AUTHORING (flow map)                 RUNTIME (operator / supervisor)
 ┌─────────────────────────────────────┐   ┌──────────────────────────────────────┐
 │ step_type=REWORK (auto max_visits=3) │   │ operator: NO live process map view ❌ │
 │ max_visits  (redo cap)            ✅ │   │   inspection-point capture → QR ✅     │
 │ is_decision_point + decision_type ✅ │   │   QR FAIL → auto-quarantine ··> ✅     │
 │ is_terminal + terminal_status     ✅ │   │   → auto-disposition (typeless) ⚠️    │
 │ rework loop edge (draw back)      ✅ │   │                                        │
 │ edge_type ALTERNATE/ESCALATION    ⚠️ │   │ quality/MRB: QaQuarantinePage +        │
 │   (inferred from id suffix/handle)   │   │   EditDispositionFormPage  ✅          │
 │ measurement edge conditions       ❌ │   │   choose REWORK/REPAIR/SCRAP/... ✅    │
 │                                      │   │   → status cascade FIXED (Phase 0)  ✅ │
 │                                      │   │   → but still no routing            ❌ │
 │                                      │   │                                        │
 │                                      │   │ supervisor: WorkOrderControlPage       │
 │                                      │   │   in-process split (no target step) ❌ │
 │                                      │   │   child-WO split (MOCK process list)⚠️ │
 │                                      │   │   redo cap / escalation shown       ❌ │
 └─────────────────────────────────────┘   └──────────────────────────────────────┘
```

### 2.2 Bulk axis — backend-only, no door in or out

```
            AUTHORING                            RUNTIME
 ┌─────────────────────────────────────┐   ┌──────────────────────────────────────┐
 │ flow map: requires_batch_completion  │   │ batch advancement (try_advance_lot) ✅ │
 │   / pass_threshold      (no editor)❌│   │   but invisible to operator;          │
 │ DWI: Substep.scope=BATCH (no editor)❌│  │   only learns via "blocked" toast ❌  │
 │ DWI: per-substep sampling_rule     ❌│   │ BatchPanel: Start ✅ / Seal ✅         │
 │                                      │   │   batch-substep CAPTURE  ❌ ("future") │
 └─────────────────────────────────────┘   └──────────────────────────────────────┘
```

---

## 3. Detailed findings

### 3.1 Backend (both axes) — essentially complete

**Rework**
- Step identity & routing: `Steps.step_type='REWORK'`, `max_visits`, `StepEdge.edge_type` ∈
  {`DEFAULT`,`ALTERNATE`,`ESCALATION`} — `PartsTracker/Tracker/models/mes_lite.py` (Steps ~427+, StepEdge ~1210+).
- Entry path A (QMS): failed check → `QuarantineDisposition(disposition_type='REWORK')` sets
  `part_status=REWORK_NEEDED` + `total_rework_count++` in `_update_part_status()` — `models/qms.py:797-827`.
  **This path was DEAD pre-fix** (case-mismatch bug, see §3.7a) and is **now fixed** (Phase 0a). Parts also
  reach `REWORK_NEEDED` via the supervisor's `bulk_set_status` button.
- Entry path B (MES): `split_part_from_lot(reason='rework', rework_target_step=<step>)` closes the
  current `StepExecution` as `ROLLED_BACK` and creates a fresh execution at the rework step with
  `visit_number+1` — `services/mes/splits.py:41-147`.
- Redo limits: `_check_cycle_limit()` routes to the `ESCALATION` edge when `max_visits` exceeded —
  `models/mes_lite.py:2657-2685`; per-step `QuarantineDisposition.check_rework_limit_exceeded(max_attempts=2)` —
  `models/qms.py:881-905`.
- Break out: success → `advance_part_step()` → `get_next_step()`; escalation/terminal → `SCRAPPED`.
- Endpoints (all real):
  - `POST /api/Parts/{id}/split_from_lot/` — accepts `{reason, rework_target_step_id?, notes?}`
    (`viewsets/mes_lite.py:530-574`).
  - `POST /api/WorkOrders/{id}/split/` — REWORK reason **requires & validates** `target_process_id`
    (`services/mes/work_order.py:373-406`).
  - `GET /api/Processes/?is_remanufactured=true` — real filter on `ProcessViewSet`
    (`viewsets/mes_lite.py:2264`). **This is the replacement for the mock rework-process list.**
  - `POST /api/QuarantineDispositions/` (+ `PATCH`) — CRUD (`viewsets/qms.py:82-108`).
  - `POST /api/SamplingDecisions/reconcile/` — sampling reconciliation only (NOT QA pass/fail).

**Bulk**
- `Steps.requires_batch_completion` + `pass_threshold` gate the lot; `try_advance_lot()` advances the
  cohort together — `services/mes/advancement.py`.
- `Substep.scope=BATCH` routes captures to `BatchExecution` instead of per-part `StepExecution` —
  `models/dwi.py`.

### 3.2 Process flow map (`ProcessFlowPage` + `components/flow/`)

- Authorable today (✅): `step_type` incl. REWORK/DECISION/TERMINAL (`step-editor-panel.tsx`), `max_visits`
  (`:269`), `is_decision_point`+`decision_type`, `is_terminal`+`terminal_status`, `requires_qa_signoff`,
  `sampling_required`, `min_sampling_rate`. Rework loops can be drawn freely.
- ⚠️ `edge_type` is **inferred**, not chosen: reverse-engineered at save from the source handle (`fail`)
  and an id suffix (`-alt`/`-esc`) — `ProcessFlowPage.tsx:408-413`.
- ❌ `StepEdge.condition_measurement/value/operator` are read from API but **never written back**
  (save payload omits them, `:410`). So `decision_type=MEASUREMENT` branches aren't configurable.
- ❌ `requires_batch_completion` / `pass_threshold` — **no authoring control** and omitted from the save
  payload. (They appear read-side only, in the flow adapter `useProcessTemplateFlow.ts:205` / `types.ts`;
  there is no editor field and no write-back.)
  - ⚠️ Note on `pass_threshold`: despite the name/docstring ("Threshold for pass/fail determination",
    `mes_lite.py:459`), it is a **cohort-readiness gate** (fraction of the lot that must be READY before the
    batch advances), not an inspection acceptance/AQL threshold. It is consumed **only** by the legacy
    `can_advance_step` (`:734`); the modern `try_advance_lot`/`can_advance_from_step` engine ignores it.
    Lot-acceptance (accept/reject on sample results) is **not modeled** — `SamplingRuleSet`/`SamplingRule`
    carry sample selection + CSP fallback only, no acceptance number. See task 1a for the resolution
    (rename + redocument, keep readiness semantics, no acceptance modeling now).
- Runtime read-back: `WorkOrderControlPage` renders `FlowCanvas` **read-only with no live overlays**;
  the part-position/status overlays exist only in **demo mode** (`process-flow-demo.ts`), and the
  metrics overlay is explicitly mock (`useProcessMetricsFlow.ts:222`).

### 3.3 DWI editor (`SubstepEditorPage`)

- Strong authoring (✅): 23 TipTap node types (`lib/dwi/node-catalog.tsx`), inspection-point coupling
  (inserting `partAnnotation` forces `is_inspection_point=true` and bundles the QA capture set —
  `SubstepEditorPage.tsx:82-135`), and `is_critical/is_optional/allow_not_applicable/requires_signature`
  toggles. No authoring stubs.
- ❌ `scope` (SAMPLED vs BATCH) is **not exposed** anywhere in authoring; `sampling_rule` per-substep is
  not exposed; no hint that BATCH captures go to `BatchExecution`.
- Persistence: substeps are direct `POST/PATCH /api/Substeps/` (not independently versioned), gated by
  the parent Step/Process being in DRAFT (`useSubsteps.ts`).

### 3.4 Operator runtime (`OperatorSubstepRuntimePage`)

- ✅ Serial per-part flow: `StartWorkDialog` queues parts; one substep at a time; `complete_step` fires
  `try_advance_lot` to move the cohort.
- ✅ Inspection points pre-bind a `QualityReports` row (`POST /api/Substeps/{id}/ensure_inspection_qr/`);
  QR status auto-derives PASS/FAIL from findings.
- ··> On FAIL the part is auto-quarantined and `ncr.opened` is emitted (`services/qms/quality_report.py`),
  **and** a `QuarantineDisposition` is auto-created and QA-assigned via the `auto_create_disposition` signal
  (`signals.py:21`) — but with **no `disposition_type`** (empty OPEN NCR) and **per-QR dedup** (a part failing
  two inspection points gets two dispositions; see §3.7k).
- ❌ No batch-substep capture UI (`BatchPanel.tsx:10-13` — "future iteration"); batch-gating is invisible
  until a `complete_step` returns `status:"blocked"`.
- ❌ No decision-point resolver (QA_RESULT/MANUAL pass-vs-fail branch picker). `PendingDecisionsPanel`
  is sampling reconciliation only.

### 3.5 Supervisor control (`WorkOrderControlPage`)

- ⚠️ Child-WO rework split (`useSplitWorkOrder` → `/WorkOrders/{id}/split/`) is real, but the process
  dropdown is hardcoded `MOCK_REWORK_PROCESSES` (`:76-79`) with fabricated IDs — the backend **rejects**
  them (`target_process_id not found`), so the path is wired-but-broken.
- ❌ In-process rework: the per-row "Rework" button calls `split_from_lot` but **never sends
  `rework_target_step_id`** (`:1807`), so the part stays put; the bulk "Rework" button only sets status
  `REWORK_NEEDED` (`:1893`). The cleaner in-process rework path is unreachable.
- ❌ No surfacing of `total_rework_count` vs `max_visits`, attempt limits, or escalation.

### 3.6 Deliberate boundaries (NOT defects)

- ✋ **Operator → quality disposition handoff is intentional** (segregation of duties / AS9100): the
  person who surfaces the quality report should not be the person who dispositions it. **This handoff is
  already automated** — `auto_create_disposition` (`signals.py:21`) opens a QA-assigned, typeless
  disposition on QR fail, so quality doesn't have to hunt for the part. The remaining work is hardening
  (per-part dedup, `ncr.opened` reconcile), not building it (see task 2a).

### 3.7 Dispositions & rework — deeper situation (verified)

This section goes beyond the original runtime/authoring audit into the QMS disposition data model itself,
because the rework lifecycle hinges on it. Several findings are more serious than the surface audit implied.

**a) ✅ FIXED — the disposition → part-status cascade was dead code.**
`QuarantineDisposition._update_part_status()` (`models/qms.py:797-827`) never mutated the part under real
data, for two compounding reasons:
- The state guard `if self.current_state not in ['in_progress', 'closed']: return` (`:805`) compares
  against **lowercase** strings, but `current_state` values are **uppercase** (`'OPEN'/'IN_PROGRESS'/'CLOSED'`,
  `:639`). The guard is always true → always early-returns.
- Even past the guard, `status_mapping` keys are lowercase (`'rework'`, `:810-816`) while `disposition_type`
  values are uppercase (`'REWORK'`, `:641`), so `.get()` returns `None`; and `total_rework_count++` is gated
  on `disposition_type in ['rework','repair']` (`:824`) which never matches.

Consequence (pre-fix): choosing REWORK/REPAIR/SCRAP/USE_AS_IS/RETURN_TO_SUPPLIER had **no effect on the
part**; parts reached `REWORK_NEEDED`/`SCRAPPED` only via the supervisor's direct `bulk_set_status` buttons.
**Fixed:** the lowercase guard/keys were corrected to uppercase (`qms.py:805,810-816,824`), and
`Tracker/tests/test_disposition_cascade.py` locks in the behavior for all five disposition types plus the
OPEN-without-type no-op. The cascade now mutates the part as intended. (Remaining debt: the logic still lives
in `save()` — see (b) and Phase 0a — but it is now correct.)

**b) ⚠️ Disposition state machine lives in `save()`** (`models/qms.py:744-772`): OPEN→IN_PROGRESS auto-fires
in `save()`; `requires_customer_approval` is auto-set in `save()`; the close-guard and `_update_part_status`
call are in `save()`. This violates the `CLAUDE.md` "no business logic in `save()`" rule. The correct fix for
(a) is to **extract this into a `services/qms/` function** (alongside the existing
`complete_disposition_resolution`, `services/qms/disposition.py:16`), not to patch the casing in place.

**c) The NCR is a failing `QualityReports` record; the disposition is the decision recorded against it.**
(Per product owner.) There is no separate `NCR`/`NonConformance` model — and there shouldn't be: a
`QualityReports` row with `status='FAIL'` *is* the nonconformance report, and a `QuarantineDisposition` is
the disposition decision made on that NCR. `ncr.opened` is the event marking a QR going to FAIL
(`services/qms/events.py:51`, fired from `services/qms/quality_report.py:136`, keyed by the QualityReports
id). The "NCR" PDF renders the report together with its disposition (`reports/adapters/ncr.py`); CAPA and RCA
records M2M-link to dispositions. **Implication:** don't propose an NCR model (per `CLAUDE.md` "prefer fields
over tables") — extend `QualityReports` / `QuarantineDisposition` instead.

**d) No MRB (Material Review Board) model or multi-signer flow.** Only a code comment references "MRB"
(`reports/adapters/deviation_request.py:60`). There is no board, quorum, or approval aggregate.

**e) ❌ Disposition approval authority is declared but UNENFORCED.** Permissions `approve_disposition` and
`close_disposition` exist (`models/qms.py:716`) but `QuarantineDispositionViewSet` (`viewsets/qms.py:82`) is a
plain `ModelViewSet` with **no `action_permissions`** — so creating a disposition is gated only by
`add_quarantinedisposition` and closing it by generic `change_` (PATCH). There is **no approval gate**, and no
severity/type-conditional authority: scrapping a part requires no more authority than a cosmetic disposition.
`severity` (CRITICAL/MAJOR/MINOR, `:649`), `requires_customer_approval`, `customer_approval_received`, and
`scrap_verified*` are all tracked as **flags but never enforced as gates** (`:684` comment is explicit).

**f) REPAIR vs REWORK is barely differentiated.** Both map to `REWORK_NEEDED` + the rework counter
(`:810-825`). REPAIR differs only in: `requires_customer_approval` auto-set (`:752`), and eligibility for the
**Deviation Request** PDF (`reports/adapters/deviation_request.py` — accepts only USE_AS_IS/REPAIR, rejects
REWORK). There is **no concession/deviation/waiver model** — only the PDF adapter and a
`RollbackReason.PROCESS_DEVIATION` enum value.

**g) ❌ Re-inspection after rework is not enforced.** `split_part_from_lot(reason=rework, rework_target_step)`
(`services/mes/splits.py:41`) closes the old execution `ROLLED_BACK`, moves the part, bumps `visit_number`,
and calls `evaluate_substep_sampling()` on the new execution (`:112`) — so a reworked part *is* re-flagged
for sampling **only if the chosen target step happens to contain inspection substeps**. Nothing forces rework
to route back through the original inspection. A hard `require_re_inspection` flag exists — but on the
separate `StepRollback` aggregate (`qms.py:2929`), **not** on `QuarantineDisposition`.

**h) No rework-specific work instructions.** A rework target is an ordinary `Steps` row; the part re-runs that
step's existing substeps. There is no rework-only DWI and no "rework step type" beyond the `step_type='REWORK'`
visual marker. Rework reason is captured only as free text (`description`/`resolution_notes`) + counters
(`rework_attempt_at_step`, `total_rework_count`) + a `StepTransitionLog` line.

**i) Dispositions are per-PART only.** `QuarantineDisposition.part` is a single FK (`:703`); it M2M-links many
QualityReports but covers one part. There is no batch/MRB disposition across many parts (batch exists only for
rollback: `BatchRollback`, `qms.py:3014`). For a lot-wide nonconformance, an operator/quality user must create
N dispositions.

**j) ❌ NEW P0 — the disposition close service is dead (same case-bug class as the cascade).**
`can_be_completed()` (`qms.py:855`) and `get_completion_blockers()` (`qms.py:873`) compare `current_state`
against **lowercase** `['open','in_progress']`, but stored values are uppercase. So `can_be_completed()`
always returns False and `get_completion_blockers()` always appends "Disposition is … not active". The
sanctioned close path `complete_disposition_resolution()` (`disposition.py:40`) raises `ValueError` on that
blocker **every time** for real data. Closing currently works only via a raw PATCH of `current_state='CLOSED'`
that bypasses the blocker check (the annotation-pending guard in `save()` still applies). This is the same
bug fixed in 0a; **it must be fixed for 2b's hook site to function.** Fix belongs in the service extraction.

**k) ⚠️ Multiple open dispositions per part have no conflict precedence.** `auto_create_disposition`
(`signals.py:21`, wired `apps.py:108`) dedups **per-QR**, which is the correct granularity — a failing QR is
one NCR, and a part with two distinct defects *should* carry two dispositions (each may get a different
decision, e.g. one USE_AS_IS, one SCRAP). The gap is **not** deduplication; it's that the part-status cascade
(`_update_part_status`) is **last-writer-wins** with no severity/terminal precedence: if a part has a SCRAP
disposition and a REWORK disposition is later saved, the REWORK save flips a SCRAPPED part back to
REWORK_NEEDED. Terminal/most-severe should dominate, and there is no part-level view aggregating a part's open
dispositions. (The `quality_reports` M2M does allow an MRB to *group* related QRs under one disposition by
choice — but that's an option, not something to force.)

**l) ❌ Terminal states (especially SCRAP) can be casually reversed.** `bulk_set_status`
(`services/mes/parts.py:524`) sets `part.part_status = new_status` with **no check on the current status**
(`:545`); `TERMINAL_PART_STATUSES` (`:449`) is used only to trigger the WO-completion cascade (`:547`), never
to block *leaving* a terminal state. So a SCRAPPED part can be set straight back to IN_PROGRESS from the
control page's "Set status"/rollback actions — one click, no elevated permission, no mandatory reason. Scrap
shouldn't be reversible as a casual status change; reversal (where allowed — e.g. for admins, QA managers,
production managers) should go through a deliberate, permission-gated, audited path. The exact reversal
policy is out of scope for this doc.
See task 0d.

**Net:** the disposition subsystem records decisions but (a) didn't act on them (cascade — now fixed),
(j) can't be closed via the sanctioned service, (e) doesn't enforce who may make them, (g) doesn't guarantee
the reworked part is re-verified, and never auto-closes after rework succeeds (G3 / task 2e). These are the
foundations the Phase 2 "connect disposition → routing" work would otherwise be built on, so they move earlier.

### 3.8 First Piece Inspection (FPI) — a real gate with no head

Surfaced while resolving the FPI × batch question. FPI is a load-bearing advancement gate that is almost
entirely invisible and unoperable in the DWI surface.

- ✅ **The gate is real:** `can_advance_from_step` blocker #3 (`mes_lite.py:903-907`) blocks every part at a
  `(work_order, step)` until `get_fpi_status()` returns PASSED/WAIVED, keyed on `FPIRecord`.
- ❌ **Not authorable in the DWI/flow surfaces:** only a legacy checkbox in `EditStepFormPage.tsx:323` sets
  `requires_first_piece_inspection`; `fpi_scope` (PER_WORKORDER/SHIFT/EQUIPMENT/OPERATOR) is authorable
  **nowhere** and silently defaults to PER_WORKORDER.
- ❌ **No operator UI:** `components/fpi-status-banner.tsx` (Start/Pass/Fail/Waive, wired to `useFpiRecords`)
  is fully built but **imported nowhere** — orphaned. An operator at an FPI-pending step gets only a generic
  "lot waiting on cohort" toast (`OperatorSubstepRuntimePage:1046`) with no way to perform or pass the FPI.
- ❌ **No first-piece designation:** `StepExecution.is_fpi` / `fpi_status` are dead (assigned by no code);
  `FPIRecord.designated_part` is set only by seed scripts. FPI is a WO+step PENDING/PASSED toggle, not a
  tracked physical part.
- ⚠️ **`fpi_scope` is ignored at gate-time:** `get_fpi_status` filters only `work_order`+`step`, so a pass
  unblocks the whole WO regardless of the authored shift/equipment/operator scope.
- **FPI × batch — uncoordinated:** FPI (blocker #3, blind to `Substep.scope`) and batch (blocker #8 via
  `advancement_gate.py`, blind to FPI) stack independently; there is **no "first piece of a batch" concept**
  (incoherent — a batch runs all parts at once). The combination is neither blocked nor reconciled.
  **Recommendation: make FPI and batch-scope mutually exclusive** (Decision #12), not invent batch-FPI.

### 3.9 Batch measurements & SPC — capture has nowhere to land, SPC is unwired

Traced backwards from the `measureInput` node.
- ✅ **Per-part measurement → record works:** a `measureInput` capture is written as a `StepExecutionMeasurement`
  keyed on `step_execution` (`services/qms/inline_capture.py:91`), promoted to a part-bound `MeasurementResult`
  only when the substep `is_inspection_point` (`:117,146`).
- ❌ **SPC is essentially unwired.** SPC = a freeze-baseline model (`SPCBaseline`) + read-side charting
  endpoints (`viewsets/spc.py`). Nothing evaluates a measurement against control limits on write, there is no
  violation model, and **`Steps.block_on_spc_violation` is dead config** (declared `mes_lite.py:545`; read by
  no service/gate — only seed data sets it). So `can_advance_from_step` can never block on an SPC violation.
- ❌ **Batch measurement → record → SPC: no path.** `StepExecutionMeasurement` has no `batch_execution` FK and
  `record_dwi_measurement` is keyed on `step_execution` (one part). A `measureInput` dropped in a BATCH-scope
  substep today would be mis-attributed to one part's execution or not persist as a measurement at all (only
  the `SubstepCompletion` lands via seal). SPC read endpoints pull part-bound `MeasurementResult`, so a per-lot
  reading could never appear on a chart even if stored.
- **Implication for 3a:** if batch substeps capture measurements (furnace temp, bath concentration), the batch
  write-path needs a per-lot measurement store (nullable `batch_execution` FK on `StepExecutionMeasurement`,
  or a batch-measurement model). Whether SPC must consume per-batch readings is Decision #13. Wiring SPC at all
  (evaluation + violation + `block_on_spc_violation`) is a **separate effort** beyond this plan.

### 3.10 Lot/batch advancement at scale — the cliffs are in the existing engine

For a 500-part cohort, the dominant costs are pre-existing, not introduced by the batch feature:
- ❌ **Per-part gate N+1 (worst offender):** `try_advance_lot` loops the cohort and calls
  `can_advance_from_step` per part (`advancement.py:155-162`); each call + `substep_completion_blockers`
  (`advancement_gate.py`) re-queries identical *step-level* data (substeps, required measurements, QA, FPI,
  sealed-batch index) with no cohort-level caching — ~8–12 queries/part → **~4–6k queries to gate 500 parts.**
- ❌ **Per-row advance:** the advance loop calls `advance_part_step` per part with per-row `.save()`/`create`
  and re-runs the gate a second time (`parts.py:142`); no `bulk_update`/`bulk_create`. Cascade recursion
  multiplies this up to ×10.
- ⚠️ **Bulk ops** (`bulk_increment`/`rollback`/`set_status`) add a SAVEPOINT/RELEASE per id on top of per-row work.
- ⚠️ **Seal amplifies it:** `seal_batch` calls `try_advance_lot` **synchronously in-request**
  (`batch_lifecycle.py:98`) — sealing a large batch pays the full gate+advance cost in one request. This is
  where the batch feature (3a) inherits the engine's N+1.
- ❌ **`limit: 500` silent truncation (correctness, not perf):** cohort/WO part loads hardcode `limit: 500`
  with no count reconciliation at `OperatorSubstepRuntimePage:214`, `WorkOrderControlPage:816`,
  `StartWorkDialog:52` — a >500-part cohort is silently truncated and a batch starts on the first 500 only.

---

## 4. Sequenced remediation plan

Phases are ordered by dependency and risk: make features authorable and unbreak wired paths first
(low risk), then close the rework routing handoffs, then build the bulk runtime capture (largest), then
add observability and guardrails. Each task lists the touch points and an acceptance check.

> **Cross-cutting reminders (from `CLAUDE.md`):** business logic lives in `services/{mes,qms}/`, not in
> `save()`; versioned models mutate via `create_new_version()`; after touching `serializers/` or
> `viewsets/`, regenerate `schema.yaml` **and** the frontend types (`bun run generate-api`) in the same PR.
>
> **Two cross-cutting requirements added after review (apply to every task):**
> - **Tests are part of "done."** Each backend change needs service/unit tests
>   (`cd PartsTracker && python manage.py test`). Call out idempotency tests explicitly where a task claims
>   it (e.g. "no duplicate dispositions"). Each FE wiring change needs at least a typecheck pass
>   (`bun run typecheck`).
> - **DRAFT-gating for new authoring fields.** Steps/Substeps are versioned through the parent Process and
>   edits are DRAFT-gated. New authoring controls (`scope`, `requires_batch_completion`,
>   `batch_ready_threshold` — renamed from `pass_threshold`, see 1a) change runtime routing, so they must
>   respect the same gate — *not editable on a Process version already
>   pinned to a running WorkOrder*. Make this an acceptance criterion on 1a/1b.
>
> **Permissions/tenant scoping (per `CLAUDE.md` 3 paradigms):** new authorized actions (auto-disposition
> assignment, in-process rework routing, decision resolver) need a deliberate gate — `action_permissions`
> and/or a real `approve_*`/`close_*` enforcement, not the generic `add_`/`change_` fallthrough they get
> today. FE process pickers (e.g. `useReworkProcesses`) must be tenant-scoped.

### Phase 0 — Correctness & safety fixes (do FIRST; Phase 2 depends on these) — ✅ COMPLETE

These are bugs/holes in the disposition subsystem (see §3.7). Building disposition-driven routing on top of
them would inherit silent failures.

> **Status: DONE.** All four tasks implemented and tested (14 tests across
> `test_disposition_cascade.py`, `test_disposition_permissions.py`, `test_terminal_reversal_guard.py`).
> No migrations. `schema.yaml` regenerated for the new `/QuarantineDispositions/{id}/close/` endpoint.
> `close_disposition` distributed generously in `presets.py` (QA Inspector / Production Manager / Shift Lead,
> plus QA Manager + Tenant Admin via SoD; line Operator excluded by design).

- **0a. [REWORK] Fix the dead disposition → part-status cascade. — ✅ DONE**
  - Casing fixed AND the logic extracted to `apply_disposition_to_part()` in `services/qms/disposition.py`;
    `_update_part_status` removed; `save()` delegates and fires **only on a `disposition_type` change**
    (Decision #5 — act on type-set), never on close. Idempotent (part-status equality guard), so a later
    close can't re-apply or re-increment. `save()` now does auto-fill only.
  - Tests (`test_disposition_cascade.py`, 9): all five types, OPEN-without-type no-op, close-after-rework
    doesn't re-increment/regress, type-correction re-applies, and the close service completes (0c).

- **0b. [REWORK] Enforce disposition approval/close authority. — ✅ DONE**
  - Added a `close` action to `QuarantineDispositionViewSet` (delegates to `complete_disposition_resolution`),
    gated by `action_permissions = {'close': ['close_disposition']}` and `crud_exempt_actions = {'close'}`
    (so close needs `close_disposition`, not also `add_quarantinedisposition`).
  - **Decision #6 — DEFERRED:** per-type elevated authority (SCRAP vs. USE_AS_IS vs. REWORK) stays for later;
    `severity` remains the future basis. `approve_disposition` stays declared-but-unwired (no approval flow yet).
  - Tests (`test_disposition_permissions.py`, 2): without `close_disposition` → 403; with it → 200 + CLOSED.

- **0c. [REWORK] Fix the dead disposition-close service (§3.7j). — ✅ DONE**
  - Fixed the lowercase state literals in `can_be_completed()` / `get_completion_blockers()`
    (`qms.py:855,873`) → `complete_disposition_resolution()` now closes a valid disposition instead of raising.
    (Also corrects the serializer's `can_be_completed`/`completion_blockers` output the FE reads.)
  - Tested via `test_close_service_completes_in_progress_disposition` + the 0b API test.

- **0d. [REWORK / SAFETY] Don't let terminal states be casually reversed — especially SCRAP (§3.7l). — ✅ DONE**
  - Added `_blocks_terminal_exit()` guard in `bulk_set_status`, `bulk_rollback`, and `rollback_part_step`:
    leaving a `TERMINAL_PART_STATUSES` status is blocked unless the caller passes `allow_terminal_exit=True`.
    The viewsets set that flag only for elevated users.
  - **Placeholder elevated check:** the viewset gate is currently `is_superuser or is_staff` (clearly
    commented). The precise elevated-role policy (admins, QA/production managers) and `scrap_verified`
    handling remain **out of scope** as agreed — the casual one-click un-scrap is now blocked, which was the goal.
  - Tests (`test_terminal_reversal_guard.py`, 3): can't un-scrap without elevation; elevated can; normal
    (non-terminal) transitions unaffected.

### Phase 1 — Make existing backend features authorable; unbreak wired paths (low risk)

Nothing downstream matters if a behavior can't be authored or its one wired control is broken.

- **1a. [BULK] Surface `requires_batch_completion` + readiness fraction (+ folded-in FPI authoring) in the flow step editor. — ✅ DONE**
  - **Rename decision: SKIPPED the DB rename** (cosmetic, ~12-file churn). Kept the column `pass_threshold`;
    fixed the misleading model docstring (`mes_lite.py:459` → "cohort-readiness fraction … NOT pass/fail") and
    use a clear UI label instead. Minimum-viable per the call.
  - **1a-ii (wiring): already enforced, not theater.** `advance_part_step`'s `requires_batch_completion`
    branch (`parts.py:207-271`) marks parts READY and calls `can_advance_step` (`mes_lite.py:737`:
    `ready_for_next/total < pass_threshold → block`) before bulk-advancing. The authored value now feeds that
    real gate. (The `try_advance_lot` all-or-none pre-gate still masks threshold<1.0 at the cohort level — a
    known nuance left as a follow-up; default 1.0 behaves correctly.)
  - **Backend:** `requires_batch_completion`, `requires_first_piece_inspection`, `fpi_scope` added to the
    node read serializer (`serializers/mes_lite.py`) for round-trip. The write path already accepted them
    (`create/update_process_with_steps` splats node dicts into `Steps`). schema + FE types regenerated.
  - **Frontend:** step editor (`step-editor-panel.tsx`) gains **Batch Completion** (toggle + "Batch ready
    threshold %" input, stored as a 0–1 fraction) and **First Piece Inspection** (toggle + FPI-scope select)
    sections; `StepData`, the node-data mapping, the read mapping, and the save payload all carry the four
    fields. This also delivers the FPI authoring exposure folded in from 1e.
  - `bun run typecheck` clean. Versioning + change-control regression suites green (74 tests, OK).
  - **Deferred:** retiring the legacy `EditStepFormPage` FPI checkbox (FPI is now authorable in the flow
    editor too; removing the legacy form is optional cleanup). A dedicated `can_advance_step` threshold test.

- **1b. [BULK] Surface `Substep.scope` (SAMPLED/BATCH) in the DWI editor. — ✅ DONE**
  - Added `scope` to `SubstepSerializer.Meta.fields` (it wasn't exposed) + regenerated `schema.yaml` and FE
    types. In `SubstepEditorPage`, added `scope` to `PendingEdits`/`PendingCreate` + the create payload, and a
    "Batch (once per lot)" toggle in `SubstepExpandedBody` with a tooltip explaining captures bind to a
    `BatchExecution`, not per part.
  - **Side-effect fix:** because the serializer didn't return `scope`, the operator runtime's
    `s.scope === "batch"` check (which decides whether `BatchPanel` shows) was always false — so `BatchPanel`
    never appeared. Exposing `scope` makes that path actually work end-to-end.
  - `bun run typecheck` clean; 84 DWI tests pass (no regression). DRAFT-gating: inherited via the editor's
    existing `is_editable` gate.

- **1c. [REWORK] Replace `MOCK_REWORK_PROCESSES` with a real query. — ✅ DONE**
  - Removed `MOCK_REWORK_PROCESSES`; `WorkOrderControlPage` now uses the existing `useRetrieveProcesses({
    is_remanufactured: true })` hook (tenant-scoped server-side) to populate the rework-process picker, with
    an empty-state hint when no remanufacturing processes exist. The split already sends the selected id as
    `target_process_id`, so the child-WO REWORK split is now wired to real, backend-validated processes.
  - `bun run typecheck` clean. No schema/type regen needed — `is_remanufactured` was already a query param on
    `api_Processes_list`.
  - Note: the `./mockData` import stays — other parts of the page still use those Mock* types (only the
    rework-process list was mock). Query is currently ungated (fetches on page load); could add
    `enabled: splitMode === "REWORK"` later if desired.

- **1d. [REWORK] Make `edge_type` an explicit authoring choice (de-fragilize escalation/alternate). — ✅ DONE**
  - Edges now carry an explicit `edge_type` in `edge.data` (`use-steps-to-flow.ts` seeds it on every built
    edge; `onConnect` defaults it from the source handle). Added an **edge inspector** in `FlowCanvas`: click an
    edge → pick DEFAULT / ALTERNATE / ESCALATION (updates `data.edge_type` + recolors the edge). The save
    mapping (`ProcessFlowPage.tsx`) now reads `edge.data.edge_type`, falling back to the legacy id-suffix/handle
    inference only for edges that predate explicit typing.
  - Accept met: an authored escalation edge persists as `edge_type='ESCALATION'` without relying on id naming.
  - `bun run typecheck` clean. FE-only — no backend change (the save payload already carried `edge_type`; only
    its source changed).
  - Stretch (MEASUREMENT edge conditions) — **Decision #4: deferred.**

- **1e. [FPI] Mount the orphaned FPI banner + FPI ⊕ batch exclusion (§3.8). — ✅ DONE (core); secondary deferred**
  - **DONE — banner mounted:** `FpiStatusBanner` now renders in `OperatorSubstepRuntimePage` (above the
    batch panel). It self-hides unless the step requires FPI; when pending it gives the operator Start / Pass /
    Fail / Waive — so an FPI-required step is now operable instead of a dead "lot waiting" toast.
  - **DONE — mutual exclusion:** `SubstepSerializer.validate` rejects `scope='batch'` on a step with
    `requires_first_piece_inspection=True` (FPI ⊕ batch). Covered by `test_substep_scope_validation.py` (3 tests).
  - **DEFERRED (secondary):** exposing `requires_first_piece_inspection` + `fpi_scope` in the flow step editor
    and retiring the legacy `EditStepFormPage` checkbox — this overlaps 1a's step-editor work, so it's best
    folded into 1a rather than done twice. FPI authoring still works via the legacy checkbox meanwhile.
  - Scope (Decision #12 — RESOLVED): once-per-WO-step FPI; this task does **not** fix `fpi_scope` gate-time
    filtering or first-piece designation — deferred as a separate effort.
  - `bun run typecheck` clean.

### Phase 2 — Close the rework routing handoffs (respect segregation of duties) — ✅ COMPLETE

> **Status: DONE.** The full rework loop is wired, lifecycle **Y** (AS9100: re-inspect before release):
> QR fail → auto-disposition (QA-assigned) → QA decides REWORK → part split + routed to the in-process rework
> step (disposition stays IN_PROGRESS) → rework + re-inspection (an inspection substep on the rework step) →
> part advances → disposition auto-closes. Terminal-dominant precedence (2a) and CRITICAL/MAJOR containment
> gate (2f) enforced. All disposition suites green (cascade + routing + permissions, 18 tests) + advancement
> regression (11). A latent `split_part_from_lot` bug (dead rework branch) was fixed en route.

- **2a. [REWORK] Harden the existing auto-disposition — conflict precedence. — ✅ DONE (core); refinements deferred**
  - **DONE — terminal-dominant precedence:** `apply_disposition_to_part` now ranks terminal statuses
    (SCRAP > CANCELLED > other terminals) and **refuses to regress a part out of (or downgrade) a terminal
    status** via a less-severe disposition. A REWORK save can no longer un-SCRAP a part; SCRAP still dominates
    a USE_AS_IS'd (READY) part. Tested (`test_disposition_cascade.py`: precedence + the existing close cases).
  - **Already adequate:** the `auto_create_disposition` signal already assigns to a QA-group user
    (`signals.py:28-32`), satisfying Decision #1's intent (the model has only a single `assigned_to` user FK,
    not a group/queue field — true queue assignment would need a model change, out of scope).
  - **Deferred refinements:** (a) a part-level "all open dispositions" view (FE nicety); (b) reconciling the
    `ncr.opened` emit with the auto-disposition into one flow; (c) moving the signal into the `services/qms/`
    FAIL handler. None are correctness issues — the precedence (the real bug) is fixed.
  - REPAIR vs REWORK remains a pure quality choice.

- **2b. [REWORK] Connect a disposition decision to actual part routing. — ✅ DONE (lifecycle Y)**
  - **Lifecycle Y (per AS9100 — re-inspect before release):** routing happens at the **decision** (when QA
    sets `disposition_type=REWORK/REPAIR`), via the disposition serializer's create/update →
    `route_part_to_rework_if_needed(disposition, request.user)`. The part is split off the lot and moved to the
    process's in-process rework step; the **disposition stays IN_PROGRESS** until the rework is re-inspected
    (closed by 2e). `complete_disposition_resolution` no longer routes — it only closes.
  - Routes only when the process has **exactly one** `step_type='REWORK'` step (zero/ambiguous → leave
    REWORK_NEEDED for manual routing via 2c). Idempotent + best-effort: a routing failure never fails the save.
  - **Latent bug fixed:** `split_part_from_lot`'s rework branch (dead until now, since no caller ever passed
    `rework_target_step`) created `StepTransitionLog(..., reason=...)` — but that model has no `reason` field.
    Dropped the kwarg (the rework reason lives on `part.split_reason` + the disposition).
  - Tests (`test_disposition_rework_routing.py`): decision routes the part + keeps the disposition IN_PROGRESS;
    no rework step → clean no-op. Advancement/split regression (11) green.
  - **Decision #2 — RESOLVED: in-process rework step.** Lifecycle (X vs Y) — RESOLVED **Y** per the standards
    ("reworked/repaired items must be re-inspected prior to release"); the NCR-decision stays open until verified.

- **2c. [REWORK] Add the in-process "send to rework step" control. — ✅ DONE**
  - `WorkOrderControlPage` row + bulk "Rework" actions now open a **rework-step picker dialog** (sourced from
    the WO's process steps where `node_type === "REWORK"`) and fire
    `{ kind: "split", reason: "rework", reworkTargetStepId }` (the field was already plumbed to the mutation).
    Empty-state hint when the process has no rework step. `bun run typecheck` clean.
  - Net effect: the in-process rework path is now reachable both automatically (2b) and manually (2c).

- **2d. [REWORK] Guarantee re-inspection of reworked parts. — ✅ DONE**
  - **Decision #7 — the rework step carries its own inspection substep** (re-inspection is a substep on the
    step, not a re-route to the original; confirmed against the DWI model — a Step is a sequence of Substeps
    and one can be `is_inspection_point`). Enforced in `split_part_from_lot`: routing to a `reason=REWORK`
    target raises `ValidationError` unless that step has an active `is_inspection_point` substep — so a rework
    target without re-inspection is rejected before any mutation. Covers both 2b (auto) and 2c (manual).
  - Runtime gate is then existing behaviour: the inspection-point substep must complete to advance, and a FAIL
    creates a QR-fail → quarantine → new disposition (loop). Tested (`test_disposition_rework_routing.py`:
    no-inspection rework target rejected).
  - (SoD note: independent verification, if required, is enforced via the inspection substep's
    signature/role fields — still one node, per Decision #7.)

- **2e. [REWORK] Close the disposition loop on successful rework (G3). — ✅ DONE**
  - When a reworked part **leaves its rework step** (rework + re-inspection passed → it advances),
    `advance_part_step` calls `_close_open_rework_disposition(part, operator)` → `complete_disposition_resolution`
    closes the part's open REWORK/REPAIR disposition. Best-effort: if the disposition still has blockers (e.g.
    CRITICAL/MAJOR containment not yet recorded, 2f), it's left open for QA. Closing re-runs routing harmlessly
    (the part is already split → no-op).
  - This is the close half of lifecycle Y: decide → route (open) → rework → re-inspect PASS → advance → close.
  - Tested (`test_disposition_rework_routing.py`: leaving the rework step closes the open disposition).

- **2f. [REWORK] Surface containment on the disposition (Level 1 — documentary) (§3.7 / Decision #10). — ✅ DONE**
  - **DONE — close gate:** `get_completion_blockers` / `can_be_completed` now require a non-empty
    `containment_action` before a CRITICAL/MAJOR disposition can close (MINOR exempt). The blocker text flows
    to the FE automatically via the serializer's `completion_blockers` field. Tested
    (`test_disposition_cascade.py`: MAJOR blocked until containment recorded, then closes).
  - `containment_action` + `severity` are already writable on `QuarantineDispositionSerializer` (not
    read-only), so the disposition form can set them; surfacing a dedicated containment input on
    `EditDispositionFormPage` is a small remaining FE nicety (the blocker reason already shows).
  - Documentary only — assisted "find & quarantine at-risk WIP" (Level 2) remains explicitly deferred.

### Phase 3 — Bulk runtime capture (largest build)

- **3a. [BULK] Add the batch-bound capture write path — the one missing piece (G1). — ✅ DONE (backend + FE); measurements remain**
  - **No migration needed** — the model layer was already there (migration `0059`: `batch_execution` FKs on
    `SubstepCompletion`/`SubstepResponse` + "exactly one of step/batch exec" check + `(batch_execution, substep
    [, node_id])` partial-unique). The whole gap was write-path logic.
  - **DONE (backend):** `submit_substep` + `_write_substep_response` + `_record_completion` now accept
    `batch_execution` (exactly one of step/batch exec); upserts key on whichever is set; the submit viewset
    accepts a `batch_execution` body param. In batch mode the inspection-QR side effects are skipped (a batch
    spans many parts → no single-part QR), and `measurement`/`harvested_components` captures are **rejected**
    (v1 batch substeps = attestation/status/text/choice/timer/sign-off). So a batch capture now lands a
    `SubstepCompletion` bound to the batch → `seal_batch` succeeds → `try_advance_lot` fires.
  - Tests (`test_batch_capture.py`, 3): seal fails without a batch completion; batch capture writes the
    batch-bound completion + enables seal; measurement-in-batch rejected. 84 DWI regression tests green
    (per-part submit path unaffected). No schema regen needed (no new API fields — the body param is untyped).
  - **DONE (FE):** `BatchPanel.tsx` now renders a `BatchCaptureSection` under each open batch — it fetches the
    step's substeps (`useSubsteps({ step })`), filters to `scope === "batch"`, and renders each with the same
    `SubstepOperatorView` + `OperatorResponseContext` the per-part runtime uses, submitting via `useSubmitSubstep`
    with `{ batch_execution, captures }` (the submit body type now allows either exec). Required fields gate on
    `findMissingRequired`; captures stay editable until seal ("Update batch capture" re-upserts). Typecheck green.
  - **REMAINING:** **Per-batch measurements** (Decision #13) — needs a nullable `batch_execution` FK on
    `StepExecutionMeasurement` + migration; deferred so 3a's core lands migration-free. SPC stays out of
    scope (§3.9).
  - **Decision #3 — RESOLVED: yes** — a batch can be added-to/edited until `sealed_at` locks it (the FE surface
    should allow edits until seal).

- **3c. [BULK] Batch cohort integrity & guards (G6/G7). — ✅ DONE**
  - Problems: (a) `BatchExecution.parts` isn't reconciled when a member is split/scrapped/quarantined after
    start — only the FE filters split parts, the backend doesn't; (b) no membership guard; (c) a per-part
    inspection failure inside a batch isn't split out or blocked at seal.
  - **Decision #14 — multiple batches per (WO, step) is VALID and required.** A fixed-capacity op (furnace,
    wash tank, autoclave) splits one lot into several loads run concurrently or in sequence. So the invariant
    is NOT "one open batch per (WO, step)" — it's **disjoint membership**: a part is in at most one *open*
    batch per step (else it's ambiguous which load's cycle data covers it). Sealed batches don't reserve
    membership. **Each load advances independently when it seals** (Decision #15), not as one lot.
  - **DONE (backend):**
    - **Membership reconciliation** — `seal_batch` drops members that went terminal (scrapped/cancelled)
      after start and re-resolves the live cohort; seal fails if no live members remain. Split parts stay
      (Case-19: the batch substep still covers a split-out part's operation).
    - **Disjoint-membership guard** — `batch_lifecycle.assert_no_open_batch_overlap(step, parts)` raises if any
      selected part is already in an open batch at the step; wired into `BatchExecutionViewSet.perform_create`
      (which also stamps `started_by`). No DB uniqueness constraint — the earlier `uniq_open_batch_per_wo_step`
      was *wrong* (forbade furnace-load splitting) and was reverted.
    - **Per-load independent advancement** — `_evaluate_and_advance` now detects a batch step (has any
      BATCH-scope substep) and advances each cohort part whose gate clears *individually*, instead of
      all-or-none. The per-part gate (`substep_completion_blockers`) already clears a part only when ITS OWN
      sealed batch carries the substep completion, so one sealed load moves on without waiting for the others.
      Non-batch steps keep classic all-or-none lot cohesion.
    - **Terminal-part exclusion** — the engine excludes terminal-status parts from the (WO, step) cohort, so a
      scrapped part left at a step can't block or be re-advanced.
  - **DONE (FE):** `BatchPanel` now starts a load from an operator-selected **subset** of units (checkbox
    picker) rather than dumping the whole cohort into one batch; parts already in an open batch are hidden
    (disjoint membership). A truncation warning blocks batch-start when the cohort list is incomplete
    (`OperatorSubstepRuntimePage` passes `cohortTruncated` from `count > results.length`).
  - **DONE (FE, all three `limit:500` sites):** `OperatorSubstepRuntimePage` blocks batch-start on truncation;
    `WorkOrderControlPage` (supervisor) and `StartWorkDialog` (start-work picker) now show a `count > loaded`
    warning banner so counts/actions aren't read as the whole lot. No silent truncation remains.
  - Tests: `test_batch_cohort_integrity.py` — seal drops scrapped member; seal fails when all terminal;
    disjoint open batches allowed; overlap rejected; overlap allowed after seal; terminal parts excluded;
    **sealed load advances without waiting for the other load**; large cohort dispatches async.

- **3d. [BULK / PERF] Make lot/batch advancement scale (§3.10). — ✅ DONE (targeted)**
  - Problem: the dominant cost is the **existing** engine — `try_advance_lot` gated each cohort part and then
    `advance_part_step` re-ran the same `can_advance_from_step` gate (double gate), and `seal_batch` ran the
    whole advance synchronously in-request.
  - **DONE:**
    - **Double-gate eliminated** — `advance_part_step(..., skip_gate_check=True)`; the engine already gated, so
      the redundant per-part re-gate (the dominant cost) is skipped. Direct callers still gate (default False).
    - **Async seal for large cohorts** — `seal_batch` advances synchronously for cohorts ≤
      `ASYNC_ADVANCE_THRESHOLD` (50) so the operator sees the move immediately; larger cohorts dispatch
      `advance_lot_task` (Celery, idempotent, `transaction.on_commit`) so the seal request stays bounded.
    - **Prefetch** — the cohort query `select_related('step','work_order','part_type')` to cut per-part N+1.
  - **NOT done (deferred):** the deeper hoist of step-invariant gate queries (substeps, required measurements,
    QA/FPI) into a single cohort-level prefetch, and bulk-write of the advance. The double-gate cut already
    roughly halves the per-part query count; revisit with a benchmark if a real large lot is still slow.
    Scope held to the advancement path; no general rewrite.

- **3b. [BULK] Make batch-gating visible in the operator runtime. — ✅ DONE**
  - **Reframed for the per-load model (Decisions #14/#15):** the original "12/15 parts ready — lot advances at
    80%" framing was the legacy `requires_batch_completion` + `pass_threshold` whole-lot mechanism. Under the
    corrected model parts advance *by load*, each sealing independently — so a "% of lot ready" banner would
    misdescribe the behavior.
  - **DONE:** `BatchPanel`'s header (rendered only on batch steps, so it IS the up-front banner) now explains
    the gating — "Parts advance by load — group the units going through this op together, capture once, then
    seal. Each sealed load moves on independently." — and shows coverage progress: `{batched}/{total} parts in
    a load · {n} not yet batched`, plus the existing `{open} open · {sealed} sealed` load counts.
  - Accept: an operator on a batch step understands up front that the step runs in loads (not part-by-part),
    that each load advances on its own seal, and sees how many parts still need a load.

### Phase 4 — Observability & guardrails

- **4a. [REWORK] Decision-point resolver UI at runtime. — ✅ DONE**
  - **Decision #16 — split by type (who resolves):** QA_RESULT decision points route automatically from the
    QualityReport (the engine already pulls the latest QR in `get_next_step`); only MANUAL points need a human
    pick, gated to **manager/lead** (QA Manager, Production Manager, Shift Lead, Tenant Admin).
  - **DONE (backend):**
    - New permission `resolve_step_decision` (Parts Meta, migration `0073`), added to `DECISION_RESOLUTION_PERMISSIONS`
      and granted to the four manager/lead roles in `presets.py`; synced to existing tenant groups via
      `GroupSeeder.sync_permissions()`.
    - `GET /api/Parts/{id}/decision_options/` — `{is_decision_point, decision_type, default_branch,
      alternate_branch, qa_suggested}` (branch targets resolved from StepEdges for real labels).
    - `POST /api/Parts/{id}/resolve_decision/` — gated by `resolve_step_decision` (via `action_permissions` +
      `crud_exempt`), MANUAL-only, routes the chosen branch. **Bypasses the per-part advancement gate on
      purpose** — the manual decision is authoritative, and the gate's pass-oriented checks (QA signoff, FPI)
      would otherwise paradoxically block routing a *failed* part to its rework branch.
    - Engine: a MANUAL decision step now reports `blocked` (`manual_decision_required`) from the normal
      complete-step flow instead of raising/500-ing.
  - **DONE (FE):** `DecisionResolverPanel` in the operator runtime — QA_RESULT shows an auto-route info note
    ("pass → X / fail → Y"); MANUAL shows permission-gated "Pass → X" / "Fail/rework → Y" branch buttons
    (hidden with an explanatory note for users without the permission). Hooks `useDecisionOptions` /
    `useResolveDecision` in `hooks/parts.ts`.
  - **Bonus bug fixed (surfaced by the smoke test):** the substep-completion gate and `seal_batch` counted
    **archived** substeps — a soft-deleted substep wrongly blocked advancement / seal. Both now filter
    `archived=False`.
  - Tests: `test_decision_resolution.py` (3) — MANUAL blocks auto-advance; DEFAULT→pass routing;
    ALTERNATE→rework routing. Browser-verified end-to-end: QA_RESULT info panel, MANUAL picker + permission
    gate, resolve → part routed to the chosen step, zero zodios errors.
  - Accept: ✅ a manual/QA decision step can be resolved in-app and routes the part along the chosen edge.

- **4b. [REWORK] Surface redo limits & escalation. — ✅ DONE**
  - **DONE (backend):** `GET /api/Parts/{id}/rework_status/` → `{total_rework_count, current_step_name,
    max_visits, current_visits, remaining, at_limit, escalation_step_name}`. Reuses
    `StepExecution.get_visit_count` + the ESCALATION `StepEdge` lookup (the same data `_check_cycle_limit`
    uses), so the surface matches engine behavior.
  - **DONE (FE):** `ReworkLimitBanner` in the operator runtime — renders only on a visit-capped (rework-loop)
    step. Shows "Rework attempt N of M", attempts remaining, and the escalation target; flips to a destructive
    "Visit cap reached — next failure escalates automatically … engine-driven, not a manual scrap decision"
    when `at_limit`. `WorkOrderControlPage` already shows a per-part `Rework ×N` badge (`total_rework_count`);
    the per-step cap/escalation detail lives in the per-part runtime banner (mixing total reworks with
    per-step visit caps in a list column would be misleading, and per-row caps would be an N+1).
  - **Runtime fix (also helps 4a):** a step with **no substeps** previously dead-ended on the "author
    substeps" screen, hiding the banners. Now the runtime renders the banners (which self-hide when N/A) above
    that message — so a **decision point with no substeps still shows its resolver**, and a capped step shows
    its rework status. (Rework steps *should* have substeps — the "author them" prompt correctly flags the gap
    when they don't.)
  - Browser-verified: not-at-limit ("attempt 1 of 3 · 2 more…") and at-limit (destructive cap-reached)
    states both render; zero console errors.
  - Accept: ✅ a user sees how many rework attempts remain and that escalation is engine-driven, not a manual
    scrap decision.

- **4c. [REWORK+BULK] Live runtime overlay on the flow map. — ✅ DONE**
  - **DONE (backend):** `GET /api/WorkOrders/{id}/step_metrics/` → `{steps: [{step_id, total, in_rework,
    quarantined, awaiting_qa}]}`. Single grouped query (GROUP BY step, part_status) over live (non-terminal)
    parts — accurate regardless of the 500-part list cap, and gives a status breakdown the client-side parts
    list doesn't.
  - **DONE (FE):** the node components had a `NodeOverlays` part-count badge, but it was **demo-gated**
    (only rendered under a `demoMode`), so the control page's read-only canvas showed nothing. Added an
    always-on `LiveMetricsBadge` (threaded `liveMetrics` through `StepData` → `buildNodesAndEdges` → node
    data) that renders a per-node count pill whenever real metrics are present, with an **attention accent**
    (destructive when any quarantined, orange when any in rework). `WorkOrderControlPage` fetches
    `useWorkOrderStepMetrics` and passes `liveMetrics` per step into `FlowCanvas`.
  - **Reframe (per the per-load pivot):** the original note said "rework loops *and batch holds*" — batch
    cohesion is now per-load, not a single whole-lot hold node, so the overlay reflects part distribution per
    step (rework/quarantine surfaced via the accent), not a batch-gate node.
  - Browser-verified: on WO-TRAIN-BOTTLE the map shows **Flow Testing = 6**, **Assembly = 2**, empty nodes
    blank — matching the live data; zero console errors. Tests: `test_step_metrics.py` (2) — status buckets
    (in_rework/quarantined/awaiting_qa) + terminal exclusion.
  - Accept: ✅ a supervisor sees where parts actually sit on the authored map, with rework/quarantine
    surfaced by the node accent.

---

## 5. Decisions to confirm before building

1. **Disposition assignment (2a):** auto-assign failed parts to a specific quality user or to a
   group/queue? (Affects notification + queue UI.) Answer: Assign it to the QA related groups
2. **Rework routing owner (2b/2c):** does quality choose the rework target at disposition time, or does a
   supervisor route afterward? And is the default an **in-process rework step** or a **child-WO rework
   process**? (Both backends exist; pick the primary UX.) In process rework step
3. **Batch re-open semantics (3a):** can a batch be edited after first capture but before seal? Yes
4. **Measurement-routed decisions (1d stretch):** are `decision_type=MEASUREMENT` branches needed
   near-term, or can edge-condition authoring stay deferred? Stay deferred for now
5. **Disposition trigger point (0a/2b):** should a disposition act on the part when the *type is set*
   (IN_PROGRESS) or only when it is *closed*? Today's intent fires on either; pick one for clarity. When the type is set
6. **Approval authority (0b):** do SCRAP / USE_AS_IS / REPAIR require elevated authority (and/or enforced
   customer approval) vs. REWORK? Severity (CRITICAL/MAJOR/MINOR) exists but drives nothing — should it? That's foundational data for later
7. **Re-inspection target (2d):** must a reworked part re-pass the *original* inspection step, or is an
   inspection substep on the rework step sufficient? Rework will get its own inspections for the rework operation
8. **REPAIR concession handling (§3.7f):** is the existing Deviation Request PDF + `requires_customer_approval`
   flag enough for REPAIR, or does REPAIR need an enforced concession/deviation record before the part can
   advance? (Avoid a new model unless genuinely required — `CLAUDE.md` prefers fields/flags.) Another to defer to later
9. **Lot-wide nonconformance (§3.7i):** dispositions are per-part. Is a batch/MRB disposition over many
   parts needed, or is creating N per-part dispositions acceptable for now? N per part
10. **Containment (§3.7 / G9):** `containment_action` fields are dormant. → **RESOLVED: Level 1 (documentary)**
    — surface `containment_action` in the disposition UI and require it for CRITICAL/MAJOR before close;
    record what was done, no system action on other parts. Assisted "find & quarantine at-risk WIP" (level 2)
    is deferred. See task 2f.
11. **Per-part failure inside a batch (G7/3c):** when one part fails during a batch operation, split it out
    and seal the rest, or block the whole batch? (Drives 3c behavior.) Split it and any other parts that failed at that operation out and seal the rest
12. **FPI × batch + FPI depth (§3.8 / 1e):** → **RESOLVED:** FPI and batch-scope are **mutually exclusive**
    (a step can't be both — enforce in 1e). Depth = **once-per-WO-step toggle (minimal)** — just mount the
    banner (1e); real `fpi_scope` gate-time filtering + first-piece designation (`StepExecution.is_fpi`) are
    **deferred** as a separate effort.
13. **Batch measurements & SPC (§3.9 / 3a):** do batch-scope substeps need to capture **measurements** (and
    therefore a per-lot measurement store), or are they attestation/sign-off only? And must per-batch readings
    feed **SPC** — noting SPC is currently unwired (`block_on_spc_violation` is dead), so consuming them is a
    separate effort, not part of this plan. They could, so we can work with that potentially

---

## 6. Quick reference — key files

| Area | File |
|---|---|
| Step / Steps / StepEdge / Parts models | `PartsTracker/Tracker/models/mes_lite.py` |
| Substep / BatchExecution models | `PartsTracker/Tracker/models/dwi.py` |
| Lot advancement engine | `PartsTracker/Tracker/services/mes/advancement.py` |
| Part advance / split | `PartsTracker/Tracker/services/mes/parts.py`, `services/mes/splits.py` |
| WO split (rework→child) | `PartsTracker/Tracker/services/mes/work_order.py` |
| QR fail side-effects | `PartsTracker/Tracker/services/qms/quality_report.py` |
| Disposition / NCR model (incl. dead cascade §3.7a) | `PartsTracker/Tracker/models/qms.py` |
| Disposition resolution (Phase 0a/2b hook) | `PartsTracker/Tracker/services/qms/disposition.py` |
| NCR PDF adapter (disposition rendering) | `PartsTracker/Tracker/reports/adapters/ncr.py` |
| Flow editor | `ambac-tracker-ui/src/pages/ProcessFlowPage.tsx`, `src/components/flow/*` |
| DWI editor | `ambac-tracker-ui/src/pages/editors/SubstepEditorPage.tsx`, `src/lib/dwi/*` |
| Operator runtime | `ambac-tracker-ui/src/pages/operator/OperatorSubstepRuntimePage.tsx` |
| Batch panel (stub) | `ambac-tracker-ui/src/components/dwi/BatchPanel.tsx` |
| Supervisor control | `ambac-tracker-ui/src/pages/workorders/WorkOrderControlPage.tsx` |
| Quality disposition UI | `ambac-tracker-ui/src/pages/editors/QaQuarantinePage.tsx`, `forms/EditDispositionFormPage.tsx` |
| Route definitions | `ambac-tracker-ui/src/router.tsx` |

---

## 7. Changes by route

A page-oriented index of the finished state: open the URL, see what's different. No new top-level
URLs are required — every item below is an in-place enhancement of an existing route (routes from
`src/router.tsx`). Task IDs in brackets refer to §4.

### `/process-flow` — Process flow editor (`ProcessFlowPage`)
- **[1a]** New "Batch completion" toggle on the step editor panel; when on, a readiness-fraction input
  appears, **relabeled** "fraction of lot ready to advance" (no longer "pass threshold"). Only meaningful
  once wired into the live engine (1a-ii) — otherwise labeled advisory.
- **[1d]** Edges get an explicit type control (DEFAULT / ALTERNATE / ESCALATION) instead of the type being
  inferred from the edge-id suffix, so authoring a rework-escalation path is intentional.
- **[1e, secondary]** FPI authoring moves here — `requires_first_piece_inspection` + `fpi_scope` on the step
  editor panel (retiring the legacy `EditStepFormPage` checkbox); a step can't be both FPI and batch.

### `/editor/processes/$processId/steps/$stepId/substeps` — DWI authoring (`SubstepEditorPage`)
- **[1b]** New per-substep **scope toggle** (SAMPLED vs BATCH) + a hint that BATCH captures are recorded once
  per batch (`BatchExecution`), not per part. The only place a batch substep can be authored.

### `/workorder/$workOrderId/control` — Supervisor control (`WorkOrderControlPage`)
- **[1c]** The "Rework" split dropdown is backed by real processes (`GET /Processes/?is_remanufactured=true`)
  instead of fabricated IDs — the child-WO rework split **actually works** instead of being rejected.
- **[2c]** Row/bulk "Rework" opens a **rework-step picker** and routes parts into a real in-process rework
  step (`rework_target_step_id`), instead of only flipping a status flag.
- **[4b]** Each part row shows **attempts vs. cap** (`total_rework_count` / `max_visits`) and flags when the
  next failure escalates to scrap.
- **[4c]** The embedded flow map becomes a **live overlay** (real part counts/status per node, replacing the
  demo-only overlays) — you can watch parts sitting in rework/escalation.
- **[0d]** "Set status" / rollback can **no longer casually un-scrap** a part — leaving a terminal status
  requires a privileged, reason-required action (available to elevated roles: admins, QA/production managers).

### `/production/dispositions` — Quality disposition queue (`QaQuarantinePage`)
- **[2a]** Failed inspections **already auto-create** QA-assigned dispositions here (`auto_create_disposition`
  signal, one per failed QR — correct). The change is **hardening**: conflict precedence when a part has
  multiple dispositions (terminal-dominant), robust assignment, `ncr.opened` reconcile.
- **[Phase 0 · done]** Dispositions now **actually move part status** (REWORK→REWORK_NEEDED, SCRAP→SCRAPPED,
  …); the cascade was silently dead before.

### `/dispositions/edit/$id` and `/dispositions/create` — Disposition form (`EditDispositionFormPage`)
- **[0c]** Closing a disposition through the sanctioned path **works** (the close service no longer throws on
  every real disposition).
- **[2b]** Resolving a REWORK/REPAIR disposition **routes the part** (triggers the split to a rework
  step/process) — decision and physical routing are finally connected.
- **[2e]** A disposition **auto-closes** once its part is reworked and passes re-inspection (no more
  orphaned `IN_PROGRESS` dispositions).
- **[2f]** A **containment** field is surfaced (and required for CRITICAL/MAJOR before close) — documentary
  level 1; no automated at-risk-WIP quarantine yet.
- **[0b]** Closing/approving a disposition is **permission-gated** (`close_disposition` / `approve_disposition`).
- *(Optional cleanup — §URL note: these legacy paths could migrate to `/production/dispositions/new` and
  `/production/dispositions/$id/edit` to match the `CLAUDE.md` convention, with redirects.)*

### `/operator/steps/$stepId/substeps` — Operator runtime (`OperatorSubstepRuntimePage`)
- **[3a]** Batch-scope substeps become **capturable** — BatchPanel gains a real capture surface behind its
  start/seal lifecycle (today it can only open/seal an empty envelope). May add a `batch=<id>` search param.
- **[3b]** A **batch-gating banner** on batch steps shows readiness progress ("12/15 ready — advances at
  80%"), so operators know the lot moves together.
- **[3c, behind the scenes]** A cohort/batch >500 parts is no longer **silently truncated** (the `limit: 500`
  fix), and **[3d]** sealing/advancing a large batch stays responsive (async + de-N+1'd engine).
- **[4a]** A **decision-point resolver** (pick pass vs. fail/rework branch) for `is_decision_point` steps —
  likely a panel here; promote to its own route (`/operator/steps/$stepId/decision`) only if it must be
  linkable from notifications.
- **[4b]** Rework attempt / remaining-attempts visibility for the part in hand.
- **[2d]** Reworked parts become **unable to advance** until re-inspection passes — surfaced via the existing
  blocker/"blocked" messaging, not a new control.
- **[1e]** FPI is **operable from the runtime** — the FPI banner (Start/Pass/Fail/Waive) is mounted, so an
  operator can clear a first-piece inspection instead of hitting a dead "blocked" toast.