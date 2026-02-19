# Permission System

## Status: Complete

The permission system is fully implemented including API endpoints for tenant self-service.

**Implemented:**
- [x] `TenantGroup` model with `role_type` field
- [x] `UserRole` model linking users to groups (with facility/company scoping)
- [x] `Facility` model for multi-site support
- [x] `RoleType` enum: admin, staff, auditor, customer
- [x] `for_user()` checks role type for data filtering
- [x] Signal auto-seeds groups on tenant creation
- [x] `permissions` M2M field on TenantGroup (links to `auth.Permission`)
- [x] Group presets defined in code (`Tracker/presets.py`)
- [x] `has_tenant_perm()` method on User model
- [x] Permission caching with 5-minute TTL + cache invalidation signals
- [x] STAFF_VIEW_PERMISSIONS constant (71 view permissions all staff get)
- [x] 10 role presets: System Admin, Tenant Admin, QA Manager, QA Inspector, Production Manager, Operator, Document Controller, Engineering, Auditor, Customer
- [x] Backfilled all 5 existing tenants (45 groups total)
- [x] API endpoints for tenant admin group management (`TenantGroupViewSet`)
- [x] Permission list endpoint with categories (`/api/permissions/`)
- [x] Preset list endpoint (`/api/presets/`)
- [x] Effective permissions endpoint (`/api/users/{id}/effective-permissions/`)

**Permission counts by role:**
| Role | Permissions | Notes |
|------|-------------|-------|
| System Admin | 417 (all) | Platform team only, not auto-seeded for tenants |
| Tenant Admin | 306 | Full tenant access for customer business admins |
| QA Manager | 224 | Quality management, approvals, CAPA control |
| Production Manager | 199 | Production operations, scheduling |
| Engineering | 149 | Design, process control, ECOs |
| QA Inspector | 131 | Perform inspections, initiate CAPAs |
| Document Controller | 122 | Document management, approvals |
| Operator | 111 | Production floor work |
| Auditor | 71 | Read-only (STAFF_VIEW_PERMISSIONS) |
| Customer | 14 | Portal access (filtered by for_user()) |

**Future enhancements:**
- [ ] Frontend UI for tenant admins to customize group permissions

---

## Design Overview

### Two-Layer Permission System

```
┌─────────────────────────────────────────────────────────────┐
│  DATA FILTERING (for_user)                                  │
│  "What data can they SEE?"                                  │
│  Based on role_type: admin/staff/auditor/customer           │
└─────────────────────────────────────────────────────────────┘
                            +
┌─────────────────────────────────────────────────────────────┐
│  ACTION PERMISSIONS (has_tenant_perm)                       │
│  "What can they DO?"                                        │
│  Based on Django Permission M2M, customizable per tenant    │
└─────────────────────────────────────────────────────────────┘
```

### Why This Design?

Based on research into existing Django multi-tenant libraries:

