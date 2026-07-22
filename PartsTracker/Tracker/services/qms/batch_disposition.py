"""Containment + disposition for a failed batch cycle.

The batch analog of the per-part FAIL reaction in
`quality_report.record_quality_report_side_effects`. When a batch-scope
inspection report (a wash/heat-treat/plating cycle) goes FAIL, the whole load
is suspect — not one part. So instead of quarantining a single part and opening
a per-part disposition, we:

  1. Contain the load — quarantine the member parts still moving through
     production. Already-terminal parts (completed, scrapped, shipped) are left
     as-is: we don't retroactively un-complete them, but the disposition (linked
     to the batch) still names the full load for QA review, so nothing is
     hidden.
  2. Open ONE disposition for the load, linked to the BatchExecution. The cycle
     failed once; one disposition covers it. Affected parts are the batch's
     members (join through batch_execution.parts).
  3. Emit `ncr.opened` at batch scope.

Idempotent: a no-op if an open disposition already covers the batch, so the
signal firing on repeated FAIL saves doesn't pile up dispositions.
"""
from __future__ import annotations

# Flow states whose parts are still in production and can be safely held.
# Terminal / resolved states (COMPLETED, SCRAPPED, SHIPPED, IN_STOCK, …) are
# deliberately excluded — see module docstring.
_QUARANTINABLE = {"IN_PROGRESS", "AWAITING_QA", "READY_FOR_NEXT_STEP", "AT_OUTSIDE_PROCESS"}


def contain_failed_batch(report) -> None:
    """Contain the load behind a failed batch cycle and open its disposition.

    `report` is a FAIL QualityReports with `batch_execution` set. Safe to call
    from the auto_create_disposition signal on every FAIL save — idempotent.
    """
    from Tracker.models import Parts, PartsStatus, QuarantineDisposition, User

    batch = report.batch_execution
    if batch is None:
        return

    # Idempotency: one open disposition per batch.
    if QuarantineDisposition.objects.filter(
        batch_execution=batch, current_state__in=["OPEN", "IN_PROGRESS"],
    ).exists():
        return

    members = list(batch.parts.all())
    # Contain: hold the members still in production.
    held = [p for p in members if p.part_status in _QUARANTINABLE]
    for p in held:
        p.part_status = PartsStatus.QUARANTINED
    if held:
        # tenant-safe: members sourced from the batch (same tenant).
        Parts.objects.bulk_update(held, ["part_status"])

    qa_user = (
        User.objects.filter(
            user_roles__group__name__in=["QA Manager", "QA Inspector"],
            user_roles__group__tenant=report.tenant,
        ).first()
        or report.detected_by
    )

    step_name = batch.step.name if batch.step else "cycle"
    disposition = QuarantineDisposition.objects.create(
        assigned_to=qa_user,
        batch_execution=batch,
        step=batch.step,
        description=(
            f"Batch cycle failed at {step_name} - {len(members)} parts in the load"
            f" ({len(held)} held, {len(members) - len(held)} already past this step)."
        ),
    )
    disposition.quality_reports.add(report)

    _emit_batch_ncr_opened(report, batch, held_count=len(held), load_size=len(members))


def _emit_batch_ncr_opened(report, batch, *, held_count: int, load_size: int) -> None:
    """Fire `ncr.opened` for a batch cycle failure. Batch-scoped: no single
    part, work order and step come from the batch."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import NCROpenedPayload

    work_order = batch.work_order
    step = batch.step
    payload = NCROpenedPayload(
        id=str(report.id),
        tenant_id=str(report.tenant_id) if report.tenant_id else "",
        part_id=None,
        part_number="",
        work_order_id=str(work_order.id) if work_order else None,
        work_order_number=work_order.ERP_id if work_order else "",
        step_id=str(step.id) if step else None,
        step_name=step.name if step else "",
        severity=report.status,
        description=(
            report.description
            or f"Batch cycle failure - {held_count} of {load_size} parts held"
        ),
        opened_by_id=report.detected_by_id,
        opened_by_name=(
            (report.detected_by.get_full_name() or report.detected_by.username)
            if report.detected_by else ""
        ),
        opened_at=report.created_at,
    )
    emit(
        "ncr.opened",
        tenant=report.tenant,
        payload=payload,
        correlation_id=f"batchexecution:{batch.id}",
        idempotency_key=f"ncr.opened:batchexecution:{batch.id}",
    )
