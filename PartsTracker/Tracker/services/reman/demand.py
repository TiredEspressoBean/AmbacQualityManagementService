"""What a reman work order actually needs — per core, by where each core is.

A new build needs its BOM times its quantity. A reman work order does not: its
process belongs to the core type, so reading it that way asks for a full rebuild kit
per core — for an exchange core that is only being harvested, and for a
repair-and-return unit's own nozzles and bodies, which go back into it. Consumption,
the material gate and the pick sheet already treat those as supplied by the unit
itself; planning was the one surface that did not.

The reman route is ONE process holding both teardown and rebuild steps, so the
process cannot tell the stages apart. The core's status can, and the rebuild plan
already says, slot by slot, what each unit needs. So demand is read per core:

| Core                                        | Demand                                  |
|---------------------------------------------|-----------------------------------------|
| exchange, in teardown                       | none — it is supply, not demand         |
| exchange, disassembled                      | none — rebuild or harvest is undecided  |
| any, in rebuild (or awaiting authorisation) | the rebuild plan                        |
| repair-and-return, disassembled             | the rebuild plan (findings are in)      |
| repair-and-return, not yet torn down        | a FORECAST from the authored fallout    |
| anything finished, returned or harvested    | none                                    |

From the plan: REPLACE_BUY is a purchase, REPLACE_POOL draws recovered stock,
REUSE and RECONDITION need nothing. Raw-material lines carry no slot, so a unit
being rebuilt needs them whole.

The forecast is kept apart from firm demand for the same reason recoverable supply
is kept apart from on-hand: nobody knows which parts a unit will lose until it is
opened. Reported beside the buy figure, never inside it — so purchasing can choose to
buy ahead, and is never made to.
"""
from __future__ import annotations

from dataclasses import dataclass

# Findings are in and a rebuild is under way or decided.
PLAN_STATES = frozenset({'IN_REBUILD', 'AWAITING_AUTHORISATION'})
# Not yet opened (or being opened): nothing recovered, nothing known.
PRE_TEARDOWN_STATES = frozenset({'RECEIVED', 'IN_DISASSEMBLY'})

REPLACE_POOL = 'REPLACE_POOL'
REPLACE_BUY = 'REPLACE_BUY'


@dataclass(frozen=True)
class LineDemand:
    """One BOM line's demand across the cores on one work order."""
    #: Known to be needed: a purchase (or, for a MAKE line, a build).
    firm: float = 0.0
    #: Expected replacements on units not yet opened. Never netted.
    forecast: float = 0.0
    #: Replacements recovered stock may fill — only on units that take pooled parts.
    #: Counted whether the plan resolved them to the pool or to a purchase: a
    #: REPLACE_BUY on an exchange rebuild is a purchase only because the pool was
    #: empty when the plan was drawn, and teardown is what would refill it.
    pool_eligible: float = 0.0


def _uses_plan(core) -> bool:
    if core.status in PLAN_STATES:
        return True
    # Disassembled: a repair-and-return unit is going back together, so its findings
    # are its demand. An exchange unit may be rebuilt or harvested, and until someone
    # decides it asks for nothing.
    return core.status == 'DISASSEMBLED' and core.returns_to_customer


def _uses_forecast(core) -> bool:
    return core.status in PRE_TEARDOWN_STATES and core.returns_to_customer


def fallout_rate(core_type_id, component_type_id) -> float | None:
    """The authored share of this component a core of this type loses in teardown,
    or None when nobody has authored one."""
    from Tracker.models import DisassemblyBOMLine

    line = (DisassemblyBOMLine.objects  # tenant-safe: .objects auto-scopes to the request tenant
            .filter(core_type_id=core_type_id, component_type_id=component_type_id,
                    is_current_version=True, archived=False)
            .only('expected_fallout_rate').first())
    return float(line.expected_fallout_rate) if line is not None else None


def work_order_line_demand(work_order, lines) -> dict:
    """`{bom_line_id: LineDemand}` for a reman work order's BOM `lines`.

    Lines with no demand are omitted. Call only for a work order that carries cores;
    a new build's demand is its BOM times its quantity, as it always was.
    """
    from Tracker.services.mes.bom import line_allows_recovery
    from Tracker.services.reman.rebuild import resolve_rebuild_plan

    firm: dict = {}
    forecast: dict = {}
    pool: dict = {}

    def add(bucket, line_id, qty):
        if qty:
            bucket[line_id] = bucket.get(line_id, 0.0) + qty

    lines = list(lines)
    for core in work_order.cores.filter(archived=False).select_related('core_type'):
        if _uses_plan(core):
            by_line: dict = {}
            for slot in resolve_rebuild_plan(core).slots:
                if slot.bom_line_id:
                    by_line.setdefault(slot.bom_line_id, []).append(slot.resolution)
            for line in lines:
                if line.component_type_id is None:
                    # Raw material carries no slot and no identity: a unit being
                    # rebuilt needs the line whole.
                    add(firm, line.id, float(line.quantity or 0))
                    continue
                resolutions = by_line.get(str(line.id), [])
                replacements = sum(1 for r in resolutions if r in (REPLACE_BUY, REPLACE_POOL))
                add(firm, line.id, float(sum(1 for r in resolutions if r == REPLACE_BUY)))
                if core.allows_pooled_harvest and line_allows_recovery(line):
                    add(pool, line.id, float(replacements))
        elif _uses_forecast(core):
            for line in lines:
                qty = float(line.quantity or 0)
                if line.component_type_id is None or not line_allows_recovery(line):
                    # Expendables and raw material are replaced every time, opened
                    # or not — that part of the kit is not a guess.
                    add(firm, line.id, qty)
                    continue
                rate = fallout_rate(core.core_type_id, line.component_type_id)
                # No authored rate: assume the worst, as the rebuild plan does for an
                # unopened unit. Safe here because a forecast is reported, not bought.
                add(forecast, line.id, qty * (rate if rate is not None else 1.0))

    return {
        line_id: LineDemand(firm=firm.get(line_id, 0.0),
                            forecast=forecast.get(line_id, 0.0),
                            pool_eligible=pool.get(line_id, 0.0))
        for line_id in set(firm) | set(forecast) | set(pool)
    }


def takes_pooled_parts(work_order) -> bool:
    """Whether recovered stock may go into anything on this work order.

    Narrower than "is reman": a repair-and-return unit keeps its own parts and is never
    offered the pool (`Core.allows_pooled_harvest`), so only a work order carrying an
    exchange unit qualifies. A new build never does.
    """
    return any(core.allows_pooled_harvest
               for core in work_order.cores.filter(archived=False))
