"""Staging pick list — what to put at each bench before the operator arrives.

The scheduler makes time-specific promises; if material isn't at the bench when a job
starts, the plan is wrong within the hour and people stop trusting the board. This is
the surface that makes the schedule executable rather than aspirational.

The behaviours worth pinning are the ones that would quietly produce a wrong pick
list: per-part tasks must collapse to per-job rows, material must scale to the units
arriving AT THIS STATION rather than the work order's whole quantity, and outside
processing must not appear (it goes to a vendor, not a bench).
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
from Tracker.services.mes.staging import set_staged, staging_list
from Tracker.tests.base import TenantContextMixin


class StagingListTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="ST", slug="staging", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="st-op", email="st@c.test", password="x", tenant=self.tenant)

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

    def _job(self, erp, units, starts_in_hours=1, step=None):
        step = step or self.step
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, quantity=units, process=self.process,
            workorder_status=WorkOrderStatus.IN_PROGRESS)
        start = self.now + timedelta(hours=starts_in_hours)
        for i in range(units):
            p = Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}",
                                     part_type=self.pt, work_order=wo, step=step)
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=self.schedule, part=p, step=step,
                machine=self.machine, start_time=start,
                end_time=start + timedelta(hours=1))
        return wo

    def _stock(self, qty):
        return MaterialLot.objects.create(
            tenant=self.tenant, material=self.seal, lot_number="L1",
            quantity=Decimal(str(qty)), quantity_remaining=Decimal(str(qty)),
            unit_of_measure="EA", received_date=timezone.localdate(),
            received_by=self.user, status='ACCEPTED')

    def test_per_part_tasks_collapse_to_one_job_per_station(self):
        """The solver writes a task per PART; a handler stages per JOB. Five rows for
        one job would be five trips to the crib."""
        self._job("WO-A", units=5)
        out = staging_list(self.tenant)
        station = out['stations'][0]
        self.assertEqual(station['name'], "Teardown Bay")
        self.assertEqual(len(station['jobs']), 1)
        self.assertEqual(station['jobs'][0]['units'], 5)

    def test_material_scales_to_the_units_arriving_here(self):
        """2 per unit x 5 units = 10 — scaled to what lands at this station, not the
        work order's total, or a lot arriving in batches over-stages the first one."""
        self._job("WO-A", units=5)
        self._stock(100)
        m = staging_list(self.tenant)['stations'][0]['jobs'][0]['materials'][0]
        self.assertEqual(m['material'], "Seal Kit")
        self.assertEqual(m['needed'], 10.0)
        self.assertEqual(m['short'], 0.0)

    def test_a_shortage_is_reported_against_on_hand(self):
        self._job("WO-A", units=5)
        self._stock(4)
        job = staging_list(self.tenant)['stations'][0]['jobs'][0]
        self.assertEqual(job['materials'][0]['short'], 6.0)
        self.assertEqual(job['short_count'], 1)

    def test_work_beyond_the_window_is_not_staged(self):
        """Staging is a shift-horizon activity — a job 40 hours out is not this
        handler's problem."""
        self._job("WO-SOON", units=1, starts_in_hours=2)
        self._job("WO-LATER", units=1, starts_in_hours=40)
        out = staging_list(self.tenant, hours=8)
        erps = [j['erp_id'] for s in out['stations'] for j in s['jobs']]
        self.assertEqual(erps, ["WO-SOON"])

    def test_outside_processing_is_not_staged(self):
        """An OSP step ships to a vendor; there is no bench to stage."""
        osp_wc = WorkCenter.objects.create(tenant=self.tenant, name="OSP Dispatch",
                                           code="OSP")
        osp_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Coating", step_type="TASK",
            work_center=osp_wc, is_outside_process=True)
        ProcessStep.objects.create(process=self.process, step=osp_step, order=2)
        self._job("WO-OSP", units=2, step=osp_step)
        out = staging_list(self.tenant)
        self.assertEqual([s['name'] for s in out['stations']], [])

    def test_narrowing_to_one_station(self):
        other = WorkCenter.objects.create(tenant=self.tenant, name="Wash Line",
                                          code="WL")
        wash = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Wash", step_type="TASK",
            work_center=other)
        ProcessStep.objects.create(process=self.process, step=wash, order=2)
        self._job("WO-TD", units=1)
        self._job("WO-WASH", units=1, step=wash)

        out = staging_list(self.tenant, work_center_id=str(self.wc.id))
        self.assertEqual([s['name'] for s in out['stations']], ["Teardown Bay"])

    def test_jobs_are_ordered_by_when_they_start(self):
        self._job("WO-THIRD", units=1, starts_in_hours=5)
        self._job("WO-FIRST", units=1, starts_in_hours=1)
        jobs = staging_list(self.tenant)['stations'][0]['jobs']
        self.assertEqual([j['erp_id'] for j in jobs], ["WO-FIRST", "WO-THIRD"])

    def test_no_active_schedule_says_so_rather_than_returning_nothing(self):
        """An empty list and 'there is no plan' mean different things to a handler."""
        ScheduleResult.objects.filter(pk=self.schedule.pk).update(is_active=False)
        out = staging_list(self.tenant)
        self.assertEqual(out['stations'], [])
        self.assertIn("solve", out['note'].lower())


