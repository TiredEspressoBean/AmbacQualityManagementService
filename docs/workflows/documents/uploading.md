# Uploading Documents

Add new documents to the uqmes document library.

## Supported File Types

The file extension must be on this list. Anything else is refused on upload.

| Category | Extensions |
|----------|------------|
| **Documents** | PDF, DOC, DOCX, TXT |
| **Spreadsheets** | XLS, XLSX, CSV |
| **Presentations** | PPT, PPTX |
| **Images** | PNG, JPG, JPEG, GIF, WEBP, SVG |
| **3D / CAD** | GLB, GLTF, STEP, STP, STL |
| **Data** | JSON, XML |

PDF is recommended for controlled documents (non-editable, consistent display).

!!! warning "Common formats that are not accepted"
    RTF, BMP, TIFF, DWG, DXF, IGES and ZIP are **refused**. Native CAD drawings
    need exporting — STEP is accepted, IGES is not. Convert anything else to PDF
    before uploading.

## File Size Limits

- **Maximum file size**: 10 MB through the upload and revision forms. A file
  uploaded under a record's **Attach Document** may be up to 100 MB.
- **Recommended**: Under 5 MB for best performance

For large files, consider:
- Compressing images
- Splitting into multiple documents
- Using external links

!!! note "The limit is fixed"
    The limits are built into the application. They are not settings, and your
    administrator cannot raise or lower them.

## Uploading a New Document

### From Document Library

1. Navigate to **Documents**
2. Click **Upload Document**
3. Drag and drop file, or click to browse
4. Fill in metadata
5. Click **Upload Document**

### From Related Record

The edit forms for an order, work order, step, process, part type or part, and
a CAPA's **Documents** tab, carry an uploader titled **Attach Document**:

1. Open the record's edit form (or the CAPA's **Documents** tab)
2. Under **Attach Document**, choose the file and classification
3. Click **Upload**
4. The file is attached to that record

## Document Metadata

### Required Fields

| Field | Description |
|-------|-------------|
| **File** | The file itself |
| **Classification Level** | Who may see the document |

There is no title field. The document's name is taken from the file you upload,
so name the file the way you want it to read in the library.

### Optional Fields

| Field | Description |
|-------|-------------|
| **Document Type** | Category — also decides whether approval is required |
| **Link To** | Records to attach the document to |
| **AI Readable** | Whether the document may be used by AI features |

!!! note "Dates are not yours to set"
    Effective date, review date, obsolete date and retention date are all
    read-only. Effective, review and retention dates are set when the document
    is released, from the document type's review and retention periods; the
    obsolete date is set when it is marked obsolete.

### Classification Levels

| Level | Who can see it |
|-------|----------------|
| **Public** | Everyone, including customers |
| **Internal** | All staff |
| **Confidential** | All staff |
| **Restricted** | All staff |
| **Secret** | Tenant Admin and Document Controller only |

Classification is a tier, not a per-document access list — you cannot name
individual users or groups on a document. Confidential and Restricted separate
staff from customers and auditors; every internal role holds both. **Secret** is
the only tier that keeps a document from most of the shop. See [Document
Library](library.md) for the detail.

## Uploading Revisions

To upload a new version of an existing document:

1. Open the existing document
2. Click **Create Revision** (not a new upload)
3. Upload the new file
4. Enter revision notes
5. Submit for approval (if controlled)

See [Document Revisions](revisions.md) for details.

## Linking During Upload

Link document to records during upload:

1. In the upload form
2. Find **Link to** section
3. Select record type — Order, Work Order, Part, Process, Step, Company,
   Quality Report, Disposition, CAPA or 3D Model. Part Type is not on the
   list; link a part type from the document's **Also Linked To** > **Attach**.
   Quality Report is listed, but its record search comes up empty
4. Search and select the record
5. Document uploads with links established

## Post-Upload Actions

After upload, you can:

- **Submit for Approval** - Start approval workflow
- **Link to Records** - Connect to orders, parts
- **Edit Metadata** - Update fields

## Upload Validation

The system validates:

- The file extension is on the allowed list
- The file is within the size limit (above)

Validation errors show before upload completes.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_documents` | Upload new documents |
| `add_documenttype` | Create new document types |

## Next Steps

- [Document Revisions](revisions.md) - Version control
- [Document Approval](approval.md) - Approval workflows
- [Document Library](library.md) - Managing documents
