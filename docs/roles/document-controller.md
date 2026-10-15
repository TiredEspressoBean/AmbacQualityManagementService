# Document Controller Guide

This guide is for Document Controllers who manage controlled documents, revisions, approvals, and document compliance.

## Your Role

As a Document Controller, you:

- Upload and manage documents
- Control document revisions
- Route documents for approval
- Maintain document compliance
- Manage document distribution
- Ensure proper retention

## Getting Started

### First-Time Setup

1. Log in and review document library
2. Understand document types and workflows
3. Configure notification preferences

### Your Main Pages

| Page | Location | Purpose |
|------|----------|---------|
| **Documents** | Documents | Document dashboard |
| **Document List** | Documents > View All Documents | All documents |
| **Inbox** | Personal > Inbox | Pending approvals and tasks |
| **Approvals** | Approvals > Overview | Pending approval requests |
| **Approval History** | Approvals > History | Approval records |

!!! important "Your approvals queue is not document-only"
    The queue routes **every** approval type you are an assigned approver for —
    CAPA approvals, process changes and training certifications sit in it
    alongside document releases, and on a working system the non-document ones
    are often the majority.

    That is deliberate: you are an **approvals operator**, not only a document
    operator. Do not filter the queue down to documents and assume the rest is
    somebody else's — if a request is assigned to you, nobody else is coming
    for it.

## Daily Workflow

### 1. Check Pending Items

1. Navigate to **Personal > Inbox**
2. Review documents pending your action
3. Check approval queue
4. Note any urgent items

### 2. Process Requests

- Upload new documents as requested
- Create revisions for updates
- Route for appropriate approvals
- Release approved documents

### 3. Monitor Status

1. Check document approval status
2. Follow up on stalled approvals
3. Address any rejections

## Document Library

### Browsing Documents

1. Navigate to **Documents**
2. Use filters:
   - Document type
   - Status
   - Date range
   - Created by
3. Search by title or number

### Document Organization

Organize by:
- Document type (Work Instructions, Specs, etc.)
- Product line
- Department
- Process

## Uploading Documents

### New Document

1. Navigate to **Documents**
2. Click **Upload Document**
3. Select file
4. Fill in metadata:

| Field | Description |
|-------|-------------|
| **Document Type** | Category — also decides whether approval is required |
| **Link To** | Records to attach the document to |

5. Set **Classification Level** — Public, Internal, Confidential, Restricted or
   Secret. You hold both `classify_documents` and `view_secret_documents`, so
   all five are genuinely yours to use and to read back.
6. Upload

The document's name comes from the file you upload; there is no title,
description or document-number field to fill in. See [Uploading
Documents](../workflows/documents/uploading.md).

### Metadata Best Practices

- Clear, searchable file names
- Accurate document type
- Complete descriptions
- Proper visibility setting

## Revision Control

### Creating New Revision

1. Open existing document
2. Click **Create Revision**
3. Upload a new file **if the content changed** — keeping the existing file is
   allowed, for a revision that only changes metadata or re-approves
4. Enter the **reason for the revision** — this is the one required field
5. Submit for approval

!!! note "One field, not two"
    There is no separate Change Summary. The reason for the revision is the
    whole of the written record, so say what changed *and* why in it.

### Revision Best Practices

- Increment revision per scheme (A, B, C or 1, 2, 3)
- Clear change notes
- Reference ECO/change request if applicable
- Don't overwrite—always create revision

## Approval Workflow

### Submitting for Approval

1. Open the document (in Draft)
2. Go to the **Approval** tab
3. Click **Submit for Approval**

There is no template to choose and no submission notes field. The approval
template is selected by approval *type*, not by you.

### Tracking Approval

1. View document detail
2. Check **Approvals** section
3. See status per approver
4. Follow up if delayed

### Handling Rejections

When document is rejected:

1. Review rejection comments
2. Make required changes
3. Create new revision
4. Resubmit for approval

## Managing Approvals

### Your Approval Queue

If you're also an approver:

1. Check **Inbox**
2. Review pending documents
3. Open and review content
4. Approve or reject with comments

### Approval Tips

- Review thoroughly
- Add constructive comments
- Sign promptly
- Don't delay the queue

## Document Distribution

### Internal Distribution

For released documents:
- Available per permissions
- Users notified of new versions
- Old versions clearly marked

### External Distribution

For customer documents:
- Set visibility appropriately
- Track distribution
- Consider watermarking

## Document Types Management

### Working with Types

Each type has:
- Approval requirements
- Retention settings
- Numbering scheme

### Common Document Types

| Type | Typical Control |
|------|-----------------|
| Work Instruction | Requires approval |
| Specification | Requires approval |
| Drawing | Requires approval |
| Form | Requires approval |
| Certificate | Reference (no approval) |
| Manual | Reference |

## Obsolete Documents

### Making Documents Obsolete

Marking a document obsolete is always a deliberate act — use **Mark Obsolete**
on the document. Creating or approving a new revision does **not** do it for
you; the superseded revision simply stops being the current one and keeps
whatever status it had.

!!! warning "Obsoleting is yours to remember"
    Nothing retires the old revision automatically. If your process says
    superseded documents must read Obsolete, that is a step on your checklist.

### Handling Obsolete Docs

- Clearly marked in system
- Retained for historical reference
- Accessible for audit purposes

Obsolete documents are **not** hidden. They stay in the library alongside
everything else, and status is a filter you choose — so anyone browsing can
still find and open them.

## Periodic Review

### Setting Up Reviews

1. Configure review interval per type
2. System tracks next review date

Nothing notifies you when a review falls due. **Home** carries it: a *Due for
review* tile under the Documents block, and a list of the documents themselves.
That is the only thing that will tell you, and you have to go and look.

### Conducting Review

When review is due:
1. Evaluate if document is still current
2. Update if needed (new revision)
3. Re-approve if current
4. Document review completion

## Compliance

### Audit Preparation

Maintain ready:
- Complete document inventory
- Revision histories
- Approval records
- Distribution records

### Compliance Reports

Generate reports for:
- Document status by type
- Pending reviews
- Approval history
- Obsolete documents

## Training Integration

### Linking to Training

When documents update:
1. Identify affected personnel
2. Training may be required
3. Coordinate with training manager
4. Track acknowledgments

## Weekly Tasks

- [ ] Process pending uploads
- [ ] Follow up stalled approvals
- [ ] Review upcoming periodic reviews
- [ ] Check for expired documents
- [ ] Update document inventory

## Quick Reference

| Task | Steps |
|------|-------|
| Upload document | Documents → **Upload Document** → Fill form → Save |
| Create revision | Open doc → **Create Revision** → file (optional) → reason → Submit |
| Submit for approval | Open doc (Draft) → **Approval** tab → **Submit for Approval** |
| Check approval status | Open doc → View Approvals section |

## Related Documentation

- [Document Library](../workflows/documents/library.md)
- [Uploading Documents](../workflows/documents/uploading.md)
- [Document Revisions](../workflows/documents/revisions.md)
- [Document Approval](../workflows/documents/approval.md)
- [Document Control (Compliance)](../compliance/document-control.md)
