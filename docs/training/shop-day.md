# The Shop Day

One working day at a fictional shop, written out in full. Every role in uqmes
has its moments in it, and the moments connect: the hold one person places is
the hold the next person works around.

!!! info "What this document is for"
    Three things, in this order.

    1. **The specification the demo seed is built to.** The day is designed from
       what the roles actually do, and the seed is built to produce it — not the
       other way round. Where the seed does not yet produce a passage below, the
       seed is incomplete, not the day.
    2. **The spine of every training track.** A role's track is its slice of
       this day. That is what makes the tracks compose: a Shift Lead and a
       Planner taking their own tracks are working the same Tuesday.
    3. **A demonstration script.** Walked end to end, it shows a shop running —
       which is the thing another facility needs to see before it can picture
       its own.

!!! warning "Portable by construction"
    The shop makes a generic product and is named after nobody. No customer,
    supplier, part number or process here refers to a real company. A facility
    adopting uqmes should be able to read this and substitute its own work
    without hitting anything that only makes sense somewhere else.

## The shop

**Meridian Works** rebuilds and builds hydraulic pumps. It runs two overlapping
shifts, takes customer units in for repair as well as building to stock, and
buys components from three suppliers. It is small enough that people hold more
than one role, which is normal and is why the tracks compose.

### The cast

| Person | Role | Why they are here |
|--------|------|-------------------|
| Dana Okonjo | Planner | Decides what the shop takes on and when |
| Marcus Reyes | Production Manager | Owns orders and work orders |
| Priya Shah | Shift Lead | Runs the floor, makes the calls an operator can't |
| Tom Alvarez | Operator | Runs the work |
| Jess Lindqvist | QA Inspector | Inspects, buys off first pieces, dispositions |
| Ruth Delacroix | QA Manager | Authority on quality decisions, closes CAPAs |
| Sam Oyelaran | Engineering | Writes processes, routings, specs, limits |
| Nina Brandt | Purchasing | Owns suppliers and what the shop is waiting on |
| Ade Fashola | Receiving | The dock |
| Chen Wei | Shipping | The other end of the building |
| Iris Vogel | Document Controller | Controlled documents and their revisions |
| Karim Haddad | Tenant Admin | Users, groups, notification rules |

Plus an **Auditor** doing a surveillance visit, who only reads, and a
**customer contact** at Harborline Marine watching their own repair — who does
not only read: a customer can respond to an approval request raised to them, and
can invite another viewer onto their own order.

## The day

### 06:00 — Dana reads the board

The overnight solve is stale. The board tells her that and nothing more — the
schedule carries a single *stale* flag with no cause on it, so whether the plan
drifted or simply ran out of its window is hers to work out from the dates.

She re-solves. The solve fails because no certified, rostered operator can run a
gated step at all. That is a staffing and training problem wearing a scheduling
costume, and no amount of re-solving fixes it.

!!! note "The labour cause is not on the solve"
    A solve that fails on labour surfaces as a failed run, not as a labelled
    reason. Where the cause is readable is the **unscheduled work order**
    diagnostics, which name the step as unstaffable. Dana goes there to find out
    what the solve would not tell her, and walks over to Priya — there is no flag
    or notification that carries it for her.

Then she admits work. Under manual release she opens **Pull in work** and reads
the recommendation as a proposal, not an instruction: it holds any order that
would push a resource past its norm and names the resource. She overrides one
hold, because she knows the second cell is coming back online at noon and the
solver does not.

> **Exercises** — Planner. Also the first half of the interlock with Priya at
> 07:30.

### 06:30 — Ade takes a delivery

A lorry arrives with three lots against expected receipts Nina raised last week.
Ade receives all three at once from **Production > Material Lots > Receive**
rather than taking them one at a time.

!!! note "Not the reman batch receive"
    `/reman/cores/receive-batch` is a different thing — taking in a lorry-load
    of **cores** for teardown. Material lots are received at
    `/production/material-lots/receive`.

Two lots pass incoming inspection. The third — seal kits from Calderon Supply —
fails: the bore diameter is out on four of the ten sampled. The lot goes to
**held**, and nothing of it reaches the floor.

