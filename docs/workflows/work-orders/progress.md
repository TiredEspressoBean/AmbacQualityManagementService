# Work Order Progress

Track work order completion, monitor metrics, and manage production flow.

## Progress Overview

Work order progress shows how much work is complete:

```
┌──────────────────────────────────────────────┐
│  WO-2026-0042                    75% ████████░░░│
│  Process: Widget Production                     │
│  Parts: 8/10 complete, 2 in progress           │
└──────────────────────────────────────────────┘
```

## Viewing Progress

### Work Order List

**Production** > **Work Orders** lists: Work Order, Process, **QA Progress**,
Due Date, Customer, Order, and a Details link.

!!! tip "Status and priority are on the Control Center"
    This list carries neither. **WO Control Center** is the fleet view — it
    adds status and priority columns, and filters for **Due today**,
    **Overdue**, **On hold**, **With exceptions** and **Expedited**, plus a
    priority selector. Use it when you are working across many work orders.

!!! important "There is no Expedite button — Expedited is derived"
    A work order counts as **Expedited** when its **priority is Urgent**. To jump
    a job to the front, set its priority; the tile and filter follow from that.

!!! important "A priority change asks why, and keeps the answer"
    Changing priority on **Data Management > Work Orders > edit** requires a
    reason — *"Why change priority from Normal to Urgent?"* — and will not save
    without one. The reason is stored with the change, and the edit form lists
    the last five: *Normal → Urgent · who, when*, with the reason beneath.

    So the trail answers *what, who, when* **and** *why*. Setting a priority when you first create the work order needs no
    reason; there is nothing to explain yet.

!!! note "Changing priority by import"
    A CSV import or the master workbook's **Work Orders** sheet needs a reason
    too: add a `priority_reason` column beside `priority`. A row that changes an
    existing work order's priority without one is refused, and the reason is
    recorded with the change as the edit form records it.

## When scrap outruns the gross-up

Planning a work order grosses the started quantity up for **expected** scrap. When
**actual** scrap runs past that, the units still alive fall below the ordered good
count and the job will finish short.

**Make-up planning tops it back up.** It reports the gap, and creating the
replacements is an explicit action. On the work order page a **Make-up** card
appears only when the job is short. It reads *"&lt;good&gt;/&lt;target&gt; good · &lt;alive&gt;
alive · &lt;scrapped&gt; scrapped"* and *"&lt;N&gt; short of &lt;target&gt; good"*, with the button
**Create N make-up part(s)**. The scheduling board's work order dialog shows the
same card at all times.

| Figure | Means |
|--------|-------|
| **Target good** | What the order owes |
| **Alive** | Units not scrapped or cancelled |
| **Shortfall** | What make-up would create |

A work order with no parts yet, or one that has completed or been cancelled,
reports no shortfall. Creating make-up needs `add_workorder`.

Replacements are created at the route's **first step**, flagged as make-up, and
the schedule is marked stale so the next solve picks them up.

!!! important "It is planner-confirmed, never automatic"
    The system reports the shortfall; a person creates the replacements. That is
    deliberate for AS9100 and ITAR work — spawning units onto a job is a decision
    with a paper trail, not a side effect of scrapping something.

!!! note "Top-up is iterative, so there is no gross-up on the gross-up"
    The rule is simply *keep alive equal to target*. A replacement that later
    scraps is covered by the next top-up, so nothing needs padding twice.

!!! warning "A reman order owes no make-up"
    Its units are **cores** — someone's actual units, received rather than made.
    A scrapped core cannot be made up by spawning another, so the shortfall is
    always zero there. What a scrapped core needs is a conversation with its
    owner, not a replacement unit.

### Work Order Detail

`/workorder/$workOrderId` carries, in its header, the status, the priority, an
**Overdue** badge once the due date has passed (unless the job is completed or
cancelled), and **N at outside process** when parts are out at a vendor — that
badge links to the control page, where send-out and receive-back live.

Below, four tabs:

| Tab | Shows |
|-----|-------|
| **Overview** | Customer, due date, quantity, and **QA Progress** — completed, total parts, need rework — with the digital traveler and notes |
| **Parts** | The parts on the job, filterable by status |
| **Materials** | Material for the job |
| **Labor** | Actual direct and rework hours per operator, against the route's planned hours — see [Labor](basics.md#labor) |

### On the Home page

