"""Supplier scorecard — a read-only quality rollup over receiving-inspection data.

Pure aggregation: no new state. Metrics come from MaterialLot (per supplier) +
the SCAR CAPAs raised against the supplier. PPM (defectives-per-million) is a
follow-on once per-sample defect capture is routine; v1 uses lot-level rates.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import F


@dataclass(frozen=True)
class SupplierScorecard:
    supplier_id: str
    lots_received: int
    lots_accepted: int
    lots_rejected: int
    lots_inspected: int
    reject_rate: float            # rejected / inspected (0..1)
    coc_compliance: float         # lots with a CoC / received (0..1)
    on_time_rate: float | None    # received_date <= promised_date / lots with a promised_date
    promised_lots: int
    open_scar_count: int


def compute_supplier_scorecard(supplier) -> SupplierScorecard:
    from Tracker.models import MaterialLot, CAPA

    lots = MaterialLot.objects.filter(supplier=supplier)
    received = lots.count()
    accepted = lots.filter(status="ACCEPTED").count()
    rejected = lots.filter(status="REJECTED").count()
    inspected = accepted + rejected

    with_coc = lots.exclude(certificate_of_conformance="").count()

    promised = lots.filter(promised_date__isnull=False)
    promised_n = promised.count()
    on_time = promised.filter(received_date__lte=F("promised_date")).count()

    open_scars = (
        CAPA.objects.filter(supplier=supplier, capa_type="SUPPLIER")
        .exclude(status__in=["CLOSED", "CANCELLED"]).count()
    )

    return SupplierScorecard(
        supplier_id=str(supplier.id),
        lots_received=received,
        lots_accepted=accepted,
        lots_rejected=rejected,
        lots_inspected=inspected,
        reject_rate=(rejected / inspected) if inspected else 0.0,
        coc_compliance=(with_coc / received) if received else 0.0,
        on_time_rate=(on_time / promised_n) if promised_n else None,
        promised_lots=promised_n,
        open_scar_count=open_scars,
    )
