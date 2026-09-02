"""RCCP / CTP HTTP surface.

The arithmetic is covered by `test_planning_rccp`; these pin the contract the capacity
view and the order simulator read — the response shape, and that bad query parameters
answer 400 rather than 500 (this endpoint is driven straight off user input in a form).
"""
from datetime import date, timedelta
from datetime import time as dtime

from Tracker.models import (
    Equipments, Parts, PartTypes, Processes, ProcessStep, Shift, Steps, StepTiming,
    WorkCenter, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class PlanningAPITests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.shift = Shift.objects.create(
            tenant=t, code="DAY", name="Day", start_time=dtime(8, 0),
            end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True)
        self.user_a.default_shift = self.shift
        self.user_a.save(update_fields=["default_shift"])

        self.wc = WorkCenter.objects.create(tenant=t, name="Cell A", code="A")
        self.machine = Equipments.objects.create(
            tenant=t, name="M-1", is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(self.machine)

        self.pt = PartTypes.objects.create(tenant=t, name="Widget")
        self.process = Processes.objects.create(tenant=t, name="W", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=t, part_type=self.pt, name="Cut", step_type="TASK", work_center=self.wc)
        StepTiming.objects.create(tenant=t, step=self.step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

        wo = WorkOrder.objects.create(
            tenant=t, ERP_id="WO-CAP", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=2, process=self.process,
            expected_completion=date.today() + timedelta(days=20))
        for i in range(2):
            Parts.objects.create(tenant=t, ERP_id=f"WO-CAP-P{i}", part_type=self.pt,
                                 work_order=wo, step=self.step)

    # --- capacity vs load --------------------------------------------------

    def test_capacity_load_returns_buckets_labor_and_work_centers(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/Schedules/capacity-load/?months=3")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["buckets"]), 3)
        self.assertEqual(len(r.data["labor"]["series"]), 3)
        row = r.data["labor"]["series"][0]
        self.assertIn("capacity_hours", row)
        self.assertIn("load_hours", row)
        self.assertTrue(any(w["name"] == "Cell A" for w in r.data["work_centers"]))

    def test_months_is_clamped_not_trusted(self):
        """The horizon comes from a UI control; an absurd value must clamp, not build
        a thousand buckets or blow up."""
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/Schedules/capacity-load/?months=9999")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["buckets"]), 60)

    def test_garbage_months_falls_back_to_the_default(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/Schedules/capacity-load/?months=abc")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["buckets"]), 12)

    # --- capable to promise ------------------------------------------------

    def test_ctp_quotes_a_small_order(self):
        self.authenticate_superuser(self.tenant_a)
        target = (date.today() + timedelta(days=60)).isoformat()
        r = self.client.get(
            f"/api/Schedules/capable-to-promise/?part_type={self.pt.id}"
            f"&quantity=5&target_date={target}")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["feasible"])
        self.assertEqual(r.data["quantity"], 5)
        self.assertIn("work_content_hours", r.data)

    def test_ctp_reports_the_binding_resource_when_it_does_not_fit(self):
        """An order far beyond the shop's capacity must come back infeasible AND name
        what runs out — "no" without a reason is useless to a salesperson."""
        self.authenticate_superuser(self.tenant_a)
        target = (date.today() + timedelta(days=30)).isoformat()
        r = self.client.get(
            f"/api/Schedules/capable-to-promise/?part_type={self.pt.id}"
            f"&quantity=100000&target_date={target}")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["feasible"])
        self.assertTrue(r.data["binding_resources"])

    def test_binding_resources_are_ranked_worst_shortfall_first(self):
        """An order that badly overruns the shop trips every resource; the constraint a
        planner would actually relieve has to be the one at the top of the list."""
        self.authenticate_superuser(self.tenant_a)
        target = (date.today() + timedelta(days=30)).isoformat()
        r = self.client.get(
            f"/api/Schedules/capable-to-promise/?part_type={self.pt.id}"
            f"&quantity=100000&target_date={target}")
        ratios = [
            b["need"] / b["free_through_target"] if b["free_through_target"] else float("inf")
            for b in r.data["binding_resources"]
        ]
        self.assertEqual(ratios, sorted(ratios, reverse=True))

    def test_ctp_requires_a_part_type(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/Schedules/capable-to-promise/?quantity=1"
                            "&target_date=2027-01-01")
        self.assertEqual(r.status_code, 400)

    def test_ctp_rejects_a_non_positive_quantity(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get(
            f"/api/Schedules/capable-to-promise/?part_type={self.pt.id}"
            f"&quantity=0&target_date=2027-01-01")
        self.assertEqual(r.status_code, 400)

    def test_ctp_rejects_a_malformed_date(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get(
            f"/api/Schedules/capable-to-promise/?part_type={self.pt.id}"
            f"&quantity=1&target_date=next-tuesday")
        self.assertEqual(r.status_code, 400)
