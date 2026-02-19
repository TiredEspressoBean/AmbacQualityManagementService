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

### Upload New Document

1. Open the order
2. Go to the **Documents** tab or section
3. Click **+ Add Document** or **Upload**
4. Select the file from your computer
5. Fill in document metadata:

| Field | Description |
|-------|-------------|
| **Document Type** | Category (Drawing, Spec, etc.) |
| **Title** | Descriptive name |
| **Revision** | Version identifier |
| **Notes** | Optional description |

6. Click **Upload**

### Link Existing Document

If the document already exists in the system:

1. Click **Link Document**
2. Search for the document
3. Select it from the results
4. The document is now linked to this order

## Viewing Documents

### Document List

The order's Documents tab shows:

- Document title and type
- Current revision
- Upload date
- Status (Draft, Approved, etc.)

### Document Preview

Click a document to:

- View the file (PDFs display inline)
- Download the file
- See version history
- View approval status

## Document Permissions

| Action | Description |
|--------|-------------|
| **View** | See document list and contents |
| **Download** | Download files locally |
| **Upload** | Add new documents |
| **Delete** | Remove document links |

!!! info "Controlled Documents"
    Some document types require approval before use. These show as "Draft" until approved. See [Document Approval](../documents/approval.md).

## Customer Document Access

Control what customers can see:

### Document Visibility Settings

| Setting | Customer Can See |
|---------|------------------|
| **Public** | Visible to customer |
| **Internal** | Hidden from customer |
| **Confidential** | Hidden, restricted internally |

Set visibility when uploading or editing documents.

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

Your organization may require certain documents per order:

- CoC before shipping
- Final inspection report
- Customer-specific requirements

Missing required documents may:

- Block order completion
- Trigger reminders
- Show warnings on the order

## Document Packages

Create document packages for shipping:

1. Open the order
2. Click **Create Document Package** or **Export Documents**
3. Select documents to include
4. Generate a combined PDF or ZIP file
5. Download or email to customer

## Searching Documents

Find documents across orders:

1. Go to **Documents** in the main navigation
2. Use filters:
   - Document type
   - Date range
   - Associated order
   - Approval status
3. Click a result to open the document

## Version History

Documents maintain revision history:

1. Open the document
2. View the **Versions** or **History** tab
3. See all revisions with:
   - Version number
   - Upload date
   - Who uploaded it
   - Change notes

Download or view any previous version.

## Next Steps

- [Document Library](../documents/library.md) - Full document management
- [Document Approval](../documents/approval.md) - Approval workflows
- [Order Status](order-status.md) - Overall order tracking
