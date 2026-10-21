"""Repairs as branches off checks (2026-10-12).

A reman route is one approved process: a main line every unit walks — nothing is
skipped — and Repair nodes hanging off its checks. A Repair node is a step carrying a
repair code (`Steps.repair_code`); a check sends a unit down it when that code is raised
for the unit, and the node's own edges bring it back into the flow. A repair that isn't
needed is simply a branch not taken, which is what the traveler then shows.

Replaces scope-as-routing (`core_steps.skip_out_of_scope`), which built a unit's route
from the operations its raised codes named and walked past everything else. An op was
skippable purely by not being mentioned, so a nozzle inspection no code happened to
name was skipped, and a decision point skipped with no result deadlocked the unit.

Who decides, by the industry's split:

- the repair is **pre-approved at this check** (`StepEdge.pre_approved`, part of the
  approved process) → it goes ahead on the inspector's finding;
- it isn't → the unit holds at the check until it's approved for this unit: by a lead
  on an exchange unit (`approve_repair`), by the customer's recorded answer on their own
  unit (`release.request_authorisation` / `record_authorisation`);
- codes in the rebuild level the customer bought count as approved — they were sold;
- a finding still waiting on a lead holds the unit at any check with Repair nodes:
  passing it down the main line would release an unreviewed finding.

Raised codes still come from `scope.resolve_scope` — scope plans the rebuild (kits,
slots, the over-and-above export); it no longer routes the unit.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from Tracker.models.mes_lite import DecisionDataMissing

# A finding's grade → the slot resolution it implies → the repair codes it raises
# (RepairCode.trigger). SCRAP is filled from stock or a purchase, decided by the plan,
# so either replacement trigger may apply.
_GRADE_TRIGGERS = {
    'A': ('REUSE',),
    'B': ('REUSE',),
    'C': ('RECONDITION',),
    'SCRAP': ('REPLACE_POOL', 'REPLACE_BUY'),
}


class RepairHold(DecisionDataMissing):
    """The unit can't leave this check until a person decides. Raised from routing, so
    advancement reports it as a blocker and the unit stays put — the safe direction."""


def _process_of(part):
    return part.work_order.process if part is not None and part.work_order_id else None


def repair_branches(process, step):
    """Edges from `step` to Repair nodes in this process version, in a stable order."""
    from Tracker.models import StepEdge
    if process is None or step is None:
        return []
    return list(
        StepEdge.objects.filter(  # tenant-safe: scoped by the process FK
            process=process, from_step=step, to_step__repair_code__isnull=False)
        .select_related('to_step__repair_code')
        .order_by('id'))


def raised_codes(core) -> dict:
    """{code: [why]} for the codes this unit's rebuild raises — its plan's findings, the
    rebuild level sold, and ALWAYS codes."""
    from Tracker.services.reman.rebuild import resolve_rebuild_plan
    from Tracker.services.reman.scope import resolve_scope

    scope = resolve_scope(core, resolve_rebuild_plan(core).slots)
    why: dict = {}
    for r in scope.expected_repairs:
        why.setdefault(r.code, list(r.because))
    for code in scope.raised_codes:
        why.setdefault(code, [])
    return why


def sold_codes(core) -> set:
    """Codes in the rebuild level sold for this core type — bought, so approved."""
    from Tracker.services.reman.scope import default_preset_for
    preset = default_preset_for(core.core_type)
    return {c.code for c in preset.codes.filter(archived=False)} if preset else set()


def is_approved(core, code: str, edge=None, *, sold=None) -> bool:
    """Whether a repair may go ahead on this unit: pre-approved where it's offered, sold
    with the rebuild level, or approved for this unit since."""
    if edge is not None and edge.pre_approved:
        return True
    if code in (core.approved_repair_codes or []):
        return True
    return code in (sold if sold is not None else sold_codes(core))


def codes_needing_approval(core) -> list[str]:
    """Raised codes whose Repair nodes are offered only without pre-approval in this
    unit's process, and that haven't been approved — what a lead approves, or what the
    customer is asked about."""
    from Tracker.models import StepEdge

    process = _process_of(core.part) if core.part_id else None
    if process is None:
        return []
    raised = raised_codes(core)
    sold = sold_codes(core)
    edges = (StepEdge.objects  # tenant-safe: scoped by the process FK
             .filter(process=process, to_step__repair_code__code__in=list(raised))
             .select_related('to_step__repair_code'))
    offered: dict = {}
    for e in edges:
        code = e.to_step.repair_code.code
        offered[code] = offered.get(code, False) or e.pre_approved
    return sorted(code for code, pre in offered.items()
                  if not pre and not is_approved(core, code, sold=sold))


def _branch_codes_for(component, step, process) -> list:
    """The repair codes a component's PROPOSED grade would raise that this check offers."""
    triggers = _GRADE_TRIGGERS.get((component.proposed_grade or '').upper(), ())
    out = []
    for e in repair_branches(process, step):
        rc = e.to_step.repair_code
        if rc.trigger in triggers and (
                rc.component_type_id is None or rc.component_type_id == component.component_type_id):
            out.append((e, rc))
    return out


