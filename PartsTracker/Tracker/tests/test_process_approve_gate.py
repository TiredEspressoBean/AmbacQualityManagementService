"""Approving a routing refuses while it has flow errors (user decision 2026-10-22).

The editor already blocked Approve on validation errors, but the API took any draft:
a QA_RESULT decision with no Fail branch could be locked for production, and a FAIL
there finds no next step and marks the part COMPLETED. `process_flow_errors` mirrors
the editor's error rules and `approve_process` enforces them on every path.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    EdgeType, PartTypes, Processes, ProcessStatus, ProcessStep, StepEdge, Steps, Tenant,
)
from Tracker.services.mes.processes import approve_process, process_flow_errors
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class ApproveGateTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Gate", slug="approve-gate", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="eng", email="eng@x.test", password="x", tenant=self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=pt,
                                                status=ProcessStatus.DRAFT)
        mk = lambda name, **kw: Steps.objects.create(tenant=self.tenant, part_type=pt, name=name, **kw)
        self.start = mk("Start", step_type="START")
        self.check = mk("Check", is_decision_point=True, decision_type="QA_RESULT")
        self.done = mk("Done", is_terminal=True)
        self.scrap = mk("Scrap", is_terminal=True)
        for i, s in enumerate((self.start, self.check, self.done, self.scrap)):
            ProcessStep.objects.create(process=self.process, step=s, order=i)
        StepEdge.objects.create(process=self.process, from_step=self.start, to_step=self.check,
                                edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=self.process, from_step=self.check, to_step=self.done,
                                edge_type=EdgeType.DEFAULT)

    def test_a_decision_with_no_fail_branch_cannot_be_approved(self):
        self.assertTrue(any("no Fail connection" in e for e in process_flow_errors(self.process)))
        with self.assertRaisesMessage(ValueError, "no Fail connection"):
            approve_process(self.process, self.user)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.DRAFT)

    def test_a_complete_routing_approves(self):
        StepEdge.objects.create(process=self.process, from_step=self.check, to_step=self.scrap,
                                edge_type=EdgeType.ALTERNATE)
        self.assertEqual(process_flow_errors(self.process), [])
        approve_process(self.process, self.user)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.APPROVED)
