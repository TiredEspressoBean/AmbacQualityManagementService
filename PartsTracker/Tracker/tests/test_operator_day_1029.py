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
