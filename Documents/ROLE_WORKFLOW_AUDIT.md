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
| 1 | See what to work next, and claim it | ✅ | ✅ | ✅ | ? | 2026-10-06 | The operator home is the claiming surface (Up next / Then / In progress), not the Work Orders page. |
| 2 | Identify the right physical unit (scan) | ✅ | ✅ | ✅ | ? | 2026-10-06 | The scan box takes work orders, serials, lots and locations. The help docs say so; the QA training script is still narrower (arc). |
| 3 | Prove qualification before starting, or be authorised | ✅ | ✅ | ✅ | ? | 2026-10-07 | Refused, then overridden by a supervisor. The override records worker, authoriser, reason and what was missing, and keeps `authorized: false`. Lit by Nozzle Inspection `min_level: 2`. |
| 4 | Follow the instruction and record as you go | ✅ | ✅ | ✅ | ? | 2026-10-06 | DWI runtime: inline spec, an In spec badge, attestation, a review screen. A value fixed before **Complete step** never becomes a nonconformance. Captures are saved when the operator moves off a substep. |
| 5 | Have the lots I used recorded against the unit | ✅ | ✅ | ✅ | ? | 2026-10-12 | Consumption is automatic on step exit, FEFO, attributed to the operator. Nobody picks a lot. |
| 6 | Report a problem mid-step | ✅ | ✅ | ✅ | ? | 2026-10-06 | **Can't run this?** routes four reasons to named owners: missing material → Materials, tooling → lead, quality hold → QA, other → lead. The home tile *Report a problem* is a dimmed preview. |
| 7 | Work a batch another operator started | ✅ | ✅ | ✅ | ? | 2026-10-06 | The batch claim dialog plus the **reassignment gate**, which names the current owner. |
| 8 | Finish and move the unit on | ✅ | ✅ | ✅ | ? | 2026-10-07 | The **lot** advances, not the part, so a finished unit can wait on a lot-mate. Finishing the last part of a batch returns to the work order. |
| 9 | Account for time | ✅ | ✅ | ✅ | ? | 2026-10-06 | Clock in/out/break/lunch writes a `SHIFT` TimeEntry. A lead approves it on Operator Hours (built 2026-10-19, not walked). |
| 10 | See what I am qualified for, and what is expiring | ✅ | ✅ | ✅ | ? | 2026-10-06 | *My Training*. Manager tiles show to operators, but the API refuses them. |
| 11 | Read and acknowledge shift notes and notifications at clock-in | ✅ | ✅ | ❌ | ? | 2026-10-07 | Walked with a note written by hand: MUST ACKNOWLEDGE, acknowledged with name and time. **The seed writes no shift notes** (arc). |
| 12 | Be called over as the second person on someone else's gate | ✅ | ✅ | ✅ | ? | 2026-10-07 | Both gates: the training override and reassignment. |
| R1 | Grade a component at teardown, with the part in your hand | ✅ | ✅ | ✅ | ? | 2026-10-07 | A DWI capture node. *"When in doubt, grade down."* **Copy-vs-control drift:** the Component Grading substep says reuse / rework / scrap but offers only Pass / Fail / Pending. Seed authoring (arc). |
| R2 | Raise a finding at the bench when a reused part fails later | ✅ | ✅ | ✅ | ? | 2026-10-13 | Walked end to end. The check held the unit, a lead applied the finding, the plan re-resolved, and the unit took Nozzle Recondition and rejoined. |
| R3 | Work a rebuild step whose scope was only settled this morning | ✅ | ✅ | ✅ | ? | 2026-10-12 | Scope is derived on read and writes nothing. The plan page gives a *Because* for each row. |
| C1 | Pull one unit out of a batch and send it back for rework | ✅ | ✅ | ❌ | ? | 2026-10-15 | The bulk write is scoped to the selection. **Demo ❌:** the demo's Rework step has no inspection substep, so rework is correctly refused (arc). |
| C2 | Get an erroneous record corrected | ✅ | ✅ | ? | ? | 2026-10-19 | A quality role voids the substep completion and the work is captured again (`void_substepcompletion`: QA Inspector, QA Manager, Tenant Admin). Measurements and quality reports are corrected by a new record, by decision. Supply-side changes made with a reason show in the record's **Corrections** block. |
| C3 | Work when the terminal or scanner is down, and catch up after | ✅ | — | — | ? | 2026-10-07 | **Settled intent.** There is no offline mode, and `entered_at` is not backdatable, because it is traceability evidence. The paper traveller is the fallback, and `dwi/running.md` describes the catch-up. |

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
| 1 | See the shift's state at a glance | ✅ | ✅ | ✅ | ? | 2026-10-07 | Biggest fire, late jobs, quarantine, CAPAs, OSP, training. Every number links. |
| 2 | Reassign work when someone cannot run it | ✅ | ✅ | ✅ | ? | 2026-10-12 | Operators *claim* work; the lead reassigns. The board's task panel offers **Reassign** (*"applies now, re-solve to optimize"*), with the picker filtered by eligibility. Needs a solved schedule. |
| 3 | Cover an absence or no-show | ✅ | ✅ | ✅ | ? | 2026-10-12 | Same surface. An **empty operator picker is a training problem wearing a scheduling costume.** |
| 4 | Unblock a stopped job | ✅ | ✅ | ✅ | ? | 2026-10-07 | Control Center **Exceptions**: unified items, each with the work order it impacts. |
| 5 | Authorise an unqualified operator, on the record | ✅ | ✅ | ✅ | ? | 2026-10-19 | The override shows on the part traveller as an amber line: worker, missing training, authoriser, time, reason. **Training Overrides** lists them across a period. |
| 6 | Triage a quality event without escalating everything | ✅ | ✅ | ✅ | ? | 2026-10-07 | Exceptions: source, severity, age, owner, *Open only*, bulk resolve. |
| 7 | Watch what is going late | ✅ | ✅ | ✅ | ? | 2026-10-07 | *Jobs going late*, plus **Overdue / Due today** filters, plus the overdue badge on Tracker cards. |
| 8 | Hand over to the next shift | ✅ | ✅ | ❌ | ? | 2026-10-07 | Shift notes: targeted by role, a High flag, *Requires acknowledgment*, and acknowledgment recorded. **The seed writes none** (arc). |
| 9 | See who is qualified for what | ✅ | ✅ | ✅ | ? | 2026-10-06 | The training matrix. It reports **role** gaps while the start gate reads **step** requirements, so a role gap doesn't block work. |
| 10 | Escalate what the shift cannot solve | ✅ | ✅ | ❌ | ? | 2026-10-19 | **Report…** records downtime for real (types with *Track downtime* off are excluded) and links to the disposition and CAPA forms. **The seed records no downtime** (arc). |
| 11 | Put a work order on hold, resume it, cancel it, or short-close it | ✅ | ✅ | ✅ | ? | 2026-10-19 | Walked: hold and resume, and the short-close refusal and completion. Hold needs a reason (Pending or In progress). Resume returns to In progress if work started, otherwise Pending. Cancel needs `cancel_workorder`. The API refuses a status set directly. |
| R1 | Decide a pending finding — apply or dismiss | ✅ | ✅ | ✅ | ? | 2026-10-08 | `PendingFindingsCard`. Apply re-grades and re-resolves the plan, leaving a trail in `condition_notes`. Dismiss takes a reason. |
| R2 | Request customer authorisation for over-and-above | ✅ | ✅ | ✅ | ? | 2026-10-07 | **Authorise…** refuses when nothing exceeds the sold rebuild level: only genuinely new work reaches the gate. |
| R3 | Decide a torn-down unit's exit: rebuild, harvest, or return | ✅ | ✅ | 🚧 | ? | 2026-10-15 | **Complete teardown**, then **Rebuild to stock** or **Release to inventory**. A repair-and-return unit offers **Release into rebuild**. **Demo 🚧:** the return exit waits on `CORE-240210-0007` reaching REBUILT. |
| C1 | Jump a job to the front, with a reason | ✅ | ✅ | ✅ | ? | 2026-10-15 | Expedited is derived from priority URGENT. `change_priority` requires a reason and writes a `RecordEdit`, and the edit form shows the last five. **Residual:** a CSV import or the master workbook changes priority without a reason. |
| C2 | Void an operator's bad record | ✅ | — | — | ? | 2026-10-15 | **Not this role, by design.** Voiding is QA Inspector, QA Manager and Tenant Admin. A lead escalates. |
| C3 | Take a machine out of service and re-plan around it | ✅ | ✅ | ✅ | ? | 2026-10-12 | An out-of-service or uncalibrated machine drops out of the solver's affinities. |

