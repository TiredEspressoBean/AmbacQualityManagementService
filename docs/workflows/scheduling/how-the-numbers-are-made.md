# How the Numbers Are Made

The planning views show dates, loads and shortages. This page says where each
comes from and how far to trust it — the other pages are about decisions, this
one is about the arithmetic under them.

## The material lane

On [Capacity Planning](capacity.md), beneath the labour and work-centre lanes,
sits **Materials — stock left after committed work (negative = short)**.

It reads differently from the lanes above it, in two ways that matter.

### It is a balance, not a per-bucket capacity

A work centre has capacity *in* a bucket: so many hours that month. A material
does not. Its cell is **cumulative** — the stock left after all demand through
that bucket, set against what is on hand plus everything arriving by then.

!!! warning "Reading it as a capacity lane gives the wrong answer twice"
    Compare one bucket's demand against one bucket's supply and you will see
    shortages that stock arriving earlier already covers — and miss that an
    early order ate stock a later one was counting on.

### Demand lands at the start, not the due date

Material is consumed when the job runs, so demand is placed at the order's
**planned start**, using the same start the capacity lanes placed it at. The
lanes therefore agree with each other.

Put demand at the due date instead and a job released in January for April looks
fine — until January arrives.

### What it is not

It is deliberately **not** a projected available balance. There is no
bucket-by-bucket netting and no planned orders — just cumulative demand against
cumulative supply.

| | |
|---|---|
| **On hand** means | Accepted or In Use lots, **less safety stock** |
| **Incoming** means | Lots with a promised date and quantity still remaining |
| **Excluded** | Make lines (they have their own orders) and optional lines (not commitments) |

!!! warning "The lane goes red while there is still stock on the shelf"
    Opening cover is **free** stock, not physical stock — the safety buffer is
    held back. That is deliberate: the row should turn before you are actually
    out. If you are looking at a shortage and a full shelf, this is why.

Nothing consumes this lane. The solver has its own material gates, and
capable-to-promise does not read it. It is there for you to spot the bucket
where committed work outruns the parts that will exist by then — and then act in
the system that owns buying. uqmes does not purchase anything.

## Where release-by dates come from

Capacity Planning shows when an order has to **start** to hit its date, and
highlights the ones already late to release.

For an order with no start date that has not begun, that date is back-scheduled
from the due date using:

**work content** + **measured queue and move time** + **vendor days**

The queue figure is the part worth understanding, because it is measured rather
than set.

### Measured flow time

`Step timing` says how long an operation *occupies* a resource. It says nothing
about how long the part *sits there* — and in a job shop the waiting dominates.
Queue is routinely most of manufacturing lead time and run time a minority of it,
so a date built from run time alone is fiction.

| Property | Value | Why |
|----------|-------|-----|
| Measured per | **Work centre**, not step | Queue belongs to the resource, not the operation |
| Statistic | **75th percentile** | The median would mean being late half the time |
| Window | Last **90 days** | Recent enough to reflect how the shop runs now |
| Minimum sample | **5** | Below that the work centre is omitted entirely |

!!! important "A new tenant's dates are optimistic, not wrong"
    A work centre with fewer than five samples contributes **zero** queue time.
    Nothing is invented to fill the gap — so early dates come out short, and get
    more honest as history accumulates.

    The bar is cleared if **either** series has five observations — queue or
    move, whichever has more. So a work centre with five move readings and one
    queue reading is kept, and its queue figure rests on that single reading.
    Thin is not the same as absent, and neither is flagged.

    If release-by dates look implausibly comfortable on a young deployment, this
    is why. Treat them as a floor until the work centres have history.

!!! note "Why measured, and not configured"
    A configured lead time can confirm itself: pad it, work releases earlier,
    queues lengthen, and the padding looks justified. A measured one cannot —
    it only ever reports what actually happened. See [Releasing
    Work](releasing.md).

## What capable-to-promise measures

Capable-to-promise answers whether a quantity can be delivered by a date, and it
measures capacity over the window **from now to the due date** — not over whole
calendar buckets, and not using the material lane above.

!!! important "It quotes against the approved routing only"
    The part type needs an **approved** routing, or you get *"No approved
    process/routing defined for that part type"* rather than a date. That is
    deliberate: quoting off the newest process would quote an unapproved draft,
    and promise work nobody has agreed to.

    It keeps working **while a revision of that routing is open**. Engineering
    can be part-way through the next version without the shop losing the ability
    to quote — the approved one stays in force until the new one is approved.

It is cumulative, so a later date can fit what an earlier one cannot, and when
it refuses it names **every resource that fell short**, ordered by how far short
they came rather than by absolute hours.

A refusal also returns the **earliest bucket that would fit** — usually the most
useful thing on the screen, since it turns "no" into something you can offer.

!!! note "It is a month, not a date"
    The answer is a bucket label — *"by the end of which month could we?"* — not
    a specific day. Treat it as the month to quote, then confirm the day once the
    order is real.

    It can also come back **empty**, which means nothing inside the planning
    horizon fits. That is an answer, not a failure: the quantity needs capacity
    you don't have on the books.

!!! note "A binding resource can be a certification, not a machine"
    Crew pools are constrained by qualification, so a shortfall can appear as
    *"Certified: Assembly Certification + …"*. That is telling you the promise
    fails for want of trained people, not equipment — and the fix is the
    training matrix, not the shop floor.

!!! warning "Cycle times are what make all of this honest"
    An operation with no cycle time contributes **no load**. The heatmap then
    shows more free capacity than exists, release dates come out too late, and
    promises come out too generous.

    Capacity Planning warns when orders have operations with no cycle time
    recorded. Fix it on [Step Timings](setup.md#step-timings) — there is nothing
    to adjust in the planning views themselves.

## Next Steps

- [Capacity Planning](capacity.md) — the lanes these numbers appear in
- [Releasing Work](releasing.md) — the decision they support
- [Schedule (Gantt)](gantt.md) — the detailed plan below them
