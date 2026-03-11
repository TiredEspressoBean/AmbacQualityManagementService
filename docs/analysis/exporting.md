# Exporting Data

Export data from uqmes for external analysis, reporting, or archival.

## Export Options

### CSV Export
Comma-separated values for spreadsheet analysis:

- Opens in Excel, Google Sheets
- Full data access
- Filterable and sortable
- Supports large datasets

### PDF Export
Formatted reports for sharing:

- Print-ready format
- Includes charts and formatting
- Professional appearance
- Suitable for audits

### Image Export
Charts and visualizations:

- PNG format
- High resolution
- For presentations
- Include in reports

## Exporting from Tables

Most data tables support export:

1. Navigate to the data page (Orders, Parts, etc.)
2. Apply desired filters
3. Click **Export** button
4. Select format (CSV, Excel)
5. Download file

### Excel Export Features

Excel exports include advanced features:

- **Reference sheets** for foreign key lookups
- **Dropdown validation** for constrained fields
- **Auto-calculated ID columns** via formulas
- **Instructions sheet** with field documentation

For detailed information on import/export functionality, including bulk imports and templates, see the [Import & Export Guide](../admin/data/import-export.md).

### Column Selection

Select which columns to export:

1. Click **Select Columns**
2. Check/uncheck columns
3. Reorder if needed
4. Apply selection

### Including Related Data

Some exports can include related data:

- Order export with part list
- Part export with measurements
- NCR export with disposition

## Exporting from Charts

### Single Chart Export

1. Hover over the chart
2. Click the export icon (download or menu)
3. Select format:
   - PNG: Image file
   - CSV: Underlying data
4. Download

### Dashboard Export

!!! note "Planned Feature"
    Dashboard export is planned for a future release.

When available, you will be able to:

1. Click **Export Dashboard**
2. Select format (PDF recommended)
3. All visible charts included
4. Download

## Report Generation

### Available Reports

Currently available report types:

| Report | How to Access |
|--------|---------------|
| **Table Exports** | Click **Export** on any data table (Orders, Parts, Quality Reports, etc.) |
| **Audit Trail** | **Admin > Audit Log** then **Export** |
| **Part Traveler** | API: `GET /api/Parts/{id}/traveler/` |
| **SPC Charts** | Via management command (see [Compliance Reports](../compliance/reports.md)) |

### Running a Table Export

1. Navigate to the data page (e.g., **Quality > Quality Reports**, **Data Management > Orders**)
2. Apply filters as needed
3. Click **Export** button
4. Select format (CSV or Excel)
5. Download file

### Scheduling Reports

!!! note "Planned Feature"
    Report scheduling is planned for a future release. Currently, reports must be generated manually.

When available, you will be able to:

1. Configure report parameters
2. Set frequency (daily, weekly, monthly)
3. Add email recipients
4. Receive reports automatically via email

## Data Exports

### Bulk Data Export

For bulk data extraction, use the export feature on individual data tables:

1. Navigate to the data page in **Data Management** (Orders, Parts, etc.)
2. Apply filters for date range or other criteria
3. Click **Export**
4. Download CSV or Excel file

Each data type has its own export:
- Orders and parts
- Quality reports
- Measurements
- Equipment, companies, etc.

### API Access

For programmatic access:

- REST API available
- Authenticate with API key
- Query specific data
- JSON format responses

See [API Overview](../integrations/api.md) for details.

## Audit Trail Export

Export audit logs for compliance:

1. Navigate to **Admin** > **Audit Log**
2. Filter as needed
3. Click **Export**
4. Download CSV or PDF

Includes:
- All system changes
- User actions
- Timestamps
- Before/after values

## Part Traveler

Complete part history is available via API:

```
GET /api/Parts/{id}/traveler/
```

Returns step-by-step history including timing, operators, equipment, measurements, defects, and attachments.

!!! note "Planned Feature"
    A UI button to generate Part Traveler PDFs is planned. Currently, traveler data is available via the API endpoint above.

When UI export is available:

1. Navigate to part detail
2. Click **Generate Traveler** or **Export History**
3. Select sections to include:
   - Part information
   - Step history
   - Measurements
   - Quality events
   - Signatures
4. Generate PDF

Use for:
- Customer documentation
- Regulatory compliance
- Archive records

## Certificate of Conformance

!!! note "Planned Feature"
    Certificate of Conformance generation is planned for a future release.

When available:

1. Open order
2. Click **Generate CoC**
3. Select parts to include
4. Add required information
5. Generate and sign
6. Export PDF

## Document Packages

!!! note "Planned Feature"
    Document package export is planned for a future release.

When available:

1. Select documents
2. Click **Create Package**
3. Choose format (ZIP or merged PDF)
4. Download

## Export Limitations

### File Size
Large exports may be:
- Split into multiple files
- Generated asynchronously
- Available via download link

### Rate Limits
Frequent exports may be rate limited to prevent system overload.

### Data Retention
Exports may be limited by data retention policies.

## Permissions

| Permission | Allows |
|------------|--------|
| `export_data` | Export data and reports |
| `view_*` | Must have view permission for data type |
| `view_auditlog` | Export audit trails |

## Best Practices

1. **Filter first** - Export only what you need
2. **Use API for automation** - Part traveler and other data available via REST API
3. **Secure downloads** - Exported data is sensitive
4. **Archive properly** - Store exports per retention policy

## Next Steps

- [Dashboard Overview](dashboard.md) - Visualize before export
- [API Overview](../integrations/api.md) - Programmatic access
- [Audit Trail](audit-trail.md) - Compliance exports
