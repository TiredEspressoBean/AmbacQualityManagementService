# Production Manager Guide

This guide is for Production Managers who manage orders, work orders and
production operations in uqmes.

!!! tip "Planning and scheduling have their own guide"
    Releasing work onto the floor, promising dates, and running the schedule
    are covered in the [Planner Guide](planner.md). This guide covers the
    production side.

!!! tip "Demo Account"
    In demo mode, log in as **Jennifer Walsh** (jennifer.mgr@demo.ambac.com).
    Home opens on what is at risk — jobs going late, parts in quarantine, CAPAs
    pending verification, first pass yield, supplier qualifications expiring and
    competency coverage.

    Orders, work orders and approvals move with every reseed and every
    walkthrough, so read the numbers Home gives you rather than looking for a
    particular order.

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
| **Home** | Home | What is at risk today |
| **WO Control Center** | Production > WO Control Center | The fleet view, with the bulk actions — release, hold, add parts |
| **Work Orders** | Production > Work Orders | A read-only list, with search and filters |
| **Orders** | Data Management > Orders | Customer order management |
| **Tracker** | Tracker | Customer-facing order overview |
| **Shipping** | Supply > Shipping | On-time delivery over the last 90 days |
| **Analytics** | Analytics | Quality KPIs — yield, scrap, rework |
| **Inbox** | Personal > Inbox | CAPA tasks and approval requests |

## Daily Workflow

### 1. Review Production Status

1. **Home** shows jobs going late and the biggest fire
2. **WO Control Center** filters to **Overdue**, **Due today**, **On hold** and
   **With exceptions**
3. Note bottlenecks — capacity planning shows them by resource

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
are `<work order ERP ID>-<part type prefix><counter padded to 4 digits>`.

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
| **Priority** | Urgent, High, Normal, Low — changing it after creation needs a reason |
| **Quantity** | Parts *started*, grossed up for expected scrap |
| **Target good quantity** | The good parts the job actually owes, before gross-up |
| **Notes** | Production instructions |

!!! note "There is no equipment field on a work order"
    Machines are not assigned to a job. Equipment is recorded **at the step**, as
    the work is done, which is why one job can run across several machines — and
    it is what lets quality ask later what a given gauge or machine touched. See
    *Resource Management* below.

!!! note "Quantity and target good quantity are different numbers"
    If a job was planned with a yield allowance, **Quantity** is what was started
    and **Target good quantity** is what the customer is owed. Scrap eats the
    difference; when it outruns the allowance the job is short and can be topped
    up. See [Make-up planning](planner.md).

## Managing Production

### Monitoring Progress

On a **work order's page**: status, priority, an **Overdue** badge once it is
late, and its QA progress — parts completed, total, needing rework.

On the **Tracker**, the customer-facing view: each order's current stage, a
progress bar of stages done, and its delivery date with a red **Overdue** badge
once it has passed. There are no time metrics — no cycle time or throughput —
on either.

### Identifying Bottlenecks

Look for:
- Steps with many parts waiting
- Work orders not progressing
- Equipment conflicts
- Resource shortages

### Adjusting Priorities

There is **no Expedite action**. Jumping a job to the front means setting the
work order's priority to **Urgent** — *Expedited* on the control centre is not a
state you set, it is what Urgent looks like.

1. Open the work order for edit
2. Change the priority
3. **Say why.** The form asks — *"Why change priority from Normal to Urgent?"* —
   and the save is refused without it: *"Say why the priority is changing."*
4. Save, and notify the floor supervisor

!!! note "The reason is kept, and the last five are shown"
    The change is recorded with the field, the old and new value, the reason, who
    made it and when. The edit form lists the **last five priority changes** with
    their reasons beneath, so the job's expediting history reads back at the
    point you are about to add to it.

    Setting a priority when you first create the work order needs no reason —
    there is nothing to explain yet. Changing it to the value it already has
    records nothing.

!!! note "Changing priority by import"
    A CSV import or the master workbook's **Work Orders** sheet needs a reason
    too: add a `priority_reason` column beside `priority`. A row that changes
    priority without one is refused, and the reason given is recorded with the
    change exactly as the edit form records it.

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

1. Equipment is recorded during step execution, by an **Equipment + roles**
   capture
2. That record is what links a machine or gauge to the parts it touched — the
   basis of a calibration exposure check
3. Machine downtime is raised from a work order's **Report…** dialog
4. There is no maintenance schedule and no equipment-availability page; what a
   machine is booked to do is on the [Schedule board](../workflows/scheduling/gantt.md)

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
2. Calculate new estimate — **Could we take this order?** on capacity planning
   gives the earliest month that fits
3. Notify customer proactively — uqmes does not
4. Update the order's estimated completion and notes

!!! note "The first date is kept, not the reason"
    The first time the date moves, the order keeps the earlier one and shows
    *Originally <date>*. Later moves are not kept individually, and no reason is
    asked for, so put the reason in the notes.

## Working with Documents

### Order Documents

Attach relevant documents:
- Customer PO
- Drawings
- Special instructions
- Certificates

### Work instructions are not documents

Operators do not open a document and work alongside it. **The instruction is the
step player** — the authored substeps they work through, which are also what
records the quality data. Nothing you attach to a work order changes what they
are told to do.

What that means for you:

- A revised procedure reaches the floor through **process change control**
  (PCR → PCO → PCN), not by swapping an attached file.
- Documents on a work order are **reference** — a customer drawing, a spec, a
  special instruction. Useful, but optional reading.
- If an operator is doing the wrong thing, the fix is in the process, and it is
  Engineering's to author.

## Analytics and Reporting

### What is measured

- **On-time delivery** — on **Shipping**, over the last 90 days, with the count
  of work orders that could not be scored beside it
- **Quality** — yield, scrap and rework on **Analytics**
- **Load against capacity** — on capacity planning

There is no throughput, WIP-level or cycle-time figure, and no daily or weekly
production report. Exports from the work order and order lists are the raw
material for one.

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
| Change priority | Open work order → change priority → **give a reason** → Save |
| Check status | Production > Work Orders → Find work order → View progress |
| Close a job short | Work order → **Short-close** → decide each unfinished unit, give a reason, answer the quantity questions |
| Approve time | Operator Hours → **Awaiting approval** → **Approve** |

## If you got something wrong

- A work order short-closed by mistake: **Reopen**, with a reason.
- Held or released by mistake: **Resume** saying it was in error, or **Un-release**.
- A customer's answer recorded wrong on a reman unit: **Correct customer's
  answer…**, until the repair starts.
- The wrong component fitted: **Remove** on the core's *As built* card.

The full list is [Putting a Mistake Right](../workflows/fixing-mistakes.md).

## Related Documentation

- [Creating Orders](../workflows/orders/creating-orders.md)
- [Adding Parts](../workflows/orders/adding-parts.md)
- [Work Order Basics](../workflows/work-orders/basics.md)
- [Order Status](../workflows/orders/order-status.md)
- [Dashboard](../analysis/dashboard.md)
