"""How the dock is doing — receiving's own numbers, not the suppliers'.

Scorecards measure suppliers. A receiving lead needs the department's view: how much
came in, how long lots sit before a decision, what is held and why, and how much was
rejected. Everything is read from records the dock already writes:

- receipts: MaterialLot.received_date
- time to decision: the lot's receiving inspection run (StepExecution with the lot as
  subject) — opened at entered_at, decided at exited_at
- holds: current QUARANTINE lots by hold_reason, and holds released in the period
  (RecordEdit on hold_reason)
- rejects: dispositions opened on lots in the period, in pieces
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from statistics import median

PENDING_STATUSES = ("RECEIVED", "AWAITING_INSPECTION")


def dock_metrics(tenant, days: int = 30, today=None) -> dict:
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Count, Sum
    from Tracker.models import MaterialLot, QuarantineDisposition, RecordEdit, StepExecution
    from Tracker.services.core.clock import tenant_today

    today = today or tenant_today(tenant)
    start = today - timedelta(days=days - 1)
    lots = MaterialLot.objects.filter(tenant=tenant, archived=False)  # tenant-safe: explicit tenant filter
    lot_ct = ContentType.objects.get_for_model(MaterialLot)
    # A split lot carries its parent's receipt date but isn't a second delivery.
    deliveries = lots.filter(parent_lot__isnull=True)

    # Receipts per day, every day in the window (zero days included, so a gap reads as one).
    per_day = {r["received_date"]: r for r in (
        deliveries.filter(received_date__gte=start, received_date__lte=today)
        .values("received_date").annotate(n=Count("id")))}
    receipts = [{"date": start + timedelta(days=i),
                 "lots": per_day.get(start + timedelta(days=i), {}).get("n", 0)}
                for i in range(days)]

    # Waiting now, and how long the oldest has waited.
    waiting = list(lots.filter(status__in=PENDING_STATUSES)
                   .exclude(received_date__isnull=True).values_list("received_date", flat=True))
    oldest_wait_days = max(((today - d).days for d in waiting), default=None)

    # Time from inspection opened to decision, for runs decided in the window.
    runs = list(StepExecution.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, subject_content_type=lot_ct, exited_at__isnull=False,
        exited_at__date__gte=start, exited_at__date__lte=today)
        .values_list("entered_at", "exited_at", "subject_id"))
    inspect_hours = [(out - inn).total_seconds() / 3600 for inn, out, _ in runs if inn and out]
    received_on = dict(lots.filter(id__in=[s for _, _, s in runs])
                       .values_list("id", "received_date"))
    dock_days = [(out.date() - received_on[s]).days for _, out, s in runs
                 if out and received_on.get(s) is not None]

    # Holds: what's held now, by reason; and how many were released in the window.
    # Every hold counts: a lot held for its CoC and its heat number is in both bars.
    from collections import Counter
    from Tracker.services.qms.lot_holds import holds
    held_counts = Counter(code for lot in lots.filter(status="QUARANTINE").exclude(hold_reason="")
                          for code in holds(lot))
    released = (RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, content_type=lot_ct, field_name="hold_reason",
        edited_at__date__gte=start, edited_at__date__lte=today)
        .values("old_value").annotate(n=Count("id")).order_by("-n"))

    # Rejected in the window. A declined whole-lot request was never a reject.
    from Tracker.services.qms.lot_reject import DECLINED_NOTE
    rejected = (QuarantineDisposition.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=tenant, material_lot__isnull=False,
        created_at__date__gte=start, created_at__date__lte=today)
        .exclude(resolution_notes__contains=DECLINED_NOTE))
    # PPM counts pieces: lots kept in each (EA) only — 40 kg of bar stock is no number of
    # pieces — and our own stock only, as received is (customer property isn't ours to
    # count either side). Summing every unit and every owner on top, mixed kilograms
    # into pieces and divided customer rejects by a total that excluded them.
    in_pieces = {"unit_of_measure__iexact": "EA", "owner__isnull": True}
    rejects = rejected.aggregate(n=Count("id"))
    pieces = (rejected.filter(**{f"material_lot__{k}": v for k, v in in_pieces.items()})
              .aggregate(q=Sum("quantity"))["q"]) or Decimal("0")
    received_pieces = (deliveries.filter(received_date__gte=start, received_date__lte=today, **in_pieces)
                       .aggregate(q=Sum("quantity"))["q"]) or Decimal("0")

    def _med(values):
        return round(median(values), 1) if values else None

    return {
        "days": days,
        "receipts": receipts,
        "lots_received": sum(r["lots"] for r in receipts),
        "awaiting_decision": len(waiting),
        "oldest_wait_days": oldest_wait_days,
        "decided": len(runs),
        "median_inspection_hours": _med(inspect_hours),
        "median_days_to_decision": _med(dock_days),
        "held_now": [{"reason": code, "lots": n} for code, n in held_counts.most_common()],
        "holds_released": [{"reason": r["old_value"], "lots": r["n"]} for r in released],
        "lots_rejected": rejects["n"] or 0,
        "pieces_rejected": float(pieces),
        # Pieces rejected per million received: the defect rate behind the reject rate.
        "ppm_rejected": (round(float(pieces) / float(received_pieces) * 1_000_000)
                         if received_pieces else None),
    }
