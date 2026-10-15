# Role Workflow Audit

**Status:** live and maintained. **138 rows across 11 roles**, nearly all walked
against the running application and dated. This is the one file in `Documents/`
that is *not* design history — see the staleness note on the rest of that
directory before trusting anything else in it.

**Started:** 2026-10-06 · **Last full pass:** 2026-10-15

**Coverage:** Operator, QA Inspector, Shift Lead, Receiving, Shipping, Scheduler
(= Planner; one role, the presets merged them), Production Manager, QA Manager,
Engineering, Purchasing, Document Controller.
**Not covered:** Administrator, Auditor, Customer — excluded from the first pass
as "read-only", which is right for Auditor and wrong for the other two.
Administrator especially: the day's work *consumes* approval templates, part
types and document types that only an admin creates. A later pass, by user
decision 2026-10-15.

!!! important "Using this file is how it stays true"
    **Flip the row in the same change that does the work.** The Docs column
    rotted once because the help docs were derived from this file and nobody
    came back; five rows went stale again in a single day on 2026-10-15 for the
    same reason. A ledger nobody closes out is worse than none, because it is
    believed.

## Why this exists

The user documentation grew subsystem by subsystem, following what was built. That
makes it accurate about features and silent about **jobs**: a reader who holds a
role cannot tell whether the thing they need to do is covered, badly covered, or
absent from the application entirely.

This audit inverts the order.

## Method

!!! warning "Check the unit of work before trusting a row"
    Two drafted workflows have already dissolved on contact with how the shop
    actually runs: both assumed one operator working one part through one long
    operation. The real unit is a **batch**, with per-unit records.

    Before auditing any row, ask whether it presumes a unit of work this shop
    doesn't have. An absence found by reasoning from other products is a weaker
    finding than one found in the code.


Deliberately **not** code-first. Deriving workflows from the code inherits what was
built rather than what is needed, and can only ever find documentation gaps.

1. **Abstract.** For each role, what must a person in that job be able to do — in
   any QMS/MES/APS/DWI, independent of this application?
2. **Docs.** Is it documented? Where?
3. **Code.** Does the application support it?

A gap can therefore be a **doc gap**, a **code gap**, or **both**. The third kind
is the reason for doing it in this order.

## Doers have queues; oversight is the other side of their gates

From `UQMES_ONBOARDING_WALKTHROUGH.md`: *"As a manager, your day is mostly the
**other side of those gates** — the approvals and verifications inspectors send
up."*

That is a **derivation rule**, not an observation. An oversight role's list
should not be written independently; it is the counterpart to the gates the doer
roles hand up. Writing it from scratch produces subsystem nouns — "run
calibration", "manage supplier quality" — which cannot be audited.

| Doer | Gate they reach | Oversight counterpart |
|------|-----------------|-----------------------|
| QA Inspector | First-piece buy-off, lacking `sign_off_fpi` | Co-sign at the inspector's station |
| QA Inspector | Disposition decision (lacks `approve_disposition`) | Authorise the decision |
| QA Inspector | CAPA verification plan authored | Record the outcome (`verify_capa`) |
| QA Inspector | Major CAPA raised | Approve it before work can start |

**Apply the same test to Operator → Shift Lead**: authorising an unqualified
operator, voiding a bad record, deciding a reman finding and releasing a hold are
all the lead's side of a gate the operator reached.

A gate should appear **twice** in this audit — once as the doer hitting it, once
as the overseer clearing it — and the two rows should name each other.

## New manufacture is the default; reman is secondary

**New manufacture is the fundamental case.** Every role's list is ordered with it
first, and reman workflows are appended as `R1`, `R2` … — present, auditable, and
deliberately **not** promoted into the main sequence.

This is a decision, not an oversight. Reman is the more distinctive subsystem and
the more interesting one to write about, which is exactly why it will keep
drifting upward unless the ordering says otherwise. A reviewer previously
recommended threading reman through the main lists; that was declined.

Reman rows are **additional work on existing roles**, never a role of their own —
see the note under QA Inspector.

## Scope

The eight roles who are in the software constantly or daily. Periodic roles
(Planner, Purchasing, Document Controller, Engineering) and read-only roles
(Auditor, Customer, Administrator) are out of scope for this pass.

