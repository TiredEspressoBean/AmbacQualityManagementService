from django.test import TestCase
from django.db import connections
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from Tracker.utils.tenant_context import (
    set_current_tenant_id,
    reset_current_tenant,
)


class VectorTestCase(TestCase):
    """
    Custom TestCase that ensures pgvector extension is available.
    Use this as the base class for any tests that depend on vector fields.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure vector extension exists in test database
        with connections['default'].cursor() as cursor:
            try:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS vector')
            except Exception as e:
                print(f"Warning: Could not create vector extension: {e}")
                # Tests will be skipped via @skipIf decorator if extension unavailable


class TenantTestCase(VectorTestCase):
    """
    Base TestCase for multi-tenancy tests.

    Provides:
    - Two pre-created tenants (tenant_a, tenant_b)
    - Users for each tenant (user_a, user_b)
    - A superuser without tenant
    - API client with helper methods for tenant context

    Usage:
        class MyTenantTest(TenantTestCase):
            def test_something(self):
                self.authenticate_as(self.user_a, self.tenant_a)
                response = self.client.get('/api/Orders/')
                ...
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        from Tracker.models import Tenant

        # Tenant itself is not a SecureModel, so its default manager does
        # not auto-scope. Create tenants first so we have an id to set the
        # ContextVar to.
        self.tenant_a = Tenant.objects.create(
            name="Tenant A",
            slug="tenant-a",
            tier="PRO"
        )
        self.tenant_b = Tenant.objects.create(
            name="Tenant B",
            slug="tenant-b",
            tier="STARTER"
        )

        # Set the tenant ContextVar so any SecureManager queries during
        # the test auto-scope to tenant_a. Tests that need to query as
        # tenant_b can call self.switch_tenant_context(self.tenant_b).
        self._tenant_cv_token = set_current_tenant_id(self.tenant_a.id)

        User = get_user_model()

        # Create users for each tenant
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a
        )
        self.user_b = User.objects.create_user(
            username='user_b',
            email='user_b@tenant-b.com',
            password='testpass123',
            tenant=self.tenant_b
        )

        # Create superuser (no tenant)
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Set up API client
        self.client = APIClient()

    def tearDown(self):
        # Reset the tenant ContextVar so it doesn't leak into the next
        # test. Using a per-test token keeps nested contexts safe.
        token = getattr(self, '_tenant_cv_token', None)
        if token is not None:
            reset_current_tenant(token)
            self._tenant_cv_token = None
        super().tearDown()

    def switch_tenant_context(self, tenant):
        """Switch the ContextVar to a different tenant mid-test. Returns
        a token the caller can pass to reset_current_tenant if they want
        to revert. Useful when a test needs to query as tenant_b after
        setUp established tenant_a as default."""
        return set_current_tenant_id(tenant.id if tenant else None)

    def authenticate_as(self, user, tenant=None):
        """
        Authenticate the API client as a user with optional tenant context.

        Args:
            user: The user to authenticate as
            tenant: Optional tenant to set in X-Tenant-ID header.
                    If None, uses user's tenant.
        """
        self.client.force_authenticate(user=user)
        tenant = tenant or getattr(user, 'tenant', None)
        if tenant:
            self.client.credentials(HTTP_X_TENANT_ID=str(tenant.id))
        else:
            # Clear tenant header
            self.client.credentials()

    def authenticate_superuser(self, tenant=None):
        """
        Authenticate as superuser with optional tenant filter.

        Args:
            tenant: Optional tenant to filter results (superusers see all by default)
        """
        self.client.force_authenticate(user=self.superuser)
        if tenant:
            self.client.credentials(HTTP_X_TENANT_ID=str(tenant.id))

    def create_for_tenant(self, model_class, tenant, **kwargs):
        """
        Helper to create a model instance for a specific tenant.

        Uses `unscoped` so the create succeeds regardless of which tenant
        the test's ContextVar currently points at. The caller specifies
        the owning tenant explicitly via the `tenant` argument.

        Args:
            model_class: The Django model class
            tenant: The tenant to assign
            **kwargs: Fields for the model

        Returns:
            The created model instance
        """
        manager = getattr(model_class, 'unscoped', model_class.objects)
        return manager.create(tenant=tenant, **kwargs)

    def grant_tenant_permissions(self, user, tenant, permissions):
        """
        Grant permissions to a user within a tenant by creating a TenantGroup.

        Creates a test group with the specified permissions and assigns the user.

        Args:
            user: The user to grant permissions to
            tenant: The tenant context
            permissions: List of permission codenames (e.g., ['view_orders', 'add_orders'])

        Returns:
            The created TenantGroup
        """
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole

        # Create a test group for this user
        group = TenantGroup.objects.create(
            tenant=tenant,
            name=f"TestGroup_{user.username}_{tenant.slug}",
            description="Test group for permission testing",
            is_custom=True
        )

        # Add permissions
        perms = Permission.objects.filter(codename__in=permissions)
        group.permissions.add(*perms)

        # Assign user to group
        UserRole.objects.create(user=user, group=group)

        # Clear permission cache
        from django.core.cache import cache
        cache.delete(f'user_{user.id}_tenant_{tenant.id}_perms')

        return group

    def grant_full_staff_access(self, user, tenant):
        """
        Grant a user full staff access within a tenant.

        Includes full_tenant_access and common CRUD permissions.

        Args:
            user: The user to grant access to
            tenant: The tenant context

        Returns:
            The created TenantGroup
        """
        staff_permissions = [
            'full_tenant_access',
            # Orders
            'view_orders', 'add_orders', 'change_orders', 'delete_orders',
            # Parts
            'view_parts', 'add_parts', 'change_parts', 'delete_parts',
            # Companies
            'view_companies', 'add_companies', 'change_companies', 'delete_companies',
            # PartTypes
            'view_parttypes', 'add_parttypes', 'change_parttypes', 'delete_parttypes',
            # WorkOrders
            'view_workorder', 'add_workorder', 'change_workorder', 'delete_workorder',
        ]
        return self.grant_tenant_permissions(user, tenant, staff_permissions)
