"""Late deliveries — expected receipts past, or close to, their promised date.

The buyer's daily question is "what's late, and who do I chase?". An ON_ORDER lot
already carries the supplier's promised date (required when it is recorded), so late
is simply that date against the plant's day. What makes a late order *urgent* is the
work it holds up, so each one lists the open work orders whose production BOM calls
for the item.

"Holding up" is read from the BOM, not from netting: it says which work needs the
item, not that this particular lot is the one that would have covered it. That is
the question a buyer chasing a supplier is actually asking.
"""
from __future__ import annotations

from datetime import timedelta

from Tracker.services.mes.material_lot import DUE_SOON_DAYS, delivery_state

# Enough to see what's at stake; the full list is on the work-order pages.
HOLDING_UP_LIMIT = 10


def late_deliveries(tenant, today=None) -> list[dict]:
    """Every ON_ORDER lot overdue or due within DUE_SOON_DAYS, most overdue first."""
    from django.db.models import Q
    from Tracker.models import BOM, BOMLine, MaterialLot, WorkOrder, WorkOrderStatus
    from Tracker.services.core.clock import tenant_today

    today = today or tenant_today(tenant)
    lots = list(
        MaterialLot.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, archived=False, status="ON_ORDER", promised_date__isnull=False,
            promised_date__lte=today + timedelta(days=DUE_SOON_DAYS))
        .select_related("material", "material_type", "supplier")
        .order_by("promised_date", "lot_number"))
    if not lots:
        return []

    mat_ids = {lot.material_id for lot in lots if lot.material_id}
    pt_ids = {lot.material_type_id for lot in lots if lot.material_type_id}

    # Latest RELEASED production BOM per part type — the in-force one, as the
    # requirements report reads it (an open draft revision must not hide it).
    latest_bom: dict = {}
    for bom_id, pt_id in (BOM.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=tenant, archived=False, status="RELEASED", bom_type="ASSEMBLY")
            .order_by("part_type_id", "-version").values_list("id", "part_type_id")):
        latest_bom.setdefault(pt_id, bom_id)

    needed_by: dict = {}   # item key -> set of assembly part-type ids that call for it
    for bom_id, pt_id, m_id, c_id in (
            BOMLine.objects.filter(  # tenant-safe: `bom` is tenant-scoped; its lines share its tenant
                archived=False, source="BUY", is_optional=False, bom_id__in=latest_bom.values())
            .filter(Q(material_id__in=mat_ids) | Q(component_type_id__in=pt_ids))
            .values_list("bom_id", "bom__part_type_id", "material_id", "component_type_id")):
        if latest_bom.get(pt_id) != bom_id:
            continue
        key = ("MATERIAL", m_id) if m_id else ("PART_TYPE", c_id)
        needed_by.setdefault(key, set()).add(pt_id)

    assemblies = set().union(*needed_by.values()) if needed_by else set()
    wos_by_pt: dict = {}
    if assemblies:
        for wo in (WorkOrder.objects.filter(  # tenant-safe: explicit tenant filter
                tenant=tenant, archived=False, process__part_type_id__in=assemblies)
                .exclude(workorder_status__in=[WorkOrderStatus.COMPLETED,
                                               WorkOrderStatus.CANCELLED,
                                               WorkOrderStatus.ON_HOLD])
                .select_related("process")
                .order_by("expected_start", "ERP_id")):
            wos_by_pt.setdefault(wo.process.part_type_id, []).append(wo)

    rows = []
    for lot in lots:
        key = ("MATERIAL", lot.material_id) if lot.material_id else ("PART_TYPE", lot.material_type_id)
        wos = sorted({wo.id: wo for pt in needed_by.get(key, ()) for wo in wos_by_pt.get(pt, [])}
                     .values(), key=lambda w: (w.expected_start is None, w.expected_start, w.ERP_id))
        rows.append({
            "lot_id": str(lot.id),
            "lot_number": lot.lot_number,
            "item_name": lot.item_name,
            "supplier_name": lot.supplier.name if lot.supplier_id else None,
            "erp_po_number": lot.erp_po_number,
            "erp_po_line": lot.erp_po_line,
            "promised_date": lot.promised_date,
            # Positive = days late; zero or negative = due today or in that many days.
            "days_late": (today - lot.promised_date).days,
            "quantity": float(lot.quantity),
            "unit_of_measure": lot.unit_of_measure,
            "state": delivery_state(lot, today),
            "holding_up_count": len(wos),
            "holding_up": [
                {"work_order_id": str(wo.id), "erp_id": wo.ERP_id,
                 "expected_start": wo.expected_start}
                for wo in wos[:HOLDING_UP_LIMIT]
            ],
        })
    rows.sort(key=lambda r: (-r["days_late"], r["lot_number"]))
    return rows
