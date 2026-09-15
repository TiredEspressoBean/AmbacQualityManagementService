# Document Library

The Document Library is the central repository for all controlled documents in uqmes.

## Accessing the Library

Navigate to **Documents** in the sidebar.

## Library Overview

The Document Library provides:

- **Centralized storage** for all documents
- **Version control** with revision history
- **Approval workflows** for controlled documents
- **Search and filtering** to find documents
- **Access control** based on permissions

## Document Dashboard

The Documents landing page shows:

Two cards:

| Card | Goes to |
|------|---------|
| **View All Documents** | Browse and search documents |
| **Upload Document** | Add a new document to the system |

When something needs you, a **Documents Needing Approval** card appears with
the count, e.g. *"1 document(s) require your review"*.

Below the cards is a list of recent documents, each showing its name, who
uploaded it, and when.

## Browsing Documents

### List View

See all documents in a table:

| Column | Description |
|--------|-------------|
| **File Name** | Document name |
| **ID** | Record identifier |
| **Version** | Current version |
| **Status** | Draft, Under Review, Approved, Released, Obsolete |
| **Type** | Category (Drawing, Work Instruction, etc.) |
| **Classification** | e.g. Internal |
| **Uploaded** | Upload date |
| **Uploaded By** | Who uploaded it |
| **Actions** | Row actions |

### Filtering

Narrow results with:

- **All document types** — Work Instruction, Drawing, etc.
- **All Status** — Draft, Under Review, Approved, Released, Obsolete
- **All Is Image** — whether the file is an image
- **Needs My Approval** — only documents awaiting your response

!!! note "No date or author filter"
    There is no date-range or created-by filter. To find a document by its
    uploader, use the search box — it matches on file name and uploader email.

### Sorting

Use the **Sort by...** dropdown. Column headers are not clickable.

## Searching Documents

The search box on the document list is scoped, as its placeholder says —
*"Search by File Name, Uploaded By Email..."*:

- **File name**
- **Uploader email**

!!! note "Not full-text search"
    Document *contents* are not searched. Neither are associated records. To
    find a document by what it is attached to, open that record and look at its
    Documents section instead.

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

### Viewing Files
- Click **Download** to view documents
- Files open in a new browser tab
- Supported formats display in browser (PDF, images)

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

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | View documents |
| `view_confidential_documents` | View confidential documents |
| `add_documents` | Upload documents |
| `change_documents` | Edit, create revisions |
| `delete_documents` | Remove documents |
| `respond_to_approval` | Respond to a document approval request (eligibility also set by the approval template) |

## Next Steps

- [Uploading Documents](uploading.md) - Adding new documents
- [Document Revisions](revisions.md) - Version control
- [Document Approval](approval.md) - Approval workflows
