"""
Base classes for integration adapters.

BaseAdapter: All adapters subclass this. Required methods raise NotImplementedError.
    Capabilities are discovered via method introspection (no enum, no manifest declaration).
    Follows the standard Django ecosystem pattern (django-allauth, Saleor, Celery).

BaseFetcher: Fallback for providers without official Python SDKs.
    Handles paginated HTTP extraction with auth, retry, and rate limit handling.
    Not used when an official SDK is available (e.g. hubspot-api-client).
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ADAPTER_API_VERSION = 1


class BaseAdapter:
    """
    Base class for all integration adapters.

    Required methods raise NotImplementedError — subclasses must implement them.
    Optional methods have default implementations that return safe no-op values.
    Capabilities are discovered by introspection — if you override a method, you support it.

    To add a new integration:
    1. Create manifest.py with MANIFEST dict (metadata, auth type, link models)
    2. Create serializers.py with inbound serializers (one per entity type) + config serializer
    3. Subclass BaseAdapter, wire SDK/fetchers to serializers
    4. Register in settings.INTEGRATION_ADAPTERS
    """

    manifest = None  # Subclass sets this to the MANIFEST dict

    # --- Required ---

    def test_connection(self, integration):
        """
        Test that the integration's credentials and config are valid.

        Args:
            integration: IntegrationConfig instance

        Returns:
            tuple[bool, str]: (success, message)
        """
        raise NotImplementedError

    def dispatch_sync_task(self, integration):
        """
        Queue the provider-specific Celery sync task.

        Args:
            integration: IntegrationConfig instance
        """
        raise NotImplementedError

    # --- Optional: Inbound sync ---

    def sync_orders(self, integration):
        """Pull orders/deals, create/update local Orders + link records."""
        return {'status': 'not_supported'}

    def sync_companies(self, integration):
        """Pull companies/accounts, create/update local Companies + link records."""
        return {'status': 'not_supported'}

    def sync_contacts(self, integration):
        """Pull contacts/users. Some providers handle this as part of sync_orders."""
        return {'status': 'not_supported'}

    # --- Optional: Outbound push ---

    def push_order_status(self, integration, link, status):
        """Push an order status/stage change to the external system."""
        return False

    # --- Optional: Webhooks ---

    def handle_webhook(self, request, integration):
        """Process an incoming webhook."""
        return {'status': 'not_supported'}

    # --- Optional: Pipeline stages ---

    @property
    def has_pipeline_stages(self):
        """Override to return True if this adapter syncs pipeline/stage data."""
        return False

    # --- Optional: Single-record fetch ---

    def pull_order(self, integration, external_id):
        """Fetch a single order/deal."""
        return None

    def pull_company(self, integration, external_id):
        """Fetch a single company/account."""
        return None


class BaseFetcher:
    """
    Handles paginated extraction from external REST APIs.

    Uses requests.Session with urllib3 retry for HTTP-level resilience.
    Subclasses override get_page() for provider-specific pagination.

    Not used when an official SDK is available (e.g. hubspot-api-client handles
    pagination and rate limits natively). This is the fallback for APIs without SDKs.
    """

    max_retries = 3
    backoff_factor = 1
    retry_status_codes = [429, 500, 502, 503, 504]

    def get_session(self, integration):
        """Build a requests.Session with retry/backoff and auth headers."""
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.retry_status_codes,
        )
        session.mount('https://', HTTPAdapter(max_retries=retry))
        session.headers.update(self.get_auth_headers(integration))
        return session

    def get_auth_headers(self, integration):
        """Return auth headers. Override for OAuth2, etc."""
        return {
            'Authorization': f'Bearer {integration.api_key}',
            'Content-Type': 'application/json',
        }

    def fetch_all(self, integration, since=None):
        """Yield all records, handling pagination automatically."""
        session = self.get_session(integration)
        next_cursor = None
        while True:
            records, next_cursor = self.get_page(
                session, integration, cursor=next_cursor, since=since
            )
            yield from records
            if not next_cursor:
                break

    def get_page(self, session, integration, cursor=None, since=None):
        """
        Fetch one page of results. Override in subclass.

        Returns:
            tuple: (list[dict], next_cursor or None)
        """
        raise NotImplementedError
