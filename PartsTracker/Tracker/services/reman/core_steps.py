"""Reman hooks on the part step engine.

A core is a part (Documents/CORE_AS_PART_DESIGN.md), so it moves through its process on
the same engine as any part — `services.mes.parts.advance_part_step` — and gets
sampling, material consumption, batch completion, rework and DWI with it. What is
genuinely reman lives here, as hooks the engine calls. Each is a no-op for a part that
plays no core role, so the engine can call them unconditionally.

This replaces `services/mes/cores.py`, a mirror of the part engine that cores had to be
walked through separately — which is why no core had ever run through DWI.
"""
from __future__ import annotations

def core_of(part):
    """The core role this part plays, or None for an ordinary part.

    The core is bound to THIS part instance. The reman services write the part status
    through `core.part`, and the engine then saves its own `part`; were those two
    Python objects, the engine's save would silently overwrite the status the stage
    just derived.
    """
    if part is None or not part.pk:
        return None
    from Tracker.models import Core
    try:
        core = part.core_role
    except Core.DoesNotExist:
        return None
    core.part = part
    return core


def assert_workable(part) -> None:
    """Refuse work on a unit a lead has parked for the customer's authorisation.

    `AWAITING_AUTHORISATION` is a person's decision — the unit waits until the customer
    answers — so nothing may be started, captured or advanced on it until someone
    records that answer. Deliberately not a start-gate refusal: those can be overridden
    with a supervisor's credentials, and a supervisor cannot answer for the customer.
    """
    from django.core.exceptions import ValidationError

    core = core_of(part)
    if core is not None and core.status == 'AWAITING_AUTHORISATION':
        raise ValidationError(
            f"{core.core_number} is waiting on the customer's authorisation. Record their "
            "answer on the core before any more work is done on it."
        )


def on_step_started(part, operator=None) -> None:
    """A step has begun on this unit. The first one on a RECEIVED core starts teardown."""
    core = core_of(part)
    if core is not None and core.status == 'RECEIVED':
        from Tracker.services.reman.core import start_core_disassembly
        start_core_disassembly(core, operator)


def finish_route(part, operator=None) -> bool:
    """The unit reached the end of what it needed. Returns True when that was a core.

    Which ending depends on which half of its life the core was in: a rebuild finishes
    REBUILT, a teardown DISASSEMBLED. The engine must not then apply a step's terminal
    status on top — the core's part status is derived from its stage, not from the
    step it happened to finish on.
    """
    core = core_of(part)
    if core is None:
        return False
    if core.status == 'IN_REBUILD':
        from Tracker.services.reman.rebuild_execution import complete_rebuild
        complete_rebuild(core, operator)
    elif core.status == 'IN_DISASSEMBLY':
        from Tracker.services.reman.core import complete_core_disassembly
        complete_core_disassembly(core, operator)
    else:
        # Reached the end from a stage with no ending of its own (RECEIVED on a
        # one-step route, say): nothing to transition, but still not a step-terminal
        # status — re-derive from the stage.
        from Tracker.services.reman.core_part import sync_part_status
        sync_part_status(core)
    return True


def after_advance(part) -> None:
    """Re-derive a core part's status after the engine moved it.

    The engine writes IN_PROGRESS on entering a step. That is right for a core being
    worked, but the stage is the source of truth, so a core's status is re-derived
    rather than trusting the engine's generic write.
    """
    core = core_of(part)
    if core is not None:
        from Tracker.services.reman.core_part import sync_part_status
        sync_part_status(core)
