"""
QA Inspector training exhibits, walked through the real services.

Two Injector Build work orders for Midwest Fleet Services on ORD-2024-QA-INSPECT.
Every part gets where it is by being run there — start_execution, submit_substep,
seal_batch, advance_part_step, pass_fpi, decide_disposition — so its traveler,
sampling decisions, training override and first-piece readings are the ones the
product writes, not a picture of them.

WO-QA-INSPECT-01, today (the shop day's 08:00-09:00):
  Mike runs four bodies through Machining, Precision Grinding and Wash to Body
  Inspection. The training gate refuses Mike at Body Inspection and Casey (Shift Lead)
  authorises each start with a reason. Mike completes the first piece's inspection,
  INJ-QA-INSPECT-001, and the run holds for its buy-off (PENDING FPI). The other
  three wait behind it; the Body Inspection sampling rule (every 4th part) flags one.

WO-QA-INSPECT-02, yesterday (the shop day's 10:00 and 11:30):
  The same route earlier, out to the plater for nitriding and back, its first pieces
  at Body Inspection and Flow Calibration bought off by Sarah. INJ-QA-INSPECT-012
  waits at Flow Calibration, ready to be failed live. INJ-QA-INSPECT-013 failed there
  (flow below its lower limit), its disposition was decided REWORK with Maria's
  authority, and the decision split it to the Rework step, where it waits for
  re-inspection. INJ-QA-INSPECT-015 failed its visual inspection at Body Inspection
  (a burr in the bore, which needs a 3D annotation): it sits quarantined, its
  disposition unassigned in the QA queue.

WO-QA-INSPECT-03/-04/-05, today: first-piece drills, one PENDING FPI each (see
DRILL_WOS).

Runs after the training phase, so the training gate has requirements to refuse on.
"""
from __future__ import annotations

from datetime import timedelta
import zlib
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    BatchExecution, Equipments, FPIRecord, FPIStatus, Orders, OrdersStatus, Parts,
    PartsStatus, Processes, ProcessStep, QualityReports, QuarantineDisposition,
    StepExecution, StepExecutionMeasurement, Substep, SubstepCompletion, SubstepResponse,
    WorkOrder, WorkOrderPriority, WorkOrderStatus,
)

from ..base import BaseSeeder


ORDER_NUMBER = 'ORD-2024-QA-INSPECT'
CUSTOMER_NAME = 'Midwest Fleet Services'
PROCESS_NAME = 'Injector Build'

TODAY_WO = 'WO-QA-INSPECT-01'
TODAY_PARTS = ['INJ-QA-INSPECT-001', 'INJ-QA-INSPECT-002',
               'INJ-QA-INSPECT-003', 'INJ-QA-INSPECT-004']
YESTERDAY_WO = 'WO-QA-INSPECT-02'
YESTERDAY_PARTS = ['INJ-QA-INSPECT-011', 'INJ-QA-INSPECT-012',
                   'INJ-QA-INSPECT-013', 'INJ-QA-INSPECT-014', 'INJ-QA-INSPECT-015']

# First-piece drills, today: each work order holds one PENDING FPI at Body Inspection
# (an FPI is one per work order and step, so each drill needs its own).
#   -03: Sarah ran the first piece's inspection, so Sarah's own buy-off is refused
#        (segregation of duties); a second inspector buys it off.
#   -04: the first piece to fail.  -05: the first piece to waive.
DRILL_WOS = {
    'WO-QA-INSPECT-03': ['INJ-QA-INSPECT-021', 'INJ-QA-INSPECT-022'],
    'WO-QA-INSPECT-04': ['INJ-QA-INSPECT-031', 'INJ-QA-INSPECT-032'],
    'WO-QA-INSPECT-05': ['INJ-QA-INSPECT-041', 'INJ-QA-INSPECT-042'],
}
SELF_BUYOFF_WO = 'WO-QA-INSPECT-03'

# The visual defect 015 is failed with: an error type that needs a 3D annotation, so
# its disposition can't close until the inspector marks it on the model.
BODY_DEFECT = 'Burr in bore'

