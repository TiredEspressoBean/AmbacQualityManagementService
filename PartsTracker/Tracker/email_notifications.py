"""
Email notification wrapper for Tracker app.

Provides a simple interface for sending emails that can be called
synchronously (immediate) or asynchronously (via Celery).
"""

import logging
from typing import List, Dict, Any
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


def send_weekly_order_update(customer_id: int, order_data: List[Dict[str, Any]], immediate: bool = False):
    """
    Send weekly order update email to a customer.

    Args:
        customer_id: Customer user ID
        order_data: List of order summary dicts
        immediate: If True, send now. If False, queue to Celery.

    Returns:
        Celery AsyncResult if queued, None if immediate
    """
    from .tasks import send_weekly_order_update_task

    if immediate:
        # Send synchronously (blocks)
        send_weekly_order_update_task(customer_id, order_data)
        logger.info(f"Sent weekly order update to customer {customer_id} (immediate)")
        return None
    else:
        # Queue to Celery (async)
        result = send_weekly_order_update_task.delay(customer_id, order_data)
        logger.info(f"Queued weekly order update for customer {customer_id} (task_id: {result.id})")
        return result


def send_invitation_email(invitation_id: int, immediate: bool = False):
    """
    Send invitation email to a user.

    Args:
        invitation_id: UserInvitation ID
        immediate: If True, send now. If False, queue to Celery.

    Returns:
        Celery AsyncResult if queued, None if immediate
    """
    from .tasks import send_invitation_email_task

    if immediate:
        # Send synchronously (blocks)
        send_invitation_email_task(invitation_id)
        logger.info(f"Sent invitation email for invitation {invitation_id} (immediate)")
        return None
    else:
        # Queue to Celery (async)
        result = send_invitation_email_task.delay(invitation_id)
        logger.info(f"Queued invitation email for invitation {invitation_id} (task_id: {result.id})")
        return result
