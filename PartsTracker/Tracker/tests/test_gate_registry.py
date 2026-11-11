"""The gate registry (services/mes/gates.py), user decisions 2026-11-11.

- Every start path runs the one start decision: PATCH to IN_PROGRESS runs the floor
  (it ran competence only), and starting a load runs it for every member and starts
  their visits for the load's holder (it ran no start checks).
- A refusal carries its stable code, who clears it and what the floor waits on.
- A bypass clears the gate it names by CODE: a substep titled "Measurement check" is
  not cleared by a measurement bypass (message matching did that).
- Work isn't recorded on a visit nobody started.
- An expired deviation refuses a start, not the finish of work started inside it.
- Passed and escaped gates are logged, one row per visit per gate per stage.
"""
import datetime
from unittest import mock

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    BatchExecution, GateDecision, Parts, PartTypes, StepExecution, StepOverride, Steps,
    Substep, WorkOrder,
)
from Tracker.services.mes.gates import (
    Blocker, GateCode, StartContext, floor_blockers, record_release,
)
from Tracker.tests.base import TenantTestCase


class GateRegistryTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.step = Steps.objects.create(tenant=t, name="Wash", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-GATE-1", quantity=2,
                                           workorder_status="IN_PROGRESS")
        self.parts = [Parts.objects.create(tenant=t, ERP_id=f"GATE-{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step,
                                           part_status="IN_PROGRESS") for i in range(2)]
        self.visits = [StepExecution.objects.create(tenant=t, part=p, step=self.step,
                                                    visit_number=1, status="PENDING")
                       for p in self.parts]
        self.authenticate_superuser(tenant=t)

    def _hold(self):
        WorkOrder.objects.filter(pk=self.wo.pk).update(workorder_status="ON_HOLD")
        self.wo.refresh_from_db()

    # --- PATCH -----------------------------------------------------------------

    def test_patch_to_in_progress_runs_the_floor(self):
        self._hold()
        resp = self.client.patch(f"/api/StepExecutions/{self.visits[0].id}/",
                                 {"status": "IN_PROGRESS"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "work_order_not_workable")
        blocker, = body["blockers"]
        self.assertEqual(blocker["clears"], "Production manager")
        self.assertIn("on hold", blocker["message"])
        self.visits[0].refresh_from_db()
        self.assertEqual(self.visits[0].status, "PENDING")

    def test_a_patched_start_is_logged(self):
        resp = self.client.patch(f"/api/StepExecutions/{self.visits[0].id}/",
                                 {"status": "IN_PROGRESS"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        gates = set(GateDecision.objects.filter(step_execution=self.visits[0], stage="START")
                    .values_list("gate", "outcome"))
        self.assertIn(("work_order_not_workable", "PASSED"), gates)
        self.assertIn(("training_not_authorized", "PASSED"), gates)

    # --- Loads -----------------------------------------------------------------

    def _start_load(self):
        return self.client.post("/api/BatchExecutions/", {
            "work_order": str(self.wo.id), "step": str(self.step.id),
            "parts": [str(p.id) for p in self.parts]}, format="json")

    def test_a_load_start_runs_the_floor_for_its_members(self):
        self._hold()
        resp = self._start_load()
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()["code"], "work_order_not_workable")
        self.assertFalse(BatchExecution.objects.filter(work_order=self.wo).exists())

    def test_starting_a_load_starts_its_parts_for_the_holder(self):
        resp = self._start_load()
        self.assertEqual(resp.status_code, 201, resp.content)
        for v in self.visits:
            v.refresh_from_db()
            self.assertEqual(v.status, "IN_PROGRESS")
            self.assertIsNotNone(v.assigned_to_id)
            self.assertTrue(GateDecision.objects.filter(
                step_execution=v, stage="START", gate="part_quarantined", outcome="PASSED").exists())

    # --- Bypass by code --------------------------------------------------------

    def test_a_bypass_clears_only_the_gate_it_names(self):
        from Tracker.services.mes.step_override import clear_bypassed
        StepOverride.objects.create(
            tenant=self.tenant_a, step_execution=self.visits[0], block_type="MEASUREMENT_FAILED",
            reason="x", status="APPROVED", requested_by=self.user_a,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        substep = Blocker(GateCode.SUBSTEPS_INCOMPLETE,
                          "Substep 'Measurement check' not completed for this part")
        reading = Blocker(GateCode.MEASUREMENT_OUT_OF_SPEC,
                          "One or more measurements are out of specification")
        self.assertEqual(clear_bypassed(self.visits[0], [substep, reading]), [substep])

    # --- Capture on an unstarted visit ------------------------------------------

    def test_work_is_not_recorded_on_an_unstarted_visit(self):
        from Tracker.services.dwi.operator_capture import submit_substep
        substep = Substep.objects.create(tenant=self.tenant_a, step=self.step, order=0, title="Load parts")
        with self.assertRaisesMessage(ValidationError, "Start Work on GATE-0"):
            submit_substep(substep=substep, step_execution=self.visits[0],
                           user=self.user_a, captures=[])

    # --- Deviation: start only -------------------------------------------------

    def test_an_expired_deviation_refuses_a_start_not_the_finish(self):
        text = "PCR-1 is a temporary change that ended on 2026-11-01."
        with mock.patch("Tracker.services.change_control.temporary.refusal", return_value=text):
            codes = [b.code for b in floor_blockers(StartContext(
                part=self.parts[0], step=self.step, work_order=self.wo, operator=None))]
            self.assertIn(GateCode.DEVIATION_EXPIRED, codes)
            self.visits[0].training_authorization = {"authorized": True, "missing": []}
            ok, blockers = self.step.can_advance_from_step(self.visits[0], self.wo)
        self.assertNotIn(text, blockers)

    # --- Release log -----------------------------------------------------------

    def test_a_release_logs_each_gate_and_the_bypass_that_cleared_one(self):
        Steps.objects.filter(pk=self.step.pk).update(requires_qa_signoff=True, block_on_quarantine=True)
        self.step.refresh_from_db()
        override = StepOverride.objects.create(
            tenant=self.tenant_a, step_execution=self.visits[0], block_type="QA_SIGNOFF",
            reason="Signer out", status="APPROVED", approved_by=self.user_a, requested_by=self.user_a,
            expires_at=timezone.now() + datetime.timedelta(hours=1))
        record_release(self.visits[0], self.wo, by=self.user_a)
        rows = {g.gate: g for g in GateDecision.objects.filter(step_execution=self.visits[0], stage="RELEASE")}
        self.assertEqual(rows["qa_signoff"].outcome, "BYPASSED")
        self.assertEqual(rows["qa_signoff"].reference, str(override.id))
        self.assertEqual(rows["quarantine_hold"].outcome, "PASSED")
