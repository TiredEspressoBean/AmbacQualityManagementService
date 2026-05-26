"""
Email notification wrapper for Tracker app.

Provides a simple interface for sending emails that can be called
synchronously (immediate) or asynchronously (via Celery).
"""

import logging
from typing import List, Dict, Any
from django.contrib.auth import get_user_model
from django.db import transaction

logger = logging.getLogger(__name__)
User = get_user_model()


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
        # Queue to Celery after the enclosing transaction commits.
        def _dispatch():
            result = send_invitation_email_task.delay(invitation_id)
            logger.info(f"Queued invitation email for invitation {invitation_id} (task_id: {result.id})")
        transaction.on_commit(_dispatch)
        return None
