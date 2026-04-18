"""
HubSpot webhook handler.

Processes inbound webhook events from HubSpot. Currently handles:
- deal.propertyChange (dealstage) — updates HubSpotOrderLink.current_stage
"""

import json
import logging

from integrations.models.links.hubspot import HubSpotOrderLink, HubSpotPipelineStage

logger = logging.getLogger(__name__)


def handle_hubspot_webhook(request, integration):
    """
    Process HubSpot webhook payload.

    HubSpot sends an array of events. Each event has:
    - subscriptionType: 'deal.propertyChange'
    - propertyName: 'dealstage'
    - propertyValue: new stage API ID
    - objectId: deal ID
    - occurredAt: timestamp (ms since epoch)

    Args:
        request: Django HttpRequest
        integration: IntegrationConfig instance

    Returns:
        dict with processing result
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return {'status': 'error', 'message': 'Invalid JSON'}

    events = payload if isinstance(payload, list) else [payload]
    processed = 0
    errors = []

    for event in events:
        try:
            if (event.get('subscriptionType') == 'deal.propertyChange'
                    and event.get('propertyName') == 'dealstage'):

                deal_id = str(event.get('objectId'))
                new_stage_api_id = event.get('propertyValue')
                event_timestamp = event.get('occurredAt')

                try:
                    link = HubSpotOrderLink.objects.get(
                        integration=integration, deal_id=deal_id
                    )
                except HubSpotOrderLink.DoesNotExist:
                    logger.debug(f"No order linked to deal {deal_id}")
                    continue

                # Out-of-order protection: skip if event is older than last sync
                if event_timestamp and link.last_synced_at:
                    from django.utils import timezone
                    from datetime import datetime
                    event_time = datetime.fromtimestamp(
                        event_timestamp / 1000, tz=timezone.utc
                    )
                    if event_time < link.last_synced_at:
                        logger.debug(f"Skipping stale webhook for deal {deal_id}")
                        continue

                try:
                    stage = HubSpotPipelineStage.objects.get(
                        integration=integration, api_id=new_stage_api_id
                    )
                except HubSpotPipelineStage.DoesNotExist:
                    logger.warning(
                        f"Unknown stage API ID: {new_stage_api_id} for deal {deal_id}"
                    )
                    continue

                link.current_stage = stage
                link.last_synced_stage_name = stage.stage_name
                link.last_synced_at = timezone.now()
                link._skip_external_push = True
                link.save()

                # Also update native milestone on the order
                if stage.mapped_milestone:
                    link.order.current_milestone = stage.mapped_milestone
                    link.order.save(update_fields=['current_milestone'])

                processed += 1
                logger.info(f"Updated deal {deal_id} to stage '{stage.stage_name}' via webhook")

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Webhook event processing error: {e}", exc_info=True)

    return {
        'status': 'ok' if not errors else 'partial',
        'processed': processed,
        'errors': errors,
    }
