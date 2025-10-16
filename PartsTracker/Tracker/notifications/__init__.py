"""
Notification system handlers and utilities.

This module provides the composition-based notification system:
- Context builders: Build fresh context from related objects
- Validators: Check if notification should send
- Senders: Send via different channels (email, in-app, etc.)
- Handlers: Compose the above into complete notification workflows
"""

from .handlers import (
    get_notification_handler,
    NOTIFICATION_HANDLERS,
    NotificationHandler,
)

__all__ = [
    'get_notification_handler',
    'NOTIFICATION_HANDLERS',
    'NotificationHandler',
]
