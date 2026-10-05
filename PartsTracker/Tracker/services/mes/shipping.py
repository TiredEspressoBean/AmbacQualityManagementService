"""Shipping to the customer — the outbound half of the dock.

A part leaves on a **shipment**: one physical consignment to one customer, on one day,
under one paperwork number. Before this, shipping was only the last step of a route —
each part flipped to SHIPPED on its own, so nothing said which parts left together, on
what date, or under which packing slip, and an order line could not say how much of it
had gone.

The route's **Ship step is the queue.** A part reaching a terminal step whose
`terminal_status` is SHIPPED waits there; shipping it completes that step through
`advance_part_step`, so the step's gate (its sign-off substeps — the release check of
ISO 9001 §8.6) runs exactly as it would for one part, and the part ends SHIPPED by the
ordinary path. Finished stock (IN_STOCK, AWAITING_PICKUP) ships too, for routes that end
in the stockroom. Completing one part's Ship step by hand still works; it just leaves
no shipment behind.

Pricing, invoicing and the bill of lading's commercial side belong to the ERP. A
shipment carries the ERP's paperwork number (`reference`) so the two can be matched.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

SHIP_TERMINAL = "SHIPPED"
FROM_STOCK = ("IN_STOCK", "AWAITING_PICKUP")
# Waiting on a decision someone else owns — never offered for shipping.
NOT_SHIPPABLE = ("QUARANTINED", "REWORK_NEEDED", "REWORK_IN_PROGRESS", "ON_HOLD")


def is_ship_step(step) -> bool:
    return bool(step and step.is_terminal and (step.terminal_status or "").upper() == SHIP_TERMINAL)


def _order_of(part):
    wo = part.work_order
    return part.order or (wo.related_order if wo is not None else None)


def _customer_of(part):
    order = _order_of(part)
    return order.company if order is not None and order.company_id else None


def shippable(part) -> str | None:
    """Why ``part`` can't ship now, or None when it can."""
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES
    if part.archived:
        return "archived"
    from Tracker.services.reman.core_steps import core_of
    if core_of(part) is not None:
        # A core goes back to its owner through Remanufacturing (its RETURNED stage).
        return "a core — return it from Remanufacturing"
    if part.part_status in NOT_SHIPPABLE:
        return f"on hold ({part.get_part_status_display()})"
    if part.part_status in FROM_STOCK:
        return None
    if part.part_status in TERMINAL_PART_STATUSES:
        return f"already {part.get_part_status_display().lower()}"
    if not is_ship_step(part.step):
        return "not at a Ship step yet"
    return None


def _ready_parts(tenant):
    from django.db.models import Q
    from Tracker.models import Parts, Steps
    ship_steps = list(Steps.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, is_terminal=True, terminal_status__iexact=SHIP_TERMINAL)
        .values_list("id", flat=True))
    return (Parts.objects.filter(tenant=tenant, archived=False)  # tenant-safe: explicit tenant filter
            # Stock is offered only when it is someone's — on an order. Unclaimed stock
            # (harvested components, build-to-stock) still ships when named, but it
            # isn't a queue anyone is waiting on. Cores return through Remanufacturing.
            .filter(core_role__isnull=True)
            .filter((Q(part_status__in=FROM_STOCK)
                     & (Q(order__isnull=False) | Q(work_order__related_order__isnull=False)))
                    | (Q(step_id__in=ship_steps)
                       & ~Q(part_status__in=list(NOT_SHIPPABLE) + [
                           "COMPLETED", "SCRAPPED", "CANCELLED", "SHIPPED", "IN_STOCK",
                           "AWAITING_PICKUP", "CORE_BANKED", "RMA_CLOSED", "DISMANTLED"])))
            .select_related("part_type", "step", "order__company",
                            "work_order__related_order__company", "work_order__order_line"))


