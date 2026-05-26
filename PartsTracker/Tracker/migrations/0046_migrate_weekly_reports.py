"""
Migrate legacy WEEKLY_REPORT NotificationTask rows to personal
NotificationSchedule rows.

Existing customer-account weekly subscriptions (created by the legacy
`enqueue_weekly_report` hook in `viewsets/core.py:975` — now removed)
need to keep firing under the new system. Each PENDING WEEKLY_REPORT
NotificationTask becomes a personal NotificationSchedule owned by the
same user, with the same cadence and time.

Orphan rows (no recipient, or recipient with no tenant) are skipped and
logged. Admins can manually create schedules for those users post-migration.

Migrated NotificationTask rows are archived (soft-deleted) but not
hard-deleted — preserves the audit trail.
"""
from __future__ import annotations

from datetime import time

from django.db import migrations


def migrate_weekly_reports(apps, schema_editor):
    NotificationTask = apps.get_model('Tracker', 'NotificationTask')
    NotificationSchedule = apps.get_model('Tracker', 'NotificationSchedule')

    rows = NotificationTask._default_manager.filter(
        notification_type='WEEKLY_REPORT',
        archived=False,
        status='PENDING',
    ).select_related('recipient', 'tenant')

    converted = 0
    skipped = 0
    for task in rows:
        if not task.recipient_id or not task.tenant_id:
            skipped += 1
            continue

        # Avoid duplicate creation if a previous failed migration run left
        # a partial schedule in place — match on (tenant, owner_user, provider).
        existing = NotificationSchedule._default_manager.filter(
            tenant=task.tenant,
            owner_user=task.recipient,
            provider_kind='customer_active_orders',
            scope_kind='personal',
            archived=False,
        ).exists()

        if not existing:
            NotificationSchedule._default_manager.create(
                tenant=task.tenant,
                owner_user=task.recipient,
                name='Weekly orders summary',
                description=(
                    'Migrated from the legacy weekly_report subscription. '
                    'Manage cadence via your profile notifications page.'
                ),
                enabled=True,
                scope_kind='personal',
                provider_kind='customer_active_orders',
                provider_params={},
                cadence='weekly',
                day_of_week=task.day_of_week if task.day_of_week is not None else 4,
                day_of_month=None,
                time_of_day=task.time or time(15, 0),
                timezone='UTC',
                channels=['email'],
            )
            converted += 1

        # Soft-archive the legacy row — keeps the audit trail, prevents
        # the legacy dispatcher from re-firing it during the transition
        # window (until R7 removes the WEEKLY_REPORT path entirely).
        task.archived = True
        task.save(update_fields=['archived'])

    if hasattr(schema_editor.connection, '_test'):
        # Avoid logging during tests.
        return
    import logging
    logging.getLogger(__name__).info(
        'migrate_weekly_reports: converted=%d skipped=%d', converted, skipped,
    )


def reverse_noop(apps, schema_editor):
    """Reverse migration is intentionally a no-op.

    Re-creating WEEKLY_REPORT NotificationTasks from NotificationSchedules
    is lossy and unsafe (the schedules may have been edited by users since
    migration). If you need to roll back, restore from a DB backup.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0045_notificationschedule_personal_scope'),
    ]

    operations = [
        migrations.RunPython(migrate_weekly_reports, reverse_noop),
    ]
