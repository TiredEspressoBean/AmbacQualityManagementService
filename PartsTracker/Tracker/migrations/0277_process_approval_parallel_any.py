"""The starter Process Approval stays "either group's first approval" (user decision
2026-10-29).

It was SEQUENTIAL / ALL_REQUIRED with two groups (QA Manager, Production Manager) and no
named people. Since sequential approvals became real stages (4ae7456d), that would read
as one stage needing BOTH groups. Each tenant's current Process Approval template that
is still sequential with no stages gets a new version set to PARALLEL / ANY, through
the template versioning service (the old version keeps its settings as history). Its
open requests move to the same rules, so none is suddenly waiting on both groups.

As in 0269, live model code is reached only when the historical model finds something
to fix, so a fresh database never runs it.
"""
from django.db import migrations


def to_parallel_any(apps, schema_editor):
    Template = apps.get_model('Tracker', 'ApprovalTemplate')
    Request = apps.get_model('Tracker', 'ApprovalRequest')
    ids = list(Template._base_manager.filter(
        approval_type='PROCESS_APPROVAL', is_current_version=True, archived=False,
        approval_sequence='SEQUENTIAL', approval_stages=[]).values_list('id', flat=True))
    # Open requests: either group's first approval closes them again.
    Request._base_manager.filter(approval_type='PROCESS_APPROVAL', status='PENDING',
                                 sequence_type='SEQUENTIAL').update(
        sequence_type='PARALLEL', flow_type='ANY')
    if not ids:
        return
    from Tracker.models import ApprovalTemplate
    from Tracker.services.core.approval_template import create_new_approval_template_version
    from Tracker.utils.tenant_context import tenant_context
    # tenant-safe: a data fix across every tenant's starter template, by id; each new
    # version is written inside that template's own tenant context.
    for template in ApprovalTemplate.all_tenants.filter(id__in=ids):
        with tenant_context(template.tenant_id):
            create_new_approval_template_version(
                template, approval_sequence='PARALLEL', approval_flow_type='ANY',
                change_description="Either group's first approval decides it (parallel, any) — "
                                   "kept as before sequential approvals became stages.")


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0276_widen_measurement_spec_decimals'),
    ]

    operations = [
        migrations.RunPython(to_parallel_any, migrations.RunPython.noop),
    ]
