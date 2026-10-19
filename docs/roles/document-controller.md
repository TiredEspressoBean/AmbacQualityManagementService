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

!!! important "Two different numbers, and only one of them is your work"
    Home shows **Approvals in flight** and **Needs my approval**. The first is
    everything moving through the system, whatever its type — you will routinely
    see CAPA approvals and process changes there. The second is what is actually
    assigned to you.

    **Seeing an approval does not mean you can act on it.** Out of the box you
    are an assigned approver for **Document Release** only; the CAPA templates
    assign other groups. So a queue showing five in flight and zero
    needing you is working correctly, not broken.

    Your tenant *can* route other approval types to you — the assignment comes
    from the approval template, not from your role's permissions — so if that has
    been configured, the queue genuinely becomes mixed and anything assigned to
    you has nobody else coming for it. Check [Approval
    Templates](../admin/setup/approval-templates.md) for what your facility
    routes where.

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
2. Use filters: **document type**, **approval status**, **is-image** and
   **needs my approval**
3. Search by **file name**, or by the **uploader's email** — the way to find
   what one person uploaded, since there is no created-by filter

There is no date-range filter.

### Document Organization

A document carries a **type** and a **classification**, and is **linked** to the
records it concerns — a part type, an order, a process. There are no product-line
or department fields; organise by type, and find by what it is linked to.

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

- **The number increments itself** — versions are 1, 2, 3 and there is no scheme
  to pick. If your drawings are controlled as *Rev C* elsewhere, keep that in the
  file name; the version number here is a different identifier
- Write the reason so a reader can tell what changed *and* why
- Reference the change request if there is one
- Never overwrite — always create a revision

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

Distribution is **access**, not a list of recipients. A released document is
readable by whoever its **classification** allows; a customer sees only
**Public** documents linked to their own orders.

- **Nobody is told about a new revision** unless your organisation has a
  notification rule for it — none is set up by default. See [Notification
  Rules](../admin/setup/notification-rules.md)
- There is no distribution record of who received which revision, and no
  watermarking. If your procedure needs either, it happens outside uqmes

## Document Types Management

### Working with Types

Each type has:
- Whether approval is required, and on which template
- A default review period
- A default retention period

There is no numbering scheme per type — see [Document
Types](../admin/setup/document-types.md).

### Common Document Types

| Type | Typical Control |
|------|-----------------|
| Work Instruction, SOP, Policy, Control Plan | Requires approval |
| Specification, Drawing, BOM | Requires approval |
| Form / Checklist | Requires approval |
| Certificate of Conformance, Material Test Report, Calibration Certificate | Reference — no approval |
| Equipment Manual, Safety Data Sheet | Reference — no approval |

The default catalogue is much longer than this — 39 types,
including the quality records the system generates itself (inspection reports,
NCRs, containment evidence) and the IATF/AS9100 set (PPAP, PSW, FMEA, 8D, FAI).

!!! note "Whether a type needs approval is a setting, not a rule"
    Nothing about being a "drawing" forces approval — it is the **Requires
    approval** flag on the type, which your administrator can change. The
    pattern in the defaults is that *things the shop writes* need approval and
    *things that arrive or are generated as evidence* do not.

    A type can also be pointed at a specific approval template rather than the
    default Document Release, so two types can route to different approvers.

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

### Answering an auditor

There are no document compliance reports to generate. The answers come from
lists you can filter and export:

- **Status by type** — the document list, filtered by type and status
- **Pending reviews** — **Due for review** on Home
- **Approval history** — **Approvals** > **History**
- **Obsolete documents** — the document list, filtered by status

## Training Integration

### Linking to Training

A new document revision does not touch training records, and there is no
read-and-acknowledge step for a document. If a revision means people need
retraining, record that as training — see [Training
Matrix](../workflows/tracking/training-matrix.md).

## Weekly Tasks

- [ ] Process pending uploads
- [ ] Follow up stalled approvals
- [ ] Review upcoming periodic reviews
- [ ] Check **Due for review** on Home
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
