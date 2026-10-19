# Order Documents

Attach and manage documents related to orders, including purchase orders, drawings, specifications, and certificates.

## Document Types for Orders

Common documents attached to orders:

| Document Type | Purpose |
|---------------|---------|
| **Purchase Order** | Customer's official order document |
| **Drawing** | Part drawings and specifications |
| **Work Instruction** | Manufacturing procedures |
| **Inspection Report** | Quality inspection results |
| **Certificate of Conformance** | Quality certification |
| **Shipping Documents** | Packing lists, bills of lading |
| **Test Reports** | Lab or functional test results |

## Attaching Documents

### Upload a new document

Documents are uploaded once, centrally, then attached to the records they
relate to:

1. Go to **Documents** and click **Upload Document**
2. Fill in the document details and upload the file
3. Attach it to the order (below)

See [Uploading Documents](../documents/uploading.md).

### Attach an existing document

From the document's own page:

1. Open the document
2. **Edit** it
3. Use **Link To (Optional)** — choose the entity type, then search for the record
4. Save

!!! note "There is no Attach button on a document"
    Linking is part of the edit form, not a separate action.

A document can be attached to several records — its detail page lists what it
is **Linked To** and what it is **Also Linked To**.

!!! note "One attach action, not two"
    There is no separate "link existing" versus "upload new" flow on the order.
    Upload centrally, then attach.

## Viewing Documents

### On the order page

The order page you reach from the **Tracker** has a **Documents** card listing
what is attached to **the order itself**: each file's name and upload date, with
a count in the header.

Clicking one **opens the file** in a new tab. It does not open the document's
own page, so revision, status and approval are not shown here — for those, open
the document from **Documents**.

!!! note "Company and customer documents are on the other order view"
    Documents linked to the order's **company** or **customer** — a quality
    agreement, an NDA — are not on that card. They appear on the generic record
    view of the order (`/details/Orders/<id>`, reached by following an order
    link from a part or work order), under **Company Documents** and **Customer
    Documents**.

## Document Permissions

| Permission | Allows |
|------------|--------|
| `view_documents` | See documents — subject to their classification |
| `add_documents` | Upload |
| `change_documents` | Edit, including what a document is linked to |
| `classify_documents` | Change a document's classification |

!!! info "Controlled Documents"
    Some document types require approval before use. These show as "Draft" until approved. See [Document Approval](../documents/approval.md).

## Customer Document Access

Control what customers can see:

### Document Visibility Settings

Visibility is the document's **classification level**, set on upload or edit.
There are five, not three:

| Level | Who can see it |
|-------|----------------|
| **Public** | Everyone, including customers |
| **Internal** | All staff |
| **Confidential** | All staff |
| **Restricted** | All staff |
| **Secret** | Tenant Admin and Document Controller only |

!!! warning "Confidential does not restrict a document internally"
    Every internal role — Operator and the dock included — can read
    **Confidential** and **Restricted**. Those tiers separate staff from
    **customers and auditors**, not managers from the floor.

    If you need a document kept from most of the shop, **Secret** is the only
    tier that does it. See
    [Classification Levels](../documents/library.md#classification-levels).

### Common Customer Documents

Customers typically access:

- Certificates of Conformance
- Test reports
- Shipping documents
- Approved drawings

Typically hidden from customers:

- Internal work instructions
- Quality issues and NCRs
- Internal memos

## Required Documents

Nothing checks that an order has particular documents attached. There is no
required-document list per order, and a missing document blocks nothing.

The requirements that *are* enforced live elsewhere:

| Requirement | Where it is set | What it does |
|-------------|-----------------|--------------|
| **Requires CoC on shipment** | The customer's company record | A Certificate of Conformance is printed with every shipment to them |
| **Requires CoC** / **Requires heat number** | The part type | A *received lot* is held until its certificate or heat number is in |

## Searching Documents

Find documents across orders:

1. Go to **Documents** in the sidebar
2. Use filters:
   - Document type
   - Approval status
   - Is-image
   - Needs my approval
3. Click a result to open the document

!!! note "No date or author filter"
    There is no date-range or created-by filter on the document list. To find
    documents for one order, open the order and read its linked documents
    rather than filtering the library.

## Version History

Revisions belong to the document, not to the order. See
[Revisions](../documents/revisions.md) for how a new revision supersedes the
one before and what the history shows.

## Next Steps

- [Document Library](../documents/library.md) - Full document management
- [Document Approval](../documents/approval.md) - Approval workflows
- [Order Status](order-status.md) - Overall order tracking
