# Scheduling

The **Scheduling** section plans when work happens: which job runs on which
resource, in what order, and whether the plant can absorb what's been promised.

!!! info "Where to find it"
    **Scheduling** in the sidebar. It's collapsed by default — click the section
    header to expand it.

## The surfaces

| Page | Answers |
|------|---------|
| **[Schedule (Gantt)](gantt.md)** | What runs where, and in what order |
| **Calendar** | When the plant is *not* working |
| **[Capacity Planning](capacity.md)** | Can we absorb the next 12 months of demand? |
| **Staging List** | What to put at each bench before the operator arrives |
| **Operator Hours** | Attendance, and the job time on operators' step records |
| **Requirements** | What to buy, build, and procure to hit the schedule |

The Gantt is the board everything else supports. The calendar feeds it working
time, capacity is the coarse long-range layer above it, and staging, hours, and
requirements are its reports.

## Calendar

**Plant closures, who's out, and overtime — the working time the scheduler plans
against.**

Click one or more days, then add:

- **Add closure** — a plant shutdown
- **Add absence / meeting** — someone unavailable
- **Add overtime** — extra working time
- **Add recurring…** — a repeating pattern

Filter by **Company** / **My crew** / **Me**, and by shift or work center.

Closures and absences are time the scheduler will **not** plan into; overtime
works the other way, adding working time it **will** plan into. Either way the
calendar is what the solver treats as available hours, and keeping it current is
what makes the Gantt's dates believable.

An entry made wrong (the wrong day, the wrong crew) is removed and added again.
Each entry in the day's list has its own **Remove**, named for what it removes,
and it asks you to confirm. Then **re-solve**, since the plan was made against the
calendar as it stood.

## Staging List

**What to put at each bench before the operator gets there — the next window of
scheduled work.**

View **By station** or **By material**, filter to a single station, choose the
window — **4h / 8h / 12h / 24h**, defaulting to 8 — and export to **PDF** for
the floor.

Each station shows its jobs with a staged count (*2 jobs · 0/2 staged*), and
each job lists its materials with quantity, **source lot** and **location** —
*Injector Spring ×4 · STOCK-CRI-SPR · Main Stores*. Optional lines are marked
**(optional)**. A step that consumes nothing says so rather than showing an
empty table.

### Recording what was picked

| Action | Does |
|--------|------|
| **Confirm** | Marks that line staged; the station count moves, and it records who staged it |
| **Took another** | You picked a different lot than the one suggested — records the lot actually taken |
| **Mark staged** | The whole job at once |

!!! tip "\"Took another\" is not an error path"
    The picker grabs what is physically nearest. Recording the real lot is what
    keeps traceability honest — the suggestion was only a suggestion.

!!! warning "An empty list is usually the window, not a fault"
    The page defaults to **8 hours**. On a plant holiday, a shutdown, or a quiet
    shift that is legitimately empty, and it says so: *"Nothing scheduled in this
    window. Try a longer window, or check the schedule board."*

    **Widen the window before concluding anything is broken.** This doubles as
    the quickest way to confirm a calendar exception reached the solver — add a
    holiday, and that day's 8-hour view empties while a 24-hour one does not.

!!! warning "Watch for the staleness banner"
    The staging list is derived from the last solve. If the schedule has moved
    since, the page warns that the times may have changed and prompts a re-solve.
    A stale staging list sends material to the wrong bench.

## Operator Hours

**Shop hours per operator — on-shift attendance, and the time on their step
records.** Covers shop-floor operators only (Operator and Shift Lead).

For a date range, per operator:

| Column | Is |
|--------|----|
| **On-shift hrs** | Time clocked in, less breaks and lunch |
| **Direct hrs** | Time working at steps, counted only while on shift |
| **Rework hrs** | The part of direct time spent on rework — included in direct, not added to it |
| **Unallocated hrs** | On-shift minus direct: at work, but not at a step |

Four cards above the table give the totals. The page, its **CSV** and its **PDF**
all use the same figures.

### Where direct time comes from

Nobody clocks onto a job. Direct time is worked out from the step records an
operator already makes by starting and completing work:

- A step's time runs from when the operator started it until the part left the
  step — or until now, while it is still running. It is credited to the operator
  who claimed it, or to whoever completed it.
