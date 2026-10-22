"""A step's visit cap (`max_visits`) with no escalation route refuses the advance.

Past the cap, `_check_cycle_limit` returned None when the process had no ESCALATION
edge, and `advance_part_step` read None as "end of the route": a part failing rework
past its cap was marked COMPLETED, or (held) left with no next step and no message
(docs walk 2026-10-22). Now the advance refuses and changes nothing.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    EdgeType, PartTypes, Parts, PartsStatus, Processes, ProcessStep,
    StepEdge, StepExecution, Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.parts import advance_part_step
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class VisitCapTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Cap", slug="visit-cap", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="cap-op", email="cap@op.test", password="x", tenant=self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P-CAP", part_type=pt)
        self.work = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Work",
                                         step_type="TASK")
        self.inspect = Steps.objects.create(tenant=self.tenant, part_type=pt, name="Inspect",
                                            step_type="TASK", max_visits=1)
        ProcessStep.objects.create(process=self.process, step=self.work, order=1)
        ProcessStep.objects.create(process=self.process, step=self.inspect, order=2)
        StepEdge.objects.create(process=self.process, from_step=self.work,
                                to_step=self.inspect, edge_type=EdgeType.DEFAULT)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-CAP",
                                      workorder_status=WorkOrderStatus.IN_PROGRESS,
                                      quantity=1, process=self.process)
        self.part = Parts.objects.create(tenant=self.tenant, ERP_id="P-CAP", part_type=pt,
                                         work_order=wo, step=self.work,
                                         part_status=PartsStatus.IN_PROGRESS)
        # Already been through Inspect once: the cap is used up.
        from django.utils import timezone
        StepExecution.objects.create(tenant=self.tenant, part=self.part, step=self.inspect,
                                     visit_number=1, status="COMPLETED",
                                     exited_at=timezone.now())
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.work, visit_number=1,
            status="IN_PROGRESS",
            training_authorization={'authorized': True, 'missing': [], 'verified': []})

    def test_past_the_cap_with_no_escalation_route_refuses(self):
        with self.assertRaisesMessage(ValueError, "no escalation route"):
            advance_part_step(self.part, operator=self.user, skip_gate_check=True)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step, self.work)
        self.assertEqual(self.part.part_status, PartsStatus.IN_PROGRESS)
        self.assertEqual(StepExecution.get_current_execution(self.part).status, "IN_PROGRESS")

    def _mrb(self):
        """MRB Review behind Inspect's cap, a Rework step, and Pack after Inspect."""
        pt = self.work.part_type
        self.mrb = Steps.objects.create(tenant=self.tenant, part_type=pt,
                                        name="MRB Review", step_type="TASK")
        self.rework = Steps.objects.create(tenant=self.tenant, part_type=pt,
                                           name="Rework", step_type="REWORK")
        self.pack = Steps.objects.create(tenant=self.tenant, part_type=pt,
                                         name="Pack", step_type="TASK")
        for i, s in enumerate((self.pack, self.rework, self.mrb), start=3):
            ProcessStep.objects.create(process=self.process, step=s, order=i)
        StepEdge.objects.create(process=self.process, from_step=self.inspect,
                                to_step=self.pack, edge_type=EdgeType.DEFAULT)
        StepEdge.objects.create(process=self.process, from_step=self.inspect,
                                to_step=self.mrb, edge_type=EdgeType.ESCALATION)

    def _escalate(self):
        from Tracker.models import QuarantineDisposition
        self._mrb()
        self.assertEqual(advance_part_step(self.part, operator=self.user, skip_gate_check=True),
                         "escalated")
        self.part.refresh_from_db()
        return QuarantineDisposition.objects.get(part=self.part, escalated_from_step=self.inspect)

    def _decide(self, disposition, kind, **kw):
        from Tracker.services.qms.disposition import decide_disposition
        from Tracker.services.qms.mrb import route_after_decision
        decide_disposition(disposition, disposition_type=kind, authorized_by=self.user, **kw)
        route_after_decision(disposition, self.user)
        self.part.refresh_from_db()

    def test_past_the_cap_it_is_held_at_mrb_with_a_decision_open(self):
        d = self._escalate()
        self.assertEqual(self.part.step, self.mrb)
        self.assertEqual(self.part.part_status, PartsStatus.QUARANTINED)
        self.assertEqual((d.current_state, d.assigned_to_id), ("OPEN", None))
        self.assertIn("Inspect", d.description)

    def test_rework_from_mrb_buys_exactly_one_more_visit(self):
        from Tracker.models import Parts
        d = self._escalate()
        self._decide(d, "REWORK")
        self.assertEqual(self.part.step, self.rework)
        # One more visit to Inspect is allowed now; the one after that escalates again.
        part = Parts.objects.get(pk=self.part.pk)
        self.assertEqual(part._check_cycle_limit(self.inspect), self.inspect)
        from django.utils import timezone
        StepExecution.objects.create(tenant=self.tenant, part=part, step=self.inspect,
                                     visit_number=2, status="COMPLETED",
                                     exited_at=timezone.now())
        part = Parts.objects.get(pk=self.part.pk)
        self.assertEqual(part._check_cycle_limit(self.inspect), self.mrb)

    def test_use_as_is_from_mrb_continues_past_the_check(self):
        d = self._escalate()
        self._decide(d, "USE_AS_IS", customer_approval={"reference": "CONC-1"})
        self.assertEqual(self.part.step, self.pack)
        self.assertEqual(self.part.part_status, PartsStatus.IN_PROGRESS)

    def test_a_fail_edge_into_mrb_holds_the_part_too(self):
        """Core Receiving / Component Grading send a failed unit straight to MRB."""
        from Tracker.models import QuarantineDisposition
        self._mrb()
        StepEdge.objects.create(process=self.process, from_step=self.work,
                                to_step=self.mrb, edge_type=EdgeType.ALTERNATE)
        self.work.is_decision_point = True
        self.work.decision_type = "MANUAL"
        self.work.save(update_fields=["is_decision_point", "decision_type"])
        self.assertEqual(advance_part_step(self.part, operator=self.user, skip_gate_check=True,
                                           decision_result="FAIL"), "escalated")
        self.part.refresh_from_db()
        self.assertEqual((self.part.step, self.part.part_status), (self.mrb, PartsStatus.QUARANTINED))
        d = QuarantineDisposition.objects.get(part=self.part)
        self.assertEqual(d.escalated_from_step, self.work)
        self.assertIn("Failed Work", d.description)
        # Use as is continues on the check's pass edge.
        self._decide(d, "USE_AS_IS", customer_approval={"reference": "CONC-2"})
        self.assertEqual(self.part.step, self.inspect)

    def test_scrap_from_mrb_scraps(self):
        d = self._escalate()
        self._decide(d, "SCRAP")
        self.assertEqual(self.part.part_status, PartsStatus.SCRAPPED)
