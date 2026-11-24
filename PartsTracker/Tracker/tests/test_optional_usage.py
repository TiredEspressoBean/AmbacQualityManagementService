"""Optional BOM lines: usage % planning, the rate draw, and the "used?" question
(user ruling 2026-11-24; services/mes/optional_usage)."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class _Fixture(TenantContextMixin, TestCase):
    """One step consuming an OPTIONAL seal kit, 1 per unit, on a work order of 8."""

    def setUp(self):
        super().setUp()
        from Tracker.models import (
            BOM, BOMLine, Material, Parts, PartTypes, Processes, ProcessStep, Steps, Tenant,
            WorkOrder, WorkOrderStatus,
        )
        self.tenant = Tenant.objects.create(name="OPT", slug="optional-usage", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.operator = User.objects.create_user(
            username="opt-op", email="opt@c.test", password="x", tenant=self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Assemble", step_type="TASK")
        self.next = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Test", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        ProcessStep.objects.create(process=self.process, step=self.next, order=2)
        self.seal = Material.objects.create(tenant=self.tenant, name="Seal Kit")
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt, bom_type='ASSEMBLY',
                                 status='RELEASED', version=1)
        self.line = BOMLine.objects.create(
            tenant=self.tenant, bom=bom, material=self.seal, quantity=1, source='BUY',
            consumed_at_step=self.step, is_optional=True, usage_percent=Decimal("25"))
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-OPT", quantity=8, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        self.parts = [Parts.objects.create(tenant=self.tenant, ERP_id=f"WO-OPT-{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step) for i in range(8)]

    def _stock(self, qty=100):
        from Tracker.models import MaterialLot
        return MaterialLot.objects.create(
            tenant=self.tenant, material=self.seal, lot_number=f"S-{qty}",
            quantity=Decimal(qty), quantity_remaining=Decimal(qty), unit_of_measure="EA",
            received_date=timezone.localdate(), received_by=self.operator, status="ACCEPTED")

    def _pass(self, part):
        """The unit leaves the step (its visit closed), and the step's material is drawn."""
        from Tracker.models import StepExecution
        from Tracker.services.mes.consumption import consume_for_step
        StepExecution.objects.create(tenant=self.tenant, part=part, step=self.step,
                                     exited_at=timezone.now())
        return consume_for_step(part, self.step, self.operator)

    def _drawn(self):
        from django.db.models import Sum
        from Tracker.models import MaterialUsage
        return MaterialUsage.objects.filter(work_order=self.wo).aggregate(
            q=Sum('qty_consumed'))['q'] or Decimal(0)

    def _ask(self):
        """Put a "used?" question for the line on the step."""
        from Tracker.models import Substep
        return Substep.objects.create(
            tenant=self.tenant, step=self.step, title="Seals", order=1,
            body_blocks={"type": "doc", "content": [{"type": "optionalPartUsed", "attrs": {
                "node_id": "used-1", "label": "Seal kit used?", "required": True,
                "bom_line_id": str(self.line.id)}}]})

    def _answer(self, part, substep, used, quantity="1"):
        from Tracker.models import StepExecution, SubstepResponse
        execution = StepExecution.objects.create(tenant=self.tenant, part=part, step=self.step,
                                                 exited_at=timezone.now())
        SubstepResponse.objects.create(
            tenant=self.tenant, step_execution=execution, substep=substep, node_id="used-1",
            kind="optional_part_used", responded_by=self.operator,
            value_json={"used": used, "quantity": quantity, "lots": []})


class PlanningCountsTheUsageShareTests(_Fixture):
    def test_requirements_count_quantity_times_usage(self):
        from Tracker.services.mes.requirements import sourcing_requirements
        rows = [r for r in sourcing_requirements(self.tenant)['source'] if r['material'] == "Seal Kit"]
        self.assertEqual(rows[0]['qty_short'], 2)          # 8 units x 1 x 25%

    def test_without_a_usage_percent_an_optional_line_is_still_left_out(self):
        from Tracker.services.mes.requirements import sourcing_requirements
        self.line.usage_percent = None
        self.line.save(update_fields=['usage_percent'])
        self.assertFalse(any(r['material'] == "Seal Kit"
                             for r in sourcing_requirements(self.tenant)['source']))

    def test_the_job_readout_shows_expected_beside_up_to(self):
        from Tracker.services.mes.requirements import work_order_material_requirements
        row = next(r for r in work_order_material_requirements(self.wo)['rows']
                   if r['component'] == "Seal Kit")
        self.assertEqual((row['quantity'], row['expected']), (8.0, 2.0))


