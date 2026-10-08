"""
Work Order Traveler adapter.

The traveler (a.k.a. router / job packet) is THE #1 printed shop-floor
document: it accompanies a work order through every operation, carrying the
routing and a place for operators and inspectors to sign off each step as the
job moves down the line. It is the paper counterpart to the on-screen Digital
Traveler.

The PDF (landscape US-letter) covers:
- Title block: work order number, part being built, process, qty, dates
- A scannable Code 128 barcode of the work-order ERP id in the header, so an
  operator/inspector can scan the paper traveler to pull the job up on screen
  (the shop-floor scan box resolves the WO and lands on WO Control).
- Order/customer reference + drawing reference (number + revision)
- Routing table — one row per operation in process order:
    Seq | Operation (+desc) | Type (+std time) | Controls & Specs |
    Operator / Date | Inspector / Date | Acc/Rej | Remarks
  The sign-off / acc-rej / remarks cells are blank for wet-ink capture.
- Final-release footer: final inspection sign-off, qty accepted / rejected /
  scrapped, date completed, QA release stamp (all blank wet-ink fields).

Routing is resolved via WorkOrder → Processes → ProcessStep (ordered by
`order`). Per-step control flags are summarised into short "control" tags and
each step's measurement definitions become printable characteristic specs.

The drawing number + revision are resolved from a controlled Document of a
"Drawing" DocumentType (code DWG/DRAWING) attached to the part type; when none
is attached the fields render as "—" (honest gap rather than a fake number).

Defense-in-depth: every ORM query in build_context() filters by tenant
explicitly, in addition to the param serializer's upstream check. See
Documents/TYPST_MIGRATION_PLAN.md "SPC service methods and tenant scoping".
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from rest_framework import serializers

from Tracker.reports.adapters.base import ReportAdapter
from Tracker.services.core.clock import tenant_today
from Tracker.reports.services.barcodes import render_barcode_svg, render_qr_svg


# ---------------------------------------------------------------------------
# Pydantic context models
# ---------------------------------------------------------------------------


class TravelerOperation(BaseModel):
    """One routing row (operation) in the traveler."""

    seq: str                       # ProcessStep.order, rendered as a string
    op_number: Optional[str] = None  # Steps.operation_number; falls back to seq
    step_name: str
    step_type: str                 # human-readable step-type label
    description: Optional[str] = None      # short step description
    std_time: Optional[str] = None         # expected duration, e.g. "2h 30m"
    controls: list[str] = Field(default_factory=list)  # short control tags
    specs: list[str] = Field(default_factory=list)     # measurement characteristics
    is_outside_process: bool = False

    # ---- As-built actuals (optional) ----
    # When populated, the row's sign-off cells render filled instead of blank.
    # The live adapter leaves these None (blank form for hand-fill); they exist
    # so an "as-built" render can show recorded operator/inspector/result data.
    operator: Optional[str] = None      # e.g. "M. Ops · 7/12"
    inspector: Optional[str] = None     # e.g. "S. Chen · 7/13"
    acc_rej: Optional[str] = None       # e.g. "ACC" / "REJ"
    remarks: Optional[str] = None
    # As-built traceability for the resolved serial (2026-10-08): what was
    # actually measured, which lots went in, how many visits, any override.
    recorded: list[str] = Field(default_factory=list)   # "Torque 25 Nm ✓ · M. Ops 10/6"
    materials: list[str] = Field(default_factory=list)  # "Lot STOCK-CRI-SOL · Solenoid Coil × 1"
    visits: int = 0                                     # >1 means the step was reworked
    overrides: list[str] = Field(default_factory=list)  # "Training expired — approved S. Chen"


class TravelerSerial(BaseModel):
    """One serial on the work order, for the traveler's per-serial lines."""

    serial: str
    step: Optional[str] = None
    status: str
    open_ncrs: int = 0
    shipped: bool = False


