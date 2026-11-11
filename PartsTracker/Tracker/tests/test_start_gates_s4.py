"""The other start gates (gate redesign S4, user decisions 2026-11-11).

- A machine that is down (out of service, in maintenance or calibration, retired)
  refuses a start on it.
- A part ON_HOLD refuses Start Work; REWORK_NEEDED stays startable.
- Training required for the machine's type is checked at start.
- A life limit refuses at START, not when the part leaves the step.
- Reman cycles: a unit's remans are counted when its reman starts, from its history,
  and the start gate refuses one already at the limit.
- An expired material lot is refused at staging.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from Tracker.models import (
    Equipments, EquipmentType, MaterialLot, Parts, PartTypes, StepEquipmentAffinity,
    StepExecution, Steps, TrainingRecord, TrainingRequirement, TrainingType, WorkOrder,
)
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking, PartTypeLifeLimit
from Tracker.services.mes.gates import GateCode, StartRefused
from Tracker.services.mes.lifecycle import NotQualified, start_execution
from Tracker.tests.base import TenantTestCase


class StartGatesS4Tests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Housing")
        self.step = Steps.objects.create(tenant=t, name="Mill", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-S4", quantity=2,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=t, ERP_id="S4-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step,
                                         part_status="IN_PROGRESS")
        self.visit = StepExecution.objects.create(tenant=t, part=self.part, step=self.step,
                                                  visit_number=1, status="PENDING")
        self.operator = get_user_model().objects.create_user(
            username="s4-op", email="s4op@t.test", password="x", tenant=t)

    def _start(self, user=None):
        v = StepExecution.objects.get(pk=self.visit.pk)
        return start_execution(v, user or self.user_a)

    def _machine(self, status="IN_SERVICE", eq_type=None):
        machine = Equipments.objects.create(tenant=self.tenant_a, name="Haas VF-2",
                                            status=status, equipment_type=eq_type)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant_a, step=self.step, equipment=machine,
            affinity=StepEquipmentAffinity.Affinity.DIALED_IN)
        return machine

    def _codes(self, ctx):
        return [b.code for b in ctx.exception.blockers]

    # --- machine down
    def test_a_machine_in_maintenance_refuses_the_start(self):
        self._machine(status="IN_MAINTENANCE")
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.EQUIPMENT_DOWN])
        self.assertIn("Haas VF-2", ctx.exception.messages[0])

    def test_a_machine_in_service_starts(self):
        self._machine()
        self._start()

    # --- part on hold
    def test_a_part_on_hold_refuses_start_work(self):
        Parts.objects.filter(pk=self.part.pk).update(part_status="ON_HOLD")
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.PART_ON_HOLD])

    def test_rework_needed_stays_startable(self):
        Parts.objects.filter(pk=self.part.pk).update(part_status="REWORK_NEEDED")
        self._start()

    # --- machine-type training
    def test_training_for_the_machines_type_is_checked_at_start(self):
        mill = EquipmentType.objects.create(tenant=self.tenant_a, name="5-axis mill")
        self._machine(eq_type=mill)
        course = TrainingType.objects.create(tenant=self.tenant_a, name="5-axis setup")
        TrainingRequirement.objects.create(tenant=self.tenant_a, training_type=course,
                                           equipment_type=mill)
        with self.assertRaises(NotQualified):
            self._start(self.operator)
        TrainingRecord.objects.create(tenant=self.tenant_a, user=self.operator,
                                      training_type=course, completed_date=date.today())
        self._start(self.operator)

    # --- life limit at start
    def _life(self, obj, accumulated, hard):
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant_a, name=f"Cycles {hard}", unit="cycles", unit_label="Cycles",
            hard_limit=Decimal(hard))
        return LifeTracking.for_object(obj, definition, accumulated=Decimal(accumulated))[0]

    def test_a_life_limit_refuses_at_start_not_release(self):
        self._life(self.part, 100, 100)
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.LIFE_LIMIT])
        from Tracker.services.mes.gates import release_blockers
        se = StepExecution.objects.get(pk=self.visit.pk)
        self.assertNotIn(GateCode.LIFE_LIMIT,
                         [b.code for b in release_blockers(self.step, se, self.wo)])

    def test_an_extension_lets_it_start(self):
        tracking = self._life(self.part, 100, 100)
        tracking.apply_override(hard_limit=Decimal(120), reason="Re-inspected",
                                approved_by=self.user_a)
        self._start()

    # --- reman cycles
    def _core(self, number, serial, disassembled=False):
        from Tracker.services.reman.core_part import create_core
        core = create_core(tenant=self.tenant_a, core_number=number, core_type=self.pt,
                           serial_number=serial, received_date=date.today(),
                           received_by=self.user_a,
                           work_order=None if disassembled else self.wo,
                           step=None if disassembled else self.step)
        if disassembled:
            type(core).objects.filter(pk=core.pk).update(
                status='DISASSEMBLED', disassembly_started_at=timezone.now() - timedelta(days=400))
        return core

    def _reman_limit(self, hard):
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant_a, name="Remans", unit="remans", unit_label="Remans",
            hard_limit=Decimal(hard))
        PartTypeLifeLimit.objects.create(tenant=self.tenant_a, part_type=self.pt,
                                         definition=definition)
        return definition

    def _core_visit(self, core):
        return StepExecution.objects.create(tenant=self.tenant_a, part=core.part, step=self.step,
                                            visit_number=1, status="PENDING")

    def test_a_reman_is_counted_when_it_starts(self):
        definition = self._reman_limit(3)
        self._core("C-OLD-1", "SN-77", disassembled=True)
        core = self._core("C-NEW", "SN-77")
        tracking = LifeTracking.objects.for_object(core).get(definition=definition)
        self.assertEqual(tracking.accumulated, Decimal(1))  # its history
        start_execution(self._core_visit(core), self.user_a)
        tracking.refresh_from_db()
        self.assertEqual(tracking.accumulated, Decimal(2))

    def test_a_unit_at_its_reman_limit_is_refused_before_teardown(self):
        self._reman_limit(2)
        self._core("C-OLD-1", "SN-88", disassembled=True)
        self._core("C-OLD-2", "SN-88", disassembled=True)
        core = self._core("C-NEW", "SN-88")
        with self.assertRaises(StartRefused) as ctx:
            start_execution(self._core_visit(core), self.user_a)
        self.assertEqual(self._codes(ctx), [GateCode.LIFE_LIMIT])
        core.refresh_from_db()
        self.assertEqual(core.status, 'RECEIVED')

    # --- expired lots at staging
    def test_an_expired_lot_is_refused_at_staging(self):
        from Tracker.services.life_tracking.shelf_life import attach_shelf_life
        from Tracker.services.mes.staging import record_pick
        today = timezone.now().date()
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-OLD", material_type=self.pt,
            received_date=today, received_by=self.user_a, quantity=Decimal(10),
            quantity_remaining=Decimal(10), unit_of_measure="EA",
            manufacture_date=today - timedelta(days=400), expiration_date=today - timedelta(days=5))
        attach_shelf_life(lot)
        with self.assertRaisesMessage(ValueError, "shelf-life expired"):
            record_pick(self.tenant_a, self.wo.id, self.step.id, self.pt.id, 1,
                        [{'lot_id': str(lot.id), 'lot_number': lot.lot_number, 'qty': 1}],
                        self.user_a, kind='PART_TYPE')
