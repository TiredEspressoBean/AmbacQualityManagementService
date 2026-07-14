"""
Demo SHOWCASE seeder — dedicated, searchable storyline objects for the
product demo script.

The demo walks one remanufactured diesel injector through the "Injector Reman"
process across four UI surfaces: process flow editor -> DWI authoring ->
operator runtime -> 3D annotation + heatmap. The generic seeded data has
cryptic serials and nothing cleanly parked for the operator/annotator scenes,
so this seeder creates a small set of named objects all tagged "SHOWCASE" and
threaded by one hero part `INJ-SHOWCASE-001`:

- A standalone DRAFT clone of "Injector Reman" ("... — Authoring Draft
  (SHOWCASE)") so the authoring/process-editor scene has an editable process
  reusing the same Step nodes (and their Nozzle Inspection substep editor).
- Work order `WO-SHOWCASE-01` on the approved Injector Reman process (plus an
  `ORD-SHOWCASE` order to hang it on).
- Hero part `INJ-SHOWCASE-001` parked at Nozzle Inspection with an open
  `StepExecution` so the operator runtime resolves to a live run.
- FAIL quality report `QR-SHOWCASE-001` on the hero part, linked to an
  ErrorType flagged `requires_3d_annotation=True` so the 3D annotator triggers.

Everything is idempotent (update_or_create / existence guards) so re-running
`seed_demo` is safe.
"""

from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    Orders, Parts, WorkOrder, Steps, Processes,
    OrdersStatus, WorkOrderStatus, WorkOrderPriority, PartsStatus,
    StepExecution, QualityReports, QualityErrorsList,
)
from Tracker.models.mes_lite import ProcessStatus
from Tracker.services.mes.processes import duplicate_process

from ..base import BaseSeeder


AUTHORING_DRAFT_NAME = "Injector Reman — Authoring Draft (SHOWCASE)"


