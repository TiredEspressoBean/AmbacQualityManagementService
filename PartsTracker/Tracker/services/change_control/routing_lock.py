"""A step's machines and required tooling are controlled content (10b, user ruling
2026-11-16): on a step that a released process owns they change only through a process
change — a draft's own copy of the step, via the process flow editor — not by editing
the step in place. Daily machine choice (dispatch, a Gantt move, the Start Work picker)
picks within the list and never edits it, so it isn't touched here.

Timing and changeovers stay editable on released steps (also ruled): scheduling data,
not routing.

One exception, recorded rather than silent: the setup workbook may load machine
eligibility onto released steps while the tenant has started no work at all — go-live
loads the master data its approved processes need. Only the workbook can turn the
exception on (`setup_load()`), and every write made under it is marked in the audit log
("Loaded by the setup workbook").
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import ValidationError

# True only inside the master workbook's sheet run (services/core/master_workbook.py).
_setup_load: ContextVar[bool] = ContextVar('routing_setup_load', default=False)

SETUP_SOURCE = "Loaded by the setup workbook"


@contextmanager
def setup_load():
    token = _setup_load.set(True)
    try:
        yield
    finally:
        _setup_load.reset(token)


def released_owner(step):
    """A process that isn't a draft and uses this step row, or None."""
    from Tracker.models import ProcessStep, ProcessStatus
    if step is None or not getattr(step, 'pk', None):
        return None
    link = (ProcessStep.objects  # tenant-safe: FK-correlated to a scoped step
            .filter(step=step, process__archived=False)
            .exclude(process__status=ProcessStatus.DRAFT)
            .select_related('process').first())
    return link.process if link is not None else None


def orphaned_copy(step) -> bool:
    """A copy of a step that no process uses any more, though another version of it is
    — what a draft's re-fork used to leave behind (walk 2026-11-16). Its machines are
    edited on the copy the process uses, not on this one. (A standalone step, such as a
    receiving inspection plan, has no other version and isn't one.)"""
    from Tracker.models import ProcessStep, Steps
    if step is None or not getattr(step, 'pk', None):
        return False
    if ProcessStep.objects.filter(step=step).exists():  # tenant-safe: FK-correlated to a scoped step
        return False
    return (Steps.objects  # tenant-safe: .objects auto-scopes
            .filter(identity_id=step.identity_id).exclude(pk=step.pk).exists())


def tenant_has_started_work(tenant_id) -> bool:
    from Tracker.models import StepExecution
    return StepExecution.unscoped.filter(  # tenant-safe: explicit tenant filter
        tenant_id=tenant_id, started_at__isnull=False).exists()


def setup_exception_applies(step) -> bool:
    """The setup workbook is loading and the tenant hasn't started any work yet."""
    return _setup_load.get() and not tenant_has_started_work(step.tenant_id)


def assert_step_routing_editable(step, *, what: str = "machines") -> bool:
    """Refuse a change to `step`'s machines / tooling when a released process owns it.
    Returns True when it went ahead under the setup-workbook exception (the caller's
    write is then marked as loaded by the setup workbook), else False.

    Raises:
        ValidationError: the step belongs to a released process.
    """
    if orphaned_copy(step):
        raise ValidationError(
            f"This copy of {step.name} isn't used by any process — change the machines on "
            f"the copy the process uses.")
    owner = released_owner(step)
    if owner is None:
        return False
    if setup_exception_applies(step):
        return True
    raise ValidationError(
        f"{step.name} belongs to an approved process ({owner.name} v{owner.version}) — "
        f"change its {what} through a process change.")


def audit_source():
    """The audit log's additional data for a write made now: the setup workbook's mark
    under the exception, else None."""
    return {'source': SETUP_SOURCE, 'before_first_start': True} if _setup_load.get() else None
