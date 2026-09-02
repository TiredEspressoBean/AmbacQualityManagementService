"""Rolling horizon — the detailed planning window.

CP-SAT plans a near-term window in detail; everything beyond it is the coarse RCCP
layer's job. These tests pin the window's edge behaviour, and in particular the one
that used to poison a whole solve: a work order releasing past the horizon.

`_release_minutes` clamps `expected_start` into [0, H], so an order releasing beyond
the window came back as `release_min == H`. The solver then holds `start >= H` while
`start`/`end` are bounded by H and the op has non-zero duration — arithmetically
impossible, so ONE far-future order made the entire tenant's schedule INFEASIBLE,
with nothing on the board and no explanation. Work outside the window is excluded
from the detailed solve instead.
"""
from datetime import time as dtime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep, Shift,
    StepEquipmentAffinity, Steps, StepTiming, Tenant, WorkCenter, WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.scheduling import data
from Tracker.tests.base import TenantContextMixin


class SchedulingHorizonTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Hz", slug="hz", tier="PRO")
        self.set_tenant_context(self.tenant)
        get_user_model().objects.create_user(
            username="hz-op", email="hz@c.test", password="x", tenant=self.tenant,
            default_shift=Shift.objects.create(
                tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
                end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True),
        )
        self.config = OptimizationConfig.objects.create(tenant=self.tenant)
        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(self.machine)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Cut", step_type="TASK",
            work_center=self.wc)
        StepTiming.objects.create(tenant=self.tenant, step=self.step, cycle_time_minutes=60)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step, equipment=self.machine,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

    def _wo(self, erp, start_offset_days=None, qty=1):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=qty, process=self.process,
            expected_completion=timezone.localdate() + timedelta(days=10),
            expected_start=(timezone.localdate() + timedelta(days=start_offset_days)
                            if start_offset_days is not None else None))
        for i in range(qty):
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}",
                                 part_type=self.pt, work_order=wo, step=self.step)
        return wo

    # --- the window itself -------------------------------------------------

    def test_horizon_length_comes_from_config(self):
        self.config.horizon_days = 60
        self.config.save(update_fields=["horizon_days"])
        h = data.get_schedule_horizon(self.tenant)
        self.assertEqual((h.end - h.start).days, 60)

    def test_horizon_defaults_to_30_days_without_config(self):
        OptimizationConfig.objects.filter(pk=self.config.pk).delete()
        h = data.get_schedule_horizon(self.tenant)
        self.assertEqual((h.end - h.start).days, 30)

    # --- the window's edge -------------------------------------------------

    def test_work_releasing_past_the_window_is_excluded_from_the_detailed_solve(self):
        """Not clamped to the window's last minute — dropped. Its capacity is the
        coarse RCCP layer's business until the window rolls far enough to reach it."""
        self._wo("WO-NEAR", start_offset_days=1)
        self._wo("WO-FAR", start_offset_days=120)
        erps = {w.erp_id for w in data.get_active_workorders(self.tenant)}
        self.assertEqual(erps, {"WO-NEAR"})

    def test_work_releasing_inside_the_window_is_kept(self):
        self._wo("WO-IN", start_offset_days=20)
        erps = {w.erp_id for w in data.get_active_workorders(self.tenant)}
        self.assertEqual(erps, {"WO-IN"})

    def test_undated_work_is_never_excluded(self):
        """No release date means "as soon as possible", not "infinitely far out"."""
        self._wo("WO-UNDATED", start_offset_days=None)
        erps = {w.erp_id for w in data.get_active_workorders(self.tenant)}
        self.assertEqual(erps, {"WO-UNDATED"})

    def test_widening_the_horizon_pulls_far_work_into_the_window(self):
        """The roll: the same order that was out of scope becomes schedulable once the
        window reaches it. This is the behaviour the roll loop automates."""
        self._wo("WO-FAR", start_offset_days=60)
        self.assertEqual(data.get_active_workorders(self.tenant), [])

        self.config.horizon_days = 90
        self.config.save(update_fields=["horizon_days"])
        erps = {w.erp_id for w in data.get_active_workorders(self.tenant)}
        self.assertEqual(erps, {"WO-FAR"})

    # --- the bug this prevents ---------------------------------------------

    def test_a_far_future_order_does_not_make_the_whole_solve_infeasible(self):
        """The regression that motivated windowing: `expected_start` clamped to H gave
        `start >= H` on an op bounded by H with non-zero duration — impossible. ONE
        far-dated order emptied the entire board with no explanation."""
        from Tracker.services.scheduling.solver import solve_schedule

        self._wo("WO-NEAR", start_offset_days=1)
        self._wo("WO-FAR", start_offset_days=365)

        result = solve_schedule(self.tenant, time_limit_seconds=10)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertGreater(result.tasks.count(), 0)
