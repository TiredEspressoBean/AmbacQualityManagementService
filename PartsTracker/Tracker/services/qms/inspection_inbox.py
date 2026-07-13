"""
The QA inspector's task inbox — one flat list across every inspection source.

Round-4 research (eQMS + shop-floor QC): the quality landing is a TASK INBOX,
never a metrics dashboard; worklists are flat with type-count chips, never
grouped by work order; first-piece requests are queue-jumpers with andon
semantics, not rows. This service unions the sources that already exist:

  - receiving        — MaterialLots awaiting inspection (or soft-held), with the
                       sampling answer ("n=13 · Ac 1"), the runtime severity
                       badge, capture-resume progress, and the hold reason.
  - outside_process  — OutsideProcessShipments back from a vendor.
  - in_process       — parts requiring sampling with no PASS report yet,
                       grouped per (work order, step) — the operation is the
                       unit of inspector work, the WO is a row attribute.
  - fpi              — FPIRecord PENDING rows: pinned banner material. A
                       machine and an operator may be idle behind these; age
                       is the urgency, not a due date.

Read-only aggregation — no new state. Rows are normalized dicts.

Due tones are bucketed (Veeva-style four-state dot), never raw day counts:
receiving/OSP age against the aging thresholds below; in-process against the
work order's expected_completion; FPI is always red (queue-jumper).
"""
from __future__ import annotations

from django.db.models import Count, Min, Q
from django.utils import timezone

# Receiving-dock aging buckets (hours). First-pass conventions — revisit when
# demand linkage (needed-by-WO) exists to rank by production need instead.
_AGE_ORANGE_HOURS = 24
_AGE_RED_HOURS = 72

# In-process tone: orange when the WO is due within this many days.
_WO_DUE_SOON_DAYS = 2


def _hours_since(dt) -> float | None:
    if dt is None:
        return None
    return max(0.0, (timezone.now() - dt).total_seconds() / 3600.0)


def _age_tone(age_hours) -> str:
    if age_hours is None:
        return "gray"
    if age_hours >= _AGE_RED_HOURS:
        return "red"
    if age_hours >= _AGE_ORANGE_HOURS:
        return "orange"
    return "green"


def _wo_due_tone(expected_completion) -> tuple[str, str]:
    if expected_completion is None:
        return "gray", "no date"
    today = timezone.now().date()
    if expected_completion < today:
        return "red", f"WO due {expected_completion.isoformat()}"
    if (expected_completion - today).days <= _WO_DUE_SOON_DAYS:
        return "orange", f"WO due {expected_completion.isoformat()}"
    return "green", f"WO due {expected_completion.isoformat()}"


def _plan_badge(lot) -> str | None:
    """The sampling ANSWER ("n=13 · Ac 1"), never the code tables."""
    from Tracker.services.qms.receiving_inspection import sample_plan_for_lot
    try:
        plan = sample_plan_for_lot(lot)
    except Exception:
        return None
    if plan is None:
        return None
    return f"n={plan.sample_size} · Ac {plan.accept_number}"


def _severity_summary(lot) -> dict | None:
    """The runtime severity badge for the lot's (receiving step, supplier)."""
    from Tracker.models import SamplingSeverityState
    from Tracker.services.qms.receiving_inspection import resolve_receiving_step
    from Tracker.services.qms.severity_switching import switching_status

    if lot.supplier_id is None:
        return None
    step = resolve_receiving_step(lot.material_type) if lot.material_type_id else None
    if step is None:
        return None
    state = (SamplingSeverityState.objects  # tenant-safe: .objects auto-scopes
             .filter(step=step, supplier_id=lot.supplier_id).first())
    if state is None:
        return None
    status = switching_status(state)
    return {
        "severity": state.severity,
        "severity_since": state.severity_since.isoformat() if state.severity_since else None,
        "discontinued": state.discontinued,
        **status,
    }


def _resume_progress(lot) -> str | None:
    """"7 of 13 samples" — derivable from per-unit MeasurementResult rows on the
    lot's open (PENDING) report; lets an interrupted inspector land exactly
    where they left off. Interruption is this persona's normal state."""
    from Tracker.models import MeasurementResult, QualityReports

    report = (QualityReports.objects  # tenant-safe: .objects auto-scopes
              .filter(material_lot=lot, status="PENDING")
              .order_by("-created_at").first())
    if report is None or not report.sample_size:
        return None
    done = (MeasurementResult.objects
            .filter(report=report, sample_number__isnull=False)
            .values("sample_number").distinct().count())
    if done == 0:
        return None
    return f"{done} of {report.sample_size} samples"


