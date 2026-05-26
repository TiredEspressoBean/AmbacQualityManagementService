"""
Notification handlers using composition pattern.

Each notification type has:
1. Context builder - builds fresh data from related objects
2. Send validator - checks if notification should send
3. Senders - dict of channel_type -> send function
"""

import logging
from typing import Dict, Any, Optional, Callable
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.db.models import Avg

logger = logging.getLogger(__name__)


def get_frontend_url() -> str:
    """Get the frontend URL for links in notifications."""
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


# ============================================================================
# CONTEXT BUILDERS - Build fresh context from related objects
# ============================================================================

# Removed: `build_weekly_report_context`.
# Replaced by CustomerActiveOrdersProvider in
# Tracker/services/core/notifications/scheduled_content/customer_active_orders.py.


def build_capa_context(task) -> Optional[Dict[str, Any]]:
    """Build context for CAPA reminder notifications."""
    capa = task.related_object
    if not capa:
        return None

    # Handle None due_date
    if not capa.due_date:
        days_until = 0
        is_overdue = False
    else:
        # Handle both date and datetime
        due = capa.due_date
        if hasattr(due, 'date'):
            due = due.date()
        days_until = (due - timezone.now().date()).days
        is_overdue = days_until < 0

    # Get CAPA number - could be capa_number or disposition_number depending on model
    capa_number = getattr(capa, 'capa_number', None) or getattr(capa, 'disposition_number', str(capa))

    # Get status - CAPA uses status field
    status = getattr(capa, 'status', None) or getattr(capa, 'current_state', 'Unknown')
    # Convert to display name if it's a choice field
    if hasattr(capa, 'get_status_display'):
        status = capa.get_status_display()

    return {
        'recipient': task.recipient,
        'disposition_number': capa_number,  # Template uses this name
        'due_date': capa.due_date,
        'days_until_due': days_until,
        'is_overdue': is_overdue,
        'current_state': status,
        'attempt_count': task.attempt_count,
        'capa_id': capa.id,
        'frontend_url': get_frontend_url(),
    }


def build_approval_request_context(task) -> Optional[Dict[str, Any]]:
    """Build context for approval request notifications."""
    approval_request = task.related_object
    if not approval_request:
        return None

    content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
    content_obj = approval_request.content_object
    content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

    return {
        'recipient': task.recipient,
        'content_type': content_type.title(),
        'content_title': content_title,
        'requested_by': approval_request.requested_by.get_full_name() or approval_request.requested_by.username,
        'due_date': approval_request.due_date,
        'approval_id': approval_request.id,
        'frontend_url': get_frontend_url(),
    }


def build_approval_decision_context(task) -> Optional[Dict[str, Any]]:
    """Build context for approval decision notifications."""
    approval_request = task.related_object
    if not approval_request:
        return None

    content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
    content_obj = approval_request.content_object
    content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

    return {
        'recipient': task.recipient,
        'content_type': content_type.title(),
        'content_title': content_title,
        'status': approval_request.status,
        'completed_at': approval_request.completed_at,
        'comments': getattr(approval_request, 'comments', None),
        'approval_id': approval_request.id,
        'frontend_url': get_frontend_url(),
    }


def build_approval_escalation_context(task) -> Optional[Dict[str, Any]]:
    """Build context for approval escalation notifications."""
    approval_request = task.related_object
    if not approval_request:
        return None

    content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
    content_obj = approval_request.content_object
    content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

    days_overdue = 0
    if approval_request.due_date:
        delta = timezone.now().date() - approval_request.due_date
        days_overdue = max(0, delta.days)

    return {
        'recipient': task.recipient,
        'content_type': content_type.title(),
        'content_title': content_title,
        'requested_by': approval_request.requested_by.get_full_name() or approval_request.requested_by.username,
        'due_date': approval_request.due_date,
        'days_overdue': days_overdue,
        'approval_id': approval_request.id,
        'frontend_url': get_frontend_url(),
    }


# ============================================================================
# SEND VALIDATORS - Check if notification should send
# ============================================================================

# Removed: `validate_weekly_report_send` (no longer referenced).


def validate_capa_send(task) -> bool:
    """Check if CAPA notification should send."""
    capa = task.related_object

    if not capa:
        task.status = 'CANCELLED'
        task.save()
        return False

    # Check status field (CAPA model uses 'status', others might use 'current_state')
    status = getattr(capa, 'status', None) or getattr(capa, 'current_state', None)
    if status in ('CLOSED', 'CANCELLED'):
        task.status = 'CANCELLED'
        task.save()
        return False

    return True


def validate_approval_request_send(task) -> bool:
    """Check if approval request notification should send."""
    if not task.related_object:
        task.status = 'CANCELLED'
        task.save()
        return False

    approval_request = task.related_object
    # Don't send if already decided
    if hasattr(approval_request, 'status') and approval_request.status != 'PENDING':
        task.status = 'CANCELLED'
        task.save()
        return False

    return True


def validate_approval_decision_send(task) -> bool:
    """Check if approval decision notification should send."""
    if not task.related_object:
        task.status = 'CANCELLED'
        task.save()
        return False
    return True


