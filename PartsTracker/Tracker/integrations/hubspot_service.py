"""
HubSpot integration service implementation.

Wraps the existing hubspot/ module with the IntegrationService interface.
"""

import logging
import hashlib
import hmac
from typing import Optional
from datetime import datetime

import requests

from django.conf import settings
from django.utils import timezone

from .base_service import IntegrationService, IntegrationConfig, SyncResult
from .registry import registry

logger = logging.getLogger(__name__)


@registry.register
class HubSpotService(IntegrationService):
    """
    HubSpot CRM integration service.

    Provides sync operations for:
    - Deals → Orders
    - Contacts → Users
    - Companies → Companies
    - Notes (outbound only)
    """

    name = 'hubspot'
    display_name = 'HubSpot CRM'
    description = 'Sync deals, contacts, and companies from HubSpot CRM'

    def __init__(self, config: Optional[IntegrationConfig] = None):
        """Initialize with HubSpot-specific config."""
        if config is None:
            config = IntegrationConfig(
                enabled=bool(getattr(settings, 'HUBSPOT_API_KEY', None)),
                api_key=getattr(settings, 'HUBSPOT_API_KEY', None),
                api_url='https://api.hubapi.com/crm/',
                webhook_secret=getattr(settings, 'HUBSPOT_WEBHOOK_SECRET', None),
                sync_interval_minutes=60,
                debug_mode=getattr(settings, 'HUBSPOT_DEBUG', False),
            )
        super().__init__(config)

    # =========================================================================
    # SYNC METHODS
    # =========================================================================

    def sync_orders(self) -> SyncResult:
        """
        Sync deals from HubSpot to local Orders.

        Delegates to existing sync_all_deals() function.
        """
        from Tracker.hubspot.sync import sync_all_deals

        started_at = datetime.now()

        try:
            result = sync_all_deals()

            return SyncResult(
                success=result.get('status') == 'success',
                created=result.get('created', 0),
                updated=result.get('updated', 0),
                errors=[result.get('message')] if result.get('status') == 'error' else [],
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f'HubSpot order sync failed: {e}', exc_info=True)
            return SyncResult(
                success=False,
                errors=[str(e)],
                started_at=started_at,
                completed_at=datetime.now(),
            )

    def sync_customers(self) -> SyncResult:
        """
        Sync contacts/companies from HubSpot.

        Note: Currently, customers are synced as part of sync_orders().
        This method is a placeholder for standalone customer sync.
        """
        # Customers are currently synced as part of deal sync
        # Could be extended to do standalone contact sync
        return SyncResult(
            success=True,
            errors=['Customer sync is currently part of order sync'],
            started_at=datetime.now(),
            completed_at=datetime.now(),
        )

    # =========================================================================
    # PUSH METHODS
    # =========================================================================

    def push_note(self, order, message: str) -> bool:
        """
        Push a note to a HubSpot deal.

        Args:
            order: Order instance with hubspot_deal_id
            message: Note content

        Returns:
            True if successful
        """
        if not order.hubspot_deal_id:
            logger.warning(f'Cannot push note: Order {order.id} has no hubspot_deal_id')
            return False

        url = f'{self.config.api_url}v3/objects/notes'
        headers = self._get_headers()

        # Create note with association to deal
        payload = {
            'properties': {
                'hs_note_body': message,
                'hs_timestamp': timezone.now().isoformat(),
            },
            'associations': [{
                'to': {'id': order.hubspot_deal_id},
                'types': [{
                    'associationCategory': 'HUBSPOT_DEFINED',
                    'associationTypeId': 214  # Note to Deal
                }]
            }]
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f'Pushed note to HubSpot deal {order.hubspot_deal_id}')
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to push note to HubSpot: {e}')
            return False

    def push_order_status(self, order, status: str) -> bool:
        """
        Push order status update to HubSpot deal stage.

        Args:
            order: Order instance
            status: New status value (should match a HubSpot stage ID)

        Returns:
            True if successful
        """
        from Tracker.hubspot.api import update_deal_stage
        from Tracker.models import ExternalAPIOrderIdentifier

        if not order.hubspot_deal_id:
            return False

        try:
            # Find the stage by name or ID
            stage = ExternalAPIOrderIdentifier.objects.filter(
                stage_name__iexact=status
            ).first()

            if not stage:
                logger.warning(f'No HubSpot stage found for status: {status}')
                return False

            result = update_deal_stage(order.hubspot_deal_id, stage, order)
            return result is not None

        except Exception as e:
            logger.error(f'Failed to push order status to HubSpot: {e}')
            return False

    # =========================================================================
    # PULL METHODS
    # =========================================================================

    def pull_order(self, external_id: str) -> Optional[dict]:
        """
        Pull a single deal from HubSpot.

        Args:
            external_id: HubSpot deal ID

        Returns:
            Dict with deal properties, or None if not found
        """
        url = f'{self.config.api_url}v3/objects/deals/{external_id}'
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                'id': data['id'],
                'name': data['properties'].get('dealname'),
                'stage': data['properties'].get('dealstage'),
                'amount': data['properties'].get('amount'),
                'close_date': data['properties'].get('closedate'),
                'pipeline': data['properties'].get('pipeline'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to pull deal {external_id}: {e}')
            return None

    def pull_customer(self, external_id: str) -> Optional[dict]:
        """
        Pull a single contact from HubSpot.

        Args:
            external_id: HubSpot contact ID

        Returns:
            Dict with contact properties, or None if not found
        """
        
        url = f'{self.config.api_url}v3/objects/contacts/{external_id}'
        params = {'properties': 'firstname,lastname,email,phone,associatedcompanyid'}
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            return {
                'id': data['id'],
                'first_name': data['properties'].get('firstname', ''),
                'last_name': data['properties'].get('lastname', ''),
                'email': data['properties'].get('email'),
                'phone': data['properties'].get('phone'),
                'company_id': data['properties'].get('associatedcompanyid'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to pull contact {external_id}: {e}')
            return None

    def pull_company(self, external_id: str) -> Optional[dict]:
        """
        Pull a single company from HubSpot.

        Args:
            external_id: HubSpot company ID

        Returns:
            Dict with company properties, or None if not found
        """
        
        url = f'{self.config.api_url}v3/objects/companies/{external_id}'
        params = {'properties': 'name,domain,industry,city,state,country'}
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            return {
                'id': data['id'],
                'name': data['properties'].get('name'),
                'domain': data['properties'].get('domain'),
                'industry': data['properties'].get('industry'),
                'city': data['properties'].get('city'),
                'state': data['properties'].get('state'),
                'country': data['properties'].get('country'),
            }

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to pull company {external_id}: {e}')
            return None

    def pull_documents(self, external_id: str) -> list[dict]:
        """
        Pull files attached to a HubSpot deal.

        Args:
            external_id: HubSpot deal ID

        Returns:
            List of document dicts
        """
        
        # Get file associations for the deal
        url = f'{self.config.api_url}v4/objects/deals/{external_id}/associations/files'
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            documents = []
            for result in data.get('results', []):
                file_id = result.get('toObjectId')
                if file_id:
                    file_info = self._get_file_info(file_id)
                    if file_info:
                        documents.append(file_info)

            return documents

        except requests.exceptions.RequestException as e:
            logger.error(f'Failed to pull documents for deal {external_id}: {e}')
            return []

    # =========================================================================
    # WEBHOOK HANDLING
    # =========================================================================

    def handle_webhook(self, payload: dict, headers: dict) -> dict:
        """
        Handle incoming HubSpot webhook.

        Args:
            payload: Webhook request body (list of events)
            headers: Request headers

        Returns:
            Processing result
        """
        from Tracker.models import Orders, ExternalAPIOrderIdentifier

        processed = 0
        errors = []

        # HubSpot sends array of events
        events = payload if isinstance(payload, list) else [payload]

        for event in events:
            try:
                # Handle deal stage changes
                if (event.get('subscriptionType') == 'deal.propertyChange' and
                        event.get('propertyName') == 'dealstage'):

                    deal_id = str(event.get('objectId'))
                    new_stage_id = event.get('propertyValue')

                    # Update local order
                    try:
                        order = Orders.objects.get(hubspot_deal_id=deal_id)
                        stage = ExternalAPIOrderIdentifier.objects.get(API_id=new_stage_id)

                        order.current_hubspot_gate = stage
                        order._skip_hubspot_push = True  # Prevent loop
                        order.save()

                        processed += 1
                        logger.info(f'Updated order {order.id} stage from webhook')

                    except Orders.DoesNotExist:
                        logger.debug(f'No order found for deal {deal_id}')
                    except ExternalAPIOrderIdentifier.DoesNotExist:
                        logger.warning(f'Unknown stage ID: {new_stage_id}')

            except Exception as e:
                errors.append(str(e))
                logger.error(f'Webhook processing error: {e}')

        return {
            'status': 'ok' if not errors else 'partial',
            'processed': processed,
            'errors': errors,
        }

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify HubSpot webhook signature.

        Args:
            payload: Raw request body
            signature: X-HubSpot-Signature header value

        Returns:
            True if signature is valid
        """
        if not self.config.webhook_secret:
            logger.warning('No webhook secret configured, skipping verification')
            return True  # Allow in dev, but log warning

        # HubSpot v1 signature: SHA-256(secret + body)
        expected = hmac.new(
            self.config.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _get_headers(self) -> dict:
        """Get API request headers."""
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
        }

    def _get_file_info(self, file_id: str) -> Optional[dict]:
        """Get file details from HubSpot Files API."""
        
        url = f'https://api.hubapi.com/files/v3/files/{file_id}'
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            return {
                'id': data['id'],
                'file_name': data.get('name'),
                'file_url': data.get('url'),
                'size': data.get('size'),
                'type': data.get('type'),
            }

        except requests.exceptions.RequestException:
            return None

    def test_connection(self) -> tuple[bool, str]:
        """Test HubSpot API connection."""
        
        url = f'{self.config.api_url}v3/objects/deals'
        params = {'limit': 1}
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return True, 'Successfully connected to HubSpot API'

        except requests.exceptions.RequestException as e:
            return False, f'Connection failed: {e}'

    def sync_pipeline_stages(self, pipeline_id: str) -> int:
        """
        Sync pipeline stages from HubSpot.

        Args:
            pipeline_id: HubSpot pipeline ID

        Returns:
            Number of stages synced
        """
        from Tracker.hubspot.api import update_stages
        return update_stages(pipeline_id) or 0

    def get_status(self) -> dict:
        """Get detailed HubSpot integration status."""
        from Tracker.models import HubSpotSyncLog

        status = super().get_status()

        # Add last sync info
        last_sync = HubSpotSyncLog.objects.filter(status='success').first()
        if last_sync:
            status['last_sync'] = {
                'completed_at': last_sync.completed_at.isoformat() if last_sync.completed_at else None,
                'deals_processed': last_sync.deals_processed,
                'deals_created': last_sync.deals_created,
                'deals_updated': last_sync.deals_updated,
            }

        return status
