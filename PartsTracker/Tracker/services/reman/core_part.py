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
    'DECLINED': PartsStatus.AWAITING_PICKUP,
    'RETURNED': PartsStatus.SHIPPED,
    'RETURNED_UNREPAIRED': PartsStatus.SHIPPED,
    # Taken apart; its components are parts of their own now. Terminal but not output.
    'HARVESTED': PartsStatus.DISMANTLED,
    'SCRAPPED': PartsStatus.SCRAPPED,
}


def part_status_for(stage: str, *, on_work_order: bool) -> str:
    """The part status a core part must carry at reman `stage`."""
    if stage == 'RECEIVED':
        return PartsStatus.PENDING if on_work_order else PartsStatus.CORE_BANKED
    try:
        return _BY_STAGE[stage]
    except KeyError:
        raise ValueError(f"No part status is defined for reman stage {stage!r}") from None
