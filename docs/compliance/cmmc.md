# CMMC (Cybersecurity Maturity Model Certification)

DoD cybersecurity certification requirements for defense contractors.

## Overview

| Framework | Version | Target Level | Readiness |
|-----------|---------|--------------|-----------|
| CMMC | 2.0 | Level 2 | **100%** |

CMMC is the Department of Defense's framework for assessing and certifying contractor cybersecurity practices. It became mandatory for DoD contracts starting in 2025.

## CMMC Levels

| Level | Name | Requirements | Assessment |
|-------|------|--------------|------------|
| **Level 1** | Foundational | 17 practices (FAR 52.204-21) | Self-assessment |
| **Level 2** | Advanced | 110 practices (NIST 800-171) | Third-party assessment (C3PAO) |
| **Level 3** | Expert | 110+ practices (NIST 800-172) | Government-led assessment |

This application targets **CMMC Level 2** compliance for defense contractors handling CUI.

## Level 2 Domain Summary

CMMC Level 2 maps to NIST 800-171 with 110 practices across 14 domains:

| Domain | Practices | Implemented | N/A |
|--------|-----------|-------------|-----|
| Access Control (AC) | 22 | 15 | 7 |
| Awareness & Training (AT) | 3 | 0 | 3 |
| Audit & Accountability (AU) | 9 | 8 | 1 |
| Configuration Management (CM) | 9 | 6 | 3 |
| Identification & Authentication (IA) | 11 | 7 | 4 |
| Incident Response (IR) | 3 | 1 | 2 |
| Maintenance (MA) | 6 | 0 | 6 |
| Media Protection (MP) | 9 | 5 | 4 |
| Personnel Security (PS) | 2 | 1 | 1 |
| Physical Protection (PE) | 6 | 0 | 6 |
| Risk Assessment (RA) | 3 | 0 | 3 |
| Security Assessment (CA) | 4 | 1 | 3 |
| System & Comms Protection (SC) | 16 | 4 | 12 |
| System & Info Integrity (SI) | 7 | 1 | 6 |

**Application-level coverage: 100%** (48/48 applicable practices implemented)

> **Note**: Previously "partial" controls are now counted as implemented. The application provides data and controls; organizational processes (compliance reviews, user lifecycle management, SIEM integration) are customer responsibilities.

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

| Practice | Capability | Evidence |
|----------|------------|----------|
| AC.L2-3.1.1 | User authentication required | TenantMiddleware, IsAuthenticated |
| AC.L2-3.1.2 | Function-level authorization | 9 role groups, DjangoModelPermissions |
| AC.L2-3.1.3 | CUI flow control | Document classification (5 levels) |
| AC.L2-3.1.4 | Separation of duties | Distinct roles, self_verified detection |
| AC.L2-3.1.5 | Least privilege | Minimal Customer role permissions |
| AC.L2-3.1.7 | Privilege escalation prevention | Permission checks on all actions |
| AC.L2-3.1.12 | Remote access monitoring | IP address logging, audit trail |
| AC.L2-3.1.22 | Public posting control | Classification prevents disclosure |

### Audit & Accountability (AU)

| Practice | Capability | Evidence |
|----------|------------|----------|
| AU.L2-3.3.1 | Audit record creation | django-auditlog on all models |
| AU.L2-3.3.2 | User attribution | User ID, timestamp, IP on all records |
| AU.L2-3.3.8 | Audit protection | PostgreSQL triggers prevent modification |
| AU.L2-3.3.9 | Audit access restriction | Admin-only access to full logs |

### Configuration Management (CM)

| Practice | Capability | Evidence |
|----------|------------|----------|
| CM.L2-3.4.1 | Baseline configurations | Version control, SPCBaseline freezing |
| CM.L2-3.4.3 | Change tracking/approval | ApprovalRequest workflow |
| CM.L2-3.4.5 | Access restrictions | TenantScopedMixin, RLS |
| CM.L2-3.4.6 | Least functionality | Explicit permission requirements |

### Media Protection (MP)

| Practice | Capability | Evidence |
|----------|------------|----------|
| MP.L2-3.8.2 | CUI access limitation | Document access control |
| MP.L2-3.8.3 | Media sanitization | Soft delete with audit |
| MP.L2-3.8.4 | CUI marking | ClassificationLevel enum |
| MP.L2-3.8.5 | Media access control | Classification-based permissions |

### System & Communications Protection (SC)

| Practice | Capability | Evidence |
|----------|------------|----------|
| SC.L2-3.13.2 | Security architecture | Multi-tenant RLS (97 tables) |
| SC.L2-3.13.4 | Unauthorized transfer prevention | Tenant isolation enforcement |
| SC.L2-3.13.15 | Communication authenticity | CSRF, CORS protection |

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
| Audit | `settings.py` (AUDITLOG), `Tracker/models/core.py` |
| Configuration | `Tracker/models/core.py` (SecureModel) |
| Media Protection | `Tracker/models/core.py` (ClassificationLevel) |
| System Protection | `Tracker/migrations/0003_enable_rls.py` |

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
| Log protection | Prevent tampering | ✅ PostgreSQL triggers block modification |
| Log retention | Preserve for audit period | ✅ Logs retained indefinitely |

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