> **Update 2026-10-12.** **Engineering**, **Purchasing** and **Document
> Controller** have since been walked and have their own sections below — their
> training tracks needed ground truth to be written against. **Planner** is
> covered by the **Scheduler** rows (one role; the presets merged them).
>
> **Customer** was probed rather than walked. Its portal is the **Tracker**
> page and it works — row filtering verified. Three rough edges are recorded
> under Findings (*the customer portal is the Tracker page, and it works*).
>
> **Seed phase 9 (`dark_exhibits.py`) landed 2026-10-12** and lit eight rows that
> were built-but-empty: Operator 5, Receiving 8, Shipping 8, Shipping 9,
> Shipping C1 (data side), Scheduler 8, Document Controller 6 and 7. Asserted in
> `Tracker/tests/test_demo_seed.py` (13 tests, OK) so they cannot go dark again
> unnoticed.
>
> ~~**Still blocked, and why:** Engineering C1 needs the PCR UI built. Shipping C1's
> denial side needs a non-US-person account.~~
>
> **Both overtaken — corrected 2026-10-15.** Engineering C1's UI was not missing;
> it was there and the walk was blocked by three separate bugs, all since fixed,
> and the row now reads *works end to end*. Shipping C1's denial side is no
> longer worth an account: export control answers a requirement that did not
> survive (user, 2026-10-14), so it is not a target and the row should not be
> read as a to-do.
>
> **CORRECTED 2026-10-12 — the "signature substep cannot be driven synthetically"
> blocker was wrong, and it was wrong about the product, not just the harness.**
> This file asserted it on Shipping R1, Shipping R2, the OSP return and QA Manager
> 4. It does not hold: the in-player `signature` node has **no signature canvas at
> all**. `AttestationCheckpoint.tsx` carries the comment *"data_uri reserved for
> SignatureCanvas integration"* — the node is a one-click attestation that records
> a name and a time, with no pad, no re-authentication, and nothing written to
> `SubstepCompletion.signature_data` / `verification_method` / `signature_meaning`.
> Walked it on 2026-10-12 (WO-TRAIN-001 / TRAIN-001-008 / Final Test / *"Final leak
> / pressure test"*, `requires_signature=True`). So the rows were not blocked by
> the harness; they were blocked by a belief about a pad that isn't there.
> `requires_signature` is enforced nowhere in `submit_substep` — raised as a
> product question, not fixed here.
>
> **2026-10-12 — the reman rows were blocked by a SECOND thing, a real defect,
> now fixed by a peer session (uncommitted at the time of writing).**
> CORE-240210-0007 could not leave **Cleaning** at all. `skip_out_of_scope` walked
> past operations the unit's rebuild scope omitted and routed onward with
> `part.get_next_step(None)`; on a `QA_RESULT` decision point that demands a
> QualityReport, which can never exist for an op nobody inspects *because it is
> being skipped*. `DecisionDataMissing` every time — a permanent deadlock.
>
> The cause was the abstraction, not the router. `resolve_scope` built scope
> **additively from RepairCodes**, so an op was skippable purely by not being
> mentioned: Nozzle Inspection, Flow Testing and Final Test are configured
> identically (`DECISION` / `QA_RESULT` / `requires_qa_signoff=True`) and the
> filter kept two and dropped the third, because no raised code happened to name
> it. Nobody decided the nozzle needn't be inspected. Routing past it on the
> DEFAULT (pass) edge — the obvious fix — would have been worse than the deadlock:
> a silent unverified release on a customer's own unit, against ISO 9001 §8.6.
>
> **The answer taken (user-decided): nothing is skipped.** Every op on the main
> line always runs; repairs become **Repair nodes** branching off a check and
> rejoining, each carrying a `RepairCode`. Pre-approval lives on the
> check→repair `StepEdge`, so it stays under change control (Steps are shared
> across versions; edges are not). Scope still plans the rebuild — kits, slots,
> the over-and-above export — it just no longer routes the unit.
> See `services/reman/repair_routing.py` and migration
> `0226_reman_repair_branches`.
>
> **Verified here 2026-10-12** (rolled-back transaction, peer's tree): the core
> now advances **Cleaning → Nozzle Inspection** with `status: advanced`. What it
> reports are that step's own forward gates — QA signoff, FPI pending, its two
> substeps, the training gate — not a deadlock. **Pending:** the demo Injector
> Reman process has **0 Repair nodes** so far, so the reseed has not run and the
> new Repair surfaces are not yet walkable.
>
> **Browser verification of the Repair-node surfaces, 2026-10-12 (still uncommitted).**
> After the demo was reseeded, four of the six surfaces were walked as
> `admin@demo.ambac.com` and pass:
>
> - **Flow editor.** Violet Repair nodes with a wrench branch off **Nozzle
>   Inspection** and rejoin at **Flow Testing** (14 steps, was 12). The Step
>   Details panel for the check reads *"Repairs offered here — Nozzle Recondition
>   **Pre-approved** · Nozzle Replacement **Needs approval**"*, and explains the
>   tick: *"goes ahead on the inspector's finding. Unticked: the unit waits here
>   for a lead, and on a customer's own unit for the customer's answer."*
> - **Cores card.** *Authorise…* appears **only** on the customer unit, driven by
>   the Exit column — CORE-240210-0007 (*Rebuild & return*) offers Work / Plan /
>   Authorise…, while the exchange unit CORE-240215-0006 offers Rebuild to stock /
>   Release to inventory and no Authorise…
> - **Rebuild plan** (`/reman/cores/$id/rebuild`). The card is now **Expected
>   repairs**, columns Repair / Code / At check / Approval / Because, and it states
>   the new model outright: *"Every operation on the route runs. These are the
>   repairs its checks will send this unit to."*
> - **Repair code editor and list.** The steps checklist is replaced by a read-only
>   *"Where it's done"*; the list's **Operations** column is now **Where it's
>   done**, and `RepairCode.steps` is dropped (migration 0227) with `schema.yaml`
>   regenerated.
>
> **Two defects found and fixed by the peer during the pass:** the Repair nodes
> rendered the badge **`no code`** — `ProcessFlowPage.tsx` hand-maps a whitelist of
> step fields to the canvas and omitted `repair_code_code`, so a value the API
> returned correctly was dropped in the page (the same shape as the `pk`/`id`
> phantom: a field that exists upstream and is lost in a hand-written mapping).
> And five copies of the retired *"emits operations"* phrasing survived in
> `serializers/reman.py`, `models/reman.py`, `rebuild.py` ×2 and `scope.py`.
>
> **Walks 2 and 3 — the unit walk and the lead-approval branch — are NOT done.**
> I quarantined CORE-240210-0007 myself while scripting the Cleaning batch step
> (a filler value of `1` went into Bath Temperature and was confirmed for the
> batch before correction, raising a FAIL batch report and an automatic
> containment). Awaiting a reseed. **Recorded as a method lesson:** do not drive
> measurement captures with scripted fallback values — a wrong value is not a
> harmless placeholder, it fires the quality machinery.
>
> **Two PRE-EXISTING defects surfaced by that accident, neither from this change:**
> (a) a quarantine leaves **no audit entry** — `batch_disposition.py` holds the
> load with `bulk_update` and `quality_gate.py` with `.update()`, both bypassing
> `post_save`; both carry comments showing the author knew and compensated for the
> *schedule* flag but not for `django-auditlog`. Measured: the part had 7 LogEntry
> rows, the last from the seed, while `updated_at` was 11 minutes later.
> (b) correcting a batch measurement **does not retract the failed batch report** —
> after 1 → 60 the stored measurement reads in-spec while the FAIL report and its
> disposition stay open, so the record contradicts itself. A void is the proper
> retraction; the UI allowed an in-place overwrite of a value that had already
> fired a report.
>
> **`dwi/running.md:70-75` "Your work is saved as you go" — VERIFIED TRUE 2026-10-13.**
> The doc promises a substep is sealed on confirm and that reopening the step
> resumes where you left off. It was briefly false — captures lived only in client
> state — and a peer fixed it with per-substep drafts
> (`StepExecution.capture_draft`). **Walked the doc's own scenario:** filled a
> capture, *Confirm & next*, **closed the tab entirely**, reopened the step — the
> values were restored and the draft cleared once the step was committed. The one
> nuance the doc does not state is that a substep is saved when the operator moves
> off it, not on each keystroke.
>
> **Docs queued against the skip retirement — do NOT write them early.** The peer's
> work is uncommitted, and HEAD still contains `skip_out_of_scope`, so
> `docs/workflows/reman/rebuild.md:269-276` (*"Out-of-scope steps are skipped, and
> the skip is recorded"*) is **correct today** and becomes false only on their
> commit. Rewriting it now would make the docs wrong about HEAD. On their commit,
> rewrite that admonition as the check/Repair-node behaviour and revisit
> `dwi/running.md` (traveler section; the "What happens next" blocker table wants a
> repair-hold row). Everything else in docs/ matching "skip" is an unrelated sense —
> skip-lot sampling, optional substeps, FEFO lot skipping, labour-model conditions —
> and stays correct. `training/shift-lead.md:428` cites "resolved scope" for
> over-and-above and also survives, since scope still plans the rebuild.
>
> **Demo-data gaps are collected in `DEMO_SEED_REQUIREMENTS.md`** (new,
> 2026-10-13). Several rows here are blocked not by a missing feature but by a
> missing *subject* — the mechanism is built and the demo has nothing to point it
> at. Six roles have no user; no FPI can be signed; no core awaits customer
> authorisation; the export-control denial side cannot fire; the change-control
> chain is unreachable from a fresh seed. Each is measured against live data and
> tied to the row it blocks, so the seed rewrite can close them deliberately.
>
> Still unwalked: **Auditor**, **Tenant Admin** and **System Admin**. Tenant Admin
> is the union of every other role; System Admin holds 3 platform permissions and
> is not a shop role.
>
> Two statements in this section have also aged out: Shift Lead now **has** a role
> guide (`docs/roles/shift-lead.md`), and the Home-block counts below predate the
> launchpad cards being added for Planner, Receiving, Shipping, Purchasing and
> Auditor.

### Interaction depth

From `ambac-tracker-ui/src/components/home/home-blocks.tsx`, which declares the
Home blocks each group receives — the application's own statement of what a role
does daily.

| Role | Home blocks | Role page |
|------|-------------|-----------|
| QA Manager | 13 | yes |
| Production Manager | 12 | yes |
| **Shift Lead** | **11** | **none** |
| Document Controller | 6 | yes |
| Engineering | 5 | none |
| Purchasing | 4 | none |
| Operator | 3 | yes |
| QA Inspector | 3 | yes |
| Auditor, Customer | welcome only | Customer only |

!!! note
    Block count is **not** depth. Operator gets three blocks because operators
    live inside the step player, not on Home. Their depth is in DWI.

**Shift Lead is the third-heaviest role in the application and has no guide.**

## Only code settles the Code column

Design documents in `Documents/` record **intent at the time of writing**, not what
shipped. They may not be used to mark a row supported.

Measured 2026-10-06, against code last touched in September:

| Document | Last changed | Age |
|----------|--------------|-----|
| `USER_DOCUMENTATION_PLAN.md` | 2026-02-19 | ~8 months |
| `WORKFLOW_ENGINE_DESIGN.md` | 2026-03-03 | ~7 months |
| `MES_BEHAVIOR_FLOWS.md` | 2026-07-13 | ~3 months |

`SCHEDULING_IMPLEMENTATION_PLAN.md` is the worked example of the hazard: it reads
as a description of what was built and describes a `Scenario` model that does not
exist. A staleness warning was added to it in `593ee8d` for that reason.

**How to use them anyway.** They are good at telling you *what to look for* — a
flow named in a design doc is a strong hint that a candidate row is worth
checking. They are worthless as evidence that it exists. Use them to generate
rows; use the code to resolve them.

`USER_DOCUMENTATION_PLAN.md` additionally predates reman, APS and the current
role set, and should carry its own staleness note.

## Candidate rows, and what the passes can prove

Rows marked **(candidate)** are workflows a reviewer suggested but nobody has
confirmed happen here. They are in the tables deliberately: the docs and code
passes will resolve most of them without anyone being asked.

**The evidence is asymmetric, so read a result carefully:**

| What the pass finds | What it proves |
|---------------------|----------------|
| Code implements it | The workflow is **real**. Settled. |
| Docs describe it | Real, and covered. Settled. |
| **Nothing anywhere** | Only that it is **not built** — never that it is not needed |

So a candidate that comes back empty is not an answer, it is a sharper question:
*does this shop do this, and in what way?* Those are worth collecting and asking
once, at the end, rather than guessing at individually now.

Two rows have already been removed this way rather than audited — a pause
primitive and a mid-step handover — because both assumed a unit of work this
shop does not have.

## Status key

| | |
|---|---|
| ✅ | Documented and supported |
| 📄 | Supported, not documented |
| 🚧 | Partly supported |
| ⚠️ | Supported with a caveat worth reading before relying on it |
| ❌ | Not supported |
| — | Not applicable to this row — out of the product's bounds by design, or deliberately another role's job. **Not a gap.** |
| ? | Not yet checked |

!!! note "`⚠️` and `—` were in use long before they were in this key"
    Added 2026-10-15. Both appear throughout the tables; neither was defined,
    which made the Code column unreadable at a glance — the thing the column
    exists for. If you add a marker, add it here in the same edit.

!!! important "The Code column answers *does it work*, not *can you show it*"
    A third state exists and has no column: **supported in code, not
    demonstrable on seeded data.** Those rows are green and correctly so — the
    application does the job — but nobody can watch it happen, which makes them
    invisible to a demo and **unteachable in a training track**.

    That distinction is the seed's worklist, and it is derived here rather than
    invented elsewhere. **As of 2026-10-15, eight rows are in that state:**

    | Row | Why it cannot be shown |
    |-----|------------------------|
    | Operator R2 | The finding capture is authored, but no demo core is at a step that raises one |
    | Operator R3 | Bench-side half needs a core on a work order with a settled scope |
    | Operator C1 | Rework refuses — the demo's rework step has no inspection substep to send a unit to |
    | Shipping 8 | Return customer property |
    | Shipping 9 | Both shipped work orders carry order lines, so neither the fallback nor the unmeasured count is exercised |
    | QA Manager R1 | Recording the customer's answer on over-and-above |
    | Engineering 4 | Authoring DWI substeps |
    | Document Controller 6 | No document has a review interval, so *due for review* is permanently empty |
    | QA Manager 10 | Gauge-exposure page is built, but no calibration FAIL record exists to open it from |
    | QA Manager R1 | Recording the customer's answer — no demo exhibit |

    **This list is not exhaustive.** It was assembled by reading, and a row only
    appears once someone notices. Add to it when you meet one; that is cheaper
    than a periodic sweep and more reliable than remembering.

    **Do not mark these ⚠️.** The caveat marker means the capability itself has
    a catch; these have none. Say it in the note and list it here.

!!! note "The Docs column was caught up on 2026-10-12 — and this warning outlived it"
    **Re-counted 2026-10-15: 130 of 131 rows now read ✅ in the Docs column.**
    The warning below was accurate when written and has since been overtaken; it
    is kept because the *lesson* is the point, not the state.

    The lesson: the help docs were written **against this audit**, and then
    nobody came back to flip the column — so a one-time derivation drifted into
    a to-do list that lied. The same thing happened again on 2026-10-15, when
    five rows went stale in a single day of fixing the things they recorded.

    **So: flipping the row is part of finishing the work, not a later pass.**
    A ledger nobody closes out is worse than no ledger, because it is believed.

    Original warning, which was true until 2026-10-12 —

    Many rows carry **Docs ⚠️** with a note ending *"Docs ⚠️: undocumented."*
    Those marks were made **before the help docs were written**. The help docs
    were then written against this audit, and nobody came back to flip the
    column.

    **Checked 2026-10-12: all 19 rows that explicitly say "undocumented" now have
    coverage.** Verified by reading, not grep, for the substantive ones:

    | Row | Now covered by |
    |-----|----------------|
    | Shift Lead R1 — pending finding | `workflows/reman/components.md` — accurate, incl. one-finding-at-a-time and the notes trail |
    | Shift Lead R2 / PM R1 — over-and-above | `workflows/reman/disassembly.md`, `rebuild.md` |
    | Shift Lead R3 — core exit | `workflows/reman/disassembly.md`, `overview.md` |
    | Receiving R2 — bulk core lots | `workflows/reman/receiving.md` §Bulk core lots — matches the walked strings |
    | Receiving 7 — put away | `workflows/supply/locations.md` |
    | Shipping 10 — subcontract | `workflows/supply/outside-processing.md` — Ready to ship / At vendor / Send out, shared inspection queue |
    | Scheduler 1–7 — the board | `workflows/scheduling/gantt.md` — Not scheduled, Dispatch, What-if, staleness, uncovered |
    | Scheduler 9 — non-working time | `workflows/scheduling/overview.md` §Calendar — closure / absence / overtime / recurring |
    | Purchasing 5 — scorecard | `workflows/supply/overview.md` §Supplier Quality |

    **The one genuine gap this pass found was fence zones** — Frozen / Slushy /
    Liquid appear in the Gantt legend and every task panel but were in no doc.
    Added to `gantt.md` with the real defaults (frozen 2 days, slushy 7).

    Corrections made to the help docs in the same pass: the stale *"Change
    Control is read-only"* warning, the approval types the system requests **by
    name** (and the exact-match group-name trap), the staging window being
    selectable rather than fixed 8h, what on-time % actually attributes through,
    and the customer-property half of the shipping board.

    **Update, later the same day:** the column has now been **re-derived for 31
    rows**, each verified by *reading the page*, not grepping — an early grep pass
    here was unreliable enough to be discarded (it pointed "delete a document" at
    `3d-models/annotations.md`).

    What that pass found, beyond the stale marks:

    | Wrong claim | Reality |
    |---|---|
    | `lot-tracking.md`: *"Select material lot to use"* | An operator **never** picks a lot. Consumption is automatic on step exit — staged lot first, then the customer's own property, then FEFO |
    | `operator.md`: can't *"create or edit orders"* or *"upload documents"* | An Operator **can** do both; the shared staff base is broad |
    | `library.md` classification tiers | Confidential and Restricted are held by **every** staff role; Secret is Tenant Admin + Document Controller **only** |
    | `compliance/reports.md`: CoC *"Planned"* | `ShipmentCocAdapter` is registered and the button is on every shipment |
    | QA Manager row 6: *"no way to record a declined CAPA"* | `NOT_REQUIRED` / `DEFERRED` exist with a **mandatory** reason, citing ISO 9001 10.2.1(b) |

    Newly documented from the walks: fence zones, deleting vs obsoleting a
    document, the selectable staging window, what on-time % attributes through,
    the supplier rating thresholds, scanning in the operator guide, Expedited
    being derived from priority with **no reason recorded**, automatic FEFO
    consumption, the CAPA decision, and make-up planning when scrap outruns the
    gross-up.

    **Completed the same day: all 131 rows re-derived, Docs is now 131/131.**
    Every row was checked against the page that covers it, by reading. Three more
    genuine gaps surfaced in the final pass and were written:

    - **Working when the terminal or scanner is down.** There is no offline mode;
      the paper traveller is the fallback, and it says so itself — *"the digital
      work order is the system of record"*, *"paper sign-offs are a fallback"*.
      Documented with the catch-up procedure, including entering the dates from
      the sheet rather than today's.
    - **Planned versus actual.** Capture is forward-looking and deliberately does
      not re-time the plan or trip staleness, so empty actuals usually mean the
      sequence (solve, *then* move a part) rather than a fault.
    - **Make-up planning** when scrap outruns the gross-up — planner-confirmed by
      design for AS9100/ITAR, and zero for a reman order, since a scrapped core
      cannot be replaced by spawning another.

    Two rows were covered in places the obvious search missed: the document
    **review period** is a document-*type* setting (`admin/setup/document-types.md`,
    which correctly notes a type with no review period never prompts one), and
    **voiding a completion** is in `workflows/dwi/running.md` with the right
    permission split.

    **Both columns are now trustworthy.** Code was walked; Docs was read.

---

## Operator

The unit of work is a **step**, not a job.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | See what to work next, and claim it | ✅ | ✅ | verified 2026-10-06 as `mike.ops`. Up next / Then / In progress / See everything ready |
| 2 | Identify the right physical unit (scan) | ✅ | ✅ | verified in the batch/load runtime — *"Scan each part into the load"*, Captured ✓. Docs narrower than the app (see DRIFT) |
| 3 | Prove qualification before starting, or be authorised | ✅ | ✅ | **verified live 2026-10-07** — refused, overridden by a supervisor, override recorded |
| 4 | Follow the instruction and record as you go | ✅ | ✅ | verified 2026-10-06 — DWI runtime: spec check, in-spec badge, attestation, review screen |
| 5 | Record which material lot was actually taken | ✅ | ✅ | **row misframed** — it's automatic FEFO on step exit, not an operator choice. 0 rows exist **LIT 2026-10-12** by seed phase 9 (`dark_exhibits.py`). `MaterialUsage` was **0 rows tenant-wide**; consumption now runs through `consume_for_step`, which resolves released BOM lines, honours shelf life and refuses another customer's property. Verified on the traveller: INJ-0042-005's Assembly row carries *Lot STOCK-CRI-SPR · Injector Spring · 1* and *Lot STOCK-CRI-SOL · Solenoid Coil · 1*. This also revives the traveller's recorded-values and overrides sections and the backward part→lot trace. |
| 6 | Report a problem mid-step | ✅ | ✅ | verified — **"Can't run this?"** is the live path (4 reasons, each routed to a named owner). The home *Report a problem* tile is dimmed preview |
| 7 | Work a batch another operator started | ✅ | ✅ | verified 2026-10-06 — batch claim dialog + **reassignment gate** fires live |
| 8 | Finish and move the unit on | ✅ | ✅ | **fix verified 2026-10-07** — lands on the work order, no live Complete step button |
| 9 | Account for time | ✅ | ✅ | verified — clock in/out/break/lunch writes a `SHIFT` TimeEntry. Note `approved:false` → an approval gate exists |
| 10 | See what I am qualified for, and what is expiring | ✅ | ✅ | verified — *My Training* + his own expiring cert. (He also sees manager tiles; API refuses him) |

!!! danger "Correction: there is no handover, and no pause — the unit of work is wrong"
    **Work is batched, and nobody stops half way through a part.** An operator
    completes some units of a batch and clocks out; another continues the batch.
    Each part carries its **own** `StepExecution` with its own `completed_by`,
    and `running.md` already distinguishes **per-part** records from **shared
    cycle** records (a wash or heat-treat load). So forty units and sixty units
    are a hundred attributed records with no transfer event between them.

    There is nothing to hand over because nothing was ever held. A pause state
    would record only that work stopped; this records who did which units.

    This row originally read "pause / hand over mid-step", and a review ranked
    the missing pause primitive as the top gap in the whole document. **Both were
    wrong**, and wrong the same way: reasoning from discrete long-cycle machining
    — one operator, one part, one long operation — rather than batch flow with
    per-unit attribution.

    **Assume that assumption contaminates other rows.** Anything phrased around a
    single part being worked, held, interrupted or transferred needs re-reading
    against batch flow before it is audited.

| 11 | Read and acknowledge shift notes and notifications at clock-in | ✅ | ✅ | **verified end to end 2026-10-07** — note received, MUST ACKNOWLEDGE, acked, recorded with name + timestamp |
| 12 | Be called over as the second person on someone else's gate | ✅ | ✅ | **verified live 2026-10-07** on both gates — training override and reassignment |
| R1 | Grade a component at teardown, with the part in your hand | ✅ | ✅ | **verified 2026-10-07** — Component Grading substep, walked end to end |
| R2 | Raise a finding at the bench when a reused part fails later | ✅ | ✅ | **Authored and reachable in principle; not demonstrable on current demo data (2026-10-08).** `rebuildFindingCapture` is now authored — step **Nozzle Inspection**, optional substep *"Report a component found worse (reman)"* (confirmed in `Substep.body_blocks`). But the demo's only core under rebuild, CORE-240210-0007, **does not have Nozzle Inspection in its resolved scope** (its 5 operations are Cleaning, Flow Testing, Assembly, Final Test, Packaging), so it never visits the step. The 7 units that ARE at Nozzle Inspection are ordinary parts, not cores, so a component finding has no subject there. The mechanism is proven to work from the other end — the seed raises one through `findings.record_finding` and Shift Lead R1 decides it. **What is missing is a rebuild whose scope includes the step the node sits on.** **WALKED END TO END 2026-10-13 — row closed.** Scope no longer routes a unit, so CORE-240210-0007 now *visits* Nozzle Inspection, and the full repair sequence ran: the check held the unit with *"A finding on **Injector Nozzle Assembly** … (grade C) is waiting on a lead's decision"*; a Shift Lead (`casey.dual`) applied it on the rebuild plan (toast *"Injector Nozzle Assembly: grade is now C"*); **the plan re-resolved from the applied finding**, flipping Expected repairs from `NZL-REPLACE / Needs approval` to `Nozzle Recondition / NZL-RECON / Goes ahead / Injector Nozzle Assembly: Grade C, from this unit` — a grade-C nozzle is reconditionable, so it stops needing replacement; the player's panel then showed **"This unit goes here"** on NZL-RECON; and completing the check routed the unit down the branch and back:

    Cleaning            COMPLETED
    Nozzle Inspection   COMPLETED   (check — routed on the applied finding)
    Nozzle Recondition  COMPLETED   (repair branch)
    Flow Testing        PENDING     (rejoined the main line)

The repair node's own instruction names the rejoin: *"Flow Testing comes next and proves the repair — you don't test it here."* |
| R3 | Work a rebuild step whose scope was only settled this morning | ✅ | ✅ | `scope.py` resolves it and writes nothing — **the derive-on-read claim is now confirmed in the browser**: the rebuild plan page renders operations + slots with a per-row *Because/Why*, and states it reserves and orders nothing. Bench-side half still not walked (needs a core on a work order with a settled scope).  **Re-checked 2026-10-12 — the bench-side half is blocked by DEMO DATA, not by the harness.** The tenant's only `IN_REBUILD` core, CORE-240210-0007 (*Rebuild & return*, Injector Reman), sits at **Cleaning with zero `StepExecution` rows** — the rebuild was released but no work has begun, so there is nothing at a bench to work and no out-of-scope step to observe being SKIPPED. Unlike the other dark exhibits this is not a row insert: it needs a core **walked into** rebuild work, which the seed can do and phase 9 deliberately does not (it populates records, it does not advance flows). **UNBLOCKED 2026-10-12 alongside R2.** The bench half needed an out-of-scope step to observe being SKIPPED; there is no such thing any more. What replaces it is the check/Repair-node outcome, which is a different and better observation: the traveler shows a branch not taken rather than an op walked past. Re-frame this row to that when the reseed lands. |

| C1 | Pull one unit out of a batch and send it back for rework | ✅ | ✅ | **RE-WALKED 2026-10-15 — the bug is gone; what remains is a seed gap, not a code one, so this is green and on the not-demonstrable list in the status key.** On WO-2024-0042-A as `admin@demo.ambac.com`: selected INJ-0042-020 and INJ-0042-022 (both IN_PROGRESS), pressed **Quarantine** in the bulk bar, and both went to QUARANTINED in the database while the unselected INJ-0042-024 stayed IN_PROGRESS — **the write lands and is scoped to the selection.** Test state restored afterwards. The button sends `status: "QUARANTINED"`, a valid `PartsStatus`, and `services/mes/parts.bulk_set_status` raises on anything invalid rather than passing silently, so the old string-vs-UUID symptom cannot recur in that form. <br><br>**Why this still is not green: Rework refuses**, and correctly — the demo's rework step has no inspection substep to send a unit to. That is **demo authoring, not product capability**, so the job is supported and simply undemonstrable until the seed authors one. It belongs to the seed work, not a bug list. <br><br>**A silent no-op is the one class of defect a code read cannot clear** — the absence of a write is not visible in the source — which is why this row needed driving rather than reading, twice. Original note: *Walked 2026-10-07 — found a bug. Quarantine returned HTTP 200 and wrote nothing — string-vs-UUID key bug in `_load_parts_scoped`, affecting all three bulk actions.* |
| C2 | Get an erroneous record corrected | ✅ | ⚠️ | **Walked 2026-10-07.** Operators cannot delete — 403 on DELETE across every model probed — which is correct: the escape hatch is a lead (Shift Lead C2, `void_substepcompletion`). Corrections themselves go through **`RecordEdit`**, whose own docstring is exactly this row: *"Used when records are edited (not voided) to maintain history of what was changed, by whom, and why."* It is written at **9 service call sites** (locations, material_lot ×4, shipping ×3, receiving_inspection) and the demo now holds 3 real rows, two of them from this audit's own walks (`storage_location/Moved`, `chase_note/Chased`, `promised_date/"Spoke to their scheduler…"`). **But `RecordEdit` is write-only: no viewset, no serializer, no URL, and no frontend reference anywhere.** The reason a record was corrected is captured and then unreachable outside the database. `django-auditlog` separately records the *change* and IS surfaced (part history / audit trail) — so the field, old value and new value are visible while the **why** is not. **Pairs with Shift Lead C1:** there, a reason is never captured; here, it is captured and never shown. <br><br>**Both halves moved on 2026-10-15, and the pairing predicted it.** Shift Lead C1 now *captures* a reason on a priority change (`5b9b6d0`), and the same work gave `RecordEdit` its **first read surface**: `WorkOrderSerializer.priority_changes` is a `SerializerMethodField` calling `services/mes/work_order.priority_changes`, so the work order response carries `[{from_priority, to_priority, reason, changed_by, changed_at}]` and the edit form lists the last five with their reasons. **So `RecordEdit` is no longer write-only — but only for this one field.** The other 9 call sites (locations, material lot ×4, shipping ×3, receiving inspection) still write a reason nothing reads. The row stays ⚠️ for that remainder, and the shape of the fix is now known rather than theoretical. |
| C3 | Work when the terminal or scanner is down, and catch up after | ✅ | ❌ | **Answered 2026-10-07 — and this one is settled intent, not an accidental gap.** **Catch up after: deliberately refused.** `StepExecution.entered_at` carries the decision in the model: *"Deliberately auto_now_add — NOT backdatable (user decision 2026-10-07). It is traceability evidence: when the part really reached the step. Making it writable would let any code path, and the serializers, rewrite execution history. History from the ERP at go-live, if ever needed, goes through a separate import path that marks rows as imported — this is why the earlier go-live-history feature was removed."* **Work while down: not supported.** No service worker, no PWA plugin, nothing in `public/`, no `navigator.onLine` handling, no offline mutation queue. `queryClient` sets `networkMode: 'offlineFirst'` with a 60s staleTime, so cached **reads** survive a brief drop — **writes do not**. So the honest answer is: the floor stops, and the work is entered when the terminal returns, at the time it is entered. **This is the one row where absence IS the answer** — the backdating half is a recorded decision, and the offline half follows from it: an offline queue would be a backdating mechanism by another name. ~~**Docs ❌: should be written down as a stated limitation, not left for a customer to discover.**~~ **Done — `workflows/dwi/running.md` states it plainly: there is no offline mode, the player needs the server, and when the terminal or network is out "work does not stop — the paper traveller does." Verified 2026-10-15.** |

## QA Inspector

The unit of work is a **decision** — but not the one I first wrote down. The
verdict is **derived**: a measurement crossing its spec quarantines the part,
writes a FAIL quality report and auto-creates a disposition. There is no
Pass/Fail button. *The spec is the judge.*

Rebuilt against `QA_INSPECTOR_TRAINING_SCRIPT.md` (Aug 2026), whose eleven
journeys are an independent derivation of this same list. Its companion is
`UQMES_ONBOARDING_WALKTHROUGH.md` — the self-serve read to this taught version.

### Where work arrives

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Read the home page | ✅ | ✅ | FPI banner · Inbox chips (All/Receiving/OSP returns/In-process) · My quality actions · Your gauges |
| 2 | Scan to navigate | ✅ | ✅ | every scan resolves to the **parent work order** |
| 3 | Receiving inspection, and clear the paperwork holds | ✅ | ✅ | *Accept lot / Reject lot*, not "complete step"; self-clearing holds resolve here |
| 4 | First-piece buy-off | ✅ | ✅ | a **batch gate**; SoD — the operator signed the substeps, so QA signs the buy-off |
| 5 | A sampled in-process inspection | ✅ | ✅ | the workflow is answering **"why this part?"** — the plan and sample size are generated |
| 6 | OSP return inspection | ✅ | ✅ | before it rejoins the routing; unified queue = purchased + OSP |

### The core — "the one to protect"

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 7 | An out-of-spec reading quarantines the part and raises its disposition | ✅ | ✅ | derived, not chosen |
| 8 | Work the disposition — **the decision needs a co-sign** | ✅ | ✅ | inspector lacks `approve_disposition`; manager authenticates on the inspector's screen (AS9100 8.7) |
| 9 | Close the disposition — this one is yours | ✅ | ✅ | **verified 2026-10-07** — refusal names BOTH missing things in one message |
| 10 | Re-inspect after rework, history first | ✅ | ✅ | exhibit correctly poised (FAIL → CLOSED REWORK → AWAITING_QA); **could not confirm it surfaces in the inbox** |

### Alongside

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 11 | Work a CAPA task; author a verification plan; initiate one for a pattern | ✅ | ✅ | outcome needs `verify_capa` — manager. Disposition = this part, CAPA = the pattern |
| 12 | Check a gauge's calibration before using it | ✅ | ✅ | *Your gauges* tile is the point-of-use nag |
| 13 | Read a finished record and narrate it backward | ✅ | ✅ | red flag: QUARANTINED/SCRAPPED with no QR or disposition behind it |

### Reman

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| R1 | Accept or reject a harvested component into stock | ✅ | ✅ | **Walked 2026-10-07 as maria.qa.** `/reman/components` → row menu offers *View Source Core / Accept to Inventory / Scrap Component*. Accept dialog states the customer-property rule in plain words: *"It becomes a part in stock. If its core goes back to its customer, the part is reserved for that core and can't go into anyone else's rebuild."* Confirmed → status **Pending → In Inventory**, Part ID issued. Two small blemishes (neither a defect): no success toast, unlike every comparable flow; and the generated serial `HC-CORE-240215-0006-BODY01A1171B` appends a raw UUID fragment. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |

!!! note "Three rows removed, with reasons"
    - **Know the sample size / accept-reject rule** — generated and displayed, not
      decided. Became part of #5.
    - **Record measurements**, **confirm the gauge is in calibration** — steps
      inside an inspection, not workflows. Calibration survives as #12, the
      before-use habit.
    - **Inspect a core on arrival** — **not inspector work.**
      `incoming_inspection.py:30` filters `.filter(holds_cores=False)`, so core
      lots never enter the queue. The condition grade is set by whoever receives
      the core.

    Also dropped: *put a lot on hold / release it* as a standalone row — holds are
    met and cleared inside #3, and releasing a judgement hold is a manager's act.


!!! warning "Table back-filled 2026-10-07 — rows 9 and 10 remain genuinely unaudited"
    These marks were reconstructed from the Findings below, which were written as
    the pass happened while the table was not kept in step. Every ✅ above points to
    a named finding; **rows 9 (close the disposition) and 10 (re-inspect after
    rework, history first) were never walked** and keep their `?`.

    Row 2 is ⚠️ on docs because of the scan-box drift; row 13 is ⚠️ because the
    record reads back but, as QA Manager row 11 records, there is no step-by-step
    history behind it.

    **The lesson is about the artifact, not the work.** A table left at `?` while
    the prose fills up makes a finished pass look untouched — the at-a-glance view
    is the thing anyone actually reads. Mark the row when the row is done.

## Shift Lead

The unit of work is the **shift**.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | See the shift's state at a glance | ✅ | ✅ | **verified 2026-10-07** as `casey.dual` — biggest fire, late jobs, quarantine, CAPAs, OSP, training |
| 2 | Put people on jobs | ✅ | ✅ | **Unblocked and walked 2026-10-12** — the earlier note (*0 ScheduledTasks — never solved*) is stale; there are now **2,849 tasks across 5 solves**. Walked as `casey.dual`: the board renders every resource as a lane, a task panel gives work order / due date / machine / work centre / operator / fence zone / live status, and **Reassign** is honest about scope — *"Reassign — applies now, re-solve to optimize"*. The operator picker is **filtered by eligibility** (work-centre membership), not a flat list. |
| 3 | Cover an absence or no-show | ✅ | ✅ | **Unblocked 2026-10-12**, same surface as row 2. Worth teaching as a diagnostic: an **empty operator picker is a training problem wearing a scheduling costume** — nobody is qualified and rostered for that work centre. |
| 4 | Unblock a stopped job | ✅ | ✅ | the Control Center **Exceptions** tab — unified 21 items, each with its impacted WO and a direct link |
| 5 | Authorise an unqualified operator, on the record | ✅ | ✅ | **verified 2026-10-07** via the Operator pass — override recorded with both names, reason and timestamp |
| 6 | Triage a quality event without escalating everything | ✅ | ✅ | Exceptions tab: source, severity, age, owner, *Open only* filter, bulk resolve |
| 7 | Watch what is going late | ✅ | ✅ | *Jobs going late (2)* on the hero + **Overdue / Due today** filters in the Control Center |
| 8 | Hand over to the next shift | ✅ | ✅ | **verified end to end 2026-10-07** — NOT weak: audience targeting, priority, acknowledgment tracking |
| 9 | See who is qualified for what | ✅ | ✅ | training matrix (verified under QA Manager row 8) + current/expiring/expired on the hero |
| 10 | Escalate what the shift cannot solve | ✅ | ✅ | **Report exception** on the Exceptions tab; existing items carry source and severity |

| R1 | Decide a pending finding — apply or dismiss | ✅ | ✅ | **Walked end to end 2026-10-08, after the reseed authored the capture nodes.** `PendingFindingsCard` rendered for the first time in this audit: *"1 finding to decide — Raised at the bench after teardown. Nothing below has changed the plan yet — applying one re-grades the component, and this plan re-resolves from it."* Injector Body, **Grade A → B**, *"Light pitting on the seat face, visible only after cleaning"*, attributed to Lisa Park with a timestamp. **Apply** → toast `Injector Body: grade is now B`, card cleared. Verified in the DB: `condition_grade` A→B, `proposed_grade` emptied, and the application appended to `condition_notes` as a trail. **Dismiss** is offered beside it (takes a reason). ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| R2 | Request customer authorisation for over-and-above | ✅ | ✅ | **Walked 2026-10-07.** From an IN_REBUILD core the card offers **Authorise…** → status becomes *Awaiting customer authorisation*. `send_for_authorisation` refuses when nothing exceeds the sold rebuild level (*"Nothing on … goes beyond the rebuild level that was sold, so there is nothing to authorise"*) — it compares resolved scope against the `RebuildScopePreset`. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| R3 | Decide a torn-down unit's exit: rebuild, harvest, or return | ✅ | ✅ | **Walked 2026-10-07 after fixing the teardown dead-end.** A DISASSEMBLED core offers **Rebuild to stock** / **Release to inventory**, each with a tooltip explaining the consequence (identity kept and stocked as reman FG, vs components accepted and the core consumed). Chose rebuild → **In Rebuild**. The third exit (*return*) is unreachable — no `REPAIR_RETURN` core exists. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |

| C1 | Jump a job to the front, with a reason | ✅ | ✅ | **BUILT 2026-10-15 (`5b9b6d0`) — the second half now exists.** A priority change requires a reason and refuses without one (`services/mes/work_order.change_priority` raises *"Say why the priority is changing"*), writing a `RecordEdit` with field/old/new/reason/who/when beside auditlog's who-and-when. The edit form asks *"Why change priority from Normal to Urgent?"* and lists the last five changes with their reasons. **Residual:** a CSV import or the master workbook still changes priority with no reason recorded. Docs updated in `5c006f3`. Original note: Walked 2026-10-07, the first half works, the second doesn't exist. There is no expedite *action*: **Expedited is derived**, `w.priority === 1` (`WorkOrdersControlCenterPage.tsx:280`), i.e. `WorkOrderPriority.URGENT`. Jumping a job = setting priority on the work order. Verified live: PATCH priority 2→1 → the Control Center's **Expedited** tile went **0 → 1**; reverted to 2. `change_workorder` is held by every operational role incl. the Shift Lead (dave.wilson); only the customer lacks it. **“With a reason” is unsupported.** No reason field on the WO edit form, none on the API, and no expedite service. `django-auditlog` records the change — `{'priority': ['2', '1']}`, actor *Maria Santos*, timestamped — so **who, when and what are kept; why is not.** Contrast the rest of the app, where consequential changes carry a reason (hold, scrap, reject, ship-back, rollback). ~~**Decision needed:** either accept priority-with-no-justification, or give expedite the reason the other consequential actions already take.~~ **Answered 2026-10-15 — the second option was taken; see the top of this row.** |
| C2 | Void an operator's bad record | ✅ | — | **NOT THIS ROLE, BY DESIGN — and the row was wrong, corrected 2026-10-15.** The *product* supports voiding; the **Shift Lead does not hold it, at all**. `VOID_COMPLETION_PERMISSIONS` goes to `tenant_admin`, `qa_manager` and `qa_inspector`, and it is withheld from Operator, Shift Lead **and** Production Manager on purpose: performing or supervising the work and adjudicating the record are different jobs (`workflows/dwi/running.md`). A lead who needs a record retracted escalates — which is **R10**, not this row. `roles/shift-lead.md` has always listed it correctly under what is not yours, so the docs were right and this row was not. Marked `—` rather than ❌ because the capability exists and is simply somebody else's; ❌ would read as a product gap. Original note, which was the error: *holds `void_substepcompletion` only, narrower than the row implies*. |
| C3 | Take a machine out of service and re-plan around it | ✅ | ✅ | holds `change_equipments`; the *re-plan* half needs a solved schedule |

## Shift Lead — first pass (2026-10-07)

Walked as **`casey.dual`**, seeded as a deliberate dual-role persona — *"Inspector
by day, Shift Lead when covering"*. Logging in lands on the **QA Inspector** home;
a persona combobox in the header switches to Shift Lead. That picker is the right
answer to a real problem (one person, two jobs) and is worth documenting — the
role guides currently read as though a person has one role.

### VERIFIED — the shift-lead hero answers "what needs me right now"

> **Biggest fire** — WO-SHOWCASE-01, high, due today · *Open control center*
> **Work orders 10** · **Jobs going late 2** · **Needs attention 2**
> Parts in quarantine **13** · CAPAs pending verification **2**
> Outside processing: out at vendors 1, ready to ship 1
> Training: current 22, expiring soon 1, expired 1

One screen, and every number is a link into the thing it counts. Rows **1**, **7**
and most of **9** fall out of it. Screenshot:
`docs/assets/shift-lead/sl-01-home.jpeg`.

### VERIFIED — the Control Center Exceptions tab is the triage surface

**Unified · 21 items** across quarantines and CAPAs, each carrying source,
severity, age, owner and — the part that makes it a *shift lead's* view rather
than a quality view — **"Impacts 1 WO: WO-2024-0042-A"**. Filters for *Open only*,
source, severity and *Oldest first*; **Report exception**; bulk select with
**Bulk resolve downtime**.

Rows **4**, **6** and **10** are all served here. Screenshot:
`docs/assets/shift-lead/sl-02-exceptions.jpeg`.

**Method note — fourth near-miss avoided.** A scripted click on the Exceptions tab
left it `aria-selected="false"` with its panel `hidden`, which reads exactly like a
broken tab. A **real trusted click** switched it immediately. Radix tabs, like the
signature pad earlier, do not respond to synthetic events. *Before filing any "this
control does nothing", retry with a trusted click.*

### NOT A FINDING — the persona picker's extra option is a deliberate supervisory preview

I flagged that Casey's picker offers **Operator** when she is seeded only as
QA Inspector + Shift Lead. **Checked: intentional, and explained in the code.**
`home-blocks.tsx:1436`:

```js
/** Supervisory preview: roles that oversee a floor surface can switch Home to
 *  it without being members of that group — the one Home link is everyone's
 *  home (an admin/lead reaches the operator surface via the persona picker,
 *  not a separate nav entry). */
const SUPERVISOR_PREVIEW = {
    "Tenant Admin":       ["Operator", "QA Inspector"],
    "Production Manager": ["Operator"],
    "Shift Lead":         ["Operator"],
    "QA Manager":         ["QA Inspector"],
};
```

A lead can see exactly what their people see. It is the gates-derivation idea
expressed in the UI, and it is why there is one **Home** link rather than a nav
entry per surface. Nothing to change.

**The real gap here is documentation, which is goal 1 territory.** No role guide
mentions the persona picker or supervisory preview. Three things follow that the
docs currently get wrong by omission:

- A person can hold **several roles** — `casey.dual` is seeded deliberately as
  *"Inspector by day, Shift Lead when covering"*. The role guides read as though a
  user has exactly one.
- **Landing is a choice, persisted** per user in localStorage, so two people in the
  same group can legitimately see different home pages. A support answer of
  "everyone with role X sees Y" is wrong.
- A supervisor **previewing** a floor surface is not the same as holding that
  role — the picker grants the *view*, not the permissions. Worth stating plainly
  so nobody reads the Operator landing as evidence a lead can do operator actions.

## Receiving

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Know what is expected | ✅ | ✅ | **lit 2026-10-07** — *On order 3 / Late 2* chips on Materials; 3 ON_ORDER lots seeded |
| 2 | Receive a delivery | ✅ | ✅ | **walked end to end 2026-10-07** — booked in 180 of 200, new lot number, auto-routed to inspection |
| 3 | Verify against the paperwork | ✅ | ✅ | the unified **Incoming Inspection** queue — purchased + OSP, one runtime for both |
| 4 | Handle a short or over delivery | ✅ | ✅ | **lit 2026-10-07** — RCV-MAT-0004 is 40 of 60 ordered, BACKORDERED |
| 5 | Resolve holds | ✅ | ✅ | verified in the QA Inspector pass — RCV-MAT-HOLD shows **Held**, multi-hold panel matches the docs |
| 6 | Reject and return | ✅ | ✅ | **Walked end to end 2026-10-07 as maria.qa (QA Manager).** `Reject remaining stock…` → *Return to supplier* + reason → toast `Rest of lot RCV-MAT-0005 rejected · disposition opened` (On hand 4→3, Rejected 1→2). **Ship back** then appeared → RMA number, *Print RTV sheet*, carrier/tracking, *The supplier is sending replacements* + date → `Lot RCV-MAT-0005 shipped back to the supplier.` (Rejected 2→1, **On order 3→4**). The replacement expected delivery `ONORDER-PO-2026-0005` (120 EA, promised 2026-10-21) was created automatically — the return→replacement→chase loop closes. Boundary held: *"Any credit is settled in your ERP."* **Permission gate verified both ways:** `reject_whole_lot` — present for maria.qa (QA Manager) and the tenant admin, absent for sarah.qa (Inspector), jennifer.mgr (PM), mike.ops, dave.wilson, casey.dual. As mike.ops the menu item is simply not rendered. ~~**Docs ⚠️: none of this is documented.**~~ **Covered — `workflows/supply/overview.md` and `roles/receiving.md`. Trailer cleared 2026-10-15.** |
| 7 | Put away and find again | ✅ | ✅ | **Walked end to end 2026-10-07 (verified first-hand, not taken from the peer's report).** `/production/locations` lists 6 locations with live Lots/Units/Machines counts and a drag-to-nest hint; Receiving Dock carries a *Receiving dock* flag. **Put away:** lot menu → *Move…* → dialog scoped to the lot (*"Now in Receiving Dock. Scan the destination's label or type it."*), destination as a native datalist, quantity optional (*blank moves all 500 EA*) so partial putaway works → toast `Lot RCV-MAT-0003 moved to Main Stores.` **Find again:** the location detail then lists it *here* and the ledger records **`In · RCV-MAT-0003 · from Receiving Dock · Maria Santos`** with a timestamp. Empty states are honest throughout (*"No serialised units here"*, *"Nothing moved in or out"*). Refusals are good too — a bad destination returns **`“MainStores” isn't one of your locations.`**, quoting the input in plain English. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 8 | Count stock | ✅ | ✅ | built (blind + applied) but **0 CycleCounts exist** — dark exhibit **LIT 2026-10-12** by seed phase 9 (`dark_exhibits.py`). `CC-2026-0001` is started blind at Main Stores, two lots counted with one deliberately one short, and **submitted but not applied** — applying needs `apply_cyclecount`, a lead, so both halves of the workflow stay exercisable. |
| 9 | Chase a late delivery | ✅ | ✅ | **lit 2026-10-07** — RCV-EXP-0103 chased; UI shows *"first promised 2026-10-02"* beside the new date |
| 10 | Hand receipts to the ERP | ✅ | — | **Rewritten 2026-10-15; the old note asked for exactly this.** The row as first drafted assumed a system-to-system hand-off. There isn't one and there is not going to be: **Glovia is human-bridged** — the ERP it has to reach dates from 1996 and cannot be integrated with, so every exchange is a person carrying a sheet of paper. That is a deliberate boundary, not a missing feature, and the integration backlog behind it was parked by the user on 2026-10-05. **What UQMES owes this job is therefore a document, not a feed**: receipts have to be legible and printable by someone who will key them in elsewhere. Judge the row on that, and mark it a gap only if the paperwork is unfit for a human to carry. |

| 11 | Stage and kit material to the bench for the next shift | ✅ | ✅ | **Walked 2026-10-08, unblocked by the solve.** `/production/staging` now lists the next 8 h of scheduled work per station — Assembly Cell, Grading Bench, Machine Shop, Pack & Ship, Teardown Bay — each job with its WO, step, part type, unit count and a relative time (*now*, *in 58m*, *in 3h*), and each material line with quantity, source lot and location (*Injector Spring ×2 · STOCK-CRI-SPR · Main Stores*). Optional lines are marked. Steps consuming nothing say so rather than showing an empty table. **Confirm** staged a line → station went **0/1 → 1/1 staged**, the row became *took 2 · STOCK-CRI-SPR*, and it recorded **"Staged by Jennifer Walsh"**. **Took another** handles the picker grabbing a different lot. It also carries the staleness warning: *"The schedule is stale — these times may have moved. Re-solve before staging to them."* **Re-walked 2026-10-12, and found the trap:** the window defaults to **next 8h**, and 2026-10-12 is *Labor Day* in the plant calendar, so the page reads *"Nothing scheduled in this window. Try a longer window, or check the schedule board."* and looks broken. At **24h** it is full — *Assembly Cell · 2 jobs · 0/2 staged*, WO-ASSESS-004 at 05:59 AM with `Injector Spring ×4 · STOCK-CRI-SPR · Main Stores` and an **(optional)** seal kit. This doubles as the **fastest proof a calendar exception reached the solver** (Scheduler row 9). **Docs: now covered in `docs/training/receiving.md` Module 8 and `docs/training/planner.md` Module 5.** |
| R1 | Receive a core | ✅ | ✅ | **walked 2026-10-07** — scan identity band, photograph as received, grade arrival condition, sign off |
| R2 | Receive a bulk core lot and identify units from it | ✅ | ✅ | **Walked end to end 2026-10-07.** `/reman/core-lots` had an honest empty state (*"No bulk lots waiting… received here with Receive in bulk"*). **Receive in bulk** → *"A counted delivery with no serials. Units are given identities later, one at a time, and are exchange cores."* The core-type picker offered **only** Common Rail Injector — the lot must be of a type cores were received as, or with a disassembly BOM, so purchased stock can't be counted into the core bank. Received 40 → `Received CORELOT-2026-0001: 40 × Common Rail Injector`, listed **40 / 40** unidentified at Receiving Dock with the reference beneath. **Identify a unit** → grade (A/B/C/Scrap), source, serial, notes, plus an **Identify and next** for working down a pallet → `CORE-2026-0001 identified from CORELOT-2026-0001`, count **40/40 → 39/40**. **Verified in the DB:** core RECEIVED, grade B, serial `MFS-INJ-440219`, part CORE_BANKED, `fulfilment_mode=EXCHANGE` (enforced — *"definitional, not shop policy"*), and **`part.received_in_lot → CORELOT-2026-0001`**, so the trace back to the receipt holds exactly as the module claims. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |

## Shipping

> **Rows 1–7 and 9 walked 2026-10-08 once the reseed landed.** Row 8 remains open. — the shipping code is complete
> and coherent; no seeded route can reach it. Re-walk once the two processes are
> authored with a `SHIPPED` terminal.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | See what is ready | ✅ | ✅ | **Walked 2026-10-08, after the reseed.** `/production/shipments` — header states the boundary: *"What can go to customers now, and what has gone. Invoicing stays in your ERP."* Tabs **Ready to ship (6)** / **Shipped**, grouped by order with the customer named (ORD-2024-0042 · Midwest Fleet Services), columns Serial / Item / Work order / Line · due / Waiting at. |
| 2 | Confirm it passed and is complete | ✅ | ✅ | **Walked 2026-10-08.** Each unit shows *Waiting at: Ship step*, and the ship dialog states the release check in words: *"Each part at a Ship step completes it, so its sign-off checks must be done."* — the ISO 9001 §8.6 gate runs through `advance_part_step` exactly as it would for one part. |
| 3 | Create the shipment | ✅ | ✅ | **Walked 2026-10-08.** Selected 3 units → **Ship …** → `SHP-2026-000003 shipped to Midwest Fleet Services.`, landing on the shipment detail. |
| 4 | Produce the paperwork | ✅ | ✅ | **Walked 2026-10-08.** Shipment detail offers **Packing list**, **CoC**, **Edit paperwork** and **Void…**. Paperwork block shows Carrier, Tracking, ERP shipper / packing slip, Expected delivery; Units table lists each serial with its WO and order; History records CREATED with actor and time. |
| 5 | Ship partially | ✅ | ✅ | **Walked 2026-10-08.** Per-unit checkboxes; **Ship …** stays disabled until something is selected. Shipped 3 of 6 → board recounted **Ready to ship (6) → (3)** with the correct three (014/015/016) still waiting. |
| 6 | Record carrier and tracking | ✅ | ✅ | **Walked 2026-10-08.** Carrier `FedEx Freight`, tracking `7742 9910 3356`, ERP slip `PS-2026-00841`, all recorded and shown. Tracking is explicitly *(can add later)* and **Edit paperwork** exists for it — the dock often ships before the number comes back. |
| 7 | Undo a mistake | ✅ | ✅ | **Walked end to end 2026-10-12.** The earlier pass inspected the affordance but did not execute it, to avoid disturbing freshly staged data; that reason has expired. To keep the seeded history intact I **shipped a unit specifically to void it**: INJ-0042-011 → `SHP-2026-000003`, then **Void…** with a reason. The dialog states the distinction exactly — *"For a shipment recorded by mistake — the parts didn't go. They return to their Ship step (sign-off runs again) or to stock. Goods that went and came back are a return, not a void."* After voiding: header reads **SHP-2026-000003 Voided**, the reason is kept on the record, History retains CREATED, and **in the DB INJ-0042-011 is back to IN_PROGRESS at the Ship step with `customer_shipment: None`** — the promise in the dialog holds. SHP-2026-000001/2 untouched, so the demo is net unchanged. |
| 8 | Return customer property | ✅ | ✅ | **Walked 2026-10-08 — and my earlier block reason was WRONG.** This never depended on a `SHIPPED` terminal: the shipping board has a second half for **lots**, filtered on `owner__isnull=False`, independent of any ship step — *"A customer's own material, still here: it can go back to them, grouped under them."* It was blocked only because **0 of 13 demo lots have an `owner`**. Set one temporarily and the board grew a dedicated **Customer property · \<customer\>** group with its own Ship action and columns *Their material · lot / Here / Location*; the dialog is lot-aware (*"Ship 1 lot… Blank quantity ships the whole lot; less splits that much off and the rest stays"*), so partial return works. Reverted after. `MaterialLot.owner` is a developed concept citing **ISO 9001 §8.5.3** in the model and enforced throughout — consumption draws customer property only for that customer's work, requirements never cover anyone else's demand, dock metrics exclude it from receipts, and the lot label prints it *"so nobody draws it into someone else's job"*. **Remaining gap is demo data only: seed one customer-owned lot.** **LIT 2026-10-12** by seed phase 9 (`dark_exhibits.py`). `RCV-MAT-0005` is now permanently owned by Midwest Fleet Services, so the board's **Customer property** group renders on a fresh seed rather than needing a hand-set owner and a revert. |
| 9 | Know whether we are on time | ✅ | ✅ | **FIXED 2026-10-15 (`e81d371`).** `delivery_performance` falls back to the work order's own `expected_completion` where there is no order line, and returns an `unmeasured` count for shipments carrying no date at all instead of filtering them out of the query. **The silent exclusion was the defect** — the page reported a confident percentage of whatever happened to carry order lines, which reads as covering everything shipped. The Shipping page now shows "N not measurable" beside the figure. Five tests in `test_customer_shipping.py` cover the fallback, a late fallback, the unmeasured count and a key collision that would have folded two line-less work orders on one shipment into a single delivery; **live demo data exercises none of them**, since both shipped work orders carry lines, so those tests are the only evidence. Docs `b5c3e7b`, `f24bc93`. <br><br>**How it got here, in order.** *2026-10-08* — measured unmeasurable: `{deliveries: 0, on_time_pct: None}` against 24 shipped units, because it keyed on `work_order__order_line__due_date` and **0 of 18 work orders had an order line**. Read at the time as a demo-data gap rather than a product one. *2026-10-12* — **LIT** by seed phase 9 (`dark_exhibits.py`): 14 dated `OrderLine`s seeded, 14 of 18 work orders pegged to one, and the figure became `{deliveries: 2, on_time: 2, on_time_pct: 100.0}`. *2026-10-15* — seeding the data had hidden the real fault rather than fixing it: a 100% from two deliveries, with four work orders still invisible, is worse than a dash. **Root cause of the original emptiness, still worth knowing:** migration 0178 backfills lines onto orders that existed when `OrderLine` was introduced, but it is one-shot history repair and `seed_demo` creates its orders afterwards — so every fresh seed produced line-less orders. |

| 10 | Send parts out to a subcontract vendor, and record them back | ✅ | ✅ | **Walked 2026-10-07** on WO-2024-0042-A. `OutsideProcessPanel` on the WO Control page: *2 at vendor · 1 to inspect*. **Send out** → dialog (vendor preselected, *PO / packing-slip reference*, qty `2 of 2 ready`, optional pick-specific-units) → toast `OSP-2026-000004 — 2 parts sent to Apex Plating Co`, panel recounted to *2 at vendor · 0 ready*. **Receive back** and **Inspect** both route into the **operator substep runtime** (`/operator/steps/…/substeps?execution=…&osp_shipment=…`) — the return inspection *is* a step execution, not a side dialog. That runtime is **properly authored**: Coating Thickness `12 +3 −2 µm`, photo capture, Pass/Fail/Pending result, and a required signature. **CORRECTION 2026-10-13 — this row was marked complete on a claim I conflated.** The shipment closes; **the parts do not move on**. `accept_return` sets every shipped part to `READY_FOR_NEXT_STEP`, completes the executions and closes the shipment, but never calls the advancement engine — despite its own docstring saying it *"advances the shipped parts past the OSP step"*. `try_advance_lot` then refuses with `['No active StepExecution']`, because the execution is already COMPLETED. Measured: **OSP-DEMO-005, OSP-DEMO-006 and CORE-240210-0007 are all stranded at Nitride Coating** with no flow out; only the control page's manual step dropdown moves them, which bypasses the gates. **What I verified and what I assumed:** I confirmed the shipment reaches CLOSED and the return inspection records — both true. I did not check that the units left the step, and asserted end-to-end completion from the shipment status alone. *"The shipment closed"* and *"the parts moved on"* are different claims. **CORE-240210-0007 was moved past Nitride Coating by MANUAL OVERRIDE** (control page step dropdown), with the user's approval, so the rest of its route could be walked. **That hop verifies nothing about advancement** — it bypasses the gates by design. `OSP-DEMO-005` and `OSP-DEMO-006` are deliberately left stranded as the reproduction. The real test is a reseed plus a fresh OSP return once `accept_return` calls the advancement engine. **Lesson for this audit: a row is walked when the SUBJECT moves, not when the surface reports success** — the same mistake shape as `complete_step` returning 200 on a refusal. **Re-walked 2026-10-13 after the reseeds, shipment side only — `OSP-2026-000002` is CLOSED.** The panel shows both halves at once (*1 at vendor · 1 to inspect*), with **Receive back** on the shipment still out and **Inspect** on the returned one. Coating Thickness 12 µm against `12 +3 −2 µm` read **In spec**, result Pass, sign-off captured, **Accept return**. **Completion first walked 2026-10-12, closing this row end to end.** The stated blocker — *"`react-signature-canvas` can't be driven synthetically"* — was wrong; there is no canvas on the node (see the corrected summary note). Recorded Coating Thickness **12.5 µm** against `12 +3 −2 µm` → panel read **In spec**, result **Pass**, *Return inspection sign-off* signed, then **Accept return** (the review screen's action here is `Accept return`, not `Complete step` — the OSP return has its own verb). Verified in the DB: the `SubstepCompletion` landed, and **`OutsideProcessShipment OSP-2026-000003` moved to `CLOSED`**. So send out → at vendor → inspect → accept is walked in full. ~~**Docs ⚠️: subcontract/outside processing appears in no doc at all** — another instance of unmentioned capability.~~ **Covered — `workflows/supply/outside-processing.md` is a page of its own. Trailer cleared 2026-10-15.** |
| R1 | Return a rejected core to its owner | ✅ | ✅ | **Unblocked by the reseed, but not completable with this tooling (2026-10-08).** The demo now has a REPAIR_RETURN unit — CORE-240210-0007, `returns_to_customer=True`, IN_REBUILD on Injector Reman. `return_to_customer` needs REBUILT or DECLINED; REBUILT is reached by finishing the scoped rebuild route (`complete_rebuild` via `finish_route`). That route's last step, **Final Test**, carries a `signature` substep (*Final leak / pressure test*). **The stated blocker was wrong (corrected 2026-10-12):** there is no `react-signature-canvas` on that node — it is a one-click attestation, and it was walked end to end on TRAIN-001-008 (value 200 bar in spec, result PASS, *Release sign-off* signed, **Complete step** accepted). The part then correctly **stayed** at Final Test, held by the step's pending FPI, which is exactly what `running.md` and `operator.md` claim. So the mechanism is walked. **What actually blocked this row was the rebuild-scope deadlock (see the summary), not the signature** — the unit could not leave Cleaning at all, and my own 2026-10-12 note that 'only 5 remaining operations' stood in the way was itself wrong: there was no route forward. That defect is now fixed in a peer's tree and the core advances again. The row stays open only until the demo process is reseeded with Repair nodes and the unit is walked to REBUILT. Service, precondition and UI all verified present. |
| R2 | Ship a rebuilt unit with a cert describing what was replaced | ❌ | ❌ | **WALKED 2026-10-13 — and the join does not exist. A product gap, not an unwalked row.** All three pieces are present and never meet: (1) **the as-built record exists** — walking CORE-240210-0007 to REBUILT produced two `AssemblyUsage` rows, both naming the unit's OWN components (*"Injector Nozzle Assembly from Core CORE-240210-0007"*, *"Control Valve Assembly from …"*), recorded at Assembly by the operator, so the repair-and-return rule holds as designed; (2) **the CoC exists**, in `reports/adapters/shipment_documents.py`, whose docstring is explicit — *"Both are built from one `CustomerShipment`"*; (3) **but `return_to_customer` creates no `CustomerShipment`** — it sets the stage RETURNED, the part SHIPPED, stamps `returned_at`/`returned_by`, and stops. The returned core is on neither shipment in the tenant. **So a repair-and-return unit goes back with no document route at all** — no packing list, no CoC, and no way to hand over the as-built list the system just recorded. The paperwork is shipment-scoped and a return is not a shipment. For a reman shop that is the sharp end: the point of repair-and-return is giving the customer back THEIR unit with evidence of what was done to it. **The earlier signature-substep blocker was wrong and is withdrawn (2026-10-12, see R1).** Worth recording what IS confirmed: `componentInstallCapture` is authored on **Assembly**, in substep *"Record the components fitted (reman)"*, and Assembly **is** in CORE-240210-0007's resolved scope — so the as-built record (what actually went in) is collected on the one unit that will be returned. The shipment surface itself is walked (rows 3–4): **CoC** is offered beside **Packing list** on every shipment. What is unwalked is the join — a cert carrying the as-built list for a returned rebuild. |

| C1 | Export-control screening before anything leaves | ✅ | — | **NOT A TARGET — user decision 2026-10-14: export control "is an artifact of a need that didn't turn out to be a true need."** Marked `—` rather than ⚠️ so nobody reads the findings below as a worklist: **do not build the rework items, do not create a non-US test account, do not flag more part types.** The machinery is real and enforced, so the mechanism notes stay accurate and are kept in case it is ever revived — but the right amount of effort to spend here is none. Everything from here down is the 2026-10-07/12 record, unchanged. <br><br>**Gate logic verified in isolation 2026-10-07; completely unexercised by the demo.** `for_export_control(user)` is wired into `SecureManager.for_user()` via `_apply_security_filters`, excludes `itar_controlled=True` rows for a non-US person, and logs each denial to a separate `compliance.access_control` logger for SIEM, citing NIST 800-171 / CMMC. Probed directly: `us_person=True` → allowed; `us_person=False` → denied with *ITAR_VIOLATION: User is not a US Person (22 CFR 120.62)*. EAR denied-country list is `BLR CUB IRN PRK RUS SYR`. **Nothing exercises it:** 0 of 153 parts are `itar_controlled`, 0 carry an ECCN, 0 require an export licence, 0 of 4 documents are controlled, and **all 8 demo users are `us_person=True`** — so neither side of the filter can fire. **Dead escape hatch:** `can_access_itar_data` falls back to `getattr(user, 'itar_authorized', False)` — commented *"explicit ITAR authorization (e.g. TAA or license)"* — but **`itar_authorized` appears exactly once in the codebase, in that `getattr` default.** No field, no migration, nothing sets it, so a non-US person holding a TAA or licence can never be granted access. The screen *at the point of shipment* still needs rework item 3. **PARTLY LIT 2026-10-12** by seed phase 9. The **data** side now exists: *Control Valve Assembly* is `itar_controlled` with ECCN `9A610`, and one document is controlled with a reason. Deliberately the **least-used** part type — the hero type carries 152 of 153 parts, so flagging it would make the whole demo export-controlled and empty it the moment a facility added a non-US user. **The denial side stays dark:** every demo user is `us_person=True`, and flipping one would silently change what that persona sees everywhere else. A facility's own non-US test account is the right way to watch the filter fire. The dead `itar_authorized` escape hatch (no field, nothing sets it) is unchanged and still needs rework item 3. |

## Scheduler

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Produce a schedule | ✅ | ✅ | **Walked 2026-10-08 as jennifer.mgr (Production Manager).** `/production/schedule`. Solve is gated on `add_scheduleresult` — held only by the PM and tenant admin — so as mike.ops the toolbar is absent and the empty state reads *"No active schedule yet — run Solve"* without an action; as the PM it gains **Undo / Solve / What-if / Dispatch** and the empty state offers Solve. Solve dispatches a Celery task; with no worker the banner says so honestly: *"Solving the schedule — queued 6s ago, waiting for a worker."* With a worker it completed **FEASIBLE in 182.7 s**, writing 1 `ScheduleResult` and **571 `ScheduledTask`s**. Header then carries the whole objective: *FEASIBLE · within 66% · 571 tasks · makespan 357.1 h · lateness 121,800 (priority-wtd) · solved in 181087 ms (machine 72452 · people 108635 ms) · ⏰ 2 late orders* — including the **two-phase split**, machine then people. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 2 | Find out why something is not on it | ✅ | ✅ | **Walked 2026-10-08 — one of the best surfaces in the product.** *Not scheduled* (17 before the solve, **6 after**) opens *"Why isn't this scheduled?"*: *"6 of 17 open work order(s) aren't fully on the board"*, grouped **by cause** with counts and a remedy per group. **NOTHING LEFT TO WORK (2)** — *"All 8 unit(s) are finished, shipped, scrapped or quarantined"* → *"Close the work order, or release the quarantined units."* **NOT PLACED BY THE LAST SOLVE (4)** — per-WO placed ratios (*12/18 placed*, *10/11*, *5/6*) and an honest admission: *"nothing above explains it — the solve most likely ran out of horizon or time"* → *"Re-solve with a longer time limit, or widen the horizon."* Each row is clickable straight into the work-order editor — diagnose and fix without leaving the dialog. `diagnostics.py` / `infeasibility.py`. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 3 | Dispatch people | ✅ | ✅ | **Walked 2026-10-08.** **Dispatch** → toast `Dispatched: 259/265 attended tasks covered`, and the schedule header gains a standing **"14 uncovered"** chip. Coverage is reported rather than assumed, and the gap stays visible on the board instead of only in the toast. `scheduling/dispatch.py`. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 4 | Adjust by hand | ✅ | ✅ | **Walked 2026-10-08.** Clicking a Gantt bar opens a task panel: work order, due date, machine, work centre, operator, start/end, **fence zone** (Frozen), live status (*▶ Running ~41 min left*), planner pin, material state. Reassign is honest about what it does — *"Reassign — applies now, re-solve to optimize"*. The operator picker is **filtered by eligibility** (4 of 9 users for Assembly Cell, via work-centre membership), not a flat list. Assigned an uncovered task to Dave Wilson → toast `Operator updated`, panel updated, and the header recounted **14 → 13 uncovered** live. Also offers **Pin** (planner lock), **Merge into batch** and **Edit WO**. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 5 | React to a disruption | ✅ | ✅ | **Spine walked 2026-10-08; the three disruption types not each walked separately.** The mechanism is reactive staleness: signals flip `ScheduleResult.is_stale` when the world changes under the live plan — new or cancelled demand, a part leaving the flow (SCRAPPED / CANCELLED / QUARANTINED), lost capacity — and `staleness.mark_active_schedule_stale` is the single entry point so bulk `.update()` paths in `services/qms/` trip it identically rather than slipping past the signals. **Deliberately NOT tripped by routine step advances**, with the reason stated: *"an actuals drift on every advance would leave the flag permanently on and meaningless."* It is *"a hint, not an auto-solve"*. Verified in the browser: `is_stale: true` and the header carries a **`stale — re-solve`** badge, from which the planner can Solve or What-if first. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 6 | Test a change before committing | ✅ | ✅ | **Walked end to end 2026-10-08 — one of the strongest surfaces in the product.** **What-if** runs a second solve as a DRAFT (`is_draft: True`, its own `ScheduleResult`), leaving the live plan untouched. The board gains a **Live / Draft** toggle and a comparison panel, *"What-if draft — review vs live"*, that states the trade-off in both directions rather than selling the change: **makespan 357.1 → 284.5 h (−72.6 h)** but **lateness 121,800 → 811,111 (+689,311)**, moves 571 tasks. It also warns what the change costs the existing plan: *"⚠ 58 frozen task(s) had to move — the world changed under the pinned plan. Review before committing."* **Commit draft** / **Discard** — discarded, and the live figures returned exactly (357.1 h, 121,800, 14 uncovered). ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 7 | Get the plan to the floor | ✅ | ✅ | **Walked 2026-10-08, same action as row 3.** Dispatch is the hand-off: it assigns people to the solved tasks and reports what it could not cover. The floor-side half (the operator's queue reflecting it) was already walked under Operator rows. The Control Center also carries a **Dispatch List** button, a separate printable path to the same plan. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| 8 | See whether the floor followed it | ✅ | ⚠️ | **Mechanism verified, no data yet — and that is by design (2026-10-08).** `scheduling/actuals.py` is **capture-only**: it stamps `ScheduledTask.actual_start` / `actual_end` as a part enters and leaves a step, and its docstring is explicit that it *"deliberately does NOT re-time the plan or mark the schedule stale — the solver already pins in-progress ops at solve time, and routine step advances are intentionally not a re-solve trigger."* Measured now: **0 of 1142 tasks carry an actual**, because capture is forward-looking and this schedule was solved after all of the demo's step activity. So planned-vs-actual is real but needs work to move *after* a solve before it shows anything. **Not re-walkable without advancing parts post-solve.** **LIT 2026-10-12.** **11 of 569 live tasks now carry an `actual_start`.** Capture fires from a signal on `StepExecution` save, matched to the active non-draft schedule; re-saving the 11 executions whose part+step pair exists on the live board stamped their real entry times. `actual_end` stays null for steps still in progress, which is correct. **Not seedable deterministically** — it needs a solve followed by movement, and the seed does not solve. |

| 9 | Author non-working time — holidays, shutdowns, PTO, training | ✅ | ✅ | **Verified 2026-10-08, including that the solver honours it — which is the half that matters.** All four kinds are authored: `PlantCalendarException` — *Labor Day (HOLIDAY) 2026-10-12*, *Quarterly Inventory Count (INVENTORY) 2026-11-04*, *Winter Shutdown (SHUTDOWN) 2026-12-24→31*; `LaborCalendarBlock` — a user's *PTO (ONCE) 2026-10-09*, another's *TRAINING (ONCE) 2026-10-14*, and an *ALL MEETING (WEEKLY)*; plus one `Shift` (Day, 06:00–18:00). **The live solve respected the holiday**: 2026-10-12 carries **0 of 571 tasks** while 2026-10-13 carries 119. The row's own warning — *"a stale calendar breaks the plan on day one"* — is therefore guarded against, not merely modelled. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| R1 | Schedule work whose route isn't known until teardown | ✅ | ⚠️ | **Walked 2026-10-08, and it surfaced a real disagreement between two subsystems.** `routing.py` schedules the **nominal** route — DEFAULT edges only, from the part's current step; ALTERNATE (rework) and ESCALATION branches are *"not scheduled up front; a re-solve handles a part that actually fails"*, which keeps the scheduled subgraph acyclic. So the answer to the row is: **book the nominal route, and re-solve when reality diverges.** Measured on the live schedule: a teardown core (IN_DISASSEMBLY) books all **10** steps, Core Receiving → Packaging; a core **DISASSEMBLED and awaiting its exit decision books 0**, which is correct — nothing is known yet. **But CORE-240210-0007 (IN_REBUILD) books 7 steps including Nozzle Inspection and Nitride Coating, which its resolved rebuild scope EXCLUDES** (the rebuild plan lists 5 operations). So the solver reserves capacity for operations the rebuild plan says will be skipped — `skip_out_of_scope` then marks them SKIPPED at runtime. The scheduler is the pessimistic one, which is the safe direction, but it inflates booked load (the board reads **220%**) and makespan for every reman unit. `routing.py`'s design note does not mention rebuild scope at all, which suggests the two were built independently rather than reconciled. **Not a defect — a stated deferral.** Per the user (2026-10-08): *"Reman side may be a bit weird, that is planned. Because of the tree versus sequential nature of reman I'm waiting until I have real data to fully flesh out the scheduling system strategy."* So the solver treating a reman unit as a sequential nominal route, rather than consuming the resolved rebuild scope, is a known simplification held open until real shop data arrives — reman is tree-shaped (what comes off a unit determines what goes back on) and the sequential model is the placeholder. **Recorded so the 220% load figure and the inflated reman makespan are read as a consequence of that choice, not as a bug.** **RESOLVED 2026-10-12 — and resolved by removal rather than reconciliation.** Under *nothing is skipped*, booking the main line stops being pessimistic and is simply correct: the ops the solver reserves are the ops that run. Verified in the peer's tree — `scheduling/data.py` has dropped `_rebuild_scope()` and the `scoped_step_ids` field, and **no production caller passes `resolve_route(..., keep_step_ids=...)` any more**. The two subsystems no longer disagree because one of them stopped having an opinion. **Re-measure the 220% figure after the reseed** — if it moves, this row and Scheduler 5 both need their numbers rewritten. **Three stale references were left behind and are now resolved (2026-10-13).** I reported them; the peer removed rather than patched the first two — `keep_step_ids` and `tests/test_scheduling_scoped_route.py` are **deleted**, since with nothing skipped the scheduler books the main line and the parameter had no caller. `reports/adapters/pick_list.py` had its divergence paragraph rewritten; its own behaviour was never affected, so it was a stale comment rather than a regression — worth recording, because the word *divergence* in it reads like a bug and is not one. **Lesson for this audit:** when a mechanism is retired, grep for its NAME, not just its call sites. The retired phrase *"emits operations"* survived in five places after the code was gone, and `skip_out_of_scope` in three. |

## Production Manager

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | See what is at risk | ✅ | ✅ | **verified 2026-10-07** as `jennifer.mgr` — late jobs, quarantine, CAPAs, FPY, supplier quals, competency coverage |
| 2 | Release work | ✅ | ⚠️ | **Walked 2026-10-08 — and my earlier note was wrong. Release is NOT the schedule's Dispatch**; it has its own service, `services/mes/release.py`, *"the planner's authorization gate"*. Its stated design is unusual and worth keeping: **the gate is advisory, not blocking** — *"a failing check never refuses; it demands a written reason, which is stored on the work order. Blocking here would just teach people to fake the data."* `EditWorkOrderDialog` on the scheduling surface uses it properly: `useReleaseReadiness` renders blockers and warnings, then `WorkOrders.release` writes `released_at`, `released_by` and — when readiness fails — `release_override_reason`. **Inconsistency found:** the WO Control Center has a button also labelled **Release (N)** that calls `handleBulkTransition(ids, 'IN_PROGRESS')` — a plain status flip. It runs no readiness check and writes none of the three release fields, so a unit 'released' there has no recorded releaser, no timestamp and no override reason. **Scope of the consequence:** `data.py:471` notes *"`released_at` is recorded but never filters — the plan stays date-driven"*, and the demo runs `release_mode=auto`, so today the bypass costs only the audit fields. **Under `release_mode=MANUAL` the solver filters on release**, and a work order 'released' from the Control Center would silently never be planned. Demo state: **0 of 18 work orders have `released_at` set.** |
| 3 | Promise a date | ✅ | ✅ | **Green since the fix below landed; the ⚠️ was left over from the walk that found it (corrected 2026-10-15).** CTP answers the question asked, the labels no longer contradict the arithmetic, and a regression test holds it. **Walked 2026-10-12 as `jennifer.mgr`.** `/production/capacity` → **Could we take this order?**. Asked for **300 Common Rail Injectors by 2026-11-01**. Answer: *"**Not by 2026-11.** What runs out: **Labor** — needs **551.6h**, only **327.8h** free by then. **Earliest it fits: 2026-11.** Work content: labor 551.6h · Wash Line 150.2h · Assembly Cell 225.3h · Pack & Ship 50.1h · Test Cell 300.4h · Machine Shop 125.5h"*. Binding resource, shortfall, counter-offer and full work content — everything the row asks for. The page also warns up front that **12 orders have operations with no cycle time**, naming four and pointing at the process editor, which is Engineering row 6 seen from the planning end. **DISPLAY DEFECT (code ⚠️): the refusal and the counter-offer name the same month and read as a contradiction.** Not a capacity-math bug — `capable_to_promise` measures the refusal to `target_end = due date + 1 day` and the earliest-fit to `buckets[i].end`, and the docstring is explicit that a whole final month is right for *"by the end of which month could we?"*. The UI renders the refusal with the **month label** instead of the date asked for, so a due date on the 1st collides with its own month. **FIXED 2026-10-12.** The collision was in the service contract, not only the render: `capable_to_promise` returned `target_bucket` (a month) to describe a refusal computed against `target_end = due date + 1 day`, and `earliest_feasible_bucket` from a scan that *starts at the same bucket* measured to its end — so both came back as the identical string and `CapacityPlanningPage.tsx` faithfully printed a contradiction. Added `target_date` and `earliest_is_target_bucket` to the payload and the inline serializer; the page now renders the **date** for the verdict and prefixes the offer with *end of* when the earliest fit is the due date's own month. **Neither figure changed** — the arithmetic was right, the labels were lossy. Re-walked in the browser: the same query now reads *"Not by **2026-11-01**. Labor — needs 551.6h, only 327.8h free by then. Earliest it fits: **end of 2026-11**."* Schema and FE types regenerated, `bun run typecheck` clean, regression test `test_ctp_answers_name_the_date_asked_about_not_just_its_month`. |
| 4 | Resolve escalations | ✅ | ✅ | holds `resolve_step_decision`; Control Center **Exceptions** is the shared surface (verified under Shift Lead) |
| 5 | Balance capacity and staffing | ✅ | ✅ | **Both halves now seen (2026-10-08).** Staffing was already confirmed (competency coverage: uncovered 0, single-operator 0). The capacity half is live on the solved board: per-resource booked hours down the left rail — Final Test Bench FTB-1 **265.8 h**, Torque Wrench TW-26 **187.2 h**, Flow Test Stand #1 **108.4 h**, Packaging PK-1 **93.2 h**, Disassembly Press DP-1 **92.0 h**, against near-idle Machine Shop 0.0 h and Wash Line 0.5 h — plus a headline **220%** load figure and **⏰ 2 late orders**. Dispatch reports staffing coverage against it (`259/265 attended tasks covered`, **13–14 uncovered**), so the two halves are read together on one surface. Note the 220% and the reman makespan are inflated by the nominal-route booking described in Scheduler R1 — a stated deferral, not a measurement error. |
| 6 | Approve over-and-above and deviations | ✅ | ✅ | **half misframed** — a deviation is a QA decision (`approve_disposition`), which the PM does **not** hold |
| 7 | Review OTD and throughput | ✅ | ✅ | **First pass yield 53.8%** on the hero; OTD lives on the supplier scorecard (verified) — no single throughput view |
| 8 | Maintain the data planning depends on | ✅ | ✅ | **Master Workbook** — 21 sheets in load order, validate-then-commit, nothing kept unless every row loads |

| 9 | Top up a job after scrap outruns the gross-up | ✅ | ✅ | built end to end with a live exhibit; **its only door is the deferred schedule page** |
| R1 | Authorise over-and-above and record the customer's answer | ✅ | ✅ | **Walked end to end 2026-10-07.** *Awaiting customer authorisation* → **Approved** / **Declined**; chose Approved → back to *In Rebuild*. Declined routes to DECLINED, which the service notes is deliberately **not** straight to returned — *"it still has to physically go back, and that is the same dispatch step a rebuilt unit takes."* **The product boundary holds exactly as stated:** the card's own comment is *"The conversation happened elsewhere; these record what the customer said."* No price, no quote, no approval-of-quote — UQMES produces the scope and records the answer. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |
| R2 | Decide harvest versus buy on a rebuild kit | ✅ | ✅ | **Surface walked 2026-10-07** at `/reman/cores/$id/rebuild`. Header states the boundary exactly: *"Proposed, not committed — nothing here is reserved or ordered. This is what the system would put back into this unit, and why — read it before anyone commits capacity or money to it."* **Operations** table carries a **Because** column (*Standard rebuild* / *always*) — *"nothing is on the job without a reason you can challenge."* **Slots** (*2 need a decision · 0 settled*): Position / Needs / Found at teardown / Proposed / Why / Decide / Options, e.g. *Injector Nozzle Assembly · not recovered from this unit · Replace — buy · nothing serviceable available*. **No pricing anywhere — boundary held.** Decision not exercised: `Options` is *none* because no serviceable component of those types is in stock. ~~**Docs ⚠️: this whole surface is undocumented.**~~ **Covered — `workflows/reman/components.md`, `disassembly.md` and `overview.md`. Trailer cleared 2026-10-15.** |

## QA Manager

Rebuilt 2026-10-06 **from the gates the QA Inspector pass actually hit**, not
from subsystem names. The previous list was nine nouns ("run calibration",
"manage supplier quality") that could not be audited.

Every gate below was observed firing for `sarah.qa`; this is the other side of
each.

### The other side of the inspector's gates

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Authorize a disposition decision | ✅ | ✅ | co-sign at the inspector's station, or commit directly holding `approve_disposition`. Verified: `decision_authorized_by` = the approver |
| 2 | Record a CAPA's effectiveness outcome | ✅ | ✅ | verified 2026-10-06. Holding `verify_capa` she goes straight through, no co-sign. Recording **Effective** auto-closes the CAPA |
| 3 | Approve a MAJOR/CRITICAL CAPA before work can start | ✅ | ✅ | verified. Full e-signature gate: decision + drawn signature + password re-auth |
| 4 | Co-sign an FPI buy-off for an inspector lacking `sign_off_fpi` | ✅ | ✅ | **Walked live 2026-10-12 as `mike.ops` (Operator, no `sign_off_fpi`)** — previously code-verified only. On WO-2024-0048-A the FPI panel reads *"First piece waiting on QA 1 · No part moves past these steps until the first piece is bought off"* and offers **Get QA sign-off** rather than a direct buy-off. The dialog switches to co-sign mode and says so in words: *"You aren't authorized to buy off a first piece. An authorized QA inspector can sign here without logging you out."* and *"It is recorded against the QA inspector's name — not the person logged in."* It collects **QA inspector email**, a **signature**, a confirmation checkbox, and the inspector's **password** (*"to verify their identity"*). **WALKED TO COMPLETION 2026-10-13 — this row is now closed.** On the reman teardown WO, as `dave.wilson` (Operator, no `sign_off_fpi`), the co-sign dialog was signed by the user and the record landed: `status=PASSED`, `result=PASS`, **`inspected_by = Sarah Chen`** — *not* the person at the keyboard, which is the whole point of the co-sign and matches the dialog's promise that it *"is recorded against the QA inspector's name — not the person logged in."* Both surfaces updated: the control page's *First piece waiting on QA* panel disappeared, and the player banner flipped to **"First Piece Inspection signed off — Setup verified"**. **Why it took four reseeds:** the two SEEDED FPIs can never be signed (one has no designated part, the other's is quarantined with an out-of-spec measurement), so the row was never blocked by the pad or the harness — it was blocked by having no signable subject. A walk-created FPI, whose designated part is clean and in spec, signs first time. Recorded in `DEMO_SEED_REQUIREMENTS.md` item 2. **DEFECT, separate: the drawn signature is discarded.** `fpi-sign-off-dialog.tsx` validates `requireSignature: true` so the user cannot proceed without drawing, then posts only `{id, notes, cosign_email, cosign_password}` — the image never leaves the browser, and `FPIRecord` has no field to hold one. The file's own comment (`viewsets/qms.py:161`) states the requirement: *"act under AS9100/ISO 9001 8.7 & 21 CFR 820.90 — the record must carry the signature of the individual authorizing it."* The password re-auth plus `inspected_by`/`inspected_at` is arguably a valid e-signature on its own, in which case the pad should not be demanded; what is not defensible is requiring it and keeping nothing. Note `ApprovalResponse.signature_data` DOES store a real PNG from the same shared component, so the two signature surfaces disagree. **Original note retained:** completion was once thought blocked by the signature pad — and here the pad is REAL, unlike the in-player node (see the corrected note in the summary; the FPI co-sign dialog genuinely draws one, because it records against someone else). The affordance, the gating and the wording are all confirmed.

**Defect found 2026-10-12 while walking this row:** on WO-2024-0048-A the panel offers **Get QA sign-off** for an FPI with `designated_part = None` — no part has reached Nozzle Inspection, so there is nothing to inspect. The signature, confirmation checkbox and the QA inspector's password are all collected, and only then does the server refuse: `400 {"detail":"No first piece has reached this step yet - nothing to inspect."}`. The refusal is correct and well-worded; the UI is not. The panel **displays** *"first piece not yet designated"* immediately beside the button, so it holds the information and offers the action anyway, and it collects a signature for something that could never succeed. Contrast the step player, which correctly offers **Start FPI** (designate the first piece) rather than a buy-off in that state — and contrast WO-QA-INSPECT-01, whose FPI has designated INJ-QA-INSPECT-001 and whose panel names the part instead. |
| 5 | Release a judgement hold at receiving | ✅ | ✅ | unqualified supplier / unapproved part — *"A quality manager can release this hold"* |

### Their own work

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 6 | Decide which of this week's NCRs becomes a CAPA — and justify the ones that don't | ✅ | ✅ | **Green — corrected 2026-10-15. Both halves of this row work and the ⚠️ was stale**: the promotion half was fixed in the pass that found it, and the justify-the-ones-that-don't half was never missing, only undocumented. promotion works (was broken, fixed this pass). **Docs correction 2026-10-12:** the note *"no way to record a declined CAPA"* is **stale** — `services/qms/capa_decision.py` records `NOT_REQUIRED` and `DEFERRED` with a **mandatory** reason (*"Say why — the reason is what an auditor reads"*), cites ISO 9001 10.2.1(b), and leaves undecided reports visible on the NCR page so an unevaluated backlog is countable. `PROMOTED` can't be set by hand; it follows from the CAPA linking the report, so the two can't disagree. Now documented in `workflows/quality/quality-reports.md`. |
| 7 | Work the approvals centre | ✅ | ✅ | verified 2026-10-06. 5 awaiting, By Type, My Submitted, Overdue |
| 8 | Qualify someone for a process, and find whose qualification lapses this month | ✅ | ✅ | verified 2026-10-06. Matrix answers more than asked — coverage risk + single-point-of-failure |
| 9 | Raise a SCAR, track the response, change the supplier's standing | ✅ | ✅ | verified 2026-10-06 on `/production/supplier-quality`. SCAR = CAPA `capa_type='SUPPLIER'`, not a parallel model |
| 10 | Find everything measured by a gauge that just failed its check | ✅ | ✅ | **built this pass.** `/quality/calibrations/records/$id/exposure`; verified 2026-10-06. Dark in seed data — no FAIL record exists |
| 11 | Pull the complete record for one serial, on demand | ✅ | ✅ | **CLOSED 2026-10-15 — and it was already done; this row was behind the product, not ahead of it.** The part detail page carries a **Traveler** button scoped to that serial (`fieldsConfigMap.tsx`, passing both the work order and the part id), described there as *"This serial's as-built traveler: its work order's routing, filled with who did each step, what was measured, the lots that went in."* That answers **both** halves of the original finding — the step-by-step history *is* the routing filled in, and the printable is the PDF. `analysis/exporting.md` still called a per-part traveler "planned" and sent readers to the API until `c3eab7f`. A row and a help page both lagging the same shipped feature is the drift this file exists to catch, so: *flip the row when the work lands.* Original note: *PARTIAL — page gathers QRs, dispositions, documents, but no step-by-step history and no per-serial printable.* |

### Reman

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| R1 | Record the customer's answer on over-and-above work | ✅ | ✅ | **row was misframed** — the decision is the customer's, not the QA Manager's. No demo exhibit |

!!! note "Why this list is shaped differently"
    Five of eleven rows exist **only because an inspector reached a gate**. That
    is the derivation rule working: write an oversight role's list from the
    doer's gates and it comes out auditable; write it from subsystem names and it
    comes out as nouns.

    Rows 1 and 5 are already ✅/✅ because the QA Inspector pass verified both
    sides of them.


---

## Engineering

**Added 2026-10-12.** The original pass scoped Engineering out as a *periodic*
role (§Scope). Walked now because its training track needed ground truth.

!!! note "Walked as `admin@demo.ambac.com` (Tenant Admin)"
    No demo account holds Engineering alone, so the **Code** column reflects
    whether the surface works, not whether Engineering can reach it. Permission
    boundaries below are read from `Tracker/presets.py`, not observed.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Author a part type and its specifications | ✅ | ✅ | `/editor/processes` family; authoring perms confirmed in presets (`add_parttypes`, `change_parttypes`) |
| 2 | Author a routing: steps, the graph, branches | ✅ | ✅ | **Walked 2026-10-12.** Flow editor renders nodes (name + description) and labelled edges. A **QA Pass/Fail** step carries **Pass** / **Fail** handles and the edges leaving it are labelled — that is how rework lanes are authored. |
| 3 | Revise an approved routing | ✅ | ✅ | **Walked 2026-10-12.** An approved process is **locked**: *"This process is locked. Duplicate to make changes."* Duplicate → Draft → Approve is the versioning mechanism. The list showed a **Draft beside the Approved version it replaces** (*Injector Reman — Authoring Draft (SHOWCASE)*, 12 steps, alongside *Injector Reman*, Approved, 12 steps) — the normal working state. |
| 4 | Author work instructions (DWI substeps) | ✅ | ✅ | Covered by the DWI passes under Operator; `SubstepResource` and `SubstepTranslation` are **0 rows**, so no demo instruction carries an image or a translation. |
| 5 | Define measurements and attach them as step requirements | ✅ | ✅ | 12 `MeasurementDefinition` rows seeded; definition-vs-requirement distinction holds. |
| 6 | Give the solver what it needs | ✅ | ✅ | Cycle times, machine eligibility, changeovers. **15 steps carry no `expected_duration`** — each contributes no load, so the capacity heatmap overstates free capacity. Same finding as Scheduler row 1 seen from the authoring end. |
| 7 | Life limits | ✅ | ✅ | 4 definitions, 2 part-type links. The link **is** the application — unlinking stops life inheritance and drops shelf life to the default. |
| C1 | Change control (PCR / PCO / PCN) | ✅ | ⚠️ | **WORKS END TO END as of 2026-10-12 — three blockers were found and fixed in the course of one walk, and the detail below is kept because each was a different class of fault.** The caveat keeping this row off green is the last paragraph: PATCH is not status-gated, so an approved PCR's `draft_process_version` can still be repointed. *The walk began "broken at step one"; that is the story, not the state.* Two corrections first: my original *"read-only shell"* was wrong (I believed the page's own stale banner), and the receiving session was right that the actions are wired. **Walked as `admin@demo.ambac.com`:** process editor → header menu → **Propose Change · *File a PCR + fork an editable draft*** (beside *Duplicate as Template · no change trail* — the menu distinguishes them). The approved process flipped from **Viewer / locked** to **Editor / DRAFT** with a banner *"Working draft for **PCR-2026-0001** · DRAFT"* plus **Submit for approval** and **View PCR**. The PCR page is real: target process, creator, **Affected in-flight WOs**, and a **Proposed changes** panel (*"Structured diff between the approved baseline and the draft"*). The submit dialog is ISO-shaped — Title, Proposed change, Justification, **Risk analysis**, Priority, **Customer notification required**. **DEFECT — a PCR cannot be submitted from the browser.** `PATCH /api/process-change-requests/{id}/` returns **200** and the server saves every field, but the zod client rejects the response: *`invalid_type, expected string, received undefined, path: ["submitted_by_username"]`*. The user sees **"Submit failed"** and the PCR stays DRAFT, so **nothing downstream can ever run** — approve, author, implement, release and close are all POSTs to `@action`s (not partial, so they serialise fine) but none is reachable until a PCR is SUBMITTED. **Mechanism (verified, not inferred):** `submitted_by_username = CharField(source='submitted_by.username', default=None, allow_null=True)`. DRF's `Field.get_default()` raises `SkipField` when `self.root.partial` is true, so on a **PATCH** the field is **omitted entirely** rather than sent as null — and `undefined` fails a zod `string | null`. Proven by serialising the same row both ways: non-partial → key present, value `None`; partial → key absent. `created_by_username` survives only because `created_by` is set, so no default is needed. **Six fields share the pattern**, all in `serializers/change_control.py` — `created_by_username`:34, `submitted_by_username`:40, `approved_by_username`:136, `implemented_by_username`:142, `released_by_username`:222, `closed_by_username`:228. Only the PATCH path is currently hit. **This is the CLAUDE.md nullable-field trap in a new shape:** a write that SUCCEEDS is reported to the user as a failure, invisible to backend tests and to `tsc`, visible only in a browser. **FIXED by the receiving session** (dropped `default=None`, kept `allow_null=True`, so DRF falls through to allow_null on partial writes; 55/55 green). **A SECOND blocker sat behind it.** With the zod error gone the real action ran and returned **400: *"PCR_APPROVAL approval template not found. Please configure approval templates."*** The tenant had `DOCUMENT_RELEASE`, `CAPA_APPROVAL`, `CAPA_MAJOR` and **`ECO`** — the old name — and none of the three the services look up (`PCR_APPROVAL`, `PCO_APPROVAL`, `PCN_RELEASE`). **FIXED:** all three added to the demo seed; `PCN_RELEASE` also added to `defaults_service.APPROVAL_TEMPLATES`, which had PCR and PCO but not the notice, so a new tenant could approve a change and then stall at the point the floor is told. **A THIRD, wider bug surfaced from the same thread.** `auto_assign_by_role` and `default_groups_names` are matched against `TenantGroup.name` **exactly** (`approval.py:211`, and `name__in` for the M2M), but both carried the obsolete underscored convention. Measured before the fix: **3 of 4 live templates auto-assigned to 0 users**, silently, because a filter that matches nothing is not an error. A previous pass had caught this for CAPA Approval alone and left the comment *"it's 'QA Manager', not 'QA_Manager'"* — the other three were never done. Fixed in the demo seed **and** in `defaults_service.py`, which matters more: it provisions **every new tenant**. After: **10 of 10 templates resolve, 0 unresolved.** **Walked to completion 2026-10-12:** PCR-2026-0001 is now `SUBMITTED`, stamped with actor and time, the **structured diff captured**, and an approval request auto-assigned to **Maria Santos (QA Manager)** — the assignment that previously found nobody. **Not recorded as fact:** the receiving session reports PATCH is not status-gated on PCR/PCO/PCN despite the viewset docstring, so an approved PCR's `draft_process_version` can still be repointed. Unfixed, with the user. |

---

## Purchasing

**Added 2026-10-12**, same reason and same caveat as Engineering.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | Know what is on order and what is late | ✅ | ✅ | 3 `ON_ORDER` lots, 2 of them late. Shares the Receiving surface (Receiving rows 1, 9). |
| 2 | Chase a late delivery | ✅ | ✅ | Receiving row 9. **OTD is scored against the *first* promise**, so re-promising never repairs the score — deliberate. |
| 3 | Maintain sourcing: lead time, preferred supplier, safety stock | ✅ | ✅ | What the requirements report nets against. A wrong lead time fails **silently** — the shortage surfaces later as a job that cannot start, and reads as a planning fault rather than a data one. Sourcing edits never version the part. |
| 4 | Qualify a supplier; maintain the approved list | ✅ | ✅ | 4 `SupplierQualification` rows. **Raising is Purchasing; `approve_supplierqualification` is QA Manager** — separation of duties, confirmed in presets. |
| 5 | Read the supplier scorecard and act on standing | ✅ | ✅ | **Walked 2026-10-12.** `/production/supplier-quality` — per-supplier acceptance, reject rate, CoC compliance, on-time delivery and open SCARs, with standing (*Qualified* / *Conditional* / *Not qualified*). Great Lakes Diesel showed **Rating C · 9 lots · 1 open SCAR** and the card **recommended an action: "Review: suspend"**. Empty states are honest — *"No material lots received from this supplier yet."* rather than zeros that read as failure. **Docs correction 2026-10-12:** my note said *"the scorecard appears in no doc"* — **wrong.** `workflows/supply/overview.md` already documented all six metrics accurately. What was missing was the **rating and its recommendation**, now added with the real thresholds (C on any open SCAR, reject ≥ 10% or on-time < 85%; A at reject ≤ 2%, CoC ≥ 99%, on-time ≥ 95%), plus the two exclusions that explain surprising numbers — on-time scores against the FIRST promise, and customer property is left out entirely. |
| 6 | Raise a SCAR against a supplier | ✅ | ✅ | A SCAR is a CAPA against a supplier; gated on `initiate_capa`, which Purchasing holds. |
| C1 | Purchase orders, prices, spend approval | ✅ | — | **Out of bounds by design.** UQMES records what is expected and what waits on it; the PO lives in the ERP. Not a gap. |

!!! note "Two empty tables behind documented behaviour"
    `ExternalContact` is **0 rows**, and `late_deliveries.py` reads the supplier's
    deliveries contact for the Late deliveries card — so the "who to chase"
    feature has nothing to show. `MaterialUsage` is also 0 tenant-wide.

---

## Document Controller

**Added 2026-10-12.** Walked as `lisa.docs@demo.ambac.com`, a real seeded
Document Controller — so unlike Engineering and Purchasing, the Code column here
reflects what the role can actually reach.

| # | Workflow | Docs | Code | Notes |
|---|----------|------|------|-------|
| 1 | See what needs me | ✅ | ✅ | **Walked 2026-10-12.** Home carries **Approvals in flight 5** (APR-2026-0003…0007, each with type and due date), **Documents** — *Needs my approval 0 · Pending approval 1 · Due for review 0 · Released 2* — and **Training** (22 / 1 / 1). Every figure links. |
| 2 | Upload a document with type and classification | ✅ | ✅ | **Walked 2026-10-12.** `/documents/list` — **New Documents**, and the list carries **File Name · ID · Version · Status · Type · Classification · Uploaded · Uploaded By**. 4 documents seeded: *DWG-CRI-8800* (Drawing/DWG, **Released**, Internal) and *WI-1003 Flow Test Procedure v4.0* (Work Instruction/WI, **Under Review**, Internal). |
| 3 | Route a document for release approval | ✅ | ✅ | Approval type **Document Release** appears in the in-flight queue alongside CAPA Approval (APR-2026-0003). |
| 4 | Work a mixed approvals queue | ✅ | ✅ | The queue is **not document-only** — four of the five in flight are *CAPA Approval*. A Document Controller is an approvals operator, not only a document operator. ~~**Docs ⚠️: no guide says this.**~~ **Was still true until 2026-10-15 — this row's finding outlived the sweep that cleared the others.** Now written: `roles/document-controller.md` states that the approvals queue is not document-only, that CAPA approvals, process changes and training certifications sit in it, and that a request assigned to you has nobody else coming for it. |
| 5 | Track the lifecycle | ✅ | ✅ | Draft → **Under Review** → **Released**, with **Version** on the row. Both live states observed. |
| 6 | Find what is due for review | ✅ | ✅ | *Due for review* tile is present and reads **0** — the periodic-review loop has no demo data, so the exhibit is dark. **LIT 2026-10-12** by seed phase 9 (`dark_exhibits.py`). One document now carries a `review_date` 14 days past, so the **Due for review** tile reads non-zero and the periodic-review loop is walkable. |
| 7 | Classify, and hold the secret tier | ✅ | ✅ | `classify_documents` + `view_secret_documents` are Document Controller's and QA Manager's alone (presets). All 4 demo documents are **Internal**, so no tier above Internal is exercised and the filtering cannot be seen working. ~~**Docs ⚠️: the tiers appear in no role guide.**~~ **Covered — `roles/document-controller.md` holds the tiers and the Secret pairing, and `workflows/documents/library.md` carries the full table plus the warning that Confidential and Restricted are not manager-only. Trailer cleared 2026-10-15.** **LIT 2026-10-12** by seed phase 9 (`dark_exhibits.py`). One document is now **Confidential**, so classification is no longer uniformly Internal and the tier filtering can be observed hiding a document from a reader below it. |
| 8 | Write training records | ✅ | ✅ | Holds `TRAINING_RECORD_WRITE` — same tier as the training gate override. Visible on Home. |
| C1 | Delete a document | ✅ | ✅ | **Delete Document** is offered on every row (manager-tier `MANAGER_DELETE_PERMISSIONS`). Soft-delete semantics — see [[soft-delete-defeats-protect]]. ~~**Docs ⚠️: undocumented.**~~ **Covered since 2026-10-12; trailer cleared 2026-10-15.** |

!!! note "Two dark exhibits, both demo-data"
    *Due for review* is 0 and every document is **Internal**. The review loop and
    the classification tiers are the two things a Document Controller is most
    distinctively for, and neither can be demonstrated on current seed data.

---

## Findings

### CORRECTED — the customer portal is the Tracker page, and it works

**Probed 2026-10-12 as `tom.bradley@midwestfleet.com` (Customer).** My first
pass filed this as "the portal does not render as a portal". **That was wrong,
and it was the same mistake as the collapsed sidebar group earlier the same day:
I looked at one surface, found nothing, and concluded the feature was absent.**

**The portal is `/tracker`,** reached from the **Tracker** link the customer has
in the sidebar. It works, and the row filtering is exactly right:

- Tom sees **11 orders, all Midwest Fleet Services** — out of **16** in the
  tenant. Great Lakes Diesel, Northern Trucking and one unassigned order are
  filtered out.
- Each card carries customer, delivery date, days remaining, current stage and
  progress (*6 / 11 stages*).

`for_user()` does what it is designed to do. **Home** is bare for a customer —
*"Welcome back, Tom · Use the sidebar to navigate to your workflow."* — which is
a signpost to Tracker, not a missing portal.

**What IS worth fixing, in descending order:**

1. **Two aggregation ViewSets skip row filtering.** Both returned 200 with
   unfiltered internal rows to a customer:

   | Endpoint | Returned |
   |---|---|
   | `/api/IncomingInspection/` | **8 rows** — supplier names (*Apex Plating Co*, *Bargain Bolts LLC*), OSP references, and that `RCV-MAT-HOLD` is 30 units in **QUARANTINE** |
   | `/api/InspectionInbox/` | **16 rows** — including FPI records |

   Root cause, `Tracker/viewsets/mes_standard.py`:

   ```python
   class IncomingInspectionViewSet(viewsets.ViewSet):
       permission_classes = [IsAuthenticated]          # no TenantModelPermissions
       def list(self, request):
           rows = incoming_inspection.build_incoming_rows()   # no user arg -> no for_user()
   ```

   `InspectionInboxViewSet` below it has the identical shape. All three
   enforcement paradigms miss: no action gating beyond authentication, no
   queryset filtering because the builder never receives a user, no per-instance
   check. Fix is small — add `TenantModelPermissions`, pass the user into the
   builders.

   !!! note "Latent, not live"
       Per the user (2026-10-12): **no customer rows exist in any production
       environment**. Nothing is exposed today; this matters before the portal
       is offered to real customers.

2. **The sidebar is not role-filtered.** A customer is shown the full internal
   navigation — Processes, Scheduling, CAPAs, Change Control, Analytics, Admin.
   The destinations refuse them (`/api/MaterialLots/` → 403,
   `dashboard/kpis` → all zeros), so this is noise and structure disclosure
   rather than data disclosure, but it is not what an external user should see.

3. **A `"Failed to load data"` toast fires on a customer's Home,** because the
   shell requests every staff dashboard endpoint and collects 403s
   (`CAPAs/stats`, `process-change-*`, `TrainingRecords/stats`,
   `CompetenceMatrix`, `OutsideProcessShipments/ready_to_ship`,
   `MaterialLots/late-deliveries`).


### VERIFIED — the hold panel matches the documentation, first time ever observed

With the seed fix in, `RCV-MAT-HOLD` renders the panel no one had seen. Checked
as `sarah.qa` (QA Inspector, no `approve_disposition`):

| Documented | On screen |
|------------|-----------|
| several holds at once, each clearing on its own | *"Held for 2 reasons — each clears on its own."* |
| judgement hold needs a quality manager | *"A quality manager can release this hold, or the lot can be rejected."* — and Sarah gets **no release button** |
| heat number is self-clearing, inline | *"Enter the heat number from the mill certificate. The lot moves on as soon as it's saved."* + a Heat number box and Save |
| the sample plan is generated, not decided | *Sample plan (C0, level II, NORMAL) · Inspect 8 of 30 · Accept ≤ 0 · Reject ≥ 1* |

The permission split, the self-clearing/judgement distinction and the
multi-hold rule are all confirmed on screen. Screenshot: `qa-02-multihold.png`.

### CORRECTED — the "orphaned dispositions" finding was mostly my error

**What I first reported:** 15 of 26 dispositions typeless and OPEN, 4 of them on
parts already SCRAPPED or COMPLETED — work that could never be done.

**What is actually true.** My query counted **soft-deleted rows as live.** Every
one of the dispositions I cited as sitting on a terminal part
(`DISP-2026-000001/3/4/7/8/12`) has `archived=True`. They are in nobody's queue.

The seed already handles this. `quality.py` runs two passes:

- `_drop_redundant_auto_dispositions()` — soft-deletes the FAIL-QR auto-created
  tag-along where the QR also carries an explicitly authored disposition. **It
  works**; those are the archived rows.
- `_enrich_auto_dispositions()` — gives the remaining bare ones a type, a
  severity and a spread of states. **It also works** — `DISP-2026-000002/5/6`
  came out REWORK / SCRAP / USE_AS_IS across OPEN, IN_PROGRESS and CLOSED.

**What genuinely remains:** seven live bare dispositions, `DISP-2026-000009`–
`000016`, from `QR-SHOWCASE-001`, `QR-TRAIN-001/002`, `QR-ASSESS-001/002` and two
others — all created by seeders that run **after** `quality.py` (step 424 of the
scenario; Capa is 446, TrainingRecords 458) and so outside its cleanup window.
All are assigned to **maria.qa**, the QA Manager.

**And that is defensible demo data**, not a defect: a QA manager with a handful
of untyped open dispositions waiting to be triaged is what a quality queue looks
like. Nothing is on a terminal part.

**No action.** If anyone wants them tidied, the fix is to run the drop/enrich
passes last rather than inside `quality.py` — but there is no user-visible
problem to solve.

**Method note — the third time today.** A claim built from a query that didn't
filter `archived`. The same shape as reading `hold_reason` instead of
`hold_reasons`, and as a case-sensitive grep missing `YOUR GAUGES`. Partial
queries produce confident wrong findings; check what a query *excludes* before
reporting a count.

### VERIFIED — the sampled inspection, and why this part

Journey 5's claims check out in the data for `INJ-QA-INSPECT-002`:

| Claim | Actual |
|-------|--------|
| Sampling Required: Yes | `requires_sampling = True` |
| reason "Post-repair verification" | `sampling_context.reason_label` = **"Post-repair verification"** |
| Rework Passes 1 | `total_rework_count = 1` |

So the answer to *"why this part?"* is staged and correct. The ruleset is
*Standard Inspection - Nozzle (v1)*.

### VERIFIED — the OSP return lane

`/production/incoming` carries the strapline *"Everything awaiting inbound
inspection — purchased material and parts back from a subcontract vendor — in
one queue. Inspect opens the same runtime for both"*, with a **Source** column
separating *Purchased lot* from *Outside process*.

Opening an OSP return lands in the ordinary DWI runtime with a *Return
inspection (post-coating)* substep — inspection point, sign-off, a measured
coating thickness (OSP-01, 12 +3 −2 µm) and a photograph. Same runtime, wider
net, exactly as both documents say.

### SEED/DOC DRIFT — part 001's documented state is not its seeded state

`WO-QA-INSPECT-01_reference.md` and the script's table both describe
`INJ-QA-INSPECT-001` as *"IN_PROGRESS @ Nozzle Inspection, first piece complete,
PENDING FPI"*.

Live after a fresh seed it is **QUARANTINED**, with a PASS and a FAIL quality
report and an **OPEN disposition**. The pending FPI is there and Journey 4 still
works — the banner renders and the sign-off dialog opens — so the exhibit is
usable, but the reference table is wrong about the state a trainer will see.

Also: the table lists **six** serials; the work order seeds **eight**
(`INJ-QA-INSPECT-007` and `-008` exist as historical first pieces for downstream
steps, per `qa_walk.py`). Not a fault, but a trainer counting parts will be
confused.

### PARTIAL — "pull the complete record for one serial" (QA Manager #11)

Tested as `maria.qa` on `INJ-0042-023` (SCRAPPED, with a FAIL QR and a CLOSED
SCRAP disposition).

**What the part page gives you:** general information, production details (order,
work order, current step), a quality-control summary (latest inspection, open
defects, rework passes, sampling), linked **Quality Reports**, linked
**Dispositions**, and **Documents** with an inline viewer. Following those links
reconstructs the story, which is what the trainer script's Journey 11 asks for.

**What it does not give you:**

- **No step-by-step execution history.** Who ran which step, when, signed by
  whom — the spine of a traceability record — is not on the part page.
- **No single artifact.** There is no per-serial printable record. The
  `work_order_traveler` report is per **work order**, not per part.

**Two demo caveats, which are not product faults:**

- `INJ-0042-023` has **0 StepExecutions** — the seed stages it with quality
  records but no execution trail, so there is nothing to show even if the page
  showed it.
- Its audit history reads *"No audit history."* with exactly **one** auditlog
  entry: an actor-less CREATE from the seeder. Auditlog itself is healthy (2,251
  entries). So the emptiness is seeded-in-final-state, not a broken log.

**Consequence:** audit readiness is the hardest thing to *demonstrate* in this
product, because the demo data has no history to narrate. An auditor's first
question — *"show me everything about this serial"* — is answered today by
visiting a page and following three links, with no printable result.

**Worth deciding:** is a per-serial record (history + measurements + QRs +
dispositions, printable) something uqmes should produce? It is the natural
companion to the receiving inspection record, which does exactly this for a lot.

### CODE GAP — a failed calibration is not traced back to what the gauge measured

**QA Manager #10 / QA Inspector C2.** The forward control exists; the backward
assessment does not.

`apply_calibration_result_to_equipment` (`services/mes/work_order.py:344`) does
exactly one thing on a FAIL: sets the equipment **OUT_OF_SERVICE**. That stops
the gauge being used *again*.

**Nothing asks what it already measured.** There is no path from a failed
`CalibrationRecord` → `QualityReportEquipment` → `QualityReports` → parts.
`QualityReportEquipment` is read by **one** service in the codebase —
`gauge_nag.py` — and that only looks forward, at what you used recently.

**Why it matters.** ISO 9001 **7.1.5.2** asks that when measuring equipment is
found unfit for purpose, the organisation determines whether the validity of
previous measurement results has been adversely affected, and takes appropriate
action. That is the recall, and it is the whole reason gauge-to-measurement
traceability is kept at all.

**The data is there.** A GAUGE-role `QualityReportEquipment` row links gauge →
report → part. The query is a join, not new modelling.

!!! note "It would have returned nothing until today"
    No seeder ever created a GAUGE-role row — only PRODUCTION. So even a correct
    recall query would have found nothing in any demo tenant. The seed fix for
    the gauge nag incidentally made this data meaningful for the first time.

**Not mine to build.** Flagging for the quality owner: is the backward
assessment expected to be in uqmes, or is it a procedure run outside it once the
gauge is flagged? Either is a legitimate answer; today the docs imply neither.

### FIXED — the "Your gauges" compliance exhibit (was empty)

Journey 1 teaches the tile as the compliance cue — *"Your gauges — calibration
status on gauges Sarah used recently (**Torque Wrench TW-25 — overdue**)"* — and
Journey 10 calls it "the point-of-use nag". The watch-for note is *"Trainee
ignores Your gauges. That's the compliance signal."*

On a fresh `seed_demo` it reads **"Nothing you've used in the last 7 days is due
for calibration."**

`my_gauge_nag` needs a gauge **used within 7 days** whose calibration is **due
within 7 days**. The seed stages no recent gauge use by Sarah, so the tile is
permanently in its empty state and there is no signal to not-ignore.

Same shape as the hold exhibit: a documented teaching moment with no data behind
it.

**Fixed 2026-10-06.** The tile needs a **GAUGE**-role `QualityReportEquipment`
row on a report the user filed; the seed only ever created **PRODUCTION** rows.
The overdue gauge already existed — the link to an inspector did not.
`quality.py::link_inspector_gauge` now adds one to every filer's most recent
report.

**Two mistakes on the way, both mine, both the same shape as the others today:**

1. I keyed it off `users['qa_staff'][0]`, which is the QA **Manager** — the nag
   landed on Maria's home, not Sarah's.
2. I read the line numbers where seeders are *instantiated* in `scenario.py` and
   assumed that was execution order. It is not: the calls are in `seed()`, where
   **Quality runs well before showcase and qa_walk**. Running inside the quality
   seeder, only one user had filed anything. Moving the call to the end of
   `scenario.seed()` took it from 1 link to 4.

Now reads *"1 gauge you used in the last 7 days needs calibration within 7
days — **Torque Wrench TW-25 — overdue 15d**"*. Screenshot:
`qa-05-gauge-nag.png`.

### VERIFIED — My quality actions

Three tiles with counts and an overdue badge, exactly as documented: **0
Approvals · 5 CAPA tasks · 2 My dispositions**, with **1 OVERDUE**. Approvals and
CAPA tasks link to `/inbox`, dispositions to `/production/dispositions`.

### RETRACTED — "the verification dialog stays open after Create"

Filed, then disproved. Reproduced on a clean CAPA: the snapshot bundled with the
Create click shows the success toast *and* the dialog; a snapshot taken
immediately after shows the dialog gone and one verification in the list. One
`POST /api/CapaVerifications/ [201]`, no duplicate, no console errors.

`click` returns when the click dispatches, so the snapshot in that same result
predates React's re-render and the dialog's exit animation. The toast is a
separate portal and paints at once.

**Method note:** never assert UI state from a snapshot bundled with a click.
Re-snapshot first. A case-sensitive grep also nearly produced a second false
finding in the same stretch — "YOUR GAUGES" renders uppercase and a search for
`Gauge` missed it.

### BUG (severe) — every CAPA dialog destroys itself as you type

**Found:** 2026-10-06, Journey 9, trying to author a verification plan as
`sarah.qa`.

**Symptom.** Typing `abcdef` into *Success Criteria* put `a` in that box and
`b`–`f` into *Verification Method*, **in reverse order**. Focus jumps to the
first field after a single keystroke and the cursor resets to position 0.
**These fields cannot be filled in by a human.**

**Cause.** `CapaVerificationTab.tsx:189` defines the dialog inside the parent:

```tsx
const VerificationDialog = () => ( … )     // line 189
…
<VerificationDialog />                      // line 449
```

Form state lives in the parent, so every keystroke re-renders it, the arrow
function gets a **new identity**, and React treats it as a different component
type — unmounting the whole subtree and mounting a fresh one. The textarea is
destroyed and recreated per character.

**Scope — five dialogs across the CAPA screen, all with text inputs:**

| File | Dialogs |
|------|---------|
| `CapaRcaTab.tsx` | `RcaDialog` (rendered **twice**, lines 336 and 494 — likely a second bug) |
| `CapaTasksTab.tsx` | `TaskDialog`, `CompleteDialog` |
| `CapaVerificationTab.tsx` | `VerificationDialog`, `CompleteVerificationDialog` |

So root cause, tasks, task completion, verification planning and verification
outcome are all affected. That is most of the CAPA workflow's data entry — QA
Inspector Journey 9 and a large part of the QA Manager's job.

**Fix.** Lift each dialog out of the component body (module scope, or inline the
JSX instead of wrapping it in a component). Mechanical, five places.

**Why no one noticed.** The CAPA screens are reachable but nothing in the demo or
training path requires *typing* into them — the seed stages CAPAs with their text
already populated, and the trainer script has the trainee *read* the Verification
tab rather than fill it. The bug sits exactly where the demo stops.

### VERIFIED (end to end) — the disposition co-sign, the core of the role

Exercised live as `sarah.qa`: opened an auto-created disposition, set
**Disposition Type = Rework**, pressed **Update Disposition**.

The editor **did not commit**. It opened **Authorize disposition decision**:

> Recording a "Rework" disposition needs approval authority. An authorized
> colleague can co-sign here; the decision is recorded under their name.

Fields: approver email, a **required** signature canvas, an *"I authorize this
disposition decision"* checkbox, and a password — captioned *"Their password, to
verify their identity. **They are not logged in here.**"*

Completed it with Maria's credentials. Result in the database:

| | |
|---|---|
| `disposition_type` | `REWORK` |
| `current_state` | `IN_PROGRESS` |
| **`decision_authorized_by`** | **Maria Santos** |
| `decision_authorized_at` | stamped |

**Everything both documents claim about this is true**: the inspector is gated
rather than blocked, the approver authenticates on the inspector's screen without
logging in, the decision commits under the approver's name, and the disposition
moves to IN_PROGRESS. The UI caption states the not-a-login-switch rule itself.

Screenshot: `qa-04-cosign.png`. This is the one screen to put in the help docs if
only one goes in.

### DOC — there are two routes to the FPI buy-off, and the script teaches only one

The script routes through the runtime: WO Detail → **Start Work** → tick the part
→ **Start**, where the FPI banner offers **Sign off & pass · Fail · Waive**.

The **WO Control page** has its own **Sign off** button on a *First piece waiting
on QA* card, which opens a dialog with only **Confirm sign-off** and **Cancel**.

So the Control route is a one-option shortcut: **you can pass an FPI there, but
not fail or waive it.** Neither document mentions it. Worth saying which route to
use and why, since a lead glancing at the Control page will find the quick path
and never meet the other two outcomes.

**Verified correct meanwhile:** the attestation wording matches the script almost
to the word — *"By signing off you attest that the setup is correct and the first
piece (INJ-QA-INSPECT-001) conforms, and this releases the run. It is recorded
against your name."* And the Control page states the batch gate plainly: *"No
part moves past these steps until the first piece is bought off."*
Screenshot: `qa-03-fpi-signoff.png`.

!!! note "Not tested: the separation-of-duties refusal"
    The script claims that if the same person signed the substeps, the buy-off
    would refuse. Sarah did not sign them (Mike did), so exercising the happy
    path proves nothing about it — and arranging the failing case would consume
    the exhibit. **Left unverified, deliberately.**

### DOC — the script says "don't inspect" the hold exhibit; it is the best screen in the journey

`QA_INSPECTOR_TRAINING_SCRIPT.md` Journey 3 treats the held lot as a
don't-touch exhibit. But **Inspect** is how you reach the hold panel, and that
panel is the richest teaching surface in the receiving journey — two holds, two
different clearing paths, and the permission boundary visible in one screen.

Rewrite it as a stop to make, not one to avoid.

### UI POLISH — the panel hedges about a fact it knows

> ⚠ This lot's supplier is not qualified for this part type. **If the part type
> requires qualification, the lot was held** — qualify the supplier…

The lot *is* held; the panel is rendering the hold. The conditional reads as
uncertainty about something the screen can see. Low priority.

### BUG — core lots appear in the QA inspector's home Receiving chip

**Found:** 2026-10-06, QA Inspector pass, logged in as `sarah.qa`.

`incoming_inspection.py` excludes core lots from the unified queue, with the
reason stated:

```python
# A customer's bulk cores are graded unit by unit as they're identified, not
# sampled as supplier stock.
.filter(holds_cores=False)
```

`inspection_inbox._receiving_rows()` (`services/qms/inspection_inbox.py:124`)
builds the same query **without that filter**. Everything else matches.

**Effect:** `/production/incoming` is correct; the **home page Receiving chip is
not**. Observed before a reseed: `CORELOT-2026-0001` (`holds_cores=True`) sat in
Sarah's inbox and the chip read 6 where the trainer script says 5.

**It does not reproduce on a fresh `seed_demo`** — that seed creates no core
lots, so the chip reads 5. The filter is still missing (`inspection_inbox.py`
contains zero references to `holds_cores`), so the bug is **invisible in demo and
live in any shop receiving bulk cores**. That makes it easier to miss, not less
real.

An inspector cannot usefully inspect it — a bulk core lot is graded unit by unit
at identification, not sampled.

**Fix:** add `.filter(holds_cores=False)` to `_receiving_rows()`. Owned by the
receiving/shipping session.

### BUG (major) — the entire receiving-hold subsystem is dark in demo data

**Found:** 2026-10-06, sweeping outward from the hold-exhibit bug below.

All four receiving gates are **opt-in per item**, and **none is armed anywhere**:

| Gate | PartTypes armed | Materials armed |
|------|-----------------|-----------------|
| `requires_supplier_qualification` | 0 of 6 | 0 of 3 |
| `requires_part_approval` | 0 of 6 | — |
| `requires_coc` | 0 of 6 | 0 of 3 |
| `requires_heat_number` | 0 of 6 | 0 of 3 |

**No lot in the database carries any `hold_reason`.** And the seed directory
contains **zero references** to any of the four field names — it never arms them.

**Effect: a whole documented subsystem cannot be observed.** Nobody can see, in
any demo or training environment:

- a lot held at receiving, for any reason
- the self-clearing holds (upload the CoC, enter the heat number)
- several holds at once, each clearing independently
- a quality manager releasing a judgement hold with a reason
- the "paperwork clears itself, judgements need authority" split that the
  documentation is built around

**It also explains something about this session's own work.** The holds were
documented across several handoffs and verified **against source only**, with
"not eye-checked" noted each time. That was not merely a browser being
unavailable — **there was no data that would have shown anything.**

**Fix:** arm the gates on at least one seeded item each and stage a lot against
them. One item with `requires_coc` + `requires_heat_number` would demonstrate
multi-hold and self-clearing in a single exhibit.

**Generalise:** when a check becomes opt-in, every demo exhibit and training
moment that assumed it was automatic goes dark — silently, because an unarmed
gate looks exactly like a passing one.

### BUG — the "unqualified supplier" hold exhibit no longer holds

**Found:** 2026-10-06, Journey 3.

`seed/demo/supplier_quality.py:144` stages `RCV-MAT-HOLD` from Bargain Bolts,
routes it through `receiving_inspection.route_received_lot()` and logs
*"1 held lot (unqualified supplier)"*.

**It is not held.** Live state: `status=AWAITING_INSPECTION`, `hold_reason=''`,
and it offers an **Inspect** button.

**Cause:** Bargain Bolts has no qualification records — genuinely unqualified —
but the part type's `requires_supplier_qualification` is **False**, and the gate
is **opt-in per item**. That field arrived with the receiving work (Phase 3,
*"Requires a qualified supplier"*). The seed predates it and assumed the hold
fired automatically.

**Effect:**
- The seed's own log line is false.
- `QA_INSPECTOR_TRAINING_SCRIPT.md` Journey 3 teaches this lot as a hold exhibit
  — *"QUARANTINE, 'Unqualified supplier' … don't inspect it"* — and a trainee
  now sees an ordinary inspectable lot. The teaching moment is gone.

**Fix:** set `requires_supplier_qualification=True` on the seeded part type (or
on the material), so the gate the exhibit depends on is actually armed.

**Generalise:** making a check opt-in silently disables every demo exhibit and
training moment that assumed it was automatic. Worth checking the other gates
that became opt-in in the same work — CoC and heat number.

### DOC — the script's hold exhibit is wrong twice over

Journey 3 names the lot **`RCV-INJ-HOLD`**; it is **`RCV-MAT-HOLD`**. It states
the status as **QUARANTINE**; it is AWAITING_INSPECTION (see the bug above).

### NOT A GAP — ISO 9001 8.5.3 customer-property reporting is out of system

A customer's core is their property in uqmes's custody. The clause asks you to
identify, verify, protect **and report loss, damage or unsuitability to the
customer**.

uqmes does the first three: identification at receipt, a required condition
grade, the CUSTOMER PROPERTY label, and ringfencing so another customer's work
cannot consume it. **It does not do the reporting, and that is current and
intended.** The two surfaces it would live on — generated email and the customer
tracker screen — are not in a state to carry it.

**Today that conversation is the reman team's, with the customer directly.**

Do not file this as a missing workflow. If it comes back into the system later it
will most likely attach to the scope-authorisation flow, which already has the
right shape: produce the finding, export it, record the answer.

### DRIFT — the scan box takes more than the docs say

`QA_INSPECTOR_TRAINING_SCRIPT.md` Journey 2 teaches *"anything typed or scanned
resolves to a work order"* and *"a scan anchors on the parent WO"*. The live
placeholder reads **"Scan or type a work order, serial, lot or location…"**.

Not wrong, but narrower than the app. The scanner was widened by the receiving
work (lots, serials, locations, `LOC:` labels). The teaching point still holds
for work orders; the other three subjects are undocumented here.

### VERIFIED — the gauge recall page ("What it measured") answers ISO 9001 7.1.5.2

Built by the scheduling session to the spec in this audit; walked as `maria.qa`
on 2026-10-06.

Route `/quality/calibrations/records/$id/exposure`, reached from a **"What it
measured"** link that appears on a calibration record only when that check found
the gauge unfit, and only for users with `view_qualityreports`.

Verified in the browser:

- The window leads, as it should — the window IS the finding:
  *"Measured between 2026-09-06 (last passing calibration) and 2026-10-06
  (failed check)."*
- Four reports listed, spanning a part, a serial, a lot-less report and a
  receiving-side one.
- A passing record returns **400** with *"This calibration found the gauge in
  tolerance, so nothing it measured is in question."* — an answer, not an error.
- `exposure-export/` returns a real .xlsx (6,126 bytes), filename
  `measured_by_Torque_Wrench_TW-25_2026-10-06.xlsx`, with an About sheet that
  repeats the window.
- It does **not** act on the list. No auto-quarantine, no auto-NCR. The page says
  in so many words that re-inspecting, accepting on other evidence, telling a
  customer or raising an NCR is decided outside it. That is correct: 7.1.5.2
  requires the *assessment*, and the judgement belongs to a person.

Screenshot: `docs/assets/qa-manager/qam-01-gauge-exposure.png`.

Three places the builder went beyond the spec, all three correct and worth
keeping:

1. **"Found unfit" is FAIL *or* `as_found_in_tolerance = False`.** A gauge found
   out of tolerance, adjusted, and then passed measured wrongly until the
   adjustment. That is exactly the 7.1.5.2 trigger, and a FAIL-only filter would
   miss the most common real case — most gauges are adjusted, not condemned.
2. **Both window ends are whole plant-local days.** A calibration carries a date,
   not a time, so a report filed on either boundary day could fall on either side
   of the check. A suspect list should err toward including it.
3. **All equipment-link roles count, not only GAUGE.** Any calibrated instrument
   attached to a report is suspect; the row notes "as production" when the role
   isn't GAUGE. The search also spans every version of the equipment, which is
   right — a new version is the same instrument ([[version-is-same-entity]]).

### BUG (major, FIXED + VERIFIED) — every picked date displayed a day early

Found while verifying the page above; unrelated to it.

On `/quality/calibrations/records/new`, picking **Oct 6th** left the field reading
**"October 5th, 2026"**, and reopening the calendar highlighted Oct 5 as selected.

The stored value was **correct** — `onSelect` did `format(date, "yyyy-MM-dd")`,
so `2026-10-06` went to the API. Only the read-back was wrong:
`new Date("2026-10-06")` parses a date-only string as **UTC midnight**, which in
`America/New_York` is Oct 5 20:00, and `format(…, "PPP")` renders that local.
Confirmed in the page console:
`new Date("2026-10-20").toString()` → `"Mon Oct 19 2026 20:00:00 GMT-0400"`.

**Why this was not cosmetic.** The display and the calendar highlight were wrong
in the same direction, so a user who trusted the screen would "correct" it by
picking the 7th — and *that* stores a genuinely wrong date. A display bug on
`calibration_date` / `next_due_date` becomes bad calibration due dates, which is
a 7.1.5.2 record. It also meant every existing record rendered a day early when
opened for edit, and the records **list** showed 9/5/2026 where the API said
`2026-09-06`.

Independently corroborated: the exposure window came back ending `2026-10-06` —
the date clicked — while the form displayed Oct 5. Proof the storage was right
and the display was wrong, rather than the reverse.

Scope was narrower than the grep suggested. Of the four files using
`format(new Date(field.value), "PPP")`, only two were affected; the other two
(`part-disposition-form.tsx`, `EditDispositionFormPage.tsx`) store
`date?.toISOString()` — a full datetime, which round-trips correctly and must be
left alone.

Fixed by the scheduling session (`new Date` → `parseISO`, which reads a bare
`yyyy-MM-dd` as local midnight; `onSelect` untouched). **Verified in the browser
2026-10-06:** clicking Oct 6 now displays "October 6th, 2026", and the records
list shows 9/6/2026 matching the API.

It also turned up a **reverse** bug in `CapaVerificationTab`, which stamped
`new Date().toISOString().split('T')[0]` on "Complete Verification" — the *UTC*
date, so after 8pm ET it recorded **tomorrow**. That one wrote a wrong value
rather than merely showing one. Also fixed.

### OPEN (needs a decision) — 33 more date-only display sites, 28 files

The same `new Date(<date-only field>)` shape survives in 33 places across 28
files: training dashboard and records, user detail, work orders, orders,
documents, home blocks. Each one displays a date a day early for any user west of
UTC.

Left unfixed deliberately — they are outside the files this work touched and other
sessions are active in several. **This is a decision for you, not a finding.** The
tidy fix is one `parseDateOnly` helper applied across the sweep, done as a single
opportunistic refactor in its own commit rather than piecemeal.

Worth noting the general lesson, which is not specific to this codebase:
**`new Date("YYYY-MM-DD")` is UTC, `new Date("YYYY-MM-DDTHH:mm")` is local.** The
bug only ever appears for date-only fields, and only for users behind UTC — so it
is invisible to a UTC-based CI run and to every backend test.

### BUG (demo data) — no failed calibration exists, so the recall page is dark

All 13 seeded calibration records are **PASS**. The "What it measured" link shows
only on a record that found the gauge unfit, so out of the box the entire recall
surface — the thing 7.1.5.2 asks for — is unreachable in a demo tenant. I had to
create a FAIL by hand to see it at all.

This is the **fourth** instance of one pattern, now the most reliable predictor of
a dark exhibit in this product:

> When a check is opt-in or rare, every demo exhibit and training moment that
> assumed it was automatic goes dark silently. Nothing errors; the surface simply
> never appears.

The other three: the receiving-hold subsystem (no gate ever armed), the home
calibration nag (no GAUGE-role link ever seeded), and the CoC/heat-number
exhibits.

**Care needed in the fix.** A FAIL sets the gauge `OUT_OF_SERVICE`
(`apply_calibration_result_to_equipment`), and an out-of-service gauge **blocks
measurement capture** (`test_measurement_blocks_out_of_service_equipment`). So the
seeded FAIL must land on a gauge with existing quality-report links but no part in
the demo's forward capture path, or it will break the operator and FPI journeys to
light up the calibration one. Choosing that gauge is the whole task; the record
itself is four lines.

Note the seeder already *can* emit a FAIL — `_create_calibration_history` rolls
`random.choice(['FAIL', 'LIMITED'])` on a 5% branch. It is random, so the exhibit
is present in roughly one seed in twenty and absent from the demo you actually
show. **A showcase exhibit must be deterministic, not probabilistic.**

### VERIFIED — the SCAR chain is one surface, not four subsystems

Row 9 was flagged by an earlier reviewer as "four subsystems in one row". Walked
on 2026-10-06; the row is fine, because the four are already assembled into one
page.

`/production/supplier-quality` is a scorecard per supplier carrying acceptance,
reject rate, CoC compliance, on-time delivery, open SCAR count, qualification
status and a standing recommendation. Great Lakes Diesel shows the designed
exhibit end to end: **Rating C · Review: suspend · Qualified · 1 open SCAR**,
reject rate 50%, CoC 17%, OTD 83%.

A SCAR is **not a parallel model** — it is a CAPA with `capa_type='SUPPLIER'`
plus a `supplier` FK, so it inherits root cause, tasks, verification and closure
from the CAPA engine. That is the right call and worth stating in the docs,
because "SCAR" reads like a separate object and someone will go looking for one.
Note the API filter value is `SUPPLIER`; `capa_type=SCAR` is rejected as an
invalid choice.

**Label trap for the docs, not a bug.** The card reads "Lots received 6" next to
"Reject rate 50%", which invites the reader to compute 1/6. The denominator is
*inspected* lots (2), not received — correct, since four are still awaiting
inspection, and documented as `rejected / inspected` on the dataclass. The screen
doesn't say so. Worth one clarifying line in the supply docs.

**Checked and NOT a bug:** Bargain Bolts shows CoC compliance 0% while on-time
shows "—". That asymmetry is correct: `on_time_rate` is genuinely `None` with no
promised dates, whereas CoC is 0 of 1 received lots, which is a real zero. I
nearly filed it before reading `compute_supplier_scorecard`.

### BUG — `is_customer` and `is_supplier` both default to True, so neither means anything

`Companies.is_customer` and `Companies.is_supplier` are both
`BooleanField(default=True)` (`models/core.py:1577-1578`). Any company created
without setting them explicitly is therefore *both*.

The visible symptom is on the supplier scorecard, which lists **AMBAC
Manufacturing** — the internal org — as a supplier to be scored, alongside
Northern Trucking Co and Midwest Fleet Services, who are carriers rather than
material suppliers. Eight companies, eight scorecards.

**The page is not at fault.** `SupplierQualityPage.tsx:131` already filters
`is_supplier: true`. The default defeats the filter. Confirmed on the API:
Bargain Bolts LLC, seeded purely as a fasteners supplier, comes back
`is_customer: true, is_supplier: true`.

Consequences beyond cosmetics: the scorecard invites a manager to act on standing
for a company that cannot have one, and the same default will be flattering or
alarming in the other direction wherever customer lists are drawn.

**This needs your decision, because the fix is a data migration, not a default
flip.** Changing the default to `False` is right going forward but silently
reclassifies nothing — existing rows keep their `True`. The honest fix is the
default plus a one-off pass that sets the flags from behaviour (has orders →
customer; has material lots or qualifications → supplier) with the internal org
excluded from both. Whether the internal org should carry either flag at all is
the question underneath, and it is yours.

### VERIFIED — CAPA effectiveness verification, and an independence control worth knowing about

Row 2 walked as `maria.qa` on 2026-10-06. The flow is two stages, which the docs
should say plainly because the button names don't: first **Add Verification**
records a *plan* (method + success criteria), then **Complete Verification**
records the *outcome*. A plan with no outcome sits at `Inconclusive`.

Holding `verify_capa`, Maria goes **straight through with no co-sign dialog** —
the exact complement of what `sarah.qa` saw, which confirms row 2 from both
sides. Recording **Effective - Confirmed** on `CAPA-2024-002` closed the CAPA to
`CLOSED` automatically. That auto-close is undocumented and will surprise someone.

**The useful discovery is a second, separate control.** On `CAPA-ASSESS-READY`,
where Maria is both `initiated_by` and `assigned_to`, the same action is refused:

> Self-verification is not permitted for this CAPA

That is an *independence* bar, not a permission one — she holds `verify_capa`
and still can't do it. It is governed per CAPA by `allow_self_verification`, an
explicit toggle on the create form reading *"the initiator or assignee may verify
their own work. Use for minor issues or when independent…"*. Good design: the
default protects, and the exception is deliberate and recorded.

**A near-miss worth recording as method.** I first wrote this up as a UI bug —
"the dialog stays open and shows no error". It was wrong. `toast.error` *is*
called (`CapaVerificationTab.tsx:163`) and does surface the server's exact
sentence; my check simply ran after the toast auto-dismissed. Polling every 300ms
from the moment of the click showed it present for 3.6s. **This is the second
time a toast/animation timing artifact has nearly become a false finding in this
audit.** The rule: when a UI "shows nothing", sample repeatedly from the instant
of the action before concluding anything.

### RETRACTED — approval DOES have an independence check; I misread the gate

I filed this as "approval has no independence check, verification does". **That
was wrong**, and the correction is worth keeping because the mistake is a
repeatable one.

I read `ApprovalRequest.can_approve()` (`models/core.py:2862`), saw it compare
only assignment and group membership, and concluded no requester≠approver bar
existed. `can_approve()` is an *eligibility* check, not the gate. The real guard
is in the service layer, `services/core/approval.py:544-550`:

```python
is_self_approval = (approval_request.requested_by == approver)
if is_self_approval:
    template = approval_request.get_template()
    if not template or not template.allow_self_approval:
        raise ValidationError("Self-approval is not permitted for this approval type")
    if not comments or len(comments.strip()) < 10:
        raise ValidationError("Justification required for self-approval (minimum 10 characters)")
```

`ApprovalTemplate.allow_self_approval` defaults to **False**
(`models/core.py:2994`), every seeded template sets it False, and the response
records `self_approved=True` on the row when it happens
(`models/core.py:2947`). Five tests cover it: blocked by default, allowed with
justification, requires justification, no justification, flag set correctly.

So approval is in fact guarded *more* thoroughly than effectiveness verification:
same default-deny and per-template opt-in, plus a mandatory written justification
and a permanent flag on the record. **There is no asymmetry.** The two controls
agree.

Maria seeing **Submit Response** on her own request is therefore correct — the
button opens the e-signature dialog, and the server decides. Eligibility and
authorisation are deliberately separate layers.

**Confirmed in the browser, not just in the code (2026-10-06).** Reading the
service was not sufficient evidence and should not have been treated as settled.
Signed in as `maria.qa`, on `CAPA-ASSESS-READY` — a CAPA she herself requested —
I completed a genuinely valid approval: decision **Approve**, comments, a real
drawn signature, the confirmation checkbox, and the correct password. The server
refused:

> ['Self-approval is not permitted for this approval type']

`approval_status` remained `PENDING`. The control is real at runtime, with
identity already verified — the refusal is about independence, not credentials.

Two defects in how that refusal is *presented*, both minor, both real:

1. **The dialog printed a raw Python list repr** — brackets and quotes included:
   `['Self-approval is not permitted for this approval type']`.

   **My diagnosis was wrong and is worth recording.** I called it a frontend
   problem — "the frontend stringifies the array instead of joining it". It was
   **server-side**: `services/core/approval.py` raises *Django's*
   `ValidationError`, and the viewset caught it with a broad `except Exception`
   and returned `{'detail': str(e)}`. `str()` on a Django `ValidationError` is its
   **list repr**, so the server was literally sending the string
   `"['Self-approval…']"`. No amount of frontend joining could have fixed it.
   Fixed with `'; '.join(e.messages)`, the idiom used elsewhere.

   The general trap: `str(e)` is safe for `ValueError` and lossy for Django's
   `ValidationError`. The ~79 other `'detail': str(e)` sites catch `ValueError`
   and are fine.
2. **The toast says only "Operation failed — Request failed with status code
   400."** The useful sentence is in the dialog; the toast, which is what catches
   the eye, says nothing actionable.

Neither blocked the control. **Both fixed and re-verified in the browser the same
day:** the alert now reads `Self-approval is not permitted for this approval type`
with no brackets, and the toast carries the same sentence. Bug 2 was fixed
globally via a new `apiErrorMessage()` used by the shared mutation toast, so every
failed mutation now shows the server's reason rather than a status code.
Screenshot: `docs/assets/qa-manager/qam-05-self-approval-refused.jpeg`.

**One sibling leak remains, and it matters.** Three further broad
`except Exception` → `str(e)` sites exist in `viewsets/qms.py`. I traced all three:

- **`approve_rca` (~1225) — REACHABLE, same bug.** `services/qms/rca.py` imports
  Django's `ValidationError` and raises *"Self-verification of RCA is not
  permitted for this CAPA"* and the matching justification message. These are the
  same family of independence refusal, so today two sibling controls render their
  refusals differently — one clean, one in brackets.
- **`complete_task` (~1127) — not reachable.** Its service raises only
  `ValueError`, caught by the preceding branch and stringified cleanly.
- **`submit_for_review` (~1205) — not reachable.** Sets a field and saves.

So the remaining work is **one line, not three** — worth noting because the
original hand-off said three, and acting on that would have been three edits for
one real defect.

**The lesson, and it is already written down.** `CLAUDE.md` says: *"Permission
enforcement uses 3 paradigms — check all three before claiming a perm is
unenforced … most `approve_*` perms exist as group-eligibility markers consumed
by template-binding logic, not as direct gates."* I checked one paradigm and
reported a gap. **Reading a single `can_*` helper is not sufficient evidence that
a control is missing in this codebase** — grep the field name across services
before filing.

### BUG (FIXED + VERIFIED) — the only NCR→CAPA promotion path was dead

Row 6's core action. On any FAIL quality report the detail page offers **Create
CAPA**; clicking it produced:

> Error Loading CAPA — Unable to load CAPA #01a11263-… It may not exist or you may
> not have permission to view it.

Reproduced on two reports. The diagnostic that cracked it: **pasting the exact
same resulting URL into the address bar worked perfectly.** So route, page and
prefill were all healthy, and only the in-app navigation resolved wrongly — it
matched `/quality/capas/$id` with the *quality report's* id bound to `$id`.

Cause: `ModelDetailPage.tsx:226` called `navigate({ to: button.getUrl(...) })`,
and that button's `getUrl` embedded a query string. In TanStack Router `to` is a
path pattern, not an href, so the query rode along inside the path, the exact
match failed, and it fell through to the dynamic route.

Fixed by the receiving session, which chose better than I suggested: rather than
special-casing this button, `getUrl` now passes through a `splitHref()` that
peels any `?query` into `search` before navigating. Every existing `getUrl` string
is untouched and the next one with a query string can't reintroduce the bug.
**Verified 2026-10-06:** QR-ASSESS-001 → Create CAPA lands on the create form with
*"Linked Quality Reports — 1 selected"*.

Cosmetic leftover, logged not fixed: the prefilled chip shows the raw UUID
(*"Report #01a11263-… - FAIL"*) rather than the report number. Only the
prefilled-from-URL path does this; picking a report by hand shows a proper label.

### GAP — there is nowhere to record an NCR that *doesn't* become a CAPA

The other half of row 6, and the half the system doesn't do.

Promoting an NCR to a CAPA now works. But the manager's weekly job is mostly the
opposite decision — *"the disposition already handles this part"*, *"one-off,
no systemic cause"* — and there is **no field, state or note for that judgement**.
An NCR that isn't promoted is indistinguishable from one nobody looked at.

This matters more than it sounds. An auditor asking *"how do you decide which
nonconformances get corrective action?"* is asking for exactly this record, and
ISO 9001 10.2.1 requires evaluating whether action is needed to eliminate causes —
the *evaluation*, not only the action. Today the evaluation leaves no trace.

**Not proposing a model.** Per the field-over-table default this is most likely a
nullable `capa_decision` + `capa_decision_rationale` on the quality report, set
when a manager triages. Flagging it as a genuine gap for you to scope, not
designing it here.

### NOT A GAP — R1 was misframed, and the system is deliberately right

R1 read *"Approve release of a unit whose scope changed after the customer
signed"*. That is wrong, and in an instructive way: **the QA Manager does not
approve this. The customer does.**

`services/reman/release.py` models it exactly to the product boundary:

- `request_authorisation(core)` computes the **over-and-above** work — raised
  repair codes minus what the sold rebuild level already covered — and refuses
  with *"Nothing … goes beyond the rebuild level that was sold"* when findings
  added nothing. Only genuinely new work reaches a gate.
- `record_authorisation(core, approved)` records **what the customer said**.
  Approved resumes rebuild; declined sends the unit to `DECLINED` rather than
  straight to returned, because it still physically has to go back.

The module docstring is explicit that UQMES does not quote, approve quotes or
raise POs — it produces the scope, exports it, records the answer. That is the
CLAUDE.md boundary implemented faithfully, and `scope.py` even carries a
`because` field giving each operation's provenance *"so a planner can challenge
it"*.

The UI exists too (`WorkOrderCoresCard.tsx:188-209`). **Row relabelled** to
"Record the customer's answer on over-and-above work."

**But there is no exhibit:** no core is in `AWAITING_AUTHORISATION` (8 cores:
2 RECEIVED, 2 IN_DISASSEMBLY, 3 DISASSEMBLED, 1 SCRAPPED). Fifth instance of the
dark-exhibit pattern, and the costliest, because over-and-above authorisation is
the single most distinctive thing reman does.

### BUG (FIXED) — UI-created RCAs had no recorded author

Narrow, real, and fixed. `CapaRcaTab.tsx` built its create payload without
`conducted_by`, and `RcaRecordViewSet` had no `perform_create` to default it, so
**every RCA created through the UI had a null author**. The seeded RCAs all have
it set (149/150/151/152), which is why demo data looked healthy.

Visible symptom nobody had connected: `CapaRcaTab.tsx:365` renders *"Conducted by
{username}"*, blank on every user-created RCA.

Fixed server-side (`perform_create` defaults to `request.user`), with a regression
test. Server-side matters — a client-side default would let an API caller omit the
field and reintroduce the gap.

### OPEN (needs a decision) — RCA has two verification paths; the guarded one is unreachable

**I filed this first as "the self-verification control can never fire" and had the
mechanism wrong.** The correction matters more than the original claim, and the
peer who took the fix caught it.

What I actually proved as `maria.qa` on 2026-10-06: created a 5-Whys RCA on
`CAPA-2024-005`, then `POST /api/RcaRecords/<id>/approve/` → **200**. Authored and
verified by the same person, no justification, no refusal. The record reads
`root_cause_verification_status: VERIFIED`, `root_cause_verified_by: Maria
Santos`, **`self_verified: false`**.

What I got wrong: I attributed that to the null `conducted_by` defeating the guard
at `rca.py:40`. It doesn't. **That guard lives in `verify_root_cause`, which is
not what `/approve/` calls.** There are two distinct functions:

| | `verify_root_cause` (rca.py:27) | `approve_rca` (rca.py:61) |
|---|---|---|
| Independence guard | **yes** — refuses, or demands ≥10 chars justification | **none, by design** |
| Sets `self_verified` | yes | **no** |
| Reachable from a viewset | **no** | yes, `/approve/` |
| Reachable from the UI | no | no |
| Callers | model wrapper + 4 test sites | the `approve` action |

`approve_rca`'s docstring states the intent plainly: *"no self-verification rules
apply here because the reviewer is explicitly a different persona."* The design is
coherent on paper. **Nothing enforces that the reviewer is a different person.**

Three consequences, all verified:

1. **The guarded path is dead code from a user's perspective.** `verify_root_cause`
   is called only by `RcaRecord.verify_root_cause()` and by
   `test_capa.RCASelfVerificationTestCase`. No viewset reaches it.
2. **`self_verified` can only ever be set by that dead path, so it is always
   False** — including on the record above, which *was* self-verified. That is a
   false record, not merely a missing one.
3. **There is no RCA approval UI at all.** The only `RcaRecords` call in the
   frontend is `create` (`useCreateRcaRecord.ts`). I reached `/approve/` only by
   hand-writing the POST. **So today's real exposure is API-only** — nobody is
   self-approving RCAs through the product, because the product offers no way to.

**Severity is therefore lower than I first said, and the shape of the problem is
different.** It is not a broken control; it is an incoherent one — a guarded
function nobody can call, an unguarded one they can, and a flag that is
structurally always false.

**Your decision, and it is genuinely a design call**, which is why the peer
stopped rather than acting:

- Make `/approve/` delegate to `verify_root_cause` (accepting a justification).
  This enforces independence on the reachable path, but **changes an API contract
  and reverses that docstring's stated design** — the reviewer persona would no
  longer be assumed distinct.
- Or keep the two personas and enforce distinctness some other way (a different
  `review_rca` holder, or an explicit check that reviewer ≠ conductor).
- Or accept it: `review_rca` is a separate permission, approval is a reviewer act,
  and the independence question is answered by who holds the perm.

Whichever way, `self_verified` should stop being written as False by a path that
cannot compute it, and the dead `verify_root_cause` should either become reachable
or be removed — a function with four passing tests that no user can execute is a
liability, because it reads as coverage.

**The generalisable lesson, and it is better than the one I first drew:**

> Passing tests prove the code works, not that anyone can reach it. Five green
> self-verification tests sat on a path no viewset and no screen calls. Check
> reachability — who calls this, from where — before counting a control as
> present.

### BUG (major) — `auto_now_add` silently discards every seeded step timestamp

Visible on the **hero showcase work order**: the Digital Traveler on
`WO-SHOWCASE-01` prints step durations of **`-11520m`, `-8640m`, `-5760m`,
`-2880m`** — negative minutes, on the single work order a demo most likely opens.

**Root cause, confirmed end to end.** `StepExecution.entered_at` is declared
`models.DateTimeField(auto_now_add=True)` (`models/mes_lite.py:1709`). Django
**ignores any value supplied for an `auto_now_add` field on insert** and always
writes `timezone.now()`.

`showcase.py:375-395` computes the pair correctly — `entered` one day *before*
`exited`:

```python
entered = self.today - timedelta(days=2 * (count - i) + 1)
exited  = self.today - timedelta(days=2 * (count - i))
```

The `entered` value is then silently thrown away on write while `exited_at`
(an ordinary field) keeps its backdated value. `duration` is
`exited_at - entered_at` (`models/mes_lite.py:1865`) — correct logic fed
impossible data — and the frontend renders `Math.round(duration_seconds / 60)`
(`qa-progress-section.tsx:375`) without guarding the sign.

Observed on the API:

| Step | `entered_at` | `exited_at` |
|---|---|---|
| Cleaning | 2026-10-06 | **2026-10-04** |
| Component Grading | 2026-10-06 | **2026-10-02** |

**This is wider than one ugly number.** Every sampled `entered_at` across 382
step executions reads `2026-10-06T18:04:19–20` — identical to the second, i.e.
the seed run time. So **all step timing in demo data is fiction**, and any
analytics, cycle-time or labour figure derived from it is meaningless. The
negative duration is merely the one case where the fiction is visible.

**It is also a product constraint, not only a seeding defect.** With
`auto_now_add`, a `StepExecution` can *never* be backdated by anything — import,
migration or correction. Anyone bringing in history from Glovia at go-live hits
this wall, and it is worth checking whether it is why the master-workbook
go-live-history feature was built and then removed ([[master-workbook-decisions]]).

**Fix:** `auto_now_add=True` → `default=timezone.now`, which still auto-populates
on create but respects an explicit value. Needs a migration. Guarding the
frontend against a negative duration is worth doing too, but it is a plaster —
the data is wrong, not the rendering.

**Generalisable, and a sibling of the RCA lesson above:**

> `auto_now_add` makes a field unwritable, silently. Code that passes a value for
> one is not wrong-looking — it reads perfectly — and no error is raised. Seeds,
> imports and corrections all fail the same quiet way.

### NOT A FINDING — the operator home's dead tiles are a known, intended preview

Recording so a later pass doesn't re-file it. Confirmed with the user 2026-10-06:
**the dimmed tiles are deliberate and known.**

`OperatorHomePage` says so on the page: *"Preview build — Up next, Then, Scan, In
progress, Notifications, Shift notes, the station-scope combobox, and the clock
are live. Dimmed tiles show the planned layout; they light up as the blocker
model and other pieces land."*

Measured rather than taken on trust — these carry `pointer-events: none`:
**Report a problem**, **Call my lead**, **Undo**, **Flag**, and the
*"Today: 14 parts completed"* summary.

**The thing worth knowing is what is NOT preview.** Row 6 ("report a problem
mid-step") looks unimplemented if you judge by the dead *Report a problem* tile.
It isn't — **"Can't run this?" is live and is the real implementation**, and it is
better than the dead tile implies: four reasons, each routed to a named owner
(*Missing material → Materials*, *Tooling / fixture unavailable → your lead*,
*Quality hold → QA*, *Something else → your lead*), and it states the consequence
up front — *"It routes straight to the owner, leaves your queue, and your next
job appears immediately."*

So the operator's blocker path exists and is well designed; only the duplicate
home-page affordance is pending. **Audit the live control, not the dimmed one.**

Not exercised: firing it would have blocked `WO-SHOWCASE-01`, the hero demo work
order. To be run against a non-showcase job.

### RE-CHECKED 2026-10-06 — the CAPA dialog focus bug is FIXED

The severe one (typing `abcdef` into *Success Criteria* put `a` there and `b`–`f`
into *Verification Method*, in reverse). Re-tested on `CAPA-2024-004`'s **Add
Verification Plan** dialog.

**Tested with real keystrokes, not scripted input** — this matters, because
setting `.value` through the native setter drives a React controlled input without
ever exercising focus, so my earlier successful use of this dialog today proved
nothing about the bug. Three separate key presses produced:

```
Verification Method: "abc"    focus: still on Method    caret: 3
Success Criteria:    ""
```

In order, in the right field, focus retained, caret not reset. The original
symptom was the opposite on all four counts. **Fixed.**

### RE-CHECKED 2026-10-06 — core lots are excluded everywhere, but it can't be proven in the browser

The fix landed and is better than a patch: `incoming_inspection.awaiting_inspection(qs)`
is now a **shared** helper carrying the `holds_cores=False` exclusion, and the
inspector's inbox imports it (`inspection_inbox.py:126-129`) instead of keeping
its own copy.

Its docstring names a **third** copy — the MaterialLot list's `inspection_pending`
lens. I checked it: `viewsets/mes_standard.py:699-706` does carry
`.filter(holds_cores=False)`. **All three agree today.** Three copies of one rule
remains a standing drift risk, and this bug was caused by exactly that; the
docstring's warning is the mitigation.

**But the fix is unverifiable from the UI, because there is nothing to exclude.**
Sarah's Receiving chip shows 5 lots, all supplier material — correct, but it would
look identical if the filter were missing. All **10** MaterialLots report
`holds_cores: false`, and `/reman/core-lots` reads *"0 unidentified units across
0 lots"*.

So this is logged as **verified by reading, not by walking** — the one place in
this audit where the code had to settle it, because the data cannot.

**Sixth dark exhibit, and a new kind.** The previous five were features whose
demo data was missing. This one is a *guard* whose counter-example is missing:
bulk core receiving has no demo lot, so neither the exclusion nor the core-lot
workflow itself can be shown. Worth a seeded bulk lot — it would light the
`/reman/core-lots` surface **and** make this regression detectable.

### BUG (severe, compliance) — any operator can write training records, for anyone

Found auditing Operator row 10 ("see what I'm qualified for"). **Proven by doing
it**, logged in as `mike.ops`, an operator.

`POST /api/TrainingRecords/` → **201 Created**. Mike awarded *himself* an **L4
(Expert)** Nozzle Inspection Certification — the exact certification the dashboard
showed expiring for him in six days. A second probe created a record for
**user 149, Maria Santos, the QA Manager**. Also 201.

Both probe records were deleted afterwards and the table is back to 24; the
cleanup itself exposed the shape of the bug, because `DELETE` returned **403** for
Mike. He can create and change, but not delete.

**Cause.** `presets.py:304` places

```python
# Training
'add_trainingrecord', 'change_trainingrecord',
```

inside **`STAFF_OPERATIONAL_WRITE`**, which is spread into eight groups —
`tenant_admin`, `qa_manager`, `qa_inspector`, `production_manager`, **`operator`**
(line 743), `shift_lead`, `document_controller`, `engineering`.
`delete_trainingrecord` is correctly isolated in `MANAGER_DELETE_PERMISSIONS`
(line 490).

**That asymmetry is the tell: the file intended training to be controlled, and
add/change slipped into the wrong bucket.** Every neighbouring entry in that block
carries a comment justifying its placement — the `orderline` lines explain why
recording demand differs from committing capacity; line 438 explains why the
teardown tech keeps `grade_component`. The Training pair has no such reasoning. It
reads as an oversight in an otherwise deliberate file.

**Why this is severe rather than untidy.** Training records are *the* qualification
control, and three audited workflows read from them:

- QA Manager row 8 — "qualify someone for a process" is the authority this
  bypasses.
- Operator row 3 — "prove qualification before starting" checks a record the
  operator can write.
- Operator row 12 / `core/second_person.py` — the training override exists
  precisely so an unqualified operator needs *someone else*; self-certification
  removes the need for the override at all.

ISO 9001 7.2 requires the organisation to determine competence and **retain
documented evidence** of it. Evidence a person can write about themselves is not
evidence. The training matrix, verified as sound earlier in this audit, is
rendered decorative — it faithfully displays numbers anyone can set.

**Decided by the user 2026-10-06, and handed off.** Remove from **`operator`**
and **`qa_inspector`** only; keep it for `tenant_admin`, `qa_manager`,
`production_manager`, `shift_lead`, `document_controller` and `engineering`. The
user's constraint was "be liberal, but definitely not operators and customers,
maybe inspectors too".

**Customers were already safe** — the `customer` group carries an explicit narrow
permission list and never receives `STAFF_OPERATIONAL_WRITE`. Same for `auditor`
and `purchasing`. Verified directly, so nothing to change there.

**The inspector question was settled by evidence, not preference.**
`override_training_gate` — the authority to vouch for an unqualified operator at a
gate — is held by exactly four groups (`TRAINING_GATE_OVERRIDE_PERMISSIONS`,
presets.py:420): tenant_admin, qa_manager, production_manager, shift_lead.
**`qa_inspector` is already deliberately excluded there.** Writing a training
record is the *stronger* act — the override is one-time, the record is standing —
so an inspector who cannot wave someone through once should not be able to
certify them permanently. Removing it aligns two existing controls rather than
drawing a new line.

Worth sweeping `STAFF_OPERATIONAL_WRITE` for other compliance-shaped records that
landed in an operational bucket. This is the only one found so far, and it was
found by accident.

### GAP (exhibit + surface) — the qualification gate is sound, unprovable, and its evidence is invisible

Covers Operator rows **3** ("prove qualification before starting, or be
authorised") and **12** ("be called over as the second person"), and by the gates
rule Shift Lead row **5** ("authorise an unqualified operator, on the record").
**Three rows across two roles rest on one gate.**

**The gate itself is well built.** `services/mes/lifecycle.py:160` —
`authorize_start(operator, step, process, authorizer=, reason=)` raises
`NotQualified` with the missing requirements, raises `OverrideReasonRequired` when
an authorizer is supplied without a reason, and otherwise records a
`supervisor_override` (worker, authorizer, reason) onto the execution's
`training_authorization` snapshot. Default-deny, override possible, override
recorded — the right shape, and `mes_lite.py:1302` refuses to advance an
execution that has no snapshot at all.

**Seventh dark exhibit, and the most consequential.** It cannot fire in demo data.
All four step-scoped `TrainingRequirement` rows are **`min_level: 1`**, and
`mike.ops` holds all five training types (Torque L2, Safety L3, Assembly L3, Flow
Testing L3, Nozzle Inspection L1). Every operator clears every bar, so neither the
refusal, nor the second-person override, nor the shift lead authorising it can be
demonstrated to anyone.

Cheapest fix: raise one step-scoped requirement above an operator's level — e.g.
Nozzle Inspection to `min_level: 2`, which Mike holds at L1. One field, and three
rows across two roles become demonstrable at once.

**A distinction the docs should state, found while testing this.** The training
matrix's *"Role fit — 1 gap"* and the start gate are **different checks**.
Requirements are scoped either to a **job role** or to a **step**; the matrix
reports role gaps, the gate reads step requirements. Mike shows a role gap and can
still start every step, and that is correct, not a bug. Anyone reading "1 gap" as
"blocked from working" will be wrong.

**Separately: the override evidence has no screen.** `training_authorization` is
exposed on the StepExecution **detail** serializer (`mes_lite.py:1447`) but not on
the 14-field list serializer, and **nothing in the frontend reads it** — a grep of
`src/` outside generated types finds no consumer. So when a shift lead authorises
an unqualified operator, the record is written and reachable by API, but no screen
in the product shows who authorised what. For AS9100 that evidence is the whole
point of permitting the override.

*(Checked before filing: the field's absence from a list response is the light
serializer, not a missing field. The detail endpoint returns it, `null` on seeded
rows.)*

### BUG (severe, compliance) — training was not alone: five more compliance records are operator-writable

The training-record fix is **verified** (`POST /api/TrainingRecords/` as
`mike.ops` now returns **403**; it returned 201 before). But the sweep it
prompted found the same hole in five more places.

**Probed as `mike.ops`, an operator.** The signature to look for is **400, not
403** — a validation error means the caller *passed* the permission check and only
failed on a missing field:

| Endpoint | Result as operator |
|---|---|
| `TrainingRecords` | **403** — fixed |
| `CalibrationRecords` | 400 → **proven 201 with valid data** |
| `Sampling-rule-sets` | 400 (passed permission check) |
| `LifeLimitDefinitions` | 400 (passed permission check) |
| `SupplierQualifications` | 400 (passed permission check) |
| `PartApprovals` | 400 (passed permission check) |

**Calibration is proven, not inferred.** With a valid payload Mike created a
**PASS** calibration record against CMM Zeiss-1, due a year out — certifying a
measuring instrument as fit for use. 201 Created. (Probe deleted; the table is
back to 14. `DELETE` returned **403** for him, the same add-but-not-delete
asymmetry as training.)

This is the closest twin to the training bug and arguably worse: a calibration
record is the evidence an instrument may be trusted, and the gauge-recall work
earlier in this audit (ISO 9001 7.1.5.2) reads exactly these rows. An operator who
can write one can also silently return a failed gauge to service, since
`apply_calibration_result_to_equipment` flips `OUT_OF_SERVICE` → `IN_SERVICE` on a
PASS.

The other four follow the same pattern and were **not** probed to completion —
they return 400 on an empty body, which proves the permission check passed but not
that a complete record would be accepted. Each deserves one probe before being
called a defect.

**The 400-not-403 inference was challenged and then proved, in this app.** The
objection was fair: wouldn't DRF validate fields before checking permissions? If
so, a 400 would say nothing about authority. Settled by sending an **identical
empty body** to four endpoints as `mike.ops`:

| Endpoint | Result |
|---|---|
| `TrainingRecords` (known denied) | **403**, no field errors |
| `CAPAs` (known denied) | **403**, no field errors |
| `CalibrationRecords` | **400** — "equipment: This field is required" |
| `LifeLimitDefinitions` | **400** — "name: This field is required" |

Same request shape, different outcomes. Were validation first, all four would
return 400. DRF runs `check_permissions` inside `initial()` during `dispatch()`,
before the view handler and therefore before `serializer.is_valid()` — so a 400
can only mean the permission gate was already cleared.

**Keep this probe.** An empty-body POST is a cheap, non-mutating authority test for
any endpoint: 403 means gated, 400 means reachable. It needs a known-denied
control in the same run to be trustworthy, which is what `TrainingRecords` and
`CAPAs` provide here.

**All five suspects resolved 2026-10-06 with real payloads. Three confirmed, two
cleared.** Every probe record was removed afterwards.

| Record | Operator can create? | Can modify? | Verdict |
|---|---|---|---|
| `CalibrationRecords` | **201** | — | **DEFECT** |
| `Sampling-rule-sets` | **201** | **AQL 1.0 → 6.5, NORMAL → REDUCED** | **DEFECT** |
| `LifeLimitDefinitions` | **201** | **hard limit → 999999** | **DEFECT** |
| `SupplierQualifications` | 201, but `PENDING` | status read-only | **not a defect** |
| `PartApprovals` | 201, but `PENDING` | status read-only | **not a defect** |

**Why the last two are fine.** They create a *draft*. `status` is read-only on the
serializer — a `PATCH` to `APPROVED` returns **200 with the status still
`PENDING`** — and the real transition is the `grant` service action, gated by
`approve_*`. So the broad `add_*` perm buys nothing. **This is the pattern the
other three should follow**: let anyone raise a draft, gate the act that gives it
force.

**Severity of the three, in order:**

1. **Sampling rule sets.** Loosening AQL 1.0 → 6.5 and severity to REDUCED means
   far fewer parts are inspected. An operator can lawfully reduce the inspection
   burden on their own work, and nothing about the output looks wrong afterwards.
2. **Calibration records.** Certifies an instrument as fit. Worse than forging
   evidence: `apply_calibration_result_to_equipment` flips `OUT_OF_SERVICE` →
   `IN_SERVICE` on a PASS, so an operator can quietly return a *failed* gauge to
   service — defeating the 7.1.5.2 control the recall page was built to serve.
3. **Life limit definitions.** A hard limit of 999999 means a life-limited part
   never retires. Partly mitigated: the model is **versioned**, so the edit
   created a new version with a new id rather than overwriting — the change is
   traceable even though it should not have been possible.

**Two incidental findings from the cleanup:**

- **`DELETE` is refused even to `tenant_admin`** on LifeLimitDefinitions,
  SupplierQualifications and PartApprovals (403), while TrainingRecords and
  CalibrationRecords delete cleanly (204). Archiving via `PATCH archived=true`
  works. Not wrong — consistent with soft-delete — but the API is inconsistent
  about which models accept `DELETE` at all.
- **`LifeLimitDefinition` is a versioned model**, so a `PATCH` returns a *new id*.
  Anything cleaning up after itself must re-query by content, not by the id the
  create returned. Cost me a 404 before I noticed.

**Is the enforcement itself misconfigured? No — checked all three paradigms.**
Worth establishing, because "a gate is broken" and "the wrong people hold the key"
need different fixes.

1. **Action gating.** No dedicated permission exists for any of the three — no
   `perform_calibration`, no `manage_sampling`, no `set_life_limit`. They are
   plain CRUD perms. `CalibrationRecordViewSet` *does* declare
   `action_permissions`, but only over the two **read** actions (`exposure`,
   `exposure_export` → `view_qualityreports`); nothing gates `create`.
   `SamplingRuleSetViewSet` and `LifeLimitDefinitionViewSet` declare none.
2. **Queryset filtering** — `for_user()` shapes reads, not creates. Not applicable.
3. **Per-instance authorization** — nothing to authorize against on a create.

So there is **no dead permission and no broken wiring**. The machinery does
exactly what it says. The defect is one of **classification**: three
compliance-evidence records were filed into an operational write bundle.

**And the file half-knows it.** Its own header (line 35) states *"Audit-record
writes: none. Append-only audit tables (sampling audit log, …)"* — the sampling
**audit log** is protected, while the sampling **ruleset** that the log records
changes to is not.

The three differ in how they got there, which matters for the fix:

- **Sampling** is the only one with a stated intent, and the intent is narrower
  than the effect. Line 293: *"Sampling — rules editable by quality doers today;
  deletes are manager-tier."* But `STAFF_OPERATIONAL_WRITE` is spread into **nine**
  groups — including `operator` and `purchasing`, who are not quality doers.
  **The comment and the code disagree**, and the comment is right.
- **Calibration** sits under `# Equipment & Calibration`, beside `add_equipments`
  and `add_equipmenttype` — classified as equipment master data. A calibration
  *record* is not configuration; it is evidence about an instrument.
- **Life limits** sit under `# Milestones & life tracking`. The neighbouring
  comments carefully justify each *delete* grant and say nothing about why
  add/change of a limit **definition** is broadly held. Same silent-oversight
  shape as the training pair.

**Consequence for the fix:** nothing in the enforcement layer needs repairing.
Move the three pairs into a narrow block (sampling's own comment names the
audience), or better, adopt the draft-plus-grant pattern the supplier records
already use.

**The common shape, and the thing to fix once rather than six times:**

> A compliance record whose create is gated only by the CRUD `add_*` permission
> inherits whatever broad write-bundle a group happens to hold. Authority over
> *evidence* needs to be modelled separately from authority over *work*.

`STAFF_OPERATIONAL_WRITE` is spread into **nine** groups, and every one of them
gets all of this.

**Correction to my own earlier note.** I reported eight groups and said
`purchasing` was unaffected. Wrong — there are **nine**; I had piped the grep to
`head` and read a truncated list as complete. `purchasing` does spread
`STAFF_OPERATIONAL_WRITE` and did hold training-record write. The peer caught it.
**Second time in this audit a truncated or case-limited grep nearly produced a
false statement** — the first was a case-sensitive grep missing `YOUR GAUGES`.
Treat a `| head` on an enumeration as a sample, never as the set.

### GAP (data) — material traceability is half-dark: forward trace is empty everywhere

Operator row **5**, and it reframes the row. The operator does **not** pick a lot.
`services/mes/consumption.py` draws the BOM lines for the step from stock
automatically on part exit, **FEFO** (oldest-expiry first, no-expiry last), and
attributes the draw to the operator. So the row should read *"have the lots I used
recorded against the unit"*, not *"record which lot was taken"*.

The design is well reasoned and the docstring states three decisions worth keeping:
consumption **never blocks advancement** (refusing to advance would punish an
operator for a stock-data error and teach people to work around the system — the
material *gate* before scheduling is the right place to stop work); **FEFO not
FIFO**; and **"no operator, no record"**, because `MaterialUsage.consumed_by` is
required and an automated advance has no one to attribute to.

**That last decision is exactly why the demo is empty.** `MaterialUsages` returns
**0 rows**. The seed advances parts without a real operator, so by design nothing
is recorded.

**The visible consequence, checked on six lots:** two-way lot trace is half dead.

| | backward | forward | customers |
|---|---|---|---|
| RCV-MAT-0001…0005, RCV-MAT-HOLD | **9 fields** | **0** | **0** |

Backward (supplier, their lot, heat, PO) is populated. Forward — *every part a step
drew this lot into, up through assemblies to the work order, order and customer* —
is **empty for every lot in the system**.

So **"which units are affected if we recall this lot?" cannot be answered in a
demo**, and the `lot_trace` report adapter built to answer it renders half a page.
That is a headline MES capability and arguably the single most persuasive thing
this product does.

It also compounds **QA Manager row 11** (audit readiness): that row already lacked
a per-serial history, and the material genealogy that would partly substitute for
it is empty too.

**Eighth dark exhibit**, and the costliest so far. Fixing it is not a seed tweak in
the usual sense — the seed would have to advance parts *through the service as a
real operator* rather than staging end states, which is the same root cause as the
`auto_now_add` timestamps. Worth treating as one piece of work: **make the demo
walk the flow instead of staging its outcome.**

### VERIFIED — the DWI runtime is the strongest operator surface in the product

Operator row **4**. Walked as `mike.ops` on the Assembly step's authored substep
(12 substeps exist across Assembly, Cleaning and Component Grading).

What it does, all observed:

- Renders the instruction with a **Caution** callout — *"Torque is safety-critical
  — use the calibrated wrench and the recorded value."*
- Shows the characteristic with its spec inline: **Assembly Torque, A-01,
  Required, 25 +2 −2 Nm**.
- Live validation. Before capture: *"2 required fields missing — Assembly Torque,
  New seals installed"*. After entering 25.0: an **In spec** badge, **Captured ✓**,
  and *"2 fields captured"*.
- A separate **attestation** checkbox with its own wording — *"I confirm new seals
  were used (no reused seals)"* — distinct from the measurement.
- A **review screen** before commit: *"Confirm the captures look right, then
  complete the step"*, each capture listed with an **Edit** affordance.

**Checked and NOT a bug (twice).** The a11y tree reports the instruction prose as a
`textbox`, which looks alarming for document-controlled content — it is a rich-text
renderer with `contenteditable="false"`. And the runtime is **not** orphaned: it is
linked from `OperatorHomePage`, `StartWorkDialog`, `useWorkUnit` and the completion
adapters, with **Resume** passing `execution: activeRun.id`.

**Two small things, neither a defect:**

- Landing on the route without params prints developer copy into an operator
  surface: *"Add `?execution=<id>` to the URL to enable submit."*
  (`OperatorSubstepRuntimePage.tsx:1208`). Only reachable by typing the URL, since
  every in-app entry passes the param — but it is the wrong register for the
  audience, and a stale bookmark would reach it.
- The measurement input's `aria-label` is literally **`—`** (an em dash). A screen
  reader announces nothing useful for the one field that carries the value.

### VERIFIED (end to end) — the real operator journey, and row 5 proved by prediction

Walked the whole path as `mike.ops` on `WO-2024-0042-A` (ordinary demo work, not an
exhibit): **Start Work → batch claim → DWI runtime → capture → review → Complete
step**.

**The batch claim dialog settles the model** the user corrected earlier:
*"Check the parts you'll work on, in the order you'll work them. After you complete
a part's step, the runtime moves to the next checked part automatically."* Parts
are grouped by step with counts. That is batch flow with per-unit records — no
pause, no handover.

Claiming routed to the runtime with **part, workOrder and execution** all in the
URL, which also explains the developer string noted above: it appears only when
`execution` is absent, and the real path always supplies it.

**Row 5 confirmed by prediction, which is the strongest form available.** I had
argued consumption never fires because the seed writes rows directly instead of
calling the service, and that the BOM and data were otherwise ready. Before
completing: `MaterialUsages` = **0**. After one real completion: **2 rows**, both
`consumed_by` Mike Rodriguez against INJ-0042-020. Nothing was changed to make this
happen — the machinery worked the moment a real operator advanced a part. That
closes any doubt about the deferred seed work being the right fix.

**Row 8 works on the backend**: execution `COMPLETED`, `exited_at` set,
`completed_by` Mike, part advanced to Nitride Coating. A second click is
**idempotent** — the part did not advance twice and no second material draw
occurred.

### BUG (UX) — finishing the LAST part of a batch leaves the operator on a dead screen

**My first diagnosis of this was wrong and the correction is the finding.** I
reported "no feedback, no navigation". A toast *does* fire — I polled 5 s after the
click and sonner dismisses at ~4 s, so I missed it. Settled from the code rather
than by fighting the UI again.

**The real defect is narrower and sharper.** `completion-adapters.tsx:114`:

```js
/** Advance the operator to the next part in the StartWorkDialog queue.
 *  No-op when the queue is empty or essential context is missing. */
if (!queue || !workOrderId) return;
const ids = queue.split(",").filter(Boolean);
if (ids.length === 0) return;
```

With parts remaining it works well — re-reads the next part's *current* step rather
than trusting the dialog snapshot, re-runs the competence and reassignment gates
through the shared path, and announces *"Moving to next part (N remaining)"*. The
handling of a gated next part is genuinely thoughtful (it stops the queue and sends
the operator to Start Work, "where the supervisor-override panel lives").

**But the empty queue — the last or only part — is an explicit no-op.** So on
finishing a batch the operator is left on the **stale review screen** with
**Complete step still enabled**, URL unchanged. Confirmed stable over several
seconds.

Consequence: the obvious reading of an enabled button is that the press failed, so
they press again. The second press is **idempotent** (verified: no second advance,
no second material draw), but it surfaces a technical warning meant for a different
case — *"Step submitted — lot waiting on cohort | No active StepExecution; Substep
'Return inspection (post-coating)' not completed for this part"*. The operator's
reward for finishing the batch is an error-shaped message.

**Fix:** the `ids.length === 0` branch needs a terminal state rather than a silent
return — route back to the operator home, or render a "batch complete" state that
retires the button. The no-op is correct for *"essential context missing"* and
wrong for *"you have finished"*; those two cases are currently the same line.

*Method note — third toast-timing near-miss in this audit. Poll from t=0, and when
the UI resists, read the handler.*

### CORRECTION — the second-person pattern DOES have an exhibit: reassignment, not training

Above I recorded row 12 as implemented-but-unprovable because the training gate
cannot fire in demo data. **That was half wrong.** `start_execution` runs two gates,
and the other one fires readily.

Trying to claim `INJ-0042-022` raised:

> **Assigned to someone else** — "This step is assigned to another operator. A
> supervisor must sign in below to reassign it — logged against their name.
> Currently assigned to **Lisa Park**." + *Supervisor authorization* →
> **Authorize & start**

So the second-person mechanism is demonstrable today, with the right wording
(*"logged against their name"*) and a named current owner. Only the **training**
flavour of it is dark.

Screenshot: `docs/assets/operator/op-02-reassignment-gate.jpeg`. Rows **7** and
**12** both verified by it.

### RETRACTED (false finding) — "Start Work silently swallows claim failures" was my measurement error

**There is no bug. I filed one, passed it to a peer, and told the user about it.**
Recording it in full because the mistake is more instructive than the finding would
have been.

**What I claimed:** pressing **Start** on a part assigned to someone else produced
nothing — no panel, no toast, no error — across three different server responses
(two 409s and a 400). I called it "the Start button discards the claim response
wholesale".

**What is actually true:** the gate panel renders perfectly. Measured on the live
page — rect 598,227 at 512×423, `opacity: 1`, `visibility: visible`, and
`document.elementFromPoint` at its centre returns the panel itself. The *outer*
dialog is the one being covered. A toast fires as well.

**The error:** I probed with

```js
document.querySelector('[role="dialog"]')
```

which returns the **first** match — the outer *Start work on parts* dialog. The
gate panel is a **second** dialog element. Every time I asked "did the dialog show
an error", I was reading the wrong node and concluding nothing had appeared.

**The part that should have caught it, and didn't.** I took a screenshot of the
"silent" state, named it `op-03-silent-claim-conflict.jpeg`, filed it as evidence
— **and never opened it.** The image shows the gate panel in full: *"Assigned to
someone else … Currently assigned to Sarah Chen"*, supervisor email, password,
reason, **Authorize & start**. I captured proof against my own claim and didn't
look. (Renamed to `op-03-gate-panel-on-claim-conflict.jpeg`.)

**Cost:** a peer began fixing a non-bug. They had read the code and said *"on paper
the code handles it — something is rendering invisibly, not being skipped"*. They
were right, and deferred to my browser evidence because "verified in the browser"
outranks "verified by reading" — a rule this audit has leaned on correctly many
times. **It only holds if the browser check is sound.**

**Three rules, earned:**

1. **`querySelector` on `[role=dialog]` is wrong whenever a dialog can stack.** Use
   `querySelectorAll` and search all of them, or match on content.
2. **A screenshot taken as evidence must be looked at.** An unopened screenshot is
   not evidence; it is a file.
3. **Absence claims need a positive control.** "Nothing was shown" should never
   rest on one query returning nothing — the same discipline as the known-denied
   control that made the 403/400 permission probe trustworthy.

Row 7 and row 12 remain verified, now on firmer ground: the reassignment gate is
not merely implemented, it is the normal, visible behaviour on a claim conflict.

### BUG (CRITICAL, verified) — any operator can forge a manager's e-signature, permanently

**The most serious finding in this audit.** Surfaced by the scheduling session's
classification sweep as a code reading; **I probed it, and it is real.**

**Proven as `mike.ops`, an operator**, with one ordinary POST:

```http
POST /api/ApprovalResponses/
{"approval_request": "<CAPA-2024-003's request>", "approver": 149, "decision": "APPROVED"}
→ 201 Created
```

`approver: 149` is **Maria Santos, the QA Manager**. No password. No drawn
signature. No co-sign. The response came back with `approver_info` naming her.

**It completed the gate.** The `post_save` signal ran `update_status()` and
cascaded:

| | after the forged POST |
|---|---|
| ApprovalRequest | **APPROVED** |
| CAPA-2024-003 `approval_status` | **APPROVED** |

So a MAJOR CAPA's *"requires management approval before work can begin"* gate was
satisfied by an operator, in a manager's name.

**This bypasses the control I verified earlier and praised.** The `submit-response`
action demands decision + drawn signature + password re-authentication, and
correctly refuses self-approval with a justification requirement and five tests
behind it. **None of that is on the model endpoint.** `ApprovalResponseViewSet`
(`viewsets/core.py:2309`) is a plain `ModelViewSet` with no `perform_create`, and
the serializer leaves `approver`, `decision` and the signature fields writable. The
gated path is a front door beside an open window.

**And the forgery cannot be removed.** Cleaning up, `DELETE` returned **403** and
`PATCH {archived:true}` returned **403**, as administrator. By design —
`presets.py:285` states *"Responses are e-signature records: DB-immutable once
written (add only…)"*. That immutability is correct for a genuine e-signature and
becomes the aggravating factor here: **an operator can write a permanent,
un-retractable signature in a manager's name, and not even an admin can take it
back.** The probe row remains in the dev database for that reason.

I restored the surrounding state (ApprovalRequest → PENDING, CAPA → PENDING); only
the immutable response row persists, with `comments` marking it as an audit probe.

**Why this outranks everything else found:** the permission holes fixed earlier let
an operator manufacture *supporting* evidence — a training record, a calibration.
This one lets them manufacture **the authorisation itself**, in someone else's
name, in the one record type the system refuses to let anyone edit or delete.
For ISO 9001 and 21 CFR Part 11 that is the signature control, and it is open.

**Fix shape** (mirrors what already works elsewhere): force `approver` to
`request.user` in `perform_create`, make `decision`/signature/verification fields
read-only on the model serializer, and route all real approvals through
`submit-response`. Consider removing `add_approvalresponse` from the broad bundle
regardless — but **note the serializer gap is the actual hole**; moving the
permission alone would still leave every bundle-holding manager able to sign as any
other manager.

### VERIFIED FIXED — all seven compliance holes, probed individually

The scheduling session's sweep was a code reading; the receiving session fixed all
seven; **I probed each as `mike.ops` rather than accepting either on paper.** All
seven hold.

| # | Probe | Result |
|---|---|---|
| 1 | **ApprovalResponse forge** — the exact POST that worked before | **405** Method Not Allowed; request stayed `PENDING` |
| 2 | QuarantineDisposition with `disposition_type: USE_AS_IS` | **400** — *"Choosing the disposition needs `approve_disposition`. Open the disposition without a type, then decide it (a co-signer can authorize)."* |
| 3 | `POST /api/spc-baselines/` | **403** (the hand-off said 405; it is 403 — gated either way) |
| 4 | SubstepGateCompletion with `completed_by: 149`, `verification_method: PASSWORD`, forged signature | **201**, but saved `completed_by: 152` (me), method **NONE**, `verified_at: null` — actor forced, verification claims stripped |
| 5 | StepOverride with `status: APPROVED`, `approved_by: 149` | **201** saved **PENDING**, `requested_by: 152`, `approved_by: null`; self-approve → **403** |
| 6 | LifeTracking `PATCH accumulated: 999999` | **400** — *"Accumulated life can't be edited — record usage with increment, or reset it after an overhaul."* |
| 7 | Equipment `PATCH status: IN_SERVICE` on a FAIL-calibrated gauge | **400** — *"Torque Wrench TW-25's last calibration failed — record a passing calibration to return it to service."* |

**#7 closes a loop opened earlier in this audit** — that is the same TW-25 I failed
to light the gauge-recall page. The guard now refuses to let anyone flip it back.

**The error messages are the quiet win.** Not one says "permission denied" and
stops. Each names the right path instead: open the disposition and decide it, use
`increment` or `reset`, record a passing calibration. That is the difference
between a control that blocks work and one that redirects it.

**Three probe rows cannot be removed** and remain in the dev database: the forged
`ApprovalResponse`, a `SubstepGateCompletion` (node_id `audit-probe`), and a
PENDING `StepOverride` ("AUDIT PROBE delete me"). `DELETE` → 403, `PATCH` → 405,
as administrator. That is the fix working: these are now append-only attestation
records. Worth stating plainly — **a correct immutability design means a probe
leaves permanent residue**, so probe deliberately on anything signature-shaped.

**Still unverified from the sweep:** nothing. The two borderline items (FPIRecord
re-pointing, CapaVerification `capa`) and the dead grants were reported as fixed or
inert and I did not probe them; they are low-severity and the user has them.

### VERIFIED (end to end) — the qualification gate now fires, and the override is a real record

The one-field change suggested earlier (Nozzle Inspection requirement →
`min_level: 2`) was made by the receiving session, and it lit **three rows across
two roles** as predicted. Walked 2026-10-07 as `mike.ops`, who holds that
certification at Level 1.

**It warns before you act.** The Start Work dialog labels the step group
**"Nozzle Inspection (0 / 2) — Training needed"** before anything is clicked.
`work_authorization` returns the reason in plain words:

```json
{"authorized": false,
 "missing": [{"training": "Nozzle Inspection Certification",
              "reason": "Level 1, needs Level 2"}]}
```

**It refuses, and offers the right way through.** Attempting the start raises:

> **Not qualified for this step** — "The operator isn't qualified. A supervisor
> must sign in below to authorize this work — logged against their name."
> **Missing training:** Nozzle Inspection Certification — Level 1, needs Level 2
> → *Supervisor authorization* → **Authorize & start**

The reason field is prompted, not merely allowed: *"Reason (required — e.g.
line-down, trainee under direct supervision)"*. That wording does real work — it
tells a supervisor what a legitimate override looks like.

**The override is recorded properly.** Authorising as `jennifer.mgr` (Production
Manager) let the work start, and the execution's `training_authorization` holds:

```json
"override": {"at": "2026-10-07T14:11:08Z",
             "reason": "Trainee under direct supervision …",
             "worker": 152, "worker_name": "Mike Rodriguez",
             "authorized_by": 151, "authorized_by_name": "Jennifer Walsh"},
"missing":  [{"training": "Nozzle Inspection Certification",
              "reason": "Level 1, needs Level 2"}],
"authorized": false
```

Who, who authorised, why, when, **and what was missing** — with names, not only
ids, and `authorized: false` preserved so the record never claims the operator was
qualified. For ISO 9001 7.2 competence that is the right shape.

Rows **Operator 3**, **Operator 12** and **Shift Lead 5** are all demonstrable on
this one exhibit. Screenshot:
`docs/assets/operator/op-05-training-gate.jpeg`.

**The one gap from the earlier finding stands:** no screen displays this. The
record is complete and reachable on the StepExecution detail endpoint, and
**nothing in the frontend reads `training_authorization`**. An auditor asking "who
let an unqualified operator run this step, and why?" is answered by the database
and not by the product.

**Minor, unexplained, flagged not filed:** the resulting execution has
`assigned_to: null` while `status` is `IN_PROGRESS`. It may be that assignment
happens on a later claim; I have not traced it and am not calling it a defect.

### VERIFIED — the FPI buy-off holds the run, and holds it against the RIGHT part

Walked 2026-10-07 as `mike.ops` (training-override authorised) on
`WO-QA-INSPECT-01`. This is **Operator row 4's gate** and **QA Inspector row 4**.

The inspection runtime is the richest surface in the product. On one step it
carries: an **FPI hold** banner, a **rework escalation counter** (*"Rework attempt
1 of 2 — 1 more attempt before this part escalates"*), an explicit **decision
point** (*"Auto · QA result — pass takes Flow Testing, fail takes Rework"*), a
**3D model with three named callouts** to mark defects on, pass/fail capture,
equipment capture, and a signed inspection sign-off.

At review it stops with:

> **Held — First Piece Inspection buy-off required.** "The first piece
> (INJ-QA-INSPECT-001) must finish its captures, then QA buys it off. **No part
> moves past this step until then.**"
> *"A QA inspector can sign here at this station — you stay logged in."*

The buy-off dialog's wording is the best in the product:

> "By signing off you attest that the setup is correct and the first piece
> conforms, and this releases the run. **It is recorded against the QA inspector's
> name — not the person logged in.**"
> "You aren't authorized to buy off a first piece. An authorized QA inspector can
> sign here without logging you out."

Screenshot: `docs/assets/operator/op-06-fpi-cosign.jpeg`.

**The server refused my sign-off, and was right to.** I had completed captures on
INJ-QA-INSPECT-**002**, while the designated first piece is **001**. The response:
*"First piece inspection incomplete — finish the step's captures first."* So the
hold is anchored to the designated part, not to whichever part happens to be in
front of you — exactly what an FPI is for. **Correct behaviour, verified by being
blocked by it.**

**One wording nit**, logged not filed: the message says *"finish the step's
captures first"* when the reader has just finished theirs. It is the **first
piece's** captures that are outstanding, and the message would be clearer naming
it — the banner above already does.

### STILL OWED — the batch-complete fix is not yet verified

Commit `58e242a`. I could not reach a clean test: every part available to
`mike.ops` on the two demo work orders is behind a gate — assigned to someone
else, held by the FPI buy-off, or already advanced by an earlier probe. The one
part I did complete end to end (INJ-0042-020, Assembly) was completed **before**
the fix landed.

Not blocking the commit, and recorded so it is not mistaken for verified. The pass
condition stands: finish a single-part batch and land somewhere sensible —
`/workorder/$workOrderId` — with no live **Complete step** button.

### VERIFIED — R1, component grading at teardown, and the batch-complete fix

Walked 2026-10-07 as `mike.ops`. The part was reassigned to him first
(`PATCH /api/StepExecutions/{id}/ {"assigned_to": 152}` as admin) — the user's
point that on a dev database you simply make the example rather than hunting for
one.

**R1 is a DWI capture node, not a button.** `grade_component` lives in the
operator runtime, which matches the row's phrasing *"with the part in your hand"*.
The **Component Grading** substep reads:

> **Grade and sort components** — "Assess each component against the grading
> criteria and sort into reuse / rework / scrap."
> **Caution:** *"When in doubt, grade down — a reused-but-marginal component
> fails downstream."*

That caution is the best piece of domain guidance in the product. Capture is a
grade decision, the defects driving it, and a signed inspection sign-off.

**The disassembly route is a deliberate redirect**, not a dead link:
`router.tsx:1214` throws `redirect({to: '/reman/cores/$id'})` — disassembly was
folded into the core detail page. Worth knowing before someone files it.

**Batch-complete (`58e242a`) verified.** Entering through **Start Work** (so the
queue param is set) and completing the only part in the batch:

- URL moved `/operator/steps/…/substeps` → `/workorder/…`
- **Complete step** button gone
- Toasts: *"Step submitted — awaiting QA sign-off"* and *"Step submitted"*

Exactly the agreed pass condition. Note the fix only engages on the queue-driven
path; arriving by URL still no-ops, which is correct — there is no batch to be at
the end of.

### DRIFT (copy vs control) — "reuse / rework / scrap" is offered as Pass / Fail / Pending

On the Component Grading substep the instruction says to *"sort into reuse /
rework / scrap"* — three outcomes — while the only control is **Pass / Fail /
Pending**, and the stated routing is *"pass takes Cleaning, fail takes the rework
branch"*. Two outcomes, no scrap path on this screen.

Scrap exists elsewhere (the core page has a **Scrap** action, and
`COMPONENT_DISPOSITION_PERMISSIONS` splits `grade_component` from
`accept_component`), so the capability is real — the substep text promises a
three-way sort the substep cannot perform.

Low severity, but it is exactly the class this audit exists to find: **instruction
text describing a richer action than the control offers.** Either the wording
should match the two-way decision, or the third outcome needs a route.

### GAP (data) — no shift notes exist, so row 11 is half-dark

`useActiveShiftNotes` and the notification feed are both live on the operator home
— notifications verified (a CAPA assignment with a working **Got it**
acknowledgement). But `ShiftNotes` returns **0 rows**, so the tile permanently
reads *"No shift notes right now."*

Shift handover is Shift Lead row 8, already flagged **suspected weak**. The two
rows share one absent fixture: nothing in the demo ever writes a shift note, so
neither the writing nor the reading of one can be shown. Ninth dark exhibit.

### VERIFIED — the permission narrowing, in both directions

Probed 2026-10-07 across four roles. **Checking only that the excluded roles are
refused proves half the fix** — a narrowing that also broke the intended holders
would look identical from that side — so the retained roles were probed too.

| Endpoint | Operator | Purchasing* | Production Mgr | Document Ctrl | QA Manager |
|---|---|---|---|---|---|
| `Sampling-rule-sets` | **403** | 403 | **403** | **403** | **400** (allowed) |
| `LifeLimitDefinitions` | **403** | 403 | **403** | **403** | **400** (allowed) |
| `PartTypeLifeLimits` | **403** | — | **403** | — | — |
| `CalibrationRecords` | **403** | 403 | **400** (allowed) | **400** (allowed) | **400** (allowed) |

\* Purchasing from the earlier sweep, not re-probed today.

Life-tracking actions as Production Manager: `reset` → **403**,
`apply_override` → **403**.

Matches the stated intent exactly: sampling and life limits to the quality roles
plus Engineering and Tenant Admin; calibration to every staff role except Operator
and Purchasing. Nothing over-restricted.

*(`/api/SamplingRules/` 404s — wrong route name in my probe, not a finding. The
real path is `/api/Sampling-rule-sets/`.)*

### VERIFIED — closing a disposition, and a refusal that names everything at once

QA Inspector row **9**, walked 2026-10-07 as `sarah.qa`. Attempting to close an
OPEN disposition with no decision and no containment:

> **400** — *"Cannot complete disposition: No disposition decision selected;
> Containment action required before closing a CRITICAL/MAJOR disposition"*

Both blockers in one message rather than one-at-a-time. That is the difference
between a control a user can satisfy in one pass and one they bounce off twice.
State stayed `OPEN`.

The new containment/resolution fields are present: **"Resolution performed by (if
not you)"** with the explanation *"Closing the disposition records who resolved
it, and when."*

### BUG (data + UI) — the QA Inspector walkthrough's own disposition cannot be saved

`DISP-QAI-006-OPEN` has **zero linked quality reports**, while the serializer
requires at least one — `quality_reports: ["This list may not be empty."]`. So any
save from its edit form fails with a 400, and the form surfaces only *"Request
failed with status code 400"*.

**Of 20 dispositions, exactly one has no quality reports, and it is the fixture
built for the QA Inspector onboarding walkthrough.** The other 19 are fine. A
record that exists in a state its own serializer rejects was created by a path that
bypasses the serializer — the seed.

Two smaller things found alongside, on the same form:

- **The Disposition Type select shows `Rework` on a disposition whose type is
  empty.** There is no blank option, so an untyped disposition reads as a typed
  one, and a save submits a type the user never chose.
- **`disposition_type` is silently ignored on PATCH**, returning **200** with the
  value unchanged, where a *create* with a type gives a clear 400 explaining that
  choosing it needs `approve_disposition`. Same rule, two behaviours — an
  inspector can pick a type, save successfully, and believe it took.

*(I first assumed the form's 400 was the disposition-type guard. It was not — a
PATCH of the type alone returns 200. Checking the response rather than inferring
from the rule is what separated the two.)*

### PARTIAL — row 10's exhibit is poised correctly, but I could not confirm the queue

`INJ-QA-INSPECT-004` reads exactly as the row describes: **QR-QA-INSPECT-004-FT
FAIL** → **DISP-QAI-004-REW CLOSED / REWORK** → part now **AWAITING_QA**. The
story is staged at the re-inspection moment, which is the right place to leave it.

**What I could not establish:** whether that part surfaces in the inspector's
queue. The inspection inbox returns **in-process rows grouped by (work order,
step) with a quantity and no part ids** — e.g. *"Nozzle Inspection · 1 pcs ·
WO-QA-INSPECT-01"*. A search of the payload for the part's ERP id finds nothing,
**and that is not evidence of absence**, because no row carries part ids at all.

Left PARTIAL rather than filed. Resolving it needs expanding a grouped row in the
UI, not another API read.

### DRIFT (convention) — the disposition create/edit routes break the documented URL rule

`router.tsx:959,965` define `/dispositions/create` and `/dispositions/edit/$id`,
while the list sits correctly at `/production/dispositions`.

`CLAUDE.md` states the convention plainly: `/{domain}/{kebab-resource}/…`, with
**`/new`** for create (not `/create`) and **`/$id/edit`** for edit (not
`/edit/$id`). These two break it three ways — no domain prefix, `create` instead
of `new`, and the id and verb reversed.

Cosmetic, but it cost me a 404 and a detour mid-audit, and the convention exists
precisely so that guessing a URL works.

### VERIFIED (end to end) — shift handover, and it is the opposite of "suspected weak"

Shift Lead row **8** and Operator row **11**, walked across two accounts on
2026-10-07. The row was marked *suspected weak* on the strength of a route
existing. **That guess was wrong** — it is one of the better-built features in the
product.

**Writing, as `casey.dual`** (`/production/shift-notes`): *"Hand off to the floor —
operators see these on their home screen and acknowledge them."* The composer has
**audience targeting by role** (Everyone on the floor, or any specific group),
a **High priority** flag, and **Requires acknowledgment**. The placeholder teaches
the genre: *"e.g. Prioritize WO-2024-0042 before lunch — customer pickup at 2pm."*

**Receiving, as `mike.ops`:**

> **SHIFT NOTES · 1 · MUST ACKNOWLEDGE**
> **High** — Casey Cross: "Night shift: TW-25 is out of service pending
> recalibration — use TW-26 for all torque work…" → **Got it**

Author attributed, priority shown, acknowledgment demanded.

**Acknowledging** records properly and clears the tile:

```json
{"ack_count": 1, "acknowledged": true,
 "acknowledged_by": [{"user_name": "Mike Rodriguez",
                      "acknowledged_at": "2026-10-07T15:18:09Z"}]}
```

**Ninth dark exhibit now lit** — the demo had zero shift notes, so neither half
could be shown. The one written during this pass is real data and stays.

**Fifth near-miss, and the cause is always the same.** I first reported the
acknowledgment as not recording. It did — I had clicked the **notifications**
"Got it", because the page has two buttons with that exact label and I took the
first match. Confirmed from the network log: both clicks were
`POST /api/notifications/feed/{id}/mark-read/`.

> **The repeating failure is selecting the first match of an ambiguous selector.**
> It produced the false "silent claim failure" (first `[role=dialog]` of two), and
> it produced this. **Rule: when a selector could match more than one element,
> disambiguate by surrounding context before acting — and confirm from the network
> request which thing you actually hit.**

### GAP (data) — the schedule has never been solved, so four rows cannot be walked

`/production/schedule` renders and is clearly built — **Machines / People / Work
orders** views, an **Undo**, a **Dispatch**, a load figure of 220% and *"Not
scheduled: 15"*. But it says:

> **No active schedule yet — run Solve.**
> *No schedule has been solved yet.*

`ScheduledTasks` returns **0**. Assignment and reassignment live here —
`TaskReassignControls.tsx` and `BulkReassignDialog.tsx`, both used by the schedule
page — so with nothing solved, **Shift Lead rows 2 and 3 have no surface to act
on**, and the re-plan half of C3 goes with them.

**Tenth dark exhibit, and the largest.** The APS is a headline capability — it is
the "A" in the product's own description — and in the demo it has never run.

**Sequencing decision (user, 2026-10-07): the scheduling surface goes LAST.** It
is heavy enough to deserve a pass of its own rather than being lit opportunistically
mid-audit. That carries a consequence worth stating: **the Scheduler role depends
on the same surface**, so it is deferred with it. Remaining order is therefore
Receiving → Shipping → Production Manager → Scheduler, with the solve and the four
blocked rows (Shift Lead 2, 3, C3's re-plan half) picked up in that final pass.

**Not lit during this pass, deliberately.** Solving is a Celery task; per the
repo's own notes it will sit `PENDING` unless a worker is running, and starting
one while two sessions are running tests risks exactly the interference CLAUDE.md
warns about. Lighting this needs a decision about the demo, not an opportunistic
click.

**Row 2 may also be misframed.** The *Dispatch List* on the Control Center turns
out to be a **report** (Download PDF / Email me), not an assignment surface. And
in the flows actually verified, operators **claim** work through Start Work rather
than being pushed it, with the lead stepping in only to reassign — the supervisor
gate I watched fire. If pull-with-supervisor-override is the real model, the row
should read *"reassign work when someone cannot run it"* rather than *"put people
on jobs"*. Worth settling before the docs describe a push model the product does
not use.

### CODE GAP — "void an operator's bad record" is narrower than the row assumes

Shift Lead **C2**. Casey's 297 effective permissions include exactly one void:
**`void_substepcompletion`**. There is no general void for a step execution, a
measurement or a quality report.

So the escape hatch for Operator C2 (*"get an erroneous record corrected"*) exists
only for substep captures. A mistyped measurement on a completed step, or a quality
report filed against the wrong part, has no lead-level correction path in the
permission set.

Consistent with [[is-voided-means-recapture]] — void means "captured wrong, do it
again" — but the capability is scoped to one record type. Whether that is
deliberate or simply as far as it got is a question for the user, not a defect I
can assert.

### Receiving / Shipping — data state before the walk (2026-10-07)

Checked the fixtures first, because several rows turn out to have nothing to walk.

| Collection | Rows | Consequence |
|---|---|---|
| `MaterialLots` | 10 | receiving lifecycle is well covered |
| `StorageLocations` | 6 | putaway has somewhere to go |
| `OutsideProcessShipments` | 3 | OSP lane works (verified from QA side) |
| **`CycleCounts`** | **0** | Receiving row 8 is dark |
| **`CustomerShipments`** | **0** | **the entire Shipping role has no data** |

**Eleventh and twelfth dark exhibits.** The receiving session reports that
shipping — partial shipments, lot shipments, void, the shipment CoC — is *"built
and tested"*, and cycle counts *"work but weren't re-checked after locations became
records"*. Both are believable; neither can be demonstrated.

**Shipping is now the role most at risk of a hollow pass.** Thirteen rows against
zero shipments means the next role would be audited entirely from code, which this
audit has repeatedly shown is the weaker method — every one of the nine
unmentioned capabilities was found by walking, not reading. Worth deciding whether
to seed a shipment or two before that pass rather than during it.

**Row 10 ("hand receipts to the ERP") needs no surface.** Glovia cannot integrate;
every exchange is a person carrying a sheet ([[glovia-human-bridge]]). Like ISO
8.5.3 customer-property reporting, the honest answer is that UQMES produces the
document and a human carries it. The row should say so rather than wait for a
feature.

### GAP (data) — the demo seeds only the post-arrival half of the receiving lifecycle

Thirteenth dark exhibit, and unlike the others it is **half a lifecycle rather
than one feature**.

There is no separate `ExpectedReceipt` model — and that is a good decision, not an
omission. **An expected receipt is simply a `MaterialLot` that has not arrived
yet**, carrying `erp_po_number`, `erp_po_line`, `promised_date`,
`original_promised_date`, `ordered_quantity`, `chase_note` and `chased_at`. Fields
over tables, exactly as `CLAUDE.md` prefers, and the lot becomes the receipt when
it lands rather than being copied into one.

But across all 10 lots:

| Check | Result |
|---|---|
| Not yet arrived (`received_date` null) | **0** |
| Ever chased (`chased_at`) | **0** |
| `ordered_quantity` set | **0** |

So three rows have nothing to act on: **1** (know what is expected), **4** (short
or over delivery — there is no ordered figure to compare a receipt against), and
**9** (chase a late delivery).

**What is being missed is good work.** `chase_expected_receipt`
(`services/mes/material_lot.py:566`) records what the buyer was told and any new
promise, and keeps the first one deliberately:

> *"The first promise stays as it was — on-time delivery is judged against it."*

That is `original_promised_date` protecting the OTD metric from being gamed by
re-promising, and the supplier scorecard honours it with
`Coalesce("original_promised_date", "promised_date")`. **A supplier cannot improve
their delivery record by asking for a later date.** That is a genuinely sharp piece
of supplier-quality thinking, it is invisible in the demo, and no document mentions
it — a tenth entry for the unmentioned-capability table.

Seeding two or three un-arrived lots — one due, one late, one chased — would light
all three rows and the OTD story at once. Cheaper than most of the other dark
exhibits because the fields already exist on a model the seed already builds.

### FIXED (seed) — expected receipts seeded; three dark rows lit at once

Written and run 2026-10-07 at the user's direction. `seed/demo/receiving.py` now
creates the **pre-dock half** of the lifecycle it was missing:

| Lot | State | Purpose |
|---|---|---|
| `RCV-EXP-0101` | ON_ORDER, promised +4d | an ordinary expected receipt (row 1) |
| `RCV-EXP-0102` | ON_ORDER, promised −3d | late and unchased (row 9's target) |
| `RCV-EXP-0103` | ON_ORDER, chased | the OTD-protection exhibit |
| `RCV-MAT-0004` | 40 of 60 ordered, BACKORDERED | short delivery (row 4) |

**The chase goes through the service, not through field assignment** —
`chase_expected_receipt(...)` rather than setting `chase_note` directly. That is
the lesson from the step-timestamp and material-usage findings applied
deliberately: the service writes the `RecordEdit` audit trail and preserves
`original_promised_date`, neither of which a direct write would produce.

**Verified in the browser.** The Materials page now reads **On order 3 · Late 2**,
and RCV-EXP-0103 renders:

> **On order** · 2026-10-09 · *Due soon*
> **first promised 2026-10-02**
> *Chased: "Spoke to their scheduler: held at the plating sub-tier, re-promised
> for Friday."*

**The UI shows the original promise beside the revised one** — better than
expected. The supplier-quality point is now visible on screen rather than only in
`Coalesce("original_promised_date", "promised_date")`: **a supplier cannot improve
their on-time record by asking for a later date, and the screen says so.**

RCV-EXP-0102 shows **Overdue**; RCV-EXP-0101 carries no badge, being not yet due.
Screenshot: `docs/assets/receiving/rcv-01-expected-receipts.jpeg`.

**Also surfaced by lighting it:** the Materials page carries **"Receipts for ERP"**,
which is the real answer to row 10. UQMES produces the document; a person carries
it to Glovia ([[glovia-human-bridge]]). The row should describe that, not wait for
an integration that cannot exist.

**Cost: one seeder function and a service call.** Three rows moved from dark to
verified, and the cheapest of the thirteen dark exhibits precisely because the
fields already existed on a model the seed already built.

### VERIFIED (end to end) — receiving a delivery, and the short-delivery question

Walked 2026-10-07 on the lot seeded an hour earlier. Rows **2**, **3** and **4**
together.

**The Receive dialog states its own consequence:** *"Book in the delivery. The lot
is then routed the same way any receipt is — to incoming inspection, or straight
to stock if this material doesn't need one."* It captures supplier lot number
(*"Kept for traceability. The lot gets its own number when it's booked in"*),
quantity, date, **heat number — required**, source from the paperwork, and
optional **photo or PDF** of the Certificate of Conformance and the packing slip,
plus a putaway location defaulting to the receiving dock.

**Entering 180 against 200 ordered raised a required decision** — and this is the
best piece of copy in the receiving flow:

> **"20 fewer than the 200 on order. What does the packing slip say?"**
> ○ *More coming* — keep the other 20 on order, same supplier, PO and promised date.
> ○ *That's all* — nothing more is expected on this line. **(UQMES stops planning
>   on the rest; closing the PO line is done in the ERP.)**

It asks what the paperwork says rather than what the system thinks, and it states
the product boundary **in the UI**: UQMES stops planning, the ERP closes the line.

**The result, verified on the API:**

- a new lot **`LOT-2026-00001`** — 180 received of 200 ordered,
  `short_receipt: BACKORDERED`, heat number captured, status
  **AWAITING_INSPECTION** (auto-routed, no manual step);
- a remainder **`ONORDER-PO-2026-EXP0101`** — qty **20**, *same PO line, same
  supplier, same promised date*, still `ON_ORDER`.

The backorder did exactly what the radio promised, and named itself after the PO.

Screenshot: `docs/assets/receiving/rcv-02-short-delivery.jpeg`.

**Row 6 read, not walked.** `LotReturnDialogs.tsx` carries the distinction that
matters: *"the lot leaves stock as **Returned — not scrapped: the goods exist, at
the vendor**. Credit is settled in the ERP."* An RTV sheet prints to travel with
the goods, and the carrier or the supplier's RMA is recorded. Two more statements
of the ERP boundary inside the product.

**Incidental check on my own sweep:** this file already imports `apiErrorMessage`,
confirming it as one of the three files I counted as safe. The count of 31 at-risk
files stands.

**Method note.** Three scripted attempts to fill this dialog left the submit button
disabled with no error shown — the DOM held the values but React's state did not.
Real typing via the harness, then a trusted click on the radio, enabled it
immediately. **Scripted `.value` assignment is not a substitute for typing in this
app**, and a disabled button after a scripted fill means nothing.

### FIXED (seed) — a core is now on a work order; the reman lane has an entry point

Written and run 2026-10-07 at the user's direction. `seed/demo/reman.py` now calls
`start_teardown_batch` on the RECEIVED cores, producing
**`TEARDOWN-20261007-160333-900282-INJ`** — In Progress, quantity 2, process
*Injector Reman*, with its Digital Traveler showing **Core Receiving · In Progress
· 0/2 parts**.

**Why this was the blocker.** The core detail page states the rule itself — *"Not
on a work order. Cores join one when teardown starts."* No teardown had ever been
started, so no core had a part on a route, and with no unit on a route there was:

- nothing to open in the DWI runtime (Operator R1, R2, R3),
- no finding to apply or dismiss (Shift Lead R1),
- no scope to resolve and therefore nothing to send for over-and-above
  authorisation (Shift Lead R2, and the `AWAITING_AUTHORISATION` exhibit),
- nothing to decide an exit for (Shift Lead R3),
- and no teardown context for the core-receiving rows (Receiving R1, R2).

**Seven rows across three roles rested on one absent fact.**

**Driven through the service, deliberately.** `start_teardown_batch` creates the WO,
moves each unit onto the route's entry step and runs the real per-core transition.
Its own comment explains why that matters: *"A core's position is its part's: put
the UNIT on the work order, at the route's first step — or there is nowhere to open
it in the DWI runtime."* A seeder that set `status = 'IN_DISASSEMBLY'` directly
would reproduce the shape and none of the behaviour — which is exactly what left
the rest of the demo hollow.

Two details worth recording while fresh:

- **The batch rules are checked against the part, not the core.** `Core` has no
  `work_order` of its own; `_validate_batch` reads `core.part.work_order_id`. My
  first attempt filtered on `core.work_order_id` and would have thrown. Mirroring
  the service's own check is the safer habit.
- **The route enters at *Core Receiving*, not *Disassembly*.** That is
  `_entry_step` resolving the process's authored entry point, and it is correct per
  the code — but a teardown batch replaying "Core Receiving" for cores already
  received reads oddly. Flagged as an observation for the user, not a defect: it may
  be exactly right for a unit arriving at the teardown cell.

Seed log line kept ASCII — a non-ASCII dash renders as mojibake on the Windows
console, which the first run demonstrated.

### VERIFIED — receiving a core is a DWI step, and it collects the right evidence

Receiving **R1**, walked 2026-10-07 as `mike.ops` on the teardown work order seeded
minutes earlier. Core receiving is **not** a form on the core page — it is an
authored step in the operator runtime, which is why it was unreachable until a core
sat on a route.

> **Receive and log incoming core** — "Receive the incoming core, scan its identity
> band, and log its arrival condition."
> **Note:** *"Cores arrive as-is from the field - record what you see, don't clean
> yet."*

Captures: **scan the identity band** (barcode/QR, required), **photograph the core
as received** (image capture or upload), **arrival condition** Pass/Fail/Pending,
and a signed inspection sign-off. Completed with the core's serial; the review
screen listed all four and the step committed.

**Two details that matter for the row's premise.** The row was written around
*customer property, often no PO, return obligation, grading at the dock* — and the
step answers the hard part of that directly:

- *"don't clean yet"* is the right instruction, because cleaning destroys the
  evidence of the condition the unit arrived in. A row about customer property
  needs exactly that.
- the **photograph** is that evidence. ISO 9001 8.5.3 requires a customer's
  property to be identified, verified, protected and any loss or damage reported;
  a timestamped as-received image attached to the unit is how the "verified" and
  "report" halves get supported. Worth noting the audit earlier concluded the
  *reporting* conversation sits outside the system — this is the part that does
  not.

**Where it stopped, and why that is correct.** On completion the core did not
advance: *"Step submitted — awaiting QA sign-off"*. Core Receiving requires a QA
buy-off, so the unit is held at that step rather than running on to Disassembly.
The batch-complete fix behaved correctly again, returning to the work order with no
live Complete step button.

!!! note "Superseded — all five of these were walked afterwards"
    Corrected 2026-10-15. This paragraph is the state during one walk, not a
    standing blocker. Shift Lead R1, R2 and R3 were each walked end to end on
    2026-10-07/08 and carry their own evidence; Operator R2 and R3 are green.
    Read what follows as how the lane was opened, not as work outstanding.

~~**Still blocked behind that gate:**~~ Operator R2/R3 and Shift Lead R1/R2/R3 need the
unit at Disassembly and Component Grading before findings exist, a scope can be
resolved, or over-and-above authorisation has anything to ask about. Reaching them
needs a QA sign-off first — one account switch, not a seeding problem. The lane is
open; the unit simply has not travelled far enough along it yet.

### BUG (major) — a QA sign-off gate with no way to satisfy it

Found while pushing the newly-seeded core along the teardown route. **My first
diagnosis was wrong in two specifics; the corrected one is worse.**

**What I reported:** the part wasn't flagged `needs_qa`, so no QA surface showed
it.

**What is actually true** (diagnosed by the receiving session, and verified here):

`Steps.can_advance_from_step` blocks on `requires_qa_signoff` until a **QaApproval**
exists for that (step, work order). Production code creates a `QaApproval` in
**exactly one place** — FPI pass/waive, `services/qms/fpi.py:67`. Confirmed by
grep: the only other writers are two **seeders** (`qa_walk.py:497`,
`quality.py:988`), which insert the rows directly.

> **So any step with `requires_qa_signoff = true` but no first-piece inspection is
> a dead end.** There is no endpoint, no service and no inbox row that can create
> the approval. The operator is told QA must sign off; no inspector has anything to
> sign.

The only escape is a `StepOverride` of block type `QA_SIGNOFF` — which also has no
UI.

**And the seeders are why nobody noticed.** Every other QA-gated step in the demo
looks healthy because a seeder wrote its `QaApproval` directly. **This is the
audit's central pattern in its purest form:** the seed stages the outcome, the
mechanism that would produce it is never exercised, and the gap only appears the
moment a unit travels a route for real. It is the same root as the empty material
usage, the identical step timestamps, and the unreachable
`verify_root_cause`.

**Two corrections to my own report:**

- **`needs_qa` was a red herring.** It means *"selected for sampling and no PASS
  report yet"* — sampling, not step sign-off. My positive control correctly proved
  the flag works; it was simply the wrong flag. A control proves a mechanism
  exists, not that it is the mechanism in play.
- **"No active StepExecution" is not a stale check.** Advancement evaluates the
  whole **cohort** — every part of the work order at that step — and the toast
  concatenates every part's blockers. The second core had never been started, so
  that clause is **true of the other unit**. Misleading as written, not false.
  Separate UX fix: show only the current unit's blockers, or label each with its
  unit.

**Decision for the user** (the receiving session has proposed, not built):

1. A **step sign-off service and action** — QA inspector or manager tier, refusing
   self-sign-off by whoever completed the step (the separation this audit has seen
   enforced correctly in dispositions, CAPA verification and approvals).
2. A **"QA sign-off" row** in the inspection inbox and the WO exceptions panel for
   any part sitting at a `requires_qa_signoff` step with captures submitted and no
   `QaApproval`.
3. **Fix the toast** to report the unit in front of the operator.

**Blocks:** Operator R2/R3 and Shift Lead R1/R2/R3 — findings, scope resolution and
over-and-above authorisation all need the unit at Disassembly and Component
Grading, and it cannot get there.

### Production Manager — first pass (2026-10-07)

Walked as `jennifer.mgr` (466 effective permissions, group **Production Manager**).

**The hero answers row 1 on one screen:** jobs going late (1), work orders (11),
parts in quarantine (13), CAPAs pending verification (3), **first pass yield
53.8%**, open NCRs (12), active CAPAs (7), outside processing in and out,
**supplier qualifications expiring** (Apex Plating *expired*, Precision Castings
due 2026-10-25), and **competency coverage** — uncovered skills 0, single-operator
skills 0, expiring soon 1.

That last block is the training matrix's staffing-risk lens surfaced for a manager,
and it is the half of row 5 that works. Screenshot:
`docs/assets/production-manager/pm-01-home.jpeg`.

**Approval here is the generic mechanism, not per-model permissions.** Jennifer has
**`respond_to_approval`**, `manage_approval_workflow`, `override_training_gate`,
`resolve_step_decision` and `sign_off_fpi`. Her approvals centre shows **1 awaiting**
(a Document Release from Lisa Park) and **3 she submitted** — the CAPA approvals
that Maria decides. The request/approve split is visible across two roles at once.

*(I nearly filed "the Production Manager holds no `approve_*` permissions" — true
literally, false in substance. There is no `approve_overandabove` because approval
is template-driven. A literal permission-name filter is not a capability check.)*

### CORRECTION — row 6 is half misframed: deviations are QA's decision, not production's

A **Deviation Request is not a model**. `reports/adapters/deviation_request.py`
describes it as *"the formal document produced when engineering determines that a
nonconforming product may be accepted without rework"*, and implements it as **a
filtered view of `QuarantineDisposition`** where the type is `USE_AS_IS` or
`REPAIR`. Another fields-over-tables decision: the deviation *is* the disposition,
rendered as a document.

So "approving a deviation" means choosing that disposition type — which requires
**`approve_disposition`**, and the Production Manager **does not have it**. She
holds `close_disposition` but not the decision.

| | Production Manager |
|---|---|
| `approve_disposition` | **no** |
| `close_disposition` | yes |

**That is correct, not a gap.** Material review authority — deciding that a
nonconforming part may be used as is — is a quality function under AS9100, and the
audit already verified it as the co-signable decision (`decision_authorized_by`).
Production can close the paperwork; it cannot make the call.

**The row should be split:** *record the customer's answer on over-and-above*
(which PM R1 already states correctly) and *close out a deviation once QA has
decided it*. As written it claims an authority the role does not have, and should
not.

### OPEN QUESTION (product) — a temporary departure from the process has no home

Raised by the user 2026-10-07 while reviewing row 6, and it is a real gap rather
than a documentation one. Three distinct things exist in a quality system; UQMES
implements two.

| Need | Home in UQMES |
|---|---|
| Accept **this nonconforming part** as it is | `QuarantineDisposition` USE_AS_IS / REPAIR, rendered as the *Deviation Request* document |
| Change the process **permanently** | PCR → PCO → PCN (`ProcessChangeOrder.effective_date`) |
| Depart from the process **temporarily**, or for a bounded quantity | **nothing** |
| Bypass a **gate** once, with an expiry | `StepOverride` (`expires_at`, `used`) |

**The industry distinction the gap sits on.** In AS9100 / aerospace practice these
are two different documents:

- a **deviation** (or deviation permit) authorises departing from the spec
  **before** the work is done, and is bounded — *"this lot only"*, *"until the
  30th"*, *"next 50 units"*;
- a **waiver / concession** authorises accepting what was already made.

**UQMES implements the waiver and calls it a Deviation Request.** That is a
terminology collision with the industry term, and the thing the name describes —
prior authorisation to do it differently — has no implementation.

**`StepOverride` is the nearest machinery and the wrong shape.** It carries
`expires_at` and `used`, which is exactly the bounded quality a deviation needs,
but its `block_type` values (QA_SIGNOFF, TRAINING_EXPIRED, CALIBRATION_EXPIRED,
QUARANTINE, ROLLBACK…) are all **gates**. It authorises skipping a check; it does
not authorise a different method, and nothing on it records what the departure
actually was.

**Change control cannot stand in**, because `effective_date` is a start with no
end. A PCO is permanent by construction, so running a temporary change through it
means raising a second PCO to put the process back — and leaves the window itself
undocumented.

**Why it matters for traceability rather than paperwork:** a part made under a
temporary deviation was made to a different spec than the released process says.
If the deviation is not recorded against the units it covered, the record claims
they were built to a process they were not. That is the same failure mode as the
gauge-recall question, pointing the other way — *which units were made under the
departure?*

**What the standards actually say (researched 2026-10-07, ISO 9000:2015 terms).**

- **Deviation permit** — *"permission to depart from the originally specified
  requirements of a product **prior to its realization**"*, and it is
  *"generally given for a **limited quantity of product or period of time, and for
  a specific use**."*
- **Concession** — *"permission to use or release a product that does not conform
  to specified requirements"*, *"generally limited to… an **agreed time or
  quantity**."*

Three things follow that sharpen the question:

1. **Both are bounded, and quantity matters as much as time.** My first framing
   called this "temporary"; the standard says *limited quantity **or** period*,
   plus **a specific use**. A deviation scoped to "the next 50 units for customer
   X" is as normal as one scoped to a date.
2. **The binding is to units, lots and work orders — not to the process.** Industry
   practice records the deviation/concession number and **its effectivity** against
   the work orders, serials and lots it covers, so the affected units are findable
   afterwards by serial, batch or work order. That is an *effectivity* concept, and
   it is precisely what the gauge-recall work established UQMES can already do.
3. **Terminology is contract-dependent.** Sources are explicit that firms use
   *concession*, *waiver* and *permit* differently and that the governing contract
   and QMS decide. So renaming the existing report is a smaller win than it looked
   — what matters is that the two *concepts* are distinguishable, not which word
   the screen uses.

**Where that leaves scope.** UQMES already implements the **concession** half
properly (the disposition, with its co-signed decision authority). The missing half
is the pre-realization permit — and the natural shape for it is the pattern this
product already uses for over-and-above: **produce the request, export it, record
the customer's answer, bind the result to the affected units.** A deviation permit
almost always needs the customer's authorisation, which sits outside UQMES by
design; what belongs inside is the scope, the bound, and the recorded answer.

**The effectivity binding is the part that would earn its place.** Without it, a
part made under a permit has a record claiming it was built to a process it was
not. With it, the question *"which units were covered by DEV-123?"* is answerable
the same way *"which parts did this gauge measure?"* now is.

**Questions for the user, not assertions:**

1. Is a pre-production, bounded deviation in scope at all, or is Ambac's practice
   to raise a PCO for anything that changes the method?
2. If it is in scope, is it a new bounded object, or `StepOverride` widened from
   "skip a gate" to "work to this instead, until X / for N units"?
3. Either way, should the existing *Deviation Request* report be renamed to
   **concession** or **waiver**, so the pre-production document can take the name
   that matches the industry's?

Not filed as a defect: a shop that handles every method change through change
control is behaving correctly, just more slowly.

## The dominant documentation gap is unmentioned capability, not wrong statements

**Recorded 2026-10-07, and it should shape goal 3.** Going in, the working
assumption was that the docs would contain incorrect claims to be corrected. Some
exist — the QA Inspector guide named **Approve FPI** / **Reject FPI** buttons that
do not exist, and the trainer script had five fixture drifts. But they are the
minority.

**The repeating shape is: the product does something good, deliberately, with a
comment explaining why — and no document mentions it at all.** Instances found so
far, each verified in the browser:

| Capability | Documented? |
|---|---|
| The **persona picker** and supervisory preview (a lead sees the operator surface) | no |
| The **batch / load runtime** — loads, sealing, batch-wide captures, sealed history | no |
| **"Can't run this?"** — four blocker reasons, each routed to a named owner | the docs describe a generic "report a problem" |
| The **reassignment gate** — supervisor authorises on the operator's screen | no |
| The **training override record** — worker, authoriser, reason, what was missing | no |
| The **FPI buy-off** wording — *"recorded against the QA inspector's name, not the person logged in"* | no |
| The **Exceptions tab** — unified triage with per-WO production impact | no |
| The **rework escalation counter** and the stated routing decision | no |
| The **scan box** accepting lots, serials and locations | docs say work orders only (filed as DRIFT) |

**Why, per the user (2026-10-07): the docs were written at one point in time, and
the product kept moving.** The landing-page work — the block-stack Home, the
persona picker, the operator and QA home surfaces — landed after they were
written. So this is a **dating problem, not neglect**, and it changes the fix:
the question to ask of each doc is not "is this wrong?" but **"what shipped after
this was written?"**

That also means the gap will keep reopening unless something ties the two
together. Worth deciding, as part of goal 3, what that is — a dated
"last verified against build X" banner on each page is the cheapest version, and
the trainer script already carries one.

Three consequences for how goal 3 should be approached:

1. **Writing from the code finds nothing.** Every item above is correctly
   implemented and often well commented. A doc written by reading source would
   describe the same things the docs already describe. These were found by
   *walking the role*, which is the only method that surfaces a feature nobody
   thought to write down.
2. **The docs understate the product.** That is commercially backwards — the
   unmentioned items are disproportionately the persuasive ones. The FPI
   attestation wording and the training override record are the two strongest
   compliance stories in the system, and neither appears in `compliance/`.
3. **Help docs and training docs need different fixes.** The help docs are
   mostly *incomplete* (missing capability). The trainer packet is mostly
   *drifted* (names fixtures and states that moved). Those are not the same job
   and should not be scheduled as one.

**Working rule for the remaining roles:** when a surface does something the row
did not predict, that is a documentation finding even though nothing is broken.
Record it as such, not merely as a verification.

### VERIFIED — make-up planning is complete, and reachable only from the wrong page

Production Manager row **9**. The service, both endpoints and the UI all exist, and
the demo carries a clean exhibit — but a PM cannot get to it without going through
the scheduling surface.

**The data is a good teaching pair**, found by calling `makeup_status` across the
work orders:

| Work order | target good | alive | scrapped | shortfall |
|---|---|---|---|---|
| **WO-2024-0038-A** | 12 | 11 | 1 | **1** |
| WO-2024-0042-A | 24 | 29 | 1 | **0** |

The first is the case the row describes — scrap outran the gross-up, so the job now
owes one. The second scrapped a part too and absorbed it, because the gross-up had
covered it. Side by side they teach the distinction better than prose.

**The design is deliberate and well stated.** `services/mes/makeup.py`:
*"Planner-confirmed by design (AS9100/ITAR): `work_order_shortfall` reports the gap
for the UI; `create_makeup_parts` is the explicit action that spawns the
replacements."* Topping up is never automatic — and the rule is iterative, *"top up
to keep alive == target"*, so a replacement that later scraps is covered by the
next top-up rather than needing a gross-up on the gross-up.

**The placement question.** `makeup_status` and `create_makeup` are both on the
work-order viewset, but the only UI that reads them is
`components/scheduling/EditWorkOrderDialog.tsx`, and that dialog is used by exactly
one page: `SchedulingGanttPage`. The work-order detail page offers Traveler, Start
Work, Hold and Cancel — no make-up.

So a production manager who has just scrapped a part and wants to top the job back
up must open the **Production Schedule**, find the work order, and edit it. Worth
asking whether that is intended: the shortfall is a property of the work order, the
action is on the work-order viewset, and the person who needs it is looking at the
work order. **Deferred with the scheduling surface, but the question is about
placement rather than the schedule.**

**One to check before building on it:** `WO-2024-0048-A` is Pending with no parts
created, and reports `shortfall: 8` — its entire ordered quantity. Arithmetically
right (target minus alive) and potentially misleading, since an unstarted job is
not short. Whether the UI guards against offering make-up there was not tested.

### VERIFIED FIXED — QA step sign-off, walked across three accounts

The gate that could never be satisfied now can be. Walked 2026-10-07.

**The inbox surfaces it.** A new chip, **"QA sign-off 1 · 34m"**, beside Receiving /
OSP returns / In-process, with the row reading:

> **QA sign-off · Core Receiving** — 1 unit waiting ·
> TEARDOWN-20261007-160333-900282-INJ — *"work is parked until signed off"*

That phrase is the finding restated to the person who can act on it.

**The confirm dialog says what signing means:** *"Signing records you as having
accepted the step's work, and the units move on to their next step."*

**Signing worked.** Afterwards `GET /api/InspectionInbox/qa-signoffs/` returns
`[]`, the inbox row is gone, and the work order's exceptions panel is clear.

**But the unit did not move — and that is correct.** The peer's walk predicted the
core would advance on sign-off; it did not, because advancement evaluates the
**cohort**. `CORE-240225-0002` had no execution at all. Completing its captures
then produced:

> **"Step complete — lot advanced (2 parts moved)."**

Both cores are now at **Disassemble injector into components**. So the full chain
is: operator submits → parked, visible to QA → QA signs → second unit submits →
lot advances together.

**Worth stating plainly, because it surprised the person who built it:** a
sign-off does not move the unit if a lot-mate has not submitted. Nothing is wrong,
but *"sign it and the core moves"* is only true for a single-unit lot, and any
documentation should say the lot moves, not the part.

**Unblocked:** Operator R2/R3 and Shift Lead R1/R2/R3 — findings, scope resolution
and over-and-above authorisation all have a unit at Disassembly to act on for the
first time in this audit.

**Not re-tested:** the segregation-of-duties refusal. An operator is blocked
earlier by lacking `sign_off_fpi` (403), and seeing the SoD message needs a lead
who also completed the captures. The peer has it under test; I have not walked it.

### GAP (authoring) — the three reman capture nodes exist but no process uses them

Walked the teardown lane end to end on 2026-10-07: Core Receiving → QA sign-off →
Disassembly → Component Grading, both cores moving as a lot. **The route works.
What is missing is what the steps were authored to capture.**

Three DWI nodes are implemented, registered and ready:

| Component | Registered type |
|---|---|
| `HarvestedComponentCapture.tsx` | `harvestedComponentCapture` |
| `ComponentInstallCapture.tsx` | `componentInstallCapture` |
| `RebuildFindingCapture.tsx` | `rebuildFindingCapture` |

**None of them appears in any authored substep.** Across all 12 substeps in the
tenant the node types actually used are: `measurementInput`,
`attestationCheckpoint`, `scanInput`, `qualityStatusField`, `errorTypesField`,
`inspectionSignatures`, `photoCapture`, `callout`, plus prose nodes. No
`harvestedComponentCapture`, no `rebuildFindingCapture`, no
`componentInstallCapture`.

**What the steps do instead.** *Disassembly* is *"Tear down injector — disassemble
into component groups. Bag and tag each subassembly"* with a scan and a photo.
*Component Grading* is *"Grade each harvested component — sort into reuse / rework
/ scrap"* with a single **Pass / Fail / Pending** verdict and a sign-off. So the
operator is told to grade *each component* and given one verdict for the whole
unit, and no component rows are created.

That also explains the 3 `HarvestedComponent` rows in the demo: they were written
directly by the seeder. **Walking the route produces none.**

**What it blocks, and why it is not a seeding problem:**

- **Operator R2** (raise a finding at the bench) — `rebuildFindingCapture` is the
  mechanism; nothing authors it, so there is no way to raise one from the runtime.
- **Operator R3** (work a rebuild step whose scope was settled this morning) —
  scope resolves from raised repair codes; with no findings, nothing accumulates.
- **Shift Lead R1** (decide a pending finding) — nothing to decide.
- **Shift Lead R2** (request customer authorisation for over-and-above) —
  `request_authorisation` refuses outright when findings added nothing beyond the
  sold level, which is always true here.

**This is a third category, distinct from the other gaps in this audit.** Not a
bug, not missing code, not absent demo data — **missing authoring**. The capability
is built and the vocabulary is registered; no one has placed the nodes in the
Injector Reman process. A substep editor exists for exactly this.

Worth deciding whether the demo process should author them (which would light four
rows and make the reman story demonstrable) or whether these nodes are ahead of the
process design and should wait.

**Confirmed working on the way through**, and worth recording as verified:

- the **QA sign-off fix**, across three accounts;
- the **toast fix** — *"Step submitted — lot waiting on cohort · Waiting on 1 other
  unit in the lot"*, with no phantom "No active StepExecution";
- **lot advancement** — *"Step complete — lot advanced (2 parts moved)"*, twice;
- **Operator R1** re-confirmed on a real core, with the same copy-vs-control drift
  already filed (instruction says three-way sort, control offers Pass/Fail/Pending).

### Method note: three false negatives in one day, all from the query, not the system

**Recorded 2026-10-08. Worth more than any single row, because it is how this audit
nearly shipped wrong answers.**

Three times in one session a search returned "nothing" and the nothing was mine:

1. **`grep -v REBUILT_TO_STOCK`** while asking what writes `REBUILT`. The one line that
   writes it — `rebuild_execution.py:79` — is
   `core.status = 'REBUILT' if core.returns_to_customer else 'REBUILT_TO_STOCK'`, so my
   own exclusion ate the answer. I was a message away from telling a peer that nothing
   sets REBUILT and the repair-and-return ending was unreachable.
2. **`getattr(ss, 'content', None) or ''`** when checking which substeps carry the reman
   capture nodes. `Substep` has no `content` field — the authored body is
   **`body_blocks`** — so every row searched as an empty string and the query reported
   the nodes authored nowhere. They were authored.
3. **`| head`** on the groups spreading `STAFF_OPERATIONAL_WRITE`, reported as eight when
   there are nine.

The shape is identical each time: **a query that cannot find the thing returns the same
answer as a system that does not contain it.** Absence of evidence arrived looking
exactly like evidence of absence, and in two of the three cases it would have become a
filed finding against working code.

The habit that caught all three was the same one: before sending a negative finding,
prove the query can find a positive. Where the claim is "nothing does X", the check is
to make the search find something it is known to contain — a field that definitely
exists, a row that definitely matches — and only then trust the empty result.

**This does not retract the original finding that the three capture nodes were authored
nowhere.** That one holds on independent evidence: all `HarvestedComponent` rows had
`proposed_grade: ''`, the `PendingFindingsCard` never rendered, and the authoring had to
be *added* in the seed before the card worked. But it was established with an unsound
query, and it happened to be right — which is a different thing from being verified.

## Post-audit rework — item 2: the demo has no new-manufacture process

**Found 2026-10-07, prompted by the user's question, and it reframes several
earlier findings.**

| Process | Part type | `is_remanufactured` | Steps |
|---|---|---|---|
| Injector Reman | Common Rail Injector | **true** | 12 |
| Injector Reman — Authoring Draft (SHOWCASE) | Common Rail Injector | **true** | 12 |

**Two processes exist. Both are reman. All 17 work orders use one of them.**

So every work order in the demo — *Midwest Fleet Order – 24 Injectors*, the
ASSESS-* set, the TRAIN-* set, the QA walkthrough — runs a route that begins
**Core Receiving → Disassembly → Component Grading**. Parts that were never cores
are travelling a core's route.

**This contradicts the audit's own founding instruction.** The user set the scope
early: *"Fold reman in as workflows on existing roles — not as a main or default
mind you. **New manufacturing is more important because it is fundamentally the
default.**"* The entire audit has been walked against a demo in which **the default
flow does not exist**, and the secondary flow is the only one there is.

**What it explains, retrospectively:**

- Why `INJ-0042-020` — an injector on a customer fleet order — sat on an *Assembly*
  step inside a route that opens with core teardown.
- Why the Digital Traveler on every work order shows Core Receiving and
  Disassembly, including for orders that are plainly new build.
- Why reman rows kept appearing reachable from "new manufacture" work orders, and
  why the distinction between the two lanes never surfaced in any walk — **there is
  only one lane.**

**It also narrows item 1 of the rework.** The missing reman capture nodes
(`harvestedComponentCapture`, `rebuildFindingCapture`, `componentInstallCapture`)
are not simply unauthored — they are unauthored **in the only process there is**,
which is also doing duty as the new-manufacture route. Authoring them into it would
make every new-build order collect harvested components.

**So the need is two processes, not one fixed one:**

1. **A genuine new-manufacture route** — raw material through machining,
   inspection, assembly, test, pack. No core receiving, no disassembly, no
   component grading. This is the *default*, and nothing in the demo currently
   demonstrates it.
2. **A properly authored reman route** — the existing one, plus the three capture
   nodes at the steps that need them, so teardown produces harvested components and
   findings rather than a single pass/fail.

Only then do *"new manufacture is the default; reman is secondary"* (the audit's
own stated rule) and the R-rows mean anything observable.

**Verified against the DB, 2026-10-07** (not inferred from the API shape):

- **17 of 17 work orders** run `Injector Reman` — `ASSESS-QA-001/002`,
  `TRAIN-FPI-001`, `WO-2024-0038-A/0042-A/0048-A`, `WO-ASSESS-001/003/004`,
  `WO-ASSESS-PM-001`, `WO-QA-INSPECT-01`, `WO-SHOWCASE-01`, `WO-TRAIN-001`,
  `WO-TRAIN-BOTTLE`, `WO-TRAIN-HOLD`, `WO-TRAIN-PM-001`, and the teardown batch this
  audit started. **No exceptions.**
- The second process, `Injector Reman — Authoring Draft (SHOWCASE)`, has **zero**
  work orders. It is an authoring exhibit, not a second route — so there is really
  only **one live process in the whole demo**.
- **4 part types exist; 3 have no process at all.** Injector Body, Injector Nozzle
  Assembly and Control Valve Assembly cannot be built — they exist only as BOM
  components. Every routing, every traveller, every step execution in the demo
  belongs to Common Rail Injector.

### RETRACTED — "a rejected lot can only be returned if it was accepted first"

**I filed this on 2026-10-07 and it is wrong. The product path is complete and
correct; the demo seeder is what's broken.**

What I observed was real: on the Rejected lens, `RCV-MAT-0005` offered **Ship back**
and `RCV-MAT-0006` offered nothing. What I concluded from it was not. I read the
`Phase 2 TODO` docstring on `receiving_inspection.reject` and treated it as current:

> ```python
> Phase 2 TODO: route through QUARANTINE and spawn a ``QuarantineDisposition``
> (RETURN_TO_SUPPLIER / USE_AS_IS / SCRAP) instead of going straight to REJECTED.
> ```

**That docstring is stale.** The routing it asks for now happens in its *caller*.
`lot_reject.reject_lot` opens a disposition on **every** branch — PARTIAL,
WHOLE_LOT_REQUESTED and WHOLE_LOT — and calls `ri.reject(report, user)` internally as
one step of that. The viewset action says so plainly:

> *"Reject at receiving inspection, opening the disposition with it. A partial reject
> splits the bad pieces off and accepts the rest; a whole-lot reject needs
> `reject_whole_lot`, and without it holds the lot as a request."*
> — `viewsets/mes_standard.py:1149`

And the UI uses it: `ReceivingInspectionPage` → `useRejectLot()` →
`MaterialLots.reject`, with a `RejectDispositionDialog` and three outcome toasts
including *"Lot rejected · disposition opened"*.

**The actual defect is in the seeder**, and it is the audit's own recurring thesis:

> `seed/demo/receiving.py:166` calls `receiving_inspection.reject(report, received_by)`
> — the low-level primitive — instead of `lot_reject.reject_lot(...)`.

So `RCV-MAT-0006` reached REJECTED by a path no user can take, with no disposition
beside it, and therefore no way back out. **The seed staged an outcome the product
would never produce, and I read the artifact as evidence about the product.** This is
the third time this pattern has produced a false finding in this audit.

**FIXED 2026-10-07 (both halves).**

1. `seed/demo/receiving.py` now rejects through `reject_lot(report, qa_manager,
   disposition_type='RETURN_TO_SUPPLIER', whole_lot=True, description=…)`. It runs as
   `users['qa_manager']` (maria.qa) because a whole-lot reject takes
   `reject_whole_lot`; as anyone else it would correctly become a *request* that holds
   the lot instead of rejecting it. On the next re-seed `RCV-MAT-0006` offers **Ship
   back** like any genuinely rejected lot.
2. The stale `Phase 2 TODO` is gone from `receiving_inspection.reject`, replaced by a
   docstring that says what the function actually is — *a primitive; prefer
   `lot_reject.reject_lot`* — and why calling it alone strands a lot.

**Takes effect on the next re-seed**; the dev DB still holds the old
`RCV-MAT-0006`.

**What survives from the walk:** everything that was a *walk* rather than an
inference. `reject_remainder` → disposition → `ship_back` → RTV sheet → automatic
replacement delivery all work end to end, and the `reject_whole_lot` permission is
distributed correctly across tenant roles. Receiving row 6 stays ✅.

### BUG — every bulk part action silently no-ops: string ids vs UUID keys

**Found 2026-10-07 walking Operator C1. Verified end to end, cause isolated,
blast radius enumerated. This is a real product bug, not a seed artifact.**

**Symptom.** Select a part on the WO Control page → **Quarantine**. The row shows
*Quarantined*. Nothing was written. The server returned **HTTP 200**:

```json
POST /api/Parts/bulk_set_status/   {"ids":["01a1171b-1bd7-…"],"status":"QUARANTINED"}
200 {"results":[{"id":"01a1171b-1bd7-…","ok":false,"error":"Part not found"}]}
```

The part exists — `GET /api/Parts/01a1171b-1bd7-…/` returns it. After a reload the row
reverts to *In Progress*.

**Cause.** `services/mes/parts.py:757`

```python
qs = Parts.unscoped.filter(tenant_id=tenant_id, id__in=part_ids)
return {p.id: p for p in qs}          # keys are UUID objects
```

then `parts.get(pid)` where `pid` came from `request.data["ids"]` — a **string**.
Django coerces the strings for the `id__in` *query*, so the rows are found; the dict is
then keyed by `UUID` and every `get(str)` misses. Proven directly:

```
rows returned: 1
key type: UUID
lookup with STRING  -> None        <-- "Part not found"
lookup with UUID    -> INJ-0042-022
```

**Blast radius — all three bulk actions**, each passing `request.data.get("ids")`
straight through with no coercion:

| Viewset action | Service | UI control |
|---|---|---|
| `bulk_set_status` (`mes_lite.py:1026`) | `parts.py:842` | **Set status… / Quarantine / Scrap / Send to QA** |
| `bulk_increment` (`mes_lite.py:740`) | `parts.py:767` | advance selection |
| `bulk_rollback` (`mes_lite.py:876`) | `parts.py:795` | **Previous step** / Rewind |

Confirmed live for `bulk_set_status`. The other two are the identical pattern against
the same helper — flagged, not separately walked.

**Why no test caught it.** Every test calls the *service* directly with an ORM value:

```python
[r] = bulk_set_status(self.tenant.id, [core.part_id], PartsStatus.SCRAPPED, self.user)
```

`core.part_id` is a `UUID`, so the service is exercised correctly and passes. **Nothing
tests the viewset**, which is the only place strings enter. The service is right; the
HTTP boundary is where it breaks, and that boundary is untested.

**Fix** (one place, not four): key the helper by `str(p.id)` and look up by `str(pid)`,
so it is indifferent to what callers pass. Add one API-level test that posts JSON ids.

**Secondary — the UI hides it.** `WorkOrderControlPage`'s advance handler parses
`data.results` and banners per-item failures; the **set-status path does not**, so a
wholly failed bulk status change renders as success until a refetch. Worth fixing with
the above.

**Also found on this walk (not a bug).** Bulk **Rework** correctly refuses:
*"Rework target step 'Rework' has no inspection substep — reworked parts must be
re-inspected before they can advance."* That is a sound ISO-aligned guard, working.
The demo's Rework step simply has no inspection substep — **another unauthored-substep
gap, same family as rework item 2.** The UI does banner this one
(*"One or more parts failed to split."*) but discards the server's specific sentence —
a missed site of commit `ddf4869`, and `apiErrorMessage` already exists for it.

### The reman lane dead-ends at IN_DISASSEMBLY — nothing in the UI completes a teardown

**Found 2026-10-07 walking Shipping R1 / Shift Lead R3 / PM R1. One missing affordance
blocks the entire downstream reman lane.**

`complete_disassembly` exists end to end on the backend:

- service — `services/reman/core.py:30` `complete_core_disassembly()` (IN_DISASSEMBLY → DISASSEMBLED)
- endpoint — `viewsets/reman.py:149`, documented in the viewset's own lifecycle note
  (*"4. complete_disassembly -> status: disassembled"*)
- permission — `complete_disassembly`, and it gates two *other* actions

**No frontend code calls it.** `useReleaseCore` and its sibling hook expose
`release_to_rebuild`, `release_to_inventory`, `request_authorisation`,
`record_authorisation` and `return_to_customer`. `complete_disassembly` appears in no
hook and no component — only in the generated client's text and three copies of a
docstring.

**So a core that enters teardown through the product can never leave it.**
`start_teardown_batch` puts it at IN_DISASSEMBLY; everything downstream needs
DISASSEMBLED:

| Action | Requires | Rows blocked |
|---|---|---|
| `release_to_rebuild` / `release_to_inventory` | `status == 'DISASSEMBLED'` (`release.py:64,97`) | Shift Lead R3 |
| `request_authorisation` | `DISASSEMBLED` or `IN_REBUILD` (`release.py:140`) | PM R1, Shift Lead R2 |
| `return_to_customer` | `REBUILT` or `DECLINED` (`release.py:197`) | Shipping R1 |

Verified on the teardown work order I started earlier this session: both cores sit at
*In Disassembly*, and the Cores card shows **Exit — "Rebuild or harvest to stock"** with
the action column empty. The card's copy is good — *"Teardown ends in one of two
places, and which one follows from the unit's arrangement"* — but neither ending is
reachable.

**The seed hides it, again.** 3 cores ARE `DISASSEMBLED` — set directly by the seeder,
not walked. They are also **not on a work order**, so `WorkOrderCoresCard` (the only
surface offering these actions) cannot act on them either. The staged outcome exists
where the mechanism cannot run, and is absent where it could.

**Second, independent block on the same lane: every core is EXCHANGE.**

| | |
|---|---|
| cores in demo | 8 |
| `fulfilment_mode == 'REPAIR_RETURN'` | **0** |
| `returns_to_customer` | **False for all 8** |

`return_to_customer` refuses an exchange unit by design — *"it is an exchange unit — it
has no owner to go back to"* — so **Shipping R1 is unwalkable regardless** of the
disassembly gap. The whole repair-and-return path (IN_REBUILD → REBUILT → RETURNED, and
the DECLINED → RETURNED_UNREPAIRED ending) has no representative unit.

**PARTIAL CORRECTION, same day, found while reviewing a peer's reman seed plan.**
My problem statement above was overstated, and the overstatement would mislead
anyone building on it.

**There IS an automatic path.** `core_steps.finish_route` (`core_steps.py:128`)
transitions a core when its unit reaches the end of its route — `IN_DISASSEMBLY →
DISASSEMBLED` via `complete_core_disassembly`, `IN_REBUILD → REBUILT` via
`complete_rebuild`. So "a core that entered teardown could never leave it" is wrong
as written, and so is that sentence in commit `05f18cc`.

**But the finding survives in substance, and is sharper for it.** The transition
fires at the *route terminal*, and for a teardown the route is the whole authored
one. `_scoped_step_ids` returns `None` for anything not under rebuild, and says why:

> *"Teardown has no resolved scope: every core goes through the same disassembly,
> which is why teardown can batch and rebuild cannot."*

A rebuild is scoped to the operations that rebuild actually needs, so reaching the
end of it means something. A teardown is not scoped, so the core walks all twelve
steps — Cleaning, Nozzle Inspection, Flow Testing, Assembly, Nitride Coating, Final
Test, Packaging — and is marked **DISASSEMBLED only after being fully reassembled
and packaged.**

So the accurate statement is not *"a teardown cannot be completed"* but **"a teardown
cannot be completed at the point teardown actually ends"** — which is the only point
at which the exit decision (rebuild vs harvest) is a real choice. The wiring below is
still the right fix; it just closes a narrower, more precise gap than I first claimed.

**Consequence for the repair-and-return lane, which I had also got wrong:**
`complete_rebuild` is reachable the same way, so a REPAIR_RETURN core finishing its
*scoped* rebuild route does become REBUILT, and `return_to_customer` then accepts it.
Shipping R1 is therefore blocked only by the absence of a REPAIR_RETURN core in the
demo — not, as I implied, by a missing writer for REBUILT.

**FIXED 2026-10-07 (the product half).**

- `useCoreLifecycleAction` gained a `complete_disassembly` action (`useReleaseCore.ts`).
- `WorkOrderCoresCard` renders **Complete teardown** for an `IN_DISASSEMBLY` core,
  beside the existing *Work* button, with the tooltip *"Everything worth keeping is off
  the unit. This is what opens its exit — rebuild, or harvest to stock."*
- **Backend consistency fix:** `complete_disassembly` was absent from the viewset's
  `action_permissions`, so the act the codename is *named for* rode the CRUD mapping
  while the two actions that merely FOLLOW it (`release_to_rebuild`,
  `release_to_inventory`) rode the codename. Now gated on its own permission and added
  to `crud_exempt_actions`. Safe: every operational role in the demo already holds
  `complete_disassembly`; only the customer holds neither it nor `change_core`.
- No schema delta (permissions aren't in OpenAPI; the endpoint was already published),
  so no frontend type regen.

**Walked end to end in the browser afterwards**, on the live teardown WO:

```
IN_DISASSEMBLY --Complete teardown--> DISASSEMBLED   (header recounts "2 · 1 awaiting release")
DISASSEMBLED  --Rebuild to stock---> IN_REBUILD      (Shift Lead R3's exit decision)
IN_REBUILD    --Authorise…---------> AWAITING_AUTHORISATION
AWAITING_AUTH --Approved-----------> IN_REBUILD      (PM R1 / Shift Lead R2)
```

**One ~20-line fix unblocked four rows.** Everything downstream was already built and
correct; nothing could reach it.

**Still outstanding — the demo half**, which belongs with rework item 2:
seed at least one `REPAIR_RETURN` core (all 8 are EXCHANGE, so the whole
repair-and-return ending is still unrepresented and **Shipping R1 stays blocked**), and
stop seeding cores into `DISASSEMBLED` off a work order.

## Post-audit rework — item 3: no seeded route can ever reach Shipping

**Found 2026-10-07 while trying to walk the Shipping rows. Same family as item 2 — a
routing-authoring gap, not missing records — but with a single, exact cause.**

Shipping looked blocked on "zero `CustomerShipments`". It isn't. The real cause:

> **Both seeders hardcode `terminal_status='COMPLETED'` on the last step of every
> route.**
> — `seed/demo/manufacturing.py:610` → `'COMPLETED' if is_terminal else ''`
> — `seed/manufacturing.py:369` → `'COMPLETED' if is_last else ''`

`Steps.terminal_status` has eight choices (`COMPLETED`, `SHIPPED`, `STOCK`,
`SCRAPPED`, `RETURNED`, `AWAITING_PICKUP`, `CORE_BANKED`, `RMA_CLOSED`). **Seven of
them are never written by anything.** The only terminal step in the demo is
`Complete`, with `terminal_status='COMPLETED'`.

**Why that empties the shipping board completely.** `shipping.py` is explicit that
the Ship step *is* the queue:

> *"The route's **Ship step is the queue.** A part reaching a terminal step whose
> `terminal_status` is SHIPPED waits there; shipping it completes that step through
> `advance_part_step`, so the step's gate (its sign-off substeps — the release check
> of ISO 9001 §8.6) runs exactly as it would for one part."*

`is_ship_step()` tests `terminal_status == 'SHIPPED'`. No step in the demo passes it,
so `_ready_parts()` has an empty `ship_steps` list and the first half of its query can
never match. The second half offers finished stock (`IN_STOCK`, `AWAITING_PICKUP`) —
also unreachable, because those statuses are only ever set by a terminal step with
`terminal_status` of `STOCK`/`AWAITING_PICKUP`, which likewise never exists.

**Measured on the dev DB:** `ready_to_ship()` returns **0 groups**; `CustomerShipment`
count is **0**; `shippable()` over all 152 parts gives

| reason | parts |
|---|---|
| not at a Ship step yet | 100 |
| already completed | 28 |
| on hold (Quarantined) | 13 |
| a core — return it from Remanufacturing | 8 |
| already scrapped | 2 |
| on hold (Rework In Progress) | 1 |

**…and 31 parts are parked ON the terminal step with status COMPLETED.** Those are
the units that finished the route. Under the intended authoring they would be
*waiting to ship*; under the actual authoring they went straight to `COMPLETED`,
which `shippable()` then rejects as "already completed". **A part that finishes the
route becomes permanently unshippable.**

**This is not a bug in the shipping code.** `services/mes/shipping.py` (410 lines) is
complete and coherent: shipment creation, partial shipment, void-and-return-to-stock,
per-order-line progress, delivery performance, export screening. It has simply never
had an input. The same is true of everything downstream of it — packing slips, OTD to
customer, order-line fulfilment.

**Fix belongs with item 2**, because "where does the route end" is part of designing
the two processes:
- the **new-manufacture** route should end at a terminal step with
  `terminal_status='SHIPPED'` (or `STOCK` for build-to-stock);
- the **reman** route likewise, so a rebuilt unit ships to its owner;
- and the seeders should take the terminal status from the route definition instead
  of hardcoding `COMPLETED`.

**Generalisable:** three of this audit's dark areas now share one root — *the demo
authors one route, and authors it incompletely*. Item 2 (no new-manufacture process),
the reman capture nodes (authored nowhere), and this (no shippable terminal) are the
same gap seen from three directions.

### The demo's lateness is a seeded capacity shortfall, not a scheduling defect

**Investigated 2026-10-08 after the solver walk, by experiment rather than inspection.**

The board reads **220% load, makespan 357 h, 2 late orders**, and weighted lateness in
the hundreds of thousands. That is not the scheduler misbehaving.

**Machine side — nine of ten steps have exactly one eligible machine.**

| Step | Machines | load |
|---|---|---|
| Final Test (FTB-1) | 1 | 265.8 h — **108% of the 246.9 h horizon capacity** |
| Assembly (Torque Wrench TW-26) | 1 | 187.1 h — 76% |
| Packaging (PK-1) | 1 | 93.2 h — 38% |
| Flow Testing | **2** | 117.7 h — 24% |

**Tested it:** added a calibrated second Final Test bench and re-solved as a what-if.
The solver used it — 37 of 99 tasks moved, FTB-1 fell **265.8 → 186.8 h (108% → 76%)**.
**Delivery did not improve**: still 2 late orders, WO-2024-0042-A still +7 d, and
WO-SHOWCASE-01 went +5 d → +6 d. Relieving Final Test simply hands the queue to the
Torque Wrench, which was already at 76% and is the other step every unit must pass. A
chain of single points moves its bottleneck; it does not lose it.

**Labour is the constraint underneath both.** Total scheduled work is **3,758 h**
against a labour supply of **2,222 h** — and that counts all 9 users as operators on the
single Day Shift. Excluding the QA manager, document controller and customer contact
puts it near **230%**, which is where the board's 220% comes from. It is also why
Dispatch reports 13–14 uncovered tasks and why the people phase of the solve (108 s)
costs more than the machine phase (72 s).

**So: a seeded shop with one shift, ~6 operators and no redundant machines cannot
deliver its seeded order book.** The scheduler is reporting that correctly, in detail,
and refusing to pretend otherwise. **Fixing it is a seed change** — a second shift, more
operators, or less demand — not a code change.

**An accidental validation:** the first attempt at the experiment failed because the new
bench was cloned without a calibration record, and `get_step_equipment_affinities`
silently dropped it — *"machines that can't be used right now — not in service, or with
lapsed calibration — are dropped so the solver never assigns work to them."* An
uncalibrated test bench being refused production work is exactly right, and it is why
the bench did not appear in the planner UI either.

**Two findings that are NOT explained by the seed**, and would persist in a real shop:

1. **The solve never gets close to optimal.** All runs finish FEASIBLE at a
   **66–99.6% optimality gap** against a 180 s limit. Objective figures are therefore
   not comparable between runs: two solves on *identical* inputs gave weighted lateness
   121,800 and 811,111. **The What-if panel presents exactly this as the effect of a
   change** (*"makespan 357.1 → 284.5 h, lateness 121,800 → 811,111"*), which is a real
   trap for a planner deciding whether to commit a draft. Worth either closing the gap
   or labelling the comparison with it.
2. **The frozen fence is overridden at scale.** `is_pinned` is False for all 569 tasks —
   nothing is planner-pinned — yet `relaxed_pin_count` is **59** against **184 frozen**
   tasks: a third of the frozen set moved. The solver is right to (the fence is a soft
   penalty by design, `solver.py:79`), but the board presents **Frozen** as a lock.

## Post-audit rework — item 1: deviation permits and conditional spec

**Flagged by the user 2026-10-07 as the first large piece of rework to follow this
audit.** Not a bug, not a documentation gap — a missing concept with a real UX
consequence.

**The gap.** UQMES implements the **concession** (accept what was made, via the
disposition and its co-signed decision) but not the **deviation permit**
(permission, *before* the work, to depart from spec — bounded by *limited quantity
of product or period of time, and for a specific use*, ISO 9000:2015).

**Why the runtime is the real work, and the rest is small.** The DWI runtime
displays the characteristic with its spec inline (*"Assembly Torque, A-01, 25 +2
−2 Nm"*) and badges a reading **In spec**; an out-of-spec reading auto-quarantines
the part and raises a disposition, with no one choosing it — *the spec is the
judge*. So if a permit authorises a different value and the runtime does not know:

> **the operator records a FAIL against the released spec, the part quarantines,
> and a disposition opens for work that was explicitly authorised.** The quality
> system generates nonconformances for conformance to an approved departure.

Teaching the runtime that *"in spec"* is **conditional on an active permit** is the
piece with no precedent anywhere in this audit. Everything else reuses shapes the
product already has:

| Need | Existing pattern to reuse |
|---|---|
| Raise it, export, record the customer's answer | `request_authorisation` / `record_authorisation` (over-and-above) |
| Refuse when expired or exhausted, naming the permit | the training gate's refusal + supervisor path |
| Show consumption (*unit 12 of 50*) | no direct precedent; closest is the rework attempt counter |
| "Built under DEV-123" on the record | lot trace / per-serial record (post-audit item 2) |
| Active permits as standing risk | supplier qualifications expiring on the PM hero |

**Two design points the research settled**, both of which a naive implementation
would get wrong:

- **Bound by quantity as well as time.** "The next 50 units for customer X" is as
  normal as a date. A permit modelled only with `expires_at` misses the commoner
  case. (`StepOverride` has exactly that shape — which is why it is the wrong
  object to widen.)
- **Effectivity binds to units, lots and work orders, not to the process.** The
  permit number and its effectivity are recorded against what it covered, so
  *"which units were built under DEV-123?"* is answerable afterwards — the same
  question shape the gauge-recall page already answers.

Terminology is contract-dependent (firms use *concession*, *waiver* and *permit*
differently), so renaming the existing report matters less than making the two
concepts distinguishable.

## Deferred: make the demo walk the flow instead of staging its outcome

**Parked 2026-10-06 by the user — a real piece of work, not a bug fix. Recorded so
it isn't rediscovered a third time.**

`seed/orders.py::_advance_part_through_workflow` reproduces the *shape* of
advancement by writing rows directly — `StepExecution.objects.filter(...).update(...)`
and `part.save(...)` — rather than calling `advance_part_step`. None of the service's
side effects therefore fire.

**Traced precisely, so the cause isn't guessed at again.** `_consume_step_material`
(`services/mes/parts.py:174`) guards on exactly one condition:

```python
if operator is None or step is None:
    return
```

No scheduling dependency, no release, no gate. Consumption fires whenever the
advance runs with a real operator. And the data it needs is already there — a
RELEASED ASSEMBLY BOM for the Common Rail Injector with 5 lines, at least one
step-mapped. **Nothing draws on it.** So no amount of reseeding or scheduling will
populate `MaterialUsage` while the seed bypasses the service.

**Symptoms this one root cause produces**, all separately filed above:

- `MaterialUsage` 0 rows → forward lot trace dead on every lot → recall question
  unanswerable.
- `entered_at` identical to the second across all 382 executions (the
  `auto_now_add` bug — the seed's direct `.update()` is both why it broke and why
  the `.update()` fix worked).
- No per-serial step history, which is half of QA Manager row 11's audit-readiness
  gap.
- Step durations that had to be corrected by hand rather than falling out of real
  entry/exit times.

**What it would cost.** Seeded parts would have to pass the competence gate, have
material available, and respect step order — which is the point, but it is a
rewrite of the part-progress seeder rather than an edit. **What it would buy** is
several dark exhibits at once: forward lot trace, true step timings, per-serial
history, the material gate, and consumption attribution.

Worth doing before any customer demo that claims traceability.

## Open questions

- Is the abstract list right? Workflows to add, drop or reprioritise.
- Should periodic roles get the same treatment in a later pass?
