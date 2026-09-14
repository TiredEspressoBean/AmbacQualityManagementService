# Compliance Reports

Generate reports for regulatory compliance and audits.

## Currently Available

### Part Traveler API

Complete part history available via API:

```
GET /api/Parts/{id}/traveler/
```

Returns step-by-step history including:
- Step transitions with timing (started/completed/duration)
- Operator and approver info
- Equipment used
- Measurements taken
- Defects found and dispositions
- Materials consumed
- Attachments

### Data Export

CSV and Excel export is available on most data tables. The format is part of
the URL path, not a query parameter:

```
GET /api/{Model}/export/csv/
GET /api/{Model}/export/xlsx/
```

Query parameters:
- `fields`: Comma-separated field names to include
- `filename`: Custom filename
- `include_references`: Include FK reference sheets (`xlsx` only, default true)

CSV is plain data; the Excel export adds reference sheets, validation, and
formatting. Exports respect all applied filters, search, and ordering.

See [Import & Export](../admin/data/import-export.md) for the full reference.

### PDF Reports

uqmes generates PDF reports server-side from a registry of report types. In the
UI, look for a **report button** on the relevant record or dashboard — it
generates the PDF and either downloads it or emails it to you.

| Report type | Title | Typically generated from |
|-------------|-------|--------------------------|
| `work_order_traveler` | Work Order Traveler | Work order detail |
| `ncr_report` | Non-Conformance Report | Quality report / disposition |
| `capa_report` | CAPA Report | CAPA detail |
| `scar` | Supplier Corrective Action Request | Supplier quality |
| `deviation_request` | Deviation Request | Quality report / disposition |
| `spc` | SPC Report | SPC page |
| `bom_report` | Bill of Materials | Part type |
| `calibration_certificate` | Calibration Certificate | Calibration record |
| `calibration_due` | Calibration Due Report | Calibration dashboard |
| `training_record` | Training Record | User detail |
| `checking_aids` | Checking Aids | Equipment |
| `dispatch_list` | Dispatch List | Work order control |
| `pick_list` | Material Requisition | Work order |
| `pick_sheet` | Pick Sheet | Work order |
| `staging_list` | Kit Sheet | Staging list |
| `requirements` | Sourcing & Production Requirements | Requirements page |
| `labor_hours` | Operator Hours | Operator hours page |
| `part_id_label` | Part ID Label / WIP Tag | Part |
| `part_id_label_batch` | Part ID Labels (Batch) | Part list |

Reports are also available over the API:

```
GET  /api/reports/types/              # enumerate available report types
POST /api/reports/generate/           # generate and email
POST /api/reports/download/           # generate and download
GET  /api/reports/history/            # previously generated reports
```

Generating reports requires the export permission; see
[Exporting Data](../analysis/exporting.md).

---

!!! warning "Planned Features"
    The features below are planned but not yet implemented.

## Planned: Report Categories

### Quality Records
- Quality report (NCR) history
- Disposition records
- CAPA records
- Measurement data

### Traceability
- Lot traceability
- Material traceability
- Equipment usage

### Document Control
- Document inventory
- Revision history
- Approval records
- Distribution records

### Access & Audit
- User activity
- Permission changes
- System audit log
- Signature records

## Planned: Standard Reports

### Certificate of Conformance
Quality certification for shipment:
- Order/part information
- Specification compliance
- Inspection results
- Authorized signature

### Audit Trail Report
System activity for period:
- All changes
- User actions
- Timestamps
- Change details

!!! note
    A per-CAPA **CAPA Report** PDF has shipped (see the table above). What
    remains planned is a rolled-up *CAPA summary* across CAPAs — closure rate,
    effectiveness metrics, and action-completion rates.

## Planned: Bulk Report Generation

Selecting many records and generating one combined report is not available.
The one exception is **Part ID Labels (Batch)**, which prints labels for a
batch of parts.

## Planned: Report Scheduling

Automate recurring reports:
- Daily, weekly, monthly frequency
- Email delivery to recipients
- Automatic generation

## Planned: Custom Reports

Build reports for specific needs:
- Select data source
- Choose fields
- Apply filters
- Set grouping
- Save template

## Planned: Regulatory Templates

### FDA Inspection
- Device history records
- CAPA summary
- Complaint records
- Audit trail

### ISO Audit
- Document control records
- Training records
- Calibration records
- NCR/CAPA summary

### AS9100 Audit
- First article reports
- Process records
- Nonconformance history
- Supplier quality

### IATF Audit
- Control plan records
- SPC data
- PPAP documentation
- Problem solving (8D)

## Next Steps

- [Audit Trails](audit-trails.md) - Activity logging
- [Exporting Data](../analysis/exporting.md) - Export options
