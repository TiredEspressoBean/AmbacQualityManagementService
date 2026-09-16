"""`?overdue=true` on the CAPA and CAPA-task lists.

Both viewsets used to evaluate overdue-ness in Python -- pulling every row,
calling a model method, then re-querying by id. On CapaTasks that method did
not exist (the model has `check_overdue()`, returning a tuple), so the filter
raised AttributeError and returned 500 for every caller. It is declared in the
schema, so the generated client offered a parameter that could only fail.

Both are SQL expressions now. These tests pin the rule each one encodes, since
"overdue" is defined in two places and they have already drifted apart once.
"""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import CAPA, CapaStatus, CapaTasks, CapaTaskStatus
from Tracker.tests.base import TenantTestCase


class OverdueFilterTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        today = timezone.now().date()
        past, future = today - timedelta(days=5), today + timedelta(days=5)

        # One of each case the rule has to separate.
        self.overdue = CAPA.objects.create(
            tenant=t, capa_type='CORRECTIVE', problem_statement='overdue',
            status=CapaStatus.OPEN, due_date=past,
        )
        self.not_due = CAPA.objects.create(
            tenant=t, capa_type='CORRECTIVE', problem_statement='not due',
            status=CapaStatus.OPEN, due_date=future,
        )
        self.closed_past_due = CAPA.objects.create(
            tenant=t, capa_type='CORRECTIVE', problem_statement='closed',
            status=CapaStatus.CLOSED, due_date=past,
        )
        self.no_due_date = CAPA.objects.create(
            tenant=t, capa_type='CORRECTIVE', problem_statement='no due date',
            status=CapaStatus.OPEN, due_date=None,
        )

        self.task_overdue = CapaTasks.objects.create(
            tenant=t, capa=self.overdue, task_type='CORRECTIVE',
            description='overdue task', status='OPEN', due_date=past,
        )
        self.task_completed = CapaTasks.objects.create(
            tenant=t, capa=self.overdue, task_type='CORRECTIVE',
            description='done task', status=CapaTaskStatus.COMPLETED, due_date=past,
        )
        self.task_no_due = CapaTasks.objects.create(
            tenant=t, capa=self.overdue, task_type='CORRECTIVE',
            description='no due date', status='OPEN', due_date=None,
        )

        self.authenticate_as(self.user_a, self.tenant_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_capa', 'view_capatasks', 'full_tenant_access',
        ])

    def _ids(self, url):
        res = self.client.get(url, {'overdue': 'true'})
        self.assertEqual(res.status_code, 200, getattr(res, 'data', res))
        return {r['id'] for r in res.data['results']}

    def test_capa_tasks_overdue_does_not_500(self):
        """The regression: this raised AttributeError and returned 500."""
        ids = self._ids('/api/CapaTasks/')
        self.assertIn(str(self.task_overdue.id), ids)

    def test_capa_tasks_overdue_excludes_completed_and_undated(self):
        ids = self._ids('/api/CapaTasks/')
        self.assertNotIn(str(self.task_completed.id), ids,
                         "a COMPLETED task is never overdue")
        self.assertNotIn(str(self.task_no_due.id), ids,
                         "a task with no due date is never overdue")

    def test_capa_overdue_matches_is_overdue(self):
        ids = self._ids('/api/CAPAs/')
        self.assertIn(str(self.overdue.id), ids)
        self.assertNotIn(str(self.not_due.id), ids)
        self.assertNotIn(str(self.closed_past_due.id), ids,
                         "a CLOSED CAPA is never overdue")
        self.assertNotIn(str(self.no_due_date.id), ids,
                         "a CAPA with no due date is never overdue")

    def test_capa_sql_filter_agrees_with_the_model_method(self):
        """The SQL rule and CAPA.is_overdue() must not drift apart."""
        ids = self._ids('/api/CAPAs/')
        for capa in CAPA.objects.filter(tenant=self.tenant_a):
            self.assertEqual(
                str(capa.id) in ids, capa.is_overdue(),
                f"{capa.problem_statement}: filter and is_overdue() disagree",
            )
