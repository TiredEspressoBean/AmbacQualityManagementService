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
    """The reman-cycle definitions that apply to the core's type: live links to current,
    unarchived definitions only (a revised limit leaves its old version's link behind;
    a removed link no longer limits)."""
    from Tracker.models import LifeLimitDefinition, PartTypeLifeLimit
    if core.core_type_id is None:
        return []
    # A revision copies the links onto the new version, so the current version's link
    # is the live one.
    ids = (PartTypeLifeLimit.objects  # tenant-safe: .objects auto-scopes
           .filter(part_type_id=core.core_type_id, archived=False)
           .values_list('definition_id', flat=True))
    return list(LifeLimitDefinition.objects.filter(  # tenant-safe: .objects auto-scopes
        id__in=ids, unit__iexact=REMAN_UNIT, is_current_version=True, archived=False))


def _serial(value) -> str:
    return ' '.join((value or '').split()).upper()


def prior_remans(core) -> int:
    """How many times this unit was remanned before: earlier cores of the same type and
    serial number (compared without case or stray spaces) whose teardown began. Archived
    cores don't count. A unit with no serial number has no history."""
    from Tracker.models import Core
    serial = _serial(core.serial_number)
    if not serial:
        return 0
    others = (Core.objects  # tenant-safe: .objects auto-scopes
              .filter(core_type_id=core.core_type_id, archived=False,
                      disassembly_started_at__isnull=False)
              .exclude(pk=core.pk).values_list('serial_number', flat=True))
    return sum(1 for s in others if _serial(s) == serial)


def reseed(core) -> None:
    """The serial changed before the reman started: the count is the new serial's
    history (user review 2026-11-11). Teardown begun, the count stands."""
    from Tracker.models import LifeTracking
    if core.status != 'RECEIVED':
        return
    prior = Decimal(prior_remans(core))
    for definition in reman_definitions(core):
        tracking, created = LifeTracking.for_object(core, definition, accumulated=prior)
        if not created and tracking.accumulated != prior:
            tracking.accumulated = prior
            tracking.save(update_fields=['accumulated', 'updated_at', 'cached_status'])


def ensure_reman_trackings(core) -> list:
    """The core's reman-cycle trackings, created where missing at the count carried from
    an earlier version of the limit, else its prior remans."""
    from Tracker.models import LifeTracking
    from Tracker.services.life_tracking.life_tracking import carried_count
    out = []
    definitions = reman_definitions(core)
    if not definitions:
        return out
    prior = None
    for definition in definitions:
        tracking = LifeTracking.objects.for_object(core).filter(definition=definition).first()  # tenant-safe: .objects auto-scopes
        if tracking is None:
            start = carried_count(core, definition)
            if start is None:
                prior = Decimal(prior_remans(core)) if prior is None else prior
                start = prior
            tracking, _ = LifeTracking.for_object(core, definition, accumulated=start)
        out.append(tracking)
    return out


def count_reman_start(core) -> None:
    """The reman is starting: count it on each reman-cycle tracking."""
    for tracking in ensure_reman_trackings(core):
        tracking.increment(1)
