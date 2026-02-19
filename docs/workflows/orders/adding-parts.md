# Adding Parts to Orders

Parts are the individual items tracked through production. This guide covers adding parts to orders.

## Adding Parts Manually

### From the Order Detail Page

1. Open the order
2. Scroll to the **Parts** section
3. Click **+ Add Parts**
4. Fill in the form:

| Field | Description |
|-------|-------------|
| **Part Type** | Type of part to create |
| **Quantity** | Number of parts to add |
| **Lot Number** | Optional batch identifier |
| **Serial Prefix** | Prefix for auto-generated serial numbers |

5. Click **Add**

### Example

Adding 10 widgets with serial numbers:

- Part Type: `Widget Assembly`
- Quantity: `10`
- Serial Prefix: `WA-`

Creates: `WA-001`, `WA-002`, ... `WA-010`

## Serial Number Generation

Serial numbers are generated automatically based on configuration:

### Sequential (Default)
Parts get incrementing numbers: `001`, `002`, `003`

### With Prefix
Add a prefix for clarity: `WA-001`, `WA-002`

### Custom Pattern
Your admin may configure patterns like:
- `{YEAR}-{SEQ}` → `2026-00001`
- `{PARTTYPE}-{LOT}-{SEQ}` → `WGT-LOT5-001`

## Lot Numbers

Lots group parts manufactured together:

- Same raw material batch
- Same machine setup
- Same operator shift

Benefits of lot tracking:

- Faster recalls if issues found
- Traceability to material sources
- Quality trend analysis by lot

## Bulk Import

For large quantities or complex data:

1. Click **Import Parts** in the order
2. Download the CSV template
3. Fill in your data:

```csv
part_type,serial_number,lot_number,notes
Widget Assembly,WA-001,LOT-2026-A,
Widget Assembly,WA-002,LOT-2026-A,
Widget Assembly,WA-003,LOT-2026-A,Custom spec
```

4. Upload the file
5. Review the preview
6. Click **Import**

!!! warning "Validation"
    The import validates:

    - Part types exist
    - Serial numbers are unique
    - Required fields are present

    Fix any errors and re-upload if needed.

## Part Attributes

Depending on your part type configuration, parts may have additional fields:

| Field | Description |
|-------|-------------|
| **Revision** | Drawing or design revision |
| **Material** | Material specification |
| **Customer Part Number** | Customer's identifier |
| **Country of Origin** | For export compliance |
| **ECCN** | Export control classification |
| **ITAR Controlled** | Defense article flag |

## Part Status

New parts start at the first step of their process. Status changes as they progress:

| Status | Meaning |
|--------|---------|
| **In Process** | Part is moving through steps |
| **Complete** | Part finished all steps |
| **Quarantine** | Part held for quality review |
| **Scrapped** | Part disposed as scrap |
| **RTV** | Returned to vendor |

## Viewing Part Details

Click on any part to see:

- Current step and status
- Measurement history
- Quality reports
- Step transition log
- Associated documents

## Removing Parts

To remove parts from an order:

1. Select the parts (checkboxes)
2. Click **Remove** or use the action menu
3. Confirm the removal

!!! note "Audit Trail"
    Removed parts are soft-deleted. The audit trail retains the history for compliance.

## Splitting Parts

To move parts to a different order:

1. Select the parts
2. Click **Move to Order**
3. Select the destination order
4. Confirm

This is useful when:
- Customer splits a PO
- Parts need separate tracking
- Orders are combined

## Next Steps

- [Tracker Overview](../tracking/tracker-overview.md) - Track parts through production
- [Order Status](order-status.md) - Monitor overall progress
- [Order Documents](order-documents.md) - Attach related files
