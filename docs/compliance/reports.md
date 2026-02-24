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

CSV and Excel export available on most data tables via the `/export/` endpoint:

```
GET /api/Parts/export/?format=xlsx
GET /api/Orders/export/?format=csv
```

Query parameters:
- `format`: `csv` or `xlsx` (default: xlsx)
- `fields`: Comma-separated field names to include
- `filename`: Custom filename

Exports respect all applied filters, search, and ordering.

### SPC Reports

SPC chart reports can be generated via management command:

```bash
python manage.py generate_pdf --type spc --params '{"process_id": 1, "step_id": 2, "measurement_id": 3}'
```

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

### CAPA Summary
CAPA status and history:
- Open CAPAs
- Closure rate
- Effectiveness metrics
- Action completion

## Planned: UI Report Generation

### From Record
1. Open record (part, order, CAPA)
2. Click **Generate Report** or **Export**
3. Select report type
4. Configure options
5. Generate PDF/CSV

### Bulk Generation
For multiple records:
1. Select records
2. Click **Bulk Export**
3. Choose format
4. Download

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
