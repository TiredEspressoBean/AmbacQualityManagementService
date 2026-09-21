"""Harvest reservations.

A core under a repair-and-return arrangement is the customer's property, and so
is everything taken out of it. Once a harvested component is accepted into
inventory it becomes an ordinary `Parts` row, indistinguishable from stock — at
which point nothing records that it is spoken for, and the first thing that ever
consumes it takes a part the customer is owed.

`Parts.reserved_for_core` is that record, and this module is the rule that reads
it. Kept out of `harvested_component.py` because the reservation is enforced far
from where it is written: the write happens once at accept time, the check
happens on every attempt to attach a part to a job.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError


def is_reserved(part) -> bool:
    """Whether this part belongs to a specific core rather than to stock."""
    return part.reserved_for_core_id is not None


def assert_work_order_allowed(part, work_order) -> None:
    """Refuse to attach a reserved part to work that is not its own core's.

    Detaching (`work_order=None`) is always allowed: putting a part back on the
    shelf takes nothing from anyone, and blocking it would strand a part that was
    attached by mistake.

    A part may join the job that owns its reserving core. Today that is the
    teardown WO — the core's only work order — so in practice this permits
    re-attaching a component to the very job that produced it and nothing else.
    When a rebuild loop exists and points a rebuild WO at the core, the same rule
    admits it without changing, which is why the check is expressed as "the core's
    work order" rather than "the teardown".

    Raises:
        ValidationError: the part is reserved to a different core's work.
    """
    if work_order is None or not is_reserved(part):
        return

    core = part.reserved_for_core
    if core.work_order_id and core.work_order_id == work_order.pk:
        return

    raise ValidationError({
        'work_order': (
            f"Part {part.ERP_id} was harvested from core {core.core_number}, which is "
            f"being repaired and returned to its customer. Its components are that "
            f"customer's property and cannot be built into other work. Release the "
            f"reservation first if the arrangement has changed."
        )
    })


def release_reservation(part, user=None):
    """Free a reserved part into general stock.

    The escape hatch for an arrangement that changed after receipt — a customer
    scrapping their unit and taking an exchange, say. Deliberately explicit: the
    reservation should never dissolve as a side effect of some other edit.
    """
    part.reserved_for_core = None
    part.save(update_fields=['reserved_for_core', 'updated_at'])
    return part
