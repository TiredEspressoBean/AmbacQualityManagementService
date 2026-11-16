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
            'view_workorder', 'change_workorder', 'cancel_workorder', 'clear_workorder_hold',
            'full_tenant_access'])
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


class HoldAndReleasePermissionTests(TenantTestCase):
    """User rulings 2026-11-16: clearing a hold (any kind) is clear_workorder_hold —
    leads and up — and releasing / un-releasing is release_workorder; change_workorder,
    which operators hold, carries neither. Placing a hold is unchanged."""

    def setUp(self):
        super().setUp()
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-PERM-1", quantity=1)

    def _as(self, *perms):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_workorder', 'change_workorder', 'full_tenant_access', *perms])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_change_workorder_alone_can_hold_but_not_clear_or_release(self):
        self._as()
        r = self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                             {"reason": "CUSTOMER"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        for url in (f"/api/WorkOrders/{self.wo.id}/clear_hold/",
                    f"/api/WorkOrders/{self.wo.id}/release/",
                    f"/api/WorkOrders/{self.wo.id}/unrelease/"):
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 403, url)
        self.assertEqual(self.client.post("/api/WorkOrders/bulk_release/",
                                          {"ids": [str(self.wo.id)]}, format="json").status_code, 403)

    def test_clear_hold_clears_any_kind(self):
        self._as('clear_workorder_hold')
        self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                         {"reason": "CUSTOMER"}, format="json")
        r = self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_presets_grant_them_to_leads_and_up_not_operators(self):
        from Tracker.presets import GROUP_PRESETS
        def holders(perm):
            return {p['name'] for p in GROUP_PRESETS.values()
                    if isinstance(p['permissions'], list) and perm in p['permissions']}
        self.assertEqual(holders('clear_workorder_hold'),
                         {'Tenant Admin', 'QA Manager', 'QA Inspector', 'Production Manager',
                          'Shift Lead'})
        self.assertEqual(holders('release_workorder'),
                         {'Tenant Admin', 'Planner', 'Production Manager', 'Shift Lead',
                          'Engineering'})


class SupervisedHoldClearTests(TenantTestCase):
    """User ruling 2026-11-16: someone who may change the order but not clear holds (an
    operator) clears one with a supervisor holding clear_workorder_hold signed in on
    their screen — both recorded. Bulk clear stays with the permission's holders."""

    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model
        from django.core.cache import cache
        cache.clear()   # the sign-in throttle lives in the cache, not the DB
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_workorder', 'change_workorder', 'full_tenant_access'])
        User = get_user_model()
        self.lead = User.objects.create_user(username="hold-lead", email="lead@hold.test",
                                             password="leadpass", tenant=self.tenant_a)
        self.grant_tenant_permissions(self.lead, self.tenant_a, [
            'view_workorder', 'change_workorder', 'clear_workorder_hold', 'full_tenant_access'])
        self.peer = User.objects.create_user(username="hold-peer", email="peer@hold.test",
                                             password="peerpass", tenant=self.tenant_a)
        self.grant_tenant_permissions(self.peer, self.tenant_a, [
            'view_workorder', 'change_workorder', 'full_tenant_access'])
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-SUP-1", quantity=1)
        self.authenticate_as(self.user_a, self.tenant_a)
        self.client.post(f"/api/WorkOrders/{self.wo.id}/place_on_hold/",
                         {"reason": "QUALITY"}, format="json")

    def _clear(self, **creds):
        return self.client.post(f"/api/WorkOrders/{self.wo.id}/clear_hold/",
                                {"notes": "Gauge recalibrated; suspects re-inspected.", **creds},
                                format="json")

    def _hold(self):
        from Tracker.models import WorkOrderHold
        return WorkOrderHold.objects.filter(work_order=self.wo).order_by('-placed_at').first()

    def test_an_operator_with_a_supervisor_clears_and_both_are_recorded(self):
        r = self._clear(supervisor_email="lead@hold.test", supervisor_password="leadpass")
        self.assertEqual(r.status_code, 200, r.content)
        hold = self._hold()
        self.assertEqual((hold.cleared_by_id, hold.cleared_authorized_by_id),
                         (self.user_a.id, self.lead.id))
        history = self.client.get(f"/api/WorkOrders/{self.wo.id}/").json()['hold_history']
        self.assertEqual(history[0]['cleared_authorized_by_name'], "hold-lead")

    def test_a_supervisor_who_cant_clear_holds_is_refused(self):
        r = self._clear(supervisor_email="peer@hold.test", supervisor_password="peerpass")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(r.json()['code'], 'hold_clear_not_permitted')
        self.assertIsNone(self._hold().cleared_at)

    def test_an_operator_alone_is_refused(self):
        r = self._clear()
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(r.json()['code'], 'hold_clear_needs_supervisor')
        self.assertIsNone(self._hold().cleared_at)

    def test_the_operator_cant_name_himself(self):
        self.user_a.set_password("ownpass")
        self.user_a.save()
        r = self._clear(supervisor_email=self.user_a.email, supervisor_password="ownpass")
        self.assertEqual(r.status_code, 403, r.content)
        self.assertIsNone(self._hold().cleared_at)

    def test_a_holder_clears_directly_and_bulk_stays_with_holders(self):
        r = self.client.post("/api/WorkOrders/bulk_clear_hold/",
                             {"ids": [str(self.wo.id)], "notes": "x"}, format="json")
        self.assertEqual(r.status_code, 403, r.content)
        self.authenticate_as(self.lead, self.tenant_a)
        r = self._clear()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(self._hold().cleared_authorized_by_id)
