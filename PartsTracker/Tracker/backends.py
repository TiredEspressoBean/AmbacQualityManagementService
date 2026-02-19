"""
Custom authentication backends for tenant-scoped permissions.

This module provides the TenantPermissionBackend which resolves user permissions
based on their group memberships within the current tenant context.
"""

from django.contrib.auth.backends import ModelBackend


class TenantPermissionBackend(ModelBackend):
    """
    Authentication backend that resolves permissions via TenantGroupMembership.

    Extends Django's ModelBackend to look up group permissions through the
    tenant-scoped TenantGroupMembership model instead of User.groups M2M.

    Usage:
        Replace ModelBackend in AUTHENTICATION_BACKENDS in settings.py:
        AUTHENTICATION_BACKENDS = [
            'Tracker.backends.TenantPermissionBackend',
            'allauth.account.auth_backends.AuthenticationBackend',
        ]

    Tenant context determined by:
        1. user._current_tenant (set by middleware)
        2. user.tenant (fallback)

    Superusers bypass all permission checks (standard Django behavior).
    """

    def _get_user_permissions(self, user_obj):
        """Get permissions directly assigned to the user."""
        return user_obj.user_permissions.all()

    def _get_group_permissions(self, user_obj):
        """
        Get permissions from user's TenantGroups via UserRole.
        """
        from Tracker.models import UserRole
        from django.contrib.auth.models import Permission

        tenant = getattr(user_obj, '_current_tenant', None) or getattr(user_obj, 'tenant', None)

        if not tenant:
            return Permission.objects.none()

        # Get TenantGroups the user belongs to via UserRole
        tenant_group_ids = UserRole.objects.filter(
            user=user_obj,
            group__tenant=tenant
        ).values_list('group_id', flat=True)

        # Get permissions from those TenantGroups
        from Tracker.models import TenantGroup
        return Permission.objects.filter(tenant_groups__id__in=tenant_group_ids).distinct()

    def get_all_permissions(self, user_obj, obj=None):
        """Return all permissions for the user."""
        if not user_obj.is_active or user_obj.is_anonymous:
            return set()

        tenant = getattr(user_obj, '_current_tenant', None) or getattr(user_obj, 'tenant', None)
        tenant_id = str(tenant.id) if tenant else 'none'
        cache_key = f'_tenant_perm_cache_{tenant_id}'

        if not hasattr(user_obj, cache_key):
            perms = set()

            perms.update(
                f"{p.content_type.app_label}.{p.codename}"
                for p in self._get_user_permissions(user_obj)
            )

            perms.update(
                f"{p.content_type.app_label}.{p.codename}"
                for p in self._get_group_permissions(user_obj)
            )

            setattr(user_obj, cache_key, perms)

        return getattr(user_obj, cache_key)

    def has_perm(self, user_obj, perm, obj=None):
        """Check if user has a specific permission."""
        if not user_obj.is_active:
            return False

        if user_obj.is_superuser:
            return True

        return perm in self.get_all_permissions(user_obj, obj)


def set_tenant_context(user, tenant):
    """
    Set the current tenant context on a user object.

    Call from middleware or views when tenant context is established.
    """
    user._current_tenant = tenant
    # Clear cached permissions when tenant changes
    for attr in list(vars(user).keys()):
        if attr.startswith('_tenant_perm_cache_'):
            delattr(user, attr)
