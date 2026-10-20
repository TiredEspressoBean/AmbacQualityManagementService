"""
Unified incoming-inspection worklist (SAP QM QA32-style).

One list across inbound-inspection sources, distinguished by a `source` column:
  - PURCHASED_LOT   — a MaterialLot received from a supplier, awaiting/held for
                      receiving inspection (Flow A).
  - OUTSIDE_PROCESS — an OutsideProcessShipment out at / back from a subcontract
                      vendor (Flow B).

Both back the same subject-agnostic DWI inspection runtime; this collapses the
two surfaces into a single queue (design doc §4). Read-only aggregation — no
new state; rows are normalized dicts the serializer renders.
"""
from __future__ import annotations

from django.db.models import Q


def visible(model, user):
    """`model`'s rows `user` may see (SecureManager.for_user: tenant, order scope,
    classification), or the tenant's rows when no user is given (internal callers).
    The inspection queues are aggregations, so they apply the row rule themselves —
    the endpoint's permission check gates the action, not which rows come back."""
    return model.objects.for_user(user) if user is not None else model.objects  # tenant-safe: .objects auto-scopes


def awaiting_inspection(qs):
    """Lots still needing a receiving decision: RECEIVED / AWAITING_INSPECTION, plus
    soft-held at receiving (QUARANTINE with a hold_reason, e.g. unqualified supplier).
    Shared by this queue and the inspector's inbox, which drifted apart when each kept
    its own copy (the inbox lost the core-lot exclusion). A third copy is the
    MaterialLot list's `inspection_pending` lens (MaterialLotViewSet.get_queryset),
    which calls this too."""
    return (qs.filter(archived=False)  # .objects doesn't exclude soft-deleted; the per-model queue does
            .filter(Q(status__in=["RECEIVED", "AWAITING_INSPECTION"])
                    | (Q(status="QUARANTINE") & ~Q(hold_reason="")))
            # A customer's bulk cores are graded unit by unit as they're identified,
            # not sampled as supplier stock.
            .filter(holds_cores=False))


def _lot_rows(user=None):
    from Tracker.models import MaterialLot
    qs = (awaiting_inspection(visible(MaterialLot, user))
          .select_related("material_type", "material", "supplier"))
    for lot in qs:
        yield {
            "source": "PURCHASED_LOT",
            "id": str(lot.id),
            "reference": lot.lot_number or "",
            "item": lot.item_name,
            "supplier": lot.supplier.name if lot.supplier_id else "",
            "quantity": float(lot.quantity) if lot.quantity is not None else None,
            "status": lot.status,
            "status_display": "Held" if lot.status == "QUARANTINE" else "Awaiting inspection",
            "received_at": lot.received_date.isoformat() if lot.received_date else None,
            "step_id": None,
        }


def _shipment_rows(user=None):
    from Tracker.models import OutsideProcessShipment
    qs = (visible(OutsideProcessShipment, user)
          .filter(archived=False)  # exclude soft-deleted (voided) shipments
          .filter(status__in=["SENT", "RETURNED"])
          .select_related("supplier", "step"))
    for s in qs:
        when = s.returned_at or s.shipped_at
        yield {
            "source": "OUTSIDE_PROCESS",
            "id": str(s.id),
            "reference": s.shipment_number or "",
            "item": s.step.name if s.step_id else "",
            "supplier": s.supplier.name if s.supplier_id else "",
            "quantity": s.quantity,
            "status": s.status,
            "status_display": "At vendor" if s.status == "SENT" else "Awaiting inspection",
            "received_at": when.isoformat() if when else None,
            "step_id": str(s.step_id) if s.step_id else None,
        }


def build_incoming_rows(user=None):
    """All inbound-inspection rows (purchased lots + subcontract shipments) `user` may
    see, newest first. Callers filter by `source` / normalized status client-side."""
    rows = [*_lot_rows(user), *_shipment_rows(user)]
    rows.sort(key=lambda r: r["received_at"] or "", reverse=True)
    return rows
