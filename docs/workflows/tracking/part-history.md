# Part History

Every action on a part is recorded for full traceability. This guide covers viewing and using part history.

## Accessing Part History

1. Navigate to the part (from order or search)
2. Click the part to open its detail view
3. The audit trail is shown on the detail page itself

The detail page is laid out as sections on a single page, not tabs:

**General Information** · **Production Details** · **Quality Control** ·
**System Information** · **Quality Reports** · **Dispositions** ·
**Documents** · **Activity History**

## Activity History

The **Activity History** section shows the record's audit trail, newest first.
Each entry carries:

| Element | Shows |
|---------|-------|
| Action badge | **Created**, **Updated**, or **Deleted**, colour-coded |
| Actor | Who made the change, or **System** for automated changes |
| Time | Relative age, e.g. "3 days ago" |
| Change details | The fields that changed, with before and after values |

An entry whose changes are all internal shows *"No significant changes"*, and a
record with no entries yet shows *"No audit history."*

!!! note "Quality events are separate sections"
    Quality reports and dispositions are not entries in the activity history —
    they have their own **Quality Reports** and **Dispositions** sections on the
    same page.

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

!!! note "No export from the history view"
    The audit trail on the detail page has no export or print control. Part
    history is available through the API:

    ```
    GET /api/Parts/{id}/traveler/
    ```

    A **Work Order Traveler** PDF can be generated from the work order detail
    page — see [Exporting Data](../../analysis/exporting.md).

### Part Traveler
The traveler data returned by the API covers:

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

!!! note "Planned Feature"
    Side-by-side comparison of two parts' histories is not available. To
    compare processing, open each part's detail page separately, or pull both
    travelers from the API.

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
