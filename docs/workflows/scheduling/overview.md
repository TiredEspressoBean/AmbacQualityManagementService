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

Three tabs:

| Tab | Covers |
|-----|--------|
| **Source (buy)** | Material to purchase |
| **Produce (build)** | Components to manufacture |
| **Tooling** | Tooling to procure |

Order-by dates come from the live schedule, so they move when the schedule
moves. Rows past their order-by date are flagged.

Exports to **CSV** and **PDF**.

## Next Steps

- **[Schedule (Gantt)](gantt.md)** - The planning board
- **[Capacity Planning](capacity.md)** - The long view
