# UQMES Behavior Flows

Flow charts describing how UQMES *should* behave, grounded in how real MES
systems run in real factories. Diagrams are the source of truth; prose is
just enough context to read them.

Every flow is **synchronous unless explicitly noted**. No Celery cascades,
no event fan-out, no background magic.

---

## 1. Operator completes a substep

The operator finishes capturing data on a single substep and submits. This
is *not* an advancement event — just a capture write.

```mermaid
flowchart TD
    A[Operator captures<br/>measurements / responses] --> B[Tap 'Submit'<br/>on substep]
    B --> C{Marked N/A?}
    C -->|No| D[Validate captures]
    C -->|Yes| E{Substep.is_critical<br/>or !allow_not_applicable<br/>or no reason code?}
    E -->|Yes| F[Reject 400<br/>Show error to operator]
    E -->|No| G[Write SubstepCompletion<br/>marked_not_applicable=true<br/>na_reason_code=...]
    D --> H[Write SubstepResponse rows<br/>StepExecutionMeasurement<br/>QualityReports if inspection point]
    H --> I[Write SubstepCompletion<br/>marked_not_applicable=false]
    G --> J[Return success<br/>Operator moves to next substep]
    I --> J
    F -.->|Operator fixes input| B
```

**Key points:**
- Submitting a substep does not advance the part. Advancement happens at
  step completion.
- Inspection-point measurements out of spec trigger flow #3, but the
  submit itself still succeeds.

---

## 2. Operator completes a step (the actual advancement trigger)

This is *the* advancement action. The operator finishes their work at a
station and explicitly indicates the step is done for their part.

```mermaid
flowchart TD
    A[Operator hits<br/>'Complete step'] --> B[Server: evaluate gate<br/>for this part]
    B --> C{Gate clears?}
    C -->|No| D[Return blocker list<br/>Operator sees missing items]
    C -->|Yes| E{Is this part split?}
    E -->|Yes| F[Advance this part solo<br/>to next step]
    E -->|No| G{All non-split cohort parts<br/>at this WO+Step<br/>have cleared the gate?}
    G -->|No| H["Wait — part is ready<br/>but cohort isn't<br/>Operator's work is done"]
    G -->|Yes| I[Advance entire cohort<br/>atomically to next step]
    F --> J[Return success<br/>Show next-step info]
    I --> J
    D -.->|Operator fixes blocker| A
    H --> K[Sibling operators<br/>finish their parts]
    K -.->|Last sibling completes| G
```

**Key points:**
- Synchronous. One gate evaluation per Complete-step action.
- No background task fires from this. The operator gets the result inline.
- Each operator completes their own part; the lot moves when the last
  sibling does.

---

## 3. Out-of-spec measurement → QA queue (no auto-disposition)

Operator captures a value that's outside tolerance. The system flags it,
but the operator does not disposition.

```mermaid
flowchart TD
    A[Operator enters<br/>measurement value] --> B[Server: validate against<br/>nominal + tolerance]
    B --> C{In spec?}
    C -->|Yes| D[Mark is_within_spec=true<br/>Capture node shows green ✓]
    C -->|No| E[Mark is_within_spec=false<br/>Capture node shows red ✗]
    E --> F["Toast to operator:<br/>'Out of spec — flagged for QA review.<br/>You can continue.'"]
    F --> G{Is inspection point?}
    G -->|Yes| H[Auto-create<br/>QualityReports row<br/>status=FAIL]
    G -->|No| I[Only StepExecutionMeasurement<br/>row written]
    H --> J[QR appears in<br/>QA queue]
    I --> K[Operator continues<br/>to next substep]
    D --> K
    J --> L{QA dispositions:}
    L -->|Pass-with-deviation| M[Update QR status=PASS<br/>+ deviation note]
    L -->|Open NCR/CAPA| N[Promote to formal NCR<br/>route to disposition flow]
    L -->|Send for rework| O[Use split-for-rework lever<br/>see flow #5]
    L -->|Scrap| P[Use split-for-scrap lever<br/>see flow #5]
```

