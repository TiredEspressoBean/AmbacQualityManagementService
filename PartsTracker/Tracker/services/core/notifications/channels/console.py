"""ConsoleChannel — Phase 1 dev/test channel.

Logs the rendered notification to stdout via the standard logger. No
external delivery, no failure modes. Used to validate the full
emit → dispatcher → outbox → channel flow before email/in-app land.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Tracker.models import NotificationOutbox

logger = logging.getLogger(__name__)


class ConsoleChannel:
    code = 'console'

    def send(self, outbox_row: 'NotificationOutbox') -> None:
        logger.info(
            "[notification] event=%s tenant=%s user=%s subject=%s body=%s",
            outbox_row.event_code,
            outbox_row.tenant_id,
            outbox_row.user_id,
            outbox_row.rendered_subject or '(no subject)',
            outbox_row.rendered_body_text or '(no body)',
        )

    def supports_attachments(self) -> bool:
        return False

    def max_body_length(self) -> int | None:
        return None
