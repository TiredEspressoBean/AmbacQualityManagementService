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


class RepeatFailureReachesMrbTests(TenantContextMixin, VectorTestCase):
    """fail → rework → fail → rework → cap → MRB, through the real routing.

    The second REWORK decision used to strand the part at the check (REWORK_NEEDED):
    routing skipped any part already split off its lot, and the first rework split it
    for good. So the inspection's visit cap could never be reached (walk 2026-10-22).
    """

    def setUp(self):
        super().setUp()
        from Tracker.models import Substep, SubstepScope
        self.tenant = Tenant.objects.create(name="Repeat", slug="repeat-fail", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="qa", email="qa@x.test", password="x", tenant=self.tenant)
        pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P-REP", part_type=pt)
        mk = lambda name, **kw: Steps.objects.create(tenant=self.tenant, part_type=pt, name=name, **kw)
        self.inspect = mk("Nozzle Inspection", step_type="TASK", max_visits=2)
        self.rework = mk("Rework", step_type="REWORK", max_visits=3)
        self.pack = mk("Pack", step_type="TASK")
        self.mrb = mk("MRB Review", step_type="TASK")
        for i, s in enumerate((self.inspect, self.pack, self.rework, self.mrb), start=1):
            ProcessStep.objects.create(process=self.process, step=s, order=i)
        E = lambda a, b, t: StepEdge.objects.create(process=self.process, from_step=a, to_step=b, edge_type=t)
        E(self.inspect, self.pack, EdgeType.DEFAULT)
        E(self.rework, self.inspect, EdgeType.DEFAULT)
        E(self.inspect, self.mrb, EdgeType.ESCALATION)
        E(self.rework, self.mrb, EdgeType.ESCALATION)
        # A rework target must re-inspect (split_part_from_lot refuses one that doesn't).
        Substep.objects.create(tenant=self.tenant, step=self.rework, order=0, title="Re-inspect",
                               scope=SubstepScope.SAMPLED, is_inspection_point=True)
        wo = WorkOrder.objects.create(tenant=self.tenant, ERP_id="WO-REP",
                                      workorder_status=WorkOrderStatus.IN_PROGRESS,
                                      quantity=1, process=self.process)
        self.part = Parts.objects.create(tenant=self.tenant, ERP_id="P-REP", part_type=pt,
                                         work_order=wo, step=self.inspect,
                                         part_status=PartsStatus.IN_PROGRESS)
        StepExecution.objects.create(tenant=self.tenant, part=self.part, step=self.inspect,
                                     visit_number=1, status="IN_PROGRESS",
                                     training_authorization={'authorized': True})

    def _fail_and_rework(self):
        """The check fails: the part is held, QA decides rework, the decision routes it."""
        from Tracker.models import QuarantineDisposition
        from Tracker.services.qms.disposition import decide_disposition, route_part_to_rework_if_needed
        self.part.refresh_from_db()
        self.part.part_status = PartsStatus.QUARANTINED
        self.part.save(update_fields=["part_status"])
        d = QuarantineDisposition.objects.create(tenant=self.tenant, part=self.part,
                                                 step=self.part.step)
        decide_disposition(d, disposition_type="REWORK", authorized_by=self.user)
        route_part_to_rework_if_needed(d, self.user)
        self.part.refresh_from_db()

    def _finish_rework(self):
        """Rework done: the part goes back to the check (or, past its cap, to MRB)."""
        result = advance_part_step(self.part, operator=self.user, skip_gate_check=True)
        self.part.refresh_from_db()
        return result

    def test_a_second_failure_is_reworked_and_the_third_visit_escalates(self):
        from Tracker.models import QuarantineDisposition
        self._fail_and_rework()
        self.assertEqual(self.part.step, self.rework, "first failure goes to rework")
        self._finish_rework()
        self.assertEqual(self.part.step, self.inspect, "back to the check, visit 2")

        self._fail_and_rework()
        self.assertEqual(self.part.step, self.rework,
                         "the second failure is routed too, not stranded at the check")
        self.assertEqual(self._finish_rework(), "escalated")
        # A third look at the check is past its cap of 2: MRB, held, with a decision.
        self.assertEqual((self.part.step, self.part.part_status),
                         (self.mrb, PartsStatus.QUARANTINED))
        self.assertTrue(QuarantineDisposition.objects.filter(
            part=self.part, escalated_from_step=self.inspect, current_state="OPEN").exists())
