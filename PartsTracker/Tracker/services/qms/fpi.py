"""
FPI (First Piece Inspection) aggregate services.

Pass / fail / waive / acknowledge flows for FPIRecord, plus the request/decided
notifications. A pending FPI is an andon call, not a worklist row — a machine
and an operator may be idle behind it — so the record carries a visible
sent → seen (acknowledge) → verdict lifecycle.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import FPIRecord, FPIResult, FPIStatus, QaApproval


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


def _reject_self_signoff(fpi: FPIRecord, user) -> None:
    """Segregation-of-duties: the person who signed the first piece's
    inspection substeps cannot ALSO buy off / waive the FPI. In QMS/AS9100
    practice a second qualified inspector must approve. If the substep
    completions on the designated part's current step-execution include
    any completed_by == user, block.

    Raises:
        ValueError: user already signed the first piece's substeps.
    """
    from Tracker.models import StepExecution, SubstepCompletion
    if fpi.designated_part_id is None:
        return  # nothing to check against yet
    se = StepExecution.get_current_execution(fpi.designated_part)
    if se is None:
        return
    if SubstepCompletion.objects.filter(step_execution=se, completed_by=user).exists():
        raise ValueError(
            "Segregation of duties: this user signed one or more of the first "
            "piece's inspection substeps. FPI buy-off must be signed by a "
            "different qualified inspector."
        )


def _assure_identity(fpi: FPIRecord, user, password: str, identity_verified: bool) -> bool:
    """Meet the step's authored assurance before the buy-off is recorded.

    A step whose author asked for a signature and a password must not be releasable
    without one just because the release came through first-piece buy-off instead of
    the step sign-off surface — that would make the author's choice a suggestion.

    `identity_verified` is True when the caller already proved identity by another
    password: the co-sign path, where a second person supplied email AND password, is
    strictly stronger than re-entering your own, so it is not asked for twice.

    Returns whether a password actually stands behind this buy-off.
    """
    from Tracker.services.core.second_person import verify_own_password
    if identity_verified:
        return True
    if fpi.step is None or fpi.step.qa_signoff_assurance != 'PASSWORD':
        return False
    refusal = verify_own_password(tenant=fpi.tenant, user=user, password=password or '',
                                  throttle_prefix='qa_signoff_reauth')
    if refusal:
        raise ValueError(refusal)
    return True


def _ensure_qa_approval(fpi: FPIRecord, user, *, password_proven: bool = False,
                        ip_address=None) -> None:
    """FPI Pass / Waive IS the QA signoff for the first piece. Record it as a
    QaApproval so `Steps.can_advance_from_step` sees the step-level signoff as
    satisfied — otherwise the FPI is passed but the WO stays stuck on the
    "QA signoff required but not received" blocker, since no other runtime
    path creates QaApproval records.

    The evidence fields match what `step_signoff.sign_off_step` records, so the same
    gate reads the same way whichever path signed it: a buy-off and a direct sign-off
    are not different kinds of release.
    """
    if fpi.step_id is None or fpi.work_order_id is None or user is None:
        return
    from Tracker.services.qms.step_signoff import signoff_meaning
    QaApproval.objects.update_or_create(
        tenant=fpi.tenant,
        step=fpi.step,
        work_order=fpi.work_order,
        defaults={
            'qa_staff': user,
            'verification_method': 'PASSWORD' if password_proven else 'NONE',
            'signature_meaning': signoff_meaning(fpi.work_order, fpi.step),
            'verified_at': timezone.now() if password_proven else None,
            'ip_address': ip_address or None,
        },
    )


def pass_fpi(fpi: FPIRecord, user, notes: str = '', performed_by=None, *,
             password: str = '', ip_address=None, identity_verified: bool = False,
             signature_data: str | None = None) -> FPIRecord:
    """Mark FPI as passed.

    Also creates the step-level QaApproval that `can_advance_from_step`
    checks — the FPI Pass IS the QA signoff for the first piece run. Blocks
    self-signoff: whoever signed the first-piece substeps cannot also sign
    off the FPI.

    `user` is the attester (recorded as `inspected_by` and on the QaApproval).
    `performed_by` is the operator at whose station a co-signature happened;
    pass it only on the co-sign path, leave None for a direct QA sign-off.
    `signature_data` is the co-signer's drawing, likewise co-sign only; the caller
    passes it after the co-signer's identity has been verified.

    Raises:
        ValueError: user already signed the first piece's substeps.
    """
    _reject_self_signoff(fpi, user)
    proven = _assure_identity(fpi, user, password, identity_verified)
    fpi.status = FPIStatus.PASSED
    fpi.result = FPIResult.PASS
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    fpi.performed_by = performed_by
    fpi.signature_data = signature_data or None
    if notes:
        fpi.notes = notes
    fpi.save()
    _ensure_qa_approval(fpi, user, password_proven=proven, ip_address=ip_address)
    notify_fpi_decided(fpi)
    return fpi


def fail_fpi(fpi: FPIRecord, user, notes: str = '', performed_by=None, *,
             signature_data: str | None = None) -> FPIRecord:
    """Mark FPI as failed.

    Blocks self-signoff (same SOD principle as `pass_fpi`). Does NOT create
    a QaApproval — a failed FPI leaves the batch blocked, and the step-level
    signoff should not be considered satisfied by a fail. See `pass_fpi` for
    the `user` / `performed_by` distinction.

    Raises:
        ValueError: user already signed the first piece's substeps.
    """
    _reject_self_signoff(fpi, user)
    fpi.status = FPIStatus.FAILED
    fpi.result = FPIResult.FAIL
    fpi.inspected_by = user
    fpi.inspected_at = timezone.now()
    fpi.performed_by = performed_by
    fpi.signature_data = signature_data or None
    if notes:
        fpi.notes = notes
    fpi.save()
    _record_first_piece_failure(fpi, user)
    notify_fpi_decided(fpi)
    return fpi


def _record_first_piece_failure(fpi: FPIRecord, user) -> None:
    """The failed first piece is nonconforming product (user decision 2026-10-20): a
    FAIL quality report on it at the FPI's step, through the same path as any failed
    inspection — the disposition (unassigned, the QA queue) from the report's save, and
    quarantine, the step-failure notice and ncr.opened from on_report_failed. The run
    stays held by the FPI itself. The FPI's own reason is the report's description, so
    the disposition doesn't read "No description"."""
    from Tracker.models import QualityReports
    from Tracker.services.qms.quality_report import on_report_failed
    if fpi.designated_part_id is None:
        return  # no first piece to hold
    step_name = fpi.step.name if fpi.step_id else "the step"
    description = (fpi.notes or "").strip() or f"First piece failed at {step_name}"
    report = fpi.quality_report
    if report is None:
        report = QualityReports.objects.create(  # tenant-safe: tenant set explicitly
            tenant=fpi.tenant, part=fpi.designated_part, step=fpi.step,
            status="FAIL", detected_by=user, description=description,
            sampling_method="fpi_fail")
        prior = None
        fpi.quality_report = report
        fpi.save(update_fields=["quality_report", "updated_at"])
    else:
        prior = report.status
        if prior == "FAIL":
            return
        report.status = "FAIL"
        if not (report.description or "").strip():
            report.description = description
        report.save(update_fields=["status", "description"])
    on_report_failed(report, prior)


