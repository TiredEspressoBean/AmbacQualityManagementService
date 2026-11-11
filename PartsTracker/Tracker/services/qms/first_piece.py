"""The first piece as a START gate (user decisions 2026-11-11).

A first piece verifies a setup before production relies on it. It is the first N
distinct parts started in its context (N = the first-piece gate row's quantity: 1, or
one per fixture nest); a load is N parts starting at once. Until the context's first
piece is passed or waived, only those N may start — every other start is refused, and
QA is called. The first gated start opens the PENDING record itself.

Context comes from recorded facts: Per Shift from the visit's start, Per Equipment
from the visit's PRODUCTION machine (services/qms/fpi_scope.py).

A first piece is re-opened only by an operator's declared "New setup" (tool change,
offset, crash, repair…), which supersedes the pass or waiver; no automatic triggers.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

NEW_SETUP_REASONS = (
    ('TOOL_CHANGE', 'Tool change'),
    ('OFFSET', 'Offset adjusted'),
    ('CRASH', 'Crash'),
    ('REPAIR', 'Repair'),
    ('OTHER', 'Other'),
)


def quantity(step) -> int:
    """How many parts make up the step's first piece."""
    row = step._gate('first_piece')
    return max(1, row.fpi_quantity) if row else 1


def _released(records) -> bool:
    from Tracker.models import FPIStatus
    return records.filter(status__in=[FPIStatus.PASSED, FPIStatus.WAIVED]).exists()


def start_context(step, work_order, part, execution=None):
    """The context a start of `part` now is in. An existing visit answers from its own
    facts; a visit not yet created (a first Start Work) from the start moment and the
    machine it will run on."""
    from Tracker.services.qms.fpi_scope import PER_EQUIPMENT, context_for
    started = getattr(execution, 'started_at', None) or timezone.now()
    if (step.fpi_scope or '') == PER_EQUIPMENT and execution is None:
        from Tracker.services.mes.parts import planned_production_machine
        machine = planned_production_machine(step.id, part.id)
        return context_for(step, work_order, part=part, equipment=machine, at=started)
    return context_for(step, work_order, part=part, at=started)


def start_blocker(step, work_order, part, execution=None):
    """The first-piece refusal for starting `part` at `step`, or None.

    Refused while the context's first piece is unpassed and `part` isn't one of its N
    pieces (already one, or a place still open in the set)."""
    if part is None or work_order is None or not step.has_gate('first_piece'):
        return None
    from Tracker.models import FPIStatus
    from Tracker.services.mes.gates import Blocker, GateCode
    from Tracker.services.qms.fpi_scope import records_for
    ctx = start_context(step, work_order, part, execution)
    if not ctx.known:
        return Blocker(GateCode.FIRST_PIECE_PENDING, (
            f"{step.name} needs a first piece per machine, and the machine {part.ERP_id} runs on "
            "isn't recorded. Record the machine, then start it."))
    records = records_for(step, work_order, ctx)
    if _released(records):
        return None
    run = records.filter(status=FPIStatus.PENDING).first()
    if run is None:
        return None  # this start opens the first piece
    members = list(run.first_piece_parts.values_list('id', flat=True))
    if part.id in members or len(members) < quantity(step):
        return None
    names = ', '.join(run.first_piece_parts.order_by('ERP_id').values_list('ERP_id', flat=True))
    where = f" for {ctx.label}" if ctx.label else ""
    return Blocker(GateCode.FIRST_PIECE_PENDING, (
        f"{step.name} is waiting on its first piece{where} ({names}): QA buys it off before "
        f"{part.ERP_id} starts."))


def join_on_start(execution) -> None:
    """After a start at a first-piece step: the part joins its context's first piece
    while there's a place, and the first such start opens the PENDING record — the call
    to QA. A start into a released context changes nothing."""
    part, step = (execution.part if execution.part_id else None), execution.step
    work_order = execution.subject_work_order
    if part is None or work_order is None or step is None or not step.has_gate('first_piece'):
        return
    from Tracker.models import FPIRecord, FPIStatus
    from Tracker.services.qms.fpi import notify_fpi_requested
    from Tracker.services.qms.fpi_scope import records_for
    ctx = start_context(step, work_order, part, execution)
    if not ctx.known:
        return
    created = None
    with transaction.atomic():
        records = records_for(step, work_order, ctx).select_for_update()
        if _released(records):
            return
        run = records.filter(status=FPIStatus.PENDING).first()
        if run is None:
            run = created = FPIRecord.objects.create(
                tenant=work_order.tenant, work_order=work_order, step=step,
                part_type=step.part_type, designated_part=part, status=FPIStatus.PENDING,
                shift_date=ctx.shift_date, shift_id=ctx.shift_id, equipment_id=ctx.equipment_id)
        members = set(run.first_piece_parts.values_list('id', flat=True))
        if part.id not in members and len(members) < quantity(step):
            run.first_piece_parts.add(part)
            if run.designated_part_id is None:
                run.designated_part = part
                run.save(update_fields=['designated_part', 'updated_at'])
    if created is not None:
        transaction.on_commit(lambda: notify_fpi_requested(created))


def first_piece_part_ids(fpi) -> list:
    """The parts of a record's first piece (the designated part for a record made
    before first pieces had sets)."""
    ids = list(fpi.first_piece_parts.values_list('id', flat=True))
    if not ids and fpi.designated_part_id:
        ids = [fpi.designated_part_id]
    return ids


def declare_new_setup(*, step, work_order, user, reason_code: str, reason: str = '',
                      part=None, equipment=None):
    """An operator's declared new setup (tool change, offset, crash, repair…) re-opens
    the first piece of the context: the pass or waiver standing in it is SUPERSEDED,
    its step release withdrawn, and the next start begins a new first piece. Returns
    the superseded record.

    Raises:
        ValidationError: no reason, the step has no first piece, the context can't be
            told, or nothing in it is passed or waived (a first piece is already open).
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import FPIRecord, FPIStatus, QaApproval, RecordEdit
    from Tracker.services.qms.fpi_scope import context_for, records_for

    codes = dict(NEW_SETUP_REASONS)
    if reason_code not in codes:
        raise ValidationError("Say what changed in the setup.")
    reason = (reason or '').strip()
    if reason_code == 'OTHER' and not reason:
        raise ValidationError("Say what changed in the setup.")
    if not step.has_gate('first_piece'):
        raise ValidationError(f"{step.name} has no first piece to re-open.")
    ctx = context_for(step, work_order, part=part, equipment=equipment, at=timezone.now())
    if not ctx.known:
        raise ValidationError("Record the machine, then declare the new setup.")
    why = f"New setup: {codes[reason_code]}" + (f" — {reason}" if reason else '')
    with transaction.atomic():
        standing = (records_for(step, work_order, ctx).select_for_update()
                    .filter(status__in=[FPIStatus.PASSED, FPIStatus.WAIVED]).first())
        if standing is None:
            raise ValidationError("There's no passed or waived first piece here to re-open.")
        RecordEdit.objects.create(
            tenant=standing.tenant, content_type=ContentType.objects.get_for_model(FPIRecord),
            object_id=standing.id, field_name='status', old_value=standing.status,
            new_value=FPIStatus.SUPERSEDED, reason=why, edited_by=user)
        standing.status = FPIStatus.SUPERSEDED
        standing.save(update_fields=['status', 'updated_at'])
        # Its release no longer stands: the setup it verified is gone.
        QaApproval.objects.filter(fpi_record=standing, archived=False).update(  # tenant-safe: scoped FK
            archived=True, updated_at=timezone.now())
    return standing