def ready_to_ship(tenant) -> list[dict]:
    """Parts that can go now, grouped by order — the shipping clerk's board.

    A group is one order (one customer); parts with no order are grouped together with
    no customer, and the clerk names who they go to when shipping."""
    groups: dict = {}
    for p in _ready_parts(tenant):
        order = _order_of(p)
        key = str(order.id) if order is not None else ""
        g = groups.get(key)
        if g is None:
            company = order.company if order is not None and order.company_id else None
            g = groups[key] = {
                "order_id": str(order.id) if order is not None else None,
                "order_number": (order.order_number or order.name) if order is not None else None,
                "customer_id": str(company.id) if company is not None else None,
                "customer_name": company.name if company is not None else None,
                "requires_coc": bool(getattr(company, "requires_coc_on_shipment", False)),
                "parts": [],
                "lots": [],
            }
        wo = p.work_order
        line = wo.order_line if wo is not None and wo.order_line_id else None
        g["parts"].append({
            "id": str(p.id),
            "erp_id": p.ERP_id,
            "part_type": p.part_type.name if p.part_type_id else None,
            "work_order": wo.ERP_id if wo is not None else None,
            "order_line": line.line_number if line is not None else None,
            "due_date": line.due_date if line is not None else None,
            "source": "STOCK" if p.part_status in FROM_STOCK else "SHIP_STEP",
            "status": p.get_part_status_display(),
        })
    # A customer's own material, still here: it can go back to them, grouped under them.
    from Tracker.models import MaterialLot
    for lot in (MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, archived=False, owner__isnull=False, holds_cores=False,
            status__in=SHIPPABLE_LOT_STATUSES, quantity_remaining__gt=0)
            .select_related("owner", "material", "material_type").order_by("lot_number")):
        key = f"owner:{lot.owner_id}"
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "order_id": None, "order_number": None,
                "customer_id": str(lot.owner_id), "customer_name": lot.owner.name,
                "requires_coc": bool(lot.owner.requires_coc_on_shipment), "parts": [], "lots": [],
            }
        g["lots"].append({
            "id": str(lot.id), "lot_number": lot.lot_number, "item_name": lot.item_name or "",
            "quantity_remaining": float(lot.quantity_remaining), "unit_of_measure": lot.unit_of_measure,
            "storage_location": lot.storage_location,
        })
    return sorted(groups.values(), key=lambda g: (g["order_number"] is None, g["order_number"] or "",
                                                  g["customer_name"] or ""))


SHIPPABLE_LOT_STATUSES = ("ACCEPTED", "IN_USE")


