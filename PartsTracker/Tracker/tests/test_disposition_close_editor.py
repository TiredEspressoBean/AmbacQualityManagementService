"""Closing a disposition through the editor's plain PATCH is a GUARDED close.

The disposition editor is a generic form: it PATCHes `current_state` like any
other field. Before the fix, setting it to CLOSED reached a terminal state
through a bare `save()` whose only guard is pending 3D annotations — so it
skipped the containment / decision completion blockers that the dedicated
`close` action enforces, and never set `resolution_completed` /
`resolution_completed_by`. Driving it live produced `CLOSED` with
`resolution_completed=False`.

The fix converges both doors on one service: the serializer's `update()`
detects a transition to CLOSED and routes it through
`complete_disposition_resolution` (the same service the close action uses), so
the blockers are enforced and the completion fields recorded regardless of
which door you came through.

What these tests pin:
* a MAJOR disposition with no containment CANNOT be closed via the editor —
  the blocker surfaces as a 400 and the row stays active (the bypass is gone);
* a valid close records `resolution_completed=True` + `resolution_completed_by`;
* containment typed in the SAME submit as the close is honoured (the other
  field edits save before the blocker check — order matters);
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

    # -- the bypass is gone -------------------------------------------------

    def test_major_without_containment_cannot_be_closed_via_editor(self):
        """The core fix: a MAJOR with no containment is refused (400), and the
        row stays active — not a silent CLOSED that skipped the blocker."""
        d = self._disposition(containment_action="")
        resp = self._patch(d, current_state="CLOSED")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Containment action required", str(resp.content))
        d.refresh_from_db()
        self.assertNotEqual(d.current_state, "CLOSED",
                            "a blocked close must not reach the terminal state")
        self.assertFalse(d.resolution_completed)

    def test_valid_close_records_completion_and_attribution(self):
        """A close that clears the blockers goes through the service, so
        resolution_completed / _by / _at are set — not left half-written."""
        d = self._disposition(
            containment_action="Segregated pending rework at Inspect.")
        resp = self._patch(d, current_state="CLOSED")
        self.assertEqual(resp.status_code, 200, resp.content)
        d.refresh_from_db()
        self.assertEqual(d.current_state, "CLOSED")
        self.assertTrue(d.resolution_completed)
        self.assertEqual(d.resolution_completed_by_id, self.user.id)
        self.assertIsNotNone(d.resolution_completed_at)

    def test_containment_in_same_submit_as_close_is_honoured(self):
        """Order matters: the other field edits save before the blocker check,
        so containment typed in the same PATCH as the close counts."""
        d = self._disposition(containment_action="")
        resp = self._patch(
            d,
            containment_action="Segregated at Inspect; awaiting rework.",
            current_state="CLOSED",
        )
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
