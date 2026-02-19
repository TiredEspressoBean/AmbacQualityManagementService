# notifications.py - Notification handler system for email/in-app notifications
"""
Notification handler module that provides the actual sending logic for different
notification types. This module is called by the send_notification_task Celery task.

Supported notification types:
- APPROVAL_REQUEST: Notify approvers of new approval request
- APPROVAL_DECISION: Notify requester of approval/rejection decision
- APPROVAL_ESCALATION: Notify escalation recipients of overdue approvals
- CAPA_REMINDER: Remind assignees of upcoming/overdue CAPA tasks
- WEEKLY_REPORT: Send weekly summary reports
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

if TYPE_CHECKING:
    from Tracker.models import NotificationTask

logger = logging.getLogger(__name__)


class NotificationHandler(ABC):
    """Base class for notification handlers."""

    @abstractmethod
    def should_send(self, task: 'NotificationTask') -> bool:
        """
        Check if notification should be sent (validation before sending).
        Return False to cancel the notification.
        """
        pass

    @abstractmethod
    def send(self, task: 'NotificationTask') -> bool:
        """
        Send the notification. Return True on success, False on failure.
        """
        pass

    def get_frontend_url(self) -> str:
        """Get the frontend URL for links in notifications."""
        if settings.DEBUG:
            return "http://localhost:5173"
        return getattr(settings, 'FRONTEND_URL', 'https://yourdomain.com')


class EmailNotificationHandler(NotificationHandler):
    """Base handler for email notifications with common email sending logic."""

    def send_email(self, recipient_email: str, subject: str, html_content: str,
                   plain_content: str = None) -> bool:
        """Send an email with both HTML and plain text versions."""
        if plain_content is None:
            plain_content = strip_tags(html_content)

        try:
            send_mail(
                subject=subject,
                message=plain_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"Email sent to {recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False


class ApprovalRequestHandler(EmailNotificationHandler):
    """Handler for APPROVAL_REQUEST notifications."""

    def should_send(self, task: 'NotificationTask') -> bool:
        """Check if the approval request is still pending."""
        if not task.related_object:
            logger.warning(f"NotificationTask {task.id} has no related object")
            return False

        approval_request = task.related_object
        # Don't send if already decided
        if hasattr(approval_request, 'status') and approval_request.status != 'PENDING':
            task.status = 'cancelled'
            task.save(update_fields=['status'])
            return False
        return True

    def send(self, task: 'NotificationTask') -> bool:
        approval_request = task.related_object
        recipient = task.recipient
        frontend_url = self.get_frontend_url()

        # Build context for email
        content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
        content_obj = approval_request.content_object
        content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

        subject = f"Approval Required: {content_type.title()} - {content_title}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Approval Request</h2>
            <p>Hello {recipient.first_name or recipient.username},</p>
            <p>You have been assigned as an approver for the following item:</p>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Type:</strong> {content_type.title()}</p>
                <p><strong>Item:</strong> {content_title}</p>
                <p><strong>Requested by:</strong> {approval_request.requested_by.get_full_name() or approval_request.requested_by.username}</p>
                <p><strong>Due Date:</strong> {approval_request.due_date.strftime('%B %d, %Y') if approval_request.due_date else 'Not specified'}</p>
            </div>

            <p>Please review and submit your approval decision:</p>
            <p>
                <a href="{frontend_url}/inbox"
                   style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Go to Inbox
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated message from AmbacTracker. Please do not reply to this email.
            </p>
        </body>
        </html>
        """

        return self.send_email(recipient.email, subject, html_content)


class ApprovalDecisionHandler(EmailNotificationHandler):
    """Handler for APPROVAL_DECISION notifications (notify requester of outcome)."""

    def should_send(self, task: 'NotificationTask') -> bool:
        if not task.related_object:
            return False
        return True

    def send(self, task: 'NotificationTask') -> bool:
        approval_request = task.related_object
        recipient = task.recipient
        frontend_url = self.get_frontend_url()

        content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
        content_obj = approval_request.content_object
        content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

        status = approval_request.status
        status_color = '#4CAF50' if status == 'APPROVED' else '#f44336' if status == 'REJECTED' else '#ff9800'

        subject = f"Approval {status}: {content_type.title()} - {content_title}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Approval Decision</h2>
            <p>Hello {recipient.first_name or recipient.username},</p>
            <p>Your approval request has been processed:</p>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Type:</strong> {content_type.title()}</p>
                <p><strong>Item:</strong> {content_title}</p>
                <p><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status}</span></p>
                <p><strong>Completed:</strong> {approval_request.completed_at.strftime('%B %d, %Y at %H:%M') if approval_request.completed_at else 'N/A'}</p>
            </div>

            <p>
                <a href="{frontend_url}/inbox"
                   style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Details
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated message from AmbacTracker. Please do not reply to this email.
            </p>
        </body>
        </html>
        """

        return self.send_email(recipient.email, subject, html_content)


class ApprovalEscalationHandler(EmailNotificationHandler):
    """Handler for APPROVAL_ESCALATION notifications."""

    def should_send(self, task: 'NotificationTask') -> bool:
        if not task.related_object:
            return False
        approval_request = task.related_object
        # Don't escalate if already decided
        if hasattr(approval_request, 'status') and approval_request.status != 'PENDING':
            task.status = 'cancelled'
            task.save(update_fields=['status'])
            return False
        return True

    def send(self, task: 'NotificationTask') -> bool:
        approval_request = task.related_object
        recipient = task.recipient
        frontend_url = self.get_frontend_url()

        content_type = approval_request.content_type.model if approval_request.content_type else 'Item'
        content_obj = approval_request.content_object
        content_title = str(content_obj) if content_obj else f"#{approval_request.object_id}"

        days_overdue = 0
        if approval_request.due_date:
            from django.utils import timezone
            delta = timezone.now().date() - approval_request.due_date
            days_overdue = delta.days

        subject = f"ESCALATION: Overdue Approval - {content_type.title()} - {content_title}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #f44336;">Approval Escalation</h2>
            <p>Hello {recipient.first_name or recipient.username},</p>
            <p>An approval request requires your attention. It is <strong>{days_overdue} day(s) overdue</strong>.</p>

            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p><strong>Type:</strong> {content_type.title()}</p>
                <p><strong>Item:</strong> {content_title}</p>
                <p><strong>Requested by:</strong> {approval_request.requested_by.get_full_name() or approval_request.requested_by.username}</p>
                <p><strong>Due Date:</strong> {approval_request.due_date.strftime('%B %d, %Y') if approval_request.due_date else 'Not specified'}</p>
                <p><strong>Days Overdue:</strong> <span style="color: #f44336; font-weight: bold;">{days_overdue}</span></p>
            </div>

            <p>Please take action to resolve this overdue approval:</p>
            <p>
                <a href="{frontend_url}/inbox"
                   style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Review Now
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated escalation message from AmbacTracker.
            </p>
        </body>
        </html>
        """

        return self.send_email(recipient.email, subject, html_content)


