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
from .routes import BUILD, REMAN, process_named, route_steps, step_key


class DemoOutsideProcessSeeder(BaseSeeder):
    """Seeds an OSP step + parts staged across ready-to-ship / at-vendor / returned."""

    def __init__(self, stdout, style, tenant, scale="small"):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant

    def _sync_process_order(self, process):
        """Renumber a process's ProcessStep.order to follow its DEFAULT-edge forward
        spine, so `order` and routing never disagree. Steps reachable from the entry
        along DEFAULT edges get 1..k in topological order; off-spine stations (e.g. a
        Rework node reached only via ALTERNATE) are appended after by their prior
        order. Idempotent — the same routing always yields the same numbering."""
        import heapq
        from collections import deque

        pss = list(ProcessStep.objects.filter(process=process).select_related('step'))
        if len(pss) < 2:
            return
        ids = {ps.step_id for ps in pss}
        existing = {ps.step_id: ps.order for ps in pss}
        adj = {}
        for e in StepEdge.objects.filter(process=process, edge_type=EdgeType.DEFAULT):
            if e.from_step_id in ids and e.to_step_id in ids:
                adj.setdefault(e.from_step_id, []).append(e.to_step_id)
        if not adj:
            return  # no DEFAULT routing to derive order from — keep authored order

        entry = next((ps.step_id for ps in pss if ps.is_entry_point), None) \
            or min(pss, key=lambda p: p.order).step_id

        # Forward-reachable spine from the entry (excludes back-edge-only stations).
        reachable, dq = set(), deque([entry])
        while dq:
            s = dq.popleft()
            if s in reachable:
                continue
            reachable.add(s)
            for nxt in adj.get(s, ()):
                if nxt not in reachable:
                    dq.append(nxt)

        # Kahn topological order of the induced spine, tie-broken by prior order.
        indeg = {s: 0 for s in reachable}
        for s in reachable:
            for nxt in adj.get(s, ()):
                if nxt in reachable:
                    indeg[nxt] += 1
        heap = [(existing.get(s, 0), str(s), s) for s in reachable if indeg[s] == 0]
        heapq.heapify(heap)
        ordered, seen = [], set()
        while heap:
            _, _, s = heapq.heappop(heap)
            if s in seen:
                continue
            seen.add(s)
            ordered.append(s)
            for nxt in adj.get(s, ()):
                if nxt in reachable:
                    indeg[nxt] -= 1
                    if indeg[nxt] == 0:
                        heapq.heappush(heap, (existing.get(nxt, 0), str(nxt), nxt))
        ordered += sorted(ids - set(ordered), key=lambda x: existing.get(x, 0))

        # Two-phase write to respect the unique(process, order) constraint: park at
        # high temp orders, then assign the final 1..N.
        for sid in ids:
            ProcessStep.objects.filter(process=process, step_id=sid).update(
                order=10000 + existing.get(sid, 0))
        for pos, sid in enumerate(ordered, start=1):
            ProcessStep.objects.filter(process=process, step_id=sid).update(order=pos)

    def _osp_step(self, process, part_type, vendor, route, *, after, before):
        """The route's Nitride Coating step: an outside-process node with Apex as its
        vendor, spliced into the route between `after` and `before`."""
        osp_step, _ = Steps.objects.update_or_create(
            tenant=self.tenant, part_type=part_type, external_id=step_key(route, "Nitride Coating"),
            defaults={
                "name": "Nitride Coating",
                "step_type": "TASK",
                "description": "Send injector bodies out for nitride coating, then inspect on return.",
                "is_outside_process": True,
                "outside_supplier": vendor,
                # Nitriding is a special process: only a vendor qualified for it may do
                # it, and send-out refuses one who isn't (outside_process.send_parts_out).
                "outside_special_process": "Nitriding",
                # Vendor turnaround for this OSP step (calendar days). Explicit so the
                # solver uses 2 days here, not the tenant fallback (config default).
                "outside_process_lead_days": 2,
                # No shop operator during the vendor turnaround — the subcontractor does
                # the coating. Without this the step defaults to 'pool' and shows dozens
                # of phantom "unassigned" operator tasks (the return inspection is its
                # own DWI content, not this scheduled span).
                "labor_model": "off",
            },
        )
        # Return-inspection characteristic (measured when parts come back).
        thickness, _ = MeasurementDefinition.objects.update_or_create(
            tenant=self.tenant, step=osp_step, label="Coating Thickness",
            defaults={"type": "NUMERIC", "unit": "µm",
                      "nominal": Decimal("12.000000"),
                      "upper_tol": Decimal("3.000000"), "lower_tol": Decimal("2.000000")},
        )
        StepMeasurementRequirement.objects.get_or_create(step=osp_step, measurement=thickness)

        # Put the OSP step on the process. The order here is a placeholder —
        # `_sync_process_order` below fixes every step's order to match the routing.
        ProcessStep.objects.get_or_create(
            process=process, step=osp_step,
            defaults={"order": ProcessStep.objects.filter(process=process).count() + 1})
        # Splice it into the routing chain so it isn't an unreachable dangling node in
        # the flow editor, and returned parts have a real next step after acceptance.
        steps = route_steps(process)
        frm, to = steps.get(after), steps.get(before)
        if frm is not None and to is not None:
            StepEdge.objects.filter(process=process, from_step=frm,
                                    to_step=to, edge_type=EdgeType.DEFAULT).delete()
            for a, b in ((frm, osp_step), (osp_step, to)):
                StepEdge.objects.update_or_create(
                    process=process, from_step=a, to_step=b, edge_type=EdgeType.DEFAULT,
                    defaults={"condition_measurement": None, "condition_operator": "",
                              "condition_value": None},
                )
        # Order must agree with the routing: renumber by the DEFAULT-edge forward spine.
        self._sync_process_order(process)
        return osp_step

    def seed(self, companies, users, manufacturing, orders):
        self.log("Creating demo outside-processing data...")
        result = {"step": None, "reman_step": None, "shipments": [], "ready_parts": []}

        part_types = manufacturing.get("part_types", []) if isinstance(manufacturing, dict) else []
        if not part_types:
            self.log("  Warning: no part types, skipping OSP seed", warning=True)
            return result
        part_type = part_types[0]

        employees = users.get("employees", []) if isinstance(users, dict) else []
        # The return inspection is the QA inspector's — not employees[0] (the admin).
        inspectors = [u for u in (users.get("qa_staff") or []) if u != users.get("qa_manager")] \
            if isinstance(users, dict) else []
        user = (inspectors or employees or [None])[0]

        work_orders = orders.get("work_orders", []) if isinstance(orders, dict) else []
        # The exhibit parts ride a new-build work order: nitriding the machined body
        # is new-manufacture work.
        work_order = next((wo for wo in work_orders
                           if wo.process and wo.process.name == BUILD), None)
        order = getattr(work_order, "related_order", None) if work_order else None
        if work_order is None or order is None or user is None:
            self.log("  Warning: no new-build work order / user, skipping OSP seed", warning=True)
            return result

        # Plating subcontractor as the default vendor (ties to the SQM seeder's Apex).
        vendor, _ = Companies.objects.update_or_create(
            tenant=self.tenant, name="Apex Plating Co",
            defaults={"description": "Plating subcontractor - outside-process vendor."},
        )

        # Each route nitrides at its own point, on its own step: a new body before it is
        # assembled, a rebuilt unit after reassembly.
        osp_step = self._osp_step(work_order.process, part_type, vendor, "build",
                                  after="Body Inspection", before="Assembly")
        reman = process_named(self.tenant, REMAN)
        if reman is not None:
            result["reman_step"] = self._osp_step(reman, part_type, vendor, "reman",
                                                  after="Reassembly", before="Final Test")
        result["step"] = osp_step

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
