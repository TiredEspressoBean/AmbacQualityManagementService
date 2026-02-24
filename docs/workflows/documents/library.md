# Document Library

The Document Library is the central repository for all controlled documents in Ambac Tracker.

## Accessing the Library

Navigate to **Documents** in the Tools section of the sidebar.

## Library Overview

The Document Library provides:

- **Centralized storage** for all documents
- **Version control** with revision history
- **Approval workflows** for controlled documents
- **Search and filtering** to find documents
- **Access control** based on permissions

## Document Dashboard

The Documents landing page shows:

### Quick Stats
- Total documents
- Pending approval
- Recently updated
- Expiring soon

### Recent Documents
Last 10 documents you accessed or were shared with you.

### Pending Actions
Documents requiring your attention (review, approval).

## Browsing Documents

### List View

See all documents in a table:

| Column | Description |
|--------|-------------|
| **Title** | Document name |
| **Type** | Category (Drawing, Spec, etc.) |
| **Revision** | Current version |
| **Status** | Draft, Under Review, Approved, Released, Obsolete |
| **Updated** | Last modified date |

### Filtering

Narrow results by:

- **Document Type**: Work Instruction, Drawing, etc.
- **Status**: Draft, Under Review, Approved, Released, Obsolete
- **Date Range**: Created or modified within period
- **Created By**: Author
- **Linked To**: Associated order, part type

### Sorting

Click column headers to sort:

- By title (A-Z, Z-A)
- By date (newest, oldest)
- By type
- By status

## Searching Documents

Use the search bar to find documents by:

- Title or filename
- Document number
- Content (if text-searchable)
- Associated records

## Document Types

Documents are categorized by type:

| Type | Purpose | Typical Control |
|------|---------|-----------------|
| **Drawing** | Part or assembly drawings | Approved |
| **Specification** | Technical requirements | Approved |
| **Work Instruction** | Step-by-step procedures | Approved |
| **Form** | Blank forms for records | Approved |
| **Certificate** | Quality certifications | Reference |
| **Report** | Test or inspection reports | Record |
| **Contract** | Customer agreements | Reference |

Your administrator configures available document types.

## Document Status

| Status | Meaning |
|--------|---------|
| **Draft** | Work in progress, not released |
| **Under Review** | Submitted for approval workflow |
| **Approved** | Approved but not yet released |
| **Released** | Released for use (effective date set) |
| **Obsolete** | Superseded, no longer valid |

## Classification Levels

| Level | Access | Description |
|-------|--------|-------------|
| **Public** | All users | General information |
| **Internal** | Employees | Internal use only |
| **Confidential** | Managers+ | Sensitive information |
| **Restricted** | Limited access | Serious impact if disclosed |
| **Secret** | Critical access | Critical impact if disclosed |

## Opening Documents

Click a document to view:

### Detail Page
- Document metadata
- Current revision
- Approval status
- Linked records

### File Preview
- PDF documents display inline
- Images display inline
- Other files show download link

### Actions Available
- Download
- View history
- Create revision
- Link to records

## Downloading Documents

1. Open the document
2. Click **Download**
3. File downloads to your computer

For controlled documents, downloads may be:

- Logged in audit trail
- Watermarked with user/date
- Restricted to current revision

## Linking Documents

Documents can be linked to:

- **Orders**: Order-specific documents
- **Parts**: Part-specific documents
- **Processes**: Process procedures
- **Steps**: Step work instructions
- **CAPAs**: Investigation evidence
- **Quality Reports**: NCR attachments

### Creating Links

From document:
1. Open document
2. Click **Link to...**
3. Select record type
4. Search and select record

From record:
1. Open order, part, etc.
2. Go to Documents section
3. Click **Add Document**
4. Search and select document

## Folder Organization

Documents can be organized in folders:

- Create folder hierarchy
- Move documents between folders
- Folder-level permissions (optional)

## Permissions

| Permission | Allows |
|------------|--------|
| `view_document` | View documents |
| `view_confidential` | View confidential documents |
| `add_document` | Upload documents |
| `change_document` | Edit, create revisions |
| `delete_document` | Remove documents |
| `approve_document` | Approve document revisions |

## Best Practices

1. **Descriptive titles** - Clear, searchable names
2. **Correct type** - Proper categorization
3. **Link appropriately** - Connect to related records
4. **Use revisions** - Don't overwrite, create new version
5. **Complete metadata** - Fill in all relevant fields

## Next Steps

- [Uploading Documents](uploading.md) - Adding new documents
- [Document Revisions](revisions.md) - Version control
- [Document Approval](approval.md) - Approval workflows
