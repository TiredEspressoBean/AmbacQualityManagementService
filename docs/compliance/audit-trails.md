# Audit Trails

Comprehensive audit logging for regulatory compliance.

!!! example "Demo: Audit Trail in Action"
    In demo mode, review the audit trail for CAPA-2024-003 to see compliance logging:

    - **Creation**: QA Inspector Sarah Chen initiated CAPA on 2024-01-15
    - **Status changes**: INITIATED → CONTAINMENT → RCA → CORRECTIVE → VERIFICATION
    - **Task assignments**: Task "Update incoming inspection procedure" assigned to Sarah Chen
    - **5-Whys RCA**: Root cause analysis completed by Maria Santos
    - **Approvals**: APR-2024-0015 pending Jennifer Walsh's closure approval

    Navigate to Admin > Audit Log and filter by "CAPA" to see the complete history with timestamps and user attribution.

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

### Authentication Events
- Login attempts (success/failure)
- Logout events
- Session timeouts
- Password changes

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

Full system audit trail with filtering:
- By user
- By record type
- By action type
- By date range

### Record History
On any record, view **History** tab:
- All changes to that record
- Chronological order
- Full change details

## Audit Reports

Audit data can be **viewed and filtered** in the UI at **Admin** > **Audit
Log**, and on any record's **History** tab.

!!! warning "Audit data cannot be exported from the UI"
    Export is deliberately disabled on the audit log viewer. To get audit data
    out for an audit or a report, use the API:

    ```
    GET /api/AuditLog/
    ```

    Filter it with the same parameters available in the UI.

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

Prepare data for external audits:

1. Filter to audit scope
2. Export to PDF or CSV
3. Include all relevant records
4. Provide in auditor-requested format

## Permissions

| Permission | Allows | Groups |
|------------|--------|--------|
| `view_auditlog` | View full system audit trail | Admin, QA_Manager, Document_Controller |
| `export_auditlog` | Export audit data for auditors | Admin |

Standard users see history of records they can access via record detail pages.

## Next Steps

- [Electronic Signatures](signatures.md) - Signature compliance
- [Document Control](document-control.md) - Document management
- [Export Controls](export-controls.md) - ITAR/EAR compliance
