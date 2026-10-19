# Work Order Basics

Work orders connect customer orders to manufacturing processes. This guide explains how work orders function in uqmes.

## What is a Work Order?

A **Work Order** defines:

- **Which order** is being worked on, if any
- **What process** to follow
- **How many** units — both what was started and what the job owes
- **When** it should be completed
- **Priority** level

It does **not** name equipment or operators. Machines are recorded at the step
as the work is done, and people claim or are dispatched to steps — so one job
routinely runs across several machines and several people. See [Assigning Work
Orders](assigning.md).

!!! example "Demo: Work Order"
    Work Order `WO-2024-0042-A` processes 24 fuel injectors for order `ORD-2024-0042` (Midwest Fleet Services) using the "Common Rail Injector Remanufacturing" process. Parts are tracked from Core Receiving through Final Test and Packaging.

## Work Order vs Order

| Concept | Purpose |
|---------|---------|
| **Order** | Customer request (PO), contains parts |
| **Work Order** | Production assignment, links to process |

An order may have multiple work orders if:

- Different part types require different processes
- Work is split across shifts or work centers
- Rework requires a new work order

## Creating a Work Order

!!! info "Three Work Orders pages, and only one of each does the job"
    | Sidebar entry | What it is for |
    |---|---|
    | **Production** > **Work Orders** | A read-only list. No create button, no Add Parts. |
    | **Production** > **WO Control Center** | Where **Add Parts** lives, in the bulk bar |
    | **Data Management** > **Work Orders** | Where a work order is **created** |

1. Navigate to **Data Management** > **Work Orders**
2. Click **New Work Orders**
3. Fill in the form:

| Field | Description | Required |
|-------|-------------|----------|
| **ERP ID** | The work order's number in the system that owns it | Yes |
| **Order** | The customer order, if there is one | No |
| **Process** | Manufacturing workflow to follow | Yes |
| **Priority** | Urgent, High, Normal, or Low | Yes |
| **Due Date** | Target completion | Yes |
| **Notes** | Instructions or comments | No |

!!! note "A work order need not be tied to a customer order"
    **Order** is optional — stock builds, internal work and rework all exist
    without one. **Due Date** is not: the schedule is built from dates, so a work
    order with no target completion has nothing to plan against.

!!! note "Equipment Assignment"
    Equipment is assigned at the step execution level, not on the work order itself. This allows different equipment to be used for different steps. See [Assigning Work Orders](assigning.md) for details.

4. Click **Save**

## Work Order Status

| Status | Meaning |
|--------|---------|
| **Pending** | Created but not started |
| **In Progress** | Active production |
| **On Hold** | Temporarily paused |
| **Completed** | All parts finished |
| **Cancelled** | Work order cancelled |

Statuses change through the work and through the work order page's **Place on
hold**, **Resume** and **Cancel** — not by editing the field. See [Status
Updates](progress.md#status-updates).

## Priority Levels

| Priority | Value | Use When |
|----------|-------|----------|
| **Urgent** | 1 | Critical, drop everything |
| **High** | 2 | Important customer, tight deadline |
| **Normal** | 3 | Default priority (standard lead time) |
| **Low** | 4 | Can wait, no deadline pressure |

Priority affects:

- Queue position
- Dashboard highlighting
- Notification urgency

## Parts and Steps

When a work order is created:

1. Parts from the order are associated with the work order
2. Each part starts at Step 1 of the process
3. Parts advance **as a cohort**, not individually
4. Work order tracks aggregate progress

!!! warning "Parts do not move independently"
    Parts that have not been split advance together — all parts at the same work
    order and step move on, or none do. A part only advances on its own once it
    has been **split** out of the lot.

    This catches people out constantly: a part whose own work is finished sits
    at its step because a *different* part in the lot still has something
    outstanding. Nothing is broken and nothing is stuck on that part — it is
    waiting for its lot. See [Moving Parts
    Forward](../tracking/moving-parts.md).

## Work Order Progress

Progress is calculated as:

```
Progress = Parts at final step or complete / Total parts
```

View progress on:

- Work order list
- Work order detail
- Dashboard widgets

## Work Order Detail View

The work order detail page shows:

### Header
- Work order number
- Order reference
- Status and priority
- Due date

### Progress Section
- Parts by step (chart)
- Completion percentage
- Time metrics

### Parts Tab
- List of all parts
- Current step for each
- Quick actions (move, flag)

### Documents Tab
- Linked work instructions
- Process documents
- Attached files

### History Tab
- Status changes
- Assignment changes
- Notes and comments

## Linking Documents

Attach documents to work orders:

1. Open the work order
2. Go to **Documents** tab
3. Click **Add Document**
4. Upload or link existing document

Common work order documents:

- Work instructions
- Setup sheets
- Inspection checklists
- Process specifications

## Work Order Notes

Add notes for communication:

1. Open the work order
2. Scroll to **Notes** section
3. Click **Add Note**
4. Enter your message
5. Notes are timestamped with your name

Notes appear in the activity feed.

## Splitting Work Orders

To split a work order (e.g., partial shipment):

1. Open the work order
2. Click **Split Work Order**
3. Select parts for the new work order
4. A new work order is created with selected parts

## Cancelling Work Orders

To cancel:

1. Open the work order
2. Click **Cancel Work Order**
3. Confirm

No reason is asked for. The status becomes **Cancelled**, so the work order
drops out of scheduling, and its parts keep their link to it. The record of what
was planned stays intact. If every work order on the customer order is now
completed or cancelled, the order completes too.

A work order already completed or cancelled cannot be cancelled again.

!!! warning "You cannot cancel once anything has left"
    The cancel is refused outright if any part on the order has shipped,
    completed, gone into stock, been banked as a core, or is awaiting pickup —
    *"Can't cancel — some parts have already shipped or completed."* Delivered
    work cannot be un-planned.

!!! note "Cancelling is manager-tier"
    It needs **`cancel_workorder`**, by default held by **Tenant Admin** and **Production
    Manager** only, and the button is hidden from anyone else. Abandoning a job
    breaks a commitment to a customer, so it is not an operator's call.

## Work Order Permissions

| Permission | Allows |
|------------|--------|
| `view_workorder` | View work orders |
| `add_workorder` | Create work orders |
| `change_workorder` | Edit, release, place on hold and resume — one at a time or in bulk from the Control Center. By default every staff role holds it; without it those buttons are hidden |
| `delete_workorder` | Delete work orders |
| `cancel_workorder` | Cancel a work order — Tenant Admin and Production Manager |

## Next Steps

- [Assigning Work Orders](assigning.md) - Equipment and operators
- [Work Order Progress](progress.md) - Tracking completion
- [First Piece Inspection](fpi.md) - FPI workflow
