# Modular Architecture Plan

> **STATUS: DRAFT - Not Yet Implemented**
> This is a design document for a future refactor. The modular architecture described below has not been built yet.

This document outlines the strategy for restructuring the PartsTracker application into a modular Django architecture that supports multiple deployment modes: SaaS (multi-tenant), Dedicated (single-tenant), and Air-Gapped (isolated/offline).

---

## Table of Contents

1. [Goals & Motivation](#goals--motivation)
2. [Current State](#current-state)
3. [Target Architecture](#target-architecture)
4. [Module Definitions](#module-definitions)
5. [Deployment Modes](#deployment-modes)
6. [Integration Pattern](#integration-pattern)
7. [Implementation Phases](#implementation-phases)
8. [Build & Packaging Pipeline](#build--packaging-pipeline)
9. [Risk Assessment](#risk-assessment)

---

## Goals & Motivation

### Business Goals

1. **Product Flexibility**: Sell different product configurations (QMS-only, MES-only, Full Platform)
2. **Enterprise Sales**: Support customers who need dedicated or air-gapped deployments
3. **Security Compliance**: Air-gapped customers can verify "only purchased code is installed"
4. **Clean Integrations**: Integrations (HubSpot, Salesforce, etc.) are truly optional

### Technical Goals

1. **Django App Separation**: Each module is a proper Django app that can be installed/uninstalled
2. **No Integration Leakage**: Core models have no knowledge of external integrations
3. **Single Codebase**: One repository serves all deployment modes
4. **Composable**: Mix and match modules per customer

### Market Alignment

The manufacturing software market is shifting from monolithic to composable architectures:

- Gartner predicts 60% of new MES deployments will use composable technology
- Best-in-class companies are 58% more likely to use integrated MES+QMS
- Modular pricing is becoming the industry standard

---

## Current State

### What's Good

- Code is already logically separated into files (`models/core.py`, `models/qms.py`, `models/mes_lite.py`, etc.)
- Integration registry pattern exists (`IntegrationService`, `IntegrationRegistry`)
- Multi-tenancy infrastructure in place (`SecureModel`, `TenantScopedMixin`)

### What Needs Work

1. **Single Django App**: Everything is in `Tracker.apps.TrackerConfig`
2. **Integration Leakage**: HubSpot fields directly on `Orders` and `Companies` models
3. **Circular Dependencies**: MES and QMS have tight coupling via signals and direct imports
4. **No Deployment Flexibility**: Same code ships everywhere regardless of what customer purchased

### HubSpot Leakage Example

Current state in `mes_lite.py`:
```python
class Orders(SecureModel):
    # HubSpot fields on core model
    current_hubspot_gate = models.ForeignKey("ExternalAPIOrderIdentifier", ...)
    hubspot_deal_id = models.CharField(max_length=60, ...)
    last_synced_hubspot_stage = models.CharField(...)
    hubspot_last_synced_at = models.DateTimeField(...)

    def save(self, *args, **kwargs):
        # HubSpot logic in save()
        if self._should_push_to_hubspot(old_stage):
            from Tracker.tasks import update_hubspot_deal_stage_task
            update_hubspot_deal_stage_task.delay(...)
```

This means:
- Every customer has HubSpot columns in their database
- `Orders` model imports HubSpot code
- Can't install/uninstall HubSpot independently

---

## Target Architecture

### Module Structure

```
PartsTracker/
├── core/                       # Always required
│   ├── apps.py                 # CoreConfig
│   ├── models.py               # Tenant, User, Companies, Documents, Approvals
│   ├── serializers.py
│   ├── viewsets.py
│   ├── events.py               # Django signals for loose coupling
│   └── migrations/
│
├── mes_lite/                   # Always required (foundation for MES concepts)
│   ├── apps.py                 # MesLiteConfig
│   ├── models.py               # Parts, PartTypes, Steps, WorkOrder, Equipment
│   └── migrations/
│
├── qms/                        # Optional module
│   ├── apps.py                 # QmsConfig
│   ├── models.py               # QualityReports, CAPA, Dispositions, ThreeDModel
│   └── migrations/
│
├── mes_full/                   # Optional module
│   ├── apps.py                 # MesFullConfig
│   ├── models.py               # SamplingRules, advanced process features
│   └── migrations/
│
├── dms/                        # Optional module (requires cloud)
│   ├── apps.py                 # DmsConfig
│   ├── models.py               # DocChunk, ChatSession
│   └── migrations/
│
├── spc/                        # Optional module
│   ├── apps.py                 # SpcConfig
│   ├── models.py               # SPCBaseline
│   └── migrations/
│
└── integrations/               # Optional, per-integration
    ├── hubspot/
    │   ├── apps.py             # HubSpotConfig
    │   ├── models.py           # HubSpotOrderLink, HubSpotCompanyLink
    │   ├── receivers.py        # post_save listeners
    │   ├── service.py          # API calls
    │   └── tasks.py            # Celery tasks
    ├── salesforce/
    └── erp_csv/
```

### Dependency Graph

```
                    ┌──────────────────────┐
                    │        core          │
                    │  (always required)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │      mes_lite        │
                    │  (always required)   │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │    qms    │       │ mes_full  │       │    spc    │
    │ (optional)│       │ (optional)│       │ (optional)│
    └───────────┘       └───────────┘       └───────────┘

    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │    dms    │       │  hubspot  │       │ erp_csv   │
    │ (optional)│       │ (optional)│       │ (optional)│
    │ cloud only│       │ cloud only│       │ air-gap ok│
    └───────────┘       └───────────┘       └───────────┘
```

---

## Module Definitions

### Core (Always Required)

**Purpose**: Foundation layer for multi-tenancy, users, documents, approvals, audit logging.

**Contains**:
- `Tenant` - SaaS customer isolation
- `User` - Extended Django user with tenant association
- `Companies` - Customer/company entities
- `Documents`, `DocumentType` - Universal document storage
- `ApprovalRequest`, `ApprovalResponse`, `ApprovalTemplate` - Approval workflows
- `SecureModel`, `SecureManager`, `SecureQuerySet` - Base classes with soft delete, versioning
- Export control fields and services (ITAR/EAR)

**Dependencies**: Django only

### MES Lite (Always Required)

**Purpose**: Minimal manufacturing vocabulary that other modules depend on.

**Contains**:
- `Parts`, `PartTypes` - Part definitions and instances
- `Steps`, `ProcessStep` - Process step definitions
- `Orders` - Customer orders
- `WorkOrder` - Internal production assignments
- `Equipment`, `EquipmentType` - Manufacturing equipment
- Basic status enums

**Dependencies**: `core`

### QMS (Optional)

**Purpose**: Quality management, defect tracking, CAPA, root cause analysis.

**Contains**:
- `QualityReports`, `QualityErrorsList` - Defect tracking
- `QuarantineDisposition` - Rework/scrap decisions
- `CAPA`, `CapaTasks`, `CapaVerification` - Corrective/preventive actions
- `RcaRecord`, `FiveWhys`, `Fishbone` - Root cause analysis
- `ThreeDModel`, `HeatMapAnnotations` - 3D model annotations
- `MeasurementResult` - Quality measurements

**Dependencies**: `core`, `mes_lite`

### MES Full (Optional)

**Purpose**: Advanced manufacturing features beyond basic tracking.

**Contains**:
- `SamplingRuleSet`, `SamplingRule` - Sampling strategies
- `SamplingTriggerState`, `SamplingAuditLog` - Sampling state management
- Advanced process routing and scheduling
- HubSpot deal stage mapping (if not separated to integration)

**Dependencies**: `core`, `mes_lite`

### DMS (Optional, Cloud Only)

**Purpose**: AI-powered document intelligence.

**Contains**:
- `DocChunk` - Document chunks with vector embeddings
- `ChatSession` - AI chat session history

**Dependencies**: `core`

**Requirements**: Cloud connectivity (AI APIs), pgvector extension

### SPC (Optional)

**Purpose**: Statistical process control.

**Contains**:
- `SPCBaseline` - Control limits for measurements

**Dependencies**: `core`, `mes_lite` (for MeasurementDefinition)

---

## Deployment Modes

### SaaS (Multi-Tenant)

**Characteristics**:
- Many customers on shared infrastructure
- All apps installed
- Feature flags control access per tenant
- Continuous deployment

**Configuration**:
```python
# settings/saas.py
DEPLOYMENT_TYPE = 'saas'
MULTI_TENANT = True

INSTALLED_APPS = CORE_APPS + [
    'qms',
    'mes_full',
    'dms',
    'spc',
    'integrations.hubspot',
    'integrations.salesforce',
    'integrations.erp_csv',
]
```

**Feature Control**:
```python
class Tenant(SecureModel):
    # Feature flags per tenant
    qms_enabled = models.BooleanField(default=True)
    mes_full_enabled = models.BooleanField(default=False)
    dms_enabled = models.BooleanField(default=False)
    hubspot_enabled = models.BooleanField(default=False)
```

**API Behavior**: Endpoints exist but return 403 if feature not enabled for tenant.

### Dedicated (Single-Tenant, Connected)

**Characteristics**:
- One customer per instance
- Only purchased modules installed
- Customer downloads updates from portal
- Internet connectivity available

**Configuration**:
```python
# settings/dedicated.py
DEPLOYMENT_TYPE = 'dedicated'
MULTI_TENANT = False

# Read from deployment manifest
manifest = yaml.safe_load(open('/etc/ambac/manifest.yaml'))
INSTALLED_APPS = CORE_APPS + manifest['modules']
```

**Manifest Example**:
```yaml
customer: "Acme Manufacturing"
product: "qms-standalone"
modules:
  - qms
integrations:
  - hubspot
license:
  key: "xxxx-xxxx-xxxx"
  expires: "2027-01-01"
  users: 25
```

**API Behavior**: Unpurchased endpoints return 404 (don't exist).

### Air-Gapped (Isolated, Offline)

**Characteristics**:
- No internet connectivity
- Only purchased modules installed
- All dependencies vendored
- Updates via physical media
- Security audit requirements

**Configuration**:
```python
# settings/airgapped.py
DEPLOYMENT_TYPE = 'airgapped'
MULTI_TENANT = False
AIRGAPPED = True

manifest = yaml.safe_load(open('/etc/ambac/manifest.yaml'))
INSTALLED_APPS = CORE_APPS + manifest['modules']

# Disable cloud features
AI_EMBED_ENABLED = False
CELERY_BROKER_URL = 'filesystem:///var/ambac/celery'
```

**Restrictions**:
- No `dms` (requires cloud AI)
- No `integrations.hubspot` (requires internet)
- No `integrations.salesforce` (requires internet)
- Only `integrations.erp_csv` (file-based) allowed

**API Behavior**: Unpurchased endpoints don't exist. Auditor can verify via `pip list`.

### Comparison Table

| Aspect | SaaS | Dedicated | Air-Gapped |
|--------|------|-----------|------------|
| Tenants | Many | One | One |
| Apps installed | All | Purchased | Purchased |
| Feature control | Runtime flags | Install-time | Install-time |
| Integrations | All available | Customer choice | Offline only |
| Updates | Continuous | Scheduled download | Physical media |
| DMS (AI) | Available | If purchased | Not available |
| HubSpot | Available | If purchased | Not available |

---

## Integration Pattern

### Principles

1. **Core models have zero integration knowledge**
2. **Integrations listen to events, don't inject code**
3. **Integration data lives in integration-owned models**
4. **Integrations can be installed/uninstalled cleanly**

### Pattern: OneToOne Link + post_save Receiver

**Integration-Owned Models**:
```python
# integrations/hubspot/models.py

class HubSpotOrderLink(models.Model):
    """Links an Order to HubSpot. Only exists if synced."""
    order = models.OneToOneField(
        'mes_lite.Orders',
        on_delete=models.CASCADE,
        related_name='hubspot'
    )
    deal_id = models.CharField(max_length=60, unique=True)
    current_stage = models.ForeignKey(HubSpotPipelineStage, null=True, on_delete=models.SET_NULL)
    last_pushed_stage = models.CharField(max_length=100, null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    skip_next_push = models.BooleanField(default=False)

    def should_push(self):
        if self.skip_next_push:
            return False
        if not self.current_stage:
            return False
        return str(self.current_stage.api_id) != str(self.last_pushed_stage)

    def mark_pushed(self):
        self.last_pushed_stage = self.current_stage.api_id if self.current_stage else None
        self.skip_next_push = False
        self.save(update_fields=['last_pushed_stage', 'skip_next_push'])
```

**Event Listener**:
```python
# integrations/hubspot/receivers.py

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender='mes_lite.Orders')
def on_order_saved(sender, instance, created, **kwargs):
    """When an Order is saved, sync to HubSpot if linked."""
    try:
        link = instance.hubspot
    except AttributeError:
        return
    except sender.hubspot.RelatedObjectDoesNotExist:
        return

    if link.should_push():
        from .tasks import push_order_to_hubspot
        push_order_to_hubspot.delay(link.id)
```

**Registration on App Load**:
```python
# integrations/hubspot/apps.py

class HubSpotConfig(AppConfig):
    name = 'integrations.hubspot'

    def ready(self):
        from . import receivers  # Registers signal handlers
```

### Result

- `Orders` model has no HubSpot code
- `post_save` fires automatically, HubSpot just listens
- If `integrations.hubspot` not in `INSTALLED_APPS`:
  - No HubSpot tables
  - No HubSpot receivers registered
  - No HubSpot code loaded
  - `order.hubspot` raises `AttributeError`

---

## Implementation Phases

### Phase 1: Django App Separation

**Effort**: 1-2 weeks
**Risk**: Medium (migrations are tricky)

| Task | Effort | Notes |
|------|--------|-------|
| Create app directories | 1 day | `core/`, `mes_lite/`, `qms/`, etc. |
| Move models to respective apps | 2-3 days | Follow existing file organization |
| Fix all imports | 1-2 days | IDE find/replace helps |
| Split/recreate migrations | 2-3 days | May need to squash first |
| Update URL routing | 0.5 day | Conditional includes |
| Update INSTALLED_APPS, test | 1-2 days | Verify everything works |

**Deliverable**: Apps can be installed/uninstalled independently.

### Phase 2: Integration Cleanup (HubSpot)

**Effort**: 2-3 days
**Risk**: Medium

| Task | Effort | Notes |
|------|--------|-------|
| Create `HubSpotOrderLink`, `HubSpotCompanyLink` | 0.5 day | New models |
| Write data migration | 0.5 day | Move existing HubSpot data |
| Add post_save receivers | 0.5 day | Listen for Order/Company changes |
| Update HubSpotService | 0.5 day | Use new models |
| Remove HubSpot fields from Orders | 0.5 day | Clean up core models |
| Test sync works | 0.5 day | End-to-end verification |

**Deliverable**: Clean integration pattern. Orders has no HubSpot knowledge.

### Phase 3: Deployment Configuration

**Effort**: 2-3 days
**Risk**: Low

| Task | Effort | Notes |
|------|--------|-------|
| Create settings files | 0.5 day | `saas.py`, `dedicated.py`, `airgapped.py` |
| Create manifest schema | 0.5 day | YAML format for customer config |
| Conditional INSTALLED_APPS | 0.5 day | Read from manifest |
| Feature flag fields on Tenant | 0.5 day | For SaaS mode |
| Feature flag middleware | 0.5 day | Check flags at runtime |
| Test each mode | 0.5 day | Verify behavior |

**Deliverable**: Same codebase supports all three deployment modes.

### Phase 4: Build & Packaging Pipeline

**Effort**: 3-5 days
**Risk**: Low-Medium

| Task | Effort | Notes |
|------|--------|-------|
| Bundle build script | 1 day | Assemble modules per manifest |
| Product manifests | 0.5 day | starter, qms, mes, full, etc. |
| CI: wheels per app | 1 day | Separate packages |
| CI: bundles per product | 1 day | Automated builds |
| Installer script | 1 day | For dedicated/airgapped |
| Test full cycle | 1 day | Build → install → run |

**Deliverable**: Automated builds for different customers/products.

### Timeline Summary

| Phase | Effort | Cumulative | Deliverable |
|-------|--------|------------|-------------|
| 1. App Separation | 1-2 weeks | 1-2 weeks | Modular Django apps |
| 2. Integration Cleanup | 2-3 days | ~2.5 weeks | Clean integration pattern |
| 3. Deployment Config | 2-3 days | ~3 weeks | Multi-mode support |
| 4. Build Pipeline | 3-5 days | ~4 weeks | Automated packaging |

**Total: 3-5 weeks for one developer**

---

## Build & Packaging Pipeline

### Source Structure

```
ambac-tracker/
├── apps/
│   ├── core/
│   ├── mes_lite/
│   ├── qms/
│   ├── mes_full/
│   ├── dms/
│   └── integrations/
├── settings/
│   ├── base.py
│   ├── saas.py
│   ├── dedicated.py
│   └── airgapped.py
├── manifests/
│   ├── products/
│   │   ├── starter.yaml
│   │   ├── qms-standalone.yaml
│   │   ├── mes-standalone.yaml
│   │   └── full-platform.yaml
│   └── customers/
│       └── {customer}.yaml
└── build/
    ├── build_packages.py
    └── build_bundle.py
```

### Product Manifests

```yaml
# manifests/products/qms-standalone.yaml
name: "QMS Standalone"
modules:
  - core
  - mes_lite
  - qms
integrations:
  allowed: [hubspot, salesforce, erp_csv]
settings: dedicated
```

```yaml
# manifests/products/full-airgapped.yaml
name: "Full Platform (Air-Gapped)"
modules:
  - core
  - mes_lite
  - qms
  - mes_full
  - spc
integrations:
  allowed: [erp_csv]
  blocked: [hubspot, salesforce, dms]
settings: airgapped
```

### Build Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCE (Git)                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CI/CD                                   │
│  1. Run tests per app                                          │
│  2. Build Python wheels per app                                │
│  3. Build Docker images (SaaS)                                 │
│  4. Build bundles per product                                  │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────────────────────┐
│   Wheels    │   │   Docker    │   │         Bundles             │
│  (per app)  │   │   Images    │   │      (per product)          │
├─────────────┤   ├─────────────┤   ├─────────────────────────────┤
│ core.whl    │   │ saas:latest │   │ qms-standalone-v2.3.tar.gz  │
│ mes_lite.whl│   │             │   │ full-airgapped-v2.3.iso     │
│ qms.whl     │   │             │   │                             │
└─────────────┘   └─────────────┘   └─────────────────────────────┘
```

### Delivery Methods

| Deployment | Delivery | Format |
|------------|----------|--------|
| SaaS | CI/CD to Kubernetes | Docker image |
| Dedicated | Customer portal download | tar.gz |
| Air-Gapped | Physical media (USB/DVD) | ISO with vendored deps |

---

## Risk Assessment

### High Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migrations break | Data loss, downtime | Test on copy of prod DB first |
| HubSpot sync breaks during cutover | Customer data out of sync | Feature flag to run old+new in parallel briefly |

### Medium Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Import errors cascade | App won't start | Run tests frequently during refactor |
| Cross-app ForeignKeys cause issues | Migrations fail | Use string references `'app.Model'` |
| Feature flags miss edge cases | Unauthorized access | Comprehensive test coverage |

### Low Risk

| Risk | Impact | Mitigation |
|------|--------|------------|
| Build pipeline complexity | Slower releases | Start simple, iterate |
| Settings files diverge | Inconsistent behavior | Share common base.py |

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Django apps over microservices | Same database, simpler ops, sufficient isolation |
| post_save over custom signals | Built-in, automatic, less code |
| OneToOne link for integrations | Clean separation, integration owns its data |
| Manifest files for deployment config | Auditable, versionable, customer-specific |
| Monorepo over multi-repo | Single source of truth, easier refactoring |

---

## Success Criteria

- [ ] Can deploy SaaS with all modules, feature flags work per tenant
- [ ] Can deploy dedicated instance with only purchased modules
- [ ] Can deploy air-gapped instance with no cloud dependencies
- [ ] Orders model has zero HubSpot code
- [ ] HubSpot integration can be added/removed without touching core
- [ ] Build pipeline produces correct bundles for each product
- [ ] All existing tests pass after refactor
