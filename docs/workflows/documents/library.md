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

The Documents landing page opens with four counts: **Total Documents**,
**Pending Approval**, **Needs My Approval** and **My Uploads**. Below them:

| Card | Contents |
|------|---------|
| **Quick Actions** | **View All Documents** (browse and search) and **Upload Document** (add a new document — shown if you may upload) |
| **Pending My Approval** | Documents waiting on your response |
| **Recently Updated** | The most recently changed documents, each with its name, uploader and last-updated date |

### When approvals are waiting for you

Two separate things surface them, and they are not duplicates:

**Documents Needing Approval** — an orange banner that appears only when there
is something to do, e.g. *"1 document(s) require your review"*. Clicking it
opens the document list with **Needs My Approval** already on, showing only
yours.

**Pending My Approval** — a panel listing the documents themselves, with a
count badge, each linking straight to the document. When there is nothing
outstanding it reads *"No approvals pending"*.

The banner tells you there is work; the panel is how you pick it up.

!!! note "If the panel is empty, check you are an assigned approver"
    Approval is authorized per request, so a document can be awaiting approval
    generally and still not be *yours*. Holding a permission does not put a
    request in your list — the approval template's assignment does. See [Who
    can approve](../approvals/overview.md#who-can-approve).

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

Documents are categorized by type. Some of the starter types:

| Type | Purpose | Requires approval |
|------|---------|-------------------|
| **Drawing/Print** | Engineering drawings and prints | Yes |
| **Specification** | Technical requirements | Yes |
| **Work Instruction** | Step-level instructions | Yes |
| **Form/Checklist** | Blank forms and checklist templates | Yes |
| **Certificate of Conformance** | Supplier certificates for incoming material | No |
| **Inspection Report** | Quality inspection reports | No |
| **Test Report** | Test results | No |

Your administrator configures available document types.

## Document Status

| Status | Meaning |
|--------|---------|
| **Draft** | Work in progress, not released |
| **Under Review** | Submitted for approval workflow |
| **Approved** | Approved but not yet released |
| **Released** | Released for use (effective date set) |
| **Obsolete** | Superseded, no longer valid |

### Taking a document out of circulation

Two different acts, and the difference matters to an auditor:

| | Use it when | What happens |
|---|---|---|
| **Obsolete** | The document was real and has been superseded | Stays in the library, marked Obsolete, with its history and the revision that replaced it |
| **Delete** | It should never have been there — a duplicate, the wrong file, a test upload | Removed from the library |

!!! important "Deleting is archiving — the record survives"
    uqmes soft-deletes. A deleted document is taken **out of circulation**, not
    destroyed: the row and its audit trail remain, and the deletion itself is
    recorded. You are not removing evidence, and you could not if you tried.

!!! warning "Prefer Obsolete for anything that was ever in force"
    A superseded document that is deleted rather than obsoleted loses the one
    thing an auditor asks for — *why* it stopped being the version people work
    to. Obsolete says that; delete does not.

    **Revisions are never deleted** at all, only archived, so a document's
    history stays intact regardless.

**Mark obsolete** asks you to confirm. It takes effect from today, and the document
is kept for its retention period.

#### Obsoleted by mistake

**Reinstate** on the obsolete document puts it back in force, with a required
reason. It is released again if it had been released, or approved if it hadn't, and
its obsolete date clears. The change and the reason show under *Corrections* on the
document's **Audit Trail**.

A revision that a later revision replaced can't be reinstated. The newer one is in
force, so revise that instead. Reinstating needs the same permission as releasing
(`release_documents`).

Deleting needs `delete_documents`, by default held by **Document Controller, QA Manager,
Production Manager, Engineering and Tenant Admin** — the authoring and manager
tiers. Operators, inspectors, the dock and auditors cannot.

## Classification Levels

| Level | Who can see it | Needs |
|-------|----------------|-------|
| **Public** | Everyone, including customers | — |
| **Internal** | All staff | the staff view base |
| **Confidential** | All staff | `view_confidential_documents` |
| **Restricted** | All staff | `view_restricted_documents` |
| **Secret** | **Tenant Admin and Document Controller only** | `view_secret_documents` |

!!! warning "Confidential and Restricted are not manager-only"
    Every internal role — Operator and the dock included — holds both
    `view_confidential_documents` and `view_restricted_documents`. They separate
    staff from **customers and auditors**, not managers from the floor.

    If you need a document kept from most of the shop, **Secret** is the only
    tier that does it.

!!! important "QA Manager can classify, but cannot read Secret"
    The level chosen at upload is the uploader's choice. Changing an existing
    document's level needs `classify_documents`, by default held by **Tenant
    Admin, QA Manager and Document Controller**. `view_secret_documents` is by
    default held by **Tenant Admin and Document Controller** only.

    So a QA Manager can mark a document Secret and then not be able to open it.
    Worth knowing before you use that tier.

!!! note "An auditor holds none of the classified tiers"
    The Auditor role is not given the classified tiers. A document invisible to
    an auditor is the control working.

!!! note "Export control is a separate filter, keyed to the user"
    Where a deployment uses ITAR/EAR filtering, it reads the *US person* and
    *ITAR authorized* flags on the **user record**, independently of the
    classification tiers and of group membership.

## Opening Documents

Click a document to view:

### Detail Page
- Document metadata
- Current revision
- Approval status
- Linked records

### Viewing Files
- The **Overview** tab's **File Preview** shows images and PDFs in the page
- Other file types show **Download to View** instead
- **Download** saves the file to your computer

### Actions Available
The detail page header offers:

- Download
- Create Revision
- Edit — where the main link and the rest of the metadata live

## Downloading Documents

1. Open the document
2. Click **Download**
3. File downloads to your computer

Every download is recorded in the document's access log. Files are not
watermarked, and earlier revisions stay downloadable from the **Versions** tab.

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
2. Click **Edit**
3. Find the **Link To (Optional)** field
4. Search and select the record, then save

**Edit → Link To** sets the document's main record. To link it to an
additional order, part, part type or work order as well, use **Attach** under
**Also Linked To** on the document's **Overview** tab.

From record: under **Attach Document** on its edit form (or a CAPA's
**Documents** tab), **Upload** a new file — it is attached to that record. To link an existing document, do it from the document
(above).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | View documents |
| `view_confidential_documents` | View confidential documents |
| `add_documents` | Upload documents, create revisions |
| `change_documents` | Edit document details |
| `add_documentlink` | Attach a document to an additional record |
| `delete_documents` | Remove documents |
| `respond_to_approval` | Respond to a document approval request (eligibility also set by the approval template) |

## Next Steps

- [Uploading Documents](uploading.md) - Adding new documents
- [Document Revisions](revisions.md) - Version control
- [Document Approval](approval.md) - Approval workflows
