"""Phase 2 CP-SAT solver — minimal slice: precedence, machine capacity (no-overlap
per machine), makespan objective, and the active-schedule supersede.
"""
from datetime import date, datetime, time as dtime, timedelta as _td
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from django.contrib.auth import get_user_model

from Tracker.models import (
    BOM,
    BOMLine,
    Equipments,
    Fixture,
    MaterialLot,
    MeasurementDefinition,
    Parts,
    PartTypes,
    PlantCalendarException,
    Processes,
    ProcessStep,
    ScheduledTask,
    ScheduleResult,
    Shift,
    StepEquipmentAffinity,
    Steps,
    StepTiming,
    Tenant,
    WorkOrder,
    WorkOrderPriority,
    WorkOrderStatus,
)
from Tracker.models.scheduling import SolverStatus
from Tracker.services.scheduling import data as sched_data
from Tracker.services.scheduling.data import HorizonData
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

    @staticmethod
    def _peak_concurrency(tasks):
        evs = []
        for t in tasks:
            evs.append((t.start_time, 1))
            evs.append((t.end_time, -1))
        evs.sort(key=lambda x: (x[0], x[1]))
        cur = peak = 0
        for _, d in evs:
            cur += d
            peak = max(peak, cur)
        return peak

    def test_batches_same_workorder_on_a_machine(self):
        # Two work orders, three parts each, sharing one machine. With the job-change
        # setup, interleaving the WOs costs setup time the solver avoids — so it keeps
        # each WO's parts batched at each operation (minimal same-op WO switches).
        self._wo("WB-A", 3)
        self._wo("WB-B", 3)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        tasks = list(
            ScheduledTask.objects.filter(schedule=result, machine=self.machine)
            .select_related('part__work_order').order_by('start_time')
        )
        # Count WO changes between adjacent SAME-operation tasks. Perfectly batched =
        # one switch per operation (2 ops → 2); interleaving would be far more.
        switches = sum(
            1 for a, b in zip(tasks, tasks[1:])
            if a.step_id == b.step_id and a.part.work_order_id != b.part.work_order_id
        )
        self.assertLessEqual(switches, 2, f"WOs not batched: {switches} same-op switches")

    def test_outside_process_scheduled_as_elapsed_and_gates_downstream(self):
        # step1 (in-house machine) → step2 → OSP plating (2-day turnaround) → grind (in-house).
        osp_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Plating", step_type="TASK",
            is_outside_process=True, outside_process_lead_days=2)
        grind = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Grind", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=osp_step, order=3)
        ProcessStep.objects.create(process=self.process, step=grind, order=4)
        StepTiming.objects.create(tenant=self.tenant, step=grind, cycle_time_minutes=30)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=grind, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        self._wo("WO-OSP", 1)

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        by_step = {t.step_id: t for t in ScheduledTask.objects.filter(schedule=result)}
        osp_task = by_step[osp_step.id]
        # Elapsed vendor turnaround: ~2 calendar days, no machine, no operator.
        dur_min = (osp_task.end_time - osp_task.start_time).total_seconds() / 60
        self.assertAlmostEqual(dur_min, 2 * 24 * 60, delta=1)
        self.assertIsNone(osp_task.machine_id)
        # Downstream op cannot start until the part is back from the vendor.
        self.assertGreaterEqual(by_step[grind.id].start_time, osp_task.end_time)

    def test_batch_capacity_runs_lots_concurrently(self):
        # A batch/process resource (batch_capacity=3) runs up to 3 jobs at once, unlike a
        # normal one-at-a-time machine. Bake-only process so upstream doesn't stagger them.
        pt = PartTypes.objects.create(tenant=self.tenant, name="Seal")
        proc = Processes.objects.create(tenant=self.tenant, name="Bake-only", part_type=pt)
        furnace = Equipments.objects.create(
            tenant=self.tenant, name="Furnace", is_schedulable=True, batch_capacity=3)
        bake = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Bake", step_type="TASK")
        ProcessStep.objects.create(process=proc, step=bake, order=1)
        StepTiming.objects.create(tenant=self.tenant, step=bake, cycle_time_minutes=120)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=bake, equipment=furnace,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        for i in range(3):
            wo = WorkOrder.objects.create(
                tenant=self.tenant, ERP_id=f"BK{i}", workorder_status=WorkOrderStatus.IN_PROGRESS,
                quantity=1, process=proc)
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"BK{i}-P", part_type=pt, work_order=wo, step=bake)

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        tasks = list(ScheduledTask.objects.filter(schedule=result, step=bake))
        self.assertEqual(len(tasks), 3)
        # capacity 3 → all three loads co-run on the furnace (a no-overlap machine → peak 1).
        self.assertEqual(self._peak_concurrency(tasks), 3)

    def test_cycle_batch_splits_job_into_fixed_time_loads(self):
        # CYCLE furnace (cap 4, fixed 120-min cycle): a 10-part job = ceil(10/4)=3 loads =
        # 360 min, NOT 10 × 120 per-part, and NOT one impossible 10-part load.
        pt = PartTypes.objects.create(tenant=self.tenant, name="Ring")
        proc = Processes.objects.create(tenant=self.tenant, name="Cure-only", part_type=pt)
        oven = Equipments.objects.create(
            tenant=self.tenant, name="Cure Oven", is_schedulable=True,
            batch_capacity=4, batch_mode=Equipments.BatchMode.CYCLE)
        cure = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Cure", step_type="TASK")
        ProcessStep.objects.create(process=proc, step=cure, order=1)
        StepTiming.objects.create(tenant=self.tenant, step=cure, cycle_time_minutes=120)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=cure, equipment=oven,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="CURE-10", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=10, process=proc)
        for i in range(10):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"CURE-10-P{i}", part_type=pt, work_order=wo, step=cure)

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        tasks = list(ScheduledTask.objects.filter(schedule=result, step=cure))
        self.assertTrue(tasks)
        dur = (tasks[0].end_time - tasks[0].start_time).total_seconds() / 60
        self.assertAlmostEqual(dur, 3 * 120, delta=1)  # 3 fixed-time loads

    def _clean_coat_process(self, max_minutes):
        """A clean→coat process with a max-time edge; returns (proc, pt, clean, coat, machine)."""
        from Tracker.models import StepEdge
        pt = PartTypes.objects.create(tenant=self.tenant, name="Coated")
        proc = Processes.objects.create(tenant=self.tenant, name="Clean-Coat", part_type=pt)
        m = Equipments.objects.create(tenant=self.tenant, name="Line", is_schedulable=True)
        clean = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Clean", step_type="TASK")
        coat = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Coat", step_type="TASK")
        ProcessStep.objects.create(process=proc, step=clean, order=1)
        ProcessStep.objects.create(process=proc, step=coat, order=2)
        StepEdge.objects.create(process=proc, from_step=clean, to_step=coat,
                                edge_type="DEFAULT", max_minutes=max_minutes)
        StepTiming.objects.create(tenant=self.tenant, step=clean, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=self.tenant, step=coat, cycle_time_minutes=30)
        for s in (clean, coat):
            StepEquipmentAffinity.objects.create(
                tenant=self.tenant, step=s, equipment=m,
                affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        return proc, pt, clean, coat, m

    def test_max_time_between_ops_met_not_flagged(self):
        proc, pt, clean, coat, _ = self._clean_coat_process(max_minutes=240)
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="CC", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=proc)
        Parts.objects.create(tenant=self.tenant, ERP_id="CC-P", part_type=pt, work_order=wo, step=clean)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        by_step = {t.step_id: t for t in ScheduledTask.objects.filter(schedule=result)}
        gap = (by_step[coat.id].start_time - by_step[clean.id].end_time).total_seconds() / 60
        self.assertLessEqual(gap, 240)                        # window met
        self.assertFalse(by_step[coat.id].cure_window_violation)

    def test_max_time_between_ops_violation_flagged(self):
        # An in-progress clean is pinned (can't move); the coater is down through the cure
        # window → coat is forced past the limit. Soft constraint: it still schedules, but
        # the op is flagged (cure_window_violation), not a hard INFEASIBLE.
        from Tracker.models import StepEdge, StepExecution, PartsStatus, DowntimeEvent
        pt = PartTypes.objects.create(tenant=self.tenant, name="Coated2")
        proc = Processes.objects.create(tenant=self.tenant, name="CC2", part_type=pt)
        washer = Equipments.objects.create(tenant=self.tenant, name="Washer", is_schedulable=True)
        coater = Equipments.objects.create(tenant=self.tenant, name="Coater", is_schedulable=True)
        clean = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Clean2", step_type="TASK")
        coat = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Coat2", step_type="TASK")
        ProcessStep.objects.create(process=proc, step=clean, order=1)
        ProcessStep.objects.create(process=proc, step=coat, order=2)
        StepEdge.objects.create(process=proc, from_step=clean, to_step=coat,
                                edge_type="DEFAULT", max_minutes=30)
        StepTiming.objects.create(tenant=self.tenant, step=clean, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=self.tenant, step=coat, cycle_time_minutes=30)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=clean, equipment=washer,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=coat, equipment=coater,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        now = timezone.now()
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="CC2", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=proc)
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="CC2-P", part_type=pt, work_order=wo, step=clean,
            part_status=PartsStatus.IN_PROGRESS)
        prev = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + _td(days=2),
            is_active=True, is_stale=False)
        ScheduledTask.objects.create(
            tenant=self.tenant, schedule=prev, part=part, step=clean, machine=washer,
            start_time=now - _td(minutes=40), end_time=now + _td(minutes=20))
        se = StepExecution.objects.create(tenant=self.tenant, part=part, step=clean)
        StepExecution.objects.filter(pk=se.pk).update(entered_at=now - _td(minutes=40))
        dt_user = get_user_model().objects.create_user(
            username="dt", email="dt@c.test", password="x", tenant=self.tenant)
        DowntimeEvent.objects.create(
            tenant=self.tenant, equipment=coater, category="PLANNED", reason="PM",
            reported_by=dt_user, start_time=now, end_time=now + _td(minutes=300))

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        coat_task = ScheduledTask.objects.get(schedule=result, step=coat)
        self.assertTrue(coat_task.cure_window_violation)  # flagged, not infeasible

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

    def test_in_progress_op_pinned_now_with_remaining_duration(self):
        # A part whose current step is physically running (open StepExecution, started
        # 40 min ago; full step1 = 60 min) must be scheduled to start "now" with only its
        # REMAINING (~20 min) duration, on the machine it's running on — not re-planned
        # later at full duration.
        from Tracker.models import PartsStatus, StepExecution
        wo, parts = self._wo("WO-IP", 1)
        part = parts[0]
        part.part_status = PartsStatus.IN_PROGRESS
        part.save(update_fields=['part_status'])
        now = timezone.now()
        # previous active schedule tells the solver which machine it's running on
        prev = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + _td(days=2),
            is_active=True, is_stale=False)
        ScheduledTask.objects.create(
            tenant=self.tenant, schedule=prev, part=part, step=self.step1,
            machine=self.machine, start_time=now - _td(minutes=40),
            end_time=now + _td(minutes=20))
        # open execution started 40 min ago (auto_now_add → override via .update())
        se = StepExecution.objects.create(tenant=self.tenant, part=part, step=self.step1)
        StepExecution.objects.filter(pk=se.pk).update(entered_at=now - _td(minutes=40))

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        t1 = ScheduledTask.objects.get(schedule=result, part=part, step=self.step1)
        # starts ~now (minute 0 of the horizon)
        self.assertLess(abs((t1.start_time - result.horizon_start).total_seconds()), 120)
        # only the remaining ~20 min is booked, not the full 60
        dur_min = (t1.end_time - t1.start_time).total_seconds() / 60
        self.assertLess(dur_min, 40)
        self.assertGreaterEqual(dur_min, 10)
        # pinned on the machine it was running on, and flagged in-progress
        self.assertEqual(t1.machine_id, self.machine.id)
        self.assertTrue(t1.in_progress)
        # the next step still follows the (shortened) running op
        t2 = ScheduledTask.objects.get(schedule=result, part=part, step=self.step2)
        self.assertGreaterEqual(t2.start_time, t1.end_time)

    def test_move_time_gap_between_operations(self):
        # With a 30-min inter-op move/queue time, step2 can't start until 30 min after
        # step1 finishes (vs 0 with the default).
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.create(tenant=self.tenant, default_move_minutes=30)
        _, parts = self._wo("WO-MV", 1)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        tasks = {t.step_id: t for t in result.tasks.filter(part=parts[0])}
        gap_min = (tasks[self.step2.id].start_time
                   - tasks[self.step1.id].end_time).total_seconds() / 60
        self.assertGreaterEqual(gap_min, 30)

    def test_shared_tool_serializes_ops(self):
        # A scarce shared resource (a cutting tool, quantity 1) required at step1 forces two
        # WOs' step1 ops to serialize even though a second machine would let them run in
        # parallel — tools/dies are finite resources like fixtures.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        tool = Fixture.objects.create(
            tenant=self.tenant, name="Broach", kind="TOOL", quantity=1)
        tool.steps.add(self.step1)
        self._wo("WT-A", 1)
        self._wo("WT-B", 1)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        s1 = list(ScheduledTask.objects.filter(schedule=result, step=self.step1)
                  .order_by('start_time'))
        self.assertEqual(len(s1), 2)
        self.assertFalse(self._overlaps(s1[0], s1[1]),
                         "a shared quantity-1 tool must serialize the two ops")

    def test_not_started_op_uses_full_duration(self):
        # Control: same setup WITHOUT an open StepExecution → step1 books its full 60 min.
        _, parts = self._wo("WO-NS", 1)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        t1 = ScheduledTask.objects.get(schedule=result, part=parts[0], step=self.step1)
        self.assertEqual((t1.end_time - t1.start_time).total_seconds(), 60 * 60)

    def test_machine_capacity_no_overlap(self):
        # Two lots (one part each) contend for the same machine at step1 → their
        # operations must not overlap. Two parts of ONE work order would be a single
        # lot (one interval), so capacity is tested with two work orders.
        self._wo("WO-B1", 1)
        self._wo("WO-B2", 1)
        result = solve_schedule(self.tenant)
        s1_tasks = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1_tasks), 2)
        self.assertFalse(self._overlaps(s1_tasks[0], s1_tasks[1]),
                         "two lots on the same machine must be serialized")

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
        # step1 gets a second eligible machine → two lots run in parallel on the two
        # machines. A single lot can't split across machines, so this uses two lots.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        self._wo("WO-MC1", 1)
        self._wo("WO-MC2", 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len({t.machine_id for t in s1}), 2,
                         "two lots should spread across the two machines")

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
        # step1 has two machines (lots could run in parallel) but shares one gauge → the
        # two lots' step1 operations cannot overlap in time.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        gauge = Equipments.objects.create(tenant=self.tenant, name="Keyence", is_schedulable=True)
        MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.step1, default_equipment=gauge, label="OD", type="NUMERIC")
        self._wo("WO-G1", 1)
        self._wo("WO-G2", 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertFalse(self._overlaps(s1[0], s1[1]),
                         "a shared gauge must serialize the two lots")

    def test_fixture_capacity(self):
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        fx = Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=1)
        fx.steps.add(self.step1)
        self._wo("WO-FX1", 1)
        self._wo("WO-FX2", 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertFalse(self._overlaps(s1[0], s1[1]),
                         "quantity-1 fixture must serialize the two lots")

    def test_fixture_capacity_two_allows_parallel(self):
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        fx = Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=2)
        fx.steps.add(self.step1)
        self._wo("WO-FX2a", 1)
        self._wo("WO-FX2b", 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertTrue(self._overlaps(s1[0], s1[1]),
                        "quantity-2 fixture allows the two lots to run concurrently")

    def test_labor_capacity_caps_concurrent_attended(self):
        # Three machines let step1 run three lots at once on MACHINE capacity alone, but
        # only two operators are rostered → the crew cap forces at most two attended lots
        # concurrently (the third waits for a free operator).
        from Tracker.models import Shift, User
        for i in (2, 3):
            m = Equipments.objects.create(tenant=self.tenant, name=f"CNC-{i}", is_schedulable=True)
            for step in (self.step1, self.step2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        shift = Shift.objects.create(
            tenant=self.tenant, name="All", code="ALL",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        for i in range(2):
            User.objects.create(username=f"op{i}", tenant=self.tenant, user_type='INTERNAL',
                                is_active=True, default_shift=shift)
        for n in ("L1", "L2", "L3"):
            self._wo(n, 1)
        result = solve_schedule(self.tenant, time_limit_seconds=20)
        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1), 3)
        self.assertLessEqual(self._peak_concurrency(s1), 2,
                             "labor capacity must cap concurrent attended lots at the crew size")

    def test_no_roster_leaves_labor_unconstrained(self):
        # With a shift but NO rostered operators (crew 0), the labor cap is skipped and
        # three lots run in parallel across three machines (machine capacity only).
        from Tracker.models import Shift
        for i in (2, 3):
            m = Equipments.objects.create(tenant=self.tenant, name=f"CNC-{i}", is_schedulable=True)
            for step in (self.step1, self.step2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        Shift.objects.create(
            tenant=self.tenant, name="All", code="ALL",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        for n in ("L1", "L2", "L3"):
            self._wo(n, 1)
        result = solve_schedule(self.tenant, time_limit_seconds=20)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(self._peak_concurrency(s1), 3,
                         "no rostered crew → attended work is not labor-capped")

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

    def test_infeasible_pin_relaxes_instead_of_failing(self):
        # A frozen pin whose time no longer fits (the machine went down under it) must
        # NOT make the solve INFEASIBLE — the pin moves, and the count of moved pins is
        # reported. Machines run lights-out by default, so the conflict is forced with a
        # downtime event (a shift restriction wouldn't confine a 24/7 machine).
        from Tracker.models import DowntimeEvent, User
        self._wo("WO-RELAX", 1)
        first = solve_schedule(self.tenant)            # tasks land at t≈0 (frozen)
        self.assertIn(first.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        self.assertEqual(first.relaxed_pin_count, 0, "nothing to relax on the first solve")

        # Machine is down for the first 2 days — the frozen t≈0 pins can't hold.
        now = timezone.now()
        reporter = User.objects.create(
            username="dt-reporter", tenant=self.tenant, user_type='INTERNAL', is_active=True)
        DowntimeEvent.objects.create(
            tenant=self.tenant, equipment=self.machine, category='UNPLANNED',
            reason="breakdown", start_time=now, end_time=now + _td(days=2),
            reported_by=reporter)
        second = solve_schedule(self.tenant)
        self.assertIn(second.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE),
                      "soft pins keep the model solvable when the frozen plan no longer fits")
        self.assertGreaterEqual(second.relaxed_pin_count, 1,
                                "tasks that couldn't stay frozen are reported as moved")

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

    # ---- cross-WO assembly-convergence pegs ------------------------------

    def test_peg_delays_parent_until_component_done(self):
        # A component WO pegged to a parent assembly WO: the parent may not start
        # until the component job finishes.
        parent, _ = self._wo("WO-PARENT", 1)
        child, _ = self._wo("WO-CHILD", 1)
        child.pegged_to_workorder = parent
        child.save(update_fields=["pegged_to_workorder"])
        result = solve_schedule(self.tenant)
        parent_start = min(t.start_time for t in result.tasks.filter(part__work_order=parent))
        child_end = max(t.end_time for t in result.tasks.filter(part__work_order=child))
        self.assertGreaterEqual(parent_start, child_end,
                                "parent assembly can't start before the component WO finishes")

    def test_staging_buffer_adds_gap_before_parent(self):
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.create(tenant=self.tenant, staging_buffer_minutes=120)
        parent, _ = self._wo("WO-P2", 1)
        child, _ = self._wo("WO-C2", 1)
        child.pegged_to_workorder = parent
        child.save(update_fields=["pegged_to_workorder"])
        result = solve_schedule(self.tenant)
        parent_start = min(t.start_time for t in result.tasks.filter(part__work_order=parent))
        child_end = max(t.end_time for t in result.tasks.filter(part__work_order=child))
        gap_min = (parent_start - child_end).total_seconds() / 60
        self.assertGreaterEqual(gap_min, 120, "staging buffer separates component finish from parent start")

    def test_peg_gates_only_the_consuming_step(self):
        # With BOMLine.consumed_at_step set, only the assembly step waits for the
        # component — pre-assembly parent work runs in parallel with the component job.
        from Tracker.models import BOM, BOMLine
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        for step in (self.step1, self.step2):
            StepEquipmentAffinity.objects.create(
                tenant=self.tenant, step=step, equipment=m2,
                affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, revision="A", description="")
        line = BOMLine.objects.create(
            tenant=self.tenant, bom=bom, component_type=self.pt, quantity=1,
            find_number="", reference_designator="", notes="", consumed_at_step=self.step2)
        parent, _ = self._wo("WO-PARENT3", 1)
        child, _ = self._wo("WO-CHILD3", 1)
        child.pegged_to_workorder = parent
        child.pegged_to_bom_line = line
        child.save(update_fields=["pegged_to_workorder", "pegged_to_bom_line"])
        result = solve_schedule(self.tenant)
        child_end = max(t.end_time for t in result.tasks.filter(part__work_order=child))
        p_step1 = result.tasks.get(part__work_order=parent, step=self.step1)
        p_step2 = result.tasks.get(part__work_order=parent, step=self.step2)
        self.assertGreaterEqual(p_step2.start_time, child_end,
                                "the assembly step waits for the component WO")
        self.assertLess(p_step1.start_time, child_end,
                        "pre-assembly parent work is NOT gated by the component")

    # ---- reman: schedule teardown cores ----------------------------------

    def _core(self, number, step, status='IN_DISASSEMBLY'):
        from Tracker.models import Core, User
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=f"WO-{number}",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process)
        user = User.objects.create(
            username=f"op-{number}", tenant=self.tenant, user_type='INTERNAL', is_active=True)
        return Core.objects.create(
            tenant=self.tenant, core_number=number, core_type=self.pt,
            received_date=date.today(), received_by=user, condition_grade='B',
            status=status, work_order=wo, step=step)

    def test_schedules_reman_core_teardown_route(self):
        core = self._core("CORE-1", self.step1)
        result = solve_schedule(self.tenant)
        core_tasks = list(result.tasks.filter(core=core))
        self.assertEqual({t.step_id for t in core_tasks}, {self.step1.id, self.step2.id},
                         "a core schedules its remaining teardown route")
        self.assertTrue(all(t.part_id is None for t in core_tasks),
                        "core tasks carry no part")

    def test_disassembled_core_is_not_scheduled(self):
        core = self._core("CORE-DONE", self.step1, status='DISASSEMBLED')
        result = solve_schedule(self.tenant)
        self.assertEqual(result.tasks.filter(core=core).count(), 0,
                         "a fully disassembled core has no teardown work left")


class LockStepBatchTests(TenantContextMixin, TestCase):
    """Lock-step lot cohesion: the cohort's non-held parts schedule as one cohesive lot
    (one start); a part split off to rework is carved into its own lot so the cohort keeps
    progressing — the batch is NOT held for a straggler."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Lock", slug="sched-lock", tier="PRO")
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
        for st in (self.step1, self.step2):
            StepEquipmentAffinity.objects.create(
                tenant=self.tenant, step=st, equipment=self.machine,
                affinity=StepEquipmentAffinity.Affinity.PREFERRED)

    def _wo(self, erp, n_parts, lockstep=None):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n_parts, process=self.process, lockstep_batch=lockstep)
        parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                work_order=wo, step=self.step1)
            for i in range(n_parts)
        ]
        return wo, parts

    def test_cohort_progresses_with_straggler_carved_out(self):
        # A lock-step WO with one part split to rework: the batch is NOT held. The
        # cohort's non-held parts schedule (as one lot), and the split part schedules
        # as its OWN lot — everything gets planned; nothing is parked.
        wo, parts = self._wo("WO-CARVE", 3, lockstep=True)
        parts[0].split_from_lot = True   # one member off in rework
        parts[0].save(update_fields=['split_from_lot'])

        result = solve_schedule(self.tenant, time_limit_seconds=15)

        self.assertIn(result.solver_status, (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE))
        wo_tasks = ScheduledTask.objects.filter(schedule=result, part__work_order=wo)
        self.assertGreater(wo_tasks.count(), 0, "the batch is not held for a straggler")
        # All three parts are scheduled (2 cohort + 1 straggler), all present.
        scheduled_parts = {t.part_id for t in wo_tasks}
        self.assertEqual(scheduled_parts, {p.id for p in parts})

    def test_split_part_carved_into_its_own_lot(self):
        # The cohort schedules as ONE lot (shared start) at step1; the split part at the
        # same step is a SEPARATE lot, so it doesn't drag the cohort.
        wo, parts = self._wo("WO-SPLITLOT", 3, lockstep=True)
        parts[0].split_from_lot = True
        parts[0].save(update_fields=['split_from_lot'])

        result = solve_schedule(self.tenant, time_limit_seconds=15)

        s1 = list(ScheduledTask.objects.filter(
            schedule=result, part__work_order=wo, step=self.step1))
        cohort_starts = {t.start_time for t in s1 if t.part_id in {parts[1].id, parts[2].id}}
        self.assertEqual(len(cohort_starts), 1, "the 2-part cohort shares one start (one lot)")
        # The split part is its own lot — distinct (step, start) grouping from the cohort.
        lots = {(t.step_id, t.start_time) for t in s1}
        self.assertEqual(len(lots), 2, "cohort lot + carved-out straggler lot = 2 lots at step1")

    def test_intact_lockstep_cohort_starts_together(self):
        wo, parts = self._wo("WO-TOG", 3, lockstep=True)  # no split

        result = solve_schedule(self.tenant, time_limit_seconds=15)

        step1_tasks = list(ScheduledTask.objects.filter(
            schedule=result, part__work_order=wo, step=self.step1))
        self.assertEqual(len(step1_tasks), 3)
        starts = {t.start_time for t in step1_tasks}
        self.assertEqual(len(starts), 1, "one lot → all parts share a single start")


class CalendarTests(TenantContextMixin, TestCase):
    """E5 — per-machine operating calendars + plant closures (holidays/shutdowns)."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Cal", slug="sched-cal", tier="PRO")
        self.set_tenant_context(self.tenant)
        base = timezone.make_aware(datetime(2026, 9, 7, 0, 0))  # a Monday, 00:00
        self.horizon = HorizonData(start=base, end=base + _td(days=3),
                                   frozen_end=base, slushy_end=base)
        self.day = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(6, 0), end_time=dtime(14, 0), days_of_week="0,1,2,3,4,5,6")
        self.night = Shift.objects.create(
            tenant=self.tenant, name="Night", code="NGT",
            start_time=dtime(22, 0), end_time=dtime(6, 0), days_of_week="0,1,2,3,4,5,6")

    @staticmethod
    def _covered(wins, dt):
        return any(w.start <= dt < w.end for w in wins)

    @staticmethod
    def _covered_tuples(wins, dt):
        return any(s <= dt < e for s, e in wins)

    def test_per_machine_operating_calendar(self):
        # Default machine inherits the tenant calendar (Day+Night); the night machine
        # gets its OWN calendar (Night only) and is unavailable during the day.
        eq_def = Equipments.objects.create(tenant=self.tenant, name="M-Def", is_schedulable=True)
        eq_night = Equipments.objects.create(tenant=self.tenant, name="M-Night", is_schedulable=True)
        eq_night.operating_shifts.add(self.night)

        avail = sched_data.get_machine_availability(self.tenant, self.horizon)
        mon_day = timezone.make_aware(datetime(2026, 9, 7, 10, 0))   # Mon 10:00 (Day)
        tue_night = timezone.make_aware(datetime(2026, 9, 8, 2, 0))  # Tue 02:00 (Night)

        self.assertTrue(self._covered(avail[eq_def.id], mon_day))     # default runs daytime
        self.assertFalse(self._covered(avail[eq_night.id], mon_day))  # night machine does NOT
        self.assertTrue(self._covered(avail[eq_night.id], tue_night)) # but runs at night

    def test_calendar_closure_removes_working_time(self):
        # An all-day Tuesday holiday drops that day's working windows but not Monday's.
        hol = timezone.make_aware(datetime(2026, 9, 8, 0, 0))
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Holiday", start_time=hol, end_time=hol + _td(days=1))

        closures = sched_data.get_calendar_closures(self.tenant, self.horizon)
        self.assertEqual(len(closures), 1)

        wins = sched_data.get_working_windows(self.tenant, self.horizon.start, self.horizon.end)
        self.assertFalse(self._covered_tuples(
            wins, timezone.make_aware(datetime(2026, 9, 8, 10, 0))))  # Tue holiday: closed
        self.assertTrue(self._covered_tuples(
            wins, timezone.make_aware(datetime(2026, 9, 7, 10, 0))))  # Mon: still open

    def test_holiday_blocks_machine_scheduling(self):
        # A 120-min job on an attended machine must not be scheduled across a closure window.
        pt = PartTypes.objects.create(tenant=self.tenant, name="PT")
        proc = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt)
        m = Equipments.objects.create(tenant=self.tenant, name="M", is_schedulable=True,
                                      runs_unattended=False)
        st = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Op", step_type="TASK")
        ProcessStep.objects.create(process=proc, step=st, order=1)
        StepTiming.objects.create(tenant=self.tenant, step=st, cycle_time_minutes=120)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=st, equipment=m,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        Shift.objects.create(tenant=self.tenant, name="AllDay", code="ALL",
                             start_time=dtime(0, 0), end_time=dtime(23, 59),
                             days_of_week="0,1,2,3,4,5,6")
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-H", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=proc)
        Parts.objects.create(tenant=self.tenant, ERP_id="WO-H-P0", part_type=pt,
                             work_order=wo, step=st)
        now = timezone.now()
        c_start, c_end = now + _td(hours=1), now + _td(hours=3)
        PlantCalendarException.objects.create(
            tenant=self.tenant, name="Closure", start_time=c_start, end_time=c_end)

        result = solve_schedule(self.tenant, time_limit_seconds=15)
        t = ScheduledTask.objects.get(schedule=result, part__work_order=wo, step=st)
        # no overlap with the closure window
        self.assertFalse(t.start_time < c_end and c_start < t.end_time,
                         "task was scheduled across the plant closure")


