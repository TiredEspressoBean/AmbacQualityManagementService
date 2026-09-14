# Your First Order

This tutorial walks you through creating an order, adding parts, and tracking progress through production. By the end, you'll understand the core workflow of uqmes.

## Prerequisites

Before starting, ensure you have:

- [x] Logged into uqmes
- [x] Permission to create orders (ask your admin if unsure)
- [x] At least one Part Type configured in the system
- [x] At least one Process configured for that Part Type

## Step 1: Create an Order

1. Navigate to **Admin** > **Data Management** > **Orders**
2. Click **New Orders**
3. Fill in the order details:

| Field | Description | Example |
|-------|-------------|---------|
| **Order Name** *(required)* | Identifier for the order | `ORD-2024-0048` |
| **Company** | The company the order belongs to | `Northern Trucking Co` |
| **Customer** | The customer contact on the order | `Tom Bradley` |
| **Estimated Completion** | When the order should be complete | `2026-03-15` |
| **Order Status** | Current state of the order | `Pending` |

4. Click **Create Order**

Your order is created but has no parts yet.

## Step 2: Add Parts to the Order

Parts are the individual items being tracked. You can add them manually or in bulk.

### Adding Parts Manually

1. Open your order (click on it in the orders list)
2. In the **Parts** section, click **Add Parts**
3. Fill in the part details:

| Field | Description | Example |
|-------|-------------|---------|
| **Part Type** | What kind of part | `Common Rail Injector` |
| **Process** | The manufacturing workflow to run | `Common Rail Injector Remanufacturing` |
| **Step** | Which step the parts start at | `1. Teardown` |
| **Quantity** | How many to create | `8` |
| **ERP ID start** | Starting identifier; subsequent parts increment from it | `INJ-0048-001` |
| **Status** | Initial part status | `In Progress` |

4. Click **Add Parts**

The system creates individual part records (e.g., `INJ-0048-001`, `INJ-0048-002`, etc.).

### Bulk Import

For large orders, you can import parts from a CSV file:

1. Click **Import** in the Parts section
2. Download the template
3. Fill in your part data
4. Upload the completed CSV

## Step 3: Create a Work Order

A Work Order connects your order to a manufacturing process:

1. Navigate to **Admin** > **Data Management** > **Work Orders**
2. Click **New Work Orders**
3. Select:
   - **Order**: Your order (`ORD-2024-0048`)
   - **Process**: The manufacturing workflow (`Common Rail Injector Remanufacturing`)
   - **Priority**: Urgent, High, Normal, or Low
4. Click **Save**

The work order is now active, and parts can begin moving through steps.

!!! note
    **Production > Work Orders** is a read-only list — it has no create button.
    Create work orders from the Data Management editor above.

## Step 4: Track Parts on the Tracker

The **Tracker** page shows all orders and their progress:

1. Navigate to **Tracker**
2. Find your order card
3. You'll see:
   - Order number and customer
   - Progress bar showing completion
   - Step distribution (how many parts at each step)

### Moving Parts Forward

**Parts advance automatically.** There is no "move to next step" button in the
normal flow. Advancement fires reactively whenever work at a step is recorded —
completing a substep, sealing a batch, splitting a part, or approving an
override. When the step's requirements are satisfied, the parts move on by
themselves.

!!! tip "Lot cohesion"
    Parts that have not been split advance **as a cohort**: all parts at the
    same work order and step move together, or none of them do. A part that has
    been split from the lot advances on its own as soon as its own requirements
    clear.

See [Digital Work Instructions](../workflows/dwi/overview.md) for how a step's
substeps work.

So to move parts forward, do the work the step asks for — record the
measurements, complete the inspection, finish the substeps. The system handles
the transition.

!!! warning "Force advance is for emergencies"
    The work order control page has a **force advance** control, labelled in the
    UI as *"Force advance step (emergency; default flow is event-driven)"*. It
    bypasses the requirements that normally gate a step. Use it only to recover
    from a stuck state, not as part of routine operation.

## Step 5: Record Measurements (Optional)

Measurements are recorded as part of the work at a step rather than from a
standalone button on the part:

- During **Incoming Inspection**, via **Record Measurements** on the lot
- As part of a **Quality Report**, which captures measurement results against
  each measurement definition
- Inside the operator step runtime, where a step defines measurement substeps

Measurements are logged with timestamps and user information for traceability.
See [Recording Measurements](../workflows/tracking/measurements.md).

## Step 6: Handle Issues

If a part has a problem:

1. Go to **Quality** > **Quality Reports**
2. Create a quality report against the part
3. Choose the error type and describe the issue
4. The part enters quarantine for disposition

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
