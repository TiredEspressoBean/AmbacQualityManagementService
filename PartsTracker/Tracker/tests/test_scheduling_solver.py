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

    def test_scheduled_breaks_expand_and_solve_stays_feasible(self):
        from Tracker.models import Shift
        from Tracker.services.scheduling import data as sdata
        Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True,
            break_windows=[{"start": "12:00", "end": "12:30"}])
        # Lunch expands to a break interval per day across the horizon.
        breaks = sdata.get_break_windows(self.tenant, sdata.get_schedule_horizon(self.tenant))
        self.assertTrue(breaks)
        # The solver adds the attended-task break constraint and stays feasible.
        self._wo("WO-BR", 1)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        self.assertEqual(result.tasks.count(), 2)

    def test_changeover_gap_between_different_steps(self):
        from Tracker.models import WorkCenterChangeover
        # step1 → step2 on the same machine incurs a 45-min changeover on top of
        # the precedence constraint.
        WorkCenterChangeover.objects.create(
            tenant=self.tenant, equipment=self.machine,
            from_step=self.step1, to_step=self.step2, changeover_minutes=45)
        _, parts = self._wo("WO-CO", 1)
        result = solve_schedule(self.tenant)
        tasks = {t.step_id: t for t in result.tasks.filter(part=parts[0])}
        gap = (tasks[self.step2.id].start_time - tasks[self.step1.id].end_time).total_seconds() / 60
        self.assertGreaterEqual(gap, 45, "changeover must separate the two step-types")

    def test_setup_solve_is_feasible(self):
        StepTiming.objects.filter(step=self.step1).update(setup_minutes=20)
        self._wo("WO-SU", 1)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        self.assertEqual(result.tasks.count(), 2)

    # ---- time fences / warm-start / continuous machines ------------------

    def test_pinned_previous_task_holds_start_and_machine(self):
        # A prior active schedule whose step1 task is planner-pinned (is_pinned) must
        # be kept at the same start + machine on the next solve, even though it sits
        # in the slushy zone (5 days out) where moves would otherwise be free.
        from Tracker.models.scheduling import FenceZone
        _, parts = self._wo("WO-PIN", 1)
        part = parts[0]
        base = timezone.now()
        pinned_start = base + _td(days=5)
        prev = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=base, horizon_end=base + _td(days=30),
            solver_status=SolverStatus.OPTIMAL, is_active=True)
        ScheduledTask.objects.create(
            tenant=self.tenant, schedule=prev, part=part, step=self.step1,
            machine=self.machine, start_time=pinned_start,
            end_time=pinned_start + _td(minutes=60),
            is_pinned=True, fence_zone=FenceZone.SLUSHY)

        result = solve_schedule(self.tenant)
        new = result.tasks.get(part=part, step=self.step1)
        self.assertTrue(new.is_pinned)
        self.assertEqual(new.machine_id, self.machine.id)
        self.assertAlmostEqual((new.start_time - pinned_start).total_seconds(), 0, delta=120)

    def test_frozen_zone_task_marked_frozen(self):
        # With no prior schedule, a task the solver places inside the frozen zone
        # (default 2 days) is stamped fence_zone=frozen.
        from Tracker.models.scheduling import FenceZone
        _, parts = self._wo("WO-FZ", 1)
        result = solve_schedule(self.tenant)
        s1 = result.tasks.get(part=parts[0], step=self.step1)
        # a fresh solve packs everything at t≈0, well inside the 2-day frozen zone.
        self.assertEqual(s1.fence_zone, FenceZone.FROZEN)

    def test_continuous_machine_uses_throughput_duration(self):
        # A continuous-feed machine ignores the 60-min cycle and runs at
        # 60 / parts_per_hour minutes per part; bar-change downtime stays feasible.
        from Tracker.models import ContinuousMachine
        ContinuousMachine.objects.create(
            tenant=self.tenant, equipment=self.machine,
            parts_per_hour=2, bar_change_interval_hours=8,
            bar_change_duration_minutes=15)
        _, parts = self._wo("WO-CONT", 1)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        s1 = result.tasks.get(part=parts[0], step=self.step1)
        self.assertEqual((s1.end_time - s1.start_time).total_seconds() / 60, 30,
                         "continuous machine uses 60/parts_per_hour = 30 min, not the 60-min cycle")

    def test_unschedulable_step_still_scheduled_without_capacity(self):
        # A step whose only machine is not is_schedulable gets no capacity link but
        # is still placed (precedence-only) — no crash, task written with null machine.
        self.machine.is_schedulable = False
        self.machine.save(update_fields=["is_schedulable"])
        _, parts = self._wo("WO-D", 1)
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.count(), 2)
        self.assertTrue(all(t.machine_id is None for t in result.tasks.all()))

    # ---- schedulability gates (don't plan work that can't run) -----------

    def test_on_hold_workorder_is_not_scheduled(self):
        wo, _ = self._wo("WO-HOLD", 1)
        wo.workorder_status = WorkOrderStatus.ON_HOLD
        wo.save(update_fields=["workorder_status"])
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.count(), 0, "held WOs are excluded from planning")

    def test_quarantined_part_is_not_scheduled(self):
        from Tracker.models.mes_lite import PartsStatus
        _, parts = self._wo("WO-QUAR", 2)
        parts[0].part_status = PartsStatus.QUARANTINED
        parts[0].save(update_fields=["part_status"])
        result = solve_schedule(self.tenant)
        scheduled_parts = {t.part_id for t in result.tasks.all()}
        self.assertNotIn(parts[0].id, scheduled_parts, "a quarantined part is dropped")
        self.assertIn(parts[1].id, scheduled_parts, "its healthy sibling still schedules")

    def test_out_of_service_machine_is_not_assigned(self):
        from Tracker.models.mes_standard import EquipmentStatus
        self.machine.status = EquipmentStatus.OUT_OF_SERVICE
        self.machine.save(update_fields=["status"])
        _, parts = self._wo("WO-DOWN", 1)
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.count(), 2)
        self.assertTrue(all(t.machine_id is None for t in result.tasks.all()),
                        "a down machine is never assigned work")

    def test_expected_start_gates_earliest_release(self):
        from datetime import datetime
        wo, _ = self._wo("WO-REL", 1)
        release_date = date.today() + _td(days=3)
        wo.expected_start = release_date
        wo.save(update_fields=["expected_start"])
        result = solve_schedule(self.tenant)
        release_dt = timezone.make_aware(datetime.combine(release_date, dtime.min))
        for t in result.tasks.all():
            self.assertGreaterEqual(t.start_time, release_dt - _td(minutes=1),
                                    "no task starts before the WO's expected_start")

    # ---- route-aware scheduling ------------------------------------------

    def test_schedules_only_remaining_route_from_current_step(self):
        # A part sitting on step2 must not re-book the already-completed step1
        # (staggered batches: parts spread across steps shouldn't phantom-load).
        _, parts = self._wo("WO-MID", 1)
        parts[0].step = self.step2
        parts[0].save(update_fields=["step"])
        result = solve_schedule(self.tenant)
        steps = {t.step_id for t in result.tasks.filter(part=parts[0])}
        self.assertEqual(steps, {self.step2.id}, "only the remaining route is scheduled")

    def test_default_edges_exclude_rework_branch(self):
        # With an authored routing graph, a rework step reachable only via an
        # ALTERNATE edge is not scheduled up front — only the DEFAULT spine is.
        from Tracker.models import StepEdge
        rework = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Rework", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=rework, order=3)
        StepEdge.objects.create(
            process=self.process, from_step=self.step1, to_step=self.step2, edge_type="DEFAULT")
        StepEdge.objects.create(
            process=self.process, from_step=self.step2, to_step=rework, edge_type="ALTERNATE")
        _, parts = self._wo("WO-RW", 1)
        result = solve_schedule(self.tenant)
        steps = {t.step_id for t in result.tasks.all()}
        self.assertEqual(steps, {self.step1.id, self.step2.id})
        self.assertNotIn(rework.id, steps, "an ALTERNATE (rework) step isn't planned up front")
