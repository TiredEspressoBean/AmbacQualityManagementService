# Document Types

Configure categories for documents with specific handling rules.

## What are Document Types?

Document Types define:
- **Categories** for organizing documents
- **Approval requirements** per type
- **Retention policies**
- **Access controls**

## Default Document Types

**About forty document types are seeded into every organisation**, covering far more
than the handful below: procedures and work instructions, drawings and CAD, material
and test certificates (MTR, CoC, CoA, SDS), inspection and nonconformance records
(IR, NCR, 8D, CAR, SCAR, FAI), automotive submissions (PPAP, PSW, FMEA, MSA, AAR),
engineering change records (ECR, ECO), commercial documents (PO, NDA, Quality
Agreement) and training records.

!!! warning "Look at the list before creating a type"
    The most common mistake here is creating a type that already exists under a
    different name — a "Certificate of Conformance" when **COC** is already there,
    or an "Inspection Report" alongside **IR**. Duplicates split the document library
    in two, and nothing warns you.

    Open **Document Types** and read the list first. Create one only when nothing
    fits, which is rarer than it looks.

A few of the most-used, to show the shape:

| Type | Purpose | Approval |
|------|---------|----------|
| **Work Instruction** | Step-by-step procedures | Required |
| **Specification** | Technical requirements | Required |
| **Drawing** | Engineering drawings | Required |
| **Form** | Blank forms/templates | Required |
| **Certificate** | Certifications, CoCs | Reference |
| **Report** | Test/inspection reports | Optional |
| **Contract** | Agreements, POs | Reference |
| **Manual** | Equipment manuals | Reference |

## Creating Document Types

1. Navigate to **Data Management** > **Document Types**
2. Click **New Document Types**
3. Fill in details:

| Field | Description |
|-------|-------------|
| **Name** *(required)* | Type name |
| **Code** *(required)* | Short code, e.g. WI, SPEC |
| **Description** | When to use this type |
| **Review Period (days)** | How often documents of this type should be reviewed |
| **Retention Period (days)** | How long to keep them |
| **Requires Approval** | Whether documents need approval before release |
| **Approval Template** | Which approval flow to use when approval is required |

Submit with **Create Document Type**.

!!! tip "Review period drives the review queue"
    **Review Period** is what populates **Due for review** on **Home**. A type
    with no review period never prompts a review.

4. Save

## Document Type Settings

### Approval Settings

| Setting | Description |
|---------|-------------|
| **Requires Approval** | Documents need approval before release |
| **Approval Template** | Which approval flow is used |

There is no auto-archive-previous setting. Superseding is handled by
[revisions](../../workflows/documents/revisions.md): a new revision links to
the version it replaces.

### Retention Settings

| Setting | Description |
|---------|-------------|
| **Retention Period (days)** | How long to keep documents of this type |
| **Review Period (days)** | How often they should be reviewed |

There is no retention *action* or retention category — the period is recorded,
and acting on it is a procedural decision.

### Access Settings

!!! note "Not set on the document type"
    Visibility is a property of each **document**, through its
    **classification** (e.g. Internal), not of its type. Two documents of the
    same type can carry different classifications. See [Export
    Controls](../../compliance/export-controls.md).

## Document Numbering

!!! note "Planned Feature"
    There is no configurable numbering pattern per document type. Document
    identifiers are entered as part of the file name when uploading.

## Permissions by Type

Access is not configured per document type. It is governed by:

- **Document permissions** — `view_documents`, `add_documents`,
  `change_documents`, `classify_documents`
- **Classification** on the individual document, filtered by
  `view_confidential_documents` and `view_restricted_documents`

See [Permissions](../users/permissions.md).

!!! warning "There is no per-type access matrix"
    Older instructions gave examples like *"Work Instructions: QA can approve,
    Operators can view"*. Approval rights come from the type's **approval
    template**, and read access from the document's **classification** — never
    from the type itself.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_documenttype` | View document types |
| `add_documenttype` | Create document types |
| `change_documenttype` | Edit document types |
| `delete_documenttype` | Remove document types |

