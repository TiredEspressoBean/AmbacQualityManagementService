"""Tool and fixture life (gate redesign S5, user decisions 2026-11-11).

Durable tooling — fixtures, dies, molds, jigs — is an Equipments row. An equipment
type with a life-limit definition (`LifeLimitDefinition.equipment_type`) is
life-limited, the way `requires_calibration` makes a type calibrated; each item
carries its own `LifeTracking`. Consumable tooling (inserts, drills) is Material and
has no life here.

A visit's tools are its TOOL / FIXTURE equipment (`StepExecutionEquipment`): stamped
at start from the step's authored affinity, or added when a work instruction captures
one. Life is counted by the definition's unit:

- ``parts``  — distinct parts started with the tool (a part's repeat visit isn't
  counted again);
- ``cycles`` — each run: a load counts once, however many parts it holds;
- ``hours``  — the run's time, when it completes (a load's once, at its completion).

At the soft limit the tool's owners are notified. At the hard limit the step's opt-in
``tool_life`` gate refuses the start, and a capture refuses the tool, until the tool is
reset (refurbished) or an extension is approved. No supervisor override.

A Fixture with an equipment type takes its scheduling capacity from the type's items
that are in service and within life (`fixture_capacity`).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal

from Tracker.services.life_tracking.life_tracking import amount

UNIT_PARTS, UNIT_CYCLES, UNIT_HOURS = 'parts', 'cycles', 'hours'
TOOL_ROLES = ('TOOL', 'FIXTURE')

# Inside a load start: the (visit, tool) runs waiting to be counted. Counting waits
# until every member has started, so the whole load is checked against the tool's
# life before it, and a cycle is counted once for the load. None outside one.
_load_runs: ContextVar[list | None] = ContextVar('tool_life_load_runs', default=None)


@contextmanager
def one_cycle_per_load(*, cycle_counted: bool = False):
    """Starting a load's members: count its tools once every member has started.
    `cycle_counted`: parts joining a load already running — its cycle was counted
    when it started, so only their parts count."""
    token = _load_runs.set([])
    try:
        yield
        runs = _load_runs.get()
    finally:
        _load_runs.reset(token)
    cycles_counted: set = set()
    for execution, equipment in runs:
        count_start(execution, equipment, cycles_counted=cycles_counted,
                    skip_cycles=cycle_counted)


def _unit(tracking) -> str:
    return (tracking.definition.unit or '').strip().lower()


def definitions_for(equipment_type_id) -> list:
    from Tracker.models import LifeLimitDefinition
    if equipment_type_id is None:
        return []
    return list(LifeLimitDefinition.objects.filter(  # tenant-safe: .objects auto-scopes
        equipment_type_id=equipment_type_id, is_current_version=True, archived=False))


def life_limited_type_ids() -> set:
    from Tracker.models import LifeLimitDefinition
    return set(LifeLimitDefinition.objects.filter(  # tenant-safe: .objects auto-scopes
        equipment_type__isnull=False, is_current_version=True, archived=False,
    ).values_list('equipment_type_id', flat=True))


def is_tooling(equipment, limited_types: set | None = None) -> bool:
    """A life-limited item that isn't a scheduled machine: tooling."""
    limited = life_limited_type_ids() if limited_types is None else limited_types
    return (equipment is not None and not equipment.is_schedulable
            and equipment.equipment_type_id in limited)


def ensure_trackings(equipment) -> list:
    """The item's life trackings, one per definition of its type: created at the count
    carried from an earlier version of the limit, else zero."""
    from Tracker.models import LifeTracking
    from Tracker.services.life_tracking.life_tracking import carried_count
    out = []
    for definition in definitions_for(equipment.equipment_type_id):
        tracking = LifeTracking.objects.for_object(equipment).filter(definition=definition).first()  # tenant-safe: .objects auto-scopes
        if tracking is None:
            carried = carried_count(equipment, definition)
            tracking, _ = LifeTracking.for_object(
                equipment, definition, accumulated=carried if carried is not None else Decimal(0))
        out.append(tracking)
    return out