The **persona picker** lets one person hold several roles: `casey.dual` is an
inspector by day and a shift lead when covering. Landing is a persisted choice.
Supervisory preview lets a lead view a surface without holding that role. It
grants the view, not the permissions.

## Receiving

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is expected | ✅ | ✅ | ✅ | ? | 2026-10-07 | Materials **On order / Late**. An expected receipt is a `MaterialLot` that hasn't arrived, with PO, line, promised date and chase fields. |
| 2 | Receive a delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | A new lot number and heat number, and the CoC or packing slip photographed. The lot is routed to inspection automatically. |
| 3 | Verify against the paperwork | ✅ | ✅ | ✅ | ? | 2026-10-07 | The unified **Incoming Inspection** queue. |
| 4 | Handle a short or over delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | *"20 fewer than the 200 on order. What does the packing slip say?"* **More coming** keeps the remainder on order; **That's all** stops planning on it (the PO line is closed in the ERP). |
| 5 | Resolve holds | ✅ | ✅ | ✅ | ? | 2026-10-06 | *Held for N reasons — each clears on its own.* Paperwork holds self-clear; judgement holds need a quality manager. |
| 6 | Reject and return | ✅ | ✅ | ✅ | ? | 2026-10-07 | Reject opens a disposition. **Ship back** takes an RMA and prints the RTV sheet, and the replacement delivery is created automatically. The lot is *Returned — not scrapped*. A whole-lot reject needs `reject_whole_lot` (QA Manager, Tenant Admin); without it, the reject becomes a request. |
| 7 | Put away and find again | ✅ | ✅ | ✅ | ? | 2026-10-07 | `/production/locations`, with nesting and **Move…** (partial moves allowed). Every movement is in the ledger. |
| 8 | Count stock | ✅ | ✅ | ✅ | ? | 2026-10-12 | A blind count, then apply. Applying needs `apply_cyclecount` (a lead's). `CC-2026-0001` is seeded submitted but not applied. |
| 9 | Chase a late delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | **The first promise is kept:** a supplier can't improve their on-time record by re-promising, and the screen shows it. |
| 10 | Hand receipts to the ERP | ✅ | — | ✅ | ? | 2026-10-15 | **Not a feed, by design.** Glovia is bridged by a person. UQMES owes the document: **Receipts for ERP** on Materials. |
| 11 | Stage and kit material to the bench for the next shift | ✅ | ✅ | ✅ | ? | 2026-10-12 | `/production/staging`. **Confirm** and **Took another**. Trap: the 8 h window reads *"Nothing scheduled"* on a plant holiday. |
| R1 | Receive a core | ✅ | ✅ | ✅ | ? | 2026-10-07 | An authored DWI step: scan the identity band, photograph it as received, grade it, sign. *"Don't clean yet"* keeps the evidence (ISO 9001 8.5.3). |
| R2 | Receive a bulk core lot and identify units from it | ✅ | ✅ | ✅ | ? | 2026-10-07 | A counted delivery with no serials. **Identify and next** works down a pallet. Exchange cores by definition. |

## Shipping

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is ready | ✅ | ✅ | ✅ | ? | 2026-10-08 | `/production/shipments`: *"Invoicing stays in your ERP."* Ready to ship / Shipped, grouped by order. |
| 2 | Confirm it passed and is complete | ✅ | ✅ | ✅ | ? | 2026-10-08 | **The route's Ship step is the queue.** Shipping completes that step through `advance_part_step`, so the 8.6 release gate runs. |
| 3 | Create the shipment | ✅ | ✅ | ✅ | ? | 2026-10-08 | Select units → **Ship …** → a shipment number. |
| 4 | Produce the paperwork | ✅ | ✅ | ✅ | ? | 2026-10-08 | Packing list, CoC, Edit paperwork, Void…, and the history. |
| 5 | Ship partially | ✅ | ✅ | ✅ | ? | 2026-10-08 | Per-unit selection; the rest keep waiting. |
| 6 | Record carrier and tracking | ✅ | ✅ | ✅ | ? | 2026-10-08 | Tracking can be added later. |
| 7 | Undo a mistake | ✅ | ✅ | ✅ | ? | 2026-10-12 | A void is for a shipment recorded by mistake: the parts return to their Ship step or to stock. *"Goods that went and came back are a return, not a void."* |
| 8 | Return customer property | ✅ | ✅ | ✅ | ? | 2026-10-12 | Independent of any ship step. Lot-aware, so partial returns work. `MaterialLot.owner` is ringfenced throughout (8.5.3). |
| 9 | Know whether we are on time | ✅ | ✅ | 🚧 | ? | 2026-10-15 | On-time %, falling back to the WO's expected completion, with "N not measurable" shown. **Demo 🚧:** the fallback never fires on seeded data. |
| 10 | Send parts out to a subcontract vendor, and record them back | ✅ | ✅ | ✅ | ? | 2026-10-19 | `OutsideProcessPanel`. The return inspection is a step execution, and **Accept return** advances the parts. A step naming a **Special process** refuses an unqualified vendor. |
| R1 | Return a rejected core to its owner | ✅ | ✅ | 🚧 | ? | 2026-10-13 | `return_core_to_customer` needs REBUILT or DECLINED and refuses an exchange unit. **Demo 🚧:** `CORE-240210-0007` hasn't been walked to REBUILT. |
| R2 | Ship a rebuilt unit with the paperwork | ✅ | ✅ | ? | ? | 2026-10-20 | A return is a `CustomerShipment` (`ac85a3e`): **Return** on the Cores card opens the ship dialog, and the Shipping board lists finished reman units under their owner. Packing list always; CoC when the customer wants one with every shipment. Exchange stock on an order ends *Shipped on exchange*. No printed as-built sheet, by decision: it stays an in-system record. Not walked. |
| C1 | Export-control screening before anything leaves | ✅ | — | — | ? | 2026-10-14 | **Not a target.** Export control is vestigial. The machinery is kept accurate in case it's revived. Don't build on it, and don't create non-US accounts. |

## Scheduler

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Produce a schedule | ✅ | ✅ | ✅ | ? | 2026-10-15 | Solve needs `add_scheduleresult` (Planner, Production Manager, Tenant Admin). It is a Celery task, and the board says so when no worker is running. **The seed doesn't solve** (arc). |
| 2 | Find out why something is not on it | ✅ | ✅ | ✅ | ? | 2026-10-08 | *"Why isn't this scheduled?"* groups by cause with a remedy each, and admits what it can't explain. |
| 3 | Dispatch people | ✅ | ✅ | ✅ | ? | 2026-10-08 | Dispatch reports coverage (*"259/265 covered"*). Uncovered work becomes a standing chip. |
| 4 | Adjust by hand | ✅ | ✅ | ✅ | ? | 2026-10-08 | The task panel: Reassign, Pin, Merge into batch, Edit WO. |
| 5 | React to a disruption | ✅ | ✅ | ✅ | ? | 2026-10-08 | Staleness flags trip on demand, part and capacity changes, not on routine step advances. It's a hint, not an auto-solve. |
| 6 | Test a change before committing | ✅ | ✅ | ✅ | ? | 2026-10-20 | **What-if** solves a draft and states trade-offs in both directions. Solves stop at a 66–99.6% optimality gap; the compare bar now shows each side's **solver gap** and warns when a difference is within it. Not walked. |
| 7 | Get the plan to the floor | ✅ | ✅ | ✅ | ? | 2026-10-08 | Dispatch is the hand-off. The **Dispatch List** is a printable report, not an assignment surface. |
| 8 | See whether the floor followed it | ✅ | ⚠️ | 🚧 | ? | 2026-10-19 | Actuals are capture-only by design and don't re-time the plan. There is no adherence view. Needs a solve followed by movement. |
| 9 | Author non-working time — holidays, shutdowns, PTO, training | ✅ | ✅ | ✅ | ? | 2026-10-08 | Calendar exceptions and labour blocks. The solve honours them. |
| R1 | Schedule work whose route isn't known until teardown | ✅ | ⚠️ | ✅ | ? | 2026-10-13 | Books the nominal route and re-solves when reality diverges. **⚠️ A deliberate simplification:** reman is tree-shaped. The user is waiting for real data before designing further. |

The **frozen fence** is a soft penalty in the solver, but the board legend says
*"Frozen stays put"*. A third of the frozen tasks moved in one solve. Either the
legend or the weight should change. Open.

## Production Manager

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is at risk | ✅ | ✅ | ✅ | ? | 2026-10-07 | Late jobs, quarantine, CAPAs, FPY, supplier qualifications expiring, competency coverage. |
| 2 | Release work | ✅ | ✅ | ❌ | ? | 2026-10-19 | `release_work_order` is advisory: a failing check demands a written reason, it never refuses. Every Release button uses it. Releasing never changes status. **Demo ❌:** no seeded work order is released. |
| 3 | Promise a date | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Could we take this order?** gives the binding resource, the shortfall and a counter-offer. It warns about operations with no cycle time. The window runs to the due date. |
| 4 | Resolve escalations | ✅ | ✅ | ✅ | ? | 2026-10-07 | `resolve_step_decision`, on the Exceptions surface shared with the Shift Lead. |
| 5 | Balance capacity and staffing | ✅ | ✅ | ✅ | ? | 2026-10-08 | Booked hours per resource, against Dispatch coverage. The demo shop can't deliver its order book: ~3,758 h of work against ~2,222 h of labour. That's a seed property. |
| 6 | Close out a nonconformance decision, and know who decides a deviation | ✅ | ✅ | ✅ | ? | 2026-10-19 | Accepting nonconforming product (*Use As Is* / *Repair*) is a disposition: QA decides it (`approve_disposition`), and the PM closes it (`close_disposition`). A **planned** departure is a temporary change — see Engineering 8. |
| 7 | Review OTD and throughput | ✅ | ✅ | ✅ | ? | 2026-10-07 | FPY on the hero, customer OTD on Shipping, supplier OTD on the scorecard. No single throughput view. |
| 8 | Maintain the data planning depends on | ✅ | ✅ | ✅ | ? | 2026-10-08 | **Master Workbook**: validate, then commit, all or nothing. |
| 9 | Top up a job after scrap outruns the gross-up | ✅ | ✅ | ✅ | ? | 2026-10-20 | Planner-confirmed by design. A **Make-up** card on the work order page when the job is short; always on the scheduling dialog. A WO with no parts, or ended, reports no shortfall. Not walked. |
| 10 | Take in a customer order and turn it into work orders | ✅ | ? | ? | ? | ? | **Not walked.** The order page lists its parts (staff only) and keeps the original delivery date once it moves. |
| 11 | See where machine time is lost | ✅ | ✅ | ❌ | ? | 2026-10-19 | Walked with one recorded event. The **Downtime** card on Analytics: hours lost by cause and machine, as a share of calendar time. No OEE, by design. **The seed records no downtime** (arc). |
| R1 | Authorise over-and-above and record the customer's answer | ✅ | ✅ | ✅ | ? | 2026-10-07 | Approved resumes the rebuild; Declined routes to DECLINED. *"The conversation happened elsewhere; these record what the customer said."* No price anywhere. |
| R2 | Decide harvest versus buy on a rebuild kit | ✅ | ✅ | 🚧 | ? | 2026-10-07 | *"Proposed, not committed."* **Demo 🚧:** no serviceable component is in stock, so every slot reads *Replace — buy* (arc). |

## QA Manager

Built from the gates the QA Inspector pass hit: this is their other side.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Authorize a disposition decision | ✅ | ✅ | ✅ | ? | 2026-10-06 | Co-sign at the inspector's station, or decide directly with `approve_disposition`. |
| 2 | Record a CAPA's effectiveness outcome | ✅ | ✅ | ✅ | ? | 2026-10-06 | **Confirmed effective** closes the CAPA. **Not effective** reopens it, flags the RCA and raises a 30-day task. Self-verification is refused unless the CAPA allows it. A verified root cause is required first. |
| 3 | Approve a MAJOR/CRITICAL CAPA before work can start | ✅ | ✅ | 🚧 | ? | 2026-10-19 | Severity picks the template (`CAPA_CRITICAL` / `CAPA_MAJOR`, falling back to `CAPA_APPROVAL`). Decision, signature and password. Self-approval is refused by default. **Demo 🚧:** no `CAPA_CRITICAL` template (arc). |
| 4 | Co-sign an FPI buy-off for an inspector lacking `sign_off_fpi` | ✅ | ✅ | 🚧 | ? | 2026-10-19 | Co-sign mode is recorded under the inspector's name, and their drawn signature is kept (`FPIRecord.signature_data`). **Demo 🚧:** the seeded FPIs can't be signed (arc). |
| 5 | Release a judgement hold at receiving | ✅ | ✅ | ✅ | ? | 2026-10-06 | Unqualified supplier or unapproved part. |
| 6 | Decide which NCRs become a CAPA, and justify the ones that don't | ✅ | ✅ | ✅ | ? | 2026-10-15 | **Create CAPA** on a FAIL report. `NOT_REQUIRED` and `DEFERRED` need a reason (ISO 9001 10.2.1(b)). The **Repeat defects** card lists candidates. |
| 7 | Work the approvals centre | ✅ | ✅ | ✅ | ? | 2026-10-06 | The queue isn't scoped by type. Assignment comes from the template, matched to group names exactly. |
| 8 | Qualify someone for a process, and find whose qualification lapses this month | 📄 | ✅ | ✅ | ? | 2026-10-20 | The matrix shows coverage and single-point risk. Writing a training record is withheld from Operator and QA Inspector. **Docs 📄 (corrected 2026-10-20):** no help page explains writing the record. The Training Matrix page only reads it. The how-to is in the old QA Inspector track (*Recording the qualification*), and moves to the Training Matrix page. |
| 9 | Raise a SCAR, track the response, change the supplier's standing | ✅ | ✅ | ✅ | ? | 2026-10-06 | A SCAR is a CAPA with `capa_type='SUPPLIER'`. The scorecard recommends an action. |
| 10 | Find everything measured by a gauge that just failed its check | ✅ | ✅ | ✅ | ? | 2026-10-19 | `/quality/calibrations/records/$id/exposure` (7.1.5.2). "Found unfit" includes found-out-of-tolerance-then-adjusted. It lists, but doesn't act. |
| 11 | Pull the complete record for one serial, on demand | ✅ | ✅ | 🚧 | ? | 2026-10-15 | The per-serial **Traveler**: who did each step, what was measured, the lots used. **Demo 🚧:** seeded parts are staged, so their histories are thin (arc). |
| 12 | Approve a root cause | ✅ | ✅ | ✅ | ? | 2026-10-19 | Walked, including the conductor's refusal. **Approve** on the RCA tab (`review_rca`), under the independence rule. A verified RCA is required before Pending Verification and before any effectiveness check. |
| 13 | Watch a control chart and respond to a signal | ✅ | ? | ? | ? | ? | **Not walked.** SPC. Possibly shared with Engineering. |
| 14 | Set or tighten a sampling plan, and answer "why wasn't that part inspected?" | ✅ | ? | ? | ? | ? | **Not walked.** The per-part **Sampling decisions** answer the second half. |
| 15 | Record a calibration result | ✅ | ? | ? | ? | ? | **Not walked.** Owned by QA Manager, by decision. The permission is wider: seven groups hold `CALIBRATION_RECORD_WRITE`, and a PASS returns out-of-service equipment to service. |
| R1 | Record the customer's answer on over-and-above work | ✅ | ✅ | ❌ | ? | 2026-10-12 | The customer decides; UQMES records the answer. **Demo ❌:** no core awaits authorisation on a fresh seed (arc). |

## Engineering

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Author a part type and its specifications | ✅ | ✅ | ✅ | ? | 2026-10-12 | The `/editor/processes` family. |
| 2 | Author a routing: steps, the graph, branches | ✅ | ✅ | ✅ | ? | 2026-10-12 | The flow editor. A QA Pass/Fail step's labelled edges are how rework lanes are authored. |
| 3 | Revise an approved routing | ✅ | ✅ | 🚧 | ? | 2026-10-19 | An approved process is locked. Duplicate → Draft → Approve, or change control (C1). **Demo 🚧:** no `PROCESS_APPROVAL` template, so **Submit for approval** is refused (arc). |
| 4 | Author work instructions (DWI substeps) | ✅ | ✅ | ❌ | ? | 2026-10-12 | **Demo ❌:** no seeded instruction carries an image or a translation (arc). |
| 5 | Define measurements and attach them as step requirements | ✅ | ✅ | ✅ | ? | 2026-10-12 | A definition is the characteristic; a requirement attaches it to a step. |
| 6 | Give the solver what it needs | ✅ | ⚠️ | 🚧 | ? | 2026-10-19 | **⚠️ Only the cycle time is Engineering's** (`change_steps`). Machine eligibility, step timings and changeovers sit with Production Manager and Tenant Admin (changeovers also with Planner). 15 steps have no duration, so capacity overstates what's free. |
| 7 | Life limits | ✅ | ✅ | ✅ | ? | 2026-10-12 | Linking a limit to a part type *is* applying it. The tracking screen is parked. |
| 8 | Raise a temporary change for named work orders, then extend or end it | ✅ | ✅ | ✅ | ? | 2026-10-19 | Walked end to end except expiry and **Extend…**. Under the default Simplified mode, approval is one click. A PCR marked temporary, with an end date. It applies only to the named WOs, and the baseline stays current. Past the date, work stops. **Extend…** raises a new PCR; **Move back to baseline** works per WO. |
| C1 | Change control (PCR / PCO / PCN) | ✅ | ✅ | ✅ | ? | 2026-10-15 | **Propose Change** in the process editor forks a draft and opens a PCR. The PCR carries affected WOs and a structured diff. An approved record can't be repointed. Approval templates are matched to group names exactly. |

## Purchasing

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is on order and what is late | ✅ | ✅ | ✅ | ? | 2026-10-12 | Shares Receiving 1 and 9. |
| 2 | Chase a late delivery | ✅ | ✅ | 🚧 | ? | 2026-10-12 | OTD is scored against the first promise. **Demo 🚧:** no `ExternalContact` rows, so *who to chase* is empty (arc). |
| 3 | Maintain sourcing: lead time, preferred supplier, safety stock | ✅ | ✅ | ✅ | ? | 2026-10-12 | **A wrong lead time fails silently**: it shows up later as a job that can't start. Sourcing edits never version the part. |
| 4 | Qualify a supplier; maintain the approved list | ✅ | ✅ | ✅ | ? | 2026-10-12 | Purchasing raises a draft (Pending); QA Manager grants it (`approve_supplierqualification`). Its other side is QA Manager's grant. |
| 5 | Read the supplier scorecard and act on standing | ✅ | ✅ | ✅ | ? | 2026-10-12 | Rating thresholds: C on any open SCAR, reject ≥ 10% or on-time < 85%. The reject rate's denominator is *inspected* lots. |
| 6 | Raise a SCAR against a supplier | ✅ | ✅ | ✅ | ? | 2026-10-12 | `initiate_capa`. See QA Manager 9. |
| C1 | Purchase orders, prices, spend approval | ✅ | — | — | ? | 2026-10-12 | **Out of bounds by design.** The PO lives in the ERP. |

## Document Controller

Walked as a real seeded Document Controller, so the Code column reflects what the
role can reach.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what needs me | ✅ | ✅ | ✅ | ? | 2026-10-12 | Approvals in flight · Documents (Needs my approval / Pending / Due for review / Released) · Training. |
| 2 | Upload a document with type and classification | ✅ | ✅ | ✅ | ? | 2026-10-12 | The name comes from the file; there's no title or document-number field. |
| 3 | Route a document for release approval | ✅ | ✅ | ✅ | ? | 2026-10-12 | The template is picked by approval type, not by the submitter. |
| 4 | Work a mixed approvals queue | ✅ | ✅ | 🚧 | ? | 2026-10-15 | **In flight ≠ assigned to me.** By default Document Controller is assigned only **Document Release**. **Demo 🚧:** nothing is assigned to this role. |
| 5 | Track the lifecycle | ✅ | ✅ | ✅ | ? | 2026-10-12 | Draft → Under Review → Released. **Obsoleting is a deliberate act.** |
| 6 | Find what is due for review | ✅ | ✅ | ✅ | ? | 2026-10-12 | Nothing notifies you; the tile is the signal. A type with no review period never prompts one. |
| 7 | Classify, and hold the secret tier | ✅ | ✅ | 🚧 | ? | 2026-10-12 | `classify_documents` and `view_secret_documents` belong to this role and QA Manager. **Demo 🚧:** nothing above Confidential is exercised (arc). |
| 8 | Write training records | 📄 | ✅ | ✅ | ? | 2026-10-20 | `TRAINING_RECORD_WRITE`. **Docs 📄:** see QA Manager 8. |
| C1 | Delete a document | ✅ | ✅ | ✅ | ? | 2026-10-12 | Deletion is a soft delete. Obsolete documents stay listed; status is a filter. |

---

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
