# Tracker Overview

The Tracker is the primary interface for monitoring parts as they move through production. This guide explains how to use the Tracker effectively.

## Accessing the Tracker

Navigate to **Tracker** in the Portal section of the sidebar. This is typically the default landing page for production users.

## Tracker Interface

The Tracker displays orders as cards with real-time status:

```
┌─────────────────────────────────────────────────────────┐
│ [Search]                    [Filters] [View Options]    │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌─────────────────────┐        │
│ │ PO-2026-001         │ │ PO-2026-002         │        │
│ │ Acme Manufacturing  │ │ Global Industries   │        │
│ │ ████████░░ 80%      │ │ ██████░░░░ 60%      │        │
│ │ Due: Mar 15         │ │ Due: Mar 20         │        │
│ │ [10 In Process]     │ │ [5 Complete] [3 QA] │        │
│ └─────────────────────┘ └─────────────────────┘        │
│                                                         │
│ ┌─────────────────────┐ ┌─────────────────────┐        │
│ │ PO-2026-003         │ │ PO-2026-004         │        │
│ │ ...                 │ │ ...                 │        │
│ └─────────────────────┘ └─────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

## Order Cards

Each card displays:

| Element | Description |
|---------|-------------|
| **Order Number** | Clickable to open order details |
| **Customer** | Company name |
| **Progress Bar** | Visual completion percentage |
| **Due Date** | Color-coded (green/yellow/red) |
| **Part Counts** | Parts at each status |
| **Priority Badge** | Rush, High, or Normal |

## Expanding Orders

Click an order card to expand and see:

- **Step Distribution** - Parts at each process step
- **Part List** - Individual parts with status
- **Quick Actions** - Move parts, create reports

## Filtering Orders

### Quick Filters

Use the filter bar for common queries:

- **My Orders** - Orders you're assigned to
- **Due Today** - Orders due today
- **Overdue** - Past due date
- **Rush** - High priority orders

### Advanced Filters

Click **Filters** for more options:

| Filter | Options |
|--------|---------|
| **Status** | Draft, In Progress, On Hold, Complete |
| **Customer** | Select specific customer |
| **Due Date** | Date range picker |
| **Part Type** | Filter by part type |
| **Process** | Filter by manufacturing process |

### Saving Filter Presets

1. Configure your filters
2. Click **Save Filter**
3. Name your preset
4. Access it from the filter dropdown

## Searching

The search bar finds orders by:

- Order number (partial match)
- Customer name
- Part serial number
- Lot number

Type and press Enter to search.

## View Options

### Card View (Default)
Orders as visual cards with progress indicators. Best for:

- Quick status overview
- Touch/mobile interaction
- Visual scanning

### Table View
Orders in a sortable table. Best for:

- Large order volumes
- Sorting by columns
- Data export

### Kanban View (if enabled)
Orders as cards in status columns. Best for:

- Workflow visualization
- Drag-and-drop status changes
- Team boards

## Real-Time Updates

The Tracker updates automatically:

- Part movements appear without refresh
- Progress bars update
- Status badges change
- Counts refresh

!!! info "Refresh"
    If you suspect stale data, pull down (mobile) or click the refresh icon.

## Infinite Scroll

Orders load as you scroll:

- Initial load: Most recent/relevant orders
- Scroll down: Older orders load
- Total count shown in header

## Big Screen Mode

For shop floor displays:

1. Click **Big Screen** in the header (or navigate to `/big-screen`)
2. Full-screen display optimized for monitors
3. Auto-cycles through orders
4. Large, readable text

Configure display options:

- Cycle interval
- Orders to show
- Display elements

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `/` | Focus search |
| `↑` `↓` | Navigate orders |
| `Enter` | Open selected order |
| `Esc` | Close expanded order |

## Mobile Usage

The Tracker is fully responsive:

- Cards stack vertically
- Swipe to reveal actions
- Pull to refresh
- Touch-friendly buttons

## Performance Tips

For large order volumes:

1. **Use filters** - Narrow to relevant orders
2. **Archive completed** - Keep active list manageable
3. **Search specifically** - Direct lookup is faster than scrolling

## Next Steps

- [Moving Parts Forward](moving-parts.md) - Pass parts through steps
- [Recording Measurements](measurements.md) - Capture inspection data
- [Flagging Issues](flagging-issues.md) - Report problems