| Library | Pattern | Our Adaptation |
|---------|---------|----------------|
| [django-tenant-users](https://github.com/Corvia/django-tenant-users) | UserTenantPermissions with PermissionsMixin | TenantGroup with M2M to Permission |
| [django-role-permissions](https://github.com/vintasoftware/django-role-permissions) | Roles defined in code with permission defaults | GROUP_PRESETS dict seeded on tenant creation |
| [django-organizations](https://github.com/bennylope/django-organizations) | OrganizationUser through model | UserRole with facility/company scoping |

**Key insight from manufacturing research:**
- Facilities need granular action control (who can approve, who can release)
- Different tenants have different permission needs
- Tenant admins must be able to customize without code changes

---

## Models

### RoleType Enum

```python
class RoleType(models.TextChoices):
    ADMIN = 'admin', 'Admin'        # Full access, can manage permissions
    STAFF = 'staff', 'Staff'        # Internal users with configurable permissions
    AUDITOR = 'auditor', 'Auditor'  # Read-only, anonymized data
    CUSTOMER = 'customer', 'Customer' # External, filtered to their orders
```

### TenantGroup

```python
class TenantGroup(models.Model):
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Base role type - determines data filtering behavior
    role_type = models.CharField(choices=RoleType.choices, default='staff')

    # Granular permissions - customizable per tenant
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='tenant_groups'
    )

    class Meta:
        db_table = 'tracker_tenant_group'
        unique_together = [('tenant', 'name')]
```

### UserRole

```python
class UserRole(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='user_roles')
    group = models.ForeignKey('TenantGroup', on_delete=models.CASCADE)
    facility = models.ForeignKey('Facility', null=True, blank=True)
    company = models.ForeignKey('Companies', null=True, blank=True)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey('User', null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'tracker_user_role'
        unique_together = [('user', 'group', 'facility', 'company')]
```

---

## Group Presets

Defined in code, seeded when tenant is created. Tenant admins can modify after creation.

```python
# Tracker/presets.py

GROUP_PRESETS = {
    'administrator': {
        'name': 'Administrator',
        'role_type': 'admin',
        'description': 'Full access to all features and settings',
        'permissions': '__all__',  # Gets all permissions
    },

    'qa_manager': {
        'name': 'QA Manager',
        'role_type': 'staff',
        'description': 'Quality management, approvals, CAPA control',
        'permissions': [
            # Quality
            'add_qualityreport', 'change_qualityreport', 'delete_qualityreport', 'view_qualityreport',
            'approve_qualityreport',
            # CAPA
            'add_capa', 'change_capa', 'delete_capa', 'view_capa',
            'approve_capa', 'close_capa', 'verify_capa',
            # Dispositions
            'add_quarantinedisposition', 'change_quarantinedisposition', 'view_quarantinedisposition',
            'approve_disposition', 'close_disposition',
            # Documents
            'view_documents', 'view_confidential_documents',
            # Production (view only)
            'view_orders', 'view_parts', 'view_workorder',
        ],
    },

    'qa_inspector': {
        'name': 'QA Inspector',
        'role_type': 'staff',
        'description': 'Perform inspections, create quality reports',
        'permissions': [
            'add_qualityreport', 'change_qualityreport', 'view_qualityreport',
            'add_capa', 'change_capa', 'view_capa',
            'view_orders', 'view_parts', 'view_workorder',
            'view_documents',
        ],
    },

    'production_manager': {
        'name': 'Production Manager',
        'role_type': 'staff',
        'description': 'Manage production operations',
        'permissions': [
            'add_orders', 'change_orders', 'view_orders',
            'add_workorder', 'change_workorder', 'view_workorder',
            'change_parts', 'view_parts',
            'view_qualityreport', 'view_capa',
            'view_documents',
        ],
    },

    'operator': {
        'name': 'Operator',
        'role_type': 'staff',
        'description': 'Production floor work',
        'permissions': [
            'view_orders', 'view_workorder',
            'change_parts', 'view_parts',
            'add_steptransitionlog',
        ],
    },

    'document_controller': {
        'name': 'Document Controller',
        'role_type': 'staff',
        'description': 'Manage controlled documents',
        'permissions': [
            'add_documents', 'change_documents', 'delete_documents', 'view_documents',
            'view_confidential_documents', 'view_restricted_documents',
            'add_threedmodel', 'change_threedmodel', 'view_threedmodel',
        ],
    },

    'auditor': {
        'name': 'Auditor',
        'role_type': 'auditor',
        'description': 'Read-only access with anonymized sensitive data',
        'permissions': [
            'view_orders', 'view_parts', 'view_workorder',
            'view_qualityreport', 'view_capa',
            'view_documents',
        ],
    },

    'customer': {
        'name': 'Customer',
        'role_type': 'customer',
        'description': 'External customer portal access',
        'permissions': [
            'view_orders', 'view_parts', 'view_documents',
        ],
    },
}
```

### Tenant Independence

Each tenant gets **their own copies** of groups. After seeding, they're independent:

```
Tenant A (aerospace - strict)
├── Customer: [view_orders]  # Locked down
│
Tenant B (job shop - collaborative)
├── Customer: [view_orders, view_parts, view_workorder, add_feedback]
├── Preferred Customer: [... + view_documents]  # Custom group they created
```

---

## Permission Checking

### User Methods

```python
class User(AbstractUser):

    def get_tenant_permissions(self, tenant=None):
        """Get all permission codenames for user in tenant (cached)."""
        tenant = tenant or self.tenant
        if not tenant:
            return set()

        cache_key = f'user_{self.id}_tenant_{tenant.id}_perms'
        perms = cache.get(cache_key)

        if perms is None:
            if self.is_superuser:
                # Superuser has all permissions
                perms = set(Permission.objects.values_list('codename', flat=True))
            else:
                # Get permissions from all groups user belongs to
                perms = set(Permission.objects.filter(
                    tenant_groups__role_assignments__user=self,
                    tenant_groups__tenant=tenant
                ).values_list('codename', flat=True))

            cache.set(cache_key, perms, timeout=300)  # 5 min cache

        return perms

    def has_tenant_perm(self, perm, tenant=None):
        """Check if user has specific permission in tenant."""
        # Admin role_type bypasses permission checks
        if self.get_role_type(tenant) == RoleType.ADMIN:
            return True
        return perm in self.get_tenant_permissions(tenant)

    def has_tenant_perms(self, perms, tenant=None):
        """Check if user has all specified permissions."""
        if self.get_role_type(tenant) == RoleType.ADMIN:
            return True
        user_perms = self.get_tenant_permissions(tenant)
        return all(perm in user_perms for perm in perms)

    def clear_permission_cache(self):
        """Clear cached permissions (call when roles/groups change)."""
        if self.tenant:
            cache.delete(f'user_{self.id}_tenant_{self.tenant.id}_perms')
```

### Cache Invalidation

```python
# In signals.py
@receiver(m2m_changed, sender=TenantGroup.permissions.through)
def clear_group_permission_cache(sender, instance, **kwargs):
    """Clear permission cache for all users in this group."""
    for role in instance.role_assignments.all():
        role.user.clear_permission_cache()

@receiver(post_save, sender=UserRole)
@receiver(post_delete, sender=UserRole)
def clear_user_permission_cache(sender, instance, **kwargs):
    """Clear permission cache when user's roles change."""
    instance.user.clear_permission_cache()
```

---

## API Endpoints

### Group Management (Tenant Admin Only)

```
GET    /api/groups/                    # List tenant's groups
POST   /api/groups/                    # Create custom group
GET    /api/groups/{id}/               # Get group with permissions
PATCH  /api/groups/{id}/               # Update name, description, role_type
DELETE /api/groups/{id}/               # Delete group (if no users assigned)

PUT    /api/groups/{id}/permissions/   # Replace all permissions
POST   /api/groups/{id}/permissions/   # Add permissions
DELETE /api/groups/{id}/permissions/   # Remove permissions

GET    /api/groups/{id}/members/       # List users in group
POST   /api/groups/{id}/members/       # Add user to group
DELETE /api/groups/{id}/members/{user_id}/  # Remove user

GET    /api/permissions/               # List all available permissions (for UI)
GET    /api/presets/                   # List available group presets
POST   /api/groups/from-preset/        # Create group from preset
```

### Permission Check (ViewSet)

```python
class TenantGroupViewSet(viewsets.ModelViewSet):
    serializer_class = TenantGroupSerializer

    def get_queryset(self):
        return TenantGroup.objects.filter(tenant=self.request.user.tenant)

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in SAFE_METHODS:
            if not request.user.is_tenant_admin():
                raise PermissionDenied("Only admins can manage groups")
```

---

## Data Filtering vs Action Permissions

| Concern | Mechanism | Example |
|---------|-----------|---------|
| **What data can they see?** | `for_user()` + `role_type` | Customer sees only their orders |
| **What actions can they take?** | `has_tenant_perm()` + M2M | QA Manager can approve CAPAs |

```python
# In a ViewSet
class CAPAViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        # DATA FILTERING - based on role_type
        return CAPA.objects.for_user(self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        # ACTION PERMISSION - based on specific permission
        if not request.user.has_tenant_perm('approve_capa'):
            raise PermissionDenied("You don't have permission to approve CAPAs")

        capa = self.get_object()
        capa.approve(by=request.user)
        return Response({'status': 'approved'})
```

---

## Custom Permissions

Django auto-generates `add_`, `change_`, `delete_`, `view_` for each model. For custom actions, define in model Meta:

```python
class CAPA(SecureModel):
    # ... fields ...

    class Meta:
        permissions = [
            ('approve_capa', 'Can approve CAPA'),
            ('close_capa', 'Can close CAPA'),
            ('verify_capa', 'Can verify CAPA effectiveness'),
        ]

class QualityReport(SecureModel):
    class Meta:
        permissions = [
            ('approve_qualityreport', 'Can approve quality report'),
        ]

class QuarantineDisposition(SecureModel):
    class Meta:
        permissions = [
            ('approve_disposition', 'Can approve disposition'),
            ('close_disposition', 'Can close disposition'),
        ]

class Documents(SecureModel):
    class Meta:
        permissions = [
            ('view_confidential_documents', 'Can view confidential documents'),
            ('view_restricted_documents', 'Can view restricted documents'),
            ('view_secret_documents', 'Can view secret documents'),
        ]
```

---

## Seeding Groups

```python
# Tracker/groups.py

def seed_groups_for_tenant(tenant):
    """Create default groups for a new tenant from presets."""
    from django.contrib.auth.models import Permission
    from Tracker.presets import GROUP_PRESETS

    created_groups = []

    for key, preset in GROUP_PRESETS.items():
        group, was_created = TenantGroup.objects.get_or_create(
            tenant=tenant,
            name=preset['name'],
            defaults={
                'description': preset['description'],
                'role_type': preset['role_type'],
            }
        )

        if was_created:
            # Assign permissions
            if preset['permissions'] == '__all__':
                group.permissions.set(Permission.objects.all())
            else:
                perms = Permission.objects.filter(codename__in=preset['permissions'])
                group.permissions.set(perms)

            created_groups.append(group)

    return created_groups
```

---

## Migration Checklist

- [x] Add `permissions` M2M field to TenantGroup
- [x] Create custom permissions in model Meta classes
- [x] Run `makemigrations` and `migrate`
- [x] Create `Tracker/presets.py` with GROUP_PRESETS
- [x] Update `seed_groups_for_tenant()` to use presets
- [x] Add `has_tenant_perm()` methods to User model
- [x] Add cache invalidation signals
- [ ] Create API viewsets for group management
- [ ] Update DRF permission classes to use `has_tenant_perm()`
- [x] Backfill permissions for existing tenant groups (45 groups across 5 tenants)

---

## Future Considerations

**Facility-scoped permissions:**
- UserRole.facility already supports this
- Can extend to check `has_tenant_perm(perm, facility=facility)`

**Training/qualification integration:**
- Manufacturing may need "can only do X if trained"
- Could add TrainingRequirement model linked to permissions
- ILUO matrix for operator skill levels

**Segregation of duties:**
- "Cannot approve own work" rules
- Could add `requires_different_user` flag to certain permissions

---

## References

- [django-tenant-users](https://github.com/Corvia/django-tenant-users) - Pattern for UserTenantPermissions
- [django-role-permissions](https://github.com/vintasoftware/django-role-permissions) - Pattern for code-defined role presets
- [django-organizations](https://github.com/bennylope/django-organizations) - Pattern for OrganizationUser through model
- [Operator Authorization Matrix](https://sgsystemsglobal.com/glossary/operator-authorization-matrix/) - Manufacturing permission patterns
