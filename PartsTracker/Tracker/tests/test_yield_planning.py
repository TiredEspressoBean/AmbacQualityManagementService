"""E4 — yield/scrap-aware quantities.

Expected scrap resolves step → process default → 0 (a future statistical rate slots in
above the authored one). `plan_work_order(apply_yield=True)` grosses up the started count so
a work order still finishes the requested number of good parts.
"""
from decimal import Decimal

from django.test import TestCase

from Tracker.models import (
    Parts, PartTypes, Processes, ProcessStatus, ProcessStep, Steps, Tenant,
)
from Tracker.services.mes.work_order import plan_work_order
from Tracker.services.mes.yield_planning import process_yield, start_quantity_for_good
from Tracker.tests.base import TenantContextMixin


class YieldPlanningTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Y", slug="yield", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="PT")

    def _process(self, default_scrap="0", step_scraps=(None, None)):
        # # APPROVED, not the model default of DRAFT: `plan_work_order` only releases
        # work against an approved routing.
        proc = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.pt,
            status=ProcessStatus.APPROVED,
            default_scrap_rate=Decimal(default_scrap))
        for i, sc in enumerate(step_scraps, start=1):
            step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name=f"Op{i}")
            if sc is not None:
                step.scrap_rate = Decimal(sc)
                step.save(update_fields=["scrap_rate"])
            ProcessStep.objects.create(process=proc, step=step, order=i)
        return proc

    def test_process_yield_uses_default(self):
        proc = self._process(default_scrap="0.1", step_scraps=(None, None))
        self.assertAlmostEqual(process_yield(proc), 0.9 * 0.9, places=4)

    def test_step_rate_overrides_process_default(self):
        proc = self._process(default_scrap="0.1", step_scraps=("0.2", None))
        self.assertAlmostEqual(process_yield(proc), 0.8 * 0.9, places=4)

    def test_no_scrap_is_full_yield(self):
        proc = self._process(default_scrap="0", step_scraps=(None, None))
        self.assertEqual(process_yield(proc), 1.0)
        self.assertEqual(start_quantity_for_good(proc, 10), 10)

    def test_start_quantity_grosses_up(self):
        proc = self._process(default_scrap="0.1", step_scraps=(None, None))  # yield 0.81
        self.assertEqual(start_quantity_for_good(proc, 10), 13)  # ceil(10/0.81)=13

    def test_plan_work_order_applies_yield(self):
        proc = self._process(default_scrap="0.1", step_scraps=(None, None))
        wo = plan_work_order(tenant=self.tenant, process=proc, quantity=10, apply_yield=True)
        self.assertEqual(wo.quantity, 13)
        self.assertEqual(Parts.objects.filter(work_order=wo).count(), 13)
        self.assertEqual(wo.yield_summary, {'target_good': 10, 'started': 13})

    def test_plan_work_order_without_yield_is_unchanged(self):
        proc = self._process(default_scrap="0.1", step_scraps=(None, None))
        wo = plan_work_order(tenant=self.tenant, process=proc, quantity=10)  # apply_yield default False
        self.assertEqual(wo.quantity, 10)
        self.assertEqual(Parts.objects.filter(work_order=wo).count(), 10)
        self.assertIsNone(wo.yield_summary)

    def test_apply_yield_noop_when_no_scrap(self):
        proc = self._process(default_scrap="0", step_scraps=(None, None))
        wo = plan_work_order(tenant=self.tenant, process=proc, quantity=10, apply_yield=True)
        self.assertEqual(wo.quantity, 10)
        self.assertIsNone(wo.yield_summary)
