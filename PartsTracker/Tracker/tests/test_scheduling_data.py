"""Phase 1 scheduling data layer — the self-contained lookups (timings with the
fallback chain, affinities, changeover, fixtures, horizon)."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from datetime import time as dtime

from Tracker.models import (
    ContinuousMachine,
    DowntimeEvent,
    Equipments,
    Fixture,
    MeasurementDefinition,
    OptimizationConfig,
    ScheduledTask,
    ScheduleResult,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    Shift,
    StepEdge,
    StepEquipmentAffinity,
    StepExecution,
    Steps,
    StepTiming,
    Tenant,
    WorkCenterChangeover,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.scheduling import data
from Tracker.tests.base import TenantContextMixin


class SchedulingDataLayerTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Data", slug="sched-data", tier="PRO")
        self.set_tenant_context(self.tenant)
        from django.contrib.auth import get_user_model
        self.user = get_user_model().objects.create_user(
            username="op-sd", email="sd@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.machine = Equipments.objects.create(tenant=self.tenant, name="CNC-1")
        self.s_timing = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Turn", step_type="TASK")
        self.s_expected = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Mill", step_type="TASK",
            expected_duration=timedelta(minutes=12),
        )
        self.s_history = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Drill", step_type="TASK")
        self.s_none = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Deburr", step_type="TASK")

    # ---- timings + fallback chain -----------------------------------------

    def test_timing_fallback_chain(self):
        StepTiming.objects.create(
            tenant=self.tenant, step=self.s_timing, cycle_time_minutes=5, setup_minutes=8)
        # history step: two completed executions of 10 minutes each.
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-D", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-D", part_type=self.pt, work_order=wo, step=self.s_history)
        now = timezone.now()
        for i in range(2):
            ex = StepExecution.objects.create(
                tenant=self.tenant, part=part, step=self.s_history, visit_number=i + 1, status="COMPLETED")
            StepExecution.objects.filter(pk=ex.pk).update(
                entered_at=now - timedelta(minutes=10), exited_at=now)

        timings = data.get_step_timings(self.tenant, min_samples=2)
        self.assertEqual(timings[self.s_timing.id].cycle_source, 'timing')
        self.assertEqual(timings[self.s_timing.id].cycle_time_minutes, 5)
        self.assertEqual(timings[self.s_timing.id].setup_minutes, 8)
        self.assertEqual(timings[self.s_history.id].cycle_source, 'history')
        self.assertAlmostEqual(timings[self.s_history.id].cycle_time_minutes, 10, places=1)
        self.assertEqual(timings[self.s_expected.id].cycle_source, 'expected')
        self.assertEqual(timings[self.s_expected.id].cycle_time_minutes, 12)
        self.assertEqual(timings[self.s_none.id].cycle_source, 'none')
        self.assertEqual(timings[self.s_none.id].cycle_time_minutes, 0.0)

    def test_history_below_min_samples_falls_through(self):
        # One sample only, min_samples=20 → not enough → falls to expected/none.
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-D2", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-D2", part_type=self.pt, work_order=wo, step=self.s_history)
        ex = StepExecution.objects.create(
            tenant=self.tenant, part=part, step=self.s_history, visit_number=1, status="COMPLETED")
        now = timezone.now()
        StepExecution.objects.filter(pk=ex.pk).update(
            entered_at=now - timedelta(minutes=10), exited_at=now)
        timings = data.get_step_timings(self.tenant)  # default min_samples=20
        self.assertEqual(timings[self.s_history.id].cycle_source, 'none')

    # ---- affinities / changeover / fixtures / horizon ---------------------

    def test_affinities(self):
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.s_timing, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED, cycle_time_override=4.5)
        aff = data.get_step_equipment_affinities(self.tenant)
        self.assertEqual(len(aff[self.s_timing.id]), 1)
        self.assertEqual(aff[self.s_timing.id][0].equipment_id, self.machine.id)
        self.assertEqual(aff[self.s_timing.id][0].affinity, 'preferred')
        self.assertEqual(aff[self.s_timing.id][0].cycle_time_override, 4.5)

    def test_changeover_matrix(self):
        WorkCenterChangeover.objects.create(
            tenant=self.tenant, equipment=self.machine,
            from_step=self.s_timing, to_step=self.s_expected, changeover_minutes=30)
        matrix = data.get_changeover_matrix(self.tenant)
        self.assertEqual(matrix[(self.machine.id, self.s_timing.id, self.s_expected.id)], 30)

    def test_fixture_availability(self):
        f = Fixture.objects.create(tenant=self.tenant, name="Vise", quantity=2)
        f.steps.add(self.s_timing, self.s_expected)
        fixtures = data.get_fixture_availability(self.tenant)
        self.assertEqual(fixtures[f.id].quantity, 2)
        self.assertEqual(fixtures[f.id].step_ids, frozenset({self.s_timing.id, self.s_expected.id}))

    def test_horizon_uses_config_zones(self):
        OptimizationConfig.objects.create(tenant=self.tenant, frozen_zone_days=3, slushy_zone_days=5)
        h = data.get_schedule_horizon(self.tenant, horizon_days=30)
        self.assertAlmostEqual((h.end - h.start).days, 30)
        self.assertAlmostEqual((h.frozen_end - h.start).days, 3)
        self.assertAlmostEqual((h.slushy_end - h.start).days, 8)  # 3 frozen + 5 slushy

    def test_horizon_defaults_without_config(self):
        h = data.get_schedule_horizon(self.tenant)
        self.assertAlmostEqual((h.frozen_end - h.start).days, 2)
        self.assertAlmostEqual((h.slushy_end - h.start).days, 9)  # 2 + 7

    # ---- active work orders -----------------------------------------------

    def test_active_workorders_carry_parts_and_graph(self):
        ProcessStep.objects.create(process=self.process, step=self.s_timing, order=1)
        ProcessStep.objects.create(process=self.process, step=self.s_expected, order=2)
        StepEdge.objects.create(process=self.process, from_step=self.s_timing, to_step=self.s_expected)

        active = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-A", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=3, priority=5, process=self.process)
        Parts.objects.create(
            tenant=self.tenant, ERP_id="P-A", part_type=self.pt, work_order=active, step=self.s_timing)
        # A completed WO must be excluded.
        WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-DONE", workorder_status=WorkOrderStatus.COMPLETED,
            quantity=1, process=self.process)

        rows = data.get_active_workorders(self.tenant)
        self.assertEqual([r.erp_id for r in rows], ["WO-A"])
        wo = rows[0]
        self.assertEqual(wo.priority, 5)
        self.assertEqual(wo.quantity, 3)
        self.assertEqual([p.current_step_id for p in wo.parts], [self.s_timing.id])
        self.assertEqual({s.step_id for s in wo.steps}, {self.s_timing.id, self.s_expected.id})
        self.assertEqual(len(wo.edges), 1)
        self.assertEqual(wo.edges[0].from_step_id, self.s_timing.id)

    # ---- machine availability ---------------------------------------------

    def _all_week(self):
        return Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True)

    def test_machine_availability_has_windows(self):
        self._all_week()
        h = data.get_schedule_horizon(self.tenant, horizon_days=2)
        avail = data.get_machine_availability(self.tenant, h)
        self.assertIn(self.machine.id, avail)
        self.assertTrue(avail[self.machine.id], "expected at least one shift window")
        for w in avail[self.machine.id]:
            self.assertLess(w.start, w.end)

    # ---- Phase 1.5 prerequisites ------------------------------------------

    def test_timing_data_methods(self):
        from Tracker.services.scheduling.data import TimingData
        t = TimingData(step_id=self.s_timing.id, cycle_time_minutes=5, setup_minutes=8,
                       load_unload_per_piece=1, external_setup_minutes=0,
                       attention_type='full', cycle_source='timing')
        self.assertEqual(t.machine_wall_time(3), 8 + 5 * 3)   # 23
        self.assertEqual(t.first_piece_done(), 8 + 5 + 1)     # 14
        self.assertEqual(t.operator_attended_time(3), 23)     # full attention
        lu = TimingData(step_id=self.s_timing.id, cycle_time_minutes=5, setup_minutes=8,
                        load_unload_per_piece=1, external_setup_minutes=0,
                        attention_type='load_unload', cycle_source='timing')
        self.assertEqual(lu.operator_attended_time(3), 8 + 1 * 3)  # 11 (unattended run)

    def test_affinity_carries_is_schedulable(self):
        sched_eq = Equipments.objects.create(tenant=self.tenant, name="Keyence", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.s_timing, equipment=sched_eq,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.s_timing, equipment=self.machine)  # default not schedulable
        aff = {a.equipment_id: a for a in data.get_step_equipment_affinities(self.tenant)[self.s_timing.id]}
        self.assertTrue(aff[sched_eq.id].is_schedulable)
        self.assertFalse(aff[self.machine.id].is_schedulable)

    def test_step_node_carries_fpi_flag(self):
        self.s_timing.requires_first_piece_inspection = True
        self.s_timing.save(update_fields=["requires_first_piece_inspection"])
        ProcessStep.objects.create(process=self.process, step=self.s_timing, order=1)
        WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-FPI", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        nodes = {s.step_id: s for s in data.get_active_workorders(self.tenant)[0].steps}
        self.assertTrue(nodes[self.s_timing.id].requires_first_piece_inspection)

    def test_secondary_resources_only_schedulable_gauges(self):
        keyence = Equipments.objects.create(tenant=self.tenant, name="Keyence", is_schedulable=True)
        caliper = Equipments.objects.create(tenant=self.tenant, name="Caliper", is_schedulable=False)
        MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.s_timing, default_equipment=keyence, label="OD", type="NUMERIC")
        MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.s_timing, default_equipment=caliper, label="ID", type="NUMERIC")
        secondary = data.get_step_secondary_resources(self.tenant)
        self.assertEqual(secondary[self.s_timing.id], frozenset({keyence.id}))  # caliper excluded

    def test_continuous_machines(self):
        ContinuousMachine.objects.create(
            tenant=self.tenant, equipment=self.machine, parts_per_hour=120,
            bar_change_interval_hours=8, bar_change_duration_minutes=15)
        cms = data.get_continuous_machines(self.tenant)
        self.assertEqual(len(cms), 1)
        self.assertEqual(cms[0].equipment_id, self.machine.id)
        self.assertEqual(cms[0].parts_per_hour, 120)

    def test_previous_schedule(self):
        self.assertIsNone(data.get_previous_schedule(self.tenant))  # none active yet
        now = timezone.now()
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-PS", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-PS", part_type=self.pt, work_order=wo, step=self.s_timing)
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1), is_active=True)
        ScheduledTask.objects.create(
            tenant=self.tenant, schedule=sched, part=part, step=self.s_timing, machine=self.machine,
            start_time=now, end_time=now + timedelta(hours=1), is_pinned=True)
        prev = data.get_previous_schedule(self.tenant)
        self.assertIsNotNone(prev)
        self.assertEqual(len(prev.tasks), 1)
        self.assertTrue(prev.tasks[0].is_pinned)
        self.assertEqual(prev.tasks[0].machine_id, self.machine.id)

    def test_get_break_windows_expands(self):
        from datetime import datetime
        from Tracker.models import Shift
        from Tracker.services.scheduling.data import HorizonData, get_break_windows
        Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True,
            break_windows=[{"start": "12:00", "end": "12:30"}])
        start = timezone.make_aware(datetime(2026, 8, 17, 0, 0))
        horizon = HorizonData(start=start, end=start + timedelta(days=1),
                              frozen_end=start, slushy_end=start)
        breaks = get_break_windows(self.tenant, horizon)
        self.assertEqual(len(breaks), 1)
        bs, be = breaks[0]
        self.assertEqual((bs - start).total_seconds() / 60, 12 * 60)         # 12:00
        self.assertEqual((be - start).total_seconds() / 60, 12 * 60 + 30)    # 12:30

    def test_downtime_is_subtracted(self):
        self._all_week()
        h = data.get_schedule_horizon(self.tenant, horizon_days=2)
        # Downtime one hour long, an hour into the horizon.
        dt_start = h.start + timedelta(hours=1)
        dt_end = h.start + timedelta(hours=2)
        DowntimeEvent.objects.create(
            tenant=self.tenant, equipment=self.machine, category="PLANNED",
            reason="maint", start_time=dt_start, end_time=dt_end, reported_by=self.user)
        avail = data.get_machine_availability(self.tenant, h)
        # No available window may overlap the downtime interval.
        for w in avail[self.machine.id]:
            self.assertFalse(w.start < dt_end and dt_start < w.end,
                             f"window {w.start}-{w.end} overlaps downtime {dt_start}-{dt_end}")
        # Another machine with no downtime keeps the full window.
        other = Equipments.objects.create(tenant=self.tenant, name="CNC-2")
        avail2 = data.get_machine_availability(self.tenant, h)
        self.assertTrue(avail2[other.id])
