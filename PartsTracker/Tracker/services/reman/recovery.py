"""The RECOVER supply lane — what the core bank could yield.

Material planning counts purchased stock and what is on the shelf, and has no idea
teardown is about to PRODUCE the component it is calling short. So a planner buys
parts the shop was going to harvest. See `Documents/REMAN_REBUILD_LOOP_DESIGN.md` §11.

The arithmetic is simple: cores in the bank × expected usable yield. What matters is
what it is NOT allowed to do.

**It reports; it does not net.** Recoverable supply is a FORECAST — teardown has not
happened — while on-hand is a fact. Silently adding the two would let a planner see
stock that does not exist yet and skip an order on the strength of it, and the error
is asymmetric: over-counting future supply stops a line, under-counting only buys a
part you could have harvested. So this returns its own number and the screen shows it
as its own lane.

**Only exchange cores count.** A repair-and-return core is committed to its owner —
`allows_pooled_harvest` says so — and you cannot tear down a customer's unit for
someone else's job.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal


@dataclass(frozen=True)
class RecoverableSupply:
    """What the core bank could yield of one component type."""
    component_type_id: str
    quantity: Decimal
    core_count: int
    # Per core type: how many cores, and what each is expected to yield. A planner who
    # cannot see which cores a number came from cannot judge whether to trust it.
    sources: list = field(default_factory=list)


def _bank_statuses():
    """Core states that still have the component inside them.

    RECEIVED and IN_DISASSEMBLY only. A DISASSEMBLED core has already given up its
    components — they are harvested rows by then, and counting both would double.
    """
    return ('RECEIVED', 'IN_DISASSEMBLY')


def recoverable_supply(component_type, tenant=None) -> RecoverableSupply:
    """How many of `component_type` the core bank could yield.

    Returns zero for anything the item master says cannot be recovered — an expendable
    never comes out of a core reusable, whatever the bank holds.

    `tenant` is optional and explicit because the shop-wide planning callers
    (`sourcing_requirements`, and the PDF adapter behind it) take a tenant as an
    ARGUMENT rather than reading the request ContextVar, and this has to match them or
    the function's scope silently depends on something its caller never passed.
    `.objects` without a context raises `TenantContextRequired` rather than returning
    an empty bank, so the failure is loud — but a report run from a task would be the
    thing that raises it, and passing the tenant the caller already holds removes the
    ambient dependency entirely.
    """
    from Tracker.models import Core, DisassemblyBOMLine

    def _scope(qs):
        return qs.filter(tenant=tenant) if tenant is not None else qs

    if not getattr(component_type, 'can_recover', False):
        return RecoverableSupply(
            component_type_id=str(component_type.id), quantity=Decimal('0'),
            core_count=0, sources=[],
        )

    # Which core types yield this component, and how much of it survives teardown.
    yields = {
        line.core_type_id: line
        for line in _scope(DisassemblyBOMLine.objects.filter(  # tenant-safe: .objects auto-scopes; `tenant` narrows further when passed
            component_type=component_type, is_current_version=True, archived=False,
        )).select_related('core_type')
    }
    if not yields:
        return RecoverableSupply(
            component_type_id=str(component_type.id), quantity=Decimal('0'),
            core_count=0, sources=[],
        )

    total = Decimal('0')
    cores_counted = 0
    sources = []
    for core_type_id, line in yields.items():
        bank = list(
            _scope(Core.objects.filter(  # tenant-safe: .objects auto-scopes; `tenant` narrows further when passed
                core_type_id=core_type_id, status__in=_bank_statuses(), archived=False,
            )).only('id', 'fulfilment_mode')
        )
        # Exchange only: a repair-and-return core's components go back into it.
        available = [c for c in bank if c.allows_pooled_harvest]
        if not available:
            continue
        per_core = Decimal(str(line.expected_usable_qty))
        qty = per_core * len(available)
        total += qty
        cores_counted += len(available)
        sources.append({
            'core_type': line.core_type.name,
            # Carried so a planner-facing lane can reach the core type's own teardown
            # lead time without re-deriving which types yielded the number.
            'core_type_id': str(line.core_type_id),
            'cores': len(available),
            'per_core': float(per_core),
            'quantity': float(qty),
        })

    return RecoverableSupply(
        component_type_id=str(component_type.id),
        quantity=total,
        core_count=cores_counted,
        sources=sources,
    )


def teardown_lead_days(core_type, tenant=None) -> int | None:
    """Working days from starting a teardown to having the components in hand.

    Summed from the disassembly process's authored step durations — the same numbers
    scheduling already plans against, so the planning sheet and the board cannot
    disagree about how long a teardown takes.

    Returns None when the process is unauthored or carries no durations, and the
    caller then omits a start-by date rather than inventing one. A made-up lead time
    is worse than none: it reads as authored fact on the sheet and a planner schedules
    against it.
    """
    from Tracker.models import ProcessStep
    from Tracker.services.reman.teardown import _resolve_teardown_process

    # The process a planned teardown would ACTUALLY use — the same resolution
    # `plan_teardown` applies — rather than whichever disassembly process sorts first.
    # A core type can carry several, and a lead time read off the wrong one is a date
    # nobody will meet.
    try:
        proc = _resolve_teardown_process(core_type, None)
    except ValueError:
        return None
    if tenant is not None and proc.tenant_id != tenant.id:
        return None

    total = timedelta()
    found = False
    for ps in (ProcessStep.objects.filter(process=proc)  # tenant-safe: scoped by `process` FK
               .select_related('step')):
        d = getattr(ps.step, 'expected_duration', None)
        if d:
            total += d
            found = True
    if not found:
        return None
    # Round UP to a whole day. Half a day of teardown still occupies a day on a
    # planner's calendar, and rounding down would quietly promise the components a day
    # earlier than the shop can produce them.
    return max(1, -(-int(total.total_seconds()) // 86400))


@dataclass(frozen=True)
class TeardownBank:
    """One core type's exchange cores, split by whether they are still free to plan."""
    core_type: object
    #: RECEIVED and on no work order — what a proposal may commit. Oldest first, so a
    #: planner's default is the unit that has waited longest.
    proposable: list
    #: Already committed: on a teardown work order, or being torn down now. Their yield
    #: is on its way, so a proposal must count it rather than propose them again.
    in_flight: int
    #: Expected usable yield per core, by component type id.
    yields: dict


