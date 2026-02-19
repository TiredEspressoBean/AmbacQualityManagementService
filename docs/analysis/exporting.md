# Exporting Data

Export data from Ambac Tracker for external analysis, reporting, or archival.

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
4. Select format (CSV, PDF)
5. Choose columns to include
6. Download file

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

Export entire dashboard:

1. Click **Export Dashboard**
2. Select format (PDF recommended)
3. All visible charts included
4. Download

## Report Generation

### Standard Reports

Pre-built reports available:

| Report | Contents |
|--------|----------|
| **Order Status** | All orders with progress |
| **Quality Summary** | NCRs, dispositions, CAPAs |
| **Production Report** | Output, throughput, efficiency |
| **Audit Trail** | System activity log |
| **Part Traveler** | Complete part history |

### Running a Report

1. Navigate to **Reports** or find in relevant section
2. Select report type
3. Configure parameters:
   - Date range
   - Filters
   - Grouping
4. Click **Generate**
5. View or download

### Scheduling Reports

Set up recurring reports:

1. Configure report as desired
2. Click **Schedule**
3. Set frequency (daily, weekly, monthly)
4. Add email recipients
5. Save schedule

Reports are emailed as attachments.

## Data Exports

### Full Data Export

For bulk data extraction:

1. Navigate to **Data Management**
2. Click **Export Data**
3. Select data types to include
4. Choose date range
5. Generate export

Includes:
- Orders and parts
- Quality reports
- Measurements
- Documents metadata

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

Generate complete part documentation:

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

Generate CoC documents:

1. Open order
2. Click **Generate CoC**
3. Select parts to include
4. Add required information
5. Generate and sign
6. Export PDF

## Document Packages

Export multiple documents together:

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
2. **Select columns** - Include relevant fields
3. **Use schedules** - Automate recurring reports
4. **Secure downloads** - Exported data is sensitive
5. **Archive properly** - Store exports per retention policy

## Next Steps

- [Dashboard Overview](dashboard.md) - Visualize before export
- [API Overview](../integrations/api.md) - Programmatic access
- [Audit Trail](audit-trail.md) - Compliance exports
