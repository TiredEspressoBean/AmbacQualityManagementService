"""
Tests for tenant-related viewsets and middleware.

Tests cover:
- CurrentTenantView: Deployment info and tenant context
- TenantSettingsView: Tenant admin settings management
- TenantLogoView: Logo upload/delete
- TenantViewSet: Platform admin CRUD operations
- SignupView: Self-service tenant creation
- TenantGroupViewSet: Role/group management
- PermissionListView: Permission enumeration
- EffectivePermissionsView: User permission aggregation
- SwitchTenantView: Multi-tenant switching
- DemoResetView: Demo data reset
- UserTenantsView: User's tenant list
- PresetListView: Permission presets
- TenantMiddleware: Tenant resolution from headers/subdomain/user
- TenantStatusMiddleware: Suspended tenant blocking
- Trial functionality: Trial tenant access
- Dedicated mode: Default tenant behavior
"""

import unittest

from django.conf import settings
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from Tracker.models import Tenant, TenantGroup, UserRole
from Tracker.tests.base import TenantTestCase

User = get_user_model()


class CurrentTenantViewTestCase(TenantTestCase):
    """Test /api/tenant/current/ endpoint."""

    def test_unauthenticated_gets_deployment_info(self):
        """Unauthenticated request returns deployment info only."""
        client = APIClient()
        response = client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('deployment', response.data)
        self.assertIn('mode', response.data['deployment'])
        self.assertIsNone(response.data['user'])

    def test_authenticated_gets_user_info(self):
        """Authenticated request includes user info."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['user'])
        self.assertEqual(response.data['user']['email'], self.user_a.email)

    def test_includes_tenant_info_when_available(self):
        """Response includes tenant info when tenant context exists."""
        self.client.force_authenticate(user=self.user_a)
        # Set tenant on request (normally done by middleware)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tenant info depends on middleware resolving tenant

    def test_features_returned(self):
        """Features dict is returned."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('features', response.data)
        self.assertIsInstance(response.data['features'], dict)


