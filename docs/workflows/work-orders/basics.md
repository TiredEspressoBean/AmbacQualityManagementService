# Work Order Basics

Work orders connect customer orders to manufacturing processes. This guide explains how work orders function in Ambac Tracker.

## What is a Work Order?

A **Work Order** defines:

- **Which order** is being worked on
- **What process** to follow
- **Who** is assigned (equipment, operators)
- **When** it should be completed
- **Priority** level

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

1. Navigate to **Production** > **Work Orders**
2. Click **+ New Work Order**
3. Fill in the form:

| Field | Description | Required |
|-------|-------------|----------|
| **Order** | Select the customer order | Yes |
| **Process** | Manufacturing workflow to follow | Yes |
| **Priority** | Normal, High, or Rush | Yes |
| **Due Date** | Target completion | No |
| **Equipment** | Assigned machine/work center | No |
| **Notes** | Instructions or comments | No |

4. Click **Save**

## Work Order Status

| Status | Meaning |
|--------|---------|
| **Pending** | Created but not started |
| **In Progress** | Active production |
| **On Hold** | Temporarily paused |
| **Waiting for Operator** | Ready to work, awaiting assignment |
| **Completed** | All parts finished |
| **Cancelled** | Work order cancelled |

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
3. Parts progress through steps independently
4. Work order tracks aggregate progress

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
3. Enter cancellation reason
4. Confirm

Parts remain in the system but are no longer associated with this work order.

## Work Order Permissions

| Permission | Allows |
|------------|--------|
| `view_workorder` | View work orders |
| `add_workorder` | Create work orders |
| `change_workorder` | Edit and status changes |
| `delete_workorder` | Delete work orders |

## Best Practices

1. **One process per work order** - Keeps tracking clean
2. **Set realistic due dates** - Based on capacity
3. **Update status promptly** - Keeps dashboards accurate
4. **Link documents** - Work instructions at hand
5. **Use notes** - Communicate with team

## Next Steps

- [Assigning Work Orders](assigning.md) - Equipment and operators
- [Work Order Progress](progress.md) - Tracking completion
- [First Piece Inspection](fpi.md) - FPI workflow
