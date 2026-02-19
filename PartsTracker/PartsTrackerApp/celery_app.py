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
