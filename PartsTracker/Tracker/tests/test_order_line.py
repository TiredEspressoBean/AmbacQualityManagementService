"""Demand becoming work.

`Orders` recorded the customer engagement but never the demand: there was nowhere to
say "customer X wants 50 of type Y by date Z", so quantity and part type existed only
on a WorkOrder — i.e. only after somebody had already decided by hand what to build.
An order could be attached to work after the fact; it could not produce it.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Orders, OrderLine, OrderLineStatus, PartTypes, Processes, ProcessStep, Steps,
    Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.order_line import CannotPlan, plan_order_line
from Tracker.tests.base import TenantContextMixin


class OrderLinePlanningTests(TenantContextMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="OL", slug="order-line", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="ol-planner", email="ol@c.test", password="x", tenant=self.tenant)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Build", part_type=self.pt,
            status='APPROVED', is_current_version=True)
        step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Assemble", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=step, order=1)

        self.order = Orders.objects.create(
            tenant=self.tenant, name="Fleet refresh", customer=self.user)
        self.due = timezone.localdate() + timedelta(days=60)
        self.line = OrderLine.objects.create(
            tenant=self.tenant, order=self.order, line_number=1,
            part_type=self.pt, quantity=50, due_date=self.due)

    # --- the gap this closes ----------------------------------------------

    def test_planning_a_line_creates_work_pegged_to_it(self):
        wo = plan_order_line(self.line, user=self.user)

        self.assertEqual(wo.quantity, 50)
        self.assertEqual(wo.order_line_id, self.line.id)
        # Both pegs: `cascade_order_status` and every existing order filter read
        # `related_order`, so a job planned from a line has to be visible to them too.
        self.assertEqual(wo.related_order_id, self.order.id)

    def test_the_lines_promised_date_lands_on_the_job(self):
        """The date the customer was told, not one somebody retyped."""
        wo = plan_order_line(self.line, user=self.user)
        self.assertEqual(wo.expected_completion, self.due)

    # --- remaining demand --------------------------------------------------

    def test_remaining_falls_as_work_is_planned(self):
        self.assertEqual(self.line.remaining_quantity, 50)
        plan_order_line(self.line, user=self.user, quantity=20)
        self.assertEqual(self.line.remaining_quantity, 30)

    def test_a_fully_planned_line_refuses_to_plan_again(self):
        plan_order_line(self.line, user=self.user)
        with self.assertRaises(CannotPlan):
            plan_order_line(self.line, user=self.user)

    def test_cancelling_a_job_returns_its_units_to_the_line(self):
        """A cancelled work order covers nothing. Without this the line would read as
        satisfied by work that will never run, and the demand would vanish silently."""
        wo = plan_order_line(self.line, user=self.user, quantity=20)
        self.assertEqual(self.line.remaining_quantity, 30)

        WorkOrder.objects.filter(pk=wo.pk).update(
            workorder_status=WorkOrderStatus.CANCELLED)
        self.assertEqual(self.line.remaining_quantity, 50)

    def test_overplanning_is_refused(self):
        with self.assertRaises(CannotPlan):
            plan_order_line(self.line, user=self.user, quantity=51)

    def test_a_cancelled_line_cannot_be_planned(self):
        self.line.status = OrderLineStatus.CANCELLED
        self.line.save(update_fields=['status'])
        with self.assertRaises(CannotPlan):
            plan_order_line(self.line, user=self.user)

    # --- refusing to guess -------------------------------------------------

    def test_a_part_type_with_no_approved_routing_is_refused_with_the_reason(self):
        """Releasing against the wrong routing produces a correct-looking job that
        builds the wrong thing, so this refuses rather than picking one."""
        other = PartTypes.objects.create(tenant=self.tenant, name="Unrouted")
        line = OrderLine.objects.create(
            tenant=self.tenant, order=self.order, line_number=2,
            part_type=other, quantity=5)
        with self.assertRaises(CannotPlan) as ctx:
            plan_order_line(line, user=self.user)
        self.assertIn("no approved build process", str(ctx.exception))

    def test_an_ambiguous_routing_is_refused_rather_than_picked(self):
        Processes.objects.create(
            tenant=self.tenant, name="Build (alt)", part_type=self.pt,
            status='APPROVED', is_current_version=True)
        with self.assertRaises(CannotPlan) as ctx:
            plan_order_line(self.line, user=self.user)
        self.assertIn("several approved build processes", str(ctx.exception))

    # --- the additive promise ----------------------------------------------

    def test_a_work_order_without_a_line_is_still_valid(self):
        """Lines are additive. Legacy orders have none, and nothing was backfilled —
        inferring a line from jobs somebody already created would invent demand the
        customer never stated."""
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-LEGACY", quantity=3, process=self.process,
            related_order=self.order, workorder_status=WorkOrderStatus.PENDING)
        self.assertIsNone(wo.order_line_id)
        self.assertEqual(self.line.remaining_quantity, 50)
