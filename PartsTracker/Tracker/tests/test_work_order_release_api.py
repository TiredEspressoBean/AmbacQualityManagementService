"""Release-gate HTTP surface.

The service tests cover the rules; these cover the contract the UI depends on — most
importantly that a blocked release comes back as **409 with the blockers attached**,
not a bare 400. The dialog's whole override flow is built on receiving that list and
re-offering with a reason, so the status code and payload shape are load-bearing.
"""
from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStep, Steps, StepTiming, WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class WorkOrderReleaseAPITests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        StepTiming.objects.create(tenant=t, step=self.step, cycle_time_minutes=60)
        self.wo = self._wo("WO-REL")

    def _wo(self, erp, process=None):
        t = self.tenant_a
        wo = WorkOrder.objects.create(
            tenant=t, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process if process is None else process)
        Parts.objects.create(tenant=t, ERP_id=f"{erp}-P0", part_type=self.pt,
                             work_order=wo, step=self.step)
        return wo

    def _url(self, wo, action):
        return f"/api/WorkOrders/{wo.id}/{action}/"

    def test_readiness_reports_ok_for_a_well_formed_order(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get(self._url(self.wo, "release_readiness"))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ok"], r.data["blockers"])
        self.assertEqual(r.data["erp_id"], "WO-REL")

    def test_release_stamps_the_work_order(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.post(self._url(self.wo, "release"), {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.data["released_at"])
        self.wo.refresh_from_db()
        self.assertIsNotNone(self.wo.released_at)

    def test_blocked_release_returns_409_with_the_blockers(self):
        """The dialog reads `blockers` off the 409 body to render the reasons and
        re-offer with an override — a 400 or an empty body breaks that flow."""
        self.authenticate_superuser(self.tenant_a)
        empty = Processes.objects.create(
            tenant=self.tenant_a, name="Empty", part_type=self.pt)
        wo = self._wo("WO-BLOCKED")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)

        r = self.client.post(self._url(wo, "release"), {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.data["blockers"])
        self.assertIn("code", r.data["blockers"][0])
        self.assertIn("detail", r.data["blockers"][0])
        wo.refresh_from_db()
        self.assertIsNone(wo.released_at)

    def test_override_reason_releases_the_blocked_order(self):
        self.authenticate_superuser(self.tenant_a)
        empty = Processes.objects.create(
            tenant=self.tenant_a, name="Empty2", part_type=self.pt)
        wo = self._wo("WO-OVR")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)

        r = self.client.post(self._url(wo, "release"),
                             {"override_reason": "routing lands Thursday"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["overridden"])
        wo.refresh_from_db()
        self.assertEqual(wo.release_override_reason, "routing lands Thursday")

    def test_unrelease_clears_the_stamp(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post(self._url(self.wo, "release"), {}, format="json")
        r = self.client.post(self._url(self.wo, "unrelease"), {}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["released_at"])

    def test_bulk_release_reports_per_order_outcomes(self):
        self.authenticate_superuser(self.tenant_a)
        good = self._wo("WO-G1")
        empty = Processes.objects.create(
            tenant=self.tenant_a, name="Empty3", part_type=self.pt)
        bad = self._wo("WO-B1")
        WorkOrder.objects.filter(pk=bad.pk).update(process=empty)

        r = self.client.post("/api/WorkOrders/bulk_release/",
                             {"ids": [str(good.id), str(bad.id)]}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data["released"], r.data["blocked"]), (1, 1))

    # --- the release queue (the "pull in work" inbox) -----------------------

    def test_release_queue_lists_unreleased_work_with_its_readiness(self):
        self.authenticate_superuser(self.tenant_a)
        r = self.client.get("/api/WorkOrders/release_queue/")
        self.assertEqual(r.status_code, 200)
        row = next(w for w in r.data["work_orders"] if w["erp_id"] == "WO-REL")
        self.assertTrue(row["ready"])
        self.assertEqual(row["open_units"], 1)
        self.assertEqual(row["blockers"], [])

    def test_release_queue_keeps_blocked_orders_visible(self):
        """A blocked order must stay in the queue, flagged — hiding it would leave the
        planner with no way to see it, let alone override it."""
        self.authenticate_superuser(self.tenant_a)
        empty = Processes.objects.create(
            tenant=self.tenant_a, name="EmptyQ", part_type=self.pt)
        wo = self._wo("WO-QBLOCKED")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)

        r = self.client.get("/api/WorkOrders/release_queue/")
        row = next(w for w in r.data["work_orders"] if w["erp_id"] == "WO-QBLOCKED")
        self.assertFalse(row["ready"])
        self.assertTrue(row["blockers"])

    def test_released_orders_leave_the_queue(self):
        self.authenticate_superuser(self.tenant_a)
        self.client.post(self._url(self.wo, "release"), {}, format="json")
        r = self.client.get("/api/WorkOrders/release_queue/")
        self.assertNotIn("WO-REL", [w["erp_id"] for w in r.data["work_orders"]])

    def test_release_fields_are_read_only_on_patch(self):
        """Release has to go through the gated endpoint — a plain PATCH that could set
        `released_at` would bypass the readiness check and the override record."""
        self.authenticate_superuser(self.tenant_a)
        r = self.client.patch(f"/api/WorkOrders/{self.wo.id}/",
                              {"released_at": "2030-01-01T00:00:00Z"}, format="json")
        self.assertIn(r.status_code, (200, 202))
        self.wo.refresh_from_db()
        self.assertIsNone(self.wo.released_at)
