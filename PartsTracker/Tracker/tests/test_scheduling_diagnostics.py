"""Why isn't this on the board? — unscheduled-work diagnosis.

The value of this panel is that each work order gets ONE reason, and it's the one the
planner should act on. So the tests pin two things: that each cause is detected at all,
and that when several apply at once the *most actionable* one wins (a held WO reads as
held, not as "no timings"). A fully-scheduled order must never appear — a diagnostic
that cries wolf gets ignored.
"""
from datetime import date, time as dtime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments, Parts, PartTypes, Processes, ProcessStep, ScheduledTask, ScheduleResult,
    Shift, Steps, StepTiming, Tenant, TrainingRequirement, TrainingType, WorkCenter,
    WorkOrder, WorkOrderStatus,
)
from Tracker.services.scheduling.diagnostics import diagnose_unscheduled
from Tracker.tests.base import TenantContextMixin


class UnscheduledDiagnosisTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Diag", slug="diag", tier="PRO")
        self.set_tenant_context(self.tenant)
        get_user_model().objects.create_user(
            username="diag-op", email="diag@c.test", password="x", tenant=self.tenant,
            default_shift=Shift.objects.create(
                tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
                end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True),
        )
        self.wc = WorkCenter.objects.create(tenant=self.tenant, name="Cell A", code="A")
        self.machine = Equipments.objects.create(
            tenant=self.tenant, name="M-1", is_schedulable=True, runs_unattended=False)
        self.wc.equipment.add(self.machine)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="W", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Cut", step_type="TASK",
            work_center=self.wc)
        StepTiming.objects.create(tenant=self.tenant, step=self.step, cycle_time_minutes=60)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

    # --- helpers -----------------------------------------------------------

    def _wo(self, erp="WO-1", qty=2, process=True, status=WorkOrderStatus.IN_PROGRESS,
            start=None, step=True):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=status, quantity=qty,
            process=self.process if process else None,
            expected_completion=timezone.localdate() + timedelta(days=10),
            expected_start=start)
        for i in range(qty):
            Parts.objects.create(
                tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                work_order=wo, step=self.step if step else None)
        return wo

    def _schedule(self, cover=()):
        """An active schedule covering exactly the given parts."""
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=30),
            is_active=True)
        for p in cover:
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=sched, part=p, step=self.step,
                machine=self.machine, start_time=now, end_time=now + timedelta(hours=1))
        return sched

    def _reason(self, out, erp):
        return next(r['reason'] for r in out['work_orders'] if r['erp_id'] == erp)

    # --- the happy path ----------------------------------------------------

    def test_fully_scheduled_work_order_is_not_reported(self):
        """Every open unit on the board ⇒ nothing to explain. A diagnostic that lists
        healthy orders is noise."""
        wo = self._wo()
        self._schedule(cover=list(wo.parts.all()))
        out = diagnose_unscheduled(self.tenant)
        self.assertEqual(out['work_orders'], [])
        self.assertEqual(out['unscheduled_work_orders'], 0)

    def test_partially_scheduled_work_order_is_reported_with_counts(self):
        """Half the lot placed is still a gap — surface it with the unit counts so the
        planner sees the size of the miss, not just its existence."""
        wo = self._wo(qty=4)
        self._schedule(cover=list(wo.parts.all())[:2])
        row = diagnose_unscheduled(self.tenant)['work_orders'][0]
        self.assertEqual((row['open_units'], row['scheduled_units']), (4, 2))

    def test_completed_work_orders_are_excluded_entirely(self):
        """Finished work isn't 'unscheduled' — it's done."""
        self._wo(erp="WO-DONE", status=WorkOrderStatus.COMPLETED)
        self._schedule()
        self.assertEqual(diagnose_unscheduled(self.tenant)['work_orders'], [])

    # --- individual causes -------------------------------------------------

    def test_held_work_order_reads_as_on_hold(self):
        self._wo(erp="WO-HELD", status=WorkOrderStatus.ON_HOLD)
        self._schedule()
        out = diagnose_unscheduled(self.tenant)
        self.assertEqual(self._reason(out, "WO-HELD"), 'on_hold')

    def test_work_order_without_a_process_reads_as_no_process(self):
        self._wo(erp="WO-NOPROC", process=False)
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-NOPROC"),
                         'no_process')

    def test_all_units_finished_reads_as_nothing_left_to_work(self):
        wo = self._wo(erp="WO-SHIPPED")
        wo.parts.update(part_status='SHIPPED')
        self._schedule()
        row = next(r for r in diagnose_unscheduled(self.tenant)['work_orders']
                   if r['erp_id'] == "WO-SHIPPED")
        self.assertEqual((row['reason'], row['open_units']), ('no_open_units', 0))

    def test_process_with_no_steps_reads_as_no_routing(self):
        empty = Processes.objects.create(
            tenant=self.tenant, name="Empty", part_type=self.pt)
        wo = self._wo(erp="WO-NOROUTE")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-NOROUTE"),
                         'no_routing')

    def test_route_without_any_timing_reads_as_no_timings(self):
        """A step with no cycle, no setup and no expected duration sizes to zero
        minutes — the solver 'places' nothing useful, so say so."""
        StepTiming.objects.filter(step=self.step).update(
            cycle_time_minutes=0, setup_minutes=0, load_unload_per_piece=0)
        Steps.objects.filter(pk=self.step.pk).update(expected_duration=None)
        self._wo(erp="WO-UNTIMED")
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-UNTIMED"),
                         'no_timings')

    def test_release_beyond_the_horizon_reads_as_outside_horizon(self):
        self._wo(erp="WO-FUTURE", start=timezone.localdate() + timedelta(days=120))
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-FUTURE"),
                         'outside_horizon')

    def test_training_gated_step_with_no_certified_operator_reads_as_unstaffable(self):
        """The step needs a cert nobody rostered holds. (Also guards the id types:
        `find_unstaffable_steps` reports string step ids, the route carries UUIDs — a
        mismatch here silently reports every such order as 'not solved'.)"""
        tt = TrainingType.objects.create(tenant=self.tenant, name="Torque")
        TrainingRequirement.objects.create(
            tenant=self.tenant, training_type=tt, step=self.step)
        self._wo(erp="WO-UNSTAFFED")
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-UNSTAFFED"),
                         'unstaffable')

    def test_no_active_schedule_reads_as_not_solved(self):
        self._wo(erp="WO-NEW")
        out = diagnose_unscheduled(self.tenant)
        self.assertIsNone(out['schedule_id'])
        self.assertEqual(self._reason(out, "WO-NEW"), 'not_solved')

    def test_stale_schedule_reads_as_stale(self):
        """A stale schedule is a re-solve away from being right — that's a different
        (and much cheaper) fix than any of the data problems above."""
        self._wo(erp="WO-STALE")
        sched = self._schedule()
        ScheduleResult.objects.filter(pk=sched.pk).update(is_stale=True)
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-STALE"),
                         'stale_schedule')

    # --- precedence --------------------------------------------------------

    def test_hold_outranks_every_data_problem(self):
        """A held WO with no timings and a far-future release must still read as held:
        clearing the hold is the one action that changes anything."""
        StepTiming.objects.filter(step=self.step).update(
            cycle_time_minutes=0, setup_minutes=0, load_unload_per_piece=0)
        Steps.objects.filter(pk=self.step.pk).update(expected_duration=None)
        self._wo(erp="WO-BOTH", status=WorkOrderStatus.ON_HOLD,
                 start=timezone.localdate() + timedelta(days=120))
        self._schedule()
        self.assertEqual(self._reason(diagnose_unscheduled(self.tenant), "WO-BOTH"),
                         'on_hold')

    def test_every_row_carries_a_label_and_a_fix(self):
        """The panel is only useful if each row tells the planner what to DO."""
        self._wo(erp="WO-A", status=WorkOrderStatus.ON_HOLD)
        self._wo(erp="WO-B", process=False)
        self._schedule()
        rows = diagnose_unscheduled(self.tenant)['work_orders']
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertTrue(r['reason_label'] and r['detail'] and r['fix'])

    def test_counts_summarise_the_rows(self):
        self._wo(erp="WO-A", status=WorkOrderStatus.ON_HOLD)
        self._wo(erp="WO-B", status=WorkOrderStatus.ON_HOLD)
        self._wo(erp="WO-C", process=False)
        self._schedule()
        out = diagnose_unscheduled(self.tenant)
        self.assertEqual(out['counts'], {'on_hold': 2, 'no_process': 1})
        self.assertEqual(out['unscheduled_work_orders'], 3)
