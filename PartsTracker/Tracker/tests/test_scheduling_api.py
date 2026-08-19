"""API tests for the scheduling endpoints (Phase 4): solve, current, tasks, pin,
dispatch, and permission gating."""
from Tracker.models import (
    Equipments,
    Parts,
    PartTypes,
    Processes,
    ProcessStep,
    StepEquipmentAffinity,
    Steps,
    StepTiming,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class SchedulingAPITests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        self.machine = Equipments.objects.create(tenant=t, name="CNC-1", is_schedulable=True)
        self.step1 = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.step2 = Steps.objects.create(tenant=t, part_type=self.pt, name="Mill", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        StepTiming.objects.create(tenant=t, step=self.step1, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=t, step=self.step2, cycle_time_minutes=30)
        for step in (self.step1, self.step2):
            StepEquipmentAffinity.objects.create(
                tenant=t, step=step, equipment=self.machine,
                affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        self.wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-API", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        Parts.objects.create(tenant=t, ERP_id="WO-API-P0", part_type=self.pt,
                             work_order=self.wo, step=self.step1)

    @staticmethod
    def _rows(data):
        return data['results'] if isinstance(data, dict) and 'results' in data else data

    def test_solve_current_and_tasks(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.post('/api/Schedules/solve/')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIn(r.data['solver_status'], ('OPTIMAL', 'FEASIBLE'))
        self.assertGreater(r.data['task_count'], 0)

        cur = self.client.get('/api/Schedules/current/')
        self.assertEqual(cur.status_code, 200)
        self.assertTrue(cur.data['is_active'])

        tasks = self.client.get('/api/ScheduledTasks/')
        self.assertEqual(tasks.status_code, 200)
        rows = self._rows(tasks.data)
        self.assertGreaterEqual(len(rows), 1)
        self.assertIn('step_name', rows[0])

    def test_current_404_when_no_schedule(self):
        self.authenticate_superuser(self.tenant_a)
        self.assertEqual(self.client.get('/api/Schedules/current/').status_code, 404)

    def test_pin_marks_stale(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        rows = self._rows(self.client.get('/api/ScheduledTasks/').data)
        task_id = rows[0]['id']
        r = self.client.post(f'/api/ScheduledTasks/{task_id}/pin/',
                             {'is_pinned': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data['is_pinned'])
        self.assertTrue(self.client.get('/api/Schedules/current/').data['is_stale'])

    def test_dispatch_returns_coverage(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        r = self.client.post('/api/Schedules/dispatch/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('covered', r.data)
        self.assertGreaterEqual(r.data['attended'], 1)

    def test_solve_requires_permission(self):
        self.authenticate_as(self.user_a, self.tenant_a)   # no perms granted
        self.assertEqual(self.client.post('/api/Schedules/solve/').status_code, 403)

    def test_tenant_isolation(self):
        # tenant A solves; tenant B must not see A's tasks/schedule or pin A's task.
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        a_rows = self._rows(self.client.get('/api/ScheduledTasks/').data)
        self.assertGreaterEqual(len(a_rows), 1)
        a_task_id = a_rows[0]['id']

        self.authenticate_superuser(self.tenant_b)
        b_rows = self._rows(self.client.get('/api/ScheduledTasks/').data)
        self.assertEqual(len(b_rows), 0, "tenant B sees none of tenant A's tasks")
        self.assertEqual(self.client.get('/api/Schedules/current/').status_code, 404)
        pin = self.client.post(f'/api/ScheduledTasks/{a_task_id}/pin/',
                               {'is_pinned': True}, format='json')
        self.assertEqual(pin.status_code, 404, "can't pin another tenant's task")
