"""Make MaterialLot tenant+lot_number uniqueness partial.

The constraint was enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same lot number.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0022_companies_reman_partial_unique'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='materiallot',
            name='materiallot_tenant_lotnumber_uniq',
        ),
        migrations.AddConstraint(
            model_name='materiallot',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'lot_number'],
                condition=models.Q(is_current_version=True),
                name='materiallot_tenant_lotnumber_uniq',
            ),
        ),
    ]
