"""4a — manual decision-point resolution.

A MANUAL decision-point step doesn't auto-advance: the normal complete-step
flow reports it as blocked (no 500), and a manager resolves it by choosing the
DEFAULT (pass) or ALTERNATE (fail/rework) branch, which routes the part along
the corresponding StepEdge.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    MeasurementDefinition,
    MeasurementResult,
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    QualityReports,
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


class MeasurementDecisionAutoRouteTests(TenantContextMixin, VectorTestCase):
    """A MEASUREMENT decision step routing from the part's own recorded reading.

    This is the per-part divergence the flow engine already supports: two units in
    one work order, same step, different readings, different next steps. It had no
    coverage, and the lookup behind it named three fields that do not exist — so
    the auto-route path raised FieldError instead of routing. MANUAL is guarded in
    advancement.py against exactly this shape of failure; MEASUREMENT was not.
    """

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Meas", slug="meas", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="insp", email="i@m.test", password="x", tenant=self.tenant,
        )
        self.part_type = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.part_type,
        )
        self.gauge_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Bore Gauge",
            step_type="TASK", is_decision_point=True, decision_type="MEASUREMENT",
        )
        self.in_spec_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Assemble",
            step_type="TASK",
        )
        self.oversize_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.part_type, name="Hone",
            step_type="TASK",
        )
        for i, s in enumerate(
            [self.gauge_step, self.in_spec_step, self.oversize_step], start=1
        ):
            ProcessStep.objects.create(process=self.process, step=s, order=i)

        self.measurement = MeasurementDefinition.objects.create(
            tenant=self.tenant, step=self.gauge_step, label="Bore ID",
            type="NUMERIC", unit="mm", nominal=10.0,
            upper_tol=10.05, lower_tol=9.95,
        )
        # At or under 10.05 the bore is usable; over it, the unit needs honing.
        StepEdge.objects.create(
            process=self.process, from_step=self.gauge_step,
            to_step=self.in_spec_step, edge_type=EdgeType.DEFAULT,
            condition_measurement=self.measurement,
            condition_operator='lte', condition_value=10.05,
        )
        StepEdge.objects.create(
            process=self.process, from_step=self.gauge_step,
            to_step=self.oversize_step, edge_type=EdgeType.ALTERNATE,
            condition_measurement=self.measurement,
            condition_operator='lte', condition_value=10.05,
        )
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-MEAS-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2,
            process=self.process,
        )

    def _part_with_reading(self, erp, value):
        part = Parts.objects.create(
            tenant=self.tenant, ERP_id=erp, part_type=self.part_type,
            work_order=self.wo, step=self.gauge_step,
        )
        report = QualityReports.objects.create(
            tenant=self.tenant, part=part, step=self.gauge_step,
            status='PASS', detected_by=self.user,
        )
        MeasurementResult.objects.create(
            tenant=self.tenant, report=report, definition=self.measurement,
            value_numeric=value, is_within_spec=(value <= 10.05),
            created_by=self.user,
        )
        return part

    def test_a_reading_in_spec_routes_to_the_default_edge(self):
        part = self._part_with_reading("P-IN", 10.01)
        self.assertEqual(part.get_next_step(), self.in_spec_step)

    def test_a_reading_out_of_spec_routes_to_the_alternate_edge(self):
        part = self._part_with_reading("P-OUT", 10.40)
        self.assertEqual(part.get_next_step(), self.oversize_step)

    def test_two_units_in_one_work_order_diverge_on_their_own_readings(self):
        """The property the reman scope design leans on: discrete units in a single
        WO take different paths, decided by their own measurements."""
        good = self._part_with_reading("P-A", 9.99)
        bad = self._part_with_reading("P-B", 10.60)
        self.assertEqual(good.get_next_step(), self.in_spec_step)
        self.assertEqual(bad.get_next_step(), self.oversize_step)
        self.assertNotEqual(good.get_next_step(), bad.get_next_step())