def ship(*, tenant, user, parts=(), lots=(), customer=None, carrier: str = "",
         tracking_number: str = "", reference: str = "", notes: str = "",
         expected_delivery: date | None = None):
    """Ship to one customer on one shipment: serialised ``parts`` and material ``lots``
    (``[{"lot": MaterialLot, "quantity": Decimal | None}]``). All or nothing.

    ``customer`` defaults to the parts' order's company, or a lot's owner; two customers
    can't share a shipment, and a customer's own lot ships only back to them. Each part at
    a Ship step completes it through ``advance_part_step`` (its gate runs); finished stock
    goes straight to SHIPPED. A lot ships whole, or — with a quantity less than what's
    left — that much is split off and the split ships.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import CustomerShipment, MaterialLot, Parts, PartsStatus, RecordEdit
    from Tracker.services.mes import inventory
    from Tracker.services.mes.material_lot import split_material_lot
    from Tracker.services.mes.parts import _cascade_work_order_completion, advance_part_step

    ids = [p.id for p in parts]
    lot_reqs = list(lots)
    if not ids and not lot_reqs:
        raise ValueError("Choose what's going.")

    with transaction.atomic():
        locked = list(Parts.objects.select_for_update(of=("self",))  # tenant-safe: explicit tenant filter
                      .filter(tenant=tenant, id__in=ids)
                      .select_related("step", "part_type", "order__company",
                                      "work_order__related_order__company"))
        if len(locked) != len(set(ids)):
            raise ValueError("Some of those parts weren't found.")
        problems = [f"{p.ERP_id}: {why}" for p in locked if (why := shippable(p))]
        locked_lots = []
        for req in lot_reqs:
            lot = (MaterialLot.objects.select_for_update(of=("self",))  # tenant-safe: explicit tenant filter
                   .select_related("owner").get(tenant=tenant, pk=req["lot"].pk))
            qty = req.get("quantity")
            qty = lot.quantity_remaining if qty in (None, "") else Decimal(str(qty))
            if lot.status not in SHIPPABLE_LOT_STATUSES or lot.holds_cores:
                problems.append(f"lot {lot.lot_number}: {lot.get_status_display().lower()}, not stock that can ship")
            elif qty <= 0 or qty > lot.quantity_remaining:
                problems.append(f"lot {lot.lot_number}: {lot.quantity_remaining} {lot.unit_of_measure} left, "
                                f"can't ship {qty}")
            locked_lots.append((lot, qty))
        if problems:
            raise ValueError("Can't ship " + "; ".join(problems))

        if customer is not None and not customer.is_customer:
            raise ValueError(f"{customer.name} isn't set up as a customer.")
        owners = {c.id: c for p in locked if (c := _customer_of(p)) is not None}
        owners.update({lot.owner_id: lot.owner for lot, _ in locked_lots if lot.owner_id})
        if customer is None:
            if len(owners) > 1:
                raise ValueError("These are for different customers — ship them separately.")
            customer = next(iter(owners.values()), None)
        elif owners and set(owners) != {customer.id}:
            raise ValueError(f"Some of this belongs to another customer, not {customer.name}.")
        if customer is None:
            raise ValueError("Nothing here is on a customer's order — say who it's going to.")
        if not customer.is_customer:
            raise ValueError(f"{customer.name} isn't set up as a customer.")

        shipment = CustomerShipment.objects.create(
            tenant=tenant, customer=customer, shipped_by=user if getattr(user, "is_authenticated", False) else None,
            carrier=carrier.strip(), tracking_number=tracking_number.strip(),
            reference=reference.strip(), notes=notes, expected_delivery=expected_delivery)

        for p in locked:
            if p.part_status in FROM_STOCK:
                p.part_status = PartsStatus.SHIPPED
                p.customer_shipment = shipment
                p.save(update_fields=["part_status", "customer_shipment"])
                _cascade_work_order_completion(p)
                continue
            p.customer_shipment = shipment
            p.save(update_fields=["customer_shipment"])
            try:
                advance_part_step(p, operator=user)
            except ValueError as e:
                raise ValueError(f"{p.ERP_id}: {e}") from e
            p.refresh_from_db(fields=["part_status"])
            if p.part_status != PartsStatus.SHIPPED:
                raise ValueError(f"{p.ERP_id} didn't finish as shipped ({p.get_part_status_display()}).")

        lot_ct = ContentType.objects.get_for_model(MaterialLot)
        for lot, qty in locked_lots:
            if qty < lot.quantity_remaining:
                lot = split_material_lot(lot, qty, reason=f"Shipped on {shipment.shipment_number}")
            # What went is recorded, so a void can put it back.
            RecordEdit.objects.create(
                tenant=tenant, content_type=lot_ct, object_id=lot.id, field_name="quantity_remaining",
                old_value=str(lot.quantity_remaining), new_value="0",
                reason=f"Shipped on {shipment.shipment_number}", edited_by=user)
            inventory.mark_lot_shipped(lot)
            lot.refresh_from_db()
            lot.quantity_remaining = Decimal("0")
            lot.customer_shipment = shipment
            lot.save(update_fields=["quantity_remaining", "customer_shipment", "updated_at"])

        orders = {o.id: o for p in locked if (o := _order_of(p)) is not None}
        transaction.on_commit(lambda: _announce(shipment, list(orders.values())))
    return shipment


def ship_parts(*, tenant, parts, user, **kwargs):
    """Serialised parts only — see ``ship``."""
    return ship(tenant=tenant, user=user, parts=parts, **kwargs)


def _announce(shipment, orders) -> None:
    """One `order.shipped` per order on the shipment. Off by default per tenant (the
    event's default_on); a rule turns it on and routes it to the customer's contacts."""
    from Tracker.services.core.notifications import emit
    from Tracker.services.mes.events import OrderShippedPayload
    for order in orders:
        emit("order.shipped", shipment.tenant, OrderShippedPayload(
            id=str(order.id), tenant_id=str(shipment.tenant_id),
            order_number=order.order_number or order.name,
            customer_id=str(shipment.customer_id), customer_name=shipment.customer.name,
            shipped_at=shipment.shipped_at, carrier=shipment.carrier,
            tracking_number=shipment.tracking_number,
            expected_delivery=shipment.expected_delivery.isoformat() if shipment.expected_delivery else None),
            idempotency_key=f"order.shipped:{shipment.id}:{order.id}")


def void_shipment(shipment, *, user, reason: str) -> None:
    """A shipment recorded by mistake — the parts didn't go. They come back to where
    they waited: a part from a Ship step is back at that step with a fresh visit (its
    sign-off runs again when it really ships); a part from stock is back in stock. A
    work order or order closed by the shipment reopens.

    Not for goods that went and came back — that is a return (RMA), a new receipt."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import (
        MaterialLot, OrdersStatus, Parts, PartsStatus, RecordEdit, StepExecution, WorkOrderStatus,
    )
    from Tracker.services.mes import inventory
    part_ct = ContentType.objects.get_for_model(Parts)

    if shipment.is_voided:
        raise ValueError("This shipment is already voided.")
    if not (reason or "").strip():
        raise ValueError("Say why the shipment is being voided.")
    with transaction.atomic():
        for p in shipment.parts.select_for_update(of=("self",)).select_related(  # tenant-safe: reverse FK from a scoped shipment
                "step", "work_order__related_order"):
            if is_ship_step(p.step):
                p.part_status = PartsStatus.IN_PROGRESS
                StepExecution.objects.create(
                    tenant=p.tenant, part=p, step=p.step, status="PENDING",
                    visit_number=StepExecution.get_visit_count_for_update(p, p.step) + 1)
            else:
                p.part_status = PartsStatus.IN_STOCK
            # The shipment keeps its list of what was on it, through this record.
            RecordEdit.objects.create(
                tenant=p.tenant, content_type=part_ct, object_id=p.id, field_name="customer_shipment",
                old_value=str(shipment.id), new_value="", reason=reason.strip(), edited_by=user)
            p.customer_shipment = None
            p.save(update_fields=["part_status", "customer_shipment"])
            wo = p.work_order
            if wo is not None and wo.workorder_status == WorkOrderStatus.COMPLETED:
                wo.workorder_status = WorkOrderStatus.IN_PROGRESS
                wo.true_completion = None
                wo.save(update_fields=["workorder_status", "true_completion"])
                order = wo.related_order
                if order is not None and order.order_status == OrdersStatus.COMPLETED:
                    order.order_status = OrdersStatus.IN_PROGRESS
                    order.save(update_fields=["order_status"])
        lot_ct = ContentType.objects.get_for_model(MaterialLot)
        for lot in shipment.material_lots.select_for_update(of=("self",)):  # tenant-safe: reverse FK from a scoped shipment
            shipped = (RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
                tenant=lot.tenant, content_type=lot_ct, object_id=lot.id, field_name="quantity_remaining",
                reason=f"Shipped on {shipment.shipment_number}").order_by("-edited_at").first())
            RecordEdit.objects.create(
                tenant=lot.tenant, content_type=lot_ct, object_id=lot.id, field_name="customer_shipment",
                old_value=str(shipment.id), new_value="", reason=reason.strip(), edited_by=user)
            inventory.unship_lot(lot)
            lot.refresh_from_db()
            lot.quantity_remaining = Decimal(shipped.old_value) if shipped else lot.quantity
            lot.customer_shipment = None
            lot.save(update_fields=["quantity_remaining", "customer_shipment", "updated_at"])
        shipment.void(user, reason.strip())


