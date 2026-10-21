# Production Manager

The production manager's slice of [the shop day](../shop-day.md): reading what's at
risk, turning a customer's order into work, promising a date you can keep,
releasing work to the floor, reading the plan, and deciding the quality questions
that land on you. Every exercise is on the training shop, and every record it names
is one the training seed creates.

**About 3 hours**, in one sitting. **Before you start:** nothing. It helps to have
watched the [Operator](operator.md) track, because the floor works to what you
release.

!!! warning "On a training instance only"
    Every exercise writes real records: a planned line makes a work order, a release
    puts work in front of operators, and an approval is signed. See the [training
    program](../index.md).

## How a session runs

1. **Watch.** Your trainer works the modules on the training instance, saying what
   they look at and why.
2. **Regenerate.** Your trainer puts every exhibit back as it was (below).
3. **Do it with help.** You work the same modules on the same exhibits, with your
   trainer beside you.
4. **Try to break it.** Where a module has a refusal, something the system won't let
   you do, do it on purpose and read what it says. The refusal is part of the
   lesson, not an error.
5. **Alone.** After another regenerate, the [final task](#final-task-observed),
   with your trainer watching and not helping.

!!! warning "One trainee per instance at a time"
    Each exercise has one exhibit, and working it uses it up: a planned line can't be
    planned again. Run trainees one at a time, or give each their own instance.

**Regenerating** (for the trainer): **Settings** > **Organization** > **Regenerate
demo data**, then type `REGENERATE` to confirm. It needs a staff login, appears only
on the training tenant, and replaces **everyone's** work on the instance. It runs in
the background and takes a few minutes; the card stops waiting after five, so if it
hasn't finished by then, reload the page later rather than pressing it again.

!!! note "The schedule needs its worker"
    Solving and dispatching run in the background. On a training instance with no
    worker running, the schedule page says *queued, waiting for a worker* and
    nothing happens. Ask whoever runs the instance to start it before the session.

## Who you are

| You log in as | When |
|---------------|------|
| **Jennifer Walsh**, Production Manager, `jennifer.mgr@demo.ambac.com` | Every module |

Every password is `demo123`. Sarah Chen, a QA inspector, raised the CAPA you decide
in module 7.

---

## 1. What needs you

**You will:** read your home page and say what's at risk.

Log in as Jennifer. Your home page opens on **Needs attention**: a core awaiting the
customer's authorisation, the parts in quarantine, and the CAPAs waiting for
verification. Below it are quality figures, the work orders (most urgent first), the
outside processing, supplier qualifications that are expiring, and your own quality
actions and approvals.

**Exercise 1.1.** Say which work order is most at risk, and why it's ahead of the
others.

---

## 2. The order book

**You will:** find the orders that still need planning.

**Production** > **Orders** is the order book: every open customer order, with
what's still unplanned, when it's promised against when the plan says it will
finish, and what's blocking it. **On time, last 90 days** at the top counts what
actually shipped against the date it was promised.

- **Planning**: *N unplanned* means part of the order has no work order yet.
- **Projected vs promised**: *on track*, *N d late*, or *not scheduled*.
- **Blocked by**: a hold, quarantined parts, and anything else stopping the work.
  Each links to where it's resolved.

**Exercise 2.1.** Filter to **Needs planning**. `ORD-2024-0051` is Great Lakes
Diesel's order for 6 injectors, due in three weeks, with nothing planned.

**Exercise 2.2.** Find `TRAIN-HOLD`. Say what's blocking it.

---

## 3. Promise a date

**You will:** check you can take the work by the date the customer wants.

1. Open `ORD-2024-0051`. Its line is 6 × Common Rail Injector, due on the order's
   promised date.
2. **Check capacity** on the line. The capacity check opens with the line's part
   type, quantity and date filled in. Press **Check capacity**.
3. *Yes — capacity exists by …*, with the work content at each resource.

**Try to break it:** change the quantity to **1000** and check again. It says no,
names the resources that run out, ordered by how badly, and gives the earliest month
the order would fit.

The check is rough-cut: it adds the order to everything already committed and
compares that with the hours your shifts provide. It is the question to ask before
you promise; the schedule (module 5) is the answer once the work is real.

---

## 4. Turn the order into work, and release it

**You will:** make a work order from the order's line, and put it in front of the
floor.

1. On `ORD-2024-0051`, **Plan 6**. A work order is created for the line's 6 units,
   on the approved process for the part type, with a part for each unit. It appears
   under **Work orders**, *pending · not released*, and the line shows nothing
   remaining.
2. Open the new work order and **Release**. Releasing is what puts its first step in
   operators' queues. If the work isn't ready, the release is refused with what's
   missing, and **Release anyway** needs a reason of your own.
3. *Released — re-solve to plan it.* The schedule doesn't know about the work yet.

**Production** > **Orders** now shows `ORD-2024-0051` as planned and *not
scheduled* until the next solve.

---

## 5. The schedule

**You will:** solve the plan, and find out why work isn't on it.

**Scheduling** > **Schedule (Gantt)** shows every machine's work, one row per
machine. The header says how good the plan is (*FEASIBLE · within N %*), how many
orders it makes late, and *stale — re-solve* when the shop has changed since it was
solved.

1. **Solve**. It runs in the background and can take a few minutes; the page says
   *Solving* until it's done.
2. **Not scheduled** lists the work orders that aren't fully on the board, grouped
   by why: added since the last solve, waiting to ship, no units created yet, on
   hold. Each says what fixes it.

3. **Dispatch** puts named operators on the plan's work, by their qualifications and
   shifts. A bar then says how it went: *Dispatch assigned N of M tasks. K have no
   qualified operator free.* **Show them in People** switches the board to one row
   per person, with the uncovered work under **— Unassigned —**.
4. **What-if** solves a draft beside the live plan; the live plan doesn't change. The
   board switches to the draft with a comparison: makespan, lateness and the
   solver's gap for each. Small differences inside the gap may not be real.
   **Commit draft** makes it the plan; **Discard** throws it away.

**Exercise 5.1.** Before solving, open **Not scheduled** and find your new work
order. Say why it isn't there. Solve, and check again.

**Exercise 5.2.** In **Not scheduled**, find `WO-2024-0048-A`. Say what's missing.

---

## 6. What to release next

**You will:** see which work must start soon to make its date.

**Scheduling** > **Capacity Planning** > **What to release** works back from each
order's due date to the day it has to start: run hours at each resource, vendor
turnaround, and the queue measured on your floor.

- **Late to release**: past its start date and not released. Release it, cut the
  scope, or move the promise.
- **Released, not started**: released in time but nothing has begun. Get it onto
  the floor or re-sequence.
- **Coming up**: what's due to start soon.

*est.* means the date was derived; setting an earliest start on a work order
overrides it. Nothing on this page changes an order; it suggests.

---

## 7. A Major CAPA's go-ahead

**You will:** approve the plan for a Major CAPA, and see why you can't approve your
own.

A Major or Critical CAPA's plan needs a go-ahead from a QA Manager or a Production
Manager before its corrective work starts. Containment doesn't wait.

1. **Approvals** > **Overview** lists what's awaiting you. Open `CAPA-SU-2026-001`, Sarah's CAPA on
   a supplier's receiving lot, and its **Approval** tab: *Waiting for a QA Manager
   or Production Manager to approve the plan.*
2. **Submit Response**, **Approve**, say what you approved, sign, and enter your
   password. *This CAPA has been approved. Work may proceed.*

**Try to break it:** open `CAPA-2024-004`, which you raised. Its Approval tab
offers you nothing: *You requested this approval; a QA Manager or Production
Manager decides it.* Nobody approves their own plan while someone else can.

---

## 8. How the shop is doing

**You will:** read delivery, yield and downtime.

- **Supply** > **Shipping**: *On time, last 90 days*, counted per order line shipped
  against its due date. Anything with no date to judge is counted as unmeasured
  rather than left out.
- **Analytics**: first-pass yield against its target, scrap and rework rates, the
  top defects, and **Downtime**: hours lost in the last 30 days, by cause and by machine.

**Exercise 8.1.** Say which machine lost the most time, and to what.

---

## 9. Load the plant from a spreadsheet

**You will:** check a workbook before anything is loaded.

**Data Management** > **Master workbook** loads a plant from one spreadsheet, a sheet
per table, in load order. **Every upload is checked first, and nothing is kept
until every row loads.**

1. **Filled in** downloads a workbook of what's in the system now.
2. Upload it and **Check it**. Almost every row is *no change*, because it is what's
   already there.

**Try to break it:** the sheets you aren't permitted to load (users, sampling
rules, life limits) come back as errors: *You don't have permission to load this
sheet.* A check never writes, and a load writes nothing unless every row loads.

