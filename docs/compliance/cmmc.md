# CMMC (Cybersecurity Maturity Model Certification)

DoD cybersecurity certification requirements for defense contractors.

!!! info "Who this page is for"
    **uqmes is not the assessed party.** CMMC certifies *defense
    contractors*. If you handle CUI under a DoD contract, you are assessed —
    and uqmes is one system inside the boundary you are assessed on.

    So this page is not a compliance claim. It answers two questions for a
    customer building their System Security Plan:

    1. Which practices can you point at uqmes for, and with what evidence?
    2. Which must you satisfy yourself, because no application can do it?

    A control marked *not provided* below is usually not a shortcoming in the
    software — it is a control that lives in your facility, your identity
    provider, or your hosting platform. The exceptions are called out as
    such.

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

## Level 2 Domain Summary

CMMC Level 2 maps to NIST 800-171 with 110 practices across 14 domains:

| Domain | Practices | Implemented | N/A |
|--------|-----------|-------------|-----|
| Access Control (AC) | 22 | 15 | 7 |
| Awareness & Training (AT) | 3 | 0 | 3 |
| Audit & Accountability (AU) | 9 | 6 | 3 |
| Configuration Management (CM) | 9 | 3 | 6 |
| Identification & Authentication (IA) | 11 | 4 | 7 |
| Incident Response (IR) | 3 | 0 | 3 |
| Maintenance (MA) | 6 | 0 | 6 |
| Media Protection (MP) | 9 | 3 | 6 |
| Personnel Security (PS) | 2 | 0 | 2 |
| Physical Protection (PE) | 6 | 0 | 6 |
| Risk Assessment (RA) | 3 | 0 | 3 |
| Security Assessment (CA) | 4 | 0 | 4 |
| System & Comms Protection (SC) | 16 | 3 | 13 |
| System & Info Integrity (SI) | 7 | 0 | 7 |

The **Implemented** column counts practices where uqmes is the mechanism —
where you can point an assessor at the software. It is not a readiness score,
and a low number is not a criticism of the product: most of CMMC is about
facilities, people and networks.

!!! warning "Don't read these as satisfied controls"
    An earlier revision showed **100% (48/48)**, on the reasoning that
    partial controls were now counted as implemented. That inflates exactly
    the number a customer would most want to trust.

    Each domain below uses three markers:

    | | Meaning |
    |---|---------|
    | ✅ **Provides** | uqmes is the mechanism; cite it directly |
    | ⚠️ **Supports** | uqmes supplies part of it — evidence, or a setting you must configure. Say what you did, not just that the feature exists |
    | ➖ **Not the application's layer** | Satisfy this in your facility, IdP, host or process |

    Where a practice is a genuine shortcoming in the software rather than a
    scope boundary, it says **gap** in the row. There is one: AU.L2-3.3.4.

## What CMMC Level 2 Requires

### CUI Protection
- Access limited to authorized users
- Data classified and marked
- Audit trail of all access
- Encryption in transit and at rest

### System Security
- Role-based access control
- Session management
- Authentication controls
- Change management

### Incident Handling
- Incident detection capability
- Response procedures
- Reporting mechanisms

## Application Capabilities for CMMC

### Access Control (AC)

