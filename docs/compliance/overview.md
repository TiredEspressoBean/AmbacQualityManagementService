# Compliance Overview

How uqmes supports the standards **your organisation** is assessed against:
defense, aerospace, automotive and general manufacturing.

!!! important "Software is never the certified party"
    There is no such thing as ISO 9001 certified software, and uqmes does not
    hold — and cannot hold — an ISO 9001, AS9100D or IATF 16949 certificate.
    Those standards certify a **quality management system run by an
    organisation**, assessed by an accredited certification body that audits
    your people, your processes and your records. The same is true of CMMC: a
    defense contractor is assessed, not a vendor's application.

    A vendor claiming its product is “ISO 9001 certified” is either describing
    *its own company's* certificate — which says nothing about the software —
    or misrepresenting the standard.

    So these pages do not describe a status uqmes holds. They answer the two
    questions that are actually useful when you are the one being audited:
    **which clauses can I point at this software for, and what must I satisfy
    myself?**

## Standards in scope

| Standard | Domain |
|----------|--------|
| **AS9100D** | Aerospace quality management |
| **IATF 16949** | Automotive quality management |
| **ISO 9001** | General quality management |
| **CMMC** | Defense contractor cybersecurity |
| **NIST 800-171** | Controlled Unclassified Information |
| **ITAR / EAR** | Export control |

!!! note "Not in scope"
    Medical-device and pharmaceutical regulation — **21 CFR Part 11**,
    **ISO 13485**, **EU MDR** — are not design goals, and no conformance with
    them is claimed or assessed anywhere in this documentation.

!!! tip "Demo: Compliance Evidence"
    In demo mode, you can see compliance features in action:

    - **Audit trail**: View CAPA-2024-003's complete history with user attribution and timestamps
    - **Approval workflows**: APR-2024-0015 shows multi-step approval with electronic signatures
    - **RBAC enforcement**: Customer Tom Bradley can only view Midwest Fleet orders (tenant isolation)
    - **Training compliance**: Dave Wilson blocked from Flow Testing due to expired certification
    - **Calibration alerts**: Torque Wrench TW-25 flagged as overdue, preventing use at Assembly step
    - **Document control**: WI-001-A shows version history and approval workflow

## Audience

This documentation is intended for:
- IT administrators preparing for audits
- Compliance officers mapping system capabilities to requirements
- Technical evaluators assessing system fit

## Scope & Boundaries

### Application-Level Controls (Covered)

This analysis covers the **software application layer**:

| Capability | Implementation |
|------------|----------------|
| Audit logging | django-auditlog with database triggers |
| Role-based access control | 15 built-in role presets, granular permissions |
| Data validation | DRF serializers with field-level validation |
| Session management | Django session framework |
| Approval workflows | ApprovalRequest/Response models |
| Document versioning | SecureModel with version tracking |
| Tenant isolation | Row-Level Security on all tables |

### Infrastructure Controls (Customer Responsibility)

The following depend on deployment configuration and are **not application features**:

- Encryption at rest (database/disk level)
- Encryption in transit (TLS/load balancer)
- Network segmentation/firewalls
- Physical security
- Backup/disaster recovery
- Host-level hardening
- Key management (HSM/KMS)
- MFA enforcement (IdP configuration)

## Compliance Readiness Matrix

!!! warning "These are not readiness scores"
    A percentage is the wrong shape for this question, because **you** are the
    assessed party. A control satisfied by your facility, identity provider or
    host is still satisfied — just not by this software, and no vendor can
    score your compliance on your behalf.

    The table below says what the application is the *mechanism* for, which is
    the input to your own assessment, not a substitute for it.

