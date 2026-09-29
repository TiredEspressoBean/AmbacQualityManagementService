"""Naming a step in a spreadsheet: `Process > Step`.

A step's name alone rarely identifies it — "Assembly" and "Final inspection" appear in
most processes — so a file that names steps (a training requirement, a changeover, a
fixture's steps) writes them qualified by a process that contains them:

    Pump Build > Assembly

An import accepts that form, a step's ID, or a bare name when exactly one step has it.
An export always writes the qualified form, so what it writes imports back.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional
from uuid import UUID

from rest_framework import serializers

SEPARATOR = ' > '


def step_refs(step_ids: Iterable) -> Dict:
    """`{step_id: "Process > Step"}` for each step, in two queries.

    The process named is one containing the step — the current version by preference,
    then by name — so the reference resolves back to this step. A step in no process
    is written by its name alone.
    """
    from Tracker.models import ProcessStep, Steps

    ids = [i for i in set(step_ids) if i is not None]
    if not ids:
        return {}
    names = dict(Steps.objects.filter(id__in=ids).values_list('id', 'name'))  # tenant-safe: .objects auto-scopes
    chosen: Dict = {}
    rows = (ProcessStep.objects.filter(step_id__in=ids)  # tenant-safe: narrowed to steps read through the scoped manager above
            .order_by('-process__is_current_version', 'process__name')
            .values_list('step_id', 'process__name'))
    for step_id, process_name in rows:
        chosen.setdefault(step_id, process_name)
    return {i: (f"{chosen[i]}{SEPARATOR}{names[i]}" if i in chosen else names[i])
            for i in ids if i in names}


def step_ref(step) -> Optional[str]:
    """The `Process > Step` reference for one step (None for None)."""
    if step is None:
        return None
    return step_refs([step.pk]).get(step.pk)


def resolve_step_ref(value, what: str = 'step'):
    """The step `value` names, or a ValidationError saying why not.

    Accepts a step ID, `Process > Step`, or a bare step name that exactly one current
    step has. `what` names the column in the error.
    """
    from Tracker.models import Processes, ProcessStep, Steps

    raw = str(value).strip()
    if not raw:
        return None
    steps = Steps.objects.filter(archived=False)  # tenant-safe: .objects auto-scopes
    try:
        found = steps.filter(id=UUID(raw)).first()
        if found:
            return found
        raise serializers.ValidationError({what: f"No step has the ID {raw}."})
    except ValueError:
        pass

    if SEPARATOR in raw:
        process_name, step_name = (p.strip() for p in raw.split(SEPARATOR, 1))
        processes = Processes.objects.filter(name__iexact=process_name, archived=False)  # tenant-safe: .objects auto-scopes
        if not processes.exists():
            raise serializers.ValidationError({what: f"No process is called '{process_name}'."})
        current = processes.filter(is_current_version=True)
        if current.exists():
            processes = current
        in_process = steps.filter(
            id__in=ProcessStep.objects.filter(process__in=processes).values('step_id'),  # tenant-safe: scoped by the processes above
            name__iexact=step_name)
        found = list(in_process[:2])
        if not found:
            raise serializers.ValidationError(
                {what: f"'{process_name}' has no step called '{step_name}'."})
        if len(found) > 1:
            raise serializers.ValidationError(
                {what: f"'{process_name}' has more than one step called '{step_name}'. Use its ID."})
        return found[0]

    named = steps.filter(name__iexact=raw)
    current = named.filter(is_current_version=True)
    if current.exists():
        named = current
    found = list(named[:2])
    if not found:
        raise serializers.ValidationError({what: f"No step is called '{raw}'."})
    if len(found) > 1:
        raise serializers.ValidationError({what: (
            f"More than one step is called '{raw}'. Name it with its process — "
            f"'<process>{SEPARATOR}{raw}' — or use its ID.")})
    return found[0]