# Working minutes per visit, and the gap between visits, for a traveler that reads as a shift.
# Nitride Coating is the plater's turnaround, two days.
STEP_MINUTES = {'Machining': 40, 'Precision Grinding': 25, 'Wash': 25, 'Body Inspection': 12,
                'Nitride Coating': 2 * 24 * 60, 'Assembly': 30, 'Flow Calibration': 15,
                'Final Test': 20, 'Rework': 30}
GAP_MINUTES = 10

# Fails its calibration this morning, so naming it at capture is refused. Yesterday's
# Body Inspection on WO-QA-INSPECT-02 used it, which is what the QA Manager traces.
FAILED_GAUGE = 'Micrometer MIC-2'

# QA Manager, module 2: a disposition that is the QA Manager's to decide. A body's bore
# is 0.002 mm over its 4.005 mm maximum; Sarah fails it, contains it, and leaves the
# decision (a Use As Is needs a concession, and the QA Manager's authority) to Maria.
MANAGER_WO = 'WO-QA-MANAGE-01'
MANAGER_PARTS = ['INJ-QA-MANAGE-001', 'INJ-QA-MANAGE-002']
OVERSIZE_BORE = 4.007

OVERRIDE_REASON = 'Only operator free for the cell; first-piece run on my authority pending nozzle re-certification.'


