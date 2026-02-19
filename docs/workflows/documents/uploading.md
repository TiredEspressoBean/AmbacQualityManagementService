# Uploading Documents

Add new documents to the Ambac Tracker document library.

## Supported File Types

Common supported formats:

| Category | Extensions |
|----------|------------|
| **Documents** | PDF, DOC, DOCX, TXT, RTF |
| **Spreadsheets** | XLS, XLSX, CSV |
| **Images** | PNG, JPG, JPEG, GIF, BMP, TIFF |
| **Drawings** | DWG, DXF, STEP, IGES |
| **Presentations** | PPT, PPTX |
| **Archives** | ZIP |

PDF is recommended for controlled documents (non-editable, consistent display).

## File Size Limits

- **Maximum file size**: 100 MB (configurable)
- **Recommended**: Under 25 MB for best performance

For large files, consider:
- Compressing images
- Splitting into multiple documents
- Using external links

## Uploading a New Document

### From Document Library

1. Navigate to **Documents**
2. Click **+ Upload** or **+ New Document**
3. Drag and drop file, or click to browse
4. Fill in metadata
5. Click **Upload**

### From Related Record

1. Open the order, part, or other record
2. Go to **Documents** section
3. Click **Upload**
4. File automatically links to the record

## Document Metadata

### Required Fields

| Field | Description |
|-------|-------------|
| **Title** | Display name |
| **Document Type** | Category |

### Optional Fields

| Field | Description |
|-------|-------------|
| **Document Number** | Your numbering scheme |
| **Revision** | Version identifier |
| **Description** | Summary of contents |
| **Effective Date** | When document becomes active |
| **Expiration Date** | When document expires |
| **Author** | Document creator |
| **Keywords** | Search terms |

### Visibility Settings

| Setting | Who Can See |
|---------|-------------|
| **Public** | All users, including customers |
| **Internal** | Staff only |
| **Confidential** | Users with confidential permission |
| **Restricted** | Specific users/groups only |

## Bulk Upload

Upload multiple documents at once:

1. Click **Bulk Upload**
2. Drag and drop multiple files
3. Files appear in upload queue
4. Set metadata for each (or apply to all)
5. Click **Upload All**

### Applying Metadata to All

1. Fill in the first document
2. Click **Apply to All**
3. Shared fields copy to other uploads
4. Adjust individual documents as needed

## Uploading Revisions

To upload a new version of an existing document:

1. Open the existing document
2. Click **New Revision** (not new upload)
3. Upload the new file
4. Enter revision notes
5. Submit for approval (if controlled)

See [Document Revisions](revisions.md) for details.

## Document Numbering

### Automatic Numbering

System-generated numbers based on:
- Document type prefix
- Sequential number
- Optional date code

Example: `WI-2026-00001` (Work Instruction #1 of 2026)

### Manual Numbering

Enter your own document number:
- Follow your organization's scheme
- Must be unique
- Can include revision in number

## Linking During Upload

Link document to records during upload:

1. In the upload form
2. Find **Link to** section
3. Select record type (Order, Part Type, etc.)
4. Search and select records
5. Document uploads with links established

## Upload from External Sources

### URL Import (if enabled)

1. Click **Import from URL**
2. Enter document URL
3. System fetches and imports

### Integration Import

If integrations are configured:
- Import from cloud storage
- Import from CAD systems
- Import from ERP

## Post-Upload Actions

After upload, you can:

- **Submit for Approval** - Start approval workflow
- **Link to Records** - Connect to orders, parts
- **Share** - Notify specific users
- **Edit Metadata** - Update fields

## Upload Validation

The system validates:

- File type allowed
- File size within limits
- Required metadata provided
- Document number unique

Validation errors show before upload completes.

## Permissions

| Permission | Allows |
|------------|--------|
| `add_document` | Upload new documents |
| `add_documenttype` | Create new document types |

## Best Practices

1. **PDF for controlled docs** - Non-editable format
2. **Clear naming** - Descriptive, consistent
3. **Complete metadata** - Improve searchability
4. **Link appropriately** - Connect to related records
5. **Right visibility** - Consider audience

## Next Steps

- [Document Revisions](revisions.md) - Version control
- [Document Approval](approval.md) - Approval workflows
- [Document Library](library.md) - Managing documents
