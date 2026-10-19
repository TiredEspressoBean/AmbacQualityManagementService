# Order Status

Monitor order progress and understand status indicators throughout uqmes.

## Viewing Order Status

### Tracker Page

The main **Tracker** page shows orders as cards, 25 at a time, loading more as
you scroll:

- **Order name** and the **company** it is for
- **Delivery date**, with a badge — days remaining ("6d"), **Today**, or a red
  **Overdue · 3d** once the date has passed
- **Current stage** - the stage the order is at, or "Not started"
- **Progress bar** - stages completed out of total

The card carries no part counts and no order-status badge — for those, open the
order.

!!! note "How the badge counts"
    Days are counted as calendar days, so an order due tomorrow reads **1d** all
    day today. A **completed** or **cancelled** order shows its date with no
    badge, late or not. The same badge appears on the order page, and on the
    Tracker a customer sees.

!!! note "There is no search or filter on the Tracker"
    It lists every order you can see, completed and cancelled included, in one
    scrolling column. Orders with no stages and no milestone yet are left off,
    and when that leaves nothing, the page says *No active orders to display*.

    To find a particular order, use the orders list in **Data Management**,
    which searches by order name, company, and customer name.

### Order Detail Page

Click an order to open it. The page carries:

- The **delivery date**, with the same badge — days remaining, **Today**, or
  **Overdue · N days**. If it has moved, *Originally <date>* shows the first
  date, struck through
- **Progress** through its stages, and the **Stages** list itself
- **Notes**, as a timeline
- **Line Items** — per part type, ordered, planned and remaining
- **Parts on this order** — each part with its type, step and status. Staff only:
  it needs `change_orders`, and customers do not see it
- **Shipping** — shipped against ordered per line, the shipments themselves, and
  late lines flagged
- **Details**
- **Documents** attached to the order
- **People** with access to it

### When the delivery date moves

The first time an order's delivery date changes, uqmes keeps the earlier date as
the **original**, and it is never overwritten after that. It counts as a move
whoever made it: an edit to the order, an import, the CRM sync, or a work order
whose expected completion pushed the order later. An order given its first date
has not slipped.

### Dashboard KPIs

!!! note "There are no order-delivery KPIs"
    The **Analytics** dashboard's figures are quality figures — first pass
    yield, scrap and rework rates, open issues, active and overdue CAPAs. There is no average cycle time, no "orders due this week" and
    no "orders at risk" tile.

    On-time delivery *is* measured — on **Shipping**, over the last 90 days. See
    [Shipping](../supply/shipping.md#seeing-whether-you-are-on-time).

## Progress Calculation

Order progress is counted in **stages, not parts**:

```
Progress = Completed stages / Total stages × 100%
```

The stages are the steps of the work order's process, in order. A stage counts
as complete when no active part is sitting on it and at least one part has
reached a later step.

For example:
- 11 stages on the order
- 3 complete
- Progress = 3 / 11 = 27%

## Status Indicators

### Order Status

| Status | Meaning |
|--------|---------|
| **RFI** | Request for information — not yet a firm order |
| **Pending** | Created, not started |
| **In progress** | Work underway |
| **On hold** | Temporarily paused |
| **Completed** | Finished |
| **Cancelled** | Will not be made |

### Part Status

Eighteen, in four groups.

**Moving through the work**

| Status | Meaning |
|--------|---------|
| **Pending** | Created, not yet started |
| **In Progress** | Being worked on |
| **At Outside Process** | Sent to a subcontract vendor — the part has left the building |
| **Awaiting QA** | Step done, waiting for inspection |
| **Ready for next step** | Can move on |
| **Completed** | Passed all steps |

**Held**

| Status | Meaning |
|--------|---------|
| **Quarantined** | Held for quality review |
| **Rework Needed** | Sent back for rework |
| **Rework In Progress** | Rework underway |
| **On Hold** | Parked on a decision someone else owns — a customer's authorisation, a release call after teardown |

**Finished**

| Status | Meaning |
|--------|---------|
| **Shipped** | Gone to the customer |
| **In Stock** | Completed into inventory |
| **Awaiting Pickup** | Ready for the customer to collect |
| **Scrapped** | Rejected permanently |
| **Cancelled** | Removed before production finished |

**Reman**

| Status | Meaning |
|--------|---------|
| **Core Banked** | Stored as a core |
| **RMA Closed** | Return completed |
| **Dismantled** | Torn down; its components became parts of their own |

!!! note "On Hold is not finished, and Dismantled is not output"
    **On Hold** is deliberately not a terminal status — if it were, a work
    order could close around a unit that is still waiting on someone.

    **Dismantled** *does* count as done for an order's progress, because a
    teardown order's job is to get its units taken apart. It never counts as
    something produced.

## Finding orders

The **Tracker** has no search. The orders list in **Data Management** searches
by **order name**, **company name**, and the **customer's first or last name** —
not by part serial number and not by notes. To get from a serial number to its
order, look the part up instead.

## Notifications

Who is told about what is decided by this organisation's **notification
rules**, not by the order itself. See [Notification
Rules](../../admin/setup/notification-rules.md).

## Exporting Status

1. Open the orders list in **Data Management**
2. Search or filter it
3. Choose **Export**, then **Excel** or **CSV**

The export takes the list's current search and filters. There is no column
picker in the interface; the file carries every exported column. See [Import &
Export](../../admin/data/import-export.md).

## Customer Portal View

Customers with portal access see:

- Their orders only
- Status and progress
- Document attachments
- Simplified view (no internal data)

## Next Steps

- [Order Documents](order-documents.md) - Attach files to orders
- [Tracker Overview](../tracking/tracker-overview.md) - Detailed tracking
- [Analytics](../../analysis/dashboard.md) - Quality metrics and trends
