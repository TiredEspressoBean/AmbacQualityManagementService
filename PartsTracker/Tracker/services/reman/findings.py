"""Findings raised after teardown, and a lead's decision on each.

Teardown grades every component, and the grades resolve the rebuild: A/B go back as
they are, C is reconditioned, SCRAP is replaced — and each resolution raises the repair
codes that make up the rebuild's scope. A component is sometimes found worse later, at
the bench during rebuild: a reused nozzle that fails its spray test, a valve seat that
looked fine until it was cleaned.

That finding changes the scope, and on a repair-and-return unit scope is the customer's
bill. So an operator RECORDS it — from the DWI runtime — and a lead DECIDES it:
applying re-grades the component, and the rebuild plan re-resolves from the new grade
as it would have at teardown; dismissing leaves the grade as it was. Nothing here sends
a unit for authorisation or changes what it will cost; whether the new scope needs the
customer is the lead's call, through `release.request_authorisation`.

Kept deliberately human for now. Once there is data on how findings are decided, parts
of this may be worth automating; until then the system records and a person decides.

State lives on the component (`proposed_*`, one pending finding at a time). What was
proposed and decided is appended to `condition_notes`, and the audit log keeps every
change of grade.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

VALID_GRADES = ('A', 'B', 'C', 'SCRAP')


def _stamp(user) -> str:
    who = (user.get_full_name() or user.get_username()) if user else 'system'
    return f"{timezone.now():%Y-%m-%d} {who}"


def _clear(component):
    component.proposed_grade = ''
    component.proposed_finding = ''
    component.proposed_by = None
    component.proposed_at = None


def record_finding(component, *, grade: str, finding: str, user):
    """Propose a new grade for a component, with what was found. Changes nothing else.

    Raises:
        ValidationError: bad grade, no description, a scrapped component, or one that
            already has a finding waiting on a lead.
    """
    grade = (grade or '').upper()
    if grade not in VALID_GRADES:
        raise ValidationError(f"Grade must be one of {', '.join(VALID_GRADES)}.")
    if not (finding or '').strip():
        raise ValidationError("Say what was found — a finding with no description can't be judged.")
    if component.is_scrapped:
        raise ValidationError(f"{component} is already scrapped.")
    if component.proposed_grade:
        raise ValidationError(
            f"{component} already has a finding waiting on a lead's decision "
            f"(grade {component.proposed_grade}). It must be applied or dismissed first."
        )
    if grade == component.condition_grade:
        raise ValidationError(
            f"{component} is already grade {grade}; a finding proposes a different grade."
        )
    component.proposed_grade = grade
    component.proposed_finding = finding.strip()
    component.proposed_by = user
    component.proposed_at = timezone.now()
    component.save(update_fields=[
        'proposed_grade', 'proposed_finding', 'proposed_by', 'proposed_at', 'updated_at'])
    return component


@transaction.atomic
def apply_finding(component, *, user):
    """A lead accepts the finding: the component takes the proposed grade.

    The rebuild plan is derived from grades, so it re-resolves on its next read — the
    same path a teardown grade takes. A SCRAP grade scraps the component.
    """
    from Tracker.services.reman.harvested_component import scrap_component

    if not component.proposed_grade:
        raise ValidationError(f"{component} has no finding waiting.")
    old, new = component.condition_grade, component.proposed_grade
    note = (f"Finding applied ({_stamp(user)}): grade {old} → {new}. "
            f"{component.proposed_finding}")
    component.condition_grade = new
    component.condition_notes = f"{component.condition_notes}\n{note}".strip()
    _clear(component)
    component.save(update_fields=[
        'condition_grade', 'condition_notes',
        'proposed_grade', 'proposed_finding', 'proposed_by', 'proposed_at', 'updated_at'])
    if new == 'SCRAP' and not component.is_scrapped:
        scrap_component(component, user, reason=note)
    return component


def dismiss_finding(component, *, user, reason: str):
    """A lead turns the finding down; the grade stays. The reason is kept."""
    if not component.proposed_grade:
        raise ValidationError(f"{component} has no finding waiting.")
    if not (reason or '').strip():
        raise ValidationError("Give a reason for dismissing the finding.")
    note = (f"Finding dismissed ({_stamp(user)}): proposed grade "
            f"{component.proposed_grade} — {component.proposed_finding}. Reason: {reason.strip()}")
    component.condition_notes = f"{component.condition_notes}\n{note}".strip()
    _clear(component)
    component.save(update_fields=[
        'condition_notes', 'proposed_grade', 'proposed_finding', 'proposed_by',
        'proposed_at', 'updated_at'])
    return component


def record_findings_from_capture(step_execution, rows: list[dict], user) -> dict:
    """The DWI capture: one row per component found worse. All or nothing.

    Each row names one of THIS unit's own harvested components; the core is reached
    through the step execution's part (a core is a part).
    """
    from Tracker.models import HarvestedComponent
    from Tracker.services.reman.core_steps import core_of

    core = core_of(step_execution.part) if step_execution.part_id else None
    if core is None:
        raise ValidationError("A rebuild finding is recorded on a core — a part playing a core role.")
    ids = []
    with transaction.atomic():
        for idx, row in enumerate(rows):
            component = HarvestedComponent.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
                pk=row.get('harvested_id'), core=core).first()
            if component is None:
                raise ValidationError(f"row {idx}: not one of this unit's own components.")
            try:
                record_finding(component, grade=row.get('grade'),
                               finding=row.get('finding', ''), user=user)
            except ValidationError as exc:
                raise ValidationError(f"row {idx}: {' '.join(exc.messages)}") from exc
            ids.append(str(component.id))
    return {'harvested_component_ids': ids}
