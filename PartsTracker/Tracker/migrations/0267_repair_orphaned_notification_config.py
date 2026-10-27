"""Repair notification config left pointing at deleted rows.

seed_demo's wipe ran with FK enforcement off and kept rules, schedules and
escalation config while deleting the users and customers they named. A personal
schedule whose owner was gone failed validation on every fire, five-minutely,
once the schedule tick began running. Apply each field's own on_delete now:
CASCADE deletes the row (through the ORM, so its dependents follow), SET_NULL
nulls the column, and dangling M2M rows are dropped.
"""
from django.db import migrations, models

MODELS = ('NotificationRule', 'NotificationSchedule', 'EscalationPolicy', 'EscalationStep')


def _dangling(schema_editor, table, column, target):
    t = target._meta
    with schema_editor.connection.cursor() as cur:
        cur.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND NOT EXISTS '
            f'(SELECT 1 FROM "{t.db_table}" x WHERE x."{t.pk.column}" = "{table}"."{column}")'
        )
        return {r[0] for r in cur.fetchall()}


def repair(apps, schema_editor):
    for name in MODELS:
        M = apps.get_model('Tracker', name)
        for f in M._meta.local_fields:
            if not f.is_relation or f.name == 'tenant':
                continue
            ids = _dangling(schema_editor, M._meta.db_table, f.column, f.related_model)
            if not ids:
                continue
            rows = M._base_manager.filter(**{f'{f.attname}__in': ids})
            if f.remote_field.on_delete is models.CASCADE:
                rows.delete()
            elif f.null:
                rows.update(**{f.attname: None})
        for f in M._meta.local_many_to_many:
            through = f.remote_field.through
            if not through._meta.auto_created:
                continue
            col = f.m2m_reverse_name()
            ids = _dangling(schema_editor, through._meta.db_table, col, f.related_model)
            if ids:
                through._base_manager.filter(**{f'{col}__in': ids}).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0266_remove_broken_celery_cleanup_schedule'),
    ]

    operations = [
        migrations.RunPython(repair, migrations.RunPython.noop),
    ]
