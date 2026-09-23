"""Rebuild slot resolution.

For a torn-down core, answers two questions at once: what goes back into it, and
what has to be done to it. See `Documents/REMAN_REBUILD_LOOP_DESIGN.md` §6.

The shape is **assignment, not netting**. Classical kitting nets quantities because
raw material is fungible; a harvested nozzle is not — it carries its own grade, its
own life and its own provenance, and two of the same part number are not
interchangeable to the customer, to quality or to cost. So a rebuild BOM explodes
into positioned SLOTS of quantity one, and each slot is bound to an identified
individual.

The other half of the shape: a slot's resolution can emit OPERATIONS rather than
demand. "Recondition the nozzle" and "replace the nozzle" resolve the same slot;
one is work, the other is a part. That is why scope and kit are one decision here
rather than two passes.

**This module writes nothing.** It is a proposal, for a screen to render and a
person to curate, and it deliberately has no side effects so it can be called on a
core nobody has committed to rebuilding yet.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

# Grades that mean "fit to go back in as-is" versus "fit only after work". There is
# no per-line acceptance criterion yet (the BOM carries `allow_harvested`, a boolean,
# and nothing about grade) — so this is the DEFAULT policy, stated in one place
# rather than scattered, and the thing to replace when slots gain real criteria.
SERVICEABLE_GRADES = ('A', 'B')
RECONDITIONABLE_GRADES = ('C',)

# Resolutions a slot can take. The first two emit operations or nothing; the last two
# emit demand. The vocabulary lives on the model (`SLOT_RESOLUTION_CHOICES`) because
# `RebuildSlotOverride` stores it — these are names for the same values, not a second
# copy of them.
REUSE = 'REUSE'
RECONDITION = 'RECONDITION'
REPLACE_POOL = 'REPLACE_POOL'
REPLACE_BUY = 'REPLACE_BUY'


@dataclass(frozen=True)
class Candidate:
    """Something that could fill a slot, whatever world it lives in."""
    kind: str                  # 'HARVESTED_THIS_CORE' | 'HARVESTED_POOL' | 'PURCHASED'
    id: str
    label: str
    grade: str | None
    detail: str = ''


@dataclass(frozen=True)
class Slot:
    """One position on the rebuild, and what we propose to put in it."""
    position: str
    component_type_id: str
    component_type_name: str
    bom_line_id: str | None
    finding: str               # what teardown found here, in plain words
    resolution: str
    reason: str
    candidates: list = field(default_factory=list)
    # Set when a person overrode the proposal. `proposed_resolution` keeps what the
    # system would have done, because "the planner disagreed" is only legible next to
    # what they disagreed with.
    is_overridden: bool = False
    proposed_resolution: str = ''
    override_id: str = ''

    @property
    def needs_decision(self) -> bool:
        """Whether a person should look at this row.

        REUSE is the unremarkable outcome — the part came out serviceable and goes
        back. Everything else costs money or time, so the screen opens on those.
        """
        return self.resolution != REUSE


@dataclass(frozen=True)
class RebuildPlan:
    core_id: str
    core_number: str
    fulfilment_mode: str
    bom_revision: str | None
    entry_scope: str | None = None
    slots: list = field(default_factory=list)
    operations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _positions_for(core_type, component_type, quantity: int, bom_line=None) -> list:
    """Position labels for a component on this core type.

    Prefers the teardown BOM's `positions`, which is the neat part: the positions a
    component came OUT of are the positions it goes back INTO, and that list is
    already authored and already validated to match `expected_qty`. Falls back to the
    assembly line's `reference_designator`, then to anonymous ordinals — position is
    optional by design, since high-volume exchange does not care which of four
    identical nozzles goes in which bore.
    """
    from Tracker.models import DisassemblyBOMLine

    line = DisassemblyBOMLine.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
        core_type=core_type, component_type=component_type, is_current_version=True,
        archived=False,
    ).first()
    if line and line.positions and len(line.positions) >= quantity:
        return list(line.positions[:quantity])

    # A single `reference_designator` names ONE slot, so it only stands in when the
    # line is quantity 1. Spreading one designator across N slots would label four
    # bores with the same name, which is worse than leaving them unlabelled.
    if quantity == 1 and bom_line is not None and bom_line.reference_designator:
        return [bom_line.reference_designator]

    return [''] * quantity


def _harvested_by_position(core):
    """This core's own usable components, keyed by (component_type_id, position)."""
    out = {}
    loose = {}
    for hc in (core.harvested_components
               .filter(is_scrapped=False, archived=False)
               .select_related('component_type')):
        key = (str(hc.component_type_id), hc.position or '')
        out.setdefault(key, []).append(hc)
        loose.setdefault(str(hc.component_type_id), []).append(hc)
    return out, loose