**Key points:**
- Operator never sees a forced-disposition modal. They're not authorized.
- Auto-NCR fires ONLY when the substep is `is_inspection_point=True`.
  Routine process-data captures do not create QualityReports.
- All dispositions are deliberate human actions taken later by QA.

---

## 4. Split for quarantine / scrap

Manual lever to pull a part off the cohort so it advances independently.
Used when a part can't continue with its siblings (quality hold, scrap
decision). Rework has its own flow (#5).

Expedite / customer-pull cases are NOT splits — they bump
`WorkOrder.workorder_priority` so the whole lot moves through queues
faster while staying together. Splitting for expedite creates downstream
packing/shipping pain when the expedited part has to rejoin its siblings
at finished goods.

```mermaid
flowchart TD
    A[Supervisor / Operator opens<br/>part action menu] --> B[Pick split reason:<br/>quarantine / scrap]
    B --> C{Has permission?}
    C -->|No| D[Reject 403]
    C -->|Yes| E[Set Parts.split_from_cohort=true<br/>+ split_reason + split_at]
    E --> F[Audit log row<br/>'part split by USER for REASON']
    F --> G[Synchronously try_advance_lot<br/>for the remaining cohort]
    G --> H{Remaining cohort<br/>gate clears?}
    H -->|Yes| I[Cohort advances<br/>without the split part]
    H -->|No| J["Cohort waits — other<br/>parts still missing work"]
    I --> K[Done]
    J --> K
```

**Key points:**
- Splits are one-way. No re-merge in v1.
- The split itself is the only synchronous side effect; advancement of the
  remaining cohort runs in the same request.

---

## 5. Split for rework (routed via process flow)

Like a regular split, but the part is moved to a `rework_target_step`
defined on the Step's StepEdge graph (edge_type=REWORK), not just held in
place.

```mermaid
flowchart TD
    A[Supervisor / Operator picks<br/>'Split for rework'] --> B{Step has<br/>rework_target_step?}
    B -->|No| C[Reject:<br/>'No rework path configured']
    B -->|Yes| D[Close current StepExecution<br/>status=ROLLED_BACK]
    D --> E[Set Parts.split_from_cohort=true<br/>split_reason=rework]
    E --> F[Move Parts.step =<br/>rework_target_step]
    F --> G[Create new StepExecution<br/>at rework target<br/>visit_number bumped]
    G --> H[Write SamplingDecisions<br/>for the new exec]
    H --> I[StepTransitionLog row]
    I --> J[Synchronously try_advance_lot<br/>for original cohort]
    J --> K[Part now travels solo<br/>through the rework path]
```

**Key points:**
- The rework path is a part of the process design (StepEdge graph), not
  ad-hoc.
- The reworked part will visit the rework step + come back through the
  canonical flow (often re-entering inspection), generating a new
  StepExecution with `visit_number=N+1`. Prior visit completions don't
  satisfy the new gate.

---

## 6. Force advance (supervisor emergency lever)

For stuck lots that can't resolve through normal flow. Sensor offline,
operator out, missing data that won't be recoverable. Permission-gated.

```mermaid
flowchart TD
    A[Supervisor sees stuck lot<br/>on WO Control page] --> B[Check blocker reasons<br/>shown inline]
    B --> C[Click 'Force advance' button]
    C --> D{User in production_manager<br/>/ qa_manager / admin?}
    D -->|No| E[Button not visible<br/>or click rejected]
    D -->|Yes| F[Confirm dialog with<br/>reason field]
    F --> G[Server: bypass gate<br/>force advance lot]
    G --> H[Each part advanced<br/>to next step]
    H --> I[StepTransitionLog rows<br/>with 'force_advanced_by'<br/>+ reason]
    I --> J[StepOverride row<br/>links to advancement]
    J --> K[Lot now at next step]
```

**Key points:**
- Not the default mechanism. It's the safety valve.
- Audit row identifies the human who overrode and why.

---

## 7. Batch lifecycle (per-cohort operations like heat treat)

When a Step has BATCH-scope substeps, an operator manages the batch as a
unit. The seal action is the cohort's "complete step" trigger.

```mermaid
flowchart TD
    A[Operator at batch station<br/>sees BATCH-scope step] --> B[Click 'Start batch with cohort']
    B --> C[Create BatchExecution<br/>parts = current cohort<br/>sealed_at=NULL]
    C --> D[Operator runs physical<br/>batch operation<br/>e.g., load oven, start cycle]
    D --> E[Operator captures<br/>BATCH-scope substep data<br/>cycle temp, dwell time, etc.]
    E --> F[Write SubstepCompletion rows<br/>linked to BatchExecution]
    F --> G[Operator clicks<br/>'Seal batch']
    G --> H[Server: validate]
    H --> I{All required BATCH<br/>substeps complete?}
    I -->|No| J[Reject 400<br/>'Cycle log incomplete']
    I -->|Yes| K{All parts in batch<br/>share work_order?}
    K -->|No| L[Reject 400<br/>'Cross-WO membership']
    K -->|Yes| M[Set sealed_at = now<br/>Audit log]
    M --> N[Synchronously try_advance_lot<br/>for the WO+Step]
    N --> O[Each cohort part's gate<br/>now sees a sealed batch<br/>covering it]
    O --> P[Cohort advances together<br/>to next step]
    J -.->|Operator captures missing data| E
```

**Key points:**
- Operator deliberately seals; no auto-seal on last capture.
- Sealing is the per-cohort analog of "Complete step" — same advancement
  trigger semantics.
- One BatchExecution per WO. Multi-WO physical runs produce multiple
  BatchExecution rows.

---

## 8. Sampling decision at step entry

When a part enters a step (new StepExecution created), the system writes
one SamplingDecision row per substep. The advancement gate reads these
later.

```mermaid
flowchart TD
    A[Part advances into a Step] --> B[Create StepExecution row]
    B --> C[For each Substep on this Step:]
    C --> D{Substep.scope?}
    D -->|BATCH| E[Write SamplingDecision<br/>outcome=SELECTED]
    D -->|SAMPLED| F{Substep.sampling_rule?}
    F -->|None 100% sample| G[Write SamplingDecision<br/>outcome=SELECTED]
    F -->|Some rule| H{Rule type?}
    H -->|EVERY_NTH_PART| I[cohort_position % N == 0?]
    H -->|FIRST_N_PARTS| J[cohort_position <= N?]
    H -->|PERCENTAGE| K[Deterministic hash<br/>against threshold]
    H -->|RANDOM| L[random.random vs threshold]
    H -->|LAST_N_PARTS / EXACT_COUNT| M["Cohort not closed yet<br/>→ PENDING"]
    I --> N{Match?}
    J --> N
    K --> N
    L --> N
    N -->|Yes| O[Write SamplingDecision<br/>outcome=SELECTED]
    N -->|No| P[Write SamplingDecision<br/>outcome=DESELECTED]
    M --> Q[Write SamplingDecision<br/>outcome=PENDING]
    E --> R[Done for this substep]
    G --> R
    O --> R
    P --> R
    Q --> R
```

**Key points:**
- Decisions are append-only. Rule changes write new rows with
  `superseded_by` pointing back to the old one.
- PENDING is non-blocking at intermediate steps. The part advances
  tentatively through CNC, assembly, etc.
- PENDING **is blocking at terminal (shipment) steps**. The gate refuses
  to advance any part with live PENDING SamplingDecisions when the step
  is marked `is_terminal=True`, forcing supervisor reconciliation before
  finished goods. Prevents shipping unverified product when rules like
  LAST_N_PARTS / EXACT_COUNT can't decide at part entry.
- Reconciliation at the terminal step is a supervisor UI action — pick
  outcomes manually, or trigger re-evaluation with now-known cohort size.
- DESELECTED substeps are **hidden from the operator's runtime entirely**
  — they don't see the substep, they don't see "Not in sample."

---

## 9. Advancement gate (what `can_advance_from_step` evaluates)

Called synchronously inside any advancement-triggering action (Complete
step, seal batch, force advance, split-driven cohort retry). Returns a list
of blockers; empty list = clear.

```mermaid
flowchart TD
    A[Gate called for<br/>StepExecution + WorkOrder] --> B[Check Step's existing<br/>blockers in order]
    B --> C[#1 Quarantine status]
    C --> D[#2 QA signoff]
    D --> E[#3 First piece inspection]
    E --> F[#4 Sampling QR<br/>step-level]
    F --> G[#5 Mandatory measurements<br/>block_on_measurement_failure]
    G --> H[#6 StepRequirement entries]
    H --> I[#7 Substep completion gate]
    I --> I2{Step.is_terminal?}
    I2 -->|Yes| I3["#8 Live PENDING<br/>SamplingDecisions on this WO?<br/>(reconcile before shipment)"]
    I2 -->|No| J[#9 StepOverride clears any?]
    I3 --> J
    J --> K{Any blockers<br/>not overridden?}
    K -->|Yes| L[Return blockers list]
    K -->|No| M[Return clear<br/>safe to advance]

    subgraph subgate [#7 Substep completion gate]
        SG1[For each Substep on this Step:] --> SG2{Optional<br/>+ no completion?}
        SG2 -->|Yes| SG3["Skip — operator declined"]
        SG2 -->|No| SG4{Scope?}
        SG4 -->|SAMPLED| SG5[Read live SamplingDecision]
        SG5 --> SG6{Outcome?}
        SG6 -->|DESELECTED| SG7[Satisfied]
        SG6 -->|PENDING| SG8["Non-blocking at non-terminal steps<br/>Blocked at Step.is_terminal=true<br/>by gate-level blocker #8"]
        SG6 -->|SELECTED| SG9{Non-voided<br/>SubstepCompletion exists?}
        SG9 -->|No| SG10[Blocker: 'not completed']
        SG9 -->|Yes| SG11{N/A still valid?<br/>not critical,<br/>allow_not_applicable,<br/>has reason code}
        SG11 -->|No| SG12[Blocker: 'N/A no longer valid']
        SG11 -->|Yes| SG13[Satisfied]
        SG4 -->|BATCH| SG14{Sealed BatchExecution<br/>covers this part?}
        SG14 -->|No| SG15[Blocker: 'no sealed batch']
        SG14 -->|Yes| SG16{Cohort completion<br/>exists for substep?}
        SG16 -->|No| SG17[Blocker: 'no batch completion']
        SG16 -->|Yes| SG18[Satisfied]
    end
```

**Key points:**
- Pure read query. No side effects.
- N/A is re-validated at gate time so retroactive `is_critical=True` edits
  invalidate existing N/A rows.
- Voided completions don't satisfy.

---

## 10. QA voids a SubstepCompletion (correction flow)

When QA discovers a problem after the fact — equipment out of cal,
operator did the wrong check, wrong revision pulled — they void the
completion. The gate re-evaluates and blocks downstream.

```mermaid
flowchart TD
    A[QA reviews part traveler<br/>finds bad completion] --> B[Open 'Void completion'<br/>dialog]
    B --> C[Enter void_reason]
    C --> D{User in QA group<br/>/ document_controller<br/>/ admin?}
    D -->|No| E[Reject 403]
    D -->|Yes| F[completion.void user reason<br/>sets is_voided=true<br/>voided_at, voided_by, void_reason]
    F --> G[Audit log row]
    G --> H{Part already<br/>past this step?}
    H -->|No| I[Next advancement attempt<br/>blocks via gate]
    H -->|Yes| J["Audit-only on this part —<br/>does not auto-cascade"]
    I --> K[Operator must redo<br/>the substep]
    J --> L[QA opens CAPA + uses<br/>QualityReports list filtered<br/>by equipment / date / etc.<br/>to discover affected parts]
    L --> M[Bulk-quarantine via existing<br/>Parts.bulk_set_status<br/>or split-for-quarantine action]
    M --> N[Link affected QRs<br/>to the CAPA investigation]
```

**Key points:**
- Voiding doesn't auto-revert the part. The gate handles it next time
  someone advances.
- For parts already past the step, voiding produces an audit row only;
  containment is a QA-driven CAPA investigation, not an automatic
  cascade.
- Discovery of affected parts happens through the **QualityReports list
  page**, filtered by equipment + date range (or whatever the void
  reason scopes against). Every QR carries the part, the machine, the
  operator, and the timestamp via the M2M-with-role through tables —
  the data is there; QA queries it through the existing list view.
- The CAPA is the system of record for the containment investigation,
  with affected QRs linked as `affected_items`. Bulk-quarantine of
  identified parts uses existing tooling
  (`Parts.bulk_set_status` or split-for-quarantine).

---

## 11. Sampling ruleset supersession (AQL escalation / fallback trigger)

When QA changes the active sampling regime — AQL switches from Normal to
Tightened after consecutive failures, or an engineer publishes a new
ruleset version — existing decisions get superseded.

```mermaid
flowchart TD
    A["Trigger event:<br/>2 of 5 consecutive lots rejected<br/>ANSI/ASQ Z1.4 Normal-to-Tightened<br/>or engineer publishes new version"] --> B[Sampling subsystem<br/>activates new ruleset]
    B --> C[For each live SamplingDecision<br/>under the old ruleset:]
    C --> D[Re-evaluate part against new rule]
    D --> E{Outcome change?}
    E -->|No| F[Leave decision as-is]
    E -->|Yes| G[Mark old SamplingDecision<br/>superseded_by = new]
    G --> H[Write new SamplingDecision row<br/>ruleset_version bumped]
    H --> I{Part still at the step?}
    I -->|Yes| J[Operator sees the substep<br/>as required<br/>next advancement attempt blocks]
    I -->|No| K["Part already advanced —<br/>audit shows retroactive selection"]
    K --> L[QA decides if recall warranted<br/>manual NCR opening]
```

**Key points:**
- Append-only. No decision row is ever updated in place.
- Retroactive selection on a part that already advanced is a QA
  conversation, not an auto-NCR.

---

## 12. What does NOT happen (the negatives)

These are common over-engineerings we explicitly avoid.

```mermaid
flowchart TB
    subgraph A [What does NOT happen]
        A1["❌ Substep submit fires Celery task"]
        A2["❌ Batch seal cascades to next step's advancement"]
        A3["❌ Out-of-spec auto-opens NCR for non-inspection captures"]
        A4["❌ Operator dispositions an out-of-spec finding"]
        A5["❌ Quarantine status auto-splits the part from cohort"]
        A6["❌ PENDING sampling decision blocks at non-terminal steps<br/>(it DOES block at is_terminal=true to force reconciliation)"]
        A7["❌ System auto-creates a batch when first BATCH substep fires"]
        A8["❌ Split-merge re-joins a part to its original cohort"]
        A9["❌ Voiding a completion auto-rolls back the part's step"]
        A10["❌ Force advance happens without permission + audit"]
        A11["❌ SamplingDecision rows get UPDATEd in place"]
        A12["❌ Expedite is modeled as a split (use WO priority instead)"]
    end
```

---

## 13. The audit-checklist

Use the boxes below to verify implementation matches the flow charts.

### Currently over-built (Celery + cascades that shouldn't exist)

- [ ] `Tracker/services/mes/advancement_tasks.py` — Celery task. **Delete.**
- [ ] `submit_substep` fires `fire_for_part` (advancement_tasks). **Strip.**
- [ ] `seal_batch` fires `try_advance_lot_task.delay(...)`. **Replace with
  synchronous `try_advance_lot()` call inside the seal request.**
- [ ] `split_part_from_lot` fires `fire_for_part`. **Strip; advancement
  happens synchronously in the split request via direct
  `try_advance_lot()`.**
- [ ] `approve_step_override` fires `fire_for_part`. **Strip.**
- [ ] `try_advance_lot` recurses into next-step advancement. **Remove —
  next step waits for its operator.**

### Currently under-built relative to flows

- [ ] **Flow #2:** Operator runtime's "Complete step" doesn't actually run
  the gate or advance. `handleCompleteStep` only submits captures.
- [ ] **Flow #3:** Out-of-spec capture doesn't show an operator-facing
  toast.
- [ ] **Flow #9:** New blocker #8 (PENDING SamplingDecisions at
  `Step.is_terminal=True`) isn't implemented. Required to force
  pre-shipment reconciliation of LAST_N_PARTS / EXACT_COUNT decisions.
