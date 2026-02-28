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


## Lot Numbers

Lots group parts manufactured together:

- Same raw material batch
- Same machine setup
- Same operator shift

Benefits of lot tracking:

- Faster recalls if issues found
- Traceability to material sources
- Quality trend analysis by lot

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
| **Pending** | Part not yet started |
| **In Progress** | Part is moving through steps |
| **Awaiting QA** | Part waiting for quality inspection |
| **Ready for Next Step** | Step complete, ready to advance |
| **Quarantined** | Part held for quality review |
| **Rework Needed** | Part requires rework |
| **Rework In Progress** | Rework underway |
| **Completed** | Part finished all steps |
| **Shipped** | Part has been shipped |
| **In Stock** | Part in inventory |
| **Scrapped** | Part disposed as scrap |
| **Cancelled** | Part cancelled |

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
