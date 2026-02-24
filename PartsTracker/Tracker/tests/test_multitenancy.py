"""
Tests for multi-tenancy functionality.

This module tests:
1. TenantMiddleware - tenant resolution from various sources
2. TenantScopedMixin - queryset filtering and auto-assignment
3. Cross-tenant data isolation - ensuring tenants can't see each other's data
4. RLS policies (when enabled) - database-level isolation
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, RequestFactory, override_settings
from django.db import connection
from rest_framework.test import APIClient
from rest_framework import status
from unittest import skipIf

from Tracker.models import Tenant, Orders, PartTypes, Companies, CAPA, TenantGroupMembership, TenantGroup, UserRole
from Tracker.middleware import TenantMiddleware
from Tracker.tests.base import VectorTestCase


def is_vector_extension_available():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            return cursor.fetchone() is not None
    except Exception:
        return False


def is_rls_enabled():
    """Check if Row-Level Security is enabled in settings."""
    from django.conf import settings
    return getattr(settings, 'ENABLE_RLS', False)


User = get_user_model()


class TenantModelTestCase(TestCase):
    """Tests for the Tenant model itself."""

    def test_tenant_creation(self):
        """Test creating a tenant with required fields."""
        tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme"
        )
        self.assertEqual(tenant.name, "Acme Corporation")
        self.assertEqual(tenant.slug, "acme")
        self.assertEqual(tenant.tier, "starter")  # Default
        self.assertTrue(tenant.is_active)
        self.assertIsNotNone(tenant.id)  # UUID7

    def test_tenant_slug_uniqueness(self):
        """Test that tenant slugs must be unique."""
        Tenant.objects.create(name="Tenant 1", slug="unique-slug")
        with self.assertRaises(Exception):  # IntegrityError
            Tenant.objects.create(name="Tenant 2", slug="unique-slug")

    def test_tenant_tiers(self):
        """Test tenant tier choices."""
        for tier in ['starter', 'pro', 'enterprise']:
            tenant = Tenant.objects.create(
                name=f"{tier.title()} Tenant",
                slug=f"{tier}-tenant",
                tier=tier
            )
            self.assertEqual(tenant.tier, tier)

    def test_tenant_settings_json(self):
        """Test tenant settings JSON field."""
        tenant = Tenant.objects.create(
            name="Custom Tenant",
            slug="custom",
            settings={
                "feature_flags": {"spc_enabled": True},
                "branding": {"primary_color": "#FF0000"}
            }
        )
        self.assertEqual(tenant.settings["feature_flags"]["spc_enabled"], True)


@override_settings(DEDICATED_MODE=False)
class TenantMiddlewareTestCase(TestCase):
    """Tests for TenantMiddleware tenant resolution."""

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TenantMiddleware(lambda r: r)

        # Create tenants
        self.tenant_acme = Tenant.objects.create(name="Acme Corp", slug="acme")
        self.tenant_globex = Tenant.objects.create(name="Globex Inc", slug="globex")

        # Create users
        self.user_acme = User.objects.create_user(
            username='acme_user',
            email='user@acme.com',
            password='testpass',
            tenant=self.tenant_acme
        )
        self.user_globex = User.objects.create_user(
            username='globex_user',
            email='user@globex.com',
            password='testpass',
            tenant=self.tenant_globex
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass'
        )

    def test_resolve_tenant_from_header_uuid(self):
        """Test tenant resolution from X-Tenant-ID header with UUID."""
        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = str(self.tenant_acme.id)
        request.user = self.user_acme

        self.middleware(request)

        self.assertEqual(request.tenant, self.tenant_acme)
        self.assertEqual(request.tenant_source, 'header')

    def test_resolve_tenant_from_header_slug(self):
        """Test tenant resolution from X-Tenant-ID header with slug."""
        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = 'globex'
        request.user = self.user_globex

        self.middleware(request)

        self.assertEqual(request.tenant, self.tenant_globex)
        self.assertEqual(request.tenant_source, 'header')

    def test_resolve_tenant_from_user(self):
        """Test tenant resolution from authenticated user's tenant."""
        request = self.factory.get('/api/Orders/')
        request.user = self.user_acme

        self.middleware(request)

        self.assertEqual(request.tenant, self.tenant_acme)
        self.assertEqual(request.tenant_source, 'user')

    def test_exempt_paths_no_tenant(self):
        """Test that exempt paths don't require tenant."""
        exempt_paths = ['/api/health/', '/api/auth/login/', '/admin/', '/accounts/']

        for path in exempt_paths:
            request = self.factory.get(path)
            request.user = self.superuser

            self.middleware(request)

            self.assertIsNone(request.tenant)

    def test_inactive_tenant_not_resolved(self):
        """Test that inactive tenants are not resolved via header."""
        self.tenant_acme.is_active = False
        self.tenant_acme.save()

        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = str(self.tenant_acme.id)
        request.user = self.superuser

        response = self.middleware(request)

        # Should return 403 - inactive tenant via explicit header request
        self.assertEqual(response.status_code, 403)
        self.assertIn('not found', response.content.decode())

    @override_settings(TENANT_BASE_DOMAIN='example.com', ALLOWED_HOSTS=['acme.example.com'])
    def test_resolve_tenant_from_subdomain(self):
        """Test tenant resolution from subdomain."""
        request = self.factory.get('/api/Orders/', HTTP_HOST='acme.example.com')
        request.user = self.superuser

        self.middleware(request)

        self.assertEqual(request.tenant, self.tenant_acme)
        self.assertEqual(request.tenant_source, 'subdomain')

    def test_header_blocked_for_unauthorized_tenant(self):
        """Test that users cannot access tenants they don't belong to via header."""
        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = str(self.tenant_globex.id)
        request.user = self.user_acme  # User belongs to acme, not globex

        response = self.middleware(request)

        # Should return 403 Forbidden, not silently fall back
        self.assertEqual(response.status_code, 403)
        self.assertIn('tenant_access_denied', response.content.decode())

    def test_header_allowed_for_authorized_tenant(self):
        """Test that users CAN access tenants they have membership in via header."""
        # Give user_acme membership in tenant_globex via UserRole + TenantGroup
        operator_group = TenantGroup.objects.create(
            tenant=self.tenant_globex,
            name='Production_Operator'
        )
        UserRole.objects.create(
            user=self.user_acme,
            group=operator_group
        )

        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = str(self.tenant_globex.id)
        request.user = self.user_acme

        self.middleware(request)

        # Header should work - user has membership in globex
        self.assertEqual(request.tenant, self.tenant_globex)
        self.assertEqual(request.tenant_source, 'header')

    def test_superuser_can_access_any_tenant_via_header(self):
        """Test that superusers can access any tenant via header."""
        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = str(self.tenant_globex.id)
        request.user = self.superuser  # Superuser with no tenant

        self.middleware(request)

        # Superuser should be able to access any tenant
        self.assertEqual(request.tenant, self.tenant_globex)
        self.assertEqual(request.tenant_source, 'header')

    def test_invalid_tenant_header_returns_403(self):
        """Test that an invalid tenant ID in header returns 403, not silent failure."""
        request = self.factory.get('/api/Orders/')
        request.META['HTTP_X_TENANT_ID'] = 'nonexistent-tenant-slug'
        request.user = self.user_acme

        response = self.middleware(request)

        # Should return 403 with clear error message
        self.assertEqual(response.status_code, 403)
        self.assertIn('not found', response.content.decode())


