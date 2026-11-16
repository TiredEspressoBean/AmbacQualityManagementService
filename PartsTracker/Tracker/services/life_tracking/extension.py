"""Extending one item's life limit — a tool, a part, a core (user ruling 2026-11-11).

An extension is an approval request, the tier for accepting recorded work: whoever asks
names the new hard limit and why; someone OTHER than the requester, holding life-limit
authority (`change_lifelimitdefinition`), approves it; only then is the limit raised,
with both on the record. No supervisor override, and the requester can't approve their
own (this type isn't self-approvable). A reset after refurbishment stays direct.

The asked-for limit waits on the tracking (`pending_hard_limit`); one request is open
per tracking at a time.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

EXTENSION_TYPE = 'LIFE_LIMIT_EXTENSION'
AUTHORITY = 'change_lifelimitdefinition'


def _item(tracking):
    """The object a tracking is on (LifeTracking has content_type + object_id, no
    generic accessor)."""
    model = tracking.content_type.model_class() if tracking.content_type_id else None
    if model is None:
        return None
    manager = getattr(model, 'unscoped', None) or model._default_manager
    return manager.filter(tenant_id=tracking.tenant_id, pk=tracking.object_id).first()  # tenant-safe: explicit tenant filter


def item_page(tracking) -> str | None:
    """The page an item's life is shown on — its Life section, where an extension is
    decided: a tool's equipment page, else the part's (a core's is its part's)."""
    item = _item(tracking)
    name = type(item).__name__ if item is not None else ''
    if name == 'Equipments':
        return f"/editor/equipment/{item.pk}/edit"
    if name == 'Parts':
        return f"/details/Parts/{item.pk}"
    if name == 'Core' and getattr(item, 'part_id', None):
        return f"/details/Parts/{item.part_id}"
    return None


def item_label(tracking) -> str | None:
    """What a tracking is ON, when it isn't the page's own item: a core's limits shown
    on its part's page say they're the core's."""
    if tracking.content_type_id is None or tracking.content_type.model != 'core':
        return None
    item = _item(tracking)
    if item is not None:
        return f"Core {item.serial_number or item.core_number}"
    return None


def request_title(tracking) -> str:
    """An extension request's title: what's asked ("GW Die life: raise to 4"), or, once
    decided, the limit it was about."""
    from Tracker.services.life_tracking.life_tracking import amount
    name = tracking.definition.name
    # The request's content_object may be a copy loaded before the limit was asked for.
    tracking.refresh_from_db(fields=['pending_hard_limit'])
    if tracking.pending_hard_limit is not None:
        return f"{name}: raise to {amount(tracking.pending_hard_limit)}"
    return f"{name}: life limit extension"


def open_request(tracking):
    """The tracking's extension request awaiting a decision, or None."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import ApprovalRequest
    return (ApprovalRequest.objects  # tenant-safe: .objects auto-scopes
            .filter(content_type=ContentType.objects.get_for_model(tracking),
                    object_id=str(tracking.pk), approval_type=EXTENSION_TYPE, status='PENDING')
            .order_by('-requested_at').first())


def request_extension(tracking, user, *, hard_limit, reason: str):
    """Ask for `tracking`'s hard limit to be raised to `hard_limit`. Returns the
    ApprovalRequest. Raises ValidationError for a missing reason, a limit that doesn't
    raise it, or a request already open."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import ApprovalRequest, GroupApproverAssignment, TenantGroup
    from Tracker.services.core.approval import notify_approvers
    from Tracker.services.life_tracking.life_tracking import amount

    reason = (reason or '').strip()
    if len(reason) < 10:
        raise ValidationError("Say why it's safe to run longer (at least 10 characters).")
    try:
        new_limit = Decimal(str(hard_limit))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("The new hard limit is a number.")
    current = tracking.effective_hard_limit
    if current is not None and new_limit <= current:
        raise ValidationError(f"An extension raises the limit: it's {amount(current)} now.")
    if open_request(tracking) is not None:
        raise ValidationError("An extension for this limit is already waiting for approval.")

    tenant = tracking.tenant
    with transaction.atomic():
        approval = ApprovalRequest.objects.create(
            tenant=tenant,
            approval_number=ApprovalRequest.generate_approval_number(tenant),
            content_type=ContentType.objects.get_for_model(tracking),
            object_id=str(tracking.pk),
            approval_type=EXTENSION_TYPE,
            requested_by=user if (user and user.is_authenticated) else None,
            reason=f"{reason} (raise {tracking.definition.name} to {amount(new_limit)})",
            flow_type="ANY",
        )
        for group in (TenantGroup.objects
                      .filter(tenant=tenant, permissions__codename=AUTHORITY).distinct()):
            GroupApproverAssignment.objects.create(approval_request=approval, group=group)
        tracking.pending_hard_limit = new_limit
        tracking.save(update_fields=['pending_hard_limit', 'updated_at'])
    notify_approvers(approval)
    return approval


def decided(tracking, request, approved: bool) -> None:
    """The cascade's call when an extension request is decided: approved, the hard
    limit is raised (approved by the approver, the request keeping who asked);
    otherwise the asked-for limit is dropped and nothing changes."""
    from Tracker.services.life_tracking.life_tracking import apply_life_override
    # The request's content_object may be a copy loaded before the limit was asked
    # for (cached when the approvers were notified): read the row as it is now.
    tracking.refresh_from_db()
    pending = tracking.pending_hard_limit
    tracking.pending_hard_limit = None
    tracking.save(update_fields=['pending_hard_limit', 'updated_at'])
    if approved and pending is not None:
        from Tracker.services.life_tracking.tool_life import plan_capacity_changed
        was_blocked = tracking.is_blocked
        apply_life_override(tracking, hard_limit=pending,
                            soft_limit=tracking.soft_limit_override,  # kept as it was
                            reason=(request.reason or '')[:200],
                            approved_by=request.get_primary_approver())
        if tracking.is_blocked != was_blocked:
            plan_capacity_changed(tracking)
