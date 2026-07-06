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


def _lot_rows():
    from Tracker.models import MaterialLot
    # Awaiting inspection (RECEIVED / AWAITING_INSPECTION) + soft-held at receiving
    # (QUARANTINE with a hold_reason, e.g. unqualified supplier) — mirrors the
    # MaterialLot queue's `inspection_pending` lens.
    qs = (MaterialLot.objects  # tenant-safe: .objects auto-scopes (request context)
          .filter(archived=False)  # .objects doesn't exclude soft-deleted; the per-model queue does
          .filter(Q(status__in=["RECEIVED", "AWAITING_INSPECTION"])
                  | (Q(status="QUARANTINE") & ~Q(hold_reason="")))
          .select_related("material_type", "supplier"))
    for lot in qs:
        yield {
            "source": "PURCHASED_LOT",
            "id": str(lot.id),
            "reference": lot.lot_number or "",
            "item": (lot.material_type.name if lot.material_type_id else "")
                    or lot.material_description or "",
            "supplier": lot.supplier.name if lot.supplier_id else "",
            "quantity": float(lot.quantity) if lot.quantity is not None else None,
            "status": lot.status,
            "status_display": "Held" if lot.status == "QUARANTINE" else "Awaiting inspection",
            "received_at": lot.received_date.isoformat() if lot.received_date else None,
            "step_id": None,
        }


def _shipment_rows():
    from Tracker.models import OutsideProcessShipment
    qs = (OutsideProcessShipment.objects  # tenant-safe: .objects auto-scopes (request context)
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


def build_incoming_rows():
    """All inbound-inspection rows (purchased lots + subcontract shipments),
    newest first. Callers filter by `source` / normalized status client-side."""
    rows = [*_lot_rows(), *_shipment_rows()]
    rows.sort(key=lambda r: r["received_at"] or "", reverse=True)
    return rows