class MaterialGateTests(TenantContextMixin, TestCase):
    """E2 — buy-side material availability: net BOM BUY-line demand vs on-hand stock;
    gate the consuming op on an incoming receipt, else flag a shortage."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Mat", slug="sched-mat", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="mu", email="mu@c.test", password="x", tenant=self.tenant)
        from Tracker.models import Material
        self.asm = PartTypes.objects.create(tenant=self.tenant, name="Asm")
        self.comp = Material.objects.create(tenant=self.tenant, name="Oring")
        self.proc = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.asm,
            status="APPROVED", is_current_version=True)
        self.s1 = Steps.objects.create(tenant=self.tenant, part_type=self.asm,
                                       name="Prep", step_type="TASK")
        self.s2 = Steps.objects.create(tenant=self.tenant, part_type=self.asm,
                                       name="Install", step_type="TASK")
        ProcessStep.objects.create(process=self.proc, step=self.s1, order=1)
        ProcessStep.objects.create(process=self.proc, step=self.s2, order=2)
        StepTiming.objects.create(tenant=self.tenant, step=self.s1, cycle_time_minutes=30)
        StepTiming.objects.create(tenant=self.tenant, step=self.s2, cycle_time_minutes=30)
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="M", is_schedulable=True)
        for s in (self.s1, self.s2):
            StepEquipmentAffinity.objects.create(
                tenant=self.tenant, step=s, equipment=self.machine,
                affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        self.bom = BOM.objects.create(
            tenant=self.tenant, part_type=self.asm, revision="A", bom_type="ASSEMBLY",
            status="RELEASED", is_current_version=True)

    def _buy_line(self, qty=2, allow_harvested=False):
        return BOMLine.objects.create(
            tenant=self.tenant, bom=self.bom, material=self.comp, quantity=qty,
            source="BUY", consumed_at_step=self.s2, allow_harvested=allow_harvested,
            line_number=1)

    def _lot(self, qty, status="ACCEPTED", promised=None):
        return MaterialLot.objects.create(
            tenant=self.tenant, lot_number=f"L-{qty}-{status}", material=self.comp,
            received_date=timezone.now().date(), received_by=self.user,
            quantity=qty, quantity_remaining=qty, unit_of_measure="EA",
            status=status, promised_date=promised)

    def _wo(self, q=3):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-M", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=q, process=self.proc)
        Parts.objects.create(tenant=self.tenant, ERP_id="WO-M-P0", part_type=self.asm,
                             work_order=wo, step=self.s1)
        return wo

    def test_enough_on_hand_no_gate(self):
        self._buy_line(qty=2)       # need 2×3 = 6
        self._lot(10)               # plenty accepted
        self._wo(3)
        hz = sched_data.get_schedule_horizon(self.tenant)
        rel, short, detail = sched_data.get_material_gates(self.tenant, hz)
        self.assertEqual(rel, {})
        self.assertEqual(short, set())

    def test_short_with_receipt_gates_consuming_step(self):
        self._buy_line(qty=2)       # need 6
        self._lot(1)                # only 1 on hand
        self._lot(10, status="RECEIVED", promised=(timezone.now() + _td(days=2)).date())
        wo = self._wo(3)
        hz = sched_data.get_schedule_horizon(self.tenant)
        rel, short, detail = sched_data.get_material_gates(self.tenant, hz)
        self.assertGreater(rel.get((wo.id, self.s2.id), 0), 0)
        self.assertEqual(short, set())
        # detail names the component, shortfall, and receipt date
        self.assertIn("Oring", detail[(wo.id, self.s2.id)])
        self.assertIn("due", detail[(wo.id, self.s2.id)])

    def test_short_no_receipt_flags_shortage(self):
        self._buy_line(qty=2)
        self._lot(1)                # short, no incoming
        wo = self._wo(3)
        hz = sched_data.get_schedule_horizon(self.tenant)
        rel, short, detail = sched_data.get_material_gates(self.tenant, hz)
        self.assertEqual(rel, {})
        self.assertIn((wo.id, self.s2.id), short)
        self.assertIn("no incoming receipt", detail[(wo.id, self.s2.id)])

    def test_allow_harvested_does_not_skip_newbuild(self):
        # allow_harvested only skips for REMAN (a WO with cores); a new-build WO is still gated.
        self._buy_line(qty=2, allow_harvested=True)
        self._lot(1)
        wo = self._wo(3)
        hz = sched_data.get_schedule_horizon(self.tenant)
        _, short, detail = sched_data.get_material_gates(self.tenant, hz)
        self.assertIn((wo.id, self.s2.id), short)

    def test_solve_flags_only_the_consuming_step(self):
        self._buy_line(qty=2)
        self._lot(1)                # short, no receipt
        wo = self._wo(3)
        result = solve_schedule(self.tenant, time_limit_seconds=15)
        s2t = ScheduledTask.objects.filter(schedule=result, part__work_order=wo, step=self.s2).first()
        s1t = ScheduledTask.objects.filter(schedule=result, part__work_order=wo, step=self.s1).first()
        self.assertTrue(s2t.material_shortage)
        self.assertFalse(s1t.material_shortage)
