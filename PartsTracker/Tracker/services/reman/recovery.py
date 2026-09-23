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
