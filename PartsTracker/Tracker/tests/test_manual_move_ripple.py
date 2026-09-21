"""Pushing an operation forward takes its downstream work with it.

The local guard used to REFUSE a move that finished after a successor started — which
is every forward move on a job with downstream work already scheduled. The planner's
most ordinary action was the one the board said no to.

The rule these pin: a pin is the only thing that stops a ripple, and a cascade is
undoable as one action, because nobody restores a dozen bar positions by hand.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStep, ScheduledTask, ScheduleResult,
    StepEdge, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.scheduling.edits import NothingToUndo, undo_last
from Tracker.services.scheduling.manual_move import MoveRejected, move_task
from Tracker.tests.base import TenantContextMixin


class _RippleFixture(TenantContextMixin):
    """Fixture only. A mixin rather than a base TestCase: subclassing one
    re-runs every parent test in the subclass, which is pure duplicated work
    (it ran 26 tests for 14 the first time)."""


    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="RP", slug="ripple", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="rp-planner", email="rp@c.test", password="x", tenant=self.tenant)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Build", part_type=self.pt)

        # A three-step chain: Wash -> Test -> Pack, so a ripple has somewhere to go.
        self.wash, self.test, self.pack = (
            self._step("Wash", 1), self._step("Test", 2), self._step("Pack", 3))
        for a, b in ((self.wash, self.test), (self.test, self.pack)):
            StepEdge.objects.create(process=self.process, from_step=a, to_step=b,
                                    edge_type="DEFAULT")

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-RP", quantity=1, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="WO-RP-P0", part_type=self.pt,
            work_order=self.wo, step=self.wash)

        self.t0 = timezone.now().replace(minute=0, second=0, microsecond=0)
        self.schedule = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=self.t0 - timedelta(days=1),
            horizon_end=self.t0 + timedelta(days=30), is_active=True)

        # Back-to-back hours: Wash 0-1, Test 1-2, Pack 2-3.
        self.a = self._task(self.wash, 0, 1)
        self.b = self._task(self.test, 1, 2)
        self.c = self._task(self.pack, 2, 3)

    def _step(self, name, order):
        s = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name=name,
                                 step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=s, order=order)
        return s

    def _task(self, step, start_h, end_h, pinned=False):
        return ScheduledTask.objects.create(
            tenant=self.tenant, schedule=self.schedule, step=step, part=self.part,
            start_time=self.t0 + timedelta(hours=start_h),
            end_time=self.t0 + timedelta(hours=end_h), is_pinned=pinned)

    def _hours(self, task):
        task.refresh_from_db()
        return ((task.start_time - self.t0).total_seconds() / 3600,
                (task.end_time - self.t0).total_seconds() / 3600)


class RippleForwardTests(_RippleFixture, TestCase):

    # --- the behaviour that was refused outright -----------------------------

    def test_pushing_a_step_forward_takes_its_successors_with_it(self):
        _, rippled = move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)

        self.assertEqual(len(rippled), 2)
        self.assertEqual(self._hours(self.a), (5.0, 6.0))
        self.assertEqual(self._hours(self.b), (6.0, 7.0))   # pushed off Wash's new end
        self.assertEqual(self._hours(self.c), (7.0, 8.0))   # and transitively

    def test_durations_are_preserved_through_the_cascade(self):
        """A move shifts, it does not resize — and neither does a ripple."""
        self.c.start_time = self.t0 + timedelta(hours=2)
        self.c.end_time = self.t0 + timedelta(hours=5)      # a 3-hour operation
        self.c.save()

        move_task(self.a, self.t0 + timedelta(hours=10), user=self.user)
        start, end = self._hours(self.c)
        self.assertEqual(end - start, 3.0)

    def test_a_successor_with_slack_is_left_alone(self):
        """Only what would actually overlap moves. A gap the planner left stays."""
        self.c.start_time = self.t0 + timedelta(hours=20)
        self.c.end_time = self.t0 + timedelta(hours=21)
        self.c.save()

        _, rippled = move_task(self.a, self.t0 + timedelta(hours=2), user=self.user)
        self.assertEqual([t.id for t in rippled], [self.b.id])
        self.assertEqual(self._hours(self.c), (20.0, 21.0))

    # --- a pin is the only thing that stops a ripple -------------------------

    def test_a_pinned_successor_refuses_the_move_and_names_itself(self):
        self.b.is_pinned = True
        self.b.save(update_fields=['is_pinned'])

        with self.assertRaises(MoveRejected) as ctx:
            move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        self.assertIn("Test", str(ctx.exception))
        # And nothing moved: the refusal is atomic.
        self.assertEqual(self._hours(self.a), (0.0, 1.0))
        self.assertEqual(self._hours(self.b), (1.0, 2.0))

    def test_the_moved_task_is_pinned_but_the_rippled_ones_are_not(self):
        """Rippled tasks moved as a consequence, not a decision. Pinning them would
        freeze a knock-on and stop the solver improving it."""
        move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        self.a.refresh_from_db(); self.b.refresh_from_db(); self.c.refresh_from_db()
        self.assertTrue(self.a.is_pinned)
        self.assertFalse(self.b.is_pinned)
        self.assertFalse(self.c.is_pinned)

    def test_a_predecessor_still_blocks_a_backward_move(self):
        """Rippling is forward-only. Nothing may start before what it depends on ends,
        and no amount of downstream movement changes that."""
        with self.assertRaises(MoveRejected) as ctx:
            move_task(self.c, self.t0 + timedelta(hours=0), user=self.user)
        self.assertIn("predecessor", str(ctx.exception).lower())

    def test_a_ripple_past_the_horizon_is_refused(self):
        with self.assertRaises(MoveRejected) as ctx:
            move_task(self.a, self.schedule.horizon_end - timedelta(hours=2),
                      user=self.user)
        self.assertIn("horizon", str(ctx.exception).lower())

    # --- undo ---------------------------------------------------------------

    def test_one_undo_reverses_the_whole_cascade(self):
        """The property rippling takes away, given back. A drag that moved three bars
        has to be reversible as one action."""
        move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        self.assertEqual(self._hours(self.c), (7.0, 8.0))

        result = undo_last(self.schedule, user=self.user)

        self.assertEqual(result['task_count'], 3)
        self.assertEqual(self._hours(self.a), (0.0, 1.0))
        self.assertEqual(self._hours(self.b), (1.0, 2.0))
        self.assertEqual(self._hours(self.c), (2.0, 3.0))

    def test_undo_restores_the_pin_state_too(self):
        """The move pinned the task. Undoing it has to unpin, or the board keeps a
        decision the planner just took back."""
        self.assertFalse(self.a.is_pinned)
        move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        undo_last(self.schedule, user=self.user)
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_pinned)

    def test_undo_walks_back_one_edit_at_a_time(self):
        move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        move_task(self.a, self.t0 + timedelta(hours=9), user=self.user)

        undo_last(self.schedule, user=self.user)
        self.assertEqual(self._hours(self.a), (5.0, 6.0))
        undo_last(self.schedule, user=self.user)
        self.assertEqual(self._hours(self.a), (0.0, 1.0))

    def test_undoing_with_nothing_to_undo_says_so(self):
        with self.assertRaises(NothingToUndo):
            undo_last(self.schedule, user=self.user)

    def test_an_undone_edit_is_not_undone_twice(self):
        move_task(self.a, self.t0 + timedelta(hours=5), user=self.user)
        undo_last(self.schedule, user=self.user)
        with self.assertRaises(NothingToUndo):
            undo_last(self.schedule, user=self.user)


class MachineOverlapTests(_RippleFixture, TestCase):
    """Rippling leaves resource contention to CP-SAT, which obliges us to show it."""

    def test_an_overlap_created_by_a_ripple_is_reported(self):
        from Tracker.models import Equipments
        from Tracker.services.scheduling.violations import find_machine_overlaps

        machine = Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True)
        # Two operations of this unit on ONE machine, back to back.
        for t in (self.a, self.b):
            t.machine = machine
            t.save(update_fields=['machine'])

        self.assertEqual(find_machine_overlaps(self.schedule), [])

        # Force an overlap the way contention actually arises: pin the successor in
        # place, then hand-place the predecessor on top of it.
        self.b.start_time = self.t0 + timedelta(hours=1)
        self.b.end_time = self.t0 + timedelta(hours=4)
        self.b.save(update_fields=['start_time', 'end_time'])
        self.a.start_time = self.t0 + timedelta(hours=2)
        self.a.end_time = self.t0 + timedelta(hours=3)
        self.a.save(update_fields=['start_time', 'end_time'])

        overlaps = find_machine_overlaps(self.schedule)
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(set(overlaps[0]['tasks']), {str(self.a.id), str(self.b.id)})
        self.assertEqual(overlaps[0]['machine_name'], "M-1")

    def test_tasks_without_a_machine_cannot_contend(self):
        from Tracker.services.scheduling.violations import find_machine_overlaps
        self.assertEqual(find_machine_overlaps(self.schedule), [])
