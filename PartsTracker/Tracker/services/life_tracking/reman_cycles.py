"""Reman cycles: a life limit on how many times a unit has been remanufactured
(user decision 2026-11-11).

A definition whose unit is ``remans``, linked to a core type through PartTypeLifeLimit,
counts the unit's remanufactures. The count lives on the core (`LifeTracking` on the
Core) and is set up when the core is received, so an extension can be approved before
any work starts: its starting value is the earlier remans of the same serial number.

It is counted when the reman STARTS — the first step's start on a RECEIVED core, the
moment teardown begins — so the life-limit start gate refuses an over-limit unit
before anyone takes it apart. What then happens to it (scrap, bank, return) is a
person's decision.
"""
from decimal import Decimal

REMAN_UNIT = 'remans'


def is_reman_cycles(definition) -> bool:
    return (definition.unit or '').strip().lower() == REMAN_UNIT


def reman_definitions(core):
    """The reman-cycle definitions that apply to the core's type."""
    from Tracker.models import LifeLimitDefinition, PartTypeLifeLimit
    if core.core_type_id is None:
        return []
    ids = (PartTypeLifeLimit.objects  # tenant-safe: .objects auto-scopes
           .filter(part_type_id=core.core_type_id).values_list('definition_id', flat=True))
    return list(LifeLimitDefinition.objects.filter(id__in=ids, unit__iexact=REMAN_UNIT))  # tenant-safe: .objects auto-scopes


def prior_remans(core) -> int:
    """How many times this unit was remanned before: earlier cores of the same type and
    serial number whose teardown began. A unit with no serial number has no history."""
    from Tracker.models import Core
    serial = (core.serial_number or '').strip()
    if not serial:
        return 0
    return (Core.objects  # tenant-safe: .objects auto-scopes
            .filter(core_type_id=core.core_type_id, serial_number__iexact=serial,
                    disassembly_started_at__isnull=False)
            .exclude(pk=core.pk).count())


def ensure_reman_trackings(core) -> list:
    """The core's reman-cycle trackings, created at its prior count where missing."""
    from Tracker.models import LifeTracking
    out = []
    definitions = reman_definitions(core)
    if not definitions:
        return out
    prior = Decimal(prior_remans(core))
    for definition in definitions:
        tracking, _ = LifeTracking.for_object(core, definition, accumulated=prior)
        out.append(tracking)
    return out


def untracked_over_limit(core) -> list:
    """Reman-cycle definitions a received core is already at the hard limit of without a
    tracking yet (a core received before its definition existed) — read, not written,
    so the start gate stays a decision. Its tracking is created when the reman starts or
    an extension is wanted."""
    from Tracker.models import LifeTracking
    if core.status != 'RECEIVED':
        return []
    tracked = set(LifeTracking.objects.for_object(core).values_list('definition_id', flat=True))  # tenant-safe: .objects auto-scopes
    missing = [d for d in reman_definitions(core) if d.id not in tracked and d.hard_limit is not None]
    if not missing:
        return []
    prior = prior_remans(core)
    return [d for d in missing if prior >= d.hard_limit]


def count_reman_start(core) -> None:
    """The reman is starting: count it on each reman-cycle tracking."""
    for tracking in ensure_reman_trackings(core):
        tracking.increment(1)
