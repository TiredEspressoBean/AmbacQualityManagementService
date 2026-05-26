"""InAppChannel — Phase 2 in-app delivery.

The outbox row IS the in-app notification — the frontend inbox queries
`NotificationOutbox` rows directly via the API where `channel='in_app'`
and reads `read_at`/`archived_at`. So this channel's `send()` is a
no-op marker that simply confirms the row is ready to be displayed.

Keeping the same `NotificationChannel` interface as email/console
means the dispatcher pipeline doesn't special-case in-app delivery —
all channels go through `dispatch_outbox_row` and end up status='sent'.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Tracker.models import NotificationOutbox

logger = logging.getLogger(__name__)


class InAppChannel:
    code = 'in_app'

    def send(self, outbox_row: 'NotificationOutbox') -> None:
        # No wire delivery — the row is the notification. Frontend reads
        # it via the inbox endpoint. Future Phase 4 work may post a
        # browser push notification here if PushChannel doesn't exist yet.
        logger.debug(
            'in_app channel: outbox %s ready for inbox display (user=%s)',
            outbox_row.id, outbox_row.user_id,
        )

    def supports_attachments(self) -> bool:
        # In-app surface doesn't render PDFs inline. The action URL on
        # the row links to the source record where attachments live.
        return False

    def max_body_length(self) -> int | None:
        return None
