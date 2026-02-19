"""
Tests for HubSpot integration.
"""

from unittest.mock import MagicMock, patch, Mock
from datetime import datetime
from django.test import TestCase, override_settings

from Tracker.integrations.base_service import IntegrationConfig, SyncResult
from Tracker.integrations.hubspot_service import HubSpotService
from Tracker.models import Orders, Companies, User, HubSpotSyncLog


class HubSpotServiceTests(TestCase):
    """Tests for HubSpotService."""

    def setUp(self):
        """Create HubSpot service with test config."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
            webhook_secret='test-webhook-secret',
            debug_mode=False,
        )
        self.service = HubSpotService(config=self.config)

    def test_service_registration(self):
        """HubSpotService is auto-registered."""
        from Tracker.integrations import registry

        self.assertIn('hubspot', registry)

    def test_service_name(self):
        """Service has correct name and display name."""
        self.assertEqual(self.service.name, 'hubspot')
        self.assertEqual(self.service.display_name, 'HubSpot CRM')

    def test_is_enabled(self):
        """Service is enabled with API key."""
        self.assertTrue(self.service.is_enabled())

    def test_is_disabled_without_api_key(self):
        """Service is disabled without API key."""
        config = IntegrationConfig(enabled=True, api_key=None)
        service = HubSpotService(config=config)

        self.assertFalse(service.is_enabled())

    def test_get_headers(self):
        """Headers include authorization."""
        headers = self.service._get_headers()

        self.assertEqual(headers['Authorization'], 'Bearer test-api-key')
        self.assertEqual(headers['Content-Type'], 'application/json')


class HubSpotSyncOrdersTests(TestCase):
    """Tests for HubSpot order sync."""

    def setUp(self):
        """Create HubSpot service with test config."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
        )
        self.service = HubSpotService(config=self.config)

    @patch('Tracker.hubspot.sync.sync_all_deals')
    def test_sync_orders_success(self, mock_sync):
        """sync_orders returns success result."""
        mock_sync.return_value = {
            'status': 'success',
            'created': 5,
            'updated': 3,
            'processed': 8,
        }

        result = self.service.sync_orders()

        self.assertTrue(result.success)
        self.assertEqual(result.created, 5)
        self.assertEqual(result.updated, 3)
        mock_sync.assert_called_once()

    @patch('Tracker.hubspot.sync.sync_all_deals')
    def test_sync_orders_failure(self, mock_sync):
        """sync_orders handles errors."""
        mock_sync.return_value = {
            'status': 'error',
            'message': 'API rate limit exceeded',
        }

        result = self.service.sync_orders()

        self.assertFalse(result.success)
        self.assertIn('API rate limit exceeded', result.errors)

    @patch('Tracker.hubspot.sync.sync_all_deals')
    def test_sync_orders_exception(self, mock_sync):
        """sync_orders handles exceptions."""
        mock_sync.side_effect = Exception('Connection error')

        result = self.service.sync_orders()

        self.assertFalse(result.success)
        self.assertIn('Connection error', result.errors)


class HubSpotPullTests(TestCase):
    """Tests for HubSpot pull operations."""

    def setUp(self):
        """Create HubSpot service with test config."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
        )
        self.service = HubSpotService(config=self.config)

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_pull_order_success(self, mock_get):
        """pull_order returns deal data."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            'id': '12345',
            'properties': {
                'dealname': 'Test Deal',
                'dealstage': 'closedwon',
                'amount': '10000',
                'closedate': '2025-01-15',
                'pipeline': 'default',
            }
        }
        mock_get.return_value = mock_response

        result = self.service.pull_order('12345')

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], '12345')
        self.assertEqual(result['name'], 'Test Deal')
        self.assertEqual(result['stage'], 'closedwon')

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_pull_order_not_found(self, mock_get):
        """pull_order returns None for missing deal."""
        from requests.exceptions import HTTPError
        mock_response = Mock(status_code=404)
        mock_response.raise_for_status.side_effect = HTTPError('Not found')
        mock_get.return_value = mock_response

        result = self.service.pull_order('99999')

        self.assertIsNone(result)

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_pull_customer_success(self, mock_get):
        """pull_customer returns contact data."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            'id': '67890',
            'properties': {
                'firstname': 'John',
                'lastname': 'Doe',
                'email': 'john@example.com',
                'phone': '555-1234',
                'associatedcompanyid': '11111',
            }
        }
        mock_get.return_value = mock_response

        result = self.service.pull_customer('67890')

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], '67890')
        self.assertEqual(result['first_name'], 'John')
        self.assertEqual(result['last_name'], 'Doe')
        self.assertEqual(result['email'], 'john@example.com')

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_pull_company_success(self, mock_get):
        """pull_company returns company data."""
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            'id': '11111',
            'properties': {
                'name': 'Acme Corp',
                'domain': 'acme.com',
                'industry': 'Manufacturing',
                'city': 'New York',
                'state': 'NY',
                'country': 'USA',
            }
        }
        mock_get.return_value = mock_response

        result = self.service.pull_company('11111')

        self.assertIsNotNone(result)
        self.assertEqual(result['id'], '11111')
        self.assertEqual(result['name'], 'Acme Corp')
        self.assertEqual(result['industry'], 'Manufacturing')


class HubSpotPushTests(TestCase):
    """Tests for HubSpot push operations."""

    def setUp(self):
        """Create HubSpot service and test data."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
        )
        self.service = HubSpotService(config=self.config)

        # Create test company
        self.company = Companies.objects.create(name='Test Company')

        # Create test order with hubspot_deal_id
        self.order = Orders.objects.create(
            name='Test Order',
            company=self.company,
            hubspot_deal_id='12345',
        )

    @patch('Tracker.integrations.hubspot_service.requests.post')
    def test_push_note_success(self, mock_post):
        """push_note creates note in HubSpot."""
        mock_response = Mock(status_code=201)
        mock_post.return_value = mock_response

        result = self.service.push_note(self.order, 'Test note message')

        self.assertTrue(result)
        mock_post.assert_called_once()

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs['json']
        self.assertEqual(payload['properties']['hs_note_body'], 'Test note message')
        self.assertEqual(payload['associations'][0]['to']['id'], '12345')

    @patch('Tracker.integrations.hubspot_service.requests.post')
    def test_push_note_failure(self, mock_post):
        """push_note handles API errors."""
        from requests.exceptions import HTTPError
        mock_response = Mock(status_code=400)
        mock_response.raise_for_status.side_effect = HTTPError('Bad request')
        mock_post.return_value = mock_response

        result = self.service.push_note(self.order, 'Test note')

        self.assertFalse(result)

    def test_push_note_without_deal_id(self):
        """push_note fails without hubspot_deal_id."""
        order_without_hubspot = Orders.objects.create(
            name='Local Order',
            company=self.company,
        )

        result = self.service.push_note(order_without_hubspot, 'Test note')

        self.assertFalse(result)


