"""
Tests for integration viewset permissions and catalog data exposure.

Covers:
- Non-staff users are denied access to integration CRUD
- Staff/admin users can access integration endpoints
- Catalog endpoint does not leak the raw config JSON
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from Tracker.tests.base import TenantTestCase

User = get_user_model()


class IntegrationViewSetPermissionTests(TenantTestCase):
    """Verify that integration endpoints require staff/admin access."""

    def test_non_staff_user_denied_list(self):
        """Regular authenticated user gets 403 on integration list."""
        self.authenticate_as(self.user_a)
        response = self.client.get('/api/integrations/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_denied_create(self):
        """Regular authenticated user gets 403 on integration create."""
        self.authenticate_as(self.user_a)
        response = self.client.post('/api/integrations/', {
            'provider': 'hubspot',
            'display_name': 'Test',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_denied_catalog(self):
        """Regular authenticated user gets 403 on catalog."""
        self.authenticate_as(self.user_a)
        response = self.client.get('/api/integrations/catalog/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_denied_sync_logs(self):
        """Regular authenticated user gets 403 on sync logs."""
        self.authenticate_as(self.user_a)
        response = self.client.get('/api/integration-sync-logs/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_denied_pipeline_stages(self):
        """Regular authenticated user gets 403 on pipeline stages."""
        self.authenticate_as(self.user_a)
        response = self.client.get('/api/hubspot-pipeline-stages/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_allowed_list(self):
        """Staff user can access integration list."""
        self.user_a.is_staff = True
        self.user_a.save()
        self.authenticate_as(self.user_a)
        response = self.client.get('/api/integrations/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_301_MOVED_PERMANENTLY])

    def test_superuser_allowed_list(self):
        """Superuser can access integration list."""
        self.authenticate_superuser(self.tenant_a)
        response = self.client.get('/api/integrations/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_301_MOVED_PERMANENTLY])

    def test_unauthenticated_user_denied(self):
        """Unauthenticated request gets 401/403."""
        response = self.client.get('/api/integrations/')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])


class CatalogDataExposureTests(TenantTestCase):
    """Verify the catalog endpoint does not leak sensitive config data."""

    def test_catalog_does_not_include_config_field(self):
        """Catalog entries should not contain the raw 'config' JSON field."""
        from integrations.models.config import IntegrationConfig

        IntegrationConfig.objects.create(
            tenant=self.tenant_a,
            provider='hubspot',
            display_name='Test HubSpot',
            api_key='secret-key-123',
            config={'pipeline_id': 'abc', 'debug_mode': True},
            is_enabled=True,
        )

        self.user_a.is_staff = True
        self.user_a.save()
        self.authenticate_as(self.user_a)

        response = self.client.get('/api/integrations/catalog/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for entry in response.json():
            self.assertNotIn(
                'config', entry,
                f"Catalog entry for '{entry.get('provider')}' leaks raw config field"
            )
