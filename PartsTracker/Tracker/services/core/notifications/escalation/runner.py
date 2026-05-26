"""
Escalation runner — beat-task entry points + per-instance state transitions.

`tick_due()` performs the cross-tenant scan, returning the IDs of instances
whose `next_fire_at` has passed and that are still in PENDING. The Celery
beat task `tick_escalations` calls this and queues one `fire_one_escalation`
task per ID — that fan-out shape means one tenant's slow source-record
query can't block escalations in another tenant.

`fire_one(instance_id)` is the per-instance worker:

    1. Resolve the instance's tenant and enter `tenant_context(...)`.
    2. Lock the row with SELECT FOR UPDATE SKIP LOCKED — concurrent
       workers can't both fire the same step.
    3. Re-check `next_fire_at <= now` and `status == PENDING` inside the
       lock. Both can change between scan and lock acquisition.
    4. Resolve the source record via the GFK. Missing → CANCELLED.
    5. Run the ack predicate. True → ACKNOWLEDGED. (Lazy ack — covers the
       common case of an admin closing the NCR/CAPA between firings.)
    6. Run the cancel predicate. True → CANCELLED.
    7. Otherwise fire the current step's outbox rows and advance.
       Last step → EXHAUSTED after the fire.

Escalation step firings bypass the rule's `min_gap_seconds` cooldown — by
definition the user already missed the original notification; cooldown
would suppress the very thing we're trying to deliver. Channel preferences
still apply (the user's "no email at night" setting is sacred).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from Tracker.utils.tenant_context import tenant_context

from .registry import is_acknowledged, is_cancelled, is_skipped

logger = logging.getLogger(__name__)


# =============================================================================
# Beat-task entry points
# =============================================================================

def tick_due(*, now=None) -> list[str]:
    """Cross-tenant scan for pending escalation instances whose timer fired.

    Returns the list of instance IDs (as strings) to dispatch. Caller is
    expected to fan out one `fire_one_escalation.delay(id)` per ID.

    Uses `all_tenants` because the beat task runs without a tenant context;
    we re-enter `tenant_context()` inside `fire_one` once we know the
    instance's tenant.
    """
    from Tracker.models import EscalationInstance, EscalationStatus

    if now is None:
        now = timezone.now()

    return [
        str(pk)
        for pk in EscalationInstance.all_tenants.filter(  # tenant-safe: beat task scans cross-tenant; fire_one re-enters tenant_context
            status=EscalationStatus.PENDING,
            archived=False,
            next_fire_at__lte=now,
        ).values_list("id", flat=True)
    ]


def fire_one(instance_id: str) -> str | None:
    """Process one escalation instance.

    Returns the new status (or None if the instance was skipped / not found).
    The status return value is mostly for tests; production callers ignore it.
    """
    from Tracker.models import EscalationInstance, EscalationStatus, Tenant

    tenant_id = (
        EscalationInstance.all_tenants
        .filter(id=instance_id)
        .values_list("tenant_id", flat=True)
        .first()
    )
    if tenant_id is None:
        logger.warning("fire_one: instance %s not found", instance_id)
        return None

    tenant = Tenant.objects.get(id=tenant_id)

    with tenant_context(tenant):
        with transaction.atomic():
            inst = (
                EscalationInstance.objects
                .select_for_update(skip_locked=True)
                .select_related("policy__rule", "source_content_type")
                .filter(id=instance_id, status=EscalationStatus.PENDING)
                .first()
            )
            if inst is None:
                # Another worker has it, or it's already terminal.
                return None

            now = timezone.now()
            if inst.next_fire_at > now:
                # Timer was bumped between scan and lock; bail.
                return None

            return _process_instance(inst, tenant=tenant, now=now)


# =============================================================================
# Per-instance state transitions
# =============================================================================

def _process_instance(inst, *, tenant, now) -> str:
    """Inside the row lock + tenant_context: check ack/cancel, fire or advance.

    Returns the new status (string).
    """
    from Tracker.models import EscalationStatus

    rule = inst.policy.rule
    event_code = rule.event_code

    source = inst.source_record  # GenericForeignKey resolution
    if source is None:
        return _terminate(inst, EscalationStatus.CANCELLED, now=now,
                          reason="source_missing")

    if is_cancelled(event_code, source):
        return _terminate(inst, EscalationStatus.CANCELLED, now=now,
                          reason="source_cancelled")

    if is_acknowledged(event_code, source):
        return _terminate(inst, EscalationStatus.ACKNOWLEDGED, now=now,
                          reason="ack")

    steps = list(inst.policy.steps.all().order_by("order"))
    if inst.current_step >= len(steps):
        # Policy lost steps between create and fire — treat as exhausted.
        return _terminate(inst, EscalationStatus.EXHAUSTED, now=now,
                          reason="step_overflow")

    step = steps[inst.current_step]
    fired_count, outbox_ids = _fire_step(
        inst=inst, rule=rule, step=step, tenant=tenant, now=now,
    )

    inst.audit = (inst.audit or []) + [{
        "step": inst.current_step,
        "fired_at": now.isoformat(),
        "recipient_count": fired_count,
    }]

    next_step_idx = inst.current_step + 1
    if next_step_idx >= len(steps):
        inst.status = EscalationStatus.EXHAUSTED
        inst.current_step = next_step_idx
        inst.save(update_fields=["status", "current_step", "audit"])
    else:
        next_step = steps[next_step_idx]
        inst.current_step = next_step_idx
        inst.next_fire_at = now + timedelta(seconds=next_step.delay_seconds)
        inst.save(update_fields=["current_step", "next_fire_at", "audit"])

    _queue_outbox(outbox_ids)
    return inst.status


def _terminate(inst, status: str, *, now, reason: str) -> str:
    """Mark instance terminal with an audit entry. No outbox rows fire."""
    inst.status = status
    inst.audit = (inst.audit or []) + [{
        "event": "terminate",
        "reason": reason,
        "at": now.isoformat(),
    }]
    inst.save(update_fields=["status", "audit"])
    return status


# =============================================================================
# Step firing — write outbox rows for the step
# =============================================================================

def _fire_step(*, inst, rule, step, tenant, now) -> tuple[int, list[str]]:
    """Write outbox rows for one escalation step.

    Recipients = union of the rule's effective user recipients and the step's
    extra recipient_users + (recipient_groups expanded via UserRole). Channels
    come from the rule. Channel preferences (Phase 2 resolver) apply.
    Cooldown does NOT apply — by definition this is an escalation.

    Returns (rows_written, outbox_ids_to_queue).
    """
    from Tracker.models import NotificationOutbox, NotificationStatus
    from ..render import render_outbox_row
    from ..resolver import resolve_default_channels

    channels = rule.channels or []
    if not channels:
        logger.warning(
            "_fire_step: rule %s has no channels; instance %s step %s skipped",
            rule.id, inst.id, step.order,
        )
        return 0, []

    # Render with the payload snapshot taken at dispatcher time. The source
    # row alone can't reproduce derived fields like `part_number` /
    # `opened_by_name` — those come from emit-site logic that walks FKs and
    # resolves users. We capture once, reuse on every step.
    payload_dict = dict(inst.payload_snapshot or {})
    payload_dict["_escalation"] = {
        "instance_id": str(inst.id),
        "step": inst.current_step,
        "policy_id": str(inst.policy_id),
    }

    # Pass payload snapshot so rules with `recipient_strategy='from_payload'`
    # resolve correctly on step firings, not just initial dispatcher fires.
    recipients = list(rule.effective_user_recipients(payload_dict)) + list(
        _step_extra_users(step)
    )
    # Dedup users — owner_user, group expansion, and step extras may overlap.
    seen_ids: set[int] = set()
    distinct_users = []
    for u in recipients:
        if u.id in seen_ids:
            continue
        seen_ids.add(u.id)
        distinct_users.append(u)

    # Apply the registered skip_recipient predicate (e.g., drop quorum-board
    # members who already responded). Default predicate is no-op, so this is
    # safe to call unconditionally — events without a custom skip predicate
    # are unaffected.
    source = inst.source_record
    if source is not None:
        distinct_users = [
            u for u in distinct_users
            if not is_skipped(rule.event_code, source, u)
        ]

    written = 0
    outbox_ids: list[str] = []

    for user in distinct_users:
        per_channel = resolve_default_channels(user, rule.event_code)
        for channel in channels:
            if not per_channel.get(channel, False):
                continue

            row = NotificationOutbox(
                tenant=tenant,
                event_code=rule.event_code,
                rule=rule,
                user=user,
                external_contact=None,
                channel=channel,
                payload=payload_dict,
                correlation_id=inst.correlation_id or "",
                attachments=[],
                status=NotificationStatus.PENDING,
                idempotency_key=(
                    f"escalation:{inst.id}:step{step.order}:"
                    f"u{user.id}:{channel}"
                ),
                # Source GFK mirrors the originating instance so step-fired
                # rows are queryable alongside the rule-fire rows for the
                # same source (admin "all notifications about this CAPA").
                source_content_type_id=inst.source_content_type_id,
                source_object_id=inst.source_object_id,
            )
            if step.subject_override:
                # The renderer fills `rendered_subject` from the template;
                # we overwrite after to make the step subject win.
                render_outbox_row(row, payload_dict, language="en")
                row.rendered_subject = step.subject_override
            else:
                render_outbox_row(row, payload_dict, language="en")
            row.save()
            outbox_ids.append(str(row.id))
            written += 1

    return written, outbox_ids


def _step_extra_users(step):
    """Step's extra recipients: recipient_users plus recipient_groups
    expanded to their UserRole members."""
    for u in step.recipient_users.all():
        yield u
    for group in step.recipient_groups.all():
        for role in group.role_assignments.select_related("user").all():
            if role.user is not None:
                yield role.user


def _queue_outbox(outbox_ids: list[str]) -> None:
    """Queue Celery dispatch for the written outbox rows, on commit."""
    if not outbox_ids:
        return

    from ..tasks import dispatch_outbox_row

    def _do_queue(ids: list[str] = outbox_ids) -> None:
        for oid in ids:
            dispatch_outbox_row.delay(oid)

    transaction.on_commit(_do_queue)
