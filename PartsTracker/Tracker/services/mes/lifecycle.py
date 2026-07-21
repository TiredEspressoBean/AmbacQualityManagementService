"""
Step-execution lifecycle transitions — the operator work-start state machine.

Owns the waiting -> in-process transition and its gates (competence +
reassignment) in ONE place, instead of re-implementing them across the
create / claim / update viewset actions. The viewset stays thin: it handles
HTTP and the second-person supervisor password verification, then delegates
here and translates the domain errors below into responses.

Split:
  - `authorize_start(...)` — the competence RULE. Returns the authorization
    snapshot to persist on `StepExecution.training_authorization`, or raises.
    Used by `create` (pre-save) and `update` (serializer-driven save).
  - `start_execution(...)` — applies the transition (reassignment + competence,
    then assigned_to / status / snapshot / save) to an existing row. Used by
    `claim` (and any future non-serializer caller).

The `authorizer` passed in is an already-verified supervisor (a DIFFERENT user
holding the override permission — the viewset checks the password). Keeping
credential verification out of here is deliberate: the state machine has no
business touching request/auth internals.
"""
from django.utils import timezone


class StartGateError(Exception):
    """Base class for work-start gate refusals (translated to HTTP by the viewset)."""


class NotQualified(StartGateError):
    """Operator isn't qualified and no supervisor override was supplied."""

    def __init__(self, missing):
        self.missing = missing
        super().__init__("Operator is not qualified for this step.")


class NeedsReassignment(StartGateError):
    """The step is assigned to a different operator; a supervisor must reassign."""

    def __init__(self, current_operator):
        self.current_operator = current_operator
        super().__init__("Step is assigned to another operator.")


class OverrideReasonRequired(StartGateError):
    """A supervisor authorization was supplied without the required reason.

    `detail` lets callers keep a context-specific message (e.g. reassignment vs
    competence override) while sharing one error code.
    """

    def __init__(self, missing=None, detail=None):
        self.missing = missing
        self.detail = detail or "An override reason is required."
        super().__init__(self.detail)


def _person(user):
    return user.get_full_name() or user.get_username()


def authorize_start(operator, step, process, *, authorizer=None, reason=None):
    """Competence rule for starting a step.

    Returns the authorization snapshot (dict for
    `StepExecution.training_authorization`), or raises `NotQualified` /
    `OverrideReasonRequired`. When the operator isn't qualified, a valid
    `authorizer` (verified upstream) plus a `reason` records a supervisor
    override on the snapshot.
    """
    from Tracker.services.training import check_training_authorization

    result = check_training_authorization(operator, step, process=process)
    snapshot = result.to_dict()
    if result.authorized:
        return snapshot

    if authorizer is None:
        raise NotQualified(missing=snapshot['missing'])
    if not (reason or '').strip():
        raise OverrideReasonRequired(missing=snapshot['missing'])

    snapshot['override'] = {
        'worker': operator.id,
        'worker_name': _person(operator),
        'authorized_by': authorizer.id,
        'authorized_by_name': _person(authorizer),
        'reason': reason.strip(),
        'at': timezone.now().isoformat(),
    }
    return snapshot


def start_execution(execution, operator, *, authorizer=None, reason=None):
    """Apply the waiting -> in-process transition to an existing execution.

    Runs the reassignment gate (if the row is another operator's) then the
    competence gate, records both on the snapshot, sets assigned_to / status,
    and saves. Raises `StartGateError` subclasses; the row is untouched on any
    raise (all checks precede the save).
    """
    reassignment = None
    if execution.assigned_to_id and execution.assigned_to_id != operator.id:
        prior = execution.assigned_to
        if authorizer is None:
            raise NeedsReassignment(current_operator=prior)
        if not (reason or '').strip():
            raise OverrideReasonRequired(detail="A reason is required to reassign.")
        reassignment = {
            'from': prior.id,
            'from_name': _person(prior),
            'to': operator.id,
            'to_name': _person(operator),
            'authorized_by': authorizer.id,
            'authorized_by_name': _person(authorizer),
            'reason': reason.strip(),
            'at': timezone.now().isoformat(),
        }

    process = getattr(execution.subject_work_order, 'process', None)
    snapshot = authorize_start(
        operator, execution.step, process, authorizer=authorizer, reason=reason,
    )
    if reassignment is not None:
        snapshot['reassignment'] = reassignment

    execution.assigned_to = operator
    execution.status = 'IN_PROGRESS'
    execution.training_authorization = snapshot
    execution.save()
    return execution
