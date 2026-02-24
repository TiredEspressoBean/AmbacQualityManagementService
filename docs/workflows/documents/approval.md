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
2. Click **Submit for Approval**
3. Select approval template (if multiple available)
4. Add submission notes
5. Click **Submit**

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
4. Editing is locked during approval

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
2. Click **View Document** to see contents
3. Review the file
4. Check revision notes
5. Verify changes are correct

## Approving Documents

1. Open the document or approval request
2. Click **Approve**
3. Add approval comments (optional)
4. Enter password to sign
5. Submit

Your electronic signature is recorded with:
- Your user identity
- Timestamp
- IP address (if logged)
- Approval comments

## Rejecting Documents

If the document is not acceptable:

1. Click **Reject**
2. Enter rejection reason (required)
3. Submit

The document:
- Returns to Draft status
- Owner is notified with rejection reason
- Can be revised and resubmitted

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

To withdraw a pending approval:

1. Open the document
2. Click **Recall** or **Withdraw**
3. Enter reason
4. Document returns to Draft

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
2. Revision becomes **Current**
3. Previous revision marked **Previous**
4. Document available for use
5. Owner and stakeholders notified

## Document Expiration

If documents have expiration dates:

1. Approaching expiration triggers notification
2. Document must be reviewed/renewed
3. May require new approval
4. Expired documents flagged

## Emergency Release

For urgent situations (with proper permission):

1. Click **Emergency Release**
2. Provide justification
3. Document released without full approval
4. Follow-up approval still required
5. Flagged in audit trail

## Approval Notifications

| Event | Recipients |
|-------|------------|
| Submitted for approval | Approvers |
| Approval reminder | Pending approvers |
| Approved by you | Other approvers |
| Fully approved | Document owner |
| Rejected | Document owner |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_document` | View documents |
| `change_document` | Submit for approval |
| `approve_document` | Approve/reject documents |
| `emergency_release` | Emergency release |

## Best Practices

1. **Complete before submit** - Minimize iterations
2. **Clear change notes** - Help approvers
3. **Respond promptly** - As approver, don't delay
4. **Constructive feedback** - If rejecting, explain why
5. **Document training** - Approvers understand content

## Next Steps

- [Document Revisions](revisions.md) - Version control
- [Document Library](library.md) - Managing documents
- [Compliance](../../compliance/document-control.md) - Regulatory requirements