- [ ] **Flow #10:** No QA-side void affordance in the UI.
- [ ] **Flow #11:** No supervisor-side review UI for superseded /
  retroactively-selected decisions.

### Aligned with flows

- [x] **Flow #1:** Substep submit writes captures + completion, returns
  inline result. N/A validation at API boundary.
- [x] **Flow #4:** Split mechanism reason-coded, audit-logged, one-way.
  `PartSplitReason` enum trimmed to QUARANTINE / REWORK / SCRAP — expedite
  goes through WO priority, not a split.
- [x] **Flow #5:** Rework split routes to `rework_target_step`, bumps
  `visit_number`.
- [x] **Flow #6:** Force advance perm-gated on WO Control page.
- [x] **Flow #7:** One BatchExecution per WO invariant; multi-WO oven
  cycles produce N BatchExecution rows.
- [x] **Flow #8:** SamplingDecision write logic correct per rule type.
  DESELECTED substeps show "Not in sample" badge (defensible for IATF
  audit; reversed earlier hide-entirely decision).
- [x] **Flow #9:** Gate blocker order is correct (#1 quarantine → #7
  substep gate → #9 override).
- [x] **Flow #10:** Containment workflow uses existing QualityReports
  list filtering + CAPA, not an auto-cascade.
- [x] **Flow #11:** SamplingDecision append-only with `superseded_by`
  chain. AQL switching trigger documented per ANSI/ASQ Z1.4 (2 of 5
  lots rejected → Tightened).

