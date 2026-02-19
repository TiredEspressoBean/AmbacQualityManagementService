# Document Revisions

Revision control ensures documents are versioned, with complete history of changes.

## What is Revision Control?

Revision control:

- **Tracks versions** of documents over time
- **Preserves history** - all versions retained
- **Ensures current version** is identifiable
- **Supports approvals** for changes
- **Provides audit trail** of who changed what

## Revision vs Version

| Term | Meaning |
|------|---------|
| **Revision** | Major change, typically requires approval |
| **Version** | Minor update, internal draft iterations |

In Ambac Tracker, "Revision" is the primary version identifier shown to users.

## Revision Identifiers

Common revision schemes:

| Scheme | Example | When to Use |
|--------|---------|-------------|
| **Numeric** | 1, 2, 3 | Simple, sequential |
| **Letter** | A, B, C | Engineering standard |
| **Letter + Number** | A1, A2, B1 | Major.Minor |
| **Date-based** | 2026-03-15 | Date is identifier |

Your administrator configures the scheme.

## Creating a New Revision

### From Document Detail

1. Open the document
2. Click **New Revision** or **Create Revision**
3. Upload the new file
4. Enter revision information:

| Field | Description |
|-------|-------------|
| **New Revision ID** | Next revision (auto-suggested) |
| **Change Summary** | What changed |
| **Reason for Change** | Why the change was made |
| **Effective Date** | When revision takes effect |

5. Click **Create Revision**

### Revision Status

New revisions start as **Draft** until approved (for controlled documents).

## Revision History

View all revisions of a document:

1. Open the document
2. Click **Revision History** or **Versions** tab
3. See list of all revisions:

| Column | Description |
|--------|-------------|
| **Revision** | Identifier (A, B, C) |
| **Date** | When created |
| **Author** | Who created |
| **Status** | Draft, Approved, Obsolete |
| **Notes** | Change summary |

### Accessing Previous Revisions

1. In revision history, find the revision
2. Click **View** or **Download**
3. Previous revision opens (read-only)

## Comparing Revisions

Compare two revisions:

1. Open revision history
2. Select two revisions
3. Click **Compare**
4. Differences highlighted (for supported file types)

## Current vs Previous Revisions

| Status | Meaning |
|--------|---------|
| **Current** | Active revision, what users see by default |
| **Previous** | Superseded, retained for reference |
| **Draft** | In progress, not yet released |
| **Obsolete** | Retired, should not be used |

Only one revision is "Current" at a time.

## Making a Revision Current

For controlled documents, approval makes a revision current:

1. Create new revision (Draft)
2. Submit for approval
3. Approver approves
4. New revision becomes Current
5. Previous revision becomes Previous

## Uncontrolled Documents

For documents without approval requirements:

1. Create new revision
2. Immediately becomes current
3. Previous revision archived

## Draft Revisions

Work on revisions before releasing:

1. Create revision as Draft
2. Upload file
3. Edit metadata
4. Can upload multiple versions while Draft
5. Submit for approval when ready

## Revision Notifications

| Event | Recipients |
|-------|------------|
| New revision created | Document owner |
| Revision submitted for approval | Approvers |
| Revision approved | Document owner, stakeholders |
| Revision rejected | Document owner |

## External Revision References

Link to external revision systems:

- PLM/PDM document numbers
- Customer revision identifiers
- Regulatory submission versions

## Retention of Revisions

All revisions are retained for:

- Audit requirements
- Regulatory compliance
- Historical reference
- Legal protection

Revisions are never deleted (may be archived).

## Permissions

| Permission | Allows |
|------------|--------|
| `change_document` | Create revisions |
| `view_document` | View revision history |
| `approve_document` | Approve revisions |

## Best Practices

1. **Increment correctly** - Follow revision scheme
2. **Clear change notes** - What and why
3. **Submit promptly** - Don't leave drafts lingering
4. **Review before release** - Verify changes
5. **Link to changes** - ECO, CAPA, etc.

## Next Steps

- [Document Approval](approval.md) - Approval workflows
- [Uploading Documents](uploading.md) - Adding documents
- [Document Library](library.md) - Managing documents
