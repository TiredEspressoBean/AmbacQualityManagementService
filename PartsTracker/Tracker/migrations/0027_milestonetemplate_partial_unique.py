"""Make MilestoneTemplate tenant+name uniqueness partial.

The constraint was enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same name.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0026_approvaltemplate_partial_unique'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='milestonetemplate',
            name='milestone_template_tenant_name_uniq',
        ),
        migrations.AddConstraint(
            model_name='milestonetemplate',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'name'],
                condition=models.Q(is_current_version=True),
                name='milestone_template_tenant_name_uniq',
            ),
        ),
    ]
