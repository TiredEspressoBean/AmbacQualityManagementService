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
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from Tracker.models import NotificationTask

logger = logging.getLogger(__name__)
User = get_user_model()


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


def enqueue_weekly_report(recipient, *, next_send_at, day_of_week, time_of_day) -> NotificationTask:
    """Queue a recurring WEEKLY_REPORT notification for a customer."""
    return NotificationTask.objects.create(
        notification_type='WEEKLY_REPORT',
        recipient=recipient,
        channel_type='EMAIL',
        interval_type='FIXED',
        day_of_week=day_of_week,
        time=time_of_day,
        interval_weeks=1,
        status='PENDING',
        next_send_at=next_send_at,
    )


# =========================================================================
# Event-driven dispatcher (NotificationRule)
# =========================================================================

def _resolve_recipients(rule, payload: dict):
    """Union of static users, group members, and resolver output for `rule`.

    Runs inside the current tenant context. Static recipients come from
    the rule's M2Ms; dynamic recipients from the registered resolver
    (if any). Returns a set of User instances.
    """
    from Tracker.services.core.notification_resolvers import get_resolver

    recipients: set = set(rule.recipient_users.all())

    for group in rule.recipient_groups.all():
        # TenantGroup → users via TenantGroupMembership
        members = User.objects.filter(
            tenant_group_memberships__group=group.group,
            tenant_group_memberships__tenant_id=rule.tenant_id,
        )
        recipients.update(members)

    if rule.recipient_resolver_key:
        try:
            resolver = get_resolver(rule.recipient_resolver_key)
            recipients.update(resolver(payload))
        except KeyError:
            logger.warning(
                'NotificationRule %s references unknown resolver %r; skipping',
                rule.id, rule.recipient_resolver_key,
            )
        except Exception:
            logger.exception(
                'NotificationRule %s resolver %r raised; skipping',
                rule.id, rule.recipient_resolver_key,
            )

    return recipients


def _within_cooldown(rule, recipient, now) -> bool:
    """True if a task was created for this (rule, recipient) within the
    rule's min_gap_seconds window."""
    if rule.min_gap_seconds <= 0:
        return False
    cooldown_start = now - timedelta(seconds=rule.min_gap_seconds)
    return NotificationTask.objects.filter(
        source_rule=rule,
        recipient=recipient,
        created_at__gte=cooldown_start,
    ).exists()


def notify(
    event_type: str,
    scope_obj=None,
    payload: dict | None = None,
    related_obj=None,
) -> list[NotificationTask]:
    """Fire a notification event.

    Finds every active NotificationRule for `event_type` whose scope is
    either null (tenant-wide) or matches `scope_obj`, resolves recipients,
    applies cooldowns, and creates NotificationTask rows. Returns the list
    of tasks created (empty if no rules matched or all were cooled down).

    Must be called inside a tenant context — the ContextVar provides the
    tenant scoping for the `NotificationRule.objects` query and the
    NotificationTask auto-inject. The existing Celery beat (dispatch_pending_notifications)
    picks up the created tasks on its next tick.

    Args:
        event_type: Must match a NotificationEventType value.
        scope_obj: Optional. A specific object (e.g. Step instance); rules
                   scoped at this exact object match. Rules with null scope
                   always match.
        payload: Arbitrary dict passed to the rule's resolver. Conventionally
                 includes IDs of the triggering objects (part_id,
                 step_execution_id, ...).
        related_obj: Optional. The object stashed on each NotificationTask's
                     related_object GFK for the handler/context-builder to
                     read. Defaults to scope_obj. Use a different value when
                     scope (for rule matching) and payload-target (for the
                     email body) differ — e.g. STEP_FAILURE scopes at the
                     Step but the handler wants the failed Part.
    """
    from Tracker.models import NotificationRule

    payload = payload or {}
    now = timezone.now()

    rules_qs = NotificationRule.objects.filter(
        event_type=event_type,
        is_active=True,
    )
    if scope_obj is not None:
        scope_ct = ContentType.objects.get_for_model(scope_obj.__class__)
        rules_qs = rules_qs.filter(
            Q(scope_content_type__isnull=True)
            | Q(scope_content_type=scope_ct, scope_object_id=str(scope_obj.pk))
        )
    else:
        rules_qs = rules_qs.filter(scope_content_type__isnull=True)

    # NotificationTask.related_* stashes the handler-facing object. When
    # the caller didn't pass `related_obj`, fall back to scope_obj so the
    # simple case (scope == target of the email) still works.
    target = related_obj if related_obj is not None else scope_obj
    related_ct = (
        ContentType.objects.get_for_model(target.__class__) if target else None
    )
    related_id = str(target.pk) if target else None

    created: list[NotificationTask] = []

    for rule in rules_qs.prefetch_related('recipient_users', 'recipient_groups'):
        recipients = _resolve_recipients(rule, payload)
        for recipient in recipients:
            if _within_cooldown(rule, recipient, now):
                continue
            task = NotificationTask.objects.create(
                notification_type=event_type,
                recipient=recipient,
                channel_type=rule.channel_type,
                interval_type='FIXED',
                related_content_type=related_ct,
                related_object_id=related_id,
                source_rule=rule,
                next_send_at=now,
                status='PENDING',
            )
            created.append(task)

    logger.info(
        'notify(%s): %d rule(s) evaluated, %d task(s) created',
        event_type, rules_qs.count(), len(created),
    )
    return created
