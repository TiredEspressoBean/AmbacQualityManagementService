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

from dataclasses import dataclass, field

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


def pending_authorisation_scope(core, *, asking: bool = False) -> list[dict]:
    """What the customer is being asked about: each code awaiting their answer, its
    name, and the findings behind it — so whoever records the answer sees what was
    agreed to. Empty unless the unit is AWAITING_AUTHORISATION.

    `asking=True`: what a request for authorisation WOULD send, for a unit in rebuild —
    so whoever sends it sees what they're asking for first."""
    from Tracker.models import RepairCode
    from Tracker.services.reman.repair_routing import codes_needing_approval, raised_codes

    if core.status != ('IN_REBUILD' if asking else 'AWAITING_AUTHORISATION'):
        return []
    codes = codes_needing_approval(core)
    if not codes:
        return []
    why = raised_codes(core)
    rows = (RepairCode.objects  # tenant-safe: .objects auto-scopes
            .filter(code__in=codes, archived=False, is_current_version=True)
            .values_list('code', 'name', 'required'))
    names = {c: n for c, n, _ in rows}
    # The shop's setting on each code; a code with no current row reads as required,
    # the safe default.
    required_by = {c: r for c, _, r in rows}
    return [{'code': c, 'name': names.get(c, ''), 'why': [str(w) for w in why.get(c, [])],
             'required': required_by.get(c, True)}
            for c in codes]


@dataclass(frozen=True)
class ScopePart:
    """A part one over-and-above repair needs: the slot it fills and why."""
    component: str
    part_number: str
    position: str
    finding: str
    source: str          # 'Replacement part' | 'From recovered stock'


@dataclass(frozen=True)
class ScopeLine:
    """One repair the customer is asked to authorise: the work, its parts, and the
    findings behind it."""
    code: str
    name: str
    work: list = field(default_factory=list)      # the repair step(s) the code sends it to
    findings: list = field(default_factory=list)
    parts: list = field(default_factory=list)     # [ScopePart]
    # The shop's setting: declining a required repair returns the unit unrepaired.
    required: bool = True


@dataclass(frozen=True)
class OverAndAboveScope:
    """What goes to the customer with an authorisation request. Scope only: UQMES
    does not price, quote or raise orders (§3.2) — pricing happens in the system that
    owns it."""
    awaiting: bool                 # already sent and waiting, or what a request would send
    entry_scope: str | None        # the rebuild level they bought
    lines: list = field(default_factory=list)   # [ScopeLine]


_PART_SOURCE = {'REPLACE_BUY': 'Replacement part', 'REPLACE_POOL': 'From recovered stock'}


def over_and_above_scope(core) -> OverAndAboveScope | None:
    """The over-and-above scope document's content: each repair awaiting the customer's
    answer (or that a request would ask about, for a unit in rebuild), the work it is,
    the parts it needs, and the findings behind it. None when there is nothing to ask.

    Built on `pending_authorisation_scope` — which codes are asked is its answer — and
    the rebuild plan, whose slots and expected repairs say what each code means for
    this unit. Writes nothing."""
    from Tracker.models import PartTypes, RepairCode
    from Tracker.services.reman.rebuild import resolve_rebuild_plan
    from Tracker.services.reman.scope import raised_by

    awaiting = core.status == 'AWAITING_AUTHORISATION'
    asked = pending_authorisation_scope(core, asking=not awaiting)
    if not asked:
        return None
    plan = resolve_rebuild_plan(core)
    codes = {c.code: c for c in RepairCode.objects.filter(  # tenant-safe: .objects auto-scopes
        code__in=[a['code'] for a in asked], is_current_version=True, archived=False)}
    replaced = [s for s in plan.slots if s.resolution in _PART_SOURCE]
    numbers = dict(PartTypes.objects.filter(  # tenant-safe: .objects auto-scopes
        id__in={s.component_type_id for s in replaced}).values_list('id', 'ERP_id'))
    numbers = {str(k): v or '' for k, v in numbers.items()}

    lines = []
    for a in asked:
        code = codes.get(a['code'])
        work = []
        for r in plan.expected_repairs:
            if r.code == a['code'] and r.step_name not in work:
                work.append(r.step_name)
        parts = [ScopePart(component=s.component_type_name,
                           part_number=numbers.get(s.component_type_id, ''),
                           position=s.position or '', finding=s.finding,
                           source=_PART_SOURCE[s.resolution])
                 for s in replaced if code is not None and raised_by(code, s)]
        lines.append(ScopeLine(code=a['code'], name=a['name'], work=work,
                               findings=list(a['why']), parts=parts,
                               required=a.get('required', True)))
    return OverAndAboveScope(awaiting=awaiting, entry_scope=plan.entry_scope, lines=lines)