def teardown_banks(tenant) -> dict:
    """`{core_type_id: TeardownBank}` for every core type with exchange cores waiting.

    Exchange only, as everywhere in this module: a repair-and-return unit's parts go
    back into it and are nobody else's supply.
    """
    from Tracker.models import Core, DisassemblyBOMLine

    by_type: dict = {}
    for core in (Core.objects  # tenant-safe: explicit tenant filter
                 .filter(tenant=tenant, archived=False, status__in=_bank_statuses())
                 .select_related('core_type')
                 .order_by('received_date', 'created_at')):
        if not core.allows_pooled_harvest:
            continue
        entry = by_type.setdefault(core.core_type_id,
                                   {'core_type': core.core_type, 'free': [], 'flight': 0})
        if core.status == 'RECEIVED' and core.work_order_id is None:
            entry['free'].append(core)
        else:
            entry['flight'] += 1
    if not by_type:
        return {}

    yields: dict = {}
    for line in (DisassemblyBOMLine.objects  # tenant-safe: explicit tenant filter
                 .filter(tenant=tenant, core_type_id__in=list(by_type),
                         is_current_version=True, archived=False)):
        per_core = float(line.expected_usable_qty)
        if per_core > 0:
            yields.setdefault(line.core_type_id, {})[line.component_type_id] = per_core

    return {
        ct_id: TeardownBank(core_type=e['core_type'], proposable=e['free'],
                            in_flight=e['flight'], yields=yields.get(ct_id, {}))
        for ct_id, e in by_type.items()
    }
