# Your First Order

This tutorial walks you through creating an order, adding parts, and tracking progress through production. By the end, you'll understand the core workflow of Ambac Tracker.

## Prerequisites

Before starting, ensure you have:

- [x] Logged into Ambac Tracker
- [x] Permission to create orders (ask your admin if unsure)
- [x] At least one Part Type configured in the system
- [x] At least one Process configured for that Part Type

## Step 1: Create an Order

1. Navigate to **Data Management** > **Orders** (or use the quick-add button)
2. Click **+ New Order**
3. Fill in the order details:

| Field | Description | Example |
|-------|-------------|---------|
| **Order Number** | Unique identifier (PO number, SO number) | `PO-2026-001` |
| **Customer** | The company this order is for | `Acme Manufacturing` |
| **Due Date** | When the order should be complete | `2026-03-15` |
| **Notes** | Optional comments | `Rush order - expedite` |

4. Click **Save**

Your order is created but has no parts yet.

## Step 2: Add Parts to the Order

Parts are the individual items being tracked. You can add them manually or in bulk.

### Adding Parts Manually

1. Open your order (click on it in the orders list)
2. In the **Parts** section, click **+ Add Parts**
3. Fill in the part details:

| Field | Description | Example |
|-------|-------------|---------|
| **Part Type** | What kind of part | `Widget Assembly` |
| **Quantity** | How many to create | `10` |
| **Lot Number** | Optional grouping | `LOT-2026-A` |
| **Serial Prefix** | Auto-generates serial numbers | `WA-` |

4. Click **Add**

The system creates individual part records (e.g., `WA-001`, `WA-002`, etc.).

### Bulk Import

For large orders, you can import parts from a CSV file:

1. Click **Import** in the Parts section
2. Download the template
3. Fill in your part data
4. Upload the completed CSV

## Step 3: Create a Work Order

A Work Order connects your order to a manufacturing process:

1. Navigate to **Production** > **Work Orders**
2. Click **+ New Work Order**
3. Select:
   - **Order**: Your order (`PO-2026-001`)
   - **Process**: The manufacturing workflow (`Widget Production Process`)
   - **Priority**: Normal, High, or Rush
4. Click **Save**

The work order is now active, and parts can begin moving through steps.

## Step 4: Track Parts on the Tracker

The **Tracker** page shows all orders and their progress:

1. Navigate to **Tracker** (in the Portal section)
2. Find your order card
3. You'll see:
   - Order number and customer
   - Progress bar showing completion
   - Step distribution (how many parts at each step)

### Moving Parts Forward

As work is completed, parts move through steps:

1. Navigate to **QA Work Orders**
2. Find your order and click the **Pass** button
3. In the "Pass Part by Step" dialog, select the step you completed
4. Click **Submit**

All parts at that step now move to the next step in the process.

!!! tip "Batch Operation"
    The Pass function moves all parts at the selected step together, making batch processing efficient.

## Step 5: Record Measurements (Optional)

If your process requires measurements:

1. Select a part
2. Click **Record Measurements**
3. Enter values for each measurement definition
4. Click **Save**

Measurements are logged with timestamps and user information for traceability.

## Step 6: Handle Issues

If a part has a problem:

1. Select the part
2. Click **Flag Issue** or **Create Quality Report**
3. Choose the error type
4. Describe the issue
5. The part enters quarantine for disposition

Quality issues are tracked separately and require disposition (Use As Is, Rework, Scrap, etc.).

## Step 7: Complete the Order

When all parts finish the final step:

1. Parts automatically move to "Complete" status
2. The order progress shows 100%
3. The order can be marked as shipped/closed

## What You've Learned

Congratulations! You've completed the basic workflow:

- [x] Created an order with customer information
- [x] Added parts to track through production
- [x] Created a work order linking to a process
- [x] Tracked parts through manufacturing steps
- [x] Understood how to handle quality issues

## Next Steps

Explore more features:

- **[Quality Reports](../workflows/quality/quality-reports.md)** - Learn NCR management
- **[Tracker Overview](../workflows/tracking/tracker-overview.md)** - Advanced tracking features
- **[Documents](../workflows/documents/library.md)** - Attach documents to orders
- **[Glossary](glossary.md)** - Reference for all terms