def order_shipping(order) -> dict:
    """What each line of ``order`` asked for, what has gone, and whether it went on
    time. Shipped counts every SHIPPED part on the line's work orders; dates come from
    shipments, so a part shipped by hand at its Ship step counts but has no date."""
    from collections import defaultdict
    from Tracker.models import Parts
    lines = list(order.lines.order_by("line_number"))  # tenant-safe: reverse FK from a scoped order
    by_line = defaultdict(list)
    for p in (Parts.objects.filter(  # tenant-safe: FK to a scoped order
            work_order__order_line__order=order, part_status="SHIPPED", archived=False)
            .select_related("customer_shipment", "work_order")):
        by_line[p.work_order.order_line_id].append(p)

    out = []
    for line in lines:
        shipped = by_line.get(line.id, [])
        dates: dict = defaultdict(int)
        numbers: dict = {}
        for p in shipped:
            s = p.customer_shipment
            if s is not None and not s.is_voided:
                dates[s.id] += 1
                numbers[s.id] = (s.shipment_number, s.shipped_at)
        shipments = [{"shipment_id": str(sid), "shipment_number": numbers[sid][0],
                      "shipped_at": numbers[sid][1], "quantity": n,
                      "on_time": (line.due_date is None
                                  or timezone.localdate(numbers[sid][1]) <= line.due_date)}
                     for sid, n in sorted(dates.items(), key=lambda kv: numbers[kv[0]][1])]
        qty = len(shipped)
        out.append({
            "line_id": str(line.id), "line_number": line.line_number,
            "part_type": line.part_type.name, "ordered": line.quantity, "shipped": qty,
            "due_date": line.due_date,
            "state": "SHIPPED" if qty >= line.quantity else ("PART_SHIPPED" if qty else "OPEN"),
            "shipments": shipments,
        })
    return {"order_id": str(order.id), "lines": out}


