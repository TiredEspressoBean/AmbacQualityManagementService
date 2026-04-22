"""Make WorkCenter and Shift tenant+code uniqueness partial.

Constraints were enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same identifiers.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0020_documenttype_partial_unique'),
    ]

    operations = [
        # WorkCenter
        migrations.RemoveConstraint(
            model_name='workcenter',
            name='workcenter_tenant_code_uniq',
        ),
        migrations.AddConstraint(
            model_name='workcenter',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'code'],
                condition=models.Q(is_current_version=True),
                name='workcenter_tenant_code_uniq',
            ),
        ),
        # Shift
        migrations.RemoveConstraint(
            model_name='shift',
            name='shift_tenant_code_uniq',
        ),
        migrations.AddConstraint(
            model_name='shift',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'code'],
                condition=models.Q(is_current_version=True),
                name='shift_tenant_code_uniq',
            ),
        ),
    ]