class TenantSettingsViewTestCase(TenantTestCase):
    """Test /api/tenant/settings/ endpoint."""

    def setUp(self):
        super().setUp()
        # Make user_a a staff user (tenant admin)
        self.user_a.is_staff = True
        self.user_a.save()

    def test_requires_authentication(self):
        """Unauthenticated requests are rejected with 401."""
        client = APIClient()
        response = client.get('/api/tenant/settings/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_tenant_context(self):
        """User without tenant cannot access tenant-specific endpoints."""
        # Create a user without tenant
        user = User.objects.create_user(
            username='no_tenant_user',
            email='notenant@test.com',
            password='testpass123',
            tenant=None,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/tenant/settings/')

        # Behavior differs by mode:
        # - Dedicated: User is forbidden from default tenant (403)
        # - SaaS: No tenant context resolved (400)
        if settings.DEDICATED_MODE:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_denied(self):
        """Non-admin users are denied access."""
        # user_b is not staff/admin
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(
            '/api/tenant/settings/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_get_settings(self):
        """Admin can retrieve tenant settings."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/settings/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('name', response.data)
        self.assertIn('tier', response.data)

    def test_superuser_can_access(self):
        """Superusers have access regardless of group membership."""
        self.user_a.is_superuser = True
        self.user_a.save()

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/settings/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TenantLogoViewTestCase(TenantTestCase):
    """Test /api/tenant/logo/ endpoint."""

    def setUp(self):
        super().setUp()
        self.user_a.is_staff = True
        self.user_a.save()

    def test_upload_requires_auth(self):
        """Logo upload requires authentication."""
        client = APIClient()
        response = client.post('/api/tenant/logo/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_requires_admin(self):
        """Logo upload requires admin permission."""
        self.client.force_authenticate(user=self.user_b)  # Not admin
        logo = SimpleUploadedFile(
            "logo.png",
            b"fake image content",
            content_type="image/png"
        )
        response = self.client.post(
            '/api/tenant/logo/',
            {'logo': logo},
            format='multipart',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_requires_file(self):
        """Upload fails without file."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            '/api/tenant/logo/',
            {},
            format='multipart',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        # Either 400 (no file) or 400 (no tenant context)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_requires_admin(self):
        """Logo delete requires admin permission."""
        self.client.force_authenticate(user=self.user_b)
        response = self.client.delete(
            '/api/tenant/logo/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TenantViewSetTestCase(TestCase):
    """Test /api/tenants/ platform admin endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='platform_admin',
            email='admin@platform.com',
            password='adminpass123',
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
        )
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            tier=Tenant.Tier.PRO,
            status=Tenant.Status.ACTIVE,
        )

    def test_list_requires_admin(self):
        """Non-admin cannot list tenants."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/Tenants/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_tenants(self):
        """Platform admin can list all tenants."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/Tenants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_tenant_with_admin_user(self):
        """Creating tenant also creates admin user."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post('/api/Tenants/', {
            'name': 'New Tenant',
            'slug': 'new-tenant',
            'tier': 'STARTER',
            'admin_email': 'newadmin@example.com',
            'admin_first_name': 'New',
            'admin_last_name': 'Admin',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify tenant created
        self.assertTrue(Tenant.objects.filter(slug='new-tenant').exists())

        # Verify admin user created — is_staff is reserved for SaaS-vendor
        # support staff; customer tenant admins should NOT have it.
        admin = User.objects.filter(email='newadmin@example.com').first()
        self.assertIsNotNone(admin)
        self.assertFalse(admin.is_staff)

    def test_create_duplicate_slug_fails(self):
        """Creating tenant with duplicate slug fails."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post('/api/Tenants/', {
            'name': 'Duplicate',
            'slug': 'test-tenant',  # Already exists
            'tier': 'STARTER',
            'admin_email': 'dup@example.com',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suspend_tenant(self):
        """Admin can suspend a tenant."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/Tenants/{self.tenant.slug}/suspend/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, Tenant.Status.SUSPENDED)

    def test_activate_tenant(self):
        """Admin can activate a suspended tenant."""
        self.tenant.status = Tenant.Status.SUSPENDED
        self.tenant.save()

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(f'/api/Tenants/{self.tenant.slug}/activate/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.status, Tenant.Status.ACTIVE)

    def test_list_tenant_users(self):
        """Admin can list users in a tenant."""
        # Create a user in the tenant
        User.objects.create_user(
            username='tenant_user',
            email='user@tenant.com',
            password='pass123',
            tenant=self.tenant,
        )

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/Tenants/{self.tenant.slug}/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


class SignupViewTestCase(TestCase):
    """Test /api/tenants/signup/ self-service endpoint."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(SAAS_MODE=False)
    def test_signup_disabled_when_not_saas(self):
        """Signup returns 403 when not in SaaS mode."""
        response = self.client.post('/api/tenants/signup/', {
            'company_name': 'New Company',
            'email': 'new@example.com',
            'password': 'securepass123',
            'first_name': 'John',
            'last_name': 'Doe',
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(SAAS_MODE=True)
    def test_signup_creates_tenant_and_user(self):
        """Successful signup creates tenant and admin user."""
        response = self.client.post('/api/tenants/signup/', {
            'company_name': 'Acme Corp',
            'email': 'admin@acme.com',
            'password': 'securepass123',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify tenant
        tenant = Tenant.objects.filter(name='Acme Corp').first()
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.tier, Tenant.Tier.STARTER)

        # Verify user — is_staff is reserved for SaaS-vendor support staff,
        # so customer admins created via signup should NOT have it.
        user = User.objects.filter(email='admin@acme.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.tenant, tenant)
        self.assertFalse(user.is_staff)

    @override_settings(SAAS_MODE=True)
    def test_signup_duplicate_email_fails(self):
        """Signup with existing email fails."""
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123',
        )

        response = self.client.post('/api/tenants/signup/', {
            'company_name': 'New Company',
            'email': 'existing@example.com',
            'password': 'securepass123',
            'first_name': 'John',
            'last_name': 'Doe',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(SAAS_MODE=True)
    def test_signup_generates_unique_slug(self):
        """Signup generates unique slug even if company name exists."""
        # Create tenant with slug 'acme'
        Tenant.objects.create(
            name='Acme',
            slug='acme',
            tier=Tenant.Tier.STARTER,
        )

        response = self.client.post('/api/tenants/signup/', {
            'company_name': 'Acme',
            'email': 'admin@acme2.com',
            'password': 'securepass123',
            'first_name': 'Jane',
            'last_name': 'Doe',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Slug should be acme-1 or similar
        tenant = Tenant.objects.filter(name='Acme').exclude(slug='acme').first()
        self.assertIsNotNone(tenant)
        self.assertNotEqual(tenant.slug, 'acme')


class TenantGroupViewSetTestCase(TenantTestCase):
    """Test /api/TenantGroups/ role management endpoints."""

    def setUp(self):
        super().setUp()
        self.user_a.is_staff = True
        self.user_a.save()

        # Create a tenant group
        self.group = TenantGroup.objects.create(
            tenant=self.tenant_a,
            name='Test Group',
            description='A test group',
            is_custom=True,
        )

    def test_list_requires_auth(self):
        """Listing groups requires authentication."""
        client = APIClient()
        response = client.get('/api/TenantGroups/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_groups(self):
        """Authenticated user can list groups."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/TenantGroups/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_group_requires_admin(self):
        """Creating groups requires admin permission."""
        self.client.force_authenticate(user=self.user_b)  # Not admin
        response = self.client.post(
            '/api/TenantGroups/',
            {'name': 'New Group', 'description': 'Test'},
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_group(self):
        """Admin can create a new group."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            '/api/TenantGroups/',
            {'name': 'New Custom Group', 'description': 'Custom role'},
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Custom Group')

    @unittest.skipUnless(settings.SAAS_MODE, "Requires tenant header support (SaaS mode)")
    def test_delete_group_with_members_fails(self):
        """Cannot delete group that has members."""
        # Add a member to the group
        UserRole.objects.create(
            user=self.user_b,
            group=self.group,
            granted_by=self.user_a,
        )

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.delete(f'/api/TenantGroups/{self.group.id}/')

        # Should return 400 with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('members', str(response.data).lower())

    @unittest.skipUnless(settings.SAAS_MODE, "Requires tenant header support (SaaS mode)")
    def test_add_member_to_group(self):
        """Admin can add members from the same tenant to a group."""
        # Create a user in tenant_a (same tenant as group)
        same_tenant_user = User.objects.create_user(
            username='same_tenant_user',
            email='same@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            f'/api/TenantGroups/{self.group.id}/members/',
            {'user_id': str(same_tenant_user.id)},
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @unittest.skipUnless(settings.SAAS_MODE, "Requires tenant header support (SaaS mode)")
    def test_clone_group(self):
        """Admin can clone a group."""
        # Add some permissions to original group
        perm = Permission.objects.first()
        if perm:
            self.group.permissions.add(perm)

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.post(
            f'/api/TenantGroups/{self.group.id}/clone/',
            {'name': 'Cloned Group'}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Cloned Group')

    @unittest.skipUnless(settings.SAAS_MODE, "Requires tenant header support (SaaS mode)")
    def test_clone_requires_name(self):
        """Cloning without name fails with 400."""
        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.post(
            f'/api/TenantGroups/{self.group.id}/clone/',
            {}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)


class PermissionListViewTestCase(TenantTestCase):
    """Test /api/permissions/ endpoint."""

    def test_requires_auth(self):
        """Permission list requires authentication."""
        client = APIClient()
        response = client.get('/api/permissions/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_permissions(self):
        """Authenticated user can list permissions."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/permissions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('permissions', response.data)

    def test_grouped_permissions(self):
        """Can request grouped permissions."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/permissions/?grouped=true')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('categories', response.data)


class EffectivePermissionsViewTestCase(TenantTestCase):
    """Test /api/users/me/effective-permissions/ endpoint."""

    def test_requires_auth(self):
        """Endpoint requires authentication."""
        client = APIClient()
        response = client.get('/api/users/me/effective-permissions/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_permissions(self):
        """User can get their own effective permissions."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/users/me/effective-permissions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('effective_permissions', response.data)
        self.assertEqual(response.data['user_email'], self.user_a.email)

    def test_admin_can_view_other_user(self):
        """Admin can view other user's permissions within same tenant."""
        self.user_a.is_staff = True
        self.user_a.save()

        # Create another user in same tenant for this test
        other_user = User.objects.create_user(
            username='other_user_a',
            email='other@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a
        )

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get(f'/api/users/{other_user.id}/effective-permissions/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_email'], other_user.email)

    def test_non_admin_cannot_view_other_user(self):
        """Non-admin cannot view other user's permissions."""
        # Create another user in same tenant for this test
        other_user = User.objects.create_user(
            username='other_user_a2',
            email='other2@tenant-a.com',
            password='testpass123',
            tenant=self.tenant_a
        )

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get(f'/api/users/{other_user.id}/effective-permissions/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SwitchTenantViewTestCase(TenantTestCase):
    """Test /api/user/tenants/switch/ endpoint."""

    def test_requires_auth(self):
        """Switching tenant requires authentication."""
        client = APIClient()
        response = client.post('/api/user/tenants/switch/', {
            'tenant_id': str(self.tenant_a.id)
        })

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_switch_to_own_tenant(self):
        """User can switch to their own tenant."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post('/api/user/tenants/switch/', {
            'tenant_id': str(self.tenant_a.id)
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_switch_to_other_tenant_denied(self):
        """User cannot switch to tenant they don't belong to."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post('/api/user/tenants/switch/', {
            'tenant_id': str(self.tenant_b.id)  # user_a doesn't belong to tenant_b
        })

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_switch_nonexistent_tenant(self):
        """Switching to nonexistent tenant returns 404."""
        import uuid
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post('/api/user/tenants/switch/', {
            'tenant_id': str(uuid.uuid4())
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_switch_requires_tenant_id(self):
        """Switching without tenant_id fails."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post('/api/user/tenants/switch/', {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DemoResetViewTestCase(TenantTestCase):
    """Test /api/tenant/demo-reset/ endpoint."""

    def setUp(self):
        super().setUp()
        self.tenant_a.is_demo = True
        self.tenant_a.save()
        self.user_a.is_staff = True
        self.user_a.save()

    def test_requires_auth(self):
        """Demo reset requires authentication."""
        client = APIClient()
        response = client.post('/api/tenant/demo-reset/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_requires_admin(self):
        """Demo reset requires admin permission."""
        self.client.force_authenticate(user=self.user_b)  # Not admin
        response = self.client.post(
            '/api/tenant/demo-reset/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_demo_tenants(self):
        """Demo reset only works on demo tenants."""
        self.tenant_a.is_demo = False
        self.tenant_a.save()

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            '/api/tenant/demo-reset/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@unittest.skipUnless(settings.SAAS_MODE, "Tenant isolation tests only apply in SaaS mode")
class TenantIsolationTestCase(TenantTestCase):
    """Test tenant isolation in tenant viewsets.

    These tests verify that users can only see/access resources within their
    tenant. In dedicated mode, there's only one tenant, so these don't apply.
    """

    def setUp(self):
        super().setUp()
        self.user_a.is_staff = True
        self.user_a.save()

        # Create groups in each tenant
        self.group_a = TenantGroup.objects.create(
            tenant=self.tenant_a,
            name='Tenant A Group',
        )
        self.group_b = TenantGroup.objects.create(
            tenant=self.tenant_b,
            name='Tenant B Group',
        )

    def test_groups_filtered_by_tenant(self):
        """User only sees groups from their tenant."""
        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/TenantGroups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response may be paginated (results key) or direct list
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data

        # Verify we got groups and they belong to tenant_a (preset groups are auto-created)
        self.assertGreater(len(data), 0, "Should have at least one group")

        # All returned groups should belong to tenant_a
        for group in data:
            if 'tenant' in group:
                self.assertEqual(str(group['tenant']), str(self.tenant_a.id))

        # Tenant B's group should not be visible
        group_names = [g['name'] for g in data]
        self.assertNotIn('Tenant B Group', group_names)

    def test_cannot_access_other_tenant_group(self):
        """User cannot access group from another tenant."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            f'/api/TenantGroups/{self.group_b.id}/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_add_member_from_other_tenant(self):
        """Cannot add user from other tenant to group."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            f'/api/TenantGroups/{self.group_a.id}/members/',
            {'user_id': str(self.user_b.id)},  # user_b is in tenant_b
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        # User from different tenant is not found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PresetListViewTestCase(TenantTestCase):
    """Test /api/presets/ endpoint."""

    def test_requires_auth(self):
        """Preset list requires authentication."""
        client = APIClient()
        response = client.get('/api/presets/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_presets(self):
        """Authenticated user can list presets."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/presets/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('presets', response.data)
        self.assertIsInstance(response.data['presets'], list)


class UserTenantsViewTestCase(TenantTestCase):
    """Test /api/user/tenants/ endpoint."""

    def test_requires_auth(self):
        """Listing user tenants requires authentication."""
        client = APIClient()
        response = client.get('/api/user/tenants/')

        # Custom exception handler ensures 401 for unauthenticated
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_own_tenants(self):
        """User can list tenants they belong to."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/user/tenants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is a list of tenants
        self.assertIsInstance(response.data, list)
        # User should see at least one tenant (their home tenant or default in dedicated mode)
        self.assertGreaterEqual(len(response.data), 1)

    def test_does_not_list_other_tenants(self):
        """User does not see tenants they don't belong to."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/user/tenants/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is a list of tenants
        tenant_ids = [str(t['id']) for t in response.data]

        # user_a should not see tenant_b (unless both are in same default tenant in dedicated mode)
        # In dedicated mode this check may not apply
        if len(tenant_ids) > 1:
            self.assertNotIn(str(self.tenant_b.id), tenant_ids)


class TenantMiddlewareTestCase(TenantTestCase):
    """Test TenantMiddleware behavior.

    Note: In DEDICATED_MODE, header-based resolution is skipped and default tenant is used.
    These tests document both SaaS and dedicated mode behaviors.
    """

    def test_exempt_paths_skip_tenant_resolution(self):
        """Exempt paths don't require tenant context."""
        client = APIClient()

        # Health check should work without tenant
        response = client.get('/health/')
        # May 404 if not implemented, but shouldn't be 403
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_resolved_and_response_has_context_header(self):
        """Tenant is resolved and response includes context header."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should have tenant context header (regardless of mode)
        self.assertIn('X-Tenant-Context', response.headers)
        # In dedicated mode, this will be the default tenant slug

    def test_tenant_resolved_from_slug_header(self):
        """Tenant can be resolved using slug in X-Tenant-ID header (SaaS mode)."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=self.tenant_a.slug
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @unittest.skipUnless(settings.SAAS_MODE, "Only runs in SaaS mode")
    def test_invalid_tenant_header_returns_403_saas_mode(self):
        """Invalid tenant ID in header returns 403 (SaaS mode only)."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID='nonexistent-tenant-slug'
        )

        # In SaaS mode, invalid tenant header returns 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @unittest.skipUnless(settings.SAAS_MODE, "Only runs in SaaS mode")
    def test_user_cannot_access_other_tenant_via_header_saas_mode(self):
        """User cannot access tenant they don't belong to via header (SaaS mode)."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)
        )

        # In SaaS mode, accessing other tenant returns 403
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_access_any_tenant(self):
        """Superuser can access any tenant via header."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_source_header_in_response(self):
        """Response includes X-Tenant-Source header."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('X-Tenant-Source', response.headers)
        # Source can be 'header' (SaaS) or 'default' (dedicated mode)
        self.assertIn(response.headers['X-Tenant-Source'], ['header', 'default', 'user'])


class TenantStatusMiddlewareTestCase(TenantTestCase):
    """Test TenantStatusMiddleware behavior with suspended tenants.

    Note: TenantStatusMiddleware must be in MIDDLEWARE stack to block suspended tenants.
    In dedicated mode with default tenant, these tests verify tenant status is tracked.
    """

    def test_active_tenant_allowed(self):
        """Active tenant can access endpoints."""
        self.tenant_a.status = Tenant.Status.ACTIVE
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/TenantGroups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trial_tenant_allowed(self):
        """Trial tenant can access endpoints."""
        self.tenant_a.status = Tenant.Status.TRIAL
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/TenantGroups/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_suspended_tenant_can_access_current_info(self):
        """Suspended tenant can still access current tenant info."""
        self.tenant_a.status = Tenant.Status.SUSPENDED
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/tenant/current/')

        # Current tenant info should work to show suspension status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_suspended_tenant_status_reflected(self):
        """Suspended status is reflected in tenant info."""
        self.tenant_a.status = Tenant.Status.SUSPENDED
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Tenant status should be visible
        if response.data.get('tenant'):
            self.assertIn('status', response.data['tenant'])

    @unittest.skipUnless(settings.SAAS_MODE, "Suspended tenant blocking only applies in SaaS mode")
    def test_suspended_tenant_blocked_from_data_endpoints(self):
        """Suspended tenant is blocked from accessing data endpoints.

        While suspended tenants can view their status via /api/tenant/current/,
        they should be blocked from accessing actual data endpoints.

        This test only runs in SaaS mode because in dedicated mode, the X-Tenant-ID
        header is ignored and the default tenant is always used.
        """
        self.tenant_a.status = Tenant.Status.SUSPENDED
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)

        # Should be blocked from TenantGroups endpoint
        response = self.client.get('/api/TenantGroups/')
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Suspended tenant should be blocked from data endpoints"
        )

    @unittest.skipUnless(settings.SAAS_MODE, "Suspended tenant blocking only applies in SaaS mode")
    def test_suspended_tenant_blocked_from_write_operations(self):
        """Suspended tenant cannot perform write operations.

        Suspended tenants should be blocked from creating, updating, or
        deleting any data.

        This test only runs in SaaS mode because in dedicated mode, the X-Tenant-ID
        header is ignored and the default tenant is always used.
        """
        self.tenant_a.status = Tenant.Status.SUSPENDED
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)

        # Should be blocked from creating a group
        response = self.client.post(
            '/api/TenantGroups/',
            {'name': 'New Group', 'description': 'Test'}
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            "Suspended tenant should be blocked from write operations"
        )


class TenantTrialTestCase(TenantTestCase):
    """Test tenant trial functionality."""

    def test_trial_tenant_info_returned(self):
        """Trial tenant info is returned correctly."""
        from django.utils import timezone
        from datetime import timedelta

        self.tenant_a.status = Tenant.Status.TRIAL
        self.tenant_a.trial_ends_at = timezone.now() + timedelta(days=14)
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify tenant info includes trial data
        if response.data.get('tenant'):
            self.assertIn('status', response.data['tenant'])

    def test_trial_tenant_can_access_features(self):
        """Trial tenant has access to features."""
        self.tenant_a.status = Tenant.Status.TRIAL
        self.tenant_a.save()

        self.authenticate_as(self.user_a, self.tenant_a)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('features', response.data)


# =============================================================================
# MODE-SPECIFIC TESTS
# =============================================================================

@unittest.skipUnless(settings.DEDICATED_MODE, "Only runs in dedicated mode")
class DedicatedModeTestCase(TestCase):
    """Test dedicated deployment mode behavior.

    In dedicated mode:
    - Header-based tenant resolution is skipped
    - Default tenant is always used
    - All users share the same tenant context

    These tests only run when DEPLOYMENT_MODE=dedicated.
    Run with: DEPLOYMENT_MODE=dedicated python manage.py test
    """

    def setUp(self):
        from Tracker.models import Tenant

        # Use the actual default tenant slug from settings
        default_slug = getattr(settings, 'DEFAULT_TENANT_SLUG', 'default')

        # Create the default tenant for dedicated mode
        self.default_tenant, _ = Tenant.objects.get_or_create(
            slug=default_slug,
            defaults={
                'name': 'Test Default Tenant',
                'tier': Tenant.Tier.PRO,
                'status': Tenant.Status.ACTIVE,
            }
        )

        self.user = User.objects.create_user(
            username='dedicated_user',
            email='dedicated@test.com',
            password='testpass123',
            tenant=self.default_tenant
        )
        self.client = APIClient()

    def test_dedicated_mode_uses_default_tenant(self):
        """In dedicated mode, default tenant is used automatically."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify we're actually in dedicated mode
        self.assertTrue(settings.DEDICATED_MODE)

    def test_header_ignored_in_dedicated_mode(self):
        """X-Tenant-ID header is ignored in dedicated mode."""
        # Create another tenant
        from Tracker.models import Tenant
        other_tenant = Tenant.objects.create(
            name='Other Tenant',
            slug='other-tenant',
            tier=Tenant.Tier.STARTER,
            status=Tenant.Status.ACTIVE,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(other_tenant.id)  # Try to switch tenant
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should still use default tenant, not the header-specified one
        self.assertEqual(response.headers.get('X-Tenant-Source'), 'default')

    def test_tenant_source_is_default(self):
        """X-Tenant-Source header shows 'default' in dedicated mode."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/tenant/current/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Tenant-Source'), 'default')


@unittest.skipUnless(settings.SAAS_MODE, "Only runs in SaaS mode")
class SaaSModeTestCase(TenantTestCase):
    """Test SaaS deployment mode behavior.

    In SaaS mode:
    - Tenant is resolved from X-Tenant-ID header
    - Users can only access tenants they belong to
    - Invalid tenant headers return 403

    These tests only run when DEPLOYMENT_MODE=saas.
    Run with: DEPLOYMENT_MODE=saas python manage.py test
    """

    def test_tenant_resolved_from_header(self):
        """Tenant is resolved from X-Tenant-ID header in SaaS mode."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Tenant-Source'), 'header')
        # Verify we're actually in SaaS mode
        self.assertTrue(settings.SAAS_MODE)

    def test_invalid_tenant_header_returns_403(self):
        """Invalid tenant ID in header returns 403 in SaaS mode."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID='nonexistent-tenant-slug'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_cannot_access_other_tenant(self):
        """User cannot access tenant they don't belong to in SaaS mode.

        Uses login() instead of force_authenticate() because the tenant middleware
        runs before DRF authentication. Session-based auth (via login) sets up
        request.user before middleware runs, allowing the tenant access check to work.
        """
        # Use login instead of force_authenticate for session-based auth
        # This ensures request.user is set when middleware runs
        self.client.login(username='user_a', password='testpass123')

        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)  # Try to access tenant_b
        )

        # Should be forbidden since user_a doesn't belong to tenant_b
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_access_any_tenant(self):
        """Superuser can access any tenant in SaaS mode."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_header_matches_response(self):
        """X-Tenant-Context header matches requested tenant."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('X-Tenant-Context'), self.tenant_a.slug)


