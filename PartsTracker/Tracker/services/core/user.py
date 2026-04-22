"""
User aggregate services.

State transitions and group-membership mutations for the User model.

Pure accessors (display_name, has_group, get_tenant_groups, etc.) and
private helpers (_resolve_tenant) stay on the model.
"""
from __future__ import annotations

from django.core.cache import cache


def deactivate_user(user) -> None:
    """Set user.is_active = False and persist."""
    user.is_active = False
    user.save()


def reactivate_user(user) -> None:
    """Set user.is_active = True and persist."""
    user.is_active = True
    user.save()


def clear_user_permission_cache(user, tenant=None) -> None:
    """Delete the cached permission set for this user in the given tenant.

    Call after any role or group-permission change.
    """
    tenant = tenant or user.tenant
    if tenant:
        cache.delete(f'user_{user.id}_tenant_{tenant.id}_perms')


def add_user_to_tenant_group(user, group_or_name, tenant=None, granted_by=None):
    """Add *user* to a TenantGroup within *tenant*.

    Args:
        user: User instance.
        group_or_name: TenantGroup instance or group name string.
        tenant: Tenant instance. Defaults to user's resolved tenant.
        granted_by: User who granted the membership (for audit trail).

    Returns:
        UserRole instance (created or existing).

    Raises:
        ValueError: If tenant cannot be resolved.
        TenantGroup.DoesNotExist: If group_name does not exist in tenant.
    """
    from Tracker.models import TenantGroup, UserRole

    tenant = user._resolve_tenant(tenant)
    if not tenant:
        raise ValueError("Tenant must be specified for group membership")

    if isinstance(group_or_name, str):
        group = TenantGroup.objects.get(name=group_or_name, tenant=tenant)
    else:
        group = group_or_name

    role, _ = UserRole.objects.get_or_create(
        user=user,
        group=group,
        defaults={'granted_by': granted_by},
    )
    if hasattr(user, '_cached_tenant_group_names'):
        delattr(user, '_cached_tenant_group_names')
    clear_user_permission_cache(user, tenant)
    return role


def remove_user_from_tenant_group(user, group_or_name, tenant=None) -> int:
    """Remove *user* from a TenantGroup within *tenant*.

    Args:
        user: User instance.
        group_or_name: TenantGroup instance or group name string.
        tenant: Tenant instance. Defaults to user's resolved tenant.

    Returns:
        Number of role assignments deleted (0 or 1).
    """
    from Tracker.models import UserRole

    tenant = user._resolve_tenant(tenant)
    if not tenant:
        return 0

    if isinstance(group_or_name, str):
        filter_kwargs = {'user': user, 'group__name': group_or_name, 'group__tenant': tenant}
    else:
        filter_kwargs = {'user': user, 'group': group_or_name}

    deleted_count, _ = UserRole.objects.filter(**filter_kwargs).delete()
    if hasattr(user, '_cached_tenant_group_names'):
        delattr(user, '_cached_tenant_group_names')
    clear_user_permission_cache(user, tenant)
    return deleted_count


def grant_group_to_user(user, group_name, tenant=None, granted_by=None):
    """Add *user* to a TenantGroup, creating the group if it does not exist.

    Preferred over add_user_to_tenant_group when callers use group name
    constants (Groups.PRODUCTION_OPERATOR, etc.) and auto-creation is
    acceptable.

    Args:
        user: User instance.
        group_name: Group name string.
        tenant: Tenant instance. Defaults to user's resolved tenant.
        granted_by: User who granted the membership (for audit trail).

    Returns:
        Tuple of (UserRole, created_boolean).

    Raises:
        ValueError: If tenant cannot be resolved.
    """
    from Tracker.models import TenantGroup, UserRole

    tenant = user._resolve_tenant(tenant)
    if not tenant:
        raise ValueError("Tenant must be specified for group membership")

    group, _ = TenantGroup.objects.get_or_create(
        name=group_name,
        tenant=tenant,
        defaults={'description': f'Auto-created group: {group_name}', 'is_custom': True},
    )

    role, created = UserRole.objects.get_or_create(
        user=user,
        group=group,
        defaults={'granted_by': granted_by},
    )
    if hasattr(user, '_cached_tenant_group_names'):
        delattr(user, '_cached_tenant_group_names')
    clear_user_permission_cache(user, tenant)
    return role, created


def revoke_group_from_user(user, group_name, tenant=None) -> int:
    """Remove *user* from *group_name* in *tenant*.

    Thin alias for remove_user_from_tenant_group with consistent naming.

    Returns:
        Number of memberships deleted (0 or 1).
    """
    return remove_user_from_tenant_group(user, group_name, tenant)
