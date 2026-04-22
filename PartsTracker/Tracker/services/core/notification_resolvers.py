"""
Role resolver registry for NotificationRule.

A resolver is a named function `(payload: dict) -> Iterable[User]` that
computes "who should be notified right now for this event" from the
event's payload. Examples: the operator currently assigned to the part's
step execution, the engineer who owns the process, the customer on the
part's order.

Resolvers are looked up by name from NotificationRule.recipient_resolver_key.

Resolver contract:
    - Runs inside the event's tenant context (ContextVar is set).
    - Queries must go through `.objects` so SecureManager auto-scopes.
      NEVER use `.all_tenants` or `.unscoped` in a resolver.
    - Return an iterable of User instances. Empty is fine.
    - Must not raise for missing data — log and return [] instead.

To add a resolver: define a function, decorate with @register_resolver('key').
Import the module once at app-ready time so the decorators run.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable

from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

_RESOLVERS: dict[str, Callable[[dict], Iterable]] = {}


def register_resolver(key: str):
    """Decorator to register a resolver under `key`."""
    def decorator(fn: Callable[[dict], Iterable]):
        if key in _RESOLVERS:
            raise ValueError(f'Notification resolver already registered: {key!r}')
        _RESOLVERS[key] = fn
        return fn
    return decorator


def get_resolver(key: str) -> Callable[[dict], Iterable]:
    """Return the resolver callable for `key`, or raise KeyError."""
    resolver = _RESOLVERS.get(key)
    if resolver is None:
        raise KeyError(f'No notification resolver registered: {key!r}')
    return resolver


def resolver_keys() -> list[str]:
    """All registered resolver keys, sorted. Useful for admin dropdowns."""
    return sorted(_RESOLVERS.keys())


# =========================================================================
# Starter resolvers
# =========================================================================

@register_resolver('step_execution_assignee')
def _step_execution_assignee(payload: dict):
    """Operator currently assigned to the step execution named in the payload.

    Expected payload: {'step_execution_id': <uuid>}
    """
    from Tracker.models import StepExecution

    exec_id = payload.get('step_execution_id')
    if not exec_id:
        return []
    execution = (
        StepExecution.objects
        .filter(id=exec_id)
        .select_related('assigned_to')
        .first()
    )
    if execution is None or execution.assigned_to is None:
        return []
    return [execution.assigned_to]
