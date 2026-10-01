"""Two-way traceability for a material lot — the recall question, answered from one page.

Backward: where the lot came from — supplier and their lot, heat, PO, the parent lot it
was split from — and the lots split off it.

Forward: where it went — every part a step drew it, or a lot split off it, into
(`MaterialUsage`), each part
up through the assemblies it was built into (`AssemblyUsage`, to the top), and each top
assembly's work order, order and customer.

Forward trace is only as complete as consumption recording: a lot used on the floor
without a step drawing from it leaves no trail here.
"""
from __future__ import annotations

# Deep enough for any real build; a cycle in bad data must not hang the page.
MAX_ASSEMBLY_DEPTH = 20


def _part_row(part) -> dict:
    wo = part.work_order
    order = (part.order or (wo.related_order if wo is not None else None))
    company = getattr(order, "company", None) if order is not None else None
    return {
        "part_id": str(part.id),
        "erp_id": part.ERP_id,
        "part_type": part.part_type.name if part.part_type_id else None,
        "status": part.get_part_status_display(),
        "work_order_id": str(wo.id) if wo is not None else None,
        "work_order": wo.ERP_id if wo is not None else None,
        "order_id": str(order.id) if order is not None else None,
        "order": (order.order_number or order.name) if order is not None else None,
        "customer": company.name if company is not None else None,
    }


def _climb(part) -> list:
    """The chain of assemblies `part` went into, innermost first."""
    from Tracker.models import AssemblyUsage
    chain, seen, current = [], {part.id}, part
    for _ in range(MAX_ASSEMBLY_DEPTH):
        use = (AssemblyUsage.objects  # tenant-safe: .objects auto-scopes; FK to a scoped part
               .filter(component=current, assembly__isnull=False)
               .select_related("assembly__part_type", "assembly__work_order__related_order__company",
                               "assembly__order__company")
               .order_by("-created_at").first())
        if use is None or use.assembly_id in seen:
            break
        seen.add(use.assembly_id)
        current = use.assembly
        chain.append(_part_row(current))
    return chain


def trace_lot(lot) -> dict:
    """The lot's backward and forward trace, shaped for `LotTraceSerializer`."""
    from Tracker.models import MaterialLot, MaterialUsage

    parent = lot.parent_lot
    children = list(MaterialLot.objects.filter(parent_lot=lot)  # tenant-safe: FK to a scoped lot
                    .order_by("lot_number").values("id", "lot_number", "status", "quantity"))
    backward = {
        "supplier": lot.supplier.name if lot.supplier_id else None,
        "supplier_lot_number": lot.supplier_lot_number or None,
        "heat_number": lot.heat_number or None,
        "source_type": lot.get_source_type_display() if lot.source_type else None,
        "erp_po": (f"{lot.erp_po_number}{' / ' + lot.erp_po_line if lot.erp_po_line else ''}"
                   if lot.erp_po_number else None),
        "received_date": lot.received_date,
        "parent_lot_id": str(parent.id) if parent is not None else None,
        "parent_lot_number": parent.lot_number if parent is not None else None,
        "split_lots": [{"lot_id": str(c["id"]), "lot_number": c["lot_number"],
                        "status": c["status"], "quantity": float(c["quantity"])} for c in children],
    }

    # Forward from the lot AND every lot split off it, at any depth: a recall of this
    # lot is a recall of its pieces, and reading only its own usages under-reported.
    family, frontier = [lot.id], [lot.id]
    for _ in range(MAX_ASSEMBLY_DEPTH):
        frontier = list(MaterialLot.objects.filter(parent_lot_id__in=frontier)  # tenant-safe: FK to a scoped lot
                        .exclude(id__in=family).values_list("id", flat=True))
        if not frontier:
            break
        family += frontier

    uses = []
    for u in (MaterialUsage.objects.filter(lot_id__in=family)  # tenant-safe: FK to scoped lots
              .select_related("lot", "part__part_type", "part__work_order__related_order__company",
                              "part__order__company", "work_order", "step", "consumed_by")
              .order_by("consumed_at")):
        part = u.part
        uses.append({
            "lot_number": u.lot.lot_number,
            "quantity": float(u.qty_consumed),
            "consumed_at": u.consumed_at,
            "step": u.step.name if u.step_id else None,
            "work_order": u.work_order.ERP_id if u.work_order_id else None,
            "part": _part_row(part) if part is not None else None,
            "built_into": _climb(part) if part is not None else [],
        })
    customers = sorted({row["customer"] for u in uses
                        for row in ([u["part"]] if u["part"] else []) + u["built_into"]
                        if row and row.get("customer")})
    return {"backward": backward, "forward": uses, "customers": customers}