> **Exercises** — Receiving: knowing what to expect, receiving, incoming
> inspection, holds. Creates the condition Nina works at 07:00 and the shortage
> Dana feels at 14:30.

### 07:00 — Nina chases, and raises a SCAR

Nina sees the held lot. She raises a **supplier corrective action request**
against Calderon: this is the second seal-kit rejection this quarter, and the
record needs to say so.

She also chases a separate late delivery — bearings that should have landed
Friday and did not. The shop is not short yet, but it will be on Thursday.

!!! note "Purchasing stops where money starts"
    Nina does not raise a purchase order here, or a price, or an approval to
    spend. Those live in the system that owns them. What uqmes holds is what she
    is expecting, from whom, and whether it turned up.

> **Exercises** — Purchasing: chasing what's late, when a supplier sends you
> something wrong, sourcing facts as planning inputs.

### 07:30 — Priya starts the shift

Priya reads her board and finds Dana's labour flag waiting. The gated step needs
a certification Tom does not hold.

This is the call that is hers: let the work start on her authority, or move the
work and leave the gate alone. She decides to let it start, because the
alternative is an idle cell, and tells Karim the record needs fixing properly.

!!! important "Deciding is not the same as authorising"
    She cannot clear the gate in advance. The override is a **second-person act
    at the moment of start**: Tom tries, the gate refuses, and Priya types her
    own email and password on his terminal, with a reason. So the decision is
    made here at 07:30 and the authorisation happens at 08:00, standing next to
    him — once per unit, not once for the shift.

> **Exercises** — Shift Lead: the calls that are yours, the training gate, your
> shift's board. Closes the interlock Dana opened at 06:00 and opens the one
> Karim closes at 15:30.

### 08:00 — Tom starts work

Tom claims work on the pump build and opens the step's work instructions. He
works through the substeps, recording measurements as he goes, confirming each
one.

The step requires a **first piece inspection**, so the run is held: no part moves
past the step until the first piece is bought off. Tom finishes the first unit's
captures and completes the step. The banner changes to *first piece complete —
awaiting buy-off*.

!!! note "Nothing is official until Complete step"
    Confirming a substep saves a draft. A value Tom fixes before completing the
    step never becomes a nonconformance. That distinction is the single thing
    most worth teaching an operator.

> **Exercises** — Operator: claiming work, running substeps, recording
> measurements, the draft-vs-record distinction, meeting an FPI hold.

### 08:30 — Jess buys off the first piece

Jess reviews the first piece's captures — the step's own work instruction *is*
the inspection — and signs it off. The step is authored to need a verified
signature, so she re-enters her own password.

She could not have done this if she had run the work herself: the server refuses
a buy-off from whoever completed the step's substeps. The gate is a second
person's judgement.

> **Exercises** — QA Inspector: first-piece buy-off, authored assurance,
> segregation of duties met head-on.

### 10:00 — A measurement goes out of spec

Tom records an outlet-port diameter above the upper limit. He has already
completed the step, so this is a record, not a draft.

He raises a **quality report** against the part with its result set to **FAIL**,
and adds the defect — error type, count, location, severity. The part is
quarantined as the report is created.

He does not pick the disposition; that is not his call.

!!! note "The result goes in at creation"
    Raising it as PENDING and failing it later would not quarantine the part —
    the hold runs once, when the report is made.

> **Exercises** — Operator: raising an issue properly. Note what is *not*
> available to him, which teaches as much as what is.

### 10:30 — Jess inspects, and the part is quarantined

The part is already quarantined — Tom's report did that when he raised it. Jess
reviews the report, confirms the finding and its severity, and takes it from
there.

She annotates the defect's location on the part's 3D model, so the next person to
see this failure sees where it was.

> **Exercises** — QA Inspector: quality reports, what quarantines a part,
> annotation.

### 11:00 — The disposition

Four more units show the same drift. A disposition is per part, so each gets its
own — Jess works the first and records **containment** on it first — the remaining units are pulled from the cell before
anything else happens.

