"""Notification channel backends.

A channel is responsible for taking a `NotificationOutbox` row that has
already been rendered and delivering it. Channels do not write to the DB
themselves — the dispatcher creates the outbox row, the worker task picks
it up and calls `channel.send(row)`, and the task updates `status` /
`sent_at` / `error` based on the return value or exception.

Phase 1 ships only ConsoleChannel, which logs to stdout. Email and in-app
channels land in Phase 2.
"""
from __future__ import annotations

from .base import NotificationChannel, ChannelRegistry, get_channel, register_channel
from .console import ConsoleChannel
from .email import EmailChannel
from .in_app import InAppChannel

# Wire the registry at import time so the dispatcher doesn't need to.
register_channel(ConsoleChannel())
register_channel(EmailChannel())
register_channel(InAppChannel())

__all__ = [
    'NotificationChannel',
    'ChannelRegistry',
    'get_channel',
    'register_channel',
    'ConsoleChannel',
    'EmailChannel',
    'InAppChannel',
]
