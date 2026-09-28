"""A core is a part; "core" is the role it plays. See Documents/CORE_AS_PART_DESIGN.md.

Two fields answer two questions, and this module keeps them from disagreeing:

- `Parts.part_status` — can this unit be worked, and where is it in the flow. What the
  scheduler, gates, queues and work-order cascade read.
- `Core.status` — the reman STAGE. What the reman services read.

The part status is DERIVED from the stage, never set independently, so a unit cannot be
"IN_REBUILD" to reman and "COMPLETED" to everything else.
"""
from __future__ import annotations

from Tracker.models.mes_lite import PartsStatus

# Stage → part status. RECEIVED is the one stage that depends on anything else: a unit
# on a work order is planned work the scheduler must place, one in the bank is not.
_BY_STAGE = {
    'IN_DISASSEMBLY': PartsStatus.IN_PROGRESS,
    # Waiting on someone else's decision — the release call after teardown, a
    # customer's authorisation. ON_HOLD, not CORE_BANKED: CORE_BANKED is terminal, and
    # a terminal status would let the work-order cascade close the order around a unit
    # still waiting to be rebuilt.
    'DISASSEMBLED': PartsStatus.ON_HOLD,
    'AWAITING_AUTHORISATION': PartsStatus.ON_HOLD,
    'IN_REBUILD': PartsStatus.IN_PROGRESS,
    'REBUILT': PartsStatus.COMPLETED,
    # An exchange unit rebuilt to stock is finished goods on the shelf.
    'REBUILT_TO_STOCK': PartsStatus.IN_STOCK,
    'DECLINED': PartsStatus.AWAITING_PICKUP,
    'RETURNED': PartsStatus.SHIPPED,
    'RETURNED_UNREPAIRED': PartsStatus.SHIPPED,
    # Taken apart; its components are parts of their own now. Terminal but not output.
    'HARVESTED': PartsStatus.DISMANTLED,
    'SCRAPPED': PartsStatus.SCRAPPED,
}


# Stages at which a core's part in its work order is over: the work the order was opened
# for is done, or will not be done. What the work-order completion cascade reads for a
# core, in place of the part status (see services.mes.parts).
#
# REBUILT and DECLINED end the order's work even though the unit is still in the
# building: returning it is logistics after the work, as shipping a built part is.
# DISASSEMBLED and AWAITING_AUTHORISATION do NOT — a decision is outstanding, and an
# open order is how that stays visible.
ENDED_STAGES = frozenset({
    'REBUILT', 'REBUILT_TO_STOCK', 'DECLINED', 'RETURNED', 'RETURNED_UNREPAIRED',
    'HARVESTED', 'SCRAPPED',
})


def part_status_for(stage: str, *, on_work_order: bool) -> str:
    """The part status a core part must carry at reman `stage`."""
    if stage == 'RECEIVED':
        return PartsStatus.PENDING if on_work_order else PartsStatus.CORE_BANKED
    try:
        return _BY_STAGE[stage]
    except KeyError:
        raise ValueError(f"No part status is defined for reman stage {stage!r}") from None


def sync_part_status(core) -> None:
    """Write the part status the core's current stage implies.

    Called by every service that moves a core's stage, straight after it saves — the
    one path by which a core part's status changes, so the two cannot drift.
    """
    from Tracker.services.mes.parts import (
        HELD_PART_STATUSES, TERMINAL_PART_STATUSES,
        _cascade_work_order_completion_for_subject,
    )

    part = core.part
    status = part_status_for(core.status, on_work_order=part.work_order_id is not None)
    # A QA hold survives a stage change, as it survives a step transition in the part
    # engine: quarantine is cleared by a disposition, never as a side effect of the unit
    # moving on. Only an ending (scrap, say) overrides it.
    held = part.part_status in HELD_PART_STATUSES and status not in TERMINAL_PART_STATUSES
    if not held and part.part_status != status:
        part.part_status = status
        part.save(update_fields=['part_status', 'updated_at'])

    # A core's ending comes from a reman transition, not from the step engine, so the
    # completion cascade has to be offered it here — or an order whose units have all
    # been harvested would never close. Offered on every ending; the cascade itself
    # decides, and leaves an already-closed order alone.
    if core.status in ENDED_STAGES and part.work_order_id:
        _cascade_work_order_completion_for_subject(part.work_order)