---

## 14. Deferred items (known, not in this push)

Features and behaviors that the spec acknowledges as real customer needs
but are deferred to future pushes. Pulling these into the current
advancement-engine work would muddy scope.

| Item | Why deferred |
|---|---|
| **OOS operator reason-code prompt** at capture time (operator picks gauge-suspect / setup / material / unknown + continue/re-measure/stop-line). | Waiting for real customer pull before building. Current behavior is silent flag + QA queue. |
| **Pre-capture gauge calibration check** — block measurement submit when the equipment binding has an expired calibration. | Real concern (IATF §7.1.5.2) but a separate calibration-gating push. Existing `EquipmentUsage` machinery captures the data; enforcement at submit is the gap. |
| **Part reclassification / substitute PartType** (reman teardown finds the wrong variant). | Reman-specialized feature. Belongs in a focused reman push alongside R5, not the DWI/advancement push. |
| **SPC analytics reading both `StepExecutionMeasurement` and `MeasurementResult`** so process-data captures drive Cpk / run rules / AQL escalation. | Analytics-layer work; current capture model already records the data correctly. |
| **End-of-shift handoff UI, andon / line-stop, kanban / pull signals**. | Operational features outside DWI scope. Most belong in dispatch / scheduling pushes. |
| **External integrations** — ERP confirmation (CO11N etc.), label printing, andon broadcast, notification fan-out. | Integrations are their own feature track; async observer design belongs there, not in the advancement-engine doc. |
| **Sampling rule evaluators as polymorphic classes** — replace the `rule_type` if-ladder in `sampling_decisions._evaluate_rule` with a strategy-pattern hierarchy (`EveryNthEvaluator`, `FirstNEvaluator`, etc.) and a `RulesetEvaluator` carrying AQL switching state. | Land with the AQL push (which adds `AQL_ATTRIBUTE` rule type + the Normal/Tightened/Reduced switching state machine — the natural forcing function for the refactor). Doing it before AQL is cleanup without a customer-pull reason. |