def _pool_candidates(component_type, core):
    """Accepted harvest from OTHER cores, admissible only if this core may pool.

    Deliberately excludes anything reserved to a different core — `reserved_for_core`
    is the existing rule and this is a read of it, not a second copy.
    """
    from Tracker.models import Parts

    if not core.allows_pooled_harvest:
        return []
    qs = (
        Parts.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            part_type=component_type, reserved_for_core__isnull=True, archived=False)
        .exclude(harvested_from__isnull=True)
        .select_related('harvested_from')[:5]
    )
    return [
        Candidate(
            kind='HARVESTED_POOL', id=str(p.id), label=p.ERP_id,
            grade=getattr(p.harvested_from, 'condition_grade', None),
            detail='recovered stock',
        )
        for p in qs
    ]


def _purchased_candidates(component_type):
    """Stock lots of this component type — new or used-purchased alike.

    `MaterialLot` holds purchased PART TYPES as well as raw material, which is what
    makes a component bought from a core specialist an ordinary BUY line. Note it
    carries no condition grade, so a used-purchased lot cannot be ranked against
    graded harvest (see the design's open question 7).
    """
    from Tracker.models import MaterialLot

    qs = MaterialLot.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
        material_type=component_type, quantity_remaining__gt=0, archived=False,
    ).select_related('supplier')[:5]
    return [
        Candidate(
            kind='PURCHASED', id=str(lot.id), label=lot.lot_number, grade=None,
            detail=f"{lot.quantity_remaining} on hand"
                   + (f" — {lot.supplier.name}" if lot.supplier_id else ''),
        )
        for lot in qs
    ]


def _resolve_slot(core, component_type, position, bom_line, own, loose, warnings, torn_down=True):
    """Propose a resolution for one slot, and say why.

    The reason is not decoration: a planner confirming "grade B, original, within
    spec" is doing something different from one confirming a blank default, and the
    over-and-above quote has to show a customer WHY a line costs money.
    """
    ct_id = str(component_type.id)
    key = (ct_id, position or '')

    # Prefer the component that came out of this very position; fall back to one of
    # the same type from this core when teardown recorded no position.
    mine = (own.get(key) or [None])[0]
    if mine is None and not position:
        mine = (loose.get(ct_id) or [None])[0]

    candidates = []
    if mine is not None:
        candidates.append(Candidate(
            kind='HARVESTED_THIS_CORE', id=str(mine.id),
            label=mine.original_part_number or str(mine),
            grade=mine.condition_grade, detail='from this unit',
        ))
    candidates += _pool_candidates(component_type, core)
    candidates += _purchased_candidates(component_type)

    if mine is not None and mine.condition_grade in SERVICEABLE_GRADES:
        return Slot(
            position=position, component_type_id=ct_id,
            component_type_name=component_type.name,
            bom_line_id=str(bom_line.id) if bom_line else None,
            finding=f"Grade {mine.condition_grade}, from this unit",
            resolution=REUSE,
            reason='serviceable as found',
            candidates=candidates,
        )

    if mine is not None and mine.condition_grade in RECONDITIONABLE_GRADES:
        return Slot(
            position=position, component_type_id=ct_id,
            component_type_name=component_type.name,
            bom_line_id=str(bom_line.id) if bom_line else None,
            finding=f"Grade {mine.condition_grade}, from this unit",
            resolution=RECONDITION,
            reason='below serviceable grade — work needed before it goes back',
            candidates=candidates,
        )

    if mine is not None:
        finding = f"Grade {mine.condition_grade}"
    elif torn_down:
        finding = 'not recovered from this unit'
    else:
        # Before teardown NOTHING has been recovered, so "not recovered" would read as
        # a missing part rather than an unopened unit. The distinction matters: one is
        # a shortage, the other is an estimate.
        finding = 'not torn down yet'
    pool = [c for c in candidates if c.kind == 'HARVESTED_POOL']
    if pool:
        return Slot(
            position=position, component_type_id=ct_id,
            component_type_name=component_type.name,
            bom_line_id=str(bom_line.id) if bom_line else None,
            finding=finding, resolution=REPLACE_POOL,
            reason=f"{len(pool)} in recovered stock",
            candidates=candidates,
        )

    if not core.allows_pooled_harvest and mine is None:
        warnings.append(
            f"{component_type.name} at {position or 'unpositioned'}: this unit goes back "
            "to its customer, so recovered stock from other cores is not offered."
        )
    return Slot(
        position=position, component_type_id=ct_id,
        component_type_name=component_type.name,
        bom_line_id=str(bom_line.id) if bom_line else None,
        finding=finding, resolution=REPLACE_BUY,
        # Before teardown this is a worst-case estimate, not a shortage — saying
        # "nothing serviceable available" of an unopened unit would read as a finding.
        reason=('teardown may yet recover this — costed as a purchase'
                if not torn_down else 'nothing serviceable available'),
        candidates=candidates,
    )


