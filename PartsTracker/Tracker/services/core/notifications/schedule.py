"""
NotificationSchedule dispatcher — fires scheduled rows on cadence.

Two entry points:
  * `compute_next_fire(schedule, *, after)` — pure function returning the next
    UTC datetime when this schedule should fire. TZ-aware via zoneinfo.
  * `fire_schedule(schedule_id)` — the worker-side fire operation.
    Acquires a row lock, re-validates due, atomically marks `last_fired_at`,
    then renders content and writes outbox rows.

Concurrency model:
  * The celery-beat tick task (`Tracker.tasks.tick_notification_schedules`)
    runs every 5 min, scans all enabled schedules cross-tenant, and queues
    `fire_one_schedule.delay(id)` for any that are due.
  * `fire_one_schedule` calls into this module's `fire_schedule()`.
  * `SELECT FOR UPDATE SKIP LOCKED` on the schedule row prevents two workers
    from firing the same schedule simultaneously — a second worker that
    races sees `DoesNotExist` (the row was either locked or already fired)
    and exits cleanly.

Crash semantics:
  * `last_fired_at` is set BEFORE rendering. A crash mid-render drops that
    cycle's delivery rather than double-firing on the next tick.
    For weekly digests this is the right trade — at-most-once is preferred
    to at-least-once when retries would duplicate user-facing email.
  * Outbox writes use a fire-window-keyed `idempotency_key`, so even if the
    fire-task is retried (e.g. by celery's max_retries), the unique
    constraint on `(event_code, idempotency_key)` ensures each
    (recipient, channel) pair gets at most one outbox row per fire window.

DST policy (decided 2026-05-19):
  * Wall-clock local time. "Monday 8 AM Eastern" means 8 AM by the local
    wall clock every week, regardless of DST. UTC fire time shifts ±1h on
    the two DST transition days per year. Edge cases (2-4 AM during
    transitions) resolve via zoneinfo's default fold=0 — see compute_next_fire.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    NotificationOutbox,
    NotificationSchedule,
    NotificationStatus,
)
from Tracker.utils.tenant_context import tenant_context

from .scheduled_content import RenderedContent, get_provider

logger = logging.getLogger(__name__)


# =============================================================================
# Public API
# =============================================================================

def compute_next_fire(schedule: NotificationSchedule, *, after: datetime) -> datetime:
    """Return the next UTC datetime when this schedule should fire, strictly
    after `after`.

    `after` should already be UTC-aware. For weekly schedules, returns the
    next datetime where weekday and time-of-day match. For monthly, the
    next datetime where day-of-month and time-of-day match. Cadences are
    resolved in the schedule's local timezone (zoneinfo) and then converted
    back to UTC.

    Raises ValueError for unknown cadences.
    """
    if after.tzinfo is None:
        # Naive datetime — make it UTC. Defensive; callers should pass aware.
        after = after.replace(tzinfo=dt_timezone.utc)

    tz = ZoneInfo(schedule.resolved_timezone())
    after_local = after.astimezone(tz)
    target_time = schedule.time_of_day

    if schedule.is_weekly:
        # Anchor on after_local's date with the target time-of-day.
        candidate = datetime.combine(
            after_local.date(), target_time, tzinfo=tz,
        )
        # Walk forward to the target weekday.
        days_until = (schedule.day_of_week - candidate.weekday()) % 7
        candidate = candidate + timedelta(days=days_until)
        # If we landed at or before `after`, jump one week.
        while candidate <= after_local:
            candidate = candidate + timedelta(days=7)
        return candidate.astimezone(dt_timezone.utc)

    if schedule.is_monthly:
        target_day = schedule.day_of_month
        # Try the current month first.
        candidate = after_local.replace(
            day=target_day,
            hour=target_time.hour,
            minute=target_time.minute,
            second=target_time.second,
            microsecond=0,
        )
        # If we landed at or before `after`, advance one month at a time.
        # day_of_month is constrained to 1-28, so .replace(day=...) never
        # raises ValueError for short-month gotchas.
        while candidate <= after_local:
            if candidate.month == 12:
                candidate = candidate.replace(
                    year=candidate.year + 1, month=1,
                )
            else:
                candidate = candidate.replace(month=candidate.month + 1)
        return candidate.astimezone(dt_timezone.utc)

    raise ValueError(f"Unknown cadence: {schedule.cadence}")


def fire_schedule(schedule_id) -> None:
    """Worker entry point. Locks the schedule row, marks fired, renders,
    and writes outbox rows. Safe to call concurrently — `SKIP LOCKED`
    means a second worker that races against the same schedule will see
    `DoesNotExist` and exit without doing anything.
    """
    # Bootstrap tenant_id without a tenant context (the SecureManager would
    # otherwise refuse the query). NotificationSchedule.all_tenants bypasses
    # the auto-scope so we can read tenant_id, then enter the context.
    tenant_id = (
        NotificationSchedule.all_tenants
        .filter(pk=schedule_id, archived=False)
        .values_list("tenant_id", flat=True)
        .first()
    )
    if tenant_id is None:
        logger.info("fire_schedule: schedule %s not found / archived", schedule_id)
        return

    with tenant_context(tenant_id):
        with transaction.atomic():
            sched = _lock_and_validate_due(schedule_id)
            if sched is None:
                return
            fire_window_start = compute_next_fire(
                sched, after=sched.last_fired_at or sched.created_at,
            )
            # Atomic with the lock: write last_fired_at before rendering.
            sched.last_fired_at = timezone.now()
            sched.save(update_fields=["last_fired_at"])

        # Lock released. Outside the row lock, render content + write outbox
        # rows. A crash here drops this cycle's delivery (at-most-once).
        _render_and_deliver(sched, fire_window_start=fire_window_start)


# =============================================================================
# Internal helpers
# =============================================================================

def _lock_and_validate_due(schedule_id) -> NotificationSchedule | None:
    """Acquire SELECT FOR UPDATE on the row and confirm it's still due.

    Returns None if (a) another worker holds the lock, (b) the row was
    deleted/archived, (c) the row is disabled, or (d) the next-fire moment
    is in the future (someone else just fired it, or the beat tick was
    stale).
    """
    try:
        sched = (
            NotificationSchedule.objects
            .select_for_update(skip_locked=True)
            .get(pk=schedule_id, archived=False)
        )
    except NotificationSchedule.DoesNotExist:
        return None

    if not sched.enabled:
        return None

    anchor = sched.last_fired_at or sched.created_at
    next_fire = compute_next_fire(sched, after=anchor)
    if next_fire > timezone.now():
        # Stale beat tick or sibling worker fired it first.
        return None
    return sched


def _render_and_deliver(
    sched: NotificationSchedule, *, fire_window_start: datetime,
) -> None:
    """Resolve recipients, render content per recipient, write outbox rows."""
    provider = get_provider(sched.provider_kind)

    # Merge in the schedule's scope_customer for customer-scoped schedules
    # so providers like CustomerActiveOrders don't need admins to type a UUID.
    params: dict = dict(sched.provider_params or {})
    if sched.is_customer_scoped and sched.scope_customer_id:
        params.setdefault("customer_id", str(sched.scope_customer_id))

    try:
        validated_params = provider.validate_params(params, tenant=sched.tenant)
    except Exception:
        logger.exception(
            "fire_schedule: param validation failed for schedule=%s provider=%s",
            sched.id, sched.provider_kind,
        )
        return

    event_code = f"schedule:{sched.provider_kind}"
    fire_window_iso = fire_window_start.isoformat()

    written = 0
    for kind, recipient in _resolve_recipients(sched):
        content = _safe_build_content(
            provider, validated_params=validated_params,
            tenant=sched.tenant, recipient=recipient,
        )
        if content is None:
            continue

        for channel in (sched.channels or []):
            row = _build_outbox_row(
                sched=sched,
                kind=kind,
                recipient=recipient,
                channel=channel,
                event_code=event_code,
                fire_window_iso=fire_window_iso,
                content=content,
            )
            try:
                row.save()
                written += 1
            except Exception:
                # Most likely the idempotency-key UNIQUE constraint blocked
                # a duplicate insert (retry-after-crash, racing fires).
                # Log at info level — it means the dedup worked.
                logger.info(
                    "fire_schedule: skipped duplicate outbox row "
                    "schedule=%s recipient=%s channel=%s",
                    sched.id, recipient, channel,
                )

    logger.info(
        "fire_schedule: schedule=%s fire_window=%s wrote=%d outbox rows",
        sched.id, fire_window_iso, written,
    )


def _resolve_recipients(
    sched: NotificationSchedule,
) -> Iterable[tuple[str, object]]:
    """Yield (kind, recipient_obj) tuples for the schedule.

    Personal scope: owner_user is the only recipient (yielded as 'user').
    Tenant/customer scope: union of recipient_users + members of
    recipient_groups + recipient_external. Dedup by (kind, id) so a user
    in both `recipient_users` and a `recipient_group` only gets one row.
    """
    if sched.is_personal:
        if sched.owner_user_id:
            yield ("user", sched.owner_user)
        return

    seen: set[tuple[str, object]] = set()

    # Direct user recipients.
    for user in sched.recipient_users.all():
        key = ("user", user.id)
        if key in seen:
            continue
        seen.add(key)
        yield ("user", user)

    # Group members expanded to users via UserRole.
    for group in sched.recipient_groups.prefetch_related("role_assignments__user"):
        for role in group.role_assignments.all():
            if not role.user_id:
                continue
            key = ("user", role.user_id)
            if key in seen:
                continue
            seen.add(key)
            yield ("user", role.user)

    # External contacts (customer-scoped only — model validation prevents
    # them from being set on tenant-scoped schedules).
    if sched.is_customer_scoped:
        for contact in sched.recipient_external.filter(enabled=True):
            key = ("external", contact.id)
            if key in seen:
                continue
            seen.add(key)
            yield ("external", contact)


def _safe_build_content(
    provider, *, validated_params, tenant, recipient,
) -> RenderedContent | None:
    """Call the provider's `build_content`, logging exceptions instead of
    crashing the whole fire. A bad provider implementation for one
    recipient shouldn't poison the fire for the others."""
    try:
        return provider.build_content(
            validated_params=validated_params,
            tenant=tenant,
            recipient=recipient,
        )
    except Exception:
        logger.exception(
            "fire_schedule: provider %s build_content failed for recipient %r",
            provider.name, recipient,
        )
        return None


def _build_outbox_row(
    *,
    sched: NotificationSchedule,
    kind: str,
    recipient,
    channel: str,
    event_code: str,
    fire_window_iso: str,
    content: RenderedContent,
) -> NotificationOutbox:
    """Construct (but do not save) a NotificationOutbox row for one recipient."""
    if kind == "user":
        user = recipient
        external_contact = None
        recipient_tag = f"u{user.id}"
    else:
        user = None
        external_contact = recipient
        recipient_tag = f"e{recipient.id}"

    idempotency_key = (
        f"schedule:{sched.id}:{fire_window_iso}:{recipient_tag}:{channel}"
    )

    return NotificationOutbox(
        tenant=sched.tenant,
        event_code=event_code,
        rule=None,  # not a rule fire
        user=user,
        external_contact=external_contact,
        channel=channel,
        payload={
            "schedule_id": str(sched.id),
            "provider": sched.provider_kind,
            "fire_window_start": fire_window_iso,
        },
        correlation_id=f"schedule:{sched.id}",
        rendered_subject=content.subject,
        rendered_body_html=content.html,
        rendered_body_text=content.text,
        attachments=[],
        status=NotificationStatus.PENDING,
        idempotency_key=idempotency_key,
    )
