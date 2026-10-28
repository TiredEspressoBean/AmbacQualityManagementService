"""FPI scopes are real gates (user decision 2026-10-28, B1/B2).

Per Operator is removed: it never keyed a record, so a step set to it behaved as Per
Work Order — which is what it becomes. FPIStatus gains SUPERSEDED, a waiver corrected
by a new first piece.
"""
from django.db import migrations, models


def per_operator_to_per_workorder(apps, schema_editor):
    Steps = apps.get_model('Tracker', 'Steps')
    Steps._base_manager.filter(fpi_scope='PER_OPERATOR').update(fpi_scope='PER_WORKORDER')


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0267_repair_orphaned_notification_config'),
    ]

    operations = [
        migrations.RunPython(per_operator_to_per_workorder, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='fpirecord',
            name='status',
            field=models.CharField(choices=[('NOT_REQUIRED', 'Not Required'), ('PENDING', 'Pending'), ('PASSED', 'Passed'), ('FAILED', 'Failed'), ('WAIVED', 'Waived'), ('VOIDED', 'Voided'), ('SUPERSEDED', 'Superseded')], default='PENDING', help_text='Current status of the FPI', max_length=20),
        ),
        migrations.AlterField(
            model_name='steps',
            name='fpi_scope',
            field=models.CharField(choices=[('PER_WORKORDER', 'Per Work Order'), ('PER_SHIFT', 'Per Shift'), ('PER_EQUIPMENT', 'Per Equipment')], default='PER_WORKORDER', help_text='Scope at which FPI applies', max_length=20),
        ),
    ]