The nonconformance is real but the parts are usable, so the decision is **Use As
Is** — which accepts nonconforming product and will not record without an
approval reference. Jess does not hold `approve_disposition`. Rather than handing
the record off, Ruth **co-signs at Jess's terminal**: her email, a drawn signature, and her
password. The record stores Ruth as the authorising party.

!!! warning "The drawn signature is discarded"
    The dialog requires a signature before it will proceed and then does not send
    it — only the email and password are transmitted. Teach the act, but do not
    tell anyone the drawing is kept, because it is not. The same is true of the
    first-piece co-sign dialog.

!!! important "This is where severity bites"
    The disposition is Major, so it cannot close until a containment action is
    **written on it**. Critical is gated the same way.

    Note what the gate checks: that the containment field is not empty. It does
    not check that containment *happened*. Typing a sentence satisfies it, so the
    discipline is yours — the system holds the record, not the act.

> **Exercises** — QA Inspector and QA Manager together. The clearest
> demonstration of co-signing in the product.

### 12:00 — Priya makes the calls

Priya has three things waiting. A **manual decision point** is holding a lot —
nothing failed; the step is simply waiting for a person. A second lot is stuck
behind the quarantine. And the same defect has now appeared on five units across
two days.

She resolves the decision point, and raises a **CAPA** for the repeat defect.
Five of the same failure is no longer a bad part; it is a bad process.

> **Exercises** — Shift Lead: manual decision points, raising a CAPA, reading a
> stuck floor. The CAPA is the thread Sam picks up at 13:00 and Ruth closes
> tomorrow.

### 13:00 — Sam changes the process

The root cause is a cycle time that does not allow the fixture to settle. Sam
opens the process, creates a **draft**, and edits the step.

The step is shared with the approved version, so the draft takes **its own copy**
on first edit — which is why editing a draft leaves the live process alone. He
corrects the timing, adjusts the work instruction's substep, and submits for
approval.

!!! note "Routings are versioned, not edited"
    The approved process is frozen. Changing it means a new version going through
    approval, and that refusal is the control working.

> **Exercises** — Engineering: authoring, versioning, copy-on-write, cycle times
> as a planning input.

### 13:30 — Iris revises the work instruction

The controlled document that goes with the step needs a revision. Iris creates
one, uploads the corrected file, and writes the **reason for the revision** — the
one required field, and the whole of the written record.

She submits it for approval. She does not choose the approval template; the
approval type does.

!!! note "Approved is not released"
    The revision reaching Approved does not put it in force. Release is a
    separate, deliberate act — and obsoleting the old revision is a third one that
    nothing does for her.

> **Exercises** — Document Controller: revisions, approval, the
> approved-vs-released gap, obsoleting.

### 14:00 — Ruth approves

Ruth has two approvals waiting: Sam's process change and Iris's document
revision. She reviews both and responds.

> **Exercises** — QA Manager: approvals, and the fact that routing comes from the
> template's approvers rather than from a permission.

### 14:30 — Dana re-promises

With the routing changed and the seal kits still held, Dana re-solves. Harborline
asks whether **a second repair**, on top of the one already in the shop, can be
promised for the 14th. Dana answers from **capable-to-promise**, which measures
capacity cumulatively across the window to the due date rather than guessing.

The answer is no for the 14th and yes for the 18th. She says so.

> **Exercises** — Planner: re-solving, CTP, the shortage interlock from Ade and
> Nina this morning.

### 15:00 — Marcus takes a new order

Harborline confirm the second repair, for the 18th. Marcus creates the order — **Order Name is
the only required field** — then creates the **work order** that carries the
production, with its ERP ID, process, priority and due date.

Then he adds parts from the **WO Control Center**, against the work order, and
sets priority. Priority lives on the work order; orders have none.

!!! note "The forms ask for more than the server requires"
    The screens are stricter than the API. Creating an order through the UI
    needs a name (a status is filled in for you); a work order's form requires a
    process, priority and due date, where the server requires only the ERP ID.
    And although the UI only adds parts against a work order, the API will
    accept them against an order too.

    That matters if you script against the API or read the schema — the form
    rules are not the contract.

> **Exercises** — Production Manager: orders vs work orders, adding parts,
> priority. This is the passage that most often exposes a reader's wrong mental
> model, which is why it is late in the day rather than first.

