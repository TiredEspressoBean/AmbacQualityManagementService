"""Operator exhibits, walked through the production services.

The operator track's day is Mike Rodriguez's, on the new-build route (Injector Build):

- WO-OPS-01: four bodies released and waiting at Machining, unclaimed: Mike's
  "Up next" when he clocks in.
- WO-OPS-02: four bodies machined and ground by Dave, then loaded into the Wash by
  Dave and left running: the load Mike takes over, through the reassignment gate.
- WO-OPS-03: two bodies inspected (first piece bought off by Sarah) and back from the
  plater, waiting at Assembly: where Mike's component lots are drawn for him.
- Two shift notes from Casey, one he must acknowledge at clock-in.
- WO-PM-MAKEUP-01: the Production Manager's exhibit, a job one body short after a
  scrap, its disposition decided and verified, waiting for the PM to close it and
  top the job up.

Reuses the QA walk's building blocks (DemoQaWalkSeeder), so every record is made
the way the runtime makes it.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import BatchExecution, Orders, OrdersStatus, QuarantineDisposition, WorkOrder

from .qa_walk import DemoQaWalkSeeder, PROCESS_NAME

ORDER_NUMBER = 'ORD-2024-OPS'
UP_NEXT_WO = 'WO-OPS-01'
UP_NEXT_PARTS = ['INJ-OPS-001', 'INJ-OPS-002', 'INJ-OPS-003', 'INJ-OPS-004']
WASH_WO = 'WO-OPS-02'
WASH_PARTS = ['INJ-OPS-011', 'INJ-OPS-012', 'INJ-OPS-013', 'INJ-OPS-014']
ASSEMBLY_WO = 'WO-OPS-03'
ASSEMBLY_PARTS = ['INJ-OPS-021', 'INJ-OPS-022']

# A job one good unit short: its first body scrapped at Machining (the PM's make-up).
MAKEUP_WO = 'WO-PM-MAKEUP-01'
MAKEUP_PARTS = ['INJ-PMK-001', 'INJ-PMK-002', 'INJ-PMK-003', 'INJ-PMK-004']
MAKEUP_DUE_DAYS = 12

# A repair unit held at Nozzle Inspection by a finding that waits for the lead.
LEAD_FINDING_CORE = 'CORE-240214-0010'
LEAD_FINDING = ('Injector Nozzle Assembly', 'SCRAP',
                'Seat eroded through at the needle guide; leaks down on the spray test.')

# A customer's own unit walked through its whole rebuild: on the shipping board.
REBUILT_CORE = 'CORE-240217-0013'

# Two cores Dave received, waiting at Disassembly for Mike to tear down and grade.
GRADING_CORES = ['CORE-240220-0003', 'CORE-240220-0004']

SHIFT_NOTES = [
    {'body': 'Flow Test Stand #2 is down until 10:00 for a seal change. Run Flow '
             'Calibration on Stand #1 only until then.',
     'priority': 'HIGH', 'acknowledgment_required': True, 'hours': 4},
    {'body': "Apex's nitride load is due back after lunch. Clear the Assembly bench "
             "before 13:00.",
     'priority': 'NORMAL', 'acknowledgment_required': False, 'hours': 8},
]


class DemoOpsWalkSeeder(DemoQaWalkSeeder):
    """Walks the Operator exhibits through the production services."""

    def seed(self, companies, users, manufacturing):
        self.log("Walking the Operator exhibits through the services...")
        result = {'work_orders': [], 'shift_notes': []}

        by_email = (users or {}).get('by_email', {})
        self.mike = by_email.get('mike.ops@demo.ambac.com')
        self.dave = by_email.get('dave.wilson@demo.ambac.com')
        self.casey = by_email.get('casey.dual@demo.ambac.com')
        self.sarah = by_email.get('sarah.qa@demo.ambac.com')
        self.maria = by_email.get('maria.qa@demo.ambac.com')
        if not all((self.mike, self.dave, self.casey, self.sarah, self.maria)):
            self.log("  Warning: an Operator walk user is missing; skipping.", warning=True)
            return result

        from Tracker.models import Processes, ProcessStep
        process = (Processes.objects.filter(tenant=self.tenant, name=PROCESS_NAME)
                   .order_by('-created_at').first())
        customer = next((c for c in (companies or []) if c.name == 'Great Lakes Diesel'), None)
        if process is None or customer is None:
            self.log("  Warning: Injector Build or Great Lakes Diesel missing; skipping.",
                     warning=True)
            return result
        self.route = [ps.step for ps in
                      ProcessStep.objects.filter(process=process).select_related('step').order_by('order')]
        self.step = {s.name: s for s in self.route}
        part_type = self.route[0].part_type
        self.equipment = self._operational_equipment()
        order = self._ops_order(customer)
        walk = {'override_count': 0}

        with transaction.atomic():
            wo = self._work_order(order, process, UP_NEXT_WO, len(UP_NEXT_PARTS))
            self._parts(wo, part_type, UP_NEXT_PARTS)
            result['work_orders'].append(wo)

        with transaction.atomic():
            wo = self._work_order(order, process, WASH_WO, len(WASH_PARTS))
            parts = self._parts(wo, part_type, WASH_PARTS)
            self._run_step_for(parts, 'Machining', walk, operator=self.dave)
            self._run_step_for(parts, 'Precision Grinding', walk, operator=self.dave)
            self._load_wash(wo, parts)
            result['work_orders'].append(wo)
        self._space_out(wo, self.today - timedelta(minutes=30))

        with transaction.atomic():
            wo = self._work_order(order, process, ASSEMBLY_WO, len(ASSEMBLY_PARTS))
            parts = self._parts(wo, part_type, ASSEMBLY_PARTS)
            self._run_step_for(parts, 'Machining', walk, operator=self.dave)
            self._run_step_for(parts, 'Precision Grinding', walk, operator=self.dave)
            self._run_batch_step(wo, parts, 'Wash', walk)
            first = parts[0]
            self._run_step_for([first], 'Body Inspection', walk, advance=False,
                               operator=self.dave)
            self._buy_off(wo, 'Body Inspection', first)
            self._advance(first, 'PASS')
            self._run_step_for(parts[1:], 'Body Inspection', walk, operator=self.dave)
            self._nitride(parts)
            result['work_orders'].append(wo)
        self._space_out(wo, self.today - timedelta(hours=2))

        result['makeup'] = self._makeup_short_job(order, process, part_type, walk)

        result['teardown_cores'] = self._cores_to_teardown()

        result['lead_finding'] = self._finding_for_the_lead(walk)

        result['rebuilt_unit'] = self._rebuilt_unit(walk)

        result['shift_notes'] = self._shift_notes()
        self.log(f"  {UP_NEXT_WO}: {len(UP_NEXT_PARTS)} bodies waiting at Machining; "
                 f"{WASH_WO}: a Wash load Dave started; {ASSEMBLY_WO}: "
                 f"{len(ASSEMBLY_PARTS)} bodies at Assembly; "
                 f"{len(result['shift_notes'])} shift notes")
        return result

    def _makeup_short_job(self, order, process, part_type, walk):
        """The Production Manager's make-up exhibit: a job one good unit short.

        Dave machines the first body out of spec, its FAIL opens a disposition, Maria
        decides SCRAP and Sarah verifies it. The close is left to the Production
        Manager (close_disposition), as is the make-up. Only then do the
        other three run Machining: the scrapped body is off the step by then, so the
        lot moves without waiting on it. Low priority and a later date, so it doesn't
        change what the operator track has up next."""
        from Tracker.models import WorkOrderPriority
        from Tracker.services.qms.disposition import (
            decide_disposition, record_containment_complete, record_scrap_verification,
        )
        with transaction.atomic():
            wo = self._work_order(order, process, MAKEUP_WO, len(MAKEUP_PARTS))
            WorkOrder.objects.filter(pk=wo.pk).update(
                priority=WorkOrderPriority.LOW,
                expected_completion=(self.today + timedelta(days=MAKEUP_DUE_DAYS)).date())
            parts = self._parts(wo, part_type, MAKEUP_PARTS)
            bad, good = parts[0], parts[1:]
            self._run_step_for([bad], 'Machining', walk, advance=False, operator=self.dave,
                               out_of_spec='Body OD', reading=5.982)
            disposition = (QuarantineDisposition.objects
                           .filter(part=bad, current_state__in=['OPEN', 'IN_PROGRESS'])
                           .order_by('-created_at').first())
            if disposition is None:
                self.log(f"  Warning: no disposition opened for {bad.ERP_id}; "
                         "make-up exhibit skipped.", warning=True)
                return wo
            disposition.assigned_to = self.sarah
            disposition.containment_action = (
                'Bar stock lot checked: the other three bodies measure in spec.')
            disposition.save(update_fields=['assigned_to', 'containment_action', 'updated_at'])
            record_containment_complete(disposition, self.sarah)
            disposition = decide_disposition(
                disposition, disposition_type='SCRAP', authorized_by=self.maria,
                notes='Turned undersize; no material left to recover the diameter.')
            record_scrap_verification(disposition, self.sarah, verified=True)
            self._run_step_for(good, 'Machining', walk, operator=self.dave)
        self._space_out(wo, self.today - timedelta(hours=3))
        return wo

    def _finding_for_the_lead(self, walk):
        """The Shift Lead's pending finding. The repair unit is cleaned in its own load,
        then at Nozzle Inspection Mike records its nozzle beyond repair through the
        capture's service (record_findings_from_capture). A replacement isn't
        pre-approved at that check, so the finding waits for the lead and the unit
        holds there until it's applied or dismissed."""
        from Tracker.models import Core, ProcessStep
        from Tracker.services.reman.findings import record_findings_from_capture
        core = Core.objects.filter(tenant=self.tenant, core_number=LEAD_FINDING_CORE,
                                   status='IN_REBUILD').first()
        if core is None or not core.part_id:
            self.log(f"  Warning: {LEAD_FINDING_CORE} not in rebuild; lead finding skipped.",
                     warning=True)
            return None
        part = core.part
        wo = part.work_order
        build_steps = self.step
        self.step = {ps.step.name: ps.step for ps in
                     ProcessStep.objects.filter(process=wo.process).select_related('step')}
        try:
            with transaction.atomic():
                self._run_batch_step(wo, [part], 'Cleaning', walk)
                part.refresh_from_db()
                if part.step is None or part.step.name != 'Nozzle Inspection':
                    self.log(f"  Warning: {LEAD_FINDING_CORE} is at "
                             f"{part.step.name if part.step else 'no step'}, not Nozzle "
                             "Inspection; lead finding skipped.", warning=True)
                    return None
                se = self._start(part, walk)
                component_name, grade, finding = LEAD_FINDING
                nozzle = core.harvested_components.filter(
                    component_type__name=component_name, is_scrapped=False).first()
                record_findings_from_capture(
                    se, [{'harvested_id': str(nozzle.id), 'grade': grade, 'finding': finding}],
                    self.mike)
        finally:
            self.step = build_steps
        self._space_out(wo, self.today - timedelta(minutes=50))
        return core

    def _rebuilt_unit(self, walk):
        """Shipping R2: a customer's own unit taken through every rebuild step to the
        end of its route. Mike runs the work steps; Sarah, certified for the checks,
        runs them and Maria signs them off; Sarah inspects the nitride load's return.
        The last advance ends the route, the core is REBUILT, and it waits on the
        shipping board under its order."""
        from Tracker.models import Core, ProcessStep
        from Tracker.services.qms.step_signoff import sign_off_step
        core = Core.objects.filter(tenant=self.tenant, core_number=REBUILT_CORE,
                                   status='IN_REBUILD').first()
        if core is None or not core.part_id:
            self.log(f"  Warning: {REBUILT_CORE} not in rebuild; rebuilt unit skipped.",
                     warning=True)
            return None
        part = core.part
        wo = part.work_order
        build_steps = self.step
        self.step = {ps.step.name: ps.step for ps in
                     ProcessStep.objects.filter(process=wo.process).select_related('step')}
        try:
            # One pass per step, bounded: a step that won't let the unit go is logged,
            # not looped on.
            for _ in range(len(self.step) + 2):
                part.refresh_from_db()
                core.refresh_from_db()
                if core.status != 'IN_REBUILD' or part.step is None:
                    break
                step = part.step
                with transaction.atomic():
                    if step.requires_batch_completion:
                        self._run_batch_step(wo, [part], step.name, walk)
                    elif step.name == 'Nitride Coating':
                        self._nitride([part])
                    elif step.requires_qa_signoff:
                        # A check: Sarah (certified for it) runs it and Maria signs it
                        # off. The sign-off moves the lot itself; advance only if not.
                        self._run_step_for([part], step.name, walk, advance=False,
                                           operator=self.sarah)
                        sign_off_step(wo, step, self.maria, password='demo123')
                        part.refresh_from_db()
                        if part.step_id == step.id:
                            self._advance(part, 'PASS')
                    else:
                        self._run_step_for([part], step.name, walk)
                part.refresh_from_db()
                if part.step_id == step.id and core.status == 'IN_REBUILD':
                    core.refresh_from_db()
                    if core.status == 'IN_REBUILD':
                        self.log(f"  Warning: {REBUILT_CORE} stuck at {step.name}; "
                                 "rebuilt unit incomplete.", warning=True)
                        return core
        finally:
            self.step = build_steps
        self._space_out(wo, self.today - timedelta(hours=1))
        core.refresh_from_db()
        self.log(f"  {REBUILT_CORE}: rebuild walked to {core.get_status_display()}")
        return core

    def _work_order(self, order, process, erp_id, quantity):
        """A work order released the way a planner releases one (release_work_order),
        overriding only if readiness blocks it, with the reason on record."""
        from Tracker.services.mes.release import ReleaseBlocked, release_work_order
        wo = super()._work_order(order, process, erp_id, quantity)
        try:
            release_work_order(wo, self.casey)
        except ReleaseBlocked as e:
            release_work_order(wo, self.casey, override_reason=(
                f"Released for the operator exhibits; blockers noted: {e}")[:500])
        wo.refresh_from_db()
        return wo

    def _cores_to_teardown(self):
        """The reman addition's exhibit: two cores Dave received, signed off at Core
        Receiving by Sarah (an inspector who didn't do the work), waiting at Disassembly
        for Mike to tear down. Teardown grades each component it takes out."""
        from Tracker.models import Core
        from Tracker.services.qms.step_signoff import sign_off_step
        cores = list(Core.objects.filter(
            tenant=self.tenant, core_number__in=GRADING_CORES, status='IN_DISASSEMBLY'))
        parts = [c.part for c in cores if c.part_id]
        if len(parts) != len(GRADING_CORES):
            self.log("  Warning: grading cores not found at teardown; skipping.", warning=True)
            return []
        walk = {'override_count': 0}
        wo = parts[0].work_order
        self._run_step_for(parts, 'Core Receiving', walk, advance=False, operator=self.dave)
        sign_off_step(wo, parts[0].step, self.sarah, password='demo123')
        for p in parts:
            p.refresh_from_db()
            if p.step and p.step.name == 'Core Receiving':
                self._advance(p, 'PASS')
        for p in parts:
            p.refresh_from_db()
        self.log(f"  Cores waiting to be torn down and graded: "
                 f"{', '.join(f'{c.core_number}@{c.part.step.name}' for c in cores)}")
        return cores

    def _ops_order(self, customer):
        return Orders.objects.update_or_create(
            tenant=self.tenant, order_number=ORDER_NUMBER,
            defaults={'name': 'Great Lakes injector build', 'company': customer,
                      'order_status': OrdersStatus.IN_PROGRESS,
                      'estimated_completion': (self.today + timedelta(days=10)).date()},
        )[0]

    def _load_wash(self, wo, parts):
        """Dave starts the Wash: each part's own substeps, then a load for the batch,
        left running. Not sealed: Mike takes it over."""
        for part in parts:
            se = self._start(part, {'override_count': 0}, operator=self.dave)
            for ss in self._substeps(part.step, scope='sampled'):
                self._submit(ss, step_execution=se, signer=self.dave)
        batch = BatchExecution.objects.create(
            tenant=self.tenant, work_order=wo, step=self.step['Wash'],
            started_by=self.dave, started_at=timezone.now())
        batch.parts.set(parts)
        return batch

    def _shift_notes(self):
        from Tracker.services.mes.shift_notes import publish_shift_note
        notes = []
        now = timezone.now()
        for spec in SHIFT_NOTES:
            notes.append(publish_shift_note(
                author=self.casey, tenant=self.tenant, body=spec['body'],
                audience_roles=['Operator'], priority=spec['priority'],
                acknowledgment_required=spec['acknowledgment_required'],
                effective_from=now - timedelta(hours=1),
                effective_until=now + timedelta(hours=spec['hours'])))
        return notes
