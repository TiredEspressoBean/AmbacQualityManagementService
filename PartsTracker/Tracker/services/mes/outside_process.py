"""
Outside-processing (subcontract) orchestration — Flow B.

An outside-process step (``Steps.is_outside_process``) is a node in the part
type's process where the parts leave the building for a vendor operation (heat
treat, plating, grinding). This service models the outbound + inbound legs:

  - ``send_parts_out``   — group the parts into an ``OutsideProcessShipment``,
                           stamp their ``StepExecution`` membership, and move the
                           parts to ``AT_OUTSIDE_PROCESS``.
  - ``receive_parts_back`` — stamp the return, move the parts to ``AWAITING_QA``,
                           and open a return inspection (a ``QualityReports``
                           keyed to the *shipment*, carried by a shipment-subject
                           ``StepExecution``). That report then runs the SAME DWI
                           receiving-inspection runtime as Flow A — the only
                           difference is the subject (shipment vs. lot), so the
                           acceptance math (``receiving_inspection.
                           evaluate_lot_acceptance``) and the sample-plan
                           calculator are reused verbatim (§13.4 subject-agnostic).
  - ``accept_return`` / ``reject_return`` — the divergent leg: unlike a lot's
                           inventory flip, accepting advances the parts past the
                           step and rejecting quarantines them (rework / scrap).

Domain errors raise ``ValueError`` (the viewset maps to HTTP 400).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from Tracker.services.qms.acceptance_sampling import compute_sample_plan
from Tracker.services.qms.receiving_inspection import (
    evaluate_lot_acceptance,
    resolve_sampling_ruleset,
)

logger = logging.getLogger(__name__)


# ── Sample plan (return inspection) ──────────────────────────────────────────

def _plan_for(shipment):
    """Compute the acceptance sample plan for a returned shipment — lot size is
    the number of parts that came back."""
    rs = resolve_sampling_ruleset(shipment.step, shipment.supplier)
    return compute_sample_plan(
        lot_size=int(shipment.quantity or 0),
        aql=float(rs.aql) if rs and rs.aql is not None else 1.0,
        inspection_level=(rs.inspection_level if rs and rs.inspection_level else "II"),
        severity=(rs.severity if rs and rs.severity else "NORMAL"),
        strategy=(rs.strategy if rs and rs.strategy else "C0"),
    )


def sample_plan_for_shipment(shipment):
    """Resolve + compute the return-inspection sample plan (read-only; endpoint use)."""
    if shipment.step_id is None:
        raise ValueError("Shipment has no step.")
    return _plan_for(shipment)


# ── Shipper board: what's ready to dispatch ──────────────────────────────────

# A part is "ready to ship" only while it's actively AT the OSP step and hasn't
# gone out yet — it arrived from the upstream step (IN_PROGRESS) and needs the
# outside op. Every other status at an OSP step means it's NOT awaiting dispatch:
#   AT_OUTSIDE_PROCESS  → already out at the vendor
#   AWAITING_QA         → already came BACK; awaiting the *return* inspection
#                         (set by receive_parts_back) — the opposite of pre-send
#   READY_FOR_NEXT_STEP → completed the OSP step (accepted on return), awaiting advance
#   QUARANTINED/REWORK  → needs disposition, not shipping
#   (terminals)         → done
_READY_TO_SHIP_STATUSES = {"IN_PROGRESS"}


def build_ready_to_ship_groups():
    """Parts staged at an outside-process step and not yet sent, grouped by step
    (the dispatch unit — the step carries the default vendor). Cross-work-order:
    a shipper batches a vendor's worth onto one pallet regardless of WO. Read-only.
    """
    from collections import defaultdict
    from Tracker.models import Parts, Steps

    osp_step_ids = list(  # tenant-safe: .objects auto-scopes (request context)
        Steps.objects.filter(is_outside_process=True).values_list("id", flat=True))
    if not osp_step_ids:
        return []

    by_step = defaultdict(list)
    parts = (Parts.objects  # tenant-safe: .objects auto-scopes (request context)
             .filter(step_id__in=osp_step_ids, part_status__in=_READY_TO_SHIP_STATUSES)
             .select_related("step", "step__outside_supplier", "work_order"))
    for p in parts:
        by_step[p.step_id].append(p)

    rows = []
    for step_id, plist in by_step.items():
        step = plist[0].step
        rows.append({
            "step_id": str(step_id),
            "step_name": step.name,
            "supplier_id": str(step.outside_supplier_id) if step.outside_supplier_id else None,
            "supplier_name": step.outside_supplier.name if step.outside_supplier_id else None,
            "ready_count": len(plist),
            "parts": [
                {"id": str(p.id), "erp_id": p.ERP_id,
                 "work_order": str(p.work_order_id) if p.work_order_id else None,
                 "status": p.part_status}
                for p in plist
            ],
        })
    rows.sort(key=lambda r: r["step_name"])
    return rows


# ── Outbound leg ─────────────────────────────────────────────────────────────

def _active_execution_for(part, step):
    """The part's current (active) StepExecution at the OSP step, creating one if
    the part is at the step but has no open execution row yet."""
    from Tracker.models import StepExecution

    ex = (StepExecution.objects
          .filter(part=part, step=step,
                  status__in=["PENDING", "CLAIMED", "IN_PROGRESS"])
          .order_by("-entered_at").first())
    if ex is None:
        ex = StepExecution.objects.create(
            tenant=part.tenant, part=part, step=step, status="IN_PROGRESS",
        )
    return ex


def send_parts_out(*, step, parts, supplier=None, reference="", user=None):
    """Send ``parts`` out to a subcontract vendor for the outside-process ``step``.

    Creates one ``OutsideProcessShipment``, links each part's active
    ``StepExecution`` to it, and moves the parts to ``AT_OUTSIDE_PROCESS``.
    ``supplier`` defaults to the step's ``outside_supplier``.
    """
    from Tracker.models import OutsideProcessShipment, PartsStatus

    if not getattr(step, "is_outside_process", False):
        raise ValueError(f"Step {step} is not an outside-process step.")
    parts = list(parts)
    if not parts:
        raise ValueError("No parts to send out.")

    supplier = supplier or step.outside_supplier
    if supplier is None:
        raise ValueError("No subcontract supplier given and the step has no default vendor.")

    work_order = next((p.work_order for p in parts if p.work_order_id), None)

    with transaction.atomic():
        shipment = OutsideProcessShipment.objects.create(
            tenant=step.tenant,
            supplier=supplier,
            step=step,
            work_order=work_order,
            reference=reference,
            shipped_by=user if (user and user.is_authenticated) else None,
            status="SENT",
        )
        for part in parts:
            ex = _active_execution_for(part, step)
            ex.outside_process_shipment = shipment
            ex.save(update_fields=["outside_process_shipment", "updated_at"])
            part.part_status = PartsStatus.AT_OUTSIDE_PROCESS
            part.save(update_fields=["part_status"])

    return shipment


# ── Inbound leg + return inspection ──────────────────────────────────────────

def receive_parts_back(shipment, user=None):
    """Receive a subcontract shipment back and open its return inspection.

    Stamps the return, moves the shipped parts to ``AWAITING_QA``, and opens a
    ``QualityReports(osp_shipment=…, step=…)`` (carried by a shipment-subject
    ``StepExecution``) snapshotting the acceptance sample plan. Returns the report.
    """
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import PartsStatus, QualityReports, StepExecution

    if shipment.status == "RETURNED" and shipment.returned_at is not None:
        raise ValueError(f"Shipment {shipment.shipment_number} is already returned.")

    step = shipment.step
    sp = _plan_for(shipment)
    rs = resolve_sampling_ruleset(step, shipment.supplier) if sp.method else None
    variables_char = rs.variables_characteristic if rs else None

    with transaction.atomic():
        shipment.returned_at = timezone.now()
        shipment.status = "RETURNED"
        if user is not None and user.is_authenticated:
            shipment.returned_by = user
        shipment.save(update_fields=["returned_at", "status", "returned_by", "updated_at"])

        # Parts are back, pending the return inspection.
        for ex in shipment.step_executions.select_related("part"):
            if ex.part_id:
                ex.part.part_status = PartsStatus.AWAITING_QA
                ex.part.save(update_fields=["part_status"])

        # Shipment-subject execution: the DWI carrier for the batch return inspection.
        StepExecution.objects.create(
            tenant=shipment.tenant,
            step=step,
            subject_content_type=ContentType.objects.get_for_model(shipment.__class__),
            subject_id=shipment.id,
            status="IN_PROGRESS",
            assigned_to=user if (user and user.is_authenticated) else None,
        )
        report = QualityReports.objects.create(
            tenant=shipment.tenant,
            osp_shipment=shipment,
            step=step,
            status="PENDING",
            sampling_method="receiving_aql",
            sample_size=sp.sample_size,
            accept_number=sp.accept_number,
            reject_number=sp.reject_number,
            acceptability_constant_k=sp.k,
            variables_characteristic=variables_char,
        )
        if user is not None and user.is_authenticated:
            report.personnel_links.create(user=user, role="INSPECTOR")

    return report


def evaluate_return_acceptance(report):
    """Set report.status from the sampled defectives vs snapshot Ac/Re — the same
    subject-agnostic AQL verdict used for incoming lots."""
    if report.osp_shipment_id is None:
        raise ValueError("Report is not an outside-process return inspection.")
    return evaluate_lot_acceptance(report)


def _return_execution(shipment):
    """The open shipment-subject StepExecution carrying the return inspection, if any."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import StepExecution
    ct = ContentType.objects.get_for_model(shipment.__class__)
    return (StepExecution.objects
            .filter(subject_content_type=ct, subject_id=shipment.id,
                    status__in=["PENDING", "CLAIMED", "IN_PROGRESS"])
            .order_by("-entered_at").first())