class DemoShowcaseSeeder(BaseSeeder):
    """Seeds the named SHOWCASE storyline objects for the product demo."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    def seed(self, manufacturing, models_3d, users):
        self.log("Creating SHOWCASE storyline objects...")

        # --- Resolve dependencies from the already-seeded data -------------
        process = self._injector_reman_process(manufacturing)
        if not process:
            self.log("  Injector Reman process not found — skipping SHOWCASE seeding", warning=True)
            return {}

        nozzle_step = Steps.objects.filter(tenant=self.tenant, name="Nozzle Inspection").first()
        if not nozzle_step:
            self.log("  'Nozzle Inspection' step not found — skipping SHOWCASE seeding", warning=True)
            return {}

        part_type = self._part_type(manufacturing)
        admin_user = self._user(users, ["admin@demo.ambac.com"], roles=["managers", "employees"])
        operator_user = self._user(users, ["mike.ops@demo.ambac.com", "dave.wilson@demo.ambac.com"],
                                   roles=["employees"])
        inspector_user = self._user(users, ["sarah.qa@demo.ambac.com", "maria.qa@demo.ambac.com"],
                                    roles=["qa_staff", "employees"])

        result = {}

        # --- 1) Standalone DRAFT clone for the authoring scene -------------
        result["authoring_draft"] = self._authoring_draft(process, admin_user)

        # --- 2) Order + work order ----------------------------------------
        order = self._order()
        work_order = self._work_order(order, process)
        result["order"] = order
        result["work_order"] = work_order

        # --- 3) Hero part parked at Nozzle Inspection + open execution -----
        hero_part = self._hero_part(part_type, order, work_order, nozzle_step)
        result["hero_part"] = hero_part
        result["step_execution"] = self._open_execution(hero_part, nozzle_step, operator_user)

        # --- 4) FAIL quality report wired to a 3D-annotation error type ----
        result["quality_report"] = self._fail_quality_report(hero_part, nozzle_step, inspector_user)

        self._log_summary(result)
        return result

    # ------------------------------------------------------------------ deps

    def _injector_reman_process(self, manufacturing):
        """The APPROVED Injector Reman process from the manufacturing seeder."""
        processes = manufacturing.get("processes", []) if manufacturing else []
        for p in processes:
            if p.name == "Injector Reman":
                return p
        return (
            Processes.objects.filter(
                tenant=self.tenant, name="Injector Reman", status=ProcessStatus.APPROVED
            ).first()
            or Processes.objects.filter(tenant=self.tenant, name="Injector Reman").first()
        )

    def _part_type(self, manufacturing):
        part_types = manufacturing.get("part_types", []) if manufacturing else []
        for pt in part_types:
            if pt.name == "Common Rail Injector":
                return pt
        return part_types[0] if part_types else None

    def _user(self, users, emails, roles):
        """Resolve a user by preferred email, falling back to a role list."""
        by_email = users.get("by_email", {}) if users else {}
        for email in emails:
            if email in by_email:
                return by_email[email]
        for role in roles:
            candidates = users.get(role, []) if users else []
            if candidates:
                return candidates[0]
        return None

    # --------------------------------------------------------------- objects

    def _authoring_draft(self, process, admin_user):
        """Standalone DRAFT clone reusing the same Step nodes. Idempotent by name."""
        existing = Processes.objects.filter(tenant=self.tenant, name=AUTHORING_DRAFT_NAME).first()
        if existing:
            self.log(f"  Authoring draft already exists: {existing.name}")
            return existing

        draft = duplicate_process(
            process, user=admin_user, name_suffix=" — Authoring Draft (SHOWCASE)"
        )
        self.log(f"  Created authoring draft process: {draft.name} ({draft.status})")
        return draft

    def _order(self):
        order, _ = Orders.objects.update_or_create(
            tenant=self.tenant,
            order_number="ORD-SHOWCASE",
            defaults={
                "name": "SHOWCASE Demo Order — Injector Reman",
                "company": None,
                "customer": None,
                "customer_note": None,
                "order_status": OrdersStatus.IN_PROGRESS,
                "estimated_completion": (self.today + timedelta(days=7)).date(),
                "original_completion_date": None,
                "current_hubspot_gate": None,
                "hubspot_deal_id": None,
                "last_synced_hubspot_stage": None,
                "hubspot_last_synced_at": None,
            },
        )
        return order

    def _work_order(self, order, process):
        work_order, _ = WorkOrder.objects.update_or_create(
            tenant=self.tenant,
            ERP_id="WO-SHOWCASE-01",
            defaults={
                "related_order": order,
                "process": process,
                "workorder_status": WorkOrderStatus.IN_PROGRESS,
                "priority": WorkOrderPriority.HIGH,
                "expected_completion": (self.today + timedelta(days=5)).date(),
                "quantity": 1,
                "notes": "SHOWCASE demo work order — hero injector INJ-SHOWCASE-001.",
                "expected_duration": None,
                "true_completion": None,
                "true_duration": None,
            },
        )
        return work_order

    def _hero_part(self, part_type, order, work_order, nozzle_step):
        part, _ = Parts.objects.update_or_create(
            tenant=self.tenant,
            ERP_id="INJ-SHOWCASE-001",
            defaults={
                "part_type": part_type,
                "order": order,
                "work_order": work_order,
                "step": nozzle_step,  # parked at Nozzle Inspection
                "part_status": PartsStatus.IN_PROGRESS,
                "requires_sampling": False,
                "sampling_rule": None,
                "sampling_ruleset": None,
                "sampling_context": {},
                "total_rework_count": 0,
                "itar_controlled": False,
                "eccn": "",
                "export_license_required": False,
                "country_of_origin": "",
                "is_fpi_candidate": False,
                "fpi_override_reason": "",
            },
        )
        return part

    def _open_execution(self, hero_part, nozzle_step, operator_user):
        """Open StepExecution so the operator runtime resolves to a live run."""
        existing = StepExecution.objects.filter(
            tenant=self.tenant,
            part=hero_part,
            step=nozzle_step,
            visit_number=1,
        ).first()
        if existing:
            if existing.status != "IN_PROGRESS" or existing.exited_at is not None:
                StepExecution.objects.filter(pk=existing.pk).update(
                    status="IN_PROGRESS", exited_at=None, completed_by=None
                )
                existing.refresh_from_db()
            self.log(f"  Open StepExecution already exists for {hero_part.ERP_id}")
            return existing

        execution = StepExecution.objects.create(
            tenant=self.tenant,
            part=hero_part,
            step=nozzle_step,
            visit_number=1,
            entered_at=self.today,
            started_at=self.today,
            exited_at=None,
            assigned_to=operator_user,
            completed_by=None,
            next_step=None,
            status="IN_PROGRESS",
        )
        return execution

    def _fail_quality_report(self, hero_part, nozzle_step, inspector_user):
        error_type = self._annotation_error_type()

        qr, _ = QualityReports.objects.update_or_create(
            tenant=self.tenant,
            report_number="QR-SHOWCASE-001",
            defaults={
                "part": hero_part,
                "step": nozzle_step,
                "status": "FAIL",
                "description": "Nozzle tip scoring found during visual inspection — 3D annotation required.",
                "detected_by": inspector_user,
                "verified_by": None,
                "sampling_method": "manual",
                "is_first_piece": False,
                "file": None,
                "sampling_audit_log": None,
            },
        )

        if error_type:
            qr.errors.set([error_type])
        else:
            self.log(
                "  No requires_3d_annotation ErrorType found — QR created without a defect link",
                warning=True,
            )

        return qr

    def _annotation_error_type(self):
        """An ErrorType flagged requires_3d_annotation=True for this tenant."""
        return (
            QualityErrorsList.objects.filter(tenant=self.tenant, requires_3d_annotation=True)
            .order_by("error_name")
            .first()
        )

    # ---------------------------------------------------------------- logging

    def _log_summary(self, result):
        draft = result.get("authoring_draft")
        order = result.get("order")
        wo = result.get("work_order")
        part = result.get("hero_part")
        ex = result.get("step_execution")
        qr = result.get("quality_report")

        self.log("  SHOWCASE storyline created:")
        if draft:
            self.log(f"    - Authoring draft process: {draft.name} ({draft.status})")
        if order:
            self.log(f"    - Order: {order.order_number} ({order.order_status})")
        if wo:
            self.log(f"    - Work order: {wo.ERP_id} on '{wo.process.name}'")
        if part:
            step_name = part.step.name if part.step else "(none)"
            self.log(f"    - Hero part: {part.ERP_id} status={part.part_status} parked at '{step_name}'")
        if ex:
            self.log(f"    - StepExecution: visit {ex.visit_number} status={ex.status}")
        if qr:
            linked = list(qr.errors.values_list("error_name", flat=True))
            self.log(f"    - Quality report: {qr.report_number} status={qr.status} errors={linked}")
