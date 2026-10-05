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
| `receiving_inspection_record` | Receiving Inspection Record | Material lot / receiving inspection |
| `rtv_sheet` | Return to Vendor (RTV) Sheet | Rejected material lot |

#### Return to Vendor (RTV) Sheet

The paperwork that travels with material going back. Printed from the **Ship
back** dialog, or **RTV sheet (PDF)** in the Materials row menu — for lots
waiting to go back and ones already returned.

It carries the return addressing (to the supplier, from you, issued by, date);
the material — item and part number, quantity returned, **your lot and theirs**,
heat, PO/line, received date, disposition number; the reason for return, with a
**SCAR callout** where one exists; and **shipped-by and received-by signature
lines**.

!!! note "No prices, by design"
    The sheet says what is going back and why. **Credit is settled in the ERP** —
    uqmes does not price the return, raise a credit note or track what you are
    owed.

    What it gives the system that does own that is an unambiguous statement of
    which material, from which lot and heat, against which PO line, and on whose
    decision.

#### Receiving Inspection Record

The **evidence of release** for incoming material — ISO 9001 §8.6. Open it from
**Record** in the receiving inspection page header, or **Inspection record
(PDF)** in the Materials row **⋯** menu.

It gathers, for one lot:

| Section | Carries |
|---------|---------|
| **As received** | Item, supplier and supplier lot, heat number, bought from, quantity and how it was counted, ERP PO / line, who received it, whether a CoC is on file |
| **Plan and sampling** | Sample size, Ac/Re or k, defectives found, inspector, verdict |
| **Measurements** | With their balloon numbers |
| **Checklist** | The answers given |
| **Release** | Accepted, rejected or hold released — with the reason, by whom, and when |

!!! note "A lot with no plan still produces a record"
    It states that the lot went **straight to stock** (dock-to-stock). That is
    itself the evidence, and the record says so rather than leaving a gap.

    The decision it evidences was made **once, on the item** — whether that
    material or part type has a plan at all — not on this delivery. So the
    record shows a standing decision being applied, which is what makes it
    defensible: nobody waved this lot through, the item was never under a plan.

    It follows that the thing to be able to justify is the **plan coverage**,
    not any individual dock-to-stock record.

!!! tip "It is regenerated, not stored"
    The PDF is built from live data each time, so it always reflects the current
    record. Don't archive a copy and treat it as the master — the system is the
    master.


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

### AS9100 / IATF Audit Pack
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
