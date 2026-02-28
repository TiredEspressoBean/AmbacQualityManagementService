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

- **Maximum file size**: 10 MB
- **Recommended**: Under 5 MB for best performance

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
| **Revision** | Version identifier |
| **Description** | Summary of contents |
| **Effective Date** | When document becomes active |
| **Expiration Date** | When document expires |
| **Keywords** | Search terms |

!!! note "Document Numbering"
    Document numbers may be auto-generated based on document type settings. Check with your administrator for your organization's numbering scheme.

### Visibility Settings

| Setting | Who Can See |
|---------|-------------|
| **Public** | All users, including customers |
| **Internal** | Staff only |
| **Confidential** | Users with confidential permission |
| **Restricted** | Specific users/groups only |

## Uploading Revisions

To upload a new version of an existing document:

1. Open the existing document
2. Click **New Revision** (not new upload)
3. Upload the new file
4. Enter revision notes
5. Submit for approval (if controlled)

See [Document Revisions](revisions.md) for details.

## Linking During Upload

Link document to records during upload:

1. In the upload form
2. Find **Link to** section
3. Select record type (Order, Part Type, etc.)
4. Search and select records
5. Document uploads with links established

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
