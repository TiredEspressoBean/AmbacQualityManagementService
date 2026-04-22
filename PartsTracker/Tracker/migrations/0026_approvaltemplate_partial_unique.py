"""Make ApprovalTemplate tenant+template_name and tenant+approval_type
uniqueness constraints partial.

The constraints were enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same name / type.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0025_lifelimitdefinition_partial_unique'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='approvaltemplate',
            name='approvaltemplate_tenant_name_uniq',
        ),
        migrations.AddConstraint(
            model_name='approvaltemplate',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'template_name'],
                condition=models.Q(is_current_version=True),
                name='approvaltemplate_tenant_name_uniq',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='approvaltemplate',
            name='approvaltemplate_tenant_type_uniq',
        ),
        migrations.AddConstraint(
            model_name='approvaltemplate',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'approval_type'],
                condition=models.Q(is_current_version=True),
                name='approvaltemplate_tenant_type_uniq',
            ),
        ),
    ]