---

## 15. How the pieces work together

The previous sections describe individual flows. This one shows the
modules and how they interconnect — useful when adding a new trigger,
debugging a stuck lot, or onboarding someone to the codebase.

### Architectural picture

```mermaid
flowchart TB
    subgraph triggers ["Operator / Supervisor / QA actions (viewset layer)"]
        T1["Operator: Complete step"]
        T2["Operator: Seal batch"]
        T3["Supervisor: Split part<br/>(quarantine / rework / scrap)"]
        T4["QA Manager: Approve StepOverride"]
        T5["Production Manager:<br/>Force advance (emergency)"]
        T6["QA: Mark QualityReport FAIL<br/>(may trip AQL escalation)"]
    end

    subgraph services ["State-changing services"]
        S1["submit_substep<br/>(operator_capture.py)"]
        S2["seal_batch<br/>(batch_lifecycle.py)"]
        S3["split_part_from_lot<br/>(splits.py)"]
        S4["approve_step_override<br/>(step_override.py)"]
    end

    subgraph engine ["Advancement engine (advancement.py)"]
        E1["try_advance_lot<br/>(THE central entry)"]
        E2["Gate evaluation<br/>(Steps.can_advance_from_step)"]
        E3["Bounded sync cascade<br/>≤10 depth"]
    end

    subgraph sampling ["Sampling subsystem (sampling_decisions.py)"]
        SP1["evaluate_substep_sampling<br/>(writes on step entry)"]
        SP2["reconcile_pending_decisions<br/>(at terminal step blocker)"]
        SP3["supersede_on_ruleset_change<br/>(AQL fallback trigger)"]
        SP4["evaluate_rule<br/>(pure: rule × part → outcome)"]
    end

    subgraph tables ["Database — shared state"]
        DB1[("SamplingDecision<br/>append-only<br/>superseded_by chain")]
        DB2[("SubstepCompletion<br/>VoidableModel<br/>na_reason_code")]
        DB3[("BatchExecution<br/>sealed_at NOT NULL<br/>= valid coverage")]
        DB4[("Parts + StepExecution<br/>split_from_cohort<br/>visit_number")]
    end

    %% Trigger → service / engine
    T1 --> E1
    T2 --> S2
    T3 --> S3
    T4 --> S4
    T5 --> E1
    T6 --> SP3

    %% Services chain into engine
    S2 --> E1
    S3 --> E1
    S4 --> E1

    %% Engine internals
    E1 --> E2
    E1 --> SP1
    E1 -.terminal step + PENDING.-> SP2
    E1 -- on cohort advance --> E3
    E3 --> E1

    %% Sampling internals
    SP1 --> SP4
    SP2 --> SP4
    SP3 --> SP4

    %% Reads / writes
    E2 -.reads.-> DB1
    E2 -.reads.-> DB2
    E2 -.reads.-> DB3
    SP1 -.writes.-> DB1
    SP2 -.writes.-> DB1
    SP3 -.writes.-> DB1
    S1 -.writes.-> DB2
    S2 -.writes.-> DB3
    E1 -.writes.-> DB4

    %% Substep submit does NOT trigger advancement
    S1 -.NO direct call.-> E1
```

