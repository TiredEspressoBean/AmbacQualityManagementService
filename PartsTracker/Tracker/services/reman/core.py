"""
Core aggregate services.

State-transition logic for the Core lifecycle: disassembly start/completion,
scrapping, and credit issuance.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import Core
from Tracker.services.reman.core_part import sync_part_status


def start_core_disassembly(core: Core, user) -> Core:
    """Transition a Core from RECEIVED to IN_DISASSEMBLY.

    Raises:
        ValueError: core is not in RECEIVED status.
    """
    if core.status != 'RECEIVED':
        raise ValueError(f"Cannot start disassembly - core is {core.status}")
    core.status = 'IN_DISASSEMBLY'
    core.disassembly_started_at = timezone.now()
    core.save()
    sync_part_status(core)
    return core


def complete_core_disassembly(core: Core, user) -> Core:
    """Transition a Core from IN_DISASSEMBLY to DISASSEMBLED.

    Raises:
        ValueError: core is not in IN_DISASSEMBLY status.
    """
    if core.status != 'IN_DISASSEMBLY':
        raise ValueError(f"Cannot complete disassembly - core is {core.status}")
    core.status = 'DISASSEMBLED'
    core.disassembly_completed_at = timezone.now()
    core.disassembled_by = user
    core.save()
    sync_part_status(core)
    return core


def scrap_core(core: Core, reason: str = '') -> Core:
    """Mark a Core as scrapped.

    Works at any point, not only before teardown: a core is just as often found
    unusable DURING disassembly — cracked housing, corrosion past limits — and that is
    the third end state beside rebuild and harvest.

    Raises:
        ValueError: core is already scrapped.
    """
    if core.status == 'SCRAPPED':
        raise ValueError("Core is already scrapped")
    core.status = 'SCRAPPED'
    core.condition_grade = 'SCRAP'
    if reason:
        core.condition_notes = f"{core.condition_notes}\nScrapped: {reason}".strip()
    core.save()
    sync_part_status(core)
    return core


def issue_core_credit(core: Core) -> Core:
    """Mark core credit as issued.

    Raises:
        ValueError: no credit value is set on the core.
    """
    if not core.core_credit_value:
        raise ValueError("No credit value set for this core")
    core.core_credit_issued = True
    core.core_credit_issued_at = timezone.now()
    core.save()
    return core


def resolve_fulfilment_mode(customer, requested: str | None = None) -> tuple[str, str]:
    """The mode a core being received should take, and where it came from.

    Returns `(mode, provenance)` where provenance is one of 'requested', 'customer' or
    'default' — so the receipt screen can say *why* it is proposing what it proposes.
    A clerk confirming "Exchange, from Acme's standing arrangement" is doing something
    different from a clerk filling in a blank, and only one of those is reliable.

    Precedence: an explicit request wins (someone deliberately overrode it), then the
    customer's standing arrangement, then EXCHANGE.

    EXCHANGE last because the error is asymmetric. Treating a repair-and-return unit as
    an exchange puts its components in the harvest pool, and the customer's own unit can
    then never be reassembled; the reverse merely adds a quoting step nobody needed. So
    the fallback is the mode with no obligations, and 'default' provenance is what lets
    the UI admit it is a fallback rather than an answer.
    """
    if requested:
        return requested, 'requested'
    arrangement = getattr(customer, 'default_core_fulfilment_mode', None) if customer else None
    if arrangement:
        return arrangement, 'customer'
    return 'EXCHANGE', 'default'


def receipt_order_refusal(*, order, customer, fulfilment_mode) -> str | None:
    """Why a core can't be received against `order`, or None when it can.

    The order is what the unit is here FOR, and it lives on the core's part
    (`Parts.order`), so it follows the unit through teardown, split and rebuild.

    Required for a repair-and-return core: it is the customer's own unit, and the order
    is what it is repaired against — without it the order can't count its cores in or
    show what is waiting on their authorisation. Optional for an exchange core, which
    may simply be surrendered into the bank.
    """
    if order is None:
        if fulfilment_mode == 'REPAIR_RETURN':
            return ("A repair-and-return core is the customer's own unit — pick the order "
                    "it is being repaired against.")
        return None
    if customer is None:
        return "Pick the customer before the order."
    if order.company_id != customer.id:
        owner = order.company.name if order.company else "no customer"
        return f"{order.order_number} is {owner}'s order, not {customer.name}'s."
    if order.archived:
        return f"{order.order_number} is archived; pick an open order."
    if order.order_status in ('COMPLETED', 'CANCELLED'):
        return f"{order.order_number} is {order.get_order_status_display().lower()}; pick an open order."
    return None
