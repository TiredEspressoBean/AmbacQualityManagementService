"""A required reman capture belongs on a reman-only step (N/A retirement, 2026-10-20).

With substep "Not applicable" retired, a new build that met a required
components-fitted / harvested / rebuild-finding capture would stick at that step for
ever. So authoring refuses it: on a substep of a step a non-reman process runs, and when
a step carrying one is added to a non-reman process.
"""
from Tracker.models import PartTypes, Processes, ProcessStep, Steps, Substep
from Tracker.services.dwi.reman_capture_guard import process_step_refusal
from Tracker.tests.base import TenantTestCase

BODY = {"type": "doc", "content": [
    {"type": "componentInstallCapture", "attrs": {
        "node_id": "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1", "required": True,
        "label": "Components fitted"}},
]}


class RemanCaptureGuardTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Injector")
        self.build = Processes.objects.create(tenant=self.tenant_a, name="Build", part_type=pt)
        self.reman = Processes.objects.create(tenant=self.tenant_a, name="Reman", part_type=pt,
                                              is_remanufactured=True)
        self.shared = Steps.objects.create(tenant=self.tenant_a, name="Assembly", part_type=pt)
        self.reman_only = Steps.objects.create(tenant=self.tenant_a, name="Reassembly", part_type=pt)
        ProcessStep.objects.create(process=self.build, step=self.shared, order=1)
        ProcessStep.objects.create(process=self.reman, step=self.shared, order=1)
        ProcessStep.objects.create(process=self.reman, step=self.reman_only, order=2)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_substep', 'add_substep', 'change_substep', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def _post(self, step, **extra):
        return self.client.post("/api/Substeps/", {
            "step": str(step.id), "order": 0, "title": "Record components",
            "body_blocks": BODY, **extra}, format="json")

    def test_a_required_reman_capture_on_a_shared_step_is_refused(self):
        resp = self._post(self.shared)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("reman-only step", str(resp.json()))

    def test_it_is_fine_on_a_reman_only_step(self):
        self.assertEqual(self._post(self.reman_only).status_code, 201)

    def test_an_optional_substep_may_carry_one(self):
        self.assertEqual(self._post(self.shared, is_optional=True).status_code, 201)

    def test_a_step_carrying_one_cannot_join_a_build_route(self):
        Substep.objects.create(tenant=self.tenant_a, step=self.reman_only, order=0,
                               title="Record components", body_blocks=BODY)
        self.assertIn("reman-only step", process_step_refusal(self.build, self.reman_only))
        self.assertIsNone(process_step_refusal(self.reman, self.reman_only))
