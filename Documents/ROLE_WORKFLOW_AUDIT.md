# Role Workflow Audit

**Status:** live and maintained. **131 rows across 11 roles**, nearly all walked
against the running application and dated. (Counted 2026-10-15: Operator 18,
Shift Lead 16, QA Inspector 14, Receiving 13, Shipping 13, QA Manager 12,
Production Manager 11, Scheduler 10, Document Controller 9, Engineering 8,
Purchasing 7. The header previously said 138, which matched nothing.) This is the one file in `Documents/`
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

**Eleven roles, all walked** — the daily ones first, the periodic ones added once
their training tracks needed ground truth. Out of scope: **Administrator**,
**Auditor** and **Customer**, by user decision 2026-10-15 (see the header).

*The original scope was narrower — the eight daily roles only, with Planner,
Purchasing, Document Controller and Engineering deferred as "periodic". It
widened on 2026-10-12. The note below is how that happened; the sentence above
is where it stands.*

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
> **The skip retirement is done, and the docs followed it.**
> `workflows/reman/rebuild.md` now states the current behaviour — *"Nothing is
> skipped. Every unit walks the whole main line of its rebuild route. Scope
> decides which repair branches the route's checks send it down, not which
> operations it performs."* It also keeps why the earlier arrangement was
> replaced: an operation nothing happened to name was walked past, and a
> decision point walked past with no result left the unit deadlocked. Other
> uses of "skip" in `docs/` are unrelated senses — skip-lot sampling, optional
> substeps, FEFO lot skipping, labour-model conditions.
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
> Auditor. **Both acted on 2026-10-15** — the Role-page column is gone, since
> every one of the fifteen roles now has a guide.

### Interaction depth

From `ambac-tracker-ui/src/components/home/home-blocks.tsx`, which declares the
Home blocks each group receives — the application's own statement of what a role
does daily.

| Role | Home blocks |
|------|-------------|
| QA Manager | 13 |
| Production Manager | 12 |
| **Shift Lead** | **11** |
| Document Controller | 6 |
| Engineering | 5 |
| Purchasing | 4 |
| Operator | 3 |
| QA Inspector | 3 |
| Auditor, Customer | welcome only |

!!! note
    Block count is **not** depth. Operator gets three blocks because operators
    live inside the step player, not on Home. Their depth is in DWI.

!!! note "The "Role page" column is gone — it is all yes now"
    Dropped 2026-10-15. It existed to carry one finding: *Shift Lead is the
    third-heaviest role in the application and has no guide.* That was true when
    written and is not now — `docs/roles/` holds a page for **all fifteen**
    roles, including the three the column still marked "none" (Shift Lead,
    Engineering, Purchasing) and the Auditor it marked "Customer only". A column
    whose every cell reads yes measures nothing, and leaving it stale let one
    fixed gap keep reading as open in four places at once.

    Counts are also older than the launchpad cards added for Planner, Receiving,
    Shipping, Purchasing and Auditor. Re-measure from `home-blocks.tsx` before
    quoting a number here.

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

!!! important "Docs, Code, Demo and Training are four different questions"
    They are deliberately not collapsible, and each answers something the others
    cannot:

    | Column | Question |
    |--------|----------|
    | **Docs** | Is there a page that explains it? |
    | **Code** | Does the application do the job? |
    | **Demo** | Can it be **shown** on seeded data? |
    | **Training** | Is there a module where someone is taught to **do** it? |

    **Demo exists because a third state kept leaking.** A row can be green on
    Code and correctly so — the application does the job — while nobody can
    watch it happen, which makes it invisible in a demo and **unteachable**. That
    state used to live in a hand-maintained list here; it is now a column, which
    is the point. A list beside a table is a second source of truth, and this one
    drifted within three days of being written: it said "eight" above a table of
    ten, listed one row twice, and named four rows their own cells recorded as
    closed. It had been built with a regex, which matched each row's description
    of its **old** dark state and never saw the correction appended after it.

    > **A pattern match over a cell reads the first thing said about a row, not
    > the last.** Set Demo by reading the row.

    **Training is downstream of Demo** — you cannot teach what you cannot show —
    so a `❌` in Demo predicts one in Training. It is `?` on every row today,
    deliberately: the training arc has not been built, and judging the current
    files against 131 rows would record claims about artifacts that are about to
    be replaced.

    **Do not reach for ⚠️ here.** The caveat marker means the capability itself
    has a catch. A row that works but cannot be shown is `✅` on Code and `❌` or
    `🚧` on Demo.

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

    **Both columns were trustworthy on 2026-10-12.** Code was walked; Docs was
    read.

    !!! warning "And that is a claim with a shelf life — it had already expired"
        Added 2026-10-15. Five Docs rows went stale within three days of this
        sentence being written, because work landed and nobody came back to the
        row. **A sweep makes a column true on a date; only the
        flip-the-row-with-the-change habit keeps it true.** Read any
        "now trustworthy" line here as *as of the date beside it*, and if you
        need to rely on it, re-check the rows you depend on.

---

## Operator

The unit of work is a **step**, not a job.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what to work next, and claim it | ✅ | ✅ | ✅ | ? | 2026-10-06 | Up next / Then / In progress / See everything ready. The operator home is the claiming surface, not the Work Orders page. |
| 2 | Identify the right physical unit (scan) | ✅ | ✅ | ✅ | ? | 2026-10-06 | Verified in the batch/load runtime — *"Scan each part into the load"*, Captured ✓. The box takes lots, serials and locations as well as work orders; the docs are narrower than the app. |
| 3 | Prove qualification before starting, or be authorised | ✅ | ✅ | ✅ | ? | 2026-10-07 | Refused, overridden by a supervisor, override recorded with worker, authoriser, reason and what was missing. Demo lit by one field (Nozzle Inspection `min_level: 2`). |
| 4 | Follow the instruction and record as you go | ✅ | ✅ | ✅ | ? | 2026-10-06 | DWI runtime: spec check, in-spec badge, attestation, review screen. A value fixed before **Complete step** never becomes a nonconformance. |
| 5 | Record which material lot was actually taken | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Row misframed** — consumption is automatic FEFO on step exit, attributed to the operator, not a choice they make. Reads correctly as *"have the lots I used recorded against the unit"*. |
| 6 | Report a problem mid-step | ✅ | ✅ | ✅ | ? | 2026-10-06 | **"Can't run this?"** is the live path — four reasons, each routed to a named owner, stating the consequence up front. The home *Report a problem* tile is dimmed preview. |
| 7 | Work a batch another operator started | ✅ | ✅ | ✅ | ? | 2026-10-06 | Batch claim dialog plus the **reassignment gate**, which fires live and names the current owner. |
| 8 | Finish and move the unit on | ✅ | ✅ | ✅ | ? | 2026-10-07 | Lands on the work order with no live **Complete step** button. The **lot** advances, not the part — a finished unit can still wait on a lot-mate. |
| 9 | Account for time | ✅ | ✅ | ✅ | ? | 2026-10-06 | Clock in/out/break/lunch writes a `SHIFT` TimeEntry. `approved: false` means an approval gate exists. |
| 10 | See what I am qualified for, and what is expiring | ✅ | ✅ | ✅ | ? | 2026-10-06 | *My Training* plus his own expiring certification. He also sees manager tiles; the API refuses him. |
| 11 | Read and acknowledge shift notes and notifications at clock-in | ✅ | ✅ | ✅ | ? | 2026-10-07 | Note received with MUST ACKNOWLEDGE, acknowledged, recorded with name and timestamp. |
| 12 | Be called over as the second person on someone else's gate | ✅ | ✅ | ✅ | ? | 2026-10-07 | Verified on **both** gates — training override and reassignment. The one thing an operator does purely for somebody else's record. |
| R1 | Grade a component at teardown, with the part in your hand | ✅ | ✅ | ✅ | ? | 2026-10-07 | A DWI capture node, not a button. Carries the best domain guidance in the product: *"When in doubt, grade down — a reused-but-marginal component fails downstream."* **Copy-vs-control drift:** the instruction says sort into reuse / rework / scrap; the control offers Pass / Fail / Pending. |
| R2 | Raise a finding at the bench when a reused part fails later | ✅ | ✅ | ✅ | ? | 2026-10-13 | Walked end to end: the check held the unit, a lead applied the finding, the rebuild plan re-resolved from it, and the unit routed down Nozzle Recondition and rejoined at Flow Testing. |
| R3 | Work a rebuild step whose scope was only settled this morning | ✅ | ✅ | ✅ | ? | 2026-10-12 | `scope.py` derives on read and writes nothing — the plan page renders operations and slots with a per-row *Because/Why* and states that it reserves and orders nothing. |
| C1 | Pull one unit out of a batch and send it back for rework | ✅ | ✅ | ❌ | ? | 2026-10-15 | The bulk write lands and is scoped to the selection (two parts quarantined, the unselected one untouched). **Demo ❌:** Rework refuses, correctly — the demo's rework step has no inspection substep to send a unit to. Seed authoring, not product capability. |
| C2 | Get an erroneous record corrected | ✅ | ⚠️ | 🚧 | ? | 2026-10-15 | Corrections go through `RecordEdit`, written at 10 service sites. **Only the priority-change site has a read surface**; the other nine capture a reason nothing displays. Pairs with Shift Lead C1, where a reason is captured and now shown. <br><br>**Reframed 2026-10-19.** The `RecordEdit` sites are not operator corrections. They cover lot moves, quantity adjustments, cancelled and chased expected deliveries, shipments and voided shipments, WO priority, and receiving hold reasons — supply-side changes. An operator's bad record is corrected by a quality role voiding the substep completion and the work being re-captured (void scope decided substep-only, 2026-10-19). So the unread reasons are a Receiving / Shipping / Purchasing gap, not an Operator one. **Undecided:** whether and where to show them. |
| C3 | Work when the terminal or scanner is down, and catch up after | ✅ | ❌ | — | ? | 2026-10-07 | **Settled intent, not a gap.** `entered_at` is deliberately not backdatable (it is traceability evidence) and there is no offline mode — an offline write queue would be a backdating mechanism by another name. The paper traveller is the fallback and `running.md` says so. |

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

## QA Inspector

The unit of work is a **decision** — but not the one I first wrote down. The
verdict is **derived**: a measurement crossing its spec quarantines the part,
writes a FAIL quality report and auto-creates a disposition. There is no
Pass/Fail button. *The spec is the judge.*

Rebuilt against `QA_INSPECTOR_TRAINING_SCRIPT.md` (Aug 2026), whose eleven
journeys are an independent derivation of this same list. Its companion is
`UQMES_ONBOARDING_WALKTHROUGH.md` — the self-serve read to this taught version.

### Where work arrives

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Read the home page | ✅ | ✅ | ✅ | ? | 2026-10-06 | FPI banner · Inbox chips (All / Receiving / OSP returns / In-process) · My quality actions · Your gauges. |
| 2 | Scan to navigate | ✅ | ✅ | ✅ | ? | 2026-10-06 | Every scan resolves to the **parent work order**. |
| 3 | Receiving inspection, and clear the paperwork holds | ✅ | ✅ | ✅ | ? | 2026-10-06 | *Accept lot / Reject lot*, not "complete step". Self-clearing holds resolve here; the multi-hold panel on `RCV-MAT-HOLD` matches the documentation exactly. |
| 4 | First-piece buy-off | ✅ | ✅ | 🚧 | ? | 2026-10-13 | A **batch gate**, and a separation of duties: the operator signed the substeps, so QA signs the buy-off. **Demo 🚧:** both *seeded* FPIs are unsignable — one has no designated part, the other's is quarantined with an out-of-spec measurement. A walk-created FPI signs first time. Recorded in `DEMO_SEED_REQUIREMENTS.md` item 2. |
| 5 | A sampled in-process inspection | ✅ | ✅ | ✅ | ? | 2026-10-06 | The workflow is answering **"why this part?"** — the plan and sample size are generated, not decided. `INJ-QA-INSPECT-002` is staged with reason *Post-repair verification* and one rework pass. |
| 6 | OSP return inspection | ✅ | ✅ | ✅ | ? | 2026-10-06 | Before it rejoins the routing. The unified queue is purchased lots + OSP returns, with a **Source** column and one runtime for both. |

### The core — "the one to protect"

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 7 | An out-of-spec reading quarantines the part and raises its disposition | ✅ | ✅ | ✅ | ? | 2026-10-06 | Derived, not chosen. *The spec is the judge* — there is no Pass/Fail button. **The two side effects of a FAIL fire on different triggers:** `record_quality_report_side_effects` (quarantine, step alert, sampling) runs **only on create** and only with a part attached, while `signals.auto_create_disposition` is a `post_save` with no `created` check, so it fires on **any** save at FAIL. A report edited from PENDING to FAIL therefore opens a disposition against a part that was never quarantined. |
| 8 | Work the disposition — **the decision needs a co-sign** | ✅ | ✅ | ✅ | ? | 2026-10-06 | The inspector lacks `approve_disposition`; an approver authenticates **on the inspector's screen** without logging them out, and the decision commits under the approver's name (AS9100 8.7). Verified: `decision_authorized_by` = the approver, state → IN_PROGRESS. The single best screen in the product. |
| 9 | Close the disposition — this one is yours | ✅ | ✅ | ✅ | ? | 2026-10-07 | The refusal names **both** missing things in one message — no decision selected, and containment required before closing a CRITICAL/MAJOR. One pass to satisfy rather than two bounces. |
| 10 | Re-inspect after rework, history first | ✅ | ✅ | ✅ | ? | 2026-10-07 | Exhibit correctly poised: `INJ-QA-INSPECT-004` runs FAIL → CLOSED REWORK → AWAITING_QA, staged at the re-inspection moment. **Unconfirmed:** whether the part surfaces in the inspector's queue — in-process rows are grouped by (work order, step) and carry no part ids, so its absence from the payload proves nothing. Needs a grouped row expanded in the UI, not another API read. |

### Alongside

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 11 | Work a CAPA task; author a verification plan; initiate one for a pattern | ✅ | ✅ | ✅ | ? | 2026-10-06 | The outcome needs `verify_capa`, which is a manager's. Two stages the button names do not convey: **Add Verification** records a *plan*, **Complete Verification** records the *outcome*. Disposition = this part; CAPA = the pattern. |
| 12 | Check a gauge's calibration before using it | ✅ | ✅ | ✅ | ? | 2026-10-06 | The *Your gauges* tile is the point-of-use nag — a gauge used in the last 7 days whose calibration is due within 7 days. Lit by `quality.py::link_inspector_gauge`; reads *"Torque Wrench TW-25 — overdue 15d"*. |
| 13 | Read a finished record and narrate it backward | ✅ | ✅ | ✅ | ? | 2026-10-15 | Red flag to teach: QUARANTINED or SCRAPPED with no quality report or disposition behind it. The per-serial **Traveler** now supplies the step history this row used to lack. |

### Reman

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| R1 | Accept or reject a harvested component into stock | ✅ | ✅ | ✅ | ? | 2026-10-07 | `/reman/components` → *View Source Core / Accept to Inventory / Scrap Component*. The Accept dialog states the customer-property rule plainly: *"It becomes a part in stock. If its core goes back to its customer, the part is reserved for that core and can't go into anyone else's rebuild."* Pending → In Inventory, Part ID issued. Two blemishes, neither a defect: no success toast, unlike every comparable flow; and the generated serial appends a raw UUID fragment. |

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


!!! note "Table back-filled 2026-10-07 — and the four exceptions it named are now closed"
    These marks were reconstructed from the Findings below, which were written as
    the pass happened while the table was not kept in step. Every ✅ above points
    to a named finding.

    **Corrected 2026-10-15.** This admonition described four rows that have since
    moved, and it was contradicting its own table in all four:

    - **Row 9** (close the disposition) — said to keep its `?`; **walked
      2026-10-07**, see *VERIFIED — closing a disposition, and a refusal that
      names everything at once*.
    - **Row 10** (re-inspect after rework) — said to keep its `?`; walked the
      same day. The exhibit is correctly poised; what stayed open is narrower and
      is recorded on the row itself — whether the part surfaces in the grouped
      inbox could not be confirmed, because no inbox row carries part ids.
    - **Row 2** — said to be ⚠️ on docs for the scan-box drift. The drift was
      written up; the row is ✅.
    - **Row 13** — said to be ⚠️ because no step-by-step history sat behind the
      record. **QA Manager row 11 closed that on 2026-10-15**: the part detail
      page carries a per-serial **Traveler**. The reason for the caveat is gone.

    **The lesson is about the artifact, not the work.** A table left at `?` while
    the prose fills up makes a finished pass look untouched — the at-a-glance view
    is the thing anyone actually reads. Mark the row when the row is done.