def waive_fpi(fpi: FPIRecord, user, reason: str, performed_by=None, *,
              password: str = '', ip_address=None, identity_verified: bool = False,
              signature_data: str | None = None) -> FPIRecord:
    """Waive the FPI requirement.

    Creates the step-level QaApproval — a documented waive with reason IS
    the QA signoff for the first piece run. Blocks self-signoff (same SOD
    principle as `pass_fpi`). See `pass_fpi` for the `user` / `performed_by`
    distinction (`waived_by` is the attester here).

    Raises:
        ValueError: reason shorter than 10 characters, or user already
            signed the first piece's substeps.
    """
    if not reason or len(reason.strip()) < 10:
        raise ValueError("Waive reason must be at least 10 characters")
    _reject_self_signoff(fpi, user)
    # A waive releases the step as surely as a pass does, so it meets the same
    # authored assurance — a gate you can walk around is not a gate.
    proven = _assure_identity(fpi, user, password, identity_verified)
    fpi.status = FPIStatus.WAIVED
    fpi.waived = True
    fpi.waived_by = user
    fpi.waive_reason = reason
    fpi.performed_by = performed_by
    fpi.signature_data = signature_data or None
    fpi.save()
    _ensure_qa_approval(fpi, user, password_proven=proven, ip_address=ip_address)
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


def first_piece_readings(fpi: FPIRecord) -> list[dict]:
    """The readings captured on the first piece at the FPI's step — what the buy-off
    attests to. The designated part's latest visit to that step, one row per
    measurement as recorded (value, limits, in spec, who, when). Empty when no first
    piece is designated or nothing was measured; the buy-off dialog says so rather
    than inviting an attestation made blind."""
    from Tracker.models import StepExecution, StepExecutionMeasurement
    if fpi.designated_part_id is None or fpi.step_id is None:
        return []
    execution = (StepExecution.objects  # tenant-safe: .objects auto-scopes; FK-correlated to the record
                 .filter(part_id=fpi.designated_part_id, step_id=fpi.step_id)
                 .order_by('-visit_number').first())
    if execution is None:
        return []
    rows = []
    for m in (StepExecutionMeasurement.objects  # tenant-safe: FK-correlated to a scoped execution
              .filter(step_execution=execution)
              .select_related('measurement_definition', 'recorded_by')
              .order_by('recorded_at')):
        d = m.measurement_definition
        nominal = d.nominal if d else None
        lower = (nominal - d.lower_tol) if (nominal is not None and d.lower_tol is not None) else None
        upper = (nominal + d.upper_tol) if (nominal is not None and d.upper_tol is not None) else None
        rows.append({
            'id': str(m.id),
            'label': d.label if d else '',
            'value': (str(m.value) if m.value is not None else (m.string_value or None)),
            'unit': (d.unit if d else '') or '',
            'nominal': str(nominal) if nominal is not None else None,
            'lower_limit': str(lower) if lower is not None else None,
            'upper_limit': str(upper) if upper is not None else None,
            'within_spec': m.is_within_spec,
            'recorded_by_name': (m.recorded_by.get_full_name() or m.recorded_by.username) if m.recorded_by_id else '',
            'recorded_at': m.recorded_at,
        })
    return rows


def first_piece_signer_ids(fpi: FPIRecord) -> list[int]:
    """Users who signed the first piece's substeps at its current execution — the
    people `_reject_self_signoff` refuses as buy-off signers. Lets the dialog say so
    before the click instead of refusing after it."""
    from Tracker.models import StepExecution, SubstepCompletion
    if fpi.designated_part_id is None:
        return []
    se = StepExecution.get_current_execution(fpi.designated_part)
    if se is None:
        return []
    return sorted(set(
        SubstepCompletion.objects  # tenant-safe: FK-correlated to a scoped execution
        .filter(step_execution=se, completed_by__isnull=False)
        .values_list('completed_by_id', flat=True)))
