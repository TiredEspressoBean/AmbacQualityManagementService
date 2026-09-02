"""Work-order release — the planner's authorization gate.

Two properties carry the whole feature and both are easy to break silently:

1. **AUTO must be a true no-op.** The gate is opt-in; a tenant that never turns it on
   must schedule exactly as it did before, released or not. A regression here empties
   every existing customer's board.
2. **The gate is advisory.** A failing check demands a written reason, never a refusal
   — a planner who knows the shortage is covered has to be able to proceed, and the
   override goes on the record rather than pushing people to fake the data.
"""
from datetime import time as dtime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from Tracker.models import (
    Equipments, OptimizationConfig, Parts, PartTypes, Processes, ProcessStep, Shift,
    Steps, StepTiming, Tenant, TrainingRequirement, TrainingType, WorkCenter, WorkOrder,
    WorkOrderStatus,
)
from Tracker.models.scheduling import ReleaseMode
from Tracker.services.mes.release import (
    ReleaseBlocked, bulk_release, evaluate_release, release_work_order,
    releasable_work_orders, unrelease_work_order,
)
from Tracker.services.scheduling.data import get_active_workorders
from Tracker.tests.base import TenantContextMixin


class WorkOrderReleaseTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Rel", slug="rel", tier="PRO")
        self.set_tenant_context(self.tenant)
        self.user = get_user_model().objects.create_user(
            username="rel-planner", email="rel@c.test", password="x", tenant=self.tenant,
            default_shift=Shift.objects.create(
                tenant=self.tenant, code="DAY", name="Day", start_time=dtime(8, 0),
                end_time=dtime(16, 0), days_of_week="0,1,2,3,4", is_active=True),
        )
        self.config = OptimizationConfig.objects.create(tenant=self.tenant)

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

    def _wo(self, erp="WO-1", qty=2, released=False):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=qty, process=self.process,
            expected_completion=timezone.localdate() + timedelta(days=10),
            released_at=timezone.now() if released else None)
        for i in range(qty):
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}",
                                 part_type=self.pt, work_order=wo, step=self.step)
        return wo

    def _manual(self):
        self.config.release_mode = ReleaseMode.MANUAL
        self.config.save(update_fields=["release_mode"])

    # --- the solver gate ---------------------------------------------------

    def test_auto_mode_schedules_unreleased_work(self):
        """The default must behave exactly as before the gate existed."""
        self._wo(erp="WO-AUTO", released=False)
        self.assertEqual(len(get_active_workorders(self.tenant)), 1)

    def test_manual_mode_hides_unreleased_work_from_the_solver(self):
        self._manual()
        self._wo(erp="WO-UNRELEASED", released=False)
        self.assertEqual(get_active_workorders(self.tenant), [])

    def test_manual_mode_schedules_released_work(self):
        self._manual()
        self._wo(erp="WO-RELEASED", released=True)
        self.assertEqual(len(get_active_workorders(self.tenant)), 1)

    def test_missing_config_falls_back_to_auto(self):
        """An unconfigured tenant must not have its whole board silently emptied."""
        OptimizationConfig.objects.filter(pk=self.config.pk).delete()
        self._wo(erp="WO-NOCFG", released=False)
        self.assertEqual(len(get_active_workorders(self.tenant)), 1)

    # --- readiness ---------------------------------------------------------

    def test_a_well_formed_work_order_is_ready(self):
        r = evaluate_release(self._wo())
        self.assertTrue(r.ok, r.blockers)

    def test_missing_routing_blocks(self):
        empty = Processes.objects.create(tenant=self.tenant, name="E", part_type=self.pt)
        wo = self._wo(erp="WO-NOROUTE")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)
        wo.refresh_from_db()
        r = evaluate_release(wo)
        self.assertFalse(r.ok)
        self.assertEqual([b['code'] for b in r.blockers], ['no_routing'])

    def test_missing_timings_block(self):
        StepTiming.objects.filter(step=self.step).update(
            cycle_time_minutes=0, setup_minutes=0, load_unload_per_piece=0)
        Steps.objects.filter(pk=self.step.pk).update(expected_duration=None)
        r = evaluate_release(self._wo(erp="WO-UNTIMED"))
        self.assertIn('no_timings', [b['code'] for b in r.blockers])

    def test_unstaffable_step_blocks(self):
        tt = TrainingType.objects.create(tenant=self.tenant, name="Torque")
        TrainingRequirement.objects.create(
            tenant=self.tenant, training_type=tt, step=self.step)
        r = evaluate_release(self._wo(erp="WO-UNSTAFFED"))
        self.assertIn('unstaffable', [b['code'] for b in r.blockers])

    def test_held_work_order_blocks(self):
        wo = self._wo(erp="WO-HELD")
        WorkOrder.objects.filter(pk=wo.pk).update(workorder_status=WorkOrderStatus.ON_HOLD)
        wo.refresh_from_db()
        self.assertIn('on_hold', [b['code'] for b in evaluate_release(wo).blockers])

    # --- releasing ---------------------------------------------------------

    def test_release_stamps_who_and_when(self):
        wo = self._wo()
        release_work_order(wo, self.user)
        wo.refresh_from_db()
        self.assertIsNotNone(wo.released_at)
        self.assertEqual(wo.released_by, self.user)
        self.assertEqual(wo.release_override_reason, "")

    def test_release_refuses_a_blocked_order_without_a_reason(self):
        empty = Processes.objects.create(tenant=self.tenant, name="E", part_type=self.pt)
        wo = self._wo(erp="WO-BLOCKED")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)
        wo.refresh_from_db()
        with self.assertRaises(ReleaseBlocked):
            release_work_order(wo, self.user)
        wo.refresh_from_db()
        self.assertIsNone(wo.released_at)

    def test_release_proceeds_with_an_override_and_records_the_reason(self):
        """Advisory, not blocking — the planner may know something the data doesn't,
        but the justification goes on the record."""
        empty = Processes.objects.create(tenant=self.tenant, name="E", part_type=self.pt)
        wo = self._wo(erp="WO-OVERRIDE")
        WorkOrder.objects.filter(pk=wo.pk).update(process=empty)
        wo.refresh_from_db()
        release_work_order(wo, self.user, override_reason="Routing lands Thursday")
        wo.refresh_from_db()
        self.assertIsNotNone(wo.released_at)
        self.assertEqual(wo.release_override_reason, "Routing lands Thursday")

    def test_a_clean_release_records_no_override_reason(self):
        """A reason passed on a ready order is noise, not a record — drop it."""
        wo = self._wo()
        release_work_order(wo, self.user, override_reason="just in case")
        wo.refresh_from_db()
        self.assertEqual(wo.release_override_reason, "")

    def test_re_releasing_keeps_the_original_timestamp(self):
        wo = self._wo()
        release_work_order(wo, self.user)
        wo.refresh_from_db()
        first = wo.released_at
        release_work_order(wo, self.user)
        wo.refresh_from_db()
        self.assertEqual(wo.released_at, first)

    def test_unrelease_clears_the_stamp_but_keeps_the_audit_trail(self):
        wo = self._wo()
        release_work_order(wo, self.user)
        unrelease_work_order(wo.__class__.objects.get(pk=wo.pk), self.user)
        wo.refresh_from_db()
        self.assertIsNone(wo.released_at)
        self.assertEqual(wo.released_by, self.user)  # who authorized it is history

    def test_release_marks_the_active_schedule_stale(self):
        from Tracker.models import ScheduleResult
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=30),
            is_active=True, is_stale=False)
        release_work_order(self._wo(), self.user)
        sched.refresh_from_db()
        self.assertTrue(sched.is_stale)

    # --- bulk --------------------------------------------------------------

    def test_bulk_release_is_per_order_not_all_or_nothing(self):
        """10 good + 2 blocked must release the 10 and report the 2."""
        ok = [self._wo(erp=f"WO-OK-{i}") for i in range(3)]
        empty = Processes.objects.create(tenant=self.tenant, name="E", part_type=self.pt)
        bad = self._wo(erp="WO-BAD")
        WorkOrder.objects.filter(pk=bad.pk).update(process=empty)

        results = bulk_release(self.tenant, [w.id for w in ok] + [bad.id], self.user)
        self.assertEqual(sum(1 for r in results if r['ok']), 3)
        self.assertEqual(sum(1 for r in results if not r['ok']), 1)
        for w in ok:
            w.refresh_from_db()
            self.assertIsNotNone(w.released_at)
        bad.refresh_from_db()
        self.assertIsNone(bad.released_at)

    def test_releasable_queue_excludes_released_and_closed_orders(self):
        self._wo(erp="WO-PENDING")
        self._wo(erp="WO-DONE-ALREADY", released=True)
        closed = self._wo(erp="WO-CLOSED")
        WorkOrder.objects.filter(pk=closed.pk).update(
            workorder_status=WorkOrderStatus.CANCELLED)
        self.assertEqual([w.ERP_id for w in releasable_work_orders(self.tenant)],
                         ["WO-PENDING"])

    # --- the diagnostic reads the gate -------------------------------------

    def test_unreleased_work_reads_as_not_released_only_under_manual_mode(self):
        """Under AUTO an unreleased order is unremarkable, so the panel must attribute
        its absence to the real cause — not to a gate that isn't switched on."""
        from Tracker.services.scheduling.diagnostics import diagnose_unscheduled

        self._wo(erp="WO-Q")
        auto = diagnose_unscheduled(self.tenant)['work_orders']
        self.assertEqual([r['reason'] for r in auto], ['not_solved'])

        self._manual()
        manual = diagnose_unscheduled(self.tenant)['work_orders']
        self.assertEqual([r['reason'] for r in manual], ['not_released'])

    def test_unreleased_work_is_flagged_even_while_the_old_schedule_still_covers_it(self):
        """Switching the gate on doesn't move bars until the next solve. An unreleased
        order that still *looks* scheduled is about to vanish, so warn now rather than
        after the planner watches it disappear."""
        from Tracker.models import ScheduledTask, ScheduleResult
        from Tracker.services.scheduling.diagnostics import diagnose_unscheduled

        wo = self._wo(erp="WO-DOOMED", qty=2)
        now = timezone.now()
        sched = ScheduleResult.objects.create(
            tenant=self.tenant, horizon_start=now, horizon_end=now + timedelta(days=30),
            is_active=True)
        for p in wo.parts.all():
            ScheduledTask.objects.create(
                tenant=self.tenant, schedule=sched, part=p, step=self.step,
                machine=self.machine, start_time=now, end_time=now + timedelta(hours=1))

        # Fully covered → invisible while the gate is off.
        self.assertEqual(diagnose_unscheduled(self.tenant)['work_orders'], [])

        self._manual()
        rows = diagnose_unscheduled(self.tenant)['work_orders']
        self.assertEqual([r['reason'] for r in rows], ['not_released'])
        self.assertEqual(rows[0]['scheduled_units'], 2)  # still on the board — for now
