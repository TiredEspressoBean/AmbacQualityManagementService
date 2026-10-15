# Work Order Progress

Track work order completion, monitor metrics, and manage production flow.

## Progress Overview

Work order progress shows how much work is complete:

```
┌──────────────────────────────────────────────┐
│  WO-2026-0042                    75% ████████░░░│
│  Process: Widget Production                     │
│  Parts: 8/10 complete, 2 in progress           │
└──────────────────────────────────────────────┘
```

## Viewing Progress

### Work Order List

**Production** > **Work Orders** lists: Work Order, Process, **QA Progress**,
Due Date, Customer, Order, and a Details link.

!!! tip "Status and priority are on the Control Center"
    This list carries neither. **WO Control Center** is the fleet view — it
    adds status and priority columns, and filters for **Due today**,
    **Overdue**, **On hold**, **With exceptions** and **Expedited**, plus a
    priority selector. Use it when you are working across many work orders.

!!! important "There is no Expedite button — Expedited is derived"
    A work order counts as **Expedited** when its **priority is Urgent**. To jump
    a job to the front, set its priority; the tile and filter follow from that.

!!! important "A priority change asks why, and keeps the answer"
    Changing priority on **Data Management > Work Orders > edit** requires a
    reason — *"Why change priority from Normal to Urgent?"* — and will not save
    without one. The reason is stored with the change, and the edit form lists
    the last five: *Normal → Urgent · who, when*, with the reason beneath.

    So the trail answers *what, who, when* **and** *why*, which it did not
    before. Setting a priority when you first create the work order needs no
    reason; there is nothing to explain yet.

!!! warning "An import changes priority silently"
    The reason is asked for on the edit form and the API. A CSV import or the
    master workbook can change priority **without** recording one, so a bulk
    re-prioritisation leaves the same gap the edit form now closes. Worth
    knowing before you reach for an import to move a lot of work at once.

## When scrap outruns the gross-up

Planning a work order grosses the started quantity up for **expected** scrap. When
**actual** scrap runs past that, the units still alive fall below the ordered good
count and the job will finish short.

**Make-up planning tops it back up.** It reports the gap, and creating the
replacements is an explicit action:

| Figure | Means |
|--------|-------|
| **Target good** | What the order owes |
| **Alive** | Units not scrapped or cancelled |
| **Shortfall** | What make-up would create |

Replacements are created at the route's **first step**, flagged as make-up, and
the schedule is marked stale so the next solve picks them up.

!!! important "It is planner-confirmed, never automatic"
    The system reports the shortfall; a person creates the replacements. That is
    deliberate for AS9100 and ITAR work — spawning units onto a job is a decision
    with a paper trail, not a side effect of scrapping something.

!!! note "Top-up is iterative, so there is no gross-up on the gross-up"
    The rule is simply *keep alive equal to target*. A replacement that later
    scraps is covered by the next top-up, so nothing needs padding twice.

!!! warning "A reman order owes no make-up"
    Its units are **cores** — someone's actual units, received rather than made.
    A scrapped core cannot be made up by spawning another, so the shortfall is
    always zero there. What a scrapped core needs is a conversation with its
    owner, not a replacement unit.

### Work Order Detail

Detailed progress view includes:

- **Parts by Step**: Bar chart showing distribution
- **Parts Complete**: Count and percentage
- **Parts In Process**: Currently being worked
- **Parts Quarantine**: Held for quality

### On the Home page

There is no separate production dashboard. The **Home** page surfaces work
order state for production roles — jobs going late, work orders in flight, and
the biggest fire — alongside links into the Control Center. See [Role
Guides](../../roles/index.md).

## Progress Calculation

```
Progress % = (Completed Parts / Total Parts) × 100
```

Parts are "completed" when they finish the final step of the process.

## Step Distribution

See where parts are in the process:

| Step | Count | % |
|------|-------|---|
| Machining | 2 | 20% |
| Inspection | 3 | 30% |
| Assembly | 3 | 30% |
| Complete | 2 | 20% |

This helps identify:

- Bottlenecks (parts piling up)
- Idle stations
- Flow issues

## Time Metrics

### Cycle Time
Average time per part through the process.

### Throughput
Parts completed per hour/shift/day.

### Lead Time
Time from work order release to completion.

### Step Duration
Average time at each step.

View metrics on the work order detail or analytics dashboard.

## Status Updates

### Automatic Updates
Status updates automatically based on progress:

| Condition | Status Change |
|-----------|---------------|
| First part moved | Pending → In Progress |
| All parts complete | In Progress → Completed |
| Part quarantined | No change (tracked separately) |

### Manual Updates

Status changes are explicit actions on the work order, not a dropdown:

| Action | Effect |
|--------|--------|
| **Place on hold** | Opens *Put Work Order on Hold*, which requires a **Reason** |
| **Cancel Work Order** | Cancels the work order |
| **Process order** | Moves the order forward |
| **Split…** | Splits the work order |

## Bottleneck Detection

Identify bottlenecks by:

1. **Step Distribution**: Where are parts accumulating?
2. **Wait Time**: How long are parts waiting at each step?
3. **Resource Utilization**: Is equipment/operator maxed out?

Dashboard alerts can highlight:

- Steps with excessive WIP
- Steps with long wait times
- Overdue work orders

## On-Time Tracking

Track on-time delivery:

```
On-Time % = (Work orders completed by due date / Total completed) × 100
```

Work orders are flagged:

- **Green**: On track (due date > 2 days out)
- **Yellow**: At risk (1-2 days to due date)
- **Red**: Overdue

## How current the figures are

Progress figures are **polled, not pushed**. There are no websockets: the
dashboard queries refresh on an interval — every 2 minutes for actionable
items such as failures and approvals, every 5 minutes for slower-moving
summaries.

So a change another user makes appears within a couple of minutes rather than
instantly. Reload if you need the current position immediately.

## Notifications

Configure alerts for progress events:

| Event | Notification |
|-------|--------------|
| Work order complete | Assigned user, supervisor |
| Work order approaching due | Assigned user |
| Work order overdue | Supervisor, planner |
| All parts at final step | Quality team |

## Progress Reports

Generate progress reports:

### Work Order Status Report
- All work orders by status
- Progress percentages
- Due date compliance

### Production Summary
- Daily/weekly output
- By process or equipment
- Trend analysis

### Export Options
- PDF for distribution
- CSV for analysis

## Bulk Progress Updates

For supervisor or planner:

1. Select multiple work orders
2. View aggregate progress
3. Bulk status changes if needed

## Historical Progress

View past performance:

1. Open work order
2. View **History** tab
3. See progress over time
4. Analyze delays or issues

## Permissions

| Permission | Allows |
|------------|--------|
| `view_workorder` | View progress |
| `change_workorder` | Update status |
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar |

## Next Steps

- [First Piece Inspection](fpi.md) - FPI workflow
- [Analytics Dashboard](../../analysis/dashboard.md) - Production metrics
- [Work Order Basics](basics.md) - Core concepts