### 15:30 — Karim fixes the training record

Priya's override this morning was the right call and the wrong steady state.
Karim creates the **training record** that makes Tom's certification real, so the
gate stops refusing him.

He also looks for a notification rule that would have told Priya about the labour
gap before Dana had to, and finds there is none to configure: the event catalogue
covers training **expiring** and **expired**, which are about a lapsing
certification rather than one never held. Tom's case fires nothing. That is worth
knowing rather than working around.

> **Exercises** — Administrator: users and groups, training records, the
> permission and notification machinery. Closes Priya's 07:30 interlock.

### 16:00 — A core comes in for repair

A customer's own pump arrives for **repair and return**. Ade receives it as a
core; it is torn down, and reaches **Disassembled**, waiting on a release
decision.

Because it is the customer's own unit, there is exactly one exit: **release to
rebuild**. Harvesting it is refused — you cannot give away a unit that belongs to
somebody else.

Had it been an **exchange** unit, the shop's own, there would have been two:
rebuild to stock, or harvest for parts.

> **Exercises** — Receiving and Shift Lead, on the reman thread. The
> fulfilment-mode distinction is the whole lesson.

### 17:00 — Chen ships

Two completed work orders are ready. Chen ships them with their paperwork and
records the shipment.

> **Exercises** — Shipping: what is ready, shipping it, what happens after,
> on-time measurement.

### 17:30 — Priya hands over

Priya writes a **shift note** for the night shift: the seal kits are held, the
CAPA is open, Tom's certification is fixed, and the second cell is back. The
system will not carry this for her — a priority change takes no reason, so the
audit trail records *what* changed and not *why*.

> **Exercises** — Shift Lead: speaking to the next shift, and why the note
> matters more than it looks.

### Through the day — two people only reading

The **auditor** follows the day backwards from the CAPA: the quality report, the
defect, the disposition and its containment, who signed what and when, whether
the person who verified was the person who did the work.

The **customer contact** at Harborline sees their own order and nothing else —
but is not merely a spectator. A customer holds `respond_to_approval`, which is
how a concession reaches the shop: the approval reference the 11:00 Use As Is
decision demands is exactly the sort of thing a customer answers.

> **Exercises** — Auditor (orientation). The Customer is listed as orientation
> too, but note the responding-to-an-approval path above is a real write and is
> not currently exercised anywhere in the day.

## Role coverage

Every role's documented responsibilities, against the passage that exercises
them. A responsibility with no passage is a gap in this document, and the gaps
are named rather than left to be discovered — a role whose row carries a long
"not yet covered" list cannot have a complete track built from this day alone.

| Role | Exercised at | Responsibilities covered |
|------|-------------|--------------------------|
| **Planner** | 06:00, 14:30 | Staleness, admitting work, a labour-infeasible solve, CTP. **Not yet covered:** manual moves and pinning, the capacity-infeasible case, dispatch, draft vs live schedules, reman scheduling |
| **Receiving** | 06:30, 16:00 | Expected receipts, multi-lot receive, incoming inspection, holds, core receipt. **Not yet covered:** returning something to a supplier, putaway and cycle counts, dock metrics |
| **Purchasing** | 07:00 | Chasing late, supplier sent something wrong, SCAR, sourcing facts |
| **Shift Lead** | 07:30, 12:00, 17:30 | Training gate, the board, manual decision points, raising a CAPA, shift notes |
| **Operator** | 08:00, 10:00 | Claiming work, substeps, measurements, draft vs record, raising an issue. **Not yet covered:** checking equipment calibration, and end-of-shift handoff |
| **QA Inspector** | 08:30, 10:30, 11:00 | FPI buy-off, segregation, quality reports, quarantine, annotation, dispositions. **Not yet covered:** sampling inspections and AQL, and working the quarantine queue |
| **QA Manager** | 11:00, 14:00 | Disposition authority, co-signing, approvals. **Not yet covered:** CAPA verification and closure — the day defers it to "tomorrow", which leaves the largest QA Manager responsibility unexercised |
| **Engineering** | 13:00 | Authoring, versioning, copy-on-write, cycle times. **Not yet covered:** life limits |
| **Document Controller** | 13:30 | Revisions, approval, approved vs released, obsoleting |
| **Production Manager** | 15:00 | Orders, work orders, adding parts, priority. **Not yet covered:** handling quality holds — which the 10:30–11:00 passage is, with him absent from it — capacity planning, and bulk order import |
| **Administrator** | 15:30 | Users, training records, notification rules. **Not yet covered:** master data setup, approval templates, audit log review, system settings — note the day *consumes* approval templates at 13:30 and 14:00 without ever showing them being made |
| **Shipping** | 17:00 | Ready to ship, shipping. **Not yet covered:** on-time performance, and what happens after a shipment leaves |
| **Auditor** | through | Reading the trail (orientation) |
| **Customer** | through | Portal scope (orientation) |

