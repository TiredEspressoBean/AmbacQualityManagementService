"""Make BOM tenant+part_type+revision+bom_type uniqueness partial.

The constraint was enforced across ALL versions, which blocks
`create_new_version` from cloning the row under the same identifiers.
Restrict enforcement to current versions only so historical versions
can coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0023_materiallot_partial_unique'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='bom',
            name='bom_tenant_parttype_rev_type_uniq',
        ),
        migrations.AddConstraint(
            model_name='bom',
            constraint=models.UniqueConstraint(
                fields=['tenant', 'part_type', 'revision', 'bom_type'],
                condition=models.Q(is_current_version=True),
                name='bom_tenant_parttype_rev_type_uniq',
            ),
        ),
    ]
