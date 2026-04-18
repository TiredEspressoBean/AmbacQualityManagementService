"""
Phase 2a regression tests — ContextVar infrastructure.

Tests the contract for the application-layer tenant ContextVar:
- tenant_context() sets and resets it
- TenantMiddleware sets and resets it per request
- ContextVar isolation between requests (reset always runs)
- unscoped and all_tenants managers exist and bypass tenant filtering
  (when Phase 2b lands auto-scoping, these stay no-filter by contract)

Phase 2a does NOT flip SecureManager.get_queryset() to auto-scope. That's
Phase 2b. These tests lock the infrastructure contract so 2b can safely
assume the ContextVar is always populated inside a request/tenant_context.
"""
from django.test import RequestFactory, TestCase

from Tracker.middleware import TenantMiddleware
from Tracker.models import Orders
from Tracker.tests.base import TenantTestCase
from Tracker.utils.tenant_context import (
    current_tenant_var,
    get_current_tenant_id,
    reset_current_tenant,
    set_current_tenant_id,
    tenant_context,
)


class TenantContextVarInfrastructureTests(TestCase):
    """Basic contract tests for the ContextVar helpers — no DB required."""

    def setUp(self):
        # Ensure clean state before each test; reset any leaked token from
        # a prior test's scope
        # ContextVar defaults to None, so an explicit set/reset pair here
        # just confirms the default.
        self.assertIsNone(current_tenant_var.get())

    def test_set_and_reset(self):
        token = set_current_tenant_id('abc-123')
        try:
            self.assertEqual(get_current_tenant_id(), 'abc-123')
        finally:
            reset_current_tenant(token)
        self.assertIsNone(get_current_tenant_id())

    def test_nested_set_and_reset(self):
        """Nested set/reset must unwind to the outer value."""
        outer_token = set_current_tenant_id('outer-tenant')
        try:
            inner_token = set_current_tenant_id('inner-tenant')
            try:
                self.assertEqual(get_current_tenant_id(), 'inner-tenant')
            finally:
                reset_current_tenant(inner_token)
            self.assertEqual(get_current_tenant_id(), 'outer-tenant')
        finally:
            reset_current_tenant(outer_token)
        self.assertIsNone(get_current_tenant_id())

    def test_tenant_context_sets_and_resets(self):
        with tenant_context('ctx-tenant'):
            self.assertEqual(get_current_tenant_id(), 'ctx-tenant')
        self.assertIsNone(get_current_tenant_id())

    def test_tenant_context_none_yields_none(self):
        with tenant_context(None):
            self.assertIsNone(get_current_tenant_id())
        self.assertIsNone(get_current_tenant_id())

    def test_tenant_context_resets_on_exception(self):
        """A raising block must still reset the ContextVar."""
        class _Boom(Exception):
            pass

        with self.assertRaises(_Boom):
            with tenant_context('raising-tenant'):
                self.assertEqual(get_current_tenant_id(), 'raising-tenant')
                raise _Boom('simulated failure')
        self.assertIsNone(get_current_tenant_id())


