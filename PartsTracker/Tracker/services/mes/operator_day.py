"""The operator home's own-day reads (decision 2026-10-29: wire the preview tiles).

- **Day recap:** step completions I signed off today and the findings I raised today
  (quality reports that FAILed or need REPAIR — a passing inspection isn't a flag), on
  the plant clock.
- **Last finished:** my most recent completed step, for the undo strip. Undo itself is
  the Parts rollback (undo window, approval past it); this only says what to offer it on.
"""
from __future__ import annotations


def my_first_pieces(tenant, user) -> list[dict]:
    """First pieces from my station: open ones, and ones decided today (plant clock).

    "Mine" is read from the run, not the record: a first piece is mine when the step
    execution on its designated part at that step is assigned to me, or I completed it.
    `FPIRecord.performed_by` is only filled on a QA co-sign, so a pending record has no
    sender of its own. Oldest open first, then the decided ones newest first.
    """
    from datetime import datetime, time
    from django.db.models import Exists, OuterRef, Q
    from django.utils import timezone
    from Tracker.models import FPIRecord, FPIStatus, StepExecution
    from Tracker.services.core.clock import plant_tz, tenant_today

    start = timezone.make_aware(datetime.combine(tenant_today(tenant), time.min), plant_tz(tenant))
    my_run = StepExecution.objects.filter(
        tenant=tenant, part_id=OuterRef('designated_part_id'), step_id=OuterRef('step_id'),
    ).filter(Q(assigned_to=user) | Q(completed_by=user))
    decided = (FPIStatus.PASSED, FPIStatus.FAILED, FPIStatus.WAIVED)
    rows = (FPIRecord.objects.filter(tenant=tenant, archived=False)
            .filter(Q(status=FPIStatus.PENDING) | Q(status__in=decided, inspected_at__gte=start))
            .filter(Exists(my_run))
            .select_related('step', 'designated_part', 'acknowledged_by', 'inspected_by'))

    def _name(u):
        return (f"{u.first_name or ''} {u.last_name or ''}".strip() or u.get_username()) if u else None

    out = [{
        'id': str(f.id),
        'step_name': f.step.name if f.step else '',
        'part_erp_id': f.designated_part.ERP_id if f.designated_part else None,
        'status': f.status,
        'sent_at': f.created_at,
        'acknowledged_by_name': _name(f.acknowledged_by),
        'decided_by_name': _name(f.inspected_by),
        'decided_at': f.inspected_at,
    } for f in rows]
    out.sort(key=lambda r: (r['status'] != FPIStatus.PENDING,
                            r['sent_at'] if r['status'] == FPIStatus.PENDING
                            else -(r['decided_at'] or r['sent_at']).timestamp()))
    return out


def my_day(tenant, user) -> dict:
    from datetime import datetime, time, timedelta
    from django.utils import timezone
    from Tracker.models import QualityReports, StepExecution
    from Tracker.services.core.clock import plant_tz, tenant_today

    start = timezone.make_aware(datetime.combine(tenant_today(tenant), time.min), plant_tz(tenant))
    end = start + timedelta(days=1)
    mine = StepExecution.objects.filter(tenant=tenant, completed_by=user, status='COMPLETED',
                                        exited_at__isnull=False)
    completed = mine.filter(exited_at__gte=start, exited_at__lt=end).count()
    flagged = QualityReports.objects.filter(tenant=tenant, detected_by=user, archived=False,
                                            status__in=('FAIL', 'REPAIR'),
                                            created_at__gte=start, created_at__lt=end).count()
    last = (mine.select_related('step', 'part').order_by('-exited_at').first())
    return {
        'completed_today': completed,
        'flagged_today': flagged,
        'last_finished': None if last is None else {
            'execution_id': str(last.id),
            'step_name': last.step.name if last.step else '',
            'part_id': str(last.part_id) if last.part_id else None,
            'part_erp_id': last.part.ERP_id if last.part else None,
            'work_order_id': str(last.part.work_order_id) if last.part and last.part.work_order_id else None,
            'finished_at': last.exited_at,
        },
    }
