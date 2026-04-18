"""
HubSpot adapter — reference implementation.

Uses the official hubspot-api-client SDK for API calls.
DRF serializers handle transform/validate/load.
"""

from integrations.adapters.base import BaseAdapter
from .manifest import MANIFEST


class HubSpotAdapter(BaseAdapter):
    manifest = MANIFEST

    def test_connection(self, integration):
        from hubspot import HubSpot
        try:
            client = HubSpot(access_token=integration.api_key)
            client.crm.deals.basic_api.get_page(limit=1)
            return True, 'Connected to HubSpot API'
        except Exception as e:
            return False, f'Connection failed: {e}'

    def dispatch_sync_task(self, integration):
        from django.db import transaction
        from integrations.tasks import sync_hubspot_deals_task
        integration_id = str(integration.id)
        # Wrap so callers inside an ORM transaction (e.g. a viewset action
        # under ATOMIC_REQUESTS) don't dispatch before commit. Outside a
        # transaction, on_commit fires immediately.
        transaction.on_commit(lambda: sync_hubspot_deals_task.delay(integration_id=integration_id))

    def sync_orders(self, integration):
        from .sync import sync_all_deals
        return sync_all_deals(integration)

    # NOTE: sync_companies is NOT overridden. Companies sync as part of sync_orders
    # (contacts carry company associations). Capability discovery correctly
    # won't report 'company_sync'.

    def push_order_status(self, integration, link, status):
        from hubspot import HubSpot
        try:
            client = HubSpot(access_token=integration.api_key)
            client.crm.deals.basic_api.update(
                deal_id=link.deal_id,
                simple_public_object_input={'properties': {'dealstage': status.api_id}}
            )
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to push deal stage: {e}")
            return False

    def handle_webhook(self, request, integration):
        from integrations.webhooks.handlers.hubspot import handle_hubspot_webhook
        return handle_hubspot_webhook(request, integration)

    @property
    def has_pipeline_stages(self):
        return True
