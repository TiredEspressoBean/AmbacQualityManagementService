# Audit Trail

The audit trail provides a complete record of all actions taken in uqmes, essential for compliance and investigation.

## What is Logged?

The audit trail captures:

| Category | Events |
|----------|--------|
| **Records** | Create, update, delete of all data |
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
| **Time** | When the action occurred — how long ago, and the date and time |
| **User** | Who performed the action |
| **Action** | Created, Updated, Deleted or Accessed |
| **Object** | The kind of record and its name, linking to the record (a deleted one is struck through, without a link) |
| **Changes** | Up to four changed fields, old value → new value |

### Searching and sorting

The page has a **search** box, which matches the record's name and the text of
the changes, and a sort: **Most Recent**, **Oldest First**, **User (A-Z)** or
**User (Z-A)**.

!!! note "No filter panel"
    There is no date-range, user, action or record-type filter on the page.
    The API takes `actor`, `action`, `content_type` and `object_pk` filters —
    `GET /api/auditlog/`.

### Change Details

Each row's details link opens the entry: **Event Details** (action, timestamp,
IP address), **Audited Object** (its type, name and ID), **User**, and every
**Change**, old value and new.

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

### Immutability

Audit records are **immutable**:

- Cannot be edited
- Cannot be deleted
- Protected at database level, by triggers that refuse any update or delete

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

The search box matches:
- The record's name
- The text of the changes — field names and values, before and after

### Combining criteria

On the page, search is the only narrowing. To combine a user, an action and a
record type, query `GET /api/auditlog/` with its `actor`, `action`,
`content_type` and `object_pk` filters. For one record's whole history, open
the record — see [Record-Level History](#record-level-history).

There are no saved searches.

## Audit Reports

There are no pre-built audit reports — no user-activity, record-history or
change-summary PDF. Audit data is read on screen, exported to Excel or CSV, or
read through the API.

## Exporting Audit Data

**Admin** > **Audit Log** has an **Export** menu — **Export as Excel** or
**Export as CSV** — for holders of `export_auditlog`. It writes what the list
shows: the same filters (user, record type, action) and search, only entries
for records you can open, newest first. The columns are Timestamp, User
(*System* for automatic changes), Action, Record type, Record, Record id,
Changes and IP address.

- An export is refused past 50,000 rows: *Filter the list first, then export.*
- Each export is itself recorded in the audit log, as an access entry naming
  who exported, the format, the row count and the filters.
- Browsing without exporting needs only `view_auditlog`; without
  `export_auditlog` the menu is not shown, and the server refuses the export.

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
| `export_auditlog` | Export the audit log to Excel or CSV — by default Tenant Admin and Document Controller |

!!! note "Credentials are not recorded"
    Passwords, API keys, integration secrets and invitation tokens are left out
    of the audit trail. A password change still appears as a change to the
    user, but without the field.

## Next Steps

- [Compliance](../compliance/audit-trails.md) - Compliance requirements
- [Exporting Data](exporting.md) - Export capabilities
- [Dashboard Overview](dashboard.md) - System monitoring
