"""Correcting a recorded inspection result without rewriting it.

A recorded report is frozen (approval_lock: "recorded as a result"). When the capture
behind it was wrong — a false FAIL — QA voids the capture; the report is then marked
SUPERSEDED (who, when, the void reason) and stays exactly as recorded. The re-capture
writes a NEW report, linked back through `replaced_by`. User decision 2026-10-22: the
re-capture used to rewrite FAIL to PASS in place, leaving only the audit log.

The nonconformance the false FAIL opened is closed separately, by the QA manager, as
"not a nonconformance" (services/qms/disposition.decide_disposition).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone


def _pair_filter(completion) -> dict:
    if completion.batch_execution_id:
        return {'batch_execution_id': completion.batch_execution_id,
                'substep_id': completion.substep_id}
    return {'step_execution_id': completion.step_execution_id,
            'substep_id': completion.substep_id}


@transaction.atomic
def void_completion(completion, user, reason: str):
    """Void a substep completion; supersede the recorded report it produced."""
    from Tracker.models import QualityReports

    completion.void(user, reason)
    if not completion.substep_id:
        return completion
    for report in (QualityReports.objects  # tenant-safe: scoped by the execution FK
                   .select_for_update()
                   .filter(superseded_at__isnull=True, **_pair_filter(completion))
                   .exclude(status='PENDING')):
        report.superseded_at = timezone.now()
        report.superseded_by = user
        report.superseded_reason = reason
        report.save(update_fields=['superseded_at', 'superseded_by', 'superseded_reason',
                                   'updated_at'])
    return completion


def link_replacement(new_report) -> None:
    """A fresh report for a pair whose earlier one was superseded: point the old one
    at it, so the record reads FAIL → superseded → this PASS."""
    from Tracker.models import QualityReports

    if new_report.substep_id is None:
        return
    pair = ({'batch_execution_id': new_report.batch_execution_id}
            if new_report.batch_execution_id else
            {'step_execution_id': new_report.step_execution_id})
    if not any(pair.values()):
        return
    (QualityReports.objects  # tenant-safe: scoped by the execution FK
     .filter(substep_id=new_report.substep_id, superseded_at__isnull=False,
             replaced_by__isnull=True, **pair)
     .exclude(pk=new_report.pk)
     .update(replaced_by=new_report))