| Framework | Target Industry | What the application covers | What it is not the mechanism for |
|-----------|-----------------|------------------------------|-----------------------------------|
| [NIST 800-171](nist-800-171.md) | Defense (CUI) | 41 of 110 controls implemented, 8 partial | 61 controls live in your facility, IdP, host or process |
| [CMMC Level 2](cmmc.md) | DoD Contractors | Same 110 controls, mapped by domain | Whole domains — training, maintenance, physical, risk assessment |
| [ISO 9001:2026](iso9001.md) | General | All 28 subclauses are mapped. Clauses 7–10 are where the software is the mechanism: documented information, production control, traceability, nonconformity, CAPA | Clauses 4–6 are mostly management activities — context, leadership, policy, objectives, risk. The page lists them and marks them yours |
| [AS9100D](as9100.md) | Aerospace | ISO 9001 plus configuration management, FAI, part traceability | AS9102 FAI form output; authentication of independent-distributor material |
| [IATF 16949](iatf-16949.md) | Automotive | ISO 9001 plus SPC, control plans, layered audits | **MSA / Gage R&R — not modelled at all.** PPAP and FMEA are partial: the data exists, the submission artifacts do not. See the page for which elements |
| [ITAR](export-controls.md) | Defense/Export | Classification, access gating on `us_person` / `itar_authorized` | License tracking; the export decision itself |

> **Note**: These counts are application-level only. Full compliance requires
> infrastructure configuration and organizational processes that no application
> supplies. SOC 2 is not covered on this page: there is no control mapping
> behind it yet.

## Key Compliance Strengths

### 1. Comprehensive Audit Trail

- **django-auditlog** with `AUDITLOG_INCLUDE_ALL_MODELS=True`
- **Immutable logs**: PostgreSQL triggers block UPDATE/DELETE on audit tables
- **PermissionChangeLog**: Tracks all permission grants/revocations
- **Document access logging**: `Documents.log_access()` captures user, IP, classification

**Key files**: `PartsTrackerApp/settings.py`, `Tracker/models/core.py`, `Tracker/management/commands/setup_audit_triggers.py`

### 2. Multi-Layer Tenant Isolation

- **Application layer**: `TenantMiddleware` sets RLS context
- **Database layer**: Row-Level Security policies on 129 listed tenant-scoped tables
- **API layer**: `TenantScopedMixin` filters all querysets

**Key files**: `Tracker/middleware.py`, `Tracker/management/commands/setup_rls.py`, `Tracker/viewsets/base.py`

!!! note "RLS is opt-in, not automatic"
    Row-Level Security is applied by the `setup_rls` management command (also
    run by `setup_database` unless `--skip-rls` is passed) — **not** by a
    migration. It therefore does not switch itself on when you deploy.

    It takes effect only when all three hold:

    1. `ENABLE_RLS=true` in settings
    2. Django connects as the `partstracker_app` role, not a superuser —
       RLS does not apply to superusers
    3. `TenantMiddleware` sets `app.current_tenant_id` on the connection

    Treat RLS as defence-in-depth beneath the application-level scoping
    (`SecureModel` / `SecureManager` / `TenantMiddleware`), which is what
    enforces isolation on every request regardless.


### 3. Granular RBAC

15 predefined groups with module-based permissions:

| Group | Primary Access |
|-------|----------------|
| System Admin | Platform-level: all tenants |
| Tenant Admin | Full access within one organization |
| QA Manager | Quality reports, dispositions, CAPA closure, approvals |
| QA Inspector | Inspections, measurements, CAPA initiation |
| Production Manager | Orders, work orders, parts, scheduling |
| Operator | Part tracking, data recording |
| Shift Lead | Operator plus FPI sign-off, decision points, training overrides |
| Planner | Release, promised dates, the solve and its calendars |
| Engineering | Processes, routings, specs, technical documents |
| Purchasing | Supplier qualification, expected receipts, sourcing |
| Receiving | Incoming receipt and inspection, holds, put-away |
| Shipping | Shipments, packing lists and CoCs, subcontract send-out |
| Document Controller | Full document control, all classifications |
| Auditor | Read-only across the tenant; no write permission |
| Customer | Read-only portal access to their own orders |

