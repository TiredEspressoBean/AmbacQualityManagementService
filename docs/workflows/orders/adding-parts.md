# Adding Parts to Orders

Parts are the individual items tracked through production. This guide covers adding parts to orders.

## Adding Parts Manually

!!! warning "Not from the order page"
    The order detail page is read-only — it is the customer-facing view of an
    order and has no **Add Parts** control. Parts are added against the *work
    order* that carries the production.

### From the Work Orders Control Center

1. Go to **Production** > **Work Orders**
2. Tick exactly one work order — the bulk bar appears at the bottom
3. Click **Add Parts**
4. Fill in the dialog:

| Field | Description |
|-------|-------------|
| **Part Type** | Shown, not chosen — it comes from the work order's process |
| **Start Step** | Which step of the process the new parts begin at |
| **Quantity** | Number of parts to create |
| **ERP ID Start** | The number the ERP IDs count up from |

5. Click to confirm, and the parts are created attached to that work order

!!! note "The work order needs a process"
    If the work order has no process assigned, the dialog refuses with "This
    work order has no process — assign a process first." There are no steps to
    start the parts at until one is.

## ERP ID Generation

Each part gets an ERP ID built from the part type's own prefix and a counter:

```
ERP ID = <part type's ID prefix><counter padded to 4 digits>
```

The counter starts at the **ERP ID Start** you entered and increments by one per
part. A part type with prefix `WA` and an ERP ID Start of 1 gives `WA0001`,
`WA0002`, ... `WA0010` for ten parts. A part type with no prefix configured
falls back to `P`.

You do not type the prefix — set it on the part type.

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

!!! note "The parts are not deleted"
    Removing a part from an order only clears its order link — the part record
    survives, unattached to any order, and nothing is archived. If you remove a
    part by mistake you will need to set its order again rather than restore it.

## Next Steps

- [Tracker Overview](../tracking/tracker-overview.md) - Track parts through production
- [Order Status](order-status.md) - Monitor overall progress
- [Order Documents](order-documents.md) - Attach related files
