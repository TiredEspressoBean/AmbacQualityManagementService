"""The operator home's day recap and last-finished step (decision 2026-10-29)."""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import PartTypes, Parts, QualityReports, StepExecution, Steps, WorkOrder
from Tracker.tests.base import TenantTestCase


class MyDayTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-DAY", quantity=2)
        self.part = Parts.objects.create(tenant=t, ERP_id="B-1", part_type=self.pt, work_order=self.wo,
                                         step=self.step)
        self.grant_tenant_permissions(self.user_a, t, ['view_stepexecution', 'full_tenant_access'])
        self.authenticate_as(self.user_a, t)

    def _done(self, when, user=None):
        return StepExecution.objects.create(
            tenant=self.tenant_a, part=self.part, step=self.step, status="COMPLETED",
            started_at=when - timedelta(minutes=10), exited_at=when, completed_by=user or self.user_a)

    def test_counts_today_and_names_the_last_finished_step(self):
        now = timezone.now()
        self._done(now - timedelta(minutes=5))
        latest = self._done(now - timedelta(minutes=1))
        self._done(now - timedelta(days=3))                      # not today
        self._done(now - timedelta(minutes=2), user=self.user_b)  # not mine
        QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                      status="FAIL", detected_by=self.user_a, description="Burr")
        # A passing inspection isn't a flag.
        QualityReports.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                      status="PASS", detected_by=self.user_a, description="OK")
        r = self.client.get('/api/StepExecutions/my_day/')
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        # Today on the plant clock; the 5- and 1-minute-old ones are today unless the
        # run straddles plant midnight, where the older one may fall on yesterday.
        self.assertIn(body['completed_today'], (1, 2))
        self.assertEqual(body['flagged_today'], 1)
        self.assertEqual(body['last_finished']['execution_id'], str(latest.id))
        self.assertEqual(body['last_finished']['part_erp_id'], "B-1")

    def test_nothing_finished_yet(self):
        body = self.client.get('/api/StepExecutions/my_day/').json()
        self.assertEqual((body['completed_today'], body['flagged_today'], body['last_finished']),
                         (0, 0, None))


class MyFirstPiecesTests(TenantTestCase):
    """FPIRecords/mine: first pieces from my runs, open or decided today."""

    def setUp(self):
        super().setUp()
        from Tracker.models import FPIRecord
        t = self.tenant_a
        self.FPIRecord = FPIRecord
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK",
                                         requires_first_piece_inspection=True)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-FPI", quantity=2)
        self.part = Parts.objects.create(tenant=t, ERP_id="B-9", part_type=self.pt, work_order=self.wo,
                                         step=self.step)
        self.grant_tenant_permissions(self.user_a, t, ['view_fpirecord', 'full_tenant_access'])
        self.authenticate_as(self.user_a, t)

    def _fpi(self, **kw):
        return self.FPIRecord.objects.create(tenant=self.tenant_a, work_order=self.wo, step=self.step,
                                             part_type=self.pt, designated_part=self.part, **kw)

    def _mine(self):
        r = self.client.get('/api/FPIRecords/mine/')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_a_pending_first_piece_on_my_run_is_listed_with_who_saw_it(self):
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     status="IN_PROGRESS", assigned_to=self.user_a)
        fpi = self._fpi(status="PENDING", acknowledged_by=self.user_b,
                        acknowledged_at=timezone.now())
        [row] = self._mine()
        self.assertEqual((row['id'], row['status'], row['part_erp_id']), (str(fpi.id), "PENDING", "B-9"))
        self.assertTrue(row['acknowledged_by_name'])

    def test_someone_elses_run_is_not_mine(self):
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     status="IN_PROGRESS", assigned_to=self.user_b)
        self._fpi(status="PENDING")
        self.assertEqual(self._mine(), [])

    def test_decided_today_shows_and_older_verdicts_do_not(self):
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     status="COMPLETED", completed_by=self.user_a,
                                     started_at=timezone.now(), exited_at=timezone.now())
        self._fpi(status="PASSED", result="PASS", inspected_by=self.user_b, inspected_at=timezone.now())
        self._fpi(status="FAILED", result="FAIL", inspected_by=self.user_b,
                  inspected_at=timezone.now() - timedelta(days=3))
        rows = self._mine()
        self.assertEqual([r['status'] for r in rows], ["PASSED"])


class UndoStateTests(TenantTestCase):
    """last_finished.undoable: offered only while the part hasn't moved past my step."""

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Body", ID_prefix="B")
        self.turn = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.grind = Steps.objects.create(tenant=t, part_type=self.pt, name="Grind", step_type="TASK",
                                          undo_window_minutes=15, rollback_requires_approval=False)
        self.wash = Steps.objects.create(tenant=t, part_type=self.pt, name="Wash", step_type="TASK")
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-UNDO", quantity=1)
        self.part = Parts.objects.create(tenant=t, ERP_id="B-5", part_type=self.pt, work_order=self.wo,
                                         step=self.grind)
        self.grant_tenant_permissions(self.user_a, t, ['view_stepexecution', 'full_tenant_access'])
        self.authenticate_as(self.user_a, t)

    def _visit(self, step, nxt, minutes_ago, user):
        when = timezone.now() - timedelta(minutes=minutes_ago)
        return StepExecution.objects.create(
            tenant=self.tenant_a, part=self.part, step=step, status="COMPLETED", next_step=nxt,
            started_at=when - timedelta(minutes=5), exited_at=when, completed_by=user)

    def _last(self):
        return self.client.get('/api/StepExecutions/my_day/').json()['last_finished']

    def test_my_step_just_finished_is_undoable_inside_the_window(self):
        mine = self._visit(self.turn, self.grind, 2, self.user_a)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.grind,
                                     status="PENDING")
        last = self._last()
        self.assertEqual((last['execution_id'], last['step_id']), (str(mine.id), str(self.turn.id)))
        self.assertTrue(last['undoable'])
        self.assertFalse(last['undo_needs_approval'])

    def test_past_the_window_it_goes_for_approval(self):
        self._visit(self.turn, self.grind, 60, self.user_a)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.grind,
                                     status="PENDING")
        last = self._last()
        self.assertTrue(last['undoable'])
        self.assertTrue(last['undo_needs_approval'])

    def test_once_the_part_has_moved_on_it_is_not_offered(self):
        self._visit(self.turn, self.grind, 10, self.user_a)
        self._visit(self.grind, self.wash, 5, self.user_b)   # someone else finished the next step
        Parts.objects.filter(pk=self.part.pk).update(step=self.wash)
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.wash,
                                     status="PENDING")
        self.assertFalse(self._last()['undoable'])
