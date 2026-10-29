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
count, and the list grouped by due date into **Overdue**, **Due Today**, **This
Week** and **Upcoming**.

Each approval row shows the item, its approval type, the request number
(`APR-2026-0004`), who raised it, its status, and how overdue it is, with
**View** and **Review** actions.

!!! tip "A short list is not a missing item"
    The tab count covers every approval; **Upcoming** starts collapsed. If the
    count says 5 and you see 4, open **Upcoming**.

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

Clicking a row opens the record the approval is for, on the page where you can
respond to it.

### Approval History

Every request, filterable by **Status**, **Type**, and **Scope** (all approvals
or only your own), with columns for Item, Type, Requested By, Requested date,
Due Date, and Status.

## Who can approve

Approving takes **both** a permission and an assignment, and the permission is
checked first. You need `respond_to_approval` to respond, claim or delegate at
all; then, on that request, you must be an assigned approver — by name or
through a group — and not have already responded.

So an assigned approver whose role lacks `respond_to_approval` is refused, and
an administrator who holds the permission but was not assigned sees no action.
Granting the permission alone will not put someone on a request, and being on a
request will not substitute for the permission.

### How approvers get assigned

The **approval template** for that approval type decides:

| Setting | Effect |
|---------|--------|
| **Approvers** | Named people, added individually or by role |
| **Auto-assign to Group** | Everyone in the group is assigned |

So "why can't this person approve?" is almost always a template question. See
[Approval Templates](../../admin/setup/approval-templates.md).

### Approving your own request

**Refused by default.** If you raised the request, responding to it is rejected:

> Self-approval is not permitted for this approval type

This is **per approval type**, not per person — the template carries an **Allow
self-approval** switch which is off unless somebody turns it on. CAPA approvals
make one exception: when nobody else on the request can approve, the requester
may decide it; while someone else can, the refusal reads *You requested this
approval, and someone else can decide it — it waits for them.* Either way the
approver must write a **justification of at least ten characters**, and the
response is permanently flagged as self-approved so an auditor can find every
one.

!!! note "Eligibility and authorisation are different layers"
    You may well *see* **Submit Response** on your own request — being an
    assigned approver is decided before anyone asks who raised it. The refusal
    comes from the server when you submit. That is not a bug: the button means
    you are eligible, not that this particular response will be accepted.

## How a request closes

Two independent settings:

**Sequence** — the order approvers are asked:

- **Parallel** — everyone is asked at once
- **Sequential** — in stages, set on the template. The request shows its
  stages, the open one marked *Waiting on this stage*. Only the open stage can
  answer; anyone later sees *"Not your turn — waiting on &lt;names or
  groups&gt;."* instead of a response button. A group shows *Any one member* until
  a member answers for it. A stage is done when everyone named in it has approved and each of
  its groups has been answered by one member. A request appears under your
  pending approvals only when it is your turn

**Approval Flow** — how many responses close it:

| Flow | Closes when |
|------|-------------|
| **All Required** | Every required approver approves |
| **Threshold** | The configured number of approvals is reached |
| **Any** | Any one approver approves |

On a **Parallel** request, the **required** approvers are the people assigned by
name and the members assigned by the template's **Auto-assign to Group**. A
group assigned as a whole lets any member respond but is not itself required —
so a Parallel request routed only to groups closes on the first approval.

Under **Sequential**, the request closes when every stage is done; a group in a
stage is required, answered by any one member. A rejection at any stage ends the
request. **Threshold** and **Any** apply to **Parallel** requests. See
[Approval Templates](../../admin/setup/approval-templates.md#sequence).

## Responding

There is one action — **Submit Response** — which opens a dialog with a
**Decision**:

| Decision | Effect |
|----------|--------|
| **Approve** | You approve: draw your signature, confirm it, and re-enter your password. The server refuses an approval without a signature (*Sign to approve.*) or without the password (*Enter your password to approve.*) |
| **Reject** | You reject, with a comment saying why — the dialog says *Comments are required when rejecting*, and the server refuses a rejection with no reason (*Say why you are rejecting it.*); the requester can revise and resubmit |
| **Delegate** | You pass the decision on. Offered only when the template's **Delegation** is **Optional**; the starter templates allow it on every type except Critical CAPA Approval, and a new template starts at **Disabled** |

There is no "request more information" decision. If you need more before you can
decide, leave the request open and ask outside it, or reject with comments
saying what is missing.

Your response records your identity, the decision, a timestamp, the
verification method used (*Password* for an approval), and your comments. See [Electronic
Signatures](../../compliance/signatures.md).

## Putting a response or a request right

| Mistake | Who | What to do |
|---------|-----|------------|
| You answered too soon, or the wrong way | The approver | **Change my response**, with a reason, while the request is open. Your answer is taken back and you answer anew |
| A request went out with a mistake in it | The requester | **Withdraw request**, with a reason, from the record or **Approvals** > *My Submitted Requests*. It reads **Cancelled**, and a document goes back to Draft to be corrected and resubmitted |

Both are possible only while the request is **pending**. A decided request and its
responses stand. Each change, and its reason, stays in the request's history next
to what it replaced.

## Due dates and escalation

A template sets **due days** from when the request is raised, and optionally
**escalation days** and an **escalation target**. Overdue requests are counted
on the Inbox, the Approvals overview, and the Home page.

## Next Steps

- **[Document Approval](../documents/approval.md)** - Approving documents
- **[Approval Templates](../../admin/setup/approval-templates.md)** - Configuring who approves
- **[Change Control](../change-control/overview.md)** - Process change approvals
