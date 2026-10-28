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

The **Activity History** section is the part's timeline: the changes to the
part and to every record about it — step executions, measurements, material
draws, quality reports, dispositions, overrides — newest first, 25 at a time
with **Show older**. Each entry carries:

| Element | Shows |
|---------|-------|
| Record and action | The kind of record, and whether it was **created**, **updated** or **deleted** (colour-coded) |
| Actor | Who made the change, or **System** for automated changes |
| Time | The date and time; hover for the relative age, e.g. "3 days ago" |
| Record | The record's name |
| Change details | The fields that changed, with before and after values — up to six, then *+N more fields* |

A part with no entries shows *"No recorded history."* The audit log records
changes as work happens, so a record loaded in its final state (an import, for
instance) starts with none.

### Corrections

Some changes are made with a **reason**. Changing a work order's priority and
releasing a lot's hold show in a **Decisions (N)** block; the rest show in a
**Corrections (N)** block. Each line gives *field: old → new*, the reason in
quotes, and who made the change and when. Corrections come from, among others:

- adjusting a lot's quantity
- cancelling or chasing an expected delivery
- shipping, and voiding a shipment
- moving a lot
- correcting the lot a draw came from
- taking a part out of a shared cycle
- short-closing a work order

The block appears on the **History** card of a Data Management record, in a
part's history timeline, and in a detail page's audit trail. It's hidden when
there are none. Reading it needs `view_recordedit`, which every staff role and
the Auditor hold by default, and you must be able to open the record itself.
There's no list of corrections across records.

!!! note "Quality events also have their own sections"
    Quality reports and dispositions have their own **Quality Reports** and
    **Dispositions** sections on the same page; their changes appear in the
    activity history as well.

!!! tip "For the whole story in one document, use the Traveler"
    Activity History is the record's **change log** — fields altered, by whom.
    It is not the same thing as the unit's manufacturing history, and reading
    one off the other means following several sections and links.

    The part's **Traveler** button produces that history as a single document:
    this serial's as-built traveler — its work order's routing, filled with who
    did each step, what was measured, and the lots that went in.

    That is what to produce when an auditor asks to see everything about one
    serial, and what to attach when a customer asks what was done to their
    unit. See [Compliance Reports](../../compliance/reports.md).

## Event Types

Each entry is a change to a record about the part — a step execution, a
measurement, a material draw, a quality report, a disposition, an override, the
part itself — and shows which fields changed. A status change reads as the
part's **Part status** field changing; a step move as its **Step** field
changing, from one step's name to the next.

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
GET /api/Parts/{part_id}/history/
```

Note the capital **P**. The endpoint returns JSON with all events in order and
takes no filters — only `limit` and `offset` for paging. Filter on your side.

## Related History

From part history, you can navigate to:

- **Order History**: All parts in the order
- **Quality Report**: Linked NCR details
- **CAPA**: Corrective action records
- **Equipment Log**: Machine history

## Permissions

| Permission | Allows |
|------------|--------|
| `view_parts` + `view_logentry` | View part history (every staff role) |
| `view_auditlog` | Browse the tenant-wide audit trail (Tenant Admin, Document Controller, QA Manager, Auditor) |
| `export_data` | Export history reports |

## Next Steps

- [Audit Trail](../../analysis/audit-trail.md) - System-wide audit log
- [Quality Reports](../quality/quality-reports.md) - NCR management
- [Compliance Reports](../../compliance/reports.md) - Compliance documentation
