"""
Demo seeder for Outside Processing (subcontract, Flow B).

Stands up the OSP surfaces end-to-end so the shipper board, the "At vendor" lens,
the unified incoming queue, and the OSP return-inspection runtime all have data:
  - flags a dedicated step as an outside-process node with a default vendor;
  - stages parts across the three states a shipper/inspector sees:
      * **Ready to ship** — staged at the OSP step, not yet dispatched;
      * **At vendor** — a SENT shipment;
      * **Returned** — a RETURNED shipment with its return inspection open.

Runs after the orders seeder (needs a work order to hang parts on) and before the
DWI seeder (which authors the return-inspection work instructions on the OSP step).
"""
from decimal import Decimal

from Tracker.models import (
    Companies, EdgeType, MeasurementDefinition, Parts, PartsStatus, ProcessStep,
    StepEdge, StepMeasurementRequirement, Steps,
)
from Tracker.services.mes import outside_process

from ..base import BaseSeeder


class DemoOutsideProcessSeeder(BaseSeeder):
    """Seeds an OSP step + parts staged across ready-to-ship / at-vendor / returned."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def seed(self, companies, users, manufacturing, orders):
        self.log("Creating demo outside-processing data...")
        result = {"step": None, "shipments": [], "ready_parts": []}

        part_types = manufacturing.get("part_types", []) if isinstance(manufacturing, dict) else []
        processes = manufacturing.get("processes", []) if isinstance(manufacturing, dict) else []
        if not part_types:
            self.log("  Warning: no part types, skipping OSP seed", warning=True)
            return result
        part_type = part_types[0]
        process = processes[0] if processes else None

        employees = users.get("employees", []) if isinstance(users, dict) else []
        user = employees[0] if employees else None

        work_orders = orders.get("work_orders", []) if isinstance(orders, dict) else []
        work_order = work_orders[0] if work_orders else None
        order = getattr(work_order, "related_order", None) if work_order else None
        if work_order is None or order is None or user is None:
            self.log("  Warning: no work order / user, skipping OSP seed", warning=True)
            return result

        # Plating subcontractor as the default vendor (ties to the SQM seeder's Apex).
        vendor, _ = Companies.objects.update_or_create(
            tenant=self.tenant, name="Apex Plating Co",
            defaults={"description": "Plating subcontractor — outside-process vendor."},
        )

        # --- OSP step: a subcontract node with a default vendor ---
        osp_step, _ = Steps.objects.update_or_create(
            tenant=self.tenant, part_type=part_type, name="Nitride Coating (Outside Process)",
            defaults={
                "step_type": "TASK",
                "description": "Send injector bodies out for nitride coating, then inspect on return.",
                "is_outside_process": True,
                "outside_supplier": vendor,
            },
        )
        # Ensure the flag/vendor stick even if the step pre-existed.
        if not osp_step.is_outside_process or osp_step.outside_supplier_id != vendor.id:
            osp_step.is_outside_process = True
            osp_step.outside_supplier = vendor
            osp_step.save(update_fields=["is_outside_process", "outside_supplier"])
        result["step"] = osp_step

        # Return-inspection characteristic (measured when parts come back).
        thickness, _ = MeasurementDefinition.objects.update_or_create(
            tenant=self.tenant, step=osp_step, label="Coating Thickness",
            defaults={"type": "NUMERIC", "unit": "µm",
                      "nominal": Decimal("12.000000"),
                      "upper_tol": Decimal("3.000000"), "lower_tol": Decimal("2.000000")},
        )
        StepMeasurementRequirement.objects.get_or_create(step=osp_step, measurement=thickness)

        if process is not None:
            next_order = (ProcessStep.objects.filter(process=process)
                          .order_by("-order").values_list("order", flat=True).first() or 0) + 1
            ProcessStep.objects.get_or_create(process=process, step=osp_step,
                                              defaults={"order": next_order})
            # Splice the OSP step into the routing chain (Assembly → Nitride →
            # Final Test) so it isn't an unreachable dangling node in the flow
            # editor — and returned parts have a real next step after acceptance.
            assembly = Steps.objects.filter(part_type=part_type, name="Assembly").first()
            final_test = Steps.objects.filter(part_type=part_type, name="Final Test").first()
            if assembly is not None and final_test is not None:
                StepEdge.objects.filter(process=process, from_step=assembly,
                                        to_step=final_test, edge_type=EdgeType.DEFAULT).delete()
                for frm, to in ((assembly, osp_step), (osp_step, final_test)):
                    StepEdge.objects.update_or_create(
                        process=process, from_step=frm, to_step=to, edge_type=EdgeType.DEFAULT,
                        defaults={"condition_measurement": None, "condition_operator": "",
                                  "condition_value": None},
                    )

        # --- Parts staged at the OSP step (dedicated, so other narratives are untouched) ---
        def make_part(suffix):
            part, _ = Parts.objects.update_or_create(
                tenant=self.tenant, ERP_id=f"OSP-DEMO-{suffix}",
                defaults={
                    "part_type": part_type, "order": order, "work_order": work_order,
                    "step": osp_step, "part_status": PartsStatus.IN_PROGRESS,
                    "requires_sampling": False, "sampling_rule": None, "sampling_ruleset": None,
                    "sampling_context": {}, "total_rework_count": 0,
                    "itar_controlled": False, "eccn": "", "export_license_required": False,
                    "country_of_origin": "", "is_fpi_candidate": False, "fpi_override_reason": "",
                },
            )
            return part

        parts = [make_part(f"{i:03d}") for i in range(1, 7)]

        # Ready to ship — leave 2 staged at the step (build_ready_to_ship_groups picks them up).
        result["ready_parts"] = parts[0:2]

        # At vendor — dispatch 2 as a SENT shipment.
        try:
            sent = outside_process.send_parts_out(
                step=osp_step, parts=parts[2:4], supplier=vendor,
                reference="OSP-2026-NITRIDE-01", user=user)
            result["shipments"].append(sent)
        except ValueError as e:
            self.log(f"  Skipped send-out: {e}", warning=True)

        # Returned — dispatch 2 then receive them back (opens the return inspection).
        try:
            shipped = outside_process.send_parts_out(
                step=osp_step, parts=parts[4:6], supplier=vendor,
                reference="OSP-2026-NITRIDE-02", user=user)
            outside_process.receive_parts_back(shipped, user=user)
            result["shipments"].append(shipped)
        except ValueError as e:
            self.log(f"  Skipped send/receive: {e}", warning=True)

        self.log(f"  Flagged OSP step '{osp_step.name}', staged {len(result['ready_parts'])} ready-to-ship, "
                 f"{len(result['shipments'])} shipment(s) (1 at vendor, 1 returned)")
        return result
