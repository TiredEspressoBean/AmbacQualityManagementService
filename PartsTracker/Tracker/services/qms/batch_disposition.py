"""Containment + decisions for a failed batch cycle.

The batch analog of the per-part FAIL reaction in
`quality_report.record_quality_report_side_effects`. When a batch-scope
inspection report (a wash/heat-treat/plating cycle) goes FAIL, the whole load
is suspect — not one part. Its NCR covers the load (ncr.ncr_for_failed_report
raised it, batch_execution set), and here we:

  1. Contain the load — quarantine the member parts still moving through
     production. Already-terminal parts (completed, scrapped, shipped) are left
     as-is: we don't retroactively un-complete them, but the NCR still lists the
     full load for QA review, so nothing is hidden.
  2. Open a decision (disposition) for each held part, under the NCR — the same
     per-part decision any failure gets, so each part is held, decided, routed and
     closed the way a single part is. QA decides them together or a few at a time
     (ncr.decide_ncr).
  3. `ncr.opened` goes out once for the NCR when it commits (ncr.announce).

Idempotent: a second failing report on the load joins its open NCR, and a report
that already contained the load doesn't contain it again.
"""
from __future__ import annotations

# Flow states whose parts are still in production and can be safely held.
# Terminal / resolved states (COMPLETED, SCRAPPED, SHIPPED, IN_STOCK, …) are
# deliberately excluded — see module docstring.
_QUARANTINABLE = {"IN_PROGRESS", "AWAITING_QA", "READY_FOR_NEXT_STEP", "AT_OUTSIDE_PROCESS"}


def contain_failed_batch(report) -> None:
    """Contain the load behind a failed batch cycle and open its parts' decisions.

    `report` is a FAIL QualityReports with `batch_execution` set. Safe to call
    from the auto_create_disposition signal on every FAIL save — idempotent.
    """
    from Tracker.models import PartsStatus, QuarantineDisposition
    from Tracker.services.qms.ncr import ncr_for_failed_report

    batch = report.batch_execution
    if batch is None:
        return

    # Once per report, as for a part's FAIL: a report that already contained the load
    # doesn't contain it again. Any later save of the report — a "no CAPA needed", a
    # claim — re-quarantined members already released and opened a bare new decision
    # (hunt 2026-11-10, N10).
    if report.dispositions.exists():
        return

    # One open NCR per load: a second failing report joins it, as evidence on the
    # decisions still open — left unlinked, it passed the once-per-report guard above
    # after they closed and re-contained the load (round-3 #8).
    ncr, raised = ncr_for_failed_report(report)
    if not raised:
        for d in ncr.dispositions.filter(archived=False).exclude(current_state='CLOSED'):
            d.quality_reports.add(report)
        return

    members = list(batch.parts.all())
    # Contain: hold the members still in production.
    held = [p for p in members if p.part_status in _QUARANTINABLE]
    # One save per part, not bulk_update: a quarantine is a quality record, and only a
    # save writes the part's audit entry (with who triggered it). A load is tens of
    # parts, not thousands.
    for p in held:
        p.part_status = PartsStatus.QUARANTINED
        p.save(update_fields=["part_status"])
    if held:
        from Tracker.services.scheduling.staleness import mark_active_schedule_stale
        mark_active_schedule_stale(report.tenant_id)

    step_name = batch.step.name if batch.step else "cycle"
    ncr.description = (
        f"Batch cycle failed at {step_name} - {len(members)} parts in the load"
        f" ({len(held)} held, {len(members) - len(held)} already past this step)."
    )
    ncr.save(update_fields=["description", "updated_at"])
    # A decision per held part. When every part had already moved past the step, there
    # is nothing to hold, but the NCR still needs a decision on the load: one per part,
    # as a record of what was decided about what had left.
    for p in (held or members):
        disposition = QuarantineDisposition.objects.create(
            assigned_to=None,  # the QA queue, like every auto-opened disposition
            ncr=ncr, part=p, step=batch.step,
        )
        disposition.quality_reports.add(report)


def join_failed_load(batch, parts) -> None:
    """Parts added to a load whose cycle has already failed join its open NCR: held, with
    a decision of their own, as the parts there at the failure were."""
    from Tracker.models import NCR, PartsStatus, QuarantineDisposition

    ncr = NCR.objects.filter(archived=False, state='OPEN', batch_execution=batch).first()  # tenant-safe: scoped by the batch FK
    if ncr is None:
        return
    report = ncr.reports.order_by('created_at').first()
    for p in parts:
        if p.part_status not in _QUARANTINABLE:
            continue
        p.part_status = PartsStatus.QUARANTINED
        p.save(update_fields=["part_status"])
        disposition = QuarantineDisposition.objects.create(
            assigned_to=None, ncr=ncr, part=p, step=batch.step)
        if report is not None:
            disposition.quality_reports.add(report)
