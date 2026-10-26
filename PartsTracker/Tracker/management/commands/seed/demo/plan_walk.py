"""Planner exhibit for Plan vs actual (Planner track module 8): this morning's plan,
and how the floor ran against it.

Five single-part work orders on ORD-2024-PLAN, released and urgent so the solver puts
their Machining first on the lathe. A plan is solved, then dated to this morning (the
whole schedule moved back as a block, as if it had been solved at the start of the
shift). Four bodies are then run through Machining by Dave, through the services
(start_execution, submit_substep, advance_part_step), each against its own slot in
that plan:

    WO-PLAN-01  on time       started and finished within a few minutes of plan
    WO-PLAN-02  early         started and finished well ahead of its slot
    WO-PLAN-03  late          finished half an hour past its planned end
    WO-PLAN-04  very late     finished an hour and a half past its planned end
    WO-PLAN-05  never started its slot passed with nobody on it

The walk runs in seconds, so its visits are re-dated against their slots afterwards,
the way qa_walk dates a shift, and the plan-vs-actual stamp is re-run so it reads the
dated times. The planning seeder then solves today's plan over everything, so every
other track opens on a live plan made now.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from Tracker.models import (
    Orders, OrdersStatus, QualityReports, StepExecution, StepExecutionMeasurement,
    SubstepCompletion, SubstepResponse, WorkOrder, WorkOrderPriority, WorkOrderStatus,
)

from .qa_walk import DemoQaWalkSeeder, PROCESS_NAME

ORDER_NUMBER = 'ORD-2024-PLAN'
CUSTOMER_NAME = 'Great Lakes Diesel'
STEP = 'Machining'

# (work order, part, outcome, minutes from planned start to entry, minutes from
# planned end to exit). None for a slot nobody took.
PLAN_DAY = [
    ('WO-PLAN-01', 'INJ-PLAN-001', 'on time', 3, 5),
    ('WO-PLAN-02', 'INJ-PLAN-002', 'early', -20, -20),   # past the 15-min tolerance, inside the shift
    ('WO-PLAN-03', 'INJ-PLAN-003', 'late', 20, 30),
    ('WO-PLAN-04', 'INJ-PLAN-004', 'very late', 70, 90),
    ('WO-PLAN-05', 'INJ-PLAN-005', 'never started', None, None),
]

# The last slot ends this long before now once the plan is dated back, so every
# outcome above has happened (the very late one finishes before now).
CLEARANCE = timedelta(hours=1)


class DemoPlanWalkSeeder(DemoQaWalkSeeder):
    """Solves this morning's plan and walks the Planner's adherence exhibit."""

    def seed(self, companies, users, manufacturing=None):
        self.log("Walking the Planner's plan-vs-actual morning...")
        result = {'work_orders': [], 'outcomes': {}, 'dated_back': None}
        by_email = (users or {}).get('by_email', {})
        self.dave = by_email.get('dave.wilson@demo.ambac.com')
        self.mike = self.dave           # the walk helpers default to self.mike
        self.casey = by_email.get('casey.dual@demo.ambac.com')
        if not (self.dave and self.casey):
            self.log("  Warning: Dave or Casey missing; skipping.", warning=True)
            return result

        from Tracker.models import Companies, Processes, ProcessStep
        process = (Processes.objects.filter(tenant=self.tenant, name=PROCESS_NAME)
                   .order_by('-created_at').first())
        customer = Companies.objects.filter(tenant=self.tenant, name=CUSTOMER_NAME).first()
        if process is None or customer is None:
            self.log("  Warning: Injector Build or Great Lakes Diesel missing; skipping.",
                     warning=True)
            return result
        self.route = [ps.step for ps in
                      ProcessStep.objects.filter(process=process).select_related('step').order_by('order')]
        self.step = {s.name: s for s in self.route}
        part_type = self.route[0].part_type
        self.equipment = self._operational_equipment()

        order = Orders.objects.update_or_create(
            tenant=self.tenant, order_number=ORDER_NUMBER,
            defaults={'name': 'Great Lakes bodies - planner exhibit', 'company': customer,
                      'order_status': OrdersStatus.IN_PROGRESS,
                      'estimated_completion': (self.today + timedelta(days=5)).date()},
        )[0]
        parts = {}
        with transaction.atomic():
            for wo_id, serial, *_ in PLAN_DAY:
                wo = WorkOrder.objects.update_or_create(
                    tenant=self.tenant, ERP_id=wo_id,
                    defaults={'related_order': order, 'process': process,
                              'priority': WorkOrderPriority.URGENT,
                              'workorder_status': WorkOrderStatus.PENDING,
                              # Due today: urgent alone doesn't pull a job forward when
                              # it isn't late, and the plan then has to be dated back a
                              # day to put the slots behind us.
                              'expected_completion': self.today.date(),
                              'quantity': 1},
                )[0]
                parts[wo_id] = self._release(wo, part_type, serial)
                result['work_orders'].append(wo)

        # Manual release, as the plant runs (the planning phase sets it too, later): only
        # released work is planned, so the morning plan holds these five jobs.
        from Tracker.models import OptimizationConfig
        from Tracker.models.scheduling import ReleaseMode
        cfg, _ = OptimizationConfig.objects.get_or_create(tenant=self.tenant)
        if cfg.release_mode != ReleaseMode.MANUAL:
            cfg.release_mode = ReleaseMode.MANUAL
            cfg.save(update_fields=['release_mode'])

        schedule = self._solve_morning_plan()
        if schedule is None:
            return result
        from Tracker.models.scheduling import ScheduledTask
        result['morning_tasks'] = ScheduledTask.objects.filter(schedule=schedule).count()
        slots = self._slots(schedule, parts)
        if len(slots) != len(PLAN_DAY):
            self.log("  Warning: the plan didn't book every exhibit's Machining; skipping.",
                     warning=True)
            return result
        result['dated_back'] = self._date_back(schedule, slots)

        walk = {'override_count': 0}
        for wo_id, _serial, outcome, start_off, end_off in PLAN_DAY:
            result['outcomes'][wo_id] = outcome
            if start_off is None:
                continue
            part = parts[wo_id]
            self._run_step_for([part], STEP, walk, operator=self.dave)
            task = slots[wo_id]
            task.refresh_from_db()
            self._date_visit(part, task.start_time + timedelta(minutes=start_off),
                             task.end_time + timedelta(minutes=end_off))
        self.log(f"  Morning plan ({result.get('morning_tasks')} ops) dated back {result['dated_back']}; "
                 + ", ".join(f"{w}: {o}" for w, o in result['outcomes'].items()))
        return result

    def _release(self, wo, part_type, serial):
        from Tracker.services.mes.release import ReleaseBlocked, release_work_order
        part = self._parts(wo, part_type, [serial])[0]
        try:
            release_work_order(wo, self.casey)
        except ReleaseBlocked as e:
            release_work_order(wo, self.casey, override_reason=(
                f"Released for the planner's exhibit; blockers noted: {e}")[:500])
        return part

    def _solve_morning_plan(self):
        from Tracker.services.scheduling.preflight import LaborInfeasible
        from Tracker.services.scheduling.solver import solve_schedule
        try:
            return solve_schedule(self.tenant, time_limit_seconds=30)
        except LaborInfeasible as e:
            self.log(f"  Warning: no morning plan solved: {e}", warning=True)
            return None

    def _slots(self, schedule, parts):
        from Tracker.models.scheduling import ScheduledTask
        slots = {}
        for wo_id, part in parts.items():
            task = (ScheduledTask.objects.filter(schedule=schedule, part=part, step=self.step[STEP])
                    .first())
            if task is not None:
                slots[wo_id] = task
        return slots

    def _date_back(self, schedule, slots):
        """Move the whole plan back as a block, by whole days, so it reads as solved
        earlier and the last exhibit slot ended at least CLEARANCE ago. Whole days keep
        every op at the time of day the solver gave it, inside working hours: a shift of
        some hours put a body on the lathe at midnight."""
        import math
        from Tracker.models.scheduling import ScheduledTask, ScheduleResult
        latest_end = max(t.end_time for t in slots.values())
        needed = latest_end - timezone.now() + CLEARANCE
        delta = timedelta(days=max(1, math.ceil(needed / timedelta(days=1))))
        ScheduledTask.objects.filter(schedule=schedule).update(
            start_time=F('start_time') - delta, end_time=F('end_time') - delta)
        ScheduleResult.objects.filter(pk=schedule.pk).update(
            created_at=F('created_at') - delta,
            horizon_start=F('horizon_start') - delta, horizon_end=F('horizon_end') - delta)
        return delta

    def _date_visit(self, part, entered, exited):
        """Date the Machining visit the walk just made to its slot, with what was
        captured during it, then re-stamp plan vs actual from the dated visit."""
        from Tracker.services.scheduling.actuals import record_execution_actuals
        visit = (StepExecution.objects.filter(part=part, step=self.step[STEP])
                 .order_by('-entered_at').first())
        if visit is None:
            return
        captured = exited - timedelta(minutes=3)
        StepExecution.objects.filter(pk=visit.pk).update(
            entered_at=entered, started_at=entered, exited_at=exited)
        StepExecutionMeasurement.objects.filter(step_execution=visit).update(recorded_at=captured)
        SubstepResponse.objects.filter(step_execution=visit).update(responded_at=captured)
        SubstepCompletion.objects.filter(step_execution=visit).update(completed_at=captured)
        QualityReports.objects.filter(part=part, step=self.step[STEP]).update(created_at=captured)
        # The next visit (arrival at Precision Grinding) follows the dated exit.
        StepExecution.objects.filter(part=part, entered_at__gt=exited).exclude(pk=visit.pk).update(
            entered_at=exited + timedelta(minutes=5))
        visit.refresh_from_db()
        record_execution_actuals(visit)