!!! note "Separation of duties is the design"
    Many roles can *raise* a nonconformance, a CAPA or a supplier qualification;
    only **QA Manager** can approve one. See [Role
    Comparison](../roles/index.md#what-tells-the-roles-apart).

**Key files**: `Tracker/permissions.py`

### 4. Full CAPA System

- **5 CAPA types**: Corrective, Preventive, Customer Complaint, Internal Audit, Supplier
- **RCA methods**: 5 Whys, Fishbone (6M categories)
- **Task management**: Containment, Corrective, Preventive tasks
- **Verification workflow**: Effectiveness confirmation with auto-closure

**Key files**: `Tracker/models/qms.py` (CAPA, CapaTasks, RcaRecord, CapaVerification)

### 5. Approval Workflows

- **ApprovalTemplate**: Define sequential/parallel approval flows
- **ApprovalRequest/Response**: Track individual approvals
- **Signature capture**: Password verification, optional handwritten
- **Self-approval detection**: `self_approved` flag for audit

**Key files**: `Tracker/models/core.py`, `Tracker/signals.py`

### 6. Document Control

- **Version control**: `create_new_version()` with history
- **Status workflow**: DRAFT → UNDER_REVIEW → APPROVED → RELEASED → OBSOLETE
- **Classification levels**: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, SECRET
- **Approval integration**: Document types link to approval templates

**Key files**: `Tracker/models/core.py` (Documents, DocumentType)

### 7. SPC Implementation

- **Chart types**: X̄-R, X̄-S, I-MR
- **Capability indices**: Cp, Cpk, Pp, Ppk
- **Baseline management**: Freeze/update with audit trail
- **Control rules**: Western Electric rules for out-of-control detection

**Key files**: `Tracker/models/spc.py`

### 8. Training & Calibration

- **TrainingRecord**: Completion tracking, expiration dates, trainer attribution
- **CalibrationRecord**: Due dates, results, certificate numbers
- **Dashboard views**: Training and calibration status at a glance

**Key files**: `Tracker/models/qms.py`

## Known Gaps & Limitations

### Priority 0 (Critical for Target Markets)

| Gap | Frameworks Affected | Status |
|-----|---------------------|--------|
| AS9102 FAI PDF Templates | AS9100D | Data ready, needs PDF generation |

### Priority 1 (Important for Compliance)

| Gap | Frameworks Affected | Notes |
|-----|---------------------|-------|
| MSA/Gage R&R Records | IATF 16949 | Need measurement system analysis model |
| Supplier Management | ISO 9001, AS9100D, IATF 16949 | AVL, qualification workflow, scorecards |
| Customer Property Tracking | ISO 9001 8.5.3 | Customer-owned tooling/materials |
| PPAP Module | IATF 16949 | PSW generation, submission tracker |

### Priority 2 (Enhancement)

| Gap | Frameworks Affected | Notes |
|-----|---------------------|-------|
| Compliance Reporting | NIST, SOC 2 | Automated audit report generation |
| Counterfeit Parts Detection | AS9100D 8.1.4 | Authentication workflow |
| User Inactivity Detection | NIST 3.5.6 | Automated account disable |

## Evidence Reference for Auditors

| Capability | Primary Files |
|------------|---------------|
| Audit Logging | `PartsTrackerApp/settings.py`, `Tracker/models/core.py` |
| RBAC/Permissions | `Tracker/permissions.py` |
| Tenant Isolation | `Tracker/middleware.py`, `Tracker/management/commands/setup_rls.py` |
| Document Control | `Tracker/models/core.py` (Documents class) |
| Approval Workflows | `Tracker/models/core.py`, `Tracker/signals.py` |
| CAPA System | `Tracker/models/qms.py`, `Tracker/signals.py` |
| SPC | `Tracker/models/spc.py` |
| Training/Calibration | `Tracker/models/qms.py` |
| Export Controls | `Tracker/models/core.py`, `Tracker/models/mes_lite.py` |

## Framework-Specific Documentation

- [NIST 800-171](nist-800-171.md) - CUI protection requirements
- [CMMC Level 2](cmmc.md) - DoD certification requirements
- [ISO 9001:2026](iso9001.md) - General QMS requirements
- [AS9100D](as9100.md) - Aerospace requirements
- [IATF 16949](iatf-16949.md) - Automotive requirements
- [Export Controls (ITAR/EAR)](export-controls.md) - Defense article controls

## Cross-Cutting Features

- [Audit Trails](audit-trails.md) - Logging and traceability
- [Electronic Signatures](signatures.md) - Attributable approvals and records
- [Document Control](document-control.md) - Controlled document management
- [Compliance Reports](reports.md) - Audit report generation
