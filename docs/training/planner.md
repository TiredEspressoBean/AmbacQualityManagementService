# Planner Training Guide

**Duration:** 4-5 hours
**Prerequisites:** None, though familiarity with the shop's routings helps
**Goal:** Learn to release work against measured load, promise dates you can
keep, run and read the schedule, and decide a core's exit after teardown

!!! note "Role Name"
    This training is for the **Planner** role in the system. Planning and
    scheduling are **one role** here — sequencing on the board is part of
    planning, not a separate trade.

!!! info "Demo Environment Login"
    **Email:** jennifer.mgr@demo.ambac.com
    **Password:** `demo123`

    The demo has no account whose only group is Planner. Jennifer Walsh is
    **Production Manager**, which holds every planner permission plus more —
    so everything in this guide works, and some screens will show more than it
    describes.

!!! warning "Planner has no Home landing yet"
    If your live account holds only Planner, Home will be empty. Reach your work
    through the **Scheduling** section of the sidebar.

---

## Module 1: The Decisions You Own

### Learning Objectives

1. Name the planning decisions and the horizon each belongs to
2. Explain why asking a question at the wrong horizon gives a wrong answer

### 1.1 Five decisions, five horizons

| Decision | Horizon | Surface |
|----------|---------|---------|
| Can we take this order at all? | Months | Capacity Planning |
| What do we let onto the floor now? | Weeks | Releasing Work |
| Where does it run, and in what order? | Days | Schedule (Gantt) |
| What do we buy, build or **recover**? | Weeks | Requirements |
| What goes to each bench tomorrow? | Hours | Staging List |

!!! warning "A question asked at the wrong horizon gets a confident wrong answer"
    Capacity planning works in months against rough-cut capacity. It should never
    be read as a promise about a particular Tuesday.

### Knowledge Check: Module 1

1. A customer asks whether you can deliver 300 units in three weeks. Which
   surface answers that, and which one does **not**?
2. Which decision is the only one that is irreversible?

---

## Module 2: Releasing Work

### Learning Objectives

1. Release work against measured load
2. Read and override the pull-in recommendation
3. Explain why padding a lead time makes things worse

### 2.1 Pull in work

Under manual release, **Pull in work** walks the whole pool in priority order,
holding any order that would push a resource past its norm and **naming that
resource**. It does not stop at the first order it holds, so smaller ones further
down can still come through.

Take it as a proposal. Override it when you know something it doesn't.

### 2.2 The failure this gate exists to prevent

!!! danger "Never release against a planned lead time"
    Padding a lead time to make dates work releases work earlier, which lengthens
    queues, which makes the padding look justified. That loop is the classic MRP
    failure. The release gate is built specifically so there is no quantity that
    can spiral.

### 2.3 The opposite mistake

!!! warning "Don't starve a resource to respect a norm"
    Holding an order back while a resource sits idle loses hours the shop can
    never recover. The recommendation already overrides its own ceilings for a
    gating resource with no committed work — trust that, and apply the same
    judgement where it can't see.

### 2.4 Release is a record, not a status

Releasing stamps **who** released it and **when**, and an override carries a
reason. That is ISO 9001 §8.5.1 evidence, separate from whether work has
actually started.

See [Releasing Work](../workflows/scheduling/releasing.md).

### Knowledge Check: Module 2

1. The recommendation holds an order and names Machining. What are your options?
2. Why is "release earlier so it finishes sooner" wrong?
3. What is the difference between released and started?

---

## Module 3: Promising a Date

### Learning Objectives

1. Use Capable-to-Promise
2. Turn a refusal into a counter-offer
3. Recognise the three ways a capacity answer can mislead you

### 3.1 Capable to promise

CTP answers whether a quantity can be delivered by a date. It is **cumulative** —
a later date can fit what an earlier one cannot.

When it refuses, it names **every resource that fell short**, ordered by how far
short they came. It also returns the **earliest month that would fit** — that is
the number to take back to the customer, because it turns a refusal into a
counter-offer.

### 3.2 Three ways it can mislead

!!! danger "Missing cycle times make every capacity answer optimistic"
    An operation with no cycle time contributes **no load**. The heatmap then
    shows free capacity that doesn't exist. Capacity Planning warns about this —
    fix it on the routing step, never in the planning view.

!!! warning "A binding resource can be a certification"
    Crew pools are constrained by qualification, so a shortfall can read
    *"Certified: Assembly Certification + …"*. The promise is failing for want of
    **trained people**, not equipment. That is the training matrix's problem.

!!! note "No approved routing, no promise"
    CTP answers only for a part type with an **approved** routing. A refusal
    naming the routing is a master-data answer, not a capacity one — and not a
    reason to quote from memory.

### 3.3 It measures the window, not the month

Capacity is measured over the window from now to the due date. An earlier version
measured whole month buckets, which credited a full extra month whenever the
window crossed a boundary — over-promising 352 hours where 112 existed.

**If a promise looks surprisingly generous, check the arithmetic rather than
trusting it.**