class CapaReminderHandler(EmailNotificationHandler):
    """Handler for CAPA_REMINDER notifications."""

    def should_send(self, task: 'NotificationTask') -> bool:
        if not task.related_object:
            return False

        capa_task = task.related_object
        # Don't remind if task is already completed or closed
        if hasattr(capa_task, 'status') and capa_task.status in ['COMPLETED', 'CLOSED', 'CANCELLED']:
            task.status = 'cancelled'
            task.save(update_fields=['status'])
            return False
        return True

    def send(self, task: 'NotificationTask') -> bool:
        capa_task = task.related_object
        recipient = task.recipient
        frontend_url = self.get_frontend_url()

        # Calculate days until/past due
        days_until_due = None
        overdue_text = ""
        if capa_task.due_date:
            from django.utils import timezone
            from datetime import date
            due = capa_task.due_date if isinstance(capa_task.due_date, date) else capa_task.due_date.date()
            delta = due - timezone.now().date()
            days_until_due = delta.days
            if days_until_due < 0:
                overdue_text = f"<span style='color: #f44336; font-weight: bold;'>{abs(days_until_due)} day(s) overdue</span>"
            elif days_until_due == 0:
                overdue_text = "<span style='color: #ff9800; font-weight: bold;'>Due today</span>"
            else:
                overdue_text = f"Due in {days_until_due} day(s)"

        capa_info = getattr(capa_task, 'capa_info', None) or getattr(capa_task, 'capa', None)
        capa_number = capa_info.capa_number if hasattr(capa_info, 'capa_number') else f"#{capa_task.capa_id}"

        subject = f"CAPA Task Reminder: {capa_task.task_number if hasattr(capa_task, 'task_number') else 'Task'}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>CAPA Task Reminder</h2>
            <p>Hello {recipient.first_name or recipient.username},</p>
            <p>This is a reminder about your assigned CAPA task:</p>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Task:</strong> {capa_task.task_number if hasattr(capa_task, 'task_number') else 'N/A'}</p>
                <p><strong>CAPA:</strong> {capa_number}</p>
                <p><strong>Description:</strong> {capa_task.description[:200] if capa_task.description else 'No description'}...</p>
                <p><strong>Status:</strong> {overdue_text}</p>
            </div>

            <p>
                <a href="{frontend_url}/inbox"
                   style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Task
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated reminder from AmbacTracker.
            </p>
        </body>
        </html>
        """

        return self.send_email(recipient.email, subject, html_content)


class WeeklyReportHandler(EmailNotificationHandler):
    """Handler for WEEKLY_REPORT notifications."""

    def should_send(self, task: 'NotificationTask') -> bool:
        # Weekly reports always send on schedule
        return True

    def send(self, task: 'NotificationTask') -> bool:
        recipient = task.recipient
        frontend_url = self.get_frontend_url()

        # This would typically aggregate data for the report
        # For now, send a simple placeholder
        subject = "Weekly Order Report - AmbacTracker"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Weekly Order Report</h2>
            <p>Hello {recipient.first_name or recipient.username},</p>
            <p>Here is your weekly summary from AmbacTracker.</p>

            <p>
                <a href="{frontend_url}/dashboard"
                   style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Dashboard
                </a>
            </p>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated weekly report from AmbacTracker.
            </p>
        </body>
        </html>
        """

        return self.send_email(recipient.email, subject, html_content)


# Handler registry
_HANDLERS = {
    'APPROVAL_REQUEST': ApprovalRequestHandler,
    'APPROVAL_DECISION': ApprovalDecisionHandler,
    'APPROVAL_ESCALATION': ApprovalEscalationHandler,
    'CAPA_REMINDER': CapaReminderHandler,
    'WEEKLY_REPORT': WeeklyReportHandler,
}


def get_notification_handler(notification_type: str) -> NotificationHandler:
    """
    Factory function to get the appropriate handler for a notification type.

    Args:
        notification_type: One of APPROVAL_REQUEST, APPROVAL_DECISION, etc.

    Returns:
        NotificationHandler instance

    Raises:
        ValueError: If notification_type is unknown
    """
    handler_class = _HANDLERS.get(notification_type)
    if handler_class is None:
        raise ValueError(f"Unknown notification type: {notification_type}")
    return handler_class()
