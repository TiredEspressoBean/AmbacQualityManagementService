# Audit Trails

Comprehensive audit logging for regulatory compliance.

!!! example "Demo: following one record"
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

### All Record Changes
Every create, update, delete is logged:
- What changed (before/after values)
- Who made the change
- When (timestamp)
- System information

### Authentication events are **not** logged

!!! danger "There is no authentication audit trail in uqmes"
    Logins, failed logins, logouts and session timeouts leave **no trace** in
    the audit log. Do not offer this as evidence, and do not plan an
    investigation around it.

    If you need to show who signed in, or investigate repeated failed attempts,
    that evidence comes from your **identity provider** or your **web server
    logs**, not from here. Establish where it lives *before* an assessor asks.

    What uqmes does record is what a signed-in user **did** — every create,
    update and delete against a record, attributed and timestamped. The identity
    is proven at the edge; the accountability is kept here.

### Electronic Signatures
- Who signed
- What was signed
- Timestamp
- Signature meaning

### Permission Changes
- Group assignments
- Permission grants/revocations
- User status changes

## Audit Trail Characteristics

### Immutability

Audit records cannot be modified, deleted, or backdated. This is enforced in
the database, not only in the application, and there are two independent
layers.

**PostgreSQL triggers prevent the write.** `setup_audit_triggers` installs
triggers that reject UPDATE and DELETE on the audit tables — **including for
superusers** — covering:

`auditlog_logentry`, `permissionchangelog`, `steptransitionlog`,
`samplingauditlog`, `approvalresponse`, `capastatustransition`, `recordedit`.

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
- Cannot use shared accounts
- Session tracking

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

!!! warning "Audit data cannot be exported from the UI"
    Export is turned off on the audit log viewer. To get audit data
    out for an audit or a report, use the API:

    ```
    GET /api/auditlog/
    ```

    Filter it with the same parameters available in the UI. Browsing it needs
    `view_auditlog`, as on screen.

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
| Audit trail for changes | All changes logged |
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

There is **no PDF or CSV export button** on the audit log — export is turned off
on that screen, as noted above. Preparing data for an external audit means:

1. Filter to the audit scope in **Admin** > **Audit Log** to confirm what you
   need, then
2. Pull the same range from `GET /api/auditlog/`, using the same filter
   parameters
3. Format it as the auditor asked for it

Reading the API needs `view_logentry`, the same permission as the screen — by
default held by every staff role. `export_auditlog` exists but nothing checks it,
so do not cite it as a control over who can extract the audit trail.

## Permissions

| Permission | Allows | Groups |
|------------|--------|--------|
| `view_auditlog` | View full system audit trail | Admin, QA Manager, Document Controller |
| `export_auditlog` | Export audit data for auditors | Admin |

Standard users see history of records they can access via record detail pages.

## Next Steps

- [Electronic Signatures](signatures.md) - Signature compliance
- [Document Control](document-control.md) - Document management
- [Export Controls](export-controls.md) - ITAR/EAR compliance
