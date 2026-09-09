"""BOM explosion → in-house component work orders (make-side, MRP-lite).

Given an assembly work order, walk its released ASSEMBLY BOM. For each **MAKE** line, net
the required quantity against available supply (on-hand accepted stock of the component +
quantity already on live component WOs pegged to this parent + line), and create a child
WorkOrder for the shortfall — pegged to the parent WO and BOM line. The CP-SAT solver
already turns that peg into a cross-WO precedence (child finish + staging ≤ the parent's
`consumed_at_step` start; see `services/scheduling/solver.py`), so this service only has to
*populate* the pegs. Recurses for multi-level BOMs (a component that is itself an assembly).

**BUY** lines are recorded in the result for the buy-side availability pass (Phase 2), not
acted on here.

Known Phase-1 limitations (honest scope):
- On-hand netting is not a hard *reservation*: two assembly WOs exploded against the same
  limited stock can each count it. A real allocation/reservation ledger is future work
  (the inventory ledger itself is a documented Phase-2 in `services/mes/inventory.py`).
- A component's build process is resolved as the single APPROVED, current, non-disassembly
  `Processes` for its part type. If there are zero or several, the line is reported `short`
  (we don't guess a routing) rather than guessed.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

logger = logging.getLogger(__name__)

# MaterialLot statuses that count as on-hand, consumable supply.
_AVAILABLE_LOT_STATUSES = ('ACCEPTED', 'IN_USE')
# WorkOrder statuses that count as live (in-flight supply, not cancelled / shipped out).
_LIVE_WO_STATUSES = ('PENDING', 'IN_PROGRESS', 'ON_HOLD', 'WAITING_FOR_OPERATOR')
# Guard against pathological / self-referential BOMs.
_MAX_DEPTH = 12


@dataclass
class ExplodeResult:
    """What an explosion did / would do, aggregated across the whole tree."""
    created: list = field(default_factory=list)  # {wo, component, qty, process}
    netted: list = field(default_factory=list)   # {component, required, covered}
    buy: list = field(default_factory=list)      # {component, required}
    short: list = field(default_factory=list)    # {component, required, reason}

    def merge(self, other: "ExplodeResult") -> None:
        self.created += other.created
        self.netted += other.netted
        self.buy += other.buy
        self.short += other.short

    def as_summary(self) -> dict:
        return {
            'created_count': len(self.created),
            'created': [
                {
                    'work_order_id': str(c['wo'].id) if c['wo'] is not None else None,
                    'erp_id': c['wo'].ERP_id if c['wo'] is not None else None,
                    'component': c['component'],
                    'quantity': c['qty'],
                    'process': c['process'],
                }
                for c in self.created
            ],
            'netted': self.netted,
            'buy': self.buy,
            'short': self.short,
        }


def _released_bom(part_type):
    """The effective released ASSEMBLY BOM for a part type, or None (leaf / purchased).

    The latest RELEASED version — deliberately NOT gated on `is_current_version`. Opening a
    draft revision flips the released row to non-current (the draft becomes the chain head),
    but the released BOM is still what the floor builds to until the draft is itself released.
    Gating on is_current_version would make an open draft silently erase the production BOM.
    """
    from Tracker.models import BOM
    return (
        BOM.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            part_type=part_type, bom_type='ASSEMBLY', status='RELEASED')
        .order_by('-version').first()
    )


def _build_process(component_type):
    """The single APPROVED, current, non-disassembly process that builds `component_type`.
    Returns (process, None) on a unique match, else (None, reason) — we never guess which
    routing to use when it's ambiguous."""
    from Tracker.models import Processes
    procs = list(
        Processes.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            part_type=component_type, status='APPROVED',
            is_current_version=True, is_disassembly=False)[:2]
    )
    if not procs:
        return None, "no approved build process for this component"
    if len(procs) > 1:
        return None, "several approved build processes — none designated"
    return procs[0], None


def _available_supply(component_type, parent_wo, line) -> Decimal:
    """Existing supply that offsets a MAKE line's requirement: finished in-house stock of
    the component (Parts marked IN_STOCK) + quantity already on live component WOs pegged
    to this (parent, line). The pegged term makes re-explosion idempotent. (MAKE
    components are in-house PartTypes — their inventory is Parts, not MaterialLots, which
    now only track purchased Materials.)"""
    from Tracker.models import Parts, PartsStatus, WorkOrder
    on_hand = Parts.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
        part_type=component_type, part_status=PartsStatus.IN_STOCK).count()
    pegged = (
        WorkOrder.objects.filter(  # tenant-safe: .objects auto-scopes to the request tenant
            pegged_to_workorder=parent_wo, pegged_to_bom_line=line,
            workorder_status__in=_LIVE_WO_STATUSES)
        .aggregate(s=Sum('quantity'))['s'] or 0
    )
    return Decimal(on_hand) + Decimal(pegged)


