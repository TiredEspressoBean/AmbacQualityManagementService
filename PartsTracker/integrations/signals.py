"""
Integration signals.

Handles outbound push when link model data changes.
The signal checks FieldTracker to see if current_stage actually changed,
and respects _skip_external_push flag to prevent loops during sync.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from integrations.models.links.hubspot import HubSpotOrderLink

logger = logging.getLogger(__name__)


@receiver(post_save, sender=HubSpotOrderLink)
def push_stage_change_to_hubspot(sender, instance, **kwargs):
    """When a HubSpotOrderLink's stage changes, push to HubSpot via Celery."""
    # Don't push if integration is disabled
    if not instance.integration.is_enabled:
        return

    # Don't push if flag is set (set during inbound sync/webhook to prevent loops)
    if getattr(instance, '_skip_external_push', False):
        return

    # Don't push if stage hasn't actually changed (FieldTracker)
    if not instance.stage_tracker.has_changed('current_stage'):
        return

    # Don't push if there's no stage set
    if not instance.current_stage_id:
        return

    from integrations.tasks import push_hubspot_deal_stage_task
    push_hubspot_deal_stage_task.delay(
        integration_id=str(instance.integration_id),
        deal_id=instance.deal_id,
        stage_id=str(instance.current_stage_id),
        order_id=str(instance.order_id),
    )
    logger.info(
        f"Queued HubSpot push for deal {instance.deal_id} "
        f"-> stage {instance.current_stage_id}"
    )
