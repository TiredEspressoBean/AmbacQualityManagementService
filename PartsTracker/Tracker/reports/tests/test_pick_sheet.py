"""Pick Sheet — the consolidated shelf pull.

The behaviours worth pinning are the ones that would quietly make a batched pull
unusable: the same material appearing on several jobs must collapse to ONE row (that
is the entire point — one trip per bin), and every row must carry its drops, because a
picker holding a combined quantity with no split has been made faster at the cost of
being unable to finish.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    BOM, BOMLine, Equipments, Material, MaterialLot, Parts, PartTypes, Processes,
    ProcessStep, ScheduledTask, ScheduleResult, Steps, Tenant, WorkCenter, WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.staging import consolidated_pick
from Tracker.tests.base import TenantContextMixin


class ConsolidatedPickTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="PS", slug="picksheet", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="ps-op", email="ps@c.test", password="x", tenant=self.tenant)

        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Teardown Bay",
                                            code="TD")
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="DP-1", is_schedulable=True)
        self.wc.equipment.add(self.machine)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Injector")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Teardown", step_type="TASK",
            work_center=self.wc)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

        self.seal = Material.objects.create(tenant=self.tenant, name="Seal Kit")
        bom = BOM.objects.create(tenant=self.tenant, part_type=self.pt,
                                 bom_type='ASSEMBLY', status='RELEASED', version=1)
        BOMLine.objects.create(tenant=self.tenant, bom=bom, material=self.seal,
                               quantity=2, source='BUY', consumed_at_step=self.step)

        self.now = timezone.now()
        self.schedule = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=self.now,
            horizon_end=self.now + timedelta(days=30), is_active=True)

    def _job(self, erp, units, starts_in_hours=1):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, quantity=units, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        start = self.now + timedelta(hours=starts_in_hours)
        for i in range(units):
            p = Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}",
                                     part_type=self.pt, work_order=wo, step=self.step)
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=self.schedule, part=p, step=self.step,
                machine=self.machine, start_time=start,
                end_time=start + timedelta(hours=1))
        return wo

    def _stock(self, qty):
        return MaterialLot.objects.create(
            tenant=self.tenant, material=self.seal, lot_number="L1",
            quantity=Decimal(str(qty)), quantity_remaining=Decimal(str(qty)),
            unit_of_measure="EA", received_date=timezone.localdate(),
            received_by=self.user, status='ACCEPTED')

    def test_one_material_across_jobs_collapses_to_one_row(self):
        """The whole point of the sheet. Two jobs needing seals is one trip to the
        seal bin, not two."""
        self._job("WO-A", units=3)
        self._job("WO-B", units=2)
        self._stock(100)
        rows = consolidated_pick(self.tenant)['materials']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['material'], "Seal Kit")
        self.assertEqual(rows[0]['needed'], 10.0)      # (3 + 2) units x 2 per unit

    def test_every_row_carries_its_drops(self):
        """Batching costs a sortation step; without the split the combined quantity
        can't be delivered."""
        self._job("WO-A", units=3)
        self._job("WO-B", units=2)
        self._stock(100)
        row = consolidated_pick(self.tenant)['materials'][0]
        drops = {(d['erp_id'], d['qty']) for d in row['drops']}
        self.assertEqual(drops, {("WO-A", 6.0), ("WO-B", 4.0)})
        self.assertEqual(sum(d['qty'] for d in row['drops']), row['needed'])

    def test_shortage_is_against_the_combined_need(self):
        """Per-job planning hands the same lot to every job and each looks covered.
        Against the combined total, the shortage is real and visible once."""
        self._job("WO-A", units=3)
        self._job("WO-B", units=2)
        self._stock(6)                                  # need 10, have 6
        row = consolidated_pick(self.tenant)['materials'][0]
        self.assertEqual(row['short'], 4.0)

    def test_no_active_schedule_says_so(self):
        ScheduleResult.objects.filter(pk=self.schedule.pk).update(is_active=False)
        out = consolidated_pick(self.tenant)
        self.assertEqual(out['materials'], [])
        self.assertIn("solve", out['note'].lower())
