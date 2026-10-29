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
| **Status** | **Pending** is the only choice: *"A new work order starts Pending. Hold, cancel or complete it from its page afterwards."* Locked once the work order exists | No |
| **Priority** | Urgent, High, Normal, or Low. Normal when left empty | No |
| **ERP ID** | The work order's number in the system that owns it | Yes |
| **Notes** | Instructions or comments | No |
| **Related Order** | The customer order, if there is one | No |
| **Process** | Manufacturing workflow to follow. Only **approved** processes **in force** are offered | No |
| **Expected Completion Date** | Target completion | Yes |

!!! note "Created Pending, and nothing else"
    Any other status on a new work order is refused: *"A new work order starts as
    Pending. Hold, cancel or complete it afterwards with its own action."* In
    Progress and Completed follow the work; holds and cancels have their own
    buttons.

!!! note "The process must be one new work may run"
    A draft, a superseded version or a temporary change's version is refused —
    the picker leaves them out, and the server refuses them if sent anyway.

!!! note "No quantity on this form"
    A work order created here has a quantity of **1** and no parts. Set the
    quantity from the schedule's **Edit work order** dialog, which adds parts for
    an increase and cancels unstarted ones for a decrease. **Add Parts** on the
    WO Control Center adds parts without changing the quantity. A work order planned from the schedule
    or an order line gets its quantity and parts when it is planned.

!!! note "A work order need not be tied to a customer order"
    **Related Order** is optional — stock builds, internal work and rework all
    exist without one. **Expected Completion Date** is not: the schedule is built
    from dates, so a work order with no target completion has nothing to plan
    against.

!!! note "Equipment Assignment"
    Equipment is assigned at the step execution level, not on the work order itself. This allows different equipment to be used for different steps. See [Assigning Work Orders](assigning.md) for details.

4. Click **Submit**

## Work Order Status

| Status | Meaning |
|--------|---------|
| **Pending** | Created but not started |
| **In Progress** | Active production |
| **On Hold** | Temporarily paused |
| **Completed** | All parts finished |
| **Cancelled** | Work order cancelled |

