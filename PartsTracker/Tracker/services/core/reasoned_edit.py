"""An edit that corrects a record, with a reason kept beside each changed field.

Corrections (user decisions 2026-10-26) all need a reason, kept with both states in
history. The audit log keeps old and new values but not why; this writes a RecordEdit
per changed field with the reason, for the records whose plain edit is the correction
(clock times, downtime). A serializer calls `require_reason` before saving and
`record` after.
"""
from __future__ import annotations


def changed_fields(instance, validated_data: dict, fields) -> dict:
    """{field: (old, new)} for each of `fields` the edit changes."""
    out = {}
    for f in fields:
        if f in validated_data and validated_data[f] != getattr(instance, f):
            out[f] = (getattr(instance, f), validated_data[f])
    return out


def require_reason(changes: dict, reason: str | None) -> str:
    """The reason, stripped; ValueError when something changes and none was given."""
    reason = (reason or '').strip()
    if changes and not reason:
        raise ValueError("Say why it's being corrected.")
    return reason


def record(instance, changes: dict, reason: str, user) -> None:
    """One RecordEdit per changed field, with the reason."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    if not changes:
        return
    ct = ContentType.objects.get_for_model(type(instance))
    for field, (old, new) in changes.items():
        RecordEdit.objects.create(
            tenant=instance.tenant, content_type=ct, object_id=instance.id, field_name=field,
            old_value='' if old is None else str(getattr(old, 'pk', old)),
            new_value='' if new is None else str(getattr(new, 'pk', new)),
            reason=reason, edited_by=user)
