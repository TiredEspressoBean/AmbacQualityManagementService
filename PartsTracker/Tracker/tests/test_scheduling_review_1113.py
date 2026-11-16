"""Scheduling review 2026-11-13 (fixed before the push): the plan, the work queue and the
start gate agree on what can run.

1. A tooling resource with none available cuts its steps, not the whole solve.
2. With a stale plan, the start gate and the queue fall back to an authored machine
   that can run — not the one that left service.
3. The work queue counts only parts that can start, and says why a row is blocked.
4. A part put on hold, and a first-piece decision, mark the plan stale.
5. Rough-cut capacity counts only machines that can run.
6. An ended deviation, and a part at its life limit, aren't planned as startable.
"""
from datetime import time as dtime, timedelta
from decimal import Decimal
from unittest import mock

from django.utils import timezone

from Tracker.models import (
    Equipments, EquipmentType, LifeLimitDefinition, LifeTracking, Parts, PartTypes,
    Processes, ProcessStep, ScheduleResult, Shift, StepEquipmentAffinity, Steps,
    StepTiming, User, WorkOrder, WorkOrderStatus,
)
from Tracker.services.scheduling.solver import solve_schedule
from Tracker.tests.base import TenantTestCase


class SchedulingReviewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Injector")
        self.process = Processes.objects.create(tenant=t, name="P", part_type=self.pt)
        self.machine = Equipments.objects.create(tenant=t, name="CNC-1", is_schedulable=True)
        self.step1 = Steps.objects.create(tenant=t, part_type=self.pt, name="Turn", step_type="TASK")
        self.step2 = Steps.objects.create(tenant=t, part_type=self.pt, name="Mill", step_type="TASK")
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        StepTiming.objects.create(tenant=t, step=self.step1, cycle_time_minutes=60)
        StepTiming.objects.create(tenant=t, step=self.step2, cycle_time_minutes=30)
        for step in (self.step1, self.step2):
            StepEquipmentAffinity.objects.create(
                tenant=t, step=step, equipment=self.machine,
                affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        shift = Shift.objects.create(tenant=t, name="Day", code="DAY", start_time=dtime(0, 0),
                                     end_time=dtime(23, 59), days_of_week="0,1,2,3,4,5,6",
                                     is_active=True)
        User.objects.create(username="op-rev", tenant=t, user_type='INTERNAL', is_active=True,
                            default_shift=shift)

    def _wo(self, erp, n=1, process=None):
        wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id=erp, workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=n, process=process or self.process, released_at=timezone.now())
        for i in range(n):
            Parts.objects.create(tenant=self.tenant, ERP_id=f"{erp}-P{i}", part_type=self.pt,
                                 work_order=wo, step=self.step1)
        return wo

    def _reason(self, erp):
        from Tracker.services.scheduling.diagnostics import diagnose_unscheduled
        return next(r for r in diagnose_unscheduled(self.tenant)['work_orders']
                    if r['erp_id'] == erp)

    def _second_machine(self):
        # Preferred, not eligible: an eligible machine is a candidate set, never the
        # authored default a start falls back to.
        m2 = Equipments.objects.create(tenant=self.tenant, name="CNC-2", is_schedulable=True)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant, step=self.step1, equipment=m2,
            affinity=StepEquipmentAffinity.Affinity.PREFERRED)
        return m2

    # 7 ------------------------------------------------------------------------
    def _first_piece_step(self, buyoff=45, cycle=None, scope='PER_WORKORDER'):
        from Tracker.services.mes.step_gates import set_gates_from_flags
        set_gates_from_flags(self.step1, requires_first_piece_inspection=True, fpi_scope=scope)
        updates = {'first_piece_buyoff_minutes': buyoff}
        if cycle is not None:
            updates['cycle_time_minutes'] = cycle
        StepTiming.objects.filter(step=self.step1).update(**updates)

    def _at(self, result, step):
        """{part ERP id: (start, end)} of the step's planned tasks."""
        return {t.part.ERP_id: (t.start_time, t.end_time)
                for t in result.tasks.filter(step=step).select_related('part')}

    def test_the_rest_of_a_run_waits_for_the_first_pieces_buy_off(self):
        self._first_piece_step(buyoff=45)
        self._wo("WO-FP", n=3)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        at = self._at(result, self.step1)
        head = min(at, key=lambda erp: at[erp][0])   # the first piece runs first
        head_end = at[head][1]
        rest = [erp for erp in at if erp != head]
        self.assertEqual(len(rest), 2, at)
        for erp in rest:
            self.assertGreaterEqual(at[erp][0], head_end + timedelta(minutes=45), at)

    def test_a_first_piece_already_passed_means_no_wait(self):
        from Tracker.models import FPIRecord, FPIStatus
        self._first_piece_step(buyoff=45)
        wo = self._wo("WO-FPOK", n=3)
        FPIRecord.objects.create(tenant=self.tenant, work_order=wo, step=self.step1,
                                 part_type=self.pt, status=FPIStatus.PASSED)
        at = self._at(solve_schedule(self.tenant), self.step1)
        self.assertEqual(len({s for s, _e in at.values()}), 1, at)   # one run together

    def test_a_per_shift_first_piece_waits_again_after_a_shift_change(self):
        """A run crossing a shift change makes the incoming shift's first piece, which
        waits its buy-off: the next step can't start until that wait too."""
        # Back-to-back shifts (06:00–18:00, 18:00–06:00) so the machine runs straight
        # through each change, and an unattended step so crew doesn't confine it: the
        # 20-hour rest of the run (2 × 10 h) has to cross a change.
        Shift.objects.filter(tenant=self.tenant).update(start_time=dtime(6, 0), end_time=dtime(18, 0))
        Shift.objects.create(tenant=self.tenant, name="Night", code="NIGHT", start_time=dtime(18, 0),
                             end_time=dtime(6, 0), days_of_week="0,1,2,3,4,5,6", is_active=True)
        self._first_piece_step(buyoff=45, cycle=600, scope='PER_SHIFT')
        StepTiming.objects.filter(step=self.step1).update(attention_type='unattended')
        self._wo("WO-FPSH", n=3)
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        turn = self._at(result, self.step1)
        mill = self._at(result, self.step2)
        last_turn_end = max(e for _s, e in turn.values())
        first_mill = min(s for s, _e in mill.values())
        self.assertGreaterEqual(first_mill, last_turn_end + timedelta(minutes=45), (turn, mill))

    def test_shift_changes_are_each_shift_runs_start(self):
        from Tracker.services.scheduling import calendars, data
        horizon = data.get_schedule_horizon(self.tenant)
        changes = calendars.get_shift_changes(self.tenant, horizon)
        self.assertTrue(changes)
        self.assertTrue(all(c > horizon.start for c in changes))
        self.assertEqual(len(changes), len(set(changes)))

    # 8 ------------------------------------------------------------------------
    def test_started_and_waiting_parts_are_separate_lots(self):
        """One first piece started and the rest waiting for its buy-off: the waiting
        parts keep their whole time; only the started one is a running remainder."""
        from types import SimpleNamespace as NS
        from Tracker.services.scheduling.solver import _lots
        part = lambda pid, started, elapsed=0.0: NS(  # noqa: E731
            part_id=pid, current_step_id="S1", individual=False, split_from_lot=False,
            in_progress=started, elapsed_minutes=elapsed)
        wo = NS(wo_id="W", parts=[part("a", True, 30.0), part("b", False), part("c", False)])
        lots = {lot['in_progress']: lot for lot in _lots(wo, {})}
        self.assertEqual((lots[True]['count'], lots[True]['elapsed']), (1, 30.0))
        self.assertEqual((lots[False]['count'], lots[False]['elapsed']), (2, 0.0))
        self.assertNotEqual(lots[True]['label'], lots[False]['label'])

    # 1 ------------------------------------------------------------------------
    def test_tooling_with_none_available_cuts_its_step_not_the_solve(self):
        from Tracker.models import Fixture
        fixture = Fixture.objects.create(tenant=self.tenant, name="Mill vise", quantity=0)
        fixture.required_by_steps.add(self.step2)
        self._wo("WO-TOOL")
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(set(result.tasks.values_list('step_id', flat=True)), {self.step1.id})
        row = self._reason("WO-TOOL")
        self.assertEqual(row['reason'], 'tooling_unavailable')
        self.assertIn("Mill vise", row['detail'])

    # 2 ------------------------------------------------------------------------
    def test_with_no_fresh_plan_a_start_runs_on_an_authored_machine_that_can(self):
        from Tracker.services.mes.parts import planned_production_machine
        m2 = self._second_machine()
        wo = self._wo("WO-STALE")
        Equipments.objects.filter(pk=self.machine.pk).update(status='OUT_OF_SERVICE')
        part = wo.parts.first()
        self.assertEqual(planned_production_machine(self.step1.id, part.id), m2)
        # Nothing can run: the preferred one, so the gate refuses with its reason.
        Equipments.objects.filter(pk=m2.pk).update(status='OUT_OF_SERVICE')
        self.assertEqual(planned_production_machine(self.step1.id, part.id), self.machine)

    def test_the_queue_names_the_gates_machine_when_the_plan_is_stale(self):
        m2 = self._second_machine()
        self._wo("WO-QSTALE")
        solve_schedule(self.tenant)
        self.machine.status = 'OUT_OF_SERVICE'
        self.machine.save(update_fields=['status'])   # marks the plan stale
        self.assertTrue(ScheduleResult.objects.filter(is_active=True, is_stale=True).exists())
        row = self._queue_row("WO-QSTALE")
        self.assertEqual(str(row['machine']), str(m2.id))
        self.assertEqual(row['readiness'], 'ready')

    # 3 ------------------------------------------------------------------------
    def _queue_row(self, erp):
        self.authenticate_superuser(self.tenant)
        r = self.client.get("/api/WorkQueue/", {"limit": 100})
        self.assertEqual(r.status_code, 200, r.content)
        rows = r.data['results'] if isinstance(r.data, dict) else r.data
        return next(x for x in rows if x['work_order_erp_id'] == erp)

    def test_the_queue_counts_only_parts_that_can_start_and_says_why_not(self):
        from Tracker.models import StepExecution
        wo = self._wo("WO-READY", n=2)
        for p in wo.parts.all():   # both waiting at Turn with an open visit
            StepExecution.objects.create(tenant=self.tenant, part=p, step=self.step1,
                                         status='PENDING', entered_at=timezone.now())
        self.assertEqual(self._queue_row("WO-READY")['qty_ready'], 2)
        Parts.objects.filter(pk=wo.parts.first().pk).update(part_status='ON_HOLD')
        self.assertEqual(self._queue_row("WO-READY")['qty_ready'], 1)
        Equipments.objects.filter(pk=self.machine.pk).update(status='IN_MAINTENANCE')
        row = self._queue_row("WO-READY")
        self.assertEqual(row['readiness'], 'blocked')
        self.assertIn("CNC-1", row['blocked_reason'])

    # 4 ------------------------------------------------------------------------
    def test_a_part_put_on_hold_marks_the_plan_stale(self):
        wo = self._wo("WO-HOLD")
        solve_schedule(self.tenant)
        part = wo.parts.first()
        part.part_status = 'ON_HOLD'
        part.save(update_fields=['part_status'])
        self.assertTrue(ScheduleResult.objects.filter(is_active=True, is_stale=True).exists())

    def test_a_first_piece_decision_marks_the_plan_stale(self):
        from Tracker.services.qms import fpi as fpi_service
        with mock.patch.object(fpi_service, '_fpi_payload_kwargs', return_value={}), \
                mock.patch('Tracker.services.qms.events.FpiDecidedPayload'), \
                mock.patch('Tracker.services.core.notifications.emit'), \
                mock.patch('Tracker.services.scheduling.staleness.mark_active_schedule_stale') as stale:
            fpi_service.notify_fpi_decided(mock.Mock(tenant_id=self.tenant.id, status='PASSED'))
        stale.assert_called_once_with(self.tenant.id)

    # 5 ------------------------------------------------------------------------
    def test_rough_cut_capacity_counts_only_machines_that_can_run(self):
        from Tracker.models import WorkCenter
        from Tracker.services.planning.rccp import _load_reference
        gauge_type = EquipmentType.objects.create(tenant=self.tenant, name="Calibrated",
                                                  requires_calibration=True)
        lapsed = Equipments.objects.create(tenant=self.tenant, name="CNC-Lapsed",
                                           is_schedulable=True, equipment_type=gauge_type)
        wc = WorkCenter.objects.create(tenant=self.tenant, name="Turning", code="TRN")
        wc.equipment.add(self.machine, lapsed)   # lapsed: never calibrated = overdue
        hours = _load_reference(self.tenant).wc_machine_hours[wc.id]
        self.assertEqual(sum(hours), 1)

    # 6 ------------------------------------------------------------------------
    def test_an_ended_deviation_is_not_planned(self):
        temp = Processes.objects.create(
            tenant=self.tenant, name="P-dev", part_type=self.pt, is_temporary=True,
            temporary_until=timezone.now().date() - timedelta(days=1))
        for order, step in ((1, self.step1), (2, self.step2)):
            ProcessStep.objects.create(process=temp, step=step, order=order)
        self._wo("WO-DEV", process=temp)
        self._wo("WO-OK")
        result = solve_schedule(self.tenant)
        self.assertIn(result.solver_status, ("OPTIMAL", "FEASIBLE"))
        planned = set(result.tasks.values_list('part__work_order__ERP_id', flat=True))
        self.assertEqual(planned, {"WO-OK"})
        self.assertEqual(self._reason("WO-DEV")['reason'], 'deviation_expired')

    def test_a_part_at_its_life_limit_is_not_planned(self):
        from Tracker.services.scheduling.data import get_active_workorders
        wo = self._wo("WO-LIFE", n=2)
        limited = wo.parts.first()
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Cycles", unit="cycles", unit_label="Cycles",
            hard_limit=Decimal(10))
        LifeTracking.for_object(limited, definition, accumulated=Decimal(10))
        parts = next(w for w in get_active_workorders(self.tenant) if w.erp_id == "WO-LIFE").parts
        self.assertEqual(len(parts), 1)
        self.assertNotEqual(parts[0].part_id, limited.id)
