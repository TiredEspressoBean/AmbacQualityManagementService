# Role Workflow Audit

**Status:** live and maintained. **140 rows across 11 roles.** Most are walked
against the running application and dated. Rewritten 2026-10-19: everything
that is still true was kept, each finding's history was cut down to its current
state, and fixed findings went into a one-line index (see [Resolved](#resolved)).
Git holds the full narrative. This is the one file in `Documents/` that is *not*
design history. Every other file there is stale, so don't trust it as current
state.

**Started:** 2026-10-06 · **Last full pass:** 2026-10-19

!!! important "Using this file is how it stays true"
    **Flip the row in the same change that does the work.** The Docs column went
    stale twice because work landed and nobody came back to the row. A ledger
    nobody closes out is worse than none, because people believe it. A sweep
    makes a column true *on a date*; only flipping the row with each change keeps
    it true. If you depend on a row, re-check it.

## How the audit works

The help docs grew subsystem by subsystem. That made them accurate about
features and silent about **jobs**. This audit works the other way round:

1. **Abstract.** What must a person in this role be able to do, in any
   QMS/MES/APS/DWI?
2. **Docs.** Is it documented, and where?
3. **Code.** Does the application do it?

So a gap can be a doc gap, a code gap, or both.

**Rules for deriving and reading rows:**

- **A gate appears twice.** Write an oversight role's list from the gates its
  doers reach. The doer hits the gate in one row, and the overseer clears it in
  another. Writing the list from subsystem nouns ("manage calibration") produces
  rows that cannot be audited.
- **New manufacture is the default; reman is secondary.** Reman rows are numbered
  `R1, R2…` and stay out of the main sequence, by decision. They are extra work
  on existing roles, never a role of their own.
- **The unit of work is a batch, with per-unit records.** Two early rows dissolved
  because they assumed one operator, one part and one long operation. Before
  auditing a row, check that it doesn't assume a unit of work this shop doesn't
  have.
- **`C` rows** are cross-cutting or candidate workflows. A candidate that comes
  back "nothing anywhere" proves only that the workflow is **not built**, never
  that it is not needed.
- **Only code settles the Code column.** Design docs in `Documents/` record past
  intent. Use them to find rows to check, never as evidence that something exists.

## Status key

| | |
|---|---|
| ✅ | Documented and supported |
| 📄 | Supported, not documented |
| 🚧 | Partly supported |
| ⚠️ | Supported, with a caveat worth reading before relying on it |
| ❌ | Not supported |
| — | Not applicable: out of the product's bounds by design, or deliberately another role's job. **Not a gap.** |
| ? | Not yet checked |

| Column | Question |
|---|---|
| **Docs** | Is there a page that explains it? |
| **Code** | Does the application do the job? |
| **Demo** | Can it be **shown** on seeded data? |
| **Training** | Is there a module where someone is taught to **do** it? |

A row can be ✅ on Code and ❌ on Demo. The application does the job, but nobody
can watch it happen, so it can't be taught. Don't use ⚠️ for that: ⚠️ means the
capability itself has a catch. **Training** is `?` on every row until the
seed/training arc rebuilds the tracks. Set Demo by reading the row, not by
pattern-matching it.

## Scope

**Eleven roles:** Operator, QA Inspector, Shift Lead, Receiving, Shipping,
Scheduler (= Planner; the presets merged them), Production Manager, QA Manager,
Engineering, Purchasing, Document Controller.

**Not covered, by user decision:** Administrator (also out of the seed/training
arc), Auditor and Customer. The Customer portal was probed, not walked; its open
findings are under [Open findings](#open-findings).

Engineering and Purchasing were walked as Tenant Admin, because no demo account
holds either role alone. Their permission boundaries come from
`Tracker/presets.py`, not from observation.

---

## Operator

The unit of work is a **step**, worked as a batch with a record per unit.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what to work next, and claim it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The operator home (Up next / Then / In progress), scoped by station. A released work order's untouched first step reaches the queue (fixed 2026-10-21; it used to need a start from the WO page). A first start records the operator (fixed 2026-10-21). `WO-OPS-01` at Machining is the exhibit. |
| 2 | Identify the right physical unit (scan) | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | A serial opens its work order with **Start work on parts** open and the part ticked. |
| 3 | Prove qualification before starting, or be authorised | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Refused with what's missing (*Dimensional Inspection, level 1, needs level 2*), then a supervisor signs in on the operator's screen with a reason. Walked on `WO-OPS-02` at Body Inspection. |
| 4 | Follow the instruction and record as you go | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Inline limits and an **In spec / Out of spec** badge; a value corrected before **Complete step** never becomes a nonconformance (walked: 6.02 → 6.004 left only a PASS report). An overdue gauge is accepted with a warning to tell QA. |
| 5 | Have the lots I used recorded against the unit | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Drawn from stock on completion (oldest lot first) and recorded against the unit; nobody scans a lot. The build BOM buys the nozzle and control valve as parts, by the lot. |
| 6 | Report a problem mid-step | ✅ | ❌ | — | ✅ | 2026-10-21 | **Not built, by decision (2026-10-21).** *Can't run this?* and *Report a problem* are previews ("the blocker aggregate isn't wired yet") and route nothing. The operator goes to their lead; the track says so. This row was wrongly marked as routing to named owners. |
| 7 | Work a batch another operator started | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The reassignment gate names the owner (*currently assigned to Dave Wilson*); a supervisor authorises. Batch captures once for the load, then **Seal batch** moves the load. A batch signature 500'd until 2026-10-21 (fixed). `WO-OPS-02` is the exhibit. |
| 8 | Finish and move the unit on | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The lot advances, not the part: "Recorded — moves on with its lot once … are done" until the last lot-mate, then "lot advanced (n parts moved)". |
| 9 | Account for time | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | Clock in/out/break/lunch writes a `SHIFT` TimeEntry (walked as Mike: *On break* → **End break** → **Clock out**). Casey approves on **Operator Hours**: per-entry **Approve** or **Approve all**, her own rows *Your time* (115 → 114). Operator track module 1, Shift Lead module 7. **⚠️:** **Clock out** has no confirm while a step is *Running*. Seed nit: hours dated 10/15 are booked to teardown WOs named `TEARDOWN-20261022-…`. |
| 10 | See what I am qualified for, and what is expiring | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | *My Training* on the Training dashboard. Manager tiles still show to operators; the API refuses them. |
| 11 | Read and acknowledge shift notes and notifications at clock-in | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Must-acknowledge notes open in a dialog at clock-in that can only be left by acknowledging; the ack (name, time) also reads the note's notification. Casey's two notes are the exhibit. |
| 12 | Be called over as the second person on someone else's gate | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Both gates (training override, reassignment) take a supervisor's own email, password and reason on the operator's screen. |
| R1 | Grade a component at teardown, with the part in your hand | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | At **Disassembly**: every expected component graded (A/B serviceable, C recondition, Scrap) or marked missing, recorded under the operator. `CORE-240220-0003`/`0004`, received and signed off, are the exhibit. |
| R2 | Raise a finding at the bench when a reused part fails later | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked on `CORE-240210-0007` at Nozzle Inspection: visual result **Needs repair** (REPAIR, built 2026-10-21), nozzle found worse at C, *Complete step* → awaiting QA sign-off; the pre-approved NZL-RECON applied at once, no disposition; after the inspector's sign-off the core went to Nozzle Recondition. A finding needing approval (scrap) waits for the lead instead (Shift Lead R1). Track R3. |
| R3 | Work a rebuild step whose scope was only settled this morning | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Scope is derived on read and writes nothing. Walked as the track's R2 on `CORE-240210-0007` at Cleaning: a held unit is greyed out of the load; sealing a load whose lot-mate is held reports *the lot waits for CORE-240212-0009 (on hold). Split it from the lot*; lock-step is deliberate (2026-10-21), and the lead's split moves the waiting unit on. Two fixes landed for this (2172b3d): the wait used to report itself as *moved*, and a split didn't release the waiting unit. |
| C1 | Pull one unit out of a batch and send it back for rework | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | WO control > **Rework**: a reason is required (decided 2026-10-21); the part is split and routed now, a FAIL report records why, and an unassigned Rework disposition opens for QA (or joins QA's, if they got there first). |
| C2 | Get an erroneous record corrected | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Operators see no **Void**; QA voids the substep completion with a reason, the step reopens, and the work is captured again. Measurements and quality reports are corrected by a new record, by decision. |
| C3 | Work when the terminal or scanner is down, and catch up after | ✅ | — | — | ✅ | 2026-10-21 | **Settled intent.** There is no offline mode, and `entered_at` is not backdatable, because it is traceability evidence. The paper traveller is the fallback. |

## QA Inspector

The verdict is **derived**. A measurement crossing its spec quarantines the part,
writes a FAIL quality report and opens a disposition. There is no Pass/Fail
button: *the spec is the judge.*

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Read the home page | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | First pieces waiting · inbox chips (Receiving / OSP returns / In-process / QA sign-off) · My quality actions · **Unassigned dispositions** with *Take it* · Your gauges. |
| 2 | Scan to navigate | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | A serial opens its work order with **Start work on parts** open and that part ticked (a quarantined or held part opens unticked). Work order, lot and location scans open those. |
| 3 | Receiving inspection, and clear the paperwork holds | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | *Accept lot / Reject lot*. Paperwork holds clear inline; judgement holds need a quality manager. `RCV-MAT-HOLD` is the exhibit. A partial reject (`RCV-MAT-0004`) splits the bad pieces into a rejected child lot with a disposition and accepts the rest; an inspector's whole-lot reject (`RCV-MAT-0003`) becomes a request that holds the lot until a QA manager confirms or declines. The verdict counts the inspector's own failing readings; Accept is disabled on REJECT. |
| 4 | First-piece buy-off | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | Both routes (runtime banner, WO Control *First piece waiting on QA*) offer **Sign off / Fail / Waive** through one dialog that shows the first piece's readings. Separation of duties: whoever signed the first piece's substeps is refused. Exhibits: `WO-QA-INSPECT-01` (pass), `-03` (Sarah ran it: her buy-off is refused), `-04` (fail), `-05` (waive). A fail quarantines the first piece and opens an unassigned disposition with the reason; WO Control then shows *First piece failed — run held* with **Start a new first piece**. When the logged-in inspector signed the first piece, the dialog says so up front and takes a second inspector's sign-in; the buy-off is recorded under the co-signer (`inspected_by`) with the caller as `performed_by`. |
| 5 | A sampled in-process inspection | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | Answers *"why this part?"*. The plan is generated, and each part's history lists its **Sampling decisions**. `INJ-QA-INSPECT-004`: *Selected by every 4th part*, with a **Sample** badge in Start Work. |
| 6 | OSP return inspection | ✅ | ✅ | ✅ | ✅ | 2026-10-06 | One queue for purchased lots and OSP returns, with a **Source** column and one runtime. |
| 7 | An out-of-spec reading quarantines the part and raises its disposition | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | An inspector's explicit FAIL on the result field runs the same consequences (fixed 2026-10-20; walked on `INJ-QA-INSPECT-015`). One handler (`quality_report.on_report_failed`) runs the FAIL consequences on the move into FAIL: created at FAIL, edited to FAIL, or resolved to FAIL by DWI findings. Each quarantine writes the part's history with the actor. Not walked. |
| 8 | Work the disposition — **the decision needs a co-sign** | ✅ | ✅ | ✅ | ✅ | 2026-10-06 | An approver authenticates **on the inspector's screen**, and the decision commits under their name (`decision_authorized_by`). The best screen in the product. |
| 9 | Close the disposition — this one is yours | ✅ | ✅ | ✅ | ✅ | 2026-10-07 | The refusal names everything missing in one message: no decision, and containment needed on CRITICAL/MAJOR. |
| 10 | Re-inspect after rework, history first | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | `INJ-QA-INSPECT-013` failed Flow Calibration, was decided REWORK on Maria's co-sign and split to Rework. Completing the Rework step's own inspection closes the disposition, and the part re-enters Body Inspection. |
| 11 | Work a CAPA task; author a verification plan; initiate one for a pattern | ✅ | ✅ | ✅ | ✅ | 2026-10-06 | **Add Verification** records a *plan*; **Complete Verification** records the *outcome*, which needs `verify_capa`. |
| 12 | Check a gauge's calibration before using it | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | *Your gauges*: a gauge used in the last 7 days that is due within 7. An out-of-service or failed gauge is refused at capture and greyed in the picker (`Micrometer MIC-2`). An overdue one is recorded with a warning to tell QA (`Micrometer MIC-1`, Machining's Body OD). |
| 13 | Read a finished record and narrate it backward | ✅ | ✅ | ✅ | ✅ | 2026-10-15 | The per-serial **Traveler**. Red flag to teach: QUARANTINED or SCRAPPED with no report or disposition behind it. |
| 14 | Mark where a defect is on the 3D model | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | Every annotation carries a quality report. A defect type that needs one blocks closing the disposition, and **Go to Annotator** opens scoped to its reports. Exhibit: `INJ-QA-INSPECT-015` (Hole blockage, quarantined, disposition unassigned). Walked by hand: markers on the report clear the annotation blocker. The severity picker shows a saved annotation's `LOW` raw beside *Low* (with -4f). |
| R1 | Accept or reject a harvested component into stock | ✅ | ✅ | ✅ | ✅ | 2026-10-07 | `/reman/components`. Accepting reserves a part for its customer's core. No success toast. |

Rows removed on purpose: *know the sample size* (generated, so part of 5);
*record measurements* and *confirm calibration* (steps inside an inspection);
*inspect a core on arrival* (not inspector work: core lots never enter the queue);
*put a lot on hold* (met inside 3; releasing one is a manager's act).

## Shift Lead

The unit of work is the **shift**.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See the shift's state at a glance | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Landing picker → Shift Lead. Biggest fire, work orders, jobs going late, on hold, Needs attention (now incl. *Finding to decide* and *Awaiting customer authorisation*), OSP, training. Track module 1. |
| 2 | Reassign work when someone cannot run it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Board › People › task › **Reassign**. The picker offered every tenant user, a customer included, until 2026-10-21; now the dispatchable crew narrowed by qualification, and the API refuses anyone off the crew. Track module 2. |
| 3 | Cover an absence or no-show | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Same surface. An **empty operator picker is a training problem wearing a scheduling costume.** Track module 2: Dave is off, so read the matrix for who covers, then reassign on People. |
| 4 | Unblock a stopped job | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Control Center **Exceptions**: quarantine, CAPA and downtime items with *Impacts N WO*. Findings to decide surface on the home's Needs attention, not here. Track module 3. |
| 5 | Authorise an unqualified operator, on the record | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Supervisor signs in on the operator's screen with a reason. **Training Overrides** review needs the audit-log permission (QA Manager), not the lead's, by design. Writing the record walked (the trainer picker was stuck on the trainee's search until 2026-10-21). Track module 6. |
| 6 | Triage a quality event without escalating everything | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Exceptions: source, severity, age, owner, *Open only*, bulk resolve. |
| 7 | Watch what is going late | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | *Jobs going late*, plus **Overdue / Due today** filters, plus the overdue badge on Tracker cards. |
| 8 | Hand over to the next shift | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Shift notes: audience by role (Customer/Auditor refused since 2026-10-21), High priority, Requires acknowledgment, acknowledgement counts. The seed writes two of Casey's. Track module 7. |
| 9 | See who is qualified for what | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | The training matrix. It reports **role** gaps while the start gate reads **step** requirements, so a role gap doesn't block work. Read by hovering cells; the footer counts L3+ cover per skill. Track module 2. **⚠️:** it lists all 14 users as *Operators* (auditor, buyer, dock staff included), and some cells' tooltips give only *Expires 2026-10-29*, without skill or level. |
| 10 | Escalate what the shift cannot solve | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **Report exception** → Downtime (machine, category, reason) starts now and lists in Exceptions; **Resolve** records end, reporter and resolver. Gauges/tools with *Track downtime* off are excluded. Track module 3. |
| 11 | Put a work order on hold, resume it, cancel it, or short-close it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Hold banner (reason, notes, placed by/at); Start Work disabled with the reason; Resume confirms and, for QUALITY/TOOLING holds, requires *What resolved it* (decided 2026-10-21); Hold history keeps each cleared hold. Track module 4. |
| R1 | Decide a pending finding — apply or dismiss | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Exhibit `CORE-240214-0010` (seeded bd87899): a scrap finding recorded at Nozzle Inspection waits for the lead. Needs attention links to its rebuild plan; Apply on a scrap confirms; the plan re-resolves to NZL-REPLACE · Needs approval. Track R1. |
| R2 | Request customer authorisation for over-and-above | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **Authorise…** (core page or WO Cores card) lists the codes and findings, **Send for authorisation** → *Awaiting customer authorisation*. Refuses when nothing exceeds the sold level. Track R2. |
| R3 | Decide a torn-down unit's exit: rebuild, harvest, or return | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `CORE-240215-0006`: Plan rebuild / Rebuild to stock / Harvest for parts (confirms: consumed, can't be undone) / Scrap (reason). Track R3. |
| C1 | Jump a job to the front, with a reason | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Priority → Urgent refused without a reason; *Priority changes* lists it with name, time and reason. **Residual:** a CSV import or the master workbook changes priority without a reason. Track module 5. |
| C2 | Void an operator's bad record | ✅ | — | — | ? | 2026-10-15 | **Not this role, by design.** Voiding is QA Inspector, QA Manager and Tenant Admin. A lead escalates. |
| C3 | Take a machine out of service and re-plan around it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | An out-of-service or uncalibrated machine drops out of the solver's affinities. The lead records the downtime (track module 3); re-solving is the planner's, by design. |

The **persona picker** lets one person hold several roles: `casey.dual` is an
inspector by day and a shift lead when covering. Landing is a persisted choice.
Supervisory preview lets a lead view a surface without holding that role. It
grants the view, not the permissions.

## Receiving

Walked 2026-10-21 as Luis Ortega (`luis.recv`), a seeded Receiving user. The seed now books lots in as Luis, chases as Priya and raises qualifications as Priya; inspections stay Sarah's.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is expected | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Materials **On order / Late**. An expected receipt is a `MaterialLot` that hasn't arrived, with PO, line, promised date and chase fields. |
| 2 | Receive a delivery | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | A new lot number and heat number, and the CoC or packing slip photographed. The lot is routed to inspection automatically. |
| 3 | Verify against the paperwork | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The unified **Incoming Inspection** queue. |
| 4 | Handle a short or over delivery | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | *"20 fewer than the 200 on order. What does the packing slip say?"* **More coming** keeps the remainder on order; **That's all** stops planning on it (the PO line is closed in the ERP). |
| 5 | Resolve holds | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | *Held for N reasons — each clears on its own.* Paperwork holds self-clear; judgement holds need a quality manager. `RCV-MAT-HOLD`: the heat number cleared its hold and the supplier hold stayed, with no release button for Receiving. |
| 6 | Reject and return | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Reject opens a disposition. **Ship back** takes an RMA and prints the RTV sheet, and the replacement delivery is created automatically. The lot is *Returned — not scrapped*. A whole-lot reject needs `reject_whole_lot` (QA Manager, Tenant Admin); without it, the reject becomes a request. |
| 7 | Put away and find again | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `/production/locations`, with nesting and **Move…** (partial moves allowed). Every movement is in the ledger. |
| 8 | Count stock | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | A blind count, then apply. Applying needs `apply_cyclecount` (a lead's). `CC-2026-0001` is seeded submitted but not applied. |
| 9 | Chase a late delivery | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **The first promise is kept:** a supplier can't improve their on-time record by re-promising, and the screen shows it. Chasing is Purchasing's: taught in the Purchasing track, module 3; the Receiving track reads the card only. |
| 10 | Hand receipts to the ERP | ✅ | — | ✅ | ✅ | 2026-10-22 | **Not a feed, by design.** Glovia is bridged by a person. UQMES owes the document: **Receipts for ERP** on Materials. Walked as Luis: *2 ready to post · 6 awaiting a decision* → **Download** → **Mark 2 as posted** → 0 ready. Track module 8. |
| 11 | Stage and kit material to the bench for the next shift | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `/production/staging`. **Confirm** and **Took another**. Trap: the 8 h window reads *"Nothing scheduled"* on a plant holiday. |
| R1 | Receive a core | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The **Receive Core** form, then **Start teardown** opens the check-in, an authored DWI step: scan the identity band, photograph it as received, grade it, sign. *"Don't clean yet"* keeps the evidence (ISO 9001 8.5.3). |
| R2 | Receive a bulk core lot and identify units from it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | A counted delivery with no serials. **Identify and next** works down a pallet. Exchange cores by definition. |

## Shipping

Walked 2026-10-21 as Rosa Kim (`rosa.ship`), a seeded Shipping user.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is ready | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `/production/shipments`: *"Invoicing stays in your ERP."* Ready to ship / Shipped, grouped by order. |
| 2 | Confirm it passed and is complete | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **The route's Ship step is the queue.** Shipping completes that step through `advance_part_step`, so the 8.6 release gate runs. |
| 3 | Create the shipment | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Select units → **Ship …** → a shipment number. |
| 4 | Produce the paperwork | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Packing list, CoC, Edit paperwork, Void…, and the history. |
| 5 | Ship partially | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Per-unit selection; the rest keep waiting. |
| 6 | Record carrier and tracking | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Tracking can be added later. |
| 7 | Undo a mistake | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | A void is for a shipment recorded by mistake: the parts return to their Ship step or to stock. *"Goods that went and came back are a return, not a void."* |
| 8 | Return customer property | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Independent of any ship step. Lot-aware, so partial returns work. `MaterialLot.owner` is ringfenced throughout (8.5.3). |
| 9 | Know whether we are on time | ✅ | ✅ | 🚧 | ✅ | 2026-10-21 | On-time %, falling back to the WO's expected completion, with "N not measurable" shown. Read in Shipping module 1 (*On time, last 90 days: 100% (2 of 2)*). **Demo 🚧:** the fallback never fires on seeded data (left: low value). |
| 10 | Send parts out to a subcontract vendor, and record them back | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `OutsideProcessPanel`. The return inspection is a step execution, and **Accept return** advances the parts. A step naming a **Special process** refuses an unqualified vendor. |
| R1 | Return a rejected core to its owner | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | `return_core_to_customer` needs REBUILT or DECLINED and refuses an exchange unit. **Demo (fixed in seed):** `CORE-240215-0011` (Midwest Fleet, `ORD-2024-0044`) is torn down on its own WO, found with a cracked nozzle, and declined by the customer (recorded by Jennifer with Tom's reference). Shipping lists it as *Scope declined — to be returned unrepaired*, and shipping it sets RETURNED_UNREPAIRED with the shipment as the return reference. Track section R. |
| R2 | Ship a rebuilt unit with the paperwork | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | A return is a `CustomerShipment` (`ac85a3e`): **Return** on the Cores card opens the ship dialog, and the Shipping board lists finished reman units under their owner. Packing list always; CoC when the customer wants one with every shipment. Exchange stock on an order ends *Shipped on exchange*. No printed as-built sheet, by decision: it stays an in-system record. **Demo (fixed in seed):** `CORE-240217-0013` (Northern Trucking, `ORD-2024-0047`) is walked through its whole rebuild by ops_walk (Mike works it; Sarah runs the checks and Maria signs them off; nitride out and back; Reassembly records its own components), ending *Rebuilt — ready to return* on the board. Walked as Rosa: shipped, then RETURNED with the shipment as its reference; packing list and CoC both download. Track section R. **⚠️ (CoC, reported):** signed by the shipper as *Quality*; lists the core number, not the customer's serial; reads *manufactured* for a rebuilt unit. |
| C1 | Export-control screening before anything leaves | ✅ | — | — | ? | 2026-10-14 | **Not a target.** Export control is vestigial. The machinery is kept accurate in case it's revived. Don't build on it, and don't create non-US accounts. |

## Scheduler

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Produce a schedule | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | Walked as Sam (Planner persona, seeded c1c1db2). Solve runs on Celery; the seed solves. **⚠️:** a re-solve from the board reports *within ~100%* and much worse lateness than a cold solve (159k vs 44k); lead: frozen-window soft pins dominate the objective and the reported gap (experiment approved 2026-10-21). Tracks say to judge by late orders, not the gap. Track module 3. |
| 2 | Find out why something is not on it | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked under manual release: on hold, not released (*Release it from the planning queue*), no units created yet, added since the last solve, waiting to ship. Track module 2. |
| 3 | Dispatch people | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | Dispatch reports coverage (*Assigned 224 of 243 operations · 19 have no qualified operator free*). Uncovered work becomes a standing chip in the header. Track module 5. **⚠️:** runs at once, with no confirm. |
| 4 | Adjust by hand | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Pin from the task panel (*Task pinned*); the pin survived a full re-solve. Reassign limited to the crew. Track module 3. |
| 5 | React to a disruption | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Staleness flags trip on demand, part and capacity changes, not on routine step advances. It's a hint, not an auto-solve. Walked as Sam: downtime on Flow Test Stand #1 → *stale* → solve. **Found and fixed by f6 (10/22):** the solve was INFEASIBLE (Nozzle Inspection's only machine was down) and the failed result became the live plan (0 tasks). Now the plan stops before the step, *Not scheduled* lists **No machine available** with the reason, and a failed solve never replaces the plan in use. Track module 7. |
| 6 | Test a change before committing | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | **What-if** solves a draft and states trade-offs in both directions. Solves stop at a 66–99.6% optimality gap; the compare bar shows each side's **solver gap** and warns when a difference is within it. Walked: *DRAFT (what-if)*, makespan, lateness and moves vs live; **Commit draft** / **Discard**. Track module 4. |
| 7 | Get the plan to the floor | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Dispatch is the hand-off (track module 5); staging and pick sheets (module 8). The **Dispatch List** is a printable report, not an assignment surface. |
| 8 | See whether the floor followed it | ✅ | ⚠️ | 🚧 | ? | 2026-10-19 | Actuals are capture-only by design and don't re-time the plan. There is no adherence view. Needs a solve followed by movement. |
| 9 | Author non-working time — holidays, shutdowns, PTO, training | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked: Add closure → *stale — re-solve* → solve leaves the day at 0 tasks, next working day 45. Seeded closures were built in server UTC until 2026-10-21 (now plant time). Headcount counts the crew. Track module 4. |
| R1 | Schedule work whose route isn't known until teardown | ✅ | ⚠️ | ✅ | ? | 2026-10-13 | Books the nominal route and re-solves when reality diverges. **⚠️ A deliberate simplification:** reman is tree-shaped. The user is waiting for real data before designing further. |

The **frozen fence** is a soft penalty in the solver, but the board legend says
*"Frozen stays put"*. A third of the frozen tasks moved in one solve. Either the
legend or the weight should change. Open.

## Production Manager

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is at risk | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Home: *Needs attention* (awaiting authorisation, quarantine, CAPAs pending verification), quality figures, work orders most urgent first. The order book adds projected vs promised and blocked-by per order. Track module 1–2. |
| 2 | Release work | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | WO page **Release** → *Released — re-solve to plan it*; a failing check shows what's missing and **Release anyway** takes a reason. The seed now releases every active work order through the service (db431f6). *What to release* splits **Late to release** from **Released, not started** (2172b3d). Track modules 4, 6. |
| 3 | Promise a date | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked: 6 × Common Rail Injector fits by its date; 1000 is refused with the binding resources and the earliest month. An order line's **Check capacity** prefills it. Rough-cut arithmetic checked by hand (2026-10-21). Track module 3. |
| 4 | Resolve escalations | ✅ | ✅ | ❌ | — | 2026-10-21 | **Corrected 2026-10-21:** escalations are not on the Exceptions surface (its sources are downtime, quarantine dispositions and CAPAs). A visit-capped rework loop escalates by itself to its escalation step (`_check_cycle_limit`, *Visit N of M* banner); a decision point with no data is resolved by a lead's cosign in the step runtime (`resolve_step_decision`, `DecisionResolverPanel`). A capped rework loop now escalates to **MRB Review**, where the QA manager decides the disposition (QA Manager row 16, exhibit `CORE-240219-0014`, 2026-10-22). **Demo ❌:** no step sits at an unresolved decision point. Not in the PM track. |
| 5 | Balance capacity and staffing | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Capacity headline: *Crew: enough … busiest 2026-10 at 42% · Tightest skill … · 2 skills only one person can do*; the Labor row is attended hours needed vs crew hours left (the current month counted from the 1st until 2026-10-21, understating load, now from today); certified-pool rows marked **one person**. Schedule › People is occupied time per operator (lanes over-summed lot rows until 2026-10-21). The old 3,758 h vs 2,222 h claim was wrong. Track module 11. |
| 6 | Close out a nonconformance decision, and know who decides a deviation | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Accepting nonconforming product (*Use As Is* / *Repair*) is a disposition: QA decides it (`approve_disposition`), and the PM closes it (`close_disposition`). Walked on `WO-PM-MAKEUP-01`'s scrap (seeded 2026-10-21): Control Center › Exceptions › **Open disposition**, Current State → Closed, **Update Disposition**. A scrapped part's disposition isn't on Quarantined Parts (it isn't quarantined). **⚠️:** the scrapped part's step execution stays IN_PROGRESS, so the traveler shows the step running (reported). A **planned** departure is a temporary change — see Engineering 8. |
| 7 | Review OTD and throughput | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Customer OTD on Shipping and on the order book (same figure, per order line shipped against its due date, unmeasured counted). FPY and downtime on Analytics. No single throughput view. Track module 8. |
| 8 | Maintain the data planning depends on | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **Master Workbook**: a *Filled in* round trip checks as 446 rows unchanged; sheets the PM may not load (users, sampling rules, life limits) are refused per sheet. Track module 9. |
| 9 | Top up a job after scrap outruns the gross-up | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Planner-confirmed by design. The **Make-up** card on the work order page (*0/4 good · 3 alive · 1 scrapped — 1 short of 4 good*) → **Create 1 make-up part** starts one at the first step. Walked on `WO-PM-MAKEUP-01`. A WO with no parts, or ended, reports no shortfall. Track module 10. |
| 10 | Take in a customer order and turn it into work orders | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **Production › Orders** (built 2026-10-21 for this): the order book with *N unplanned*, and the order page's **Plan N** creates a work order with a part per unit on the approved process. `ORD-2024-0051` is the exhibit. Order planning used to live only on the Data Management edit form, where its buttons also saved the form (fixed 2172b3d). Track modules 2, 4. |
| 11 | See where machine time is lost | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | The **Downtime** card on Analytics: 7.8 h over 3 seeded events, by cause and by machine. No OEE, by design. Track module 8. |
| R1 | Authorise over-and-above and record the customer's answer | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked on `CORE-240212-0009` (`ORD-2024-0046`): the rebuild plan lists *NZL-REPLACE · Needs approval* with its finding; the core's **Approved…** records who answered, how and a reference → *approved, rebuild resumed*, hold cleared, answer appended to the core's notes. No price anywhere. **Gap:** the core page doesn't show which order the core was received for. Track R1. |
| R2 | Decide harvest versus buy on a rebuild kit | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | **Demo (fixed in seed):** `CORE-240216-0012`, an exchange unit released into rebuild with its nozzle scrapped at the bench. Ready to Rebuild › **Plan rebuild**: the nozzle slot proposes *Replace — recovered stock* (a grade B nozzle from `CORE-240215-0005`) against *Replace — buy*. **Change** › resolution plus a required reason › **Record decision**. Track R2. **⚠️:** a decision equal to the proposal reads *overridden*; the header keeps *1 need a decision*; the dialog prints ".."; **Continue rebuild** takes a PM into the operator runtime. Reported to f6. |

## QA Manager

Built from the gates the QA Inspector pass hit: this is their other side.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Authorize a disposition decision | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | Decide on the disposition page, or co-sign at the inspector's station. Use As Is is refused without a concession reference. The disposition on `INJ-QA-MANAGE-002` (bore 4.007 against a 4.005 max) is the exhibit. **⚠️ (fix uncommitted, re-walk):** a failing reading and a defect on one inspection opened two dispositions, and deciding one released the part while the other was open. The concession date was left blank. |
| 2 | Record a CAPA's effectiveness outcome | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | Two stages: a plan (method and success criteria), then the outcome. **Effective – Confirmed** closes the CAPA. Self-verification is refused unless the CAPA allows it (`CAPA-TRAIN-COMPLETE`). |
| 3 | Approve a MAJOR/CRITICAL CAPA before work can start | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | A QA Manager or a Production Manager approves (decided 10/20). Until then only containment can be worked. The requester self-approves, with a justification, only when nobody else can. **⚠️ (fix uncommitted, re-walk):** the gate and the template routing. The page didn't refresh after approving. |
| 4 | Co-sign an FPI buy-off for an inspector lacking `sign_off_fpi` | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | Walked in the QA Inspector track: pass, fail, waive and co-sign. |
| 5 | Release a judgement hold at receiving | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | Release with a reason (`RCV-MAT-HOLD`); confirm or decline a whole-lot reject request (`RCV-MAT-0007`). **⚠️ (fix uncommitted, re-walk):** a declined request's disposition closed as Return to Supplier, and the panel didn't show who asked or why. |
| 6 | Decide which NCRs become a CAPA, and justify the ones that don't | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | **No CAPA needed** and **Deferred** need a reason (ISO 9001 10.2.1(b)). **Create CAPA** links the report. The **Repeat defects** card lists candidates (Flow rate out of spec, 3×). |
| 7 | Work the approvals centre | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | Awaiting my approval / my requests / history. **⚠️ (fix uncommitted):** the home page's "Approvals in flight" rows weren't links. |
| 8 | Qualify someone for a process, and find whose qualification lapses this month | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | The training dashboard lists what expires (Mike's L1 certifications, 10/27); the matrix shows levels and coverage. **⚠️:** the record form defaults to Level 3 and no expiry; a renewal leaves the old record reminding; the matrix's expiry shows by colour only. |
| 9 | Raise a SCAR, track the response, change the supplier's standing | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | Suspend from the Approved Supplier List row menu. **⚠️:** the scorecard recommends an action but offers none, counts on-order lots as received, and lists customers. A suspension doesn't reach lots already at the dock. |
| 10 | Find everything measured by a gauge that just failed its check | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | `/quality/calibrations/records/$id/exposure` (7.1.5.2). MIC-2 measured five bodies at Body Inspection before failing this morning. It lists, but doesn't act. |
| 11 | Pull the complete record for one serial, on demand | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | The per-serial **Traveler**: who did each step, what was measured, the lots used. A serial is credited only with its own work: `INJ-QA-INSPECT-012`'s Flow Calibration is blank, `-013` prints REJ beside its out-of-spec flow, and Nitride Coating carries the return inspection's readings. *Needs repair* prints RPR. **⚠️:** a visit nobody has worked prints its assignee as the operator (`-013`'s Rework shows Sarah). |
| 12 | Approve a root cause | ✅ | ✅ | ✅ | ✅ | 2026-10-20 | **Approve** on the RCA tab (`review_rca`), under the independence rule. `CAPA-2024-003` (analysed by Jennifer, its go-ahead approved) is the exhibit. |
| 13 | Watch a control chart and respond to a signal | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | SPC drives no decisions yet (user, 10/20): reading the chart is the workflow. **⚠️:** with no variation the page reports Cpk = Infinity and a healthy process. |
| 14 | Set or tighten a sampling plan, and answer "why wasn't that part inspected?" | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | The part's **Sampling decisions** answer the second half ("Not selected — no rule in Standard Inspection - Body chose it"). **⚠️:** a rule change saves silently and doesn't appear in the rule set's History (auditlog records it twice); the rule set's View page fails to load. |
| 15 | Record a calibration result | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | TW-25 (overdue) recorded PASS and back in calibration. **⚠️:** Result defaults to PASS; next due isn't derived from the interval; the dashboard's buckets don't add up and leave out the failed MIC-2. |
| 16 | Decide a unit that ran out of reworks (MRB) | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | `CORE-240219-0014` failed Nozzle Inspection twice, was reworked twice, and hit the visit cap: quarantined at **MRB Review** with an open disposition. Re-walked on 96557fa + the persona-order fix: **Dispositions to take** on the home lists it tagged MRB; **Take it** moves it to Inbox > Dispositions; it carries the last FAIL; **Rework** sends the unit back to Rework, and the second rework's disposition is closed as superseded. Track module R2. |
| R1 | Record the customer's answer on over-and-above work | ✅ | ⚠️ | ✅ | ✅ | 2026-10-20 | `CORE-240212-0009`: the nozzle was found cracked at the bench and a replacement isn't pre-approved, so the unit waits. **Approved…** on the teardown work order's cores card resumes rebuild. **⚠️:** the dialog doesn't list the repairs being approved, and nothing outside that card shows the unit waiting. |

## Engineering

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Author a part type and its specifications | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | Walked as Jordan: Part Types › New (name, prefix, ERP id, sourcing) → *Part Type created successfully!* (the form stays on /new afterwards). Specs are measurements on steps (module 3). Track module 6. |
| 2 | Author a routing: steps, the graph, branches | ✅ | ⚠️ | ✅ | ✅ | 2026-10-22 | The flow editor. A QA Pass/Fail step's labelled edges are how rework lanes are authored; escalations draw as *Max Exceeded*. Walked: **Duplicate as Template** → rename, part type → Save → **Approve — Lock for production use** (Simplified: the author may). Track module 6. **⚠️:** Approve has no confirm and ignores open **Validation Issues**. Reported to f6. |
| 3 | Revise an approved routing | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked as Jordan (Engineering persona, cdd4b59): Process Actions › **Propose Change** forks a draft (the draft gets its own copy of an edited step; approved untouched) → Submit → Approve → PCO Implement (keep / migrate all / migrate selected, with reason) → new version current, old kept for running work → PCN released, closed with evidence. **Gaps (to -4f):** lock banner says *Duplicate* (the no-trail path); URL keeps the approved id after forking; diff shows edges as raw ids and **omits measurement-definition changes**; an empty (no-diff) PCR submits and approves; draft editable after submit. Track module 2. |
| 4 | Author work instructions (DWI substeps) | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked: Edit substeps › Add substep › text + a Measurement block linked to a definition › Save draft; Operator view previews it. Still no seeded instruction carries an image or translation. Track module 4. |
| 5 | Define measurements and attach them as step requirements | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | In the draft step: Configure measurements › Add Measurement (versioned with the step). **⚠️:** the tolerance hints read as absolute limits (*Maximum value*) though stored as offsets; the list drops the minus sign. Track module 3. |
| 6 | Give the solver what it needs | ✅ | ❌ | 🚧 | — | 2026-10-21 | **❌:** the step panel shows timing *Not set — taking no time* with inputs capped at 0, although StepTiming holds the real setup/cycle (Wash 15/30); an engineer can't read or set it there (to -4f). Not in the track until fixed. |
| 7 | Life limits | ✅ | ✅ | — | — | 2026-10-21 | **No UI yet** (user, 2026-10-21). Not in the track. |
| 8 | Raise a temporary change for named work orders, then extend or end it | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | Walked as Jordan on c8's d76dd0f. The temporary option requires an end date. Implement's picker lists in-flight WOs on every approved version, with a Version column, and greys a row where the change doesn't apply cleanly. `WO-2024-0042-A` (on v1, with v2 current) took the deviation on a v1-based fork with its parts on route, and **Move back to baseline** returned it to v1. Track module 5. **⚠️ (reported to c8):** the fork is numbered v2 beside the real v2; Move back has no confirm or reason; the PCR header reads *Affected in-flight WOs 0*; a description edit diffs as 8 edge changes. |
| C1 | Change control (PCR / PCO / PCN) | ✅ | ✅ | ✅ | ? | 2026-10-15 | **Propose Change** in the process editor forks a draft and opens a PCR. The PCR carries affected WOs and a structured diff. An approved record can't be repointed. Approval templates are matched to group names exactly. |

## Purchasing

Walked 2026-10-21 as Priya Nair (`priya.buy`), a seeded Purchasing user.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is on order and what is late | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | The Purchasing home: Late deliveries and expiring qualifications. **Shortages** (Requirements) shows the seeded valve shortage, *Control Valve Assembly · short 8 · order now* (STOCK-CRI-VLV seeded at 150). **Add expected delivery** records the ERP order as incoming. **⚠️:** incoming covers a line whatever its date, so a receipt promised after need-by makes the line vanish. Reported to -4f; fix in progress (netted by date, Incoming flags *after need*). An empty-lanes blank page reported 10/21 did not reproduce on 10/22: every lane reads *Nothing outstanding*. |
| 2 | Chase a late delivery | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | OTD is scored against the first promise. **Demo (fixed in seed):** Great Lakes Diesel has a deliveries contact (Dana Fischer) and a quality contact (Rob Lindqvist), so the card names whom to chase and **Chase…** offers to email them. |
| 3 | Maintain sourcing: lead time, preferred supplier, safety stock | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Part Types › **Sourcing** dialog: *The part itself isn't changed.* **A wrong lead time fails silently**: it shows up later as a job that can't start. Sourcing edits never version the part. |
| 4 | Qualify a supplier; maintain the approved list | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | Purchasing raises a draft (Pending); QA Manager grants it (`approve_supplierqualification`), and Grant… is refused for Priya. The seed now raises qualifications as Priya. **⚠️:** Grant… is offered anyway; the form promises *submit for approval*, which doesn't exist; the Basis picker shows raw codes. Reported to -4f. |
| 5 | Read the supplier scorecard and act on standing | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Rating thresholds: C on any open SCAR, reject ≥ 10% or on-time < 85%. The reject rate's denominator is *inspected* lots. Great Lakes: *Rating C · Review: suspend*. |
| 6 | Raise a SCAR against a supplier | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | **Raise SCAR** on a rejected lot's inspection page. **⚠️:** no duplicate check (a second SCAR on `RCV-MAT-0006`), and a rejected lot's inspection page can't be reached from any list. Reported to -4f. |
| C1 | Purchase orders, prices, spend approval | ✅ | — | — | ? | 2026-10-12 | **Out of bounds by design.** The PO lives in the ERP. |

## Document Controller

Walked as a real seeded Document Controller, so the Code column reflects what the
role can reach.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what needs me | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Approvals in flight · Documents (Needs my approval / Pending / Due for review / Released) · Training. |
| 2 | Upload a document with type and classification | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Walked as Lisa: **Upload Document** with a file, type and classification creates v1 Draft. The name comes from the file, extension included (`WI-1004 Seat loupe check.txt`); there's no title or document-number field. |
| 3 | Route a document for release approval | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | **Submit for Approval** on the Approval tab: Under Review, assigned by the Document Release template to the QA Manager (Maria), not to Lisa. **⚠️:** one click, no confirm, no toast. |
| 4 | Work a mixed approvals queue | ✅ | ✅ | 🚧 | ✅ | 2026-10-22 | **In flight ≠ assigned to me.** The seed's Document Release template routes to the QA Manager; the Document Controller's template is PCN release. Lisa's home lists every approval in flight (4 CAPA Major, 1 Document Release) with *Needs my approval 0*. Read in track module 1. **Demo 🚧:** nothing is assigned to this role. |
| 5 | Track the lifecycle | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Draft → Under Review → Approved (QA Manager, drawn signature and password) → **Release** (optional effective date; sets review and retention from the type: `WI-1001` reviews 2027-10-22) → **Mark obsolete** (confirm; can't be undone). Release/obsolete came in f6's 0ad5261 (`release_documents`: DC, QA Manager, Tenant Admin). Releasing a revision supersedes the previous released one (user decision 10/22): `WI-1002` v3 released → v2 *Superseded by v3*, no actions left. Track modules 3–6. |
| 6 | Find what is due for review | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Nothing notifies you; the tile is the signal. A type with no review period never prompts one. Release sets the review date from the type (track module 4). **Demo (fixed in seed):** the overdue exhibit had silently moved to a document with a future review date when the PUBLIC certificate sorted first; it now targets `DWG-CRI-8800` by name. |
| 7 | Classify, and hold the secret tier | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | `classify_documents`: Tenant Admin, QA Manager, Document Controller. `view_secret_documents`: Tenant Admin and Document Controller only, so Maria can classify Secret and then not see it. **Demo (fixed in seed):** `DWG-CRI-8800-N Nozzle seat geometry` at Secret; the API returns it to Lisa and the admin and not to Maria, Jordan, Mike or the Auditor. Track module 7. |
| 8 | Write training records | 📄 | ✅ | ✅ | ✅ | 2026-10-22 | `TRAINING_RECORD_WRITE`. Same form as Shift Lead module 6, which walks it. **Docs 📄:** see QA Manager 8. |
| C1 | Delete a document | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Deletion is a soft delete. Obsolete documents stay listed; status is a filter. Track module 6: a controlled document ends by **Mark obsolete**, not deletion. |

## Customer

Walked as Tom Bradley (`tom.bradley`, Midwest Fleet Services, portal user).

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See my orders and where each is | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | **Tracker**: one card per order with delivery date, stage and shipments. Visibility is `customer` or `viewers` on the order. **Demo (fixed in seed):** only orders naming Tom were visible (4 of 8), so the seed now names each company's portal contact on its orders. **⚠️:** a repair order with no work order yet (`ORD-2024-0044`, core `CORE-240210-0007`) is dropped from Tracker, so the customer can't see their own unit. Reported to -4f. |
| 2 | Read one order: progress, shipments, documents | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | A customer sees only PUBLIC documents attached to their order, its work orders, parts or part types. **Demo (fixed in seed):** none existed, so `CERT Flow test results SHP-2026-000001` is now seeded on `ORD-2024-0042`. The order was named 24 injectors with 30 parts on it (now 30), and its placed date was the seed's run time (now `days_ago`). **⚠️:** Line Items reads *0/25 completed* with 10 shipped; **Edit** and a Notes box are offered and then refused (403). Reported to -4f. |
| 3 | Invite a colleague to an order | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | **Invite** → *Invitation sent*. The invitee joins `viewers` with a pending `UserInvitation`. **⚠️:** the invitee is created INTERNAL with no company, and the People list doesn't show a pending invite. Reported to -4f. |
| 4 | Give my answer when the shop needs one | ✅ | — | ✅ | ✅ | 2026-10-21 | **Not in the portal, by design.** Staff record the customer's answer with their reference (`decide_disposition(customer_approval=…)`, the reman scope answer). The old track's "respond in the portal" was wrong. |

## Administrator

Walked 2026-10-21 as Alex Demo (Tenant Admin).

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Add a user with roles and a position | ✅ | ⚠️ | ✅ | ✅ | 2026-10-21 | **User Management › Add user**: role checkboxes (multi-role allowed), Position for the training matrix, Company and *Contact for* for outside people. **⚠️:** the form shows Django's *Staff Status* (admin-site login). Reported to -4f. |
| 2 | Change a user's roles | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | Edit › roles › Save; each grant and removal is in the user's History and the audit log. |
| 3 | Suspend a leaver | ✅ | ✅ | ✅ | ✅ | 2026-10-22 | Untick **Active User** (users are never deleted). Re-walked on 0ad5261: `Dave Wilson`'s Position loads (*Flow Test Technician*), Save → *User updated successfully!*, inactive with the position kept. |
| 4 | Find who changed what | ✅ | ✅ | 🚧 | ✅ | 2026-10-21 | **Audit Log**: time, user, action, object, before → after. Changes made in the app are all there. **Demo 🚧:** seeded changes have no actor and don't show (see Auditor 3). |
| 5 | Read what a role can do | ✅ | ✅ | ✅ | ✅ | 2026-10-21 | **Settings › Roles & Permissions** lists 14 groups with member and permission counts. **View** shows members and permissions. |
| 6 | Keep outside contacts out of the invite flow | — | ⚠️ | ✅ | — | 2026-10-21 | Supplier contacts (contact_role users) list as *Pending invite*, and **Invite N not yet invited** would invite them. Customer contacts live in a separate model (Settings › External Contacts). Reported to -4f. |

## Auditor

Walked as Alex Morgan (`alex.audit`), a seeded Auditor. Lower priority than the
production roles (user, 2026-10-21).

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Land on the evidence | ✅ | ✅ | ✅ | ? | 2026-10-21 | The Auditor home lists Audit log, CAPAs, Calibration records, Training records, Documents and Approvals, with CAPA and NCR-aging counts. |
| 2 | Look without being able to change | ✅ | ⚠️ | ✅ | ? | 2026-10-21 | The group holds only `view_*`, `export_data` and `full_tenant_access`, so the server refuses writes. **⚠️:** the UI still offers them: **Add Task**, **Add RCA** and **Upload** show on a CAPA. |
| 3 | Read one record's history | ✅ | ✅ | 🚧 | ? | 2026-10-21 | **Demo 🚧:** every seeded change was written outside a request, so none of the 4,435 entries has an actor. The API hides actor-less entries, so History reads *No audit history* on every seeded record. Changes trainees make carry their names. Fixing it means each seeded write takes its persona as actor; stamping one actor on all of them would misattribute the work. A decision for the user. |

---

## Corrections

The rows above walk the happy path. This table walks the other half: a person has
recorded something wrong, and it's been committed. For each mistake, the question is
whether there is a way to put it right, and what the record keeps of both.

Inventoried from code 2026-10-22, not yet walked. **Code** uses the status key:
✅ a page corrects it; ⚠️ a page does, with a catch; 🚧 the API allows it but no page
does; ❌ no path. **Walked** stays `?` until the correction is done in the browser as
the persona. Every model is in django-auditlog, so a plain field edit always leaves
who, when and old→new, but never a reason.

| # | Mistake | Role | Correction path | Code | Walked | Notes |
|---|---------|------|-----------------|------|--------|-------|
| 1 | Wrong reading, before **Complete step** | Operator | **Back** / **Edit** on the review screen; the draft is overwritten | ✅ | ? | |
| 1b | Wrong reading, after **Complete step** | Operator → QA Inspector | **Void** on the step's completions (reason), then re-capture: the reading versions | ⚠️ | ⚠️ | Void walked 2026-10-22 (reason required, *"Completion voided"*); the re-capture also rewrites the linked report (see 8). The runtime's equipment row defaults silently to the first machine. Re-capture only while the part is still at the step; past it, the void is audit-only and needs a rollback (#3) |
| 2 | Recorded on the wrong part | Operator → QA Inspector | Void on the wrong part, capture on the right one | ⚠️ | ? | Harvest/install rows can't be re-captured: "correct on the core's record" |
| 3 | Advanced a part too early | Operator, Shift Lead | **Previous step** / bulk rewind on WO Control (`rollback_part_step`) | ⚠️ | ✅ | **Re-walked 2026-10-22 on 26fe076:** Mike ran Machining on `WO-OPS-01`'s lot; Casey rolled `INJ-OPS-001` back with a reason: *1 part(s) rolled back*, Grinding visit ROLLED_BACK, Machining visit 2 open. **⚠️:** with no approval needed, the required reason is discarded (only the approval path stores it). Reported to f6. **First walk 2026-10-22 as Casey (`INJ-OPS-014`): refused,** *"No completed execution found for current step"*. `can_rollback_step` wants a COMPLETED execution at the step the part is *at*, which it only has after looping back. The page toasts *Parts rolled back* beside a *1 part(s) failed* banner with no reason. The button sends no reason while approval is required by default. Reported to f6 |
| 4 | Wrong material lot consumed | Operator | None. Usage is read-only; **Adjust quantity** fixes the count, not the genealogy | ❌ | ? | |
| 5 | Wrong clock times | Operator | PATCH time entry | 🚧 | ? | Not locked after approval |
| 6 | Wrong part in a sealed batch | Operator | PATCH the batch's parts, or void the batch completion (every part in it) | 🚧 | ? | No unseal |
| 7 | Report recorded PASS, should be FAIL | QA Inspector | Void the completion and re-capture as FAIL (as 1b) | ? | ? | Edit is refused: a recorded report is frozen (`approval_lock`) |
| 8 | Report recorded FAIL, should be PASS | QA Inspector | Void the completion, re-capture as PASS; then the disposition | ❌ | ❌ | **Walked 2026-10-22 as Sarah (`INJ-QA-INSPECT-015`):** Edit is refused (frozen), but the re-capture **rewrote the FAIL report to PASS in place**; only auditlog keeps the FAIL. Its disposition stays OPEN and the part quarantined; Complete step is refused with *"FAIL recorded"* while the banner says PASS. No disposition type fits "never a nonconformance": Rework loops a good part, Use As Is wants a concession. **Decided 10/22:** a new close, *not a nonconformance*, by the QA manager with the void reason; the FAIL report kept and superseded by a new PASS report. Spec'd to f6 |
| 9 | FPI passed wrongly | QA Inspector | None. A failed/waived FPI opens a new one | ❌ | ? | |
| 10 | Wrong gauge on a reading | Operator, QA Inspector | Void and re-capture (as 1b) | ⚠️ | ? | |
| 11 | Training override given wrongly | Shift Lead | Reassign; the override itself stays on the execution | ❌ | ? | |
| 12 | Hold placed wrongly | Production Manager, Shift Lead | **Resume** | ⚠️ | ? | Reads as a real hold that was cleared; no hold void |
| 13 | Downtime recorded wrongly | Shift Lead | PATCH | 🚧 | ? | |
| 14 | Wrong training record | QA Manager | Edit, or delete (archives) | ✅ | ? | |
| 15 | Wrong disposition decision | QA Manager | Decide again, until closed | ❌ | ❌ | **Walked 2026-10-22 as Maria (`DISP-2026-000013`):** Scrap went through with no confirm; re-deciding Rework moved the part to Rework but left it **SCRAPPED**, and replaced the Scrap note instead of appending. **Decided 10/22:** while open, a re-decide un-scraps, with a reason, both decisions kept. Spec'd to f6 |
| 16 | CAPA verified wrongly | QA Manager | Not Effective reopens it; Closed is terminal | ⚠️ | ? | `verify` doesn't refuse re-verifying a decided verification (API) |
| 17 | Wrong approval response | QA Manager, Production Manager | None; the request can be cancelled while pending | ❌ | ? | |
| 18 | Supplier suspended wrongly | QA Manager | **Grant…**; a disqualified one needs a new qualification | ⚠️ | ? | Grant doesn't release lots the suspension held |
| 19 | Wrong calibration result | QA Manager | Edit or delete; the gauge status re-applies | ✅ | ? | |
| 20 | Wrong teardown grade | Shift Lead | A finding, then **Apply** | ✅ | ? | |
| 21 | Core received under the wrong order/mode | Receiving | PATCH while RECEIVED | 🚧 | ? | None once teardown starts |
| 22 | Customer's answer recorded wrongly | QA Manager, Production Manager | None | ❌ | ? | Declined can't be re-requested |
| 23 | Wrong component installed | Operator | Remove (reason), install the right one | 🚧 | ? | Component status and reservation aren't restored |
| 24 | Wrong received quantity | Receiving | **Adjust quantity** fixes what's left, not what was received | ❌ | ❌ | **Walked 2026-10-22 as Luis (`RCV-MAT-0005`, 120 keyed, 12 arrived):** adjusted to 12; the list reads *12 EA of 120*, and the ERP sheet still says received 120, accepted 120, *Ready to post*. **Decided 10/22:** a separate **Correct receipt** action with a reason, while nothing has been used; posted rows flag *Changed since posted*. Spec'd to f6 |
| 25 | Wrong supplier, material or PO line on a lot | Receiving | PATCH | 🚧 | ? | No reason |
| 26 | Lot accepted or rejected wrongly | Receiving, QA Manager | **Reject remainder**, or Use As Is on a concession; a pending whole-lot request can be declined | ✅ | ? | |
| 27 | **That's all** chosen by mistake | Receiving | None; record a new expected receipt | ❌ | ? | |
| 28 | Lot put in the wrong place | Receiving | **Move…** | ✅ | ? | |
| 29 | Cycle count wrong | Receiving | Re-enter while open; once submitted, a new count or Adjust quantity | ⚠️ | ? | |
| 30 | Marked posted to the ERP by mistake | Receiving | None | ❌ | ? | |
| 31 | Shipment recorded by mistake | Shipping | **Void shipment**, then ship again | ✅ | ✅ | Shipping row 7 |
| 32 | Wrong carrier or tracking | Shipping | **Edit paperwork** | ✅ | ? | |
| 33 | Wrong quantity shipped from a lot | Shipping | Void and ship again | ⚠️ | ? | The split-off child lot isn't merged back |
| 34 | Wrong quantity or date on an expected receipt | Purchasing | Cancel and re-record, or re-import; **Chase…** for the date | ⚠️ | ? | The first chase turns a typo'd promise into the "original promise" used for on-time scoring |
| 35 | Wrong lead time or preferred supplier | Purchasing | Edit again | ✅ | ? | |
| 36 | Work order released by mistake | Planner | **Withdraw release** (Gantt → task → **Edit WO**) | ⚠️ | ✅ | **Walked 2026-10-22 as Sam (`WO-OPS-02`):** withdrawn at once, *"Release withdrawn — re-solve to drop it"*, with four parts mid-Wash: no confirm, no reason, nothing said about the work on the floor. **Release** puts it back (*Ready to release*). Reported to f6 |
| 37 | Wrong calendar closure | Planner | Delete and re-add; re-solve | ✅ | ? | |
| 38 | What-if draft committed | Planner | None; re-solve | ❌ | ? | Undo reverses only the last manual move |
| 39 | Wrong priority, pin or move | Planner, Shift Lead | Set again (reason) / unpin / **Undo** | ✅ | ? | |
| 40 | Wrong WO quantity or date | Production Manager | Quantity (cancels unstarted parts only), edit the date, or cancel the WO | ✅ | ? | |
| 41 | Disposition closed, or WO short-closed, by mistake | QA Manager, Production Manager | None; a new disposition or WO | ❌ | ? | |
| 42 | Process change implemented by mistake | Engineering | None; a new change back | ❌ | ? | |
| 43 | Wrong measurement definition | Engineering | A new draft of the process | ✅ | ? | |
| 44 | Temporary change applied to the wrong WO | Engineering | **Move back to baseline** | ✅ | ? | |
| 45 | Wrong revision released, or obsoleted by mistake | Document Controller | Revise → release; obsolete has no undo | ⚠️ | ? | |
| 46 | Wrong classification | Document Controller | Edit in draft; otherwise revise | ✅ | ? | |
| 47 | Wrong role, or suspended by mistake | Administrator | Remove from the group and add the right one / **Activate** | ✅ | ? | |

**Walk first** (how often × how hard to undo): 3, 1b, 7–8, 15, 24, 36, 12, 34.

## Open findings

### Product gaps and defects

| Finding | Where | Note |
|---|---|---|
| **The customer sidebar shows internal sections** | `app-sidebar.tsx:160-166` | Sections are gated per permission; the Customer preset's view perms turn on Production, Scheduling and CAPAs. The destinations refuse them. |
| **The frozen fence is presented as a lock** | Scheduler | It's a soft penalty. See the note under Scheduler. |
| **Priority changed by import has no reason** | Shift Lead C1 | CSV import and the master workbook bypass `change_priority`. |
| **In Simplified mode one person can carry a process change alone** | Change control | The default mode for every tenant. **Approve** needs only the authoring permissions, nothing stops the submitter approving, no signature is collected, and the PCO is created already approved. By design, but a decision to make knowingly: Regulated mode enforces the signed, independent path. Docs now say so (`change-control/overview.md`) |
| **`/orders/<order number>` errors** | | Only `/orders/<uuid>` loads, although the route parameter is named `$orderNumber` |
| **Change-control loose ends** | Engineering C1 / 8 | A PCR with an empty diff can be submitted and approved. *Affected in-flight WOs* counts every WO on the process even for a temporary change. After a Simplified approval the signatures panel reads *Cancelled* while the approver's row still reads *Pending*. **Move back to baseline** has no confirmation |
| **The over-and-above scope has no document** | Shift Lead R2, Production Manager R1 | The customer's answer is recorded (`viewsets/reman.py:279`), but nothing produces the scope to send the customer: what work, what parts, and the finding behind each. The product boundary says UQMES exports it. Found by the documents session 2026-10-20 |
| **The Pick Sheet has no button** | Receiving 11 | `pick_sheet` is registered, but no screen offers it. Found by the documents session 2026-10-20 |
| **Every report is gated by one permission** | | All reports sit behind `export_data` (`reports/viewsets.py`, `CanExportReports`), so who can print a CoC is the same as who can print a training record. Worth deciding whether any documents need narrower gates |
| **Small copy and accessibility** | | `OperatorSubstepRuntimePage.tsx:1271` and `completion-adapters.tsx:261` show developer copy (*"Add `?execution=<id>`…"*); the measurement input's accessible name is `—`; the receiving hold panel hedges (*"If the part type requires qualification, the lot was held"*); part Activity History dumps a raw `Capture Draft: {…}` field and prints `Expires At` as a raw UTC timestamp; CAPA **Related Items** shows raw UUIDs for the step and work order; the CAPA prefill chip shows the report's UUID, not its number; the FPI incomplete message says *"finish the step's captures"* when it means the first piece's. |

### Walked 2026-10-19 — the day's builds

All walked in the browser against the dev database, and each checked against the
database, not just the screen.

**Working as built:**
- correction reasons
- time approval, including self-approval refused
- the training-overrides review, including the Operator explanation
- the downtime card and the Report dialog
- repeat defects
- sampling decisions
- the delivery-date slip
- hold and resume
- short-close: its refusal, the required answers, the move, the badge and both
  corrections
- remove from order
- the gate bypass: request, can't decide your own, refuse needs a reason,
  approve
- RCA approval, including the conductor's refusal
- audit-log browsing refused for an Operator, while a record's own history stays
  open
- the temporary change: submit, refusal without a date, the register badge, the
  PCR approve, implementing selected WOs only, the baseline staying current, the
  server refusing new work on the temporary version, move back to baseline

**Found and fixed during the walk:**
- The order-parts card collided with the infinite parts query on one cache key,
  so the card was stuck on *Loading…* and **Line Items** read "0 types".
- The PCR submit dialog let Justification and Risk analysis through blank, and
  the client then refused with a Zodios error.

**Not walked:**
- the expiry refusal (the end date is in the future; tests cover it)
- **Extend…**
- the PCN text
- the process-editor banner on a temporary version

### Parked

- **Life tracking's screen.** Fully built on the server, with no UI. The user has
  parked it.
- **`can_make` on part types.** Meant for the scheduler's make-or-buy choice, but
  how it should work isn't designed.
- **The reman scheduling strategy** (Scheduler R1). Waiting for real data.
- **An adherence view** (Scheduler 8).
- **A per-ruleset list of sampling decisions.** Only the per-part view is built.

## Seed and training arc backlog

Seed and training are one arc. Each item below is something the demo can't show
or gets wrong. The fix is in the seed or the training material, not the product.

**Process and flow**

- **The demo should walk the flow, not stage its outcome.**
  `seed/orders.py::_advance_part_through_workflow` writes `StepExecution` rows
  directly instead of calling `advance_part_step`. One root cause leaves several
  things thin or empty:
  - material consumption and forward lot trace
  - real step timings
  - per-serial histories (QA Manager 11)
  - QA approvals the mechanism never produced
- **A new-manufacture process is seeded** (`DEMO_BUILD_PROCESS`, ending at a
  `SHIPPED` step). Check that work orders actually use it. The reman route still
  ends `COMPLETED`, and `seed/manufacturing.py` still hardcodes `COMPLETED` on the
  last step.
- **The seed doesn't solve a schedule.** Scheduler 1–8 and Shift Lead 2 and 3
  need a solve, which needs a Celery worker (`--pool=solo` on Windows).
- **The seeded shop can't meet its order book:** one shift and no redundant
  machines. Add capacity, or reduce demand, if the shop day needs on-time work.
- **Cores are seeded `DISASSEMBLED` off any work order,** where nothing can act on
  them. `CORE-240210-0007` needs walking to REBUILT for Shipping R1 and Shift
  Lead R3.
- **No reman unit has walked past Nozzle Inspection.** `d0ef5f9` moved the three
  customer orders to Injector Build so shipping could be shown, and nothing replaced
  them on the reman route. Reassembly (with its components-fitted capture), Final
  Test and Packaging have no reman history; the WO-TRAIN/ASSESS reman parts sitting
  there were placed with no executions. Needs one services-walked rebuild: a
  teardown-released core through Reassembly to Final Test. Reman track's to build.
- **The rework step has no inspection substep** (Operator C1).
- **The Component Grading substeps** say reuse / rework / scrap but capture only
  Pass / Fail / Pending (Operator R1).

**Tenant defaults the demo lacks**

- The demo tenant has 4 document types; a new tenant gets 39.
- It has no `PROCESS_APPROVAL`, `CAPA_CRITICAL` or `TRAINING_CERT` template.
  Without `PROCESS_APPROVAL`, Engineering 3 refuses.

**The shop day's cast** (`docs/training/shop-day.md`, recast 2026-10-20 onto the seed's
own world)

- No logins for Engineering, Purchasing, Receiving, Shipping or Auditor. Jennifer
  (Production Manager) plans, and Casey (Shift Lead and inspector) runs the floor.
- The internal company is named *AMBAC Manufacturing* and the logins are
  `@demo.ambac.com`, so the training shop names the reference customer. Deferred
  with the seed mechanics (user, 2026-10-20); the shop day avoids the company name.
- Each moment is an outline until its role's track is built and walked.

**Missing subjects** (the mechanism works, but there's nothing to point it at)

- No shift notes (Operator 11, Shift Lead 8).
- No downtime (Shift Lead 10, Production Manager 11).
- No released work orders (Production Manager 2).
- No core awaiting authorisation (QA Manager R1).
- No serviceable components in stock (Production Manager R2).
- No `ExternalContact` (Purchasing 2).
- No substep images or translations (Engineering 4).
- No Secret-tier document (Document Controller 7).
- Nothing assigned to Document Controller (Document Controller 4).
- No delivery-date slips.
- Shipping 9's fallback never fires.
- Receiving gates are only partly armed: `requires_part_approval` and
  `requires_coc` are on nothing.
- All demo companies are both customer and supplier. The internal org stays both,
  by decision; narrow the carriers.

**Residue to clear on reseed**

Walk residue, 2026-10-19:
- `TEARDOWN-…850345` was short-closed, and its 3 cores moved to `TEARDOWN-…251373`
  (quantity 5).
- `ASSESS-004`'s date moved to Nov 10, and `ASSESS-004-004` was removed from the
  order.
- A test RCA by Maria is on CAPA-2024-003, and its original RCA is now verified.
- An approved bypass is on `TRAIN-BOTTLE-001`.
- `PCR-2026-0002` / `PCO-2026-0001` left a temporary *Injector Reman* version
  (no WOs on it).
- One time entry is approved, and one downtime event is resolved.


- `CAPA-2024-003` carries an immutable, forged approval response in the QA
  Manager's name. Don't use it as an approval exhibit.
- Probe rows that can't be removed: a `SubstepGateCompletion` (`audit-probe`)
  and a PENDING `StepOverride` (*AUDIT PROBE*).
- `OSP-DEMO-005` / `-006` wait at Nitride Coating for their return inspection, as designed: **Accept return** advances them once the inspection is done on the shipment (SEED: they were read as stranded because nobody had inspected them).
- Seeded time entries start at 03:00 local: written in UTC without the shop's timezone.
- Parts the seed staged have no active step execution, so they show no blockers and can't demonstrate a bypass. `TRAIN-BOTTLE-001` and `INJ-0042-017` can.
- `RCV-MAT-0006` was rejected through the primitive, so it has no disposition.
  The seeder is fixed; a reseed clears it.

**Training material drift** (all training pages are stale, so these are only the
known specifics)

- The QA script's scan box is too narrow.
- The hold exhibit is named `RCV-INJ-HOLD` (it's `RCV-MAT-HOLD`) and taught as
  "don't inspect", when it's the best screen in the journey.
- The script teaches one FPI route of two.
- `training/operator.md` and `training/shift-lead.md` describe the old Report
  dialog.
- Help docs still cite demo users and IDs on 13 pages (the QA Inspector's pages are clear). Pull those out role by role
  as each track is built.

**Not walked yet: walk these.** Rows marked *Not walked* above, plus capabilities
that are built and have a UI but no row of their own:

- void a substep
- QA sign-off without a first piece
- decide a whole-lot reject request
- grant a supplier qualification or part approval
- apply a cycle count
- lot trace
- approve a repair branch that wasn't pre-approved
- start a teardown batch
- the calibrations-due list

Also: the FPI separation-of-duties refusal, and the temporary change, RCA
Approve, WO hold/resume and audit-log batches built 2026-10-19.

## Decisions — not gaps

Settled with the user. Don't re-raise them.

| Decision | Date |
|---|---|
| **Void is for substep completions only.** A wrong measurement or quality report is corrected by a new record; the pair is the evidence. | 2026-10-19 |
| **The tenant's own company stays both customer and supplier.** | 2026-10-19 |
| **A deviation is a temporary process change** through change control, scoped to named WOs and ended by finishing or by date. No permit model. | 2026-10-19 |
| **Version numbers are for reference, not lineage.** A temporary and a permanent version can share v(n+1). | 2026-10-19 |
| **`export_auditlog` is reserved** for a future CSV export of the audit log. | 2026-10-19 |
| **Calibration recording is owned by QA Manager**, for now. | 2026-10-19 |
| **Training on a revised step:** requirements carry forward, and a newly added one must be held on its own (verified in `check_training_authorization`). | 2026-10-19 |
| **Out of the software:** management review, quality objectives, the risk register, the internal-audit programme, customer communication (escapes, complaints: email), delayed CAPA re-checks. | 2026-10-19 |
| **Parts reach an order through work orders**, never directly. Retiring a part type or an instruction means archiving it. | 2026-10-19 |
| **Scrap proof of destruction** isn't an MES record for ISO 9001. Revisit with AS9100. | 2026-10-19 |
| **The audit log's existing rows are not rewritten;** credentials are excluded going forward and masked on read. | 2026-10-19 |
| **`entered_at` is not backdatable,** and there is no offline mode. History import would be a separate, marked path. | 2026-10-07 |
| **Customer-property loss reporting (8.5.3) sits outside the system,** with the reman team. | 2026-10-06 |
| **Export control is vestigial.** Keep it accurate; don't build on it. | 2026-10-14 |
| **No quotes, prices or POs.** The ERP (Glovia, human-bridged) owns them. | standing |
| **`is_portable` is inert, and documented as such.** | 2026-10-19 |
| **The operator home's dimmed tiles are an intended preview**, and the persona picker's extra option is supervisory preview. | 2026-10-06 |
| **The training tracks serve both change-control modes.** Each track works for a facility in either mode, branching only where the mode changes the steps (PCR approval, PCO authoring and approval). The seed must run the shop day in either mode. The default for new organisations is undecided. | 2026-10-20 |
| **Whoever conducted an RCA can't approve it** unless the CAPA allows self-verification. A verified RCA gates Pending Verification (8D D4, ISO 9001 10.2.1(b)); containment and tasks are not gated. | 2026-10-19 |

## Method lessons

What this audit learned the hard way. Each one produced at least one false
finding before it was written down.

1. **A walk is complete when the subject moves, not when the surface reports
   success.** Reload, or read the database. A shipment closing doesn't prove its
   parts advanced. A draft showing in a list doesn't prove anything was saved.
2. **An absence claim needs a positive control.** Before reporting "nothing does
   X", make the same query find something it's known to contain. Most false
   negatives came from the query:
   - a guessed field name (`content` vs `body_blocks`)
   - a case-sensitive grep
   - a `| head` read as the whole set
   - a `grep -v` that excluded the answer
   - an unfiltered `archived`
   - a grep that missed a generated `api_*` alias
3. **Disambiguate selectors, and confirm from the network.** Stacked dialogs and
   duplicate button labels made the first match the wrong element twice.
4. **Poll toasts from t=0.** They dismiss in about 4 s.
5. **Scripted input isn't typing.** Setting `.value` doesn't drive React state,
   and synthetic clicks don't drive Radix. Use real keystrokes and trusted
   clicks.
6. **A screenshot taken as evidence must be looked at.**
7. **An empty-body POST is a cheap permission probe:** 403 means gated, 400 means
   reachable. Run it alongside a known-denied control.
8. **Passing tests prove the code works, not that anyone can reach it.** Check who
   calls it, and from where.
9. **An OPEN finding proves something was open once.** Re-check it before quoting
   it.
10. **The seed stages outcomes, and that hides mechanisms.** Opt-in gates and rare
    events go dark silently, because an unarmed gate looks exactly like a passing
    one. A showcase exhibit must be deterministic, not random. Read a seeded state
    as evidence about the seed, not the product.
11. **Don't drive measurement captures with filler values.** A placeholder fires
    the quality machinery for real.
12. **Probe records on immutable models leave permanent residue.** Probe
    signature-shaped records deliberately.
13. **A date-only field is safe only if both ends agree.** `new Date("YYYY-MM-DD")`
    is UTC midnight. A form that round-trips a date it never edited can still move
    it a day.
14. **A partial PATCH omits `default=None` fields.** The write succeeds, and the
    zod client then reports it to the user as a failure.
15. **`str(e)` on a Django `ValidationError` is its list repr.** Join `e.messages`
    instead.
16. **Two methods find disjoint gaps.** Walking a role finds capability that's
    finished but unmentioned. Writing a help page from the code finds capability
    built to the edge of visibility and stopped there, because the page forces
    the question *"where do you go to see it?"* Neither substitutes for the other.
17. **A training page is not a help page.** Docs ✅ means a help page explains it.
    Writing a training record was marked ✅ while its only how-to sat in a
    training track, which teaches on demo data and is being rebuilt. When a row's
    only page is under `training/`, Docs is 📄.

---

## Resolved

One line each, newest first. The full write-ups are in git history.

| Finding | Resolution |
|---|---|
| A returned reman unit had no paperwork route | Returns ship as a `CustomerShipment` with packing list and CoC; exchange stock ships on an order (`ac85a3e`, 2026-10-20, not walked) |
| A FAIL reached by editing a report opened a disposition without a quarantine | `on_report_failed` runs the FAIL consequences on the move into FAIL, from PATCH and from DWI findings (2026-10-20, not walked) |
| A quarantine left no audit entry | Quality-gate hold and failed-batch containment save each part, so its history carries the change and actor (2026-10-20) |
| `disposition_type` was silently ignored on PATCH | Refused with 400, naming Decide; re-sending the same value passes (2026-10-20) |
| The inspection aggregation endpoints didn't filter rows by user | Incoming queue and inbox rows follow `for_user` (2026-10-20) |
| What-if compared runs that differ by solver noise | Compare bar shows each side's solver gap and warns within it (2026-10-20, not walked) |
| Make-up was reachable only from the scheduling page | Make-up card on the work order page when short; no false shortfall on empty or ended WOs (2026-10-20, not walked) |
| The WO Control page's FPI sign-off only passed | Sign off / Fail / Waive on both routes, one dialog (2026-10-20, not walked) |
| The order edit form showed RFI for a PENDING order | Select shows the real status; new orders default to Pending (2026-10-20, not walked) |
| An on-order lot read "On hand" | Reads "On hand 0 · N expected" (2026-10-20, not walked) |
| New-work process pickers offered the temporary version and drafts | One rule for new work: approved, in force, not temporary; the server refuses the rest (2026-10-19, re-walked) |
| Start Work offered on held and ended work orders, and the server didn't check | Disabled with the reason; the server refuses with no override (2026-10-19, re-walked) |
| Short-close could move a customer's unit to another customer's work | Same-customer or no-order targets only; a customer's own unit only to theirs (2026-10-19, re-walked) |
| Order-parts card stuck on *Loading…*; Line Items read "0 types" (cache-key collision) | Own query key, found and fixed on the walk (2026-10-19) |
| PCR submit failed with a Zodios error on blank Justification / Risk analysis | Both marked required, with plain messages (2026-10-19) |
| Bulk hold / clear-hold gated on `add_workorder` | Gated on `change_workorder`, and buttons hidden without it (2026-10-19) |
| Single-WO status PATCH writes any status | Refused, naming the action to use. Hold, Resume and Cancel go through services. Clearing a hold no longer sticks at ON_HOLD (2026-10-19) |
| Bulk "Change status" with no rules | Dialog, endpoint and service removed (2026-10-19) |
| `WAITING_FOR_OPERATOR` never set | Status removed, migration 0237 (2026-10-19) |
| Audit log showed every record's changes to every staff role, password hashes included | Rows follow record visibility; browsing needs `view_auditlog`; credentials excluded (2026-10-19) |
| RCA approval had no UI; review status bugs; nothing needed a verified RCA | Approve built; statuses fixed; verified RCA gates Pending Verification and effectiveness (2026-10-19) |
| FPI co-sign discarded the drawn signature | `FPIRecord.signature_data`, migration 0239 (2026-10-19) |
| FPI with no first piece skipped segregation of duties | `get_or_create` refuses without a first piece (2026-10-19) |
| Deviation permits had no home | Built as temporary process changes, migration 0240 (2026-10-19) |
| Downtime captured but never analysed | Downtime card on Analytics (2026-10-19) |
| Repeat defects API-only | Card on NCR Analysis (2026-10-19) |
| Sampling log credited skips to the wrong rule, and had no screen | Attribution fixed (0238); per-part Sampling decisions (2026-10-19) |
| No screen listed an order's parts; remove was unaudited | Parts on this order card, audited service, `change_orders` (2026-10-19) |
| Delivery-date slip never recorded | `original_completion_date` stamped once, DateField, migration 0241 (2026-10-19) |
| QA panel annotated on the first model by name | Prefers a completed model with no step (2026-10-19) |
| Special-process qualification never checked at send-out | `Steps.outside_special_process`, migration 0235 (2026-10-19) |
| CAPA approval not tiered by severity | Severity picks the template, with fallback (2026-10-19) |
| Report exception saved nothing | Downtime posts a real event; quarantine and CAPA link to forms (2026-10-19) |
| Work order page's Release skipped the release service | Calls `release_work_order` (2026-10-19) |
| Reman dashboard's component links never loaded | Filter declared, router values unwrapped (2026-10-19) |
| Training overrides had no screen | Shown on the part traveller (2026-10-19) |
| Disposition routes broke the URL convention | `/production/dispositions/new` and `/$id/edit` (2026-10-19) |
| No failed calibration in demo, so the recall page was dark | Seeded found-out-of-tolerance calibration (2026-10-19) |
| Change Control page banner said the actions weren't built | Banner replaced (2026-10-19) |
| Change-control nullable fields reported successful PATCHes as failures | Fields read-only, nullable (2026-10-15) |
| 45 date-only display sites read as UTC, two of them also writing | `parseDateOnly` sweep, `3e4cba4` (2026-10-15) |
| Every bulk part action silently no-oped (string vs UUID keys) | Helper keyed by `str(id)` (2026-10-15) |
| The RCA independence guard was unreachable | `approve_rca` delegates to `verify_root_cause`, `3ed193a` (2026-10-06) |
| An NCR not promoted to a CAPA left no trace | `NOT_REQUIRED` / `DEFERRED` with a mandatory reason (2026-10-06) |
| Any operator could forge a manager's e-signature | `ApprovalResponse` read-only; responses only via `submit-response` (2026-10-07) |
| Seven compliance holes (disposition type, SPC baselines, gate completions, overrides, life tracking, out-of-service equipment) | All probed and closed (2026-10-07) |
| Operators could write training, calibration, sampling and life-limit records | Permissions narrowed and probed both ways (2026-10-07) |
| A QA sign-off gate with no way to satisfy it | Step sign-off service, inbox chip, dialog (2026-10-07) |
| Teardown couldn't be completed where teardown ends | **Complete teardown** action (2026-10-07) |
| Finishing the last part of a batch left a dead screen | Returns to the work order (2026-10-07) |
| Every CAPA dialog destroyed itself as you typed | Dialogs lifted out of render (2026-10-06) |
| The only NCR→CAPA path was dead | Router query split from the path (2026-10-06) |
| UI-created RCAs had no author | `perform_create` defaults `conducted_by` (2026-10-06) |
| Core lots in the inspector's Receiving chip | Shared `awaiting_inspection` helper (2026-10-06) |
| A picked date showed a day early | `parseISO` (2026-10-06) |
| Self-approval refusal printed a list repr; toasts said only the status code | `'; '.join(e.messages)`; `apiErrorMessage()` (2026-10-06) |
| Demo exhibits lit by the seed: the hold panel, gauge nag, training gate, expected receipts, a core on a work order, the reman capture nodes, shift-note handover, a repair-and-return core, shipping data | Seed phases through `dark_exhibits.py` (2026-10-06 → 10-19) |
| `auto_now_add` discards seeded step timestamps | **Decided, not a bug**: `entered_at` stays unwritable; the seed must walk the flow (2026-10-07) |
| `requires_signature` enforced nowhere | Enforced in `services/dwi/operator_capture.py:174` |
| Retracted, not bugs: the verification dialog "stays open"; "Start Work swallows claim failures"; "approval has no independence check"; "a rejected lot can only be returned if accepted first"; "orphaned dispositions" | Measurement or reading errors by the auditor. See method lessons 2–5 and 10 |