class WorkOrderTravelerContext(BaseModel):
    """Top-level shape passed to the work_order_traveler.typ template."""

    # ---- Work order header ----
    wo_number: str
    part_number: str
    part_name: str
    process_name: str
    revision: Optional[str] = None      # part_type.version — e.g. "Rev 3"
    serial: Optional[str] = None        # the resolved part's ERP id (as-built)
    drawing_number: Optional[str] = None    # from attached Drawing document
    drawing_revision: Optional[str] = None  # from attached Drawing document
    quantity: int
    priority: str
    status: str
    start_date: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None

    # ---- Order / customer reference ----
    order_number: Optional[str] = None
    order_name: Optional[str] = None
    customer_name: Optional[str] = None

    # ---- Routing ----
    operations: list[TravelerOperation] = Field(default_factory=list)
    total_operations: int

    # ---- Encoded media ----
    barcode_svg: str                    # Code 128 SVG encoding the WO ERP id
    qr_svg: str                         # QR SVG → the WO's on-screen URL (phone scan)

    # ---- Final-release actuals (optional) ----
    # Populated only for an "as-built" render; blank on the job-release form.
    qty_accepted: Optional[str] = None
    qty_rejected: Optional[str] = None
    qty_scrapped: Optional[str] = None
    date_completed: Optional[str] = None
    final_signoff: Optional[str] = None
    qa_release: Optional[str] = None
    date_released: Optional[str] = None

    # ---- Traceability (2026-10-08) ----
    # The resolved serial's nonconformances and how each was dispositioned.
    nonconformances: list[str] = Field(default_factory=list)
    # One line per serial on the work order — where each unit is, and whether it
    # carries an open nonconformance. Empty on a single-serial work order.
    serials: list["TravelerSerial"] = Field(default_factory=list)
    serials_truncated: int = 0          # serials beyond the printed cap

    # ---- Document metadata ----
    tenant_name: str
    generated_date: datetime.date


# ---------------------------------------------------------------------------
# DRF param serializer
# ---------------------------------------------------------------------------


class WorkOrderTravelerParamsSerializer(serializers.Serializer):
    """
    Accepts {"id": <uuid>} identifying the WorkOrder to print a traveler for.
    Confirms the WorkOrder exists in the requesting user's tenant. The adapter
    re-queries with an explicit tenant filter for defense-in-depth.

    WorkOrder uses a UUID primary key (SecureModel default), so the id field
    is a UUIDField, not IntegerField.
    """

    id = serializers.UUIDField()
    # Optional: render the as-built history for a specific part on the WO.
    # Omitted → the adapter auto-uses the sole part on a single-part WO, else
    # renders the blank job-release form.
    part = serializers.UUIDField(required=False)

    def _tenant(self):
        user = self.context.get("user") or (
            getattr(self.context.get("request"), "user", None)
        )
        if user is None:
            raise serializers.ValidationError("Authenticated user required.")
        tenant = getattr(user, "_current_tenant", None) or getattr(user, "tenant", None)
        if tenant is None:
            raise serializers.ValidationError("No tenant context on user.")
        return tenant

    def validate_id(self, value):
        from Tracker.models.mes_lite import WorkOrder

        tenant = self._tenant()
        # tenant-safe: explicit tenant filter
        exists = WorkOrder.unscoped.filter(id=value, tenant=tenant).exists()
        if not exists:
            raise serializers.ValidationError(f"WorkOrder {value} not found.")
        return value

    def validate_part(self, value):
        from Tracker.models.mes_lite import Parts

        tenant = self._tenant()
        # tenant-safe: explicit tenant filter
        if not Parts.unscoped.filter(id=value, tenant=tenant).exists():
            raise serializers.ValidationError(f"Part {value} not found.")
        return value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_dec(d: Decimal) -> str:
    """Format a Decimal without trailing zeros or scientific notation."""
    normalized = d.normalize()
    if normalized == normalized.to_integral_value():
        return str(int(normalized))
    return str(normalized)


