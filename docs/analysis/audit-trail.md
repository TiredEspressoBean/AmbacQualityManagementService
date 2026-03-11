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

Full system-wide audit trail:
- All users
- All record types
- All actions

### Record-Level History

View history for specific records:

1. Open any record (order, part, NCR, etc.)
2. Click **History** or **Audit Trail** tab
3. See all changes to that record

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
| **IP Address** | (if enabled) Request source |
| **Session** | Session identifier |

### Immutability

Audit records are **immutable**:

- Cannot be edited
- Cannot be deleted
- Protected at database level
- Tamper-evident

!!! warning "Compliance Requirement"
    Audit log immutability is required for regulatory compliance (ISO 13485, 21 CFR Part 11, AS9100D).

## Special Audit Events

### Electronic Signatures

Signature events include:
- User who signed
- Password verification status
- Signature meaning
- Signed record

### Login/Logout

Authentication events:
- Successful logins
- Failed login attempts
- Logouts
- Session timeouts

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

Custom and compliance-focused reports (FDA 21 CFR Part 11, ISO 13485, AS9100D) are also planned.

## Exporting Audit Data

!!! note "Planned Feature"
    UI export of audit data is planned for a future release.

**Current access:** Use the REST API endpoint `GET /api/AuditLog/` with filters to retrieve audit data programmatically for external reporting or archival.

When UI export is available:

| Format | Use Case |
|--------|----------|
| **CSV** | Analysis, archival |
| **PDF** | Auditor submission |
| **JSON** | Integration, backup |

Steps will be:

1. Filter to desired data
2. Click **Export**
3. Select format
4. Download

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

Old audit logs may be archived:
- Moved to cold storage
- Still accessible on request
- Meets retention requirements

## Permissions

| Permission | Allows |
|------------|--------|
| `view_auditlog` | View audit trail |
| `export_auditlog` | Export audit data |

Standard users can view history of records they can access.
Full audit log access is typically admin-only.

## Best Practices

1. **Review regularly** - Check for anomalies
2. **Investigate issues** - Use trail for root cause
3. **Prepare for audits** - Use API to extract data for compliance reviews
4. **Monitor sensitive** - Watch critical record types
5. **Protect access** - Limit who can view full audit log

## Next Steps

- [Compliance](../compliance/audit-trails.md) - Compliance requirements
- [Exporting Data](exporting.md) - Export capabilities
- [Dashboard Overview](dashboard.md) - System monitoring
