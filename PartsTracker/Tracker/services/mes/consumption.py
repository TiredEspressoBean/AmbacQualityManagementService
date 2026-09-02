"""Material consumption — recording what actually went into a part.

`MaterialUsage` and the stock deduction it performs have existed for a while, but
nothing ever created a row: receipts pushed `quantity_remaining` up and nothing pushed
it down. On-hand therefore drifted high, and two features already believe it —
`get_material_gates` decides whether the SOLVER thinks material is available, and the
staging list tells a handler what to pick. Both were reading a number that only ever
grew.

This module is the missing call site. When a part leaves a step, the BOM lines
consumed at that step are drawn from stock, oldest-expiry first, and recorded against
the part for traceability ("what lots went into this unit", "which units are affected
if this lot is recalled").

Three decisions worth stating:

**Consumption never blocks advancement.** If stock says there isn't enough but the
operator physically built the part, the stock figure was wrong — refusing to advance
would punish them for a data error and, worse, teach people to work around the system.
We record what we can, report the shortfall, and let the material GATE (which runs
before work is scheduled) be the thing that prevents starting without material.

**FEFO, not FIFO.** Shelf-life-controlled material is drawn oldest-expiry-first so the
stock most at risk of expiring is used first. Lots with no expiry sort last.

**No operator, no record.** `MaterialUsage.consumed_by` is required and traceability
is the point of the table — an automated or seeded advance has no one to attribute
consumption to, so it records nothing rather than inventing an actor.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)


@dataclass
class ConsumptionResult:
    """What was drawn for one part at one step."""
    usages: list = field(default_factory=list)      # MaterialUsage rows created
    shortfalls: list = field(default_factory=list)  # {material, needed, drawn, short}
    skipped_reason: str | None = None

    @property
    def consumed_any(self) -> bool:
        return bool(self.usages)


def _released_bom_lines(part_type_id, cache: dict) -> list:
    """BUY/consumable lines of the part type's released assembly BOM.

    Latest RELEASED rather than `is_current_version`, matching the material gate: an
    open draft revision flips the released row non-current while the floor still
    builds to it.
    """
    if part_type_id not in cache:
        from Tracker.models import BOM, BOMLine

        bom = (BOM.objects.filter(part_type_id=part_type_id, bom_type='ASSEMBLY',
                                  status='RELEASED').order_by('-version').first())
        if not bom:
            cache[part_type_id] = []
        else:
            # tenant-safe: `bom` is a tenant-scoped row; its lines share its tenant.
            lines = BOMLine.objects.filter(bom=bom).select_related('material')
            cache[part_type_id] = list(lines)
    return cache[part_type_id]


def _usable_lots(material_id, tenant):
    """Accepted stock of a material, oldest-expiry first (FEFO), then oldest receipt.

    Lots with no expiry date sort last: dated stock is the stock that can spoil, so it
    should leave first.
    """
    from django.db.models import F
    from Tracker.models import MaterialLot

    return list(
        MaterialLot.objects.filter(
            tenant=tenant, material_id=material_id,
            status__in=('ACCEPTED', 'IN_USE'), quantity_remaining__gt=0,
        ).order_by(F('expiration_date').asc(nulls_last=True), 'received_date')
    )


@transaction.atomic
def consume_for_step(part, step, operator, bom_cache: dict | None = None
                     ) -> ConsumptionResult:
    """Draw and record the material the BOM consumes at `step` for one `part`.

    Returns a `ConsumptionResult`; never raises for insufficient stock. A shelf-life
    expired lot is skipped rather than consumed — `assert_lot_usable` is the gate, and
    this path calls it explicitly rather than relying on the model's save() backstop.
    """
    from Tracker.models import MaterialUsage
    from Tracker.services.life_tracking.shelf_life import assert_lot_usable

    result = ConsumptionResult()
    if operator is None or not getattr(operator, 'is_authenticated', True):
        result.skipped_reason = "no operator to attribute consumption to"
        return result
    if part.part_type_id is None or step is None:
        result.skipped_reason = "part has no part type, or no step given"
        return result

    work_order = part.work_order
    # A reman unit's harvested components come from teardown, not purchased stock —
    # the same carve-out the material gate makes, so the two can't disagree.
    is_reman = bool(work_order and work_order.cores.exists())

    cache = bom_cache if bom_cache is not None else {}
    tenant = part.tenant
    for line in _released_bom_lines(part.part_type_id, cache):
        if line.consumed_at_step_id != step.id:
            continue
        if line.source != 'BUY' or line.is_optional:
            continue
        if is_reman and line.allow_harvested:
            continue
        if line.material_id is None:
            continue

        needed = Decimal(str(line.quantity))
        drawn = Decimal('0')
        for lot in _usable_lots(line.material_id, tenant):
            if drawn >= needed:
                break
            try:
                assert_lot_usable(lot)
            except ValueError:
                continue  # expired — leave it for disposal, don't build with it
            take = min(lot.quantity_remaining, needed - drawn)
            if take <= 0:
                continue
            usage = MaterialUsage.objects.create(
                tenant=tenant, lot=lot, part=part, work_order=work_order,
                qty_consumed=take, consumed_by=operator, step=step,
            )
            result.usages.append(usage)
            drawn += take

        if drawn < needed:
            # Recorded, not raised: the part was built, so the shortfall is a stock
            # accuracy problem to surface, not a reason to refuse the advance.
            result.shortfalls.append({
                'material': line.material.name if line.material else str(line.material_id),
                'needed': float(needed), 'drawn': float(drawn),
                'short': float(needed - drawn),
            })
    return result


def consume_for_step_safely(part, step, operator, bom_cache: dict | None = None):
    """`consume_for_step` that can never break the caller's transition.

    Advancement is the operator's real work; recording what it used is bookkeeping.
    A bug or bad BOM data here must not strand a finished part at its old step, so
    failures are logged and swallowed. Returns the result, or None if it blew up.
    """
    try:
        result = consume_for_step(part, step, operator, bom_cache)
    except Exception:  # noqa: BLE001 - bookkeeping must not block the floor
        logger.exception(
            "Material consumption failed for part=%s step=%s; advancing anyway.",
            getattr(part, 'id', None), getattr(step, 'id', None))
        return None
    if result.shortfalls:
        logger.warning(
            "Material shortfall consuming for part=%s step=%s: %s",
            part.id, step.id, result.shortfalls)
    return result
