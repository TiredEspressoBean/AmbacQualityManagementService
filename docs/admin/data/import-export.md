# Data Import & Export

Import and export data in bulk using CSV or Excel files. This feature is available for most data types in the system.

## Overview

The import/export system provides:

- **Export**: Download filtered data as CSV or Excel
- **Import**: Upload data files to create or update records
- **Templates**: Download pre-formatted templates for data entry
- **Excel Features**: Reference sheets, dropdowns, and auto-calculated fields

## Accessing Import/Export

Import and export buttons appear in data table toolbars:

1. Navigate to any data editor (e.g., **Admin** > **Data Management** > **Parts**)
2. The toolbar shows **Import** and **Export** buttons
3. Any active search/filter is applied to exports

## Exporting Data

### Export Formats

| Format | Best For | Features |
|--------|----------|----------|
| **Excel (.xlsx)** | Data review & editing | Reference sheets, dropdowns, formulas |
| **CSV** | Simple data transfer | Universal compatibility, smaller files |

### How to Export

1. Navigate to the data editor
2. Apply any filters or search (optional)
3. Click the **Export** dropdown
4. Select **Export as Excel** or **Export as CSV**
5. File downloads automatically

### Excel Export Features

Excel exports include advanced features for easier data management:

#### Multiple Worksheets

| Sheet | Purpose |
|-------|---------|
| **Instructions** | Field documentation, types, and requirements |
| **Data** | Your exported records |
| **[Reference Sheets]** | Lookup tables for foreign key relationships |

#### Reference Sheets

For fields that link to other records (e.g., Part Type, Order), the export includes reference sheets with valid values:

```
Sheet: PartTypes
| ID                                   | Name                  |
|--------------------------------------|-----------------------|
| 019cc953-b91b-7f31-8ed3-d04d30485eb1 | Common Rail Injector  |
| 019cc953-bded-7750-8cbd-775594e5918e | Injector Body         |
```

#### Dropdown Validation

Columns with constrained values have dropdown lists:

- **Foreign Key fields**: Select from reference sheet values
- **Status fields**: Select from valid statuses (e.g., PENDING, IN_PROGRESS, COMPLETE)
- **Boolean fields**: Select True or False

#### Auto-Calculated ID Fields

When you select a name from a dropdown, the corresponding ID column automatically updates using an Excel formula. These columns are marked with `(auto)` in the header and highlighted in light green.

Example:
- Select "Common Rail Injector" from the **Part Type Name** dropdown
- The **Part Type (auto)** column automatically fills with the UUID

#### Required Fields

Required fields are marked with an asterisk (`*`) in the column header. Empty required fields are highlighted in yellow.

### Filtered Exports

Exports respect your current filters:

1. Use the search box to filter records
2. Apply dropdown filters (status, type, etc.)
3. Export - only matching records are included

This allows you to export subsets like:
- All parts with status "IN_PROGRESS"
- All orders for a specific customer
- Records created in a date range

## Importing Data

### Import Modes

| Mode | Creates New | Updates Existing | Deletes Missing |
|------|-------------|-----------------|-----------------|
| **Create** | Yes | No (error if exists) | No |
| **Update** | No (error if not found) | Yes | No |
| **Upsert** (default) | Yes | Yes | No |

!!! warning "Import Does Not Delete"
    Records that exist in the database but are NOT in your import file are left untouched. Import only creates and/or updates - it never deletes records.

### How to Import

1. Navigate to the data editor
2. Click the **Import** button
3. Download a template (optional but recommended)
4. Drag & drop your file or click to browse
5. Review the column mapping preview
6. Adjust mappings if needed
7. Select import mode
8. Click **Import**

### Import Process

#### Step 1: File Upload

Supported formats:
- CSV (.csv)
- Excel (.xlsx, .xls)

Maximum file size: 10 MB

#### Step 2: Column Mapping

The system automatically maps columns based on:
- Exact name matches (high confidence)
- Similar names (medium confidence)
- Custom mappings you configure

