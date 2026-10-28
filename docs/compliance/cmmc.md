# CMMC (Cybersecurity Maturity Model Certification)

DoD cybersecurity certification requirements for defense contractors.

!!! info "Who this page is for"
    **uqmes is not the assessed party.** CMMC certifies *defense
    contractors*. If you handle CUI under a DoD contract, you are assessed —
    and uqmes is one system inside the boundary you are assessed on.

    So this page is not a compliance claim. It describes what the software
    does for the practices it can reach, and with what evidence, so you can
    cite it in your System Security Plan.

    Most CMMC practices are about your facility, your people, your identity
    provider and the hosting the application runs on. Those are not the
    software's job. They are listed once, under
    [Organisation and hosting responsibilities](#organisation-and-hosting-responsibilities),
    and not described further here.

!!! important "Which installation this page describes"
    A CMMC facility runs uqmes **on premises**, installed with Docker Compose
    and set to dedicated mode (`DEPLOYMENT_MODE=dedicated`), so the whole
    installation is one organization's. Everything below describes that
    installation.

    The shared hosted service serves several organizations and is not a
    FedRAMP environment, so it is not for CUI. A cloud deployment for CMMC
    would need a FedRAMP-authorized one.

## Overview

CMMC is the Department of Defense's framework for assessing and certifying
contractor cybersecurity practices. It became mandatory for DoD contracts
starting in 2025.

## CMMC Levels

| Level | Name | Requirements | Assessment |
|-------|------|--------------|------------|
| **Level 1** | Foundational | 17 practices (FAR 52.204-21) | Self-assessment |
| **Level 2** | Advanced | 110 practices (NIST 800-171) | Third-party assessment (C3PAO) |
| **Level 3** | Expert | 110+ practices (NIST 800-172) | Government-led assessment |

This page maps uqmes against **CMMC Level 2**, the tier that applies to
contractors handling CUI.

## Where the software contributes

CMMC Level 2 is the 110 practices of NIST 800-171 across 14 domains. The
software has a part in five of them; the other nine are wholly organisational,
physical or infrastructure domains.

| Domain | What uqmes does |
|--------|-----------------|
| Access Control (AC) | Authentication on every API call, role-based permissions, classification and export-control filtering, tenant isolation |
| Audit & Accountability (AU) | Change and access records, immutable at the database, browsable by permission |
| Configuration Management (CM) | Versioned, approval-locked records and change control for documents and processes |
| Identification & Authentication (IA) | Individual accounts, hashed passwords, optional Microsoft SSO, password re-entry at signatures |
| Media Protection (MP) / System & Comms Protection (SC) | Classification marking and access, tenant isolation, CSRF/CORS controls |

!!! info "How to read the markers"
    | | Meaning |
    |---|---------|
    | ✅ **Provides** | uqmes is the mechanism; cite it directly |
    | ⚠️ **Partial** | uqmes supplies some of it, or a setting you must configure. Say what you did, not just that the feature exists |

    Where a practice *is* a genuine shortcoming in the software the row says
    **gap** — one does, 3.3.4 below.

## What the software does, by domain

### Access Control (AC)

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| AC.L2-3.1.1 | User authentication required | ✅ | `IsAuthenticated` is the default permission on every API endpoint, alongside `TenantAccessPermission`; the session and token authenticators refuse a user who asks for a tenant they do not belong to. The few unauthenticated endpoints — sign-in, sign-up, password reset — are rate-limited per client IP |
| AC.L2-3.1.2 | Function-level authorization | ✅ | 15 role presets (`GROUP_PRESETS` in `Tracker/presets.py`) over model permissions, enforced by `TenantModelPermissions` (HTTP method → view/add/change/delete) plus per-action gates declared on the viewsets |
| AC.L2-3.1.3 | CUI flow control | ✅ | Five classification levels — Public, Internal, Confidential, Restricted, Secret — filtered by `for_classification()` in `SecureQuerySet`; ITAR- and EAR-flagged records are filtered by `for_export_control()`, keyed to the user's US-person, ITAR-authorisation and citizenship fields |
| AC.L2-3.1.4 | Separation of duties | ✅ | Distinct roles. The segregation-of-duties permissions (verify a CAPA, review an RCA, approve a disposition or step override, grant supplier and part approvals) are in the QA Manager and Tenant Admin presets only. A requester decides their own approval only where the template allows it, or for a CAPA plan when nobody else can — always with a written justification, and recorded as `self_approved`. `self_verified` records when a CAPA or RCA was verified by its own conductor |
| AC.L2-3.1.5 | Least privilege | ✅ | Presets grant per role. The Customer role sees only orders it is the customer or a viewer of, and the work, parts, documents and quality reports on them; it can also answer approval requests sent to it and invite viewers to its own orders |
| AC.L2-3.1.7 | Privileged functions | ✅ | Group membership and group permissions can be changed only by holders of `change_tenantgroup` (Tenant Admin), so no other user can grant themselves a permission. Every such change is in the audit log with who made it |
| AC.L2-3.1.8 | Unsuccessful logon attempts | ⚠️ | Sign-in is rate-limited per client IP (`THROTTLE_LOGIN`, default 10 a minute). There is no per-account lockout; with SSO, cite your identity provider's lockout |
| AC.L2-3.1.9 | Privacy and security notices | ✅ | The tenant sets a system-use notice for the login page (**Settings** > **Organization** > **Sign-in notice**) and can require it acknowledged. Password sign-in without the acknowledgement is refused by the server, and each acknowledgement is an access entry with the user, trusted IP and a hash of the wording. The wording is the shop's; none ships. A Microsoft sign-in is gated on the page only, and not recorded. On a dedicated installation the notice is always the organization's |
| AC.L2-3.1.10 / 3.1.11 | Session lock and termination | ⚠️ | Sessions expire after `SESSION_COOKIE_AGE` of inactivity and can be made to end on browser close; API tokens expire after `API_TOKEN_TTL_SECONDS` (default one hour). There is no screen lock that hides the page — see the session settings below |
| AC.L2-3.1.22 | Public posting control | ✅ | Classification gates what a Customer-role user can retrieve |

### Audit & Accountability (AU)

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| AU.L2-3.3.1 | Audit record creation | ✅ | django-auditlog on every model (`AUDITLOG_INCLUDE_ALL_MODELS`), including group permission and membership changes. Reads are recorded too: opening or downloading a document, generating a report, a data export and an AI query each write an access record (`services/core/access_log.py`). Credential fields — passwords, integration keys, invitation tokens — are excluded from the trail |
| AU.L2-3.3.2 | User attribution | ✅ | Every change and access record carries the actor and a server timestamp. Approvals and QA releases also record the signer, the verification method and the trusted client IP. Change records store the same trusted client IP, read from the configured proxy header rather than the client-set first `X-Forwarded-For` entry |
| AU.L2-3.3.4 | Alert on audit logging failure | ⚠️ **gap** | uqmes emits the signal; you route it. A failed access-log write logs at **ERROR** to the `compliance.access_control` logger with `audit_write_failed` in the record, carrying a traceback. Point your log pipeline at that marker to make it an alert — the application does not page anyone itself. Writes stay non-fatal by design: the read has already happened, so failing the request afterwards records nothing extra |
| AU.L2-3.3.6 | Reduction and report generation | ✅ | The audit log (**Admin** > **Audit Log**, `/api/auditlog/`) is filterable by actor, content type, object and action, with search and ordering; the filtered view exports to Excel or CSV behind `export_auditlog`, and each export is itself logged |
| AU.L2-3.3.7 | Authoritative timestamps | ✅ | Timestamps are set by the server, stored in UTC (`TIME_ZONE = 'UTC'`, `USE_TZ`) |
| AU.L2-3.3.8 | Audit protection | ✅ | PostgreSQL triggers refuse UPDATE and DELETE on six audit tables, superusers included, and on approval responses admit only withdraw, delegate, or answer again after withdrawal (`setup_audit_triggers`, which `setup_database` runs on every start or release) |
| AU.L2-3.3.9 | Audit access restriction | ✅ | Browsing the audit trail across records needs `view_auditlog` (Tenant Admin, Document Controller, QA Manager and Auditor presets). One record's history needs `view_logentry` and being able to open that record. The log endpoint is read-only and scoped to the tenant |

AU.L2-3.3.3 (review of logged events) and 3.3.5 (correlation across systems)
are your review and SIEM practices; the software's part is the API above.

!!! warning "3.3.4 is a deployment step, not a code gap — but it is still yours to close"
    An assessor will ask what happens when audit logging itself fails. Two
    different things can fail, and only one of them is at risk:

    - **Change records** (django-auditlog) are written inside the request
      transaction. If that write fails the whole transaction rolls back, so a
      change is never recorded as having happened when it did not. Nothing to
      do here.
    - **Access records** — who *read* a document, an export, a controlled
      drawing — are written after the read has already occurred. A failure
      there is deliberately non-fatal: refusing the request afterwards would
      block a shop-floor operator from opening a drawing without recording
      anything extra.

    uqmes does its half: that failure logs at **ERROR** to the
    `compliance.access_control` logger with `audit_write_failed` in the record
    and a traceback, exactly so it can be alerted on. **Nothing pages anyone
    until you point a log pipeline at that marker.** An unrouted deployment
    fails 3.3.4; a routed one satisfies it. Do that before an assessment, and
    say in your SSP where the alert goes.

### Identification & Authentication (IA)

Where sign-in goes through Microsoft SSO (`SSO_ENABLED`), multifactor
authentication, password reuse and lockout are the identity provider's, and
you cite it for them. The rows below are what the software does itself.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| IA.L2-3.5.1 | Identify users | ✅ | One account per person, signed in by email; records are attributed to that account |
| IA.L2-3.5.2 | Authenticate before access | ✅ | Session (password or Microsoft SSO) or an expiring API token; every API endpoint but sign-in, sign-up and password reset requires an authenticated user |
| IA.L2-3.5.3 | Multifactor authentication | ⚠️ | Not built into local password sign-in. Satisfied only through SSO with MFA enforced at the identity provider |
| IA.L2-3.5.6 | Disable identifiers | ⚠️ | Accounts are deactivated, singly or in bulk, never deleted. Nothing deactivates an account automatically after inactivity |
| IA.L2-3.5.7 | Password complexity | ⚠️ | Django validators: similarity to user attributes, minimum length, common-password list, all-numeric rejection. No character-class rule |
| IA.L2-3.5.8 | Prohibit password reuse | ⚠️ | uqmes keeps no password history; satisfied only through the identity provider |
| IA.L2-3.5.9 | Temporary password on first use | ⚠️ | Invitations carry a sign-up link rather than a temporary password, so the practice does not map cleanly; there is no forced first-login change |
| IA.L2-3.5.10 | Cryptographically protected passwords | ✅ | Stored as salted hashes with Django's default PBKDF2-SHA256 hasher; never stored in clear |
| IA.L2-3.5.11 | Obscure authentication feedback | ✅ | A failed sign-in does not say whether the account exists |

**Re-authentication at signatures.** An approval through the API needs a drawn
signature and the approver's own password, checked on the server; a QA release
or a work-instruction signature asks for the password where the author set it
to. Signing passwords are throttled — five failures per gate and ten across all
gates per user in 15 minutes (`services/core/second_person.py`) — so an open
session is not a password oracle. See [Electronic Signatures](signatures.md).

!!! warning "Set the session lifetime for your deployment"
    The default is 14 days with no expiry on browser close. On a shared
    shop-floor tablet the next operator inherits the session — and in a
    quality system every record they create is attributed to whoever logged
    in, which makes it an attribution problem as much as an access one.

    Three environment variables control this:

    | Variable | Default | For shared devices |
    |----------|---------|--------------------|
    | `SESSION_COOKIE_AGE` | `1209600` (14 days) | `28800` for one shift, or shorter |
    | `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `False` | `true` |
    | `ACCOUNT_EMAIL_VERIFICATION` | `optional` | `mandatory` where delivery matters |

    Sessions roll on each request (`SESSION_SAVE_EVERY_REQUEST`), so the age
    is an idle timeout rather than a hard cap — a tablet in continuous use
    will not log itself out mid-shift.

### Configuration Management (CM)

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| CM.L2-3.4.1 | Baseline configurations | ✅ | Versioned records via `create_new_version()`; `SPCBaseline` freezes a control-chart baseline |
| CM.L2-3.4.3 | Change tracking and approval | ✅ | `ApprovalRequest` plus change control. A **document** revision is refused without a reason — `Documents.revise` returns 400 *"change_justification is required when creating a revision"*. A **process** change carries its own `proposed_change`, `justification` and `risk_analysis` on the change request, and cannot reach production except through it |
| CM.L2-3.4.5 | Access restrictions on change | ✅ | Per-action permissions, plus the approval lock (`services/core/approval_lock.py`): a record under approval or approved — and a closed CAPA, a verified RCA, a recorded inspection result, a closed disposition, a process out of draft — refuses client edits and deletes, and its status and approver fields change only through their workflow actions |

The other CM practices — host baselines, least functionality, software
allow-listing — concern the platform the application runs on.

### Media Protection (MP)

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| MP.L2-3.8.2 | Limit access to CUI | ✅ | Classification and export-control filtering in `SecureQuerySet` (`for_classification()`, `for_export_control()`) |
| MP.L2-3.8.4 | Mark media with CUI markings | ✅ | Five `ClassificationLevel` values carried on documents and shown in the UI; changing one needs `classify_documents` |
| MP.L2-3.8.5 | Control access to media | ✅ | Classification-tier permissions: `view_confidential_documents`, `view_restricted_documents`, `view_secret_documents` |

### System & Communications Protection (SC)

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| SC.L2-3.13.2 | Security architecture | ✅ | Tenant isolation is enforced in the application by tenant-scoped managers and tenant-membership checks at authentication. Database row-level security beneath it is **opt-in**: with `ENABLE_RLS=true`, `setup_rls` (run by `setup_database`) applies `FORCE ROW LEVEL SECURITY` and a tenant policy to the tenant-scoped tables it lists, and each request sets the tenant before it runs. RLS needs the application to connect as a non-superuser database role, since PostgreSQL does not apply it to superusers |
| SC.L2-3.13.4 | Prevent unauthorized transfer | ✅ | Tenant-scoped querysets (and RLS where enabled); `perform_update()` refuses changing a record's tenant |
| SC.L2-3.13.8 | Transmission confidentiality | ⚠️ | With `DEBUG` off the application marks session and CSRF cookies Secure and sends HSTS. TLS itself terminates at your proxy or platform |
| SC.L2-3.13.15 | Communication authenticity | ✅ | CSRF protection with an explicit trusted-origin list; CORS allow-list rather than wildcard |

uqmes encrypts stored integration credentials only, so do not cite
application-layer encryption for CUI at rest (3.13.16).

### Where the software supplies records for your practice

| Practice | What uqmes provides |
|----------|---------------------|
| AC.L2-3.1.20 (external connections) | Each integration sync is logged (`IntegrationSyncLog`) |
| CM.L2-3.4.4 (security impact of changes) | The change justification and approval record on every document revision and process change |
| IR.L2-3.6.1–3 (incident handling) | CAPA can hold an investigation and corrective-action record once you have declared an incident |
| PS.L2-3.9.2 (personnel actions) | Account deactivation, and the audit record of group and permission changes |
| CA.L2-3.12.1–4, SI.L2-3.14.6–7 (assessment, monitoring) | The audit trail and access records above |

## Organisation and hosting responsibilities

These are not the software's job, and uqmes does not perform or schedule them:

- **Your organisation:** security awareness training (AT), incident response
  planning and reporting (IR), personnel screening and offboarding (PS),
  physical protection (PE), risk assessment (RA), security assessment, the SSP
  and the POA&M (CA), and the review of logged events (AU 3.3.3).
- **Your identity provider:** multifactor authentication, password history,
  account lockout and lifecycle, where you use SSO.
- **Your hosting:** encryption at rest, TLS termination, network boundary and
  segmentation, host hardening and least functionality, maintenance (MA), flaw
  remediation and malicious-code protection (SI), backups, clock
  synchronisation, and sanitising storage at disposal (MP 3.8.3 — soft delete
  *retains* records on purpose and is not evidence for it).

**One application-level item belongs on your POA&M until you route it: 3.3.4.**
See [Audit & Accountability](#audit-accountability-au).

## Assessment Preparation

### For C3PAO Assessment

The application provides evidence for these assessment objectives:

**Access control:**
- Who has what: each group's members and permissions, and each user's groups and
  effective permissions, from the tenant group and user-permission endpoints
- Role definitions: `GROUP_PRESETS` in `Tracker/presets.py`; the enforcement
  classes that read them are in `Tracker/permissions.py`

**Audit:**
- The audit trail at `/api/auditlog/`, filterable by actor, record type, record
  and action — including group permission and membership changes
- Access records for document views and downloads, report generation, data
  exports and AI queries
- Superuser and staff accounts can also read the log in the Django admin at
  `/admin/auditlog/logentry/`

**Configuration:**
- Version history for documents and processes
- Approval requests and responses, with signer, method, meaning and IP
- Change justifications on document revisions and process change requests

### Management commands

```bash
# Database integrity of the permission table: duplicate and orphaned
# permissions (read-only unless --fix)
python manage.py check_permissions

# Reconcile preset-backed groups to their preset, adding and revoking
# (--dry-run to preview)
python manage.py sync_tenant_permissions
```

!!! warning "`setup_audit_triggers` is not a status command"
    It **drops and recreates** the immutability triggers on the audit tables.
    It is idempotent and safe to re-run, but it is a DDL command, not a
    read-only check — don't reach for it to show an assessor that the
    triggers are in place. To *inspect* them, query `pg_trigger` directly, or
    show that `setup_database` runs the command on every start or release.

### Key Files for Assessors

| Domain | Files |
|--------|-------|
| Access Control | `Tracker/presets.py` (role definitions), `Tracker/permissions.py` (enforcement), `Tracker/authentication.py` (tenant membership, token expiry), `Tracker/middleware.py` (tenant binding) |
| Audit | `PartsTrackerApp/settings.py` (`AUDITLOG_*`), `Tracker/services/core/access_log.py`, `Tracker/management/commands/setup_audit_triggers.py` |
| Configuration | `Tracker/models/core.py` (`SecureModel` versioning), `Tracker/services/core/approval_lock.py` |
| Media Protection | `Tracker/models/core.py` (`ClassificationLevel`), `Tracker/services/export_control.py` |
| System Protection | `Tracker/management/commands/setup_rls.py`, `Tracker/middleware.py` |

## SPRS Score Calculation

There is no application-level SPRS subtotal to quote here. SPRS scores the 110
NIST 800-171 practices as the *assessed organization* implements them, so no
vendor can score a slice of it on your behalf. Use
[What the software does, by domain](#what-the-software-does-by-domain) as an
input to your own scoring.

## Scoping Guidance

### CUI Assets in This Application

| Asset Type | CUI Handling | Protection |
|------------|--------------|------------|
| Documents | May contain CUI | Classification, export-control flags, access records |
| Parts data | May reference CUI specs | Tenant isolation, role-based access, export-control flags where set |
| Quality reports | May reference CUI | Role-based access |
| CAPA records | May discuss CUI issues | Role-based access |

## Related Documentation

- [NIST 800-171](nist-800-171.md) - Detailed control mapping
- [Export Controls (ITAR)](export-controls.md) - Defense article handling
- [Audit Trails](audit-trails.md) - Logging details
- [Compliance Overview](overview.md) - All frameworks
