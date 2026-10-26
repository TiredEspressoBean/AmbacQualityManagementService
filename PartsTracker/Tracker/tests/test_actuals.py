"""Execution-actuals capture (Tracker/services/scheduling/actuals.py).

A part/core entering or exiting a step stamps the live schedule's matching task
with the real start/end — planned-vs-actual data. Capture-only: it must NOT mark
the schedule stale (routine advances are not a re-solve trigger).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Parts, PartTypes, Processes, ScheduledTask, ScheduleResult, StepExecution,
    Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin


class ScheduleActualsCaptureTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Act", slug="actuals", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op", email="op@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-A", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-A", part_type=self.pt,
            work_order=self.wo, step=self.step)

    def _schedule(self, *, is_active=True, is_draft=False):
        now = timezone.now()
        return ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=is_active, is_draft=is_draft, is_stale=False)

    def _task(self, schedule):
        now = timezone.now()
        return ScheduledTask.objects.create(
            tenant=self.tenant, schedule=schedule, part=self.part, step=self.step,
            start_time=now, end_time=now + timedelta(hours=1))

    def _exec(self):
        return StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step)

    def test_entry_stamps_actual_start(self):
        task = self._task(self._schedule())
        se = self._exec()
        task.refresh_from_db()
        self.assertEqual(task.actual_start, se.entered_at)
        self.assertIsNone(task.actual_end)

    def test_exit_stamps_actual_end(self):
        task = self._task(self._schedule())
        se = self._exec()
        se.exited_at = timezone.now()
        se.save(update_fields=['exited_at'])
        task.refresh_from_db()
        self.assertIsNotNone(task.actual_end)
        self.assertEqual(task.actual_end, se.exited_at)

    def test_capture_does_not_mark_stale(self):
        sched = self._schedule()
        self._task(sched)
        self._exec()
        sched.refresh_from_db()
        self.assertFalse(sched.is_stale)

    def test_draft_task_not_stamped(self):
        task = self._task(self._schedule(is_active=False, is_draft=True))
        self._exec()
        task.refresh_from_db()
        self.assertIsNone(task.actual_start)

    def test_no_matching_task_is_noop(self):
        self._schedule()  # active schedule, but no task for this part+step
        self._exec()  # must not raise

    # --- plan vs actual (2026-10-26) ----------------------------------------------

    def _resolve(self, end_in_hours):
        """A re-solve: the old schedule retires; the running op is re-pinned with a new end."""
        ScheduleResult.objects.filter(tenant=self.tenant, is_active=True).update(is_active=False)
        s2 = self._schedule()
        now = timezone.now()
        t2 = ScheduledTask.objects.create(
            tenant=self.tenant, schedule=s2, part=self.part, step=self.step, in_progress=True,
            start_time=now, end_time=now + timedelta(hours=end_in_hours))
        return s2, t2

    def test_the_planned_finish_is_frozen_at_the_start_across_a_re_solve(self):
        from Tracker.services.scheduling.actuals import carry_running_actuals
        t1 = self._task(self._schedule())
        se = self._exec()
        t1.refresh_from_db()
        self.assertEqual(t1.planned_end_at_start, t1.end_time)
        s2, t2 = self._resolve(end_in_hours=5)
        carry_running_actuals(s2)
        t2.refresh_from_db()
        self.assertEqual((t2.actual_start, t2.planned_end_at_start), (se.entered_at, t1.end_time))
        se.exited_at = timezone.now()
        se.save(update_fields=['exited_at'])
        t2.refresh_from_db()
        # Judged against the plan it started on, not the re-solved end five hours out.
        self.assertEqual(t2.planned_end_at_start, t1.end_time)
        self.assertNotEqual(t2.planned_end_at_start, t2.end_time)

    def test_a_finished_op_survives_a_re_solve_in_plan_vs_actual(self):
        from Tracker.services.scheduling.adherence import adherence_ops
        self._task(self._schedule())
        se = self._exec()
        se.exited_at = timezone.now()
        se.save(update_fields=['exited_at'])
        # The re-solve books only remaining work: no task for this op any more.
        ScheduleResult.objects.filter(tenant=self.tenant, is_active=True).update(is_active=False)
        self._schedule()
        ops = adherence_ops(self.tenant)
        self.assertEqual([(o['state'], o['part_erp']) for o in ops], [('done', 'P-A')])

    def test_an_op_due_and_never_started_is_missed(self):
        from Tracker.services.scheduling.adherence import adherence_ops
        sched = self._schedule()
        past = timezone.now() - timedelta(hours=3)
        ScheduledTask.objects.create(tenant=self.tenant, schedule=sched, part=self.part, step=self.step,
                                     start_time=past, end_time=past + timedelta(hours=1))
        ops = adherence_ops(self.tenant)
        self.assertEqual([o['state'] for o in ops], ['missed'])
