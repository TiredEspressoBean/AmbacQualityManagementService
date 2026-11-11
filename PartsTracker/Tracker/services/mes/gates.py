"""
Production gates: one decision function per stage, called by every enforcement point.

A gate is a check that refuses or holds shop-floor work (user decisions 2026-11-11).
Two stages:

- START — "is the process fit to run?": checked before work starts, on every start
  path (Start Work / claim, creating a visit IN_PROGRESS, PATCHing one to IN_PROGRESS,
  starting a load). `decide_start` is the one function they call.
- RELEASE — "is this work acceptable?": checked when the part leaves the step
  (`release_blockers`, behind `Steps.can_advance_from_step`).

Every refusal is a `Blocker` with a stable `GateCode` — overrides key on the code,
never on the message text — plus who clears it and what the floor is waiting on.

Escapes are tiered (user decision): a supervisor override for workflow rules
(training, revisit, reassignment), a bypass request approved by someone else for the
release gates a StepOverride may clear, and none at all for the floor gates whose
owner acts upstream (a disposition, change control, the customer, the order's hold).

Every passed or escaped gate is written to the decision log (`GateDecision`): one row
per visit per gate per stage. Refusals that are later cleared are not kept.

Decisions read recorded facts. Which gates apply to a step is the engineer's choice,
recorded as the step's StepRequirement rows (services/mes/step_gates.py): a gate with
no row doesn't apply to that step.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

if TYPE_CHECKING:
    from Tracker.models import Parts, StepExecution, Steps, WorkOrder


class Stage(StrEnum):
    START = 'START'
    RELEASE = 'RELEASE'


class Escape(StrEnum):
    NONE = 'NONE'                          # its owner acts upstream; nobody on the floor clears it
    SUPERVISOR_OVERRIDE = 'SUPERVISOR_OVERRIDE'
    BYPASS_REQUEST = 'BYPASS_REQUEST'      # a StepOverride someone else approves
    LIMIT_EXTENSION = 'LIMIT_EXTENSION'    # life limits: an approved extension


class GateCode(StrEnum):
    # --- START: no escape on the floor
    CORE_AWAITING_AUTHORISATION = 'core_awaiting_authorisation'
    DEVIATION_EXPIRED = 'deviation_expired'
    WORK_ORDER_NOT_WORKABLE = 'work_order_not_workable'
    PART_QUARANTINED = 'part_quarantined'
    # --- START: supervisor override (the codes the API already answers with)
    REVISIT_RULE = 'revisit_rule'
    ASSIGNED_TO_OTHER = 'assigned_to_other'
    TRAINING = 'training_not_authorized'
    # --- RELEASE
    QUARANTINE_HOLD = 'quarantine_hold'
    LIFE_LIMIT = 'life_limit'
    QA_SIGNOFF = 'qa_signoff'
    FIRST_PIECE = 'first_piece'
    SAMPLING_REQUIRED = 'sampling_required'
    SAMPLING_FAILED = 'sampling_failed'
    MEASUREMENT_OUT_OF_SPEC = 'measurement_out_of_spec'
    SUBSTEPS_INCOMPLETE = 'substeps_incomplete'
    QUALIFIED_OPERATOR = 'qualified_operator'


@dataclass(frozen=True)
class GateSpec:
    code: GateCode
    stage: Stage
    escape: Escape
    clears: str        # who clears it
    waiting_on: str    # what the floor waits for, for the operator screen


_SPECS = [
    GateSpec(GateCode.CORE_AWAITING_AUTHORISATION, Stage.START, Escape.NONE,
             "Reman lead", "the customer's authorisation"),
    GateSpec(GateCode.DEVIATION_EXPIRED, Stage.START, Escape.NONE,
             "Change control", "change control to extend the deviation or return the order to baseline"),
    GateSpec(GateCode.WORK_ORDER_NOT_WORKABLE, Stage.START, Escape.NONE,
             "Production manager", "the work order's hold to clear"),
    GateSpec(GateCode.PART_QUARANTINED, Stage.START, Escape.NONE,
             "QA", "the part's disposition"),
    GateSpec(GateCode.REVISIT_RULE, Stage.START, Escape.SUPERVISOR_OVERRIDE,
             "Supervisor", "a supervisor to authorise the repeat visit"),
    GateSpec(GateCode.ASSIGNED_TO_OTHER, Stage.START, Escape.SUPERVISOR_OVERRIDE,
             "Supervisor", "a supervisor to reassign the step"),
    GateSpec(GateCode.TRAINING, Stage.START, Escape.SUPERVISOR_OVERRIDE,
             "Supervisor", "a supervisor to authorise an operator without the training"),
    GateSpec(GateCode.QUARANTINE_HOLD, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "the part's disposition"),
    GateSpec(GateCode.LIFE_LIMIT, Stage.RELEASE, Escape.LIMIT_EXTENSION,
             "Engineering", "an approved life-limit extension"),
    GateSpec(GateCode.QA_SIGNOFF, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "QA's sign-off"),
    GateSpec(GateCode.FIRST_PIECE, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "the first piece to be bought off"),
    GateSpec(GateCode.SAMPLING_REQUIRED, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "the sampling inspection"),
    GateSpec(GateCode.SAMPLING_FAILED, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "a disposition of the failed sample"),
    GateSpec(GateCode.MEASUREMENT_OUT_OF_SPEC, Stage.RELEASE, Escape.BYPASS_REQUEST,
             "QA", "the out-of-spec reading to be dealt with"),
    GateSpec(GateCode.SUBSTEPS_INCOMPLETE, Stage.RELEASE, Escape.NONE,
             "Operator", "the work instruction's required substeps"),
    GateSpec(GateCode.QUALIFIED_OPERATOR, Stage.RELEASE, Escape.NONE,
             "Supervisor", "a qualified operator on record"),
]
SPECS: dict[GateCode, GateSpec] = {s.code: s for s in _SPECS}


@dataclass(frozen=True)
class Blocker:
    code: GateCode
    message: str

    @property
    def spec(self) -> GateSpec:
        return SPECS[self.code]

    def to_dict(self) -> dict:
        return {'code': str(self.code), 'message': self.message, 'stage': str(self.spec.stage),
                'escape': str(self.spec.escape), 'clears': self.spec.clears,
                'waiting_on': self.spec.waiting_on}


class StartRefused(ValidationError):
    """A start refused by a gate nobody on the floor can override. A ValidationError so
    every existing caller and the API handler treat it as the refusal it always was; it
    carries the structured blockers for the response."""

    def __init__(self, blockers: list[Blocker]):
        self.blockers = list(blockers)
        super().__init__([b.message for b in self.blockers])


# ============================================================================
# START
# ============================================================================

@dataclass(frozen=True)
class StartContext:
    part: Optional['Parts']
    step: 'Steps'
    work_order: Optional['WorkOrder']
    operator: object
    visit_number: int = 1
    execution: Optional['StepExecution'] = None

    @property
    def process(self):
        return getattr(self.work_order, 'process', None)


def context_for_execution(execution, operator) -> StartContext:
    return StartContext(
        part=execution.part if execution.part_id else None,
        step=execution.step,
        work_order=execution.subject_work_order,
        operator=operator,
        visit_number=execution.visit_number or 1,
        execution=execution,
    )


def _refusal_text(exc: ValidationError) -> str:
    return '; '.join(exc.messages)


def _carries(step, code: GateCode) -> bool:
    """Does the step carry this gate? With no step to ask (a caller checking the floor
    alone), every gate applies."""
    return step is None or step.has_gate(str(code))


def floor_blockers(ctx: StartContext) -> list[Blocker]:
    """The start gates nobody on the floor can override that the step carries, every
    one that refuses.

    - a reman unit parked on the customer's authorisation;
    - a QUARANTINED part: its disposition decides what happens to it (user decision
      2026-10-20) — except a voided result being re-captured, the one piece of work a
      held part may take;
    - an expired temporary change (deviation);
    - a held, cancelled or completed work order.
    """
    out: list[Blocker] = []
    part, wo, step = ctx.part, ctx.work_order, ctx.step
    if part is not None and _carries(step, GateCode.CORE_AWAITING_AUTHORISATION):
        from Tracker.services.reman.core_steps import assert_workable
        try:
            assert_workable(part)
        except ValidationError as exc:
            out.append(Blocker(GateCode.CORE_AWAITING_AUTHORISATION, _refusal_text(exc)))
    if part is not None and _carries(step, GateCode.PART_QUARANTINED):
        from Tracker.models import PartsStatus
        from Tracker.services.qms.report_supersede import awaiting_recapture
        if part.part_status == PartsStatus.QUARANTINED and not awaiting_recapture(part):
            from Tracker.models import QuarantineDisposition
            disp = (QuarantineDisposition.objects  # tenant-safe: FK-correlated to a scoped part
                    .filter(part=part, archived=False).exclude(current_state='CLOSED')
                    .order_by('-created_at').first())
            out.append(Blocker(GateCode.PART_QUARANTINED, (
                f"{part.ERP_id} is quarantined — "
                + (f"{disp.disposition_number} decides what happens to it; work it from there."
                   if disp else "it needs a disposition before any work starts."))))
    if wo is not None and _carries(step, GateCode.DEVIATION_EXPIRED):
        from Tracker.services.change_control.temporary import refusal as deviation_refusal
        expired = deviation_refusal(wo)
        if expired:
            out.append(Blocker(GateCode.DEVIATION_EXPIRED, expired))
    if wo is not None and _carries(step, GateCode.WORK_ORDER_NOT_WORKABLE):
        from Tracker.services.mes.work_order import start_refusal
        held_or_ended = start_refusal(wo)
        if held_or_ended:
            out.append(Blocker(GateCode.WORK_ORDER_NOT_WORKABLE, held_or_ended))
    return out


def _floor_applies(ctx: StartContext) -> list[GateCode]:
    codes = []
    if ctx.part is not None:
        codes += [GateCode.CORE_AWAITING_AUTHORISATION, GateCode.PART_QUARANTINED]
    if ctx.work_order is not None:
        codes += [GateCode.DEVIATION_EXPIRED, GateCode.WORK_ORDER_NOT_WORKABLE]
    return [c for c in codes if _carries(ctx.step, c)]


@dataclass
class Outcome:
    code: GateCode
    outcome: str                      # GateDecision.Outcome value
    by: object = None
    reason: str = ''
    reference: str = ''


@dataclass
class StartDecision:
    """What a start was cleared on: the training snapshot to keep on the visit, and
    the outcome of each gate that applied (for the decision log)."""
    snapshot: dict
    outcomes: list[Outcome] = field(default_factory=list)


def decide_start(ctx: StartContext, *, authorizer=None, reason=None) -> StartDecision:
    """The one start decision. Raises `StartRefused` for a floor refusal, or a
    `lifecycle.StartGateError` for a supervisor-overridable one (the caller asks for a
    supervisor and calls again with `authorizer`). Writes nothing.

    Reassignment applies only to an existing visit held by someone else."""
    from Tracker.services.mes.lifecycle import (
        NeedsReassignment, OverrideReasonRequired, authorize_start, build_reassignment,
        check_revisit_rule,
    )

    refused = floor_blockers(ctx)
    if refused:
        raise StartRefused(refused)
    outcomes = [Outcome(c, 'PASSED') for c in _floor_applies(ctx)]

    revisit = check_revisit_rule(ctx.part, ctx.step, ctx.operator, visit_number=ctx.visit_number,
                                 authorizer=authorizer, reason=reason)
    if ctx.part is not None and ctx.visit_number > 1 and ctx.step.has_gate(str(GateCode.REVISIT_RULE)):
        outcomes.append(Outcome(GateCode.REVISIT_RULE, 'OVERRIDDEN', authorizer, reason or '')
                        if revisit is not None else Outcome(GateCode.REVISIT_RULE, 'PASSED'))

    reassignment = None
    ex = ctx.execution
    if ex is not None and ex.assigned_to_id and ex.assigned_to_id != ctx.operator.id:
        if authorizer is None:
            raise NeedsReassignment(current_operator=ex.assigned_to)
        if not (reason or '').strip():
            raise OverrideReasonRequired(detail="A reason is required to reassign.")
        reassignment = build_reassignment(prior=ex.assigned_to, operator=ctx.operator,
                                          authorizer=authorizer, reason=reason)
        outcomes.append(Outcome(GateCode.ASSIGNED_TO_OTHER, 'OVERRIDDEN', authorizer, reason or ''))

    if ctx.step.has_gate(str(GateCode.TRAINING)):
        snapshot = authorize_start(ctx.operator, ctx.step, ctx.process, authorizer=authorizer,
                                   reason=reason)
        outcomes.append(Outcome(GateCode.TRAINING, 'OVERRIDDEN', authorizer, reason or '')
                        if snapshot.get('override') else Outcome(GateCode.TRAINING, 'PASSED'))
    else:
        # The step doesn't carry the training gate: the start is recorded as gated (the
        # snapshot the advancement backstop trusts), with nothing checked.
        snapshot = {'authorized': True, 'missing': [], 'verified': [], 'training_gate': False}
    if reassignment is not None:
        snapshot['reassignment'] = reassignment.to_dict()
    if revisit is not None:
        snapshot['revisit_override'] = revisit
    return StartDecision(snapshot=snapshot, outcomes=outcomes)


def record_start(execution, decision: StartDecision, *, by=None, at=None) -> None:
    """Log the start's gate outcomes against the visit."""
    _record(execution, Stage.START, decision.outcomes, by=by, at=at)