def explode_work_order(work_order, user=None, create: bool = True, _seen=None, _depth: int = 0) -> ExplodeResult:
    """Explode `work_order`'s released BOM into pegged component WOs (see module docstring).

    `create=False` does a shallow (top-level) dry run — it reports what *would* be made
    without creating WOs and without recursing. `create=True` creates + pegs child WOs and
    recurses through multi-level BOMs. Returns an `ExplodeResult`.
    """
    from Tracker.models import BOMLine
    from Tracker.services.mes.work_order import plan_work_order

    result = ExplodeResult()
    part_type = work_order.process.part_type if work_order.process_id else None
    if part_type is None or _depth > _MAX_DEPTH:
        return result
    if _seen is None:
        _seen = {part_type.id}

    bom = _released_bom(part_type)
    if bom is None:
        return result  # leaf / no assembly BOM → nothing to explode

    # tenant-safe: `bom` is a tenant-scoped row; its lines belong to the same tenant.
    lines = BOMLine.objects.filter(bom=bom).select_related('component_type', 'material')
    for line in lines:
        if line.is_optional:
            continue
        required = Decimal(line.quantity) * Decimal(work_order.quantity)

        if line.source == 'BUY':
            # Purchased — the buy-side pass (material gate / sourcing report) handles it.
            # Never spawns a child WO, whether it's a raw Material or a buyable PartType:
            # a bought part is procured, not produced, even though we could make it.
            from Tracker.services.mes.bom import buy_line_item
            buy = buy_line_item(line)
            if buy is not None:
                result.buy.append({'component': buy.name, 'buy_kind': buy.kind,
                                   'material_id': str(buy.id),
                                   'required': float(required)})
            else:
                # BUY with no component, or pointing at a make-only part type — an
                # authoring error that would otherwise vanish silently.
                result.short.append({
                    'component': line.component_label,
                    'required': float(required),
                    'reason': 'BUY line has no purchasable component set',
                })
            continue

        # --- MAKE line (in-house component / PartType) ----------------------
        comp = line.component_type
        if comp is None:
            continue  # MAKE line without an in-house component set (misconfigured)
        available = _available_supply(comp, work_order, line)
        shortfall = required - available
        if shortfall <= 0:
            result.netted.append({'component': comp.name, 'required': float(required),
                                  'covered': float(available)})
            continue
        if comp.id in _seen:
            result.short.append({'component': comp.name, 'required': float(shortfall),
                                 'reason': 'BOM cycle — component depends on itself'})
            continue
        proc, reason = _build_process(comp)
        if proc is None:
            result.short.append({'component': comp.name, 'required': float(shortfall),
                                 'reason': reason})
            continue

        qty = int(math.ceil(shortfall))
        if not create:  # shallow preview — don't create, don't recurse
            result.created.append({'wo': None, 'component': comp.name, 'qty': qty,
                                   'process': proc.name})
            continue

        child = plan_work_order(
            tenant=work_order.tenant, process=proc, quantity=qty, user=user,
            auto_explode=False,  # this service owns the recursion, not plan_work_order
            apply_yield=True,    # `qty` is good components needed → start more for scrap
        )
        child.pegged_to_workorder = work_order
        child.pegged_to_bom_line = line
        child.save(update_fields=['pegged_to_workorder', 'pegged_to_bom_line'])
        result.created.append({'wo': child, 'component': comp.name, 'qty': qty,
                               'process': proc.name})
        # recurse for multi-level BOMs, guarding against cycles
        result.merge(explode_work_order(
            child, user=user, create=True, _seen=_seen | {comp.id}, _depth=_depth + 1))

    return result


def explode_work_order_tx(work_order, user=None, create: bool = True) -> ExplodeResult:
    """`explode_work_order` wrapped in its own transaction — the entry point for the
    explicit re-explode action (auto-explode from `plan_work_order` already runs inside
    that call's transaction)."""
    with transaction.atomic():
        result = explode_work_order(work_order, user=user, create=create)
    logger.info("Exploded WO %s: created=%d netted=%d buy=%d short=%d by user=%s",
                work_order.ERP_id, len(result.created), len(result.netted),
                len(result.buy), len(result.short), getattr(user, 'id', None))
    return result
