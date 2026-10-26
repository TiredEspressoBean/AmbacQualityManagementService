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
from dataclasses import dataclass

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


def _iso(at=None):
    """ISO-8601 string for a supplied datetime, or now. Callers that need a
    deterministic timestamp (the demo seed) pass `at`; live gates pass nothing."""
    return (at or timezone.now()).isoformat()


@dataclass(frozen=True)
class SupervisorOverride:
    """A supervisor authorizing an operator who isn't qualified to start/perform
    a step anyway. Serialized onto `StepExecution.training_authorization`; the
    competence gate trusts a snapshot that carries one.

    This is a frozen DTO (per the repo convention) precisely so the JSON shape
    lives in one place — it was previously hand-built in both `authorize_start`
    and the demo seed, and the two had already drifted (`missing` was a list of
    lists in one, a list of dicts in the other)."""
    worker_id: int
    worker_name: str
    authorized_by_id: int
    authorized_by_name: str
    reason: str
    at: str  # ISO-8601

    def to_dict(self):
        return {
            'worker': self.worker_id,
            'worker_name': self.worker_name,
            'authorized_by': self.authorized_by_id,
            'authorized_by_name': self.authorized_by_name,
            'reason': self.reason,
            'at': self.at,
        }


@dataclass(frozen=True)
class Reassignment:
    """A supervisor moving a step from one operator to another at start."""
    from_id: int
    from_name: str
    to_id: int
    to_name: str
    authorized_by_id: int
    authorized_by_name: str
    reason: str
    at: str  # ISO-8601

    def to_dict(self):
        return {
            'from': self.from_id,
            'from_name': self.from_name,
            'to': self.to_id,
            'to_name': self.to_name,
            'authorized_by': self.authorized_by_id,
            'authorized_by_name': self.authorized_by_name,
            'reason': self.reason,
            'at': self.at,
        }


def build_supervisor_override(*, worker, authorizer, reason, at=None) -> SupervisorOverride:
    return SupervisorOverride(
        worker_id=worker.id,
        worker_name=_person(worker),
        authorized_by_id=authorizer.id,
        authorized_by_name=_person(authorizer),
        reason=(reason or '').strip(),
        at=_iso(at),
    )


def build_reassignment(*, prior, operator, authorizer, reason, at=None) -> Reassignment:
    return Reassignment(
        from_id=prior.id,
        from_name=_person(prior),
        to_id=operator.id,
        to_name=_person(operator),
        authorized_by_id=authorizer.id,
        authorized_by_name=_person(authorizer),
        reason=(reason or '').strip(),
        at=_iso(at),
    )


def authorization_snapshot(result, *, override: SupervisorOverride | None = None,
                           reassignment: Reassignment | None = None) -> dict:
    """Assemble the `training_authorization` JSON from a competence result plus
    optional supervisor override / reassignment. Single source of truth for the
    snapshot shape — the start gate and the demo seed both build through here,
    so they cannot diverge."""
    snap = result.to_dict()
    if override is not None:
        snap['override'] = override.to_dict()
    if reassignment is not None:
        snap['reassignment'] = reassignment.to_dict()
    return snap


def override_summary(execution) -> dict | None:
    """The supervisor override recorded on a step execution's training snapshot, flat
    for display (who worked it, who authorized it, why, when, and the training that was
    missing), or None when the operator was qualified or the step never started."""
    snap = execution.training_authorization or {}
    override = snap.get('override')
    if not override:
        return None
    flag = override.get('flag') or {}
    return {
        'execution_id': str(execution.id),
        'visit_number': execution.visit_number or 1,
        # Flagged for QA review as given wrongly (the override itself stands).
        'flagged': bool(flag),
        'flag_reason': flag.get('reason') or '',
        'flagged_by_name': flag.get('by_name') or '',
        'flagged_at': flag.get('at'),
        'worker_name': override.get('worker_name') or '',
        'authorized_by_name': override.get('authorized_by_name') or '',
        'reason': override.get('reason') or '',
        'at': override.get('at'),
        'missing_training': [m.get('training', '') for m in snap.get('missing') or []
                             if isinstance(m, dict)],
    }


def flag_override(execution, user, reason: str):
    """An override that shouldn't have been given: flag it for QA review (user decision
    2026-10-26, Corrections #11). The override stays — the work happened under it — and
    the flag, with who raised it, why and when, rides on the same record, so the QA
    manager's overrides review shows it.

    Raises:
        ValueError: no reason, no override on this execution, or already flagged.
    """
    reason = (reason or '').strip()
    if not reason:
        raise ValueError("Say why the override is being flagged.")
    snap = dict(execution.training_authorization or {})
    override = dict(snap.get('override') or {})
    if not override:
        raise ValueError("No training override was given on this step.")
    if override.get('flag'):
        raise ValueError("This override is already flagged for QA review.")
    override['flag'] = {'by': user.id, 'by_name': _person(user), 'reason': reason, 'at': _iso()}
    snap['override'] = override
    execution.training_authorization = snap
    execution.save(update_fields=['training_authorization', 'updated_at'])
    return execution


