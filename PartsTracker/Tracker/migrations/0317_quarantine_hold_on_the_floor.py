"""The quarantine hold joins the floor (user ruling 2026-11-17): a part quarantined after
its visit started doesn't move on from the step until its disposition is decided —
deciding one takes the part off QUARANTINED, and MRB moves a decided part itself, so
nothing waits on the gate for good.

Every existing step without it is given it (additive; a step that already has it is
left as it is). Backward does nothing: some steps carried the gate before this, and
there is no telling them apart from the ones given it here.
"""
from django.db import migrations

GATE = 'quarantine_hold'


def forwards(apps, schema_editor):
    StepRequirement = apps.get_model('Tracker', 'StepRequirement')
    Steps = apps.get_model('Tracker', 'Steps')
    rows = StepRequirement._base_manager.filter(archived=False)
    have = set(rows.filter(gate=GATE).values_list('step_id', flat=True))
    last = {}
    for step_id, order in rows.values_list('step_id', 'order'):
        last[step_id] = max(order, last.get(step_id, 0))
    tenants = dict(Steps._base_manager.values_list('id', 'tenant_id'))
    batch = [StepRequirement(tenant_id=tenant_id, step_id=step_id, gate=GATE,
                             order=last.get(step_id, 0) + 1)
             for step_id, tenant_id in tenants.items() if step_id not in have]
    StepRequirement._base_manager.bulk_create(batch, batch_size=2000)


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0316_cyclecount_erp_keyed_help'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
