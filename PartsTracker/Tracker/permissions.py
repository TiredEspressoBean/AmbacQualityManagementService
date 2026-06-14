"""
Tenant-scoped DRF permission classes for PartsTracker.

Group -> permission definitions live in `Tracker.presets.GROUP_PRESETS`
(seeded onto TenantGroup via GroupSeeder / `sync_tenant_permissions`).
This module holds only the DRF permission classes that enforce tenant
access and tenant-scoped model permissions via `user.has_tenant_perm()`.
"""




# =============================================================================
# DRF PERMISSION CLASSES (Tenant-Scoped)
# =============================================================================

from rest_framework.permissions import BasePermission


class TenantAccessPermission(BasePermission):
    """
    Enforces tenant access control for API-authenticated requests.

    This permission class closes a security gap where middleware-level tenant
    access checks don't work for DRF token/JWT authentication (because DRF
    authentication happens after middleware runs).

    The middleware already handles session-authenticated users, but for API
    clients using tokens, this permission ensures they can only access tenants
    they belong to.

    Access is granted if:
    1. Running in dedicated mode (all users share one tenant)
    2. No tenant context on request (let other permissions handle)
    3. User is not authenticated (let IsAuthenticated handle)
    4. User is superuser or SaaS-vendor staff
    5. Tenant is user's home tenant (user.tenant)
    6. User has a UserRole in a TenantGroup belonging to that tenant

    Add to DEFAULT_PERMISSION_CLASSES or specific viewsets.
    """

    message = "You don't have permission to access this tenant."

    def has_permission(self, request, view):
        from django.conf import settings as django_settings

        # In dedicated mode, tenant isolation isn't enforced - all users share one tenant
        if getattr(django_settings, 'DEDICATED_MODE', False):
            return True

        # If no tenant context, skip this check (other permissions will handle)
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return True

        # Unauthenticated requests should be handled by IsAuthenticated
        if not request.user or not request.user.is_authenticated:
            return True  # Let IsAuthenticated handle this

        return self._user_can_access_tenant(request.user, tenant)

    def _user_can_access_tenant(self, user, tenant):
        """Check if user has access to the specified tenant."""
        # Superusers and staff can access any tenant (for support)
        if user.is_superuser or user.is_staff:
            return True

        # Check if it's the user's home tenant
        if hasattr(user, 'tenant') and user.tenant == tenant:
            return True

        # Check if user has any group membership in this tenant (via UserRole)
        from Tracker.models import UserRole
        return UserRole.objects.filter(
            user=user,
            group__tenant=tenant
        ).exists()


class AllowAnyWithTenantAccess(TenantAccessPermission):
    """
    Allows unauthenticated access but enforces tenant access for authenticated users.

    Use this for endpoints like /api/tenant/current/ that need to:
    - Allow unauthenticated requests (for deployment info, login page, etc.)
    - Block authenticated users from accessing other tenants (SaaS mode only)

    This combines AllowAny behavior with TenantAccessPermission.
    In dedicated mode, all users share one tenant so access is always allowed.
    """

    def has_permission(self, request, view):
        from django.conf import settings as django_settings

        # In dedicated mode, tenant isolation isn't enforced
        if getattr(django_settings, 'DEDICATED_MODE', False):
            return True

        # Unauthenticated requests are allowed
        if not request.user or not request.user.is_authenticated:
            return True

        # For authenticated users, enforce tenant access
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return True  # No tenant context, allow

        return self._user_can_access_tenant(request.user, tenant)


