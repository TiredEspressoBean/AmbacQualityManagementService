"""Gate bypass: request a StepOverride for a block the gate lets one clear, QA decides.

- The part's blockers say which ones a bypass can clear (block_type) and what's asked.
- Only the five block types the gate honours can be requested; training is the
  supervisor override at start, so TRAINING_EXPIRED is refused.
- An approved bypass stops clearing its block when it expires (the gate ignored
  expires_at, so an approval lasted forever).
"""
import datetime

from django.utils import timezone

from Tracker.models import Parts, PartTypes, StepExecution, StepOverride, Steps, WorkOrder
from Tracker.tests.base import TenantTestCase


class GateBypassTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.step = Steps.objects.create(tenant=self.tenant_a, name="Final QA", part_type=pt,
                                         requires_qa_signoff=True)
        self.wo = WorkOrder.objects.create(tenant=self.tenant_a, ERP_id="WO-BYP-1", quantity=1)
        self.part = Parts.objects.create(tenant=self.tenant_a, ERP_id="BYP-1", part_type=pt,
                                         work_order=self.wo, step=self.step, part_status="IN_PROGRESS")
        self.se = StepExecution.objects.create(
            tenant=self.tenant_a, part=self.part, step=self.step, visit_number=1, status="IN_PROGRESS",
            training_authorization={"authorized": True, "missing": [], "verified": []})
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_parts', 'view_stepoverride', 'add_stepoverride', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _blockers(self):
        resp = self.client.get(f"/api/Parts/{self.part.id}/blockers/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def _request(self, block_type="QA_SIGNOFF"):
        return self.client.post("/api/StepOverrides/", {
            "step_execution": str(self.se.id), "block_type": block_type,
            "reason": "Signer out; QA lead confirmed by phone"}, format="json")

    def _gate(self):
        return self.step.can_advance_from_step(self.se, self.wo)

    def test_the_blocker_names_the_bypass_that_clears_it(self):
        body = self._blockers()
        self.assertEqual(body["step_name"], "Final QA")
        row, = [b for b in body["blockers"] if "QA signoff" in b["message"]]
        self.assertEqual(row["block_type"], "QA_SIGNOFF")
        self.assertIsNone(row["request_status"])

    def test_a_request_shows_on_the_blocker_and_cannot_be_doubled(self):
        self.assertEqual(self._request().status_code, 201)
        row, = [b for b in self._blockers()["blockers"] if b["block_type"] == "QA_SIGNOFF"]
        self.assertEqual(row["request_status"], "PENDING")
        self.assertEqual(self._request().status_code, 400)

    def test_training_is_not_bypassed_by_request(self):
        resp = self._request("TRAINING_EXPIRED")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("supervisor", resp.content.decode())

    def test_an_approved_bypass_clears_the_block_until_it_expires(self):
        override = StepOverride.objects.create(
            tenant=self.tenant_a, step_execution=self.se, block_type="QA_SIGNOFF", reason="x",
            requested_by=self.user_a, status="APPROVED",
            expires_at=timezone.now() + datetime.timedelta(hours=4))
        ok, blockers = self._gate()
        self.assertFalse(any("QA signoff" in b for b in blockers), blockers)
        row, = [b for b in self._blockers()["blockers"] if b["block_type"] == "QA_SIGNOFF"]
        self.assertTrue(row["bypassed"])
        override.expires_at = timezone.now() - datetime.timedelta(minutes=1)
        override.save(update_fields=["expires_at"])
        ok, blockers = self._gate()
        self.assertTrue(any("QA signoff" in b for b in blockers), blockers)
