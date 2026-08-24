from django.db import migrations


class Migration(migrations.Migration):
    """Rename the PART-grain lot-split fields to disambiguate them from the WO-grain
    WorkOrder.split_reason/split_at, and drop the now-unused held_lockstep_count
    (lock-step no longer holds a WO out of the plan; it carves out split parts instead).
    See Documents/COHORT_VS_WORKORDER_SPLIT_RECONCILIATION.md."""

    dependencies = [
        ('Tracker', '0134_optimizationconfig_default_lockstep_batch_and_more'),
    ]

    operations = [
        migrations.RenameField('parts', 'split_from_cohort', 'split_from_lot'),
        migrations.RenameField('parts', 'split_reason', 'lot_split_reason'),
        migrations.RenameField('parts', 'split_at', 'lot_split_at'),
        migrations.RemoveField('scheduleresult', 'held_lockstep_count'),
    ]