class TenantPermission(BasePermission):
    """
    Base class for tenant-scoped permissions.

    Checks permissions against TenantGroup.permissions instead of
    Django's global auth.Permission system.

    Tenant resolution is handled automatically by User._resolve_tenant():
    - Dedicated mode: TenantMiddleware sets user._current_tenant to default tenant
    - SaaS mode: TenantMiddleware sets user._current_tenant from header/subdomain

    Permission classes just call user.has_tenant_perm() - no special handling needed.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superuser bypasses all checks
        if request.user.is_superuser:
            return True

        return True  # Base class allows access; subclasses add restrictions


class TenantModelPermissions(TenantPermission):
    """
    Tenant-scoped model permissions for DRF viewsets.

    Maps HTTP methods to permission codenames:
    - GET/HEAD/OPTIONS -> view_{model}
    - POST -> add_{model}
    - PUT/PATCH -> change_{model}
    - DELETE -> delete_{model}

    Optionally, viewsets can declare action-specific permissions via an
    `action_permissions` attribute. These are checked ADDITIVELY on top of
    the CRUD perm (both must pass). The dict maps DRF action names to a
    list of required permission codenames.

    Usage:
        class OrderViewSet(viewsets.ModelViewSet):
            permission_classes = [TenantModelPermissions]
            queryset = Orders.objects.all()

            # Optional: action-level gates on top of CRUD
            action_permissions = {
                'approve': ['approve_orders'],
                'close':   ['close_orders'],
            }

    Viewsets without `action_permissions` behave exactly as the CRUD-only
    case; actions not listed in the dict fall through to CRUD-only.

    The model name is derived from view.queryset.model._meta.model_name.
    """

    # Map HTTP methods to permission action prefixes
    perms_map = {
        'GET': 'view',
        'OPTIONS': 'view',
        'HEAD': 'view',
        'POST': 'add',
        'PUT': 'change',
        'PATCH': 'change',
        'DELETE': 'delete',
    }

    def get_required_permission(self, request, view):
        """
        Get the permission codename required for this request.

        Returns permission like 'add_orders', 'view_parts', etc.
        """
        # Get action prefix from HTTP method
        action = self.perms_map.get(request.method)
        if not action:
            return None

        # Get model name from view
        if hasattr(view, 'get_queryset'):
            try:
                model = view.get_queryset().model
            except Exception:
                model = getattr(view, 'queryset', None)
                if model is not None:
                    model = model.model
        else:
            model = getattr(view, 'queryset', None)
            if model is not None:
                model = model.model

        if model is None:
            return None

        model_name = model._meta.model_name
        return f"{action}_{model_name}"

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        action = getattr(view, 'action', None)
        action_permissions = getattr(view, 'action_permissions', None) or {}
        required = action_permissions.get(action) or []

        # CRUD gate (HTTP method → view/add/change/delete_{model}).
        #
        # Skipped for actions in `crud_exempt_actions`: some custom
        # @action endpoints don't map cleanly onto the model's CRUD
        # perms. e.g. POST /submit-response/ would demand
        # `add_approvalrequest` (because POST → add), but an approver
        # responding to a request is NOT creating one — they
        # legitimately lack that perm. For those, the declarative
        # `action_permissions` entry is the sole, sufficient gate.
        crud_exempt = getattr(view, 'crud_exempt_actions', None) or set()
        if action not in crud_exempt:
            perm = self.get_required_permission(request, view)
            if perm and not request.user.has_tenant_perm(perm):
                return False

        # Action-specific gate. Additive on top of CRUD for normal
        # actions; the only gate for crud-exempt ones.
        if required and not request.user.has_tenant_perms(required):
            return False

        return True


class RequirePermission(TenantPermission):
    """
    Decorator-style permission that requires specific permission(s).

    Usage as class:
        permission_classes = [RequirePermission('approve_capa')]

    Usage in view for inline check:
        if not RequirePermission.check(request.user, 'approve_capa'):
            raise PermissionDenied()
    """

    def __init__(self, *perms):
        self.required_perms = perms

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return request.user.has_tenant_perms(self.required_perms)

    @classmethod
    def check(cls, user, *perms):
        """
        Utility method for inline permission checks.

        Usage:
            if not RequirePermission.check(request.user, 'approve_capa'):
                raise PermissionDenied("You don't have permission to approve CAPAs")
        """
        if user.is_superuser:
            return True
        return user.has_tenant_perms(perms)
