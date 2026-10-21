"""A work order's status isn't a field you edit.

PATCH /api/WorkOrders/{id}/ wrote any workorder_status: Completed with parts in
progress, In progress with nothing started, On hold with no reason. Each legal move
now has its action (hold, clear hold, cancel) and the derived ones follow the work.
"""
from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStep, StepExecution, Steps, WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class WorkOrderStatusGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_workorder', 'change_workorder', 'cancel_workorder', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Shaft")
        process = Processes.objects.create(tenant=self.tenant_a, name="P", part_type=pt)
        self.step = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Turn",
                                         step_type="TASK")
        ProcessStep.objects.create(process=process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant_a, ERP_id="WO-GATE-1", quantity=1, process=process,
            workorder_status=WorkOrderStatus.PENDING)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="G-1", part_type=pt,
                                         work_order=self.wo, step=self.step)

    def _patch(self, status):
        return self.client.patch(f"/api/WorkOrders/{self.wo.id}/",
                                 {"workorder_status": status}, format="json")

    def _status(self):
        self.wo.refresh_from_db()
        return self.wo.workorder_status

    def test_each_hand_set_status_is_refused_with_its_move_named(self):
        for target, says in [
            (WorkOrderStatus.ON_HOLD, "on hold, with a reason"),
            (WorkOrderStatus.CANCELLED, "use Cancel"),
            (WorkOrderStatus.COMPLETED, "every part finishing"),
            (WorkOrderStatus.IN_PROGRESS, "first work started"),
        ]:
            resp = self._patch(target)
            self.assertEqual(resp.status_code, 400, (target, resp.content))
            self.assertIn(says, str(resp.json()["workorder_status"]), target)
        self.assertEqual(self._status(), WorkOrderStatus.PENDING)

    def test_an_edit_that_leaves_status_alone_still_saves(self):
        resp = self.client.patch(f"/api/WorkOrders/{self.wo.id}/",
                                 {"workorder_status": "PENDING", "notes": "rush"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    def test_clearing_a_hold_returns_an_unstarted_order_to_pending(self):
        self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                         {"reason": "MATERIAL"}, format="json")
        self.assertEqual(self._status(), WorkOrderStatus.ON_HOLD)
        resp = self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self._status(), WorkOrderStatus.PENDING)

    def test_clearing_a_hold_returns_a_started_order_to_in_progress(self):
        StepExecution.objects.create(tenant=self.tenant_a, part=self.part, step=self.step,
                                     visit_number=1, status="IN_PROGRESS")
        self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                         {"reason": "TOOLING"}, format="json")
        self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/",
                         {"notes": "Fixture re-shimmed"}, format="json")
        self.assertEqual(self._status(), WorkOrderStatus.IN_PROGRESS)

    def test_a_quality_or_tooling_hold_needs_a_resolution_note(self):
        """User decision 2026-10-21: required for Quality and Tooling, optional otherwise."""
        from Tracker.models import WorkOrderHold
        for reason in ("QUALITY", "TOOLING"):
            self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                             {"reason": reason}, format="json")
            resp = self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/", {}, format="json")
            self.assertEqual(resp.status_code, 400, resp.content)
            self.assertIn("resolution note", resp.data["detail"])
            self.assertEqual(self._status(), WorkOrderStatus.ON_HOLD)
            resp = self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/",
                                    {"notes": "Gauge recalibrated; suspects re-inspected"}, format="json")
            self.assertEqual(resp.status_code, 200, resp.content)
        latest = WorkOrderHold.objects.filter(work_order=self.wo).order_by("-cleared_at").first()
        self.assertEqual(latest.clear_notes, "Gauge recalibrated; suspects re-inspected")

    def test_bulk_clear_refuses_a_quality_hold_without_a_note_on_its_own_row(self):
        self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                         {"reason": "QUALITY"}, format="json")
        resp = self.client.post("/api/WorkOrders/bulk_clear_hold/", {"ids": [str(self.wo.id)]},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        row, = resp.data["results"]
        self.assertFalse(row["ok"])
        self.assertEqual(self._status(), WorkOrderStatus.ON_HOLD)

    def test_cancel_is_its_own_action(self):
        resp = self.client.post(f"/api/WorkOrders/{self.wo.id}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(self._status(), WorkOrderStatus.CANCELLED)
        again = self.client.post(f"/api/WorkOrders/{self.wo.id}/cancel/", {}, format="json")
        self.assertEqual(again.status_code, 400)


class BulkHoldPermissionTests(TenantTestCase):
    """The Control Center's bulk Hold / Clear hold fell back to add_workorder, which
    every staff role holds — now change_workorder, like the single-order actions."""

    def setUp(self):
        super().setUp()
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_workorder', 'add_workorder', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-BULK-1", quantity=1)

    def test_an_add_only_role_cannot_bulk_hold(self):
        resp = self.client.post("/api/WorkOrders/bulk_place_on_hold/",
                                {"ids": [str(self.wo.id)], "reason": "MATERIAL"}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_an_add_only_role_cannot_bulk_clear_a_hold(self):
        resp = self.client.post("/api/WorkOrders/bulk_clear_hold/",
                                {"ids": [str(self.wo.id)]}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_an_add_only_role_cannot_hold_one_order(self):
        resp = self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                                {"reason": "MATERIAL"}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