## Shift Lead

The unit of work is the **shift**.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See the shift's state at a glance | ✅ | ✅ | ✅ | ? | 2026-10-07 | Biggest fire, late jobs, quarantine, CAPAs, OSP, training — one screen. |
| 2 | Put people on jobs | ✅ | ✅ | ✅ | ? | 2026-10-12 | The board renders every resource as a lane; the task panel gives work order / due date / machine / work centre / operator / fence zone / live status. **Reassign** is honest about scope — *"applies now, re-solve to optimize"* — and the operator picker is filtered by **eligibility** (work-centre membership), not a flat list. **Row may be misframed:** operators *claim* through Start Work rather than being pushed work, with the lead stepping in to reassign; *"reassign work when someone cannot run it"* is closer to the real model. |
| 3 | Cover an absence or no-show | ✅ | ✅ | ✅ | ? | 2026-10-12 | Same surface as row 2. Worth teaching as a diagnostic: an **empty operator picker is a training problem wearing a scheduling costume** — nobody is qualified and rostered for that work centre. |
| 4 | Unblock a stopped job | ✅ | ✅ | ✅ | ? | 2026-10-07 | The Control Center **Exceptions** tab — 21 unified items, each with its impacted work order and a direct link. |
| 5 | Authorise an unqualified operator, on the record | ✅ | ✅ | ✅ | ? | 2026-10-07 | Override recorded with both names, the reason and a timestamp, and `authorized: false` preserved so the record never claims the operator was qualified. Shares one exhibit with Operator 3 and 12. **No screen displays it** — `training_authorization` is on the StepExecution detail endpoint and nothing in the frontend reads it. |
| 6 | Triage a quality event without escalating everything | ✅ | ✅ | ✅ | ? | 2026-10-07 | Exceptions tab: source, severity, age, owner, *Open only* filter, bulk resolve. |
| 7 | Watch what is going late | ✅ | ✅ | ✅ | ? | 2026-10-07 | *Jobs going late* on the hero, plus **Overdue / Due today** filters in the Control Center. |
| 8 | Hand over to the next shift | ✅ | ✅ | ✅ | ? | 2026-10-07 | **Not weak, as the row was first guessed** — audience targeting by role, a High priority flag, *Requires acknowledgment*, and acknowledgment recorded with name and timestamp. The composer's placeholder teaches the genre. |
| 9 | See who is qualified for what | ✅ | ✅ | ✅ | ? | 2026-10-06 | The training matrix, plus current / expiring / expired on the hero. Note the matrix reports **role** gaps while the start gate reads **step** requirements — a person can show a role gap and still start every step. |
| 10 | Escalate what the shift cannot solve | ✅ | ✅ | ✅ | ? | 2026-10-19 | **Report…** on the Exceptions tab records **downtime** for real and links out to the disposition and CAPA forms for the other two — see **Report exception saves nothing** (fixed). Walked 2026-10-19 as Tenant Admin on the WO control page and the Control Center: equipment list excludes types with *Track downtime* off, the event survives a reload and resolves from the card. **Demo seeds no downtime events**, so the card shows only what someone records. Escalating a record for retraction (C2) has no dedicated route. Existing items in the tab are real and carry source and severity. |
| R1 | Decide a pending finding — apply or dismiss | ✅ | ✅ | ✅ | ? | 2026-10-08 | `PendingFindingsCard`: *"1 finding to decide — Raised at the bench after teardown. Nothing below has changed the plan yet — applying one re-grades the component, and this plan re-resolves from it."* Injector Body **Grade A → B**, attributed with a timestamp. **Apply** re-grades and clears the card; the application is appended to `condition_notes` as a trail and `proposed_grade` is emptied. **Dismiss** sits beside it and takes a reason. |
| R2 | Request customer authorisation for over-and-above | ✅ | ✅ | ✅ | ? | 2026-10-07 | From an IN_REBUILD core, **Authorise…** → *Awaiting customer authorisation*. `send_for_authorisation` compares resolved scope against the `RebuildScopePreset` and refuses when nothing exceeds the sold level: *"Nothing on … goes beyond the rebuild level that was sold, so there is nothing to authorise."* Only genuinely new work reaches a gate. |
| R3 | Decide a torn-down unit's exit: rebuild, harvest, or return | ✅ | ✅ | 🚧 | ? | 2026-10-15 | A DISASSEMBLED core offers **Rebuild to stock** / **Release to inventory**, each tooltipped with its consequence (identity kept and stocked as reman FG, vs components accepted and the core consumed). Rebuild → **In Rebuild**, walked. **Demo 🚧:** the third exit (*return*) has a subject since the reseed — `CORE-240210-0007`, a Midwest warranty unit, `REPAIR_RETURN`, `returns_to_customer=True` — but it waits on that unit reaching REBUILT, which Shipping R1 tracks. |
| C1 | Jump a job to the front, with a reason | ✅ | ✅ | ✅ | ? | 2026-10-15 | **Both halves now exist** (`5b9b6d0`). There is no expedite *action*: **Expedited is derived** from `priority === URGENT`, so jumping a job means setting priority. `change_priority` refuses without a reason — *"Say why the priority is changing"* — and writes a `RecordEdit` with field / old / new / reason / who / when beside auditlog's who-and-when. The edit form asks *"Why change priority from Normal to Urgent?"* and lists the last five with their reasons. **Residual:** a CSV import or the master workbook still changes priority with no reason recorded. |
| C2 | Void an operator's bad record | ✅ | — | — | ? | 2026-10-15 | **Not this role, by design.** The product supports voiding; the Shift Lead does not hold it at all. `VOID_COMPLETION_PERMISSIONS` goes to `tenant_admin`, `qa_manager` and `qa_inspector`, withheld from Operator, Shift Lead **and** Production Manager on purpose — performing or supervising work and adjudicating the record are different jobs. A lead who needs a record retracted escalates, which is row 10. Marked `—` not ❌: the capability exists and is somebody else's. |
| C3 | Take a machine out of service and re-plan around it | ✅ | ✅ | ✅ | ? | 2026-10-12 | Holds `change_equipments`. The *re-plan* half needs a solved schedule, which now exists. An uncalibrated or out-of-service machine is dropped from solver affinities, so the two halves interlock. |

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

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is expected | ✅ | ✅ | ✅ | ? | 2026-10-07 | *On order / Late* chips on Materials. An expected receipt is **not a separate model** — it is a `MaterialLot` that has not arrived yet, carrying PO number, line, promised date and chase fields. |
| 2 | Receive a delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | Booked in 180 of 200 → new lot number, heat number captured, auto-routed to inspection with no manual step. The dialog states its own consequence and takes a photo or PDF of the CoC and packing slip. |
| 3 | Verify against the paperwork | ✅ | ✅ | ✅ | ? | 2026-10-07 | The unified **Incoming Inspection** queue — purchased lots + OSP returns, one runtime for both, separated by a **Source** column. |
| 4 | Handle a short or over delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | The best copy in the receiving flow: *"20 fewer than the 200 on order. What does the packing slip say?"* → *More coming* keeps the remainder on order; *That's all* stops UQMES planning on it and says outright that closing the PO line happens in the ERP. Produces a BACKORDERED lot plus a named remainder. |
| 5 | Resolve holds | ✅ | ✅ | ✅ | ? | 2026-10-06 | `RCV-MAT-HOLD` shows **Held for 2 reasons — each clears on its own**. Paperwork holds self-clear inline (enter the heat number and it moves); judgement holds need a quality manager, and an inspector gets no release button. |
| 6 | Reject and return | ✅ | ✅ | ✅ | ? | 2026-10-07 | `Reject remaining stock…` → *Return to supplier* + reason → disposition opened with it. **Ship back** then appears: RMA number, *Print RTV sheet*, carrier and tracking, replacement expected. The replacement delivery is created automatically, so return → replacement → chase closes as a loop. The lot leaves as **Returned, not scrapped — the goods exist, at the vendor**; credit is settled in the ERP. `reject_whole_lot` is QA Manager and Tenant Admin only; for anyone else the menu item is not rendered. |
| 7 | Put away and find again | ✅ | ✅ | ✅ | ? | 2026-10-07 | `/production/locations` — 6 locations with live Lots / Units / Machines counts and drag-to-nest. **Move…** is scoped to the lot, destination is a datalist, quantity optional so partial putaway works. The location detail then lists it and the ledger records **`In · from Receiving Dock · <who>`** with a timestamp. Refusals quote the input: *"MainStores isn't one of your locations."* |
| 8 | Count stock | ✅ | ✅ | ✅ | ? | 2026-10-12 | Blind count then apply. `CC-2026-0001` is seeded started-blind at Main Stores with two lots counted and one deliberately one short, **submitted but not applied** — applying needs `apply_cyclecount`, a lead's, so both halves stay exercisable. |
| 9 | Chase a late delivery | ✅ | ✅ | ✅ | ? | 2026-10-07 | `chase_expected_receipt` records what the buyer was told and any new promise, and **keeps the first one**: *"The first promise stays as it was — on-time delivery is judged against it."* The UI shows *"first promised …"* beside the new date, so **a supplier cannot improve their OTD by asking for a later date**, and the screen says so. |
| 10 | Hand receipts to the ERP | ✅ | — | ✅ | ? | 2026-10-15 | **Not a feed, by design.** **Glovia is human-bridged** — the ERP this has to reach dates from 1996 and cannot be integrated with, so every exchange is a person carrying a sheet. What UQMES owes the job is a **document**: the Materials page carries *"Receipts for ERP"*, and the row is a gap only if that paperwork is unfit for a human to carry. |
| 11 | Stage and kit material to the bench for the next shift | ✅ | ✅ | ✅ | ? | 2026-10-12 | `/production/staging` lists scheduled work per station with each material line's quantity, source lot and location; optional lines are marked and steps consuming nothing say so. **Confirm** moves a station 0/1 → 1/1 and records who staged it; **Took another** handles the picker grabbing a different lot. Carries its own staleness warning. **Trap worth teaching:** the window defaults to 8 h, so on a plant holiday the page reads *"Nothing scheduled in this window"* and looks broken — at 24 h it is full. Doubles as the fastest proof a calendar exception reached the solver (Scheduler 9). |
| R1 | Receive a core | ✅ | ✅ | ✅ | ? | 2026-10-07 | **Not a form on the core page — an authored DWI step**, which is why it was unreachable until a core sat on a route. Scan the identity band, photograph as received, grade arrival condition, sign off. *"Cores arrive as-is from the field - record what you see, don't clean yet"* is the right instruction: cleaning destroys the evidence of arrival condition, and the photograph is what supports ISO 9001 8.5.3 for customer property. |
| R2 | Receive a bulk core lot and identify units from it | ✅ | ✅ | ✅ | ? | 2026-10-07 | *"A counted delivery with no serials. Units are given identities later, one at a time, and are exchange cores."* The core-type picker offers only types cores were received as or with a disassembly BOM, so purchased stock cannot be counted into the core bank. **Identify a unit** takes grade, source, serial and notes, with **Identify and next** for working down a pallet. `fulfilment_mode=EXCHANGE` is enforced — *"definitional, not shop policy"* — and `part.received_in_lot` holds the trace back to the receipt. |

## Shipping

> **All thirteen rows walked.** Rows 1–7 and 9 on 2026-10-08 once the reseed
> landed; **row 8 on 2026-10-12**, when seed phase 9 (`dark_exhibits.py`) gave
> `RCV-MAT-0005` a permanent owner and the board's **Customer property** group
> rendered on a fresh seed.
>
> *Corrected 2026-10-15.* This header read *"Row 8 remains open. — the shipping
> code is complete and coherent; no seeded route can reach it"* — a sentence
> welded to the middle of an older one by an edit that never finished, and wrong
> twice over: row 8 had been lit three days earlier, and the ship-terminal
> problem it was describing belongs to the rows that *do* still wait on it, not
> to row 8, which never depended on a ship step at all.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is ready | ✅ | ✅ | ✅ | ? | 2026-10-08 | `/production/shipments` states the boundary in its header: *"What can go to customers now, and what has gone. Invoicing stays in your ERP."* Tabs **Ready to ship** / **Shipped**, grouped by order with the customer named. |
| 2 | Confirm it passed and is complete | ✅ | ✅ | ✅ | ? | 2026-10-08 | Each unit shows *Waiting at: Ship step*. The ship dialog states the release check plainly — *"Each part at a Ship step completes it, so its sign-off checks must be done"* — so the ISO 9001 §8.6 gate runs through `advance_part_step` exactly as it would for one part. **The route's Ship step is the queue.** |
| 3 | Create the shipment | ✅ | ✅ | ✅ | ? | 2026-10-08 | Select units → **Ship …** → shipment number issued, landing on the shipment detail. |
| 4 | Produce the paperwork | ✅ | ✅ | ✅ | ? | 2026-10-08 | Shipment detail offers **Packing list**, **CoC**, **Edit paperwork** and **Void…**. The paperwork block carries carrier, tracking, ERP shipper / packing slip and expected delivery; Units lists each serial with its work order and order; History records CREATED with actor and time. |
| 5 | Ship partially | ✅ | ✅ | ✅ | ? | 2026-10-08 | Per-unit checkboxes, **Ship …** disabled until something is selected. Shipping 3 of 6 recounts the board and leaves the correct three waiting. |
| 6 | Record carrier and tracking | ✅ | ✅ | ✅ | ? | 2026-10-08 | Carrier, tracking and ERP slip recorded and shown. Tracking is explicitly *(can add later)* with **Edit paperwork** for it — the dock often ships before the number comes back. |
| 7 | Undo a mistake | ✅ | ✅ | ✅ | ? | 2026-10-12 | The dialog states the distinction exactly: *"For a shipment recorded by mistake — the parts didn't go. They return to their Ship step (sign-off runs again) or to stock. **Goods that went and came back are a return, not a void.**"* Verified by shipping a unit specifically to void it: header reads **Voided**, the reason is kept, History retains CREATED, and in the database the part is back to IN_PROGRESS at its Ship step with `customer_shipment: None`. |
| 8 | Return customer property | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Independent of any ship step** — the board's second half filters lots on `owner__isnull=False`: *"A customer's own material, still here: it can go back to them, grouped under them."* The dialog is lot-aware (*"Blank quantity ships the whole lot; less splits that much off and the rest stays"*), so partial return works. `MaterialLot.owner` cites **ISO 9001 §8.5.3** and is enforced throughout: consumption draws customer property only for that customer's work, requirements never cover anyone else's demand, dock metrics exclude it, and the lot label prints it *"so nobody draws it into someone else's job"*. |
| 9 | Know whether we are on time | ✅ | ✅ | 🚧 | ? | 2026-10-15 | **Fixed** (`e81d371`): `delivery_performance` falls back to the work order's own `expected_completion` where there is no order line, and returns an `unmeasured` count for shipments carrying no date at all. **The silent exclusion was the defect** — the page reported a confident percentage of whatever happened to carry order lines, which reads as covering everything shipped. Now shows "N not measurable" beside the figure. **Demo 🚧:** both shipped work orders carry lines, so neither the fallback nor the unmeasured count fires on seeded data; five tests in `test_customer_shipping.py` are the only evidence, including a key collision that would have folded two line-less work orders on one shipment into one delivery. **Worth knowing:** migration 0178 backfills order lines as one-shot history repair, and `seed_demo` creates its orders afterwards — which is why every fresh seed produced line-less orders. |
| 10 | Send parts out to a subcontract vendor, and record them back | ✅ | ✅ | ✅ | ? | 2026-10-19 | `OutsideProcessPanel` on the WO Control page. **Send out** takes vendor, PO / packing-slip reference and quantity. **Receive back** and **Inspect** both route into the **operator substep runtime** — the return inspection *is* a step execution, not a side dialog — properly authored with a measured coating thickness, photo capture, result and sign-off. The review screen's verb is **Accept return**, not Complete step. Shipment reaches CLOSED. <br><br>**Fixed (re-checked 2026-10-19):** `services/mes/outside_process.py::accept_return` now sends each part through `advance_part_step`, so an accepted return moves its parts on. Since 2026-10-19 a step naming a **Special process** also refuses send-out to an unqualified vendor. *History of the defect, kept for the lesson:* **The shipment used to close while the parts did not move on.** `accept_return` sets each part `READY_FOR_NEXT_STEP`, completes the executions and closes the shipment, but never calls the advancement engine — despite its docstring saying it *"advances the shipped parts past the OSP step"*. `try_advance_lot` then refuses with `['No active StepExecution']` because the execution is already COMPLETED. `OSP-DEMO-005` and `OSP-DEMO-006` are deliberately left stranded at Nitride Coating as the reproduction. **Lesson: a row is walked when the SUBJECT moves, not when the surface reports success** — I asserted end-to-end completion from the shipment status alone. **Residue:** `OSP-DEMO-005` / `-006` are still `READY_FOR_NEXT_STEP` at Nitride Coating from the old reproduction — a reseed or the arc clears them. |
| R1 | Return a rejected core to its owner | ✅ | ✅ | 🚧 | ? | 2026-10-13 | Service, precondition and UI all verified present. `return_to_customer` needs REBUILT or DECLINED; REBUILT comes from finishing the scoped rebuild route (`complete_rebuild` via `finish_route`), and the Final Test sign-off that was once thought to block it is a one-click attestation, walked. **Demo 🚧:** `CORE-240210-0007` is the subject and has not yet been walked to REBUILT. `return_to_customer` refuses an EXCHANGE unit by design — *"it is an exchange unit — it has no owner to go back to"* — so this row needs that one warranty core specifically. |
| R2 | Ship a rebuilt unit with a cert describing what was replaced | ❌ | ❌ | — | ? | 2026-10-13 | **A product gap, and the sharpest one in the file.** Three pieces exist and never meet: (1) the **as-built record** is collected — `componentInstallCapture` is authored on Assembly, which is in this unit's resolved scope, producing `AssemblyUsage` rows naming the unit's **own** components; (2) the **CoC** exists, built from a `CustomerShipment`; (3) **`return_to_customer` creates no `CustomerShipment`** — it sets the stage RETURNED, the part SHIPPED, stamps `returned_at`/`returned_by` and stops. **So a repair-and-return unit goes back with no document route at all** — no packing list, no CoC, no way to hand over the as-built list just recorded. The paperwork is shipment-scoped and a return is not a shipment. For a reman shop that is the point of the whole lane: giving a customer back *their* unit with evidence of what was done to it. |
| C1 | Export-control screening before anything leaves | ✅ | — | — | ? | 2026-10-14 | **Not a target — user decision:** export control *"is an artifact of a need that didn't turn out to be a true need."* Marked `—` so nobody reads this as a worklist: **do not build the rework items, do not create a non-US test account, do not flag more part types.** The machinery is real and enforced — `for_export_control(user)` excludes `itar_controlled` rows for a non-US person and logs each denial to a `compliance.access_control` logger — and is kept accurate in case it is ever revived. Two facts worth retaining: the denial side can never fire in demo, because every seeded user is `us_person=True`; and `can_access_itar_data` falls back to `getattr(user, 'itar_authorized', False)`, a field that **exists nowhere else in the codebase**, so a non-US person holding a TAA or licence could never be granted access. |

