# Compliance Reports

Generate reports for regulatory compliance and audits.

## Report Categories

### Quality Records
- Quality report (NCR) history
- Disposition records
- CAPA records
- Measurement data

### Traceability
- Part history (traveler)
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

## Standard Reports

### Part Traveler
Complete part history:
- Part identification
- Step transitions
- All measurements
- Quality events
- Signatures
- Associated documents

Generate from part detail or bulk for order.

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

## Generating Reports

### From Record
1. Open record (part, order, CAPA)
2. Click **Generate Report** or **Export**
3. Select report type
4. Configure options
5. Generate PDF/CSV

### From Reports Section
1. Navigate to **Reports** (if available)
2. Select report type
3. Configure parameters
4. Generate

### Bulk Generation
For multiple records:
1. Select records
2. Click **Bulk Export**
3. Choose format
4. Download

## Report Formats

### PDF
- Formatted for printing
- Includes headers/footers
- Signature lines
- Company branding

### CSV
- Data export
- For further analysis
- Spreadsheet compatible
- All raw data

### Excel
- Formatted spreadsheet
- Multiple sheets
- Charts included
- Analysis ready

## Scheduling Reports

Automate recurring reports:

1. Configure report
2. Click **Schedule**
3. Set frequency:
   - Daily
   - Weekly
   - Monthly
4. Add recipients
5. Save

Reports email automatically.

## Custom Reports

Build reports for specific needs:

1. Select data source
2. Choose fields
3. Apply filters
4. Set grouping
5. Add calculations
6. Save template

## Regulatory Report Templates

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

## Data Retention

Reports are retained per policy:
- Generated reports archived
- Available for future reference
- Retention per document type

## Permissions

| Permission | Allows |
|------------|--------|
| `generate_reports` | Create reports |
| `export_data` | Export data |
| `view_compliance_reports` | Access compliance reports |

## Best Practices

1. **Prepare in advance** - Have reports ready before audits
2. **Use templates** - Consistent formatting
3. **Schedule recurring** - Automate routine reports
4. **Verify data** - Spot check accuracy
5. **Secure distribution** - Control who receives

## Next Steps

- [Audit Trails](audit-trails.md) - Activity logging
- [Part History](../workflows/tracking/part-history.md) - Traceability
- [Exporting Data](../analysis/exporting.md) - Export options
