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
from django.db.models import Avg, Max

logger = logging.getLogger(__name__)


# ============================================================================
# CONTEXT BUILDERS - Build fresh context from related objects
# ============================================================================

def build_weekly_report_context(task) -> Optional[Dict[str, Any]]:
    """Build context for weekly order report notifications."""
    from Tracker.models import Orders, OrdersStatus, Steps

    customer = task.recipient

    # Get customer's active orders
    active_statuses = [
        OrdersStatus.RFI,
        OrdersStatus.PENDING,
        OrdersStatus.IN_PROGRESS,
        OrdersStatus.ON_HOLD
    ]

    active_orders = Orders.objects.filter(
        customer=customer,
        archived=False,
        order_status__in=active_statuses
    ).select_related('company').prefetch_related('parts__step')

    if not active_orders.exists():
        # No active orders, skip sending
        return None

    # Prepare order summaries
    order_summaries = []
    for order in active_orders:
        parts_qs = order.parts.filter(archived=False).select_related('step')
        total_parts = parts_qs.count()
        completed_parts = parts_qs.filter(part_status='COMPLETED').count()

        # Average current step index
        avg_step = parts_qs.aggregate(a=Avg('step__order'))['a'] or 0

        # All processes for the parts in this order
        process_ids = parts_qs.values_list('step__process_id', flat=True).distinct()

        # True max step across those processes
        max_step = (
            Steps.objects.filter(process_id__in=process_ids)
            .aggregate(m=Max('order'))['m']
        ) or 0

        progress = int(round(100 * (avg_step / max_step))) if max_step else 0

        # Get current stage
        current_stage = "Not Started"
        if order.parts.exists():
            first_part = order.parts.first()
            if first_part and first_part.step:
                current_stage = first_part.step.name

        order_summaries.append({
            'name': order.name,
            'status': order.get_order_status_display(),
            'progress': round(progress),
            'current_stage': current_stage,
            'completion_date': order.estimated_completion,
            'original_completion': order.original_completion_date,
            'total_parts': total_parts,
            'completed_parts': completed_parts,
        })

    return {
        'customer': customer,
        'customer_name': customer.get_full_name() or customer.email,
        'orders': order_summaries,
        'week_ending': timezone.now().date(),
        'total_orders': len(order_summaries),
    }


def build_capa_context(task) -> Optional[Dict[str, Any]]:
    """Build context for CAPA reminder notifications."""
    capa = task.related_object
    if not capa:
        return None

    days_until = (capa.due_date - timezone.now()).days

    return {
        'disposition_number': capa.disposition_number,
        'due_date': capa.due_date,
        'days_until_due': days_until,
        'is_overdue': days_until < 0,
        'current_state': capa.current_state,
        'attempt_count': task.attempt_count,
        'capa_id': capa.id,
    }


# ============================================================================
# SEND VALIDATORS - Check if notification should send
# ============================================================================

def validate_weekly_report_send(task) -> bool:
    """Check if weekly report should send."""
    # Check if user is active
    if not task.recipient.is_active:
        task.status = 'cancelled'
        task.save()
        return False

    return True


def validate_capa_send(task) -> bool:
    """Check if CAPA notification should send."""
    capa = task.related_object

    if not capa:
        # Related object deleted
        task.status = 'cancelled'
        task.save()
        return False

    if capa.current_state == 'CLOSED':
        # CAPA was closed
        task.status = 'cancelled'
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
        template_base: Base template path (e.g., 'emails/weekly_report')

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
    Send in-app push notification.

    For now, this is a placeholder. In the future, this would create
    an InAppNotification record that the frontend polls/subscribes to.

    Args:
        task: NotificationTask instance
        context: Template context dict
        notification_data: In-app notification specific data (title, message, link, etc.)

    Returns:
        True if sent successfully, False otherwise
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
    'WEEKLY_REPORT': NotificationHandler(
        context_builder=build_weekly_report_context,
        send_validator=validate_weekly_report_send,
        senders={
            'email': lambda task, ctx: send_via_email(task, ctx, 'emails/weekly_report'),
            'in_app': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'info',
                'title': 'Weekly Order Report Available',
                'message': f"Your report for week ending {ctx['week_ending']} is ready",
                'link': '/orders/reports/weekly/',
            }),
        }
    ),

    'CAPA_REMINDER': NotificationHandler(
        context_builder=build_capa_context,
        send_validator=validate_capa_send,
        senders={
            'email': lambda task, ctx: send_via_email(task, ctx, 'emails/capa_reminder'),
            'in_app': lambda task, ctx: send_via_in_app(task, ctx, {
                'type': 'warning' if ctx.get('is_overdue') else 'info',
                'title': f"CAPA Action Required: {ctx['disposition_number']}",
                'message': f"Due in {ctx['days_until_due']} days" if not ctx['is_overdue'] else f"OVERDUE by {abs(ctx['days_until_due'])} days",
                'link': f"/qa/quarantine/{ctx['capa_id']}/",
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
