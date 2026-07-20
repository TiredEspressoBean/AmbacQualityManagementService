"""Shift-note aggregate services — publish, edit (until acknowledged), retract,
acknowledge, and the operator's active feed.

The note is the record of record; the notification engine only alerts that one
was published (the shift_note.published event, wired separately). Editing locks
once the first acknowledgment lands (ShiftNote.is_locked); retract (void) stays
available at any time.
"""
from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

# Sentinel so edit_shift_note can distinguish "clear this field" (None) from
# "leave it unchanged" (not passed).
_UNSET = object()


def audience_user_ids(tenant, audience_roles):
    """Resolve a note's audience to concrete user ids (for from_payload
    notification routing). Empty audience = everyone on the floor (internal,
    active users in the tenant); otherwise users in the named tenant groups."""
    from Tracker.models import User, UserRole

    if audience_roles:
        return list(
            UserRole.objects.filter(
                group__tenant=tenant, group__name__in=audience_roles
            ).values_list("user_id", flat=True).distinct()
        )
    return list(
        User.objects.filter(tenant=tenant, is_active=True, user_type="INTERNAL")
        .values_list("id", flat=True)
    )


def publish_shift_note(
    *, author, tenant, body, audience_roles=None, work_order=None,
    priority="NORMAL", acknowledgment_required=False,
    effective_from=None, effective_until=None,
):
    """Create and publish a shift note, then emit shift_note.published so the
    audience gets a feed alert. Returns the ShiftNote."""
    from Tracker.models import ShiftNote

    body = (body or "").strip()
    if not body:
        raise ValueError("Shift note body cannot be empty.")

    audience = list(audience_roles or [])
    note = ShiftNote.objects.create(
        tenant=tenant,
        author=author,
        body=body,
        audience_roles=audience,
        work_order=work_order,
        priority=priority,
        acknowledgment_required=acknowledgment_required,
        effective_from=effective_from,
        effective_until=effective_until,
    )

    # Alert the audience via the notification feed (the note is the record;
    # the engine only points at it). Recipients resolved from the audience.
    from Tracker.services.core.notifications import emit
    from Tracker.services.mes.events import ShiftNotePublishedPayload

    author_name = ""
    if author is not None:
        author_name = author.get_full_name() or getattr(author, "email", "") or ""
    emit(
        "shift_note.published",
        tenant=tenant,
        payload=ShiftNotePublishedPayload(
            id=str(note.id),
            tenant_id=str(tenant.id),
            author_name=author_name,
            body_preview=note.body[:140],
            work_order_erp_id=(note.work_order.ERP_id if note.work_order_id else ""),
            priority=note.priority,
            recipient_user_ids=audience_user_ids(tenant, audience),
        ),
        correlation_id=f"shift_note:{note.id}",
        idempotency_key=f"shift_note.published:{note.id}",
    )
    return note


def edit_shift_note(
    note, *, body=None, audience_roles=None, work_order=_UNSET, priority=None,
    effective_from=_UNSET, effective_until=_UNSET,
):
    """Edit a not-yet-acknowledged note. Raises ValueError once it's locked.

    Only supplied fields change; pass ``work_order``/``effective_*`` explicitly
    (including ``None``) to clear them.
    """
    if note.is_locked:
        raise ValueError(
            "This note has been acknowledged and can no longer be edited; "
            "retract and repost instead."
        )
    if body is not None:
        body = body.strip()
        if not body:
            raise ValueError("Shift note body cannot be empty.")
        note.body = body
    if audience_roles is not None:
        note.audience_roles = list(audience_roles)
    if work_order is not _UNSET:
        note.work_order = work_order
    if priority is not None:
        note.priority = priority
    if effective_from is not _UNSET:
        note.effective_from = effective_from
    if effective_until is not _UNSET:
        note.effective_until = effective_until
    note.save()
    return note


def retract_shift_note(note, *, user, reason=""):
    """Retract (void) a note — available at any time, acknowledged or not."""
    note.void(user=user, reason=reason or "Retracted by author")
    return note


def acknowledge_shift_note(note, *, user):
    """Record a reader's acknowledgment. Idempotent per (note, user)."""
    from Tracker.models import ShiftNoteAck

    ack, _ = ShiftNoteAck.objects.get_or_create(
        tenant=note.tenant, note=note, user=user,
    )
    return ack


def active_shift_notes_for_user(user, *, tenant):
    """Notes the user should see now: not voided, within the effective window,
    audience match (empty audience = everyone, else the note's roles intersect
    the user's tenant groups), and not yet acknowledged by this user."""
    from Tracker.models import ShiftNote

    now = timezone.now()
    user_groups = list(user.get_tenant_group_names(tenant=tenant))

    return list(
        ShiftNote.objects.filter(is_voided=False)
        .filter(Q(effective_from__isnull=True) | Q(effective_from__lte=now))
        .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=now))
        .filter(Q(audience_roles__len=0) | Q(audience_roles__overlap=user_groups))
        .exclude(acknowledgments__user=user)
        .select_related("author", "work_order")
        .order_by("-created_at")
    )
