# Multi-Tenancy & Deployment Roadmap

**Last Updated:** February 18, 2026
**Status:** Phase 0 & 1 Complete (including Tenant Group Management API)
**Approach:** SaaS-First, Foundation-Ready

## Quick Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | ✅ Complete | Schema foundations (UUIDs, tenant FK, constraints, seeding) |
| Phase 1 | ✅ Complete | RLS + Tenant Middleware implemented |
| Phase 2 | 🔲 Pending | Facility support (multi-site) |
| Phase 3 | 🔲 Pending | Customer portal |
| Phase 4 | 🔲 Pending | Dedicated deployments |
| Phase 5 | 🔲 Pending | Hub + Sync (air-gapped)

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Current State](#current-state)
3. [Required Decisions](#required-decisions)
4. [Phase 0: Schema Foundations](#phase-0-schema-foundations)
5. [Phase 1: SaaS with Shared Database + RLS](#phase-1-saas-with-shared-database--rls)
6. [Phase 2: Facility Support](#phase-2-facility-support)
7. [Phase 3: Customer Portal](#phase-3-customer-portal)
8. [Phase 4: Dedicated Deployments](#phase-4-dedicated-deployments)
9. [Phase 5: Hub + Sync](#phase-5-hub--sync)
10. [Deployment Configurations](#deployment-configurations)
11. [Summary](#summary)

---

## Philosophy

### Context: Pre-Production

This application is not yet in production. There is no live data to migrate. This means:
- Schema changes are straightforward (no dual-write, no backfill)
- We can squash migrations and start fresh with UUIDs
- The focus is on getting the schema right, not migration mechanics

### The Rake Test

**"How hard is this to change later with data in the system?"**

| Decision | Change Later | Verdict |
|----------|--------------|---------|
| UUID vs int PK | Brutal | Do now |
| `tenant_id` column | Hard | Add nullable now |
| Global unique constraints | Hard | Make tenant-scoped now |
| GenericForeignKey object_id type | Hard | Change to CharField now |
| Reference data scoping | Hard | Decide now |
| RLS policies | Easy | Do in Phase 1 |
| Everything else | Easy | Do when needed |

### The Strategy

```
Schema foundations are hard to change  →  Do them right, do them now
Architecture is just code              →  Build when you need it
```

---

## Current State

### Existing Foundation

`SecureModel` in `Tracker/models/core.py` has soft delete, timestamps, and versioning. `SecureManager` provides permission-based filtering via `for_user()`. User extends `AbstractUser` directly (not SecureModel).

### Data Model

```
┌─────────────────────────────────────────────────────────────┐
│  CURRENT: Single-Tenant with Customer Filtering             │
│                                                             │
│  You (the operator) ─┬─► Companies (Boeing, Northrop, etc.) │
│                      │      └─► Orders placed WITH you      │
│                      └─► Users                              │
│                            └─► parent_company (FK)          │
└─────────────────────────────────────────────────────────────┘
```

### Key Distinction: Tenant ≠ Companies

```
Tenant = Organization that USES your software (SaaS customer)
Companies = That tenant's customers (Boeing is THEIR customer)

Tenant → Companies → Orders → Parts
```

---

## Required Decisions

**These cannot be deferred. Decide before Phase 0.**

### 1. Reference Data Scoping

**Decision: Per-tenant for all reference data.**

| Model | Scoping | Rationale |
|-------|---------|-----------|
| `QualityErrorsList` | Per-tenant | Tenants customize defect codes to their industry |
| `EquipmentType` | Per-tenant | Looks standard but tenants will want custom types |
| `DocumentType` | Per-tenant | Different doc classification systems |
| `ProcessStep` templates | Per-tenant | Core differentiator, definitely custom |
| `ApprovalTemplate` | Per-tenant | Different approval workflows |

**Principle:** If there's any chance a tenant will want to customize it, make it per-tenant. It's easier to seed identical data to new tenants than to untangle shared data later.

**Implementation:** These models inherit `SecureModel`, so they get the `tenant` FK automatically. When creating a new tenant, seed their reference data from a template.

### 2. Username Uniqueness

**Decision: Email as username (globally unique).**

Emails are inherently unique. No tenant scoping needed for usernames.

### 3. Group Scoping

**Decision: Tenant-scoped membership.**

Django's `auth.Group` has no tenant FK, but we can scope the *membership* rather than the groups themselves:
- Group definitions are global ("QA Manager" exists once with its permissions)
- `TenantGroupMembership` tracks which users belong to which groups within which tenant
- Custom auth backend makes `user.has_perm()` check tenant-scoped membership

See Phase 0.8 for implementation.

---

## Phase 0: Schema Foundations

**Goal:** Fix schema issues that are brutal to change later.

### 0.1 UUIDv7 Generator

```python
# Tracker/utils/uuid.py
import uuid, time

def uuid7():
    """Time-ordered UUID for better B-tree performance."""
    timestamp_ms = int(time.time() * 1000)
    return uuid.UUID(bytes=timestamp_ms.to_bytes(6, 'big') + uuid.uuid4().bytes[6:], version=7)
```

### 0.2 Fix GenericForeignKey Fields

These 4 fields use integer types for `object_id` which breaks with UUIDs:

| Model | Field | Current Type | Location |
|-------|-------|--------------|----------|
| `ArchiveReason` | `object_id` | `PositiveIntegerField` | core.py:609 |
| `NotificationTask` | `related_object_id` | `PositiveIntegerField` | core.py:806 |
| `ApprovalRequest` | `object_id` | `PositiveIntegerField` | core.py:960 |
| `Documents` | `object_id` | `PositiveBigIntegerField` | core.py:1476 |

Change all to:
```python
object_id = models.CharField(max_length=36)
```

### 0.3 Fix Global Unique Constraints

These 12 fields have `unique=True` which blocks multi-tenancy:

| Model | Field | Location |
|-------|-------|----------|
| `ExternalAPIOrderIdentifier` | `stage_name` | core.py:539 |
| `ApprovalRequest` | `approval_number` | core.py:958 |
| `ApprovalTemplate` | `template_name` | core.py:1370 |
| `ApprovalTemplate` | `approval_type` | core.py:1371 |
| `DocumentType` | `name` | core.py:1412 |
| `DocumentType` | `code` | core.py:1413 |
| `ChatSession` | `langgraph_thread_id` | dms.py:84 |
| `QuarantineDisposition` | `disposition_number` | qms.py:358 |
| `CAPA` | `capa_number` | qms.py:645 |
| `CapaTask` | `task_number` | qms.py:1019 |
| `Orders` | `hubspot_deal_id` | mes_lite.py:1086 |

Change pattern - replace `unique=True` with:
```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['tenant', 'field_name'],
            condition=Q(deleted_at__isnull=True),
            name='model_tenant_field_unique'
        )
    ]
```

**Note:** Also fix `generate_approval_number()`, `generate_disposition_number()`, and similar functions to filter by tenant when finding the next sequence number.

### 0.4 SecureModel Updates

```python
class SecureModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    archived = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_current_version = models.BooleanField(default=True)

    tenant = models.ForeignKey('Tenant', on_delete=models.PROTECT, null=True, blank=True, db_index=True)

    # For external integrations (ERP, webhooks) - enables idempotent upserts
    external_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'external_id'],
                condition=Q(external_id__isnull=False),
                name='%(class)s_tenant_external_id_unique'
            )
        ]
```

### 0.5 Tenant Model

```python
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)  # Immutable after creation - used in API headers

    class Tier(models.TextChoices):
        STARTER = 'starter'
        PRO = 'pro'
        ENTERPRISE = 'enterprise'

    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STARTER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    settings = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:  # Existing tenant
            old = Tenant.objects.filter(pk=self.pk).values_list('slug', flat=True).first()
            if old and old != self.slug:
                raise ValueError("Tenant slug cannot be changed after creation")
        super().save(*args, **kwargs)
```

### 0.6 User Model (Does NOT Inherit SecureModel)

```python
class User(AbstractUser):
    """User extends AbstractUser, not SecureModel - needs tenant FK directly."""

    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True)

    class UserType(models.TextChoices):
        INTERNAL = 'internal'
        PORTAL = 'portal'

    user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.INTERNAL)
    parent_company = models.ForeignKey(Companies, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Validate parent_company belongs to same tenant
        if self.parent_company_id and self.tenant_id:
            if self.parent_company.tenant_id != self.tenant_id:
                raise ValueError("User's parent_company must belong to same tenant")
        super().save(*args, **kwargs)
```

### 0.8 Tenant-Scoped Groups (IMPLEMENTED)

> **Status:** Implemented with simplified 4-role system. See [PERMISSION_SYSTEM_REFACTOR.md](./PERMISSION_SYSTEM_REFACTOR.md) for details.

Instead of scoping Django's `auth.Group`, we use custom tenant-owned groups with a simple role type:

```python
class RoleType(models.TextChoices):
    ADMIN = 'admin'      # Full access
    STAFF = 'staff'      # View all, edit work
    AUDITOR = 'auditor'  # Read-only, anonymized data
    CUSTOMER = 'customer' # Their orders only

class TenantGroup(models.Model):
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    role_type = models.CharField(choices=RoleType.choices, default='staff')

class UserRole(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    group = models.ForeignKey('TenantGroup', on_delete=models.CASCADE)
    facility = models.ForeignKey('Facility', null=True)  # Future
    company = models.ForeignKey('Companies', null=True)  # For customers
```

**Why this approach:**
- Simpler than granular Django permissions
- `for_user()` checks role_type directly
- Default groups seeded on tenant creation
- Extensible if granular permissions needed later

### 0.9 Checklist (COMPLETE)

- [x] Add `uuid7` function
- [x] Change 4 GenericForeignKey `object_id` fields to `CharField(max_length=36)` *(already done)*
- [x] Convert 12 global `unique=True` to tenant-scoped `UniqueConstraint` *(most already done, ArchiveReason fixed)*
- [x] Add `tenant` FK to SecureModel
- [x] Add `external_id` to SecureModel *(already present)*
- [x] Add `tenant` FK to User model
- [x] Add tenant validation to User.parent_company *(already in User.save())*
- [x] Create Tenant model with immutable slug
- [x] Make sequence generators tenant-scoped *(all use `generate_next_sequence(tenant=tenant)`)*
- [x] Add `TenantGroup` + `UserRole` models (replaced TenantGroupMembership)
- [x] Add `Facility` model for multi-site support
- [x] Implement `for_user()` role-based filtering
- [x] Add group seeding signal on tenant creation
- [x] Create tenant seeding script for reference data *(signal + defaults_service)*

### 0.10 Permission System (COMPLETE)

> See [PERMISSION_SYSTEM_REFACTOR.md](./PERMISSION_SYSTEM_REFACTOR.md) for full details.

- [x] Add `permissions` M2M field to TenantGroup
- [x] Define group presets in `Tracker/presets.py` (10 roles)
- [x] Implement `has_tenant_perm()` on User model
- [x] Add permission caching (5-min TTL) with invalidation signals
- [x] STAFF_VIEW_PERMISSIONS constant (71 view permissions)
- [x] System Admin vs Tenant Admin split (platform vs customer admins)
- [x] Backfill existing tenants with default groups
- [x] Tenant Group Management API (`TenantGroupViewSet` in `viewsets/tenant.py`)

**Tenant Group Management API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/TenantGroups/` | GET, POST | List/create tenant groups |
| `/api/TenantGroups/{id}/` | GET, PATCH, DELETE | Retrieve/update/delete group |
| `/api/TenantGroups/{id}/permissions/` | GET, PUT, POST, DELETE | Manage group permissions |
| `/api/TenantGroups/{id}/members/` | GET, POST | List/add group members |
| `/api/TenantGroups/{id}/members/{user_id}/` | DELETE | Remove member |
| `/api/TenantGroups/{id}/clone/` | POST | Clone group with new name |
| `/api/TenantGroups/{id}/preset-diff/` | GET | Compare vs preset template |
| `/api/TenantGroups/from-preset/` | POST | Create group from preset |
| `/api/permissions/` | GET | List permissions (grouped optional) |
| `/api/presets/` | GET | List available group presets |
| `/api/users/{id}/effective-permissions/` | GET | User's effective permissions |

### 0.11 Reference Data Seeding (COMPLETE)

- [x] `seed_reference_data_for_tenant()` in `defaults_service.py`
- [x] Signal auto-seeds on Tenant creation: groups, document types, approval templates
- [x] `setup_tenant` management command reports seeded data

---

## Phase 1: SaaS with Shared Database + RLS (COMPLETE)

**Goal:** Multi-tenant SaaS with database-level isolation from day one.

**Why RLS in Phase 1:** App-level filtering alone is a single point of failure. One forgotten `.for_user()` = complete data breach. RLS is the backstop.

**Status:** ✅ IMPLEMENTED

### Implementation Files

| Component | File | Description |
|-----------|------|-------------|
| Tenant Middleware | `Tracker/middleware.py` | `TenantMiddleware` resolves tenant from header/subdomain/user |
| RLS Context | `middleware.py:_set_rls_context()` | `SET LOCAL app.current_tenant_id = %s` |
| RLS Setup | `management/commands/setup_rls.py` | Enables RLS on 50+ tables |
| App Role | `init-db.sql` | Creates `partstracker_app` role (non-superuser) |
| Status Middleware | `middleware.py:TenantStatusMiddleware` | Blocks suspended/inactive tenants |

### 1.0 Settings Prerequisite ✅

```python
# settings.py - REQUIRED for SET LOCAL to work
DATABASES = {
    'default': {
        # ... existing config ...
        'ATOMIC_REQUESTS': True,  # Already configured
    }
}

# Enable RLS (set to True in production)
ENABLE_RLS = env.bool('ENABLE_RLS', False)
```

### 1.1 Tenant Middleware ✅

Already implemented in `Tracker/middleware.py`:

- **Multi-mode resolution:** header (`X-Tenant-ID`) → subdomain → user.tenant → default
- **Security:** Validates user can access requested tenant
- **RLS context:** Calls `SET LOCAL app.current_tenant_id` when `ENABLE_RLS=True`
- **Response headers:** `X-Tenant-Context` and `X-Tenant-Source` for debugging

### 1.2 Celery Task Context ✅

Already implemented in `Tracker/utils/tenant_context.py`:

- `tenant_context()` context manager for background jobs
- `with_tenant_from_model()` decorator for auto-extracting tenant
- `TenantAwareTask` mixin for Celery Task classes
- Helper functions: `get_tenant_for_user()`, `get_tenant_for_object()`

### 1.3 RLS Setup ✅

Already implemented in `management/commands/setup_rls.py`:

```bash
# Enable RLS on all tables
python manage.py setup_rls --force

# Disable RLS (for development)
python manage.py setup_rls --disable
```

**Features:**
- 50+ tenant-scoped tables covered
- Handles case-insensitive table names
- Verifies `tenant_id` column exists before enabling
- Creates policy: `tenant_id IS NULL OR tenant_id = current_setting('app.current_tenant_id')::uuid`
- Idempotent (safe to run multiple times)

### 1.4 Database App Role ✅

Already configured in `init-db.sql`:

```sql
-- Creates partstracker_app role (non-superuser, subject to RLS)
-- Grants SELECT, INSERT, UPDATE, DELETE but NOT superuser
-- Use postgres superuser for migrations (bypasses RLS)
```

### Original Example Code (for reference)

```python
# management/commands/setup_rls.py (ORIGINAL EXAMPLE - NOW IMPLEMENTED)

class Command(BaseCommand):
    TENANT_TABLES = [
        'tracker_parts', 'tracker_orders', 'tracker_workorders',
        'tracker_qualityreports', 'tracker_documents',
        'tracker_approvalrequest', 'tracker_archivereason',
        'tracker_notificationtask', 'tracker_companies',
        # ... add all tenant-scoped tables
    ]

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for table in self.TENANT_TABLES:
                cursor.execute(f'''
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

                    DROP POLICY IF EXISTS tenant_isolation ON {table};
                    CREATE POLICY tenant_isolation ON {table}
                        FOR ALL
                        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
                        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
                ''')
```

### 1.5 Checklist

- [x] Add `ATOMIC_REQUESTS=True` to database settings
- [x] Add `TenantMiddleware` with RLS context setting
- [x] Add `tenant_context()` for Celery tasks (`Tracker/utils/tenant_context.py`)
- [x] Create non-superuser database role for the app (`init-db.sql`)
- [x] Run `setup_rls` management command (available, run when enabling RLS)
- [x] Verify RLS blocks cross-tenant queries at DB level

---

## Phase 2: Facility Support

**Goal:** Support customers with multiple manufacturing sites.

**Timeline:** When a customer has multiple facilities.

> **See also:** [PERMISSION_SYSTEM_REFACTOR.md](./PERMISSION_SYSTEM_REFACTOR.md) for detailed implementation of `Facility` model and `UserRole` with facility scoping.

The permission system refactor supersedes the simple `UserFacilityAccess` model below with a more comprehensive `UserRole` model that combines:
- Tenant-scoped groups (`TenantGroup`)
- Facility scoping
- Customer company scoping

```python
# Simplified version (for reference only - see PERMISSION_SYSTEM_REFACTOR.md for full design)
class Facility(SecureModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    timezone = models.CharField(max_length=50, default='America/Chicago')
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'code'], name='facility_tenant_code_unique')
        ]
```

---

## Phase 3: Customer Portal

**Goal:** External users view order status (pizza tracker).

**Timeline:** When customers request it.

> **See also:** [PERMISSION_SYSTEM_REFACTOR.md](./PERMISSION_SYSTEM_REFACTOR.md) for `UserRole.company` field that tracks which company a customer user represents.

### Simple Approach: Access via Order relationships

No separate grants model. Just M2M fields on Order:

```python
class Orders(SecureModel):
    customer = models.ForeignKey('Companies', ...)  # Who placed the order (existing)

    # Company-level access - all users from these companies can see the order
    viewer_companies = models.ManyToManyField(
        'Companies',
        related_name='viewable_orders',
        blank=True,
        help_text="Companies whose portal users can view this order"
    )

    # User-level access - specific people, for large orgs where not everyone should see
    viewer_users = models.ManyToManyField(
        'User',
        related_name='viewable_orders',
        blank=True,
        help_text="Specific users who can view this order"
    )
```

```python
class PortalOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Portal users see orders they have access to."""
    serializer_class = PortalOrderSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type != 'portal':
            return Orders.objects.none()

        return Orders.objects.filter(
            Q(customer=user.parent_company) |       # Your company placed it
            Q(viewer_companies=user.parent_company) |  # Your company was granted access
            Q(viewer_users=user)                    # You specifically were granted access
        ).distinct()
```

**Usage patterns:**
- **Small customer:** Add company to `viewer_companies` → all their portal users see it
- **Large customer (Volvo):** Add specific contacts to `viewer_users` → only those people see it
- **Mixed:** Use both as needed

**Why this is simpler:**
- No separate `OrderAccessGrant` model
- No invitation tokens or expiration logic
- No email-based grants that need to be linked to users later
- Just relationships on the Order model

---

## Phase 4: Dedicated Deployments

**Goal:** Enterprise/gov customers get their own deployment.

**Key Insight:** Dedicated deployments are separate instances, not tenants in SaaS.

```
YOUR SAAS (Azure Commercial)     →  Shared DB, multiple tenants
BIGCORP DEDICATED                →  Own DB, one tenant row
NORTHROP GOVERNMENT (Azure Gov)  →  Separate cloud entirely
BOEING AIR-GAPPED (On-prem)      →  No internet, syncs via export
```

**Same codebase. Same Docker image. Different deployment.**

```python
# settings.py
DEPLOYMENT_MODE = env('DEPLOYMENT_MODE', default='saas')
IS_SAAS = DEPLOYMENT_MODE == 'saas'
IS_AIRGAPPED = DEPLOYMENT_MODE == 'airgapped'

FEATURES = {
    'self_service_signup': IS_SAAS,
    'stripe_billing': IS_SAAS,
    'ai_assistant': not IS_AIRGAPPED,
}
```

---

## Phase 5: Hub + Sync

**Goal:** Air-gapped deployments sync to central hub.

**Timeline:** When air-gapped customer needs central reporting.

```python
class SyncReadyModel(SecureModel):
    origin_instance = models.CharField(max_length=50, default='cloud', db_index=True)

class SyncConflict(models.Model):
    """Log conflicts instead of silently dropping data."""
    model_name = models.CharField(max_length=100)
    record_id = models.UUIDField()
    local_version = models.PositiveIntegerField()
    remote_version = models.PositiveIntegerField()
    remote_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

class SyncService:
    def apply_changes(self, changes):
        for change in changes:
            model = apps.get_model('Tracker', change['model'])
            existing = model.all_objects.filter(id=change['id']).first()

            if existing and existing.version > change['version']:
                # Log conflict instead of silent drop
                SyncConflict.objects.create(
                    model_name=change['model'],
                    record_id=change['id'],
                    local_version=existing.version,
                    remote_version=change['version'],
                    remote_data=change['data']
                )
                continue

            instance = self.deserialize(model, change['data'])
            instance.save(from_sync=True)
```

---

## Deployment Configurations

```bash
# SAAS
DEPLOYMENT_MODE=saas
DATABASE_URL=postgres://user:pass@saas-db.azure.com/ambac

# DEDICATED
DEPLOYMENT_MODE=dedicated
CUSTOMER_NAME=BigCorp
DATABASE_URL=postgres://user:pass@bigcorp-db.azure.com/ambac

# AIR-GAPPED
DEPLOYMENT_MODE=airgapped
CUSTOMER_NAME=Boeing
DATABASE_URL=postgres://ambac:pass@localhost/ambac
INSTANCE_ID=airgapped-boeing-sea
```

---

## Summary

### The 5 Rake Problems (Fix in Phase 0)

| # | Issue | Count | Solution |
|---|-------|-------|----------|
| 1 | GenericForeignKey `object_id` fields | 4 | Change to `CharField(max_length=36)` |
| 2 | Global `unique=True` constraints | 12 | Change to tenant-scoped `UniqueConstraint` |
| 3 | User model lacks tenant FK | 1 | Add `tenant` FK directly |
| 4 | `ATOMIC_REQUESTS` not set | 1 | Add to database settings |
| 5 | Group membership not tenant-scoped | - | Add `TenantGroupMembership` + auth backend |

### Also Do Now (Easy But Important)

| Issue | Solution |
|-------|----------|
| PK type | UUIDv7 from day one |
| Reference data | Per-tenant, seed on tenant creation |
| Tenant.slug | Make immutable after creation |
| Sequence generators | Make tenant-scoped (`generate_approval_number()`, etc.) |
| `external_id` field | Add for integration idempotency |

### Do in Phase 1

| Issue | Reason |
|-------|--------|
| RLS policies | App-level filtering alone = single point of failure |
| Non-superuser DB user | Superusers bypass RLS entirely |

### Not Rake Problems (Fix When Needed)

| Issue | Why It Can Wait |
|-------|-----------------|
| Views with `.objects.all()` | RLS is the backstop |
| Signals without tenant context | Copy tenant from parent object |
| Composite indexes | Add when you see slow queries |
| API tenant routing | `user.tenant` is sufficient |
| Serializer FK validation | RLS catches it; nice-to-have for better errors |

### Defer Until Needed

| Capability | Build When |
|------------|------------|
| Facility scoping | Customer has multiple sites |
| Customer portal | Customer requests it |
| Dedicated deployments | Enterprise/gov signs |
| Hub + sync | Air-gapped needs reporting |
| Enterprise SSO | Enterprise customer requires it |

---

## Authentication & SSO Roadmap

### Current State

Using `django-allauth` with:
- `ModelBackend` → replaced with `TenantPermissionBackend`
- `allauth.account.auth_backends.AuthenticationBackend` for email login

### User Onboarding Flows

| Flow | Tenant Source | Implementation |
|------|---------------|----------------|
| **Invitation** | From `UserInvitation.user.tenant` | `TenantAccountAdapter` checks session |
| **Self-service signup** | Create new tenant | Signup form creates tenant + admin user |
| **Subdomain** | From `Tenant.slug` via URL | `TenantMiddleware` resolves |
| **SSO (SaaS)** | From SSO provider config | WorkOS/Auth0 Organizations |
| **SSO (Air-gapped)** | From on-prem IdP | SAML (ADFS) or LDAP |

### SSO Strategy by Deployment Type

| Deployment | SSO Approach | Library/Service |
|------------|--------------|-----------------|
| **SaaS (cloud)** | Outsource to WorkOS | WorkOS SDK - handles SAML/OIDC complexity |
| **Air-gapped (Microsoft)** | ADFS (SAML) | `allauth.socialaccount.providers.saml` |
| **Air-gapped (simple)** | LDAP direct | `django-auth-ldap` |
| **Air-gapped (Keycloak)** | OIDC | `allauth.socialaccount.providers.openid_connect` |

### SSO Implementation Notes

**For SaaS (WorkOS/Auth0):**
- Outsource SSO complexity to specialized provider
- They handle per-customer IdP configuration
- You receive `organization_id` in callback, map to `Tenant`
- Build when enterprise customers demand it (sales unlock)

**For Air-gapped (ADFS/LDAP):**
- SSO config must be in database, not settings.py (each deployment differs)
- Model needed: `TenantSSOConfig` with provider details
- LDAP is simpler: user enters password in your app, you validate against AD
- SAML is more complex: redirect to IdP, receive assertion

**LDAP vs SAML:**
| | LDAP | SAML |
|---|------|------|
| Password entered in | Your app | IdP's login page |
| Your app sees password | Yes | No (token only) |
| True SSO | No | Yes |
| Complexity | Simple | Higher |
| Air-gapped friendly | Very | Yes |

### Models Needed (Future)

```python
class TenantSSOConfig(models.Model):
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE)
    provider_type = models.CharField(choices=['saml', 'oidc', 'ldap'])

    # SAML/OIDC
    metadata_url = models.URLField(blank=True)
    entity_id = models.CharField(max_length=255, blank=True)

    # LDAP
    ldap_server = models.CharField(max_length=255, blank=True)
    ldap_bind_dn = models.CharField(max_length=255, blank=True)
    ldap_base_dn = models.CharField(max_length=255, blank=True)

    # Behavior
    auto_create_users = models.BooleanField(default=True)
    default_group = models.ForeignKey(Group, null=True, blank=True)
```

### Build Order

1. **Now (Phase 0):** `TenantAccountAdapter` for invitation + self-service
2. **Phase 1:** `TenantMiddleware` for subdomain routing
3. **When enterprise asks:** WorkOS integration for SaaS SSO
4. **When air-gapped customer signs:** SAML/LDAP support

### The One-Liner

> **5 schema changes + RLS. Everything else can wait.**
