# Compliance Overview

Technical compliance analysis of Ambac Tracker against major regulatory frameworks for defense, aerospace, automotive, and general manufacturing.

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
| Role-based access control | 9 permission groups, granular permissions |
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

| Framework | Target Industry | App-Level Readiness | Key Gaps |
|-----------|-----------------|---------------------|----------|
| [NIST 800-171](nist-800-171.md) | Defense (CUI) | **100%** | None (organizational processes are customer responsibility) |
| [CMMC Level 2](cmmc.md) | DoD Contractors | **100%** | None (organizational processes are customer responsibility) |
| [ISO 9001:2015](iso9001.md) | General | **92%** | Customer property tracking, supplier scorecards |
| [AS9100D](as9100.md) | Aerospace | **80%** | AS9102 FAI PDF templates, counterfeit parts workflow |
| [IATF 16949](iatf-16949.md) | Automotive | **70%** | MSA/Gage R&R, PPAP module, FMEA data model |
| [ITAR](export-controls.md) | Defense/Export | **89%** | License tracking model |
| SOC 2 Type II | SaaS/Cloud | **80%** | Anomaly detection (infrastructure) |

> **Note**: Percentages reflect application-level controls only. Full compliance requires proper infrastructure configuration and organizational processes.

## Key Compliance Strengths

### 1. Comprehensive Audit Trail

- **django-auditlog** with `AUDITLOG_INCLUDE_ALL_MODELS=True`
- **Immutable logs**: PostgreSQL triggers block UPDATE/DELETE on audit tables
- **PermissionChangeLog**: Tracks all permission grants/revocations
- **Document access logging**: `Documents.log_access()` captures user, IP, classification

**Key files**: `settings.py`, `Tracker/models/core.py`, `Tracker/management/commands/setup_audit_triggers.py`

### 2. Multi-Layer Tenant Isolation

- **Application layer**: `TenantMiddleware` sets RLS context
- **Database layer**: Row-Level Security policies on 97 tables
- **API layer**: `TenantScopedMixin` filters all querysets

**Key files**: `Tracker/middleware.py`, `Tracker/migrations/0003_enable_rls.py`, `Tracker/viewsets/base.py`

### 3. Granular RBAC

9 predefined groups with module-based permissions:

| Group | Primary Access |
|-------|----------------|
| Admin | Full system access |
| QA_Manager | Quality reports, dispositions, CAPA closure |
| QA_Inspector | Inspections, measurements, CAPA initiation |
| Production_Manager | Orders, work orders, parts |
| Production_Operator | Part tracking, data recording |
| Document_Controller | Full document control, all classifications |
| Engineering | Technical documents, design CAPAs |
| Supplier_Quality | Incoming inspection, supplier CAPAs |
| Customer | Read-only portal access |

**Key files**: `Tracker/permissions.py`, `Tracker/services/permission_service.py`

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
| Audit Logging | `settings.py`, `Tracker/models/core.py` |
| RBAC/Permissions | `Tracker/permissions.py`, `Tracker/services/permission_service.py` |
| Tenant Isolation | `Tracker/middleware.py`, `Tracker/migrations/0003_enable_rls.py` |
| Document Control | `Tracker/models/core.py` (Documents class) |
| Approval Workflows | `Tracker/models/core.py`, `Tracker/signals.py` |
| CAPA System | `Tracker/models/qms.py`, `Tracker/signals.py` |
| SPC | `Tracker/models/spc.py` |
| Training/Calibration | `Tracker/models/qms.py` |
| Export Controls | `Tracker/models/core.py`, `Tracker/models/mes_lite.py` |

## Framework-Specific Documentation

- [NIST 800-171](nist-800-171.md) - CUI protection requirements
- [CMMC Level 2](cmmc.md) - DoD certification requirements
- [ISO 9001:2015](iso9001.md) - General QMS requirements
- [AS9100D](as9100.md) - Aerospace requirements
- [IATF 16949](iatf-16949.md) - Automotive requirements
- [Export Controls (ITAR/EAR)](export-controls.md) - Defense article controls

## Cross-Cutting Features

- [Audit Trails](audit-trails.md) - Logging and traceability
- [Electronic Signatures](signatures.md) - 21 CFR Part 11 compliance
- [Document Control](document-control.md) - Controlled document management
- [Compliance Reports](reports.md) - Audit report generation
