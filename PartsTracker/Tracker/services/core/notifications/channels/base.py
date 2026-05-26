"""Base channel interface + a small in-process registry.

Phase 1 ships ConsoleChannel only; Phase 2 adds Email and In-App.
"""
from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from Tracker.models import NotificationOutbox


class NotificationChannel(Protocol):
    """Channels deliver rendered outbox rows. Raise on failure for retry."""

    code: str

    def send(self, outbox_row: 'NotificationOutbox') -> None:
        ...

    def supports_attachments(self) -> bool:
        ...

    def max_body_length(self) -> int | None:
        ...


class ChannelRegistry:
    """Simple in-process registry. Replace with settings-driven discovery later."""

    def __init__(self) -> None:
        self._channels: dict[str, NotificationChannel] = {}

    def register(self, channel: NotificationChannel) -> None:
        code = channel.code
        if not code:
            raise ValueError("Channel must define a non-empty `code` attribute.")
        if code in self._channels:
            existing = self._channels[code]
            if existing is channel:
                return
            raise ValueError(f"Channel already registered: {code!r}")
        self._channels[code] = channel

    def get(self, code: str) -> NotificationChannel:
        try:
            return self._channels[code]
        except KeyError:
            raise KeyError(f"Unknown channel: {code!r}") from None

    def codes(self) -> list[str]:
        return sorted(self._channels)


CHANNEL_REGISTRY = ChannelRegistry()


def register_channel(channel: NotificationChannel) -> None:
    CHANNEL_REGISTRY.register(channel)


def get_channel(code: str) -> NotificationChannel:
    return CHANNEL_REGISTRY.get(code)
