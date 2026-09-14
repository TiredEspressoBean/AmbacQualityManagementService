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
| **Capacity heatmap** | Committed load against available capacity, month by month |
| **What to release** | Work that should be released now to hit its dates |
| **Could we take this order?** | Whether a prospective order fits |

The horizon is **12 months**. Export to **CSV** for planning offline.

## Missing cycle times undermine it

The page warns when orders have operations with no cycle time recorded — for
example:

> *11 orders have operations with no cycle time recorded, so their load and
> release dates below are undercounted.*

Take that warning seriously. An operation with no cycle time contributes **no
load**, so the heatmap shows more free capacity than exists and release dates
come out too late. The more operations missing times, the more optimistic — and
the more wrong — the whole picture.

Fixing it means recording cycle times on the routing steps, not adjusting
anything here.

## Next Steps

- **[Schedule (Gantt)](gantt.md)** - The detailed near-term plan
- **[Scheduling Overview](overview.md)** - The other scheduling surfaces