def create_core(*, tenant, work_order=None, step=None, core_number=None,
                received_in_lot=None, **fields):
    """Receive a core: the part it is, and the role it plays, in one step.

    The part's ERP id IS the core number, and `Core.part` is required, so the number is
    generated first, the part minted with it, and the role created on the part.
    `work_order` and `step` are where the UNIT is, so they go on the part, as does
    `received_in_lot` — the bulk receipt a unit was given its identity from.

    Every core in the system is created here — receipt, bulk receipt, seeders and tests
    alike — so none can exist without its part.
    """
    from django.db import transaction
    from Tracker.models import Core, Parts

    core_type = fields.get('core_type')
    core_type_id = core_type.id if core_type is not None else fields.get('core_type_id')
    stage = fields.get('status', 'RECEIVED')
    with transaction.atomic():
        number = core_number or Core.generate_core_number(tenant)
        part = Parts.objects.create(
            tenant=tenant,
            ERP_id=number,
            part_type_id=core_type_id,
            work_order=work_order,
            step=step,
            received_in_lot=received_in_lot,
            part_status=part_status_for(stage, on_work_order=work_order is not None),
        )
        return Core.objects.create(tenant=tenant, part=part, core_number=number, **fields)


def move_core(core, *, work_order=..., step=...) -> None:
    """Move the unit: put the core's part on a work order and/or at a step.

    The core's position is its part's, so this is the one way to change it. The part
    status is re-derived, since RECEIVED means something different on a work order.
    """
    part = core.part
    fields = []
    if work_order is not ...:
        part.work_order = work_order
        fields.append('work_order')
    if step is not ...:
        part.step = step
        fields.append('step')
    if fields:
        part.save(update_fields=[*fields, 'updated_at'])
    sync_part_status(core)


# ---------------------------------------------------------------------------------------
# Generic part services that write a status directly. A core's part status follows its
# stage, so each of these asks here first: for an ordinary part the answer is "not a
# core, carry on"; for a core the change is made to the STAGE, and the part follows.
# ---------------------------------------------------------------------------------------

def scrap_if_core(part, *, reason: str = '') -> bool:
    """Scrap `part` as a core if it plays one — a stage change — and return True.

    Returns False for an ordinary part; the caller then writes SCRAPPED itself. Call it
    BEFORE writing the part's own status, so the stage's work-order cascade sees the
    scrapped unit.
    """
    from Tracker.services.reman.core import scrap_core
    from Tracker.services.reman.core_steps import core_of

    core = core_of(part)
    if core is None:
        return False
    if core.status != 'SCRAPPED':
        scrap_core(core, reason=reason)
    return True


def release_from_order_if_core(part) -> bool:
    """Take a core that was never started off its work order, and return True.

    For an ordinary part a smaller order CANCELS its unstarted units. A core is a
    customer's or the bank's unit, not one the order made, so it is not cancelled: it
    goes back to the bank, received and unplanned, as it was before it was planned.
    Returns False for an ordinary part.
    """
    from Tracker.services.reman.core_steps import core_of

    core = core_of(part)
    if core is None:
        return False
    if core.status != 'RECEIVED':
        raise ValueError(
            f"Core {core.core_number} has started {core.get_status_display().lower()}; "
            "only a core not yet started can be taken off its order"
        )
    move_core(core, work_order=None, step=None)
    return True


def assert_status_settable(part, new_status) -> None:
    """Refuse a direct status change that would contradict a core's stage.

    A QA hold, or any in-flow status, may be set on a core's part as on any part — the
    next stage change re-derives it. An ENDING may not: a core ends by its reman stage
    (rebuilt, returned, harvested, scrapped), and a part marked COMPLETED under a core
    still "in teardown" is two answers to one question. Scrapping is allowed and routed
    through the stage by the caller (`scrap_if_core`); un-ending is refused, since the
    stage would stay ended.
    """
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES
    from Tracker.services.reman.core_steps import core_of

    core = core_of(part)
    if core is None or new_status == PartsStatus.SCRAPPED or new_status == part.part_status:
        return
    if core.status in ENDED_STAGES:
        raise ValueError(
            f"{core.core_number} is a core that has ended ({core.get_status_display()}); "
            "its status follows its reman stage and cannot be reopened here"
        )
    if part.part_status == PartsStatus.CORE_BANKED:
        raise ValueError(
            f"{core.core_number} is in the core bank; plan its teardown to put it to work"
        )
    if new_status in TERMINAL_PART_STATUSES:
        raise ValueError(
            f"{core.core_number} is a core; it ends by its reman stage — rebuild, return, "
            "harvest or scrap it — not by setting its part status"
        )
