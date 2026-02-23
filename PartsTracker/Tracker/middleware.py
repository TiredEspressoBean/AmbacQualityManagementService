"""
Tenant middleware for multi-tenancy support.

Resolves the current tenant from the request and makes it available
throughout the request lifecycle.

Behavior varies by DEPLOYMENT_MODE:
- saas: Full resolution (header -> subdomain -> user)
- dedicated: Always use DEFAULT_TENANT_SLUG

Response Headers:
- X-Tenant-Context: slug of the resolved tenant (for debugging)
- X-Tenant-Source: how the tenant was resolved (header/subdomain/user/default)
"""

import logging
from django.db import connection
from django.http import Http404, JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class TenantResolutionError(Exception):
    """Raised when tenant resolution fails in a way that should block the request."""
    pass


class TenantMiddleware:
    """
    Middleware that resolves tenant from request and sets up tenant context.

    In SaaS mode, resolution order:
    1. X-Tenant-ID header (for API clients, testing)
    2. Subdomain (acme.example.com -> tenant slug "acme")
    3. User's default tenant (if authenticated)

    In dedicated/demo mode:
    - Directly use the configured default/demo tenant

    Also sets up PostgreSQL RLS context for database-level isolation.
    """

    # Paths that don't require tenant context (auth, health checks, admin)
    TENANT_EXEMPT_PATHS = [
        '/health/',
        '/ready/',
        '/api/health/',
        '/api/auth/',
        '/admin/',
        '/accounts/',
        '/__reload__/',
        '/api/schema/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self._default_tenant = None  # Cached for dedicated/demo modes

    def __call__(self, request):
        # Skip tenant resolution for exempt paths
        if self._is_exempt_path(request.path):
            request.tenant = None
            request.tenant_source = None
            return self.get_response(request)

        # Resolve tenant based on deployment mode
        try:
            tenant, source = self._resolve_tenant(request)
        except TenantResolutionError as e:
            # Explicit tenant request that user cannot access - return 403
            return JsonResponse(
                {
                    'detail': str(e),
                    'code': 'tenant_access_denied',
                },
                status=403
            )

        request.tenant = tenant
        request.tenant_source = source  # 'header', 'subdomain', 'user', 'default', or None

        # Add deployment mode info to request for convenience
        request.deployment_mode = getattr(settings, 'DEPLOYMENT_MODE', 'dedicated')
        request.is_demo = tenant.is_demo if tenant else False

        # Set tenant context on user for permission checks
        if request.user.is_authenticated:
            request.user._current_tenant = tenant

        # Set up RLS context if tenant resolved and RLS is enabled
        if tenant and getattr(settings, 'ENABLE_RLS', False):
            self._set_rls_context(tenant)

        response = self.get_response(request)

        # Add tenant context headers to response for debugging/transparency
        # Only add headers if response supports it (has __setitem__)
        if tenant and hasattr(response, '__setitem__'):
            response['X-Tenant-Context'] = tenant.slug
            response['X-Tenant-Source'] = source or 'unknown'

        return response

    def _is_exempt_path(self, path):
        """Check if path is exempt from tenant requirement."""
        return any(path.startswith(exempt) for exempt in self.TENANT_EXEMPT_PATHS)

    def _resolve_tenant(self, request):
        """
        Resolve tenant from request using multiple strategies.

        In dedicated mode, always returns the default tenant.
        In SaaS mode, uses header -> subdomain -> user fallback.

        Returns:
            Tuple of (Tenant instance or None, source string or None)
            Source is one of: 'header', 'subdomain', 'user', 'default', None

        Raises:
            TenantResolutionError: If user explicitly requests a tenant via header
                                   that they don't have access to. This prevents
                                   silent fallback that could mask client bugs.
        """
        from Tracker.models import Tenant

        # Dedicated mode: always use the configured default tenant
        if getattr(settings, 'DEDICATED_MODE', False):
            return self._get_default_tenant(), 'default'

        # SaaS mode: full resolution

        # 1. Check X-Tenant-ID header (useful for API clients and testing)
        tenant_header = request.headers.get('X-Tenant-ID')
        if tenant_header:
            tenant = self._get_tenant_by_id_or_slug(tenant_header)
            if tenant is None:
                # Header specified but tenant not found - fail explicitly
                raise TenantResolutionError(
                    f"Tenant '{tenant_header}' not found or inactive. "
                    f"Check the X-Tenant-ID header value."
                )

            # Security check: verify user can access this tenant
            # Note: For API clients, authentication may happen after middleware (in DRF views).
            # We trust the header for unauthenticated requests - views will enforce auth.
            # For authenticated users, we verify tenant access.
            if request.user.is_authenticated and not self._user_can_access_tenant(request.user, tenant):
                logger.warning(
                    f"User {request.user.username} "
                    f"attempted to access tenant {tenant.slug} without permission"
                )
                # Fail explicitly instead of silent fallback
                raise TenantResolutionError(
                    f"Access denied to tenant '{tenant.slug}'. "
                    f"You don't have permission to access this tenant."
                )

            logger.debug(f"Tenant resolved from header: {tenant.slug}")
            return tenant, 'header'

        # 2. Check subdomain
        tenant = self._get_tenant_from_subdomain(request)
        if tenant:
            logger.debug(f"Tenant resolved from subdomain: {tenant.slug}")
            return tenant, 'subdomain'

        # 3. Fall back to user's tenant (if authenticated)
        if request.user.is_authenticated and hasattr(request.user, 'tenant'):
            tenant = request.user.tenant
            if tenant and tenant.is_active:
                logger.debug(f"Tenant resolved from user: {tenant.slug}")
                return tenant, 'user'

        # No tenant resolved - this is OK for some paths
        logger.debug("No tenant resolved for request")
        return None, None

    def _get_default_tenant(self):
        """
        Get or create the default tenant for dedicated mode.

        Caches the tenant instance to avoid repeated DB queries.
        """
        from Tracker.models import Tenant

        # Return cached tenant if available
        if self._default_tenant is not None:
            return self._default_tenant

        slug = getattr(settings, 'DEFAULT_TENANT_SLUG', 'default')
        name = getattr(settings, 'DEFAULT_TENANT_NAME', 'My Company')

        # Get or create the default tenant
        tenant, created = Tenant.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'tier': Tenant.Tier.PRO,
                'status': Tenant.Status.ACTIVE,
                'is_active': True,
                'is_demo': False,
            }
        )

        if created:
            logger.info(f"Auto-created default tenant: {tenant.slug} (dedicated mode)")

        # Cache for subsequent requests
        self._default_tenant = tenant
        return tenant

    def _get_tenant_by_id_or_slug(self, identifier):
        """Get tenant by ID (UUID) or slug."""
        from Tracker.models import Tenant
        import uuid

        try:
            # Try as UUID first
            tenant_id = uuid.UUID(identifier)
            return Tenant.objects.filter(id=tenant_id, is_active=True).first()
        except (ValueError, TypeError):
            # Try as slug
            return Tenant.objects.filter(slug=identifier, is_active=True).first()

    def _user_can_access_tenant(self, user, tenant):
        """
        Check if user is allowed to access the specified tenant.

        Access is granted if:
        1. User is a superuser (can access any tenant)
        2. Tenant is the user's home tenant (user.tenant)
        3. User has a TenantGroupMembership for that tenant

        Returns True if access is allowed, False otherwise.
        """
        # Anonymous users cannot use header to select tenant
        if not user.is_authenticated:
            return False

        # Superusers can access any tenant
        if user.is_superuser:
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

    def _get_tenant_from_subdomain(self, request):
        """Extract tenant from subdomain."""
        from Tracker.models import Tenant

        host = request.get_host().split(':')[0]  # Remove port if present

        # Get base domain from settings (e.g., "example.com")
        base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', None)

        if base_domain and host.endswith(base_domain):
            # Extract subdomain: "acme.example.com" -> "acme"
            subdomain = host[:-len(base_domain)].rstrip('.')
            if subdomain and subdomain not in ['www', 'api']:
                return Tenant.objects.filter(slug=subdomain, is_active=True).first()

        # For local development without subdomains
        if settings.DEBUG:
            # In debug mode, check query param for easy testing
            tenant_slug = request.GET.get('_tenant')
            if tenant_slug:
                return Tenant.objects.filter(slug=tenant_slug, is_active=True).first()

        return None

    def _set_rls_context(self, tenant):
        """
        Set PostgreSQL session variable for Row-Level Security.

        This requires ATOMIC_REQUESTS=True and a non-superuser database role.

        When ENABLE_RLS=True, failures will raise an exception to prevent
        requests from proceeding without tenant isolation.
        """
        try:
            with connection.cursor() as cursor:
                # SET LOCAL only lasts for the current transaction
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(tenant.id)]
                )
        except Exception as e:
            logger.error(f"Failed to set RLS context for tenant {tenant.slug}: {e}")
            # ENABLE_RLS=True means strict enforcement - fail the request
            raise RuntimeError(
                f"RLS context setup failed. Request blocked to prevent "
                f"cross-tenant data access. Error: {e}"
            ) from e


