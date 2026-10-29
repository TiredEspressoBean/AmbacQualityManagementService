# Document Approval

Controlled documents require approval before release. This guide covers document approval workflows.

## What Requires Approval?

Document types that typically require approval:

| Document Type | Why |
|---------------|-----|
| **Work Instructions** | Ensure procedures are correct |
| **Specifications** | Verify technical accuracy |
| **Drawings** | Engineering sign-off |
| **Policies** | Management approval |
| **Forms** | Quality system control |

Your administrator configures which types require approval.

### A type that needs no approval

A Draft of a type with **Requires approval** off skips the workflow below. The
document header shows **Release** to holders of `release_documents`, and
releasing puts the Draft in force directly — its dates are set and the earlier
released revision is made obsolete. Its **Approval** tab reads *"No approval
needed — This document's type doesn't require approval. It is put in force with
Release, by someone who can release documents."*

A Draft of a type that requires approval can't be released before it is
approved: *"This document's type requires approval. Must be approved before
release — submit it for approval first."*

## Approval Workflow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Draft   │────▶│  Under   │────▶│ Approved │────▶│ Released │
│          │     │  Review  │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                  │
                      ▼                                  ▼
             (rejected or withdrawn —               ┌──────────┐
                  back to Draft)                    │ Obsolete │
                                                    └──────────┘
