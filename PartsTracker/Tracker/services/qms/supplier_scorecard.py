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
    rating: str | None            # 'A' | 'B' | 'C' overall tier, or None when no data
    rating_reason: str            # short driver of the tier (for the UI tooltip)


def _rating(*, inspected, reject_rate, on_time_rate, coc_compliance, open_scar_count):
    """Roll the metrics into an A/B/C tier. None when there's no inspection history.

    C (action needed): an open SCAR, reject rate >= 10%, on-time < 85%.
    A (preferred): reject <= 2%, CoC >= 99%, on-time >= 95% (or no promise data).
    B otherwise. Thresholds are deliberately simple/explicit for a small shop.
    """
    if inspected == 0:
        return None, "No inspection history yet"
    if open_scar_count > 0:
        return "C", f"{open_scar_count} open SCAR(s)"
    if reject_rate >= 0.10:
        return "C", f"Reject rate {round(reject_rate * 100)}%"
    if on_time_rate is not None and on_time_rate < 0.85:
        return "C", f"On-time {round(on_time_rate * 100)}%"
    on_time_ok = on_time_rate is None or on_time_rate >= 0.95
    if reject_rate <= 0.02 and coc_compliance >= 0.99 and on_time_ok:
        return "A", "Within all thresholds"
    return "B", "Minor metrics below target"


def compute_supplier_scorecard(supplier) -> SupplierScorecard:
    from Tracker.models import MaterialLot, CAPA

    lots = MaterialLot.objects.filter(supplier=supplier)  # tenant-safe: runs in request/tenant_context; SecureManager auto-scopes
    received = lots.count()
    accepted = lots.filter(status="ACCEPTED").count()
    rejected = lots.filter(status="REJECTED").count()
    inspected = accepted + rejected

    with_coc = lots.exclude(certificate_of_conformance="").count()

    promised = lots.filter(promised_date__isnull=False)
    promised_n = promised.count()
    on_time = promised.filter(received_date__lte=F("promised_date")).count()

    open_scars = (
        CAPA.objects.filter(supplier=supplier, capa_type="SUPPLIER")  # tenant-safe: runs in request/tenant_context; SecureManager auto-scopes
        .exclude(status__in=["CLOSED", "CANCELLED"]).count()
    )

    reject_rate = (rejected / inspected) if inspected else 0.0
    coc_compliance = (with_coc / received) if received else 0.0
    on_time_rate = (on_time / promised_n) if promised_n else None
    rating, rating_reason = _rating(
        inspected=inspected, reject_rate=reject_rate, on_time_rate=on_time_rate,
        coc_compliance=coc_compliance, open_scar_count=open_scars,
    )

    return SupplierScorecard(
        supplier_id=str(supplier.id),
        lots_received=received,
        lots_accepted=accepted,
        lots_rejected=rejected,
        lots_inspected=inspected,
        reject_rate=reject_rate,
        coc_compliance=coc_compliance,
        on_time_rate=on_time_rate,
        promised_lots=promised_n,
        open_scar_count=open_scars,
        rating=rating,
        rating_reason=rating_reason,
    )
