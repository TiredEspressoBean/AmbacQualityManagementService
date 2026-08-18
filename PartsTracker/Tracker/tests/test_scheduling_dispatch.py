"""Layer 2 operator dispatch — assignment over the fixed Layer-1 schedule:
capability gating, operator no-overlap, and actual-break unavailability.
"""
from datetime import time as dtime, timedelta as _td

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    Shift,
    StepEquipmentAffinity,
    Steps,
    StepTiming,
    Tenant,
    TimeEntry,
    TrainingRecord,
    TrainingRequirement,
    TrainingType,
    User,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.qms import CompetencyLevel
from Tracker.services.scheduling.dispatch import dispatch_operators
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.tests.base import TenantContextMixin


class DispatchTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Disp", slug="sched-disp", tier="PRO")
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
        # Round-the-clock shift so Layer-1 tasks (packed at t≈0) sit inside it and
        # rostered operators are on shift for them.
        self.shift = Shift.objects.create(
            tenant=self.tenant, name="Day", code="DAY",
            start_time=dtime(0, 0), end_time=dtime(23, 59),
            days_of_week="0,1,2,3,4,5,6", is_active=True)

    # -- fixtures ----------------------------------------------------------
    def _operator(self, username, shift='default'):
        """Create an internal operator. `shift` defaults to the 24/7 shift; pass
        None to leave them unrostered (not dispatchable)."""
        return User.objects.create(
            username=username, tenant=self.tenant, user_type='INTERNAL', is_active=True,
            default_shift=self.shift if shift == 'default' else shift)

    def _wo(self, erp, n_parts=1):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n_parts, process=self.process)
        for i in range(n_parts):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                work_order=wo, step=self.step1)
        return wo

    def _cert(self, user, ttype, level=CompetencyLevel.QUALIFIED):
        TrainingRecord.objects.create(
            tenant=self.tenant, user=user, training_type=ttype,
            completed_date=timezone.now().date(), level=level)

    def _require(self, step, ttype, level=CompetencyLevel.QUALIFIED):
        TrainingRequirement.objects.create(
            tenant=self.tenant, training_type=ttype, step=step, min_level=level)

    def _second_machine(self):
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step2, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        return m2

    # -- tests -------------------------------------------------------------
    def test_no_schedule_returns_none(self):
        self.assertIsNone(dispatch_operators(self.tenant))

    def test_uncertified_shop_covers_every_attended_task(self):
        # No TrainingRequirements → every operator qualifies; one operator can cover
        # a single part's two (sequential) attended tasks.
        self._operator("op-a")
        self._wo("WO-A", 1)
        result = solve_schedule(self.tenant)
        summary = dispatch_operators(self.tenant, schedule=result)
        self.assertEqual(summary.attended, 2)
        self.assertEqual(summary.covered, 2)
        self.assertEqual(summary.uncovered, 0)
        self.assertTrue(all(t.assigned_operator_id is not None
                            for t in result.tasks.all()))

    def test_capability_gate_assigns_only_qualified_operator(self):
        weld = TrainingType.objects.create(tenant=self.tenant, name="Turning cert")
        a = self._operator("op-qualified")
        self._operator("op-unqualified")
        self._cert(a, weld)
        self._require(self.step1, weld)      # step1 needs the cert; step2 is open
        self._wo("WO-CAP", 1)
        result = solve_schedule(self.tenant)
        dispatch_operators(self.tenant, schedule=result)
        s1 = result.tasks.get(step=self.step1)
        self.assertEqual(s1.assigned_operator_id, a.id,
                         "only the certified operator may take the gated step")

    def test_operator_cannot_be_in_two_places_at_once(self):
        # Two parts run step1 in parallel on two machines; a single operator can
        # cover only one — the other step1 task is left uncovered.
        self._second_machine()
        self._operator("op-solo")
        self._wo("WO-CAP2", 2)
        result = solve_schedule(self.tenant)
        summary = dispatch_operators(self.tenant, schedule=result)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1), 2)
        covered_s1 = [t for t in s1 if t.assigned_operator_id is not None]
        self.assertEqual(len(covered_s1), 1, "one operator can attend only one of the parallel tasks")
        self.assertGreaterEqual(summary.uncovered, 1)

    def test_operator_on_break_cannot_be_dispatched(self):
        # The only qualified operator is clocked out for lunch across the whole
        # horizon window → nothing they'd need to attend gets covered.
        a = self._operator("op-lunch")
        self._wo("WO-BRK", 1)
        result = solve_schedule(self.tenant)
        TimeEntry.objects.create(
            tenant=self.tenant, user=a, entry_type='LUNCH',
            start_time=result.horizon_start,
            end_time=result.horizon_start + _td(hours=3))
        summary = dispatch_operators(self.tenant, schedule=result)
        self.assertEqual(summary.covered, 0, "an operator on lunch cannot be dispatched")
        self.assertTrue(all(t.assigned_operator_id is None for t in result.tasks.all()))

    def test_requires_operator_flag_written(self):
        self._operator("op-flag")
        self._wo("WO-FLAG", 1)
        result = solve_schedule(self.tenant)
        dispatch_operators(self.tenant, schedule=result)
        self.assertTrue(all(t.requires_operator for t in result.tasks.all()),
                        "full-attention tasks require an operator")

    # -- roster (User.default_shift) --------------------------------------
    def test_unrostered_operator_is_not_dispatchable(self):
        # A qualified, active operator with no rostered shift can't be assigned.
        self._operator("op-noshift", shift=None)
        self._wo("WO-NOSHIFT", 1)
        result = solve_schedule(self.tenant)
        summary = dispatch_operators(self.tenant, schedule=result)
        self.assertEqual(summary.covered, 0)
        self.assertTrue(all(t.assigned_operator_id is None for t in result.tasks.all()))

    def test_operator_only_available_during_rostered_shift(self):
        # An 8-hour day shift never yields an availability window longer than 8h,
        # so the operator is provably not on the floor round-the-clock.
        from Tracker.services.scheduling import data
        day = Shift.objects.create(
            tenant=self.tenant, name="Days", code="DYS",
            start_time=dtime(6, 0), end_time=dtime(14, 0),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        op = self._operator("op-day", shift=day)
        horizon = data.get_schedule_horizon(self.tenant)
        windows = data.get_operator_shift_windows(self.tenant, horizon)
        self.assertIn(op.id, windows)
        longest_h = max((e - s).total_seconds() / 3600 for s, e in windows[op.id])
        self.assertLessEqual(longest_h, 8.01, "a 06:00–14:00 shift caps windows at 8h")

    def test_shift_gap_blocks_a_task_outside_the_window(self):
        # Two operators, each rostered to a non-overlapping half-day shift. Only the
        # operator whose shift covers the task's time can take it.
        from Tracker.services.scheduling import data
        horizon = data.get_schedule_horizon(self.tenant)
        # Build shifts around the horizon start so the task (t≈now) lands in one only.
        now = timezone.localtime(horizon.start)
        on = self._operator("op-onshift")           # 24/7 shift → always covers t≈0
        off_shift = Shift.objects.create(
            tenant=self.tenant, name="Graveyard", code="GRV",
            start_time=dtime((now.hour + 4) % 24, 0), end_time=dtime((now.hour + 6) % 24, 0),
            days_of_week="0,1,2,3,4,5,6", is_active=True)
        self._operator("op-offshift", shift=off_shift)
        self._wo("WO-SHIFTGAP", 1)
        result = solve_schedule(self.tenant)
        dispatch_operators(self.tenant, schedule=result)
        s1 = result.tasks.get(step=self.step1)
        self.assertEqual(s1.assigned_operator_id, on.id,
                         "only the on-shift operator can cover a task at t≈now")
