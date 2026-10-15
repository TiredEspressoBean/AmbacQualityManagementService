# Production Manager Guide

This guide is for Production Managers who manage orders, work orders and
production operations in uqmes.

!!! tip "Planning and scheduling have their own guide"
    Releasing work onto the floor, promising dates, and running the schedule
    are covered in the [Planner Guide](planner.md). This guide covers the
    production side.

!!! tip "Demo Account"
    In demo mode, log in as **Jennifer Walsh** (jennifer.mgr@demo.ambac.com) to experience the Production Manager workflow. You'll see:

    - 3 orders in different states: ORD-2024-0042 (in progress), ORD-2024-0038 (completed), ORD-2024-0048 (pending)
    - Work order WO-2024-0042-A in progress with 67% completion
    - CAPA-2024-003 that you own (nozzle defect investigation)
    - Pending approval APR-2024-0015 (CAPA closure requiring your sign-off)
    - Equipment alert: Torque Wrench TW-25 calibration overdue

## Your Role

As a Production Manager, you:

- Create and manage customer orders
- Create work orders and assign resources
- Monitor production progress
- Manage production priorities
- Coordinate with quality and shipping
- Track on-time delivery

## Getting Started

### First-Time Setup

1. Log in and review the system
2. Configure your notification preferences
3. Familiarize yourself with order flow

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Work Orders** | Production > Work Orders | Main production management |
| **Orders** | Data Management > Orders | Customer order management |
| **Tracker** | Tracker | Customer-facing order overview |
| **Analytics** | Analytics | Production metrics |
| **Inbox** | Personal > Inbox | CAPA tasks and approval requests |

## Daily Workflow

### 1. Review Production Status

1. Navigate to **Production** > **Work Orders**
2. Check work order progress
3. Identify behind-schedule orders
4. Note bottlenecks

### 2. Manage Priorities

1. Review rush and high-priority work orders
2. Adjust priorities as needed
3. Communicate changes to floor supervisors

### 3. Handle Exceptions

1. Check **Inbox** for CAPA tasks and approval requests
2. Address quality holds via **Quality** > **Dispositions**
3. Resolve resource conflicts
4. Update customer if needed

## Creating Orders

### New Order Entry

1. Navigate to **Data Management** > **Orders**
2. Click **New Orders**
3. Fill in order details:

| Field | Description | Required |
|-------|-------------|----------|
| **Order Name** | Your PO/SO number | **Yes — the only one** |
| **Company** / **Customer** | Who placed it | No |
| **Estimated Completion** | Target completion | No |
| **Notes** | Special instructions | No |

4. Click **Create Order**

The order *number* (`ORD-YYYY-NNNN`) is generated for you. Orders have **no
priority field** — priority lives on the work order.

### Adding Parts

!!! warning "Not from the order page"
    The order detail page is read-only and has no **Add Parts** control. Parts
    are added against the **work order**.

1. Go to **Production** > **WO Control Center**
2. Tick exactly one work order — the bulk bar appears at the bottom
3. Click **Add Parts** in the bulk bar
4. Specify:
   - **Start Step** — where the parts begin
   - **Quantity**
   - **ERP ID Start** — the counter ERP IDs start from
5. Confirm

Part Type is shown, not chosen: it comes from the work order's process. ERP IDs
are `<part type prefix><counter padded to 4 digits>`.

### Bulk Order Import

For multiple orders:
1. Click **Import**
2. Download CSV template
3. Fill in order data
4. Upload and confirm

## Creating Work Orders

### Linking Order to Process

1. Navigate to **Data Management** > **Work Orders**
2. Click **New Work Orders**
3. Fill in:
   - **ERP ID** — the work order's number in the system that owns it (required)
   - **Process** (required)
   - **Priority** (required)
   - **Due date** (required)
   - **Order** — the customer order, if there is one (optional)
4. Save

!!! note "ERP ID is required and easy to miss"
    The save fails without it. It is the work order's identifier in whatever
    system owns the number.

### Work Order Settings

| Field | Purpose |
|-------|---------|
| **Priority** | Urgent, High, Normal, Low |
| **Equipment** | Assigned machine |
| **Notes** | Production instructions |

## Managing Production

### Monitoring Progress

On **Work Orders** page:
- Detailed progress by work order
- Parts by step
- Time metrics
- Priority and status indicators

On **Tracker** (for customer-facing overview):
- Progress bars show completion
- Color coding shows on-time status
- Expand for step distribution

### Identifying Bottlenecks

Look for:
- Steps with many parts waiting
- Work orders not progressing
- Equipment conflicts
- Resource shortages

### Adjusting Priorities

1. Open work order
2. Change priority level
3. Save
4. Notify floor supervisor

## Handling Quality Holds

When parts are quarantined:

1. View quarantined parts in **Quality** > **Dispositions**
2. Understand the issue
3. Coordinate with Quality
4. Adjust schedule if needed
5. Update customer if delayed

### Expediting Dispositions

For urgent orders:
- Contact QA Manager
- Provide business context
- Request prioritized disposition

## Resource Management

### Equipment Assignment

!!! note "Step-Level Assignment"
    Equipment is assigned when executing individual steps, not at the work order level. This allows different equipment to be used for different steps in the process.

Equipment tracking:

1. Equipment is selected during step execution
2. Each step records which equipment was used
3. Equipment usage is tracked for calibration and maintenance
4. Check equipment availability via the Equipment page

### Capacity Planning

Consider:
- Equipment availability
- Operator scheduling
- Process cycle times
- Quality inspection time

## Customer Communication

### Order Status Updates

When customers inquire:
1. Open the order in **Data Management** > **Orders** or view on **Tracker**
2. Review progress and ETD
3. Check for quality issues
4. Provide accurate status

### Delay Notification

When orders will be late:
1. Document the reason
2. Calculate new estimate
3. Notify customer proactively
4. Update order notes

## Working with Documents

### Order Documents

Attach relevant documents:
- Customer PO
- Drawings
- Special instructions
- Certificates

### Accessing Work Instructions

Ensure operators can access:
1. Link documents to work order
2. Verify latest revision
3. Check accessibility

## Analytics and Reporting

### Production Metrics

Review regularly:
- **On-time delivery** rate
- **Throughput** by area
- **WIP** levels
- **Cycle time** trends

### Reports

Generate for management:
- Daily production summary
- Weekly status report
- Customer-specific reports

## Coordination

### With Quality

- Understand hold reasons
- Expedite when needed
- Address recurring issues

### With Shipping

- Coordinate completed orders
- Prepare ship documentation
- Confirm delivery schedule

### With Customer Service

- Provide status updates
- Flag potential delays
- Support customer inquiries

## Weekly Tasks

- [ ] Review order book
- [ ] Check on-time delivery rate
- [ ] Identify at-risk orders
- [ ] Capacity planning for next week
- [ ] Team scheduling

## Quick Reference

| Task | Steps |
|------|-------|
| Create order | Data Management > Orders → **New Orders** → Order Name → **Create Order** |
| Add parts | Production > WO Control Center → tick one → **Add Parts** → Start Step, Quantity, ERP ID Start |
| Create work order | Data Management > Work Orders → **New Work Orders** → ERP ID, process, priority, due date → Save |
| Change priority | Open work order → Change priority → Save |
| Check status | Production > Work Orders → Find work order → View progress |

## Related Documentation

- [Creating Orders](../workflows/orders/creating-orders.md)
- [Adding Parts](../workflows/orders/adding-parts.md)
- [Work Order Basics](../workflows/work-orders/basics.md)
- [Order Status](../workflows/orders/order-status.md)
- [Dashboard](../analysis/dashboard.md)