def _split_answer(core, waiting: list, declined_codes) -> tuple[list, list, list]:
    """A per-item answer against what is waiting: `(approved, declined, required_declined)`.

    A code named as declined that isn't waiting on the customer is refused, so a stale
    screen can't record an answer to a question nobody asked. Whether a declined repair
    ends the unit is the shop's setting on the code (`RepairCode.required`)."""
    from Tracker.models import RepairCode
    declined = sorted(set(declined_codes or ()))
    stray = [c for c in declined if c not in waiting]
    if stray:
        raise ValidationError(
            f"{', '.join(stray)} {'is' if len(stray) == 1 else 'are'} not waiting on the "
            f"customer for {core.core_number}.")
    required = set(RepairCode.objects  # tenant-safe: .objects auto-scopes
                   .filter(code__in=declined, archived=False, is_current_version=True,
                           required=True).values_list('code', flat=True))
    # A code with no current row reads as required, the safe default.
    known = set(RepairCode.objects  # tenant-safe: .objects auto-scopes
                .filter(code__in=declined, archived=False, is_current_version=True)
                .values_list('code', flat=True))
    required |= set(declined) - known
    return ([c for c in waiting if c not in declined], declined, sorted(required))


@transaction.atomic
def record_authorisation(core, approved: bool, user=None, note: str = '', *,
                         contact: str = '', method: str = '', reference: str = '',
                         declined_codes=()):
    """Record what the customer said. The decision was made elsewhere; this is the
    production record of it, and the thing that unblocks or ends the job.

    Approved resumes the rebuild and approves the repairs that were waiting on them, so
    the unit goes down those branches. Declined sends the unit to DECLINED — not
    straight to returned, because it still has to physically go back, and that is the
    same dispatch step a rebuilt unit takes.

    `declined_codes`: an approval that declines some repairs. A declined OPTIONAL repair
    is recorded and the unit is rebuilt without it; declining a REQUIRED one (the
    shop's setting on the code) declines the unit, since it can't be rebuilt without it.

    `contact`, `method` and `reference` say who answered, how, and the reference to
    trace it — nobody at the customer needs a login for their answer to be on record.
    """
    from Tracker.services.reman.repair_routing import codes_needing_approval

    if core.status != 'AWAITING_AUTHORISATION':
        raise ValidationError(
            f"{core.core_number} is not awaiting authorisation (it is "
            f"{core.get_status_display()})."
        )

    waiting = codes_needing_approval(core)
    codes, declined, required_declined = (
        _split_answer(core, waiting, declined_codes) if approved else ([], [], []))
    if required_declined:
        approved, codes, declined = False, [], []
    who = (user.get_full_name() or user.get_username()) if user else 'system'
    verdict = 'approved' if approved else 'declined'
    parts = [f"{timezone.now():%Y-%m-%d} {who}: customer {verdict}"]
    if codes:
        parts.append(f"repairs {', '.join(codes)}")
    if declined:
        parts.append(f"declined {', '.join(declined)}, rebuilt without")
    if required_declined:
        parts.append(f"declined {', '.join(required_declined)}, required for the rebuild, "
                     "so the unit goes back unrepaired")
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
    core.declined_repair_codes = sorted(set(core.declined_repair_codes or []) | set(declined))
    core.condition_notes = f"{core.condition_notes}\n{line}".strip()
    core.authorisation_answered_at = timezone.now()
    core.authorisation_contact = contact.strip()
    core.authorisation_method = method.strip()
    core.authorisation_reference = reference.strip()
    core.authorisation_codes = list(codes)
    core.save(update_fields=['status', 'approved_repair_codes', 'declined_repair_codes',
                             'condition_notes',
                             'authorisation_answered_at', 'authorisation_contact',
                             'authorisation_method', 'authorisation_reference',
                             'authorisation_codes', 'updated_at'])
    sync_part_status(core)
    return core


def _one_customers_units(cores, status: str, doing: str):
    """Refuse a batch unless every unit is the same customer's own unit, at `status`.
    Names the units that don't fit, so whoever picked them can fix the selection."""
    if not cores:
        raise ValidationError("Choose at least one unit.")
    customers = {c.customer_id for c in cores}
    if len(customers) > 1:
        raise ValidationError(
            f"These units belong to more than one customer; {doing} one customer's units "
            "at a time.")
    misfits = [c for c in cores if c.status != status or not c.returns_to_customer]
    if misfits:
        listed = ', '.join(f"{c.core_number} ({c.get_status_display()})" for c in misfits)
        raise ValidationError(f"Not every unit can be included — {listed}.")


@transaction.atomic
def request_authorisation_for(cores, user=None) -> list:
    """Send several of one customer's units for authorisation together — a lot answered
    on one sheet. Each unit is checked as `request_authorisation` checks it; any refusal
    refuses the batch, so a lot is never half-sent."""
    cores = list(cores)
    _one_customers_units(cores, 'IN_REBUILD', 'send')
    return [request_authorisation(c, user)[0] for c in cores]