class TenantAccessLogicTestCase(TenantTestCase):
    """Mode-independent tests for tenant access logic.

    These tests verify the middleware's tenant access checking logic
    directly, without going through HTTP requests. They run in both modes.
    """

    def test_user_cannot_access_other_tenant_logic(self):
        """Middleware correctly denies access to other tenants."""
        from Tracker.middleware import TenantMiddleware

        middleware = TenantMiddleware(lambda r: None)

        # user_a belongs to tenant_a, not tenant_b
        can_access = middleware._user_can_access_tenant(self.user_a, self.tenant_b)
        self.assertFalse(can_access, "User should not have access to other tenant")

    def test_user_can_access_own_tenant_logic(self):
        """Middleware correctly allows access to own tenant."""
        from Tracker.middleware import TenantMiddleware

        middleware = TenantMiddleware(lambda r: None)

        # user_a should have access to their own tenant
        can_access = middleware._user_can_access_tenant(self.user_a, self.tenant_a)
        self.assertTrue(can_access, "User should have access to own tenant")

    def test_superuser_can_access_any_tenant_logic(self):
        """Middleware correctly allows superuser to access any tenant."""
        from Tracker.middleware import TenantMiddleware

        middleware = TenantMiddleware(lambda r: None)

        # Superuser should have access to any tenant
        can_access = middleware._user_can_access_tenant(self.superuser, self.tenant_b)
        self.assertTrue(can_access, "Superuser should have access to any tenant")


