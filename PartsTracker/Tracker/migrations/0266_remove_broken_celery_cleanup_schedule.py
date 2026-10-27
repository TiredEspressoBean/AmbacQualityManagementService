"""
Remove the beat entry for a task that doesn't exist.

`cleanup-celery-results` named `django_celery_results.tasks.cleanup_expired_results`,
which django_celery_results doesn't provide, so every hour the worker logged
"Received unregistered task" and dropped it. Celery's own `celery.backend_cleanup`
already prunes results (CELERY_RESULT_EXPIRES). The entry is gone from
CELERY_BEAT_SCHEDULE, but the DatabaseScheduler never deletes rows for removed
entries, so the stored one is removed here.
"""
from django.db import migrations


def remove_entry(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    PeriodicTask.objects.filter(name='cleanup-celery-results').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0265_cancel_retired_pending_notifications'),
        ('django_celery_beat', '0019_alter_periodictasks_options'),
    ]

    operations = [
        migrations.RunPython(remove_entry, migrations.RunPython.noop),
    ]
