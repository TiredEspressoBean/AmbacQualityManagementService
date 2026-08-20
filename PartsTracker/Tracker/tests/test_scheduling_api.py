"""API tests for the scheduling endpoints (Phase 4): solve, current, tasks, pin,
move, dispatch, and permission gating. Solve/dispatch are async (Celery); tests run
tasks eagerly and store the eager result so `solve_status` is pollable."""
from datetime import datetime, timedelta

from django.test import override_settings

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


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CELERY_TASK_STORE_EAGER_RESULT=True,
)
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

    @staticmethod
    def _parse(iso):
        return datetime.fromisoformat(iso.replace('Z', '+00:00'))

    def test_solve_current_and_tasks(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.post('/api/Schedules/solve/')
        self.assertEqual(r.status_code, 202, r.content)
        self.assertIn('task_id', r.data)

        # Eager: the solve ran inline; solve_status reports SUCCESS with the schedule id.
        st = self.client.get('/api/Schedules/solve_status/', {'task_id': r.data['task_id']})
        self.assertEqual(st.status_code, 200, st.content)
        self.assertEqual(st.data['state'], 'SUCCESS')
        self.assertIn(st.data['result']['solver_status'], ('OPTIMAL', 'FEASIBLE'))

        cur = self.client.get('/api/Schedules/current/')
        self.assertEqual(cur.status_code, 200)
        self.assertTrue(cur.data['is_active'])
        self.assertGreater(cur.data['task_count'], 0)

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

    def _move(self, task_id, when):
        return self.client.post(f'/api/ScheduledTasks/{task_id}/move/',
                                {'start_time': when.isoformat()}, format='json')

    def test_move_pins_and_marks_stale(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        rows = {r['step_name']: r for r in self._rows(self.client.get('/api/ScheduledTasks/').data)}
        turn_end = self._parse(rows['Turn']['end_time'])
        r = self._move(rows['Mill']['id'], turn_end + timedelta(hours=2))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data['is_pinned'])
        self.assertTrue(self.client.get('/api/Schedules/current/').data['is_stale'])

    def test_move_rejected_before_predecessor(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        rows = {r['step_name']: r for r in self._rows(self.client.get('/api/ScheduledTasks/').data)}
        turn_end = self._parse(rows['Turn']['end_time'])
        # Start Mill before its predecessor Turn finishes → refused (still inside horizon).
        r = self._move(rows['Mill']['id'], turn_end - timedelta(minutes=30))
        self.assertEqual(r.status_code, 422, r.content)
        self.assertIn('predecessor', r.data['detail'].lower())

    def test_batch_pin_and_move(self):
        self.authenticate_superuser(self.tenant_a)
        # A second part → a batch of 2 parts at the same step (no mutual precedence).
        Parts.objects.create(tenant=self.tenant_a, ERP_id="WO-API-P1", part_type=self.pt,
                             work_order=self.wo, step=self.step1)
        self.client.post('/api/Schedules/solve/')
        rows = self._rows(self.client.get('/api/ScheduledTasks/').data)
        mills = [r for r in rows if r['step_name'] == 'Mill']
        self.assertEqual(len(mills), 2)
        ids = [r['id'] for r in mills]
        turn_end = max(self._parse(r['end_time']) for r in rows if r['step_name'] == 'Turn')

        # pin_batch pins every part + marks stale.
        rp = self.client.post('/api/ScheduledTasks/pin_batch/',
                              {'task_ids': ids, 'is_pinned': True}, format='json')
        self.assertEqual(rp.status_code, 200, rp.content)
        self.assertEqual(rp.data['pinned'], 2)

        # move_batch re-anchors the Mill batch after Turn finishes (valid — no successor).
        rm = self.client.post('/api/ScheduledTasks/move_batch/',
                              {'task_ids': ids, 'start_time': (turn_end + timedelta(hours=2)).isoformat()},
                              format='json')
        self.assertEqual(rm.status_code, 200, rm.content)
        self.assertEqual(rm.data['moved'], 2)
        after = {r['id']: r for r in self._rows(self.client.get('/api/ScheduledTasks/').data)}
        for i in ids:
            self.assertTrue(after[i]['is_pinned'])
            self.assertGreaterEqual(self._parse(after[i]['start_time']), turn_end)

    def test_dispatch_returns_coverage(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post('/api/Schedules/solve/')
        r = self.client.post('/api/Schedules/dispatch/')
        self.assertEqual(r.status_code, 202, r.content)
        st = self.client.get('/api/Schedules/solve_status/', {'task_id': r.data['task_id']})
        self.assertEqual(st.data['state'], 'SUCCESS', st.content)
        self.assertIn('covered', st.data['result'])
        self.assertGreaterEqual(st.data['result']['attended'], 1)

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
