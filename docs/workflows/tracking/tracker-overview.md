# Tracker Overview

The Tracker is the primary interface for monitoring parts as they move through production. This guide explains how to use the Tracker effectively.

## Accessing the Tracker

Click **Tracker** in the sidebar — it sits near the top, with Home and
Help & Docs, and is available to every signed-in user.

!!! note "Not the landing page"
    **Home** is the landing page, and it is role-aware — an Operator, a QA
    Inspector and a Production Manager each land on a different surface. The
    Tracker is the order-status view, reached deliberately. See [Role
    Guides](../../roles/index.md).

## Tracker Interface

The Tracker displays orders as cards showing current status. Figures are
polled rather than pushed, so a change made elsewhere appears within a couple
of minutes rather than instantly.

## Order Cards

Each card shows:

| Element | Description |
|---------|-------------|
| **Order name** | The order's name, e.g. "Great Lakes Diesel Order - 12 Injectors" |
| **Company** and **customer** | Who the order is for |
| **Delivery** | The delivery date, with a badge for how far away it is — "Today", "6d", or "Not started" |
| **Current stage** | The stage the order is at, e.g. "Current: Core Receiving" |
| **Progress** | A progress bar with stages completed out of total, e.g. 3/11 stages |
| **Latest note** | The most recent note on the order, with who left it |

!!! note "No priority on the tracker"
    Cards carry no priority badge. Priority is a work order field — see
    [Work Order Basics](../work-orders/basics.md).

## Expanding Orders

Cards are collapsible. Click one to expand it and see the order's detail
in place.

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
