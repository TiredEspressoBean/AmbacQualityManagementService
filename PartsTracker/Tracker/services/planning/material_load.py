"""Material demand, time-phased into the RCCP buckets.

The third lane. Capacity answers "can we build it"; this answers "will we have the
parts", on the same grid so both read off one picture.

Two things make it different from a capacity lane, and both matter:

1. **A material has no capacity, it has a balance.** A work centre offers so many hours
   *per bucket*; stock is a quantity that sits there until something consumes it. So the
   comparison is cumulative — demand through bucket N against everything on hand plus
   everything arriving by then — the same shape CTP uses for capacity, and for the same
   reason: an order due in March may draw on stock that arrives in February.

2. **Demand lands at the planned START, not the due date.** Material is consumed while
   the job runs, so an order released in January to ship in April needs its parts in
   January. Placing them at the due date is the classic way to be three months late and
   look fine on the report.

Deliberately NOT a projected available balance. A real PAB rolls stock forward bucket by
bucket, nets gross requirements, and offsets by lead time to emit planned order releases.
This is the honest first approximation: cumulative demand against cumulative supply, so a
bucket goes red the moment commitments outrun what will exist by then.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

# On-hand is usable stock; incoming is inbound and not yet usable. They must stay
# disjoint or accepted stock is counted twice — once as held, once as promised.
_ON_HAND_STATUSES = ('ACCEPTED', 'IN_USE')
_TERMINAL_STATUSES = ('CONSUMED', 'SCRAPPED', 'REJECTED', 'RETURNED', 'CANCELLED', 'SHIPPED')


def material_series(tenant, buckets, wo_starts: dict, extra_demand: list | None = None) -> list:
    """Per material: demand per bucket, and the stock left after it.

    `wo_starts` maps work-order id -> the bucket index its work begins in, which the
    caller already computed when placing capacity load. Reusing it is the point: the
    material lane and the capacity lanes then agree about when a job runs, instead of
    each deciding separately and disagreeing on the same screen.

    `extra_demand` is demand not yet carried by work orders — open order lines (and, in
    time, forecast): `[{'part_type_id', 'quantity', 'idx', 'band'}]`, placed at the bucket
    its work would start in. Unlike a work order, whose MAKE components are child work
    orders with their own demand, nothing carries these components yet, so the BOM is
    exploded through its MAKE lines down to what is bought (2026-11-02). The quantity is
    grossed up by the routing's expected yield first, as planning a work order would.
    Each bucket's demand is also broken out by `band`.
    """
    from django.db.models import Q
    from Tracker.models import BOM, BOMLine, MaterialLot, Processes, WorkOrder
    from Tracker.services.mes.bom import buy_line_item

    n = len(buckets)
    extra_demand = extra_demand or []
    if not n or not (wo_starts or extra_demand):
        return []

    # process -> part type, so a work order can find its BOM without another query each.
    # tenant-safe: explicit tenant filter
    pt_of_process = {
        r['id']: r['part_type_id']
        for r in Processes.objects.filter(tenant=tenant).values('id', 'part_type_id')
    }

    bom_lines: dict = {}

    def _lines(part_type_id):
        if part_type_id not in bom_lines:
            # Latest RELEASED, not is_current_version — an open DRAFT revision must not
            # hide the BOM the floor is actually building to.
            bom = (BOM.objects.filter(archived=False, tenant=tenant, part_type_id=part_type_id,
                                      bom_type='ASSEMBLY', status='RELEASED')
                   .order_by('-version').first())
            # tenant-safe: `bom` is a tenant-scoped row; its lines belong to the same tenant.
            bom_lines[part_type_id] = list(
                BOMLine.objects.filter(archived=False, bom=bom)
                .select_related('material', 'component_type')
                if bom else [])
        return bom_lines[part_type_id]

    # demand[(kind, id)][bucket] = quantity. Keyed by kind as well as id because a BUY
    # line can point at a raw Material or a buyable PartType, and both stock as lots.
    demand: dict = defaultdict(lambda: [0.0] * n)
    by_band: dict = defaultdict(lambda: defaultdict(lambda: [0.0] * n))  # key -> band -> buckets
    names: dict = {}
    safety: dict = {}   # (kind, id) -> buffer held back from planning
    items: dict = {}    # (kind, id) -> BuyItem, for the export's keys and units

    def _add(buy, qty: float, idx: int, band: str):
        demand[buy.key][idx] += qty
        by_band[buy.key][band][idx] += qty
        if buy.key not in names:
            names[buy.key] = buy.name
            safety[buy.key] = buy.safety_stock
            items[buy.key] = buy

    # tenant-safe: explicit tenant filter
    for wo in (WorkOrder.objects.filter(tenant=tenant, id__in=list(wo_starts))
               .values('id', 'process_id', 'quantity')):
        idx = wo_starts.get(wo['id'])
        if idx is None or not (0 <= idx < n):
            continue
        pt = pt_of_process.get(wo['process_id'])
        if pt is None:
            continue
        for line in _lines(pt):
            # MAKE lines are their own work orders with their own demand; optional lines
            # aren't commitments. Counting either here double-books the plan.
            if line.is_optional:
                continue
            buy = buy_line_item(line)
            if buy is None:
                continue
            _add(buy, float(Decimal(str(line.quantity)) * wo['quantity']), idx, 'firm')

    # Demand no work order carries yet: explode through MAKE lines, since no child work
    # order exists to carry the components.
    started_qty: dict = {}

    def _started(part_type_id, good: float) -> float:
        """Grossed up for the routing's expected scrap, as planning a work order is."""
        from Tracker.services.mes.bom_explosion import _build_process
        from Tracker.services.mes.yield_planning import start_quantity_for_good
        if part_type_id not in started_qty:
            started_qty[part_type_id] = _build_process(part_type_id)[0]
        proc = started_qty[part_type_id]
        if proc is None or good <= 0:
            return good
        return float(start_quantity_for_good(proc, int(-(-good // 1))))

    def _explode(part_type_id, qty: float, idx: int, band: str, depth: int, seen: frozenset):
        if depth > 10 or part_type_id in seen:  # a BOM cycle is an authoring error; stop
            return
        for line in _lines(part_type_id):
            if line.is_optional:
                continue
            line_qty = float(Decimal(str(line.quantity))) * qty
            buy = buy_line_item(line)
            if buy is not None:
                _add(buy, line_qty, idx, band)
            elif line.source == 'MAKE' and line.component_type_id:
                _explode(line.component_type_id, _started(line.component_type_id, line_qty),
                         idx, band, depth + 1, seen | {part_type_id})

    for d in extra_demand:
        idx = d['idx']
        if idx is None or not (0 <= idx < n) or d['quantity'] <= 0:
            continue
        _explode(d['part_type_id'], _started(d['part_type_id'], d['quantity']), idx,
                 d.get('band', 'firm'), 0, frozenset())

    if not demand:
        return []

    keys = list(demand)
    mat_ids = [k[1] for k in keys if k[0] == 'MATERIAL']
    pt_ids = [k[1] for k in keys if k[0] == 'PART_TYPE']
    # One lot table, two columns: a raw Material's stock hangs off `material`, a bought
    # part's off `material_type`. Query both and fold into the same (kind, id) space.
    lot_scope = Q(material_id__in=mat_ids) | Q(material_type_id__in=pt_ids)

    def _key(row):
        return (('MATERIAL', row['material_id']) if row['material_id'] is not None
                else ('PART_TYPE', row['material_type_id']))

    on_hand: dict = {}
    # Our stock only: customer property covers only its owner's work, which this
    # aggregate view can't attribute — undercounting is the safe side for a capacity gate.
    for r in (MaterialLot.objects.filter(archived=False, tenant=tenant, status__in=_ON_HAND_STATUSES,
                                         owner__isnull=True)
              .filter(lot_scope)
              .values('material_id', 'material_type_id', 'quantity_remaining')):
        k = _key(r)
        on_hand[k] = on_hand.get(k, 0.0) + float(r['quantity_remaining'] or 0)

    # Incoming, placed in the bucket it is promised for — a receipt that lands in March
    # cannot cover a February commitment.
    incoming: dict = defaultdict(lambda: [0.0] * n)
    for lot in (MaterialLot.objects.filter(archived=False,
            tenant=tenant, promised_date__isnull=False, quantity_remaining__gt=0)
            .filter(lot_scope)
            .exclude(status__in=_ON_HAND_STATUSES + _TERMINAL_STATUSES + ('QUARANTINE',))  # held: not supply
            .values('material_id', 'material_type_id', 'promised_date',
                    'quantity_remaining')):
        for i, b in enumerate(buckets):
            if b.start.date() <= lot['promised_date'] < b.end.date():
                incoming[_key(lot)][i] += float(lot['quantity_remaining'] or 0)
                break

    # How each item is bought, for the outlook export: quantities stay in stock units,
    # with the purchase unit and its conversion beside them for whoever orders.
    from Tracker.models import Material, PartTypes
    buying: dict = {}
    for kind, model, ids in (('MATERIAL', Material, mat_ids), ('PART_TYPE', PartTypes, pt_ids)):
        if ids:
            for r in (model.objects.filter(tenant=tenant, id__in=ids)  # tenant-safe: explicit tenant filter
                      .values('id', 'purchase_unit', 'units_per_purchase_unit')):
                buying[(kind, r['id'])] = r

    out = []
    for mid in keys:
        # Opening cover is free stock, not physical stock: the safety buffer is held back
        # so the row goes red while there is still something on the shelf to react with.
        # Without it "will we have it" is knife-edge at zero, which is where the warning
        # arrives too late to place an order against.
        series, cum_demand = [], 0.0
        cover = on_hand.get(mid, 0.0) - safety.get(mid, 0.0)
        for i, b in enumerate(buckets):
            cum_demand += demand[mid][i]
            cover += incoming[mid][i]
            # What's LEFT after everything committed through this bucket. A quantity,
            # not a ratio: it falls as commitments accrue, goes negative exactly when
            # you're short, and the number itself is the thing a planner acts on.
            #
            # A percentage was wrong here. For a capacity row both sides are hours in
            # that bucket, so 13% for eleven months means eleven months of steady work.
            # For a material the numerator is cumulative and the denominator is a stock
            # level, so the same 13% held flat means one month of demand and then
            # nothing — the same glyph reading the opposite way on adjacent rows.
            remaining = cover - cum_demand
            series.append({
                'bucket': b.label,
                'demand': round(demand[mid][i], 2),
                # Where this bucket's demand comes from: firm (work orders and confirmed
                # order lines), tentative (RFI), forecast (unclaimed forecast).
                'demand_by_band': {band: round(v[i], 2) for band, v in by_band[mid].items()},
                'cumulative_demand': round(cum_demand, 2),
                'available': round(cover, 2),
                'remaining_cover': round(remaining, 2),
                'short': remaining < 0,
            })
        kind, item_id = mid
        item, buy = items[mid], buying.get(mid, {})
        per = buy.get('units_per_purchase_unit')
        out.append({'id': str(item_id), 'kind': kind,
                    'name': names.get(mid, str(item_id)),
                    # What a buyer keys into the ERP: part number / ERP id.
                    'part_number': item.part_number,
                    'unit_of_measure': item.unit_of_measure,
                    'purchase_unit': buy.get('purchase_unit') or 'STOCK',
                    'units_per_purchase_unit': float(per) if per is not None else None,
                    'on_hand': round(on_hand.get(mid, 0.0), 2),
                    'incoming': round(sum(incoming[mid]), 2),
                    'safety_stock': safety.get(mid, 0.0), 'series': series})

    out.sort(key=lambda m: m['name'])
    return out