def _fmt_duration(td) -> Optional[str]:
    """Format a timedelta as a compact 'Nh Mm' string; None if empty."""
    if not td:
        return None
    total = int(td.total_seconds())
    hours, rem = divmod(total, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    if minutes:
        return f"{minutes}m"
    return None


def _short_name(user) -> Optional[str]:
    """Compact person label: 'First L.' or username/email-local."""
    if not user:
        return None
    full = (user.get_full_name() or "").strip() if hasattr(user, "get_full_name") else ""
    if full:
        parts = full.split()
        return f"{parts[0]} {parts[-1][0]}." if len(parts) >= 2 else full
    handle = getattr(user, "username", "") or getattr(user, "email", "") or ""
    return handle.split("@")[0] or None


def _short_date(dt) -> Optional[str]:
    """Compact 'M/D' date label from a date/datetime; None if empty."""
    if not dt:
        return None
    return f"{dt.month}/{dt.day}"


def _join_person_date(user, dt) -> Optional[str]:
    label = " · ".join(x for x in (_short_name(user), _short_date(dt)) if x)
    return label or None


def _step_controls(step) -> list[str]:
    """Summarise a step's control flags into short printable tags."""
    tags: list[str] = []
    if getattr(step, "requires_qa_signoff", False):
        tags.append("QA sign-off")
    if getattr(step, "requires_first_piece_inspection", False):
        tags.append("First piece")
    if getattr(step, "sampling_required", False):
        rate = getattr(step, "min_sampling_rate", 0) or 0
        # min_sampling_rate is stored as a whole-number percent (e.g. 25.0)
        tags.append(f"Sampling {rate:g}%")
    if getattr(step, "is_outside_process", False):
        supplier = getattr(step, "outside_supplier", None)
        tags.append(f"Outside: {supplier.name}" if supplier else "Outside process")
    if getattr(step, "is_decision_point", False) and step.decision_type:
        tags.append(f"Decision: {step.get_decision_type_display()}")
    if getattr(step, "is_terminal", False):
        tags.append("Terminal")
    return tags


def _fmt_measurement(m) -> str:
    """Render a MeasurementDefinition as a compact characteristic spec string,
    e.g. 'Spray Angle 12.5 ±0.5° (N-12)'."""
    parts = [m.label]
    unit = f"{m.unit}" if m.unit else ""
    if m.nominal is not None:
        nom = _fmt_dec(m.nominal)
        if (
            m.upper_tol is not None
            and m.lower_tol is not None
            and m.upper_tol == m.lower_tol
        ):
            parts.append(f"{nom} ±{_fmt_dec(m.upper_tol)}{unit}")
        elif m.upper_tol is not None or m.lower_tol is not None:
            up = f"+{_fmt_dec(m.upper_tol)}" if m.upper_tol is not None else ""
            lo = f"-{_fmt_dec(m.lower_tol)}" if m.lower_tol is not None else ""
            parts.append(f"{nom} {up}/{lo}{unit}".strip())
        elif unit:
            parts.append(f"{nom}{unit}")
        else:
            parts.append(nom)
    elif unit:
        parts.append(f"({unit})")
    label = " ".join(parts)
    char = m.characteristic_number
    if char:
        label += f" ({char})"
    return label


def _fmt_recorded(m) -> str:
    """A recorded StepExecutionMeasurement, e.g. 'Assembly Torque 25 Nm ✓ · M. Ops 10/6'."""
    d = m.measurement_definition
    label = d.label if d else "Measurement"
    if m.value is not None:
        value = _fmt_dec(m.value) + (f" {d.unit}" if d and d.unit else "")
    else:
        value = (m.string_value or "—").strip()
    verdict = {True: " ✓", False: " ✗ OUT OF SPEC"}.get(m.is_within_spec, "")
    who = _join_person_date(m.recorded_by, m.recorded_at)
    return f"{label} {value}{verdict}" + (f" · {who}" if who else "")


def _fmt_usage(u) -> str:
    """A material draw at a step, e.g. 'Lot STOCK-CRI-SOL · Solenoid Coil × 1'."""
    lot = u.lot
    if lot is not None:
        item = getattr(getattr(lot, "material", None), "name", None) or             getattr(getattr(lot, "material_type", None), "name", None) or ""
        text = f"Lot {lot.lot_number}" + (f" · {item}" if item else "")
    elif u.harvested_component_id:
        text = f"Harvested {u.harvested_component}"
    else:
        text = "Material"
    qty = _fmt_dec(u.qty_consumed) if u.qty_consumed is not None else None
    if qty:
        text += f" × {qty}"
    if u.is_substitute:
        text += " (substitute)"
    return text


def _fmt_override(o) -> str:
    """A step override, e.g. 'Training expired — approved S. Chen 10/6: <reason>'."""
    kind = o.get_block_type_display() if hasattr(o, "get_block_type_display") else str(o.block_type)
    state = o.get_status_display() if hasattr(o, "get_status_display") else str(o.status)
    who = _join_person_date(o.approved_by, o.approved_at)
    text = f"{kind} — {state.lower()}" + (f" {who}" if who else "")
    reason = (o.reason or "").strip()
    return text + (f": {reason}" if reason else "")


def _fmt_disposition(d) -> str:
    """A nonconformance and its disposition, e.g. 'DISP-0012 · Use as is · Closed · authorised S. Chen 10/6'."""
    number = d.disposition_number or "Disposition"
    kind = d.get_disposition_type_display() if d.disposition_type else "Undecided"
    state = d.get_current_state_display() if hasattr(d, "get_current_state_display") else str(d.current_state)
    text = f"{number} · {kind} · {state}"
    who = _join_person_date(d.decision_authorized_by, d.decision_authorized_at)
    if who:
        text += f" · authorised {who}"
    return text


def _resolve_drawing(part_type) -> tuple[Optional[str], Optional[str]]:
    """Resolve (drawing_number, drawing_revision) from a controlled Document
    of a 'Drawing' DocumentType attached to the part type.

    Returns (None, None) when no such document is attached — the traveler then
    renders "—" rather than a fabricated drawing number. Populating this
    requires a DocumentType with code DWG/DRAWING and a drawing attached to
    the part type (see the gaps note in REPORT_CONTENT_SPECS.md)."""
    if part_type is None:
        return None, None
    try:
        drawing = (
            part_type.documents
            .filter(
                is_current_version=True,
                document_type__code__in=["DWG", "DRAWING"],
            )
            .select_related("document_type")
            .order_by("-version")
            .first()
        )
    except Exception:  # noqa: BLE001 — a resolution failure must not break the traveler
        return None, None
    if drawing is None:
        return None, None
    number = drawing.file_name or None
    revision = f"Rev {drawing.version}" if getattr(drawing, "version", None) else None
    return number, revision


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class WorkOrderTravelerAdapter(ReportAdapter):
    """
    Renders a Work Order Traveler PDF for a given WorkOrder.

    The routing is resolved via WorkOrder → Processes → ProcessStep (ordered).
    If the WO has no process, the operations list is empty and the template
    renders a "no routing" note gracefully.
    """

    name = "work_order_traveler"
    title = "Work Order Traveler"
    template_path = "work_order_traveler.typ"
    context_model_class = WorkOrderTravelerContext
    param_serializer_class = WorkOrderTravelerParamsSerializer

    def build_context(self, validated_params, user, tenant) -> WorkOrderTravelerContext:
        from Tracker.models.mes_lite import ProcessStep, Parts, WorkOrder

        today = tenant_today(tenant)

        # tenant-safe: explicit tenant filter (defense-in-depth)
        wo = (
            WorkOrder.objects
            .filter(tenant=tenant)
            .select_related(
                "process__part_type",
                "related_order__company",
                "tenant",
            )
            .get(id=validated_params["id"])
        )

        process = wo.process
        part_type = process.part_type if (process and process.part_type) else None

        # ERP_id is nullable: a part type with no part number printed nothing but a 500.
        part_number = (part_type.ERP_id or "") if part_type else ""
        part_name = part_type.name if part_type else "-"
        revision: Optional[str] = None
        if part_type and getattr(part_type, "version", None):
            revision = f"Rev {part_type.version}"
        drawing_number, drawing_revision = _resolve_drawing(part_type)

        # As-built target part: an explicit `part` param, else the sole part on a
        # single-part WO. When resolved, routing rows are filled from that part's
        # StepExecution + QualityReports history; otherwise cells stay blank
        # (the job-release form). tenant-safe: explicit tenant filter.
        target_part = self._resolve_part(wo, tenant, validated_params.get("part"))
        exec_by_step, qr_by_step = self._history_maps(target_part, tenant)
        trace_by_step = self._trace_maps(target_part, tenant)
        signoff_by_step = self._signoff_map(wo, tenant) if target_part else {}

        # Routing — ProcessStep rows are scoped through the (tenant-checked)
        # process; ProcessStep itself is not a SecureModel.
        operations: list[TravelerOperation] = []
        if process is not None:
            process_steps = (
                ProcessStep.objects
                .filter(process=process)
                .select_related("step", "step__outside_supplier")
                .prefetch_related("step__measurement_definitions")
                .order_by("order")
            )
            for ps in process_steps:
                step = ps.step
                specs = [
                    _fmt_measurement(m)
                    for m in step.measurement_definitions.all()
                    if getattr(m, "is_current_version", True)
                ]
                description = (step.description or "").strip() or None
                operator, inspector, acc_rej, remarks = self._step_actuals(
                    exec_by_step.get(step.id), qr_by_step.get(step.id),
                    signoff_by_step.get(step.id),
                )
                trace = trace_by_step.get(step.id, {})
                operations.append(TravelerOperation(
                    seq=str(ps.order),
                    op_number=(getattr(step, "operation_number", "") or "").strip() or None,
                    step_name=step.name,
                    step_type=step.get_step_type_display(),
                    description=description,
                    std_time=_fmt_duration(step.expected_duration),
                    controls=_step_controls(step),
                    specs=specs,
                    is_outside_process=bool(getattr(step, "is_outside_process", False)),
                    operator=operator,
                    inspector=inspector,
                    acc_rej=acc_rej,
                    remarks=remarks,
                    recorded=trace.get("recorded", []),
                    materials=trace.get("materials", []),
                    visits=trace.get("visits", 0),
                    overrides=trace.get("overrides", []),
                ))

        order = wo.related_order
        order_number = None
        order_name = None
        customer_name = None
        if order is not None:
            order_number = order.order_number or None
            order_name = order.name or None
            if order.company is not None:
                customer_name = order.company.name

        return WorkOrderTravelerContext(
            wo_number=wo.ERP_id,
            part_number=part_number,
            part_name=part_name,
            process_name=process.name if process else "-",
            revision=revision,
            serial=(target_part.ERP_id if target_part else None),
            drawing_number=drawing_number,
            drawing_revision=drawing_revision,
            quantity=wo.quantity,
            priority=wo.get_priority_display(),
            status=wo.get_workorder_status_display(),
            start_date=wo.expected_start,
            due_date=wo.expected_completion,
            order_number=order_number,
            order_name=order_name,
            customer_name=customer_name,
            operations=operations,
            total_operations=len(operations),
            barcode_svg=render_barcode_svg(wo.ERP_id or "UNKNOWN", module_height=8.0),
            qr_svg=render_qr_svg(
                f"https://{getattr(tenant, 'slug', None) or 'example'}"
                f".ambactracker.example/workorder/{wo.id}"
            ),
            nonconformances=self._nonconformances(target_part, tenant),
            **self._serials(wo, tenant),
            tenant_name=tenant.name,
            generated_date=today,
        )

    # A work order's per-serial lines stop here; the rest are counted, not listed.
    SERIAL_CAP = 200

    def _trace_maps(self, part, tenant) -> dict:
        """Per step, for the resolved serial: recorded measurements, lots drawn,
        number of visits, and step overrides. Empty when no part is resolved."""
        if part is None:
            return {}
        from Tracker.models import MaterialUsage, StepExecutionMeasurement, StepOverride

        out: dict = {}

        def slot(step_id):
            return out.setdefault(step_id, {"recorded": [], "materials": [], "visits": 0, "overrides": []})

        for ex in part.step_executions.all():
            slot(ex.step_id)["visits"] += 1
        # tenant-safe: every query below is keyed to the tenant-checked part.
        for m in (StepExecutionMeasurement.objects
                  .filter(tenant=tenant, step_execution__part=part)
                  .select_related("measurement_definition", "recorded_by", "step_execution")
                  .order_by("recorded_at")):
            slot(m.step_execution.step_id)["recorded"].append(_fmt_recorded(m))
        for u in (MaterialUsage.objects
                  .filter(tenant=tenant, part=part)
                  .select_related("lot__material", "lot__material_type", "harvested_component")
                  .order_by("consumed_at")):
            if u.step_id:
                slot(u.step_id)["materials"].append(_fmt_usage(u))
        for o in (StepOverride.objects
                  .filter(tenant=tenant, step_execution__part=part)
                  .select_related("approved_by", "step_execution")
                  .order_by("requested_at")):
            slot(o.step_execution.step_id)["overrides"].append(_fmt_override(o))
        return out

    def _nonconformances(self, part, tenant) -> list[str]:
        """The resolved serial's dispositions, oldest first."""
        if part is None:
            return []
        from Tracker.models import QuarantineDisposition
        # tenant-safe: explicit tenant filter
        return [_fmt_disposition(d) for d in (
            QuarantineDisposition.objects
            .filter(tenant=tenant, part=part)
            .select_related("decision_authorized_by")
            .order_by("created_at"))]

    def _serials(self, wo, tenant) -> dict:
        """One line per serial on a multi-serial work order (empty for a single one)."""
        from django.db.models import Count, Q
        from Tracker.models import Parts

        # tenant-safe: explicit tenant filter
        qs = (Parts.objects.filter(tenant=tenant, work_order=wo)
              .select_related("step")
              .annotate(open_ncrs=Count(
                  "quarantinedisposition",
                  filter=~Q(quarantinedisposition__current_state="CLOSED"), distinct=True))
              .order_by("ERP_id"))
        total = qs.count()
        if total < 2:
            return {"serials": [], "serials_truncated": 0}
        rows = [TravelerSerial(
            serial=p.ERP_id,
            step=(p.step.name if p.step_id else None),
            status=p.get_part_status_display(),
            open_ncrs=p.open_ncrs,
            shipped=(p.part_status == "SHIPPED"),
        ) for p in qs[:self.SERIAL_CAP]]
        return {"serials": rows, "serials_truncated": max(0, total - self.SERIAL_CAP)}

    def _resolve_part(self, wo, tenant, part_id):
        """The part whose as-built history fills the routing rows: an explicit
        `part_id`, else the sole part on a single-part WO, else None."""
        from Tracker.models.mes_lite import Parts

        if part_id:
            return (
                Parts.objects
                .filter(tenant=tenant, work_order=wo, id=part_id)
                .select_related("part_type")
                .first()
            )
        parts = list(
            Parts.objects.filter(tenant=tenant, work_order=wo)
            .select_related("part_type")[:2]
        )
        return parts[0] if len(parts) == 1 else None

    def _history_maps(self, part, tenant):
        """Prefetch a part's executions + quality reports keyed by step id
        (avoids per-row queries). Empty dicts when no part is resolved."""
        if part is None:
            return {}, {}

        from Tracker.models.qms import QualityReports

        exec_by_step: dict = {}
        for ex in (
            part.step_executions
            .select_related("completed_by", "assigned_to")
            .order_by("visit_number", "entered_at")
        ):
            exec_by_step[ex.step_id] = ex  # keep the latest visit

        # Keep one report per step, preferring a decided verdict (PASS/FAIL)
        # over a PENDING placeholder, and the latest among equals — so a real
        # FAIL is never masked by a later auto-bound PENDING inspection QR.
        def _rank(qr):
            return 1 if getattr(qr, "status", None) in ("PASS", "FAIL") else 0

        qr_by_step: dict = {}
        for qr in (
            QualityReports.objects
            .filter(tenant=tenant, part=part)
            .select_related("detected_by", "verified_by")
            .order_by("created_at")
        ):
            if qr.step_id is None:
                continue
            current = qr_by_step.get(qr.step_id)
            if current is None or _rank(qr) >= _rank(current):
                qr_by_step[qr.step_id] = qr
        return exec_by_step, qr_by_step

    def _signoff_map(self, wo, tenant) -> dict:
        """The QA sign-off (QaApproval) of each step on this work order, by step id."""
        from Tracker.models import QaApproval
        # tenant-safe: explicit tenant filter
        return {a.step_id: a for a in (
            QaApproval.objects.filter(tenant=tenant, work_order=wo, archived=False)
            .select_related("qa_staff").order_by("created_at"))}

    def _step_actuals(self, execution, quality_report, qa_signoff=None):
        """(operator, inspector, acc_rej, remarks) for one routing row, from the
        step's latest StepExecution + QualityReports, else its QA sign-off. All None
        when absent.

        Inspector is whoever inspected — the report's verifier/detector, or on a QA
        sign-off step with no report, the QaApproval's signer. It used to come only from
        a report, so a signed-off step printed its inspector nowhere (2026-10-08)."""
        operator = inspector = acc_rej = remarks = None

        if execution is not None:
            who = execution.completed_by or execution.assigned_to
            when = execution.exited_at or execution.started_at or execution.entered_at
            operator = _join_person_date(who, when)

        if quality_report is not None:
            who = quality_report.verified_by or quality_report.detected_by
            inspector = _join_person_date(who, quality_report.created_at)
            status = getattr(quality_report, "status", None)
            if status == "PASS":
                acc_rej = "ACC"
            elif status == "FAIL":
                acc_rej = "REJ"
            # Full text — the Remarks box grows to fit; clipping a
            # nonconformance finding mid-sentence loses traceability.
            desc = (quality_report.description or "").strip()
            if desc:
                remarks = desc
        elif qa_signoff is not None:
            inspector = _join_person_date(qa_signoff.qa_staff, qa_signoff.created_at)
            acc_rej = "ACC"  # a QA sign-off is the step's acceptance

        return operator, inspector, acc_rej, remarks

    def get_filename(self, validated_params) -> str:
        return f"work_order_traveler_{validated_params.get('id', 'unknown')}.pdf"