For each column, you can:
- Accept the suggested mapping
- Select a different target field
- Skip the column (won't be imported)

#### Step 3: Preview & Import

Review:
- Total rows to process
- Mapped columns
- Sample data

Then click **Import** to process.

### Import Results

After import, you'll see:

| Metric | Description |
|--------|-------------|
| **Total** | Rows processed |
| **Created** | New records created |
| **Updated** | Existing records updated |
| **Errors** | Rows that failed |

Error details show:
- Row number
- Error message
- Which field caused the issue

### Large Imports

For files with 100+ rows:
- Import runs in the background
- You'll receive a task ID
- Check progress via the status indicator
- You can close the dialog and continue working

## Templates

### Downloading Templates

1. Click **Export** dropdown
2. Select **Excel Template** or **CSV Template**
3. Template downloads with:
   - All importable columns
   - Example data row
   - Reference sheets (Excel only)
   - Dropdown validation (Excel only)

### Template Structure

Templates include:
- Required fields (marked with `*`)
- Optional fields
- Example values showing expected format
- Reference data for foreign keys

### Best Practices for Templates

1. **Start with a template** - Ensures correct column names and format
2. **Keep the header row** - Column names must match exactly
3. **Use dropdowns** - Prevents invalid values
4. **Fill required fields** - Marked with asterisk
5. **Use reference sheets** - Look up valid IDs or use names

## Field Types

### Foreign Key Fields

Fields that reference other records (e.g., `part_type`, `order`):

**Option 1: Use the Name column with dropdown**
- Select from the dropdown
- ID auto-populates (Excel only)

**Option 2: Provide the UUID directly**
- Paste the exact UUID
- Must match an existing record

### Choice/Enum Fields

Fields with predefined values (e.g., `part_status`):

- Use the dropdown to see valid values
- Must match exactly (case-sensitive)
- Common values: `PENDING`, `IN_PROGRESS`, `COMPLETE`, `QUARANTINED`

### Boolean Fields

True/false fields (e.g., `requires_sampling`, `itar_controlled`):

- Use dropdown: `True` or `False`
- Also accepts: `true`, `false`, `1`, `0`, `yes`, `no`

### Date Fields

Dates should be formatted as:
- `YYYY-MM-DD` (recommended)
- `MM/DD/YYYY`
- Excel date values (numeric)

### Text Fields

- Plain text, no special formatting needed
- Watch for leading/trailing spaces
- Special characters are allowed

## Troubleshooting

### Common Import Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Required field missing" | Required column empty | Fill in the required value |
| "Invalid choice" | Value not in allowed list | Use dropdown or check valid values |
| "Related object not found" | FK reference doesn't exist | Check reference sheet for valid IDs |
| "Duplicate key" | Record already exists (create mode) | Use upsert mode or update existing |
| "Record not found" | ID doesn't exist (update mode) | Use upsert mode or check ID |

### Export Issues

| Issue | Solution |
|-------|----------|
| Export is empty | Check your filters - may be too restrictive |
| Missing columns | Not all fields are exported by default |
| Formulas show errors | Reference data may be empty |

## Permissions

| Permission | Allows |
|------------|--------|
| `view_[model]` | Export data |
| `add_[model]` | Import with create mode |
| `change_[model]` | Import with update/upsert mode |

## API Access

For programmatic import/export, see the [API Documentation](../../integrations/api.md).

### Export Endpoint
```
GET /api/{Model}/export/csv/
GET /api/{Model}/export/xlsx/
```

Query parameters:
- `fields`: Comma-separated field names
- `filename`: Custom filename
- `search`: Search filter
- Any filter parameters

### Import Endpoint
```
POST /api/{Model}/import/
```

Form data:
- `file`: CSV or Excel file
- `mode`: `create`, `update`, or `upsert`
- `column_mapping`: JSON mapping of columns

### Template Endpoint
```
GET /api/{Model}/import-template/csv/
GET /api/{Model}/import-template/xlsx/
```

## Best Practices

1. **Always use templates** - Ensures correct format
2. **Export before major imports** - Create a backup
3. **Test with small batches** - Verify mapping before large imports
4. **Use upsert mode** - Most flexible, handles both new and existing
5. **Review errors carefully** - Fix issues before re-importing
6. **Filter exports** - Only export what you need

## Next Steps

- [API Documentation](../../integrations/api.md) - Programmatic access
- [Audit Trail](../../analysis/audit-trail.md) - Track import/export activity
- [User Permissions](../users/permissions.md) - Configure access