def _trackings(equipment) -> list:
    from Tracker.models import LifeTracking
    return list(LifeTracking.objects.for_object(equipment).select_related('definition'))  # tenant-safe: .objects auto-scopes


def at_hard_limit(equipment) -> list:
    """Its trackings at the hard limit, against current limits only (a revised limit
    leaves its old version's tracking behind)."""
    return [t for t in _trackings(equipment)
            if t.definition.is_current_version and not t.definition.archived and t.is_blocked]


def _limit_text(equipment, tracking) -> str:
    return (f"{equipment.name} has reached its life limit ({tracking.definition.name}: "
            f"{amount(tracking.current_value)} of {amount(tracking.effective_hard_limit)} "
            f"{tracking.definition.unit_label.lower()}) — reset it after refurbishment, "
            "or get an extension approved.")


# --- the tools of a visit ---------------------------------------------------

def authored_tools(step) -> list:
    """The tooling the step's author named (a dialed-in or preferred affinity)."""
    from Tracker.models import StepEquipmentAffinity
    aff = StepEquipmentAffinity.Affinity
    limited = life_limited_type_ids()
    if not limited:
        return []
    links = (StepEquipmentAffinity.objects  # tenant-safe: .objects auto-scopes
             .filter(step=step, archived=False, affinity__in=[aff.DIALED_IN, aff.PREFERRED])
             .select_related('equipment'))
    rank = {aff.DIALED_IN: 0, aff.PREFERRED: 1}
    ordered = sorted(links, key=lambda l: (rank.get(l.affinity, 9), l.equipment.name))
    return [l.equipment for l in ordered if is_tooling(l.equipment, limited)]


def visit_tools(execution) -> list:
    from Tracker.models.qms import StepExecutionEquipment
    if execution is None or not execution.pk:
        return []
    return [l.equipment for l in StepExecutionEquipment.objects  # tenant-safe: FK-correlated to a scoped visit
            .filter(step_execution=execution, role__in=TOOL_ROLES).select_related('equipment')]


def start_refusals(step, execution=None) -> list[tuple]:
    """Each tool a start would use that is at its hard limit, as (tool, why).

    A tool the visit recorded (DWI capture) is the one in use: at its limit, it refuses.
    With none recorded, the step's authored tools are interchangeable — the plan counts
    them as one pool — so they refuse only when NONE of them is within life, naming
    each (user ruling 2026-11-16; scheduling review item 10)."""
    return _tool_refusals(step, execution) + _pool_refusals(step)


def _tool_refusals(step, execution=None) -> list[tuple]:
    recorded = visit_tools(execution)
    if recorded:
        tools = {e.id: e for e in recorded}
        return [(e, _limit_text(e, t)) for e in tools.values() for t in at_hard_limit(e)]
    authored = {e.id: e for e in authored_tools(step)}
    limits = {e.id: at_hard_limit(e) for e in authored.values()}
    if not authored or any(not hits for hits in limits.values()):
        return []
    return [(e, _limit_text(e, t)) for e in authored.values() for t in limits[e.id]]


def pool_items(fixture) -> list:
    """A tracked tooling pool's items, current and not archived."""
    from Tracker.models import Equipments
    if fixture.equipment_type_id is None:
        return []
    return list(Equipments.objects.filter(  # tenant-safe: .objects auto-scopes
        equipment_type_id=fixture.equipment_type_id, archived=False, is_current_version=True)
        .order_by('name'))


def _pool_refusals(step) -> list[tuple]:
    """Each tracked tooling pool the step needs (Steps.required_tooling, 10b) with no
    item in service and within life — each needed pool must have one (user ruling
    2026-11-16). A pool without tracked items (an NC program, a typed quantity) has no
    life to read and never refuses here; it only limits the plan. `(item or None, why)`."""
    out = []
    for f in step.required_tooling.filter(archived=False, equipment_type__isnull=False):
        items = pool_items(f)
        if any(e.status == 'IN_SERVICE' and not at_hard_limit(e) for e in items):
            continue
        out.append((items[0] if items else None,
                    f"None of {f.name} is usable — every one is out of service or at its life "
                    f"limit. Return one to service, or reset or extend one."))
    return out


