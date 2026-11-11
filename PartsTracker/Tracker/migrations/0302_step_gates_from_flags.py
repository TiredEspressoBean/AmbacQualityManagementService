"""Move every step's gate flags into typed StepRequirement rows (user decisions
2026-11-11). Each step gets the floor — the gates that applied to every step whatever
its flags said — plus one row per flag that was on, so its behaviour is exactly what it
was. Covered by Tracker/tests/test_step_gates_migration.py.

The mapping lives here, not in app code: a migration's behaviour must not change when
the services it would have imported do.
"""
from django.db import migrations

ORDER = (
    'work_order_not_workable', 'deviation_expired', 'part_quarantined',
    'core_awaiting_authorisation', 'training_not_authorized', 'revisit_rule',
    'substeps_incomplete', 'qualified_operator', 'life_limit', 'quarantine_hold',
    'qa_signoff', 'first_piece', 'measurement_out_of_spec',
)
FLOOR = (
    'work_order_not_workable', 'deviation_expired', 'part_quarantined',
    'core_awaiting_authorisation', 'training_not_authorized', 'substeps_incomplete',
    'qualified_operator', 'life_limit',
)


def rows_for_flags(*, requires_first_piece_inspection, fpi_scope, requires_qa_signoff,
                   qa_signoff_assurance, block_on_quarantine, block_on_measurement_failure,
                   revisit_assignment, revisit_role_id):
    """The rows that reproduce a step's old flags: the floor, plus a row per flag on.
    ANY (the default revisit rule) constrained nothing, so it is no row."""
    rows = [{'gate': g} for g in FLOOR]
    rule = (revisit_assignment or 'ANY').upper()
    if rule in ('SAME', 'DIFFERENT', 'ROLE'):
        rows.append({'gate': 'revisit_rule', 'revisit_assignment': rule,
                     'revisit_role_id': revisit_role_id if rule == 'ROLE' else None})
    if block_on_quarantine:
        rows.append({'gate': 'quarantine_hold'})
    if requires_qa_signoff:
        rows.append({'gate': 'qa_signoff',
                     'qa_assurance': qa_signoff_assurance if qa_signoff_assurance in ('NONE', 'PASSWORD') else 'NONE'})
    if requires_first_piece_inspection:
        rows.append({'gate': 'first_piece',
                     'fpi_scope': fpi_scope if fpi_scope in ('PER_WORKORDER', 'PER_SHIFT', 'PER_EQUIPMENT')
                     else 'PER_WORKORDER'})
    if block_on_measurement_failure:
        rows.append({'gate': 'measurement_out_of_spec'})
    rank = {g: i for i, g in enumerate(ORDER)}
    rows.sort(key=lambda r: rank[r['gate']])
    for i, r in enumerate(rows):
        r['order'] = i
    return rows


def forwards(apps, schema_editor):
    Steps = apps.get_model('Tracker', 'Steps')
    StepRequirement = apps.get_model('Tracker', 'StepRequirement')
    batch = []
    for step in Steps._base_manager.all().iterator():
        for row in rows_for_flags(
                requires_first_piece_inspection=step.requires_first_piece_inspection,
                fpi_scope=step.fpi_scope,
                requires_qa_signoff=step.requires_qa_signoff,
                qa_signoff_assurance=step.qa_signoff_assurance,
                block_on_quarantine=step.block_on_quarantine,
                block_on_measurement_failure=step.block_on_measurement_failure,
                revisit_assignment=step.revisit_assignment,
                revisit_role_id=step.revisit_role_id):
            batch.append(StepRequirement(tenant_id=step.tenant_id, step_id=step.id, **row))
        if len(batch) >= 2000:
            StepRequirement._base_manager.bulk_create(batch)
            batch = []
    if batch:
        StepRequirement._base_manager.bulk_create(batch)


def backwards(apps, schema_editor):
    apps.get_model("Tracker", "StepRequirement")._base_manager.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0301_step_gates_typed'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