## Scheduler

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Produce a schedule | ✅ | ✅ | ✅ | ? | 2026-10-15 | Solve is gated on `add_scheduleresult`, held by **Planner, Production Manager and Tenant Admin** — `presets.py:984` grants it to `planner` directly rather than via the `SCHEDULING_PLANNER_PERMISSIONS` bundle, whose own comment names only the other two. For anyone else the toolbar is absent and the empty state has no action. Solve dispatches a Celery task and says so honestly with no worker: *"queued 6s ago, waiting for a worker."* The header then carries the whole objective, including the **two-phase split**, machine then people. |
| 2 | Find out why something is not on it | ✅ | ✅ | ✅ | ? | 2026-10-08 | One of the best surfaces in the product. *Not scheduled* opens *"Why isn't this scheduled?"*, grouped **by cause** with a remedy per group, and admits what it cannot explain: *"nothing above explains it — the solve most likely ran out of horizon or time."* Every row clicks straight into the work-order editor, so you diagnose and fix without leaving the dialog. |
| 3 | Dispatch people | ✅ | ✅ | ✅ | ? | 2026-10-08 | **Dispatch** reports coverage rather than assuming it — *"259/265 attended tasks covered"* — and the uncovered count becomes a standing chip on the board, not just a toast. |
| 4 | Adjust by hand | ✅ | ✅ | ✅ | ? | 2026-10-08 | The task panel gives work order, due date, machine, work centre, operator, **fence zone**, live status and material state. Reassign is honest about scope — *"applies now, re-solve to optimize"* — and the operator picker is filtered by **eligibility**, not a flat list. Reassigning recounts the uncovered chip live. Also offers Pin, Merge into batch and Edit WO. |
| 5 | React to a disruption | ✅ | ✅ | ✅ | ? | 2026-10-08 | Reactive staleness: signals flip `ScheduleResult.is_stale` when demand, a part or capacity changes under the live plan, with `mark_active_schedule_stale` as the single entry point so bulk `.update()` paths trip it identically. **Deliberately not tripped by routine step advances** — *"an actuals drift on every advance would leave the flag permanently on and meaningless."* A hint, not an auto-solve. |
| 6 | Test a change before committing | ✅ | ✅ | ✅ | ? | 2026-10-08 | **What-if** runs a second solve as a DRAFT, leaving the live plan untouched, and the comparison panel states the trade-off in **both** directions rather than selling the change — makespan down, lateness up. It also warns what the change costs: *"⚠ 58 frozen task(s) had to move — the world changed under the pinned plan."* Discard restores the live figures exactly. **Caveat:** solves finish at a 66–99.6% optimality gap, so two runs on identical inputs give very different objective numbers — the panel presents that as the effect of the change. |
| 7 | Get the plan to the floor | ✅ | ✅ | ✅ | ? | 2026-10-08 | Dispatch is the hand-off; the floor-side half is covered by the Operator rows. The Control Center's **Dispatch List** is a separate printable path to the same plan — a report, not an assignment surface. |
| 8 | See whether the floor followed it | ✅ | ⚠️ | 🚧 | ? | 2026-10-12 | `scheduling/actuals.py` is **capture-only** by design: it stamps `actual_start` / `actual_end` as a part enters and leaves a step and *"deliberately does NOT re-time the plan or mark the schedule stale."* **Demo 🚧:** 11 of 569 tasks carry an `actual_start`; `actual_end` stays null for steps still running, which is correct. **Not seedable deterministically** — it needs a solve *followed by* movement, and the seed does not solve. **Re-checked 2026-10-19:** unchanged — still capture-only, no adherence view, and the demo still has no solved schedule (0 `ScheduledTask` rows). |
| 9 | Author non-working time — holidays, shutdowns, PTO, training | ✅ | ✅ | ✅ | ? | 2026-10-08 | All four kinds authored: plant calendar exceptions (holiday, inventory, shutdown) and labour blocks (PTO, training, a recurring meeting), plus a shift. **The solve honours them** — the seeded holiday carries 0 tasks while the next day carries 119. That is the half that matters; the row's own warning is *"a stale calendar breaks the plan on day one."* |
| R1 | Schedule work whose route isn't known until teardown | ✅ | ⚠️ | ✅ | ? | 2026-10-13 | **Book the nominal route, re-solve when reality diverges.** `routing.py` schedules DEFAULT edges only; rework and escalation branches are *"not scheduled up front; a re-solve handles a part that actually fails"*, keeping the scheduled subgraph acyclic. A core awaiting its exit decision books **0** steps, correctly — nothing is known yet. <br><br>**⚠️ A deliberate simplification, held open.** Per the user: *"Because of the tree versus sequential nature of reman I'm waiting until I have real data to fully flesh out the scheduling system strategy."* The scheduler treats a reman unit as a sequential nominal route; reman is tree-shaped, since what comes off a unit decides what goes back on. The earlier disagreement — the solver booking operations the rebuild scope would skip — **resolved itself by removal**: under *nothing is skipped*, booking the main line is simply correct, and `scheduling/data.py` dropped `_rebuild_scope()` entirely. The two subsystems stopped disagreeing because one stopped having an opinion. **Re-measure the 220% board load after a reseed**; if it moves, this row and Scheduler 6 need their numbers rewritten. |

## Production Manager

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what is at risk | ✅ | ✅ | ✅ | ? | 2026-10-07 | One screen: late jobs, quarantine, CAPAs, first pass yield, supplier qualifications expiring, competency coverage. The last of those is the training matrix's staffing-risk lens surfaced for a manager. |
| 2 | Release work | ✅ | ✅ | ❌ | ? | 2026-10-19 | Release is **not** the schedule's Dispatch — it has its own service, *"the planner's authorization gate"*, and the gate is **advisory, not blocking**: *"a failing check never refuses; it demands a written reason, which is stored on the work order. Blocking here would just teach people to fake the data."* <br><br>**Every door uses the service.** The scheduling surfaces (`useReleaseForScheduling` — capacity planning, the Gantt, Pull in work), the WO Control Center's **Release (N)** (`useBulkRelease` → `bulk_release`, `services/mes/release.py:238`, which re-offers blocked orders for an override reason) and, since 2026-10-19, the work order page's **Release** all call `release_work_order`, writing `released_at`, `released_by` and `release_override_reason`. Releasing never changes status; *In progress* follows from work starting. See **BUG — the work order page's Release skips release** (fixed). **Demo ❌:** 0 of 18 work orders have `released_at` set. |
| 3 | Promise a date | ✅ | ✅ | ✅ | ? | 2026-10-12 | `/production/capacity` → **Could we take this order?** gives binding resource, shortfall, counter-offer and full work content: *"Not by 2026-11-01. Labor — needs 551.6h, only 327.8h free by then. Earliest it fits: end of 2026-11."* The page also warns that 12 orders have operations with **no cycle time**, naming four and linking to the process editor — Engineering 6 seen from the planning end. **Fixed on the walk:** the verdict and the counter-offer both rendered as a month, so a due date on the 1st collided with its own month and read as a contradiction. The arithmetic was always right; the labels were lossy. Regression test holds it. |
| 4 | Resolve escalations | ✅ | ✅ | ✅ | ? | 2026-10-07 | Holds `resolve_step_decision`. Control Center **Exceptions** is the shared surface with the Shift Lead. |
| 5 | Balance capacity and staffing | ✅ | ✅ | ✅ | ? | 2026-10-08 | Both halves on one surface: per-resource booked hours down the board's left rail, with Dispatch reporting staffing coverage against it. The demo's shop cannot deliver its own order book — ~3,758 h of work against ~2,222 h of labour — which the solver reports correctly rather than hiding. **That is a seed property, not a scheduling defect**, and the 220% figure is further inflated by the nominal-route booking in Scheduler R1. |
| 6 | Approve over-and-above and deviations | ✅ | ✅ | ✅ | ? | 2026-10-07 | **Half misframed.** A "deviation" here is a `QuarantineDisposition` of type USE_AS_IS or REPAIR, rendered as the Deviation Request document — so approving one needs `approve_disposition`, which the PM does **not** hold. That is correct under AS9100: material review authority is a quality function. The PM holds `close_disposition` — production closes the paperwork, quality makes the call. The row should split into *record the customer's answer on over-and-above* (which R1 states correctly) and *close out a deviation once QA has decided it*. |
| 7 | Review OTD and throughput | ✅ | ✅ | ✅ | ? | 2026-10-07 | First pass yield on the hero; customer OTD on the Shipping page, supplier OTD on the scorecard. **There is no single throughput view** — the row is answered across three surfaces. |
| 8 | Maintain the data planning depends on | ✅ | ✅ | ✅ | ? | 2026-10-08 | **Master Workbook** — 21 sheets in load order, validate-then-commit, nothing kept unless every row loads. |
| 9 | Top up a job after scrap outruns the gross-up | ✅ | ✅ | ✅ | ? | 2026-10-08 | Planner-confirmed by design: `work_order_shortfall` reports the gap, `create_makeup_parts` is the explicit action — topping up is never automatic. The demo carries a clean teaching pair: one job where scrap outran the gross-up and owes one, and one that absorbed its scrap because the gross-up covered it. **Placement question:** the only UI door is the scheduling page's work-order dialog, though the shortfall is a property of the work order and the person who needs it is looking at the work order. |
| R1 | Authorise over-and-above and record the customer's answer | ✅ | ✅ | ✅ | ? | 2026-10-07 | *Awaiting customer authorisation* → **Approved** / **Declined**. Approved resumes rebuild; Declined routes to DECLINED rather than straight to returned, because *"it still has to physically go back, and that is the same dispatch step a rebuilt unit takes."* **The product boundary holds exactly:** the card's own comment is *"The conversation happened elsewhere; these record what the customer said."* No price, no quote, no approval-of-quote — UQMES produces the scope and records the answer. |
| R2 | Decide harvest versus buy on a rebuild kit | ✅ | ✅ | 🚧 | ? | 2026-10-07 | `/reman/cores/$id/rebuild` states its boundary in the header: *"Proposed, not committed — nothing here is reserved or ordered."* **Operations** carries a **Because** column so *"nothing is on the job without a reason you can challenge"*; **Slots** gives Position / Needs / Found at teardown / Proposed / Why / Decide / Options. **No pricing anywhere.** **Demo 🚧:** the decision itself cannot be exercised — `Options` is empty because no serviceable component of those types is in stock, so every slot reads *Replace — buy* with nothing to choose between. |

## QA Manager

Rebuilt 2026-10-06 **from the gates the QA Inspector pass actually hit**, not
from subsystem names. The previous list was nine nouns ("run calibration",
"manage supplier quality") that could not be audited.

Every gate below was observed firing for `sarah.qa`; this is the other side of
each.

