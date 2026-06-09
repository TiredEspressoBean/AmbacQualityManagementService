# Per-row identity backfill for Substep.identity_id.
#
# Django's `default=uuid.uuid4` on the AddField in 0068 evaluates the
# default ONCE and writes the same UUID to every existing row. Walk
# every Substep and reassign a fresh identity_id so the field is
# actually per-row unique.
#
# Idempotent and safe to re-run: only acts on rows whose identity_id
# is shared with another row. Tenants whose initial 0068+backfill
# already completed see this as a no-op. Tenants where a previous
# attempt was interrupted partway through see this finish the job.
#
# `atomic = False` so each per-batch commit lands independently —
# a mid-walk crash leaves a partially-fixed table that the next
# `migrate` run finishes via the duplicate-detection guard.

import uuid
from django.db import migrations, transaction
from django.db.models import Count


def assign_unique_identity_per_substep(apps, schema_editor):
    Substep = apps.get_model('Tracker', 'Substep')

    # Identify identity_id values shared across multiple Substep rows.
    # The AddField default collapses every pre-existing row onto one
    # UUID, so the duplicate set is "every row that existed before
    # this column landed".
    duplicate_ids = list(
        Substep._base_manager
        .values('identity_id')
        .annotate(n=Count('id'))
        .filter(n__gt=1)
        .values_list('identity_id', flat=True)
    )
    if not duplicate_ids:
        return

    to_update = []
    for sub in (
        Substep._base_manager
        .filter(identity_id__in=duplicate_ids)
        .iterator(chunk_size=500)
    ):
        sub.identity_id = uuid.uuid4()
        to_update.append(sub)
        if len(to_update) >= 500:
            with transaction.atomic():
                Substep._base_manager.bulk_update(to_update, ['identity_id'])
            to_update = []
    if to_update:
        with transaction.atomic():
            Substep._base_manager.bulk_update(to_update, ['identity_id'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    # See module docstring — RunPython mustn't be wrapped in the
    # global migration transaction, otherwise per-batch atomic blocks
    # collapse into savepoints under one super-transaction.
    atomic = False

    dependencies = [
        ('Tracker', '0068_substep_identity_id'),
    ]

    operations = [
        migrations.RunPython(assign_unique_identity_per_substep, reverse_code=noop_reverse),
    ]
