"""
Orders aggregate services.

Simple mutators for now — `push_to_hubspot` (external API) and
`create_parts_batch` (cross-aggregate) stay on the model until we do
a larger Orders pass.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import Orders


def add_order_note(
    order: Orders,
    user,
    message: str,
    visibility: str = 'VISIBLE',
) -> dict:
    """Prepend a timestamped note onto the order's timeline string.

    Does not save — callers persist via `order.save()` afterward, same
    contract as the old model method.

    Raises:
        ValueError: message is empty or whitespace-only.
    """
    if not message or not message.strip():
        raise ValueError("Note message cannot be empty")

    user_name = user.get_full_name().strip() if user else "System"
    if not user_name:
        user_name = user.username if user else "System"

    header = f"[{timezone.now().isoformat()} | {user_name} | {visibility}]"
    new_note = f"{header}\n{message.strip()}"

    if order.customer_note:
        order.customer_note = new_note + "\n---\n" + order.customer_note
    else:
        order.customer_note = new_note

    return {
        'timestamp': timezone.now().isoformat(),
        'user': user_name,
        'visibility': visibility,
        'message': message.strip(),
    }


def remove_parts_from_order(order: Orders, part_ids) -> int:
    """Take parts off a customer order. Only the order link is cleared: each part stays
    on its work order, at its step, in its status.

    Saved one part at a time so the audit log records each removal — the model method
    this replaces used a queryset `.update()`, which writes no audit entry.
    """
    from Tracker.models import Parts
    removed = 0
    for part in Parts.objects.filter(id__in=list(part_ids), order=order):  # tenant-safe: FK-scoped to the order
        part.order = None
        part.save(update_fields=['order'])
        removed += 1
    return removed


def note_completion_change(order: Orders, previous) -> bool:
    """Record the customer's original promised date the first time it moves.

    Call after `order.estimated_completion` may have changed, with the value it had
    before. The first move stamps `original_completion_date` with that earlier date;
    it is never overwritten after, so "Originally <date>" keeps the first promise
    however often the date slips again. A date set for the first time (nothing before)
    is not a slip. Every writer counts — an edit, the HubSpot sync, a work order's
    later date cascading up — because the promised date moved either way.

    Saves only the stamp. Returns True when it stamped.
    """
    if (previous is None or order.original_completion_date is not None
            or order.estimated_completion == previous):
        return False
    order.original_completion_date = previous
    order.save(update_fields=['original_completion_date'])
    return True
