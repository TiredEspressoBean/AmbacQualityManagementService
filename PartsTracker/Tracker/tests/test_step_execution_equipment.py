"""Wiring #1 (plan #1): advancing a part stamps the destination step's authored
production machine (highest-priority StepEquipmentAffinity) onto the new
StepExecution as a PRODUCTION StepExecutionEquipment link. Steps with no single
authored machine leave it unset — the operator (DWI) or the solver sets it then.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    StepEquipmentAffinity,
    StepExecution,
    StepExecutionEquipment,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.qms import EquipmentRole
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin


class StepExecutionEquipmentCaptureTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Eq", slug="exec-equip", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-eq", email="eq@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.cnc = Equipments.objects.create(tenant=self.tenant, name="CNC-7")
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK",
        )
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-EQ-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-EQ-1", part_type=self.pt,
            work_order=self.wo, step=self.step1,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step1, visit_number=1,
            status="IN_PROGRESS",
        )

    def _advance(self):
        return try_advance_lot(
            work_order_id=str(self.wo.id), step_id=str(self.step1.id),
            tenant_id=str(self.tenant.id), operator=self.user,
        )

    def _new_exec_at_step2(self):
        return StepExecution.objects.get(part=self.part, step=self.step2)

    def test_preferred_affinity_stamps_production_link(self):
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=self.cnc,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED,
        )
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        ex = self._new_exec_at_step2()
        link = ex.equipment_links.get(role=EquipmentRole.PRODUCTION)
        self.assertEqual(link.equipment, self.cnc)
        self.assertEqual(ex.primary_equipment, self.cnc)

    def test_dialed_in_wins_over_preferred(self):
        best = Equipments.objects.create(tenant=self.tenant, name="CNC-dialed")
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=self.cnc,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED,
        )
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=best,
            affinity=StepEquipmentAffinity.Affinity.DIALED_IN,
        )
        self._advance()
        self.assertEqual(self._new_exec_at_step2().primary_equipment, best)

    def test_only_eligible_leaves_production_unset(self):
        # ELIGIBLE is a candidate set, not a single authored default → no stamp.
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=self.cnc,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE,
        )
        self._advance()
        ex = self._new_exec_at_step2()
        self.assertFalse(ex.equipment_links.exists())
        self.assertIsNone(ex.primary_equipment)

    def test_no_affinity_leaves_production_unset(self):
        self._advance()
        self.assertIsNone(self._new_exec_at_step2().primary_equipment)

    def _make_scheduled_task(self, machine, step, *, is_active=True):
        from datetime import timedelta

        from django.utils import timezone

        from Tracker.models import ScheduledTask, ScheduleResult
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=is_active,
        )
        return ScheduledTask.objects.create(
            tenant=self.tenant, schedule=sched, part=self.part, step=step,
            machine=machine, start_time=now, end_time=now + timedelta(hours=1),
        )

    def test_active_schedule_machine_stamped_when_no_affinity(self):
        # No authored affinity on step2, but the live schedule assigned CNC-7 →
        # that solver choice becomes the as-built PRODUCTION link.
        self._make_scheduled_task(self.cnc, self.step2, is_active=True)
        self._advance()
        self.assertEqual(self._new_exec_at_step2().primary_equipment, self.cnc)

    def test_authored_affinity_wins_over_schedule(self):
        best = Equipments.objects.create(tenant=self.tenant, name="CNC-dialed")
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=best,
            affinity=StepEquipmentAffinity.Affinity.DIALED_IN,
        )
        self._make_scheduled_task(self.cnc, self.step2, is_active=True)
        self._advance()
        # Authoring beats the schedule fallback.
        self.assertEqual(self._new_exec_at_step2().primary_equipment, best)

    def test_inactive_schedule_not_used(self):
        self._make_scheduled_task(self.cnc, self.step2, is_active=False)
        self._advance()
        self.assertIsNone(self._new_exec_at_step2().primary_equipment)
