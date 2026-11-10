"""
QualityReports aggregate services.

Side effects that fire when a quality report is first created (audit log
linkage, sampling fallback trigger, sampling analytics update). These were
extracted from QualityReports.save() so that save() remains storage-only
and callers (serializers, viewsets) invoke record_quality_report_side_effects
explicitly after the report row is committed.

All three helpers are create-only: they should run once per report, not on
every subsequent save. The serializer is the sole production create path;
tests that call QualityReports.objects.create() directly bypass these side
effects by design (they are testing model/DB behaviour, not the full flow).

A report that becomes FAIL later — edited to FAIL, or resolved to FAIL by its
findings — gets the FAIL consequences through `on_report_failed`, the same ones a
report created at FAIL gets. (The disposition is opened by the post_save signal on
any save at FAIL, so the trigger must be a real save, never a queryset .update().)
"""
from __future__ import annotations

from Tracker.models import PartsStatus, SamplingTriggerManager


# --- who did what: the role-tagged personnel record ---------------------------------
#
# `QualityReportPersonnel` (role per user) is the record of who detected, operated,
# verified, inspected or witnessed. The flat `detected_by` / `verified_by` / `operators`
# columns are deprecated but still written by the paths that create reports;
# `sync_personnel` carries the detector and verifier into role rows (migration 0291 did
# the same for existing reports). Readers go through `QualityReports.primary_detector` /
# `primary_verifier` / `operator_list` (and `detected_by_q` for filters), so they see
# one record whichever path wrote it.

def sync_personnel(report) -> None:
    """Make the report's DETECTED_BY / VERIFIED_BY rows agree with its deprecated
    `detected_by` / `verified_by` columns: the column's user gets a row, and an
    *unsigned* row for anyone else is dropped (a signed one is an attestation and
    stays).

    Operators aren't synced: the manual form edits the deprecated `operators` list,
    which is empty on a captured report, so pruning OPERATOR rows from it would delete
    the operator capture recorded. `operator_list` reads both instead."""
    from Tracker.models.qms import PersonnelRole, QualityReportPersonnel

    links = QualityReportPersonnel.objects.filter(quality_report=report)
    for role, user_id in ((PersonnelRole.DETECTED_BY, report.detected_by_id),
                          (PersonnelRole.VERIFIED_BY, report.verified_by_id)):
        stale = links.filter(role=role, signed_at__isnull=True)
        if user_id:
            stale = stale.exclude(user_id=user_id)
            QualityReportPersonnel.objects.get_or_create(quality_report=report, user_id=user_id, role=role)
        stale.delete()
    # Drop any prefetched rows so accessors read what's now stored.
    getattr(report, "_prefetched_objects_cache", {}).pop("personnel_links", None)


def claim_inspection(report, user) -> None:
    """The first person to record on an unattributed inspection becomes its inspector
    and detector. A receiving / OSP-return inspection opened at receipt names nobody —
    whoever received the goods isn't who inspects them — so attribution waits for the
    first reading or verdict. No-op once anyone is named, or without a signed-in user."""
    from Tracker.models.qms import PersonnelRole, QualityReportPersonnel

    if user is None or not getattr(user, "is_authenticated", False) or report.detected_by_id:
        return
    if QualityReportPersonnel.objects.filter(
            quality_report=report,
            role__in=(PersonnelRole.DETECTED_BY, PersonnelRole.INSPECTOR)).exists():
        return
    report.detected_by = user
    report.save(update_fields=["detected_by"])
    QualityReportPersonnel.objects.get_or_create(quality_report=report, user=user,
                                                 role=PersonnelRole.INSPECTOR)
    sync_personnel(report)


def detected_by_q(user):
    """Q for reports `user` detected — the detector role, the inspector who opened a
    receiving / OSP inspection, or (older rows) the deprecated column. Use .distinct()."""
    from django.db.models import Q
    from Tracker.models.qms import PersonnelRole
    return (Q(personnel_links__user=user,
              personnel_links__role__in=(PersonnelRole.DETECTED_BY, PersonnelRole.INSPECTOR))
            | Q(detected_by=user))


