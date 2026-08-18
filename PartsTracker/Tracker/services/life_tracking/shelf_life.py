"""
Material shelf-life, unified under LifeTracking.

A material lot's shelf life is tracked with a calendar-based ``LifeTracking``
record (the same machinery as part life limits), NOT the raw
``MaterialLot.expiration_date`` scalar. That gives lots the pre-expiry WARNING
window, the live ``is_blocked`` gate, and governed extensions-with-approver for
free, and puts materials on the one status system shared with parts/cores.

Data flow:
  * ``expiration_date`` remains the receipt *input* (what the supplier's CoC
    states). ``attach_shelf_life`` seeds a LifeTracking record FROM it so the
    record — not the scalar — is the runtime authority for gating/status.
  * When the supplier gives no absolute date but the material type carries a
    calendar (shelf-life) ``LifeLimitDefinition``, the definition's ``hard_limit``
    (days) drives expiry and we derive ``expiration_date`` for display.
  * ``extend_shelf_life`` is the governed change: it writes a per-instance
    override (reason + approver) via ``apply_life_override`` and keeps the
    ``expiration_date`` mirror in sync.

Materials with no shelf life (no absolute date and no calendar definition on the
type — bar stock, castings) get no record and are never gated.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

SHELF_LIFE_DEFINITION_NAME = "Shelf Life"


def get_or_create_shelf_life_definition(tenant):
    """The tenant's canonical calendar ``Shelf Life`` definition, created on first
    use (mirrors the values the seeders use: days, warn at 270, expire at 365)."""
    from Tracker.models import LifeLimitDefinition

    existing = LifeLimitDefinition.objects.filter(
        name=SHELF_LIFE_DEFINITION_NAME, is_current_version=True
    ).first()
    if existing is not None:
        return existing
    return LifeLimitDefinition.objects.create(
        tenant=tenant,
        name=SHELF_LIFE_DEFINITION_NAME,
        unit="days",
        unit_label="Days",
        is_calendar_based=True,
        soft_limit=Decimal("270"),
        hard_limit=Decimal("365"),
    )


def resolve_lot_shelf_life_definition(lot):
    """A calendar life-limit definition configured for the lot's material type
    (via ``PartTypeLifeLimit``), or ``None``. This lets a tenant use a per-type
    shelf life (e.g. 12 months for adhesive X) instead of the default."""
    if not lot.material_type_id:
        return None
    from Tracker.models import PartTypeLifeLimit

    link = (
        PartTypeLifeLimit.objects.filter(
            part_type_id=lot.material_type_id,
            definition__is_calendar_based=True,
            definition__is_current_version=True,
        )
        .select_related("definition")
        .first()
    )
    return link.definition if link else None


def attach_shelf_life(lot):
    """Attach a calendar ``LifeTracking`` record to ``lot`` at receipt, if it has a
    shelf life. Idempotent (``for_object`` is get-or-create). Returns the record,
    or ``None`` when the material has no shelf life.
    """
    from Tracker.models import LifeTracking

    definition = resolve_lot_shelf_life_definition(lot)
    # No shelf life at all: no per-type calendar definition AND no supplier date.
    if definition is None and lot.expiration_date is None:
        return None

    reference_date = lot.manufacture_date or lot.received_date
    source = LifeTracking.Source.OEM  # supplier/CoC-provided
    override = None

    if lot.expiration_date is not None:
        # Supplier gave an absolute use-by date: express it as a per-instance
        # limit (days from the reference date) so is_blocked flips exactly then.
        # A lot received already past its date lands negative → immediately EXPIRED.
        if definition is None:
            definition = get_or_create_shelf_life_definition(lot.tenant)
        override = Decimal((lot.expiration_date - reference_date).days)
    else:
        # Derive the display date from the type's shelf-life duration.
        source = LifeTracking.Source.CALCULATED
        if definition.hard_limit is not None:
            lot.expiration_date = reference_date + timedelta(days=int(definition.hard_limit))
            lot.save(update_fields=["expiration_date", "updated_at"])

    tracking, _created = LifeTracking.for_object(
        lot,
        definition,
        reference_date=reference_date,
        source=source,
        hard_limit_override=override,
    )
    return tracking


def lot_shelf_life_tracking(lot):
    """The lot's calendar shelf-life ``LifeTracking`` record, or ``None``.

    Uses the prefetched ``lot.life_tracking`` GenericRelation when available (list
    views prefetch it) to avoid an N+1; falls back to a query otherwise.
    """
    cache = getattr(lot, "_prefetched_objects_cache", None)
    if cache is not None and "life_tracking" in cache:
        for lt in lot.life_tracking.all():
            if lt.definition.is_calendar_based:
                return lt
        return None
    from Tracker.models import LifeTracking

    return (
        LifeTracking.objects.for_object(lot)
        .select_related("definition")
        .filter(definition__is_calendar_based=True)
        .first()
    )


def shelf_life_status(lot):
    """Live ``OK``/``WARNING``/``EXPIRED`` for the lot, or ``None`` if not tracked."""
    lt = lot_shelf_life_tracking(lot)
    return lt.status if lt is not None else None


def is_lot_shelf_life_expired(lot) -> bool:
    """True when the lot has a shelf-life record and it is past its (possibly
    extended) hard limit."""
    lt = lot_shelf_life_tracking(lot)
    return bool(lt is not None and lt.is_blocked)


def assert_lot_usable(lot) -> None:
    """Raise ``ValueError`` if the lot is shelf-life-expired. The single gate the
    acceptance and consumption paths call before letting material be used."""
    if is_lot_shelf_life_expired(lot):
        raise ValueError(
            f"Lot {lot.lot_number} is shelf-life expired and cannot be used. "
            f"Extend the shelf life (with evidence) or dispose of the lot."
        )


def extend_shelf_life(lot, new_expiration_date: date, reason: str, approved_by=None):
    """Governed shelf-life extension: engineering/quality re-tests the material and
    approves a new use-by date. Writes a per-instance override (reason + approver,
    captured by auditlog) and keeps the ``expiration_date`` mirror in sync.
    """
    from Tracker.services.life_tracking.life_tracking import apply_life_override

    lt = lot_shelf_life_tracking(lot)
    if lt is None:
        raise ValueError(f"Lot {lot.lot_number} has no shelf-life tracking to extend.")
    if not reason:
        raise ValueError("A reason is required to extend shelf life.")

    reference_date = lt.reference_date or lot.manufacture_date or lot.received_date
    new_limit = Decimal((new_expiration_date - reference_date).days)
    apply_life_override(
        lt,
        hard_limit=new_limit,
        soft_limit=lt.soft_limit_override,
        reason=reason,
        approved_by=approved_by,
    )
    lot.expiration_date = new_expiration_date
    fields = ["expiration_date", "updated_at"]
    # If the lot was quarantined *solely* for shelf life and the extension clears
    # the expiry, re-qualify it: back to RECEIVED so it re-enters the receiving
    # queue and flows normally. ("SHELF_LIFE_EXPIRED" is the hold_reason set by
    # services.qms.receiving_inspection; kept as a literal to avoid a circular import.)
    if (
        lot.status == "QUARANTINE"
        and lot.hold_reason == "SHELF_LIFE_EXPIRED"
        and not lt.is_blocked
    ):
        lot.status = "RECEIVED"
        lot.hold_reason = ""
        fields += ["status", "hold_reason"]
    lot.save(update_fields=fields)
    return lt
