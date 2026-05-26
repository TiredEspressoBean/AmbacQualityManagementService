"""Celery tasks for the notification system.

Phase 1: a single `dispatch_outbox_row(outbox_id)` task that locks the
row, calls the channel adapter, and updates `status`/`sent_at`/`error`.

The dispatcher queues this task via `transaction.on_commit()` so a rollback
prevents downstream side-effects (the codebase convention; see
`tests/test_celery_dispatch.py`).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from Tracker.utils.tenant_context import tenant_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def dispatch_outbox_row(self, outbox_id: str) -> dict:
    """Lock the outbox row, deliver via its channel, update status.

    Phase 1 keeps this simple: no exponential backoff tuning, no
    transient-vs-permanent classification beyond "exception → retry".
    Refinement lands when real channels (email, in-app) ship.
    """
    from Tracker.models import NotificationOutbox, NotificationStatus
    from Tracker.services.core.notifications.channels import get_channel

    # Unscoped lookup — the row has a tenant FK we'll respect via context.
    try:
        row = NotificationOutbox.unscoped.get(id=outbox_id)
    except NotificationOutbox.DoesNotExist:
        logger.error("dispatch_outbox_row: row %s not found", outbox_id)
        return {'status': 'missing', 'outbox_id': str(outbox_id)}

    with tenant_context(row.tenant_id):
        with transaction.atomic():
            # Lock so two workers can't double-send.
            row = NotificationOutbox.unscoped.select_for_update().get(id=outbox_id)

            if row.status in (
                NotificationStatus.SENT,
                NotificationStatus.SUPPRESSED,
                NotificationStatus.CANCELLED,
            ):
                return {'status': 'already-handled', 'outbox_id': str(outbox_id)}

            try:
                channel = get_channel(row.channel)
            except KeyError as exc:
                row.status = NotificationStatus.FAILED
                row.error = f"Unknown channel: {row.channel}"
                row.save(update_fields=['status', 'error', 'updated_at'])
                logger.error("dispatch_outbox_row: %s", exc)
                return {'status': 'failed', 'outbox_id': str(outbox_id), 'reason': 'unknown-channel'}

            try:
                channel.send(row)
            except Exception as exc:  # noqa: BLE001 — channels signal retry via raise
                row.status = NotificationStatus.RETRYING
                row.retry_count = (row.retry_count or 0) + 1
                row.error = str(exc)
                row.save(update_fields=['status', 'retry_count', 'error', 'updated_at'])
                logger.warning(
                    "dispatch_outbox_row: channel %s raised; retrying (attempt %d)",
                    row.channel, row.retry_count,
                )
                raise self.retry(exc=exc) from exc

            row.status = NotificationStatus.SENT
            row.sent_at = timezone.now()
            row.error = ''
            row.save(update_fields=['status', 'sent_at', 'error', 'updated_at'])
            return {'status': 'sent', 'outbox_id': str(outbox_id)}
