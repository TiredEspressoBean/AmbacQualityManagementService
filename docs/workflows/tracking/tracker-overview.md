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
│ │ ORD-2024-0042       │ │ ORD-2024-0038       │        │
│ │ Midwest Fleet       │ │ Great Lakes Diesel  │        │
│ │ ████████░░ 67%      │ │ ██████████ 100%     │        │
│ │ Due: Mar 15         │ │ Complete            │        │
│ │ [16 Complete][2 QA] │ │ [12 Shipped]        │        │
│ └─────────────────────┘ └─────────────────────┘        │
│                                                         │
│ ┌─────────────────────┐                                │
│ │ ORD-2024-0048       │                                │
│ │ Northern Trucking   │                                │
│ │ ░░░░░░░░░░ 0%       │ [HIGH] Due: Mar 20            │
│ │ [Pending]           │                                │
│ └─────────────────────┘                                │
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

## Searching

!!! note "Filtering"
    Advanced filtering and filter presets are planned for the Tracker page. Currently, use the search functionality or access filtered views through the **Work Orders** page (Production > Work Orders) which has more filtering options.

## Search Bar

The search bar finds orders by:

- Order number (partial match)
- Customer name
- Part serial number
- Lot number

Type and press Enter to search.

## Card View

The Tracker displays orders as visual cards with progress indicators. This view is optimized for:

- Quick status overview
- Touch/mobile interaction
- Visual scanning

!!! note "Additional Views"
    Table View and Kanban View are planned for future releases. Currently, the Tracker uses the card view with infinite scroll.

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
