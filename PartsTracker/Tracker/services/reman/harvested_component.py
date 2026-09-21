"""
HarvestedComponent aggregate services.

Scrap a component or accept it into inventory as a Parts record.
Life-tracking transfer is kept on the model for now (`_transfer_life_tracking`)
because it straddles the reman → life_tracking aggregate boundary and
has no other callers.
"""
from __future__ import annotations

from django.utils import timezone

from Tracker.models import HarvestedComponent


def scrap_component(
    component: HarvestedComponent,
    user,
    reason: str = '',
) -> HarvestedComponent:
    """Mark a harvested component as scrapped.

    Raises:
        ValueError: component is already scrapped.
    """
    if component.is_scrapped:
        raise ValueError("Component already scrapped")

    component.is_scrapped = True
    component.scrap_reason = reason
    component.scrapped_at = timezone.now()
    component.scrapped_by = user
    component.condition_grade = 'SCRAP'
    component.save()
    return component


def accept_component_to_inventory(
    component: HarvestedComponent,
    user,
    erp_id: str | None = None,
    transfer_life: bool = True,
):
    """Accept a component into inventory by creating a Parts record.

    Generates a default ERP id if one isn't provided. Optionally
    transfers applicable life-tracking records from the parent Core to
    the new Part.

    When the parent core does NOT allow pooled harvest — a repair-and-return unit,
    which goes back to the customer it came from — the new part is reserved to that
    core. Otherwise it enters stock unreserved, like any other inventory.

    Raises:
        ValueError: component is scrapped, or already accepted to inventory.
    """
    from Tracker.models import Parts, PartsStatus

    if component.is_scrapped:
        raise ValueError("Cannot accept scrapped component to inventory")
    if component.component_part:
        raise ValueError("Component already accepted to inventory")

    if not erp_id:
        short_id = str(component.pk).replace('-', '')[:8].upper()
        prefix = component.component_type.ID_prefix or 'P'
        erp_id = f"HC-{component.core.core_number}-{prefix}{short_id}"

    part = Parts.objects.create(
        tenant=component.tenant,
        ERP_id=erp_id,
        part_type=component.component_type,
        part_status=PartsStatus.PENDING,
        # Reserved at CREATION rather than in a second write: between the two there
        # would be a window in which the customer's part sits in stock looking free,
        # and this is the one transition the reservation exists to cover.
        reserved_for_core=(
            None if component.core.allows_pooled_harvest else component.core
        ),
    )

    component.component_part = part
    component.save()

    if transfer_life:
        component._transfer_life_tracking(part)

    return part