class MarkStagedTests(StagingListTests):
    """Marking a job's material as staged at its bench."""

    def _first_job(self):
        out = staging_list(self.tenant)
        return out['stations'][0]['jobs'][0]

    def test_marking_staged_records_who_and_when(self):
        self._job("WO-A", units=2)
        j = self._first_job()
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)

        after = self._first_job()
        self.assertIsNotNone(after['staged_at'])
        self.assertEqual(after['staged_by'], self.user.get_full_name() or self.user.username)

    def test_staging_survives_a_re_solve(self):
        """The reason this isn't a flag on ScheduledTask. The solver replaces every
        task row each run; staging recorded there would vanish the moment a planner
        re-solved, throwing away work already done on the floor."""
        from Tracker.models import ScheduledTask

        wo = self._job("WO-A", units=2)
        j = self._first_job()
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)

        # Simulate a re-solve: every scheduled task is replaced.
        ScheduledTask.objects.filter(schedule=self.schedule).delete()
        now = timezone.now()
        for p in wo.parts.all():
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=self.schedule, part=p, step=self.step,
                machine=self.machine, start_time=now + timedelta(hours=2),
                end_time=now + timedelta(hours=3))

        self.assertIsNotNone(self._first_job()['staged_at'],
                             "staging must outlive the tasks it was recorded against")

    def test_unstaging_clears_it(self):
        self._job("WO-A", units=1)
        j = self._first_job()
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)
        set_staged(self.tenant, j['work_order_id'], j['step_id'], False, self.user)
        after = self._first_job()
        self.assertIsNone(after['staged_at'])
        self.assertIsNone(after['staged_by'])

    def test_marking_twice_is_idempotent(self):
        """Two handlers working the same cart, or a double tap, must not create a
        second record or move the timestamp on work already staged."""
        from Tracker.models import MaterialStaging

        self._job("WO-A", units=1)
        j = self._first_job()
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)
        first = self._first_job()['staged_at']
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)

        self.assertEqual(self._first_job()['staged_at'], first)
        self.assertEqual(MaterialStaging.objects.filter(tenant=self.tenant).count(), 1)

    def test_station_reports_staged_progress(self):
        self._job("WO-A", units=1)
        self._job("WO-B", units=1)
        j = self._first_job()
        set_staged(self.tenant, j['work_order_id'], j['step_id'], True, self.user)
        station = staging_list(self.tenant)['stations'][0]
        self.assertEqual(station['staged_count'], 1)
        self.assertEqual(len(station['jobs']), 2)
