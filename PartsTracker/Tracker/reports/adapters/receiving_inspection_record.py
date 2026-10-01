"""
Receiving Inspection Record adapter — the retained evidence that a lot of purchased
material was verified before release.

ISO 9001 §8.6 asks for documented information on the release of product: evidence of
conformity with the acceptance criteria, and traceability to the person(s) who
authorized the release. For a received lot that is:

    - WHAT was received — item, lot, supplier + supplier lot, heat number, source,
      quantity (and what was counted: "3 boxes"), CoC on file
    - AGAINST WHAT — the receiving plan (RIP) and its sampling plan: strategy, sample
      size, accept / reject numbers or the variables constant k
    - THE RESULT — each measurement recorded, and every checklist answer from the
      inspection run ("Is the CoC present and correct?" — yes)
    - THE DECISION — accepted or rejected, by whom and when (from the audit log of the
      lot's status), plus any receiving hold a person released, with their reason

The record is regenerated from live data on request — nothing here is a stored copy.
Rendered PDFs are byte-unstable for identical content (Typst stamps a timestamped
document id), so don't hash them to detect change.

Defense-in-depth: build_context() filters by tenant explicitly, in addition to the
param serializer's upstream check.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.services.core.clock import tenant_today


class InspectionMeasurementRow(BaseModel):
    sample: Optional[int] = None
    characteristic: str
    balloon: Optional[str] = None
    spec: str = ""
    value: str
    result: str               # "OK" / "OUT"


class ChecklistAnswerRow(BaseModel):
    question: str
    answer: str
    by: Optional[str] = None


class ReleaseEventRow(BaseModel):
    what: str                 # "Accepted", "Rejected", "Hold released (Unqualified supplier)"
    by: Optional[str] = None
    at: Optional[datetime] = None
    note: Optional[str] = None


class ReceivingInspectionRecordContext(BaseModel):
    lot_number: str
    item_name: str
    part_number: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_lot_number: Optional[str] = None
    heat_number: Optional[str] = None
    source_type: Optional[str] = None
    quantity: str
    received_as: Optional[str] = None
    received_date: Optional[date] = None
    received_by: Optional[str] = None
    erp_po: Optional[str] = None
    coc_on_file: bool = False
    status: str

    plan_name: Optional[str] = None
    report_number: Optional[str] = None
    strategy: Optional[str] = None
    sample_size: Optional[int] = None
    accept_number: Optional[int] = None
    reject_number: Optional[int] = None
    k: Optional[float] = None
    defectives_found: Optional[int] = None
    verdict: Optional[str] = None      # PASS / FAIL / PENDING, or None with no inspection
    inspected_by: Optional[str] = None

    measurements: list[InspectionMeasurementRow] = []
    checklist: list[ChecklistAnswerRow] = []
    events: list[ReleaseEventRow] = []

    tenant_name: str
    generated_date: date


class ReceivingInspectionRecordParamsSerializer(serializers.Serializer):
    """{"lot_id": <uuid>} — the material lot to document."""
    lot_id = serializers.UUIDField()

    def validate_lot_id(self, value):
        from Tracker.models import MaterialLot
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        # tenant-safe: explicit tenant filter
        if not MaterialLot.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"Lot {value} not found.")
        return value


def _name(user) -> Optional[str]:
    if user is None:
        return None
    full = user.get_full_name() if hasattr(user, "get_full_name") else ""
    return (full or "").strip() or getattr(user, "email", None) or getattr(user, "username", None)


def _num(v) -> str:
    if v is None:
        return ""
    text = f"{v:f}" if not isinstance(v, float) else repr(v)
    return text.rstrip("0").rstrip(".") if "." in text else text


def _spec(defn) -> str:
    if defn is None or defn.nominal is None:
        return ""
    lo = f" −{_num(defn.lower_tol)}" if defn.lower_tol is not None else ""
    hi = f" +{_num(defn.upper_tol)}" if defn.upper_tol is not None else ""
    return f"{_num(defn.nominal)}{hi}{lo} {defn.unit or ''}".strip()


def _status_events(lot) -> list[ReleaseEventRow]:
    """Accepted / rejected, from the audit log of the lot's `status` — who flipped it and
    when. The log is the one place that records the actor on a status change."""
    from auditlog.models import LogEntry
    events = []
    for entry in LogEntry.objects.get_for_object(lot).order_by("timestamp"):
        change = (entry.changes_dict or {}).get("status") if hasattr(entry, "changes_dict") else None
        if not change or len(change) != 2:
            continue
        new = change[1]
        if new in ("ACCEPTED", "REJECTED"):
            events.append(ReleaseEventRow(
                what="Accepted" if new == "ACCEPTED" else "Rejected",
                by=_name(entry.actor), at=entry.timestamp))
    return events


def _hold_releases(lot) -> list[ReleaseEventRow]:
    """Receiving holds a person released, with the reason they gave (a concession)."""
    from django.contrib.contenttypes.models import ContentType
    from Tracker.models import RecordEdit
    from Tracker.services.qms.receiving_inspection import HOLD_SUPPLIER_UNQUALIFIED  # noqa: F401
    labels = {
        "SUPPLIER_UNQUALIFIED": "Unqualified supplier", "PART_UNAPPROVED": "Unapproved part",
        "SHELF_LIFE_EXPIRED": "Shelf life expired", "AWAITING_COC": "Awaiting CoC",
        "AWAITING_HEAT_NUMBER": "Awaiting heat number",
    }
    edits = RecordEdit.objects.filter(  # tenant-safe: explicit tenant filter
        tenant=lot.tenant, content_type=ContentType.objects.get_for_model(lot.__class__),
        object_id=lot.id, field_name="hold_reason").select_related("edited_by").order_by("edited_at")
    return [ReleaseEventRow(what=f"Hold released ({labels.get(e.old_value, e.old_value)})",
                            by=_name(e.edited_by), at=e.edited_at, note=e.reason) for e in edits]


def build_receiving_inspection_record_context(lot, tenant) -> ReceivingInspectionRecordContext:
    """Caller is responsible for tenant filtering on the MaterialLot query."""
    from Tracker.services.qms.receiving_inspection import receiving_execution

    item = lot.item
    report = lot.quality_reports.select_related("step", "detected_by").order_by("-created_at").first()

    measurements = []
    if report is not None:
        for m in (report.measurements.select_related("definition")
                  .order_by("sample_number", "definition__label")):
            d = m.definition
            value = _num(m.value_numeric) if m.value_numeric is not None else (m.value_pass_fail or "")
            measurements.append(InspectionMeasurementRow(
                sample=m.sample_number, characteristic=d.label if d else "—",
                balloon=(d.characteristic_number or None) if d else None, spec=_spec(d),
                value=value, result="OK" if m.is_within_spec else "OUT"))

    checklist = []
    execution = receiving_execution(lot)
    if execution is None:
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import StepExecution
        # The run is closed once the lot is decided; the latest one is the inspection.
        execution = (StepExecution.objects.filter(  # tenant-safe: explicit tenant filter
            tenant=lot.tenant, subject_content_type=ContentType.objects.get_for_model(lot.__class__),
            subject_id=lot.id).order_by("-entered_at").first())
    if execution is not None:
        from Tracker.models import SubstepResponse
        for r in (SubstepResponse.objects.filter(step_execution=execution)  # tenant-safe: FK to a tenant-scoped execution
                  .select_related("substep", "responded_by").order_by("responded_at")):
            answer = r.value_text or ("Document attached" if r.value_document_id else "")
            if not answer and r.value_json:
                answer = str(r.value_json)
            checklist.append(ChecklistAnswerRow(
                question=getattr(r.substep, "title", None) or getattr(r.substep, "name", None) or r.node_id,
                answer=answer or "—", by=_name(r.responded_by)))

    received_as = None
    if lot.received_as_quantity is not None and lot.received_as_unit not in ("", "STOCK"):
        one, many = {"BOX": ("box", "boxes"), "LB": ("lb", "lb")}[lot.received_as_unit]
        received_as = f"{_num(lot.received_as_quantity)} {one if lot.received_as_quantity == 1 else many}"

    events = sorted(_hold_releases(lot) + _status_events(lot), key=lambda e: e.at or datetime.min)

    return ReceivingInspectionRecordContext(
        lot_number=lot.lot_number,
        item_name=lot.item_name or "—",
        part_number=(getattr(item, "part_number", None) or getattr(item, "ERP_id", None) or None)
        if item is not None else None,
        supplier_name=lot.supplier.name if lot.supplier_id else None,
        supplier_lot_number=lot.supplier_lot_number or None,
        heat_number=lot.heat_number or None,
        source_type=lot.get_source_type_display() if lot.source_type else None,
        quantity=f"{_num(lot.quantity)} {lot.unit_of_measure}".strip(),
        received_as=received_as,
        received_date=lot.received_date,
        received_by=_name(lot.received_by),
        erp_po=(f"{lot.erp_po_number}{' / ' + lot.erp_po_line if lot.erp_po_line else ''}"
                if lot.erp_po_number else None),
        coc_on_file=bool(lot.certificate_of_conformance),
        status=lot.get_status_display(),
        plan_name=report.step.name if report is not None and report.step_id else None,
        report_number=report.report_number or None if report is not None else None,
        strategy=report.sampling_method if report is not None else None,
        sample_size=report.sample_size if report is not None else None,
        accept_number=report.accept_number if report is not None else None,
        reject_number=report.reject_number if report is not None else None,
        k=report.acceptability_constant_k if report is not None else None,
        defectives_found=report.defectives_found if report is not None else None,
        verdict=report.status if report is not None else None,
        inspected_by=_name(report.detected_by) if report is not None else None,
        measurements=measurements,
        checklist=checklist,
        events=events,
        tenant_name=tenant.name,
        generated_date=tenant_today(tenant),
    )


class ReceivingInspectionRecordAdapter(ReportAdapter):
    """The inspection-and-release record for one received lot."""

    name = "receiving_inspection_record"
    title = "Receiving Inspection Record"
    template_path = "receiving_inspection_record.typ"
    context_model_class = ReceivingInspectionRecordContext
    param_serializer_class = ReceivingInspectionRecordParamsSerializer

    def build_context(self, validated_params, user, tenant) -> ReceivingInspectionRecordContext:
        from Tracker.models import MaterialLot
        # tenant-safe: explicit tenant filter (defense-in-depth)
        lot = (MaterialLot.unscoped.filter(tenant=tenant)
               .select_related("material", "material_type", "supplier", "received_by")
               .get(id=validated_params["lot_id"]))
        return build_receiving_inspection_record_context(lot, tenant)

    def get_filename(self, validated_params) -> str:
        return f"receiving_inspection_{validated_params.get('lot_id', 'unknown')}.pdf"