# ============================================================================
# RELEASE
# ============================================================================

def release_blockers(step: 'Steps', step_execution, work_order) -> list[Blocker]:
    """Everything that holds `step_execution`'s part at `step`, before any bypass."""
    from Tracker.models import PartsStatus, QualityReports

    out: list[Blocker] = []
    part = step_execution.part  # None for a core's teardown execution.

    # Quarantine (Parts only — cores carry no quarantine state).
    if part is not None and part.part_status == PartsStatus.QUARANTINED and step.block_on_quarantine:
        out.append(Blocker(GateCode.QUARANTINE_HOLD, "Part is quarantined and step blocks on quarantine"))

    # Life limit. Read the live `is_blocked`, not the possibly stale cached status, so
    # calendar (shelf-life) expiries are caught. Released by an approved limit
    # extension, not a bypass.
    if part is not None and step.has_gate(str(GateCode.LIFE_LIMIT)):
        for lt in _life_trackings(part):
            if lt.is_blocked:
                out.append(Blocker(GateCode.LIFE_LIMIT, f"Life limit exceeded: {lt.definition.name}"))

    # QA sign-off. A first-piece release covers its own context only.
    if step.requires_qa_signoff:
        from Tracker.services.qms.fpi_scope import qa_released
        if not qa_released(step, work_order, part=part):
            out.append(Blocker(GateCode.QA_SIGNOFF, "QA signoff required but not received"))

    # First piece (Parts only).
    if part is not None and step.requires_first_piece_inspection:
        fpi_status = step.get_fpi_status(work_order, part=part)
        if fpi_status['status'] not in ('PASSED', 'WAIVED', 'NOT_REQUIRED'):
            ctx = fpi_status.get('context_label')
            out.append(Blocker(GateCode.FIRST_PIECE,
                               f"First Piece Inspection required{f' for {ctx}' if ctx else ''}: "
                               f"{fpi_status['status']}"))

    # Sampling (Parts only).
    if part is not None and step.sampling_required and part.requires_sampling:
        report = QualityReports.objects.filter(part=part, step=step, archived=False).first()  # tenant-safe: FK-correlated to a scoped part
        if not report:
            out.append(Blocker(GateCode.SAMPLING_REQUIRED, "Sampling inspection required but not completed"))
        elif report.status == 'FAIL':
            out.append(Blocker(GateCode.SAMPLING_FAILED, "Sampling inspection failed - disposition required"))

    # An out-of-spec reading at this visit, when the step blocks on one.
    if step.block_on_measurement_failure:
        from Tracker.models import StepExecutionMeasurement
        if StepExecutionMeasurement.objects.filter(step_execution=step_execution,  # tenant-safe: FK-correlated to a scoped visit
                                                   is_within_spec=False).exists():
            out.append(Blocker(GateCode.MEASUREMENT_OUT_OF_SPEC,
                               "One or more measurements are out of specification"))

    # The work instruction's required substeps (Parts only).
    if part is not None and step.has_gate(str(GateCode.SUBSTEPS_INCOMPLETE)):
        from Tracker.services.dwi.advancement_gate import substep_completion_blockers
        out += [Blocker(GateCode.SUBSTEPS_INCOMPLETE, m)
                for m in substep_completion_blockers(step, step_execution, work_order)]

    # Competence backstop: a visit that never passed a start gate has no training
    # snapshot; it doesn't leave a step that needs training unless the recorded
    # operator is qualified. Visits gated at start are trusted (a cert lapsing
    # mid-step doesn't re-block them).
    if _needs_operator_backstop(step, step_execution, work_order):
        from Tracker.services.training import check_training_authorization
        worker = step_execution.assigned_to
        if worker is None:
            out.append(Blocker(GateCode.QUALIFIED_OPERATOR,
                               "No qualified operator recorded for a step that requires training"))
        elif not check_training_authorization(worker, step, process=getattr(work_order, 'process', None)).authorized:
            who = worker.get_full_name() or worker.get_username()
            out.append(Blocker(GateCode.QUALIFIED_OPERATOR, f"Operator {who} is not qualified for this step"))
    return out