```

The five statuses are **Draft**, **Under Review**, **Approved**, **Released**
and **Obsolete**. *Approved* and *Released* are distinct: approval is the
signature, release is putting it into force.

!!! note "What makes a document Obsolete"
    **Releasing** a new revision obsoletes the released revision it replaces,
    so two revisions of one document are never in force at once. Approving one
    does not: until the new revision is released, the old one stays in force.
    A document withdrawn without a replacement is obsoleted by hand, with **Mark
    obsolete** — see [Taking a document out of
    circulation](library.md#taking-a-document-out-of-circulation).

## Submitting for Approval

### From Document Detail

1. Open the document (in Draft status)
2. Go to the **Approval** tab — it shows *"Document Not Yet Submitted"*
3. Click **Submit for Approval**

Once submitted, each individually assigned approver is notified and the
document moves to **Under Review**. Members of an assigned group are not
notified; they see the request in their **Inbox**.

### Approval Templates

Templates define:

- Who needs to approve
- Whether approvers are asked all at once (parallel) or one at a time (sequential)
- Number of approvals required

A template cannot fix the order of a sequential approval — see [Approval
Templates](../../admin/setup/approval-templates.md#sequence).

## Under Review

After submission:

1. Document status changes to **Under Review**
2. Approvers are notified
3. Document appears in approvers' queues
4. The document is **locked** — neither its details nor its file can change

!!! important "What is approved is what was reviewed"
    While approvers are looking at a document, nobody can change it. The edit
    page says so up front — *Under review — can't be changed while approvers are
    looking at it* — and won't save. To change a document under review, the
    person who asked for the approval [withdraws the
    request](#withdrawing-a-request), edits the draft and submits again.

### Viewing Pending Documents

Approvers:
1. Navigate to **Approvals** > **Overview**
2. See documents awaiting your approval
3. Click to review and act

Document owner:
1. Open the document
2. See approval status in header
3. View who has/hasn't approved

## Reviewing Documents

As an approver:

1. Open the document from approval queue
2. Click **Download** or **Download to View** to see the contents
3. Review the file
4. Check revision notes
5. Verify changes are correct

## Responding to an Approval Request

Approving and rejecting are one action, not two buttons:

1. Open the document and go to the **Approval** tab
2. Click **Submit Response**
3. Choose a **Decision**:

| Decision | Effect |
|----------|--------|
| **Approve** | You approve the document |
| **Reject** | You reject it; the owner is notified and can revise and resubmit |
| **Delegate** | You pass the decision to someone else. Offered only when the approval template allows delegation |

4. To approve, draw your signature, confirm it and enter your password; to
   reject, a comment is required
5. Submit the response

### Changing your response

Answered too soon, or the wrong way? While the request is still **open**, **Change
my response** takes your answer back, with a required reason. You are waiting on
again, and answer anew when you're ready. The approval history shows what you had
answered, that you withdrew it and why, and your new answer.

Once the request is decided, its responses stand.

!!! warning "Only assigned approvers see the button"
    **Submit Response** appears only if you are an assigned approver on the
    pending request — by name or through a group — and have not already
    responded. Everyone else sees *"You are not assigned as an approver for
    this document."*

    Being a tenant administrator does **not** let you respond. Approval is
    authorized **per request**, not by a global permission, so an admin who was
    not assigned to a document sees no action available. Granting someone a
    permission will not change this.

See [Approvals](../approvals/overview.md) for how the approval system works
across documents, CAPAs, and change control.

## Who gets assigned as an approver

If the wrong people — or nobody — can approve a document, the cause is almost
always the **approval template**, not permissions. Each template decides who is
assigned when a request is raised:

| Template setting | Effect |
|------------------|--------|
| **Add Person** | Specific users assigned every time, as required approvers |
| **Add Role** | The group is assigned as a whole; any member may respond |
| **Auto-assign to Group** | Assigns every member of the named group individually, as a required approver, e.g. `QA Manager` |

The starter **Document Release Approval** template names no individual default
approvers, but it auto-assigns the group **QA Manager** and adds two roles:
**QA Manager** and **Document Controller**. When a request is raised,
every QA Manager is added as a required approver and both groups may respond,
so a Document Controller *can* respond — but the release is approved only once
every QA Manager has approved.

!!! tip "To let another role approve"
    Change the template, not the permissions — add the group with **Add
    Role**. See
    [Approval Templates](../../admin/setup/approval-templates.md).

Templates also control the flow: how many approvals are required, whether they
run in parallel or in sequence, whether delegation is allowed, and whether a
requester may approve their own request.

Your electronic signature is recorded with your user identity, a timestamp, the
IP address, and your comments. See [Electronic
Signatures](../../compliance/signatures.md).

## What the Approval Tab Shows

| Section | Contents |
|---------|----------|
| **Approval Status** | The document's workflow status, e.g. Under Review |
| **Assigned Approvers** | Each approver and whether they are Pending or have responded |
| **Approval History** | Every response recorded against the request |

## Multi-Level Approval

For documents requiring multiple approvals:

### Sequential Approval
One required approver is shown as pending at a time. The order is not set by
the template, and an assigned approver may respond before their turn; the
document is approved once every required approver has approved.

### Parallel Approval
All approvers can act simultaneously:
1. All individually assigned approvers are notified at once
2. Each reviews independently
3. Complete when the template's flow is satisfied — every required approver,
   the threshold, or any one approval

## Approval Thresholds

Some templates use thresholds:
- "2 of 3 approvers must approve"
- "Any one Engineering lead"

## Viewing Approval Status

On the document:

1. Open document detail
2. Open the **Approval** tab
3. See each approver:
   - Name
   - Status — **Pending**, or their decision (**Approved**, **Rejected**,
     **Delegated**)
   - Date/time of action
   - Comments

## Withdrawing a request

Submitted with a mistake in it? The person who asked for the approval can take it
back: **Withdraw request** on the document's **Approval** tab, or on the request's
row under **Approvals** > *My Submitted Requests*. Give a reason.

- The approvers are no longer asked to decide.
- The request reads **Cancelled**, and keeps the reason.
- The document goes back to **Draft**, so it can be corrected and submitted again.

Only the requester can withdraw, and only while the request is still pending.
Approvers don't need to reject a submission that was simply made too early.

## Approval History

All approvals are permanently recorded:

1. Open document
2. Open the **Approval** tab — **Approval History**
3. See all approval events:
   - Submissions
   - Approvals
   - Rejections
   - Comments

## After Approval

When fully approved:

1. Document status becomes **Approved**
2. Document available for use
3. The person who requested approval is notified

!!! note "Approval does not make a revision current"
    A new revision becomes the current one the moment it is **created**, while
    it is still a draft — the revision it came from stops being current at the
    same instant. Approval writes only the status and who approved it when.
    See [Document Revisions](revisions.md).

## Document Expiration

If documents have expiration dates:

1. Document must be reviewed/renewed
2. May require new approval
3. Expired documents flagged

Nothing tells you a review is coming due. Check the **Due for review** tile and
list on **Home** — it is pull-only, and no message is sent.

## Approval Notifications

When a document approval request is raised, each individually assigned approver
is queued a notification directly; members of an assigned group are not
notified and see it in their **Inbox**. This does **not** go through the
notification rules, so there is no rule to configure, disable or get wrong. Approvers also see the request in their **Inbox** and on the Documents
dashboard; see [Approvals](../approvals/overview.md).

Other document events — as opposed to approval requests — are rule-driven, and
no document routing is seeded by default. See [Notification
Rules](../../admin/setup/notification-rules.md).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | View documents |
| `add_documents` | Submit for approval |
| `respond_to_approval` | Respond to a document approval request (eligibility also set by the approval template) |

## Next Steps

- [Document Revisions](revisions.md) - Version control
- [Document Library](library.md) - Managing documents
- [Compliance](../../compliance/document-control.md) - Regulatory requirements
