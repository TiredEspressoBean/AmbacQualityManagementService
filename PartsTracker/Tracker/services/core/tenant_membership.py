"""Per-tenant membership: the source of truth for tenant access.

See ``Tracker.models.TenantMembership`` for the model rationale. This module
centralizes the access check (previously duplicated and divergent between
``TenantMiddleware`` and the DRF auth classes) and the membership lifecycle
(ensure / suspend / reactivate), plus a backfill used by the data migration.
"""
from __future__ import annotations

from django.utils import timezone


def user_is_tenant_member(user, tenant) -> bool:
    """Return True if *user* may access *tenant*.

    - Superusers / SaaS-vendor staff: always (cross-tenant support access).
    - Otherwise: an ACTIVE ``TenantMembership`` must exist.

    Self-heals: if no membership row exists yet but the user qualifies under
    the legacy derivation (home tenant, or a ``UserRole`` in the tenant), an
    ACTIVE membership is created lazily so access is preserved during and after
    rollout. A SUSPENDED row is authoritative — access is denied even for the
    user's home tenant (that is the whole point of per-tenant suspension).
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    if tenant is None:
        return False

    from Tracker.models import TenantMembership

    membership = TenantMembership.objects.filter(user=user, tenant=tenant).first()
    if membership is not None:
        return membership.status == TenantMembership.Status.ACTIVE

    # No row yet — fall back to the legacy derivation and heal forward.
    if _legacy_has_access(user, tenant):
        ensure_membership(
            user, tenant, is_home=(getattr(user, 'tenant_id', None) == tenant.id)
        )
        return True
    return False


def _legacy_has_access(user, tenant) -> bool:
    from Tracker.models import UserRole

    if getattr(user, 'tenant_id', None) == tenant.id:
        return True
    return UserRole.objects.filter(user=user, group__tenant=tenant).exists()


def ensure_membership(user, tenant, *, is_home: bool = False):
    """Idempotently ensure an ACTIVE membership exists for (user, tenant).

    Does NOT reactivate a SUSPENDED row — suspension is sticky until an admin
    explicitly reactivates. Only promotes ``is_home`` when asserted.
    """
    from Tracker.models import TenantMembership

    membership, created = TenantMembership.objects.get_or_create(
        user=user, tenant=tenant,
        defaults={'status': TenantMembership.Status.ACTIVE, 'is_home': is_home},
    )
    if not created and is_home and not membership.is_home:
        membership.is_home = True
        membership.save(update_fields=['is_home', 'updated_at'])
    return membership


def suspend_membership(user, tenant, *, by=None):
    """Suspend *user*'s access to *tenant* (tenant-scoped; account stays active).

    Creates a SUSPENDED row if none exists, so the suspension is durable even
    for a user who previously had only legacy-derived (home/role) access.
    """
    from Tracker.models import TenantMembership

    membership, _ = TenantMembership.objects.get_or_create(
        user=user, tenant=tenant,
        defaults={'is_home': (getattr(user, 'tenant_id', None) == tenant.id)},
    )
    membership.status = TenantMembership.Status.SUSPENDED
    membership.suspended_at = timezone.now()
    membership.suspended_by = by
    membership.save(update_fields=['status', 'suspended_at', 'suspended_by', 'updated_at'])
    _clear_perm_cache(user, tenant)
    return membership


def reactivate_membership(user, tenant):
    """Restore *user*'s access to *tenant*."""
    from Tracker.models import TenantMembership

    membership, _ = TenantMembership.objects.get_or_create(
        user=user, tenant=tenant,
        defaults={'is_home': (getattr(user, 'tenant_id', None) == tenant.id)},
    )
    membership.status = TenantMembership.Status.ACTIVE
    membership.suspended_at = None
    membership.suspended_by = None
    membership.save(update_fields=['status', 'suspended_at', 'suspended_by', 'updated_at'])
    _clear_perm_cache(user, tenant)
    return membership


def member_user_ids(tenant):
    """User ids with a membership (any status) in *tenant* — for list scoping.

    Returns all members, suspended included, so a tenant admin can still see and
    reactivate a suspended user.
    """
    from Tracker.models import TenantMembership

    return TenantMembership.objects.filter(tenant=tenant).values_list('user_id', flat=True)


def _clear_perm_cache(user, tenant):
    try:
        from Tracker.services.core.user import clear_user_permission_cache
        clear_user_permission_cache(user, tenant)
    except Exception:  # cache clearing is best-effort, never block the write
        pass


def backfill_memberships(User=None, UserRole=None, TenantMembership=None) -> int:
    """Create membership rows from the legacy derivation (home FK + UserRoles).

    Idempotent. Used by the data migration (which passes historical model
    classes) and by tests/manual runs (which use the real models). Returns the
    number of rows created.
    """
    if User is None:
        from django.contrib.auth import get_user_model
        User = get_user_model()
    if UserRole is None or TenantMembership is None:
        from Tracker.models import UserRole as _UR, TenantMembership as _TM
        UserRole = UserRole or _UR
        TenantMembership = TenantMembership or _TM

    created = 0
    # Home memberships (one per user with a home tenant).
    for user_id, tenant_id in (
        User.objects.exclude(tenant__isnull=True).values_list('id', 'tenant_id')
    ):
        _, was_created = TenantMembership.objects.get_or_create(
            user_id=user_id, tenant_id=tenant_id,
            defaults={'status': 'ACTIVE', 'is_home': True},
        )
        created += int(was_created)

    # Role-derived memberships (consultants / cross-tenant members).
    for user_id, tenant_id in (
        UserRole.objects.values_list('user_id', 'group__tenant_id').distinct()
    ):
        if tenant_id is None:
            continue
        _, was_created = TenantMembership.objects.get_or_create(
            user_id=user_id, tenant_id=tenant_id,
            defaults={'status': 'ACTIVE'},
        )
        created += int(was_created)

    return created