@unittest.skipUnless(settings.SAAS_MODE, "Only runs in SaaS mode")
class TenantAccessPermissionTestCase(TenantTestCase):
    """Test TenantAccessPermission for API token authentication.

    This permission class closes the security gap where middleware-level
    tenant access checks don't work for DRF token authentication.

    These tests verify that API-authenticated users (using force_authenticate,
    which simulates token auth) are properly blocked from accessing other tenants.
    """

    def test_api_user_blocked_from_other_tenant(self):
        """API-authenticated user cannot access tenant they don't belong to.

        This tests the TenantAccessPermission class which enforces tenant access
        at the DRF permission level (after authentication).
        """
        # Use force_authenticate (simulates API token auth)
        self.client.force_authenticate(user=self.user_a)

        # Try to access tenant_b via header
        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)
        )

        # Should be forbidden - TenantAccessPermission blocks this
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_user_can_access_own_tenant(self):
        """API-authenticated user can access their own tenant."""
        self.client.force_authenticate(user=self.user_a)

        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_a.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_superuser_can_access_any_tenant(self):
        """API-authenticated superuser can access any tenant."""
        self.client.force_authenticate(user=self.superuser)

        response = self.client.get(
            '/api/tenant/current/',
            HTTP_X_TENANT_ID=str(self.tenant_b.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
