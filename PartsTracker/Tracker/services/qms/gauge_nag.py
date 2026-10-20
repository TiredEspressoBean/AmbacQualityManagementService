"""
The personal calibration nag: "N gauges you used this week are due within 7 days."

Round-4 research (Plex, GageList, Quality Digest): parts measured with an
out-of-cal gauge become suspect product retroactively — so the point-of-use
gate must block, and this nag exists to PRE-EMPT that gate: warn the inspector
about gauges in their own recent rotation before the block lands.

"Gauges you used" = the equipment attached to the quality reports the user
filed (`QualityReportEquipment` via `detected_by`). This is the single
equipment↔user source since `EquipmentUsage` was retired (it modeled the same
link but was never written at runtime — see plan #1).
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from Tracker.services.core.clock import tenant_today

DEFAULT_USED_WITHIN_DAYS = 7
DEFAULT_DUE_WITHIN_DAYS = 7


def my_gauge_nag(user, used_within_days: int = DEFAULT_USED_WITHIN_DAYS,
                 due_within_days: int = DEFAULT_DUE_WITHIN_DAYS) -> list[dict]:
    """Equipment the user recently used whose calibration FAILED, is overdue, or is
    due soon. One row per equipment; failed first, then most-urgent. A failed gauge
    you just measured with is the exposure case — the readings may be suspect — so it
    is listed, not dropped (it used to be excluded)."""
    from Tracker.models import CalibrationRecord, QualityReportEquipment

    used_cutoff = timezone.now() - timedelta(days=used_within_days)

    # Gauges the user used = equipment on the quality reports they filed. The
    # junction has no tenant field; scoping is inherited via the parent report,
    # which .objects auto-scopes through the FK filter.
    used_ids = set(
        QualityReportEquipment.objects
        .filter(quality_report__in=__reports_by(user, used_cutoff))
        .values_list("equipment_id", flat=True)
    )
    if not used_ids:
        return []

    today = tenant_today(user.tenant_id)
    due_cutoff = today + timedelta(days=due_within_days)

    # The latest calibration per gauge decides: a FAIL is listed whatever its due date.
    records = (CalibrationRecord.objects  # tenant-safe: .objects auto-scopes
               .filter(equipment_id__in=used_ids)
               .select_related("equipment"))
    if hasattr(records, "latest_per_equipment"):
        records = records.latest_per_equipment()

    rows = []
    for rec in records:
        failed = rec.result == 'FAIL'
        if not failed and rec.due_date > due_cutoff:
            continue
        rows.append({
            "equipment_id": str(rec.equipment_id),
            "equipment_name": rec.equipment.name if rec.equipment_id else "",
            "due_date": rec.due_date.isoformat(),
            "days_until_due": (rec.due_date - today).days,
            "overdue": rec.due_date < today,
            "failed": failed,
        })
    rows.sort(key=lambda r: (not r["failed"], r["days_until_due"]))
    return rows


def __reports_by(user, cutoff):
    from Tracker.models import QualityReports
    return QualityReports.objects.filter(archived=False,   # tenant-safe: .objects auto-scopes
        detected_by=user, created_at__gte=cutoff,
    )