def plan_capacity_changed(tracking) -> None:
    """A tool's tracking crossed into or out of its hard limit (counted to it, reset,
    extended): the tooling the plan counted on changed, so the plan is stale
    (scheduling review item 10). Not on every count — only a crossing changes
    capacity."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import Equipments
    from Tracker.services.scheduling.staleness import mark_active_schedule_stale
    if tracking.content_type_id == ContentType.objects.get_for_model(Equipments).id:
        mark_active_schedule_stale(tracking.tenant_id)


# --- counting -------------------------------------------------------------

def _count(tracking, equipment, by) -> None:
    soft = tracking.effective_soft_limit
    before = tracking.current_value
    was_blocked = tracking.is_blocked
    tracking.increment(by)
    if soft is not None and before < soft <= tracking.current_value:
        _notify_soft_limit(tracking, equipment)
    if tracking.is_blocked != was_blocked:
        plan_capacity_changed(tracking)


def _counted_part_before(equipment, execution) -> bool:
    from Tracker.models.qms import StepExecutionEquipment
    if not execution.part_id:
        return False
    return (StepExecutionEquipment.objects  # tenant-safe: FK-correlated to a scoped visit
            .filter(equipment=equipment, role__in=TOOL_ROLES,
                    step_execution__part_id=execution.part_id)
            .exclude(step_execution=execution).exists())


def count_start(execution, equipment, *, cycles_counted: set | None = None,
                skip_cycles: bool = False) -> None:
    """A run with `equipment` began on this visit: count its parts and cycles. Inside a
    load start it is queued until the load has started (`one_cycle_per_load`)."""
    pending = _load_runs.get()
    if pending is not None:
        pending.append((execution, equipment))
        return
    seen = cycles_counted
    repeat_part = None
    for tracking in ensure_trackings(equipment):
        unit = _unit(tracking)
        if unit == UNIT_PARTS:
            if repeat_part is None:
                repeat_part = _counted_part_before(equipment, execution)
            if not repeat_part:
                _count(tracking, equipment, 1)
        elif unit == UNIT_CYCLES:
            if skip_cycles:
                continue
            if seen is not None:
                if tracking.id in seen:
                    continue
                seen.add(tracking.id)
            _count(tracking, equipment, 1)


def stamp(execution, equipment, role='TOOL') -> bool:
    """Put `equipment` on the visit as a tool; True when it wasn't there already."""
    from Tracker.models.qms import StepExecutionEquipment
    _, created = StepExecutionEquipment.objects.get_or_create(  # tenant-safe: FK-correlated to a scoped visit
        step_execution=execution, equipment=equipment, role=role)
    return created


def on_start(execution) -> None:
    """The visit started: the authored tool it runs with goes on it, and every tool on
    it is counted. The step's authored tools are interchangeable (one pool), so only
    one is in use: the first within life — counting them all wore tools that weren't
    used (scheduling review item 10). With a tool already captured, that's the one."""
    if execution.step_id is None:
        return
    if not visit_tools(execution):
        usable = [e for e in authored_tools(execution.step) if not at_hard_limit(e)]
        if usable:
            stamp(execution, usable[0])
    # Each tracked pool the step needs (10b): one of its items is in use — the first
    # usable — unless one of that type is already on the visit.
    on_visit_types = {e.equipment_type_id for e in visit_tools(execution)}
    for pool in execution.step.required_tooling.filter(archived=False, equipment_type__isnull=False):
        if pool.equipment_type_id in on_visit_types:
            continue
        usable = [e for e in pool_items(pool)
                  if e.status == 'IN_SERVICE' and not at_hard_limit(e)]
        if usable:
            stamp(execution, usable[0])
    for equipment in visit_tools(execution):
        count_start(execution, equipment)


