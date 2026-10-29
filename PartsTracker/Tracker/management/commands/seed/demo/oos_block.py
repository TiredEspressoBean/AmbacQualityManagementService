"""
Block on out-of-spec measurement, walked through the real services.

A small route of its own, so the switch touches no other exhibit (steps are shared
across a process's versions; turning it on at Injector Build's Body Inspection would
change every walk that runs through it). Its own part type too, so planning an
Injector order still finds exactly one approved process.

Nozzle Bench Check: Opening Pressure Check (Block on out-of-spec measurement ON,
per-part) -> Release. The reading is process data, not an inspection point, so an
out-of-spec value writes no failed report and opens no disposition: the step's switch
is the only thing that holds the part.

WO-QA-OOS-01, two nozzle tips:
  NOZ-OOS-001: Mike started the check and recorded 26.5 MPa against 28.0 +/- 1.0. The
               advance is refused ("One or more measurements are out of
               specification"), so it waits at the check, in progress.
  NOZ-OOS-002: waiting at the check, untouched, to run in spec and see it move.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from Tracker.models import (
    MeasurementDefinition, Orders, OrdersStatus, PartTypes, Processes, ProcessStep,
    StepEdge, Steps, Substep,
)
from Tracker.models.mes_lite import EdgeType, ProcessStatus

from .dwi import _attest_confirm, _doc, _measurement, _para
from .qa_walk import CUSTOMER_NAME, DemoQaWalkSeeder
from .routes import step_key

PART_TYPE = {'name': 'Nozzle Tip', 'ID_prefix': 'NOZ', 'ERP_id': 'NOZ-100'}
PROCESS_NAME = 'Nozzle Bench Check'
CHECK_STEP = 'Opening Pressure Check'
RELEASE_STEP = 'Release'
# MPa, not bar: a measurement's values are numeric(9, 6), so under 1000.
MEASUREMENT = {'label': 'Opening Pressure', 'unit': 'MPa',
               'nominal': 28.0, 'upper_tol': 1.0, 'lower_tol': 1.0}
OUT_OF_SPEC_READING = 26.5

ORDER_NUMBER = 'ORD-2024-QA-OOS'
WORK_ORDER = 'WO-QA-OOS-01'
PARTS = ['NOZ-OOS-001', 'NOZ-OOS-002']


class DemoOutOfSpecBlockSeeder(DemoQaWalkSeeder):
    """Walks the Block on out-of-spec measurement exhibit through the services."""

    def seed(self, companies, users, manufacturing):
        self.log("Walking the out-of-spec block exhibit through the services...")
        result = {'work_order': None, 'held': None, 'override_count': 0}

        by_email = (users or {}).get('by_email', {})
        self.mike = by_email.get('mike.ops@demo.ambac.com')
        self.casey = by_email.get('casey.dual@demo.ambac.com')
        self.sarah = by_email.get('sarah.qa@demo.ambac.com')
        self.maria = by_email.get('maria.qa@demo.ambac.com')
        customer = next((c for c in (companies or []) if c.name == CUSTOMER_NAME), None)
        if not all((self.mike, self.casey, customer)):
            self.log("  Warning: a user or the customer is missing; skipping.", warning=True)
            return result
        self.equipment = self._operational_equipment()

        with transaction.atomic():
            part_type, process, check = self._route()
            substep = self._instruction(check)
            order = Orders.objects.update_or_create(
                tenant=self.tenant, order_number=ORDER_NUMBER,
                defaults={'name': 'Midwest Fleet nozzle tips', 'company': customer,
                          'order_status': OrdersStatus.IN_PROGRESS,
                          'estimated_completion': (self.today + timedelta(days=8)).date()},
            )[0]
            wo = self._work_order(order, process, WORK_ORDER, len(PARTS))
            held, fresh = self._parts(wo, part_type, PARTS)

            se = self._start(held, result)
            self._submit(substep, step_execution=se, out_of_spec=MEASUREMENT['label'],
                         reading=OUT_OF_SPEC_READING)
            try:
                self._advance(held, None)
                self.log(f"  Warning: {held.ERP_id} advanced past the block.", warning=True)
            except ValueError as exc:
                self.log(f"  {held.ERP_id} held at {CHECK_STEP}: {exc}")
        self._space_out(wo, self.today - timedelta(minutes=35))

        result['work_order'] = wo
        result['held'] = held
        return result

    def _route(self):
        part_type, _ = PartTypes.objects.update_or_create(
            tenant=self.tenant, name=PART_TYPE['name'],
            defaults={'ID_prefix': PART_TYPE['ID_prefix'], 'ERP_id': PART_TYPE['ERP_id']},
        )
        process, _ = Processes.objects.update_or_create(
            tenant=self.tenant, name=PROCESS_NAME, part_type=part_type,
            defaults={'is_remanufactured': False, 'category': 'MANUFACTURING',
                      'status': ProcessStatus.APPROVED,
                      'change_description': 'Initial demo process setup',
                      'approved_at': timezone.now(), 'approved_by': None},
        )
        check, _ = Steps.objects.update_or_create(
            tenant=self.tenant, part_type=part_type,
            external_id=step_key('nozzle-check', CHECK_STEP),
            defaults={'name': CHECK_STEP, 'step_type': 'START',
                      'description': 'Bench-test the tip: opening pressure inside its limits.',
                      'expected_duration': timedelta(minutes=10),
                      'block_on_measurement_failure': True,
                      'part_advancement_mode': 'PER_PART'},
        )
        release, _ = Steps.objects.update_or_create(
            tenant=self.tenant, part_type=part_type,
            external_id=step_key('nozzle-check', RELEASE_STEP),
            defaults={'name': RELEASE_STEP, 'step_type': 'TERMINAL', 'is_terminal': True,
                      'terminal_status': 'COMPLETED',
                      'description': 'Tip released to stock.'},
        )
        for order, step in ((1, check), (2, release)):
            ProcessStep.objects.update_or_create(
                process=process, step=step,
                defaults={'order': order, 'is_entry_point': order == 1,
                          'is_exit_point': step is release},
            )
        StepEdge.objects.update_or_create(
            process=process, from_step=check, to_step=release, edge_type=EdgeType.DEFAULT,
            defaults={'condition_measurement': None, 'condition_operator': '',
                      'condition_value': None, 'pre_approved': False},
        )
        # The helpers run a part from route[0].
        self.route = [check, release]
        self.step = {CHECK_STEP: check, RELEASE_STEP: release}
        return part_type, process, check

    def _instruction(self, check):
        md, _ = MeasurementDefinition.objects.update_or_create(
            tenant=self.tenant, step=check, label=MEASUREMENT['label'],
            defaults={'type': 'NUMERIC', 'unit': MEASUREMENT['unit'],
                      'nominal': MEASUREMENT['nominal'], 'upper_tol': MEASUREMENT['upper_tol'],
                      'lower_tol': MEASUREMENT['lower_tol'], 'required': True,
                      'default_equipment': self.equipment},
        )
        substep, _ = Substep.objects.update_or_create(
            tenant=self.tenant, step=check, title='Bench-test the opening pressure',
            defaults={'order': 1, 'is_inspection_point': False,
                      'body_blocks': _doc(
                          _para('Mount the tip on the bench, bleed it, and raise the pressure '
                                'until it opens. Record where it opens.'),
                          _measurement(check, 'opening-pressure', md),
                          _attest_confirm(check, 'bench-bled', 'Bench bled',
                                          'The bench was bled before the test.'),
                      )},
        )
        return substep
