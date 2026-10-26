# Planner Guide

This guide is for the person who decides **what the shop takes on, when it is
admitted, and where it runs** — the planning and scheduling side of uqmes.

!!! info "Planner is a group, and it covers scheduling too"
    There is a **Planner** group, and it holds everything on this page: running
    and committing a solve, working the board by hand, and the calendars the
    plan is built on — shifts, overtime, holidays, PTO, changeovers and who is
    rostered where.

    **Production Manager** and **Tenant Admin** hold the plan as well, which is
    why most plants never staff this separately. The group exists so a facility
    that *does* staff planning separately can.

    !!! warning "They are not identical, and the difference bites"
        A Planner holds the **calendars** (shifts, overtime, holidays, PTO),
        **changeovers**, **rostering**, the solver settings and the board itself
        — including removing a slot and deleting a shift, which the manager
        cannot.

        A Planner does **not** hold two of the solver's own inputs: **step
        timings** (cycle times) and **machine eligibility**. Those sit with
        Production Manager and Tenant Admin. So when the plan is wrong *because
        the model is wrong*, a standalone Planner can diagnose it and cannot fix
        it — they have to hand it over. Worth knowing before you staff the role
        on its own.

    Working the board — moving, pinning, reassigning, dispatching — is wider than
    the group: **QA Manager** and **Shift Lead** hold it as well, so a shift lead
    can run the board for their shift without being able to re-plan the shop. See
    [Who can touch the board](../workflows/scheduling/gantt.md#who-can-touch-the-board).

    Two things stay with the manager even though they look adjacent: **work
    centres** (Engineering defines the plant; the planner uses it) and
    **cancelling a work order** — breaking a commitment to a customer, which
    needs `cancel_workorder`.

    **Equipment is yours**, despite sitting next to work centres: you can add and
    change equipment, and only *deleting* it is manager-tier.

!!! info "How to use this guide"
    It maps the decisions you own to the surface each is made on, and links to
    the reference page for the mechanics. It deliberately doesn't repeat those
    procedures — where this guide and a workflow page disagree, the workflow
    page is right.

## The decisions you own

| Decision | Horizon | Surface |
|----------|---------|---------|
| Can we take this order at all? | Months | [Capacity Planning](../workflows/scheduling/capacity.md) |
| What do we let onto the floor now? | Weeks | [Releasing Work](../workflows/scheduling/releasing.md) |
| Where does it run, and in what order? | Days | [Schedule (Gantt)](../workflows/scheduling/gantt.md) — see [Running the board](#running-the-board) |
| What do we buy, build or **recover** to support it? | Weeks | [Requirements](../workflows/scheduling/overview.md#requirements) |
| What goes to each bench tomorrow? | Hours | [Staging List](../workflows/scheduling/overview.md#staging-list) |

!!! tip "Recover is the one planners miss"
    Requirements has a **Recover (tear down)** section alongside buy and build:
    cores you already hold that could be torn down to cover a component need,
    instead of purchasing it. On a reman shop it is often the cheapest answer to
    a shortage, and it is the only place a teardown gets planned *ahead* rather
    than started on the unit. See [Planning a
    teardown](../workflows/scheduling/overview.md#planning-a-teardown).

They run at different horizons on purpose. A question asked at the wrong one
gets a confident answer that doesn't survive contact — capacity planning works
in months against rough-cut capacity and should never be read as a promise about
a particular Tuesday.

## A day

**Morning — read the board.** Open the Schedule and check whether it is stale.
Staleness has two causes and they need different responses: the plan *drifted*
(work didn't go as scheduled) or the plan simply *ran out* of the window it was
solved for. See [Why the schedule goes
stale](../workflows/scheduling/gantt.md).

**Then — admit work.** Under manual release, open **Pull in work**. Take the
recommendation as a proposal: it walks the whole pool in priority order,
holding any order that would push a resource past its norm and naming that
resource. It does not stop at the first order it holds, so smaller ones
further down can still come through. Override it when you know something it
doesn't.

**Through the day — handle what the solver couldn't place.** An infeasible solve
names what blocked it. Two causes worth telling apart:

- **Capacity** — nowhere to put the work in the window
- **Labour** — no certified, rostered operator can run a gated step at all

The second is a staffing or training problem wearing a scheduling costume, and
no amount of re-solving fixes it.

**As needed — move things by hand.** A manual move pins the task, and the next
solve holds it: same machine, same operator, same place in the queue. If
something makes it impossible (the machine goes down, the operator's off), the
solve releases it and says why rather than failing. Use it when you know
something the model doesn't, and check it survived.

## Running the board

Planning and scheduling are different horizons, but they are **one role** in
uqmes — the same surface, behind the same gates. Sequencing on the board is part
of planning, not a separate trade.

| | Longer horizon | Shorter horizon |
|---|---------|-----------|
| **Span** | Months to weeks | Days to hours |
| **Question** | Can we take it, and what do we release? | Where does it run, in what order, and who does it? |
| **Surfaces** | Capacity Planning, Requirements, Releasing | Schedule (Gantt), Dispatch, Staging |

### The loop

1. **Solve** — the solver places every task it can
2. Read **Not scheduled** — what it couldn't place, and why
3. **Dispatch** — assign operators to the placed work
4. Adjust by hand where you know something the solver doesn't
5. Re-solve when the shop moves

The header carries solver status, task count, **makespan**, **weighted lateness**
and how long the solve took.

!!! tip "Judge a draft by disruption, not only by lateness"
    The board compares the two — *makespan X → Y h*, *lateness X → Y*, *moves N
    tasks*. A better lateness figure that moves 500 tasks can cost more in
    disruption than it saves. See [Comparing before you
    commit](../workflows/scheduling/gantt.md#comparing-before-you-commit).

### Why isn't my job on the board?

**Not scheduled** answers it directly, grouped by reason, each row naming the
work order, how many units were placed, and the fix. There are twelve reasons,
and they are checked in order — the first that applies is the one you are shown:

| | Reason | What it means |
|---|--------|---------------|
| 1 | **On hold** | The work order is held |
| 2 | **Not released** | Not yet admitted to the floor |
| 3 | **No process assigned** | Nothing to schedule against |
| 4 | **Nothing left to work** | Every unit is finished, shipped, scrapped or quarantined |
| 5 | **No routing to schedule** | The process has no usable route |
| 6 | **No timings authored** | Operations carry no cycle time |
| 7 | **No trained operator** | Nobody certified and rostered can run a gated step |
| 8 | **Starts past the horizon** | Real, but beyond the window solved for |
| 9 | **Waiting on material** | Gated on material that has not arrived |
| 10 | **Material short** | Not enough to cover it |
| 11 | **Added since the last solve** | The board simply predates it |
| 12 | **Not placed by the last solve** | Nothing above explains it — the solve ran out of horizon or time |

The order matters when you are reading a long list: a job showing **Not
released** may *also* have no timings, and you will not see the second until you
fix the first.

Several resolve themselves on the next solve, and the dialog says so when the
schedule is stale. Number 7 is the one that never does — see *Labour* above.

### Dispatch

Dispatch assigns operators to placed tasks, **per lot rather than per piece**.
Until it runs, late tasks read *Uncovered — no operator assigned*, which is a
one-click problem rather than a training one.

### Moving something by hand

Drag a task and the rest of that unit's route **ripples with it**. Two checks run
first — the schedule horizon and the work order's release date — and a **pinned
successor** stops a ripple and is named.

**Merge** and **Break** decide whether an order's units travel as one lot or
separately. **Unpin** is what a pinned-successor refusal is asking for.

### When the shop fights the plan

| Symptom | Look at | Yours to fix? |
|---------|---------|---------------|
| Dates look too comfortable | [Step Timings](../workflows/scheduling/setup.md#step-timings) — an operation with no timing of any kind contributes no load | **No** — the step's own duration is [Engineering](engineering.md)'s |
| Work lands on the wrong machine | [Machine Eligibility](../workflows/scheduling/setup.md#machine-eligibility) | **No** — Production Manager or Tenant Admin |
| The solver interleaves similar jobs | [Changeovers](../workflows/scheduling/setup.md#changeovers) | Yes |
| Nobody can run a gated step | The training matrix — a binding resource can be a certification | Rostering yes; the certification itself no |
| The calendar is wrong | Shifts, overtime, holidays, PTO | Yes |

## Promising a date

**Capable to promise** answers whether a quantity can be delivered by a date. It
is cumulative — a later date can fit what an earlier one cannot — and when it
refuses it names **every resource that fell short**, ordered by how far short
they came rather than by absolute hours.

It also returns the **earliest month that would fit**, which is the number to
take back to the customer: it turns a refusal into a counter-offer. If it comes
back empty, nothing in the planning horizon fits.

!!! warning "No approved routing, no quote"
    It answers only for a part type with an **approved** routing. A refusal
    naming the routing rather than a resource is a master-data answer, not a
    capacity one — and it is not a reason to quote from memory. An open revision
    of an approved routing is fine; the approved version stays in force.

!!! note "A binding resource can be a certification"
    Crew pools are constrained by qualification, so a shortfall can read
    *"Certified: Assembly Certification + …"*. The promise is failing for want
    of trained people, not equipment — that is the training matrix's problem,
    not the shop floor's.

!!! info "It measures the window, not the month"
    Capacity-to-promise counts the hours available between **now and the due
    date you asked about** — not the hours in the months that window touches.

    So the same quantity can be refused for one date and promised for a date a
    week later, and asking again tomorrow gives you slightly less capacity than
    today. That is the arithmetic working, not drifting.

!!! danger "Missing cycle times make every capacity answer optimistic"
    An operation with no authored cycle time, no measured history and no
    expected duration on the step contributes **no load**. The capacity
    heatmap then shows more free capacity than exists and release dates come out
    too late. Capacity Planning warns when orders have operations with no cycle
    time — take it seriously, and fix it on the routing step rather than
    adjusting anything in the planning view.

## Draft and live

A solve can produce a **draft** schedule you review against the live one, then
commit or discard. Committing promotes it to active and supersedes the old one.

Review the draft before committing when the solve was triggered by something
structural — a changed routing, a new constraint, a big release — rather than by
routine drift.

## Remanufacturing

If the shop remans, one planning decision is yours and it is not reversible:
**what happens to a core after teardown**.

A torn-down unit sits at *Disassembled*, on hold, until you choose its exit. What
you're offered depends on how it is being fulfilled:

- **Repair and return** — one option, *Release into rebuild*. It is the
  customer's own unit, so it goes back to them. Releasing it to inventory is
  **refused outright**, and the refusal says why: its components are that
  customer's property and cannot become your stock.
- **Exchange** — *Rebuild to stock* or *Release to inventory*. The customer
  already has a unit from stock, so this one is the shop's and both are
  legitimate.

A rebuilt exchange unit ends at **Rebuilt to stock** and **keeps its identity** —
same unit, same core number — ready to go out against the next exchange.

Releasing to rebuild is refused when the unit's **route does not continue past
teardown** — there is nowhere for the rebuild to pick up:

> *… has no next step on its route after teardown — check the work order's
> process continues past teardown.*

That is a **process** gap, not a master-data one. A core type with no repair
codes and no rebuild levels releases to rebuild perfectly well — the unit simply
walks its main line and no repair branch is offered.

See [Remanufacturing Overview](../workflows/reman/overview.md).

!!! note "Releasing to inventory is a real decision, not a fallback"
    It ends the unit. Its usable components are accepted into stock and the core
    itself is **consumed**: the core's stage becomes *Harvested to inventory*
    and its part goes to *Dismantled*. The unit does not come back from it.

    **Dismantled is terminal but is deliberately not counted as output** — a
    harvested unit no longer exists and must not read as something the shop
    produced. Choose this when the body has failed or cores of that type are in
    surplus, not when you are unsure.

    Partial runs finish cleanly: components already accepted are skipped rather
    than erroring, so releasing again after an interruption completes the job.

## What good looks like

**Release against measured load, never against a planned lead time.** Padding a
lead time to make dates work releases work earlier, which lengthens queues,
which makes the padding look justified. That loop is the classic MRP failure and
the release gate is built specifically to have no quantity that can spiral.

**Don't starve a resource to respect a norm.** Holding an order back while a
resource sits idle loses hours the shop can never recover. The recommendation
already overrides its own ceilings for a gating resource with no committed work
— trust that, and apply the same judgement to the cases it can't see.

**Treat the schedule as a forecast with a shelf life.** It is honest about
staleness; act on that rather than working from a board you last solved a week
ago.

## If you got something wrong

- A what-if committed by mistake: **Restore the previous plan**, one step back.
- A task moved or pinned by mistake: **Undo** the last move, or unpin it.
- A work order released by mistake: **Un-release** it.
- A calendar entry made wrong: **Remove** it, add it again, and re-solve.

See [Putting a Mistake Right](../workflows/fixing-mistakes.md#planning).

## Related

- [Releasing Work](../workflows/scheduling/releasing.md)
- [Schedule (Gantt)](../workflows/scheduling/gantt.md)
- [Capacity Planning](../workflows/scheduling/capacity.md)
- [Scheduling Overview](../workflows/scheduling/overview.md) — Calendar, Staging, Operator Hours, Requirements
- [Production Manager Guide](production-manager.md) — orders, work orders and the production side