class TenantMiddlewareContextVarTests(TenantTestCase):
    """TenantMiddleware must set the ContextVar during the request and
    restore the prior value after.

    TenantTestCase.setUp sets the ContextVar to tenant_a (so tests can
    query SecureModels without explicit context). These tests verify the
    middleware nests correctly: it switches to the request's tenant
    during the view and restores the prior (outer) value after.
    """

    def test_middleware_sets_contextvar_for_resolved_tenant(self):
        """Inside get_response, ContextVar is set to the request's tenant;
        after response, restored to the outer (setUp-provided) value."""
        factory = RequestFactory()
        observed_during: list = []

        def get_response(request):
            observed_during.append(get_current_tenant_id())
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = TenantMiddleware(get_response)

        # Outer state: tenant_a (set by TenantTestCase.setUp).
        outer_value = get_current_tenant_id()
        self.assertEqual(outer_value, str(self.tenant_a.id))

        # Middleware switches to tenant_b for the duration of the request.
        request = factory.get(
            '/api/Orders/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id),
        )
        request.user = self.superuser  # can access any tenant
        middleware(request)

        # During request: ContextVar was tenant_b's id.
        self.assertEqual(len(observed_during), 1)
        self.assertEqual(observed_during[0], str(self.tenant_b.id))

        # Post-request: ContextVar restored to the outer value.
        self.assertEqual(get_current_tenant_id(), outer_value)

    def test_middleware_resets_contextvar_on_exception(self):
        """If the view raises, middleware still restores the prior ContextVar."""
        factory = RequestFactory()

        class _ViewBoom(Exception):
            pass

        def raising_view(request):
            raise _ViewBoom('view failed')

        middleware = TenantMiddleware(raising_view)
        request = factory.get(
            '/api/Orders/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id),
        )
        request.user = self.superuser  # can access any tenant

        outer_value = get_current_tenant_id()
        with self.assertRaises(_ViewBoom):
            middleware(request)
        # ContextVar restored to the outer (pre-middleware) value.
        self.assertEqual(get_current_tenant_id(), outer_value)

    def test_exempt_path_does_not_change_contextvar(self):
        """Admin/health/etc. paths skip middleware resolution entirely —
        the ContextVar stays at whatever the outer scope has set."""
        factory = RequestFactory()
        observed_during: list = []

        def get_response(request):
            observed_during.append(get_current_tenant_id())
            from django.http import HttpResponse
            return HttpResponse('ok')

        middleware = TenantMiddleware(get_response)
        request = factory.get('/admin/')
        request.user = self.superuser  # can access any tenant

        outer_value = get_current_tenant_id()
        middleware(request)
        # Exempt path: no attempt to set/reset the ContextVar.
        self.assertEqual(observed_during[0], outer_value)
        self.assertEqual(get_current_tenant_id(), outer_value)


class TenantScopedPrimaryKeyRelatedFieldTests(TenantTestCase):
    """Verify TenantScopedPrimaryKeyRelatedField rejects cross-tenant PKs
    at validation time regardless of RLS state."""

    def test_cross_tenant_fk_fails_validation(self):
        """A request body referencing a foreign-tenant PK must fail
        DRF validation even when the base queryset is `unscoped`."""
        from rest_framework.exceptions import ValidationError
        from Tracker.models import Companies
        from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

        # Use `unscoped.create` to create a company in tenant_b without
        # touching the current (tenant_a) ContextVar set by setUp.
        company_b = Companies.unscoped.create(
            tenant=self.tenant_b,
            name='Tenant B Company',
        )

        field = TenantScopedPrimaryKeyRelatedField(
            queryset=Companies.unscoped.all(),
        )
        # setUp set ContextVar to tenant_a; validating a tenant_b PK
        # must fail because the field re-scopes its queryset.
        with self.assertRaises(ValidationError):
            field.to_internal_value(str(company_b.id))

    def test_same_tenant_fk_passes_validation(self):
        """A PK belonging to the current tenant resolves successfully."""
        from Tracker.models import Companies
        from Tracker.serializers.fields import TenantScopedPrimaryKeyRelatedField

        company_a = Companies.unscoped.create(
            tenant=self.tenant_a,
            name='Tenant A Company',
        )

        field = TenantScopedPrimaryKeyRelatedField(
            queryset=Companies.unscoped.all(),
        )
        resolved = field.to_internal_value(str(company_a.id))
        self.assertEqual(resolved.pk, company_a.pk)


class SecureModelManagersTests(TestCase):
    """`unscoped` and `all_tenants` managers exist on every SecureModel subclass."""

    def test_orders_has_all_three_managers(self):
        self.assertTrue(hasattr(Orders, 'objects'))
        self.assertTrue(hasattr(Orders, 'unscoped'))
        self.assertTrue(hasattr(Orders, 'all_tenants'))

    def test_unscoped_and_all_tenants_are_plain_managers(self):
        from django.db.models import Manager
        # Both are plain managers — they deliberately do NOT filter.
        # In Phase 2b `objects` (SecureManager) will auto-scope; these
        # two stay no-filter as the designated escape hatches.
        self.assertIsInstance(Orders.unscoped, Manager)
        self.assertIsInstance(Orders.all_tenants, Manager)

    def test_base_manager_is_unscoped(self):
        """Django's `_base_manager` is used for related-object lookups and
        by third-party tools like django-auditlog. We point it at
        `unscoped` so Phase 2b's auto-scoping on `objects` doesn't affect
        Django internals that bypass application logic."""
        # _meta.base_manager_name is only set literally on the concrete
        # model; we set it on the abstract SecureModel so it's inherited
        # via _meta.base_manager itself.
        self.assertEqual(Orders._meta.base_manager.name, 'unscoped')
