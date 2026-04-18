"""
Tests for HubSpot contact resolution (resolve_contact).

Covers:
- New user created with correct tenant
- Existing user in same tenant gets updated
- Existing user in different tenant is NOT overwritten (no tenant hijack)
- Multi-tenant: existing user gets a Customer role in the syncing tenant
"""

from unittest.mock import MagicMock

from django.test import TestCase

from Tracker.tests.base import TenantTestCase
from Tracker.models import User, TenantGroup, UserRole

from integrations.adapters.hubspot.serializers import resolve_contact


def _make_integration(tenant):
    integration = MagicMock()
    integration.tenant = tenant
    return integration


class ResolveContactNewUserTests(TenantTestCase):
    """Tests for creating new users from HubSpot contacts."""

    def test_creates_new_user_with_correct_tenant(self):
        contact_info = {
            'email': 'newcontact@example.com',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_a)

        user = resolve_contact(contact_info, {}, integration, self.tenant_a)

        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newcontact@example.com')
        self.assertEqual(user.tenant, self.tenant_a)
        self.assertEqual(user.user_type, User.UserType.PORTAL)

    def test_new_user_gets_customer_role_in_tenant(self):
        contact_info = {
            'email': 'newrole@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_a)

        user = resolve_contact(contact_info, {}, integration, self.tenant_a)

        self.assertTrue(
            UserRole.objects.filter(
                user=user,
                group__name='Customer',
                group__tenant=self.tenant_a,
            ).exists()
        )

    def test_returns_none_for_no_email(self):
        result = resolve_contact(
            {'email': None}, {}, _make_integration(self.tenant_a), self.tenant_a
        )
        self.assertIsNone(result)

    def test_returns_none_for_empty_contact(self):
        result = resolve_contact(
            None, {}, _make_integration(self.tenant_a), self.tenant_a
        )
        self.assertIsNone(result)


class ResolveContactExistingUserTests(TenantTestCase):
    """Tests for resolving contacts that match existing users."""

    def test_existing_user_same_tenant_updated(self):
        """User in same tenant gets name updated."""
        existing = User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='testpass',
            tenant=self.tenant_a,
            first_name='Old',
            last_name='Name',
        )

        contact_info = {
            'email': 'existing@example.com',
            'first_name': 'New',
            'last_name': 'Name',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_a)

        user = resolve_contact(contact_info, {}, integration, self.tenant_a)

        self.assertEqual(user.pk, existing.pk)
        existing.refresh_from_db()
        self.assertEqual(existing.first_name, 'New')
        self.assertEqual(existing.tenant, self.tenant_a)  # unchanged

    def test_existing_user_different_tenant_not_overwritten(self):
        """User belonging to Tenant A is NOT reassigned to Tenant B."""
        existing = User.objects.create_user(
            username='shared@example.com',
            email='shared@example.com',
            password='testpass',
            tenant=self.tenant_a,
            first_name='Original',
            last_name='Name',
        )

        contact_info = {
            'email': 'shared@example.com',
            'first_name': 'Overwritten',
            'last_name': 'Name',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_b)

        user = resolve_contact(contact_info, {}, integration, self.tenant_b)

        existing.refresh_from_db()
        # Tenant must NOT change
        self.assertEqual(existing.tenant, self.tenant_a)
        # Name must NOT be overwritten by a different tenant's sync
        self.assertEqual(existing.first_name, 'Original')

    def test_cross_tenant_user_gets_role_in_both_tenants(self):
        """User from Tenant A gets a Customer role in Tenant B without losing Tenant A."""
        existing = User.objects.create_user(
            username='multi@example.com',
            email='multi@example.com',
            password='testpass',
            tenant=self.tenant_a,
        )

        contact_info = {
            'email': 'multi@example.com',
            'first_name': 'Multi',
            'last_name': 'Tenant',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_b)

        user = resolve_contact(contact_info, {}, integration, self.tenant_b)

        # Primary tenant unchanged
        existing.refresh_from_db()
        self.assertEqual(existing.tenant, self.tenant_a)

        # Has Customer role in Tenant B
        self.assertTrue(
            UserRole.objects.filter(
                user=existing,
                group__name='Customer',
                group__tenant=self.tenant_b,
            ).exists()
        )

    def test_sequential_sync_from_two_tenants_creates_roles_in_both(self):
        """User synced by Tenant A then Tenant B has Customer roles in both."""
        contact_info = {
            'email': 'bothtenants@example.com',
            'first_name': 'Both',
            'last_name': 'Tenants',
            'associated_company_id': None,
        }

        # Tenant A syncs first — creates the user
        resolve_contact(contact_info, {}, _make_integration(self.tenant_a), self.tenant_a)
        # Tenant B syncs same contact
        resolve_contact(contact_info, {}, _make_integration(self.tenant_b), self.tenant_b)

        user = User.objects.get(email='bothtenants@example.com')

        # Primary tenant stays as Tenant A (first creator)
        self.assertEqual(user.tenant, self.tenant_a)

        # Customer role in both tenants
        self.assertTrue(
            UserRole.objects.filter(
                user=user, group__name='Customer', group__tenant=self.tenant_a,
            ).exists()
        )
        self.assertTrue(
            UserRole.objects.filter(
                user=user, group__name='Customer', group__tenant=self.tenant_b,
            ).exists()
        )

    def test_duplicate_sync_same_tenant_no_duplicate_roles(self):
        """Syncing the same contact twice in one tenant doesn't create duplicate roles."""
        contact_info = {
            'email': 'dupecheck@example.com',
            'first_name': 'Dupe',
            'last_name': 'Check',
            'associated_company_id': None,
        }
        integration = _make_integration(self.tenant_a)

        resolve_contact(contact_info, {}, integration, self.tenant_a)
        resolve_contact(contact_info, {}, integration, self.tenant_a)

        user = User.objects.get(email='dupecheck@example.com')
        role_count = UserRole.objects.filter(
            user=user, group__name='Customer', group__tenant=self.tenant_a,
        ).count()
        self.assertEqual(role_count, 1)

    def test_cross_tenant_sync_does_not_reset_password(self):
        """Existing user's password is preserved when synced by a different tenant."""
        existing = User.objects.create_user(
            username='keeppass@example.com',
            email='keeppass@example.com',
            password='myoriginalpassword',
            tenant=self.tenant_a,
        )
        original_password_hash = existing.password

        contact_info = {
            'email': 'keeppass@example.com',
            'first_name': 'Keep',
            'last_name': 'Pass',
            'associated_company_id': None,
        }
        resolve_contact(contact_info, {}, _make_integration(self.tenant_b), self.tenant_b)

        existing.refresh_from_db()
        self.assertEqual(existing.password, original_password_hash)
        self.assertTrue(existing.check_password('myoriginalpassword'))

    def test_cross_tenant_sync_preserves_user_type(self):
        """An INTERNAL user doesn't get downgraded to PORTAL by another tenant's sync."""
        existing = User.objects.create_user(
            username='internal@example.com',
            email='internal@example.com',
            password='testpass',
            tenant=self.tenant_a,
            user_type=User.UserType.INTERNAL,
        )

        contact_info = {
            'email': 'internal@example.com',
            'first_name': 'Internal',
            'last_name': 'User',
            'associated_company_id': None,
        }
        resolve_contact(contact_info, {}, _make_integration(self.tenant_b), self.tenant_b)

        existing.refresh_from_db()
        self.assertEqual(existing.user_type, User.UserType.INTERNAL)
        self.assertEqual(existing.tenant, self.tenant_a)

    def test_same_tenant_sync_preserves_user_type(self):
        """An INTERNAL user in the same tenant doesn't get downgraded to PORTAL on re-sync."""
        existing = User.objects.create_user(
            username='staff@example.com',
            email='staff@example.com',
            password='testpass',
            tenant=self.tenant_a,
            user_type=User.UserType.INTERNAL,
        )

        contact_info = {
            'email': 'staff@example.com',
            'first_name': 'Staff',
            'last_name': 'Member',
            'associated_company_id': None,
        }
        resolve_contact(contact_info, {}, _make_integration(self.tenant_a), self.tenant_a)

        existing.refresh_from_db()
        self.assertEqual(existing.user_type, User.UserType.INTERNAL)
