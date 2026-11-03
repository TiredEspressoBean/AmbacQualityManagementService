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

## Where the capacity comes from

Capacity is read from the [Calendar](overview.md#calendar) and the roster — the
same working time the scheduler plans against:

| Row | Hours available |
|-----|-----------------|
| **Labor** | Each shop-floor operator's own shift, plus that shift's overtime, less plant closures, company-wide blocks and their own time off (PTO, sick, training) |
| **A work centre** | Its attended machines × the plant's working hours (shifts plus overtime, less closures), plus its lights-out machines × every hour of the month less closures |
| **A certification pool** | The labor hours of the operators qualified for that work, worked out the same way as Labor |

- **Yearly closures** count in every year of the view, so a 24- or 36-month
  horizon loses each year's shutdown, not just the first.
- The current month offers only what is **left** of it.
- It is **today's** roster carried forward. A hire, a new shift or a newly
  qualified operator counts only once they are on the roster or trained. There
  is no way to plan one ahead.
- A plant closure stops **every** machine, lights-out ones included, as it does
  on the schedule: a two-day shutdown takes 48 h off each lights-out machine
  that month.
- Machine downtime is not taken off here, for either kind of machine.
- **Could we take this order?** counts the same hours.

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
  orders don't already use up — orders use up their due month's forecast, then
  neighbouring months' within the [consumption window](forecast.md#orders-use-up-the-forecast).
  Inside the [demand time fence](forecast.md#the-demand-time-fence) — the next
  30 days, by default — no forecast is planned, only orders. The verdict
  says *Includes &lt;U&gt; units of unclaimed forecast (~&lt;H&gt; h)*, linking
  to the forecast: the units actually in the load, past the fence, and the hours
  they cost.

A heatmap cell carrying either has a thin strip along its bottom edge — **sky
blue** for tentative (RFI), **violet** for unclaimed forecast — as wide as that
share of the month's load. Hovering adds *of which &lt;X&gt;h tentative (RFI
orders), &lt;Y&gt;h unclaimed forecast*. Forecast for a part type with no approved
routing can't be placed; an amber line says so — *Forecast for &lt;N&gt; part
type-months (&lt;U&gt; units) can't be placed (no approved routing) — not in the
load*. Those units aren't counted in the verdict's figure.

!!! warning "Lines that can't be placed aren't in the load"
    A line with **no due date**, or whose part type has **no approved routing**,
    can't be placed. The page says so in amber — *&lt;N&gt; order lines can't be
    placed (no due date or no approved routing) — not in the load* — and hovering
    lists each line and its reason. Fix the line or the routing; until then that
    demand is invisible here.

**Could we take this order?** measures against the same load — see [What it
counts](#what-it-counts).

## Material outlook

The **Materials** rows show, for each bought item, the demand landing in each
month — work orders, open order lines, RFIs and the unclaimed forecast together.
Demand is exploded through the bill of materials down to the items you buy,
each made level grossed up by its routing's expected yield, and lands in the
month the work starts, not the month it is due.

Hover a month for the quantity in the item's stock unit — *&lt;n&gt; EA needed
this month* — and, where some of it isn't firm, the split *(firm &lt;x&gt; · RFI
&lt;y&gt; · forecast &lt;z&gt;)*. The same sky-blue and violet strip as the
capacity cells shows the RFI and forecast share.

### Exporting it

The Materials header carries **Material outlook (&lt;N&gt; months): Excel ·
CSV**, for the horizon selected on the page. It needs `export_data`, and each
export is recorded as a bulk export. Purchasing's home has a **Material
outlook** tile that opens this page at 24 months.

One row per bought item, keyed the way the ERP keys it:

| Column | Holds |
|--------|-------|
| **Item** | A material's part number, or a bought part type's ERP id |
| **Name**, **Kind** | *Material* or *Bought part* |
| **Stock unit**, **Purchase unit**, **Stock units per purchase unit** | How it is counted and bought; the last is blank when it is bought in the stock unit |
| **On hand**, **Safety stock**, **Incoming** | Incoming is lots promised within the horizon, plus lots promised before this month and still expected |
| **Incoming (late)** | Of Incoming, the lots already past their promised month and not yet received — counted as supply in the current month; blank when none |
| **Lead time (days)** | The item's purchase lead time, from its sourcing |
| **First short (firm)** | The first month (`YYYY-MM`) whose running balance — on hand − safety stock + incoming − firm demand so far — goes below zero |
| **Order by** | The 1st of the first short month, less the lead time in calendar days; with no lead time set, the 1st of that month |
| **Late** | *Late* when the order-by date has already passed (the date is still shown) |
| **Watch from** | For a shortage only RFI or forecast demand causes: the month it starts and what causes it — *2026-12 (on forecast)*, *(on RFI)* or *(on RFI and forecast)* |
| One column per month (`YYYY-MM`) | Demand in **stock units** |
| **Total demand**, **Balance at end** | Balance at end = on hand − safety stock + incoming − total demand; negative is short |

**First short (firm)**, **Order by** and **Late** come from **firm** demand
alone — work orders and firm order lines. A shortage that appears only once RFI
or forecast demand is added isn't something to buy yet: it gets no order-by
date, and **Watch from** says when it would start instead. When firm demand
goes short first, Watch from is blank. The lane's month cells count **all**
demand, so a row can go negative before its first firm shortage — that's the
watch.

The order-by columns are blank for an item firm demand never takes short in the
horizon. On the page, hovering a material's name shows the same answer — *First
short (firm) &lt;month&gt; · order by &lt;date&gt; · &lt;n&gt;-day lead time* (or *no
lead time set*), or *Watch: short from &lt;month&gt; (on forecast)* — and a red
*order late* marker sits beside the name when the order-by date has passed.

!!! info "Why its order-by can differ from the Requirements page's"
    [Requirements](overview.md#requirements) dates each shortage from the exact need-by
    date of the open work orders, netting stock and receipts due in time. The
    outlook works by **month** — the 1st of the first short month, less the lead
    time — and also counts open order lines not yet planned into work. Use the
    outlook for the long view; Requirements is the precise one for released
    work.

!!! warning "When to act, not a buying plan"
    Only the **first** shortage is dated: it tells you when to act. There are no
    order quantities, no rounding to purchase packs, no planned orders, and later
    shortages aren't rolled forward — buying stays in your ERP, which this sheet
    feeds. A wrong lead time gives a wrong order-by date, so keep sourcing
    current.

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

### What it counts

The hours already spoken for are **all the planned load**: work orders, open
order lines not yet on work orders, RFIs (tentative) and the unclaimed forecast
outside the [demand time fence](forecast.md#the-demand-time-fence). So the
forecast alone can turn an answer into *Not by …*.

On a refusal, each short resource says what is standing in the way — *Already
taken by work orders &lt;a&gt;h · order lines not yet planned &lt;b&gt;h · RFI
(tentative) &lt;c&gt;h · unclaimed forecast &lt;d&gt;h* — naming only the kinds
present. Whether real orders or a forecast are in the way is a different
conversation.

### When the order was already forecast

An order you expected shouldn't be refused for colliding with its own forecast.
So the quantity asked for first uses up its part type's **unclaimed** forecast:
its due month, then earlier months nearest first, within the [consumption
window](forecast.md#orders-use-up-the-forecast) — never later months, and never
inside the demand time fence. A later month's forecast is planned after the date
you asked about, so it frees nothing in time.

The due month's **own** forecast is planned as due at the month's end, so its
hours may fall after the date you asked about. Units taken from it still need
free capacity by that date; only units from earlier months come free. The answer
says so:

- *&lt;n&gt; of the &lt;q&gt; were already forecast (&lt;n&gt; in
  &lt;month&gt;, …); &lt;m&gt; need free capacity, which exists by then.* — or *…, which
  isn't there by then.*
- *All &lt;q&gt; were already forecast (…)* — followed by *; &lt;m&gt; need
  free capacity…* when some came from the due month, or *— promisable against
  that forecast.* when none did.
- Beneath, when the due month contributed: *&lt;k&gt; of those come from
  &lt;month&gt;'s own forecast, planned to month end — so they still have to fit
  by the due date.*

So 500 asked for by 25 March, with 150 unclaimed in March and 190 in February,
reads *340 of the 500 were already forecast (150 in 2027-03, 190 in 2027-02);
310 need free capacity* — the 160 not forecast plus March's 150.

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