class RateDrawTests(_Fixture):
    def test_the_running_total_is_exact_and_never_overdraws(self):
        """25% of 1 per unit, half up: after n units, round(n/4) drawn — 0,1,1,1,1,2,2,2."""
        self._stock()
        totals = []
        for n, part in enumerate(self.parts, start=1):
            self._pass(part)
            drawn = self._drawn()
            self.assertLessEqual(drawn, Decimal(n))         # never past n x qty
            totals.append(int(drawn))
        self.assertEqual(totals, [0, 1, 1, 1, 1, 2, 2, 2])

    def test_a_bulk_advance_of_units_with_no_step_execution_counts_and_draws(self):
        """Walk 2026-11-24 (WO-TRAIN-BOTTLE): two units moved in one bulk call, with no
        step execution at the step. The rate draw counted units from exited executions,
        read 0, and drew nothing; the call also reported 0 advanced. Now 2 advanced, and
        the 25% kit is drawn on the 2nd unit (half up: 0 then 1)."""
        from Tracker.models import Orders, StepExecution
        self._stock()
        order = Orders.objects.create(tenant=self.tenant, name="O-BULK")
        two = self.parts[:2]
        for p in two:
            p.order = order
            p.save(update_fields=["order"])
        self.assertFalse(StepExecution.objects.filter(part__in=two).exists())
        result = order.bulk_increment_parts_at_step(self.step.id, operator=self.operator)
        self.assertEqual(result, {"advanced": 2, "total": 2})
        self.assertEqual(self._drawn(), Decimal(1))

    def test_no_usage_percent_and_no_question_draws_nothing(self):
        self._stock()
        self.line.usage_percent = None
        self.line.save(update_fields=['usage_percent'])
        for part in self.parts:
            self._pass(part)
        self.assertEqual(self._drawn(), Decimal(0))


class UsedQuestionTests(_Fixture):
    def test_the_answer_replaces_the_rate_draw(self):
        """Asked on the step: units draw what they answered, not 25% — no double draw."""
        from Tracker.services.mes.consumption import consume_for_step
        self._stock()
        substep = self._ask()
        for i, part in enumerate(self.parts[:4]):
            self._answer(part, substep, used=(i == 0))     # one used, three not
            consume_for_step(part, self.step, self.operator)
        self.assertEqual(self._drawn(), Decimal(1))

    def test_not_used_draws_nothing(self):
        from Tracker.services.mes.consumption import consume_for_step
        self._stock()
        substep = self._ask()
        self._answer(self.parts[0], substep, used=False, quantity="0")
        consume_for_step(self.parts[0], self.step, self.operator)
        self.assertEqual(self._drawn(), Decimal(0))

    def test_an_unanswered_question_refuses_the_unit_leaving_the_step(self):
        """Refused even on a step with no gates configured: the question is required
        whatever the step's gate setup (the substep gate would refuse first otherwise)."""
        from Tracker.services.mes.parts import advance_part_step
        from Tracker.services.mes.step_gates import set_step_gates
        set_step_gates(self.step, [])
        self._ask()
        with self.assertRaisesMessage(ValueError, "used? not answered"):
            advance_part_step(self.parts[0], operator=self.operator)
        self.parts[0].refresh_from_db()
        self.assertEqual(self.parts[0].step_id, self.step.id)

    def test_a_used_answer_is_bounded_by_the_line_quantity(self):
        from Tracker.services.mes.optional_usage import validate_answer
        substep = self._ask()
        with self.assertRaisesMessage(ValueError, "used is 1 to"):
            validate_answer(substep, "used-1", {"used": True, "quantity": "3"}, None)
