"""Event registry.

Curated, dev-owned. Events are registered at app startup by importing the
domain `events.py` modules from `TrackerConfig.ready()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Type


# `eq=False` keeps `__hash__` = id()-based. With `eq=True` (the default for
# frozen dataclasses), Python derives `__hash__` from the field values — and
# the `list` defaults below make instances unhashable, which breaks Django
# signal dispatch (signals require `sender` to be hashable).
@dataclass(frozen=True, eq=False)
class EventType:
    code: str
    label: str
    domain: str
    payload_schema: Type
    default_channels: list[str] = field(default_factory=lambda: ['in_app'])
    default_recipient_groups: list[str] = field(default_factory=list)
    default_on: bool = False
    transactional: bool = False
    description: str = ''
    external_routable: bool = False


EVENT_REGISTRY: dict[str, EventType] = {}


def register_event(event_type: EventType) -> EventType:
    if event_type.code in EVENT_REGISTRY:
        existing = EVENT_REGISTRY[event_type.code]
        if existing is event_type:
            return event_type
        raise ValueError(f"Event code already registered: {event_type.code!r}")

    schema = event_type.payload_schema
    if not is_dataclass(schema):
        raise TypeError(
            f"payload_schema for {event_type.code!r} must be a dataclass; got {schema!r}"
        )
    if not hasattr(schema, 'sample') or not callable(getattr(schema, 'sample')):
        raise TypeError(
            f"payload_schema for {event_type.code!r} must define a sample() classmethod"
        )

    field_names = {f.name for f in fields(schema)}
    if 'id' not in field_names and 'correlation_id' not in field_names:
        raise TypeError(
            f"payload_schema for {event_type.code!r} must expose either an "
            f"`id` field or an explicit `correlation_id` field"
        )

    EVENT_REGISTRY[event_type.code] = event_type
    return event_type


def get_event(code: str) -> EventType:
    try:
        return EVENT_REGISTRY[code]
    except KeyError:
        raise KeyError(f"Unknown event code: {code!r}") from None