### The other side of the inspector's gates

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Authorize a disposition decision | ✅ | ✅ | ✅ | ? | 2026-10-06 | Either co-sign at the inspector's station or commit directly holding `approve_disposition`. `decision_authorized_by` records the approver, not the person logged in. The complement of QA Inspector 8, confirming the control from both sides. |
| 2 | Record a CAPA's effectiveness outcome | ✅ | ✅ | ✅ | ? | 2026-10-06 | Holding `verify_capa` she goes straight through with no co-sign. Recording **Effective** **auto-closes the CAPA**, which is undocumented and will surprise someone. A second, separate control sits beside it: `allow_self_verification` is per-CAPA and default-deny, so *"Self-verification is not permitted for this CAPA"* refuses an initiator-assignee even though she holds the permission — an independence bar, not a permission one. |
| 3 | Approve a MAJOR/CRITICAL CAPA before work can start | ✅ | ✅ | ✅ | ? | 2026-10-19 | **Severity chooses the template** (since 2026-10-19): Critical → `CAPA_CRITICAL`, Major → `CAPA_MAJOR`, each falling back to `CAPA_APPROVAL` — see **CAPA approval is not tiered by severity** (built). In demo, Critical falls back (no `CAPA_CRITICAL` template). Full e-signature gate: decision + drawn signature + password re-auth. Self-approval is refused by default per template and, where allowed, demands ≥10 characters of justification and flags `self_approved` on the record permanently. |
| 4 | Co-sign an FPI buy-off for an inspector lacking `sign_off_fpi` | ✅ | ✅ | 🚧 | ? | 2026-10-19 | Walked to completion as an operator with no `sign_off_fpi`: the dialog switches to co-sign mode and says so — *"An authorized QA inspector can sign here without logging you out… It is recorded against the QA inspector's name — not the person logged in."* The record landed with `inspected_by` = the **inspector**, not the person at the keyboard, and both surfaces updated. <br><br>**⚠️ Two defects.** (1) **The drawn signature is discarded.** The dialog validates `requireSignature: true` so you cannot proceed without drawing, then posts only `{id, notes, cosign_email, cosign_password}` — the image never leaves the browser and `FPIRecord` has no field for it, while `ApprovalResponse.signature_data` stores a real PNG from the *same component*. The password re-auth plus `inspected_by`/`inspected_at` may well be a valid e-signature on its own; requiring a pad and keeping nothing is not defensible either way. (2) **The action is offered when it cannot succeed** — for an FPI with no designated part the panel displays *"first piece not yet designated"* and offers **Get QA sign-off** beside it, collecting a signature and a password before the server refuses. <br><br>**Demo 🚧:** both *seeded* FPIs are unsignable (no designated part; designated part quarantined). A walk-created one signs first time. `DEMO_SEED_REQUIREMENTS.md` item 2. **Defect (1) → FIXED 2026-10-19** (migration 0239): `FPIRecord.signature_data` keeps the co-signer's drawing, stored only on the co-sign path and only after email and password verify; the API exposes `has_signature`. `compliance/signatures.md` and `work-orders/fpi.md` updated. **Defect (2) left open deliberately:** the server designates the first piece lazily at sign-off, so "not yet designated" does not always mean sign-off fails, and hiding the button would block that case. **→ FIXED 2026-10-19:** `get_or_create` refuses with `fpi_no_first_piece` when no part has reached the step, so every new FPI has a first piece and fail and waive always run segregation of duties. The panel's old-row text now reads *"first piece designated at sign-off"*. The seeded undesignated FPI is training-arc work. **As found:** the FPI is created only from the runtime banner's **Start FPI**, where a part is already at the step, so it is always designated. A null `designated_part` comes only from the seed or a direct API call. On such a record, fail and waive skip the segregation-of-duties check (`_reject_self_signoff` returns early on None). **Fix handed to the code session:** `get_or_create` refuses when nothing can be designated. The seeded undesignated FPI is training-arc work. |
| 5 | Release a judgement hold at receiving | ✅ | ✅ | ✅ | ? | 2026-10-06 | Unqualified supplier or unapproved part — *"A quality manager can release this hold, or the lot can be rejected."* The judgement/self-clearing split is the whole teaching point of the hold panel. |

### Their own work

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 6 | Decide which of this week's NCRs becomes a CAPA — and justify the ones that don't | ✅ | ✅ | ✅ | ? | 2026-10-15 | Both halves work. Promotion goes through **Create CAPA** on a FAIL report. The *declining* half is `services/qms/capa_decision.py`: `NOT_REQUIRED` and `DEFERRED` with a **mandatory** reason — *"Say why — the reason is what an auditor reads"* — citing ISO 9001 10.2.1(b), with undecided reports left visible so an unevaluated backlog is countable. `PROMOTED` cannot be set by hand; it follows from the CAPA linking the report, so the two can never disagree. |
| 7 | Work the approvals centre | ✅ | ✅ | ✅ | ? | 2026-10-06 | Awaiting / By Type / My Submitted / Overdue. The queue is **not type-scoped** — document releases, CAPA approvals, process changes and training certifications all land in the same place. |
| 8 | Qualify someone for a process, and find whose qualification lapses this month | ✅ | ✅ | ✅ | ? | 2026-10-06 | The matrix answers more than the row asks: coverage risk and single-point-of-failure, not just who holds what. Writing a training record is deliberately **not** an operator or inspector permission — it used to be, and it let people certify themselves. |
| 9 | Raise a SCAR, track the response, change the supplier's standing | ✅ | ✅ | ✅ | ? | 2026-10-06 | A SCAR is **not a parallel model** — it is a CAPA with `capa_type='SUPPLIER'` plus a supplier FK, so it inherits root cause, tasks, verification and closure. Worth saying in the docs, because "SCAR" reads like a separate object and someone will go looking for one. The API filter value is `SUPPLIER`; `capa_type=SCAR` is rejected. The scorecard recommends an action (*"Review: suspend"*) rather than only scoring. |
| 10 | Find everything measured by a gauge that just failed its check | ✅ | ✅ | ✅ | ? | 2026-10-19 | `/quality/calibrations/records/$id/exposure`, answering ISO 9001 **7.1.5.2**. The window leads, because the window *is* the finding. "Found unfit" includes `as_found_in_tolerance=False`, not just FAIL — a gauge adjusted back into tolerance measured wrongly until the adjustment, which is the commoner case. It deliberately does **not** act on its list: the assessment is required, the judgement belongs to a person. **Demo ✅ (2026-10-19):** the seed now records Keyence Vision IM-7020 found out of tolerance at calibration on seed day, adjusted and passed (`as_found_in_tolerance=False`, not a FAIL, so the gauge stays in service), and links it as GAUGE to the Nozzle Inspection reports since its previous calibration. Its exposure lists 9 reports, all with parts (`seed_found_out_calibration`, run last in the scenario). |
| 11 | Pull the complete record for one serial, on demand | ✅ | ✅ | 🚧 | ? | 2026-10-15 | The part detail page carries a **Traveler** scoped to the serial: *"This serial's as-built traveler: its work order's routing, filled with who did each step, what was measured, the lots that went in."* Step history and printable, both halves. **Demo 🚧:** the demo's parts are staged in end state rather than walked, so a seeded serial has few or no `StepExecution` rows to narrate — audit readiness is the hardest thing in this product to *demonstrate*, which is the argument for the deferred seed rewrite. |

### Reman

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| R1 | Record the customer's answer on over-and-above work | ✅ | ✅ | ❌ | ? | 2026-10-12 | **Row was misframed** — the decision is the **customer's**, not the QA Manager's, and the system is deliberately right about that. `request_authorisation` computes the over-and-above and refuses when findings added nothing beyond the sold level; `record_authorisation` records what the customer said. No quote, no approval-of-quote, no PO. **Demo ❌:** no core sits in `AWAITING_AUTHORISATION` on a fresh seed, so there is no answer to record — and over-and-above is the single most distinctive thing reman does. |

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

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Author a part type and its specifications | ✅ | ✅ | ✅ | ? | 2026-10-12 | The `/editor/processes` family. Authoring permissions confirmed in presets, not observed — no demo account holds Engineering alone. |
| 2 | Author a routing: steps, the graph, branches | ✅ | ✅ | ✅ | ? | 2026-10-12 | The flow editor renders nodes and labelled edges. A **QA Pass/Fail** step carries **Pass** and **Fail** handles with labelled edges leaving it — that is how rework lanes are authored. |
| 3 | Revise an approved routing | ✅ | ✅ | 🚧 | ? | 2026-10-19 | An approved process is **locked**: *"This process is locked. Duplicate to make changes."* Duplicate → Draft → Approve is the versioning mechanism, and the list shows a Draft beside the Approved version it replaces — the normal working state. **Demo 🚧 (2026-10-19):** the demo tenant has **no `PROCESS_APPROVAL` template**, so a duplicated draft cannot be approved through **Submit for approval** — `services/mes/processes.py:107` refuses with *"PROCESS_APPROVAL approval template not found"*. The change-control route (C1) still approves a new version. See **GAP (config) — CAPA approval is not tiered by severity**, *Also seen*. |
| 4 | Author work instructions (DWI substeps) | ✅ | ✅ | ❌ | ? | 2026-10-12 | Covered by the DWI passes under Operator. **Demo ❌:** `SubstepResource` and `SubstepTranslation` are **0 rows**, so no demo instruction carries an image or a translation — two authored capabilities that cannot be shown. |
| 5 | Define measurements and attach them as step requirements | ✅ | ✅ | ✅ | ? | 2026-10-12 | 12 `MeasurementDefinition` rows seeded. The definition-vs-requirement distinction holds: a definition is the characteristic, the requirement is its attachment to a step. |
| 6 | Give the solver what it needs | ✅ | ⚠️ | 🚧 | ? | 2026-10-15 | **Only the cycle time is Engineering's.** `Steps.expected_duration` rides on `change_steps`, so authoring roles set it. **Machine eligibility (`stepequipmentaffinity`), changeovers and `StepTiming` are not in `AUTHORING_PERMISSIONS`** — they sit in `SCHEDULING_PLANNER_PERMISSIONS` (Production Manager, Tenant Admin), with changeovers also granted to Planner. So the role that authors the route cannot tell the solver which machines can run it. **15 steps carry no `expected_duration`**, and a step with no duration contributes no load, so the capacity view overstates free capacity — the capacity page surfaces this from the other end, naming the orders affected. **Re-checked 2026-10-19 against `presets.py`:** unchanged — `change_steps` is Engineering's; `steptiming` and `stepequipmentaffinity` are Production Manager / Tenant Admin only, changeovers add Planner. `roles/engineering.md` now says so. |
| 7 | Life limits | ✅ | ✅ | ✅ | ? | 2026-10-12 | 4 definitions, 2 part-type links. **The link *is* the application** — unlinking stops a harvested component inheriting its core's accumulated life and drops a lot's shelf life to the default, which is why `delete_parttypelifelimit` travels with the definition's write permission. |
| C1 | Change control (PCR / PCO / PCN) | ✅ | ✅ | ✅ | ? | 2026-10-15 | **Works end to end.** The process editor's **Propose Change · *File a PCR + fork an editable draft*** sits beside *Duplicate as Template · no change trail*, and the menu distinguishes them. The approved process flips from Viewer/locked to Editor/DRAFT with a banner naming the PCR. The PCR page carries target process, creator, **Affected in-flight WOs** and a **Proposed changes** structured diff; the submit dialog is ISO-shaped — Title, Proposed change, Justification, **Risk analysis**, Priority, **Customer notification required**. Submitting stamps actor and time, captures the diff and auto-assigns an approval. <br><br>**An approved record cannot be repointed.** Two independent guards: `assert_pcr_editable` refuses any write outside `PCR_EDITABLE_FIELDS`, so `target_process` and `draft_process_version` are never editable — *"set when the change is proposed, and the diff is computed at submit"* — and the shared approval lock freezes the row once it leaves DRAFT. PUT on a PCO or PCN is refused outright (405); they are created by approving a PCR and implementing a PCO, not by POST. <br><br>**Three blockers were found and fixed on one walk, each a different class, and the first is the one to remember.** A PCR could not be submitted from the browser: the PATCH returned **200** and saved every field, but the zod client rejected the *response* on `submitted_by_username`, so the user saw "Submit failed" and nothing downstream could ever run. Cause: `CharField(source=…, default=None, allow_null=True)` — DRF's `get_default()` raises `SkipField` when the serializer is **partial**, so on a PATCH the key is omitted entirely rather than sent as null, and `undefined` fails a zod `string | null`. **That is the CLAUDE.md nullable-field trap in a new shape: a write that SUCCEEDS reported to the user as a failure**, invisible to backend tests and to `tsc`. Six fields in `serializers/change_control.py` share the pattern. The other two: the tenant had an `ECO` template and none of the three the services look up; and `auto_assign_by_role` matched `TenantGroup.name` **exactly** while carrying the obsolete underscored convention, so **3 of 4 live templates auto-assigned to 0 users** — silently, because a filter that matches nothing is not an error. Both fixed in the seed *and* in `defaults_service.py`, which provisions every new tenant. |

---

## Purchasing

**Added 2026-10-12**, same reason and same caveat as Engineering.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | Know what is on order and what is late | ✅ | ✅ | ✅ | ? | 2026-10-12 | Shares the Receiving surface (Receiving 1 and 9). Permission boundaries read from `presets.py`, not observed — no demo account holds Purchasing alone. |
| 2 | Chase a late delivery | ✅ | ✅ | 🚧 | ? | 2026-10-12 | Receiving row 9's surface. **OTD is scored against the *first* promise**, so re-promising never repairs the score — deliberate, and the screen shows the original promise beside the revised one. **Demo 🚧:** `ExternalContact` is **0 rows**, and `late_deliveries.py` reads the supplier's deliveries contact for the Late deliveries card — so the "who to chase" half has nothing to show. |
| 3 | Maintain sourcing: lead time, preferred supplier, safety stock | ✅ | ✅ | ✅ | ? | 2026-10-12 | What the requirements report nets against. **A wrong lead time fails silently** — the shortage surfaces later as a job that cannot start and reads as a planning fault rather than a data one. Sourcing edits never version the part. |
| 4 | Qualify a supplier; maintain the approved list | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Raising is Purchasing; approving is QA Manager** (`approve_supplierqualification`) — separation of duties. The create/grant split is the pattern worth copying: anyone may raise a draft, which lands PENDING with `status` read-only, and only the `approve_*`-gated action gives it force. |
| 5 | Read the supplier scorecard and act on standing | ✅ | ✅ | ✅ | ? | 2026-10-12 | Per-supplier acceptance, reject rate, CoC compliance, on-time delivery and open SCARs, with standing and a **recommended action** (*"Review: suspend"*), not just a score. Thresholds: C on any open SCAR, reject ≥ 10% or on-time < 85%; A at reject ≤ 2%, CoC ≥ 99%, on-time ≥ 95%. Empty states are honest rather than showing zeros that read as failure. **Label trap:** "Lots received 6" beside "Reject rate 50%" invites 1/6 — the denominator is *inspected* lots, and customer property is excluded entirely. |
| 6 | Raise a SCAR against a supplier | ✅ | ✅ | ✅ | ? | 2026-10-12 | A SCAR is a CAPA against a supplier, gated on `initiate_capa`, which Purchasing holds. See QA Manager 9 for why it is not a parallel model. |
| C1 | Purchase orders, prices, spend approval | ✅ | — | — | ? | 2026-10-12 | **Out of bounds by design.** UQMES records what is expected and what waits on it; the PO lives in the ERP. Not a gap, and not a row to build against. |

!!! note "Two empty tables behind documented behaviour"
    `ExternalContact` is **0 rows**, and `late_deliveries.py` reads the supplier's
    deliveries contact for the Late deliveries card — so the "who to chase"
    feature has nothing to show. `MaterialUsage` is also 0 tenant-wide.

---

## Document Controller

**Added 2026-10-12.** Walked as `lisa.docs@demo.ambac.com`, a real seeded
Document Controller — so unlike Engineering and Purchasing, the Code column here
reflects what the role can actually reach.

