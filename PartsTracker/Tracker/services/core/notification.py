"""
NotificationTask aggregate services.

Scheduling and post-send bookkeeping for NotificationTask, plus the
event-driven dispatcher (`notify`) that turns NotificationRule matches
into NotificationTask rows.

The interval-resolution helpers (`_get_current_interval`,
`_find_matching_tier`) stay on the model as private accessors because
they read only fields off `self` and have no callers outside this
module.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytz
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from Tracker.models import NotificationTask

logger = logging.getLogger(__name__)


def calculate_next_send(task: NotificationTask):
    """Return the next send datetime for this task.

    FIXED schedules land on the configured day_of_week/time, spaced by
    interval_weeks. DEADLINE_BASED schedules use the model's escalation
    tier lookup.

    Raises:
        ValueError: interval_type is neither FIXED nor DEADLINE_BASED.
    """
    base_time = task.last_sent_at or task.created_at

    if task.interval_type == 'FIXED':
        if task.last_sent_at:
            next_date = task.last_sent_at.date() + timedelta(weeks=task.interval_weeks)
        else:
            now = timezone.now()
            days_ahead = (task.day_of_week - now.weekday()) % 7
            if days_ahead == 0 and now.time() > task.time:
                days_ahead = 7
            next_date = (now + timedelta(days=days_ahead)).date()

        next_dt = datetime.combine(next_date, task.time)
        return timezone.make_aware(next_dt, pytz.UTC)

    if task.interval_type == 'DEADLINE_BASED':
        interval_days = task._get_current_interval()
        return base_time + timedelta(days=interval_days)

    raise ValueError(f"Unknown interval_type: {task.interval_type}")


def should_send_notification(task: NotificationTask) -> bool:
    """True iff the task is PENDING and its next_send_at has elapsed."""
    if task.status != 'PENDING':
        return False
    if timezone.now() < task.next_send_at:
        return False
    return True


def mark_notification_sent(
    task: NotificationTask,
    success: bool = True,
    sent_at=None,
) -> NotificationTask:
    """Record a send attempt. On success, schedule the next send unless
    max_attempts is reached. On failure, transition to FAILED."""
    task.attempt_count += 1
    task.last_sent_at = sent_at or task.next_send_at

    if success:
        task.status = 'SENT'
        if task.max_attempts is None or task.attempt_count < task.max_attempts:
            task.status = 'PENDING'
            task.next_send_at = calculate_next_send(task)
    else:
        task.status = 'FAILED'

    task.save()
    return task


# =========================================================================
# NotificationTask creation helpers
# =========================================================================
# Tenant is auto-injected by SecureModel.save() from the ContextVar, so
# callers don't need to pass it explicitly — they just need to be running
# inside a tenant_context (request, TenantTestCase, or tenant_context()
# wrapper in a Celery task / management command).

def _enqueue_for_approval_request(
    *,
    notification_type: str,
    recipient,
    approval_request,
) -> NotificationTask:
    """Shared core for the three approval-flow notification helpers."""
    # tenant-safe: SecureManager auto-scopes via tenant_context ContextVar
    return NotificationTask.objects.create(
        notification_type=notification_type,
        recipient=recipient,
        channel_type='EMAIL',
        interval_type='FIXED',
        related_content_type=ContentType.objects.get_for_model(approval_request.__class__),
        related_object_id=approval_request.id,
        next_send_at=timezone.now(),
    )


def enqueue_approval_notification(recipient, approval_request) -> NotificationTask:
    """Queue an APPROVAL_REQUEST email for a pending approver."""
    return _enqueue_for_approval_request(
        notification_type='APPROVAL_REQUEST',
        recipient=recipient,
        approval_request=approval_request,
    )


def enqueue_decision_notification(recipient, approval_request) -> NotificationTask:
    """Queue an APPROVAL_DECISION email for the requester."""
    return _enqueue_for_approval_request(
        notification_type='APPROVAL_DECISION',
        recipient=recipient,
        approval_request=approval_request,
    )


def enqueue_escalation_notification(recipient, approval_request) -> NotificationTask:
    """Queue an APPROVAL_ESCALATION email for the escalation target."""
    return _enqueue_for_approval_request(
        notification_type='APPROVAL_ESCALATION',
        recipient=recipient,
        approval_request=approval_request,
    )


# `enqueue_weekly_report` removed — replaced by personal NotificationSchedule
# rows created from /profile/notifications. See migration 0046_migrate_weekly_reports.

# =============================================================================
# Legacy event-driven dispatcher removed in Phase 3 slice 3.
#
# `notify()` and its NotificationRule-driven recipient resolver are gone.
# The replacement is `emit(event_code, tenant, payload)` from
# `Tracker.services.core.notifications`, which fans out via the rule-based
# Phase 3 dispatcher to `NotificationOutbox` rows.
#
# The `NotificationTask` aggregate helpers above (calculate_next_send,
# mark_notification_sent, enqueue_*) remain because the legacy approval
# and CAPA paths still create NotificationTask rows directly via tasks.py.
# Phase 5 migrates those paths to `emit()` and deletes the rest of this
# module.
# =============================================================================