def record_quality_report_side_effects(report) -> None:
    """Run all create-time side effects for a newly created QualityReports row.

    Call this once, after the report has been persisted (i.e. report.pk is
    set). Callers are responsible for wrapping this in transaction.on_commit
    if the side effects should be deferred past the current transaction.

    Side effects performed:
    - Link report to the sampling audit log that triggered this inspection.
    - Update the SamplingTriggerManager state (PASS or FAIL).
    - If FAIL: trigger sampling fallback for remaining parts.
    - If FAIL: auto-quarantine the associated part.
    - Update sampling analytics counters for the ruleset / work-order pair.
    """
    _link_sampling_audit_log(report)

    # Sampling state is per part; a receiving lot's or an OSP return's report has none.
    if report.status == "PASS" and report.part:
        SamplingTriggerManager(report.part, report.status).update_state()

    if report.status == "FAIL":
        _apply_fail_consequences(report)

    _update_sampling_analytics(report)


def on_report_failed(report, prior_status) -> bool:
    """Run the FAIL consequences when `report` has just moved into FAIL from
    `prior_status` — the same ones a report created at FAIL gets: sampling state and
    fallback, quarantine of the part, the step-failure notification, ncr.opened.
    Returns True when it ran. No-op when the report was already FAIL or isn't now."""
    if prior_status == "FAIL" or report.status != "FAIL":
        return False
    # A batch cycle's report has no single part to react on; the disposition signal
    # contains the whole load instead (batch_disposition.contain_failed_batch).
    if report.batch_execution_id or report.part_id is None:
        return False
    _apply_fail_consequences(report)
    return True


_NOT_QUARANTINED_ON_FAIL = (PartsStatus.SHIPPED, PartsStatus.SCRAPPED, PartsStatus.CANCELLED,
                            PartsStatus.COMPLETED)


def _apply_fail_consequences(report) -> None:
    # A report with no part (a receiving lot, an OSP return) has no sampling state or
    # part to quarantine — the lot/shipment flow contains it — but is still an NCR.
    if report.part:
        SamplingTriggerManager(report.part, "FAIL").update_state()
    _trigger_sampling_fallback(report)
    if report.part:
        # A part already shipped, scrapped, cancelled or completed isn't put back in
        # quarantine: that rewrote where it is (hunt #18). The finding still stands —
        # NCR and disposition — and decides what happens to it.
        if report.part.part_status not in _NOT_QUARANTINED_ON_FAIL:
            report.part.part_status = PartsStatus.QUARANTINED
            report.part.save(update_fields=["part_status"])
        _notify_step_failure(report)
    _emit_ncr_opened(report)


def _notify_step_failure(report) -> None:
    """Fire the STEP_FAILURE event for the rule dispatcher.

    Scope is the Step the part was at. Rules scoped at that Step — or
    tenant-wide rules with null scope — will match and enqueue
    NotificationTask rows for their recipients. Runs inside the caller's
    tenant context.
    """
    from Tracker.models import StepExecution
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import StepFailurePayload

    part = report.part
    step = getattr(part, 'step', None)

    # Current StepExecution for this part+step. Phase 3 rules can match on
    # this via `payload.step_execution_id` if they need to route to the
    # current operator; the legacy `step_execution_assignee` resolver is
    # gone, replaced by personal rules with CEL conditions.
    step_execution = None
    if part and step:
        step_execution = (
            StepExecution.objects
            .filter(archived=False, part=part, step=step)
            .order_by('exited_at', '-entered_at')
            .first()
        )

    work_order = part.work_order if part else None
    payload = StepFailurePayload(
        id=str(report.id),
        tenant_id=str(report.tenant_id),
        quality_report_id=str(report.id),
        part_id=str(part.id) if part else '',
        # Parts.ERP_id (uppercase) — pre-Phase 5 code had `erp_id` here which
        # silently returned None and emitted blank part_numbers since 2025.
        part_number=getattr(part, 'ERP_id', None) or getattr(part, 'name', '') or '',
        step_id=str(step.id) if step else None,
        step_name=getattr(step, 'name', '') if step else '',
        work_order_id=str(work_order.id) if work_order else None,
        # WorkOrder model uses ERP_id, not order_number. The latter raised
        # AttributeError on every emit() in the pre-Phase 5 code.
        work_order_number=getattr(work_order, 'ERP_id', '') if work_order else '',
        step_execution_id=str(step_execution.id) if step_execution else None,
    )
    emit('quality.step_failure', tenant=report.tenant, payload=payload)