@transaction.atomic
def record_authorisation_for(cores, approved: bool, user=None, note: str = '', *,
                             contact: str = '', method: str = '', reference: str = '',
                             declined_by_core=None) -> list:
    """Record the customer's answer for several of their units waiting on it — the
    customer answered the lot. Each unit gets its own record, as `record_authorisation`
    writes it; any refusal refuses the batch, so a lot is never half-answered.

    `declined_by_core`: `{core id: [codes]}`, the repairs declined on each unit (the
    lot grid's unticked cells)."""
    cores = list(cores)
    _one_customers_units(cores, 'AWAITING_AUTHORISATION', 'answer for')
    declined_by_core = {str(k): v for k, v in (declined_by_core or {}).items()}
    return [record_authorisation(c, approved, user, note, contact=contact, method=method,
                                 reference=reference,
                                 declined_codes=declined_by_core.get(str(c.id), ()))
            for c in cores]


def _authorised_repair_started(core, codes=None) -> bool:
    """Whether work has begun on a repair the customer's answer authorised: a repair
    step for one of its codes (or of `codes`, when given) started on this unit."""
    from Tracker.models import StepExecution
    codes = list(codes if codes is not None else (core.authorisation_codes or []))
    if not codes or not core.part_id:
        return False
    return StepExecution.objects.filter(  # tenant-safe: FK-correlated to a scoped core
        part_id=core.part_id, step__repair_code__code__in=codes,
        status__in=('IN_PROGRESS', 'COMPLETED')).exists()


@transaction.atomic
def correct_authorisation(core, approved: bool, user, reason: str, *, declined_codes=()):
    """The customer's answer was recorded wrong: put the right one on record (user
    decision 2026-10-26, Corrections #22). Allowed until a repair it would take back has
    started — or, for a decline, until the unit has gone back. Both answers stay in the
    core's notes, with the reason.

    Approved → declined takes back the repairs that answer approved and sends the unit
    to DECLINED. Declined → approved resumes the rebuild and approves what was waiting.
    `declined_codes` corrects item by item: the repairs the customer actually declined,
    as `record_authorisation` takes them (a required one declines the unit).

    Raises:
        ValidationError: no reason, nothing recorded to correct, the same answer, or work
            has begun on a repair the correction would take back.
    """
    from Tracker.services.reman.repair_routing import codes_needing_approval

    reason = (reason or '').strip()
    if not reason:
        raise ValidationError("Say why the customer's answer is being corrected.")
    if core.authorisation_answered_at is None:
        raise ValidationError(f"{core.core_number} has no customer answer on record to correct.")
    was_approved = core.status == 'IN_REBUILD'
    if core.status not in ('IN_REBUILD', 'DECLINED'):
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — its answer can no longer be corrected.")

    # What the recorded answer was about: the repairs it approved and the ones it
    # declined — or, after a whole-unit decline, what is still waiting.
    old_approved = set(core.authorisation_codes or [])
    old_declined = set(core.declined_repair_codes or [])
    asked = (sorted(old_approved | old_declined) if was_approved
             else codes_needing_approval(core))
    if approved:
        new_approved, new_declined, required_declined = _split_answer(core, asked, declined_codes)
        if required_declined:
            approved, new_approved, new_declined = False, [], []
    else:
        new_approved, new_declined, required_declined = [], [], []
    if approved == was_approved and set(new_approved) == old_approved \
            and set(new_declined) == (old_declined & set(asked)):
        raise ValidationError("That is the answer already on record.")
    taken_back = old_approved - set(new_approved)
    if taken_back and _authorised_repair_started(core, taken_back):
        raise ValidationError(
            f"Work has started on a repair the customer's answer authorised on {core.core_number}; "
            "the answer can no longer be corrected.")

    who = (user.get_full_name() or user.get_username()) if user else 'system'
    core.approved_repair_codes = sorted(
        (set(core.approved_repair_codes or []) - old_approved) | set(new_approved))
    core.declined_repair_codes = sorted((old_declined - set(asked)) | set(new_declined))
    core.authorisation_codes = list(new_approved)
    core.status = 'IN_REBUILD' if approved else 'DECLINED'
    said = 'approved' if approved else 'declined'
    if new_declined:
        said += f", declining {', '.join(new_declined)}"
    if required_declined:
        said += (f" (declined {', '.join(required_declined)}, required for the rebuild, so "
                 "the unit goes back unrepaired)")
    line = (f"{timezone.now():%Y-%m-%d} {who}: correction — customer {said} (recorded as "
            f"{'approved' if was_approved else 'declined'}). {reason}")
    core.condition_notes = f"{core.condition_notes}\n{line}".strip()
    core.save(update_fields=['status', 'approved_repair_codes', 'declined_repair_codes',
                             'authorisation_codes', 'condition_notes', 'updated_at'])
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