def repair_route(part, step):
    """Where a unit leaving `step` goes for a repair, or None to route as the step
    normally does.

    Applies only to a core in rebuild at a step with Repair nodes in its process; for
    anything else it's a no-op, so the engine calls it unconditionally.

    Raises:
        RepairHold: a finding is waiting on a lead, or the repair this unit needs here
            isn't approved for it yet.
    """
    from Tracker.models import StepExecution
    from Tracker.services.reman.core_steps import core_of

    core = core_of(part)
    if core is None or core.status != 'IN_REBUILD':
        return None
    process = _process_of(part)
    edges = repair_branches(process, step)
    if not edges:
        return None

    pending = list(core.harvested_components.filter(
        archived=False, is_scrapped=False).exclude(proposed_grade=''))
    if pending:
        # Only a finding that needs work done to the component and has nowhere to get
        # it here is an NCR. Scrap is a lead's disposition whatever this check offers:
        # once applied, the PLAN fills the slot (recovered stock or a purchase), and
        # only a purchase raises a replace code — a pool part is fitted from the kit with
        # no repair branch. So don't promise a branch here that routing may not take.
        c = pending[0]
        grade = (c.proposed_grade or '').upper()
        if grade == 'SCRAP':
            raise RepairHold(
                f"{c} is proposed for scrap and waiting on a lead's decision. {part} stays "
                f"at {step.name} until it is signed off or dismissed; its replacement then "
                "comes from recovered stock or a purchase, per the rebuild plan.")
        if grade != 'C' or _branch_codes_for(c, step, process):
            raise RepairHold(
                f"A finding on {c} (grade {c.proposed_grade}) is waiting on a lead's "
                f"decision. {part} stays at {step.name} until it is applied or dismissed.")
        raise RepairHold(
            f"A finding on {c} (grade {c.proposed_grade}) has no planned repair at "
            f"{step.name}. Raise an NCR for it, or a lead dismisses the finding — the unit "
            "can't go on down the line with it unresolved.")

    raised = raised_codes(core)
    done = set(StepExecution.objects.filter(  # tenant-safe: scoped by the part FK
        part=part, status='COMPLETED', step__repair_code__isnull=False,
    ).values_list('step__repair_code__code', flat=True))
    sold = sold_codes(core)
    for e in edges:
        rc = e.to_step.repair_code
        if rc.code not in raised or rc.code in done:
            continue
        if is_approved(core, rc.code, e, sold=sold):
            return e.to_step
        who = ("the customer's answer — a lead sends it for authorisation and records what "
               "they say" if core.returns_to_customer else "a lead's approval on the core")
        raise RepairHold(
            f"{rc.code} — {rc.name} isn't pre-approved at {step.name}, so {part} waits "
            f"here for {who}.")
    return None


def repair_result_offered(part, step) -> bool:
    """Whether "Needs repair" is a result an inspector may record for `part` at `step`:
    a core in rebuild at a check with Repair nodes in its process. Everywhere else an
    inspection is Pass or Fail."""
    from Tracker.services.reman.core_steps import core_of
    if part is None or step is None:
        return False
    core = core_of(part)
    return (core is not None and core.status == 'IN_REBUILD'
            and bool(repair_branches(_process_of(part), step)))


def repair_result_refusal(part, step) -> str | None:
    """Why a REPAIR result can't be recorded for `part` at `step`, or None."""
    if repair_result_offered(part, step):
        return None
    return (f"Needs repair is only a result at a rebuild check with planned repairs; "
            f"{step.name if step else 'this step'} has none for {part}. Record Pass or Fail.")


