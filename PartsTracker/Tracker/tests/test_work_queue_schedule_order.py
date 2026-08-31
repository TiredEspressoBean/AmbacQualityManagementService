"""The operator work queue follows the APS schedule when there is one.

WorkQueueViewSet ranks WO×step rows by the live schedule's planned start
(scheduled rows lead, in planned order), falling back to the priority→due→aging
heuristic for rows the solver hasn't placed. These cover both.
"""
from datetime import timedelta

from django.utils import timezone

from Tracker.models import (
    Parts, PartTypes, Processes, ScheduledTask, ScheduleResult, StepExecution,
    Steps, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class WorkQueueScheduleOrderTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        # WO-A is Normal priority; WO-B is Urgent. By the heuristic alone, B leads.
        self.wo_a = self._wo("WO-A", priority=3)
        self.wo_b = self._wo("WO-B", priority=1)
        self.part_a = self._part("A0", self.wo_a)
        self.part_b = self._part("B0", self.wo_b)
        self._open_exec(self.part_a)
        self._open_exec(self.part_b)

    def _wo(self, erp, priority):
        return WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process, priority=priority)

    def _part(self, erp, wo):
        return Parts.objects.create(
            tenant=self.tenant_a, ERP_id=erp, part_type=self.pt, work_order=wo, step=self.step)

    def _open_exec(self, part):
        return StepExecution.objects.create(
            tenant=self.tenant_a, part=part, step=self.step, status="PENDING")

    def _schedule_with(self, first_part, second_part):
        """Active schedule placing first_part's op before second_part's."""
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant_a, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_draft=False, is_stale=False)
        ScheduledTask.objects.create(
            tenant=self.tenant_a, schedule=sched, part=first_part, step=self.step,
            start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        ScheduledTask.objects.create(
            tenant=self.tenant_a, schedule=sched, part=second_part, step=self.step,
            start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4))
        return sched

    def _queue_order(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get('/api/WorkQueue/')
        self.assertEqual(r.status_code, 200, r.content)
        rows = r.data['results'] if 'results' in r.data else r.data
        return [str(row['work_order']) for row in rows]

    def test_heuristic_order_without_schedule(self):
        # No schedule: urgent WO-B leads on priority.
        order = self._queue_order()
        self.assertEqual(order, [str(self.wo_b.id), str(self.wo_a.id)])

    def test_schedule_order_overrides_heuristic(self):
        # Schedule places the Normal WO-A first; the queue must follow the plan,
        # not the priority heuristic.
        self._schedule_with(self.part_a, self.part_b)
        order = self._queue_order()
        self.assertEqual(order, [str(self.wo_a.id), str(self.wo_b.id)])

    def test_scheduled_start_exposed(self):
        self._schedule_with(self.part_a, self.part_b)
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get('/api/WorkQueue/')
        rows = r.data['results'] if 'results' in r.data else r.data
        by_wo = {str(row['work_order']): row for row in rows}
        self.assertIsNotNone(by_wo[str(self.wo_a.id)]['scheduled_start'])

    def _schedule_with_machine(self, machine):
        """Active schedule: WO-A's op assigned to `machine`, WO-B's op unassigned."""
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant_a, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_draft=False, is_stale=False)
        ScheduledTask.objects.create(
            tenant=self.tenant_a, schedule=sched, part=self.part_a, step=self.step,
            machine=machine, start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        ScheduledTask.objects.create(
            tenant=self.tenant_a, schedule=sched, part=self.part_b, step=self.step,
            start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4))
        return sched

    def test_machine_surfaced_on_row(self):
        from Tracker.models import Equipments
        machine = Equipments.objects.create(tenant=self.tenant_a, name="CNC-3", is_schedulable=True)
        self._schedule_with_machine(machine)
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get('/api/WorkQueue/')
        rows = r.data['results'] if 'results' in r.data else r.data
        by_wo = {str(row['work_order']): row for row in rows}
        self.assertEqual(by_wo[str(self.wo_a.id)]['machine_name'], "CNC-3")
        self.assertEqual(str(by_wo[str(self.wo_a.id)]['machine']), str(machine.id))
        self.assertIsNone(by_wo[str(self.wo_b.id)]['machine'])  # unassigned op

    def test_machine_filter_scopes_to_station(self):
        from Tracker.models import Equipments
        machine = Equipments.objects.create(tenant=self.tenant_a, name="CNC-3", is_schedulable=True)
        self._schedule_with_machine(machine)
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get('/api/WorkQueue/', {'machine': str(machine.id)})
        rows = r.data['results'] if 'results' in r.data else r.data
        # Only WO-A (assigned to CNC-3) — WO-B (no machine) drops out.
        self.assertEqual([str(x['work_order']) for x in rows], [str(self.wo_a.id)])
