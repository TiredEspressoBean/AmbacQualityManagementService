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

    @staticmethod
    def _peak(tasks):
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
        # Dispatch's own operator no-overlap, in isolation: two lots overlap in time
        # (built directly, bypassing the solver's labor cap, which would otherwise
        # serialize them), and a single operator can cover only one.
        from datetime import timedelta
        from Tracker.models import ScheduleResult, ScheduledTask
        from Tracker.models.scheduling import SolverStatus
        a = self._operator("op-solo")
        wo1 = self._wo("WO-A", 1)
        wo2 = self._wo("WO-B", 1)
        m2 = self._second_machine()
        # Fixed mid-day anchor so the 60-min task stays well inside the 00:00–23:59 shift
        # (t≈now would flake near midnight).
        base = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=base, horizon_end=base + timedelta(days=1),
            solver_status=SolverStatus.OPTIMAL, is_active=True)
        for part, mach in ((wo1.parts.first(), self.machine), (wo2.parts.first(), m2)):
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=sched, part=part, step=self.step1,
                machine=mach, start_time=base, end_time=base + timedelta(minutes=60))
        summary = dispatch_operators(self.tenant, schedule=sched)
        covered = [t for t in sched.tasks.filter(step=self.step1) if t.assigned_operator_id]
        self.assertEqual(len(covered), 1, "one operator can attend only one of the overlapping lots")
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

    # -- preflight: unstaffable trained steps -------------------------------
    def test_preflight_flags_step_no_dispatchable_operator_is_trained_for(self):
        from Tracker.services.scheduling.preflight import find_unstaffable_steps
        cert = TrainingType.objects.create(tenant=self.tenant, name="Special cert")
        self._require(self.step1, cert)          # step1 gated on the cert
        self._operator("op-nocert")              # rostered, but NOT certified
        self._wo("WO-GAP", 1)
        gaps = find_unstaffable_steps(self.tenant)
        by_step = {g['step_name']: g for g in gaps}
        self.assertIn("Turn", by_step, "step1 needs a cert no dispatchable op holds")
        self.assertEqual(by_step["Turn"]['required_training'], ["Special cert"])
        self.assertNotIn("Mill", by_step, "an ungated step is never a training gap")
        # Certify + roster someone → the gap closes.
        a = self._operator("op-cert")
        self._cert(a, cert)
        self.assertNotIn("Turn", {g['step_name'] for g in find_unstaffable_steps(self.tenant)})

    def test_preflight_clean_when_requirements_are_met(self):
        from Tracker.services.scheduling.preflight import find_unstaffable_steps
        self._operator("op1")
        self._wo("WO-OK", 1)
        self.assertEqual(find_unstaffable_steps(self.tenant), [],
                         "ungated steps with a rostered operator are staffable")

    def test_solve_refuses_when_a_required_step_has_no_trained_operator(self):
        # A required-training step with nobody certified can't be executed → the solve
        # refuses rather than emitting a plan with permanently uncoverable work.
        from Tracker.services.scheduling.preflight import LaborInfeasible
        cert = TrainingType.objects.create(tenant=self.tenant, name="Rare cert")
        self._require(self.step1, cert)
        self._operator("op-nocert")     # rostered, but nobody holds the cert
        self._wo("WO-BLOCK", 1)
        with self.assertRaises(LaborInfeasible):
            solve_schedule(self.tenant)

    def test_off_labor_model_step_is_not_a_staffing_blocker(self):
        # A training-gated step set to labor_model=OFF imposes no crew constraint, so a
        # missing certification there must NOT be flagged unstaffable or refuse the solve.
        from Tracker.models import Steps
        from Tracker.services.scheduling.preflight import find_unstaffable_steps
        cert = TrainingType.objects.create(tenant=self.tenant, name="Rare cert")
        self._require(self.step1, cert)
        self._operator("op-nocert")     # rostered, nobody holds the cert
        Steps.objects.filter(id=self.step1.id).update(labor_model='off')
        self._wo("WO-OFF", 1)
        gaps = find_unstaffable_steps(self.tenant)
        self.assertNotIn("Turn", {g['step_name'] for g in gaps},
                         "an OFF step is never a staffing blocker")
        result = solve_schedule(self.tenant)  # must not raise LaborInfeasible
        self.assertIsNotNone(result)

    def test_scarce_skill_serializes_and_dispatch_covers_it(self):
        # Only ONE operator is certified for step1; three lots need it. Machine capacity
        # would allow all three in parallel, but the per-skill cap forces them one at a
        # time — so they push LATER (serialized), not pile up uncoverable. Dispatch then
        # covers every one with the single certified operator, in sequence.
        cert = TrainingType.objects.create(tenant=self.tenant, name="Turn cert")
        a = self._operator("op-turn")
        self._cert(a, cert)
        self._operator("op-b")            # rostered but not certified for step1
        self._operator("op-c")
        self._require(self.step1, cert)
        for i in (2, 3):                  # 3 machines so step1 isn't machine-bound
            m = Equipments.objects.create(tenant=self.tenant, name=f"CNC-{i}", is_schedulable=True)
            for step in (self.step1, self.step2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        for n in ("S1", "S2", "S3"):
            self._wo(n, 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1), 3)
        self.assertEqual(self._peak(s1), 1,
                         "a one-operator skill serializes step1 — never two at once")
        dispatch_operators(self.tenant, schedule=result)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertTrue(all(x.assigned_operator_id == a.id for x in s1),
                        "the one certified operator covers all three, in sequence")

    def test_continuity_post_pass_groups_same_workorder(self):
        # Two operators can each do two same-WO steps. Starting from a WO-mixed assignment
        # (X:A1,B2 ; Y:B1,A2), the coverage-preserving continuity pass should regroup so
        # each operator does one WO's consecutive lots — without dropping any coverage.
        from Tracker.services.scheduling.dispatch import _improve_continuity
        e = {'X': 0, 'Y': 0}
        lots = [
            {'s': 0, 'e': 10, 'wo': 'A', 'step': 's1', 'elig': e},   # 0 = A step1
            {'s': 20, 'e': 30, 'wo': 'A', 'step': 's2', 'elig': e},  # 1 = A step2
            {'s': 0, 'e': 10, 'wo': 'B', 'step': 's1', 'elig': e},   # 2 = B step1
            {'s': 20, 'e': 30, 'wo': 'B', 'step': 's2', 'elig': e},  # 3 = B step2
        ]
        out = _improve_continuity({0: 'X', 3: 'X', 2: 'Y', 1: 'Y'}, lots)
        self.assertEqual(set(out.keys()), {0, 1, 2, 3}, "coverage preserved")
        self.assertEqual(out[0], out[1], "one operator does both of WO A's lots")
        self.assertEqual(out[2], out[3], "the other does both of WO B's lots")
        self.assertNotEqual(out[0], out[2], "the two WOs went to different operators")

    def test_continuity_pass_never_reduces_coverage(self):
        # An infeasible swap (operator would double-book) must be rejected; every lot stays
        # covered by an eligible operator.
        from Tracker.services.scheduling.dispatch import _improve_continuity
        lots = [
            {'s': 0, 'e': 10, 'wo': 'A', 'step': 's1', 'elig': {'X': 0}},        # only X
            {'s': 5, 'e': 15, 'wo': 'A', 'step': 's1', 'elig': {'X': 0, 'Y': 0}},  # overlaps 0
        ]
        out = _improve_continuity({0: 'X', 1: 'Y'}, lots)
        self.assertEqual(len(out), 2, "both stay covered")
        self.assertEqual(out[0], 'X')
        self.assertNotEqual(out[0], out[1], "overlapping lots keep different operators")

    def test_match_operators_two_phase_produces_matched_schedule(self):
        # match_operators runs the two-phase solve (machines, then operators warm-started
        # from that layout). A scarce skill serializes and every attended lot is coverable.
        from Tracker.models import OptimizationConfig
        OptimizationConfig.objects.update_or_create(
            tenant=self.tenant, defaults={'match_operators': True})
        cert = TrainingType.objects.create(tenant=self.tenant, name="Turn cert")
        a = self._operator("op-turn")
        self._cert(a, cert)
        self._operator("op-b")
        self._require(self.step1, cert)
        for i in (2, 3):
            m = Equipments.objects.create(tenant=self.tenant, name=f"CNC-{i}", is_schedulable=True)
            for step in (self.step1, self.step2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        for n in ("S1", "S2", "S3"):
            self._wo(n, 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(len(s1), 3)
        self.assertEqual(self._peak(s1), 1, "scarce skill serialized under two-phase matching")
        dispatch_operators(self.tenant, schedule=result)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertTrue(all(x.assigned_operator_id == a.id for x in s1),
                        "every step1 lot is covered by the one certified operator")

    def test_labor_model_off_removes_the_crew_constraint(self):
        # step1 set to OFF drops the crew cap entirely — three lots run in parallel on
        # three machines even though only one operator is rostered.
        from Tracker.models import Equipments, Steps
        Steps.objects.filter(id__in=[self.step1.id, self.step2.id]).update(labor_model='off')
        self._operator("op-solo")
        for i in (2, 3):
            m = Equipments.objects.create(tenant=self.tenant, name=f"CNC-{i}", is_schedulable=True)
            for step in (self.step1, self.step2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        for n in ("O1", "O2", "O3"):
            self._wo(n, 1)
        result = solve_schedule(self.tenant)
        s1 = list(result.tasks.filter(step=self.step1))
        self.assertEqual(self._peak(s1), 3, "OFF removes the crew cap → step1 runs three-wide")

    def test_named_model_shares_one_operator_across_steps(self):
        # One operator certified for BOTH step1 and step2, both set to NAMED. Unlike POOL
        # (independent per-step caps that would let a step1 and a step2 op overlap), NAMED
        # treats the operator as a single resource, so no two of their attended ops run at
        # once — everything serializes through that one person.
        from Tracker.models import Steps
        cert = TrainingType.objects.create(tenant=self.tenant, name="Multi cert")
        a = self._operator("op-multi")
        self._cert(a, cert)
        self._require(self.step1, cert)
        self._require(self.step2, cert)
        Steps.objects.filter(id__in=[self.step1.id, self.step2.id]).update(labor_model='named')
        self._second_machine()
        self._wo("WO-N1", 1)
        self._wo("WO-N2", 1)
        result = solve_schedule(self.tenant)
        self.assertEqual(self._peak(list(result.tasks.all())), 1,
                         "one named operator serializes ALL their attended ops across steps")
