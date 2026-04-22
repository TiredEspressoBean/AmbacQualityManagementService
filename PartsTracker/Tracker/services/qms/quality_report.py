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
"""
from __future__ import annotations

from Tracker.models import PartsStatus, SamplingTriggerManager


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

    if report.status in {"PASS", "FAIL"}:
        SamplingTriggerManager(report.part, report.status).update_state()

    if report.status == "FAIL":
        _trigger_sampling_fallback(report)

        if report.part:
            report.part.part_status = PartsStatus.QUARANTINED
            report.part.save(update_fields=["part_status"])
            _notify_step_failure(report)

    _update_sampling_analytics(report)


def _notify_step_failure(report) -> None:
    """Fire the STEP_FAILURE event for the rule dispatcher.

    Scope is the Step the part was at. Rules scoped at that Step — or
    tenant-wide rules with null scope — will match and enqueue
    NotificationTask rows for their recipients. Runs inside the caller's
    tenant context.
    """
    from Tracker.models import StepExecution
    from Tracker.services.core.notification import notify

    part = report.part
    step = getattr(part, 'step', None)

    # Current StepExecution for this part+step. `step_execution_id` in
    # the payload lets the `step_execution_assignee` resolver notify the
    # operator. Prefer an open execution (exited_at IS NULL) over a closed
    # one, so late-arriving QA reports still reach whoever is on the step.
    step_execution = None
    if part and step:
        step_execution = (
            StepExecution.objects
            .filter(part=part, step=step)
            .order_by('exited_at', '-entered_at')
            .first()
        )

    payload = {
        'part_id': str(part.id),
        'step_id': str(step.id) if step else None,
        'work_order_id': str(part.work_order.id) if part.work_order else None,
        'quality_report_id': str(report.id),
        'step_execution_id': str(step_execution.id) if step_execution else None,
    }
    # Scope = Step (so rules can target a specific step); related_obj = Part
    # (so the email-building handler reads the failed part off the task).
    notify('STEP_FAILURE', scope_obj=step, payload=payload, related_obj=part)


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
    """Trigger fallback sampling for the remaining parts in the work order."""
    from Tracker.services.mes.sampling_applier import SamplingFallbackApplier

    if report.part and report.part.sampling_ruleset:
        report.part.sampling_ruleset.create_fallback_trigger(
            triggering_part=report.part,
            quality_report=report,
        )
        return

    # Legacy path: no ruleset attached, use the generic applier.
    fallback_applier = SamplingFallbackApplier(report.part)
    fallback_applier.apply()


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
