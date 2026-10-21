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

from Tracker.services.reman.core_part import move_core, sync_part_status

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


def _first_rebuild_step(core):
    """Where the rebuild picks up: the next step on the main line after where teardown
    left the unit. Returns `(step, plan)`; step is None when there's nowhere to go.

    Every unit walks the whole main line (services/reman/repair_routing). A unit that
    has physically been torn down stands on its last teardown step, so the rebuild
    starts at the step after it.
    """
    from Tracker.models.mes_lite import EdgeType
    from Tracker.services.reman.rebuild import resolve_rebuild_plan

    plan = resolve_rebuild_plan(core)
    part = core.part
    if part is None or part.step_id is None or not part.work_order_id:
        return None, plan
    return part._get_edge(part.step, EdgeType.DEFAULT), plan


@transaction.atomic
def release_core_to_rebuild(core, user=None):
    """Send a torn-down core into the rebuild half of its work order.

    Either mode: a repair-and-return unit is rebuilt to go back to its customer, an
    exchange unit to go into stock (the industry norm for exchange — harvesting is its
    other exit, `release_core_to_inventory`). Which parts may go into it is the rebuild
    plan's business: pooled recovered stock for exchange, only its own for
    repair-and-return.

    Raises:
        ValidationError: the core is not ready, or has no resolved scope to enter.
    """
    if core.status != 'DISASSEMBLED':
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a disassembled "
            "core can be released into rebuild."
        )
    step, plan = _first_rebuild_step(core)
    if step is None:
        where = core.part.step.name if core.part and core.part.step_id else 'teardown'
        raise ValidationError(
            f"{core.core_number} has no next step on its route after {where} — check the "
            "work order's process continues past teardown."
        )

    core.status = 'IN_REBUILD'
    core.save(update_fields=['status', 'updated_at'])
    # The unit enters rebuild at the next step on its route after teardown.
    # Position is the part's.
    move_core(core, step=step)
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
    sync_part_status(core)
    return core, accepted


@transaction.atomic
def request_authorisation(core, user=None):
    """Pause a customer's unit until they authorise repairs that aren't pre-approved.

    What needs their decision is derivable: the raised codes whose repairs this unit's
    process doesn't pre-approve, minus the rebuild level they bought and anything they
    have already approved (`repair_routing.codes_needing_approval`). A unit with none
    needs no gate and is not sent to one. An exchange unit has no customer to ask — a
    lead approves its repairs (`repair_routing.approve_repair`).

    UQMES does not quote, approve quotes or raise purchase orders (§3.2). This records
    that the unit is waiting and what it is waiting on; the conversation happens
    elsewhere.

    Returns `(core, over_and_above)` — the codes needing a decision.
    """
    from Tracker.services.reman.repair_routing import codes_needing_approval

    if core.status not in ('DISASSEMBLED', 'IN_REBUILD'):
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a unit before or "
            "in rebuild can be sent for authorisation."
        )

    if not core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} is an exchange unit — it has no customer to ask. A lead "
            "approves its repairs on the core."
        )
    over_and_above = codes_needing_approval(core)
    if not over_and_above:
        raise ValidationError(
            f"Every repair raised on {core.core_number} is pre-approved or was sold with "
            "its rebuild level, so there is nothing to authorise."
        )

    core.status = 'AWAITING_AUTHORISATION'
    core.save(update_fields=['status', 'updated_at'])
    sync_part_status(core)
    return core, over_and_above


def pending_authorisation_scope(core) -> list[dict]:
    """What the customer is being asked about: each code awaiting their answer, its
    name, and the findings behind it — so whoever records the answer sees what was
    agreed to. Empty unless the unit is AWAITING_AUTHORISATION."""
    from Tracker.models import RepairCode
    from Tracker.services.reman.repair_routing import codes_needing_approval, raised_codes

    if core.status != 'AWAITING_AUTHORISATION':
        return []
    codes = codes_needing_approval(core)
    if not codes:
        return []
    why = raised_codes(core)
    names = dict(RepairCode.objects  # tenant-safe: .objects auto-scopes
                 .filter(code__in=codes, archived=False).values_list('code', 'name'))
    return [{'code': c, 'name': names.get(c, ''), 'why': [str(w) for w in why.get(c, [])]}
            for c in codes]


