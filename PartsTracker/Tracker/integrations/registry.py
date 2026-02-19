"""
Integration registry for managing external system integrations.

The registry provides a central place to:
- Register available integrations
- Discover enabled integrations
- Get integration instances by name

Usage:
    from Tracker.integrations import registry

    # Register an integration (usually done in apps.py or __init__.py)
    registry.register(HubSpotService)

    # Get a specific integration
    hubspot = registry.get('hubspot')

    # Get all enabled integrations
    for integration in registry.get_enabled():
        integration.sync_orders()
"""

import logging
from typing import Optional, Type

from .base_service import IntegrationService

logger = logging.getLogger(__name__)


class IntegrationRegistry:
    """
    Registry for managing integration services.

    Singleton pattern - use the module-level `registry` instance.
    """

    def __init__(self):
        self._integrations: dict[str, Type[IntegrationService]] = {}
        self._instances: dict[str, IntegrationService] = {}

    def register(self, service_class: Type[IntegrationService]) -> Type[IntegrationService]:
        """
        Register an integration service class.

        Can be used as a decorator:

            @registry.register
            class HubSpotService(IntegrationService):
                name = 'hubspot'
                ...

        Or called directly:

            registry.register(HubSpotService)

        Args:
            service_class: IntegrationService subclass to register

        Returns:
            The service class (for decorator use)

        Raises:
            ValueError: If name is empty or already registered
        """
        name = service_class.name

        if not name:
            raise ValueError(f'{service_class.__name__} must have a non-empty name attribute')

        if name in self._integrations:
            logger.warning(f'Integration "{name}" is being re-registered')

        self._integrations[name] = service_class
        logger.debug(f'Registered integration: {name}')

        return service_class

    def unregister(self, name: str) -> bool:
        """
        Unregister an integration by name.

        Args:
            name: Integration name

        Returns:
            True if unregistered, False if not found
        """
        if name in self._integrations:
            del self._integrations[name]
            if name in self._instances:
                del self._instances[name]
            return True
        return False

    def get(self, name: str) -> Optional[IntegrationService]:
        """
        Get an integration service instance by name.

        Instances are cached - same instance returned for multiple calls.

        Args:
            name: Integration name (e.g., 'hubspot')

        Returns:
            IntegrationService instance, or None if not registered
        """
        if name not in self._integrations:
            return None

        if name not in self._instances:
            self._instances[name] = self._integrations[name]()

        return self._instances[name]

    def get_all(self) -> list[IntegrationService]:
        """
        Get all registered integration instances.

        Returns:
            List of all registered IntegrationService instances
        """
        return [self.get(name) for name in self._integrations.keys()]

    def get_enabled(self) -> list[IntegrationService]:
        """
        Get all enabled integration instances.

        Returns:
            List of enabled IntegrationService instances
        """
        return [
            integration
            for integration in self.get_all()
            if integration.is_enabled()
        ]

    def get_configured(self) -> list[IntegrationService]:
        """
        Get all configured (but not necessarily enabled) integrations.

        Returns:
            List of configured IntegrationService instances
        """
        return [
            integration
            for integration in self.get_all()
            if integration.is_configured()
        ]

    def list_names(self) -> list[str]:
        """
        List all registered integration names.

        Returns:
            List of integration names
        """
        return list(self._integrations.keys())

    def clear(self):
        """
        Clear all registered integrations.

        Primarily for testing.
        """
        self._integrations.clear()
        self._instances.clear()

    def clear_instances(self):
        """
        Clear cached instances (but keep registrations).

        Useful for testing or when config changes.
        """
        self._instances.clear()

    def __contains__(self, name: str) -> bool:
        """Check if integration is registered."""
        return name in self._integrations

    def __len__(self) -> int:
        """Number of registered integrations."""
        return len(self._integrations)

    def __repr__(self) -> str:
        names = ', '.join(self._integrations.keys()) or 'none'
        return f'<IntegrationRegistry: {names}>'


# Module-level singleton instance
registry = IntegrationRegistry()
