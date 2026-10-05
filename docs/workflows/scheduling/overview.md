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
| **Operator Hours** | Attendance and time clocked onto jobs |
| **Requirements** | What to buy, build, and procure to hit the schedule |

The Gantt is the board everything else supports. The calendar feeds it working
time, capacity is the coarse long-range layer above it, and staging, hours, and
requirements are its reports.

## Calendar

**Plant closures and who's out — the non-working time the scheduler plans
around.**

Click one or more days, then add:

- **Add closure** — a plant shutdown
- **Add absence / meeting** — someone unavailable
- **Add overtime** — extra working time
- **Add recurring…** — a repeating pattern

Filter by **Company** / **My crew** / **Me**, and by shift or work center.

Everything recorded here is time the scheduler will not plan into. Keeping it
current is what makes the Gantt's dates believable.

## Staging List

**What to put at each bench before the operator gets there — the next 8 hours
of scheduled work.**

View **By station** or **By material**, filter to a single station, and export
to **PDF** for the floor.

!!! warning "Watch for the staleness banner"
    The staging list is derived from the last solve. If the schedule has moved
    since, the page warns that the times may have changed and prompts a re-solve.
    A stale staging list sends material to the wrong bench.

## Operator Hours

**Shop hours per operator — on-shift attendance and time clocked onto jobs.**
Covers shop-floor operators only (Operator and Shift Lead).

Shows total **on-shift hours** against total **direct (job) hours** for a date
range, per operator. The gap between the two is time at work but not clocked
onto a job.

Exports to **CSV** and **PDF**.

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

You give one **PO number** for the whole set, then per row a **quantity**
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

    Which is why it asks for a PO number: you are telling UQMES an order already
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
