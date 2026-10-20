"""Walk findings 2026-10-19.

- New work runs only a process in force: approved, not archived, not a temporary
  change's version. The new-WO picker offered a draft and the temporary version (a
  second identically-named "Injector Reman"); the server refused only the latter.
- Work doesn't start on a held or ended work order, and the refusal names the hold or
  how the order ended. Start Work was offered on both.
"""
import datetime

from django.core.exceptions import ValidationError

from Tracker.models import Parts, PartTypes, Processes, StepExecution, Steps, WorkOrder
from Tracker.services.mes.lifecycle import start_execution
from Tracker.services.mes.work_order import place_on_hold
from Tracker.tests.base import TenantTestCase


class NewWorkProcessTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.approved = Processes.objects.create(tenant=self.tenant_a, name="Injector Reman",
                                                 part_type=pt, status="APPROVED")
        self.draft = Processes.objects.create(tenant=self.tenant_a, name="Injector Reman - Draft",
                                              part_type=pt)
        self.temporary = Processes.objects.create(
            tenant=self.tenant_a, name="Injector Reman", part_type=pt, status="APPROVED",
            is_temporary=True, is_current_version=False,
            temporary_until=datetime.date(2026, 12, 31))
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_processes', 'view_workorder', 'add_workorder', 'change_workorder',
            'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _create(self, process):
        return self.client.post("/api/WorkOrders/", {
            "ERP_id": f"WO-NW-{process.pk.hex[:6]}", "quantity": 1, "process": str(process.id)},
            format="json")

    def test_the_picker_lists_only_the_version_in_force(self):
        resp = self.client.get("/api/Processes/", {"for_new_work": "true", "limit": 50})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r["id"] for r in resp.json()["results"]], [str(self.approved.id)])

    def test_new_work_on_the_approved_process_is_accepted(self):
        self.assertEqual(self._create(self.approved).status_code, 201)

    def test_new_work_on_a_draft_is_refused(self):
        resp = self._create(self.draft)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("not approved", str(resp.json()))

    def test_new_work_on_a_temporary_version_is_refused(self):
        resp = self._create(self.temporary)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("temporary change", str(resp.json()))

    def test_a_work_order_already_on_a_draft_keeps_it_on_edit(self):
        wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-NW-OLD", quantity=1,
                                      process=self.draft)
        resp = self.client.patch(f"/api/WorkOrders/{wo.id}/", {"notes": "checked"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_get_available_skips_the_temporary_version(self):
        self.assertEqual(list(Processes.get_available()), [self.approved])


class StartOnHeldOrEndedWorkOrderTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Assemble", part_type=pt)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-ST-1", quantity=1,
                                           workorder_status="IN_PROGRESS")
        part = Parts.objects.create(tenant=self.tenant_a, ERP_id="ST-1", part_type=pt,
                                    work_order=self.wo, step=self.step, part_status="IN_PROGRESS")
        self.ex = StepExecution.objects.create(tenant=self.tenant_a, part=part, step=self.step,
                                               visit_number=1, status="PENDING")

    def _start(self):
        with self.assertRaises(ValidationError) as ctx:
            start_execution(self.ex, self.user_a)
        return " ".join(ctx.exception.messages)

    def test_a_held_order_names_its_hold(self):
        place_on_hold(self.wo, reason="MATERIAL", placed_by=self.user_a, notes="Bar stock late")
        msg = self._start()
        self.assertIn("on hold", msg)
        self.assertIn("Material: Bar stock late", msg)

    def test_a_short_closed_order_says_so(self):
        WorkOrder.objects.filter(pk=self.wo.pk).update(
            workorder_status="COMPLETED", short_closed=True, short_close_reason="Customer took 3")
        self.ex.refresh_from_db()
        msg = self._start()
        self.assertIn("short-closed (Customer took 3)", msg)

    def test_a_cancelled_order_takes_no_work(self):
        WorkOrder.objects.filter(pk=self.wo.pk).update(workorder_status="CANCELLED")
        self.ex.refresh_from_db()
        self.assertIn("cancelled", self._start())

    def test_the_work_order_says_why_start_is_refused(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, ['view_workorder', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        self.assertIsNone(self.client.get(f"/api/WorkOrders/{self.wo.id}/").json()["start_refusal"])
        place_on_hold(self.wo, reason="MATERIAL", placed_by=self.user_a)
        self.assertIn("on hold", self.client.get(f"/api/WorkOrders/{self.wo.id}/").json()["start_refusal"])