### Knowledge Check: Module 3

1. CTP refuses a date and names three resources. What two numbers do you take
   back to the customer?
2. The heatmap shows plenty of free capacity but the floor is visibly swamped.
   What do you check first?

---

## Module 4: Running the Schedule

### Learning Objectives

1. Run a solve and read its figures
2. Diagnose what didn't schedule
3. Judge a draft before committing it

### 4.1 The loop

1. **Solve** — the solver places every task it can
2. Read **Not scheduled** — what it couldn't place, and why
3. **Dispatch** — assign operators to the placed work
4. Adjust by hand where you know something the solver doesn't
5. Re-solve when the shop moves

### 4.2 Reading the figures

The header carries solver status, task count, **makespan**, **weighted lateness**
and solve time.

!!! tip "Judge a draft by disruption, not only by lateness"
    The board compares the two — *makespan X → Y h*, *lateness X → Y*, *moves N
    tasks*. A better lateness figure that moves 500 tasks can cost more in
    disruption than it saves.

**What-if** explores a change without touching the live schedule; **Commit
draft** makes it real. Review a draft before committing when the solve was
triggered by something structural — a changed routing, a new constraint, a big
release — rather than by routine drift.

### 4.3 Why isn't my job on the board?

**Not scheduled** answers directly, grouped by reason, each row naming the work
order, how many units were placed, and the fix. Twelve reasons, from *On hold*
and *Not released* through *No trained operator* and *Material short* to *Added
since the last solve*.

Several resolve themselves on the next solve, and the dialog says so when the
schedule is stale.

!!! warning "Capacity and labour are different problems"
    **Capacity** — nowhere to put the work in the window.
    **Labour** — no certified, rostered operator can run a gated step at all.

    The second is a staffing or training problem wearing a scheduling costume.
    No amount of re-solving fixes it.

### 4.4 Moving something by hand

A manual move **pins** the task, and the next solve honours the pin — but
**softly**: if the move turns out infeasible against the global constraints, the
solve relaxes it rather than failing.

Use it when you know something the model doesn't, and **check it survived**.

### Knowledge Check: Module 4

1. A draft improves lateness by 8% and moves 400 tasks. Do you commit it?
2. *No trained operator* appears against six work orders. Who do you talk to?
3. You pinned a task yesterday and it has moved. Is that a bug?

---

## Module 5: Non-Working Time

### Learning Objectives

1. Author the four kinds of non-working time
2. Confirm the solver actually honoured it

### 5.1 The calendar is yours because the plan is

A stale calendar breaks the plan on day one, so the person who owns the plan owns
the calendar. There are four kinds, and you author all of them:

| Kind | What it is | Demo examples |
|------|-----------|---------------|
| **Plant exception** | The whole site is down | *Labor Day* (HOLIDAY) · *Quarterly Inventory Count* (INVENTORY) · *Winter Shutdown* 24–31 Dec |
| **Labour block** | One named person is unavailable | *PTO* (once) · *Training* (once) · an *ALL MEETING* (weekly) |
| **Shift** | The pattern capacity is measured against | Day, 06:00–18:00 |
| **Overtime window** | Capacity you are buying back | — |

### 5.2 Prove the solver honoured it

Authoring is half the job. **Check the board afterwards.**

Verified 2026-10-12: Labor Day carries **0 tasks**, while the next working day
carries 119. The calendar is not decoration — the solve plans around it.

!!! tip "The staging list is the fastest proof"
    Open **Staging List** on a plant holiday and the default 8-hour window is
    empty: *"Nothing scheduled in this window."* Widen it to 24h and the benches
    fill up again. That round trip confirms, in about ten seconds, that your
    exception reached the solver.

!!! warning "This is also the most common false alarm"
    *"The staging list is broken"* on a holiday morning is your calendar working.
    Teach your leads to widen the window before raising it.

### Knowledge Check: Module 5

1. You add a shutdown week. What do you check before telling anyone the plan is safe?
2. A lead says staging is empty. What two questions do you ask?
3. Whose PTO belongs in a labour block rather than a plant exception?

---

## Module 6: Did the Floor Follow It?

### Learning Objectives

1. Read planned versus actual
2. Understand why it is often empty, and why that is deliberate

### 6.1 Capture is forward-looking

Each scheduled task stamps an **actual start** and **actual end** as a part
enters and leaves its step.

!!! important "It records; it does not react"
    Capture deliberately **does not** re-time the plan or mark the schedule
    stale. The solver already pins in-progress operations when it solves, and
    *"an actuals drift on every advance would leave the flag permanently on and
    meaningless."*

### 6.2 Why yours may be empty

Actuals only accrue for work that moves **after** a solve. A schedule solved
today, over a shop whose activity happened last week, will show nothing — not
because capture is broken, but because there was nothing left to capture.

!!! note "To see it work, move a part after solving"
    Solve, then advance a unit through a step, then look again. That is the only
    sequence that produces an actual.