def _life_trackings(part):
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import LifeTracking
    return (LifeTracking.objects  # tenant-safe: generic FK to a scoped part
            .filter(content_type=ContentType.objects.get_for_model(part), object_id=part.pk)
            .select_related('definition'))


def _needs_operator_backstop(step, step_execution, work_order) -> bool:
    if step_execution.training_authorization is not None:
        return False
    if not step.has_gate(str(GateCode.QUALIFIED_OPERATOR)):
        return False
    from Tracker.services.training import get_required_training
    return bool(get_required_training(step, getattr(work_order, 'process', None)))


# Release gates a StepOverride clears, and the block type it names.
BYPASS_BLOCK_TYPE = {
    GateCode.QUARANTINE_HOLD: 'QUARANTINE',
    GateCode.QA_SIGNOFF: 'QA_SIGNOFF',
    GateCode.FIRST_PIECE: 'FPI_REQUIRED',
    GateCode.SAMPLING_REQUIRED: 'SAMPLING_REQUIRED',
    GateCode.SAMPLING_FAILED: 'SAMPLING_REQUIRED',
    GateCode.MEASUREMENT_OUT_OF_SPEC: 'MEASUREMENT_FAILED',
}


def _release_applies(step, step_execution, work_order) -> list[GateCode]:
    """The release gates that applied to this visit — for the decision log. Cheap:
    read from the step's configuration and the part's own facts, not re-checked."""
    from Tracker.models import Substep
    part = step_execution.part
    codes = []
    if part is not None and step.block_on_quarantine:
        codes.append(GateCode.QUARANTINE_HOLD)
    if part is not None and step.has_gate(str(GateCode.LIFE_LIMIT)) and _life_trackings(part).exists():
        codes.append(GateCode.LIFE_LIMIT)
    if step.requires_qa_signoff:
        codes.append(GateCode.QA_SIGNOFF)
    if part is not None and step.requires_first_piece_inspection:
        codes.append(GateCode.FIRST_PIECE)
    if part is not None and step.sampling_required and part.requires_sampling:
        codes.append(GateCode.SAMPLING_REQUIRED)
    if step.block_on_measurement_failure:
        codes.append(GateCode.MEASUREMENT_OUT_OF_SPEC)
    if (part is not None and step.has_gate(str(GateCode.SUBSTEPS_INCOMPLETE))
            and Substep.objects.filter(step=step, archived=False).exists()):  # tenant-safe: FK-correlated to a scoped step
        codes.append(GateCode.SUBSTEPS_INCOMPLETE)
    if _needs_operator_backstop(step, step_execution, work_order):
        codes.append(GateCode.QUALIFIED_OPERATOR)
    return codes


