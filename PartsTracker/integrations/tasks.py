"""
Integration Celery tasks.

sync_all_integrations_task: Dispatched by Celery Beat, iterates enabled integrations.
sync_hubspot_deals_task: HubSpot-specific sync.
push_hubspot_deal_stage_task: Push stage change to HubSpot (called from signal).
cleanup_processed_webhooks: Prune old ProcessedWebhook records.
"""

import logging
from datetime import timedelta

from celery import Task, shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


class RetryableIntegrationTask(Task):
    """Base task for integration operations with automatic retry on transient failures."""
    autoretry_for = (ConnectionError, TimeoutError, OSError)
    retry_backoff = True
    retry_backoff_max = 900  # Max 15 minutes between retries
    retry_jitter = True
    max_retries = 4
    soft_time_limit = 60
    time_limit = 120


@shared_task
def sync_all_integrations_task():
    """
    Dispatch sync tasks for all enabled integrations.
    Called by Celery Beat on schedule.
    """
    from integrations.models.config import IntegrationConfig
    from integrations.services.registry import get_adapter

    # tenant-safe: intentional cross-tenant dispatcher; dispatches per-tenant sync tasks
    for config in IntegrationConfig.objects.filter(is_enabled=True):
        try:
            adapter = get_adapter(config.provider)
            adapter.dispatch_sync_task(config)
            logger.info(f"Dispatched sync for {config}")
        except Exception as e:
            logger.error(f"Failed to dispatch sync for {config}: {e}")


@shared_task(bind=True, base=RetryableIntegrationTask)
def sync_hubspot_deals_task(self, integration_id):
    """Sync HubSpot deals for a specific integration."""
    from integrations.models.config import IntegrationConfig
    from integrations.adapters.hubspot.sync import sync_all_deals

    # tenant-safe: integration_id dispatched from tenant-scoped caller; downstream ops use integration.tenant
    integration = IntegrationConfig.objects.get(id=integration_id)

    if not integration.is_enabled:
        return {'status': 'skipped', 'reason': 'integration_disabled'}

    return sync_all_deals(integration)


@shared_task(bind=True, base=RetryableIntegrationTask)
def push_hubspot_deal_stage_task(self, integration_id, deal_id, stage_id, order_id):
    """Push a stage change to HubSpot. Called from post_save signal on HubSpotOrderLink."""
    from integrations.models.config import IntegrationConfig
    from integrations.models.links.hubspot import HubSpotOrderLink, HubSpotPipelineStage
    from integrations.services.registry import get_adapter

    integration = IntegrationConfig.objects.get(id=integration_id)
    link = HubSpotOrderLink.objects.get(integration=integration, deal_id=deal_id)
    stage = HubSpotPipelineStage.objects.get(id=stage_id)

    adapter = get_adapter(integration.provider)
    result = adapter.push_order_status(integration, link=link, status=stage)

    if result:
        logger.info(f"Pushed stage '{stage.stage_name}' to HubSpot deal {deal_id}")
    else:
        logger.error(f"Failed to push stage to HubSpot deal {deal_id}")

    return {'status': 'success' if result else 'failed', 'deal_id': deal_id}


@shared_task
def cleanup_processed_webhooks(days=30):
    """Delete ProcessedWebhook records older than N days."""
    from integrations.models.config import ProcessedWebhook

    cutoff = timezone.now() - timedelta(days=days)
    # tenant-safe: intentional cross-tenant cleanup of expired webhook records
    deleted, _ = ProcessedWebhook.objects.filter(processed_at__lt=cutoff).delete()
    logger.info(f"Cleaned up {deleted} processed webhook records older than {days} days")
    return {'deleted': deleted}