def training_override_rows(executions, *, since=None, until=None, limit=500) -> list[dict]:
    """Supervisor training overrides across `executions` (already narrowed to what the
    reader may see), newest first, for review. `since`/`until` are ISO dates and bound
    the override's own time; the part's arrival at the step pre-filters (an override
    is given at start, which is never before arrival)."""
    from datetime import date, datetime, time, timedelta
    qs = executions.filter(training_authorization__has_key='override')
    lo = date.fromisoformat(since) if since else None
    hi = date.fromisoformat(until) if until else None
    if hi:
        qs = qs.filter(entered_at__lt=timezone.make_aware(datetime.combine(hi + timedelta(days=1), time.min)))
    rows = []
    for ex in qs.select_related('part', 'part__work_order', 'step').order_by('-entered_at')[:limit * 2]:
        summary = override_summary(ex)
        if summary is None:
            continue
        at = summary['at']
        day = datetime.fromisoformat(at).date() if at else None
        if day and ((lo and day < lo) or (hi and day > hi)):
            continue
        wo = ex.part.work_order if ex.part_id else None
        rows.append({
            'execution_id': ex.id,
            'part_id': ex.part_id,
            'part_erp_id': ex.part.ERP_id if ex.part_id else '',
            'work_order_erp_id': wo.ERP_id if wo else None,
            'step_name': ex.step.name if ex.step_id else '',
            **summary,
        })
    rows.sort(key=lambda r: r['at'] or '', reverse=True)
    return rows[:limit]


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
    if result.authorized:
        return authorization_snapshot(result)

    if authorizer is None:
        raise NotQualified(missing=result.to_dict()['missing'])
    if not (reason or '').strip():
        raise OverrideReasonRequired(missing=result.to_dict()['missing'])

    override = build_supervisor_override(worker=operator, authorizer=authorizer, reason=reason)
    return authorization_snapshot(result, override=override)


def assert_startable(part, work_order) -> None:
    """Every refusal that stands before a step is started, whoever asks — none of them
    is a start-gate refusal a supervisor can override. Both start paths call this
    (start_execution, and creating an execution IN_PROGRESS), so neither can skip one.

    - a reman unit parked on the customer's authorisation (assert_workable);
    - an expired temporary change (assert_in_date);
    - a held, cancelled or completed work order (work_order.start_refusal);
    - a QUARANTINED part: it waits for its disposition, which decides what happens to
      it (user decision 2026-10-20). Rework is routed by the disposition's split, not a
      plain start, and containment is recorded on the disposition, so neither is
      blocked by this.

    Raises:
        ValidationError: naming why.
    """
    from django.core.exceptions import ValidationError
    if part is not None:
        from Tracker.services.reman.core_steps import assert_workable
        assert_workable(part)
        from Tracker.models import PartsStatus
        from Tracker.services.qms.report_supersede import awaiting_recapture
        # A voided result is re-captured before QA closes the disposition — the one
        # piece of work a held part may take (re-walk 2026-10-22: the UI allowed it,
        # this gate refused the claim).
        if part.part_status == PartsStatus.QUARANTINED and not awaiting_recapture(part):
            from Tracker.models import QuarantineDisposition
            disp = (QuarantineDisposition.objects  # tenant-safe: FK-correlated to a scoped part
                    .filter(part=part, archived=False).exclude(current_state='CLOSED')
                    .order_by('-created_at').first())
            raise ValidationError(
                f"{part.ERP_id} is quarantined — "
                + (f"{disp.disposition_number} decides what happens to it; work it from there."
                   if disp else "it needs a disposition before any work starts."))
    if work_order is not None:
        from Tracker.services.change_control.temporary import assert_in_date
        assert_in_date(work_order)
        from Tracker.services.mes.work_order import start_refusal
        held_or_ended = start_refusal(work_order)
        if held_or_ended:
            raise ValidationError(held_or_ended)


def start_execution(execution, operator, *, authorizer=None, reason=None):
    """Apply the waiting -> in-process transition to an existing execution.

    Runs the reassignment gate (if the row is another operator's) then the
    competence gate, records both on the snapshot, sets assigned_to / status,
    and saves. Raises `StartGateError` subclasses; the row is untouched on any
    raise (all checks precede the save).
    """
    # Refusals no supervisor override reaches past (see assert_startable).
    assert_startable(execution.part if execution.part_id else None, execution.subject_work_order)

    reassignment = None
    if execution.assigned_to_id and execution.assigned_to_id != operator.id:
        prior = execution.assigned_to
        if authorizer is None:
            raise NeedsReassignment(current_operator=prior)
        if not (reason or '').strip():
            raise OverrideReasonRequired(detail="A reason is required to reassign.")
        reassignment = build_reassignment(
            prior=prior, operator=operator, authorizer=authorizer, reason=reason,
        )

    process = getattr(execution.subject_work_order, 'process', None)
    snapshot = authorize_start(
        operator, execution.step, process, authorizer=authorizer, reason=reason,
    )
    if reassignment is not None:
        snapshot['reassignment'] = reassignment.to_dict()

    execution.assigned_to = operator
    execution.status = 'IN_PROGRESS'
    execution.training_authorization = snapshot
    execution.save()
    # Work has actually begun, so the work order is no longer merely pending. No-op
    # once it is past PENDING. Distinct from release, which authorizes it (release.py).
    from Tracker.services.mes.work_order import mark_started
    mark_started(execution.subject_work_order)
    # The first step started on a RECEIVED core begins its teardown. No-op otherwise.
    if execution.part_id:
        from Tracker.services.reman.core_steps import on_step_started
        on_step_started(execution.part, operator)
    return execution