def _apply_overrides(core, slots, slot_lines):
    """Replace proposed resolutions with the planner's, where one was recorded.

    Keyed on (bom_line, position) — the same pair that identifies a slot — so an
    override survives re-running the proposal, which is the whole point: the plan is
    recomputed on every request and a decision must not be.
    """
    from Tracker.models import RebuildSlotOverride

    overrides = {
        (str(o.bom_line_id), o.position or ''): o
        for o in RebuildSlotOverride.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            core=core, archived=False)
    }
    if not overrides:
        return slots

    out = []
    for slot, line in zip(slots, slot_lines):
        o = overrides.get((str(line.id), slot.position or ''))
        if o is None:
            out.append(slot)
            continue
        out.append(replace(
            slot,
            resolution=o.resolution,
            reason=o.reason,
            is_overridden=True,
            proposed_resolution=slot.resolution,
            override_id=str(o.id),
        ))
    return out


def resolve_rebuild_plan(core) -> RebuildPlan:
    """Propose what goes back into `core`, slot by slot. Writes nothing.

    Scope is NOT route-filtered yet: the released assembly BOM is taken whole,
    because resolving which operations a unit needs is the step before this one and
    is not built. That is recorded as a warning rather than hidden, since an
    unfiltered BOM over-states the kit on a branched process — the same defect
    `pick_list.py` has today.
    """
    from Tracker.services.mes.bom_explosion import _released_bom

    warnings = []
    bom = _released_bom(core.core_type)
    if bom is None:
        return RebuildPlan(
            core_id=str(core.id), core_number=core.core_number,
            fulfilment_mode=core.fulfilment_mode, bom_revision=None,
            entry_scope=None, slots=[], operations=[],
            warnings=[
                f"No released assembly BOM for {core.core_type.name}. A rebuild kit "
                "cannot be proposed until one is released."
            ],
        )

    own, loose = _harvested_by_position(core)
    torn_down = core.status == 'DISASSEMBLED'
    if not torn_down:
        warnings.append(
            "This core has not finished teardown, so nothing has been recovered from it "
            "yet and every slot reads as a purchase. Useful as a worst-case estimate of "
            "what a rebuild would cost — not as a kit."
        )
    slots = []
    slot_lines = []   # parallel to `slots`: the BOM line each slot came from
    # `.objects` scopes by tenant but does NOT exclude soft-deleted rows, so every
    # query in this module says `archived=False` explicitly.
    lines = (bom.lines.filter(archived=False)
             .select_related('component_type').order_by('line_number'))
    for line in lines:
        if line.component_type_id is None:
            continue  # a raw-material line has no instance identity to assign
        qty = int(line.quantity or 1)
        positions = _positions_for(core.core_type, line.component_type, qty, bom_line=line)
        for i in range(qty):
            slots.append(_resolve_slot(
                core, line.component_type, positions[i], line, own, loose, warnings,
                torn_down=torn_down,
            ))
            slot_lines.append(line)

    # Overrides land BEFORE scope is derived. A planner who changes a slot from
    # replace-to-recondition is changing what work the unit needs, so scope has to be
    # computed from the decided resolutions rather than the proposed ones.
    slots = _apply_overrides(core, slots, slot_lines)

    # Scope is derived FROM the resolved slots, not beside them: a repair code is a
    # slot resolution that emits operations (§6.4), so resolving the two separately
    # is how they drift apart.
    from Tracker.services.reman.scope import resolve_scope

    scope = resolve_scope(core, slots)
    warnings.extend(scope.warnings)

    # Now that the scope exists, drop slots the unit does not actually reach. A BOM
    # line consumed at a step outside this rebuild's operations is not part of this
    # kit — which is the over-picking defect `pick_list.py` still has on any branched
    # process. Only filter when scope resolved something: with no codes authored,
    # filtering would empty the kit rather than narrow it.
    scoped_step_ids = scope.step_ids
    if scoped_step_ids:
        in_scope, dropped = [], 0
        for slot, line in zip(slots, slot_lines):
            step_id = str(line.consumed_at_step_id) if line.consumed_at_step_id else None
            # A line with no consuming step cannot be placed, so it stays rather than
            # being silently dropped by a filter it was never subject to.
            if step_id is None or step_id in scoped_step_ids:
                in_scope.append(slot)
            else:
                dropped += 1
        slots = in_scope
        if dropped:
            warnings.append(
                f"{dropped} BOM line(s) are consumed at operations outside this "
                "rebuild's scope and are not in the kit."
            )
    else:
        warnings.append(
            "No operations were resolved, so the kit below is the whole released BOM "
            "rather than what this unit needs. Expect it to over-state."
        )

    return RebuildPlan(
        core_id=str(core.id), core_number=core.core_number,
        fulfilment_mode=core.fulfilment_mode,
        bom_revision=bom.revision, entry_scope=scope.entry_scope,
        slots=slots, operations=scope.operations, warnings=warnings,
    )
