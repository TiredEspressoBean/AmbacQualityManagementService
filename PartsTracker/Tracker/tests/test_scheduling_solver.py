"""Phase 2 CP-SAT solver — minimal slice: precedence, machine capacity (no-overlap
per machine), makespan objective, and the active-schedule supersede.
"""
from decimal import Decimal

from django.test import TestCase

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
    StepTiming,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.scheduling import SolverStatus
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.tests.base import TenantContextMixin


class SolverTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Solve", slug="sched-solve", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.machine = Equipments.objects.create(tenant=self.tenant, name="CNC-1", is_schedulable=True)
        self.step1 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Turn", step_type="TASK")
        self.step2 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Mill", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        StepTiming.objects.create(tenant=self.tenant, step=self.step1, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=self.tenant, step=self.step2, cycle_time_minutes=30)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)

    def _wo(self, erp, n_parts):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n_parts, process=self.process)
        parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                work_order=wo, step=self.step1)
            for i in range(n_parts)
        ]
        return wo, parts

    @staticmethod
    def _overlaps(a, b):
        return a.start_time < b.end_time and b.start_time < a.end_time

    def test_empty_tenant_returns_empty_optimal(self):
        result = solve_schedule(self.tenant)
        self.assertEqual(result.solver_status, SolverStatus.OPTIMAL)
        self.assertTrue(result.is_active)
        self.assertEqual(result.tasks.count(), 0)

    def test_produces_tasks_and_intra_part_precedence(self):
        _, parts = self._wo("WO-A", 1)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        tasks = {t.step_id: t for t in result.tasks.filter(part=parts[0])}
        self.assertEqual(len(tasks), 2)  # two non-terminal steps
        # step2 cannot start before step1 finishes.
        self.assertGreaterEqual(tasks[self.step2.id].start_time, tasks[self.step1.id].end_time)
        # durations reflect the timings (60 / 30 min).
        s1 = tasks[self.step1.id]
        self.assertEqual((s1.end_time - s1.start_time).total_seconds(), 60 * 60)

    def test_machine_capacity_no_overlap(self):
        # Two parts share the same machine at step1 → their tasks must not overlap.
        _, parts = self._wo("WO-B", 2)
        result = solve_schedule(self.tenant)
        s1_tasks = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1_tasks), 2)
        self.assertFalse(self._overlaps(s1_tasks[0], s1_tasks[1]),
                         "two parts on the same machine must be serialized")

    def test_solve_supersedes_prior_active(self):
        self._wo("WO-C", 1)
        first = solve_schedule(self.tenant)
        second = solve_schedule(self.tenant)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(first.is_stale)
        self.assertTrue(second.is_active)
        # exactly one active schedule at a time.
        self.assertEqual(ScheduleResult.objects.filter(tenant=self.tenant, is_active=True).count(), 1)

    def test_unschedulable_step_still_scheduled_without_capacity(self):
        # A step whose only machine is not is_schedulable gets no capacity link but
        # is still placed (precedence-only) — no crash, task written with null machine.
        self.machine.is_schedulable = False
        self.machine.save(update_fields=["is_schedulable"])
        _, parts = self._wo("WO-D", 1)
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.count(), 2)
        self.assertTrue(all(t.machine_id is None for t in result.tasks.all()))