@transaction.atomic
def record_authorisation(core, approved: bool, user=None, note: str = '', *,
                         contact: str = '', method: str = '', reference: str = ''):
    """Record what the customer said. The decision was made elsewhere; this is the
    production record of it, and the thing that unblocks or ends the job.

    Approved resumes the rebuild and approves the repairs that were waiting on them, so
    the unit goes down those branches. Declined sends the unit to DECLINED — not
    straight to returned, because it still has to physically go back, and that is the
    same dispatch step a rebuilt unit takes.

    `contact`, `method` and `reference` say who answered, how, and the reference to
    trace it — nobody at the customer needs a login for their answer to be on record.
    """
    from Tracker.services.reman.repair_routing import codes_needing_approval

    if core.status != 'AWAITING_AUTHORISATION':
        raise ValidationError(
            f"{core.core_number} is not awaiting authorisation (it is "
            f"{core.get_status_display()})."
        )

    codes = codes_needing_approval(core) if approved else []
    who = (user.get_full_name() or user.get_username()) if user else 'system'
    verdict = 'approved' if approved else 'declined'
    parts = [f"{timezone.now():%Y-%m-%d} {who}: customer {verdict}"]
    if codes:
        parts.append(f"repairs {', '.join(codes)}")
    if contact.strip():
        parts.append(f"answered by {contact.strip()}")
    if method.strip():
        parts.append(f"via {method.strip()}")
    if reference.strip():
        parts.append(f"ref {reference.strip()}")
    line = ' — '.join(parts) + '.'
    if (note or '').strip():
        line += f" {note.strip()}"

    core.status = 'IN_REBUILD' if approved else 'DECLINED'
    core.approved_repair_codes = sorted(set(core.approved_repair_codes or []) | set(codes))
    core.condition_notes = f"{core.condition_notes}\n{line}".strip()
    core.save(update_fields=['status', 'approved_repair_codes', 'condition_notes', 'updated_at'])
    sync_part_status(core)
    return core


# A finished unit's stage when it leaves on a shipment, keyed by the stage it left from.
# REBUILT and DECLINED are a customer's own unit going back; REBUILT_TO_STOCK is exchange
# stock going out. `undispatch_core` reads it backwards when a shipment is voided.
DISPATCH_STAGE = {
    'REBUILT': 'RETURNED',
    'DECLINED': 'RETURNED_UNREPAIRED',
    'REBUILT_TO_STOCK': 'SHIPPED',
}


def core_shippable(core) -> str | None:
    """Why this unit can't leave on a shipment now, or None when it can."""
    if core.status not in DISPATCH_STAGE:
        return f"{core.get_status_display().lower()} — not finished, so not ready to go"
    if core.status in ('REBUILT', 'DECLINED') and not core.returns_to_customer:
        return "an exchange unit — rebuild it to stock before it ships"
    return None


def dispatch_core(core, shipment, user=None):
    """Move a unit that has just gone on ``shipment`` to the stage that says it left.

    Called by `services.mes.shipping.ship`, inside its transaction, after the part has
    been put on the shipment. A customer's own unit is stamped as returned, with the
    shipment number as its reference.
    """
    if (why := core_shippable(core)) is not None:
        raise ValidationError(f"{core.core_number} can't ship: {why}.")
    fields = ['status', 'updated_at']
    if core.status in ('REBUILT', 'DECLINED'):
        core.returned_at = shipment.shipped_at
        core.returned_by = user if getattr(user, 'is_authenticated', False) else None
        core.return_reference = shipment.shipment_number
        fields += ['returned_at', 'returned_by', 'return_reference']
    core.status = DISPATCH_STAGE[core.status]
    core.save(update_fields=fields)
    sync_part_status(core)
    return core


def undispatch_core(core):
    """A shipment recorded by mistake: the unit is back at the stage it left from."""
    back = {v: k for k, v in DISPATCH_STAGE.items()}
    if core.status not in back:
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — it isn't on a shipment.")
    core.status = back[core.status]
    core.returned_at = None
    core.returned_by = None
    core.return_reference = ''
    core.save(update_fields=['status', 'returned_at', 'returned_by', 'return_reference',
                             'updated_at'])
    sync_part_status(core)
    return core


def return_core_to_customer(core, user=None, reference: str = '', *, carrier: str = '',
                            tracking_number: str = '', notes: str = ''):
    """Dispatch a unit back to the customer it came from, on a shipment of its own.

    Serves both endings of the repair-and-return path: a REBUILT unit goes back
    repaired, a DECLINED one goes back unrepaired — physically the same act, and the
    distinction is kept in the terminal status rather than in two services.

    It is a `CustomerShipment` like any other, so the packing list and CoC print for
    it; `reference` is the ERP's paperwork number, as on any shipment. Units going back
    together go from the Shipping board, which ships several at once.

    Returns the core.
    """
    from Tracker.services.mes.shipping import ship

    if core.status not in ('REBUILT', 'DECLINED'):
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a rebuilt unit or "
            "one whose scope was declined can be returned."
        )
    if not core.returns_to_customer:
        raise ValidationError(
            f"{core.core_number} is an exchange unit — it has no owner to go back to."
        )
    if core.customer_id is None:
        raise ValidationError(
            f"{core.core_number} has no customer recorded, so there is no one to return it to."
        )
    try:
        ship(tenant=core.tenant, user=user, parts=[core.part], customer=core.customer,
             carrier=carrier, tracking_number=tracking_number, reference=reference,
             notes=notes)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    core.refresh_from_db()
    return core
