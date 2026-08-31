"""Make-up planning — replace scrap to keep a work order on track for its ordered good
count (Tracker/services/mes/makeup.py). Planner-confirmed; parts flagged is_makeup.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Parts, PartsStatus, PartTypes, Processes, ProcessStep, ScheduleResult,
    Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.mes.makeup import work_order_shortfall, create_makeup_parts
from Tracker.tests.base import TenantContextMixin


class MakeupPlanningTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="MU", slug="makeup", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Nz")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(tenant=self.tenant, part_type=self.pt, name="Op1")
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

    def _wo(self, target=5, started=5):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-MU", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=started, target_good_quantity=target, process=self.process)
        for i in range(started):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"WO-MU-P{i}", part_type=self.pt,
                work_order=wo, step=self.step, part_status=PartsStatus.PENDING)
        return wo

    def _scrap(self, wo, n):
        for p in wo.parts.all()[:n]:
            p.part_status = PartsStatus.SCRAPPED
            p.save(update_fields=['part_status'])

    def test_no_shortfall_when_all_alive(self):
        wo = self._wo(target=5, started=5)
        self.assertEqual(work_order_shortfall(wo)['shortfall'], 0)

    def test_scrap_creates_shortfall(self):
        wo = self._wo(target=5, started=5)
        self._scrap(wo, 2)
        info = work_order_shortfall(wo)
        self.assertEqual(info['alive'], 3)
        self.assertEqual(info['scrapped'], 2)
        self.assertEqual(info['shortfall'], 2)

    def test_create_makeup_tops_up_to_target(self):
        wo = self._wo(target=5, started=5)
        self._scrap(wo, 2)
        result = create_makeup_parts(wo)
        self.assertEqual(result['created'], 2)
        self.assertEqual(result['shortfall'], 0)
        makeups = wo.parts.filter(is_makeup=True)
        self.assertEqual(makeups.count(), 2)
        # Replacements start at the route's first step, PENDING.
        self.assertTrue(all(p.step_id == self.step.id and p.part_status == PartsStatus.PENDING
                            for p in makeups))

    def test_create_makeup_noop_when_on_track(self):
        wo = self._wo(target=5, started=5)
        result = create_makeup_parts(wo)
        self.assertEqual(result['created'], 0)
        self.assertEqual(wo.parts.filter(is_makeup=True).count(), 0)

    def test_target_falls_back_to_quantity_when_null(self):
        wo = self._wo(target=4, started=4)
        WorkOrder.objects.filter(pk=wo.pk).update(target_good_quantity=None)
        wo.refresh_from_db()
        self._scrap(wo, 1)
        self.assertEqual(work_order_shortfall(wo)['shortfall'], 1)  # target falls back to quantity=4

    def test_makeup_marks_schedule_stale(self):
        wo = self._wo(target=5, started=5)
        self._scrap(wo, 1)
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=1),
            is_active=True, is_draft=False, is_stale=False)
        create_makeup_parts(wo)
        sched.refresh_from_db()
        self.assertTrue(sched.is_stale)