These are the practices the application contributes to. AC has 22 practices
in total; the rest are organisational or network controls that no application
can satisfy on its own — see [Shared Responsibility](#shared-responsibility-model).

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| AC.L2-3.1.1 | User authentication required | ✅ | `TenantMiddleware` + `IsAuthenticated` on every endpoint |
| AC.L2-3.1.2 | Function-level authorization | ✅ | 12 role presets (`GROUP_PRESETS`) over Django model permissions, plus per-action gates |
| AC.L2-3.1.3 | CUI flow control | ✅ | Five classification levels — Public, Internal, Confidential, Restricted, Secret — filtered in `SecureManager.for_user()` |
| AC.L2-3.1.4 | Separation of duties | ✅ | Distinct roles, plus `self_verified` flags that record when a CAPA or RCA was verified by its own conductor |
| AC.L2-3.1.5 | Least privilege | ✅ | Presets grant the minimum per role; the Customer role is read-only and scoped to its own company |
| AC.L2-3.1.7 | Privilege escalation prevention | ✅ | Permission checks on every action; a user cannot grant themselves a permission |
| AC.L2-3.1.12 | Remote access monitoring | ⚠️ | IP is captured at signing and on invitations, not on every session. There is no session-level remote-access monitor |
| AC.L2-3.1.22 | Public posting control | ✅ | Classification gates what a Customer-role user can retrieve |

### Audit & Accountability (AU)

All nine AU practices are listed below, including the ones this application
does not satisfy. A control matrix is only useful if the gaps are in it.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| AU.L2-3.3.1 | Audit record creation | ✅ | django-auditlog on all models; pgAudit at the database |
| AU.L2-3.3.2 | User attribution | ✅ | Actor, timestamp and IP on every record |
| AU.L2-3.3.3 | Review and update logged events | ⚠️ | Procedural. The event set is fixed in code; nothing in the application prompts or records a periodic review of *what* is logged |
| AU.L2-3.3.4 | Alert on audit logging failure | ❌ | **Gap — a real one, in the software.** Audit-write failures are caught and logged as a warning so the request survives: availability over alerting. Nothing notifies anyone, so uqmes can be losing audit records while appearing healthy. Raise this with us rather than writing around it |
| AU.L2-3.3.5 | Audit correlation | ⚠️ | Both layers timestamp in UTC and record the actor, which makes correlation possible by hand. No tooling correlates them |
| AU.L2-3.3.6 | Reduction and report generation | ✅ | The audit log is filterable by actor, content type, object and action, with search and ordering; export is permission-gated on `export_auditlog` |
| AU.L2-3.3.7 | Authoritative timestamps | ✅ | Server-side, `TIME_ZONE = 'UTC'` with `USE_TZ`. Clock synchronisation itself is the host's responsibility, not the application's |
| AU.L2-3.3.8 | Audit protection | ✅ | PostgreSQL triggers block UPDATE/DELETE on seven audit tables, superusers included (`setup_audit_triggers`, run by `setup_database` from the app container, so present on every deployment). pgAudit adds statement-level logging on the self-hosted Compose stack only — a managed Postgres does not have it |
| AU.L2-3.3.9 | Audit access restriction | ✅ | `view_auditlog` / `view_logentry` for reading, `export_auditlog` for extraction; the log viewset is read-only and tenant-scoped |

!!! warning "3.3.4 is the one to fix before an assessment"
    An assessor will ask what happens when audit logging itself fails. The
    current answer is that the request proceeds and a warning goes to the
    application log — which means the system can be losing audit records
    while appearing healthy. Availability over alerting is a defensible
    engineering choice; it is not a defensible answer to 3.3.4.

### Identification & Authentication (IA)

Eleven practices. Several are deliberately delegated to the identity provider
rather than implemented here — which is a valid answer for an assessment, but
only if the IdP is in scope and configured.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| IA.L2-3.5.1 | Identify users and devices | ✅ | Unique account per person; no shared logins by design |
| IA.L2-3.5.2 | Authenticate before access | ✅ | Session or SSO; every endpoint requires an authenticated user |
| IA.L2-3.5.3 | Multifactor authentication | ➖ | Yours via the IdP. Enable SSO and enforce MFA in Microsoft Entra; cite the IdP, not uqmes. **A password-only deployment cannot evidence this at all** |
| IA.L2-3.5.4 | Replay-resistant authentication | ⚠️ | Satisfied via the IdP's OIDC flow when SSO is used; local password login is session-cookie based |
| IA.L2-3.5.5 | Prevent identifier reuse | ➖ | Yours, as an account-administration practice. uqmes deactivates rather than deletes, which preserves history but does not itself block reuse of an address |
| IA.L2-3.5.6 | Disable identifiers after inactivity | ⚠️ | `is_active` and bulk activate/deactivate exist; nothing disables an account automatically on inactivity |
| IA.L2-3.5.7 | Password complexity | ⚠️ | Django validators: similarity to user attributes, minimum length, common-password list, all-numeric rejection. No character-class rule |
| IA.L2-3.5.8 | Prohibit password reuse | ➖ | Yours via the IdP. uqmes keeps no password history, so a local-password deployment cannot evidence this |
| IA.L2-3.5.9 | Temporary password on first use | ⚠️ | Invitations carry a signup link rather than a temporary password, so the practice does not map cleanly; there is no forced first-login change |
| IA.L2-3.5.10 | Cryptographically protected passwords | ✅ | Django's password hashers; passwords are never stored or transmitted in clear |
| IA.L2-3.5.11 | Obscure authentication feedback | ✅ | Django's default — failures do not reveal whether the account exists |

!!! warning "Set the session lifetime for your deployment"
    The default is 14 days with no expiry on browser close. That suits a
    personal machine and is a real exposure on a shared shop-floor tablet,
    where the next operator inherits the session — and in a quality system
    every record they create is attributed to whoever logged in, which makes
    it an attribution problem as much as an access one.

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

Four of nine practices have an application component. The rest — host
baseline inventory, software allow-listing, user-installed software — are
platform and organizational controls.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| CM.L2-3.4.1 | Baseline configurations | ✅ | Versioned records via `create_new_version()`; `SPCBaseline` freezes a control-chart baseline |
| CM.L2-3.4.3 | Change tracking and approval | ✅ | `ApprovalRequest` plus change control; every revision carries a required `change_justification` |
| CM.L2-3.4.5 | Access restrictions on change | ✅ | Row-level security (see SC below) and per-action permissions |
| CM.L2-3.4.6 | Least functionality | ➖ | Yours, at the host — disabled services and ports. Role permissions narrow what users can do but are not what this practice asks about |

### Media Protection (MP)

Media protection is mostly physical. Four of nine practices have an
application component.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| MP.L2-3.8.2 | Limit access to CUI | ✅ | Classification filtering in `SecureManager.for_user()` |
| MP.L2-3.8.3 | Sanitize media before disposal | ➖ | Yours. **Do not cite soft delete for this** — an earlier revision did, and it is backwards: soft delete *retains* the record, deliberately, so traceability survives. Sanitization applies to the storage when you dispose of it |
| MP.L2-3.8.4 | Mark media with CUI markings | ✅ | Five `ClassificationLevel` values carried on documents and shown in the UI |
| MP.L2-3.8.5 | Control access to media | ✅ | Classification-based permissions (`view_confidential_documents`, `view_restricted_documents`) |

### System & Communications Protection (SC)

Sixteen practices, most of them network and boundary controls. Five have an
application or deployment component.

| Practice | Capability | Status | Evidence |
|----------|------------|--------|----------|
| SC.L2-3.13.2 | Security architecture | ✅ | Row-level security over **129 listed tenant-scoped tables** (`setup_rls`, run by `setup_database`), using `FORCE ROW LEVEL SECURITY` so the policy binds the table owner too, not only unprivileged roles |
| SC.L2-3.13.4 | Prevent unauthorized transfer | ✅ | Tenant isolation via `SecureManager` and the RLS policies above |
| SC.L2-3.13.8 | Transmission confidentiality | ⚠️ | TLS terminates at the reverse proxy (`conf/Caddyfile`) self-hosted, or at the platform when hosted. Cite your TLS configuration; uqmes does not terminate TLS itself |
| SC.L2-3.13.15 | Communication authenticity | ✅ | CSRF protection with an explicit trusted-origin list; CORS allow-list rather than wildcard |
| SC.L2-3.13.16 | Protect CUI at rest | ➖ | Yours, via storage-level encryption on the host or volume. uqmes encrypts one field only (a stored integration `api_key`), so do not cite application-layer encryption for CUI |

### Domains with no application component

Four domains are wholly organizational or physical. The application cannot
satisfy them, and a zero here reflects scope rather than a gap in the
software:

| Domain | Practices | Why |
|--------|-----------|-----|
| **Awareness & Training (AT)** | 3 | Security awareness and role-based training are programmes, not features. The training module tracks *manufacturing* competence, not security awareness — do not offer it as evidence for AT |
| **Maintenance (MA)** | 6 | Physical and remote maintenance of the equipment the system runs on |
| **Physical Protection (PE)** | 6 | Facility access, visitor escort, physical media handling |
| **Risk Assessment (RA)** | 3 | Risk assessment and vulnerability scanning of the environment |

### Domains where the application contributes only evidence

These have an application component, but it is evidence for a process rather
than the control itself. Claiming them as implemented overstates it.

| Practice | Application provides | Organization must provide |
|----------|---------------------|---------------------------|
| **IR.L2-3.6.1–3** | CAPA gives a structured investigation and corrective-action record, with root-cause analysis and effectiveness verification | Incident *classification*, reporting timelines, and the judgement that something is a security incident rather than a quality one |
| **PS.L2-3.9.1–2** | `is_active`, bulk deactivation, and an audit trail of permission changes | Screening before access, and the offboarding process that triggers deactivation |
| **CA.L2-3.12.1–4** | `PermissionChangeLog` and the audit trail as evidence for review | The security assessment, the SSP, and the POA&M themselves |
| **SI.L2-3.14.1–7** | Structured error handling; scoped rate limiting on abuse-prone unauthenticated endpoints | Flaw remediation, malicious-code protection, and monitoring — none of which live in the application |

!!! note "CAPA is not an incident response plan"
    CAPA is a genuinely good fit for tracking a security incident once one has
    been declared, and it is worth using that way. But IR asks for detection,
    classification and reporting, and the application does none of those.

## Shared Responsibility Model

No application-level POA&M items are required. The following are organizational responsibilities:

| Practice | Application Provides | Organization Provides |
|----------|---------------------|----------------------|
| IA.L2-3.5.6 | `is_active` field, bulk activate/deactivate | User lifecycle management via IdP/HR |
| AU.L2-3.3.3 | Audit logs via API, admin interface | Compliance review procedures |
| AU.L2-3.3.5 | Audit data accessible via API | SIEM integration, log forwarding |
| AU.L2-3.3.6 | Excel export, API filtering | Report formatting for auditors |
| AC.L2-3.1.20 | Integration logging (HubSpot sync) | External system inventory in SSP |
| CM.L2-3.4.4 | `change_justification`, approval workflow | Security impact review process |
| IR.L2-3.6.2 | CAPA system for incident tracking | Security incident classification |
| CA.L2-3.12.3 | PermissionChangeLog, audit trail | Security monitoring procedures |

## Assessment Preparation

### For C3PAO Assessment

The application provides evidence for these assessment objectives:

**Access Control Evidence:**
- User permission reports (who has access to what)
- Role group definitions (`Tracker/permissions.py`)
- Tenant isolation proof (RLS policies)

**Audit Evidence:**
- Full audit log export
- Permission change history
- Document access logs

**Configuration Evidence:**
- Version history for documents/processes
- Approval workflow records
- Change justification records

### Evidence Collection

**Audit logs:** Access via Django admin at `/admin/auditlog/logentry/` or query the database directly.

**Permission report:** Run `python manage.py check_permissions` to verify permission structure.

**Available management commands:**
```bash
# Check permission structure
python manage.py check_permissions

# Setup/update permissions
python manage.py setup_permissions

# View audit trigger status
python manage.py setup_audit_triggers
```

### Key Files for Assessors

| Domain | Files |
|--------|-------|
| Access Control | `Tracker/permissions.py`, `Tracker/middleware.py` |
| Audit | `PartsTrackerApp/settings.py` (AUDITLOG), `Tracker/models/core.py` |
| Configuration | `Tracker/models/core.py` (SecureModel) |
| Media Protection | `Tracker/models/core.py` (ClassificationLevel) |
| System Protection | `Tracker/management/commands/setup_rls.py`, `Tracker/middleware.py` |

## Shared Responsibility Model

### Application Provides
- User authentication enforcement
- Role-based access control
- Audit logging (immutable)
- Document classification
- Tenant isolation
- Session management
- Approval workflows

### Customer Must Provide
- MFA enforcement (via IdP)
- Encryption at rest (database)
- Encryption in transit (TLS)
- Network security
- Physical security
- Backup encryption
- Vulnerability scanning
- Security awareness training
- Incident response procedures

## SPRS Score Calculation

For your Supplier Performance Risk System (SPRS) score:

| Category | Max Points | Estimated Score |
|----------|------------|-----------------|
| Application controls | 48 | 42 |
| Infrastructure controls | 62 | Customer-dependent |

Application-level contribution: **42/48 points** (partial controls counted as 0.5)

> **Note**: Final SPRS score depends on infrastructure configuration and organizational policies.

## Scoping Guidance

### CUI Assets in This Application

| Asset Type | CUI Handling | Protection |
|------------|--------------|------------|
| Documents | May contain CUI | Classification + access control |
| Parts data | May reference CUI specs | Tenant isolation |
| Quality reports | May reference CUI | Role-based access |
| CAPA records | May discuss CUI issues | Role-based access |

### Out of Scope

- Email systems
- File shares outside application
- Endpoint devices
- Network infrastructure

## Application Requirements for CUI Environments

When software is used in a CMMC-certified facility to process CUI, it must support the organization's security controls. These are the application-level expectations:

### Access Control (AC)

| Requirement | Purpose | This Application |
|-------------|---------|------------------|
| User authentication | Verify identity before access | ✅ Required login, session management |
| Role-based permissions | Limit access to need-to-know | ✅ 9 role groups, model-level permissions |
| Least privilege | Minimal default access | ✅ Customer role is view-only |
| Separation of duties | Prevent single-person control | ✅ Distinct roles, self-approval detection |
| Session timeout | Prevent unattended access | ✅ Configurable SESSION_COOKIE_AGE |

### Audit & Accountability (AU)

| Requirement | Purpose | This Application |
|-------------|---------|------------------|
| Action logging | Record who did what, when | ✅ django-auditlog on all models |
| User attribution | Trace actions to individuals | ✅ User ID, timestamp, IP on records |
| Log protection | Prevent tampering | ✅ PostgreSQL triggers block modification, superusers included |
| Log retention | Preserve for audit period | ✅ Logs retained indefinitely |

This summary covers the practices that are met. For the full nine, including
the **3.3.4 gap** on alerting when audit logging itself fails, see [Audit &
Accountability](#audit-accountability-au) above.

### Media Protection (MP)

| Requirement | Purpose | This Application |
|-------------|---------|------------------|
| CUI marking | Identify sensitive data | ✅ ClassificationLevel (5 levels) |
| Access restriction | Limit CUI to authorized users | ✅ Classification-based permissions |
| Controlled disposal | Audit trail on deletion | ✅ Soft delete with ArchiveReason |

### Configuration Management (CM)

| Requirement | Purpose | This Application |
|-------------|---------|------------------|
| Change control | Approve before implementing | ✅ ApprovalRequest workflow |
| Version history | Track what changed | ✅ SecureModel versioning |
| Baseline management | Freeze known-good configs | ✅ SPCBaseline, Process approval |

### System Protection (SC)

| Requirement | Purpose | This Application |
|-------------|---------|------------------|
| Boundary protection | Isolate tenant data | ✅ Row-Level Security (97 tables) |
| Unauthorized transfer prevention | Block cross-tenant access | ✅ TenantScopedMixin on all views |

### What the Application Does NOT Provide

These are infrastructure/organizational responsibilities:

| Control | Owner | Notes |
|---------|-------|-------|
| MFA enforcement | Identity Provider | Configure in SSO/IdP |
| Encryption at rest | Database/hosting | PostgreSQL TDE or disk encryption |
| Encryption in transit | Load balancer/proxy | TLS termination |
| Network segmentation | Infrastructure | Firewall rules |
| Vulnerability scanning | Security team | External scanning tools |
| Security awareness training | Organization | Training program |
| Incident response | Organization | IR procedures |
| Physical security | Facility | Badge access, etc. |

## Related Documentation

- [NIST 800-171](nist-800-171.md) - Detailed control mapping
- [Export Controls (ITAR)](export-controls.md) - Defense article handling
- [Audit Trails](audit-trails.md) - Logging details
- [Compliance Overview](overview.md) - All frameworks
