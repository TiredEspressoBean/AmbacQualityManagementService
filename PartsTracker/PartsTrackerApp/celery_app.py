import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PartsTrackerApp.settings')

app = Celery('PartsTracker')
# All Celery configuration — the beat schedule and the time zone included — is in
# settings.py, as CELERY_-prefixed names. A schedule or time zone set here as well
# competes with it (this file once had a second schedule that never ran).
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
