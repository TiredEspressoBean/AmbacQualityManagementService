from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

from PartsTrackerApp import settings


def send_weekly_order_report(user, order_data):
    subject = 'Your Weekly Order Status Report'
    html_message = render_to_string('tracker/email/weekly_report.html', {
        'user': user,
        'orders': order_data,
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        None,  # uses DEFAULT_FROM_EMAIL
        [user.email],
        html_message=html_message,
    )


def get_sampling_notification_recipients(sampling_trigger):
    """Get users who should receive sampling notifications for this specific step"""
    # Get step-specific notification users
    recipients = sampling_trigger.step.notification_users.filter(
        is_active=True,
        email__isnull=False
    ).exclude(email='')

    return list(recipients)


def send_sampling_trigger_email(sampling_trigger):
    """Send email notification when sampling trigger is created"""
    try:
        recipients = get_sampling_notification_recipients(sampling_trigger)

        if not recipients:
            return

        recipient_emails = [user.email for user in recipients]

        # Email context
        context = {
            'trigger': sampling_trigger,
            'work_order': sampling_trigger.work_order,
            'step': sampling_trigger.step,
            'quality_report': sampling_trigger.triggered_by,
            'fail_count': sampling_trigger.fail_count,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }

        # Subject line
        subject = f"Quality Issue - Sampling Triggered - WO: {sampling_trigger.work_order.ERP_id} - {sampling_trigger.step.name}"

        # Email body
        message = render_to_string('emails/sampling_trigger_notification.txt', context)

        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_emails,
            fail_silently=False,
        )

        # Update notification tracking
        sampling_trigger.notification_sent = True
        sampling_trigger.notification_sent_at = timezone.now()
        sampling_trigger.save()
        sampling_trigger.notified_users.set(recipients)


    except Exception as e:
        return


def resend_sampling_notification(sampling_trigger_id):
    """Manually resend notification for a specific trigger"""
    try:
        from .models import SamplingTriggerState
        trigger = SamplingTriggerState.objects.get(id=sampling_trigger_id)
        send_sampling_trigger_email(trigger)
        return True
    except Exception as e:
        return False