| # | Workflow | Docs | Code | Demo | Training | Checked | Notes |
|---|----------|------|------|------|----------|---------|-------|
| 1 | See what needs me | ✅ | ✅ | ✅ | ? | 2026-10-12 | Home carries **Approvals in flight**, **Documents** (*Needs my approval · Pending approval · Due for review · Released*) and **Training**. Every figure links. Walked as a real seeded Document Controller, so unlike Engineering and Purchasing this role's Code column reflects what the role can actually reach. |
| 2 | Upload a document with type and classification | ✅ | ✅ | ✅ | ? | 2026-10-12 | The list carries File Name · ID · Version · Status · Type · Classification · Uploaded · Uploaded By. The document's name comes from the file — there is no title, description or document-number field. |
| 3 | Route a document for release approval | ✅ | ✅ | ✅ | ? | 2026-10-12 | Approval type **Document Release** appears in the in-flight queue. There is no template to choose: the template is selected by approval *type*, not by the submitter. |
| 4 | Work a mixed approvals queue | ✅ | ✅ | 🚧 | ? | 2026-10-15 | **In flight ≠ assigned to me.** Home's *Approvals in flight* lists everything moving through the system; *Needs my approval* is the actionable number, and for this role it reads **0** beside an in-flight count of 5. Eligibility is per-request: `can_approve()` checks approver and group assignment, enforced at `services/core/approval.py:553`, and those assignments come from the **approval template**. By default (`defaults_service.py:149-184`) Document Controller is assigned to **Document Release** only — CAPA approvals follow the severity-chosen template (`CAPA_CRITICAL` / `CAPA_MAJOR`, falling back to `CAPA_APPROVAL`) — none of them assigns Document Controller by default. So this is a document approvals queue unless a tenant routes other types here. **Demo 🚧:** nothing is assigned to this role, so the queue cannot be worked. |
| 5 | Track the lifecycle | ✅ | ✅ | ✅ | ? | 2026-10-12 | Draft → **Under Review** → **Released**, with Version on the row; both live states observed. **Obsoleting is a deliberate act** — approving a new revision does not retire the old one, which simply stops being current and keeps whatever status it had. |
| 6 | Find what is due for review | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Nothing notifies you** — the *Due for review* tile on Home is the only thing that will tell you, and you have to go and look. The review period is a document-*type* setting, and a type with no review period never prompts one. Lit by seed phase 9: one document carries a `review_date` 14 days past. |
| 7 | Classify, and hold the secret tier | ✅ | ✅ | 🚧 | ? | 2026-10-12 | `classify_documents` and `view_secret_documents` are this role's and the QA Manager's alone, so the Document Controller can both set and read back all five tiers. **Demo 🚧:** one document is now Confidential, so the filtering can be seen hiding a document from a reader below it — but **no tier above Confidential is exercised**, and Secret, the distinctive one, stays dark. |
| 8 | Write training records | ✅ | ✅ | ✅ | ? | 2026-10-12 | Holds `TRAINING_RECORD_WRITE` — the same tier as the training gate override, and deliberately withheld from Operator and QA Inspector. |
| C1 | Delete a document | ✅ | ✅ | ✅ | ? | 2026-10-12 | **Delete Document** is offered on every row at manager tier. Soft-delete semantics — see [[soft-delete-defeats-protect]]. Obsolete documents are **not** hidden: they stay in the library and status is a filter you choose. |

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

   !!! warning "Re-checked and DELEGATED 2026-10-15 — and the mechanism is sharper than written above"
       Still live: `viewsets/mes_standard.py:1356` and `:1379`. Handed to the
       scheduling session to fix; it was the oldest unfixed finding in the file
       and the only outstanding one that is a disclosure issue rather than a
       decision owed.

       **The root cause is not a missing gate — it is a weaker one replacing the
       default.** `settings.py:341-345` sets `DEFAULT_PERMISSION_CLASSES` to
       three stacked classes — `IsAuthenticated`, `TenantAccessPermission`,
       `TenantModelPermissions`. Every other viewset in the file inherits all
       three, which is why `TenantModelPermissions` appears **zero** times in it.
       These two declare `permission_classes = [IsAuthenticated]`, and DRF treats
       that as a **replacement**: the line that reads as *adding* a check drops
       two. Worth stating plainly, because the original write-up below reads as
       "no permission class was set", and someone checking would find one and
       move on.

       **Queryset filtering cannot run even in principle.**
       `build_incoming_rows()` and `build_inbox_rows()` are declared with **no
       parameters at all**, so the viewset has `request.user` and nowhere to pass
       it. `for_user()` (`models/core.py:655`) is never reachable from here.

       **Tenant isolation is intact** and the finding should not be read as a
       cross-tenant leak: both builders use `.objects`, which auto-scopes via the
       ContextVar `TenantMiddleware` sets. What leaks is **within-tenant, across
       roles** — a customer reading the supplier list and quarantine state, but
       equally any operator reading the inspector's queue.

       **The fix is two parts**, and the second is where the work is:
       `build_inbox_rows()` composes five sub-builders (`_fpi_rows`,
       `_qa_signoff_rows`, `_receiving_rows`, `_outside_process_rows`,
       `_in_process_rows`), each constructing its own queryset, so the user has
       to be threaded through each rather than at one call site. Note
       `awaiting_inspection(qs)` is shared with the MaterialLot
       `inspection_pending` lens and has already drifted into three copies once —
       keep the rule in one place.

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

### ~~PARTIAL~~ → CLOSED 2026-10-15 — "pull the complete record for one serial" (QA Manager #11)

!!! success "Both halves of this finding are answered; the row is green"
    The two gaps below — *no step-by-step execution history* and *no single
    per-serial artifact* — are both closed by the **Traveler** button on the part
    detail page, scoped to that serial (`fieldsConfigMap.tsx`, passing both the
    work order and the part id): *"This serial's as-built traveler: its work
    order's routing, filled with who did each step, what was measured, the lots
    that went in."* The step history **is** the routing filled in, and the
    printable is the PDF.

    Two things this finding said would be needed arrived separately and are worth
    connecting: `MaterialUsage` was lit by seed phase 9, so the lots-that-went-in
    line is populated; and QA Inspector row 13's ⚠️ was resting on this same
    absence and has been cleared with it.

    **Kept rather than deleted** because the reasoning below — that audit
    readiness is the hardest thing to *demonstrate*, and that the demo's
    staged-end-state data has no history to narrate — is still true and is the
    argument for the deferred seed rewrite.

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

### ~~CODE GAP~~ → BUILT — a failed calibration is not traced back to what the gauge measured

!!! success "This gap was specced here and built from the spec"
    It closed within the same pass. The backward assessment now exists as
    `/quality/calibrations/records/$id/exposure` — see **VERIFIED — the gauge
    recall page ("What it measured") answers ISO 9001 7.1.5.2** below, which
    walks it and records three places the builder went beyond this spec and was
    right to. QA Manager row 10 and QA Inspector C2 are both green on it.

    The question the finding ends on — *is the backward assessment expected to be
    in UQMES, or run as a procedure outside it?* — was answered **in**, and the
    page deliberately stops short of acting on its own list: 7.1.5.2 requires the
    assessment, and the judgement belongs to a person.

    **One thing here is still true:** the exhibit is dark. All 13 seeded
    calibration records are PASS and the link only appears on a record that found
    the gauge unfit, so the page cannot be reached in a fresh demo. That is
    carried on the not-demonstrable list in the status key.

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

### ~~BUG (severe)~~ → FIXED — every CAPA dialog destroys itself as you type

> **Fixed; see *RE-CHECKED 2026-10-06 — the CAPA dialog focus bug is FIXED*
> below.** Re-confirmed 2026-10-15 by reading: none of the five dialogs is a
> component defined in a parent body any more — `CapaVerificationTab.tsx:258`
> holds `completeVerificationDialog` as plain JSX, and `RcaDialog`, `TaskDialog`
> and `CompleteDialog` no longer exist as identifiers anywhere in `src/`.

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

### ~~BUG~~ → FIXED — core lots appear in the QA inspector's home Receiving chip

> **Fixed; see *RE-CHECKED 2026-10-06 — core lots are excluded everywhere* below.**
> Re-confirmed 2026-10-15: `inspection_inbox.py:126` imports the shared
> `awaiting_inspection` helper from `incoming_inspection`, which carries the
> `holds_cores=False` exclusion, rather than keeping its own copy of the query.
> **A grep for `holds_cores` in `inspection_inbox.py` still returns nothing** —
> which is the fix working, not the bug persisting. Searching for the filter
> rather than the helper nearly re-filed this as live during the 2026-10-15
> read-through.

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

### ~~BUG (major)~~ → PARTIAL, CARRIED TO THE TRAINING ARC — the entire receiving-hold subsystem is dark in demo data

> **Re-checked 2026-10-19.** Partly lit: of 4 current part types, 1 now has `requires_supplier_qualification` and 1 `requires_heat_number`; `requires_part_approval` and `requires_coc` are armed on none, and on 0 of 3 materials. One lot is held (`RCV-MAT-HOLD`). The code was never at fault — this is seed coverage, and seed and training are one arc, so the remaining gates are armed there.

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

### ~~BUG~~ → FIXED — the "unqualified supplier" hold exhibit no longer holds

> **Re-checked 2026-10-19:** `RCV-MAT-HOLD` is `QUARANTINE` with `hold_reason = SUPPLIER_UNQUALIFIED`, matching Receiving row 5.

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

### ~~DRIFT~~ → FIXED IN HELP DOCS, CARRIED TO THE TRAINING ARC — the scan box takes more than the docs say

> **Re-checked 2026-10-19.** The help docs now say the box takes work orders, serials, lots and locations (`supply/locations.md`, `getting-started/navigation.md`). The narrower wording survives in `Documents/QA_INSPECTOR_TRAINING_SCRIPT.md` and its trainer-packet copy — training material, fixed in the arc.

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

### ~~OPEN (needs a decision)~~ → DECIDED AND FIXED — 33 more date-only display sites, 28 files

> **Re-checked 2026-10-19.** Swept in `3e4cba4` (*fix(ui): read date-only fields as local*, 35 files), and `TrackerCard.tsx` on 2026-10-19. The last site, `pages/quality/PcoDetailPage.tsx:119` (`ProcessChangeOrder.effective_date`, a `DateField`), was fixed the same day with `parseDateOnly`. The `ApprovalRequest.due_date` sites on the approvals, inbox and dashboard pages are correct — that field is a `DateTimeField`.

The same `new Date(<date-only field>)` shape survives in 33 places across 28
files: training dashboard and records, user detail, work orders, orders,
documents, home blocks. Each one displays a date a day early for any user west of
UTC.

Left unfixed deliberately — they are outside the files this work touched and other
sessions are active in several. **This is a decision for you, not a finding.** The
tidy fix is one `parseDateOnly` helper applied across the sweep, done as a single
opportunistic refactor in its own commit rather than piecemeal.

!!! note "Decided and delegated 2026-10-15 — this is no longer a question"
    **Do the sweep.** User decision; handed to the receiving/shipping session as
    a self-contained piece of work. Re-checked first: `parseISO` appears in only
    **7 files** across `src/`, which is the two fixed with the original bug plus
    a handful of others — not the 28 this finding names — so no sweep had
    happened.

    **"Display-only" was WRONG, and the sweep is what proved it.** I scoped this
    as cosmetic when delegating it — *"storage is correct everywhere, the seed is
    untouched"* — on the strength of the original bug, where `onSelect` did
    `format(date, "yyyy-MM-dd")` and the right value reached the API. **Two sites
    were display-and-write:**

    - **`OrderFormPage`** loaded `estimated_completion` with `new Date()` (UTC
      midnight = the previous evening, locally) and submitted
      `format(values.estimated_completion, "yyyy-MM-dd")`, which formats
      **local**. Opening an order and saving it *without touching the date* moved
      it back one day. Every save, for every user behind UTC.
    - **`EditWorkOrderFormPage`** had the identical round trip on
      `expected_completion`. Its submit side was already careful — a comment
      explains it must send a local date string rather than an ISO timestamp —
      so the care at one end was being undone at the other.

    **The general shape, worth keeping:** a date-only field is safe only if
    *both* ends agree. The parse is UTC and the format is local, so a form that
    merely round-trips a value it never edited still corrupts it. Checking the
    submit path alone — which is what made the original bug look cosmetic — sees
    nothing.

    **DONE 2026-10-15 — 45 sites across 33 files, 9 deliberately skipped,
    `bun run typecheck` clean.** Helper is `src/lib/date-only.ts`
    (`parseDateOnly`, wrapping `parseISO`), with the scope rule in its docstring
    so the next person does not apply it to an `_at` field. Uncommitted at time
    of writing.

    **The count was 45, not 33, and the raw grep was 301.** Neither number was
    trusted: every `new Date(<expr>)` site was extracted, the leaf field name
    taken, and each classified against `schema.yaml` by `format: date` vs
    `format: date-time`. **83 distinct leaf names, of which 7 are date-only.**
    That is the method this finding asked for — the distinction is the whole bug,
    and a grep-driven fix would have broken the 250-odd sites that were already
    right.

    !!! warning "`due_date` is a DateField on every model except one"
        All nine skips share a single cause: **`ApprovalRequest.due_date` is a
        `DateTimeField`** while every other model's `due_date` is a `DateField` —
        22 date-only against 3 date-time in the schema. So `approval.due_date` in
        `InboxPage` (×2), `ApprovalsHistoryPage` (×2), `ApprovalsOverviewPage`
        (×3), `DocumentsDashboardPage` and `QualityDashboardPage` is correctly
        out of scope. It was the **only** ambiguous field name in the codebase;
        everything else was uniform. Anyone reasoning about dates by field name
        will get `due_date` wrong, and only there.

    **The predicted sibling existed.** `CoreReceiveFormPage:72` defaulted
    `received_date` to `new Date().toISOString().split("T")[0]` — today's **UTC**
    date — so after ~8pm ET the receive form opened pre-filled with *tomorrow*.
    Exactly the `CapaVerificationTab` shape, found by looking for it. One more in
    `work-order-status-actions.tsx:78` fed a note a person reads back and was
    fixed too; `DefectAnalysisPage:253` only names a download file and was left.

Worth noting the general lesson, which is not specific to this codebase:
**`new Date("YYYY-MM-DD")` is UTC, `new Date("YYYY-MM-DDTHH:mm")` is local.** The
bug only ever appears for date-only fields, and only for users behind UTC — so it
is invisible to a UTC-based CI run and to every backend test.

### ~~BUG (demo data)~~ → FIXED — no failed calibration exists, so the recall page is dark

> **Fixed 2026-10-19** by `DemoQualitySeeder.seed_found_out_calibration`: a PASS calibration found out of tolerance and adjusted, on the Keyence Vision gauge, with GAUGE links to the reports in its window — the exposure list shows 9 reports and the gauge stays in service. QA Manager row 10 is Demo ✅.

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

### BUG → PARTIAL — `is_customer` and `is_supplier` both default to True, so neither means anything

> **Re-checked 2026-10-19.** The flags now **mean something** wherever they are set: order, receiving, qualification, part-approval, outside-process and core pickers all narrow by them (`admin/setup/companies.md`). What is unchanged is the **data**: all 8 demo companies are still both, internal org included, so the supplier scorecard still lists carriers and AMBAC Manufacturing. The defaults stay True by design (existing companies keep appearing until narrowed). Remaining: narrow the demo companies — training arc. **Decision (user, 2026-10-19): the internal org stays both customer and supplier**, so its scorecard and picker entries are by choice, not a defect.

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

!!! note "Re-scoped 2026-10-15 — cosmetic, and the proposed fix was the risky option"
    `models/core.py:1577-1578` are unchanged, but **the severity below is
    overstated and the remedy is worse than the symptom.** Established by
    enumerating every reader, after the user pushed back on it being a decision
    at all:

    **Almost every consumer is a dropdown filter.** `is_supplier: true` narrows
    the pickers in `ExpectedReceiptDialog`, `SendPartsOutDialog`,
    `EditMaterialFormPage`, `EditPartTypeFormPage`, `PartApprovalFormPage`,
    `SupplierQualificationFormPage` and `ReceiveLotsBatchPage`; `is_customer:
    true` narrows `ShippingPage`, `CoreLotsPage`, `OrderFormPage` and
    `CoreReceiveFormPage`. With the default `True` those lists are unnarrowed —
    a longer dropdown, not a wrong outcome. The only other surface is
    `SupplierQualityPage.tsx:131`, which is the eight-scorecard symptom described
    below.

    **The flags gate nothing today, and the three validations fail OPEN.**
    `shipping.py:194,206` (refuse to ship to a non-customer), `reman.py:58,61`
    (core source) and `stock_import.py:70` all raise on `not company.is_customer`
    / `not company.is_supplier`. With everything `True`, none of them ever fires.

    **That inverts the risk.** Setting the flags *correctly* is what introduces
    refusals — a behavioural backfill that misjudges one company breaks shipping
    to them. The permissive default is the safe state, and the "honest fix" below
    is the option with a downside.

    **So: not a decision owed.** If the cards are the annoyance, exclude the
    internal org in `SupplierQualityPage`, or set `is_supplier=False` on the two
    carriers in the seed. No model change, no migration, no backfill rule. This
    finding was listed beside the RCA question as a pending decision; it does not
    belong there.

~~**This needs your decision, because the fix is a data migration, not a default
flip.**~~ Changing the default to `False` is right going forward but silently
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

### ~~GAP~~ → BUILT — there is nowhere to record an NCR that *doesn't* become a CAPA

