# Material Lot Tracking

Material lot tracking provides full traceability for raw materials, components, and consumables used in production.

## Overview

Lot tracking enables:

- **Material Traceability** - Track which lots were used in which parts
- **Supplier Tracking** - Link lots to suppliers and supplier lot numbers
- **Quarantine Management** - Isolate suspect material lots
- **Usage Tracking** - Record material consumption during production

## Key Concepts

### Material Lots

A **material lot** represents a batch of material received or produced:

| Field | Description |
|-------|-------------|
| **Lot Number** | Unique identifier for this lot |
| **Material Type** | Type of material (part type) |
| **Supplier** | Company that supplied this lot |
| **Supplier Lot Number** | Vendor's lot identification |
| **Status** | RECEIVED, IN_USE, CONSUMED, SCRAPPED, QUARANTINE |
| **Quantity** | Amount in lot (with unit) |
| **Parent Lot** | If this lot was split from another |

### Lot Statuses

| Status | Meaning |
|--------|---------|
| **RECEIVED** | Lot received but not yet released |
| **IN_USE** | Lot available for production use |
| **CONSUMED** | Lot fully used |
| **SCRAPPED** | Lot disposed of |
| **QUARANTINE** | Lot under investigation |

### Material Usage

**Material usage** records track consumption:

- Which lot was used
- How much was consumed
- Which part/work order used it
- When and by whom

## Lot Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   RECEIVED   │────▶│    IN_USE    │────▶│   CONSUMED   │
│              │     │              │     │              │
│ Incoming     │     │ Available    │     │ Fully used   │
│ inspection   │     │ for use      │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │
       │                    │ If issue found
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│   SCRAPPED   │     │  QUARANTINE  │
│              │     │              │
│ Disposed     │     │ Under        │
│              │     │ investigation│
└──────────────┘     └──────────────┘
```

## Common Operations

### Receiving Lots

When material arrives:

1. Create material lot record
2. Enter lot number and supplier information
3. Record quantity received
4. Perform incoming inspection
5. Release to IN_USE or quarantine if issues found

### Using Material

During production:

1. Select material lot to use
2. Record quantity consumed
3. Link to part/work order
4. Remaining quantity updates automatically

### Splitting Lots

To divide a lot:

1. Select lot to split
2. Specify quantity for new lot
3. System creates child lot with parent reference
4. Both lots maintain traceability

### Quarantining Lots

When issues are suspected:

1. Change lot status to QUARANTINE
2. Document reason
3. Investigate affected parts
4. Either release (back to IN_USE) or scrap

## Traceability

Lot tracking enables forward and backward traceability:

**Forward Traceability**: Given a lot, find all parts that used it
- Useful for recalls and quality investigations
- Shows impact scope of material issues

**Backward Traceability**: Given a part, find which lots were used
- Supports root cause analysis
- Shows material history for any part

## Integration Points

### SPC Analysis

When SPC charts show out-of-control signals:

- Check if affected parts share a material lot
- Material variation is a common root cause
- Lot-level analysis helps identify supplier issues

### Quality Reports

When creating quality reports:

- Link to material lot if material-related
- Supports supplier quality tracking
- Enables lot-based containment actions

### CAPA

Material-related CAPAs can:

- Reference specific material lots
- Track supplier-related corrective actions
- Drive incoming inspection improvements

## Best Practices

1. **Assign clear lot numbers** - Use consistent numbering schemes
2. **Record supplier info** - Always capture supplier lot numbers
3. **Track usage promptly** - Record consumption as it happens
4. **Investigate signals** - Check lot correlation for quality issues
5. **Document splits** - Maintain parent-child relationships
6. **Quarantine fast** - Isolate suspect material immediately

## Permissions

| Permission | Allows |
|------------|--------|
| `view_materiallot` | View material lots |
| `add_materiallot` | Create new lots |
| `change_materiallot` | Update lot information |
| `delete_materiallot` | Delete lots |

## API Access

Material lots are available via the REST API:

- `GET /api/MaterialLots/` - List lots
- `POST /api/MaterialLots/` - Create lot
- `POST /api/MaterialLots/{id}/split/` - Split a lot
- Export to Excel supported

## Related Topics

- [Quality Reports](../quality/quality-reports.md) - Linking lots to NCRs
- [Quarantine](../quality/quarantine.md) - Managing quarantined lots
- [SPC Analysis](../../analysis/spc.md) - Material-related variations
