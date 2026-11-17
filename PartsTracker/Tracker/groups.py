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
    PURCHASING = 'Purchasing'

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
        PURCHASING,
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
        PURCHASING,
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
        from auditlog.context import disable_auditlog
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup
        from Tracker.presets import GROUP_PRESETS, grantable_permissions

        created = []
        # Suppress auditlog while seeding. The Admin group's
        # `permissions.set(Permission.objects.all())` otherwise makes auditlog
        # stringify every permission (each str() lazily fetches content_type),
        # an N+1 that costs ~9s per tenant created. These default groups are
        # actor-less system setup, fully reproducible from GROUP_PRESETS, so the
        # per-permission audit rows are noise. Admin edits to groups afterward
        # are still audited normally.
        with disable_auditlog():
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
                        # Admin gets every permission a tenant may hold — which is not
                        # literally every row: Django's own admin perms are excluded.
                        group.permissions.set(grantable_permissions())
                    else:
                        group.permissions.set(
                            grantable_permissions(preset['permissions']))

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
    def sync_permissions(cls, dry_run=False):
        """
        Bring preset-backed TenantGroups up to their preset, keeping admins' additions
        (user ruling 2026-11-17).

        For each group whose NAME matches a preset: the preset's permissions it lacks
        are added; a permission is removed only when the preset granted it once and
        no longer does (`presets.RETIRED_PRESET_PERMISSIONS`), so moving a permission
        out of a role still takes effect on existing tenants. Anything else a tenant
        admin added stays. Permissions no tenant group may hold (Django's admin ones)
        are always removed — the repair path for groups that got one from an old filter.

        Custom groups — and a preset group renamed, which no longer matches its
        preset by name — are skipped: they keep their grants and get no preset updates.

        Runs on every migrate (apps.setup_defaults) and from `sync_tenant_permissions`.
        Returns a dict with grant/revoke counters.
        """
        from Tracker.models import TenantGroup
        from Tracker.presets import (
            GROUP_PRESETS, RETIRED_PRESET_PERMISSIONS, grantable_permissions,
        )

        preset_by_name = {preset['name']: preset for preset in GROUP_PRESETS.values()}
        all_perm_ids = set(grantable_permissions().values_list('id', flat=True))
        retired_ids = {
            name: set(grantable_permissions(codenames).values_list('id', flat=True))
            for name, codenames in RETIRED_PRESET_PERMISSIONS.items()}

        results = {
            'groups_inspected': 0,
            'groups_updated': 0,
            'groups_skipped_custom': 0,
            'permissions_added': 0,
            'permissions_removed': 0,
        }

        for group in TenantGroup.objects.all():
            results['groups_inspected'] += 1
            preset = preset_by_name.get(group.name)
            if not preset:
                results['groups_skipped_custom'] += 1
                continue

            if preset['permissions'] == '__all__':
                desired_ids = all_perm_ids
            else:
                desired_ids = set(
                    grantable_permissions(preset['permissions'])
                    .values_list('id', flat=True)
                )

            existing_ids = set(group.permissions.values_list('id', flat=True))
            missing_ids = desired_ids - existing_ids
            # Revoked: what this preset retired (and doesn't grant again), and anything
            # no tenant group may hold. An admin's own additions stay.
            retired = retired_ids.get(group.name, set()) - desired_ids
            extra_ids = (existing_ids & retired) | (existing_ids - all_perm_ids)
            if not missing_ids and not extra_ids:
                continue

            results['permissions_added'] += len(missing_ids)
            results['permissions_removed'] += len(extra_ids)
            results['groups_updated'] += 1
            if not dry_run:
                if missing_ids:
                    group.permissions.add(*missing_ids)
                if extra_ids:
                    group.permissions.remove(*extra_ids)

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
        from Tracker.presets import GROUP_PRESETS, grantable_permissions

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
                group.permissions.set(grantable_permissions())
            else:
                group.permissions.set(grantable_permissions(preset['permissions']))

            results['groups_updated'] += 1

        return results