Statuses change through the work and through the work order page's **Hold**,
**Resume** and **Cancel** — not by editing the field. A work order on hold,
completed, short-closed or cancelled takes no more work: **Start Work** is
disabled and says why, and starting a step on it is refused. No supervisor
override gets past that. See [Status
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

### Changing priority needs a reason

Editing an existing work order and changing **Priority** adds a required field,
*Why change priority from &lt;old&gt; to &lt;new&gt;?* — *"Recorded with the change,
so the reason is on file when someone asks later."* Saving without one is
refused: *"Say why the priority is changing."*

The form's **Priority changes** box lists the most recent changes: from and to,
who, when, and the reason.

## Parts and Steps

When a work order is created:

1. Parts are added to it — **Add Parts** on the WO Control Center's bulk bar,
   or created with it when the work order is planned from the schedule or an
   order line
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
Progress = Parts finished (completed, shipped, in stock, awaiting pickup or dismantled) / Total parts
```

View progress on:

- Work order list
- Work order detail

## Work Order Detail View

The work order detail page (`/workorder/$workOrderId`) has a header with status,
priority and badges, and four tabs: **Overview**, **Parts**, **Materials** and
**Labor**. See [Work Order Detail](progress.md#work-order-detail).

### Labor

**Labor** shows the operator time on this job to date:

| Card | Is |
|------|----|
| **Actual direct hrs** | Operators' time at this job's steps, while on shift. Turns amber when it exceeds planned |
| **of which rework** | The part spent on rework — repeat visits and rework steps |
| **Planned hrs** | The route's operator time for the work order quantity, from the steps' time standards; rework steps aren't planned. *No time standards on the route* when no step has one |

Below the cards, a table gives each operator's direct and rework hours, or *No
work started on this job yet.* The hours are worked out from the step records,
the same way as [Operator Hours](../scheduling/overview.md#where-direct-time-comes-from).

## Linking Documents

Attach documents to work orders:

1. **Data Management** > **Work Orders**, edit the work order
2. Under **Attach Documents**, choose the file and classification and click
   **Upload**

(Existing documents are linked from the document's **Also Linked To** >
**Attach**, or its **Edit** > **Link To**.)

Common work order documents:

- Work instructions
- Setup sheets
- Inspection checklists
- Process specifications

## Work Order Notes

**Notes** is a field on the work order's form in **Data Management**. It shows
on the detail page's **Overview** tab. Changes to it are listed on the form's
**History** card.

## Splitting Work Orders

To split a work order (e.g., partial shipment):

1. Open the work order's control page
2. Click **Split…** (or select parts in the table and choose **Split selection…**)
3. Choose **Quantity**, **Selected parts** or **Rework**, then give the quantity
   to move (or select the parts), the **New ERP id** and any notes
4. Click **Create child WO**. A new work order is created with them

## Cancelling Work Orders

To cancel:

1. Open the work order
2. Click **Cancel**
3. Click **Confirm Cancel**

No reason is asked for. The status becomes **Cancelled**, so the work order
drops out of scheduling, and its parts keep their link to it. The record of what
was planned stays intact. If every work order on the customer order is now
completed or cancelled, and at least one completed, the order completes too.

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

## Short-closing a Work Order

When a job will finish with fewer built than planned, **Short-close** it rather
than cancelling it. The button sits beside Cancel, needs the same permission
(`cancel_workorder`), and is hidden while the work order is on hold.

The dialog — *"Complete it with fewer built than planned: X of Q built"* — asks:

1. **For each unfinished unit,** **Scrap** it or **Move** it to another open
   work order on the same process, where it keeps its step. A unit moves only
   to work for the **same customer**, or to a work order on no order. A
   customer's own unit (a repair-and-return core) moves only to that customer's
   work. Each option names its customer. **Set all to…** offers only targets
   every unit may take.
2. **Why it is closing short.** A reason is required.
3. **For each work order receiving units:** raise its quantity to cover them, or
   leave it as it is.
4. **If the job is on an order line and units are left over:** give them back to
   the line as demand still to plan, or treat the line as done with them.

Questions 3 and 4 have no default; you must answer them.

The work order becomes **Completed**, with a **Short-closed** badge whose
tooltip gives the reason. Every scrap, move and quantity change is recorded as a
correction with that reason (see [Part History](../tracking/part-history.md#corrections)).
On the order page, **Planned** notes *N short-closed*. Units given back reappear
in **Remaining**.

Short-close is refused:

- without a reason
- when nothing is finished: cancel it instead
- with any unit left undecided, or a question unanswered
- for a move to a work order on a different process, or for a different
  customer
- for scrapping a quarantined unit, or one out at a vendor. Moving them is fine.

### Short-closed by mistake

**Reopen**, beside the **Short-closed** badge, takes the work order back to **In
Progress**, with its order if the close had completed it. It needs the same
permission as short-closing and a required reason, kept on the work order.

- Units the close **scrapped stay scrapped**, and units it **moved stay where they
  went**. Reopening undoes the closing, not the decisions made in it. Where scrap
  left the work order short, its **Make-up** card offers make-up parts.
- Units it gave back to the order line are no longer counted there as well, so
  the line doesn't plan them twice.

## Work Order Permissions

| Permission | Allows |
|------------|--------|
| `view_workorder` | View work orders |
| `add_workorder` | Create work orders |
| `change_workorder` | Edit, release, place on hold and resume — one at a time or in bulk from the Control Center. By default every staff role except Auditor holds it; without it those buttons are hidden |
| `delete_workorder` | Delete work orders |
| `cancel_workorder` | Cancel or short-close a work order — Tenant Admin and Production Manager |

## Next Steps

- [Assigning Work Orders](assigning.md) - Equipment and operators
- [Work Order Progress](progress.md) - Tracking completion
- [First Piece Inspection](fpi.md) - FPI workflow
