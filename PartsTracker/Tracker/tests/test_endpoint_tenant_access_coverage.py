"""
Coverage guard: every DRF endpoint that serves tenant-scoped data must enforce
the tenant-membership backstop (`TenantAccessPermission` or a subclass).

Why this exists
---------------
`TenantMiddleware` trusts the `X-Tenant-ID` header to resolve the request
tenant. For session auth the middleware validates membership, but for DRF
token auth the user isn't known until *after* middleware runs, so the header
is trusted unconditionally at that point. `TenantAccessPermission` is the
control that re-checks membership once the user is authenticated. It's in the
global DEFAULT_PERMISSION_CLASSES, but any view that overrides
`permission_classes` silently drops it — which is exactly the bug this audit
found (TenantScopedMixin, several `[IsAuthenticated]` viewsets).

This walks the live URLconf, finds every DRF view whose model is tenant-scoped
(has a `tenant` FK), and fails if it neither enforces the backstop nor is
explicitly allow-listed. New endpoints are safe-by-default (inherit the global
default); the test only bites when someone overrides `permission_classes` and
forgets the backstop.

Limitation: the model is detected from `queryset`/`serializer_class.Meta.model`.
A view that returns tenant data via raw queries with no detectable model won't
be seen here — those need a manual eye. Non-DRF (legacy `Tracker/views.py`)
endpoints are session-auth and out of scope.
"""

from django.apps import apps
from django.test import SimpleTestCase
from django.urls import get_resolver

from Tracker.permissions import TenantAccessPermission


# View classes that serve tenant-scoped data but legitimately do NOT need the
# membership backstop. Each entry must carry a reason.
ALLOWLISTED_VIEWS = {
    # Admin/staff-only endpoints. IsAdminUser already restricts to staff, and
    # staff are intentionally allowed cross-tenant access (support) — the same
    # bypass TenantAccessPermission itself grants. Backstop would be redundant.
    "IntegrationConfigViewSet",
    "IntegrationSyncLogViewSet",
    "HubSpotPipelineStageViewSet",
    "TenantViewSet",
    # dj-rest-auth's /auth/user/ — serializes request.user (self) only, never a
    # cross-tenant query, and is a third-party view we don't control.
    "UserDetailsView",
}


class EndpointTenantAccessCoverageTests(SimpleTestCase):
    @staticmethod
    def _has_tenant_fk(model):
        if model is None:
            return False
        return any(
            getattr(f, "related_model", None) is not None
            and f.related_model.__name__ == "Tenant"
            and f.name == "tenant"
            for f in model._meta.get_fields()
        )

    @staticmethod
    def _view_model(cls):
        qs = getattr(cls, "queryset", None)
        if qs is not None and hasattr(qs, "model"):
            return qs.model
        sc = getattr(cls, "serializer_class", None)
        meta = getattr(sc, "Meta", None) if sc is not None else None
        return getattr(meta, "model", None)

    @staticmethod
    def _enforces_backstop(perms):
        return any(
            isinstance(p, type) and issubclass(p, TenantAccessPermission)
            for p in (perms or [])
        )

    def _iter_view_routes(self):
        """Yield (view_cls, effective_permission_classes) for every DRF route.

        Effective perms honor per-`@action` overrides, which the router stores
        in the callback's initkwargs; otherwise the class-level list applies.
        """
        seen = set()

        def walk(patterns):
            for p in patterns:
                if hasattr(p, "url_patterns"):
                    yield from walk(p.url_patterns)
                    continue
                cls = getattr(p.callback, "cls", None)
                if cls is None:
                    continue
                initkwargs = getattr(p.callback, "initkwargs", {}) or {}
                perms = initkwargs.get("permission_classes", getattr(cls, "permission_classes", []))
                key = (cls, tuple(perms))
                if key in seen:
                    continue
                seen.add(key)
                yield cls, perms

        yield from walk(get_resolver().url_patterns)

    def test_tenant_data_endpoints_enforce_membership_backstop(self):
        offenders = []
        for cls, perms in self._iter_view_routes():
            if cls.__name__ in ALLOWLISTED_VIEWS:
                continue
            model = self._view_model(cls)
            if not self._has_tenant_fk(model):
                continue
            if self._enforces_backstop(perms):
                continue
            offenders.append(
                f"{cls.__name__} (model={model.__name__}) "
                f"perms={[getattr(p, '__name__', p) for p in perms]}"
            )

        if offenders:
            self.fail(
                "DRF endpoints serving tenant-scoped data without the tenant "
                "membership backstop (TenantAccessPermission). These trust the "
                "X-Tenant-ID header from token clients unconditionally — a "
                "cross-tenant leak.\n\n"
                "Fix: add TenantAccessPermission to the view's permission_classes "
                "(or stop overriding permission_classes so it inherits the global "
                "default). If access is legitimately not tenant-bound, add the "
                "view to ALLOWLISTED_VIEWS with a reason.\n\nOffenders:\n  "
                + "\n  ".join(sorted(set(offenders)))
            )

    def test_allowlist_has_no_stale_entries(self):
        """Every allow-listed name must still resolve to a discovered view, so
        the allowlist can't silently rot."""
        discovered = {cls.__name__ for cls, _ in self._iter_view_routes()}
        stale = ALLOWLISTED_VIEWS - discovered
        if stale:
            self.fail(
                "ALLOWLISTED_VIEWS entries no longer match any endpoint — "
                "remove them:\n  " + "\n  ".join(sorted(stale))
            )
