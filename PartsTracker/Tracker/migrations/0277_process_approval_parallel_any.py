"""The starter Process Approval stays "either group's first approval" (user decision
2026-10-29).

It was SEQUENTIAL / ALL_REQUIRED with two groups (QA Manager, Production Manager) and no
named people. Since sequential approvals became real stages (4ae7456d), that would read
as one stage needing BOTH groups. Each tenant's current Process Approval template still
in that shape becomes PARALLEL / ANY, and its open requests move to the same rules, so
none is suddenly waiting on both groups.

Historical models only. The first version of this migration called the live template
versioning service, which broke once a later migration (0278) added a field the live
model expects: a database migrating through here would run code ahead of its schema.
Production ran that first version (deployed 15bd23ad), which made a new template
version; this body doesn't re-run there. A database that hasn't run it gets the same
settings written in place — on a fresh one there are no templates yet, so it is a no-op.
"""
from django.db import migrations


def to_parallel_any(apps, schema_editor):
    Template = apps.get_model('Tracker', 'ApprovalTemplate')
    Request = apps.get_model('Tracker', 'ApprovalRequest')
    Template._base_manager.filter(
        approval_type='PROCESS_APPROVAL', is_current_version=True, archived=False,
        approval_sequence='SEQUENTIAL', approval_stages=[],
    ).update(approval_sequence='PARALLEL', approval_flow_type='ANY')
    # Open requests: either group's first approval closes them again.
    Request._base_manager.filter(approval_type='PROCESS_APPROVAL', status='PENDING',
                                 sequence_type='SEQUENTIAL').update(
        sequence_type='PARALLEL', flow_type='ANY')


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0276_widen_measurement_spec_decimals'),
    ]

    operations = [
        migrations.RunPython(to_parallel_any, migrations.RunPython.noop),
    ]
