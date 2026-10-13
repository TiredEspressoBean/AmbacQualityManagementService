"""Closing a disposition happens through the `close` action, never a PATCH.

The editor used to PATCH `current_state` to CLOSED, and a later fix routed that
PATCH through `complete_disposition_resolution` so the blockers held. Since the
approval lock (2026-10-12) a decision field moves only through its action: the
PATCH is refused, and the editor saves its fields, then calls `close`.

What these tests pin:
* closing by PATCH is refused and the row stays active;
* a MAJOR disposition with no containment can't be closed by the action either;
* a valid close records `resolution_completed` + `resolution_completed_by`;
* containment saved by the editor's PATCH, then `close`, counts — the editor's
  own order;
* a non-close field edit is unaffected.
"""
from Tracker.models import (
    PartTypes, Parts, ProcessStep, Processes, QuarantineDisposition, Steps,
    WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase


class DispositionEditorCloseTests(TenantTestCase):
    def setUp(self):
        super().setUp()  # ContextVar -> tenant_a, fresh API client
        self.tenant = self.tenant_a
        self.user = self.user_a
        self.grant_tenant_permissions(
            self.user, self.tenant,
            ['full_tenant_access', 'view_quarantinedisposition',
             'change_quarantinedisposition', 'close_disposition'],
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Inspect", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CE-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-CE-1", part_type=self.pt,
            work_order=self.wo, step=self.step)
        self.authenticate_as(self.user, self.tenant)

    def _disposition(self, **overrides):
        # Type set → save() auto-transitions OPEN -> IN_PROGRESS.
        defaults = dict(
            tenant=self.tenant, part=self.part, step=self.step,
            disposition_type="REWORK", severity="MAJOR",
            description="editor close test",
        )
        defaults.update(overrides)
        return QuarantineDisposition.objects.create(**defaults)

    def _url(self, d):
        return f"/api/QuarantineDispositions/{d.id}/"

    def _patch(self, d, **body):
        return self.client.patch(self._url(d), body, format="json")

    def _close(self, d):
        return self.client.post(f"{self._url(d)}close/", {}, format="json")

    # -- the bypass is gone -------------------------------------------------

    def test_closing_by_patch_is_refused(self):
        d = self._disposition(containment_action="Segregated pending rework at Inspect.")
        resp = self._patch(d, current_state="CLOSED")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("decided through", resp.json()["detail"])
        d.refresh_from_db()
        self.assertEqual(d.current_state, "IN_PROGRESS")

    def test_major_without_containment_cannot_be_closed(self):
        d = self._disposition(containment_action="")
        resp = self._close(d)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Containment action required", str(resp.content))
        d.refresh_from_db()
        self.assertNotEqual(d.current_state, "CLOSED")
        self.assertFalse(d.resolution_completed)

    def test_valid_close_records_completion_and_attribution(self):
        d = self._disposition(containment_action="Segregated pending rework at Inspect.")
        resp = self._close(d)
        self.assertEqual(resp.status_code, 200, resp.content)
        d.refresh_from_db()
        self.assertEqual(d.current_state, "CLOSED")
        self.assertTrue(d.resolution_completed)
        self.assertEqual(d.resolution_completed_by_id, self.user.id)
        self.assertIsNotNone(d.resolution_completed_at)

    def test_containment_saved_then_close_counts(self):
        """The editor's order: save the fields, then close."""
        d = self._disposition(containment_action="")
        self.assertEqual(self._patch(d, containment_action="Segregated at Inspect; awaiting rework.")
                         .status_code, 200)
        resp = self._close(d)
        self.assertEqual(resp.status_code, 200, resp.content)
        d.refresh_from_db()
        self.assertEqual(d.current_state, "CLOSED")
        self.assertTrue(d.resolution_completed)

    def test_non_close_edit_is_unaffected(self):
        """A field edit that isn't a close transition behaves exactly as before
        — no service call, stays IN_PROGRESS."""
        d = self._disposition(containment_action="")
        resp = self._patch(d, description="updated description")
        self.assertEqual(resp.status_code, 200, resp.content)
        d.refresh_from_db()
        self.assertEqual(d.description, "updated description")
        self.assertEqual(d.current_state, "IN_PROGRESS")
        self.assertFalse(d.resolution_completed)
