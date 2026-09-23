"""Where a torn-down core goes next.

Teardown ends in exactly two places, and which one is not a separate decision — it
follows from the core's fulfilment mode:

- **repair and return** → released into rebuild **on the same work order**. The unit
  keeps one traceable thread from arrival to shipment, which is what an audit of a
  customer's own unit actually tests, and it is the shape a refurbishment order takes
  in the industry (SAP's refurbishment order, an aviation shop visit).
- **anything else** → released to inventory. The customer already has a unit from
  stock; this core is a source of parts, and its usable components become stock.

There is deliberately no "what shall we do with it" field. `Core.returns_to_customer`
already answers it, and a second field would be a place for the two to disagree.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


def _first_rebuild_step(core):
    """The earliest in-scope operation on the core's process, or None.

    Resolved from the rebuild plan rather than from process order alone: the point of
    scope resolution is that a unit visits only the operations its findings call for,
    so entering at "the step after teardown" would put it through work it does not
    need.
    """
    from Tracker.models import ProcessStep
    from Tracker.services.reman.rebuild import resolve_rebuild_plan

    plan = resolve_rebuild_plan(core)
    step_ids = {op.step_id for op in plan.operations}
    if not step_ids or core.process is None:
        return None, plan

    ordered = (
        ProcessStep.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            process=core.process, step_id__in=step_ids)
        .select_related('step')
        .order_by('order')
        .first()
    )
    return (ordered.step if ordered else None), plan


@transaction.atomic
def release_core_to_rebuild(core, user=None):
    """Send a repair-and-return core into the rebuild half of its work order.

    Raises:
        ValidationError: the core is not ready, is not a repair-and-return unit, or
            has no resolved scope to enter.
    """
    if core.status != 'DISASSEMBLED':
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a disassembled "
            "core can be released into rebuild."
        )
    if not core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} is an exchange unit: the customer already has a unit "
            "from stock, so this core is a source of parts. Release it to inventory "
            "instead."
        )

    step, plan = _first_rebuild_step(core)
    if step is None:
        raise ValidationError(
            f"No rebuild operations resolved for {core.core_number}. Author a rebuild "
            "level or repair codes for this core type first — releasing it with no "
            "scope would put it on a work order with nothing to do."
        )

    core.status = 'IN_REBUILD'
    core.step = step
    core.save(update_fields=['status', 'step', 'updated_at'])
    return core, plan


@transaction.atomic
def release_core_to_inventory(core, user=None):
    """Accept this core's usable components into stock; the core is then consumed.

    Accepting is the act that makes a recovered component available, so it is also the
    point at which it becomes stock — see `accept_component_to_inventory`. Components
    already accepted are skipped rather than erroring, so a partial release finishes
    cleanly on a second run.

    Returns `(core, accepted_parts)`.
    """
    from Tracker.services.reman.harvested_component import accept_component_to_inventory

    if core.status != 'DISASSEMBLED':
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a disassembled "
            "core can be released to inventory."
        )
    if core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} goes back to its customer, so its components are that "
            "customer's property and cannot be released into stock. Release it into "
            "rebuild instead."
        )

    accepted = []
    for component in core.harvested_components.filter(
        is_scrapped=False, component_part__isnull=True, archived=False,
    ):
        accepted.append(accept_component_to_inventory(component, user))

    core.status = 'HARVESTED'
    core.disassembly_completed_at = core.disassembly_completed_at or timezone.now()
    core.save(update_fields=['status', 'disassembly_completed_at', 'updated_at'])
    return core, accepted


@transaction.atomic
def request_authorisation(core, user=None):
    """Pause a rebuild until the customer authorises work beyond what was sold.

    Only over-and-above work needs a decision — the entry scope was already bought
    (§3.3). What findings ADDED is the question, and it is derivable: the raised codes
    minus the ones the rebuild level already included. A job whose findings raised
    nothing new needs no gate and is not sent to one.

    UQMES does not quote, approve quotes or raise purchase orders (§3.2). This records
    that the unit is waiting and what it is waiting on; the conversation happens
    elsewhere.

    Returns `(core, over_and_above)` — the codes needing a decision.
    """
    from Tracker.services.reman.scope import default_preset_for, resolve_scope
    from Tracker.services.reman.rebuild import resolve_rebuild_plan

    if core.status not in ('DISASSEMBLED', 'IN_REBUILD'):
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a unit before or "
            "in rebuild can be sent for authorisation."
        )

    plan = resolve_rebuild_plan(core)
    scope = resolve_scope(core, plan.slots)
    preset = default_preset_for(core.core_type)
    sold = {c.code for c in preset.codes.filter(archived=False)} if preset else set()
    over_and_above = [c for c in scope.raised_codes if c not in sold]

    if not over_and_above:
        raise ValidationError(
            f"Nothing on {core.core_number} goes beyond the rebuild level that was sold, "
            "so there is nothing to authorise."
        )

    core.status = 'AWAITING_AUTHORISATION'
    core.save(update_fields=['status', 'updated_at'])
    return core, over_and_above


@transaction.atomic
def record_authorisation(core, approved: bool, user=None, note: str = ''):
    """Record what the customer said. The decision was made elsewhere; this is the
    production record of it, and the thing that unblocks or ends the job.

    Approved resumes the rebuild. Declined sends the unit to DECLINED — not straight
    to returned, because it still has to physically go back, and that is the same
    dispatch step a rebuilt unit takes.
    """
    if core.status != 'AWAITING_AUTHORISATION':
        raise ValidationError(
            f"{core.core_number} is not awaiting authorisation (it is "
            f"{core.get_status_display()})."
        )

    core.status = 'IN_REBUILD' if approved else 'DECLINED'
    if note:
        core.condition_notes = f"{core.condition_notes}\n{note}".strip()
    core.save(update_fields=['status', 'condition_notes', 'updated_at'])
    return core


@transaction.atomic
def return_core_to_customer(core, user=None, reference: str = ''):
    """Dispatch a unit back to the customer it came from.

    Serves both endings of the repair-and-return path: a REBUILT unit goes back
    repaired, a DECLINED one goes back unrepaired — physically the same act, and the
    distinction is kept in the terminal status rather than in two services.

    Records that it left and how to trace it. Booking freight, rating and labelling
    belong to whatever owns shipping (§3.2).
    """
    if core.status not in ('REBUILT', 'DECLINED'):
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a rebuilt unit or "
            "one whose scope was declined can be returned."
        )
    if not core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} is an exchange unit — it has no owner to go back to."
        )

    core.status = 'RETURNED' if core.status == 'REBUILT' else 'RETURNED_UNREPAIRED'
    core.returned_at = timezone.now()
    core.returned_by = user
    core.return_reference = reference
    core.save(update_fields=[
        'status', 'returned_at', 'returned_by', 'return_reference', 'updated_at'])
    return core