### The interlocks

These are what make it a day rather than fourteen exercises. Break one and two
tracks stop making sense.

| Opened at | Closed at | What connects them |
|-----------|-----------|--------------------|
| 06:00 Dana's solve fails on labour | 07:30 Priya decides, 08:00 she authorises | The solver's failure is a person without a certification. Nothing carries it between them — Dana walks over |
| 07:30 Priya overrides | 15:30 Karim writes the record | An override is a decision, not a fix |
| 06:30 Ade holds a lot | 14:30 Dana re-promises short | A dock decision becomes a scheduling constraint |
| 06:30 Ade holds a lot | 07:00 Nina raises a SCAR | A rejection is a supplier fact, not just a shortage |
| 10:00 Tom reports | 11:00 Ruth co-signs | An operator's finding reaches an authority without a handoff |
| 12:00 Priya raises a CAPA | 13:00 Sam changes the process | Five of the same defect is a process problem |
| 13:00 Sam's change | 13:30 Iris's revision, 14:00 Ruth's approval | A process change drags a document with it |

## What the seed must produce

The day above is the requirement. This is what has to exist for it to be
walkable.

!!! warning "Not yet true"
    This section is a specification, not a description. The seed currently
    produces part of it — `TRAIN-BOTTLE` and `TRAIN-HOLD` already stage a
    bottleneck and a quality hold — and the gaps below are work, not errors.

**Users.** One per role in the cast. Six roles currently have no demo account at
all — Shift Lead, Planner, Engineering, Purchasing, Receiving, Shipping — and
their tracks cannot be performed without one.

**Master data.** A part type with a process that has a gated step, an FPI step,
and a measurement with tolerances tight enough to fail believably. A core type
with a route that continues past teardown. Three suppliers, one of them with a
rejection history.

**The situations**, each tied to its passage: a stale schedule and an order
infeasible on labour; expected receipts with one lot that fails incoming
inspection; a late delivery; an operator without a certification a gated step
needs; a work order at an FPI-gated step; a measurement result out of spec with a
defect; a Major disposition awaiting containment; five instances of one defect
across two days; a draft process; a document due for revision; a core at
Disassembled under repair-and-return; two work orders ready to ship.

**What must be true of it.** Deterministic, so an exercise can name a record and
have it be there. Idempotent, so re-seeding a training environment does not
duplicate the day. Neutral, so a facility that does not rebuild pumps can still
read it.

## Rules this document obeys

- **No money.** No prices, quotes, purchase orders or approvals to spend. Where a
  decision would need one, the day produces the scope and records the answer.
- **Two deployment dependencies, named rather than hidden.** The Planner's
  passages need a **Celery worker and beat scheduler** — a solve is dispatched
  asynchronously with no synchronous fallback, so with no worker it sits Pending
  forever, and the "overnight solve" is a beat task. Publishing a shift note
  emits an event, so a deployment with no mail path records the note and
  delivers nothing. Nothing here needs SSO or any integration connected.
- **Nothing real.** No company, person, supplier or part number refers to anyone.
- **Nothing that does not exist.** Every control named was checked against the
  source, and the day was then adversarially re-checked against it — which found
  real errors in the first draft and is why several passages now say what the
  product *doesn't* do. Where something is absent and its absence teaches — priority
  changes taking no reason, a drawn signature that is thrown away — the day says so
  rather than stepping around it.
