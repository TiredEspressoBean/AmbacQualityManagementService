# Production Manager Guide

This guide is for Production Managers and Planners who manage orders, schedule work, and oversee production operations in uqmes.

!!! tip "Demo Account"
    In demo mode, log in as **Jennifer Walsh** (jennifer.mgr@demo.ambac.com) to experience the Production Manager workflow. You'll see:

    - 3 orders in different states: ORD-2024-0042 (in progress), ORD-2024-0038 (completed), ORD-2024-0048 (pending)
    - Work order WO-0042-A in progress with 67% completion
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
| **Tracker** | Portal > Tracker | Customer-facing order overview |
| **Analytics** | Tools > Analytics | Production metrics |
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
2. Address quality holds via **Production** > **Dispositions**
3. Resolve resource conflicts
4. Update customer if needed

## Creating Orders

### New Order Entry

1. Navigate to **Data Management** > **Orders**
2. Click **+ New Order**
3. Fill in order details:

| Field | Description |
|-------|-------------|
| **Order Number** | Your PO/SO number |
| **Customer** | Select customer |
| **Due Date** | Target completion |
| **Priority** | Normal, High, Rush |
| **Notes** | Special instructions |

4. Save order

### Adding Parts to Order

1. Open the order
2. Go to **Parts** section
3. Click **+ Add Parts**
4. Specify:
   - Part type
   - Quantity
   - Serial prefix (optional)
   - Lot number (optional)
5. Add parts

### Bulk Order Import

For multiple orders:
1. Click **Import**
2. Download CSV template
3. Fill in order data
4. Upload and confirm

## Creating Work Orders

### Linking Order to Process

1. Navigate to **Production** > **Work Orders**
2. Click **+ New Work Order**
3. Select:
   - Order
   - Process
   - Priority
   - Due date
4. Assign resources (optional)
5. Save

### Work Order Settings

| Field | Purpose |
|-------|---------|
| **Priority** | Normal, High, Rush |
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

1. View quarantined parts in **Production** > **Dispositions**
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
| Create order | Data Management > Orders → + New → Fill form → Save |
| Add parts | Open order → Parts → + Add → Configure → Save |
| Create work order | Production > Work Orders → + New → Configure → Save |
| Change priority | Open work order → Change priority → Save |
| Check status | Production > Work Orders → Find work order → View progress |

## Related Documentation

- [Creating Orders](../workflows/orders/creating-orders.md)
- [Adding Parts](../workflows/orders/adding-parts.md)
- [Work Order Basics](../workflows/work-orders/basics.md)
- [Order Status](../workflows/orders/order-status.md)
- [Dashboard](../analysis/dashboard.md)
