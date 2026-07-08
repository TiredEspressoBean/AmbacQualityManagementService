"""
FPI (First Piece Inspection) aggregate services.

Pass / fail / waive / acknowledge flows for FPIRecord, plus the request/decided
notifications. A pending FPI is an andon call, not a worklist row — a machine
and an operator may be idle behind it — so the record carries a visible
sent → seen (acknowledge) → verdict lifecycle.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import FPIRecord, FPIResult, FPIStatus


def acknowledge_fpi(fpi: FPIRecord, user) -> FPIRecord:
    """QA acknowledges a pending FPI ("I'm on it"). Idempotent per record —
    the first acknowledgment wins; later calls are no-ops so the operator-facing
    "Seen by X" stays stable.

    Raises:
        ValueError: record is not pending.
    """
    if fpi.status != FPIStatus.PENDING:
        raise ValueError(f"Cannot acknowledge FPI with status '{fpi.status}'")
    if fpi.acknowledged_at is not None:
        return fpi
    fpi.acknowledged_by = user
    fpi.acknowledged_at = timezone.now()
    fpi.save(update_fields=['acknowledged_by', 'acknowledged_at', 'updated_at'])
    return fpi


def pass_fpi(fpi: FPIRecord, user, notes: str = '') -> FPIRecord:
    """Mark FPI as passed."""
    fpi.status = FPIStatus.PASSED
    fpi.result = FPIResult.PASS
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    if notes:
        fpi.notes = notes
    fpi.save()
    notify_fpi_decided(fpi)
    return fpi


def fail_fpi(fpi: FPIRecord, user, notes: str = '') -> FPIRecord:
    """Mark FPI as failed."""
    fpi.status = FPIStatus.FAILED
    fpi.result = FPIResult.FAIL
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    if notes:
        fpi.notes = notes
    fpi.save()
    notify_fpi_decided(fpi)
    return fpi


def waive_fpi(fpi: FPIRecord, user, reason: str) -> FPIRecord:
    """Waive the FPI requirement.

    Raises:
        ValueError: reason shorter than 10 characters.
    """
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Waive reason must be at least 10 characters")
    fpi.status = FPIStatus.WAIVED
    fpi.waived = True
    fpi.waived_by = user
    fpi.waive_reason = reason
    fpi.save()
    notify_fpi_decided(fpi)
    return fpi


# ── notifications ─────────────────────────────────────────────────────────────

def _fpi_payload_kwargs(fpi: FPIRecord) -> dict:
    return dict(
        id=str(fpi.id),
        tenant_id=str(fpi.tenant_id) if fpi.tenant_id else "",
        fpi_record_id=str(fpi.id),
        work_order_id=str(fpi.work_order_id) if fpi.work_order_id else None,
        work_order_number=fpi.work_order.ERP_id if fpi.work_order_id else "",
        step_id=str(fpi.step_id) if fpi.step_id else None,
        step_name=fpi.step.name if fpi.step_id else "",
        equipment_name=fpi.equipment.name if fpi.equipment_id else "",
    )


def notify_fpi_requested(fpi: FPIRecord) -> None:
    """Emit `fpi.requested` — the andon call to QA. Fired by the creation
    site (the ensure action); a machine may be idle from this moment."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import FpiRequestedPayload

    emit(
        "fpi.requested",
        tenant=fpi.tenant,
        payload=FpiRequestedPayload(**_fpi_payload_kwargs(fpi)),
        correlation_id=f"fpi:{fpi.id}",
        idempotency_key=f"fpi.requested:{fpi.id}",
    )


def notify_fpi_decided(fpi: FPIRecord) -> None:
    """Emit `fpi.decided` — the verdict back to the floor (pass/fail/waive)."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.qms.events import FpiDecidedPayload

    emit(
        "fpi.decided",
        tenant=fpi.tenant,
        payload=FpiDecidedPayload(**_fpi_payload_kwargs(fpi), status=fpi.status),
        correlation_id=f"fpi:{fpi.id}",
        idempotency_key=f"fpi.decided:{fpi.id}:{fpi.status}",
    )
