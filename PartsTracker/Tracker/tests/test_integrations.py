"""
Tests for the integration framework base classes and registry.
"""

from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings

from Tracker.integrations.base_service import (
    IntegrationService,
    IntegrationConfig,
    SyncResult,
)
from Tracker.integrations.registry import IntegrationRegistry


class DummyIntegration(IntegrationService):
    """Test integration implementation."""

    name = 'dummy'
    display_name = 'Dummy Integration'
    description = 'A test integration'

    def sync_orders(self) -> SyncResult:
        return SyncResult(success=True, created=5, updated=3)

    def sync_customers(self) -> SyncResult:
        return SyncResult(success=True, created=2)

    def push_note(self, order, message: str) -> bool:
        return True

    def pull_order(self, external_id: str):
        return {'id': external_id, 'name': f'Order {external_id}'}

    def pull_customer(self, external_id: str):
        return {'id': external_id, 'email': f'{external_id}@test.com'}


class IntegrationConfigTests(TestCase):
    """Tests for IntegrationConfig."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = IntegrationConfig()

        self.assertFalse(config.enabled)
        self.assertIsNone(config.api_key)
        self.assertEqual(config.sync_interval_minutes, 60)
        self.assertFalse(config.debug_mode)

    def test_custom_values(self):
        """Config accepts custom values."""
        config = IntegrationConfig(
            enabled=True,
            api_key='test-key',
            api_url='https://api.test.com',
            sync_interval_minutes=30,
            debug_mode=True,
        )

        self.assertTrue(config.enabled)
        self.assertEqual(config.api_key, 'test-key')
        self.assertEqual(config.api_url, 'https://api.test.com')
        self.assertEqual(config.sync_interval_minutes, 30)
        self.assertTrue(config.debug_mode)

    @override_settings(
        TEST_ENABLED=True,
        TEST_API_KEY='settings-key',
        TEST_DEBUG=True,
    )
    def test_from_settings(self):
        """Config can be loaded from Django settings."""
        config = IntegrationConfig.from_settings('TEST')

        self.assertTrue(config.enabled)
        self.assertEqual(config.api_key, 'settings-key')
        self.assertTrue(config.debug_mode)


class SyncResultTests(TestCase):
    """Tests for SyncResult."""

    def test_total_processed(self):
        """Total processed includes created, updated, deleted."""
        result = SyncResult(success=True, created=5, updated=3, deleted=2)
        self.assertEqual(result.total_processed, 10)

    def test_duration_calculation(self):
        """Duration is calculated from timestamps."""
        from datetime import datetime, timedelta

        start = datetime.now()
        end = start + timedelta(seconds=30)

        result = SyncResult(
            success=True,
            started_at=start,
            completed_at=end,
        )

        self.assertAlmostEqual(result.duration_seconds, 30, places=1)

    def test_to_dict(self):
        """Result can be converted to dict."""
        result = SyncResult(success=True, created=5, errors=['warning'])
        data = result.to_dict()

        self.assertTrue(data['success'])
        self.assertEqual(data['created'], 5)
        self.assertEqual(data['errors'], ['warning'])


class IntegrationServiceTests(TestCase):
    """Tests for IntegrationService base class."""

    def test_is_enabled_requires_api_key(self):
        """Integration requires API key to be enabled."""
        config = IntegrationConfig(enabled=True, api_key=None)
        integration = DummyIntegration(config=config)

        self.assertFalse(integration.is_enabled())

    def test_is_enabled_with_api_key(self):
        """Integration is enabled with API key."""
        config = IntegrationConfig(enabled=True, api_key='test-key')
        integration = DummyIntegration(config=config)

        self.assertTrue(integration.is_enabled())

    def test_is_configured(self):
        """Configured means API key is set."""
        config_without = IntegrationConfig(api_key=None)
        config_with = IntegrationConfig(api_key='test-key')

        integration_without = DummyIntegration(config=config_without)
        integration_with = DummyIntegration(config=config_with)

        self.assertFalse(integration_without.is_configured())
        self.assertTrue(integration_with.is_configured())

    def test_sync_orders(self):
        """sync_orders returns SyncResult."""
        config = IntegrationConfig(enabled=True, api_key='test')
        integration = DummyIntegration(config=config)

        result = integration.sync_orders()

        self.assertIsInstance(result, SyncResult)
        self.assertTrue(result.success)
        self.assertEqual(result.created, 5)
        self.assertEqual(result.updated, 3)

    def test_sync_all(self):
        """sync_all runs all sync operations."""
        config = IntegrationConfig(enabled=True, api_key='test')
        integration = DummyIntegration(config=config)

        results = integration.sync_all()

        self.assertIn('orders', results)
        self.assertIn('customers', results)
        self.assertTrue(results['orders'].success)
        self.assertTrue(results['customers'].success)

    def test_sync_all_skips_when_disabled(self):
        """sync_all returns empty when disabled."""
        config = IntegrationConfig(enabled=False)
        integration = DummyIntegration(config=config)

        results = integration.sync_all()

        self.assertEqual(results, {})

    def test_get_status(self):
        """get_status returns status dict."""
        config = IntegrationConfig(enabled=True, api_key='test', debug_mode=True)
        integration = DummyIntegration(config=config)

        status = integration.get_status()

        self.assertEqual(status['name'], 'dummy')
        self.assertEqual(status['display_name'], 'Dummy Integration')
        self.assertTrue(status['enabled'])
        self.assertTrue(status['configured'])
        self.assertTrue(status['debug_mode'])

    def test_repr(self):
        """String representation shows name and status."""
        config = IntegrationConfig(enabled=True, api_key='test')
        integration = DummyIntegration(config=config)

        self.assertIn('dummy', repr(integration))
        self.assertIn('enabled', repr(integration))


class IntegrationRegistryTests(TestCase):
    """Tests for IntegrationRegistry."""

    def setUp(self):
        """Create fresh registry for each test."""
        self.registry = IntegrationRegistry()

    def test_register_integration(self):
        """Can register an integration."""
        self.registry.register(DummyIntegration)

        self.assertIn('dummy', self.registry)
        self.assertEqual(len(self.registry), 1)

    def test_register_as_decorator(self):
        """Register works as decorator."""
        @self.registry.register
        class DecoratorIntegration(DummyIntegration):
            name = 'decorator_test'

        self.assertIn('decorator_test', self.registry)

    def test_register_requires_name(self):
        """Registration fails without name."""
        class NoNameIntegration(DummyIntegration):
            name = ''

        with self.assertRaises(ValueError):
            self.registry.register(NoNameIntegration)

    def test_get_integration(self):
        """Can get integration by name."""
        self.registry.register(DummyIntegration)

        integration = self.registry.get('dummy')

        self.assertIsInstance(integration, DummyIntegration)

    def test_get_returns_none_for_unknown(self):
        """Get returns None for unknown integration."""
        integration = self.registry.get('unknown')
        self.assertIsNone(integration)

    def test_get_returns_same_instance(self):
        """Get returns cached instance."""
        self.registry.register(DummyIntegration)

        instance1 = self.registry.get('dummy')
        instance2 = self.registry.get('dummy')

        self.assertIs(instance1, instance2)

    def test_get_all(self):
        """get_all returns all registered integrations."""
        self.registry.register(DummyIntegration)

        class AnotherIntegration(DummyIntegration):
            name = 'another'

        self.registry.register(AnotherIntegration)

        all_integrations = self.registry.get_all()

        self.assertEqual(len(all_integrations), 2)

    def test_get_enabled(self):
        """get_enabled returns only enabled integrations."""
        # Enabled integration
        class EnabledIntegration(DummyIntegration):
            name = 'enabled_test'

            def __init__(self, config=None):
                super().__init__(IntegrationConfig(enabled=True, api_key='test'))

        # Disabled integration
        class DisabledIntegration(DummyIntegration):
            name = 'disabled_test'

            def __init__(self, config=None):
                super().__init__(IntegrationConfig(enabled=False))

        self.registry.register(EnabledIntegration)
        self.registry.register(DisabledIntegration)

        enabled = self.registry.get_enabled()

        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].name, 'enabled_test')

    def test_list_names(self):
        """list_names returns registered names."""
        self.registry.register(DummyIntegration)

        names = self.registry.list_names()

        self.assertEqual(names, ['dummy'])

    def test_unregister(self):
        """Can unregister an integration."""
        self.registry.register(DummyIntegration)
        self.assertIn('dummy', self.registry)

        result = self.registry.unregister('dummy')

        self.assertTrue(result)
        self.assertNotIn('dummy', self.registry)

    def test_unregister_unknown(self):
        """Unregister returns False for unknown."""
        result = self.registry.unregister('unknown')
        self.assertFalse(result)

    def test_clear(self):
        """Clear removes all registrations."""
        self.registry.register(DummyIntegration)
        self.registry.get('dummy')  # Create instance

        self.registry.clear()

        self.assertEqual(len(self.registry), 0)
        self.assertIsNone(self.registry.get('dummy'))

    def test_clear_instances(self):
        """clear_instances removes cached instances."""
        self.registry.register(DummyIntegration)
        instance1 = self.registry.get('dummy')

        self.registry.clear_instances()
        instance2 = self.registry.get('dummy')

        self.assertIsNot(instance1, instance2)
