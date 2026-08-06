"""
QuarantineDisposition aggregate services.

Holds the disposition aggregate's business logic: applying a disposition's
decision to its part's status (`apply_disposition_to_part`) and the top-level
close flow (`complete_disposition_resolution`). `QuarantineDisposition.save()`
delegates the part cascade here rather than carrying it inline.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from Tracker.models import QuarantineDisposition

logger = logging.getLogger(__name__)


def apply_disposition_to_part(disposition: QuarantineDisposition, *, user=None) -> None:
    """Apply a disposition's decision to its part's status.

    Maps `disposition_type` to a part status and, for REWORK/REPAIR, bumps the
    rework counter. Idempotent: if the part is already at the mapped status it is
    a no-op, so it never double-applies or double-increments.

    Intended to fire when the `disposition_type` is *set or changed* (the
    OPEN->IN_PROGRESS decision), NOT on close — `QuarantineDisposition.save()`
    only calls this on a type change, so a later close can't re-apply/re-increment.

    `user` is accepted for symmetry with non-request callers; in the request path
    auditlog attributes the `part.save()` to `request.user` via middleware.
    """
    from Tracker.models import PartsStatus, Parts

    if disposition.part_id is None or not disposition.disposition_type:
        return

    # Only act once the decision is being implemented (or closed).
    if disposition.current_state not in ('IN_PROGRESS', 'CLOSED'):
        return

    # Keys MUST match the uppercase DISPOSITION_TYPES values.
    status_mapping = {
        'REWORK': PartsStatus.REWORK_NEEDED,
        'REPAIR': PartsStatus.REWORK_NEEDED,  # AS9100: may not fully conform
        'SCRAP': PartsStatus.SCRAPPED,
        'USE_AS_IS': PartsStatus.READY_FOR_NEXT_STEP,
        'RETURN_TO_SUPPLIER': PartsStatus.CANCELLED,
    }

    # QMS design intent: a disposition is a *documented decision*, not a
    # routing action. Loop-back decisions (REWORK / REPAIR) only translate
    # into a part-status change while the part is still held awaiting a
    # decision — QUARANTINED, or the initial PENDING before it entered
    # production. Once the part has moved past that point (IN_PROGRESS at
    # a step, AWAITING_QA at visit N, REWORK_IN_PROGRESS, terminal, etc.)
    # the disposition is a paper record of what was authorized; the
    # operator has already routed the part, and cascading REWORK_NEEDED
    # would drag it backwards.
    #
    # Terminal decisions (SCRAP / USE_AS_IS / RETURN_TO_SUPPLIER) keep the
    # cascade at any state — closing an NCR with SCRAP IS the terminal
    # decision, and the terminal-precedence guard below still protects
    # against downgrades.
    LOOPBACK_TYPES = ('REWORK', 'REPAIR')
    ROUTABLE_STATUSES = (PartsStatus.QUARANTINED, PartsStatus.PENDING)
    new_status = status_mapping.get(disposition.disposition_type)
    if not new_status:
        return  # unknown type

    # Terminal-dominant precedence (2a): a less-severe disposition must not pull a
    # part out of — or downgrade — a terminal status. SCRAP dominates everything;
    # a REWORK/REPAIR/USE_AS_IS decision can't reactivate a SCRAPPED/CANCELLED part.
    # (Reversing a terminal status is the deliberate, permission-gated bulk path
    # from 0d, never an incidental side-effect of another disposition.)
    terminal_rank = {
        PartsStatus.SCRAPPED: 3,
        PartsStatus.CANCELLED: 2,
        PartsStatus.COMPLETED: 1,
        PartsStatus.SHIPPED: 1,
        PartsStatus.IN_STOCK: 1,
        PartsStatus.AWAITING_PICKUP: 1,
        PartsStatus.CORE_BANKED: 1,
        PartsStatus.RMA_CLOSED: 1,
    }

    # Lock the part so the read-check-write below is atomic. Dispositions are
    # per-QR (several can target one part), and the advancement engine writes
    # part_status too; without the lock two concurrent appliers each read a
    # stale status and the precedence guard can be defeated — e.g. a REWORK
    # decision reviving a part another disposition just SCRAPPED, or the rework
    # counter double-incrementing. The second applier blocks here, then re-reads
    # the committed status and the guard holds.
    with transaction.atomic():
        part = Parts.objects.select_for_update().get(pk=disposition.part_id)
        if part.part_status == new_status:
            return  # idempotent no-op
        if terminal_rank.get(part.part_status, 0) > terminal_rank.get(new_status, 0):
            return  # current terminal status outranks this decision — don't regress it
        # Loop-back-only guard: REWORK/REPAIR only routes parts that are still
        # held awaiting a decision. If the part has already moved on
        # (AWAITING_QA, IN_PROGRESS, REWORK_IN_PROGRESS, READY, etc.), the
        # disposition is a paper record — someone has already routed the part.
        if (disposition.disposition_type in LOOPBACK_TYPES
                and part.part_status not in ROUTABLE_STATUSES):
            return

        part.part_status = new_status
        if disposition.disposition_type in ('REWORK', 'REPAIR'):
            part.total_rework_count += 1
        part.save(update_fields=['part_status', 'total_rework_count'])


# USE_AS_IS and REPAIR accept known-nonconforming product, so the standard treats
# them as the highest-authority decisions — requiring recorded customer / design
# approval (a concession or deviation) before the disposition is authorized.
_APPROVAL_REQUIRED_TYPES = {'USE_AS_IS', 'REPAIR'}


def decide_disposition(
    disposition: QuarantineDisposition,
    *,
    disposition_type: str,
    authorized_by,
    notes: str = '',
    customer_approval: dict | None = None,
) -> QuarantineDisposition:
    """Authorize and record a disposition decision (its ``disposition_type``).

    Choosing rework / repair / scrap / use-as-is / return-to-supplier is the
    authorized act under AS9100 & ISO 9001 8.7 and 21 CFR 820.90: the record must
    carry who authorized it, captured here as ``decision_authorized_by`` /
    ``_at``. Setting the type drives the existing cascade in
    ``QuarantineDisposition.save()`` — OPEN -> IN_PROGRESS and the part-status
    update via ``apply_disposition_to_part``.

    ``authorized_by`` is whoever the viewset resolved as the authority: the
    caller when they hold ``approve_disposition``, or an inline co-signer.

    Raises:
        ValueError: unknown type; a decision on a closed record; or a
            USE_AS_IS / REPAIR decision without a customer/design-approval
            reference (these accept nonconforming product and need a concession).
    """
    valid = dict(QuarantineDisposition.DISPOSITION_TYPES)
    if disposition_type not in valid:
        raise ValueError(f"Unknown disposition type: {disposition_type!r}.")

    if disposition.current_state == 'CLOSED':
        raise ValueError("This disposition is closed; its decision can no longer be changed.")

    if disposition_type in _APPROVAL_REQUIRED_TYPES:
        reference = str((customer_approval or {}).get('reference') or '').strip()
        if not reference:
            raise ValueError(
                f"A '{valid[disposition_type]}' decision accepts nonconforming product and "
                "requires recorded customer/design approval — provide an approval reference."
            )
        disposition.requires_customer_approval = True
        disposition.customer_approval_received = True
        disposition.customer_approval_reference = reference
        disposition.customer_approval_date = (
            (customer_approval or {}).get('date') or timezone.now().date()
        )

    disposition.disposition_type = disposition_type
    disposition.decision_authorized_by = authorized_by
    disposition.decision_authorized_at = timezone.now()
    if notes:
        existing = disposition.resolution_notes or ''
        disposition.resolution_notes = f"{existing}\n{notes}".strip() if existing else notes

    disposition.save()
    disposition.refresh_from_db()
    return disposition


def complete_disposition_resolution(
    disposition: QuarantineDisposition,
    user,
) -> QuarantineDisposition:
    """Mark resolution as completed and close the disposition if in progress.

    The blocker check + state mutation + save run inside a transaction
    with SELECT FOR UPDATE so a concurrent writer can't add a new blocker
    (e.g., a fresh quality report) between the check and the save.
    Without this, the disposition could close while a blocker is in flight,
    leaving the parts cascade in `QuarantineDisposition.save()` to act on
    a stale state.

    Raises:
        ValueError: blockers exist (pending annotations, etc.).
    """
    with transaction.atomic():
        # Lock the row so the blocker check below sees a consistent view.
        # Tenant-scoped (`.objects`): every caller runs under request or
        # tenant_context (serializer decision path, advance-off-rework close,
        # the async advance task), so this stays within the active tenant
        # rather than reaching across tenants via `.unscoped`.
        locked = (
            QuarantineDisposition.objects
            .select_for_update()
            .get(pk=disposition.pk)
        )

        blockers = locked.get_completion_blockers()
        if blockers:
            raise ValueError(
                f"Cannot complete disposition: {'; '.join(blockers)}"
            )

        locked.resolution_completed = True
        locked.resolution_completed_by = user
        locked.resolution_completed_at = timezone.now()

        if locked.current_state == 'IN_PROGRESS':
            locked.current_state = 'CLOSED'

        locked.save()

    disposition.refresh_from_db()
    return disposition


def route_part_to_rework_if_needed(disposition: QuarantineDisposition, user) -> None:
    """Route a REWORK/REPAIR disposition's part to the process's in-process rework
    step at *decision* time (when the type is set) — split off the lot and moved
    there, while the disposition stays IN_PROGRESS until the rework is re-inspected
    (2e closes it then). Per AS9100, a rework/repair isn't resolved until
    re-inspection passes, so the NCR-decision record stays open until verified.

    No-op unless: the type is REWORK/REPAIR, the part exists and isn't already
    split, and the process has exactly ONE rework step (zero or ambiguous → leave
    it REWORK_NEEDED for manual routing via the control page, 2c). Idempotent."""
    if disposition.disposition_type not in ('REWORK', 'REPAIR'):
        return
    part = disposition.part
    if part is None or part.split_from_cohort:
        return
    process = part.work_order.process if part.work_order_id else None
    if process is None:
        return

    from Tracker.models import ProcessStep, PartSplitReason

    rework_steps = {
        ps.step_id: ps.step
        for ps in ProcessStep.objects.filter(
            process=process, step__step_type='REWORK',
        ).select_related('step')
    }
    if len(rework_steps) != 1:
        return  # zero or ambiguous — manual routing (2c)

    from Tracker.services.mes.splits import split_part_from_lot
    target = next(iter(rework_steps.values()))
    split_part_from_lot(
        part=part,
        reason=PartSplitReason.REWORK,
        user=user,
        rework_target_step=target,
        notes=f"Routed from disposition {disposition.disposition_number}",
    )
    logger.info(
        "Routed part %s to rework step %s from disposition %s",
        part.id, target.id, disposition.pk,
    )
