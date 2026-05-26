"""Notification dispatcher receiver — Phase 3 rule-driven.

Replaces the Phase 2 `default_recipient_groups`-based stub. On each
`notification_event`:

    1. Load matching `NotificationRule`s across three scopes:
       - tenant rules (always considered)
       - customer rules where `scope_customer_id == payload.customer_id`
         (only when the payload carries a customer_id)
       - personal rules for the tenant + event_code
    2. Evaluate each rule's compiled CEL condition against the payload
       (with `owner_user` context for personal rules).
    3. Union recipients across matched rules:
       - tenant/customer rules: recipient_users + groups expanded to users
         + (customer only) recipient_external contacts
       - personal rules: owner_user only
    4. For each (recipient, channel) pair: check the per-rule
       `min_gap_seconds` cooldown against `NotificationOutbox` history.
       Intersect with the user's channel preferences (Phase 2 resolver).
    5. Render and write outbox rows, queue Celery dispatch on commit.

Outbox rows reference both `rule` (the firing rule) and exactly one of
`user` or `external_contact` (mutually exclusive).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.dispatch import receiver
from django.utils import timezone

from Tracker.models import SCOPE_CUSTOMER, SCOPE_PERSONAL, SCOPE_TENANT

from .emit import notification_event
from .escalation import get_ack_registration

logger = logging.getLogger(__name__)


@receiver(notification_event)
def on_notification_event(
    sender,  # EventType
    *,
    event_code: str,
    tenant,
    payload,
    payload_dict: dict,
    correlation_id: str,
    idempotency_key: str,
    **kwargs,
) -> None:
    """Fan out a single event to its rule × recipient × channel matrix."""
    from Tracker.models import NotificationOutbox, NotificationStatus, NotificationRule
    from .cel import compile_condition, evaluate
    from .render import render_outbox_row
    from .resolver import resolve_default_channels
    from .tasks import dispatch_outbox_row

    if tenant is None:
        logger.info("dispatcher: event %s has no tenant; skipping", event_code)
        return

    # ---- Step 1: load candidate rules across the three scopes -----------
    customer_id = payload_dict.get("customer_id")
    scope_q = Q(scope_kind="tenant") | Q(scope_kind="personal")
    if customer_id:
        scope_q |= Q(scope_kind="customer", scope_customer_id=customer_id)

    # Order candidates personal → customer → tenant so the dedup logic
    # below (first-rule-per-(recipient,channel)-wins) gives personal
    # subscriptions precedence over admin-authored tenant rules. The user's
    # own "ping me when X" beats the admin's broad fan-out when both target
    # the same channel — the user gets one notification, attributed to their
    # personal rule.
    scope_order = Case(
        When(scope_kind=SCOPE_PERSONAL, then=Value(0)),
        When(scope_kind=SCOPE_CUSTOMER, then=Value(1)),
        When(scope_kind=SCOPE_TENANT, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )
    candidates = list(
        NotificationRule.objects
        .filter(tenant=tenant, event_code=event_code, enabled=True, archived=False)
        .filter(scope_q)
        .annotate(_scope_order=scope_order)
        .order_by("_scope_order", "priority", "created_at")
        .prefetch_related(
            "recipient_users",
            "recipient_groups__role_assignments__user",
            "recipient_external",
            "escalation_policy__steps",
        )
        .select_related("owner_user", "scope_customer", "escalation_policy")
    )

    if not candidates:
        logger.info(
            "dispatcher: no rules matched %s in tenant %s; skipping",
            event_code, tenant.id,
        )
        return

    # ---- Step 2: CEL evaluation -----------------------------------------
    matched: list = []
    for rule in candidates:
        owner_ctx = (
            {"id": rule.owner_user_id} if rule.is_personal and rule.owner_user_id else {}
        )
        try:
            program = compile_condition(rule.conditions_source)
        except Exception:
            logger.exception(
                "dispatcher: rule %s has invalid CEL; skipping",
                rule.id,
            )
            continue
        if not evaluate(program, payload_dict, owner_user=owner_ctx):
            continue
        matched.append(rule)

    if not matched:
        logger.info(
            "dispatcher: %d candidate rules for %s, none passed CEL",
            len(candidates), event_code,
        )
        return

    attachments = list(payload_dict.get("attachments") or [])
    now = timezone.now()

    # Resolve the source GFK once per event. The ack registry already knows
    # which model the event's source records are (used for escalation), so we
    # reuse that mapping here. Events without an ack registration get null
    # source — those tend not to need PII redaction anyway.
    source_ct_id, source_oid = _resolve_source_gfk(event_code, payload_dict)

    # Dedup pairs across rules so two rules targeting the same recipient
    # via the same channel produce one outbox row, not two.
    written_pairs: set = set()
    rows_to_queue: list[str] = []

    for rule in matched:
        rule_channels = rule.channels or list(sender.default_channels)

        # ---- User recipients --------------------------------------------
        # Pass payload_dict so rules with `recipient_strategy='from_payload'`
        # or 'union' can resolve domain-driven recipients. Static-strategy
        # rules ignore the payload and behave as before.
        resolved_users = rule.effective_user_recipients(payload_dict)
        if (
            rule.recipient_strategy in ("from_payload", "union")
            and not resolved_users
            and not rule.recipient_external.exists()
        ):
            logger.warning(
                "dispatcher: rule %s uses recipient_strategy=%s but payload "
                "produced no recipients (event=%s, payload keys=%s)",
                rule.id, rule.recipient_strategy, event_code,
                list(payload_dict.keys()),
            )
        for user in resolved_users:
            # Apply the user's channel preferences once per user; this is
            # the Phase 2 cascade (user → role → tenant → registry).
            per_channel = resolve_default_channels(user, event_code)

            for channel in rule_channels:
                pair = ("user", user.id, channel)
                if pair in written_pairs:
                    continue
                if not per_channel.get(channel, False):
                    continue
                if _within_cooldown(
                    rule=rule, user_id=user.id, external_id=None,
                    channel=channel, now=now,
                ):
                    continue

                row = _build_user_row(
                    tenant=tenant,
                    rule=rule,
                    user=user,
                    channel=channel,
                    event_code=event_code,
                    payload_dict=payload_dict,
                    attachments=attachments,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    source_ct_id=source_ct_id,
                    source_oid=source_oid,
                )
                render_outbox_row(row, payload_dict, language="en")
                row.save()
                rows_to_queue.append(str(row.id))
                written_pairs.add(pair)

        # ---- External contact recipients (customer-scoped rules only) ----
        for contact in rule.effective_external_recipients(payload_dict):
            for channel in rule_channels:
                pair = ("contact", contact.id, channel)
                if pair in written_pairs:
                    continue
                if _within_cooldown(
                    rule=rule, user_id=None, external_id=contact.id,
                    channel=channel, now=now,
                ):
                    continue

                row = _build_external_row(
                    tenant=tenant,
                    rule=rule,
                    contact=contact,
                    channel=channel,
                    event_code=event_code,
                    payload_dict=payload_dict,
                    attachments=attachments,
                    correlation_id=correlation_id,
                    idempotency_key=idempotency_key,
                    source_ct_id=source_ct_id,
                    source_oid=source_oid,
                )
                render_outbox_row(row, payload_dict, language="en")
                row.save()
                rows_to_queue.append(str(row.id))
                written_pairs.add(pair)

        # ---- Escalation instance (Phase 4) ------------------------------
        # Create one EscalationInstance per (policy, source_record). Keyed
        # off the rule match, NOT the outbox row count — even if cooldown
        # swallowed every recipient at first-fire, the escalation chain
        # should still run on schedule. get_or_create gives first-fire-wins
        # semantics; re-firing the same rule against the same source record
        # is a no-op for the existing instance.
        _ensure_escalation_instance(
            rule=rule,
            tenant=tenant,
            event_code=event_code,
            payload_dict=payload_dict,
            correlation_id=correlation_id,
            now=now,
        )

    if not rows_to_queue:
        return

    # Defer Celery dispatch until commit so a rolled-back originating
    # transaction doesn't fire notifications.
    def _queue_all(ids: list[str] = rows_to_queue) -> None:
        for outbox_id in ids:
            dispatch_outbox_row.delay(outbox_id)

    transaction.on_commit(_queue_all)


# =============================================================================
# Cooldown lookup
# =============================================================================

def _within_cooldown(
    *,
    rule,
    user_id,
    external_id,
    channel: str,
    now,
) -> bool:
    """Was a notification from this rule to this recipient fired recently?

    Uses the `(rule, user, created_at)` index on `NotificationOutbox`.
    The external-contact variant uses a (rule, external_contact, created_at)
    scan; not indexed (lower volume).

    A `min_gap_seconds` of 0 disables cooldown entirely.
    """
    if rule.min_gap_seconds <= 0:
        return False

    from Tracker.models import NotificationOutbox

    cutoff = now - timedelta(seconds=rule.min_gap_seconds)
    qs = NotificationOutbox.objects.filter(  # tenant-safe: dispatcher runs in emit-site tenant_context
        rule=rule,
        channel=channel,
        created_at__gte=cutoff,
    )
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    elif external_id is not None:
        qs = qs.filter(external_contact_id=external_id)
    else:
        return False
    return qs.exists()


# =============================================================================
# Outbox row builders
# =============================================================================

def _build_user_row(*, tenant, rule, user, channel, event_code, payload_dict,
                    attachments, correlation_id, idempotency_key,
                    source_ct_id=None, source_oid=""):
    from Tracker.models import NotificationOutbox, NotificationStatus

    return NotificationOutbox(
        tenant=tenant,
        event_code=event_code,
        rule=rule,
        user=user,
        external_contact=None,
        channel=channel,
        payload=payload_dict,
        correlation_id=correlation_id,
        attachments=attachments,
        status=NotificationStatus.PENDING,
        idempotency_key=f"{idempotency_key}:{rule.id}:u{user.id}:{channel}",
        source_content_type_id=source_ct_id,
        source_object_id=source_oid,
    )


def _build_external_row(*, tenant, rule, contact, channel, event_code, payload_dict,
                        attachments, correlation_id, idempotency_key,
                        source_ct_id=None, source_oid=""):
    from Tracker.models import NotificationOutbox, NotificationStatus

    return NotificationOutbox(
        tenant=tenant,
        event_code=event_code,
        rule=rule,
        user=None,
        external_contact=contact,
        channel=channel,
        payload=payload_dict,
        correlation_id=correlation_id,
        attachments=attachments,
        status=NotificationStatus.PENDING,
        idempotency_key=f"{idempotency_key}:{rule.id}:e{contact.id}:{channel}",
        source_content_type_id=source_ct_id,
        source_object_id=source_oid,
    )


def _resolve_source_gfk(event_code: str, payload_dict: dict) -> tuple[int | None, str]:
    """Look up the source ContentType + object id for an event.

    Uses the ack registry's `source_model` binding — events that declare
    an ack predicate also declare which model their source records belong
    to. Events without an ack registration get `(None, '')`, leaving the
    GFK null on the outbox row.

    Returns: `(content_type_id, source_object_id_str)`.
    """
    reg = get_ack_registration(event_code)
    if reg is None:
        return None, ""

    source_oid = payload_dict.get("id")
    if not source_oid:
        return None, ""

    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(reg.source_model)
    return ct.id, str(source_oid)


# =============================================================================
# Escalation hook (Phase 4)
# =============================================================================

def _ensure_escalation_instance(
    *,
    rule,
    tenant,
    event_code: str,
    payload_dict: dict,
    correlation_id: str,
    now,
) -> None:
    """Create the EscalationInstance for a rule fire, if applicable.

    Preconditions for creating an instance:
    - The rule has an enabled `EscalationPolicy` with at least one step.
    - The event has an ack registration (else there's no way to ever stop
      the chain — better to no-op than to escalate forever).
    - The payload carries an `id` field (source record PK by convention).

    First-fire-wins: re-firing the same rule against the same source record
    leaves the existing instance untouched (no timer reset).
    """
    policy = getattr(rule, "escalation_policy", None)
    if policy is None or not policy.enabled:
        return

    steps = list(policy.steps.all())
    if not steps:
        return
    first_step = min(steps, key=lambda s: s.order)

    reg = get_ack_registration(event_code)
    if reg is None:
        logger.info(
            "dispatcher: rule %s has escalation but event %s has no ack "
            "registration; skipping instance creation",
            rule.id, event_code,
        )
        return

    source_oid = payload_dict.get("id")
    if not source_oid:
        logger.warning(
            "dispatcher: rule %s escalation requires payload.id; "
            "event=%s payload keys=%s",
            rule.id, event_code, list(payload_dict.keys()),
        )
        return

    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import EscalationInstance, EscalationStatus

    source_ct = ContentType.objects.get_for_model(reg.source_model)
    next_fire_at = now + timedelta(seconds=first_step.delay_seconds)

    # tenant-safe: dispatcher receiver runs in the emit-site's tenant_context;
    # the get_or_create's tenant in defaults pins ownership explicitly.
    _, created = EscalationInstance.objects.get_or_create(
        policy=policy,
        source_content_type=source_ct,
        source_object_id=str(source_oid),
        defaults={
            "tenant": tenant,
            "current_step": 0,
            "next_fire_at": next_fire_at,
            "status": EscalationStatus.PENDING,
            "correlation_id": correlation_id or "",
            "payload_snapshot": payload_dict,
        },
    )
    if created:
        logger.info(
            "dispatcher: created EscalationInstance for rule=%s source=%s:%s",
            rule.id, source_ct.id, source_oid,
        )
