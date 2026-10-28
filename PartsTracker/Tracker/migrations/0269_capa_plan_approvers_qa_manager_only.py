"""Only a QA Manager approves a Major or Critical CAPA's plan (user decision
2026-10-28, B3). The starter CAPA_CRITICAL / CAPA_MAJOR templates also listed
Production Manager, under an ANY flow, so a Production Manager could approve alone.

Existing tenants' current templates get a new version without that group, through the
template versioning service (ApprovalTemplate is versioned: the old version keeps its
groups as history). Requests already open keep the approvers they were created with.

The live service is reached only when the historical model finds a template to fix,
so a fresh database (and the test database) never touches live model code that may be
ahead of this migration's schema.
"""
from django.db import migrations

TYPES = ('CAPA_CRITICAL', 'CAPA_MAJOR')
GROUP = 'Production Manager'


def drop_production_manager(apps, schema_editor):
    Historical = apps.get_model('Tracker', 'ApprovalTemplate')
    ids = list(Historical._base_manager.filter(
        approval_type__in=TYPES, is_current_version=True, archived=False,
        default_groups__name=GROUP).values_list('id', flat=True).distinct())
    if not ids:
        return
    from Tracker.models import ApprovalTemplate
    from Tracker.services.core.approval_template import create_new_approval_template_version
    from Tracker.utils.tenant_context import tenant_context
    # tenant-safe: a data fix across every tenant's starter templates, by id; each
    # new version is written inside that template's own tenant context.
    for template in ApprovalTemplate.all_tenants.filter(id__in=ids):
        keep = [g for g in template.default_groups.all() if g.name != GROUP]
        with tenant_context(template.tenant_id):
            create_new_approval_template_version(
                template, default_groups=keep,
                change_description="Only a QA Manager approves a Major or Critical CAPA's plan "
                                   "(Production Manager removed).")


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0268_fpi_scope_per_operator_removed'),
    ]

    operations = [
        migrations.RunPython(drop_production_manager, migrations.RunPython.noop),
    ]
