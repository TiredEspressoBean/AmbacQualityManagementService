"""In-flight work (2026-11-03): the open part visits and loads the Resume / Continue
work picker lists — the operator's own, narrowed to a work order when asked, with how
far each has got and where a load opens."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from Tracker.models import (
    BatchExecution, Parts, PartTypes, Processes, StepExecution, Steps, Substep,
    SubstepCompletion, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.in_flight import in_flight
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class InFlightTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Flight", slug="in-flight", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.me = User.objects.create_user(username="me", email="me@f.test", password="x",
                                           tenant=self.tenant, is_staff=True, is_superuser=True)
        self.other = User.objects.create_user(username="other", email="o@f.test", password="x",
                                              tenant=self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        process = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt)
        self.lap = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Lap", step_type="TASK")
        self.wash = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Wash", step_type="TASK")
        self.s1 = Substep.objects.create(tenant=self.tenant, step=self.lap, order=0, title="A")
        self.s2 = Substep.objects.create(tenant=self.tenant, step=self.lap, order=1, title="B")
        self.s3 = Substep.objects.create(tenant=self.tenant, step=self.lap, order=2, title="C")
        self.bath = Substep.objects.create(tenant=self.tenant, step=self.wash, order=0,
                                           title="Bath", scope="batch")
        self.wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-F1", process=process,
                                           workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=3)
        self.wo2 = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-F2", process=process,
                                            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1)
        self.parts = [Parts.objects.create(tenant=self.tenant, ERP_id=f"P-F{i}", part_type=pt,
                                           work_order=self.wo, step=self.lap) for i in range(3)]
        p2 = Parts.objects.create(tenant=self.tenant, ERP_id="P-G", part_type=pt,
                                  work_order=self.wo2, step=self.lap)

        # Mine, started, one substep confirmed and one drafted.
        self.mine = StepExecution.objects.create(
            tenant=self.tenant, part=self.parts[0], step=self.lap, assigned_to=self.me,
            status="IN_PROGRESS", started_at=timezone.now(),
            capture_draft={str(self.s2.id): {"n": "1"}})
        SubstepCompletion.objects.create(tenant=self.tenant, substep=self.s1,
                                         step_execution=self.mine, completed_by=self.me)
        # Someone else's, and an unassigned one waiting (the queue, not in flight).
        StepExecution.objects.create(tenant=self.tenant, part=self.parts[1], step=self.lap,
                                     assigned_to=self.other, status="IN_PROGRESS")
        StepExecution.objects.create(tenant=self.tenant, part=self.parts[2], step=self.lap)
        # Mine on another order.
        StepExecution.objects.create(tenant=self.tenant, part=p2, step=self.lap,
                                     assigned_to=self.me, status="PENDING")
        # My open load at Wash, worked from a part still at the step.
        at_wash = StepExecution.objects.create(tenant=self.tenant, part=self.parts[2], step=self.wash)
        self.at_wash = at_wash
        self.load = BatchExecution.objects.create(tenant=self.tenant, work_order=self.wo,
                                                  step=self.wash, started_by=self.me)
        self.load.parts.set([self.parts[2]])

    def test_my_open_visits_and_loads_with_progress(self):
        items = in_flight(self.tenant, user=self.me)
        self.assertEqual(sorted((i.kind, i.work_order_erp_id) for i in items),
                         [("load", "WO-F1"), ("part", "WO-F1"), ("part", "WO-F2")])
        mine = next(i for i in items if i.id == self.mine.id)
        self.assertEqual((mine.substeps_done, mine.substeps_total), (2, 3),
                         "a confirmed substep and a drafted one count as done")
        load = next(i for i in items if i.kind == "load")
        self.assertEqual((load.substeps_total, load.part_count, load.resume_execution_id),
                         (1, 1, self.at_wash.id))

    def test_a_sealed_load_stays_in_flight_running_until_completed(self):
        BatchExecution.objects.filter(pk=self.load.pk).update(sealed_at=timezone.now())
        load = next(i for i in in_flight(self.tenant, user=self.me) if i.kind == "load")
        self.assertEqual(load.status, "RUNNING")
        BatchExecution.objects.filter(pk=self.load.pk).update(completed_at=timezone.now())
        self.assertFalse([i for i in in_flight(self.tenant, user=self.me) if i.kind == "load"])

    def test_narrowed_to_a_work_order_and_everyone(self):
        self.assertEqual(len(in_flight(self.tenant, user=self.me, work_order_id=self.wo2.id)), 1)
        everyone = in_flight(self.tenant, user=self.me, everyone=True)
        self.assertEqual(sum(i.kind == "part" for i in everyone), 3, "the unassigned one is the queue")

    def test_work_whose_holder_is_off_the_clock_is_marked_and_a_break_is_not(self):
        from Tracker.models import TimeEntry
        now = timezone.now()
        # I'm on a break (the pause entry is open); the other operator clocked out.
        TimeEntry.objects.create(tenant=self.tenant, user=self.me, entry_type="BREAK", start_time=now)
        TimeEntry.objects.create(tenant=self.tenant, user=self.other, entry_type="SHIFT",
                                 start_time=now, end_time=now)
        everyone = in_flight(self.tenant, user=self.me, everyone=True)
        self.assertEqual({i.holder_name: i.holder_off_clock for i in everyone if i.kind == "part"},
                         {"me": False, "other": True})
        off = in_flight(self.tenant, user=self.me, everyone=True, off_clock=True)
        self.assertEqual([i.holder_id for i in off], [self.other.id])

    def test_the_endpoint_lists_mine(self):
        client = APIClient()
        client.force_authenticate(user=self.me)
        client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        r = client.get("/api/StepExecutions/in-flight/", {"work_order": str(self.wo.id)})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(sorted(row["kind"] for row in r.json()), ["load", "part"])
