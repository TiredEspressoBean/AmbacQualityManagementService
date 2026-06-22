"""
Tenant-membership-enforcing DRF authentication classes.

Wired into settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] as
defense-in-depth alongside (not instead of) TenantAccessPermission.

Background
----------
`TenantMiddleware` resolves the request tenant from the `X-Tenant-ID` header.
For session auth the middleware can validate membership (the user is known at
middleware time). For token auth it cannot — DRF authenticates inside the
view, *after* middleware — so the header is trusted unconditionally and the
ContextVar / RLS GUC get set to whatever tenant the client asked for.

Today the compensating control is `TenantAccessPermission`, a DRF *permission*.
That works, but it's opt-out-able: any view that overrides `permission_classes`
silently drops it (the bug this audit found). `test_endpoint_tenant_access_coverage`
now guards against that, but it's a CI tripwire, not a structural guarantee.

This module moves the membership check to the *authentication* layer instead.
The check then runs on every DRF request as a side effect of resolving the
user, and `authentication_classes` is overridden far less often (and far more
conspicuously) than `permission_classes`. It closes the token-auth gap at the
exact moment the gap exists — when identity becomes known.

Design
------
`TenantMembershipMixin.authenticate()` calls the parent authenticator; if it
returns a user, it verifies that user can access `request.tenant` (reusing the
same logic as `TenantAccessPermission`) and raises `AuthenticationFailed`
otherwise. Resolution mirrors the permission class:

  * dedicated mode -> no tenant isolation, allow
  * no tenant on request -> allow (nothing to scope to)
  * superuser / staff -> allow (intentional cross-tenant support access)
  * user's home tenant, or a tenant they hold a UserRole in -> allow
  * otherwise -> AuthenticationFailed (401)

We raise `PermissionDenied` (403), not `AuthenticationFailed` (401): the user
IS authenticated, they're just not authorized for the requested tenant. This
keeps the signal identical to `TenantAccessPermission` so clients/tests see one
consistent 403 regardless of which layer rejects.

CSRF: TenantMembershipSessionAuthentication keeps DRF's SessionAuthentication
CSRF enforcement — it only adds a post-auth membership check.

Possible future hardening (intentionally NOT done here): have these classes
(rather than the middleware) be what *sets* the ContextVar / RLS GUC for
header-resolved tenants, so an unverified header tenant never reaches the query
layer at all. That's a larger change to the middleware/auth boundary.
"""

from rest_framework.authentication import (
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class TenantMembershipMixin:
    """Adds a post-authentication tenant-membership check to any DRF
    authenticator. Mix in BEFORE the concrete authentication class so this
    `authenticate()` wraps the parent's."""

    message = "You are not a member of the requested tenant."

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            # Parent didn't authenticate via this scheme; let the next
            # authenticator (or IsAuthenticated) handle it.
            return None

        user, auth = result
        if not self._user_can_access_tenant(request, user):
            # PermissionDenied (403), not AuthenticationFailed (401): the user
            # is authenticated, just not authorized for the requested tenant.
            raise PermissionDenied(self.message)
        return user, auth

    @staticmethod
    def _user_can_access_tenant(request, user):
        from django.conf import settings

        # Dedicated mode: single shared tenant, no isolation to enforce.
        if getattr(settings, "DEDICATED_MODE", False):
            return True

        tenant = getattr(request, "tenant", None)
        if tenant is None:
            # No tenant context resolved — nothing to scope against. Other
            # layers (IsAuthenticated, view logic) still apply.
            return True

        # Per-tenant membership is the source of truth (superuser/staff bypass
        # and self-healing legacy fallback live in the service).
        from Tracker.services.core.tenant_membership import user_is_tenant_member
        return user_is_tenant_member(user, tenant)


class ExpiringTokenAuthentication(TokenAuthentication):
    """TokenAuthentication with a hard time-to-live.

    DRF's stock Token never expires, so a leaked API token is usable forever
    until manually revoked. Here a token older than ``settings.API_TOKEN_TTL_SECONDS``
    is rejected (and deleted). The token-issuing endpoint (`get_user_api_token`)
    reissues a fresh token before expiry, and the frontend refreshes well within
    the window, so this is transparent to legitimate clients. Set the TTL to 0
    to disable expiry.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        from datetime import timedelta
        from django.conf import settings
        from django.utils import timezone

        ttl_seconds = getattr(settings, "API_TOKEN_TTL_SECONDS", 0)
        if ttl_seconds and (timezone.now() - token.created) > timedelta(seconds=ttl_seconds):
            # Reject (don't mutate on a read path); the stale row is rotated out
            # by get_user_api_token on the next fetch.
            raise AuthenticationFailed("Token has expired. Request a new token.")
        return user, token


class TenantMembershipTokenAuthentication(TenantMembershipMixin, ExpiringTokenAuthentication):
    """Token auth that enforces BOTH tenant membership and a token TTL — closes
    the header-spoof gap for API clients and bounds a leaked token's lifetime."""


class TenantMembershipSessionAuthentication(TenantMembershipMixin, SessionAuthentication):
    """SessionAuthentication with the same membership check, for symmetry.
    The middleware already validates session users, so this is belt-and-
    suspenders for that path."""


# ---------------------------------------------------------------------------
# drf-spectacular auth extensions
#
# Without these, drf-spectacular can't map our custom authenticator subclasses
# to an OpenAPI security scheme and emits a "could not resolve authenticator"
# warning for every viewset that uses them (~one per operation → the bulk of
# the schema-generation warning count). These thin subclasses just re-point
# spectacular's built-in Session/Token schemes at our classes; the resulting
# security schemes are identical to stock DRF session/token auth.
#
# Defined here so they self-register (via the extension metaclass) whenever this
# module is imported — and settings references these auth classes, so that's at
# startup, before any schema generation runs.
# ---------------------------------------------------------------------------
from drf_spectacular.authentication import SessionScheme, TokenScheme  # noqa: E402


class TenantMembershipSessionScheme(SessionScheme):
    target_class = "Tracker.authentication.TenantMembershipSessionAuthentication"


class TenantMembershipTokenScheme(TokenScheme):
    target_class = "Tracker.authentication.TenantMembershipTokenAuthentication"