class DemoQaWalkSeeder(BaseSeeder):
    """Walks the QA Inspector exhibits through the production services."""

    def __init__(self, stdout, style, tenant, scale='small'):
        super().__init__(stdout, style, scale=scale)
        self.tenant = tenant
        self.today = timezone.now()

    # ---- entry point -------------------------------------------------------

    def seed(self, companies, users, manufacturing):
        self.log("Walking the QA Inspector exhibits through the services...")
        result = {'order': None, 'work_orders': [], 'parts': [], 'fpi': None,
                  'fail_report': None, 'rework_disposition': None, 'override_count': 0}

        by_email = (users or {}).get('by_email', {})
        self.mike = by_email.get('mike.ops@demo.ambac.com')
        self.casey = by_email.get('casey.dual@demo.ambac.com')
        self.sarah = by_email.get('sarah.qa@demo.ambac.com')
        self.maria = by_email.get('maria.qa@demo.ambac.com')
        if not all((self.mike, self.casey, self.sarah, self.maria)):
            self.log("  Warning: a QA walk user is missing; skipping.", warning=True)
            return result

        process = (Processes.objects.filter(tenant=self.tenant, name=PROCESS_NAME)
                   .order_by('-created_at').first())
        customer = next((c for c in (companies or []) if c.name == CUSTOMER_NAME), None)
        if process is None or customer is None:
            self.log(f"  Warning: {PROCESS_NAME} process or {CUSTOMER_NAME} missing; skipping.",
                     warning=True)
            return result
        self.route = [ps.step for ps in
                      ProcessStep.objects.filter(process=process).select_related('step').order_by('order')]
        self.step = {s.name: s for s in self.route}
        part_type = self.route[0].part_type

        self.equipment = self._operational_equipment()

        order = self._order(customer)
        result['order'] = order

        # Yesterday's work order first: its history is shifted a day back afterwards.
        with transaction.atomic():
            wo2 = self._work_order(order, process, YESTERDAY_WO, len(YESTERDAY_PARTS))
            parts2 = self._parts(wo2, part_type, YESTERDAY_PARTS)
            self._walk_yesterday(wo2, parts2, result)
        self._shift_back(wo2, timedelta(days=1))
        self._space_out(wo2, self.today - timedelta(days=1, hours=-2))

        with transaction.atomic():
            wo1 = self._work_order(order, process, TODAY_WO, len(TODAY_PARTS))
            parts1 = self._parts(wo1, part_type, TODAY_PARTS)
            self._walk_today(wo1, parts1, result)
        self._space_out(wo1, self.today - timedelta(minutes=20))

        drills = []
        for i, (erp_id, serials) in enumerate(DRILL_WOS.items()):
            with transaction.atomic():
                wo = self._work_order(order, process, erp_id, len(serials))
                parts = self._parts(wo, part_type, serials)
                runner = self.sarah if erp_id == SELF_BUYOFF_WO else self.mike
                self._walk_drill(wo, parts, runner, result)
            self._space_out(wo, self.today - timedelta(minutes=50 + 15 * i))
            drills.append(wo)

        with transaction.atomic():
            wo = self._work_order(order, process, MANAGER_WO, len(MANAGER_PARTS))
            parts = self._parts(wo, part_type, MANAGER_PARTS)
            result['manager_disposition'] = self._walk_manager_disposition(wo, parts, result)
        self._space_out(wo, self.today - timedelta(hours=3))

        result['failed_gauge'] = self._fail_gauge()

        result['work_orders'] = [wo1, wo2] + drills
        result['parts'] = parts1 + parts2
        sampled = [p.ERP_id for p in parts1 if p.requires_sampling]
        self.log(f"  {TODAY_WO}: first piece {TODAY_PARTS[0]} awaiting buy-off; "
                 f"sampled at Body Inspection: {', '.join(sampled) or 'none'}")
        self.log(f"  {YESTERDAY_WO}: {YESTERDAY_PARTS[1]} at Flow Calibration; "
                 f"{YESTERDAY_PARTS[2]} at Rework "
                 f"({result['rework_disposition'].disposition_number if result['rework_disposition'] else 'no disposition'})")
        annotation = result.get('annotation_disposition')
        self.log(f"  {YESTERDAY_PARTS[4]} quarantined at Body Inspection "
                 f"({annotation.disposition_number if annotation else 'no disposition'}, unassigned)")
        self.log(f"  First-piece drills: {', '.join(DRILL_WOS)} "
                 f"({SELF_BUYOFF_WO}'s first piece run by Sarah)")
        md = result.get('manager_disposition')
        self.log(f"  {MANAGER_WO}: {MANAGER_PARTS[1]} bore oversize, "
                 f"{md.disposition_number if md else 'no disposition'} waiting on Maria")
        self.log(f"  Training-gate overrides recorded: {result['override_count']}")
        return result

    # ---- the two days ------------------------------------------------------

    def _walk_yesterday(self, wo, parts, result):
        first, fresh, failing, spare, blocked = parts
        self._make_bodies(wo, parts, result)

        # Body Inspection, measured with MIC-2 (still in calibration yesterday): the
        # gauge fails its check this morning (_fail_gauge), so what it measured is the
        # QA Manager's exposure exhibit.
        production_gauge = self.equipment
        self.equipment = (Equipments.objects.filter(tenant=self.tenant, name=FAILED_GAUGE).first()
                          or production_gauge)
        # Body Inspection: first piece, Sarah buys it off, the rest follow.
        self._run_step_for([first], 'Body Inspection', result, advance=False)
        self._buy_off(wo, 'Body Inspection', first)
        self._advance(first, 'PASS')
        self._run_step_for([fresh, failing, spare], 'Body Inspection', result)
        # 015 fails its visual inspection: a FAIL report, the part quarantined, its
        # disposition opened unassigned, left for QA to take and annotate.
        self._run_step_for([blocked], 'Body Inspection', result, advance=False,
                           defect=self._defect(BODY_DEFECT))
        result['annotation_disposition'] = (QuarantineDisposition.objects
                                            .filter(part=blocked, current_state='OPEN').first())
        self.equipment = production_gauge
        parts = [first, fresh, failing, spare]

        self._nitride(parts)
        self._run_step_for(parts, 'Assembly', result)

        # Flow Calibration: first piece bought off; the failing part fails for real.
        self._run_step_for([first], 'Flow Calibration', result, advance=False)
        self._buy_off(wo, 'Flow Calibration', first)
        self._advance(first, 'PASS')
        # 012 and 014 wait at Flow Calibration unclaimed (PENDING, nobody assigned), so
        # the operator who runs 012 live at 10:00 picks it up without a reassignment.
        report = self._run_step_for([failing], 'Flow Calibration', result, advance=False,
                                    out_of_spec='Flow Rate')
        result['fail_report'] = report
        result['rework_disposition'] = self._rework(failing, report)

    def _walk_today(self, wo, parts, result):
        first = parts[0]
        self._make_bodies(wo, parts, result)
        # The first piece's inspection is completed and the run holds for its buy-off.
        self._run_step_for([first], 'Body Inspection', result, advance=False)
        result['fpi'] = self._raise_fpi(wo, 'Body Inspection', first)
        # The rest wait behind the first piece unclaimed (PENDING, nobody assigned): the
        # sampled one is inspected by whoever picks it up after the buy-off.
        for p in parts:
            p.refresh_from_db()

    def _walk_drill(self, wo, parts, runner, result):
        """The bodies made by Mike, then the first piece's inspection by `runner`,
        holding for its buy-off (PENDING FPI); the second part waits."""
        first = parts[0]
        self._make_bodies(wo, parts, result)
        self._run_step_for([first], 'Body Inspection', result, advance=False,
                           operator=runner)
        self._raise_fpi(wo, 'Body Inspection', first)

    def _walk_manager_disposition(self, wo, parts, result):
        """The first piece bought off; the second body's bore measures oversize. Sarah
        fails it with the defect, contains it, and assigns the decision to Maria."""
        from Tracker.services.qms.disposition import record_containment_complete
        first, oversize = parts
        self._make_bodies(wo, parts, result)
        self._run_step_for([first], 'Body Inspection', result, advance=False)
        self._buy_off(wo, 'Body Inspection', first)
        self._advance(first, 'PASS')
        self._run_step_for([oversize], 'Body Inspection', result, advance=False,
                           out_of_spec='Bore Diameter', reading=OVERSIZE_BORE,
                           defect=self._defect('Bore oversize'),
                           defect_note={'location': 'Seat bore',
                                        'notes': 'Bore 4.007 mm on the CMM, 0.002 over the '
                                                 '4.005 maximum. Seat finish good.'})
        disposition = (QuarantineDisposition.objects
                       .filter(part=oversize, current_state='OPEN').first())
        if disposition is None:
            self.log(f"  Warning: no disposition opened for {oversize.ERP_id}.", warning=True)
            return None
        disposition.assigned_to = self.maria
        disposition.containment_action = (
            'Part tagged and moved to the hold rack. Bores of the other bodies from this '
            'grinder setup re-checked on the CMM; all within 4.005.')
        disposition.save(update_fields=['assigned_to', 'containment_action', 'updated_at'])
        record_containment_complete(disposition, self.sarah)
        return disposition

    def _make_bodies(self, wo, parts, result):
        """Machining, grinding and the wash: a body made, up to its inspection."""
        self._run_step_for(parts, 'Machining', result)
        self._run_step_for(parts, 'Precision Grinding', result)
        self._run_batch_step(wo, parts, 'Wash', result)

    def _nitride(self, parts):
        """Out to the plater and back: sent, returned, inspected on the shipment's own
        execution (coating thickness at nominal), accepted, and the parts advanced to
        Assembly through the outside-process service."""
        from Tracker.services.mes import outside_process
        step = self.step['Nitride Coating']
        shipment = outside_process.send_parts_out(step=step, parts=parts, user=self.mike,
                                                  reference=f"{parts[0].work_order.ERP_id}-NITRIDE")
        report = outside_process.receive_parts_back(shipment, user=self.sarah)
        # The return inspection is the shipment's, done once for the parts that rode it.
        inspection = outside_process._return_execution(shipment)
        for ss in self._substeps(step, scope='sampled'):
            self._submit(ss, step_execution=inspection, signer=self.sarah)
        outside_process.accept_return(report, user=self.sarah)
        for p in parts:
            p.refresh_from_db()

    # ---- building blocks ---------------------------------------------------

    def _order(self, customer):
        return Orders.objects.update_or_create(
            tenant=self.tenant, order_number=ORDER_NUMBER,
            defaults={'name': 'Midwest Fleet injector build', 'company': customer,
                      'order_status': OrdersStatus.IN_PROGRESS,
                      'estimated_completion': (self.today + timedelta(days=8)).date()},
        )[0]

    def _work_order(self, order, process, erp_id, quantity):
        return WorkOrder.objects.update_or_create(
            tenant=self.tenant, ERP_id=erp_id,
            defaults={'related_order': order, 'process': process,
                      'priority': WorkOrderPriority.NORMAL,
                      'workorder_status': WorkOrderStatus.PENDING,
                      'expected_completion': (self.today + timedelta(days=8)).date(),
                      'quantity': quantity},
        )[0]

    def _parts(self, wo, part_type, erp_ids):
        first_step = self.route[0]
        parts = []
        for erp_id in erp_ids:
            part, _ = Parts.objects.update_or_create(
                tenant=self.tenant, ERP_id=erp_id,
                defaults={'part_type': part_type, 'order': wo.related_order, 'work_order': wo,
                          'step': first_step, 'part_status': PartsStatus.PENDING},
            )
            parts.append(part)
        return parts

    def _operational_equipment(self):
        """Equipment a capture accepts: in service and in calibration. A gauge that is
        out of service or failed is refused at capture."""
        for e in Equipments.objects.filter(tenant=self.tenant).order_by('name'):
            if e.is_operational:
                return e
        return None

    def _start(self, part, result, operator=None):
        """Start the part's current step as `operator` (Mike unless told) — through the
        competence gate, with Casey's override where the gate refuses them."""
        from Tracker.services.mes.lifecycle import NotQualified, start_execution
        operator = operator or self.mike
        part.refresh_from_db()
        se = StepExecution.get_current_execution(part)
        if se is None:
            # A fresh part's first execution, as the runtime creates it on first start.
            se = StepExecution.objects.create(tenant=self.tenant, part=part, step=part.step,
                                              visit_number=1, status='PENDING')
        if se.status == 'IN_PROGRESS' and se.assigned_to_id == operator.id:
            return se
        try:
            start_execution(se, operator)
        except NotQualified:
            start_execution(se, operator, authorizer=self.casey, reason=OVERRIDE_REASON)
            result['override_count'] += 1
        return se

    def _run_step_for(self, parts, step_name, result, *, advance=True, out_of_spec=False,
                      operator=None, defect=None, reading=None, defect_note=None):
        """Run the named step on each part: start, submit every per-part substep, then
        advance (PASS) unless told to stop. Returns the last inspection report written."""
        report = None
        for part in parts:
            part.refresh_from_db()
            if part.step is None or part.step.name != step_name:
                self.log(f"  Warning: {part.ERP_id} is at "
                         f"{part.step.name if part.step else 'no step'}, not {step_name}.",
                         warning=True)
                continue
            se = self._start(part, result, operator)
            for ss in self._substeps(part.step, scope='sampled'):
                self._submit(ss, step_execution=se, out_of_spec=out_of_spec,
                             signer=operator, defect=defect, reading=reading,
                             defect_note=defect_note)
            report = (QualityReports.objects.filter(part=part, step=part.step)
                      .order_by('-created_at').first()) or report
            if advance:
                self._advance(part, 'PASS' if part.step.is_decision_point else None)
        return report

    def _run_batch_step(self, wo, parts, step_name, result):
        """A batch step: each part's own substeps, then one load for the batch
        substeps, sealed — sealing advances the load."""
        from Tracker.services.dwi.batch_lifecycle import seal_batch
        for part in parts:
            se = self._start(part, result)
            for ss in self._substeps(part.step, scope='sampled'):
                self._submit(ss, step_execution=se)
        step = self.step[step_name]
        batch = BatchExecution.objects.create(tenant=self.tenant, work_order=wo, step=step,
                                              started_by=self.mike, started_at=timezone.now())
        batch.parts.set(parts)
        for ss in self._substeps(step, scope='batch'):
            self._submit(ss, batch_execution=batch)
        seal_batch(batch=batch, user=self.mike)
        for part in parts:
            part.refresh_from_db()

    def _advance(self, part, decision):
        from Tracker.services.mes.parts import advance_part_step
        part.refresh_from_db()
        advance_part_step(part, operator=self.mike, decision_result=decision)
        part.refresh_from_db()

    def _raise_fpi(self, wo, step_name, first_piece):
        """The first piece is at the step: raise its FPI, as the runtime does
        (viewsets.qms FPIRecord get_or_create designates the part at the step)."""
        step = self.step[step_name]
        fpi, _ = FPIRecord.objects.get_or_create(
            tenant=self.tenant, work_order=wo, step=step, status=FPIStatus.PENDING,
            defaults={'part_type': step.part_type, 'designated_part': first_piece},
        )
        return fpi

    def _buy_off(self, wo, step_name, first_piece):
        """Sarah buys off the first piece. She signed none of its substeps (Mike did),
        so segregation of duties holds; identity is taken as verified for seeded
        history, the way submit_substep takes `preverified`."""
        from Tracker.services.qms.fpi import pass_fpi
        fpi = self._raise_fpi(wo, step_name, first_piece)
        pass_fpi(fpi, self.sarah, notes='First piece checked against the drawing; conforms.',
                 identity_verified=True)
        return fpi

    def _rework(self, part, report):
        """The FAIL opened a disposition. Maria decides REWORK, which splits the part
        to the Rework step for re-inspection."""
        from Tracker.services.qms.disposition import (
            decide_disposition, record_containment_complete, route_part_to_rework_if_needed,
        )
        disposition = (QuarantineDisposition.objects
                       .filter(part=part, current_state__in=['OPEN', 'IN_PROGRESS'])
                       .order_by('-created_at').first())
        if disposition is None:
            self.log(f"  Warning: no disposition opened for {part.ERP_id}.", warning=True)
            return None
        disposition.assigned_to = self.sarah
        disposition.containment_action = (
            'Remaining parts at Flow Calibration re-checked on the second flow bench; '
            'none below the lower limit.')
        disposition.save(update_fields=['assigned_to', 'containment_action', 'updated_at'])
        record_containment_complete(disposition, self.sarah)
        disposition = decide_disposition(
            disposition, disposition_type='REWORK', authorized_by=self.maria,
            notes='Low flow traced to a partly blocked spray hole; clean and re-test.')
        # Maria co-signs at Sarah's terminal: the decision is Maria's, the act Sarah's,
        # so the split (and the rework visit it assigns) is Sarah's — not left on Maria's
        # name, where Sarah's re-inspection would need a supervisor to reassign it.
        route_part_to_rework_if_needed(disposition, self.sarah)
        part.refresh_from_db()
        return disposition

    def _defect(self, name):
        from Tracker.models import QualityErrorsList
        defect = QualityErrorsList.objects.filter(tenant=self.tenant, error_name=name).first()
        if defect is None:
            self.log(f"  Warning: error type {name!r} not found.", warning=True)
        return defect

    def _substeps(self, step, *, scope):
        return [ss for ss in Substep.objects.filter(tenant=self.tenant, step=step).order_by('order')
                if (getattr(ss, 'scope', 'sampled') or 'sampled').lower() == scope]

    def _submit(self, substep, *, step_execution=None, batch_execution=None, out_of_spec=False,
                signer=None, defect=None, reading=None, defect_note=None):
        """Submit a value for every capture node through submit_substep, the path the
        runtime uses. Readings are at nominal; `out_of_spec` (a measurement label) puts that
        reading below its lower limit, or at `reading` when given; `defect` (an error type)
        fails the visual result and records the defect (with `defect_note`), with readings
        left in spec."""
        from Tracker.models import EquipmentRole
        from Tracker.services.dwi.operator_capture import submit_substep

        signer = signer or self.mike
        stamp = timezone.now().isoformat()
        nodes = _capture_nodes(substep.body_blocks)
        # A result field on the same substep as the failing reading says FAIL too.
        fails_here = bool(defect) or any(t == 'measurementInput' and a.get('label') == out_of_spec
                                         for t, a in nodes)
        captures = []
        for node_type, attrs in nodes:
            node_id = attrs['node_id']
            if node_type == 'measurementInput':
                nominal = attrs.get('nominal')
                value = nominal
                if nominal is not None:
                    # Real readings vary: a deterministic spread within a quarter of the
                    # tolerance, so the SPC charts see a process, not a constant (a
                    # constant reads as sigma 0 and Cpk infinity).
                    tol = min(Decimal(str(attrs.get('lower_tol') or 0)), Decimal(str(attrs.get('upper_tol') or 0)))
                    # A shipment's return inspection has no part: key it by the execution.
                    who = (step_execution.part.ERP_id if step_execution is not None and step_execution.part_id
                           else str(getattr(step_execution, 'pk', '')))
                    frac = Decimal(zlib.crc32(f"{who}:{node_id}".encode()) % 1000 - 500) / Decimal(2000)
                    value = float(Decimal(str(nominal)) + tol * frac)
                if out_of_spec and out_of_spec == attrs.get('label') and nominal is not None:
                    low = Decimal(str(attrs.get('lower_tol') or 0))
                    value = (reading if reading is not None
                             else float(Decimal(str(nominal)) - low - Decimal('2')))
                captures.append({'node_id': node_id, 'kind': 'measurement',
                                 'measurement_definition_id': attrs.get('measurement_definition_id'),
                                 'value_numeric': value,
                                 'value_string': '' if nominal is not None else 'PASS'})
            elif node_type == 'attestationCheckpoint':
                if attrs.get('kind') == 'signature':
                    captures.append({'node_id': node_id, 'kind': 'attestation',
                                     'signature': {'user_id': str(signer.id), 'signed_at': stamp},
                                     'meaning': attrs.get('label') or 'Signed'})
                else:
                    captures.append({'node_id': node_id, 'kind': 'attestation', 'confirm': True,
                                     'meaning': attrs.get('label') or 'Confirmed'})
            elif node_type == 'qualityStatusField':
                captures.append({'node_id': node_id, 'kind': 'status',
                                 'status': 'FAIL' if fails_here else 'PASS'})
            elif node_type == 'errorTypesField' and defect is not None:
                captures.append({'node_id': node_id, 'kind': 'defects',
                                 'rows': [{'error_type_id': str(defect.id), 'severity': 'MAJOR',
                                           'location': (defect_note or {}).get('location', 'Fuel passage breakout'),
                                           'count': 1,
                                           'notes': (defect_note or {}).get(
                                               'notes', 'Burr where the cross-drilling breaks into the bore.')}]})
            elif node_type == 'equipmentRolesField' and self.equipment is not None:
                # An instrument is recorded as the gauge it is, a machine as production.
                is_gauge = any(w in self.equipment.name for w in ('Micrometer', 'Caliper', 'CMM', 'Gauge'))
                captures.append({'node_id': node_id, 'kind': 'equipment_roles',
                                 'rows': [{'equipment_id': str(self.equipment.id),
                                           'role': (EquipmentRole.GAUGE if is_gauge
                                                    else EquipmentRole.PRODUCTION).value}]})
            elif node_type == 'partAnnotation':
                captures.append({'node_id': node_id, 'kind': 'annotation', 'annotations': []})
            elif node_type == 'inspectionSignatures':
                captures.append({'node_id': node_id, 'kind': 'signatures',
                                 'detected': {'user_id': str(signer.id), 'signed_at': stamp}})
            elif node_type == 'scanInput' and step_execution is not None:
                captures.append({'node_id': node_id, 'kind': 'scan',
                                 'value_text': step_execution.part.ERP_id})
        # A substep with nothing to capture is still submitted, as the runtime does
        # ("Nothing captured — you can still continue"): its completion is what the
        # advancement gate reads.
        submit_substep(substep=substep, step_execution=step_execution,
                       batch_execution=batch_execution, user=signer, captures=captures,
                       preverified=True)

    def _fail_gauge(self):
        """A gauge that failed its calibration this morning, so a capture that names it
        is refused — the other half of the gauge check (an overdue gauge is accepted
        with a warning; MIC-1 and TW-25 are overdue). Recorded as a calibration result
        and applied through the service, which takes the gauge out of service."""
        from Tracker.models import CalibrationRecord
        from Tracker.services.mes.work_order import apply_calibration_result_to_equipment
        gauge = Equipments.objects.filter(tenant=self.tenant, name=FAILED_GAUGE).first()
        if gauge is None:
            self.log(f"  Warning: {FAILED_GAUGE} not found; no failed gauge.", warning=True)
            return None
        record, _ = CalibrationRecord.objects.update_or_create(
            tenant=self.tenant, equipment=gauge, calibration_date=self.today.date(),
            defaults={
                'due_date': self.today.date(),
                'result': CalibrationRecord.CalibrationResult.FAIL,
                'calibration_type': CalibrationRecord.CalibrationType.SCHEDULED,
                'performed_by': 'Demo Calibration Services',
                'external_lab': 'Demo Calibration Services',
                'certificate_number': 'CAL-MIC-002-FAIL',
                'standards_used': 'NIST-traceable gauge blocks',
                'as_found_in_tolerance': False,
                'adjustments_made': False,
                'notes': 'Reads 0.012 mm high across the range; spindle worn. Sent for repair.',
            },
        )
        apply_calibration_result_to_equipment(record)
        gauge.refresh_from_db()
        return gauge

    def _space_out(self, wo, end_at):
        """Re-date each part's executions as a shift: the walk runs in seconds, so
        without this every step reads as started and ended in the same second. Visits
        keep their order and get a working duration each, the last ending at `end_at`."""
        for part in Parts.objects.filter(work_order=wo):
            visits = list(StepExecution.objects.filter(part=part).order_by('entered_at', 'id'))
            span = sum((STEP_MINUTES.get(v.step.name, 20) + GAP_MINUTES) for v in visits)
            cursor = end_at - timedelta(minutes=span)
            for v in visits:
                minutes = STEP_MINUTES.get(v.step.name, 20)
                fields = {'entered_at': cursor}
                # A visit only entered stays unstarted, or the traveler reads its
                # assignee as having worked it. One that was worked gets a start even
                # where the walk captured without pressing Start Work.
                if v.started_at is not None or v.status != 'PENDING':
                    fields['started_at'] = cursor + timedelta(minutes=2)
                if v.exited_at is not None:
                    fields['exited_at'] = cursor + timedelta(minutes=minutes)
                StepExecution.objects.filter(pk=v.pk).update(**fields)
                # What was captured during the visit moves with it, stamped near its
                # end, so a reading or a report doesn't carry the seed's run time.
                captured_at = cursor + timedelta(minutes=max(minutes - 3, 3))
                StepExecutionMeasurement.objects.filter(step_execution=v).update(
                    recorded_at=captured_at)
                SubstepResponse.objects.filter(step_execution=v).update(responded_at=captured_at)
                SubstepCompletion.objects.filter(step_execution=v).update(completed_at=captured_at)
                QualityReports.objects.filter(part=part, step=v.step,
                                              created_at__gte=v.entered_at).update(
                    created_at=captured_at)
                cursor += timedelta(minutes=minutes + GAP_MINUTES)

    def _shift_back(self, wo, delta):
        """Move a work order's walked history back in time. The services stamp now();
        this is yesterday's run, so its rows are re-dated as a block."""
        from django.db.models import F
        StepExecution.objects.filter(part__work_order=wo).update(
            entered_at=F('entered_at') - delta)
        StepExecution.objects.filter(part__work_order=wo, started_at__isnull=False).update(
            started_at=F('started_at') - delta)
        StepExecution.objects.filter(part__work_order=wo, exited_at__isnull=False).update(
            exited_at=F('exited_at') - delta)
        QualityReports.objects.filter(part__work_order=wo).update(created_at=F('created_at') - delta)
        QuarantineDisposition.objects.filter(part__work_order=wo).update(
            created_at=F('created_at') - delta)
        # The decision too, or 013's REWORK reads as authorised a day after its
        # rework visit opened.
        for stamp in ('decision_authorized_at', 'containment_completed_at',
                      'scrap_verified_at', 'resolution_completed_at'):
            QuarantineDisposition.objects.filter(
                part__work_order=wo, **{f'{stamp}__isnull': False}).update(
                **{stamp: F(stamp) - delta})
        FPIRecord.objects.filter(work_order=wo).update(created_at=F('created_at') - delta)
        FPIRecord.objects.filter(work_order=wo, inspected_at__isnull=False).update(
            inspected_at=F('inspected_at') - delta)
        BatchExecution.objects.filter(work_order=wo).update(started_at=F('started_at') - delta)
        BatchExecution.objects.filter(work_order=wo, sealed_at__isnull=False).update(
            sealed_at=F('sealed_at') - delta)



def _capture_nodes(body):
    """(node type, attrs) for every capture node in a substep body."""
    out = []

    def walk(node):
        if isinstance(node, dict):
            attrs = node.get('attrs') or {}
            if node.get('type') and attrs.get('node_id'):
                out.append((node['type'], attrs))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(body)
    return out
