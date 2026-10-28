# Document Revisions

Revision control ensures documents are versioned, with complete history of changes.

## What is Revision Control?

Revision control:

- **Tracks versions** of documents over time
- **Preserves history** - all versions retained
- **Ensures current version** is identifiable
- **Supports approvals** for changes
- **Provides audit trail** of who changed what

## Versions are numbered, and that is not configurable

There is **one** concept, not two: a document carries a **version number** — a
plain integer starting at 1 and incrementing with each revision. Each version
points back to the one it superseded, and exactly one is flagged current.

!!! warning "There is no revision scheme to choose"
    uqmes does not offer letter revisions (Rev A, Rev B), letter-and-number
    schemes or date-based identifiers, and there is no administrator setting to
    pick one. Versions are 1, 2, 3.

    If your drawings are controlled as **Rev C** in the system that owns them,
    carry that in the document's **file name** or its reason-for-revision text.
    Do not expect the version number here to match your engineering revision —
    they are different identifiers, and conflating them is how people end up
    citing the wrong one in an audit.

## Creating a New Revision

### From Document Detail

1. Open the document
2. Click **Create Revision**
3. Optionally upload a new file — keeping the existing file is allowed
4. Enter the **reason for the revision**

!!! warning "The reason is required"
    A revision cannot be created without a justification. The request is
    rejected with *"change_justification is required when creating a
    revision"*.

    This is deliberate: the justification is the controlled record of **why** a
    document changed, and it is what document-control and configuration-
    management audits ask for. See [Document
    Control](../../compliance/document-control.md).

Creating a revision:

- Increments the version number
- Links the new version to the previous one
- Resets status to **Draft**
- Preserves the document type, classification, and any linked object

### Revision Status

New revisions start as **Draft** until approved (for controlled documents).

## Revision History

View all revisions of a document:

1. Open the document
2. Open the **Versions** tab
3. See the list of all revisions under **Version History**:

| Column | Description |
|--------|-------------|
| **Version** | The number — 1, 2, 3 |
| **File Name** | The revision's file |
| **Uploaded By** | Who created it |
| **Date** | When created |
| **Status** | Draft, Under Review, Released, Obsolete |
| **Change Notes** | Why it changed — the required justification |
| **Actions** | Open or download that revision |

### Accessing Previous Revisions

1. On the **Versions** tab, find the revision
2. Use the open (↗) or download icon on its row
3. Previous revision opens (read-only)

## Current vs Previous Revisions

These are **two independent things**, and reading them as one list is the
commonest misunderstanding on this page.

**Which version is current** — exactly one, always:

| | Meaning |
|---|---------|
| **Current** | The active version, what users see by default |
| **Superseded** | An earlier version, retained and still readable |

**What state that version is in** — its status, independent of the above:

| | Meaning |
|---|---------|
| **Draft** | Being worked on |
| **Under Review** | Submitted, awaiting approval |
| **Approved** | Signed off |
| **Released** | In force |
| **Obsolete** | Deliberately retired |

A version can be **Current and Draft at the same time**, and routinely is. See
the warning below.

## Making a Revision Current

Creating the revision is what makes it current — not approving it:

1. Create new revision — it is current immediately, while still Draft
2. The revision it came from stops being current at the same moment
3. Submit for approval
4. Approver approves — this changes the status only

!!! warning "A draft can be the current revision"
    Because the swap happens at creation, the current revision of a controlled
    document may be an unapproved draft for as long as approval takes. Approval
    records who signed off and when; it does not promote anything.

## Uncontrolled Documents

For documents without approval requirements the same thing happens, with no
approval step in between:

1. Create new revision
2. Immediately becomes current
3. The previous revision stays in the history, still visible and not archived

## Draft Revisions

Work on revisions before releasing:

1. Create revision as Draft
2. Upload file
3. Edit metadata
4. Can upload multiple versions while Draft
5. Submit for approval when ready

## Revision Notifications

Notifications are **rule-driven and configurable** — who gets told what is
decided by this tenant's notification rules, not by the event itself. Any rule
can be edited, disabled or deleted, so treat routing as something to check
rather than something to rely on. See [Notification
Rules](../../admin/setup/notification-rules.md).

No revision routing is seeded by default. Revision activity is visible on
the document itself and in the audit trail whether or not anyone is notified.

## External revision references

There is no field for an outside identifier — no PLM/PDM number, customer
revision or regulatory submission version. If a document is controlled as
something else in the system that owns it, carry that identifier in the
**file name** and repeat it in the **reason for the revision**.

That keeps it searchable and puts it in the controlled record, which is what an
auditor tracing your revision back to the customer's will look for.

## Retention of Revisions

All revisions are retained for:

- Audit requirements
- Regulatory compliance
- Historical reference
- Legal protection

Revisions are never deleted. Superseding a revision does not archive it either —
it simply stops being the current one. Archiving is a separate, deliberate act.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_documents` | Create revisions |
| `view_documents` | View revision history |
| `respond_to_approval` | Respond to a document approval request (eligibility also set by the approval template) |

## Next Steps

- [Document Approval](approval.md) - Approval workflows
- [Uploading Documents](uploading.md) - Adding documents
- [Document Library](library.md) - Managing documents
