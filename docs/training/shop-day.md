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

Plus two who only read: an **Auditor** doing a surveillance visit, and a
**customer contact** at Harborline Marine, watching their own repair.

## The day

### 06:00 — Dana reads the board

The overnight solve is stale. Dana checks which kind of stale it is, because the
two need different answers: the plan **drifted** (work didn't go as scheduled) or
it **ran out** of the window it was solved for.

She re-solves. One order comes back **infeasible on labour** — no certified,
rostered operator can run a gated step at all. That is a staffing and training
problem wearing a scheduling costume, and no amount of re-solving fixes it. She
flags it for Priya and carries on.

Then she admits work. Under manual release she opens **Pull in work** and reads
the recommendation as a proposal, not an instruction: it holds any order that
would push a resource past its norm and names the resource. She overrides one
hold, because she knows the second cell is coming back online at noon and the
solver does not.

> **Exercises** — Planner. Also the first half of the interlock with Priya at
> 07:30.

### 06:30 — Ade takes a delivery

A lorry arrives with three lots against expected receipts Nina raised last week.
Ade uses **batch receive** rather than taking them one at a time.

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

This is the call that is hers. She can **override the training gate** to let the
work start, which is recorded against her name — or she can move the work and
leave the gate alone. She overrides it for the first two units, because the
alternative is an idle cell, and tells Karim the record needs fixing properly.

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

He raises a **quality report** against the part and adds the defect — error type,
count, location, severity. He does not pick the disposition; that is not his
call.

> **Exercises** — Operator: raising an issue properly. Note what is *not*
> available to him, which teaches as much as what is.

### 10:30 — Jess inspects, and the part is quarantined

Jess records the report's result as **FAIL**, and the part is quarantined.
Creating the report did not do that — failing did.

She annotates the defect's location on the part's 3D model, so the next person to
see this failure sees where it was.

> **Exercises** — QA Inspector: quality reports, what quarantines a part,
> annotation.

### 11:00 — The disposition

Four more units show the same drift. Jess opens the disposition and records
**containment** first — the remaining units are pulled from the cell before
anything else happens.

The nonconformance is real but the parts are usable, so the decision is **Use As
Is** — which accepts nonconforming product and will not record without an
approval reference. Jess does not hold `approve_disposition`. Rather than handing
the record off, Ruth **co-signs at Jess's terminal**: her email, her signature,
her password. The record carries Ruth as the authority and Jess as the caller.

!!! important "This is where severity bites"
    The disposition is Major, so it cannot close until containment is recorded on
    it. Containment first is not a convention here; it is a gate.

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

With the routing changed and the seal kits still held, Dana re-solves. A customer
asks whether a repair can be promised for the 14th; Dana answers from
**capable-to-promise**, which measures capacity across the window to the due date
rather than guessing.

The answer is no for the 14th and yes for the 18th. She says so.

> **Exercises** — Planner: re-solving, CTP, the shortage interlock from Ade and
> Nina this morning.

### 15:00 — Marcus takes a new order

A new order comes in from Harborline Marine. Marcus creates it — **Order Name is
the only required field** — then creates the **work order** that carries the
production, with its ERP ID, process, priority and due date.

Then he adds parts, against the work order rather than the order, and sets
priority. Priority lives on the work order; orders have none.

> **Exercises** — Production Manager: orders vs work orders, adding parts,
> priority. This is the passage that most often exposes a reader's wrong mental
> model, which is why it is late in the day rather than first.

### 15:30 — Karim fixes the training record

Priya's override this morning was the right call and the wrong steady state.
Karim creates the **training record** that makes Tom's certification real, so the
gate stops refusing him.

He also checks the notification rule that should have told Priya about the labour
gap before Dana had to.

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

The **customer contact** at Harborline sees their own order and nothing else.

> **Exercises** — Auditor and Customer, both orientation rather than training.

## Role coverage

Every role's documented responsibilities, against the passage that exercises
them. A responsibility with no passage is a gap in this document.

| Role | Exercised at | Responsibilities covered |
|------|-------------|--------------------------|
| **Planner** | 06:00, 14:30 | Staleness, admitting work, infeasible solves (capacity vs labour), manual moves, CTP |
| **Receiving** | 06:30, 16:00 | Expected receipts, batch receive, incoming inspection, holds, core receipt |
| **Purchasing** | 07:00 | Chasing late, supplier sent something wrong, SCAR, sourcing facts |
| **Shift Lead** | 07:30, 12:00, 17:30 | Training gate, the board, manual decision points, raising a CAPA, shift notes |
| **Operator** | 08:00, 10:00 | Claiming work, substeps, measurements, draft vs record, raising an issue |
| **QA Inspector** | 08:30, 10:30, 11:00 | FPI buy-off, segregation, quality reports, quarantine, annotation, dispositions |
| **QA Manager** | 11:00, 14:00 | Disposition authority, co-signing, approvals, CAPA verification |
| **Engineering** | 13:00 | Authoring, versioning, copy-on-write, cycle times |
| **Document Controller** | 13:30 | Revisions, approval, approved vs released, obsoleting |
| **Production Manager** | 15:00 | Orders, work orders, adding parts, priority |
| **Administrator** | 15:30 | Users, training records, notification rules |
| **Shipping** | 17:00 | Ready to ship, shipping, on-time |
| **Auditor** | through | Reading the trail (orientation) |
| **Customer** | through | Portal scope (orientation) |

### The interlocks

These are what make it a day rather than fourteen exercises. Break one and two
tracks stop making sense.

| Opened at | Closed at | What connects them |
|-----------|-----------|--------------------|
| 06:00 Dana flags a labour gap | 07:30 Priya overrides the gate | The solver's "infeasible" is a person without a certification |
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
- **No deployment assumptions.** Nothing here requires email to send, SSO to be
  configured, or a particular integration to be connected.
- **Nothing real.** No company, person, supplier or part number refers to anyone.
- **Nothing that does not exist.** Every control named has been verified against
  the product. Where something is absent and its absence teaches — priority
  changes taking no reason, an annotation that cannot be moved — the day says so
  rather than stepping around it.
