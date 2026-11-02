# Capacity Planning

**Rough-cut capacity vs committed load, month by month — the long view the
30-day schedule can't give you.**

**Scheduling** > **Capacity Planning**

## What it's for

The Gantt board plans the detailed near term. Capacity planning answers the
questions that sit outside that window:

- Are we going to run out of capacity in four months?
- What should we release, and when?
- Could we take this order?

It works in months against rough-cut capacity rather than exact operation times,
so treat it as a planning aid, not a commitment.

## The views

| View | Shows |
|------|-------|
| **Capacity heatmap** | Load — work orders, open order lines and the unclaimed forecast — against available capacity, month by month |
| **What to release** | Work that should be released now to hit its dates |
| **Could we take this order?** | Whether a prospective order fits |

The horizon is a selector — **6, 12, 24 or 36 months**, defaulting to 12. Export
to **CSV** for planning offline.

## What's in the load

The heatmap's load is the work orders, **plus open order lines not yet planned
into work orders**. A customer order that hasn't been turned into a work order
yet still asks for the crew and machines, so it counts:

- Each such line is placed as if it were a work order: its work starts its
  routing's lead time before the line's due date, on the part type's
  **approved** routing, and its hours spread from there to the due month. A line
  due next year loads next year; a line already overdue loads the current month.
- A line already covered by work orders adds nothing more — the work orders carry
  it.
- Its material is in the load too: the line's bill of materials is exploded
  through the parts you make down to the items you buy, each made level grossed
  up by its routing's expected yield, landing in the month the line's work would
  start.

The crew verdict says how much of the load is lines like these — *Includes
&lt;N&gt; open order lines not yet planned* — so you can tell demand you have
committed to work from demand still on paper.

### RFIs and the forecast

Two more kinds of demand are in the load, and both are **shaded apart from firm
work**:

- **RFI orders are tentative.** An RFI order's open lines load capacity and
  material like any order line, but as *tentative* — the deal may not close.
  The verdict counts them: *…open order lines not yet planned, &lt;K&gt; of them
  RFI (tentative)*. An RFI line can't be planned into work until the order moves
  past RFI — see [Order Status](../orders/order-status.md).
- **The unclaimed forecast.** The [volume forecast](forecast.md) adds whatever
  orders due that month don't already cover. The verdict says *Includes
  &lt;U&gt; units of unclaimed forecast*, linking to the forecast.

A heatmap cell carrying either has a thin strip along its bottom edge — **sky
blue** for tentative (RFI), **violet** for unclaimed forecast — as wide as that
share of the month's load. Hovering adds *of which &lt;X&gt;h tentative (RFI
orders), &lt;Y&gt;h unclaimed forecast*. Forecast for a part type with no approved
routing can't be placed; an amber line says so — *Forecast for &lt;N&gt; part
type-months can't be placed (no approved routing) — not in the load*.

!!! warning "Lines that can't be placed aren't in the load"
    A line with **no due date**, or whose part type has **no approved routing**,
    can't be placed. The page says so in amber — *&lt;N&gt; order lines can't be
    placed (no due date or no approved routing) — not in the load* — and hovering
    lists each line and its reason. Fix the line or the routing; until then that
    demand is invisible here.

**Could we take this order?** is different: it measures against work orders
only, not against open order lines, RFIs or the forecast.

## Could we take this order?

Ask for a quantity of a part type by a date. The answer names the **binding
resource**, how short it is, and — when the answer is no — **the earliest date
that would fit**, which turns a refusal into a counter-offer worth taking back
to the customer.

> *Not by 2026-11-01. **Labor** — needs 551.6 h, only 327.8 h free by then.
> Earliest it fits: end of 2026-11.*

A refusal names **every** resource that fell short, ordered by how far short
they came rather than by absolute hours. If it comes back with nothing, nothing
in the planning horizon fits.

!!! info "It measures the window, not the month"
    Capacity-to-promise counts the hours available between **now and the date
    you asked about** — not the hours in the months that window happens to
    touch.

    Two consequences that look like bugs and are not:

    - The same quantity can be **refused for one date and promised for a date a
      week later**, because the later window contains more hours.
    - **Asking again tomorrow gives you slightly less capacity than today**, for
      the same reason.

    It is also **cumulative**, so a later date can fit what an earlier one
    cannot.

!!! warning "No approved routing, no answer"
    It answers only for a part type with an **approved** routing. A refusal that
    names the routing rather than a resource is a master-data answer, not a
    capacity one — and it is not a reason to quote from memory.

    An open revision alongside an approved one is fine; the approved version
    stays in force.

!!! note "A binding resource can be a certification"
    Crew pools are constrained by qualification, so a shortfall can read
    *"Certified: Assembly Certification + …"*. That promise is failing for want
    of **trained people**, not equipment — which is the
    [training matrix](../tracking/training-matrix.md)'s problem, not the floor's.

## Missing cycle times undermine it

The page warns when orders have operations with no cycle time recorded — for
example:

> *11 orders have operations with no cycle time recorded, so their load and
> release dates below are understated.*

Take that warning seriously. The orders it counts are the ones where an
operation has no authored cycle time, no measured history **and** no expected
duration on the step — those operations contribute **no run time** (at most
their setup), so the heatmap shows more free capacity than exists and release dates
come out too late. The more operations missing times, the more optimistic — and
the more wrong — the whole picture.

Fixing it means recording cycle times on the routing steps, not adjusting
anything here.

## Next Steps

- **[Schedule (Gantt)](gantt.md)** - The detailed near-term plan
- **[Scheduling Overview](overview.md)** - The other scheduling surfaces
