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

        part.part_status = new_status
        if disposition.disposition_type in ('REWORK', 'REPAIR'):
            part.total_rework_count += 1
        part.save(update_fields=['part_status', 'total_rework_count'])


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
