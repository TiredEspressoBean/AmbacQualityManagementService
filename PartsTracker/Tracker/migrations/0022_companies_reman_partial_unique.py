"""Route Companies and DisassemblyBOMLine through create_new_version.

Companies has no pre-existing explicit unique constraints (natural
uniqueness is via name only, no UniqueConstraint in Meta), so no
RemoveConstraint step is needed for it.

DisassemblyBOMLine previously used `unique_together = ['core_type',
'component_type']`, which blocked create_new_version from cloning the
row under the same FK pair. Convert to a partial UniqueConstraint
restricted to is_current_version=True so historical versions can
coexist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0021_mes_standard_partial_unique'),
    ]

    operations = [
        # DisassemblyBOMLine: drop legacy unique_together, add partial constraint
        migrations.AlterUniqueTogether(
            name='disassemblybomline',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='disassemblybomline',
            constraint=models.UniqueConstraint(
                fields=['core_type', 'component_type'],
                condition=models.Q(is_current_version=True),
                name='disassemblybomline_coretype_component_uniq',
            ),
        ),
    ]