def _emit_ncr_opened(report) -> None:
    """Fire `ncr.opened` on the new unified notification path.

    Parallels the legacy `_notify_step_failure` until Phase 5 removes that.
    The new path is rule-resolution-free in Phase 1 (one ConsoleChannel row);
    Phase 3 adds per-tenant/per-customer/per-user rules.
    """
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import NCROpenedPayload

    part = report.part
    work_order = part.work_order if part else None
    step = report.step
    opener = report.primary_detector

    payload = NCROpenedPayload(
        id=str(report.id),
        tenant_id=str(report.tenant_id) if report.tenant_id else '',
        part_id=str(part.id) if part else None,
        part_number=part.ERP_id if part else '',
        work_order_id=str(work_order.id) if work_order else None,
        work_order_number=work_order.ERP_id if work_order else '',
        step_id=str(step.id) if step else None,
        step_name=step.name if step else '',
        severity=report.status,
        description=report.description or '',
        opened_by_id=opener.pk if opener else None,
        opened_by_name=(opener.get_full_name() or opener.username) if opener else '',
        opened_at=report.created_at,
    )

    # Use a stable idempotency key tied to the source record so retries of
    # the create-side-effects flow (e.g. on partial commit) don't double-emit.
    emit(
        'ncr.opened',
        tenant=report.tenant,
        payload=payload,
        correlation_id=f"qualityreport:{report.id}",
        idempotency_key=f"ncr.opened:qualityreport:{report.id}",
    )


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------

def _link_sampling_audit_log(report) -> None:
    """Link the report to the most recent positive sampling decision for its part."""
    from Tracker.models import SamplingAuditLog

    if report.part and report.part.requires_sampling:
        audit_log = (
            SamplingAuditLog.objects
            .filter(part=report.part, sampling_decision=True)
            .order_by("-timestamp")
            .first()
        )
        if audit_log:
            report.sampling_audit_log = audit_log
            report.save(update_fields=["sampling_audit_log"])


def _trigger_sampling_fallback(report) -> None:
    """Evaluate the step's quality gate for this inspection result.

    The gate (on the step's primary ruleset) decides whether any action fires —
    including TIGHTEN_SAMPLING, which replaces the old unconditional fallback
    switch. No-op when the step has no gate configured.
    """
    from Tracker.services.qms.quality_gate import evaluate_step_gate, gate_ruleset_for_step

    part = report.part
    if not part:
        return

    ruleset = gate_ruleset_for_step(part.step, part.part_type)
    evaluate_step_gate(
        ruleset=ruleset,
        work_order=part.work_order,
        trigger=report,
        triggering_part=part,
        user=report.primary_detector,
    )


def _update_sampling_analytics(report) -> None:
    """Increment sampling analytics counters for the report's ruleset / work-order."""
    from Tracker.models import SamplingAnalytics

    if not report.part or not report.part.sampling_ruleset:
        return

    analytics, _ = SamplingAnalytics.objects.get_or_create(
        ruleset=report.part.sampling_ruleset,
        work_order=report.part.work_order,
        defaults={
            "parts_sampled": 0,
            "parts_total": report.part.work_order.quantity,
            "defects_found": 0,
            "actual_sampling_rate": 0.0,
            "target_sampling_rate": 0.0,
            "variance": 0.0,
        },
    )

    analytics.parts_sampled += 1
    if report.status == "FAIL":
        analytics.defects_found += 1

    analytics.actual_sampling_rate = analytics.parts_sampled / analytics.parts_total * 100
    analytics.variance = abs(analytics.actual_sampling_rate - analytics.target_sampling_rate)

    analytics.save()