def _receiving_rows():
    from Tracker.models import MaterialLot
    qs = (MaterialLot.objects  # tenant-safe: .objects auto-scopes
          .filter(archived=False)
          .filter(Q(status__in=["RECEIVED", "AWAITING_INSPECTION"])
                  | (Q(status="QUARANTINE") & ~Q(hold_reason="")))
          .select_related("material_type", "supplier"))
    for lot in qs:
        received_dt = None
        if lot.received_date is not None:
            from datetime import datetime, time
            received_dt = timezone.make_aware(datetime.combine(lot.received_date, time.min))
        age = _hours_since(received_dt)
        blocked = lot.hold_reason if lot.status == "QUARANTINE" else None
        item = ((lot.material_type.name if lot.material_type_id else "")
                or lot.material_description or "")
        yield {
            "type": "receiving",
            "subject_kind": "material_lot",
            "id": str(lot.id),
            "title": f"{item} · Lot {lot.lot_number}".strip(" ·"),
            "detail": lot.supplier.name if lot.supplier_id else "",
            "wo": None,
            "quantity": float(lot.quantity) if lot.quantity is not None else None,
            "age_hours": age,
            "due_tone": "gray" if blocked else _age_tone(age),
            "due_label": f"received {lot.received_date.isoformat()}" if lot.received_date else "",
            "plan": None if blocked else _plan_badge(lot),
            "severity": _severity_summary(lot),
            "resume": None if blocked else _resume_progress(lot),
            "blocked_reason": blocked,
        }


def _outside_process_rows():
    from Tracker.models import OutsideProcessShipment
    qs = (OutsideProcessShipment.objects  # tenant-safe: .objects auto-scopes
          .filter(archived=False, status="RETURNED")
          .select_related("supplier", "step"))
    for s in qs:
        age = _hours_since(s.returned_at)
        yield {
            "type": "outside_process",
            "subject_kind": "shipment",
            "id": str(s.id),
            "title": f"{s.step.name if s.step_id else 'OSP return'} · {s.shipment_number or ''}".strip(" ·"),
            "detail": s.supplier.name if s.supplier_id else "",
            "wo": None,
            "quantity": s.quantity,
            "age_hours": age,
            "due_tone": _age_tone(age),
            "due_label": f"returned {s.returned_at.date().isoformat()}" if s.returned_at else "",
            "plan": None,
            "severity": None,
            "resume": None,
            "blocked_reason": None,
        }


def _in_process_rows():
    from Tracker.models import Parts
    from Tracker.services.mes.parts import TERMINAL_PART_STATUSES

    # The operation (work order × step) is the unit of inspector work; parts
    # are its quantity. Mirrors the Parts.needs_qa property semantics.
    groups = (Parts.objects  # tenant-safe: .objects auto-scopes
              .filter(archived=False, requires_sampling=True)
              .exclude(error_reports__status="PASS")
              .exclude(part_status__in=list(TERMINAL_PART_STATUSES))
              .exclude(step__isnull=True)
              .values("work_order", "step",
                      "work_order__ERP_id", "work_order__expected_completion",
                      "step__name", "part_type__name")
              .annotate(qty=Count("id"), oldest=Min("updated_at")))
    for g in groups:
        tone, label = _wo_due_tone(g["work_order__expected_completion"])
        yield {
            "type": "in_process",
            "subject_kind": "operation",
            "id": f"{g['work_order']}:{g['step']}",
            "title": f"{g['step__name']} · {g['qty']} pcs",
            "detail": g["part_type__name"] or "",
            "wo": g["work_order__ERP_id"],
            "quantity": g["qty"],
            "age_hours": _hours_since(g["oldest"]),
            "due_tone": tone,
            "due_label": label,
            "plan": None,
            "severity": None,
            "resume": None,
            "blocked_reason": None,
        }


def _fpi_rows():
    from Tracker.models import FPIRecord
    qs = (FPIRecord.objects  # tenant-safe: .objects auto-scopes
          .filter(status="PENDING")
          .select_related("work_order", "step", "part_type", "designated_part", "equipment"))
    for r in qs:
        age = _hours_since(r.created_at)
        yield {
            "type": "fpi",
            "subject_kind": "fpi_record",
            "id": str(r.id),
            "title": f"First piece · {r.step.name if r.step_id else ''}".strip(" ·"),
            "detail": " · ".join(filter(None, [
                r.part_type.name if r.part_type_id else None,
                r.equipment.name if r.equipment_id else None,
                r.designated_part.ERP_id if r.designated_part_id else None,
            ])),
            "wo": r.work_order.ERP_id if r.work_order_id else None,
            "quantity": 1,
            "age_hours": age,
            # Queue-jumper: a machine and operator may be idle behind this.
            "due_tone": "red",
            "due_label": "machine may be waiting",
            "plan": None,
            "severity": None,
            "resume": None,
            "blocked_reason": None,
        }


def build_inbox_rows():
    """The inspector inbox rows: FPI first, then by urgency tone, then age.
    A flat list (the ``build_incoming_rows`` convention) — clients derive the
    type-count chips (with oldest-age; counts alone hide rot) from the rows."""
    rows = [*_fpi_rows(), *_receiving_rows(), *_outside_process_rows(), *_in_process_rows()]

    tone_rank = {"red": 0, "orange": 1, "green": 2, "gray": 3}
    rows.sort(key=lambda r: (
        0 if r["type"] == "fpi" else 1,
        tone_rank.get(r["due_tone"], 3),
        -(r["age_hours"] or 0.0),
    ))
    return rows
