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

The work order list shows:

- Progress bar per work order
- Status badge
- Priority indicator
- Due date (color-coded)

### Work Order Detail

Detailed progress view includes:

- **Parts by Step**: Bar chart showing distribution
- **Parts Complete**: Count and percentage
- **Parts In Process**: Currently being worked
- **Parts Quarantine**: Held for quality

### Dashboard Widgets

The Production Dashboard shows:

- Active work orders
- On-time vs. delayed
- Completion rate
- Work in process (WIP)

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
| First part moved | Draft → In Progress |
| All parts complete | In Progress → Complete |
| Part quarantined | No change (tracked separately) |

### Manual Updates
Change status manually when needed:

1. Open work order
2. Click status dropdown
3. Select new status
4. Enter reason (for hold/cancel)

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

## Real-Time Updates

Progress updates in real-time:

- Parts move → Progress bar updates
- No refresh needed
- Changes visible to all users

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
- Scheduled email reports

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
| `view_analytics` | View reports |

## Next Steps

- [First Piece Inspection](fpi.md) - FPI workflow
- [Analytics Dashboard](../../analysis/dashboard.md) - Production metrics
- [Work Order Basics](basics.md) - Core concepts
