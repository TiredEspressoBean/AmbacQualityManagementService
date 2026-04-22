"""Make DocumentType tenant+name / tenant+code uniqueness partial.

Constraints were enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same identifiers.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0019_notificationtask_securemodel'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='documenttype',
            name='documenttype_tenant_name_uniq',
        ),
        migrations.RemoveConstraint(
            model_name='documenttype',
            name='documenttype_tenant_code_uniq',
        ),
        migrations.AddConstraint(
            model_name='documenttype',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'name'],
                condition=models.Q(is_current_version=True),
                name='documenttype_tenant_name_uniq',
            ),
        ),
        migrations.AddConstraint(
            model_name='documenttype',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'code'],
                condition=models.Q(is_current_version=True),
                name='documenttype_tenant_code_uniq',
            ),
        ),
    ]