def delivery_performance(tenant, days: int = 90) -> dict:
    """On-time delivery to customers: of the order-line shipments made in the window
    against a due date, how many went on or before it."""
    from Tracker.models import Parts
    since = timezone.now() - timedelta(days=days)
    rows = (Parts.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, part_status="SHIPPED", customer_shipment__isnull=False,
        customer_shipment__is_voided=False, customer_shipment__shipped_at__gte=since,
        work_order__order_line__due_date__isnull=False)
        .values_list("customer_shipment_id", "customer_shipment__shipped_at",
                     "work_order__order_line_id", "work_order__order_line__due_date")
        .distinct())
    deliveries = {(s, line): timezone.localdate(at) <= due for s, at, line, due in rows}
    on_time = sum(1 for ok in deliveries.values() if ok)
    total = len(deliveries)
    return {"days": days, "deliveries": total, "on_time": on_time,
            "on_time_pct": round(on_time / total * 100, 1) if total else None}


def shipment_units(shipment):
    """The units on ``shipment`` — for a voided one, the units it had when voided."""
    from Tracker.models import Parts, RecordEdit
    if not shipment.is_voided:
        return list(shipment.parts.all())  # tenant-safe: reverse FK from a scoped shipment
    ids = RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=shipment.tenant, field_name="customer_shipment", old_value=str(shipment.id)
    ).values_list("object_id", flat=True)
    return list(Parts.objects.filter(tenant=shipment.tenant, id__in=list(ids))  # tenant-safe: explicit tenant filter
                .select_related("part_type", "work_order__related_order", "order").order_by("ERP_id"))


def shipment_lots(shipment):
    """The material lots on ``shipment`` — for a voided one, those it had when voided."""
    from Tracker.models import MaterialLot, RecordEdit
    if not shipment.is_voided:
        return list(shipment.material_lots.select_related("material", "material_type"))  # tenant-safe: reverse FK from a scoped shipment
    ids = RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=shipment.tenant, field_name="customer_shipment", old_value=str(shipment.id)
    ).values_list("object_id", flat=True)
    return list(MaterialLot.objects.filter(tenant=shipment.tenant, id__in=list(ids))  # tenant-safe: explicit tenant filter
                .select_related("material", "material_type"))
