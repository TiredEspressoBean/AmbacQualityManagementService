"""Bulk core receipt and assigning identity. See Documents/CORE_AS_PART_DESIGN.md §6.

Some cores arrive individually identified and are received straight in as core parts
(`core_part.create_core`). Some arrive in bulk — a pallet of forty injector bodies,
counted, no serials. Those are received as a `MaterialLot` whose `material_type` is the
core type, and each unit is given an identity when the shop chooses to (at receiving
inspection, when pulled for teardown, any time): `assign_core_identity` takes one unit
off the lot and mints its part and core role. From there it is an ordinary core, and
`Parts.received_in_lot` keeps the trace back to the receipt.

A core lot is marked `MaterialLot.holds_cores`, set here at receipt and nowhere else.
The part type cannot tell: a reman shop's core type is usually the part number it sells,
so a bought lot of that part and a pallet of returned cores share a type — and counting
the first as cores put the shop's purchased stock in the core bank. The lot must still
be OF a core type — one cores were received as, or with a disassembly BOM authored — so
the bank knows what it yields.

Only exchange cores may stay in bulk. Repair-and-return means THIS unit goes back to its
owner, which needs an identity from the moment it is received — so a lot can only be
received for exchange, and every identity assigned from one is an exchange core. That is
definitional, not shop policy, so it is enforced here rather than configured.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

#: Lot states whose unassigned units are in the building and may be given an identity —
#: and so are counted in the core bank. Not ON_ORDER (not here yet), QUARANTINE or
#: REJECTED (held, or going back), CONSUMED or SCRAPPED (nothing left).
BANK_LOT_STATUSES = ('RECEIVED', 'AWAITING_INSPECTION', 'ACCEPTED', 'IN_USE')


def is_core_type(part_type) -> bool:
    """Cores were received as it, or it has a disassembly BOM authored."""
    from django.db.models import Q
    from Tracker.models import PartTypes
    return (PartTypes.objects  # tenant-safe: filtered to one known row by pk
            .filter(pk=part_type.pk)
            .filter(Q(cores__isnull=False) | Q(disassembly_bom_lines__isnull=False))
            .exists())


def receive_core_lot(*, tenant, core_type, quantity, received_by, customer=None,
                     received_date=None, lot_number: str = '', storage_location: str = '',
                     source_reference: str = ''):
    """Receive `quantity` unidentified cores of `core_type` as one lot.

    `customer` is who sent them, recorded as the lot's supplier. A customer whose
    standing arrangement is repair-and-return is refused: their units go back to them,
    so each needs its own identity at receipt — receive them individually instead.

    Raises:
        ValueError: quantity is not a positive whole number, or the customer's units
            must be received individually.
    """
    from django.utils import timezone
    from Tracker.models import MaterialLot
    from Tracker.services.reman.core import resolve_fulfilment_mode
    from Tracker.utils.sequences import generate_next_sequence

    qty = Decimal(str(quantity))
    if qty <= 0 or qty != qty.to_integral_value():
        raise ValueError("A core lot is a count of whole units — give a positive whole number")
    if not is_core_type(core_type):
        raise ValueError(
            f"{core_type.name} is not a core type yet — author its disassembly BOM, or "
            "receive a first unit individually, so the bank knows what a lot of it holds"
        )
    mode, _ = resolve_fulfilment_mode(customer)
    if mode != 'EXCHANGE':
        raise ValueError(
            f"{customer.name}'s cores are repair-and-return — each unit goes back to them, "
            "so each must be received individually with its own identity"
        )

    if not lot_number:
        lot_number = generate_next_sequence(
            queryset=MaterialLot.objects,
            number_field='lot_number',
            prefix=f"CORELOT-{timezone.now().year}-",
            padding=4,
            tenant=tenant,
        )
    return MaterialLot.objects.create(
        tenant=tenant,
        lot_number=lot_number,
        material_type=core_type,
        supplier=customer,
        supplier_lot_number=source_reference,
        received_date=received_date or timezone.now().date(),
        received_by=received_by,
        quantity=qty,
        quantity_remaining=qty,
        unit_of_measure='EA',
        status='RECEIVED',
        storage_location=storage_location,
        holds_cores=True,
    )


def assign_core_identity(lot, *, user, condition_grade: str, serial_number: str = '',
                         core_number: str | None = None, condition_notes: str = '',
                         source_type: str = 'CUSTOMER_RETURN'):
    """Take one unit off a core lot and give it an identity: its part and core role.

    The unit is graded by whoever is holding it — `condition_grade` is required, as it
    is at individual receipt. It inherits the lot's receipt (date, receiver, customer)
    and is always an exchange core (see module docstring).

    Race-safe: the lot is locked, so two people identifying units off the same lot can
    never overdraw it.

    Raises:
        ValueError: the lot is not a core lot with units left to identify.
    """
    from Tracker.models import MaterialLot
    from Tracker.services.reman.core_part import create_core

    with transaction.atomic():
        locked = MaterialLot.all_tenants.select_for_update().get(pk=lot.pk)
        if not locked.holds_cores:
            raise ValueError(f"Lot {locked.lot_number} is not a lot of cores")
        if locked.status not in BANK_LOT_STATUSES:
            raise ValueError(
                f"Lot {locked.lot_number} is {locked.get_status_display().lower()}; "
                "units can only be identified from a lot that is in the building"
            )
        if locked.quantity_remaining < 1:
            raise ValueError(f"Every unit in lot {locked.lot_number} already has an identity")

        core = create_core(
            tenant=locked.tenant,
            core_number=core_number,
            received_in_lot=locked,
            core_type=locked.material_type,
            customer=locked.supplier,
            received_date=locked.received_date,
            received_by=locked.received_by or user,
            source_type=source_type,
            source_reference=locked.lot_number,
            serial_number=serial_number,
            condition_grade=condition_grade,
            condition_notes=condition_notes,
            fulfilment_mode='EXCHANGE',
        )

        locked.quantity_remaining -= 1
        fields = ['quantity_remaining', 'updated_at']
        if locked.quantity_remaining <= 0:
            locked.status = 'CONSUMED'
            fields.append('status')
        locked.save(update_fields=fields)
        lot.refresh_from_db()
    return core


def bank_lots(tenant=None, core_type_ids=None):
    """Core lots with units still to identify, oldest receipt first.

    The unassigned half of the core bank; the other half is banked core parts. Exchange
    by construction, so every unit here is pool supply.
    """
    from Tracker.models import MaterialLot

    qs = MaterialLot.objects  # tenant-safe: .objects auto-scopes; `tenant` narrows further when passed
    if tenant is not None:
        qs = qs.filter(tenant=tenant)
    qs = (qs
          .filter(archived=False, holds_cores=True, status__in=BANK_LOT_STATUSES, quantity_remaining__gte=1)
          .select_related('material_type')
          .order_by('received_date', 'created_at'))
    if core_type_ids is not None:
        qs = qs.filter(material_type_id__in=list(core_type_ids))
    return list(qs)
