"""
Cancel NotificationTask rows that can never send but were left PENDING.

Migration 0046 archived the legacy WEEKLY_REPORT rows without changing their status,
and `dispatch_pending_notifications` didn't skip archived rows, so every five minutes
the worker re-queued them and each failed on the retired type ("Unknown notification
type: WEEKLY_REPORT"), forever. The dispatcher now skips archived rows and a send for
a retired type cancels its row; this clears the backlog already sitting in the queue.

Cancelled, not deleted: the rows stay for the audit trail.
"""
from django.db import migrations
from django.db.models import Q


def cancel_retired(apps, schema_editor):
    NotificationTask = apps.get_model('Tracker', 'NotificationTask')
    NotificationTask._default_manager.filter(status='PENDING').filter(
        Q(archived=True) | Q(notification_type='WEEKLY_REPORT')
    ).update(status='CANCELLED')


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0264_repair_code_required_and_declined'),
    ]

    operations = [
        migrations.RunPython(cancel_retired, migrations.RunPython.noop),
    ]
