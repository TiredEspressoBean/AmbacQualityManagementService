# Audit Trails

Comprehensive audit logging for regulatory compliance.

!!! example "Following one record"
    Open **Admin > Audit Log** and filter to a CAPA to see what a complete
    history looks like — who raised it, every field change with its before and
    after values, task assignments, the RCA, and the approval responses, each
    attributed and timestamped.

    A CAPA moves through **Open → In Progress → Pending Verification → Closed**
    (or Cancelled). Those are the statuses you will see in the log; the
    investigation phases you may work to — containment, root cause, corrective
    action — are how you run it, not states the record holds.

## Compliance Requirements

Audit trails are required by:

| Standard | Requirement |
|----------|-------------|
| **ISO 9001** | Records of monitoring and measurement |
| **AS9100D** | Configuration management, traceability |
| **IATF 16949** | Process control records |

## What is Logged

### Record Changes
Changes made through the application's normal save path are logged:
- What changed (before/after values)
- Who made the change
- When (timestamp)

Bulk system updates, which bypass that path, are not logged, and changes made
with no acting user (background and system writes) are not visible in the
tenant's audit log.

### Authentication events are **not** logged

!!! danger "There is no authentication audit trail in uqmes"
    Failed logins, logouts and session timeouts leave **no trace** in the audit
    log, and sign-ins are not recorded as authentication events. Do not offer
    the audit log as evidence of who signed in, and do not plan an
    investigation around it.

    If you need to show who signed in, or investigate repeated failed attempts,
    that evidence comes from your **identity provider** or your **web server
    logs**, not from here. Establish where it lives *before* an assessor asks.

    What uqmes does record is what a signed-in user **did** — the creates,
    updates and deletes they make against records, attributed and timestamped. The identity
    is proven at the edge; the accountability is kept here.

### Electronic Signatures
- Who signed
- What was signed
- Timestamp
- Signature meaning

### Permission Changes
- Group assignments
- Permission grants/revocations — in the group's history, as a change to
  **permissions** (add or delete) with who made it
- User status changes

## Audit Trail Characteristics

### Immutability

Audit records cannot be modified, deleted, or backdated. This is enforced in
the database, not only in the application, and there are two independent
layers.

**PostgreSQL triggers prevent the write.** `setup_audit_triggers` installs
triggers that block UPDATE and DELETE on the audit tables by any role,
superusers included, while the trigger is installed — covering:

`auditlog_logentry`, `permissionchangelog`, `steptransitionlog`,
`samplingauditlog`, `capastatustransition`, `recordedit`.

`approvalresponse` has its own trigger: a recorded approval response can only be
withdrawn, delegated, or answered again after withdrawal. Any other change, and
any deletion, is refused (*COMPLIANCE VIOLATION: An approval response can only be
withdrawn, delegated, or answered again after withdrawal.*). Each withdrawal and
re-answer is also kept as a correction (`recordedit`) and in the audit log.

The command runs as step 4 of `setup_database`, which containers run on
start, so a normal deployment has them without anyone remembering to.

**pgAudit records the attempt — on the self-hosted stack.** The Docker
Compose deployment builds PostgreSQL from `Dockerfile.postgres`, which
installs pgAudit, and preloads it with `pgaudit.log = "write, ddl, role"`.
Deliberately not `all`: those three classes are the accountability set.

!!! warning "pgAudit is not part of every deployment"
    It comes from the custom Postgres image. A deployment using a managed or
    templated Postgres — the Railway `pgvector` service, for instance — does
    **not** have pgAudit, and does not run `init-db.sql` either, so the
    RLS-subject application role is absent there too.

    The triggers are unaffected: they are installed by a Django management
    command from the application container, so they travel with every
    deployment. Confirm which layers you actually have before describing them
    to an assessor.

!!! info "Why both, where both exist"
    The triggers stop the modification; pgAudit means an action taken to
    *remove* a trigger is itself DDL, and therefore logged. Prevention and
    detection by separate mechanisms is what makes the control defensible
    rather than merely present — but only the first half is guaranteed.