NO_REPAIR_RAISED = ("Repair recorded but no repair was raised — record what needs repairing "
                    "(Report a component found worse), or change the result.")


def assert_repair_result_routed(part, step) -> None:
    """A unit inspected "Needs repair" here leaves by a repair branch or not at all.

    Called when routing found no repair to take. A REPAIR result on this visit with no
    repair raised — no finding recorded, or one dismissed — must not fall through to the
    step's own routing: on a QA_RESULT check that is the Rework branch, and the unit was
    never failed.

    Raises:
        RepairHold: this visit's inspection says Needs repair.
    """
    from Tracker.models import QualityReports, StepExecution
    ex = StepExecution.get_current_execution(part)
    if ex is None or ex.step_id != getattr(step, 'id', None):
        return
    if QualityReports.objects.filter(  # tenant-safe: scoped by the execution FK
            step_execution=ex, status='REPAIR', archived=False).exists():
        raise RepairHold(NO_REPAIR_RAISED)


def auto_apply_pre_approved(component, step_execution, user) -> bool:
    """Apply a just-recorded finding at once when this check pre-approves the repair it
    raises — the approved process is the authorisation. Returns True when applied.

    Scrap never auto-applies (an authorised disposition, even on your own stock), nor
    does a finding this check has no repair for: both stay with a lead.
    """
    from Tracker.services.reman.findings import apply_finding

    if (component.proposed_grade or '').upper() == 'SCRAP':
        return False
    process = _process_of(step_execution.part)
    for edge, rc in _branch_codes_for(component, step_execution.step, process):
        if edge.pre_approved:
            apply_finding(component, user=user, note=(
                f"Applied automatically: {rc.code} is pre-approved at "
                f"{step_execution.step.name}"))
            return True
    return False


def repair_options(part, step) -> dict:
    """What the operator runtime shows at a check with Repair nodes: each repair it
    offers, whether it's pre-approved here, whether this unit needs it, and the hold the
    unit would meet leaving now (None when it can leave). Empty when the step offers no
    repairs or the unit isn't a core in rebuild."""
    from Tracker.services.reman.core_steps import core_of

    core = core_of(part)
    edges = repair_branches(_process_of(part), step)
    if core is None or not edges:
        return {'branches': [], 'hold': None, 'core_id': None, 'customer_unit': False}
    raised = raised_codes(core) if core.status == 'IN_REBUILD' else {}
    sold = sold_codes(core)
    branches = [{
        'step_id': str(e.to_step_id),
        'step_name': e.to_step.name,
        'code': e.to_step.repair_code.code,
        'code_name': e.to_step.repair_code.name,
        'pre_approved': e.pre_approved,
        'needed': e.to_step.repair_code.code in raised,
        'approved': is_approved(core, e.to_step.repair_code.code, e, sold=sold),
    } for e in edges]
    hold = None
    try:
        repair_route(part, step)
    except RepairHold as exc:
        hold = str(exc)
    # Which unit, and whose: on an exchange unit a lead approves a repair here; on a
    # customer's own unit it goes for their authorisation instead.
    return {'branches': branches, 'hold': hold, 'core_id': str(core.id),
            'customer_unit': core.returns_to_customer}


@transaction.atomic
def approve_repair(core, code: str, *, user, note: str = ''):
    """A lead approves a repair that isn't pre-approved, on an exchange unit.

    A customer's own unit needs the customer's answer instead — a lead can't give it
    for them (`release.request_authorisation`).
    """
    if core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} is the customer's own unit — send it for their "
            "authorisation and record their answer; a lead can't approve on their behalf.")
    if code not in codes_needing_approval(core):
        raise ValidationError(f"{code} doesn't need approval on {core.core_number}.")
    who = (user.get_full_name() or user.get_username()) if user else 'system'
    line = f"{timezone.now():%Y-%m-%d} {who}: approved repair {code}."
    if (note or '').strip():
        line += f" {note.strip()}"
    core.approved_repair_codes = sorted(set(core.approved_repair_codes or []) | {code})
    core.condition_notes = f"{core.condition_notes}\n{line}".strip()
    core.save(update_fields=['approved_repair_codes', 'condition_notes', 'updated_at'])
    return core
