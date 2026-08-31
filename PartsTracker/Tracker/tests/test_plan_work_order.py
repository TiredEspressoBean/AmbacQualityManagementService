"""`plan_work_order` — the Gantt 'add work' service: create a WO + spawn its parts
at the process's first step so it schedules on the next solve.
"""
from django.test import TestCase

from Tracker.models import (
    Parts,
    PartsStatus,
    PartTypes,
    Processes,
    ProcessStep,
    Steps,
    Tenant,
    WorkOrderStatus,
)
from Tracker.services.mes.work_order import plan_work_order
from Tracker.tests.base import TenantContextMixin


class PlanWorkOrderTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Plan", slug="plan-wo", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nozzle", ID_prefix="NZ")
        self.process = Processes.objects.create(tenant=self.tenant, name="Injector Line", part_type=self.pt)
        self.s1 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        self.s2 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op2")
        ProcessStep.objects.create(process=self.process, step=self.s1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.s2, order=2)

    def test_creates_wo_and_parts_at_first_step(self):
        wo = plan_work_order(tenant=self.tenant, process=self.process, quantity=5)
        self.assertEqual(wo.quantity, 5)
        self.assertEqual(wo.workorder_status, WorkOrderStatus.PENDING)
        self.assertEqual(wo.process_id, self.process.id)
        parts = Parts.objects.filter(work_order=wo)
        self.assertEqual(parts.count(), 5)
        # all parts land on the process's FIRST step, PENDING
        self.assertTrue(all(p.step_id == self.s1.id for p in parts))
        self.assertTrue(all(p.part_status == PartsStatus.PENDING for p in parts))

    def test_autogenerates_erp_id_when_omitted(self):
        wo = plan_work_order(tenant=self.tenant, process=self.process, quantity=1)
        self.assertTrue(wo.ERP_id)
        # a second WO gets a distinct id
        wo2 = plan_work_order(tenant=self.tenant, process=self.process, quantity=1)
        self.assertNotEqual(wo.ERP_id, wo2.ERP_id)

    def test_honors_explicit_erp_priority_and_dates(self):
        import datetime
        due = datetime.date(2026, 12, 1)
        wo = plan_work_order(
            tenant=self.tenant, process=self.process, quantity=2,
            erp_id="WO-CUSTOM-1", priority=1, expected_completion=due)
        self.assertEqual(wo.ERP_id, "WO-CUSTOM-1")
        self.assertEqual(wo.priority, 1)
        self.assertEqual(wo.expected_completion, due)

    def test_rejects_bad_quantity(self):
        with self.assertRaises(ValueError):
            plan_work_order(tenant=self.tenant, process=self.process, quantity=0)

    def test_rejects_process_without_steps(self):
        empty = Processes.objects.create(tenant=self.tenant, name="Empty", part_type=self.pt)
        with self.assertRaises(ValueError):
            plan_work_order(tenant=self.tenant, process=empty, quantity=1)


class ReduceWorkOrderQuantityTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="RQ", slug="reduce-qty", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz", ID_prefix="NZ")
        self.process = Processes.objects.create(tenant=self.tenant, name="Line", part_type=self.pt)
        self.s1 = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        ProcessStep.objects.create(process=self.process, step=self.s1, order=1)
        self.wo = plan_work_order(tenant=self.tenant, process=self.process, quantity=5)

    def test_reduce_cancels_unstarted_parts(self):
        from Tracker.services.mes.work_order import reduce_work_order_quantity
        n = reduce_work_order_quantity(self.wo, 3, user=None)
        self.assertEqual(n, 2)
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.quantity, 3)
        live = Parts.objects.filter(work_order=self.wo).exclude(part_status=PartsStatus.CANCELLED)
        self.assertEqual(live.count(), 3)

    def test_reduce_refuses_when_parts_worked(self):
        from Tracker.models import StepExecution
        from Tracker.services.mes.work_order import reduce_work_order_quantity
        # mark 4 of 5 as worked (have a StepExecution) → only 1 unstarted removable
        for p in Parts.objects.filter(work_order=self.wo).order_by("ERP_id")[:4]:
            StepExecution.objects.create(tenant=self.tenant, part=p, step=self.s1, visit_number=1)
        with self.assertRaises(ValueError):
            reduce_work_order_quantity(self.wo, 1, user=None)  # needs to remove 4, only 1 removable

    def test_reduce_rejects_increase(self):
        from Tracker.services.mes.work_order import reduce_work_order_quantity
        with self.assertRaises(ValueError):
            reduce_work_order_quantity(self.wo, 10, user=None)
