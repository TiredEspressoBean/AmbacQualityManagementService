"""Phase 2 CP-SAT solver — minimal slice: precedence, machine capacity (no-overlap
per machine), makespan objective, and the active-schedule supersede.
"""
from datetime import date, time as dtime, timedelta as _td
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments,
    Fixture,
    MeasurementDefinition,
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
    WorkOrderPriority,
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

    def test_machine_choice_spreads_across_machines(self):
        # step1 gets a second eligible machine → two parts run in parallel.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        _, parts = self._wo("WO-MC", 2)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len({t.machine_id for t in s1}), 2,
                         "two parts should spread across the two machines")

    def test_cost_objective_schedules_urgent_before_low(self):
        # Two WOs (1 part each) contend for the same single machine at step1, both
        # already overdue. The solver should place URGENT first (its lateness costs
        # far more per minute than LOW's).
        past = date.today() - _td(days=1)
        wo_low = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-LOW", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process, priority=WorkOrderPriority.LOW, expected_completion=past)
        low_part = Parts.objects.create(
            tenant=self.tenant, ERP_id="LOW-P", part_type=self.pt, work_order=wo_low, step=self.step1)
        wo_urg = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-URG", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process, priority=WorkOrderPriority.URGENT, expected_completion=past)
        urg_part = Parts.objects.create(
            tenant=self.tenant, ERP_id="URG-P", part_type=self.pt, work_order=wo_urg, step=self.step1)

        result = solve_schedule(self.tenant)
        urg = result.tasks.get(part=urg_part, step=self.step1)
        low = result.tasks.get(part=low_part, step=self.step1)
        self.assertLess(urg.start_time, low.start_time, "urgent work should be scheduled first")

    # ---- shift windows / secondary resources / fixtures ------------------

    def test_window_gaps_helper(self):
        from Tracker.services.scheduling.solver import _window_gaps
        from Tracker.services.scheduling.data import MachineWindow
        start = timezone.now()
        H = 600
        w = MachineWindow(equipment_id=self.machine.id,
                          start=start + _td(minutes=60), end=start + _td(minutes=300))
        self.assertEqual(_window_gaps([w], start, H), [(0, 60), (300, 600)])
        self.assertEqual(_window_gaps([], start, H), [])  # no windows → 24/7, no gaps

    def test_shift_constrained_solve_is_feasible(self):
        from Tracker.models import Shift
        Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        self._wo("WO-SH", 1)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        self.assertEqual(result.tasks.count(), 2)

    def test_secondary_gauge_serializes(self):
        # step1 has two machines (could run in parallel) but shares one gauge → the
        # two parts' step1 tasks cannot overlap in time.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        gauge = Equipments.objects.create(tenant=self.tenant, name="Keyence", is_schedulable=True)
        MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.step1, default_equipment=gauge, label="OD", type="NUMERIC")
        self._wo("WO-G", 2)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertFalse(self._overlaps(s1[0], s1[1]),
                         "a shared gauge must serialize the two tasks")

    def test_fixture_capacity(self):
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        fx = Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=1)
        fx.steps.add(self.step1)
        self._wo("WO-FX", 2)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertFalse(self._overlaps(s1[0], s1[1]),
                         "quantity-1 fixture must serialize the two tasks")

    def test_fixture_capacity_two_allows_parallel(self):
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        fx = Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=2)
        fx.steps.add(self.step1)
        self._wo("WO-FX2", 2)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertTrue(self._overlaps(s1[0], s1[1]),
                        "quantity-2 fixture allows the two tasks to run concurrently")

    def test_unschedulable_step_still_scheduled_without_capacity(self):
        # A step whose only machine is not is_schedulable gets no capacity link but
        # is still placed (precedence-only) — no crash, task written with null machine.
        self.machine.is_schedulable = False
        self.machine.save(update_fields=["is_schedulable"])
        _, parts = self._wo("WO-D", 1)
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.count(), 2)
        self.assertTrue(all(t.machine_id is None for t in result.tasks.all()))
