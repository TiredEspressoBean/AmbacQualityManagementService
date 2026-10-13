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
fetched when the page loads and are then cached, so a change made elsewhere
appears the next time you open or reload the page — not while you sit on it.

## Order Cards

Each card shows:

| Element | Description |
|---------|-------------|
| **Order name** | The order's name, e.g. "Great Lakes Diesel Order - 12 Injectors" |
| **Company** | Who the order is for. The Tracker does not pass a customer name, so no individual contact appears here |
| **Delivery** | The delivery date, with a badge for how far away it is — "Today" or "6d". The badge is dropped once the date is past, leaving the date alone |
| **Current stage** | The stage the order is at, e.g. "Current: Core Receiving" — or "Not started" when no stage is current |
| **Progress** | A progress bar with stages completed out of total, e.g. 3/11 stages |
| **Latest note** | The most recent note on the order, with who left it |

!!! note "No priority on the tracker"
    Cards carry no priority badge. Priority is a work order field — see
    [Work Order Basics](../work-orders/basics.md).

## Expanding Orders

Cards are collapsible. Click one to expand it and see the order's detail
in place.

## Finding an order

!!! note "No search or filters here"
    The Tracker has no search box and no filter controls — it is one list of
    cards you scroll. To search or filter, use the **Work Orders** page
    (Production > Work Orders), which has both.

## Card View

The Tracker displays orders as visual cards with progress indicators. This view is optimized for:

- Quick status overview
- Touch/mobile interaction
- Visual scanning

!!! note "Additional Views"
    Table View and Kanban View are planned for future releases. Currently, the Tracker uses the card view with infinite scroll.

## Keeping the page current

The Tracker does not refresh itself. Cards are rendered from cached data and
stay as they were until you reload the page — there is no refresh button, and
nothing updates while you watch it.

## Infinite Scroll

Orders load as you scroll:

- Initial load: Most recent/relevant orders
- Scroll down: Older orders load

## Mobile Usage

The Tracker is fully responsive — cards stack vertically and the controls are
touch-sized. There are no swipe or pull-to-refresh gestures.

## Next Steps

- [Moving Parts Forward](moving-parts.md) - Pass parts through steps
- [Recording Measurements](measurements.md) - Capture inspection data
- [Flagging Issues](flagging-issues.md) - Report problems
