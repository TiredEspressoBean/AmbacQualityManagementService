"""4a — manual decision-point resolution.

A MANUAL decision-point step doesn't auto-advance: the normal complete-step
flow reports it as blocked (no 500), and a manager resolves it by choosing the
DEFAULT (pass) or ALTERNATE (fail/rework) branch, which routes the part along
the corresponding StepEdge.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    StepEdge,
    StepExecution,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.mes_lite import EdgeType
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.services.mes.parts import advance_part_step
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class ManualDecisionResolutionTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Dec", slug="dec", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="mgr", email="m@m.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        # decision → (pass) final / (fail) rework
        self.decision_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Final Decision",
            step_type="TASK", is_decision_point=True, decision_type="MANUAL",
        )
        self.pass_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Final Test", step_type="TASK",
        )
        self.fail_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Rework", step_type="REWORK",
        )
        for i, s in enumerate([self.decision_step, self.pass_step, self.fail_step], start=1):
            ProcessStep.objects.create(process=self.process, step=s, order=i)
        StepEdge.objects.create(
            process=self.process, from_step=self.decision_step,
            to_step=self.pass_step, edge_type=EdgeType.DEFAULT,
        )
        StepEdge.objects.create(
            process=self.process, from_step=self.decision_step,
            to_step=self.fail_step, edge_type=EdgeType.ALTERNATE,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-DEC-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2, process=self.process,
        )

    def _part(self, erp):
        p = Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, part_type=self.part_type,
            work_order=self.wo, step=self.decision_step,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=p, step=self.decision_step, visit_number=1, status="IN_PROGRESS",
        )
        return p

    def test_manual_decision_blocks_auto_advance(self):
        self._part("P-DEC-A")
        result = try_advance_lot(
            work_order_id=str(self.wo.id),
            step_id=str(self.decision_step.id),
            tenant_id=str(self.tenant.id),
            operator=self.user,
        )
        # Reported as blocked, not raised — the operator's complete-step won't 500.
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.reason, "manual_decision_required")

    def test_default_branch_routes_to_pass_step(self):
        p = self._part("P-DEC-B")
        advance_part_step(p, operator=self.user, decision_result="DEFAULT")
        p.refresh_from_db()
        self.assertEqual(p.step_id, self.pass_step.id)

    def test_alternate_branch_routes_to_rework_step(self):
        p = self._part("P-DEC-C")
        advance_part_step(p, operator=self.user, decision_result="ALTERNATE")
        p.refresh_from_db()
        self.assertEqual(p.step_id, self.fail_step.id)
