"""Fix the migration 0065 bug where `default=uuid.uuid4` on AddField
applied a single value to every existing row, collapsing all Step
identities to one shared UUID.

Re-assign identity_id per chain: each root Step gets a fresh UUID, and
the chain walks forward copying the root's UUID to its descendants.
"""
import uuid
from django.db import migrations


def reassign_identity_per_chain(apps, schema_editor):
    Steps = apps.get_model('Tracker', 'Steps')

    # 1) Roots (no previous_version): assign a fresh UUID each.
    roots_to_update = []
    root_id_to_identity = {}
    for step in Steps._base_manager.filter(previous_version__isnull=True).iterator():
        new_identity = uuid.uuid4()
        root_id_to_identity[step.id] = new_identity
        if step.identity_id != new_identity:
            step.identity_id = new_identity
            roots_to_update.append(step)
    if roots_to_update:
        Steps._base_manager.bulk_update(roots_to_update, ['identity_id'])

    # 2) Walk descendants. Repeat passes until stable so chains of any
    # depth resolve.
    pending = list(
        Steps._base_manager.filter(previous_version__isnull=False).values_list('id', 'previous_version_id')
    )
    pass_no = 0
    while pending and pass_no < 50:
        pass_no += 1
        progress = False
        resolved = []
        for step_id, prev_id in pending:
            if prev_id in root_id_to_identity:
                root_id_to_identity[step_id] = root_id_to_identity[prev_id]
                resolved.append((step_id, prev_id))
                progress = True
        if not progress:
            break
        pending = [p for p in pending if p not in resolved]

    # 3) Bulk-update descendants with their chain root's identity.
    to_update = []
    for step in Steps._base_manager.exclude(previous_version__isnull=True).only(
        'id', 'identity_id',
    ).iterator():
        target = root_id_to_identity.get(step.id)
        if target is not None and step.identity_id != target:
            step.identity_id = target
            to_update.append(step)
    if to_update:
        Steps._base_manager.bulk_update(to_update, ['identity_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0066_drop_pcr_one_open_constraint'),
    ]

    operations = [
        migrations.RunPython(reassign_identity_per_chain, reverse_code=noop_reverse),
    ]
