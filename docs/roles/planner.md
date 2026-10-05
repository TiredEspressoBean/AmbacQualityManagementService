# Planner Guide

This guide is for the person who decides **what the shop takes on, when it is
admitted, and where it runs** — the planning and scheduling side of uqmes.

!!! info "There is no Planner group"
    Unlike the other role guides, this one does not correspond to a group you
    can be put in. **Solving and committing** a schedule are gated on
    **Production Manager** or **Tenant Admin**; ask for one of those if Solve
    and Commit aren't available to you.

    Working the board — moving, pinning, reassigning, dispatching — is a wider
    permission, also held by **QA Manager** and **Shift Lead**. So half of this
    guide applies to you even without a planner role. See [Who can touch the
    board](../workflows/scheduling/gantt.md#who-can-touch-the-board).

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
| Where does it run, and in what order? | Days | [Schedule (Gantt)](../workflows/scheduling/gantt.md) — day to day this is [Scheduler](scheduler.md) work |
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
solve honours the pin — but softly: if the move turns out infeasible against the
global constraints, the solve relaxes it rather than failing. Use it when you
know something the model doesn't, and check it survived.

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

!!! warning "It measures the window, not the month"
    Capacity is measured over the window from now to the due date. This matters
    because an earlier version measured whole month buckets, which credited a
    full extra month whenever the window crossed a boundary — over-promising
    352 hours where 112 existed, and only for roughly the first third of each
    month.

    If a promise looks surprisingly generous, check the arithmetic rather than
    trusting it.

!!! danger "Missing cycle times make every capacity answer optimistic"
    An operation with no cycle time contributes **no load**. The capacity
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

- **Repair and return** — one option, *Release to rebuild*. It is the customer's
  own unit; it goes back to them.
- **Exchange** — *Rebuild to stock* or *Harvest for parts*. The unit is the
  shop's, so both are legitimate.

Releasing to rebuild is refused if **no rebuild scope resolves** for that core
type — releasing with nothing to do would put the unit on a work order with no
operations. That is a master-data gap (a rebuild level or repair codes), not a
decision you can force.

See [Remanufacturing Overview](../workflows/reman/overview.md).

!!! note "Harvest is a real decision, not a fallback"
    Harvesting ends the unit — it becomes *Dismantled*, terminal and explicitly
    not counted as output. Choose it when the body has failed or cores of that
    type are in surplus, not when you are unsure.

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

## Related

- [Releasing Work](../workflows/scheduling/releasing.md)
- [Schedule (Gantt)](../workflows/scheduling/gantt.md)
- [Capacity Planning](../workflows/scheduling/capacity.md)
- [Scheduling Overview](../workflows/scheduling/overview.md) — Calendar, Staging, Operator Hours, Requirements
- [Production Manager Guide](production-manager.md) — orders, work orders and the production side
