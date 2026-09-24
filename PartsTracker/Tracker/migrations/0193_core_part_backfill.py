"""Give every core its part, and move the generic rows that pointed at the core onto it.

A core is a part; "core" is the role it plays (Documents/CORE_AS_PART_DESIGN.md). This
mints the part for each existing core and re-points the four generic relations —
step execution, scheduled task, transition log, assembly parent — from the core to that
part, so the next migration can drop them.

Historical models carry no custom managers, so every query uses `_default_manager` and
sees all tenants and archived rows, which is what a backfill wants.
"""
from django.db import migrations

# A frozen copy of services/reman/core_part._BY_STAGE as of this migration. Migrations
# must not import app code that can change underneath them.
_BY_STAGE = {
    'IN_DISASSEMBLY': 'IN_PROGRESS',
    'DISASSEMBLED': 'ON_HOLD',
    'AWAITING_AUTHORISATION': 'ON_HOLD',
    'IN_REBUILD': 'IN_PROGRESS',
    'REBUILT': 'COMPLETED',
    'DECLINED': 'AWAITING_PICKUP',
    'RETURNED': 'SHIPPED',
    'RETURNED_UNREPAIRED': 'SHIPPED',
    'HARVESTED': 'DISMANTLED',
    'SCRAPPED': 'SCRAPPED',
}


def _part_status(stage, on_work_order):
    if stage == 'RECEIVED':
        return 'PENDING' if on_work_order else 'CORE_BANKED'
    return _BY_STAGE.get(stage, 'PENDING')


def forwards(apps, schema_editor):
    Core = apps.get_model('Tracker', 'Core')
    Parts = apps.get_model('Tracker', 'Parts')
    StepExecution = apps.get_model('Tracker', 'StepExecution')
    ScheduledTask = apps.get_model('Tracker', 'ScheduledTask')
    StepTransitionLog = apps.get_model('Tracker', 'StepTransitionLog')
    AssemblyUsage = apps.get_model('Tracker', 'AssemblyUsage')

    for core in Core._default_manager.filter(part__isnull=True).iterator():
        part = Parts._default_manager.create(
            tenant_id=core.tenant_id,
            ERP_id=core.core_number,
            part_type_id=core.core_type_id,
            work_order_id=core.work_order_id,
            step_id=core.step_id,
            part_status=_part_status(core.status, core.work_order_id is not None),
            archived=core.archived,
        )
        Core._default_manager.filter(pk=core.pk).update(part=part)

        StepExecution._default_manager.filter(core_id=core.pk).update(part=part, core=None)
        ScheduledTask._default_manager.filter(core_id=core.pk).update(part=part, core=None)
        StepTransitionLog._default_manager.filter(core_id=core.pk).update(part=part, core=None)
        AssemblyUsage._default_manager.filter(assembly_core_id=core.pk).update(
            assembly=part, assembly_core=None)


def backwards(apps, schema_editor):
    """Unlink only. The parts stay: once other rows point at them, deleting them is not
    a safe inverse, and this runs on dev data where a reseed is the real undo."""
    Core = apps.get_model('Tracker', 'Core')
    Core._default_manager.update(part=None)


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0192_core_part_link'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
