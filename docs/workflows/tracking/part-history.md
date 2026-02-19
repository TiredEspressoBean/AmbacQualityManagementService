# Part History

Every action on a part is recorded for full traceability. This guide covers viewing and using part history.

## Accessing Part History

1. Navigate to the part (from order or search)
2. Click on the part to open detail view
3. Select the **History** or **Audit Trail** tab

## History Timeline

The history displays chronologically, newest first:

```
March 15, 2026 - 2:30 PM
  Part moved from "Final QA" to "Complete"
  By: Jane Smith
  Duration at step: 45 minutes

March 15, 2026 - 1:45 PM
  Measurement recorded: Outer Diameter = 25.003mm (Pass)
  By: John Doe
  Equipment: CMM-001

March 15, 2026 - 11:00 AM
  Part moved from "Assembly" to "Final QA"
  By: Mike Johnson

...
```

## Event Types

The history tracks all part-related events:

### Step Transitions

| Data | Description |
|------|-------------|
| From/To Step | Which steps |
| User | Who performed |
| Timestamp | When |
| Duration | Time at previous step |
| Equipment | Equipment used (if tracked) |

### Measurements

| Data | Description |
|------|-------------|
| Measurement Name | What was measured |
| Value | Recorded value |
| Pass/Fail | Result |
| User | Who recorded |
| Equipment | Measurement instrument |

### Status Changes

| Event | Description |
|-------|-------------|
| Quarantine | Part entered quarantine |
| Released | Part released from quarantine |
| Scrapped | Part dispositioned as scrap |
| Complete | Part finished all steps |

### Quality Events

| Event | Description |
|-------|-------------|
| Quality Report Created | NCR linked to part |
| Disposition Assigned | Decision recorded |
| CAPA Linked | Part connected to CAPA |

### Document Links

| Event | Description |
|-------|-------------|
| Document Attached | File linked to part |
| Certificate Generated | CoC or similar created |

## Filtering History

For parts with extensive history:

- **By Event Type**: Show only transitions, only measurements
- **By Date Range**: Focus on specific period
- **By User**: See actions by specific person

## Exporting History

Generate a part traveler or history report:

1. Open part history
2. Click **Export** or **Print**
3. Select format (PDF, CSV)
4. Download the report

### Part Traveler
A comprehensive document showing:

- Part identification
- Complete step history
- All measurements
- Quality events
- Signatures/approvals
- Current status

Useful for:

- Customer documentation
- Audit evidence
- Shipment records

## Comparing Parts

To compare history of multiple parts:

1. Select parts from the order
2. Click **Compare History**
3. View side-by-side timelines
4. Identify differences in processing

## Root Cause Analysis

Use history for investigation:

1. Find when a defect was introduced
2. Identify who was operating
3. Check equipment used
4. Compare to passing parts
5. Look for patterns

## Immutable Records

!!! info "Audit Compliance"
    Part history records are immutable. Once logged, events cannot be deleted or modified. This ensures regulatory compliance and audit integrity.

If a correction is needed:

1. A new "correction" event is logged
2. Original record is preserved
3. Both visible in history
4. Reason for correction recorded

## History Retention

Part history is retained according to your organization's retention policy:

| Industry | Typical Retention |
|----------|-------------------|
| Medical Devices | Life of device + 2 years |
| Aerospace | 10+ years |
| Automotive | 15+ years |
| General | 7 years |

See your administrator for specific policies.

## API Access

For integrations, part history is available via API:

```
GET /api/parts/{part_id}/history/
```

Returns JSON with all events, filterable by type and date.

## Related History

From part history, you can navigate to:

- **Order History**: All parts in the order
- **Quality Report**: Linked NCR details
- **CAPA**: Corrective action records
- **Equipment Log**: Machine history

## Permissions

| Permission | Allows |
|------------|--------|
| `view_parts` | View part history |
| `view_auditlog` | View detailed audit data |
| `export_data` | Export history reports |

## Next Steps

- [Audit Trail](../../analysis/audit-trail.md) - System-wide audit log
- [Quality Reports](../quality/quality-reports.md) - NCR management
- [Compliance Reports](../../compliance/reports.md) - Compliance documentation
