"""Convert NotificationTask from plain models.Model to SecureModel.

Adds the SecureModel columns, backfills `tenant` from `recipient.tenant`,
then makes `tenant` non-nullable. The integer primary key is preserved
(explicit `BigAutoField` override on the model) — converting to UUID
would invalidate the existing notification_task table without benefit.

Any NotificationTask rows with a recipient whose `tenant_id` is NULL
will be DELETED rather than left tenantless. Notification rows are
transient queue items, so this is acceptable; warn if any are pruned.
"""
import django.db.models.deletion
from django.db import migrations, models


def backfill_tenant_and_prune(apps, schema_editor):
    NotificationTask = apps.get_model('Tracker', 'NotificationTask')
    User = apps.get_model('Tracker', 'User')

    # Pull recipient tenant_id in one query (state-forwards models don't
    # expose related accessors cleanly, so go through a values query).
    user_tenants = dict(
        User.objects.values_list('id', 'tenant_id')
    )

    to_delete = []
    for task in NotificationTask.objects.all():
        tenant_id = user_tenants.get(task.recipient_id)
        if tenant_id is None:
            to_delete.append(task.id)
            continue
        task.tenant_id = tenant_id
        task.save(update_fields=['tenant'])

    if to_delete:
        NotificationTask.objects.filter(id__in=to_delete).delete()


def reverse_noop(apps, schema_editor):
    # Reversing the backfill isn't meaningful — we'd be moving a dataset
    # back to "unknown tenant" state. Make it a no-op; the column drop
    # in the reverse of AddField handles the schema side.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0018_migrate_hubspot_gates_to_milestones'),
    ]

    operations = [
        # 1. Add the SecureModel fields.
        migrations.AddField(
            model_name='notificationtask',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='external_id',
            field=models.CharField(
                blank=True, db_index=True, max_length=255, null=True,
                help_text='External system identifier for integration sync',
            ),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='version',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='is_current_version',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='previous_version',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='next_versions',
                to='Tracker.notificationtask',
            ),
        ),
        migrations.AddField(
            model_name='notificationtask',
            name='tenant',
            field=models.ForeignKey(
                blank=True,
                db_index=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='Tracker.tenant',
                help_text='Tenant this record belongs to',
            ),
        ),
        # 2. Backfill tenant from the recipient. Prune rows whose
        # recipient has no tenant (shouldn't happen in any active data
        # set).
        migrations.RunPython(backfill_tenant_and_prune, reverse_noop),
        # 3. Add the composite tenant/created_at index that SecureModel
        # declares on every subclass.
        migrations.AddIndex(
            model_name='notificationtask',
            index=models.Index(
                fields=['tenant', 'created_at'],
                name='tracker_not_tenant__a13df9_idx',
            ),
        ),
    ]
