"""emit() — the single entry point for sending a notification event.

Validates the payload against the registered event's schema, builds a
correlation id, and fires the Django signal `notification_event`. The
dispatcher receiver (see dispatcher.py) handles the rest.

Callers do not interact with the outbox, channels, or rules. They build
a typed payload dataclass and call `emit(code, tenant, payload)`.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import asdict, is_dataclass

import django.dispatch
from django.core.serializers.json import DjangoJSONEncoder

from .registry import get_event

# Signal payload kwargs:
#   sender: EventType
#   event_code: str
#   tenant: Tenant
#   payload: dataclass instance
#   correlation_id: str
#   idempotency_key: str
notification_event = django.dispatch.Signal()


def emit(event_code, tenant, payload, *, correlation_id=None, idempotency_key=None):
    """Emit a notification event.

    Args:
        event_code: registered code (e.g. 'ncr.opened').
        tenant: Tenant model instance the event belongs to.
        payload: instance of the event's `payload_schema` dataclass.
        correlation_id: optional override; defaults to `'{event_code}:{payload.id}'`.
        idempotency_key: optional override; defaults to a fresh random key.
            Pass an explicit value (e.g. `f'{event_code}:{source.id}:{action}'`)
            when the same emit may fire from a retry; the outbox unique
            constraint will then dedupe.

    Returns: the `idempotency_key` used (caller can store/log it).

    Raises:
        KeyError: event_code is not registered.
        TypeError: payload is not an instance of the event's schema.
    """
    event = get_event(event_code)
    schema = event.payload_schema

    if not isinstance(payload, schema):
        raise TypeError(
            f"emit({event_code!r}, ...): payload must be {schema.__name__}, "
            f"got {type(payload).__name__}"
        )
    if not is_dataclass(payload):
        raise TypeError(
            f"emit({event_code!r}, ...): payload must be a dataclass instance"
        )

    # Round-trip through DjangoJSONEncoder so non-JSON-native values in the
    # payload (datetime, Decimal, UUID, etc.) become JSON-safe before they
    # reach the outbox JSONField. The dispatcher stores `payload_dict` raw.
    payload_dict = json.loads(json.dumps(asdict(payload), cls=DjangoJSONEncoder))

    if correlation_id is None:
        # Prefer payload.correlation_id if defined, else event_code:id.
        explicit = payload_dict.get('correlation_id')
        if explicit:
            correlation_id = str(explicit)
        else:
            correlation_id = f"{event_code}:{payload_dict.get('id', '')}"

    if idempotency_key is None:
        idempotency_key = f"{event_code}:{correlation_id}:{secrets.token_hex(8)}"

    notification_event.send(
        sender=event,
        event_code=event_code,
        tenant=tenant,
        payload=payload,
        payload_dict=payload_dict,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )

    return idempotency_key
