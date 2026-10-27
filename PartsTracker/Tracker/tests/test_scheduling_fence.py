"""The hard time fence (2026-10-21).

Re-solves were measured compounding: on the same inputs a solve from scratch came out
at a 0.8% gap with 1 late order, and one on top of the live plan at 96% with 3 — the
soft frozen pins (100,000/min) protected stale positions and pushed new work late.

Now frozen and planner-pinned operations are held EXACTLY unless they can no longer
happen where they are (each such one is re-planned and reported with its reason), and
slushy ones prefer to stay put at a cost on the lateness scale.
"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    DowntimeEvent, Equipments, Parts, PartTypes, Processes, ProcessStep, ScheduledTask,
    StepEquipmentAffinity, Steps, StepTiming, Tenant, User, WorkOrder, WorkOrderPriority,
    WorkOrderStatus,
)
from Tracker.models.scheduling import SolverStatus
from Tracker.services.scheduling import data as sched_data
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.tests.base import TenantContextMixin

SOLVED = (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)


class FrozenFenceTests(TenantContextMixin, TestCase):
    """Two machines on one step pair: Turn (60 min/pc) then Mill (30 min/pc)."""

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Fence", slug="sched-fence", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Body")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.m1 = Equipments.objects.create(tenant=self.tenant, name="CNC-1", is_schedulable=True)
        self.m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        self.turn = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Turn", step_type="TASK")
        self.mill = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Mill", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.turn, order=1)
        ProcessStep.objects.create(process=self.process, step=self.mill, order=2)
        StepTiming.objects.create(tenant=self.tenant, step=self.turn, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=self.tenant, step=self.mill, cycle_time_minutes=30)
        for step in (self.turn, self.mill):
            for m in (self.m1, self.m2):
                StepEquipmentAffinity.objects.create(
                    tenant=self.tenant, step=step, equipment=m,
                    affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)

    def _wo(self, erp, n, *, due_days=10, start_days=None, priority=WorkOrderPriority.NORMAL):
        today = timezone.localdate()
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n, process=self.process, priority=priority,
            expected_completion=today + timedelta(days=due_days),
            expected_start=(today + timedelta(days=start_days)) if start_days is not None else None)
        parts = [Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-{i}", part_type=self.pt,
                                      work_order=wo, step=self.turn) for i in range(n)]
        return wo, parts

    def _solve(self, cold=False, limit=10):
        if cold:
            with mock.patch.object(sched_data, 'get_previous_schedule', return_value=None):
                return solve_schedule(self.tenant, time_limit_seconds=limit, draft=True)
        return solve_schedule(self.tenant, time_limit_seconds=limit)

    @staticmethod
    def _frozen(result):
        return {(t.part_id, t.step_id): (t.start_time, t.machine_id)
                for t in result.tasks.filter(fence_zone='frozen')}

    # --- a / b: a re-solve is as good as a fresh one, and doesn't compound ----------

    def test_a_warm_solve_matches_a_cold_one_and_the_gap_means_something(self):
        # Existing work releases after the frozen zone, so the fence holds little and a
        # new urgent order can be placed as well warm as cold.
        for i in range(3):
            self._wo(f"WO-L{i}", 2, due_days=8, start_days=3)
        first = self._solve()
        self.assertIn(first.solver_status, SOLVED)
        self._wo("WO-NEW", 2, due_days=1, priority=WorkOrderPriority.URGENT)
        cold = self._solve(cold=True)
        warm = self._solve()
        self.assertIn(warm.solver_status, SOLVED)
        self.assertLessEqual(warm.weighted_lateness, cold.weighted_lateness * 1.15 + 1)
        self.assertLess(warm.relative_gap or 0, 0.05)
        self.assertGreaterEqual(warm.stickiness_cost, 0)

    def test_b_successive_re_solves_hold_frozen_work_and_get_no_worse(self):
        for i in range(3):
            self._wo(f"WO-C{i}", 2, due_days=4)
        r1 = self._solve()
        frozen = self._frozen(r1)
        self.assertTrue(frozen, "the fixture puts work inside the frozen zone")
        lateness = [r1.weighted_lateness]
        for _ in range(2):
            r = self._solve()
            self.assertIn(r.solver_status, SOLVED)
            self.assertEqual(r.frozen_freed, [])
            for key, (start, machine) in frozen.items():
                t = r.tasks.get(part_id=key[0], step_id=key[1])
                self.assertEqual((t.start_time, t.machine_id), (start, machine), "frozen work moved")
            lateness.append(r.weighted_lateness)
        self.assertLessEqual(lateness[2], lateness[0])

    def test_b_held_work_from_different_solves_still_fits_together(self):
        """The walk that found this (2026-10-21): a re-solve 2 minutes after another
        freed every held operation as `conflict`. Held work keeps its exact time, and
        each solve counted minutes from a "now" with a seconds part — so held work from
        two solves sat on two sub-minute grids, rounded differently, and back-to-back
        operations collided. Re-solved at different seconds, it must all hold."""
        for i in range(3):
            self._wo(f"WO-G{i}", 2, due_days=4)
        base = timezone.now().replace(second=0, microsecond=0)
        results = []
        # Three solves inside one minute, at different seconds: nothing passes its
        # slot, so anything freed is the rounding, not the clock.
        for secs in (5.8, 23.9, 47.2):
            at = base + timedelta(seconds=secs)
            with mock.patch.object(timezone, 'now', return_value=at):
                results.append(solve_schedule(self.tenant, time_limit_seconds=10))
        last = results[-1]
        self.assertIn(last.solver_status, SOLVED)
        self.assertNotIn('conflict', self._freed_codes(last))
        self.assertGreater(last.frozen_kept, 0)

    # --- c: an operation is freed only when it can't happen where it is -------------

    def _held_task(self):
        self._wo("WO-H", 1, due_days=5)
        r1 = self._solve()
        return r1, r1.tasks.get(step=self.turn)

    def _freed_codes(self, result):
        return {f['reason_code'] for f in result.frozen_freed}

    def test_c_machine_out_of_service_frees_it(self):
        _, t = self._held_task()
        Equipments.objects.filter(pk=t.machine_id).update(is_schedulable=False)
        r2 = self._solve()
        self.assertIn(r2.solver_status, SOLVED)
        self.assertIn('machine_unavailable', self._freed_codes(r2))
        self.assertNotEqual(r2.tasks.get(step=self.turn).machine_id, t.machine_id)

    def test_c_machine_down_in_the_slot_frees_it(self):
        _, t = self._held_task()
        reporter = User.objects.create(username="dt", tenant=self.tenant, user_type='INTERNAL')
        DowntimeEvent.objects.create(
            tenant=self.tenant, equipment_id=t.machine_id, category='UNPLANNED', reason="breakdown",
            start_time=timezone.now() - timedelta(hours=1), end_time=timezone.now() + timedelta(days=2),
            reported_by=reporter)
        r2 = self._solve()
        self.assertIn(r2.solver_status, SOLVED)
        self.assertIn('machine_blocked', self._freed_codes(r2))
        self.assertEqual(r2.relaxed_pin_count, len(r2.frozen_freed))

    def test_c_a_slot_that_passed_unstarted_slides_instead_of_freeing(self):
        """Freeze the order, not the clock: work whose slot passed unstarted keeps its
        machine and slides to now — it doesn't lose its place to the back of the queue."""
        r1, t = self._held_task()
        ScheduledTask.objects.filter(schedule=r1).update(
            start_time=timezone.now() - timedelta(hours=3), end_time=timezone.now() - timedelta(hours=2))
        r2 = self._solve()
        self.assertNotIn('slot_past', self._freed_codes(r2))
        t2 = r2.tasks.get(step=self.turn)
        self.assertEqual(t2.machine_id, t.machine_id)
        self.assertGreaterEqual(t2.start_time, timezone.now().replace(second=0, microsecond=0))

    def test_c_passed_slots_that_cant_all_fit_now_say_the_slot_passed(self):
        """Two lots planned side by side, both slots gone by unstarted, and one operator
        on shift now: they can't both slide to "now", so one is re-planned — and the
        planner is told its slot passed unstarted, not that the crew is busy
        (user decision 2026-10-27)."""
        from Tracker.models import Shift
        from datetime import time as dtime
        self._wo("WO-SP1", 1, due_days=5)
        self._wo("WO-SP2", 1, due_days=5)
        r1 = self._solve()
        turns = list(r1.tasks.filter(step=self.turn))
        self.assertEqual(len({t.machine_id for t in turns}), 2, "the fixture runs both at once")
        shift = Shift.objects.create(
            tenant=self.tenant, name="All", code="ALL", start_time=dtime(0, 0),
            end_time=dtime(23, 59), days_of_week="0,1,2,3,4,5,6", is_active=True)
        User.objects.create(username="op-one", tenant=self.tenant, user_type='INTERNAL',
                            is_active=True, default_shift=shift)
        ScheduledTask.objects.filter(schedule=r1, step=self.turn).update(
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(hours=2))
        r2 = self._solve()
        self.assertIn(r2.solver_status, SOLVED)
        # The Turn ops are the ones whose slot passed. (A Mill op still ahead of its
        # slot that collides with work slid to "now" is genuinely crew-full.)
        turn_codes = {f['reason_code'] for f in r2.frozen_freed if f['step'] == 'Turn'}
        self.assertEqual(turn_codes, {'slot_passed'})

    def test_b_a_re_solve_after_the_minute_rolls_keeps_held_work_in_order(self):
        """The dev failure: a re-solve that crossed a minute freed work planned at "now",
        and it queued behind the whole frozen window (3x lateness). Held work now keeps
        its machine and its order and slides; nothing is freed, lateness no worse."""
        for i in range(3):
            self._wo(f"WO-R{i}", 2, due_days=4)
        base = timezone.now().replace(second=0, microsecond=0)
        with mock.patch.object(timezone, 'now', return_value=base + timedelta(seconds=10)):
            r1 = solve_schedule(self.tenant, time_limit_seconds=10)
        order = {}
        for t in r1.tasks.filter(fence_zone='frozen').order_by('start_time'):
            order.setdefault(t.machine_id, []).append((t.part_id, t.step_id))
        with mock.patch.object(timezone, 'now', return_value=base + timedelta(minutes=3, seconds=5)):
            r2 = solve_schedule(self.tenant, time_limit_seconds=10)
        self.assertEqual(r2.frozen_freed, [])
        self.assertLessEqual(r2.weighted_lateness, r1.weighted_lateness + 1)
        for machine, seq in order.items():
            later = [r2.tasks.get(part_id=p, step_id=st) for p, st in seq]
            self.assertTrue(all(x.machine_id == machine for x in later), "held work changed machine")
            starts = [x.start_time for x in later]
            self.assertEqual(starts, sorted(starts), "held work changed order on its machine")

    def test_c_an_operator_off_the_crew_frees_it(self):
        r1, t = self._held_task()
        stranger = User.objects.create(username="gone", tenant=self.tenant, user_type='INTERNAL')
        ScheduledTask.objects.filter(pk=t.pk).update(assigned_operator=stranger)
        r2 = self._solve()
        self.assertIn('operator_off_crew', self._freed_codes(r2))

    def test_c_a_held_order_is_simply_not_planned(self):
        """An order on hold isn't in the solve at all, so its old slot isn't consulted —
        nothing is reported as re-planned, and its work leaves the board."""
        wo, _ = self._wo("WO-HOLD", 1, due_days=5)
        self._solve()
        WorkOrder.objects.filter(pk=wo.pk).update(workorder_status=WorkOrderStatus.ON_HOLD)
        r2 = self._solve()
        self.assertEqual(r2.frozen_freed, [])
        self.assertFalse(r2.tasks.filter(part__work_order=wo).exists())

    # --- d: planner pins are hard; an invalid one is released -------------------

    def test_d_a_planner_pin_in_the_slushy_zone_is_kept_exactly(self):
        self._wo("WO-P", 1, due_days=12)
        r1 = self._solve()
        t = r1.tasks.get(step=self.turn)
        pinned_at = timezone.now() + timedelta(days=4, minutes=7)
        ScheduledTask.objects.filter(pk=t.pk).update(
            start_time=pinned_at, end_time=pinned_at + timedelta(hours=1), is_pinned=True)
        r2 = self._solve()
        t2 = r2.tasks.get(step=self.turn)
        self.assertTrue(t2.is_pinned)
        self.assertEqual((t2.start_time, t2.machine_id), (pinned_at, t.machine_id))

    def test_d_a_pin_that_can_no_longer_hold_is_released_and_unpinned(self):
        self._wo("WO-PX", 1, due_days=12)
        r1 = self._solve()
        t = r1.tasks.get(step=self.turn)
        ScheduledTask.objects.filter(pk=t.pk).update(is_pinned=True)
        Equipments.objects.filter(pk=t.machine_id).update(is_schedulable=False)
        r2 = self._solve()
        freed, = [f for f in r2.frozen_freed if f['step'] == 'Turn']
        self.assertTrue(freed['was_pinned'])
        self.assertFalse(r2.tasks.get(step=self.turn).is_pinned)

    # --- f: the objective split is on the result ---------------------------------

    def test_f_the_result_carries_the_fence_report_and_the_objective_split(self):
        self._wo("WO-F", 2, due_days=3)
        self._solve()
        r = self._solve()
        self.assertGreater(r.frozen_kept, 0)
        self.assertEqual(r.frozen_freed, [])
        self.assertGreaterEqual(r.stickiness_cost, 0)
        self.assertGreaterEqual(r.weighted_lateness, 0)