!!! warning "Verify the triggers on any database not built by the standard deployment"
    A database restored from a dump, or created outside the container
    entrypoint, may not have them. Run `python manage.py setup_audit_triggers`
    — it is idempotent, and `--disable` exists for development only.

### Computer-Generated Timestamps
- Server-side timestamp (not client)
- UTC timezone
- Synchronized time source
- Cannot be altered by users

### User Attribution
- Unique user identification

## Viewing Audit Data

### System Audit Log
Navigate to **Admin** > **Audit Log**

Browsing needs `view_auditlog` — by default Tenant Admin, QA Manager, Document
Controller and Auditor — and shows only entries for records the reader can open.
Filter:
- By user
- By record type
- By action type
- By date range

### Record History
On any record, open the record's **Activity History** section (the **History**
card on a Data Management edit form). Every staff role can read the history of a
record they can open:
- All changes to that record
- Chronological order
- Full change details

## Audit Reports

Audit data can be **viewed and filtered** in the UI at **Admin** > **Audit
Log**, and in any record's **Activity History** section.

The audit log exports to Excel or CSV from the same screen — see [Export for
Auditors](#export-for-auditors). It can also be read through the API, `GET
/api/auditlog/`, with the same filter parameters; that needs `view_auditlog`,
as on screen.

### Planned

| Report | Status |
|--------|--------|
| User activity, change summary, access log, signature reports | Planned |
| Custom report builder with column selection | Planned |
| Scheduled / automated reports | Planned |

## Regulatory Mappings

### Audit trail properties

| Property | Implementation |
|----------|----------------|
| Secure, computer-generated timestamps | Server-side UTC timestamps |
| Audit trail for changes | Changes through the normal save path logged (see [Record Changes](#record-changes)) |
| Record of operator identity | User ID on all records |
| Previous values retained | Before/after values stored |
| Traceability | Part-to-lot-to-material tracking |

!!! note "Medical-device and FDA regulation is not a target"
    uqmes targets aerospace and automotive quality standards. 21 CFR Part 11,
    ISO 13485, and EU MDR are **not** design goals and no conformance with
    them is claimed.

## Data Retention

Audit logs retained per policy:

| Industry | Typical Retention |
|----------|-------------------|
| Medical Devices | Life of device + 2 years |
| Aerospace | 10+ years |
| Automotive | 15+ years |
| General | 7 years minimum |

Audit logs are never auto-deleted.

## Export for Auditors

Preparing data for an external audit:

1. Filter **Admin** > **Audit Log** to the audit scope — user, record type,
   action, search
2. **Export** > **Export as Excel** or **Export as CSV**. The file holds what
   the list shows, newest first: Timestamp, User, Action, Record type, Record,
   Record id, Changes and IP address
3. Hand it over, or format it as the auditor asked for it

**Who can extract the audit trail is a control.** Exporting needs
`export_auditlog` — by default Tenant Admin and Document Controller — and the
server enforces it: *Exporting the audit log needs the export audit log
permission.* Browsing needs only `view_auditlog` (Tenant Admin, QA Manager,
Document Controller and Auditor), so a QA Manager can review the log on screen
without being able to take it out. One record's history needs only
`view_logentry`.

**Every export is itself logged** — an access entry *Export csv: Audit log
(&lt;n&gt; rows)* (or *xlsx*) with the person, their IP address, the row count
and the filters used. An export is refused past 50,000 rows; filter first.

There is no PDF of the audit log.

## Permissions

| Permission | Allows | Groups |
|------------|--------|--------|
| `view_auditlog` | View full system audit trail | Tenant Admin, QA Manager, Document Controller, Auditor |
| `export_auditlog` | Export the audit log to Excel or CSV | Tenant Admin, Document Controller |

Standard users see history of records they can access via record detail pages.

## Next Steps

- [Electronic Signatures](signatures.md) - Signature compliance
- [Document Control](document-control.md) - Document management
- [Export Controls](export-controls.md) - ITAR/EAR compliance
