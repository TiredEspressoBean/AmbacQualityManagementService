"""Notification system v1 — registry, emit, dispatcher, channels, CEL.

Public entry points:
    register_event(event_type)              — registry.py
    emit(event_code, tenant, payload, ...)  — emit.py
    compile_condition(source)               — cel.py
    validate_against_event(source, code)    — cel.py
    evaluate(program, payload, owner_user)  — cel.py
"""
from .registry import EventType, register_event, get_event, EVENT_REGISTRY
from .emit import emit, notification_event
from .cel import (
    CelValidationError,
    compile_condition,
    evaluate,
    validate_against_event,
)

__all__ = [
    'EventType',
    'register_event',
    'get_event',
    'EVENT_REGISTRY',
    'emit',
    'notification_event',
    'CelValidationError',
    'compile_condition',
    'evaluate',
    'validate_against_event',
]
