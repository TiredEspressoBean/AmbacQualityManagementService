# Exporting Data

Export data from uqmes for external analysis, reporting, or archival.

## Export Options

### CSV Export
Comma-separated values for spreadsheet analysis:

- Opens in Excel, Google Sheets
- The rows the table shows, with its filters, search and sorting
- Up to **50,000 rows** per export

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
4. Select **Export as Excel** or **Export as CSV**
5. Download file

### Excel Export Features

Excel exports include advanced features:

- **Reference sheets** for foreign key lookups
- **Dropdown validation** for constrained fields
- **Required fields** marked with `*`, and empty required cells highlighted
- **Instructions sheet** with field documentation

Every cell holds a value, not a formula.

For detailed information on import/export functionality, including bulk imports and templates, see the [Import & Export Guide](../admin/data/import-export.md).

### Column Selection

!!! note "No column picker in the UI"
    The export menu offers **Export as Excel** and **Export as CSV**; it does
    not offer column selection. Exports include the model's standard export
    fields and respect the filters, search, and sorting applied to the table.

    To restrict columns, call the export endpoint directly with the `fields`
    query parameter — see [Import & Export](../admin/data/import-export.md).

### Related Data

An export is one row per record of the table you are on; related records are
not nested into it. A link to another record comes out as that record's ID,
with a readable name in the column beside it where there is one, and a list of
links as one cell
separated by `;`. To get, say, an order's parts, export the parts table
filtered to that order.

## Exporting from Charts

!!! note "No chart or dashboard export"
    There is no per-chart export control — no hover icon, no PNG and no
    chart-level CSV — and no export of a dashboard.

    What does exist: the **Defect Analysis** page's own **Export**, which
    downloads the records it lists as CSV, following its period and filters,
    and the **SPC Report** PDF on the SPC page.

## Report Generation

### Available Reports

| Report | How to Access |
|--------|---------------|
| **Table Exports** | Click **Export** on any data table (Orders, Parts, Quality Reports, etc.) |
| **Part Traveler** | The **Traveler** button on the part detail page — *"this serial's as-built traveler: its work order's routing, filled with who did each step, what was measured, the lots that went in"*. Also available at `GET /api/Parts/{id}/traveler/` |
| **SPC Report** | The **SPC Report** button on the SPC page |

A PDF report button offers **Download PDF** or **Email me**, which builds the
PDF in the background and emails it to you.

### Running a Table Export

1. Navigate to the data page (e.g., **Quality > Quality Reports**, **Data Management > Orders**)
2. Apply filters as needed
3. Click **Export** button
4. Select format (CSV or Excel)
5. Download file

### Scheduling Reports

Exports and PDF reports are run by hand; none of them can be scheduled. The
one scheduled email is the **Customer active orders** summary, set up under
**Settings** > **Notifications** > **Schedules** with a weekly or monthly
cadence. See [Notification Rules](../admin/setup/notification-rules.md).

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

The **Admin** > **Audit Log** page has no **Export**: the log is viewed and
filtered there. To take it out, use the REST API endpoint `GET /api/auditlog/`
with filters.

Audit log data includes:

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

### Work Order Traveler

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

!!! note "A unit returned unrepaired gets a note, not a CoC"
    Returning a remanufacturing unit (**Return** on the work order's cores) is a
    shipment like any other, so its packing list prints — and its CoC, if the
    customer wants one. A unit going back **unrepaired** gets no CoC, since
    nothing was done to it to certify; it gets a **Returned as received** note
    instead. See [Shipping](../roles/shipping.md).

## Document Packages

There is no document package export — no bundling of several documents into a
ZIP or a merged PDF. Download documents one at a time.

## Export Limitations

!!! warning "A table export holds the tab open — do not navigate away"
    Table exports download straight to your browser. **There is no background
    job and no emailed download link** for them, so the request stays open
    until the file is built and navigating away cancels it. (A PDF report can
    be emailed instead — **Email me**.)

    An export of more than **50,000 rows** is refused: filter the list first.
    For a large export, narrow the date range or filter rather than waiting it
    out. See [Export taking too long](../troubleshooting/common-issues.md).

## Permissions

| Permission | Allows |
|------------|--------|
| `view_*` | A table's export needs only the view permission for that table |
| `export_data` | Generate PDF reports |
| `view_auditlog` | View the audit trail |

## Next Steps

- [Dashboard Overview](dashboard.md) - Visualize before export
- [API Overview](../integrations/api.md) - Programmatic access
- [Audit Trail](audit-trail.md) - View compliance history
