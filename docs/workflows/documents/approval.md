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

## Approval Workflow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Draft   │────▶│ Pending  │────▶│ Approved │────▶│ Released │
│          │     │ Approval │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │
                      ▼
                ┌──────────┐
                │ Rejected │
                │          │
                └──────────┘
```

## Submitting for Approval

### From Document Detail

1. Open the document (in Draft status)
2. Go to the **Approval** tab — it shows *"Document Not Yet Submitted"*
3. Click **Submit for Approval**

Once submitted, the designated approvers are notified and the document moves to
**Under Review**.

### Approval Templates

Templates define:

- Who needs to approve
- Approval order (sequential/parallel)
- Number of approvals required

Example template: "Engineering Approval"
- Requires: 1 Engineering approval, 1 QA approval
- Order: Sequential (Engineering first)

## Under Review

After submission:

1. Document status changes to **Under Review**
2. Approvers are notified
3. Document appears in approvers' queues
4. The document stays editable — both metadata and the file

!!! warning "Review does not lock the document"
    Nothing is locked while a document is under review. The file can only be
    swapped once the document is **Approved** or **Released**; until then an
    editor can replace the very file the approvers are reading. If that matters
    for your process, it is a convention to hold to, not a rule the system
    enforces.

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
| **Approved** | You approve the document |
| **Rejected** | You reject it; the owner is notified and can revise and resubmit |
| **Delegated** | You pass the decision to someone else |

4. Add comments, and sign if the approval template requires it
5. Submit the response

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
| **Default approvers** | Specific users assigned every time |
| **Default groups** | Every member of those groups assigned |
| **Auto-assign by role** | Assigns the named group, e.g. `QA Manager` |

The starter **Document Release Approval** template names no individual default
approvers, but it does seed two default groups: **QA Manager** and **Document
Controller**. Every member of either group is assigned when a request is raised,
so a Document Controller *can* approve a document release out of the box.

!!! tip "To let another role approve"
    Change the template, not the permissions — add the group to **Default
    groups**. See
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
Approvers act in order:
1. First approver reviews and approves
2. Second approver is notified
3. Continue until all approve

### Parallel Approval
All approvers can act simultaneously:
1. All approvers notified at once
2. Each reviews independently
3. Complete when all approve (or threshold met)

## Approval Thresholds

Some templates use thresholds:
- "2 of 3 approvers must approve"
- "Any one Engineering lead"

## Viewing Approval Status

On the document:

1. Open document detail
2. View **Approvals** section
3. See each approver:
   - Name
   - Status (Pending, Approved, Rejected)
   - Date/time of action
   - Comments

## Recalling a Submission

!!! note "Not available"
    There is no recall or withdraw control on the document approval tab. A
    submitted document stays under review until the assigned approvers respond.

    If a submission was made in error, ask an approver to **reject** it — the
    document returns to the owner and can be revised and resubmitted.

Use when:
- Errors found after submission
- Need to make additional changes
- Wrong template selected

## Approval History

All approvals are permanently recorded:

1. Open document
2. View **History** tab
3. See all approval events:
   - Submissions
   - Approvals
   - Rejections
   - Comments

## After Approval

When fully approved:

1. Document status becomes **Approved**
2. Document available for use
3. Owner and stakeholders notified

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

Nothing tells you a review is coming due. Check the **due for review** list on
the Documents page — it is pull-only, and no message is sent.

## Approval Notifications

When a document approval request is raised, each assigned approver is queued a
notification directly. This does **not** go through the notification rules, so
there is no rule to configure, disable or get wrong — approvers are told either
way. Approvers also see the request in their **Inbox** and on the Documents
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
