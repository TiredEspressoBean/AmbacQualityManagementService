"""One serial's history: the audit trail of the part and of every record about it.

django-auditlog already records every change to every model (AUDITLOG_INCLUDE_ALL_MODELS),
but a LogEntry names one object, so the part's own page showed only the part row's changes
— a step moving, a status flipping — and none of the step executions, measurements,
quality reports, dispositions or material draws that are the part's actual history.

This gathers them on read: the part (across its versions), every Tracker row with a
foreign key to it, and every row hanging off its step executions, then returns their log
entries as one timeline. Nothing is stored or cascaded — the audit log stays the single
source, so there is never a second copy to disagree with it.

Foreign-key values inside `changes` are resolved to the related record's name, so a step
move reads "Assembly → Nitride Coating" rather than two UUIDs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from Tracker.services.core.audit_display import actor_name, display_changes, resolve_fk_names

# Rows hanging off a part's step executions (one hop further than "points at the part").
_VIA_STEP_EXECUTION = True


@dataclass(frozen=True)
class HistoryChange:
    field: str
    old: str | None
    new: str | None


@dataclass(frozen=True)
class HistoryEntry:
    id: int
    timestamp: datetime
    action: str                      # created / updated / deleted / accessed
    actor_id: int | None
    actor_name: str                  # "" when the change was made by the system
    record_type: str                 # e.g. "step execution", "quality report"
    record_id: str
    record: str                      # the record's name as logged
    changes: tuple[HistoryChange, ...]


_ACTIONS = {0: 'created', 1: 'updated', 2: 'deleted', 3: 'accessed'}




def _related_objects(part) -> list[tuple[type, list[str]]]:
    """(model, [pk, ...]) for the part's versions and every Tracker row about it."""
    from django.apps import apps
    from Tracker.models import Parts, StepExecution

    part_ids = [p.pk for p in part.get_version_history()] if hasattr(part, 'get_version_history') else [part.pk]
    found: list[tuple[type, list[str]]] = [(Parts, [str(pk) for pk in part_ids])]
    exec_ids: list = []

    for model in apps.get_app_config('Tracker').get_models():
        for f in model._meta.get_fields():
            if not (getattr(f, 'many_to_one', False) and f.concrete):
                continue
            if f.related_model is Parts and f.name != 'previous_version':
                manager = getattr(model, 'objects', model._default_manager)  # tenant-scoped
                pks = list(manager.filter(**{f'{f.name}_id__in': part_ids}).values_list('pk', flat=True))
                if pks:
                    found.append((model, [str(pk) for pk in pks]))
                    if model is StepExecution:
                        exec_ids = pks

    if _VIA_STEP_EXECUTION and exec_ids:
        for model in apps.get_app_config('Tracker').get_models():
            for f in model._meta.get_fields():
                if (getattr(f, 'many_to_one', False) and f.concrete
                        and f.related_model is StepExecution and model is not StepExecution):
                    manager = getattr(model, 'objects', model._default_manager)
                    pks = list(manager.filter(**{f'{f.name}_id__in': exec_ids}).values_list('pk', flat=True))
                    if pks:
                        found.append((model, [str(pk) for pk in pks]))
    return found


def _entries_queryset(part):
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Q
    from auditlog.models import LogEntry

    q = Q()
    for model, pks in _related_objects(part):
        q |= Q(content_type=ContentType.objects.get_for_model(model, for_concrete_model=False),
               object_pk__in=pks)
    # tenant-safe: every object_pk was reached through tenant-scoped managers from the part.
    return (LogEntry.objects.filter(q).exclude(action=3)  # reads aren't history
            .select_related('content_type', 'actor').order_by('-timestamp', '-id'))


def part_history(part, *, limit: int = 50, offset: int = 0) -> tuple[int, list[HistoryEntry]]:
    """(total, page) of the serial's history, newest first."""
    qs = _entries_queryset(part)
    total = qs.count()
    page = list(qs[offset:offset + limit])
    names = resolve_fk_names(page)

    out = []
    for e in page:
        model = e.content_type.model_class()
        changes = tuple(HistoryChange(field=c.field, old=c.old, new=c.new)
                        for c in display_changes(e, names))
        out.append(HistoryEntry(
            id=e.pk,
            timestamp=e.timestamp,
            action=_ACTIONS.get(e.action, 'changed'),
            actor_id=e.actor_id,
            actor_name=actor_name(e.actor),
            record_type=(model._meta.verbose_name if model else e.content_type.model),
            record_id=e.object_pk,
            record=e.object_repr,
            changes=changes,
        ))
    return total, out
