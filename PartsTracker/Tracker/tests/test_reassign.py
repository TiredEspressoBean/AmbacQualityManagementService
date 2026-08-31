"""`reassign_machine` / `reassign_operator` — direct-manipulation resource override.

Both apply immediately, mark the schedule stale, and warn (never block) when the machine
isn't eligible / the operator isn't qualified. Machine reassignment also pins the task.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    ScheduledTask,
    ScheduleResult,
    StepEquipmentAffinity,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.scheduling.manual_move import (
    bulk_reassign_machine,
    bulk_reassign_operator,
    reassign_machine,
    reassign_operator,
)
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class ReassignTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="RA", slug="reassign", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = User.objects.create_user(
            username="op1", email="op1@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.eligible = Equipments.objects.create(tenant=self.tenant, name="CNC-1")
        self.other = Equipments.objects.create(tenant=self.tenant, name="CNC-2")
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step, equipment=self.eligible,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-RA", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-RA-1", part_type=self.pt,
            work_order=self.wo, step=self.step)
        now = timezone.now()
        self.sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_stale=False)
        self.task = ScheduledTask.objects.create(
            tenant=self.tenant, schedule=self.sched, part=self.part, step=self.step,
            machine=self.eligible, start_time=now, end_time=now + timedelta(hours=1))

    def _stale(self):
        self.sched.refresh_from_db()
        return self.sched.is_stale

    def test_reassign_machine_eligible_pins_no_warning(self):
        res = reassign_machine(self.task, self.eligible)
        self.task.refresh_from_db()
        self.assertEqual(self.task.machine_id, self.eligible.id)
        self.assertTrue(self.task.is_pinned)
        self.assertTrue(self._stale())
        self.assertIsNone(res["warning"])

    def test_reassign_machine_ineligible_warns_but_applies(self):
        res = reassign_machine(self.task, self.other)  # not in the step's affinities
        self.task.refresh_from_db()
        self.assertEqual(self.task.machine_id, self.other.id)
        self.assertTrue(self.task.is_pinned)
        self.assertIsNotNone(res["warning"])

    def test_reassign_operator_assigns_and_marks_stale(self):
        # no training requirement on the step → the operator is qualified
        res = reassign_operator(self.task, self.user)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_operator_id, self.user.id)
        self.assertTrue(self._stale())
        self.assertIsNone(res["warning"])

    def test_reassign_operator_none_clears(self):
        reassign_operator(self.task, self.user)
        reassign_operator(self.task, None)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assigned_operator_id)

    # --- bulk (multi-select) variants ---------------------------------------

    def _second_task(self):
        """A second scheduled part on the same step, for bulk tests."""
        part2 = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-RA-2", part_type=self.pt,
            work_order=self.wo, step=self.step)
        now = timezone.now()
        return ScheduledTask.objects.create(
            tenant=self.tenant, schedule=self.sched, part=part2, step=self.step,
            machine=self.eligible, start_time=now, end_time=now + timedelta(hours=1))

    def test_bulk_reassign_machine_moves_and_pins_all(self):
        t2 = self._second_task()
        res = bulk_reassign_machine([self.task, t2], self.eligible)
        self.assertEqual(res["changed"], 2)
        self.assertEqual(res["warnings"], [])
        for t in (self.task, t2):
            t.refresh_from_db()
            self.assertEqual(t.machine_id, self.eligible.id)
            self.assertTrue(t.is_pinned)
        self.assertTrue(self._stale())

    def test_bulk_reassign_machine_ineligible_warns_once_but_applies(self):
        t2 = self._second_task()
        res = bulk_reassign_machine([self.task, t2], self.other)  # both same step
        self.assertEqual(res["changed"], 2)
        # one warning for the shared step, not one per task
        self.assertEqual(len(res["warnings"]), 1)
        for t in (self.task, t2):
            t.refresh_from_db()
            self.assertEqual(t.machine_id, self.other.id)

    def test_bulk_reassign_operator_covers_all(self):
        t2 = self._second_task()
        res = bulk_reassign_operator([self.task, t2], self.user)
        self.assertEqual(res["changed"], 2)
        for t in (self.task, t2):
            t.refresh_from_db()
            self.assertEqual(t.assigned_operator_id, self.user.id)
        self.assertTrue(self._stale())

    def test_bulk_reassign_operator_none_clears_all(self):
        t2 = self._second_task()
        bulk_reassign_operator([self.task, t2], self.user)
        bulk_reassign_operator([self.task, t2], None)
        for t in (self.task, t2):
            t.refresh_from_db()
            self.assertIsNone(t.assigned_operator_id)
