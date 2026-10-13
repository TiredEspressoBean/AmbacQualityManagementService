"""Rebuild scope resolution.

Turns a unit's findings into the repair codes its rebuild raises, and the repairs those
codes send it to. Scope PLANS the rebuild — the kit, the over-and-above question, the
rebuild plan's "expected repairs" — and no longer routes the unit: every op on the main
line runs, and a repair is a Repair node a check sends the unit down when its code is
raised (services/reman/repair_routing, 2026-10-12).

Two layers, because every mature MRO system keeps both:

- the **entry scope** — what was quoted and sold before anything was found. An
  engine shop sells "performance restoration"; a `RebuildScopePreset` is that.
- the **accumulated scope** — what the findings added. Each slot resolution raises
  a `RepairCode`, and the codes compose.

The gap between them is the over-and-above story: a unit ships having had a set of
repairs no tier name describes.

**This module writes nothing.** Like the slot resolver it feeds, it is a proposal.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExpectedRepair:
    """One repair this rebuild is expected to take, and what put it there."""
    step_id: str
    step_name: str
    code: str
    code_name: str
    # Plain-language provenance: "Standard rebuild" for the entry scope, or the
    # slots whose findings raised it. Without this a planner sees a list of
    # repairs with no way to challenge any of them.
    because: list = field(default_factory=list)
    # The check that offers this repair, and whether the unit can go down it without
    # anyone approving it first. `needs_approval` is the early warning: seek the lead's
    # or the customer's answer before the unit gets to the check.
    check_name: str = ''
    needs_approval: bool = False


@dataclass(frozen=True)
class ResolvedScope:
    entry_scope: str | None
    expected_repairs: list = field(default_factory=list)
    raised_codes: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def step_ids(self) -> set:
        return {r.step_id for r in self.expected_repairs}


def default_preset_for(core_type):
    """The entry scope proposed for this core type, or None if none is configured."""
    from Tracker.models import RebuildScopePreset

    return (
        # `archived=False` everywhere in this module: `.objects` scopes by TENANT
        # only — it does not exclude soft-deleted rows — so a retired code or level
        # would go on raising repairs on every job it once matched.
        RebuildScopePreset.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            core_type=core_type, is_default=True, is_current_version=True,
            archived=False,
        )
        .prefetch_related('codes')
        .first()
    )


def resolve_scope(core, slots, preset=None) -> ResolvedScope:
    """The repair codes this unit's rebuild raises, and the repairs they'll route it
    to, given its resolved slots.

    `slots` are the `Slot` objects from `services.reman.rebuild` — scope is derived
    FROM them rather than beside them, because a repair code is raised by a slot
    resolution. Resolving the two separately is how they drift.
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
    ):
        _raise(code, 'always')

    expected = _expected_repairs(core, raised)

    if not raised:
        warnings.append(
            "No repair codes matched this unit's findings, so no repairs are expected. "
            "Every operation on its route still runs."
        )

    return ResolvedScope(
        entry_scope=preset.name if preset is not None else None,
        expected_repairs=expected,
        raised_codes=[c.code for c, _ in raised.values()],
        warnings=warnings,
    )


def _expected_repairs(core, raised: dict) -> list:
    """The Repair nodes in this unit's process that its raised codes send it to.

    One entry per Repair node, matched on the code string so a code that versions keeps
    its repairs. A unit with no process yet (before it has a work order) has none.
    """
    from Tracker.models import StepEdge

    part = getattr(core, 'part', None)
    process = part.work_order.process if part is not None and part.work_order_id else None
    if process is None or not raised:
        return []
    because_by_code = {code.code: (code, because) for code, because in raised.values()}
    approved = set(core.approved_repair_codes or [])
    sold = set()
    preset = default_preset_for(core.core_type)
    if preset is not None:
        sold = {c.code for c in preset.codes.filter(archived=False)}

    by_step: dict = {}
    for edge in (StepEdge.objects  # tenant-safe: scoped by the process FK
                 .filter(process=process, to_step__repair_code__code__in=list(because_by_code))
                 .select_related('from_step', 'to_step__repair_code')
                 .order_by('id')):
        step = edge.to_step
        code, because = because_by_code[step.repair_code.code]
        key = str(step.id)
        entry = by_step.get(key)
        ok = edge.pre_approved or code.code in approved or code.code in sold
        if entry is None:
            by_step[key] = ExpectedRepair(
                step_id=key, step_name=step.name, code=code.code, code_name=code.name,
                because=list(because), check_name=edge.from_step.name,
                needs_approval=not ok,
            )
        elif ok and entry.needs_approval:
            # Offered at two checks, pre-approved at one: it can go ahead there.
            by_step[key] = ExpectedRepair(**{**entry.__dict__, 'needs_approval': False})
    return list(by_step.values())