!!! success "Built to the shape this finding proposed, including the field names"
    Closed and documented. `services/qms/capa_decision.py` records
    **`NOT_REQUIRED`** and **`DEFERRED`** with a **mandatory** reason — *"Say why
    — the reason is what an auditor reads"* — cites ISO 9001 **10.2.1(b)**, and
    leaves undecided reports visible on the NCR page so an unevaluated backlog is
    countable. `PROMOTED` cannot be set by hand; it follows from the CAPA linking
    the report, so the decision and the link can never disagree.

    That is almost exactly the *"nullable `capa_decision` +
    `capa_decision_rationale`, set when a manager triages"* proposed below, which
    is the fields-over-tables default working. Documented in
    `workflows/quality/quality-reports.md`; QA Manager row 6 is green on both
    halves.

    **The paragraph below beginning "This matters more than it sounds" is the
    reason the feature exists** and is worth keeping for anyone asking why the
    reason field is mandatory.

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

### ~~OPEN (needs a decision)~~ → DECIDED AND BUILT — RCA has two verification paths; the guarded one is unreachable

!!! success "Option 1 was taken, the same day this was filed — `3ed193a`"
    Checked against the code 2026-10-15. **There is no longer a decision here**,
    and this entry sat as "needs a decision" for nine days after the work landed.

    `approve_rca` (`services/qms/rca.py:62`) is now four lines that delegate to
    `verify_root_cause`, and its docstring states the reversal: *"This used to
    set VERIFIED unconditionally on the assumption that the reviewer is a
    different person; nothing checked that, and `self_verified` was never set
    (2026-10-06)."* `review_rca` is gated declaratively —
    `action_permissions = {'approve_rca': ['review_rca']}` (`viewsets/qms.py:1207`).

    **Three of the four consequences below are now false:**

    | Claimed | Now |
    |---|---|
    | `verify_root_cause` is dead code no viewset reaches | `approve_rca` calls it; `/approve/` calls that |
    | `self_verified` is structurally always False | `rca.py:56` sets it from `is_self_verification` |
    | Nothing enforces reviewer ≠ conductor | the guard runs on the reachable path |
    | **No RCA approval UI at all** | **still true** — the only frontend call is `useCreateRcaRecord` |

    **The exploit recorded below is now a regression test.**
    `test_capa.py:964` posts to `/approve/` as the author and asserts **400**
    with the bare sentence (not Django's list repr — that was the sibling bug).
    Three more cover a different reviewer passing with `self_verified: False`,
    the author passing where the CAPA allows it with a justification that is
    **kept** rather than only checked, and a short justification refused.
    `perform_create` now defaults `conducted_by`, with a backfill that reads the
    author from the audit log and refuses to guess.

    **What genuinely remains is narrower and is a UI question:** there is still
    no approval affordance, so a correct control is reachable only by
    hand-written POST. Either it belongs on `CapaRcaTab` beside the create, or
    RCA review is meant to run through the approvals centre and `/approve/` is
    the machinery for that. Open, but not the independence question this entry
    poses.

    **Method note.** This was carried as one of three decisions owed for over a
    week because the entry said so and nobody re-read the code. The lesson the
    entry itself draws — *passing tests prove the code works, not that anyone can
    reach it* — has a twin: **an OPEN finding proves something was open once.**
    Re-check before quoting one.

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

### ~~BUG (major)~~ → DECIDED, NOT A BUG — `auto_now_add` silently discards every seeded step timestamp

!!! important "Overtaken by a user decision on 2026-10-07 — read this first"
    Re-checked 2026-10-15: `StepExecution.entered_at` is **still**
    `auto_now_add=True` (`models/mes_lite.py:1758`), and that is now deliberate.
    **The fix prescribed at the end of this finding was considered and
    refused.** The model carries the decision in its own comment:

    > *"Deliberately auto_now_add — NOT backdatable (user decision 2026-10-07).
    > It is traceability evidence: when the part really reached the step. Making
    > it writable would let any code path, and the serializers, rewrite execution
    > history. History from the ERP at go-live, if ever needed, goes through a
    > separate import path that marks rows as imported — this is why the earlier
    > go-live-history feature was removed."*

    So the finding's **diagnosis stands and its remedy does not.** The negative
    durations were real and the seed's timestamps are fiction, but the answer is
    *the seed must advance parts through the service* (see **Deferred: make the
    demo walk the flow instead of staging its outcome**), not *make the field
    writable*. Operator C3 records the same decision from the row side. Do not
    re-file this as a bug; the field is doing its job.

    The go-live paragraph below reads as an open question and is answered:
    the removal of the master-workbook go-live-history feature was for exactly
    this reason ([[master-workbook-decisions]]).

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

### ~~BUG (severe, compliance)~~ → FIXED — any operator can write training records, for anyone

> **Re-checked 2026-10-19:** the `operator` preset holds neither `add_trainingrecord` nor `change_trainingrecord` (`Tracker/presets.py`). The 403 was already verified in the follow-up entry below.

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

### ~~GAP (surface)~~ → BUILT — the qualification gate is sound, unprovable, and its evidence is invisible

> **Re-checked 2026-10-19.** The **exhibit** half is lit: **4** step executions carry a real override (others carry an authorisation snapshot without one), and Shift Lead row 5 is Demo ✅. **Surface built 2026-10-19 (uncommitted):** the part traveller (`Parts/{id}/traveler/`, via `lifecycle.override_summary`) carries `training_overrides` per step row, shown as an always-visible amber line under the step — worker, missing training, authoriser, time, reason. Walked on INJ-QA-INSPECT-001 → Nozzle Inspection. Docs: `work-orders/assigning.md`, `dwi/running.md`.

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

### ~~BUG (severe, compliance)~~ → FIXED — training was not alone: five more compliance records are operator-writable

> **Re-checked 2026-10-19:** the three real defects are closed — the `operator` preset holds none of `add_calibrationrecord`, `add_samplingruleset` / `add_samplingrule`, `add_lifelimitdefinition` (nor SPC baseline writes). Supplier qualifications and part approvals stay creatable, by design: they save **Pending** and only the `approve_*`-gated **Grant** gives them force.

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

### ~~GAP (data)~~ → FIXED — material traceability is half-dark: forward trace is empty everywhere

> **Re-checked 2026-10-19:** 66 `MaterialUsage` rows now exist, so forward trace has data to show. The broader lesson recorded below — *make the demo walk the flow instead of staging its outcome* — is training-arc work.

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

### ~~BUG (UX)~~ → FIXED — finishing the LAST part of a batch leaves the operator on a dead screen

> **Re-checked 2026-10-19:** `pages/operator/completion-adapters.tsx::advanceToNextQueuedPart` now treats an empty queue as the batch finished and leaves the step — to the work order, else operator home — instead of returning silently.

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

### ~~BUG (CRITICAL, verified)~~ → FIXED — any operator can forge a manager's e-signature, permanently

> **Re-checked 2026-10-19:** `ApprovalResponseViewSet` (`viewsets/core.py:2323`) is now a `ReadOnlyModelViewSet` — there is no create endpoint to forge through. Responses are written only by `submit-response`, which checks `approval.can_approve(request.user)` and signs as the requesting user. **The probe's forged response is still in the dev database** — responses are immutable, so neither DELETE nor archive can remove it (the request and CAPA were restored to PENDING). CAPA-2024-003's approval history therefore carries a response in the QA Manager's name that she never gave. A reseed clears it; until then, do not use CAPA-2024-003 as an approval exhibit in training.

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

### DRIFT (copy vs control) → STILL OPEN, CARRIED TO THE TRAINING ARC — "reuse / rework / scrap" is offered as Pass / Fail / Pending

> **Re-checked 2026-10-19 (`Substep.body_blocks`):** both **Component Grading → "Grade and sort components"** substeps still say *reuse / rework / scrap* and still carry only a `qualityStatusField`. The four-grade capture (`harvestedComponentCapture`) is now authored, but on a different substep. Seed authoring — fixed in the arc.

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

### GAP (data) → STILL OPEN, CARRIED TO THE TRAINING ARC — no shift notes exist, so row 11 is half-dark

> **Re-checked 2026-10-19:** `ShiftNote` has **0 rows**. Seed coverage — the arc writes one.

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

### ~~BUG (data + UI)~~ → DATA FIXED, FORM UNVERIFIED — the QA Inspector walkthrough's own disposition cannot be saved

> **Re-checked 2026-10-19:** `DISP-QAI-006-OPEN` now has **1** linked quality report, so the serializer's non-empty rule is met. Its `disposition_type` is still blank — the form-display issue noted below (the select showing *Rework* for a blank type) was not re-checked and needs a browser.

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

### PARTIAL → UNCHANGED, NEEDS A BROWSER — row 10's exhibit is poised correctly, but I could not confirm the queue

> **Not re-checked 2026-10-19:** resolving it needs expanding a grouped inbox row in the UI, which this pass did not do.

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

### ~~DRIFT (convention)~~ → FIXED — the disposition create/edit routes break the documented URL rule

> **Fixed 2026-10-19 (uncommitted):** now `/production/dispositions/new` and `/production/dispositions/$id/edit`, matching the list; the old paths redirect. The shared `legacyRedirect` helper also now carries the query string over (it dropped it), so `?partId=` survives — for every legacy redirect. All 9 callers updated, including the Report dialog. No help page named the old URLs.

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

### GAP (data) → STILL OPEN, CARRIED TO THE TRAINING ARC — the schedule has never been solved, so four rows cannot be walked

> **Re-checked 2026-10-19:** 0 `ScheduleResult` and 0 `ScheduledTask` rows in the dev database. A solve is a seed step — the arc runs it.

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

### CODE GAP → DECIDED AS-IS (substep only) — "void an operator's bad record" is narrower than the row assumes

> **Re-checked 2026-10-19:** `void_substepcompletion` is still the only `void_*` permission in `presets.py`. **Decision (user, 2026-10-19): substep completions only.** Measurements and quality reports get no void. A wrong one is corrected by a new record, and the pair is the evidence. NOT A GAP.

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

### GAP (data) → PARTIAL, CARRIED TO THE TRAINING ARC — the demo seeds only the post-arrival half of the receiving lifecycle

> **Re-checked 2026-10-19:** 3 lots are now `ON_ORDER`, so the expected half has a start. Whether they carry PO, promised date and a late one for the OTD story was not checked — arc work.

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

### ~~BUG (major)~~ → FIXED — a QA sign-off gate with no way to satisfy it

> **Re-checked 2026-10-19:** `services/qms/step_signoff.py` now writes the `QaApproval` the gate waits for, and the work order page's QA progress section opens it through `components/qa/QaSignOffDialog.tsx` — no longer only FPI pass/waive.

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

### OPEN QUESTION (product) → STILL OPEN — a temporary departure from the process has no home

> **Re-checked 2026-10-19:** no deviation-permit model exists; see *Post-audit rework — item 1*, still unbuilt.

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

### ~~BUG (major)~~ → FIXED — Report exception saves nothing

**Found 2026-10-19** by the code session while wiring `track_downtime`; it breaks
Shift Lead row **10**, which was marked ✅ on the 2026-10-07 walk.

**Symptom.** The **Report…** dialog (`pages/workorders/ReportExceptionDialog.tsx`)
offers **Downtime**, **Quarantine** and **CAPA**. Submitting one shows it in the
Exceptions list straight away — and it is gone on reload.

**Cause.** Both callers, `WorkOrderControlPage.reportWoException` and
`WorkOrdersControlCenterPage.reportException`, push the payload into React state
with a made-up `source_ref` (`DowntimeEvent/exc-<timestamp>`). Nothing is POSTed
for any of the three types. No UI anywhere calls `DowntimeEvents_create`.

**Why it matters.** A lead who reports a quarantine has quarantined nothing, and a
lead who escalates a record for retraction (row 10 → C2) has escalated nothing.
The draft appearing in the list is the most convincing possible false positive.

**What does work.** The Exceptions tab *lists* real records — `DowntimeEvents_list`,
quarantines and CAPAs from the API — and **Bulk resolve downtime** calls the real
`resolve` action. So rows **4** and **6** stand; only *raising* is broken.

**How the walk missed it.** The 2026-10-07 walk saw the item appear and recorded
the row. It proved the dialog renders and the list updates, not that anything
persisted — a reload would have caught it. Same lesson as *walk proves a path, not
an invariant*.

**Fixed and walked 2026-10-19 (uncommitted).** User decision: **Downtime**
now POSTs a real `DowntimeEvent` — equipment (types with *Track downtime* off are
left out), one of nine categories, a required reason (≤200), optional description,
and in the Control Center an optional work order; it starts now and is resolved
from the Exceptions list. **Quarantine** and **CAPA** no longer pretend to save:
each links to its form (`/dispositions/create`, `/quality/capas/new`) and offers
only Cancel. Severity and the free-text *Impacted WOs* field are gone. Server
refusal is tested. Walked as Tenant Admin on WO-SHOWCASE-01's control page and the
Control Center: 11 production machines offered and none of the 8 handheld /
torque / gauge items, *Record downtime* disabled until machine and reason are set,
the event survives a reload and **Resolve** clears it, and the DB row carries
equipment, category, work order, start, end, reporter and resolver. Both form
links land on their create pages. Walk residue deleted.

Help pages updated: `roles/operator.md`, `workflows/tracking/flagging-issues.md`,
`workflows/quality/quarantine.md`, `admin/setup/equipment.md`. **Still to update
when the training arc starts:** `training/operator.md`, `training/shift-lead.md`.

### ~~BUG~~ → FIXED — the work order page's Release skips release

**Found 2026-10-19** in the help-doc pass (`work-orders/progress.md`). Scheduler
row **2** had recorded the Control Center's **Release (N)** as the bypass; that
button now goes through `bulk_release` → `release_work_order` and is sound. This
one is the remaining bypass.

**Symptom.** `/workorder/$id` shows **Release** on a Pending work order.
`components/work-order-status-actions.tsx:109` — `handleRelease()` →
`updateStatus("IN_PROGRESS", "RELEASED")`, a plain PATCH of `workorder_status`
with a `[RELEASED - ts]` note prefix.

**Consequence.** It never reaches `services/mes/release.py::release_work_order`:
no readiness evaluation, no `released_at` / `released_by` / override reason, and
an unstarted job reads **In progress** — the exact regression `mark_started`'s
docstring (`services/mes/work_order.py:284`) says was fixed. The fix reached the
scheduling surfaces only.

Every other Release goes through the service: `useReleaseForScheduling`
(`CapacityPlanningPage`, `SchedulingGanttPage`, `PullInWorkDialog`) and the
Control Center's `useBulkRelease`. This button is the only one that does not.

**Fixed and walked 2026-10-19 (user approved; uncommitted).** The button now
calls `api_WorkOrders_release_create`: readiness check, `released_at` /
`released_by`, schedule marked stale, and no status change or notes stamp. A
refusal opens *Not ready to release* with the blockers and a required *Reason to
release anyway*. A released order shows **Un-release**. It appears whenever the
order is unreleased and not on hold (completed and cancelled orders render no
actions at all); permission unchanged (`change_workorder`). Walked as Tenant Admin
on both paths — WO-2024-0048-A blocked (*No units left to work*), released with an
override; WO-ASSESS-004 clean — status stayed Pending, `released_at` / `released_by`
and the reason were written, notes untouched, and Un-release flipped it back. Walk
residue reverted. The walk also removed a duplicate *Operation failed* toast that
`useReleaseForScheduling` / `useUnreleaseForScheduling` raised on every surface
sharing them.

### ~~BUG~~ → FIXED — the Remanufacturing dashboard's component links never loaded

**Found 2026-10-19** in the help-doc pass (`reman/components.md`); **fixed and walked
the same day** by the code session (user approved; uncommitted).

**First diagnosis, from reading:** `component_part__isnull` was not a declared filter
on `HarvestedComponentViewSet`, so *Pending Inventory Acceptance* would show the same
list as *Usable Components*.

**What a user actually saw:** both links showed *"Couldn't load harvested components.
Try refreshing."* — neither ever showed a list. Three layers:

1. **Server** — `component_part__isnull` undeclared (`viewsets/reman.py:680`).
2. **Router** — Link search values arrive JSON-quoted (`is_scrapped=%22false%22`);
   the page passed `'"false"'` to the zod client, which wants a boolean and refused
   before any request was sent.
3. **No metadata endpoint** for this viewset, so `ModelEditorPage` never converted
   the filters to booleans.

**Fix.** `filterset_fields` is a dict including `component_part: ['isnull']`
(schema regenerated); `ModelEditorPage` unwraps JSON-quoted URL values, which helps
every list page a router Link deep-links into; `HarvestedComponentsPage` converts
both filters to booleans. Walked: *Pending* → 5 rows, all Pending; *Usable* → 8 (5
pending + 3 in inventory, scrapped excluded). `test_reman` + the four guards, 128 OK.

**Lesson worth keeping:** the read-only diagnosis was right about the server and
wrong about the symptom. A deep link can fail on the client before the server is ever
asked — a reading of the viewset alone cannot see that.

### ~~GAP (config)~~ → BUILT — CAPA approval is not tiered by severity; the Critical and Major templates are never used

**Found 2026-10-19** in the help-doc pass, checking AS9100 8.1.1's claim of
"auto-escalation for critical". Affects QA Manager row **3** and Document
Controller row **4**, and four help pages that described severity tiers.

**What ships.** `services/defaults_service.py` seeds three CAPA templates:

| Template | Type | Approvers | Shape |
|---|---|---|---|
| CAPA Approval | `CAPA_APPROVAL` | QA Manager | parallel, 5 days, delegation optional |
| Major CAPA Approval | `CAPA_MAJOR` | QA Manager, Production Manager | parallel, all required, 5 days |
| Critical CAPA Approval | `CAPA_CRITICAL` | QA Manager → Production Manager → Tenant Admin | **sequential**, all required, **no delegation**, 3 days, escalates after 1 |

**What runs.** The `post_save` signal (`signals.py:285-289`) calls
`services/qms/capa.py::auto_request_capa_approval` for any new CAPA of severity
CRITICAL or MAJOR, and that looks up **`CAPA_APPROVAL` only** — its own template
description says *"Generic CAPA approval used by the post_save signal regardless of
severity"*. No code anywhere selects `CAPA_MAJOR` or `CAPA_CRITICAL`.

**Consequence.** A Critical CAPA is authorised by **one QA Manager**, exactly like a
Major one. The three-signature sequential chain the Critical template describes —
and the help docs promised — never happens, and editing that template has no
effect. If the template silently goes missing, `auto_request_capa_approval`
returns `None` and the CAPA proceeds with **no approval at all**.

**For an audit.** Do not cite severity-tiered authorisation as a control. What is
true: Major and Critical CAPAs require a management approval before work, signed
with re-authentication, and self-approval is refused by the template.

**Also seen:** the dev demo tenant carries no `CAPA_CRITICAL`, `PROCESS_APPROVAL` or
`TRAINING_CERT` template at all (current types: CAPA_APPROVAL, CAPA_MAJOR,
DOCUMENT_RELEASE, PCN_RELEASE, PCO_APPROVAL, PCR_APPROVAL). A missing
`PROCESS_APPROVAL` refuses every process submission in demo — worth checking
against the Engineering rows.

**Built 2026-10-19 (user confirmed; uncommitted).** `services/qms/capa.py::
capa_approval_template` picks `CAPA_CRITICAL` / `CAPA_MAJOR` by severity, each
falling back to `CAPA_APPROVAL` when the tenant has no current template of its own
type; Minor and others use `CAPA_APPROVAL`. Both the automatic request at creation
and the manual *request approval* use it. **No CAPA template at all** is, per the
user, a deliberate configuration: an automatically raised Critical or Major CAPA
proceeds without approval and the server logs a WARNING (nothing shown to a user);
a manual request refuses — *"No CAPA approval template is configured. Add one in
approval templates."* Completion is keyed on the CAPA, so approve/reject behave as
before. `CAPASeverityTemplateTests` (5) + signals + approval tests + the four
guards, 90 OK. **Demo:** has `CAPA_MAJOR` but no `CAPA_CRITICAL`, so new Critical
CAPAs fall back to `CAPA_APPROVAL` there (seed left untouched by user decision). Help pages now describe the real behaviour: `roles/index.md`,
`admin/setup/approval-templates.md`, `roles/administrator.md`, `roles/qa-manager.md`.

### ~~GAP~~ → BUILT — a special-process qualification is recorded but never checked at send-out

**Found 2026-10-19** in the help-doc pass (`compliance/as9100.md`, 8.5.1.2).
`SupplierQualification` supports `scope_type = SPECIAL_PROCESS` with a
`scope_label` (e.g. *Heat treat*, basis *Nadcap*), and
`services/qms/supplier_qualification.py::is_supplier_qualified` accepts a
`special_process` argument. The only caller passing it is the status query at
`viewsets/qms.py:403`. **Outside-processing send-out does not call it**, so parts
can be dispatched to a vendor for plating or heat treat with no qualification for
that process on record — the case AS9100 8.4 / 8.5.1.2 and Nadcap customers care
about most. Part-type and commodity scopes, by contrast, **are** enforced at
receiving.

**Built and walked 2026-10-19 (uncommitted).** New step field
`Steps.outside_special_process` (free text, blank by default, migration 0235), in
the process editor's outside-process section under *Default vendor*. When set,
`send_parts_out` refuses unless the vendor holds an active (APPROVED / CONDITIONAL,
in date) SPECIAL_PROCESS qualification with the same label, case-insensitive:
*"<Vendor> has no active qualification for <process>. Qualify them for it, or send
the parts to a vendor who is."* It **refuses rather than holds**, unlike receiving —
once parts have gone, the work is already being done. Blank checks nothing, so
existing steps and the demo are unchanged. Walked on the showcase draft's Nitride
Coating → Apex Plating Co with *Nitriding* set: refused, nothing moved; restored to
blank. `test_outside_process` (6 new) + versioning tests + the four guards, 97 OK.

**Found and fixed alongside:** the step's **Turnaround (calendar days)** never
saved (`ProcessFlowPage` did not load or send `outside_process_lead_days`), and the
outside-process section showed only on RECEIVING-type steps although any flagged
step sends out — so the demo's Nitride Coating (a TASK) showed no vendor,
turnaround or toggle at all. Both fixed. Docs: `admin/processes/steps.md` gained an
*Outside processing* section; `compliance/as9100.md` 8.5.1.2 updated.

### BUG — the Control Center's bulk "Change status" writes any status, with no rules

**Found 2026-10-19** while tracing why `WAITING_FOR_OPERATOR` exists.

**Symptom.** The WO Control Center's bulk bar opens *"Change status for N WOs"*,
offering Pending, In progress, Waiting for operator, On hold, Completed and
Cancelled. It calls `services/mes/work_order.py::bulk_transition` (endpoint
`bulk_transition`, `viewsets/mes_lite.py:2962`), whose docstring says *"no legality
gate"* — it writes the chosen status onto every selected work order.

**Consequence.** Each target undoes a rule the product enforces elsewhere:
**Completed** with parts still in progress, skipping the completion date and the
order-completion cascade that follow from parts ending; **In progress** with no work
started, the regression the Release fix closed; **On hold** with no reason, which the
single-WO hold requires; and reopening a Completed or Cancelled work order. The
proper bulk actions — release, hold with reason, clear hold — sit beside it on the
same bar.

**Decision (user, 2026-10-19): remove the dialog.** The endpoint's only caller is
this dialog (`useBulkTransitionWorkOrders`). **→ FIXED 2026-10-19:** the dialog, its
bulk-bar button, `POST /api/WorkOrders/bulk_transition/`, `bulk_transition` and the
hook are gone. Release (N), Hold, Clear hold, Report, Add parts and Split remain.

**Still open, the same shape on one work order:** a plain PATCH of
`workorder_status` writes any status. The WO page's Hold / Resume / Cancel use it, so
the buttons are the only thing keeping it legal — the API does not. Filed below as
**Single-WO status PATCH has no legality gate**.

### ~~GAP~~ → FIXED — single-WO status PATCH has no legality gate

> **→ FIXED 2026-10-19** (code session; uncommitted).
> - **The gate:** PATCH or PUT of `workorder_status` on an existing WO is refused
>   with a 400 naming the action to use (`services/mes/work_order.manual_status_refusal`).
>   Create is not gated, and an unchanged status still saves.
> - **The WO page's buttons:** Hold, Resume and Cancel now call `place_on_hold`
>   (with the shared hold reasons), `clear_hold` and the new `cancel_work_order`.
>   Hold is now offered on Pending too, and the edit form's Status is locked.
> - **Found and fixed on the way:**
>   - Clearing a hold, single or bulk, left the WO at ON_HOLD forever. It now
>     returns to In progress if work has started, else to Pending.
>   - Cancel skipped the order-completion cascade; it now runs it.
>   - Single hold and clear-hold fell back to `add_workorder`; they are now gated
>     on `change_workorder`.
>
> Docs: `work-orders/progress.md`, `basics.md`.
>
> **Still open, filed below:** the bulk hold and clear-hold still fall back to
> `add_workorder`.

### ~~GAP~~ → FIXED 2026-10-19 — bulk hold and clear-hold fall back to `add_workorder`

> **Fixed:** `bulk_place_on_hold` and `bulk_clear_hold` are gated on
> `change_workorder`, with 3 tests checking an add-only role gets 403. The WO page's
> Release, Un-release, Hold and Resume, and the bulk bar's Release, Hold and Clear
> hold, are hidden without the permission. Every staff group holds
> `change_workorder` by default, so the fix matters only for custom groups.

**Found 2026-10-19** by the code session. The single-WO hold and clear-hold are gated
on `change_workorder`. The Control Center's bulk **Hold** and **Clear hold** still fall
back to `add_workorder`, which every staff role holds by default, so any role can
hold or release a selection of work orders that it could not hold one at a time. Size
**XS**: add both to the viewset's `action_permissions`.

**Found 2026-10-19** by the code session while removing `bulk_transition`, whose
docstring said it *"matches single-WO behavior (no legality gate)"*. `PATCH
/api/WorkOrders/{id}/` accepts any `workorder_status`, so every consequence listed
above for the bulk dialog — Completed with parts in progress, In progress with no
work started, On hold with no reason, reopening a closed work order — is still
reachable one work order at a time through the API. The UI's buttons only offer legal
moves. **Decision (user, 2026-10-19): gate it to the legal moves**: the set the WO page's Hold / Resume / Cancel define. Derived statuses (In progress, Completed, auto-Cancelled) can't be set by hand. **Handed to the code session.**

### ~~BUG (moderate, security)~~ → FIXED — the audit log shows every record's changes to every staff role, password hashes included

**Found 2026-10-19** while checking what `export_auditlog` gates (it gates nothing).

> **→ FIXED 2026-10-19** (code session; uncommitted, not yet browser-walked).
> - **Row visibility follows the record:** `services/core/audit_visibility.visible_entries`
>   keeps an entry only if the reader can open its record through that model's
>   `for_user()`. Classification and export control therefore apply.
> - **Browsing is gated:** listing without `content_type` + `object_pk` needs
>   `view_auditlog`. That permission moved off the staff base onto Tenant Admin, QA
>   Manager, Document Controller and Auditor (the user's choice).
> - **Per-record history is filtered:** it still needs only `view_logentry`, but
>   shows only records the reader can open, and a hidden single entry returns 404.
> - **Credentials are excluded:** `AUDITLOG_EXCLUDE_TRACKING_FIELDS` covers
>   password, the IntegrationConfig secrets (which auditlog would have logged
>   *decrypted*), invitation and unsubscribe tokens. Existing rows are masked on
>   read, not rewritten.
> - **Not changed:** `export_auditlog` is still checked nowhere, so the last-mile row
>   stands.
>
> Docs updated: `analysis/audit-trail.md`, `compliance/audit-trails.md`,
> `admin/users/permissions.md`, `admin/data/data-management.md`, `navigation.md`,
> `roles/auditor.md`.

**Severity, as weighed with the user.** A pbkdf2 hash cannot be used to sign in and is
slow to guess against; the real risk is offline guessing of *weak* passwords by an
insider, so it is **moderate**, not severe. The larger problem is the row-filtering
bypass below — the hash is only its most vivid instance. Nobody has a legitimate use
for a credential hash in an audit log, which is why stopping it is still worth doing.

**Where it shows in the UI, not only the API.** **Admin > Audit Log** is in the sidebar
for anyone holding `view_auditlog` or `view_logentry` (`app-sidebar.tsx:182`) — every
staff role by default — and its change renderer (`HistoryPage.tsx:206`) skips only
`id`, timestamps, `created_by`, `version` and a few relation fields, so a password change
reads *password: <old hash> → <new hash>*. The **History** card on a user's edit form
(`EditUserFormPage.tsx:580` → `RecordHistoryCard`, via `services/core/audit_display.py`,
whose `BOILERPLATE` set does not include `password` either) shows the same.

**The mechanism.** `AUDITLOG_INCLUDE_ALL_MODELS = True` (`settings.py:624`) audits every
model, including `User`, and nothing masks fields — so a password change is logged with
the `password` field's old and new **hash** in `changes`. `GET /api/auditlog/`
(`LogEntryViewSet`, `viewsets/core.py:1876`, a plain `ReadOnlyModelViewSet`) returns
the raw `changes` for every entry whose actor belongs to the tenant, gated only by
`view_logentry` — held by every staff role by default. `AuditLogSerializer` and
`services/core/audit_display` mask nothing.

**Proven 2026-10-19, rolled back.** As `mike.ops` (Operator), `POST
/auth/password/change/`; then as `dave.wilson` (another Operator) read the audit log
for Mike's user record: one entry, carrying the new `pbkdf2_sha256` hash. Run inside a
transaction with `set_rollback(True)`; Mike's password verified unchanged afterwards.

**Scope.** Live wherever a signed-in user changes a password (actor = that user, so the
entry is tenant-visible). The 18 password-bearing entries already in the dev database
were written with no actor (by the seed) and are visible to superusers only. Signup and
reset-by-link run anonymously and are likewise actor-less.

**The same hole, wider.** The endpoint applies **no** row filtering beyond the actor's
tenant — not `for_user()`, not document classification, not export control. So the
field-level changes of any record are readable by anyone with `view_logentry`,
including records that user cannot open: Secret-tier document metadata, export-controlled
part data, other users' emails and flags. Not demonstrated on documents (the dev
database has no Secret documents); true by construction.

**Related:** `export_auditlog` is defined and granted (Tenant Admin, Document
Controller) but checked nowhere, and the audit log screen has export turned off — see
the last-mile row.

**Status: handed to the code session 2026-10-19, with the user's framing.** In order:
(1) **filter entries by whether the reader may see the underlying record** — the
bypass is the main problem; (2) gate the endpoint and the sidebar link on a specific
permission rather than `view_logentry`; (3) **stop logging credential fields going
forward** (`password`, and any token or secret fields). **Leave the existing audit rows
alone** — per the framing agreed with the user, the stored hashes are not worth an
exception to audit immutability.

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

### ~~GAP (authoring)~~ → FIXED — the three reman capture nodes exist but no process uses them

> **Re-checked 2026-10-19 (`Substep.body_blocks`):** `harvestedComponentCapture`, `componentInstallCapture` and `rebuildFindingCapture` are each authored on a seeded substep.

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

## The other half of the pattern — capability built to the edge of visibility, then stopped

**Recorded 2026-10-16, from the help-doc pass.** The section above records
capability that is *finished and unmentioned*. This records its inverse:
capability where the model, the capture and the service logic are done and the
thing that would make it visible to a person was never built. Nothing here is
broken. Each one is a last mile.

**These were found by writing from the code, which the note above says finds
nothing.** That claim needs narrowing rather than retracting: *walking a role*
finds work that is finished but undocumented, because only a walk shows you a
surface nobody wrote about. *Writing a doc page from the code* finds this class
instead, because a help page forces the question nobody asks while building —
**"and then where do you go to look at it?"** There is no way to write
"Viewing life status" and not discover there is nowhere to view it. The two
methods find disjoint sets; neither substitutes for the other.

### Captured but never analysed

| Item | Built | Missing |
|---|---|---|
| ~~**Downtime**~~ → BUILT 2026-10-19 — **Downtime** card on Analytics, `GET /api/DowntimeEvents/summary/` (`services/mes/downtime.downtime_summary`): hours lost and counts by cause and by machine, open events counted to now, share of calendar time. Still no OEE or availability — by design. **As found:** `models/mes_standard.py:1165` | `DowntimeEvent` with nine categories (the Six Big Losses shape: planned, unplanned, changeover, calibration, no work, no operator, material, quality, other), FKs to equipment / work centre / work order, reporter and resolver, `duration`. Raised from the work order **Report…** dialog (it saved nothing until 2026-10-19 — see **Report exception saves nothing** below). Open events show on the WO control pages and operator home. Composite indexes on `(equipment, start_time)`, `(work_center, start_time)`, `(category, start_time)` | Any rollup. No OEE, no availability %, no Pareto, no per-machine downtime list. Its own docstring says it exists for OEE. **The indexes are built for a query nobody wrote** |
| ~~**Part-type quality rollup**~~ → BUILT (already) — `quality-summary` action on the PartTypes viewset | Inspection pass/fail, FPY, open dispositions and CAPAs, defect Pareto, recent failures, 30-day yield trend — honouring `qs_for_user` | **Mis-filed: it was already drawn.** `PartTypeQualityRenderer` (via `usePartTypeQualitySummary`) is the right-hand panel of `/details/PartTypes/$id`, reached by **View** on the part types list. A grep for `quality-summary` misses it because the hook calls the generated alias. Only the help page was wrong; fixed 2026-10-19 |
| ~~**Sampling decision log**~~ → BUILT 2026-10-19 (per part) — `GET /api/Parts/{id}/sampling-decisions/`, shown as **Sampling decisions** in a part's history on the WO control page. No cross-part or per-ruleset list. **As found:** `models/mes_standard.py:827`, written at `services/mes/sampling_applier.py:153` | Every selection *and* skip, with part, rule, decision, ruleset type, timestamp. The skips are what answer an auditor's "why was that one not inspected?" **Attribution → FIXED 2026-10-19** (migration 0238): an exclusion is logged against the rule that excluded; a part no rule selected has `rule = NULL` and names the `ruleset` — it used to be credited to the first rule | **No surface — confirmed 2026-10-19:** no viewset, no frontend reader; the only reader is a debug dict at `models/mes_lite.py:3870`. **STILL OPEN.** `sampling-rules.md` now says no screen shows it |
| ~~**Repeat defects**~~ → BUILT 2026-10-19 — **Repeat defects** card on NCR Analysis, defects on 3+ failed reports in the page's range; response now typed in the schema. **As found:** `/api/dashboard/repeat-defects/` (`viewsets/dashboard.py:1138`) | The same error recurring on the same part type — the classic CAPA candidate list — computed server-side | Any UI. Not called by any page or hook (checked by URL and by generated alias `api_dashboard_repeat_defects_retrieve`). Its siblings on the same viewset — NCR trend, aging, disposition breakdown, defects by process — all render on NCR Analysis or Defect Analysis. Size **S**: a card on NCR Analysis |

### Flags recorded that nothing reads

| Item | Note |
|---|---|
| **`can_make`** on PartTypes | **User, 2026-10-19:** intended for the scheduler's make-or-buy distinction — a type the shop *could* make but would rather buy (shims). Not wired; no decision on how. Editable on the part-type form (`EditPartTypeFormPage.tsx:244`), zero readers in backend or frontend. `can_buy` by contrast gates BOM BUY lines and expected-receipt import |
| **`export_auditlog`** permission | Defined on the model and held by Tenant Admin and Document Controller by default, but **checked nowhere**: the audit log screen has `disableExport={true}`, and `GET /api/auditlog/` is gated by `view_auditlog` (browsing) and `view_logentry` (one record's history) since 2026-10-19. So it controls nothing, and the docs had cited it as the gate on extracting the audit trail. **Decision (user, 2026-10-19): leave as is.** It is reserved for a future CSV export of the audit log, which would be gated on it; until then it stays defined, granted and inert. Origin: `bb9a749` (2026-02-24), documented as *"Export audit data for auditors"*. NOT A GAP |
| **`is_portable`** on EquipmentType | Seeded into demo, no readers. **User, 2026-10-19: leave it, documented as inert** |
| ~~**`track_downtime`** on EquipmentType~~ → BUILT 2026-10-19 | `DowntimeEventSerializer.validate_equipment` refuses equipment whose type has it off (`services/mes/downtime.py`); untyped equipment is allowed. The rebuilt **Report…** dialog leaves those machines out of its picker. When this was first filed, the dialog had no equipment picker and **saved nothing** — both handlers (`WorkOrderControlPage.reportWoException`, `WorkOrdersControlCenterPage.reportException`) only push a draft into React state, so a reported downtime, quarantine or CAPA is gone on reload. No UI calls `DowntimeEvents_create`. That is a bigger gap than this row, filed below |

### Built, with no way in

| Item | Note |
|---|---|
| **Life tracking, entirely** | Limit definitions, accumulation, status calculation, shelf life, limit overrides and resets-with-history all work server-side. There is no screen anywhere — not on part detail, not as a list of parts near their limits. Overrides and resets are API-only and gated to QA/Engineering |
| **Life-limit `required`** | Recorded; nothing creates a tracking record from it, and nothing refuses a part missing one. Already noted in `life-tracking.md` before this pass |
| ~~**RCA approval paths**~~ → BUILT 2026-10-19 — **Approve** on each RCA card in `CapaRcaTab` for `review_rca` holders. It refuses the conductor unless self-verification is allowed, and then notes are required. submit-for-review now sets REQUIRED; approval sets COMPLETED; the dead pencil is removed. **Gate built:** `CAPA.rca_verified()` is required for → Pending Verification *and* in `verify_capa_effectiveness`, which had not checked status and could close from In progress. `rca_complete()` rejects a blank summary. All 4 demo CAPAs past In progress already had verified RCAs. Docs: `capa/overview.md`, `capa/verification.md`, `roles/qa-manager.md`. **As found:** **Re-verified 2026-10-19.** `POST /api/RcaRecords/{id}/approve/` works, gated by `review_rca` (QA Manager, Tenant Admin by default), under the independence rule. No UI: only create is wired, and each RCA card's pencil button has no handler. Also found: `submit-for-review` writes `'PENDING'`, not a `RcaReviewStatus` choice; approval never sets `COMPLETED`, so an RCA flagged REQUIRED by a *Not effective* check stays REQUIRED; and nothing downstream needs a VERIFIED RCA — the CAPA's move to Pending Verification checks only that `root_cause_summary` is not None. **Decision (user, 2026-10-19): verify, then build.** The UI and the two status bugs were handed to the code session. **Gate decided (user, 2026-10-19: "match the standard"):** per 8D D4 / ISO 9001 10.2.1(b), a VERIFIED RCA is required before Pending Verification, and an empty `root_cause_summary` no longer counts as complete. Containment and tasks are not gated. Handed to the code session |
| ~~**Delivery-date slip**~~ → BUILT 2026-10-19 — `original_completion_date` is now a DateField (0241), stamped once by `services/mes/orders.note_completion_change` from all three writers (order edit and CSV, HubSpot sync, WO cascade). System-driven moves count. The seed writes none, so demo shows no slips. **As found:** `Orders.original_completion_date` | The order detail page shows *Originally <date>*, struck through, when the delivery date has moved (`OrderDetailsPage.tsx:312-381`), and the generic detail config lists the field. **Nothing in the product ever writes it** — not the order form, not a service, not the HubSpot sync; the seed sets it to `None`. So a slipped date is never captured and the line can never appear. Size **S**, but two parts: stamp it from a service on the first change to `estimated_completion` (not in `save()`), **and** make it a `DateField` — it is a `DateTimeField` against a `DateField`, compared by exact millisecond at line 313, so once written it would read as *changed* on every order west of UTC |
| ~~**Calibration exposure**~~ → BUILT (seed) | QA Manager row 10 flipped to Demo ✅ 2026-10-19 — see that row |
| ~~**Report exception saves nothing**~~ → BUILT 2026-10-19 — `pages/workorders/ReportExceptionDialog.tsx` | **Fixed:** Downtime now POSTs a real `DowntimeEvent` (equipment filtered by `track_downtime`, category, reason, optional WO; starts now, resolved from the exceptions list). Quarantine and CAPA link to `/dispositions/create` and `/quality/capas/new` instead of faking a draft; the draft state is gone from both callers. **As found:** The dialog offers Downtime / Quarantine / CAPA and both callers keep the result as a client-side draft (`source_ref` `DowntimeEvent/exc-<timestamp>`, a fake id). Nothing is POSTed. Downtime can only be recorded through the API. The 'Captured but never analysed' downtime row above overstated the capture side |

### Found later in the pass (2026-10-19)

| Item | Note |
|---|---|
| ~~**QA panel annotates on the first model by name**~~ → FIXED 2026-10-19 — now prefers a COMPLETED model with no step, then any COMPLETED one; none completed → no 3D tab. **As found:** `components/qa-right-panel.tsx:22-43` | Fetches the part type's 3D models with `limit: 1` under the viewset's `ordering = ['name']`, so it uses whichever sorts first — including one still converting or failed, or one tied to a single step. Size **XS**: filter to completed, prefer a model with no step |
| **`WaitingForOperator` is never set** — `WorkOrderStatus.WAITING_FOR_OPERATOR` | **Legacy.** In the original status set (`7211e68`, 2025-07-27) and ticked *DONE* on `WO_MANAGEMENT_FEATURE_MATRIX.md` 1.2.5 because the enum existed; nothing in the repo's history ever set it automatically — only the bulk *Change status* dialog could, by hand. Its meaning is now carried by Dispatch's *uncovered* and by *In progress* = work began. **Decision (user, 2026-10-19): remove it.** 0 work orders hold it. **→ REMOVED 2026-10-19** (migration 0237); the lot gate now accepts Pending / In progress. `basics.md` and `progress.md` updated |
| ~~**Removing parts from an order is API-only**~~ → BUILT 2026-10-19 — **Parts on this order** card (staff, `change_orders`) with **Remove from order (N)**, through the audited `services/mes/orders.remove_parts_from_order`; the endpoint is now gated on `change_orders`. **Still orphaned:** bulk-add (endpoint and hook, gated on `add_orders`). **As found:** `Orders.parts/bulk-remove` | `useRemovePartsMutation` exists; no component calls it. Clears the order link only, leaving the work order. **Bigger than filed (code session, 2026-10-19):** the order page shows part **counts only** — no screen lists an order's parts — and the add-parts hook is orphaned too. The endpoint uses `.update(order=None)`, which skips auditlog, and it falls back to `add_orders`. Proposed: an audited service gated on `change_orders`, plus a staff-only Parts card on the order page. Size **S–M**; scope with the user |

### Seeded into inertness

| Item | Note |
|---|---|
| ~~**Document review**~~ → BUILT 2026-10-19 (review only; the user chose no retention default) — SOP, WI, POL, CP carry `default_review_period_days: 365` in `DOCUMENT_TYPES`. Not pushed to existing tenants: `seed_document_types(update_existing=True)` setattrs every key (name, description too) and saves in place, bypassing `create_new_version` | A **new organisation** gets all 39 types from `DOCUMENT_TYPES` in `services/defaults_service.py` (via the `seed_tenant_defaults` signal), and none of those dicts carries `default_review_period_days` or `default_retention_days` — so the review queue works and stays empty until someone sets a period. **The demo tenant is not like this:** it has only 4 types (WI, RCA, PO, DWG) from the demo seed, all at 365-day review / 2555-day retention, so the queue *does* fill in demo. That difference hides the gap from anyone evaluating on the demo. The cheapest fix in this list — add the two keys to the authored types (SOP, WI, CP, POL) in `DOCUMENT_TYPES` |

### Reading it

The spread in cost is wide and worth separating. A downtime Pareto and a
quality-summary page are small — the queries exist and the work is a route and a
chart. Review periods are a seed edit. A life tracking screen is a real build.

**Scope:** sixteen items from the full help-doc pass (every page outside
`training/`, completed 2026-10-19). Five are built and two are decided as-is; the rest are listed with sizes
for the user to prioritise.

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

### ~~BUG~~ → FIXED — every bulk part action silently no-ops: string ids vs UUID keys

> **Fixed, and it was never marked here.** `services/mes/parts.py:769` now reads
> `return {str(p.id): p for p in qs}` — the one-place fix proposed below, so all
> three bulk actions are indifferent to whether a caller passes a string or a
> UUID. Confirmed 2026-10-15 by reading the helper, and independently by Operator
> C1's re-walk the same day, which drove **Quarantine** on two selected parts and
> saw both land in the database while the unselected one did not move.

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
**— CLOSED by the reseed; struck 2026-10-15.**

~~| cores in demo | 8 | · | `fulfilment_mode == 'REPAIR_RETURN'` | **0** | · |
`returns_to_customer` | **False for all 8** |~~

`return_to_customer` refuses an exchange unit by design — *"it is an exchange unit — it
has no owner to go back to"* — which was, at the time, a second block on Shipping R1.
**`seed/demo/reman.py:230` now seeds `CORE-240210-0007`**, a Midwest Fleet warranty
unit with `fulfilment_mode='REPAIR_RETURN'` and `returns_to_customer=True`, carrying a
bench finding that routes it down the Nozzle Recondition branch. The repair-and-return
path has a representative unit; Shipping R1 records what it still waits on, which is
that unit reaching REBUILT — **not** the absence of a subject.

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

~~**Still outstanding — the demo half**, which belongs with rework item 2:
seed at least one `REPAIR_RETURN` core (all 8 are EXCHANGE, so the whole
repair-and-return ending is still unrepresented and **Shipping R1 stays blocked**), and
stop seeding cores into `DISASSEMBLED` off a work order.~~

**Half done — corrected 2026-10-15.** The `REPAIR_RETURN` core was seeded
(`CORE-240210-0007`, `seed/demo/reman.py:230`), so that clause is closed and
Shipping R1 is no longer blocked on a missing subject. **Still outstanding:**
stop seeding cores into `DISASSEMBLED` off a work order — the staged outcome
still sits where the mechanism cannot run.

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

## Post-audit rework — item 1: deviation permits and conditional spec → BUILT as temporary process changes

**Flagged by the user 2026-10-07 as the first large piece of rework to follow this
audit.** Not a bug, not a documentation gap — a missing concept with a real UX
consequence.

> **Decision (user, 2026-10-19): a deviation is a temporary process revision**, so it
> is supported through change control rather than as a permit model. The details:
> - **Scope:** it applies to **named work orders only**. The revised version is
>   approved, and those WOs move onto it through the existing *migrate selected* path.
>   The baseline stays current for new work. The WOs' parts bound the quantity.
> - **Ending:** it ends when its WOs finish, with an **expiry date** as a backstop.
>   After the date, the deviated work can't proceed until the change is extended
>   through change control or the WO moves back to the baseline.
> - **Customer agreement:** recorded on the PCR through the existing *Customer
>   notification required* flag and its text or attachment.
>
> Today, implementing a PCO always makes the new version current and retires the
> predecessor (`services/mes/processes.py:60-77`). That is the piece to change.
> **→ BUILT 2026-10-19** (migration 0240; uncommitted, not browser-walked).
> - **Fields:** `is_temporary`, `temporary_until`, `extends_request` and
>   `customer_agreement` on the PCR; `is_temporary` and `temporary_until` on
>   Processes.
> - **Implementing:** a temporary change approves without becoming current and is
>   MIGRATE_SELECTED only.
> - **Expiry:** starting a step is refused once the date passes, with no supervisor
>   override.
> - **Ways on:** an extension is a new PCR; *Move back to baseline* works per work
>   order.
> - **Versioning:** history, rebase, sibling detection and propose all exclude
>   temporary versions, and a WO can't be pointed at one by hand.
> - **Left as is:** version numbering — a temporary version still takes v(n+1), so a
>   later permanent change can share its number; the labels say *temporary*. **Accepted
>   (user, 2026-10-19):** a version number is for reference, not a record of
>   lineage.
>
> Docs: `change-control/overview.md` (new section), `iatf-16949.md` 8.5.6.1.1,
> `quality/dispositions.md`. The runtime problem below — a reading against a
> permitted value raising an NCR — is gone, because the named WOs run a version whose
> spec *is* the permitted value.

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
