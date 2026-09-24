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

from django.utils import timezone


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


def on_step_started(part, operator=None) -> None:
    """A step has begun on this unit. The first one on a RECEIVED core starts teardown."""
    core = core_of(part)
    if core is not None and core.status == 'RECEIVED':
        from Tracker.services.reman.core import start_core_disassembly
        start_core_disassembly(core, operator)


def _scoped_step_ids(core):
    """Operations this unit's rebuild actually needs, or None if scope does not apply.

    None — "walk the route as authored" — for anything not under rebuild. Teardown has
    no resolved scope: every core goes through the same disassembly, which is why
    teardown can batch and rebuild cannot.

    Recomputed rather than stored. A scope change mid-rebuild is the same class of
    event as a process change mid-Op, which this system answers with a deliberate
    migration disposition rather than a silent freeze.
    """
    if core.status not in ('IN_REBUILD', 'AWAITING_AUTHORISATION'):
        return None
    from Tracker.services.reman.rebuild import resolve_rebuild_plan
    from Tracker.services.reman.scope import resolve_scope

    plan = resolve_rebuild_plan(core)
    # An empty scope means nothing was resolved — codes unauthored, say. Falling back
    # to the authored route is the safe direction: the unit does too much work rather
    # than skipping everything and arriving "rebuilt" untouched.
    return resolve_scope(core, plan.slots).step_ids or None


def skip_out_of_scope(part, next_step, operator=None):
    """Walk past operations this unit's rebuild does not need, recording each SKIPPED.

    SKIPPED rather than silently absent: the traveler has to show what was
    deliberately not done — the difference between "we chose not to" and "we forgot",
    which matters most on a customer's own unit. Returns the next step to enter, or
    None when the rest of the route is out of scope.

    Bounded by the number of steps in the process, since a cyclic route (rework
    edges) would otherwise spin here.
    """
    core = core_of(part)
    if core is None or next_step is None:
        return next_step
    scoped_ids = _scoped_step_ids(core)
    if scoped_ids is None:
        return next_step

    from Tracker.models import ProcessStep, StepExecution

    process = part.work_order.process if part.work_order_id else None
    limit = (ProcessStep.objects.filter(process=process).count() + 1) if process else 1  # tenant-safe: scoped by `process` FK
    hops = 0
    previous = part.step
    try:
        while next_step is not None and str(next_step.id) not in scoped_ids and hops < limit:
            StepExecution.objects.create(
                part=part,
                step=next_step,
                visit_number=StepExecution.objects.filter(part=part, step=next_step).count() + 1,  # tenant-safe: scoped by `part` FK
                status='SKIPPED',
                exited_at=timezone.now(),
                completed_by=operator,
            )
            # Route from the skipped step without moving the unit there.
            part.step = next_step
            next_step = part.get_next_step(None)
            hops += 1
    finally:
        part.step = previous
    return next_step


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