def _finalize_return_execution(shipment, user):
    ex = _return_execution(shipment)
    if ex is not None:
        ex.status = "COMPLETED"
        ex.exited_at = timezone.now()
        if user is not None and user.is_authenticated:
            ex.completed_by = user
        ex.save(update_fields=["status", "exited_at", "completed_by", "updated_at"])


def accept_return(report, user=None):
    """Accept a return inspection: advance the shipped parts past the OSP step
    (READY_FOR_NEXT_STEP) and finalize both the part executions and the batch
    inspection execution."""
    from Tracker.models import PartsStatus

    shipment = report.osp_shipment
    if shipment is None:
        raise ValueError("Report is not an outside-process return inspection.")

    with transaction.atomic():
        for ex in shipment.step_executions.select_related("part"):
            if ex.part_id:
                ex.part.part_status = PartsStatus.READY_FOR_NEXT_STEP
                ex.part.save(update_fields=["part_status"])
            if ex.status not in ("COMPLETED", "SKIPPED", "CANCELLED"):
                ex.status = "COMPLETED"
                ex.exited_at = timezone.now()
                ex.save(update_fields=["status", "exited_at", "updated_at"])
        _finalize_return_execution(shipment, user)
        if report.status == "PENDING":
            report.status = "PASS"
            report.save(update_fields=["status"])
        shipment.status = "CLOSED"
        shipment.save(update_fields=["status", "updated_at"])

    return report


def reject_return(report, user=None):
    """Reject a return inspection: quarantine the shipped parts for disposition
    (rework / scrap) and finalize the batch inspection execution."""
    from Tracker.models import PartsStatus

    shipment = report.osp_shipment
    if shipment is None:
        raise ValueError("Report is not an outside-process return inspection.")

    with transaction.atomic():
        for ex in shipment.step_executions.select_related("part"):
            if ex.part_id:
                ex.part.part_status = PartsStatus.QUARANTINED
                ex.part.save(update_fields=["part_status"])
        _finalize_return_execution(shipment, user)
        if report.status == "PENDING":
            report.status = "FAIL"
            report.save(update_fields=["status"])
        shipment.status = "CLOSED"
        shipment.save(update_fields=["status", "updated_at"])

    return report
