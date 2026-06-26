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

        _emit_ncr_opened(report)

    _update_sampling_analytics(report)


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
            .filter(part=part, step=step)
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
        opened_by_id=report.detected_by_id,
        opened_by_name=(
            (report.detected_by.get_full_name() or report.detected_by.username)
            if report.detected_by else ''
        ),
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
        user=getattr(report, "detected_by", None),
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
