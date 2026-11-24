"""A unit with no visit recorded at its step is gated as "nothing done yet" (user
ruling 2026-11-24). It used to skip every gate: advance_part_step ran the step's
gates only when the unit had a StepExecution, so units placed at a step (or a new
order's units nobody had opened) moved past required substeps, QA sign-off and FPI."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class _Fixture(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        from Tracker.models import (
            Parts, PartTypes, Processes, ProcessStep, Steps, Tenant, WorkOrder, WorkOrderStatus,
        )
        self.tenant = Tenant.objects.create(name="GWX", slug="gate-no-exec", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.operator = User.objects.create_user(
            username="gwx-op", email="gwx@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Assemble",
                                         step_type="TASK")
        self.next = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Test",
                                         step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        ProcessStep.objects.create(process=self.process, step=self.next, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-GWX", quantity=1, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.part = Parts.objects.create(tenant=self.tenant, ERP_id="WO-GWX-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step)

    def _gates(self, *gates):
        from Tracker.services.mes.step_gates import set_step_gates
        set_step_gates(self.step, [{'gate': g} for g in gates])

    def _advance(self):
        from Tracker.services.mes.parts import advance_part_step
        return advance_part_step(self.part, operator=self.operator)

    def _refused(self, words):
        from Tracker.models import StepExecution
        self.assertFalse(StepExecution.objects.filter(part=self.part).exists())
        with self.assertRaisesMessage(ValueError, words):
            self._advance()
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step.id)


class GatedWithoutAVisitTests(_Fixture):
    def test_required_substeps_hold_a_unit_with_no_visit(self):
        from Tracker.models import Substep
        Substep.objects.create(tenant=self.tenant, step=self.step, title="Torque the nut", order=1,
                               body_blocks={"type": "doc", "content": []})
        self._gates('substeps_incomplete')
        self._refused("Substep 'Torque the nut' not completed")

    def test_qa_signoff_holds_a_unit_with_no_visit(self):
        self._gates('qa_signoff')
        self._refused("QA signoff required")

    def test_first_piece_holds_a_unit_with_no_visit(self):
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step, requires_first_piece_inspection=True)
        self._refused("First Piece Inspection required")

    def test_an_optional_substep_holds_nothing(self):
        from Tracker.models import Substep
        Substep.objects.create(tenant=self.tenant, step=self.step, title="Photo if you like",
                               order=1, is_optional=True, body_blocks={"type": "doc", "content": []})
        self._gates('substeps_incomplete')
        self.assertEqual(self._advance(), "advanced")

    def test_with_nothing_to_hold_it_a_unit_with_no_visit_advances(self):
        self._gates('substeps_incomplete', 'qualified_operator')   # gates, but nothing required
        self.assertEqual(self._advance(), "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.next.id)

    def test_the_order_level_advance_is_held_too(self):
        from Tracker.models import Orders
        self._gates('qa_signoff')
        order = Orders.objects.create(tenant=self.tenant, name="O-GWX")
        self.part.order = order
        self.part.save(update_fields=["order"])
        result = order.bulk_increment_parts_at_step(self.step.id, operator=self.operator)
        self.assertEqual(result["advanced"], 0)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step.id)