def validate_approval_escalation_send(task) -> bool:
    """Check if approval escalation notification should send."""
    if not task.related_object:
        task.status = 'CANCELLED'
        task.save()
        return False

    approval_request = task.related_object
    # Don't escalate if already decided
    if hasattr(approval_request, 'status') and approval_request.status != 'PENDING':
        task.status = 'CANCELLED'
        task.save()
        return False

    return True


# ============================================================================
# CHANNEL SENDERS - Send via different channels
# ============================================================================

def send_via_email(task, context: Dict[str, Any], template_base: str) -> bool:
    """
    Send notification via email.

    Args:
        task: NotificationTask instance
        context: Template context dict
        template_base: Base template path (e.g., 'emails/weekly_customer_update')

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Render email templates
        subject = render_to_string(f'{template_base}_subject.txt', context).strip()
        html_content = render_to_string(f'{template_base}.html', context)
        text_content = render_to_string(f'{template_base}.txt', context)

        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[task.recipient.email],
            html_message=html_content,
            fail_silently=False,
        )

        logger.info(f"Sent {task.notification_type} email to {task.recipient.email}")
        return True

    except Exception as e:
        logger.error(f"Error sending {task.notification_type} email to {task.recipient.email}: {e}")
        return False


def send_via_in_app(task, context: Dict[str, Any], notification_data: Dict[str, Any]) -> bool:
    """
    Send in-app notification.

    For now, this is a placeholder. In the future, this would create
    an InAppNotification record that the frontend polls/subscribes to.
    """
    logger.info(f"In-app notification placeholder for {task.recipient.email}: {notification_data.get('title')}")
    # TODO: Implement in-app notification storage when ready
    return True


# ============================================================================
# NOTIFICATION HANDLERS - Compose context + validation + sending
# ============================================================================

class NotificationHandler:
    """
    Handler for a specific notification type.
    Composes context builder, validator, and senders.
    """

    def __init__(
        self,
        context_builder: Callable,
        send_validator: Callable,
        senders: Dict[str, Callable]
    ):
        self.context_builder = context_builder
        self.send_validator = send_validator
        self.senders = senders

    def should_send(self, task) -> bool:
        """Check if notification should send."""
        return self.send_validator(task)

    def send(self, task) -> bool:
        """Send notification via appropriate channel."""
        # Build fresh context
        context = self.context_builder(task)
        if not context:
            logger.info(f"No context for {task.notification_type}, skipping")
            return False

        # Get sender for this channel
        sender = self.senders.get(task.channel_type)
        if not sender:
            logger.error(f"No sender configured for channel: {task.channel_type}")
            return False

        # Send it
        return sender(task, context)


# ============================================================================
# NOTIFICATION REGISTRY - Map notification types to handlers
# ============================================================================

NOTIFICATION_HANDLERS = {
    # WEEKLY_REPORT removed — replaced by personal NotificationSchedule
    # rows fired via `Tracker.tasks.fire_one_schedule`.

    'CAPA_REMINDER': NotificationHandler(
        context_builder=build_capa_context,
        send_validator=validate_capa_send,
        senders={
            'EMAIL': lambda task, ctx: send_via_email(task, ctx, 'emails/capa_reminder'),
            'IN_APP': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'warning' if ctx.get('is_overdue') else 'info',
                'title': f"CAPA Action Required: {ctx['disposition_number']}",
                'message': f"Due in {ctx['days_until_due']} days" if not ctx['is_overdue'] else f"OVERDUE by {abs(ctx['days_until_due'])} days",
                'link': f"/qa/quarantine/{ctx['capa_id']}/",
            }),
        }
    ),

    'APPROVAL_REQUEST': NotificationHandler(
        context_builder=build_approval_request_context,
        send_validator=validate_approval_request_send,
        senders={
            'EMAIL': lambda task, ctx: send_via_email(task, ctx, 'emails/approval_request'),
            'IN_APP': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'info',
                'title': f"Approval Required: {ctx['content_title']}",
                'message': f"Requested by {ctx['requested_by']}",
                'link': '/inbox',
            }),
        }
    ),

    'APPROVAL_DECISION': NotificationHandler(
        context_builder=build_approval_decision_context,
        send_validator=validate_approval_decision_send,
        senders={
            'EMAIL': lambda task, ctx: send_via_email(task, ctx, 'emails/approval_decision'),
            'IN_APP': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'success' if ctx['status'] == 'APPROVED' else 'warning',
                'title': f"Approval {ctx['status']}: {ctx['content_title']}",
                'message': f"Your request has been {ctx['status'].lower()}",
                'link': '/inbox',
            }),
        }
    ),

    'APPROVAL_ESCALATION': NotificationHandler(
        context_builder=build_approval_escalation_context,
        send_validator=validate_approval_escalation_send,
        senders={
            'EMAIL': lambda task, ctx: send_via_email(task, ctx, 'emails/approval_escalation'),
            'IN_APP': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'danger',
                'title': f"ESCALATION: {ctx['content_title']}",
                'message': f"{ctx['days_overdue']} days overdue",
                'link': '/inbox',
            }),
        }
    ),
}


def get_notification_handler(notification_type: str) -> NotificationHandler:
    """Get handler for a notification type."""
    handler = NOTIFICATION_HANDLERS.get(notification_type)
    if not handler:
        raise ValueError(f"Unknown notification type: {notification_type}")
    return handler
