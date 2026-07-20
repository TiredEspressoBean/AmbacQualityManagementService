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


def publish_shift_note(
    *, author, tenant, body, audience_roles=None, work_order=None,
    priority="NORMAL", effective_from=None, effective_until=None,
):
    """Create and publish a shift note. Returns the ShiftNote."""
    from Tracker.models import ShiftNote

    body = (body or "").strip()
    if not body:
        raise ValueError("Shift note body cannot be empty.")

    return ShiftNote.objects.create(
        tenant=tenant,
        author=author,
        body=body,
        audience_roles=list(audience_roles or []),
        work_order=work_order,
        priority=priority,
        effective_from=effective_from,
        effective_until=effective_until,
    )


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
