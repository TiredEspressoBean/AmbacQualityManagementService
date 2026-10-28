"""
StepOverride aggregate services.

Covers the override-approval workflow: approve / reject a pending
override on a StepExecution. The viewset actions (and the model
methods, kept as thin delegates) funnel through here so status-gate
checks and expiry computation live in one place.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import OverrideStatus, StepOverride
from Tracker.models.qms import BlockType

# The gate's blocker text -> the block type a bypass of it names. Only these can be
# bypassed by request: the gate raises nothing else a StepOverride clears. Training
# is the supervisor override at start, life limits a limit extension, rollback its
# own flow (services/mes/parts.py).
_BYPASSABLE = (
    ('quarantine', BlockType.QUARANTINE),
    ('qa signoff', BlockType.QA_SIGNOFF),
    ('first piece', BlockType.FPI_REQUIRED),
    ('sampling', BlockType.SAMPLING_REQUIRED),
    ('measurement', BlockType.MEASUREMENT_FAILED),
)
BYPASSABLE_TYPES = frozenset(bt for _, bt in _BYPASSABLE)


def block_type_for(blocker: str) -> str | None:
    """The block type a bypass of this gate blocker would name, or None if it can't be
    bypassed by request."""
    text = (blocker or '').lower()
    for fragment, block_type in _BYPASSABLE:
        if fragment in text:
            return block_type
    return None


def _live_bypasses(step_execution):
    """Approved bypasses on this execution still in force: unused and unexpired."""
    from django.db.models import Q
    return StepOverride.objects.filter(
        step_execution=step_execution, status=OverrideStatus.APPROVED, used=False,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))


def clear_bypassed(step_execution, blockers: list[str]) -> list[str]:
    """`blockers` less those an approved, unexpired bypass on the execution covers."""
    live = set(_live_bypasses(step_execution).values_list('block_type', flat=True))
    if not live:
        return blockers
    return [b for b in blockers if block_type_for(b) not in live]


def part_blockers(part) -> dict | None:
    """What holds `part` at its current step, each blocker with the bypass that could
    clear it and any request already made. None when the part has no active step."""
    from Tracker.models import StepExecution
    se = StepExecution.get_current_execution(part)
    if se is None or se.step is None:
        return None
    _, raw = se.step.can_advance_from_step(se, part.work_order, apply_overrides=False)
    requests = {}
    for o in StepOverride.objects.filter(step_execution=se).order_by('requested_at'):
        requests[o.block_type] = o  # latest per type wins
    live = set(_live_bypasses(se).values_list('block_type', flat=True))
    rows = []
    for message in raw:
        bt = block_type_for(message)
        req = requests.get(bt) if bt else None
        rows.append({
            'message': message,
            'block_type': bt,
            'bypassed': bool(bt and bt in live),
            'request_id': req.id if req else None,
            'request_status': req.status if req else None,
            'request_reason': req.reason if req else None,
        })
    return {'step_execution': se.id, 'step_name': se.step.name, 'blockers': rows}


def validate_bypass_request(step_execution, block_type) -> None:
    """Refuse a bypass that can't clear anything, or one already asked for.

    Raises:
        ValueError: naming why.
    """
    if block_type not in BYPASSABLE_TYPES:
        raise ValueError(
            "That block can't be bypassed by request. Training gaps are authorised by a "
            "supervisor when the step starts; a life limit needs a limit extension.")
    if StepOverride.objects.filter(step_execution=step_execution, block_type=block_type,
                                   status=OverrideStatus.PENDING).exists():
        raise ValueError("A bypass of this block is already waiting for a decision.")


@transaction.atomic
def approve_step_override(
    override: StepOverride,
    user,
    expiry_hours: int | None = None,
) -> StepOverride:
    """Approve a pending override.

    If `expiry_hours` is not supplied, fall back to the step's
    `override_expiry_hours` (default 24).

    Raises:
        ValueError: override is not in PENDING state.
    """
    if override.status != OverrideStatus.PENDING:
        raise ValueError(
            f"Cannot approve override with status '{override.status}'"
        )
    if override.requested_by_id and override.requested_by_id == getattr(user, 'id', None):
        raise ValueError("You can't approve your own override request — someone else has to.")

    if expiry_hours is None:
        step = override.step_execution.step if override.step_execution else None
        expiry_hours = getattr(step, 'override_expiry_hours', 24)

    override.status = OverrideStatus.APPROVED
    override.approved_by = user
    override.approved_at = timezone.now()
    override.expires_at = timezone.now() + timedelta(hours=expiry_hours)
    override.save(update_fields=[
        'status', 'approved_by', 'approved_at', 'expires_at',
    ])

    part = override.step_execution.part if override.step_execution else None
    # An approved rollback is carried out now, for whoever asked — the lead isn't left
    # to notice the approval and press again (walk 2026-10-26). Re-running advancement
    # here instead would have pushed the part on, the opposite of what was asked.
    if override.block_type == BlockType.ROLLBACK:
        if part is not None:
            from Tracker.services.mes.parts import rollback_part_step
            rollback_part_step(part, override.requested_by or user, reason=override.reason,
                               override_id=override.id)
            override.refresh_from_db()
            if not override.used:
                override.used = True
                override.used_at = timezone.now()
                override.save(update_fields=['used', 'used_at'])
        return override

    # Override clears a specific blocker. Synchronously re-evaluate
    # advancement in the same request so the QA manager sees the
    # outcome inline.
    if part and part.work_order_id and part.step_id:
        from Tracker.services.mes.advancement import try_advance_lot
        try_advance_lot(
            work_order_id=str(part.work_order_id),
            step_id=str(part.step_id),
            tenant_id=str(part.tenant_id),
            operator=user,
        )

    return override


def reject_step_override(
    override: StepOverride,
    user,
    reason: str = '',
) -> StepOverride:
    """Reject a pending override. Appends the reason to the existing
    justification text for audit trail.

    Raises:
        ValueError: override is not in PENDING state.
    """
    if override.status != OverrideStatus.PENDING:
        raise ValueError(
            f"Cannot reject override with status '{override.status}'"
        )
    # Both rules were the UI's alone; the API took a self-refusal with no reason.
    if override.requested_by_id and override.requested_by_id == getattr(user, 'id', None):
        raise ValueError("You can't refuse your own override request — someone else decides it.")
    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Say why the request is refused.")

    override.status = OverrideStatus.REJECTED
    override.approved_by = user
    override.approved_at = timezone.now()
    if reason:
        override.reason = f"{override.reason}\n\n[REJECTED]: {reason}"
    override.save(update_fields=[
        'status', 'approved_by', 'approved_at', 'reason',
    ])
    return override


def mark_override_used(override: StepOverride) -> StepOverride:
    """Record that an approved override was consumed.

    Locks the row with SELECT FOR UPDATE inside a transaction so two
    concurrent callers can't both pass the status / expiry checks and
    each think they consumed the override. The first caller commits with
    used=True; the second reads used=True and raises.

    Raises:
        ValueError: override is not APPROVED, is already used, or is
            past expiry (flips status to EXPIRED and persists before
            raising).
    """
    with transaction.atomic():
        locked = StepOverride.unscoped.select_for_update().get(pk=override.pk)
        if locked.status != OverrideStatus.APPROVED:
            raise ValueError("Only approved overrides can be used")
        if locked.used:
            raise ValueError("Override has already been used")
        if locked.expires_at and timezone.now() > locked.expires_at:
            locked.status = OverrideStatus.EXPIRED
            locked.save(update_fields=['status'])
            raise ValueError("Override has expired")

        locked.used = True
        locked.used_at = timezone.now()
        locked.save(update_fields=['used', 'used_at'])
    # Refresh the caller's instance so they see the new state.
    override.refresh_from_db()
    return override
