"""django-auditlog changes, made readable (2026-10-08).

A LogEntry's `changes` stores raw values: a foreign key is its id ("Released By: None →
187"), a many-to-many change is a dict, an empty related manager is
"Tracker.QualityReports.None". For an audit reader those are noise — 187 is the person who
authorised production, and the record should say so.

`resolve_fk_names(entries)` names every foreign-key value on a page of entries in one
query per related model; `display_changes(entry, names)` turns one entry's changes into
(field, old, new) words. Shared by the part timeline and the audit-log API.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Bookkeeping every row carries; it says nothing about the change.
BOILERPLATE = {'id', 'created_at', 'updated_at', 'modified_at', 'tenant', 'version',
               'is_current_version', 'previous_version', 'archived'}
# Working state saved as the operator types — the finished capture is the record.
WORKING_STATE = {'capture_draft'}

_EMPTY_MANAGER = re.compile(r'^\w+\.\w+\.None$')
# A Python object repr ("<...Manager object at 0x...>") is never a value worth printing.
_OBJECT_REPR = re.compile(r'^<.* object at 0x[0-9a-fA-F]+>$')
# Django's default __str__ ("Orders object (uuid)"), with or without a version suffix.
_DEFAULT_STR = re.compile(r'^\w+ object \(')
# What to show for a record whose model never defined a readable __str__.
_LABEL_ATTRS = ('name', 'ERP_id', 'order_number', 'number', 'title', 'label')
_EMPTY = (None, 'None', '', '{}', '[]')
_M2M_VERBS = {'add': 'added', 'delete': 'removed', 'remove': 'removed', 'clear': 'cleared'}
# Names are a convenience: per related model, a cap on values resolved per page.
_MAX_RESOLVE = 500


@dataclass(frozen=True)
class DisplayChange:
    field: str
    old: str | None
    new: str | None


def actor_name(user) -> str:
    """A person's name for an audit line: full name, else email, else username."""
    if user is None:
        return ''
    return (user.get_full_name() or user.email or user.username or '').strip()


def _label(obj) -> str:
    text = str(obj)
    if not _DEFAULT_STR.match(text):
        return text
    for attr in _LABEL_ATTRS:
        value = getattr(obj, attr, None)
        if value:
            return str(value)
    return text


def _fk_model(model, field):
    if model is None:
        return None
    try:
        f = model._meta.get_field(field)
    except Exception:  # noqa: BLE001 - a field since removed from the model
        return None
    return f.related_model if getattr(f, 'many_to_one', False) else None


def _is_datetime(model, field) -> bool:
    from django.db import models
    try:
        return isinstance(model._meta.get_field(field), models.DateTimeField)
    except Exception:  # noqa: BLE001 - no model, or a field since removed
        return False


def _plant_time(value, tz) -> str:
    """A stored timestamp on the plant's clock ("Oct 27, 2026 09:03"), not raw UTC."""
    from django.utils.dateparse import parse_datetime
    try:
        dt = parse_datetime(str(value))
    except ValueError:
        dt = None
    if dt is None:
        return str(value)
    if dt.tzinfo is None:
        # auditlog writes a datetime as naive UTC.
        from datetime import timezone as dt_timezone
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt.astimezone(tz).strftime('%b %d, %Y %H:%M')


def resolve_fk_names(entries) -> dict[tuple[type, str], str]:
    """Names for the foreign-key values in these entries' changes, one query per model."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    wanted: dict[type, set[str]] = {}
    for e in entries:
        model = e.content_type.model_class()
        changes = e.changes_dict if isinstance(e.changes_dict, dict) else {}
        for field, pair in changes.items():
            related = _fk_model(model, field)
            if related is None or not isinstance(pair, (list, tuple)):
                continue
            for v in pair:
                if v not in _EMPTY:
                    wanted.setdefault(related, set()).add(str(v))
    names: dict[tuple[type, str], str] = {}
    for related, pks in wanted.items():
        manager = getattr(related, 'objects', related._default_manager)
        try:
            for obj in manager.filter(pk__in=list(pks)[:_MAX_RESOLVE]):
                names[(related, str(obj.pk))] = actor_name(obj) if related is User else _label(obj)
        except Exception:  # noqa: BLE001 - an id that can't be resolved stays an id
            continue
    return names


def display_changes(entry, names: dict) -> tuple[DisplayChange, ...]:
    """One entry's changes as words: names for ids, verbs for m2m, empties dropped."""
    model = entry.content_type.model_class()
    out = []
    changes = entry.changes_dict if isinstance(entry.changes_dict, dict) else {}
    from Tracker.services.core.audit_visibility import MASK, credential_fields
    hidden = credential_fields()
    tz = None
    for field, pair in changes.items():
        if field in BOILERPLATE or field in WORKING_STATE:
            continue
        label = field.replace('_', ' ')
        if field in hidden:
            # A credential written before they were excluded: say it changed, not to what.
            out.append(DisplayChange(field=label, old=MASK, new=MASK))
            continue
        if isinstance(pair, dict) and pair.get('type') == 'm2m':
            # auditlog's many-to-many shape — reads as "added QR-0038-003", not a dict.
            verb = _M2M_VERBS.get(pair.get('operation'), str(pair.get('operation') or 'changed'))
            objects = ', '.join(str(o) for o in (pair.get('objects') or []))
            out.append(DisplayChange(field=label, old=None, new=f"{verb} {objects}".strip()))
            continue
        old, new = (list(pair) + [None, None])[:2] if isinstance(pair, (list, tuple)) else (None, pair)
        related = _fk_model(model, field)
        if _is_datetime(model, field) and tz is None:
            from Tracker.services.core.clock import plant_tz
            tz = plant_tz()
        as_time = tz if _is_datetime(model, field) else None

        def show(v):
            # "Tracker.QualityReports.None" is auditlog's text for an empty related
            # manager on create — no value, not a value to print.
            if v in _EMPTY or _EMPTY_MANAGER.match(str(v)) or _OBJECT_REPR.match(str(v)):
                return None
            if as_time is not None:
                return _plant_time(v, as_time)
            return names.get((related, str(v)), str(v)) if related else str(v)

        o, n = show(old), show(new)
        if o != n:
            out.append(DisplayChange(field=label, old=o, new=n))
    return tuple(out)
