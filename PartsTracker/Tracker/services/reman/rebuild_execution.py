"""Recording what actually went into a rebuilt unit, and finishing the job.

The as-built record. Once a unit ships, this is the only place that answers "where
did this component come from" — see `Documents/REMAN_REBUILD_LOOP_DESIGN.md` §6.5.

`AssemblyUsage` carries it, widened for this: a repair-and-return rebuild has a Core
as parent and `HarvestedComponent`s as children, because those components are the
customer's property and never became stock. Same nullable-pair shape as
`StepExecution.part`/`core`.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction


@transaction.atomic
def install_component(core, *, harvested=None, part=None, user, bom_line=None, step=None):
    """Record a component going into a core under rebuild.

    Exactly one of `harvested` (the customer's own, off this unit) or `part` (a stock
    item) — which mirrors the two supply worlds a slot can be filled from.

    Refuses a component belonging to a DIFFERENT core: reinstalling one unit's part
    into another is precisely what `reserved_for_core` exists to prevent, and a
    repair-and-return customer's components are their property.
    """
    from Tracker.models import AssemblyUsage
    from Tracker.services.reman.reservation import assert_work_order_allowed

    if (harvested is None) == (part is None):
        raise ValidationError("Install exactly one of a harvested component or a part.")
    if core.status != 'IN_REBUILD':
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — components can only be "
            "installed into a unit under rebuild."
        )

    if harvested is not None:
        if harvested.core_id != core.id:
            raise ValidationError(
                f"{harvested} came out of a different core. A repair-and-return unit is "
                "rebuilt with its own components."
            )
        if harvested.is_scrapped:
            raise ValidationError(f"{harvested} was scrapped and cannot be installed.")
    else:
        # A reserved part may only serve the core it is reserved to — the existing rule,
        # read here rather than restated.
        assert_work_order_allowed(part, core.work_order)

    return AssemblyUsage.objects.create(
        tenant=core.tenant,
        assembly_core=core,
        component_harvested=harvested,
        component=part,
        bom_line=bom_line,
        step=step,
        installed_by=user,
    )


@transaction.atomic
def complete_rebuild(core, user=None):
    """Mark a rebuilt unit ready to go back.

    Deliberately does NOT check that every slot was filled. The as-built record is what
    went in, and a unit can legitimately ship with a slot resolved differently than
    proposed — that is what curation is for. Asserting completeness here would make the
    proposal authoritative over what the bench actually did, which is backwards.
    """
    if core.status != 'IN_REBUILD':
        raise ValidationError(
            f"{core.core_number} is {core.get_status_display()} — only a unit under "
            "rebuild can be completed."
        )
    core.status = 'REBUILT'
    core.save(update_fields=['status', 'updated_at'])
    return core