### Reading the diagram

**Layers (top to bottom):**
1. **Triggers** — viewset actions a human (or QA-side automation) initiates
2. **Services** — state-changing units that own a single concern (capture, seal, split, approve)
3. **Engine** — `try_advance_lot` is the single advancement entry; everything else delegates to it
4. **Sampling subsystem** — owns rule evaluation logic + decision writes
5. **Database** — the four tables that carry the engine + sampling shared state

**Arrow types:**
- **Solid arrow** — direct function call
- **Dotted arrow** — database read/write
- **Dotted with label** — conditional call (e.g., only at terminal step with PENDING)

**Key non-relationships (deliberately absent):**
- `submit_substep` → `try_advance_lot`: NO direct call. Substep captures don't trigger advancement. Operator's "Complete step" is the trigger. (Marked with the dotted "NO direct call" line.)
- Sampling subsystem → Engine: never. The engine calls into sampling; sampling never calls into the engine.
- Engine → ruleset lifecycle: never. AQL escalation is triggered by QR FAIL writes, not by advancement.

### The contract between engine and sampling

The engine and sampling subsystem share two thin contracts:

1. **Data contract** — the `SamplingDecision` table. Engine writes via the sampling subsystem; engine reads in the gate. Append-only with `superseded_by` chain for audit.
2. **Function-call contract** — engine calls three sampling functions at specific lifecycle moments:

| Lifecycle moment | Engine action | Sampling function |
|---|---|---|
| Part enters a step (incl. cascade) | Triggers per-substep decision write | `evaluate_substep_sampling(step_execution)` |
| Part reaches `is_terminal=True` with PENDING decisions upstream | Triggers reconciliation before allowing shipment | `reconcile_pending_decisions(work_order, step)` |
| QualityReport FAIL trips AQL switching rule | (engine is NOT involved) | `supersede_on_ruleset_change(old_ruleset, new_ruleset)` triggered from the QR FAIL save path |

The sampling subsystem owns the rule math (`evaluate_rule(rule, part, context) → outcome`) and the ruleset lifecycle (active / inactive / fallback chain). The engine doesn't know about rule types; it just gets back SELECTED / DESELECTED / PENDING via `SamplingDecision.outcome`.

### What "adding a new trigger" looks like

If a new operator/supervisor action could plausibly affect lot advancement, the integration is:

1. Implement the state-changing service (or use an existing one).
2. The service's caller (usually the viewset action) calls `try_advance_lot(work_order_id, step_id, tenant_id)` synchronously after the state change.
3. The advancement result (advanced / blocked / no-op) gets returned to the caller in the same response.

You do NOT:
- Fire a Celery task
- Emit an event
- Subscribe to a signal
- Add a hook inside the service that auto-chains advancement

Caller orchestrates; the engine is the orchestration target.

### What "debugging a stuck lot" looks like

When a lot won't advance, the diagnostic walk is:

1. Call `Steps.can_advance_from_step(step_execution, work_order)` — returns the blocker list.
2. For each blocker, identify the source table:
   - "Substep 'X' not completed" → missing `SubstepCompletion` row, or `is_voided=True` on the existing one
   - "Sampling decision missing" → bug; `SamplingDecision` row absent (the entry hook didn't fire)
   - "Batch substep '...' requires sealed batch" → no `BatchExecution.sealed_at` for the cohort
   - "N/A no longer valid" → substep had `is_critical` flipped to True after the N/A row was written
   - "PENDING reconciliation needed" (terminal blocker #8) → `reconcile_pending_decisions` hasn't run, or PENDING rules can't auto-resolve
3. Fix the data or take the appropriate action (record completion, seal batch, supervisor reconciliation).
4. Re-trigger advancement via the original trigger (Complete step, or supervisor Force-advance for emergency cases).

The diagram makes the "where do I look" question answerable: read the gate's blockers, follow the dotted-read arrows to the table holding the offending row.
