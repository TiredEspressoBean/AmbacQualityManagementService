# Document Control

Document management for regulated environments.

## Regulatory Requirements

| Standard | Key Requirements |
|----------|------------------|
| **ISO 9001** | Document control procedure, revision control |
| **AS9100D** | Configuration management |
| **IATF 16949** | Controlled documents, approval before release |

## Document Control Features

### Revision Control
- All revisions retained
- Version history tracked
- Changes documented
- Previous versions accessible

### Approval Workflow
- Configurable approval templates
- Electronic signatures
- Approval records retained
- Rejection tracking

### Access Control

Five classification levels — **Public, Internal, Confidential, Restricted,
Secret** — plus per-document links and customer access control.

!!! warning "Only Secret withholds a document from the shop floor"
    Confidential and Restricted are by default both held by **every staff role**, Operator
    included. They separate staff from **customers and auditors**, not managers
    from the floor.

    **Secret** is the only tier that restricts within staff — Tenant Admin and
    Document Controller. Note a QA Manager can classify a document Secret and
    then be unable to read it back.

    If a control plan or a customer drawing must not be visible to the floor,
    Confidential will not do it.

### Audit Trail
- Changes made in the application logged — see [Audit Trails](audit-trails.md)
- Who, what, when recorded
- Immutable records

## Document Lifecycle

```
Draft → Review → Approval → Released → Current
                    ↓
                 Rejected → Revision → (back to Review)

Released (previous) → Obsolete
```

### Status Definitions

| Status | Meaning |
|--------|---------|
| **Draft** | Work in progress, not yet submitted |
| **Under Review** | Submitted; approvers are responding |
| **Approved** | Approvals complete — the decision is made |
| **Released** | In force; this is the revision people must work to |
| **Obsolete** | Superseded or withdrawn, retained for history |

!!! note "Approved and Released are separate"
    Approval records the decision; release puts the document into force. The
    gap is deliberate — a revision can be approved ahead of the date, training,
    or tooling change it depends on, and only released when the floor is ready
    for it. There is no *Archived* status: obsolete revisions are retained, not
    archived.

## Creating Controlled Documents

1. Upload the document — **its filename becomes the document's name**; there is
   no title field
2. Set the classification level, and the document type if one applies
3. Save as draft
4. Submit for approval from the document's **Approval** tab
5. The approval workflow proceeds

**Approval does not release the document.** It reaches **Approved**, and
putting it into force is a separate, deliberate act — see *Approved and Released
are separate* above.

## Revision Process

1. Open existing document
2. Click **Create Revision**
3. Enter the **Change Justification** (required) and, optionally, a new file
4. Click **Create Revision** — the new revision, in Draft, becomes the current
   version of the document
5. Submit it for approval — or, if its document type needs no approval,
   release the draft directly
6. Release it once approved — releasing it makes the previously released
   revision obsolete

## Change Documentation

Each revision carries one field for its change record: the **Change
Justification** — what changed and why. A revision is refused without it.

## Distribution Control

Track document distribution:

### For Internal Documents
- Available to permitted users, by classification level
- Access logged

### For External Distribution

!!! warning "Controlled-copy features are not built"
    There is **no watermarking, no controlled-copy numbering and no distribution
    register** in uqmes. A document handed to an outside party leaves the
    system's control at that point.

    If your procedure requires controlled copies, that control lives outside
    this system and you own it.

## Obsolete Document Handling

Releasing a new revision obsoletes earlier released revisions automatically;
obsoleting a document with no successor is a deliberate act (`release_documents`).

When documents become obsolete:
- Clearly marked as obsolete
- **Still visible in the library**; they are not hidden or removed from views
- Retained for historical reference
- Accessible for audit purposes

## Periodic Review

A document type carries a **Review Period (days)**. When a document of that type
is released, its **review date** is set to the effective date plus that period.

Released documents whose review date has arrived are listed as due for review —
the **Periodic review due** list on the Home page of the Document Controller,
QA Manager and Tenant Admin, and a **Due for review** count. There is no review
owner and no reminder notification; whoever keeps the document library reads
that list.

## Document Retention

Retention per document type:

| Type | Typical Retention |
|------|-------------------|
| Quality Records | Per regulatory requirements |
| Work Instructions | Life of product + years |
| Certificates | Per certification body |
| Contracts | Per legal requirements |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | View documents |
| `add_documents` | Create documents and revisions; submit for approval |
| `change_documents` | Edit |
| `release_documents` | Release, mark obsolete, and reinstate |
| `classify_documents` | Change a document's classification after upload — the uploader picks any classification at upload |
| `view_confidential_documents` | Access CONFIDENTIAL docs |
| `view_restricted_documents` | Access RESTRICTED docs |
| `view_secret_documents` | Access SECRET docs |
| `respond_to_approval` | Approve documents when assigned |

## Next Steps

- [Document Approval](../workflows/documents/approval.md) - Approval process
- [Document Library](../workflows/documents/library.md) - Using documents
- [Audit Trails](audit-trails.md) - Compliance logging