def record_release(step_execution, work_order, *, by=None, at=None) -> None:
    """Log a release that went through: each gate that applied passed, or was cleared
    by the approved bypass that names it."""
    from Tracker.services.mes.step_override import live_bypasses
    step = step_execution.step
    if step is None:
        return
    bypasses = {o.block_type: o for o in live_bypasses(step_execution).select_related('approved_by')}
    outcomes = []
    for code in _release_applies(step, step_execution, work_order):
        override = bypasses.get(BYPASS_BLOCK_TYPE.get(code))
        if override is not None:
            outcomes.append(Outcome(code, 'BYPASSED', override.approved_by, override.reason or '',
                                    str(override.id)))
        else:
            outcomes.append(Outcome(code, 'PASSED'))
    _record(step_execution, Stage.RELEASE, outcomes, by=by, at=at)


# ============================================================================
# Decision log
# ============================================================================

def _record(step_execution, stage: Stage, outcomes: list[Outcome], *, by=None, at=None) -> None:
    from Tracker.models import GateDecision
    if step_execution is None or step_execution.pk is None:
        return
    at = at or timezone.now()
    for o in outcomes:
        GateDecision.objects.update_or_create(  # tenant-safe: keyed to a scoped visit
            step_execution=step_execution, gate=str(o.code), stage=str(stage),
            defaults={'tenant_id': step_execution.tenant_id, 'outcome': o.outcome,
                      'decided_by': o.by if o.by is not None else by, 'decided_at': at,
                      'reason': o.reason or '', 'reference': o.reference or ''})
