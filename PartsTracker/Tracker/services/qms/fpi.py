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
        # A withdrawn approval (a voided pass) stays as it was recorded; a new pass
        # gets a new row rather than rewriting it.
        archived=False,
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


def void_fpi_pass(fpi: FPIRecord, user, reason: str) -> FPIRecord:
    """A first piece passed in error: void the pass (user decision 2026-10-26,
    Corrections #9). The passed record is kept as recorded and marked VOIDED, with the
    reason; the step sign-off it gave is withdrawn (archived, kept); a fresh PENDING
    FPI takes its place, so the run holds behind it until the piece is re-inspected.
    Parts already past the step are not pulled back. Returns the new PENDING record.

    Raises:
        ValueError: no reason, or the record isn't a pass.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction
    from Tracker.models import RecordEdit

    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Say why the pass is being voided")
    with transaction.atomic():
        fpi = FPIRecord.objects.select_for_update().get(pk=fpi.pk)  # tenant-safe: .objects auto-scopes
        if fpi.status != FPIStatus.PASSED:
            raise ValueError(f"Only a passed first piece can be voided; this one is {fpi.get_status_display().lower()}")
        RecordEdit.objects.create(
            tenant=fpi.tenant, content_type=ContentType.objects.get_for_model(FPIRecord),
            object_id=fpi.id, field_name='status', old_value=FPIStatus.PASSED,
            new_value=FPIStatus.VOIDED, reason=reason, edited_by=user)
        fpi.status = FPIStatus.VOIDED
        fpi.save(update_fields=['status', 'updated_at'])
        # The pass was the step's QA release for this work order; it no longer stands.
        QaApproval.objects.filter(  # tenant-safe: scoped FKs
            step_id=fpi.step_id, work_order_id=fpi.work_order_id, archived=False,
        ).update(archived=True, updated_at=timezone.now())
        fresh = FPIRecord.objects.create(
            tenant=fpi.tenant, work_order=fpi.work_order, step=fpi.step, part_type=fpi.part_type,
            designated_part=fpi.designated_part, equipment=fpi.equipment,
            shift_date=fpi.shift_date, status=FPIStatus.PENDING,
            notes=f"Re-inspection: the pass on {fpi.inspected_at:%Y-%m-%d} was voided — {reason}"
                  if fpi.inspected_at else f"Re-inspection: an earlier pass was voided — {reason}")
        transaction.on_commit(lambda: notify_fpi_requested(fresh))
    return fresh


def _first_piece_in(work_order, step, ctx, prefer=None):
    """The part a first piece for `ctx` is made against: `prefer` when it is at the step
    and in the context, else the first part to enter the step in the context (earliest
    open visit), else the lowest-numbered such part. None if there is none."""
    from Tracker.models import Parts, StepExecution
    from Tracker.services.qms.fpi_scope import PER_EQUIPMENT, machine_of

    def fits(part):
        if part is None or part.work_order_id != work_order.id or part.step_id != step.id:
            return False
        if ctx.scope == PER_EQUIPMENT:
            m = machine_of(part, step)
            return m is not None and m.id == ctx.equipment_id
        return True

    if fits(prefer):
        return prefer
    visits = (StepExecution.objects.filter(  # tenant-safe: .objects auto-scopes
        step=step, exited_at__isnull=True, part__work_order=work_order, part__step=step)
        .select_related('part').order_by('entered_at'))
    for se in visits:
        if fits(se.part):
            return se.part
    for part in Parts.objects.filter(work_order=work_order, step=step).order_by('ERP_id'):
        if fits(part):
            return part
    return None


def start_fpi(work_order, step, user, *, part=None, equipment=None, shift_date=None):
    """Start a first piece for the context `part` (or the given machine / shift) needs
    under the step's scope. Returns ``(record, created)``.

    - An open (PENDING) first piece in the context is returned, not duplicated.
    - After a pass nothing is started: a pass given in error is voided (Void pass).
    - After a waiver, a new first piece corrects it (B2): only a buy-off authority may
      start one, and the waiver is marked SUPERSEDED, with the person and reason kept.
    - After a fail, the new first piece is the recovery, as before.

    Raises:
        ValueError: the context can't be told (a Per Equipment step with no machine),
            no part of the context is at the step, it already passed, or a waiver is
            being superseded by someone without `sign_off_fpi`.
    """
    from django.contrib.contenttypes.models import ContentType
    from django.db import transaction
    from Tracker.models import RecordEdit
    from Tracker.services.qms.fpi_scope import context_for, records_for

    ctx = context_for(step, work_order, part=part, equipment=equipment, shift_date=shift_date)
    if not ctx.known:
        raise ValueError("This step needs a first piece per machine, and the machine this "
                         "part runs on isn't recorded. Set the machine, then start the FPI.")
    with transaction.atomic():
        records = records_for(step, work_order, ctx).select_for_update()
        latest = records.first()
        if latest is not None and latest.status == FPIStatus.PENDING:
            return latest, False
        if latest is not None and latest.status == FPIStatus.PASSED:
            raise ValueError("The first piece has passed. If the pass was given in error, "
                             "void it; that opens the re-inspection.")
        if latest is not None and latest.status == FPIStatus.WAIVED:
            if not user.has_tenant_perm('sign_off_fpi'):
                raise ValueError("Only someone who can sign off a first piece can replace a waiver "
                                 "with a new one.")
        designated = _first_piece_in(work_order, step, ctx, prefer=part)
        if designated is None:
            raise ValueError("No part has reached this step yet — start the FPI from a part "
                             "at the step.")
        if latest is not None and latest.status == FPIStatus.WAIVED:
            RecordEdit.objects.create(
                tenant=latest.tenant, content_type=ContentType.objects.get_for_model(FPIRecord),
                object_id=latest.id, field_name='status', old_value=FPIStatus.WAIVED,
                new_value=FPIStatus.SUPERSEDED,
                reason="Corrected by a new first piece", edited_by=user)
            latest.status = FPIStatus.SUPERSEDED
            latest.save(update_fields=['status', 'updated_at'])
        fpi = FPIRecord.objects.create(
            tenant=work_order.tenant, work_order=work_order, step=step,
            # Steps.part_type is non-null (PROTECT); WorkOrder has none of its own.
            part_type=step.part_type, designated_part=designated, status=FPIStatus.PENDING,
            shift_date=ctx.shift_date, equipment_id=ctx.equipment_id)
    # The andon call: a machine and operator may be idle from this moment.
    notify_fpi_requested(fpi)
    return fpi, True


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
