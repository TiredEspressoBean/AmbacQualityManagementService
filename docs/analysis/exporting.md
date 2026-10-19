# Exporting Data

Export data from uqmes for external analysis, reporting, or archival.

## Export Options

### CSV Export
Comma-separated values for spreadsheet analysis:

- Opens in Excel, Google Sheets
- Full data access
- Filterable and sortable
- Supports large datasets

### Excel Export
The same data as a workbook, with reference sheets for lookups.

!!! note "PDF is for *reports*, not for exporting a view"
    You cannot export an arbitrary list, chart or dashboard as PDF or PNG —
    those export as CSV or Excel.

    PDF is how **documents** come out, and there are a lot of them. They are
    reached from the record they describe rather than from a general export
    menu, which is why they are easy to miss:

    | Where you are | What prints |
    |---------------|-------------|
    | A work order | **Traveler** — the as-built routing, filled in |
    | A part | That serial's own traveler |
    | A shipment | **Packing list** and **Certificate of Conformance** |
    | A rejected lot | **RTV sheet**, to travel with the goods |
    | A received lot | Receiving inspection record; lot and part labels |
    | The schedule | **Dispatch list**; pick and staging lists |
    | A calibration | Certificate, and the calibrations-due list |
    | A quality record | NCR, CAPA report, SCAR, deviation request |
    | The SPC page | **SPC Report** |

    Plus requirements, lot trace, BOM, labour hours and training records. If you
    are looking for a printable version of something, check the record's own
    page before concluding there isn't one.

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

!!! note "No column picker in the UI"
    The export menu offers **Export as Excel** and **Export as CSV**; it does
    not offer column selection. Exports include the model's standard export
    fields and respect the filters, search, and sorting applied to the table.

    To restrict columns, call the export endpoint directly with the `fields`
    query parameter — see [Import & Export](../admin/data/import-export.md).

### Including Related Data

Some exports can include related data:

- Order export with part list
- Part export with measurements
- NCR export with disposition

## Exporting from Charts

!!! note "Planned Feature"
    There is no per-chart export control — no hover icon, no PNG and no
    chart-level CSV. Image and PDF export from analytics charts is planned.

    What does exist: the **Defect Analysis** page's own **Export**, which
    downloads the current view as CSV respecting the period and part type you
    have selected, and the **SPC Report** PDF on the SPC page.

### Dashboard Export

!!! note "Planned Feature"
    Dashboard export is planned for a future release.

## Report Generation

### Available Reports

Currently available report types:

| Report | How to Access |
|--------|---------------|
| **Table Exports** | Click **Export** on any data table (Orders, Parts, Quality Reports, etc.) |
| **Part Traveler** | The **Traveler** button on the part detail page — *"this serial's as-built traveler: its work order's routing, filled with who did each step, what was measured, the lots that went in"*. Also available at `GET /api/Parts/{id}/traveler/` |
| **SPC Report** | The **SPC Report** button on the SPC page |
| **Audit Trail** | Planned - see [Audit Trail Export](#audit-trail-export) |

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

!!! note "Planned Feature"
    Audit Trail UI export is planned for a future release. Currently, audit logs can be viewed and filtered in the UI, or accessed via the API.

When available:

1. Navigate to **Admin** > **Audit Log**
2. Filter as needed
3. Click **Export**
4. Download CSV or PDF

Audit log data includes:

- All system changes
- User actions
- Timestamps
- Before/after values

**Current access:** Use the REST API endpoint `GET /api/auditlog/` with filters to retrieve audit data programmatically.

## Part Traveler

Complete part history is available via API:

```
GET /api/Parts/{id}/traveler/
```

Returns step-by-step history including timing, operators, equipment, measurements, defects, and attachments.

### Work Order Traveler (available)

A **Traveler** button on the work order detail page generates a Work Order
Traveler PDF, downloaded or emailed to you.

A **per-serial** traveler is on the part itself: open the part and use
**Traveler** in its header. It renders that serial's as-built record — its work
order's routing, who did each step, what was measured, and the lots that went
in.

Use for:
- Customer documentation
- Regulatory compliance
- Archive records

## Certificate of Conformance

**The CoC exists and prints from the shipment**, not from the order — it
certifies what actually went, so it is produced once there is a shipment to
certify.

1. Open the shipment (**Supply** > **Shipping** > Shipped, or from the order's
   shipping card)
2. Click **CoC**

It prints automatically alongside the packing list for any customer whose
company record has **CoC with every shipment** set, and the shipping board
badges those customers so you know before you pack.

!!! warning "A returned reman core gets no CoC"
    Returning a unit through Remanufacturing does **not** create a shipment, and
    the certificate is built from one — so a repair-and-return unit currently
    goes back without a packing list or a CoC. See [Shipping](../roles/shipping.md).

## Document Packages

!!! note "Planned Feature"
    Document package export is planned for a future release.

When available:

1. Select documents
2. Click **Create Package**
3. Choose format (ZIP or merged PDF)
4. Download

## Export Limitations

!!! warning "An export holds the tab open — do not navigate away"
    Exports download straight to your browser. **There is no background job,
    no asynchronous generation and no emailed download link**, so the request
    stays open until the file is built and navigating away cancels it.

    For a large export, narrow the date range or filter first rather than
    waiting it out. See [Export taking too
    long](../troubleshooting/common-issues.md).

### Data Retention
Exports may be limited by data retention policies.

## Permissions

| Permission | Allows |
|------------|--------|
| `export_data` | Export data and reports |
| `view_*` | Must have view permission for data type |
| `view_auditlog` | View audit trail (export planned) |

## Next Steps

- [Dashboard Overview](dashboard.md) - Visualize before export
- [API Overview](../integrations/api.md) - Programmatic access
- [Audit Trail](audit-trail.md) - View compliance history
