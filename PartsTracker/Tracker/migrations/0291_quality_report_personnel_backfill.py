"""Carry quality reports' deprecated detector / verifier columns into role rows.

`QualityReportPersonnel` is the record of who did what on a report; the paths that
create reports now keep it in step (services/qms/quality_report.sync_personnel). This
does the same once for reports made before: a DETECTED_BY row for `detected_by`, a
VERIFIED_BY row for `verified_by`, where one isn't there already. Additive only.

Operators aren't copied: the deprecated `operators` list is still read alongside the
OPERATOR rows (QualityReports.operator_list).
"""
from django.db import migrations


def forwards(apps, schema_editor):
    QualityReports = apps.get_model('Tracker', 'QualityReports')
    Personnel = apps.get_model('Tracker', 'QualityReportPersonnel')
    # Historical models have no SecureManager: this reads every tenant, deliberately.
    from django.db.models import Q
    existing = set(Personnel._default_manager.filter(role__in=('DETECTED_BY', 'VERIFIED_BY'))
                   .values_list('quality_report_id', 'user_id', 'role'))
    rows = []
    for qr_id, det, ver in (QualityReports._default_manager
                            .filter(Q(detected_by__isnull=False) | Q(verified_by__isnull=False))
                            .values_list('id', 'detected_by_id', 'verified_by_id')):
        for user_id, role in ((det, 'DETECTED_BY'), (ver, 'VERIFIED_BY')):
            if user_id and (qr_id, user_id, role) not in existing:
                existing.add((qr_id, user_id, role))
                rows.append(Personnel(quality_report_id=qr_id, user_id=user_id, role=role))
    Personnel._default_manager.bulk_create(rows, batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ('Tracker', '0290_cycle_count_scope_and_erp_keyed'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
