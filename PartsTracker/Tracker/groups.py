# Tracker/groups.py
"""
Group registry with constants and default permissions.

Usage:
    from Tracker.groups import Groups

    # Instead of magic strings
    user.grant_group(Groups.PRODUCTION_OPERATOR, tenant)

    # Check membership
    if user.has_group(Groups.INTERNAL_STAFF, tenant):
        ...
"""


class Groups:
    """Registry of known groups with their default permissions."""

    # Internal staff roles
    ADMIN = 'Admin'
    QA_MANAGER = 'QA_Manager'
    QA_INSPECTOR = 'QA_Inspector'
    PRODUCTION_MANAGER = 'Production_Manager'
    PRODUCTION_OPERATOR = 'Production_Operator'
    DOCUMENT_CONTROLLER = 'Document_Controller'

    # External roles
    CUSTOMER = 'Customer'

    # All known group names
    ALL = {
        ADMIN,
        QA_MANAGER,
        QA_INSPECTOR,
        PRODUCTION_MANAGER,
        PRODUCTION_OPERATOR,
        DOCUMENT_CONTROLLER,
        CUSTOMER,
    }

    # Internal staff groups (for for_user() checks)
    INTERNAL_STAFF = {
        ADMIN,
        QA_MANAGER,
        QA_INSPECTOR,
        PRODUCTION_MANAGER,
        PRODUCTION_OPERATOR,
        DOCUMENT_CONTROLLER,
    }

    # External groups
    EXTERNAL = {
        CUSTOMER,
    }

    # Default permissions per group (used for seeding)
    # Patterns: '*' = all, 'view_*' = all view, 'add_orders' = specific
    DEFAULT_PERMISSIONS = {
        ADMIN: ['*'],  # Full access

        QA_MANAGER: [
            'view_*', 'add_*', 'change_*',
            'delete_qualityreport', 'delete_capa', 'delete_quarantinedisposition',
        ],

        QA_INSPECTOR: [
            'view_*',
            'add_qualityreport', 'change_qualityreport',
            'add_quarantinedisposition', 'change_quarantinedisposition',
            'add_measurement', 'change_measurement',
        ],

        PRODUCTION_MANAGER: [
            'view_*', 'add_*', 'change_*',
        ],

        PRODUCTION_OPERATOR: [
            'view_orders', 'view_parts', 'view_workorders',
            'view_processes', 'view_steps', 'view_parttypes',
            'view_companies', 'view_equipment',
            'change_parts',  # Update part status
            'add_steptransitionlog', 'change_steptransitionlog',
        ],

        DOCUMENT_CONTROLLER: [
            'view_*',
            'add_documents', 'change_documents', 'delete_documents',
            'add_threedmodel', 'change_threedmodel', 'delete_threedmodel',
        ],

        CUSTOMER: [
            'view_orders', 'view_parts',  # Filtered to their company by for_user()
        ],
    }

    @classmethod
    def is_internal(cls, group_name):
        """Check if a group name is an internal staff group."""
        return group_name in cls.INTERNAL_STAFF

    @classmethod
    def is_external(cls, group_name):
        """Check if a group name is an external group."""
        return group_name in cls.EXTERNAL

    @classmethod
    def get_default_permissions(cls, group_name):
        """Get default permission patterns for a group."""
        return cls.DEFAULT_PERMISSIONS.get(group_name, [])


class GroupSeeder:
    """
    Handles seeding of default groups for tenants.

    Uses GROUP_PRESETS from presets.py as the source of truth.
    """

    # Maps old Django Group names to preset keys (for migration)
    LEGACY_NAME_MAP = {
        'Admin': 'tenant_admin',
        'QA_Manager': 'qa_manager',
        'QA_Inspector': 'qa_inspector',
        'Production_Manager': 'production_manager',
        'Production_Operator': 'operator',
        'Document_Controller': 'document_controller',
        'Customer': 'customer',
    }

    # Groups that should NOT be auto-seeded for every tenant
    # system_admin is only for platform team, not customer tenants
    SKIP_FOR_TENANT_SEEDING = {'system_admin'}

    @classmethod
    def seed_for_tenant(cls, tenant):
        """
        Create default groups for a new tenant with permissions.

        Called automatically via signal when a Tenant is created.
        Returns list of created TenantGroup instances.

        Uses GROUP_PRESETS from presets.py which includes:
        - name, description
        - permissions list (or '__all__' for admin)

        Note: 'system_admin' is NOT seeded - that's only for platform team.
        """
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup
        from Tracker.presets import GROUP_PRESETS

        created = []
        for key, preset in GROUP_PRESETS.items():
            # Skip system_admin - that's only for platform team
            if key in cls.SKIP_FOR_TENANT_SEEDING:
                continue

            group, was_created = TenantGroup.objects.get_or_create(
                tenant=tenant,
                name=preset['name'],
                defaults={
                    'description': preset['description'],
                    'is_custom': False,
                }
            )
            if was_created:
                # Assign permissions
                if preset['permissions'] == '__all__':
                    # Admin gets all permissions
                    group.permissions.set(Permission.objects.all())
                else:
                    perms = Permission.objects.filter(codename__in=preset['permissions'])
                    group.permissions.set(perms)

                created.append(group)

        return created

    @classmethod
    def backfill_all_tenants(cls):
        """
        Backfill default groups for all existing tenants.

        Run this after migration to ensure all tenants have default groups.
        """
        from Tracker.models import Tenant

        results = {'tenants': 0, 'groups_created': 0}
        for tenant in Tenant.objects.all():
            created = cls.seed_for_tenant(tenant)
            results['tenants'] += 1
            results['groups_created'] += len(created)

        return results

    @classmethod
    def backfill_permissions(cls):
        """
        Backfill permissions for existing TenantGroups.

        Run this after adding the permissions M2M field to assign
        default permissions to groups that were created before the migration.
        """
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup
        from Tracker.presets import GROUP_PRESETS

        # Build lookup by name
        preset_by_name = {preset['name']: preset for preset in GROUP_PRESETS.values()}

        results = {'groups_updated': 0, 'groups_skipped': 0}

        for group in TenantGroup.objects.all():
            preset = preset_by_name.get(group.name)
            if not preset:
                # Custom group, skip
                results['groups_skipped'] += 1
                continue

            # Only update if group has no permissions (don't override customizations)
            if group.permissions.exists():
                results['groups_skipped'] += 1
                continue

            if preset['permissions'] == '__all__':
                group.permissions.set(Permission.objects.all())
            else:
                perms = Permission.objects.filter(codename__in=preset['permissions'])
                group.permissions.set(perms)

            results['groups_updated'] += 1

        return results