class TenantStatusMiddleware:
    """
    Middleware that blocks requests for suspended or inactive tenants.

    Returns 403 Forbidden if tenant is suspended or pending deletion.
    Use this after TenantMiddleware in the middleware stack.
    """

    # Paths that should work even for suspended tenants (billing, support)
    SUSPENSION_EXEMPT_PATHS = [
        '/api/tenant/current/',  # Need to see why suspended
        '/api/tenant/billing/',  # Need to pay to unsuspend
        '/api/auth/',  # Need to log in to see status
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.http import JsonResponse

        tenant = getattr(request, 'tenant', None)

        if tenant and not self._is_tenant_accessible(tenant):
            # Check if path is exempt
            if not any(request.path.startswith(p) for p in self.SUSPENSION_EXEMPT_PATHS):
                logger.warning(f"Blocked request for suspended tenant: {tenant.slug}")
                return JsonResponse(
                    {
                        'detail': f'Tenant is {tenant.status}. Please contact support.',
                        'status': tenant.status,
                        'tenant': tenant.slug,
                    },
                    status=403
                )

        return self.get_response(request)

    def _is_tenant_accessible(self, tenant):
        """Check if tenant is in an accessible state."""
        from Tracker.models import Tenant
        return tenant.status in [Tenant.Status.ACTIVE, Tenant.Status.TRIAL]


class TenantRequiredMiddleware:
    """
    Optional stricter middleware that returns 404 if no tenant is resolved.

    Use this in addition to TenantMiddleware if you want to enforce
    tenant requirement on all non-exempt paths.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check after TenantMiddleware has run
        if not hasattr(request, 'tenant'):
            return self.get_response(request)

        # If tenant is None and path is not exempt, return 404
        if request.tenant is None:
            exempt_paths = TenantMiddleware.TENANT_EXEMPT_PATHS
            if not any(request.path.startswith(p) for p in exempt_paths):
                logger.warning(f"No tenant for non-exempt path: {request.path}")
                raise Http404("Tenant not found")

        return self.get_response(request)