- It counts only while that operator was **on shift**: no clock-in, no direct
  time; breaks and lunch are excluded.
- Work running at the same time is **shared, not added**. A lot at one step is
  one stretch of time, not one per part; two jobs at once split the time in
  proportion to their parts.
- Time while the work order was **on hold**, or the part was **out for outside
  processing**, is left out.
- **Rework** is a repeat visit to a step, or a rework step.
- Setup and run time are not separated.

### By work order

Below the table, **By work order** splits the same direct time by work order
and operator, with rework — *for costing in the system that prices it*. Its
**CSV** and **Excel** exports need `export_data`, and each export is recorded.
The same figures for one job are on the work order's **Labor** tab — see
[Work Order Basics](../work-orders/basics.md).

### Approving time

The **Awaiting approval** card lists finished attendance entries — shift,
break and lunch — in the page's date range that nobody has approved yet, with
operator, type, start and hours. **Approve** one at a time, or **Approve all
(N)**. Job time is not approved line by line: it follows from the step records
and from the attendance it is clipped to, so correcting a clock time corrects
the direct hours too.

You can't approve your own time: your entries read *Your time*, with no button.
An entry still running can't be approved until it ends. Approving needs
`approve_timeentry`, held by default by **Shift Lead**, **Production Manager**
and **Tenant Admin**. Without it the card isn't shown.

**Correct times** on an entry fixes a clock-in or clock-out that was wrong, before
it is approved: change the time, give a **reason**, and the hours recalculate. Each
change and its reason are kept on the entry. Correct first, approve second: an
approved entry leaves this card, and can't be corrected here.

## Requirements

**What open demand needs — material to buy, components to build, tooling to
procure — with order-by dates from the live schedule.**

Four sections, one under another on the page:

| Section | Covers |
|---------|--------|
| **Source (buy)** | Purchased material short of coverage — see [Turning a shortage into an expected delivery](#turning-a-shortage-into-an-expected-delivery) |
| **Recover (tear down)** | Teardown proposed to refill recovered stock — see [Planning a teardown](#planning-a-teardown) |
| **Produce (build)** | In-house component work orders pegged to open demand |
| **Tooling** | Fixtures, tools, dies and NC programs not yet on hand |

### Turning a shortage into an expected delivery

Each **Source (buy)** row has a checkbox, with select-all in the header, and the
material cell shows its **part number** and **preferred supplier** under the
name. Tick rows and **Add expected deliveries (N)** opens *Add expected
deliveries*.

You can give one **PO number** for the whole set (optional), then per row a **quantity**
(pre-filled with the shortage), a **promised date** (pre-filled one lead time
from today), a **supplier** (pre-filled with the preferred one) and a **PO
line**. It records every row or none.

The shortage then reads as covered, because the expected receipts now exist as
incoming supply.

!!! important "Nothing is purchased here"
    This closes the loop between *what we are short of* and *what we are
    expecting*, so planning stops flagging a gap someone has already dealt with.
    The buying itself happens in the system that owns it — you are recording the
    answer, not making it.

    Which is why it offers a PO number: you are telling UQMES an order already
    exists. See [Loading what is on
    order](../supply/overview.md#loading-what-is-on-order).

### Planning a teardown

**Recover** is the bridge between the core bank and buying. Rather than
purchasing a component, it asks whether tearing down cores you already hold
would cover the need — each row naming the core type, how many are **in bank**
and already committed, what the teardown would **cover** (*"2.3 of 5 needed · 1
on shelf · 1.7 on the way"*), and a start-by date.

**Plan teardown** commits those cores to a future teardown work order. Nothing
on the page commits a core on its own.

!!! note "This is for exchange rebuilds"
    Recovered stock refills the pool that exchange units are rebuilt from. A
    repair-and-return unit is rebuilt with its own components, so it never draws
    on this. See [Rebuild](../reman/rebuild.md#two-kinds-of-replace).

Note this is the **plan-ahead** path. Tearing a core down now starts from the
core itself — see [Teardown](../reman/disassembly.md).

Order-by dates come from the live schedule, so they move when the schedule
moves. Rows past their order-by date are flagged.

Exports to **CSV** and **PDF**.

## Next Steps

- **[Schedule (Gantt)](gantt.md)** - The planning board
- **[Capacity Planning](capacity.md)** - The long view