class HubSpotWebhookTests(TestCase):
    """Tests for HubSpot webhook handling."""

    def setUp(self):
        """Create HubSpot service and test data."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
            webhook_secret='test-secret',
        )
        self.service = HubSpotService(config=self.config)

    def test_verify_webhook_signature_valid(self):
        """Valid signature passes verification."""
        import hmac
        import hashlib

        payload = b'{"test": "data"}'
        signature = hmac.new(
            b'test-secret',
            payload,
            hashlib.sha256
        ).hexdigest()

        result = self.service.verify_webhook_signature(payload, signature)

        self.assertTrue(result)

    def test_verify_webhook_signature_invalid(self):
        """Invalid signature fails verification."""
        payload = b'{"test": "data"}'
        signature = 'invalid-signature'

        result = self.service.verify_webhook_signature(payload, signature)

        self.assertFalse(result)

    def test_handle_webhook_empty(self):
        """handle_webhook processes empty payload."""
        result = self.service.handle_webhook([], {})

        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['processed'], 0)


class HubSpotTestConnectionTests(TestCase):
    """Tests for HubSpot connection testing."""

    def setUp(self):
        """Create HubSpot service."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
        )
        self.service = HubSpotService(config=self.config)

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_connection_success(self, mock_get):
        """test_connection returns True on success."""
        mock_response = Mock(status_code=200)
        mock_get.return_value = mock_response

        success, message = self.service.test_connection()

        self.assertTrue(success)
        self.assertIn('Successfully', message)

    @patch('Tracker.integrations.hubspot_service.requests.get')
    def test_connection_failure(self, mock_get):
        """test_connection returns False on failure."""
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError('Connection refused')

        success, message = self.service.test_connection()

        self.assertFalse(success)
        self.assertIn('Connection refused', message)


class HubSpotStatusTests(TestCase):
    """Tests for HubSpot status reporting."""

    def setUp(self):
        """Create HubSpot service and sync logs."""
        self.config = IntegrationConfig(
            enabled=True,
            api_key='test-api-key',
            api_url='https://api.hubapi.com/crm/',
            debug_mode=True,
        )
        self.service = HubSpotService(config=self.config)

    def test_get_status_basic(self):
        """get_status returns basic info."""
        status = self.service.get_status()

        self.assertEqual(status['name'], 'hubspot')
        self.assertEqual(status['display_name'], 'HubSpot CRM')
        self.assertTrue(status['enabled'])
        self.assertTrue(status['configured'])
        self.assertTrue(status['debug_mode'])

    def test_get_status_with_sync_log(self):
        """get_status includes last sync info."""
        from django.utils import timezone

        HubSpotSyncLog.objects.create(
            sync_type='full',
            status='success',
            deals_processed=10,
            deals_created=3,
            deals_updated=7,
            completed_at=timezone.now(),
        )

        status = self.service.get_status()

        self.assertIn('last_sync', status)
        self.assertEqual(status['last_sync']['deals_processed'], 10)
        self.assertEqual(status['last_sync']['deals_created'], 3)
        self.assertEqual(status['last_sync']['deals_updated'], 7)
