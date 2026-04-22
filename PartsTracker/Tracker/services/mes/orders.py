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

    user_name = f"{user.first_name} {user.last_name}".strip() if user else "System"
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
