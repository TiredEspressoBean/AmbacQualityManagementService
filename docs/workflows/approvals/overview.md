# Approvals

One approval system serves documents, CAPAs, and change control. A request is
raised against a record, assigned approvers respond, and the record moves on
when the flow's conditions are met.

## Where approvals appear

| Surface | What it is for |
|---------|----------------|
| **Personal** > **Inbox** | Everything waiting on you — approvals alongside tasks and dispositions |
| **Approvals** > **Overview** | Approvals only, split into what needs you and what you asked others for |
| **Approvals** > **History** | The audit view of every request |

### Inbox

Tabs for **All**, **Tasks**, **Approvals**, and **Dispositions**, each with a
count, and a split between **Overdue** and **Upcoming**.

Each approval row shows the item, its approval type, the request number
(`APR-2026-0004`), who raised it, its status, and how overdue it is, with
**View** and **Review** actions.

!!! tip "A short list is not a missing item"
    The tab count covers every approval; the list is split into Overdue and
    Upcoming. If the count says 5 and you see 4, the fifth is under Upcoming.

### Approvals Overview

Four figures at the top:

| Tile | Meaning |
|------|---------|
| **Awaiting My Approval** | Requests assigned to you |
| **Overdue** | Of those, past their due date |
| **My Requests Pending** | Requests you raised, awaiting others |
| **Recently Approved** | Your requests that completed |

Below them, the items awaiting you, a **by type** breakdown, and your own
submitted requests.

!!! warning "Known issue: document approvals link to the wrong page"
    Clicking a **Document Release** row here opens the generic record page
    (headed *"documents Detail"*), which has no Approval tab and no way to
    respond.

    Open the document from **Documents** instead, or use the **Review** action
    in your Inbox, which routes correctly. CAPA approvals from this list are
    unaffected.

### Approval History

Every request, filterable by **Status**, **Type**, and **Scope** (all approvals
or only your own), with columns for Item, Type, Requested By, Requested date,
Due Date, and Status.

## Who can approve

Approval is authorized **per request**, not by holding a permission. You can
respond only if you are an assigned approver on that request — by name or
through a group — and have not already responded.

An administrator who was not assigned sees no action. Granting a permission
will not change that; the assignment is what matters.

### How approvers get assigned

The **approval template** for that approval type decides:

| Setting | Effect |
|---------|--------|
| **Approvers** | Named people, added individually or by role |
| **Auto-assign to Group** | Everyone in the group is assigned |

So "why can't this person approve?" is almost always a template question. See
[Approval Templates](../../admin/setup/approval-templates.md).

## How a request closes

Two independent settings:

**Sequence** — the order approvers are asked:

- **Parallel** — everyone is asked at once
- **Sequential** — each is asked in turn

**Approval Flow** — how many responses close it:

| Flow | Closes when |
|------|-------------|
| **All Required** | Every assigned approver approves |
| **Threshold** | The configured number of approvals is reached |
| **Any** | Any one approver approves |

A Threshold flow can run either sequence.

## Responding

There is one action — **Submit Response** — which opens a dialog with a
**Decision**:

| Decision | Effect |
|----------|--------|
| **Approved** | You approve |
| **Rejected** | You reject; the requester can revise and resubmit |
| **Delegated** | You pass the decision on, if the template allows delegation |

Your response records your identity, the decision, a timestamp, the
verification method used, and your comments. See [Electronic
Signatures](../../compliance/signatures.md).

## Due dates and escalation

A template sets **due days** from when the request is raised, and optionally
**escalation days** and an **escalation target**. Overdue requests are counted
on the Inbox, the Approvals overview, and the Home page.

## Next Steps

- **[Document Approval](../documents/approval.md)** - Approving documents
- **[Approval Templates](../../admin/setup/approval-templates.md)** - Configuring who approves
- **[Change Control](../change-control/overview.md)** - Process change approvals