def capture(execution, equipment, role) -> list[str]:
    """A work instruction captured a tool on the visit. Refused at its hard limit; a new
    one is put on the visit and counted. Returns the soft-limit warnings."""
    from django.core.exceptions import ValidationError
    blocked = at_hard_limit(equipment)
    if blocked:
        raise ValidationError(_limit_text(equipment, blocked[0]))
    if execution is not None and stamp(execution, equipment, role):
        count_start(execution, equipment)
    return [f"{equipment.name} is near its life limit ({t.definition.name}: "
            f"{amount(t.current_value)} of {amount(t.effective_hard_limit)}) — tell tooling."
            for t in _trackings(equipment) if t.status == 'WARNING']


def _hours(start, end) -> Decimal:
    if start is None or end is None or end <= start:
        return Decimal(0)
    return Decimal(str(round((end - start).total_seconds() / 3600, 2)))


def _add_hours(equipment, hours) -> None:
    if hours <= 0:
        return
    for tracking in ensure_trackings(equipment):
        if _unit(tracking) == UNIT_HOURS:
            _count(tracking, equipment, hours)


def in_load(execution) -> bool:
    from Tracker.models import BatchExecution
    if not execution.part_id or execution.started_at is None:
        return False
    return BatchExecution.objects.filter(  # tenant-safe: .objects auto-scopes
        step_id=execution.step_id, parts=execution.part_id,
        started_at__gte=execution.started_at).exists()


def on_complete(execution) -> None:
    """A visit completed: its tools accrue the run's hours. A load's are counted once,
    when the load completes (`on_load_complete`)."""
    if in_load(execution):
        return
    hours = _hours(execution.started_at, execution.exited_at)
    for equipment in visit_tools(execution):
        _add_hours(equipment, hours)


def on_load_complete(batch) -> None:
    from Tracker.models import Equipments, StepExecution
    from Tracker.models.qms import StepExecutionEquipment
    visits = StepExecution.objects.filter(  # tenant-safe: .objects auto-scopes
        step_id=batch.step_id, part__in=batch.parts.all(), started_at__lte=batch.started_at,
    ).exclude(exited_at__lt=batch.started_at)
    ids = set(StepExecutionEquipment.objects.filter(  # tenant-safe: FK-correlated to scoped visits
        step_execution__in=visits, role__in=TOOL_ROLES).values_list('equipment_id', flat=True))
    hours = _hours(batch.started_at, batch.completed_at)
    for equipment in Equipments.objects.filter(id__in=ids):  # tenant-safe: .objects auto-scopes
        _add_hours(equipment, hours)


def _notify_soft_limit(tracking, equipment) -> None:
    from django.db import transaction
    from Tracker.services.core.notifications import emit
    from Tracker.services.mes.events import ToolLifeWarningPayload
    payload = ToolLifeWarningPayload(
        id=str(tracking.id), tenant_id=str(tracking.tenant_id),
        equipment_id=str(equipment.id), equipment_name=equipment.name,
        limit_name=tracking.definition.name,
        current=amount(tracking.current_value),
        soft_limit=amount(tracking.effective_soft_limit),
        hard_limit=amount(tracking.effective_hard_limit),
    )
    key = f"tool_life.warning:{tracking.id}:{tracking.updated_at.isoformat()}"
    transaction.on_commit(lambda: emit('tool_life.warning', tenant=tracking.tenant,
                                       payload=payload, correlation_id=f"tool:{equipment.id}",
                                       idempotency_key=key))


# --- scheduling capacity --------------------------------------------------

def fixture_capacity(fixture) -> int:
    """How many of a Fixture can be in use at once. With an equipment type: its items
    in service and within life. Without one (an NC program, untracked tooling): the
    typed quantity."""
    from Tracker.models import Equipments
    if fixture.equipment_type_id is None:
        return fixture.quantity
    items = Equipments.objects.filter(  # tenant-safe: .objects auto-scopes
        equipment_type_id=fixture.equipment_type_id, status='IN_SERVICE', archived=False,
        is_current_version=True)
    return sum(1 for e in items if not at_hard_limit(e))
