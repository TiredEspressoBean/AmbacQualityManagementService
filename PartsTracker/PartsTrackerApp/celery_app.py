import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')

app = Celery('PartsTracker')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# Celery Beat Schedule - periodic tasks
app.conf.beat_schedule = {
    # Dispatch pending notifications every 5 minutes
    'dispatch-pending-notifications': {
        'task': 'Tracker.tasks.dispatch_pending_notifications',
        'schedule': crontab(minute='*/5'),
    },
    # Scan scheduled notifications for due fires every 5 minutes.
    # Each due schedule gets a `fire_one_schedule` task queued by the tick.
    'tick-notification-schedules': {
        'task': 'Tracker.tasks.tick_notification_schedules',
        'schedule': crontab(minute='*/5'),
    },
    # Scan escalation instances whose timer has elapsed. Every minute —
    # escalation timers are measured in hours, but a tight tick keeps the
    # delay between "step due" and "step fires" bounded.
    'tick-escalations': {
        'task': 'Tracker.tasks.tick_escalations',
        'schedule': crontab(minute='*'),
    },
    # Check for overdue approvals every hour
    'check-overdue-approvals': {
        'task': 'Tracker.tasks.check_overdue_approvals',
        'schedule': crontab(minute=0),  # Every hour on the hour
    },
    # Escalate overdue approvals every hour (offset by 30 min)
    'escalate-approvals': {
        'task': 'Tracker.tasks.escalate_approvals',
        'schedule': crontab(minute=30),  # Every hour at :30
    },
    # Check overdue CAPAs daily at 8 AM
    'check-overdue-capas': {
        'task': 'Tracker.tasks.check_overdue_capas',
        'schedule': crontab(hour=8, minute=0),
    },
}

app.conf.timezone = 'UTC'
