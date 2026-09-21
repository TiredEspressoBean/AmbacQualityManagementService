"""Turning customer demand into work.

`Orders` records the customer engagement; an `OrderLine` records what they actually
asked for. This module is the step between a line and a job — the one that did not
exist, which is why an order could be attached to work after the fact but could never
produce it.

Planning is deliberately explicit rather than automatic. Creating a line is a sales
act; releasing work against it commits capacity and material, and in a shop where
release is `MANUAL`-gated it would be strange for demand entry to quietly bypass the
gate that exists one step later.
"""
from __future__ import annotations

from django.db import transaction

from Tracker.models import OrderLineStatus, WorkOrder


class CannotPlan(ValueError):
    """The line can't become work, with the reason a planner needs to act on."""


def plan_order_line(line, *, user=None, quantity: int | None = None,
                    priority: int | None = None) -> WorkOrder:
    """Create a work order covering `quantity` of `line` (default: all that remains).

    Pegs the job to BOTH the line and its order. `related_order` is what
    `cascade_order_status` reads and what every existing surface filters on, so a job
    planned from a line has to be visible to those as well — setting only the line
    would make order-level completion silently stop working for exactly the orders
    that used the new path.

    Refuses rather than guesses. A part type with no approved routing, or with several
    and none designated, is a decision for whoever owns the routing — releasing against
    the wrong one produces a correct-looking job that builds the wrong thing.
    """
    from Tracker.services.mes.bom_explosion import _build_process
    from Tracker.services.mes.work_order import plan_work_order

    if line.status == OrderLineStatus.CANCELLED:
        raise CannotPlan("This line is cancelled.")

    remaining = line.remaining_quantity
    if remaining <= 0:
        raise CannotPlan(
            f"Line {line.line_number} is fully planned "
            f"({line.planned_quantity} of {line.quantity} on work orders).")

    qty = remaining if quantity is None else int(quantity)
    if qty <= 0:
        raise CannotPlan("Quantity must be greater than zero.")
    if qty > remaining:
        raise CannotPlan(
            f"Only {remaining} of {line.quantity} are still unplanned; asked for {qty}.")

    process, reason = _build_process(line.part_type)
    if process is None:
        raise CannotPlan(f"Can't plan {line.part_type}: {reason}.")

    with transaction.atomic():
        wo = plan_work_order(
            tenant=line.tenant,
            process=process,
            quantity=qty,
            user=user,
            priority=priority,
            # The line's date is the promise. Carrying it onto the job is what lets the
            # scheduler back-schedule against what the customer was told, rather than
            # against a date somebody retyped.
            expected_completion=line.due_date,
        )
        # Both pegs, for the reason in the docstring.
        # tenant-safe: `wo` was just created by plan_work_order under line.tenant, and
        # this addresses it by its own pk — there is no wider set to leak into.
        WorkOrder.objects.filter(pk=wo.pk).update(
            order_line=line, related_order_id=line.order_id)
        wo.refresh_from_db()
    return wo
