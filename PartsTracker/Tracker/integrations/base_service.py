"""
Abstract base class for integration services.

All external integrations (HubSpot, ERP CSV, Salesforce, etc.) should
implement this interface to ensure consistent behavior across integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """
    Configuration for an integration.

    Can be loaded from Django settings, database, or environment variables.
    """
    enabled: bool = False
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    sync_interval_minutes: int = 60
    debug_mode: bool = False
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_settings(cls, prefix: str) -> 'IntegrationConfig':
        """
        Load configuration from Django settings.

        Args:
            prefix: Settings prefix (e.g., 'HUBSPOT' for HUBSPOT_API_KEY)

        Returns:
            IntegrationConfig instance
        """
        from django.conf import settings

        return cls(
            enabled=getattr(settings, f'{prefix}_ENABLED', False),
            api_key=getattr(settings, f'{prefix}_API_KEY', None),
            api_url=getattr(settings, f'{prefix}_API_URL', None),
            webhook_secret=getattr(settings, f'{prefix}_WEBHOOK_SECRET', None),
            sync_interval_minutes=getattr(settings, f'{prefix}_SYNC_INTERVAL', 60),
            debug_mode=getattr(settings, f'{prefix}_DEBUG', False),
        )


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    created: int = 0
    updated: int = 0
    deleted: int = 0
    errors: list = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def total_processed(self) -> int:
        return self.created + self.updated + self.deleted

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'created': self.created,
            'updated': self.updated,
            'deleted': self.deleted,
            'total_processed': self.total_processed,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds,
        }


class IntegrationService(ABC):
    """
    Abstract base class for integration services.

    All integrations must implement this interface. This ensures:
    - Consistent sync patterns across integrations
    - Easy testing via mock implementations
    - Clean separation of concerns
    - Registry-based discovery

    Example implementation:

        class HubSpotService(IntegrationService):
            name = 'hubspot'
            display_name = 'HubSpot CRM'

            def sync_orders(self) -> SyncResult:
                # Pull deals from HubSpot, create/update Orders
                ...
    """

    # Class-level attributes - override in subclass
    name: str = ''  # Unique identifier (e.g., 'hubspot', 'erp_csv')
    display_name: str = ''  # Human-readable name
    description: str = ''  # Brief description

    def __init__(self, config: Optional[IntegrationConfig] = None):
        """
        Initialize the integration service.

        Args:
            config: Integration configuration. If None, loads from settings.
        """
        if config is None:
            config = IntegrationConfig.from_settings(self.name.upper())
        self.config = config
        self._client = None

    def is_enabled(self) -> bool:
        """Check if this integration is enabled."""
        return self.config.enabled and self.config.api_key is not None

    def is_configured(self) -> bool:
        """Check if this integration has required configuration."""
        return self.config.api_key is not None

    # =========================================================================
    # SYNC METHODS - Override these in subclass
    # =========================================================================

    @abstractmethod
    def sync_orders(self) -> SyncResult:
        """
        Sync orders/deals from the external system.

        Pull orders from external system and create/update local Orders.

        Returns:
            SyncResult with counts and any errors
        """
        pass

    @abstractmethod
    def sync_customers(self) -> SyncResult:
        """
        Sync customers/contacts from the external system.

        Pull contacts and companies, create/update local Users and Companies.

        Returns:
            SyncResult with counts and any errors
        """
        pass

    def sync_all(self) -> dict[str, SyncResult]:
        """
        Run all sync operations.

        Returns:
            Dict mapping sync type to SyncResult
        """
        results = {}

        if self.is_enabled():
            results['customers'] = self.sync_customers()
            results['orders'] = self.sync_orders()

        return results

    # =========================================================================
    # PUSH METHODS - Override these in subclass
    # =========================================================================

    @abstractmethod
    def push_note(self, order, message: str) -> bool:
        """
        Push a note/activity to the external system.

        Args:
            order: Order instance with external ID
            message: Note content

        Returns:
            True if successful
        """
        pass

    def push_order_status(self, order, status: str) -> bool:
        """
        Push order status update to external system.

        Optional - not all integrations support this.

        Args:
            order: Order instance
            status: New status value

        Returns:
            True if successful, False if not supported
        """
        return False  # Default: not supported

    # =========================================================================
    # PULL METHODS - Override these in subclass
    # =========================================================================

    @abstractmethod
    def pull_order(self, external_id: str) -> Optional[dict]:
        """
        Pull a single order/deal from the external system.

        Args:
            external_id: ID in external system

        Returns:
            Dict of order data, or None if not found
        """
        pass

    @abstractmethod
    def pull_customer(self, external_id: str) -> Optional[dict]:
        """
        Pull a single customer/contact from the external system.

        Args:
            external_id: ID in external system

        Returns:
            Dict of customer data, or None if not found
        """
        pass

    def pull_documents(self, external_id: str) -> list[dict]:
        """
        Pull documents attached to an order in the external system.

        Optional - not all integrations support this.

        Args:
            external_id: Order ID in external system

        Returns:
            List of document dicts with file_url, file_name, etc.
        """
        return []  # Default: not supported

    # =========================================================================
    # WEBHOOK HANDLING - Override in subclass if supported
    # =========================================================================

    def handle_webhook(self, payload: dict, headers: dict) -> dict:
        """
        Handle incoming webhook from external system.

        Args:
            payload: Webhook request body
            headers: Webhook request headers

        Returns:
            Dict with processing result
        """
        return {'status': 'not_supported'}

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature for security.

        Args:
            payload: Raw request body
            signature: Signature from headers

        Returns:
            True if signature is valid
        """
        return False  # Default: no verification

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def test_connection(self) -> tuple[bool, str]:
        """
        Test connection to external system.

        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to pull something simple
            self.pull_order('test')
            return True, 'Connection successful'
        except Exception as e:
            return False, str(e)

    def get_status(self) -> dict:
        """
        Get integration status for monitoring/debugging.

        Returns:
            Dict with status information
        """
        return {
            'name': self.name,
            'display_name': self.display_name,
            'enabled': self.is_enabled(),
            'configured': self.is_configured(),
            'debug_mode': self.config.debug_mode,
        }

    def __repr__(self) -> str:
        status = 'enabled' if self.is_enabled() else 'disabled'
        return f'<{self.__class__.__name__} ({self.name}) [{status}]>'