@skipIf(not is_vector_extension_available(), "Vector extension not available")
@override_settings(DEDICATED_MODE=False)
class TenantScopedViewSetTestCase(VectorTestCase):
    """Tests for TenantScopedMixin queryset filtering."""

    def setUp(self):
        # Create tenants
        self.tenant_acme = Tenant.objects.create(name="Acme Corp", slug="acme")
        self.tenant_globex = Tenant.objects.create(name="Globex Inc", slug="globex")

        # Create users (us_person=True prevents ITAR warning noise in tests)
        self.user_acme = User.objects.create_user(
            username='acme_user',
            email='user@acme.com',
            password='testpass',
            tenant=self.tenant_acme
        )
        self.user_acme.us_person = True
        self.user_acme.save(update_fields=['us_person'])

        self.user_globex = User.objects.create_user(
            username='globex_user',
            email='user@globex.com',
            password='testpass',
            tenant=self.tenant_globex
        )
        self.user_globex.us_person = True
        self.user_globex.save(update_fields=['us_person'])

        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass'
        )

        # Create companies for each tenant
        self.company_acme = Companies.objects.create(
            tenant=self.tenant_acme,
            name="Acme Supplier"
        )
        self.company_globex = Companies.objects.create(
            tenant=self.tenant_globex,
            name="Globex Supplier"
        )

        # Create part types for each tenant
        self.parttype_acme = PartTypes.objects.create(
            tenant=self.tenant_acme,
            name="Acme Widget",
            ID_prefix="ACM"
        )
        self.parttype_globex = PartTypes.objects.create(
            tenant=self.tenant_globex,
            name="Globex Gadget",
            ID_prefix="GLX"
        )

        # Create orders for each tenant
        self.order_acme = Orders.objects.create(
            tenant=self.tenant_acme,
            name="Acme Order 001",
            company=self.company_acme
        )
        self.order_globex = Orders.objects.create(
            tenant=self.tenant_globex,
            name="Globex Order 001",
            company=self.company_globex
        )

        # Grant full staff access to test users for multitenancy testing
        # (These tests focus on data isolation, not permission logic)
        # Uses TenantGroup + UserRole with full_tenant_access for full visibility
        from Tracker.models import TenantGroup, UserRole
        from django.contrib.auth.models import Permission

        staff_permissions = [
            'full_tenant_access',
            'view_orders', 'add_orders', 'change_orders', 'delete_orders',
            'view_parts', 'add_parts', 'change_parts', 'delete_parts',
            'view_companies', 'add_companies', 'change_companies', 'delete_companies',
            'view_parttypes', 'add_parttypes', 'change_parttypes', 'delete_parttypes',
            'view_workorder', 'add_workorder', 'change_workorder', 'delete_workorder',
        ]

        # Create staff group for Acme tenant
        acme_group = TenantGroup.objects.create(
            tenant=self.tenant_acme,
            name="Staff",
            description="Staff group for testing",
            is_custom=True
        )
        acme_group.permissions.add(*Permission.objects.filter(codename__in=staff_permissions))
        UserRole.objects.create(user=self.user_acme, group=acme_group)

        # Create staff group for Globex tenant
        globex_group = TenantGroup.objects.create(
            tenant=self.tenant_globex,
            name="Staff",
            description="Staff group for testing",
            is_custom=True
        )
        globex_group.permissions.add(*Permission.objects.filter(codename__in=staff_permissions))
        UserRole.objects.create(user=self.user_globex, group=globex_group)

        self.client = APIClient()

    def test_user_sees_only_own_tenant_orders(self):
        """Test that users only see orders from their tenant."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        response = self.client.get('/api/Orders/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_names = [o['name'] for o in response.data['results']]
        self.assertIn("Acme Order 001", order_names)
        self.assertNotIn("Globex Order 001", order_names)

    def test_user_cannot_access_other_tenant_order(self):
        """Test that users cannot access specific orders from other tenants."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        # Try to access globex's order
        response = self.client.get(f'/api/Orders/{self.order_globex.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_superuser_sees_all_tenants_by_default(self):
        """Test that superusers can see all tenants' data."""
        self.client.force_authenticate(user=self.superuser)

        response = self.client.get('/api/Orders/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_names = [o['name'] for o in response.data['results']]
        self.assertIn("Acme Order 001", order_names)
        self.assertIn("Globex Order 001", order_names)

    def test_superuser_can_filter_by_tenant(self):
        """Test that superusers can filter by specific tenant."""
        self.client.force_authenticate(user=self.superuser)

        response = self.client.get(f'/api/Orders/?tenant={self.tenant_acme.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_names = [o['name'] for o in response.data['results']]
        self.assertIn("Acme Order 001", order_names)
        self.assertNotIn("Globex Order 001", order_names)

    def test_create_order_auto_assigns_tenant(self):
        """Test that creating an order auto-assigns the user's tenant."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        response = self.client.post('/api/Orders/', {
            'name': 'New Acme Order',
            'company': self.company_acme.id,
            'order_status': 'PENDING',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_order = Orders.objects.get(id=response.data['id'])
        self.assertEqual(new_order.tenant, self.tenant_acme)

    def test_tenant_injection_blocked_on_create(self):
        """Test that users cannot inject a different tenant_id in POST body."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        # Try to create order with globex's tenant_id in the body
        response = self.client.post('/api/Orders/', {
            'name': 'Malicious Order',
            'company': self.company_acme.id,
            'order_status': 'PENDING',
            'tenant': str(self.tenant_globex.id),  # Attempted injection
        }, format='json')

        # Should succeed but with user's tenant, not the injected one
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_order = Orders.objects.get(id=response.data['id'])
        self.assertEqual(new_order.tenant, self.tenant_acme)  # NOT globex

    def test_user_sees_only_own_tenant_companies(self):
        """Test tenant isolation for Companies."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        response = self.client.get('/api/Companies/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        company_names = [c['name'] for c in response.data['results']]
        self.assertIn("Acme Supplier", company_names)
        self.assertNotIn("Globex Supplier", company_names)

    def test_user_sees_only_own_tenant_part_types(self):
        """Test tenant isolation for PartTypes."""
        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        response = self.client.get('/api/PartTypes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [pt['name'] for pt in response.data['results']]
        self.assertIn("Acme Widget", names)
        self.assertNotIn("Globex Gadget", names)

    def test_archived_orders_hidden_by_default(self):
        """Test that archived orders are hidden by default, visible with include_archived=true."""
        # Archive one of acme's orders
        self.order_acme.archived = True
        self.order_acme.save(update_fields=['archived'])

        # Verify it's actually archived
        self.order_acme.refresh_from_db()
        self.assertTrue(self.order_acme.archived, "Order should be archived")

        self.client.force_authenticate(user=self.user_acme)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_acme.id))

        # Without filter - archived orders are HIDDEN by default
        response = self.client.get('/api/Orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_names = [o['name'] for o in response.data['results']]
        self.assertNotIn("Acme Order 001", order_names)  # Hidden by default

        # With include_archived=true - archived orders are visible
        response = self.client.get('/api/Orders/?include_archived=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_names = [o['name'] for o in response.data['results']]
        self.assertIn("Acme Order 001", order_names)  # Visible when requested


@skipIf(not is_vector_extension_available(), "Vector extension not available")
@override_settings(DEDICATED_MODE=False)
class TenantDataIsolationTestCase(VectorTestCase):
    """End-to-end tests for complete data isolation between tenants."""

    def setUp(self):
        # Create tenants
        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b")

        # Create users (us_person=True prevents ITAR warning noise in tests)
        self.user_a = User.objects.create_user(
            username='user_a', email='a@test.com', password='testpass',
            tenant=self.tenant_a
        )
        self.user_a.us_person = True
        self.user_a.save(update_fields=['us_person'])

        self.user_b = User.objects.create_user(
            username='user_b', email='b@test.com', password='testpass',
            tenant=self.tenant_b
        )
        self.user_b.us_person = True
        self.user_b.save(update_fields=['us_person'])

        # Create test data for Tenant A
        self.company_a = Companies.objects.create(
            tenant=self.tenant_a, name="Company A"
        )
        self.parttype_a = PartTypes.objects.create(
            tenant=self.tenant_a, name="Part Type A", ID_prefix="PTA"
        )
        self.order_a = Orders.objects.create(
            tenant=self.tenant_a,
            name="Order A",
            company=self.company_a
        )

        # Create test data for Tenant B
        self.company_b = Companies.objects.create(
            tenant=self.tenant_b, name="Company B"
        )
        self.parttype_b = PartTypes.objects.create(
            tenant=self.tenant_b, name="Part Type B", ID_prefix="PTB"
        )
        self.order_b = Orders.objects.create(
            tenant=self.tenant_b,
            name="Order B",
            company=self.company_b
        )

        # Grant staff permissions via TenantGroup + UserRole
        staff_permissions = [
            'full_tenant_access',
            'view_orders', 'add_orders', 'change_orders', 'delete_orders',
        ]

        # Create staff group for Tenant A
        group_a = TenantGroup.objects.create(
            tenant=self.tenant_a,
            name="Staff",
            description="Staff group for testing",
            is_custom=True
        )
        group_a.permissions.add(*Permission.objects.filter(codename__in=staff_permissions))
        UserRole.objects.create(user=self.user_a, group=group_a)

        # Create staff group for Tenant B
        group_b = TenantGroup.objects.create(
            tenant=self.tenant_b,
            name="Staff",
            description="Staff group for testing",
            is_custom=True
        )
        group_b.permissions.add(*Permission.objects.filter(codename__in=staff_permissions))
        UserRole.objects.create(user=self.user_b, group=group_b)

        self.client = APIClient()

    def test_full_isolation_orders(self):
        """Test complete isolation of Orders between tenants."""
        # User A's view
        self.client.force_authenticate(user=self.user_a)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))
        response_a = self.client.get('/api/Orders/')

        self.assertEqual(len(response_a.data['results']), 1)
        self.assertEqual(response_a.data['results'][0]['name'], "Order A")

        # User B's view
        self.client.force_authenticate(user=self.user_b)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_b.id))
        response_b = self.client.get('/api/Orders/')

        self.assertEqual(len(response_b.data['results']), 1)
        self.assertEqual(response_b.data['results'][0]['name'], "Order B")

    def test_cross_tenant_update_blocked(self):
        """Test that users cannot update other tenant's data."""
        self.client.force_authenticate(user=self.user_a)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

        # Try to update Tenant B's order
        response = self.client.patch(
            f'/api/Orders/{self.order_b.id}/',
            {'name': 'Hacked Order'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify order wasn't changed
        self.order_b.refresh_from_db()
        self.assertEqual(self.order_b.name, "Order B")

    def test_cross_tenant_delete_blocked(self):
        """Test that users cannot delete other tenant's data."""
        self.client.force_authenticate(user=self.user_a)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant_a.id))

        # Try to delete Tenant B's order
        response = self.client.delete(f'/api/Orders/{self.order_b.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify order still exists
        self.assertTrue(Orders.objects.filter(id=self.order_b.id).exists())


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class TenantSequenceGeneratorTestCase(VectorTestCase):
    """Tests for tenant-scoped sequence generators (CAPA numbers, etc.)."""

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b")

        self.user_a = User.objects.create_user(
            username='user_a', email='a@test.com', password='testpass',
            tenant=self.tenant_a
        )
        self.user_b = User.objects.create_user(
            username='user_b', email='b@test.com', password='testpass',
            tenant=self.tenant_b
        )

    def test_capa_numbers_unique_per_tenant(self):
        """Test that CAPA numbers are unique within tenant, not globally."""
        # Create CAPA for Tenant A
        capa_a = CAPA.objects.create(
            tenant=self.tenant_a,
            problem_statement="Problem A",
            capa_type="CORRECTIVE",
            severity="MAJOR",
            initiated_by=self.user_a,
            assigned_to=self.user_a
        )

        # Create CAPA for Tenant B
        capa_b = CAPA.objects.create(
            tenant=self.tenant_b,
            problem_statement="Problem B",
            capa_type="CORRECTIVE",
            severity="MAJOR",
            initiated_by=self.user_b,
            assigned_to=self.user_b
        )

        # Both should have sequence number 1 (first in their tenant)
        self.assertIn("001", capa_a.capa_number)
        self.assertIn("001", capa_b.capa_number)

        # Create second CAPA for Tenant A (same type to test sequence increment)
        capa_a2 = CAPA.objects.create(
            tenant=self.tenant_a,
            problem_statement="Problem A2",
            capa_type="CORRECTIVE",  # Same type as capa_a to test sequence
            severity="MINOR",
            initiated_by=self.user_a,
            assigned_to=self.user_a
        )

        # Should be sequence 2 for Tenant A (same type)
        self.assertIn("002", capa_a2.capa_number)


class TenantUserAssociationTestCase(TestCase):
    """Tests for user-tenant associations."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Tenant", slug="test")

    def test_user_belongs_to_tenant(self):
        """Test that users can be assigned to a tenant."""
        user = User.objects.create_user(
            username='tenant_user',
            email='user@tenant.com',
            password='testpass',
            tenant=self.tenant
        )
        self.assertEqual(user.tenant, self.tenant)

    def test_tenant_users_relation(self):
        """Test reverse relation from tenant to users."""
        user1 = User.objects.create_user(
            username='user1', email='user1@test.com', password='testpass',
            tenant=self.tenant
        )
        user2 = User.objects.create_user(
            username='user2', email='user2@test.com', password='testpass',
            tenant=self.tenant
        )

        self.assertEqual(self.tenant.users.count(), 2)
        self.assertIn(user1, self.tenant.users.all())
        self.assertIn(user2, self.tenant.users.all())

    def test_superuser_without_tenant(self):
        """Test that superusers can exist without a tenant."""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='testpass'
        )
        self.assertIsNone(superuser.tenant)


@skipIf(not is_vector_extension_available(), "Vector extension not available")
class RLSPolicyTestCase(VectorTestCase):
    """
    Tests for Row-Level Security policies.

    These tests only run when ENABLE_RLS=True and verify database-level isolation.
    """

    def setUp(self):
        self.tenant_a = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.tenant_b = Tenant.objects.create(name="Tenant B", slug="tenant-b")

        # Create test data
        self.company_a = Companies.objects.create(
            tenant=self.tenant_a, name="Company A"
        )
        self.company_b = Companies.objects.create(
            tenant=self.tenant_b, name="Company B"
        )

    @skipIf(not is_rls_enabled(), "RLS tests require ENABLE_RLS=True in settings")
    def test_rls_filters_by_tenant_context(self):
        """Test that RLS policies filter based on app.current_tenant_id."""
        # Set tenant context
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.current_tenant_id = %s",
                [str(self.tenant_a.id)]
            )

            # Query should only return Tenant A's data
            cursor.execute(
                "SELECT name FROM Tracker_companies WHERE tenant_id IS NOT NULL"
            )
            results = cursor.fetchall()

            company_names = [r[0] for r in results]
            self.assertIn("Company A", company_names)
            self.assertNotIn("Company B", company_names)

    @skipIf(not is_rls_enabled(), "RLS tests require ENABLE_RLS=True in settings")
    def test_rls_blocks_cross_tenant_insert(self):
        """Test that RLS blocks inserts with wrong tenant_id."""
        with connection.cursor() as cursor:
            # Set context to Tenant A
            cursor.execute(
                "SET LOCAL app.current_tenant_id = %s",
                [str(self.tenant_a.id)]
            )

            # Try to insert with Tenant B's ID - should fail
            with self.assertRaises(Exception):
                cursor.execute(
                    """
                    INSERT INTO Tracker_companies (id, tenant_id, name, created_at, updated_at)
                    VALUES (gen_random_uuid(), %s, 'Malicious Company', NOW(), NOW())
                    """,
                    [str(self.tenant_b.id)]
                )
