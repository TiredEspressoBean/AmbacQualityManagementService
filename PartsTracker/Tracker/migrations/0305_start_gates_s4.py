"""Two new floor gates — a part on hold, a machine down (gate redesign S4, user
decisions 2026-11-11) — and the life limit moves to the start.

Every existing step is given the two new gates, so existing routings refuse a held
part or a down machine as new ones do. (No step had been composed in the gates editor
yet, so every step still carried the floor these join.)

Backward removes every row of the two gates, including any a later step was given
with the floor; the deployment only migrates forward.
"""
from django.db import migrations, models

NEW_FLOOR = ('part_on_hold', 'equipment_down')


def forwards(apps, schema_editor):
    StepRequirement = apps.get_model('Tracker', 'StepRequirement')
    Steps = apps.get_model('Tracker', 'Steps')
    rows = StepRequirement._base_manager.filter(archived=False)
    have = set(rows.filter(gate__in=NEW_FLOOR).values_list('step_id', 'gate'))
    last = {}
    for step_id, order in rows.values_list('step_id', 'order'):
        last[step_id] = max(order, last.get(step_id, 0))
    tenants = dict(Steps._base_manager.values_list('id', 'tenant_id'))
    batch = []
    for step_id in tenants:
        for i, gate in enumerate(NEW_FLOOR, start=1):
            if (step_id, gate) not in have:
                batch.append(StepRequirement(tenant_id=tenants[step_id], step_id=step_id,
                                             gate=gate, order=last.get(step_id, 0) + i))
    StepRequirement._base_manager.bulk_create(batch, batch_size=2000)


def backwards(apps, schema_editor):
    apps.get_model('Tracker', 'StepRequirement')._base_manager.filter(gate__in=NEW_FLOOR).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0304_first_piece_set'),
    ]

    operations = [
        migrations.AlterField(
            model_name='steprequirement',
            name='gate',
            field=models.CharField(choices=[('work_order_not_workable', 'Work order workable'), ('deviation_expired', 'Deviation in date'), ('part_quarantined', 'Part not quarantined'), ('core_awaiting_authorisation', 'Customer authorisation'), ('part_on_hold', 'Part not on hold'), ('equipment_down', 'Machine in service'), ('life_limit', 'Life limit'), ('training_not_authorized', 'Operator trained'), ('revisit_rule', 'Repeat visits'), ('substeps_incomplete', 'Work instruction done'), ('qualified_operator', 'Qualified operator on record'), ('quarantine_hold', 'Quarantine hold'), ('qa_signoff', 'QA sign-off'), ('first_piece', 'First piece'), ('measurement_out_of_spec', 'Readings in spec')], max_length=40),
        ),
        migrations.RunPython(forwards, backwards),
    ]
