# Order Status

Monitor order progress and understand status indicators throughout Ambac Tracker.

## Viewing Order Status

### Tracker Page

The main **Tracker** page shows all orders as cards:

- **Progress bar** - Visual completion percentage
- **Part counts** - How many parts at each step
- **Status badge** - Current order status
- **Due date** - With overdue highlighting

### Order Detail Page

Click an order to see detailed status:

- **Summary cards** - Parts complete, in process, on hold
- **Step distribution chart** - Parts by step
- **Recent activity** - Latest transitions and events

### Dashboard KPIs

The **Analytics** dashboard shows aggregate metrics:

- Orders due this week
- On-time delivery rate
- Average cycle time
- Orders at risk (behind schedule)

## Progress Calculation

Order progress is calculated as:

```
Progress = (Parts at final step + Completed parts) / Total parts × 100%
```

For example:
- 10 total parts
- 3 completed
- 2 at final step
- Progress = (3 + 2) / 10 = 50%

## Status Indicators

### Order Status

| Status | Color | Meaning |
|--------|-------|---------|
| **Draft** | Gray | Not started |
| **In Progress** | Blue | Work underway |
| **On Hold** | Yellow | Temporarily paused |
| **Complete** | Green | All parts finished |
| **Shipped** | Green | Delivered |
| **Cancelled** | Red | Order cancelled |

### Part Status

| Status | Color | Meaning |
|--------|-------|---------|
| **In Process** | Blue | Moving through steps |
| **Quarantine** | Yellow | Held for quality |
| **Complete** | Green | Finished |
| **Scrapped** | Red | Disposed |

### Due Date Indicators

| Indicator | Meaning |
|-----------|---------|
| **Green** | On track (>3 days to due date) |
| **Yellow** | Approaching (1-3 days) |
| **Red** | Overdue or due today |

## Filtering Orders

Use filters to find specific orders:

### By Status
- Show only "In Progress" orders
- Hide completed orders
- Find orders on hold

### By Customer
- View orders for specific customer
- Compare across customers

### By Date
- Due this week
- Due this month
- Overdue only

### By Priority
- Rush orders
- High priority
- Normal

## Searching Orders

The search bar finds orders by:

- Order number
- Customer name
- Part serial numbers
- Notes content

## Order Timeline

View the history of an order:

1. Open the order
2. Click the **History** or **Activity** tab
3. See chronological events:
   - Order created
   - Parts added
   - Status changes
   - Step transitions
   - Quality reports

## Notifications

Configure alerts for order events:

- Order approaching due date
- Order status changed
- Parts entering quarantine
- Order completed

See your **Profile** > **Notification Preferences** to configure.

## Exporting Status

Export order status for reporting:

1. Navigate to **Orders**
2. Apply desired filters
3. Click **Export**
4. Select columns to include
5. Download CSV

## Customer Portal View

Customers with portal access see:

- Their orders only
- Status and progress
- Document attachments
- Simplified view (no internal data)

## Next Steps

- [Order Documents](order-documents.md) - Attach files to orders
- [Tracker Overview](../tracking/tracker-overview.md) - Detailed tracking
- [Analytics](../../analysis/dashboard.md) - Order metrics and trends
