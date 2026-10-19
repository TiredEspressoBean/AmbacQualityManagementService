# Audit Trail

The audit trail provides a complete record of all actions taken in uqmes, essential for compliance and investigation.

## What is Logged?

The audit trail captures:

| Category | Events |
|----------|--------|
| **Records** | Create, update, delete of all data |
| **Access** | Login, logout, session activity |
| **Documents** | Uploads, approvals, revisions |
| **Quality** | NCRs, dispositions, CAPA actions |
| **Parts** | Step transitions, measurements, status changes |
| **Approvals** | Electronic signatures, approval decisions |
| **Admin** | User changes, permission changes, settings |

## Accessing the Audit Trail

### System Audit Log

Navigate to **Admin** > **Audit Log**

The audit trail across records — every user, every record type, every action.
Browsing it needs `view_auditlog`, by default held by **Tenant Admin**,
**QA Manager**, **Document Controller** and **Auditor**. Other roles do not see
the menu entry.

!!! note "You see the history of what you can open"
    Even with `view_auditlog`, an entry is shown only if you can open the record
    it belongs to. A document you are not cleared for, or a record outside your
    access, leaves no trace in your view of the log.

### Record-Level History

View history for specific records:

1. Open any record (order, part, NCR, etc.)
2. Scroll to the **Activity History** section at the bottom of the detail page
3. See all changes to that record

This needs only `view_logentry`, which every staff role holds by default. It
shows the history of the record in front of you, and never of a record you
cannot open. On a Data Management edit form the same history is the **History**
card.

!!! note "A section, not a tab"
    There is no *History* or *Audit Trail* tab. The audit trail is a section on
    the record's own detail page.

## Audit Log Interface

### List View

| Column | Description |
|--------|-------------|
| **Timestamp** | When the action occurred |
| **User** | Who performed the action |
| **Action** | Create, Update, Delete |
| **Record Type** | What kind of record |
| **Record** | Link to the record |
| **Changes** | What changed |

### Filtering

Filter the audit log:

| Filter | Options |
|--------|---------|
| **Date Range** | Start and end dates |
| **User** | Specific user |
| **Action** | Create, Update, Delete |
| **Record Type** | Orders, Parts, NCRs, etc. |
| **Search** | Text search in changes |

### Change Details

Click an entry to see details:

```
Record: Part WA-001
Action: Update
User: jane.smith@company.com
Timestamp: 2026-03-15 10:30:45 UTC

Changes:
┌────────────────┬─────────────┬─────────────┐
│ Field          │ Before      │ After       │
├────────────────┼─────────────┼─────────────┤
│ current_step   │ Machining   │ Inspection  │
│ updated_at     │ 2026-03-15  │ 2026-03-15  │
│ updated_by     │ john.doe    │ jane.smith  │
└────────────────┴─────────────┴─────────────┘
```

## Audit Data

### What is Captured

For each change:

| Data | Description |
|------|-------------|
| **Timestamp** | Exact time (UTC) |
| **User ID** | Unique user identifier |
| **User Email** | User's email |
| **Action** | Type of change |
| **Object Type** | Model/record type |
| **Object ID** | Record identifier |
| **Before State** | Previous values |
| **After State** | New values |
| **IP Address** | Request source, where the entry records one |
| **Session** | Session identifier |

### Immutability

Audit records are **immutable**:

- Cannot be edited
- Cannot be deleted
- Protected at database level
- Tamper-evident

!!! warning "Compliance Requirement"
    Audit log immutability is required for regulatory compliance (AS9100D, IATF 16949, ISO 9001).

## Special Audit Events

### Electronic Signatures

Signature events include:
- User who signed
- Password verification status
- Signature meaning
- Signed record

### Login/Logout — not recorded here

!!! warning "There is no authentication trail in uqmes"
    Logins, failed logins, logouts and session timeouts leave **no trace** in
    the audit log. Do not plan an investigation around them, and do not offer
    them as evidence.

    That evidence lives in your **identity provider** or your **web server
    logs**. What uqmes records is what a signed-in user *did* — every create,
    update and delete, attributed and timestamped.

### Permission Changes

User permission changes:
- Role assignments
- Group membership changes
- Permission grants/revocations

## Searching the Audit Trail

### Basic Search

Search text in change details:
- Field names
- Values (before/after)
- Record identifiers

### Advanced Search

Combine filters:
- User AND date range
- Record type AND action
- Multiple criteria

### Saved Searches

!!! note "Planned Feature"
    Saved search functionality is planned for a future release.

When available:

1. Configure filters
2. Click **Save Search**
3. Name the search
4. Access from saved list

## Audit Reports

!!! note "Planned Feature"
    Pre-built audit reports and custom report generation are planned for a future release. Currently, audit data can be viewed in the UI or accessed via the API.

When available, standard reports will include:

- **User Activity Report**: Actions by user
- **Record History Report**: Changes to specific records
- **Login Report**: Authentication activity
- **Change Summary**: Aggregate change statistics

Custom and compliance-focused reports (AS9100D, IATF 16949, ISO 9001) are also planned.

## Exporting Audit Data

!!! note "No export from the audit log screen"
    The audit log viewer has no Export control. To take audit data out, read it
    from the REST API — `GET /api/auditlog/` — with the same filters, and format
    it as the auditor asks.

    Reading the API across records needs `view_auditlog`, the same as the
    screen, and it returns only entries for records you can open. A separate
    `export_auditlog` permission exists, but nothing checks it.

## Retention

### Audit Log Retention

Audit logs are retained per policy:

| Industry | Typical Retention |
|----------|-------------------|
| Medical Devices | Life of device + 2 years |
| Aerospace | 10+ years |
| Automotive | 15+ years |
| General | 7 years |

### Archival

Audit logs are **never auto-deleted** and there is no archival tier — no cold
storage, and no request process to retrieve anything, because nothing is moved
out of reach in the first place.

## Permissions

| Permission | Allows |
|------------|--------|
| `view_logentry` | The history of a record you can open — by default, every staff role |
| `view_auditlog` | Browse the audit trail across records — by default Tenant Admin, QA Manager, Document Controller and Auditor |
| `export_auditlog` | Exists, but nothing checks it — there is no export to gate |

!!! note "Credentials are not recorded"
    Passwords, API keys, integration secrets and invitation tokens are left out
    of the audit trail. A password change still appears as a change to the
    user, but without the field.

## Next Steps

- [Compliance](../compliance/audit-trails.md) - Compliance requirements
- [Exporting Data](exporting.md) - Export capabilities
- [Dashboard Overview](dashboard.md) - System monitoring