---

## 10. A job short after scrap

**You will:** close a scrap decision, and top the job back up.

`WO-PM-MAKEUP-01` was four bodies for Great Lakes. One turned undersize at
Machining. QA decided **Scrap**, and the scrap has been verified. Closing the
disposition, and replacing the body, are yours.

1. **Production** > **WO Control Center** > **Exceptions**. The disposition for
   `WO-PM-MAKEUP-01` is *In progress*: *Failed Machining: Body OD … (limits
   5.99–6.01)*. **Open disposition**.
2. Read the decision: **Scrap**, who authorised it, and the containment. Set
   **Current State** to **Closed**, add your resolution notes, and **Update
   Disposition**. Closing records who resolved it, and when.
3. Open `WO-PM-MAKEUP-01`. The **Make-up** card says *0/4 good · 3 alive · 1
   scrapped — 1 short of 4 good*. **Create 1 make-up part**: a new body starts at
   Machining, and the card clears.

Make-up is never automatic. A scrapped unit doesn't always need replacing (the
customer may take the short quantity), so a person decides.

---

## 11. Is the crew enough?

**You will:** say whether you have the people for the work, and where one absence
would stop it.

Two pages answer two different questions.

**Scheduling** > **Capacity Planning** > **Capacity heatmap** asks *does the plan fit
the month?* The headline says it: *Crew: enough for the planned work · busiest
2026-10 at 42%*. The **Labor** row compares the operator hours the work needs (setup
and the hands-on part of each operation, not a machine's whole run) with your crew's
working hours left in each month. Under about 85% is comfortable; over 100% you're
short.

The rows under it ask the sharper question: *enough of the right people?* Each is a
set of qualifications and how many people hold them. A row marked **one person**
is a step only one operator can do: one absence stops it, however much crew you
have. The headline counts them: *2 skills only one person can do*.

**Scheduling** > **Schedule (Gantt)** > **People** asks *who is booked?* Each row is
one operator's occupied time on the current plan. It doesn't tell you whether the
month fits.

**Exercise 11.1.** Say which two skills only one person can do, and what you'd do
about it before someone's away.

---

## Final task — observed

Your trainer regenerates the data, logs you in as Jennifer, and says only: *"Great
Lakes wants six injectors in three weeks. Can we, and get it started."* Then they
watch without helping:

- find the order in the order book
- check capacity for its line
- plan it, release it, and solve
- say where it sits on the plan and whether it makes its date

Your trainer is watching for:

- [ ] You checked capacity before treating the date as promised.
- [ ] You released only once the work was ready, or gave a reason to override.
- [ ] You re-solved after releasing, and read the result.
- [ ] When the system refused something, you read the refusal and acted on it.

## If your shop remanufactures

Everything above is new manufacture. A shop that also remanufactures adds this
module; a new-build-only shop skips it.

### R1. Record the customer's answer on extra work

**You will:** read what a customer is being asked to approve, and record their
answer.

`CORE-240212-0009` is Great Lakes Diesel's own injector, here for repair under
`ORD-2024-0046`. At the bench its nozzle was found cracked, and replacing it is more
than the rebuild they bought. The unit waits, *Awaiting customer authorisation*.

1. **Remanufacturing** > **Cores**, open `CORE-240212-0009`: *Awaiting customer
   authorisation*, *Repair & return — this unit goes back*.
2. **Approved…**. The dialog lists the repairs waiting on the customer's answer:
   *NZL-REPLACE · Replace injector nozzle*, with the finding behind it. That's the
   scope they were asked about; the price is agreed in your own system, not here.
   Record **who answered**, **how** (phone, email) and a **reference** you can find
   again, then **Record approval**.
3. *Approved, rebuild resumed.* The core is *In Rebuild*, its hold is cleared, and
   the answer is added to its notes with your name.

**Declined…** records a refusal the same way.

## Recording your qualification

Passing the final task is the assessment. The record is a **training record**, which
your QA manager writes. See [Training Records](../../workflows/quality/training-records.md).
