"""Rebuild scope resolution.

Turns a unit's findings into the set of operations its rebuild needs. See
`Documents/REMAN_REBUILD_LOOP_DESIGN.md` §3.3 and §6.4.

Two layers, because every mature MRO system keeps both:

- the **entry scope** — what was quoted and sold before anything was found. An
  engine shop sells "performance restoration"; a `RebuildScopePreset` is that.
- the **accumulated scope** — what the findings added. Each slot resolution raises
  a `RepairCode`, and the codes compose.

The gap between them is the over-and-above story: a unit ships having had a set of
operations no tier name describes.

**This module writes nothing.** Like the slot resolver it feeds, it is a proposal.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScopedOperation:
    """One operation the rebuild needs, and what put it there."""
    step_id: str
    step_name: str
    code: str
    code_name: str
    # Plain-language provenance: "Standard rebuild" for the entry scope, or the
    # slots whose findings raised it. Without this a planner sees a list of
    # operations with no way to challenge any of them.
    because: list = field(default_factory=list)


@dataclass(frozen=True)
class ResolvedScope:
    entry_scope: str | None
    operations: list = field(default_factory=list)
    raised_codes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def step_ids(self) -> set:
        return {op.step_id for op in self.operations}


def default_preset_for(core_type):
    """The entry scope proposed for this core type, or None if none is configured."""
    from Tracker.models import RebuildScopePreset

    return (
        # `archived=False` everywhere in this module: `.objects` scopes by TENANT
        # only — it does not exclude soft-deleted rows — so a retired code or level
        # would go on adding operations to every job it once matched.
        RebuildScopePreset.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            core_type=core_type, is_default=True, is_current_version=True,
            archived=False,
        )
        .prefetch_related('codes__steps')
        .first()
    )


def resolve_scope(core, slots, preset=None) -> ResolvedScope:
    """The operations this unit's rebuild needs, given its resolved slots.

    `slots` are the `Slot` objects from `services.reman.rebuild` — scope is derived
    FROM them rather than beside them, because a repair code is a slot resolution
    that emits operations (§6.4). Resolving the two separately is how they drift.
    """
    from Tracker.models import RepairCode

    warnings = []
    preset = preset if preset is not None else default_preset_for(core.core_type)

    # code id -> (RepairCode, [reasons])
    raised: dict = {}

    def _raise(code, because: str):
        entry = raised.setdefault(code.id, (code, []))
        if because not in entry[1]:
            entry[1].append(because)

    if preset is not None:
        for code in preset.codes.filter(archived=False):
            _raise(code, preset.name)
    else:
        warnings.append(
            "No default rebuild scope is configured for this core type, so the scope "
            "is only what the findings raised. A shop that sells named rebuild levels "
            "should author one."
        )

    # Codes raised by findings. Matched on (component type, resolution), with a
    # null component_type meaning "whatever the component" — whole-unit work like a
    # final test, which is raised by any slot taking that resolution.
    resolutions = {s.resolution for s in slots}
    candidates = (
        RepairCode.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            is_current_version=True, archived=False, trigger__in=resolutions)
        .prefetch_related('steps')
        .select_related('component_type')
    )
    by_trigger: dict = {}
    for code in candidates:
        by_trigger.setdefault(code.trigger, []).append(code)

    for slot in slots:
        for code in by_trigger.get(slot.resolution, []):
            if code.component_type_id and str(code.component_type_id) != slot.component_type_id:
                continue
            where = slot.position or slot.component_type_name
            _raise(code, f"{where}: {slot.finding}")

    # ALWAYS codes are base scope whatever the findings — the operations you do to
    # every unit of this type. They are raised even when no preset names them, since
    # "always" is a property of the code rather than of a sales level.
    for code in (
        RepairCode.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            is_current_version=True, archived=False, trigger='ALWAYS')
        .prefetch_related('steps')
    ):
        _raise(code, 'always')

    operations = []
    seen_steps = set()
    for code, because in raised.values():
        # `archived=False` here too — this was missed in the first sweep. A retired
        # operation still hanging off a live code would have gone on the job.
        # NB: deliberately NOT filtered on `is_current_version`. The M2M points at a
        # specific Step row, and if that row has been superseded, showing the
        # superseded operation is better than silently dropping it — the
        # version-drift question is recorded as design open question 8.
        for step in code.steps.filter(archived=False):
            # A step reached by two codes is ONE operation. Attributing it to the
            # first code that raised it would hide the second reason, so the reasons
            # merge onto the operation instead.
            key = str(step.id)
            if key in seen_steps:
                for op in operations:
                    if op.step_id == key:
                        for b in because:
                            if b not in op.because:
                                op.because.append(b)
                        break
                continue
            seen_steps.add(key)
            operations.append(ScopedOperation(
                step_id=key, step_name=step.name,
                code=code.code, code_name=code.name,
                because=list(because),
            ))

    if not operations and preset is None:
        warnings.append(
            "No repair codes matched this unit's findings, so no operations were "
            "resolved. Until codes are authored, the kit below is the whole BOM "
            "rather than what this unit needs."
        )

    return ResolvedScope(
        entry_scope=preset.name if preset is not None else None,
        operations=operations,
        raised_codes=[c.code for c, _ in raised.values()],
        warnings=warnings,
    )