There is no separate production dashboard. The **Home** page surfaces work
order state for production roles — jobs going late, work orders in flight, and
the biggest fire — alongside links into the Control Center. See [Role
Guides](../../roles/index.md).

## Status Updates

### Automatic

| Status | Set when |
|--------|----------|
| **Pending** | The work order is created |
| **In progress** | Someone actually starts work on one of its steps |
| **Completed** | Every part on it has ended |
| **Cancelled** | Every part on it ended **scrapped** — automatically, not as a manual cancel |

!!! note "Started is a fact, not a button"
    *In progress* records that work began. It is separate from **release**,
    which authorises the job, and a planner needs both: released-but-not-started
    is exactly the queue that workload control manages.

### Manual, on the work order page

| Button | Appears when | Effect |
|--------|--------------|--------|
| **Release** | Not yet released, and not on hold | Releases the job — the readiness check runs, and if it refuses, *Not ready to release* lists the blockers and asks for a **reason to release anyway**. It does **not** change the status |
| **Un-release** | Released | Withdraws the authorisation |
| **Hold** (*Place on hold* on the control page) | Pending or in progress | Asks for a reason — waiting on material, quality hold, tooling, operator unavailable, customer hold, other — with optional details. The hold record keeps them |
| **Resume** | On hold | Clears the hold. The work order returns to **In progress** if any work has started, otherwise to **Pending**. A quality or tooling hold needs **What resolved it** before it clears |
| **Cancel** | Not completed or cancelled | Asks to confirm, then cancels — see [Cancelling](basics.md#cancelling-work-orders) |
| **Short-close** | Not on hold, completed or cancelled (refused when nothing has finished) | Completes it short, deciding each unfinished unit — see [Short-closing](basics.md#short-closing-a-work-order) |

!!! note "Status is not something you set"
    These buttons are the only way to change a work order's status by hand.
    The status field on the edit form is locked on an existing work order, and
    the API refuses a status set directly, naming the action to use instead —
    *"place the work order on hold, with a reason, instead of setting the
    status"*. **In progress** and **Completed** follow the work and are never
    set by hand.

See [Releasing](../scheduling/releasing.md) for what release decides and the
other places it can be done.

### Undoing one by mistake

| Mistake | Put right with |
|---------|----------------|
| Held the wrong work order | **Resume**, saying it was placed in error. **Hold history** keeps both the hold and why it came off |
| Released one that wasn't ready | **Un-release** |
| Short-closed one by mistake | **Reopen** — see [Short-closed by mistake](basics.md#short-closed-by-mistake) |

A cancelled work order has no way back. Raise a new one for the work.

## Progress figures

The work order's progress is its **QA Progress** counts: parts completed, total,
and needing rework. An **order's** progress is counted differently, in stages
— see [Order Status](../orders/order-status.md#progress-calculation).

## What is not measured

!!! note "No time metrics on a work order"
    There is no cycle time, throughput, lead time or step-duration figure for a
    work order. Step timings are a planning *input*.

    Delivery is measured, but on **Shipping**, not here: it shows on-time % for
    the last 90 days, scored against each work order's line due date or
    expected completion. See [Shipping](../supply/shipping.md#seeing-whether-you-are-on-time). For where work is piling up against capacity, see
    [Capacity](../scheduling/capacity.md).

## How current the figures are

Progress figures are **polled, not pushed**. There are no websockets: the
dashboard queries refresh on an interval — every 2 minutes for actionable
items such as failures and approvals, every 5 minutes for slower-moving
summaries.

So a change another user makes appears within a couple of minutes rather than
instantly. Reload if you need the current position immediately.

## Notifications

Who hears about a work order is set by this organisation's [notification
rules](../../admin/setup/notification-rules.md), not by the work order.

## Reports

The work order page carries the **Traveler**. Dispatch lists and labour hours
come from scheduling. There is no work-order status report or production
summary report.

## Several at once

Bulk actions across work orders live on the **WO Control Center**'s bulk bar —
see [Assigning](assigning.md) and [Work Order Basics](basics.md).

## History

A work order's own changes, including priority with its reasons, are on the
**History** card of its edit form in **Data Management**.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_workorder` | View progress |
| `change_workorder` | Update status |
| `view_documents` *or* `view_chatsession` | Makes the Analytics link appear in the sidebar |

## Next Steps

- [First Piece Inspection](fpi.md) - FPI workflow
- [Analytics Dashboard](../../analysis/dashboard.md) - Production metrics
- [Work Order Basics](basics.md) - Core concepts
