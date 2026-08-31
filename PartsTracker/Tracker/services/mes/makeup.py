"""Make-up planning — replace scrap so a work order still delivers its ordered good count.

`plan_work_order` grosses the started quantity up for *expected* scrap. When *actual*
scrap outruns that, the count of parts still alive drops below the ordered good count
(`WorkOrder.target_good_quantity`). Make-up planning tops it back up: it creates
replacement parts (flagged `is_makeup`) at the route's first step, which the next solve
schedules (the re-solve loop acts on the staleness flag set here).

Planner-confirmed by design (AS9100/ITAR): `work_order_shortfall` reports the gap for the
UI; `create_makeup_parts` is the explicit action that spawns the replacements. The rule is
iterative — top up to keep alive == target — so a replacement that later scraps is covered
by the next top-up, and no gross-up-on-the-gross-up is needed.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def work_order_shortfall(work_order) -> dict:
    """Report the make-up gap for a work order: how many good parts it owes vs. how many
    are still alive (not scrapped/cancelled). `shortfall` is what make-up would create."""
    from Tracker.models import PartsStatus

    target = work_order.target_good_quantity or work_order.quantity
    parts = work_order.parts  # tenant-safe: reverse FK from the tenant-scoped WO
    alive = parts.exclude(
        part_status__in=[PartsStatus.SCRAPPED, PartsStatus.CANCELLED]).count()
    return {
        'target_good': target,
        'alive': alive,
        'good': parts.filter(part_status=PartsStatus.COMPLETED).count(),
        'scrapped': parts.filter(part_status=PartsStatus.SCRAPPED).count(),
        'shortfall': max(0, target - alive),
    }


def create_makeup_parts(work_order, user=None) -> dict:
    """Create `shortfall` replacement parts at the route's first step, flagged `is_makeup`,
    and mark the schedule stale so the next solve picks them up. No-op when on track.
    Returns the recomputed shortfall report plus `created`."""
    from django.db import transaction
    from Tracker.models import Parts, PartsStatus, ProcessStep
    from Tracker.services.scheduling.staleness import mark_active_schedule_stale

    info = work_order_shortfall(work_order)
    n = info['shortfall']
    if n <= 0:
        return {'created': 0, **info}

    process = work_order.process
    part_type = process.part_type if process else None
    if part_type is None:
        raise ValueError("work order has no process/part type to make up against")
    first_ps = ProcessStep.objects.filter(process=process).order_by('order').first()
    if first_ps is None:
        raise ValueError("process has no steps")

    existing_mu = Parts.objects.filter(work_order=work_order, is_makeup=True).count()
    with transaction.atomic():
        new_parts = [
            Parts(
                tenant=work_order.tenant, work_order=work_order, part_type=part_type,
                step=first_ps.step, is_makeup=True, part_status=PartsStatus.PENDING,
                ERP_id=f"{work_order.ERP_id}-MU{existing_mu + i + 1:04d}",
            )
            for i in range(n)
        ]
        # tenant-safe: each Part sets tenant=work_order.tenant explicitly above.
        Parts.objects.bulk_create(new_parts)
        # Sampling eval, mirroring create_parts_batch.
        work_order._bulk_evaluate_sampling(new_parts)
        # New demand (bulk_create bypasses the Parts post_save) — flag for re-solve.
        mark_active_schedule_stale(work_order.tenant_id)

    logger.info("Created %s make-up parts on WO %s by user=%s",
                n, work_order.ERP_id, getattr(user, 'id', None))
    return {'created': n, **work_order_shortfall(work_order)}