### Knowledge Check: Module 6

1. Your board shows no actuals at all. What is the first thing to check?
2. Why doesn't a part finishing early mark the schedule stale?

---

## Module 7: Buy, Build or Recover

### Learning Objectives

1. Read the requirements report
2. Recognise when teardown beats purchasing

### 5.1 The third option

Requirements has a **Recover (tear down)** section alongside buy and build: cores
you already hold that could be torn down to cover a component need, instead of
purchasing it.

!!! tip "Recover is the one planners miss"
    On a reman shop it is often the cheapest answer to a shortage, and it is the
    only place a teardown gets planned *ahead* rather than started on the unit.

!!! warning "uqmes does not price any of this"
    It produces the **scope** — what work, what parts, and the finding behind
    each — exports it, and records the answer. The buy decision happens in the
    system that owns the money.

### Knowledge Check: Module 7

1. You are short twelve nozzles. What three options does the report offer?
2. Where does the cost comparison happen?

---

## Module 8: A Core's Exit

### Learning Objectives

1. Choose a core's exit after teardown
2. Explain why the choice depends on fulfilment type

### 6.1 The decision

A torn-down unit sits at *Disassembled*, on hold, until you choose its exit. What
you are offered depends on how it is being fulfilled:

- **Repair and return** — one option, *Release to rebuild*. It is the customer's
  own unit; it goes back to them.
- **Exchange** — *Rebuild to stock* or *Harvest for parts*. The unit is the
  shop's, so both are legitimate.

### 6.2 Two things that will stop you

!!! note "Harvest is a real decision, not a fallback"
    Harvesting **ends** the unit — it becomes *Dismantled*, terminal, and
    explicitly not counted as output. Choose it when the body has failed or cores
    of that type are in surplus, never when you are unsure.

!!! warning "Release to rebuild is refused with no rebuild scope"
    If no scope resolves for that core type, releasing would put the unit on a
    work order with **no operations**. That is a master-data gap — a rebuild
    level or repair codes — not a decision you can force.

See [Remanufacturing Overview](../workflows/reman/overview.md).

### Knowledge Check: Module 8

1. A customer's own core comes back under repair-and-return. Can you harvest it?
2. *Release to rebuild* is greyed out. What do you fix?

---

## Practical Assessment

### Task 1: Release against load
Open Pull in work. Identify an order the recommendation holds, name the resource
it named, and justify either accepting or overriding the hold.

### Task 2: Promise a date
Run Capable-to-Promise for a quantity that will fail. Report both the shortfall
resources and the earliest month that fits.

### Task 3: Diagnose a capacity answer
Find a routing operation with no cycle time. Explain what it does to the heatmap
and where you would fix it.

### Task 4: Solve and read it
Run a solve. Report makespan, weighted lateness, and the top three reasons in
Not scheduled. Say which of those will fix themselves.

### Task 5: Judge a draft
Produce a what-if draft. Decide whether to commit it, and say why in terms of
both lateness and disruption.

### Task 6: Decide a core's exit
Find a disassembled core and choose its exit. State what the fulfilment type
allowed and what it ruled out.

### Task 7: Author non-working time, and prove it landed (row 9)
Add a plant exception. Then open the schedule and the staging list and show that
the solver planned around it. Say which of the four kinds you used and why.

### Task 8: Read planned versus actual (row 8)
Report how many scheduled tasks carry an actual. If it is zero, explain the
sequence that would produce one — and why capture does not mark the plan stale.

---

## Training Completion

### Sign-Off Requirements

- [ ] Completed all modules
- [ ] Passed knowledge checks
- [ ] Completed practical assessment
- [ ] Supervisor verification

### Trainee Acknowledgment

By completing this training, I confirm that I:

- Will release against measured load, never against a padded lead time
- Will quote from Capable-to-Promise, not from memory
- Will check a surprisingly generous promise before passing it on
- Will treat the schedule as a forecast with a shelf life

### Recording the qualification

Create a **Training Record** under **Quality** > **Training**, as in [Operator
training](operator.md#recording-the-qualification).

---

## Quick Reference Card

### The loop
Solve → read Not scheduled → Dispatch → adjust by hand → re-solve

### Before you promise
- Is the routing **approved**?
- Do all its operations have **cycle times**?
- Is the binding resource a machine or a **certification**?

### Before you commit a draft
- Lateness change
- Makespan change
- **How many tasks it moves**

### Red flags
- A promise that looks too generous → check the window arithmetic
- *No trained operator* → training matrix, not the schedule
- Release date earlier than the material → check Requirements

---

## Next Steps

- [Planner role guide](../roles/planner.md)
- [Releasing Work](../workflows/scheduling/releasing.md)
- [Capacity Planning](../workflows/scheduling/capacity.md)
- [Schedule (Gantt)](../workflows/scheduling/gantt.md)
- [Scheduling Setup](../workflows/scheduling/setup.md) — what the solver believes
- [Production Manager Training](production-manager.md) — the role that usually also holds this
