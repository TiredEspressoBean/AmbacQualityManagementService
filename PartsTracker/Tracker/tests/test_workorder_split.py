"""WorkOrder-grain split / undo (`services.mes.work_order.split_work_order` / `undo_split`).

Distinct from the PART-grain lot split (`split_part_from_lot`): WO-split moves parts into a
NEW child WorkOrder (QUANTITY / OPERATION / REWORK). These paths previously had zero test
coverage; this locks in provenance, the REWORK reset, the orphaned-lot-flag fix, and undo.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    Parts,
    PartsStatus,
    PartTypes,
    Processes,
    ProcessStatus,
    ProcessStep,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderSplitReason,
    WorkOrderStatus,
)
from Tracker.services.mes.work_order import split_work_order, undo_split
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class WorkOrderSplitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Split Shop", slug="split-shop")
        cls._tok = set_current_tenant_id(cls.tenant.id)
        cls.user = User.objects.create_user(
            username="splitter", email="s@t.com", password="x", tenant=cls.tenant)
        cls.pt = PartTypes.objects.create(name="Widget", ID_prefix="WDG", tenant=cls.tenant)
        cls.process = Processes.objects.create(
            name="Main", part_type=cls.pt, tenant=cls.tenant, status=ProcessStatus.APPROVED)
        cls.s1 = Steps.objects.create(name="Op1", part_type=cls.pt, tenant=cls.tenant)
        cls.s2 = Steps.objects.create(name="Op2", part_type=cls.pt, tenant=cls.tenant)
        ProcessStep.objects.create(process=cls.process, step=cls.s1, order=0)
        ProcessStep.objects.create(process=cls.process, step=cls.s2, order=1)
        # A separate process for REWORK-reason splits (which reroute to another routing).
        cls.rework_proc = Processes.objects.create(
            name="Rework", part_type=cls.pt, tenant=cls.tenant, status=ProcessStatus.APPROVED)
        cls.rs1 = Steps.objects.create(name="ReworkOp", part_type=cls.pt, tenant=cls.tenant)
        ProcessStep.objects.create(process=cls.rework_proc, step=cls.rs1, order=0)

    @classmethod
    def tearDownClass(cls):
        try:
            reset_current_tenant(cls._tok)
        except Exception:
            pass
        super().tearDownClass()

    def _wo(self, erp, n, status=PartsStatus.PENDING, step=None):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n, process=self.process)
        parts = [
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-{i}", part_type=self.pt,
                work_order=wo, step=step or self.s1, part_status=status)
            for i in range(n)
        ]
        return wo, parts

    def test_quantity_split_moves_first_n_and_records_provenance(self):
        wo, _ = self._wo("WO-Q", 5)
        child = split_work_order(
            wo, WorkOrderSplitReason.QUANTITY, self.user, new_erp_id="WO-Q-C", quantity=2)
        self.assertEqual(child.parent_workorder_id, wo.id)
        self.assertEqual(child.split_reason, WorkOrderSplitReason.QUANTITY)
        self.assertIsNotNone(child.split_at)
        self.assertEqual(Parts.objects.filter(work_order=child).count(), 2)
        self.assertEqual(Parts.objects.filter(work_order=wo).count(), 3)

    def test_operation_split_moves_given_parts(self):
        wo, parts = self._wo("WO-O", 4)
        child = split_work_order(
            wo, WorkOrderSplitReason.OPERATION, self.user, new_erp_id="WO-O-C",
            part_ids=[str(parts[0].id), str(parts[1].id)])
        self.assertEqual(
            set(Parts.objects.filter(work_order=child).values_list('id', flat=True)),
            {parts[0].id, parts[1].id})

    def test_rework_split_reroutes_to_target_process_and_resets(self):
        wo, parts = self._wo("WO-R", 3, status=PartsStatus.IN_PROGRESS, step=self.s2)
        child = split_work_order(
            wo, WorkOrderSplitReason.REWORK, self.user, new_erp_id="WO-R-C",
            part_ids=[str(parts[0].id)], target_process_id=str(self.rework_proc.id))
        p = Parts.objects.get(id=parts[0].id)
        self.assertEqual(p.work_order_id, child.id)
        self.assertEqual(child.process_id, self.rework_proc.id)
        self.assertIsNone(p.step_id)
        self.assertEqual(p.part_status, PartsStatus.PENDING)

    def test_split_clears_orphaned_lot_split_flag_but_keeps_genealogy(self):
        wo, parts = self._wo("WO-ORPH", 3)
        parts[0].split_from_lot = True
        parts[0].lot_split_reason = 'quarantine'
        parts[0].save(update_fields=['split_from_lot', 'lot_split_reason'])
        split_work_order(
            wo, WorkOrderSplitReason.OPERATION, self.user, new_erp_id="WO-ORPH-C",
            part_ids=[str(parts[0].id)])
        p = Parts.objects.get(id=parts[0].id)
        self.assertFalse(p.split_from_lot, "parent-cohort split flag cleared in the child")
        self.assertEqual(p.lot_split_reason, 'quarantine', "genealogy retained")

    def test_undo_split_returns_parts_clears_flag_and_restores_step(self):
        wo, parts = self._wo("WO-U", 3, status=PartsStatus.IN_PROGRESS, step=self.s2)
        child = split_work_order(
            wo, WorkOrderSplitReason.REWORK, self.user, new_erp_id="WO-U-C",
            part_ids=[str(parts[0].id)], target_process_id=str(self.rework_proc.id))
        parent = undo_split(child, self.user)
        self.assertEqual(parent.id, wo.id)
        p = Parts.objects.get(id=parts[0].id)
        self.assertEqual(p.work_order_id, wo.id, "part returned to parent")
        self.assertFalse(p.split_from_lot)
        self.assertEqual(p.step_id, self.s1.id, "stranded (step=None) part restored to first step")
        child.refresh_from_db()
        self.assertTrue(child.archived)
