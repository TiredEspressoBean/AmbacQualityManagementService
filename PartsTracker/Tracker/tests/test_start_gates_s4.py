"""The other start gates (gate redesign S4, user decisions 2026-11-11).

- A machine that is down (out of service, in maintenance or calibration, retired)
  refuses a start on it.
- A part ON_HOLD refuses Start Work; REWORK_NEEDED stays startable.
- Training required for the machine's type is checked at start.
- A life limit refuses at START, not when the part leaves the step.
- Reman cycles: a unit's remans are counted when its reman starts, from its history,
  and the start gate refuses one already at the limit.
- An expired material lot is refused at staging.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from Tracker.models import (
    Equipments, EquipmentType, MaterialLot, Parts, PartTypes, StepEquipmentAffinity,
    StepExecution, Steps, TrainingRecord, TrainingRequirement, TrainingType, WorkOrder,
)
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking, PartTypeLifeLimit
from Tracker.services.mes.gates import GateCode, StartRefused
from Tracker.services.mes.lifecycle import NotQualified, start_execution
from Tracker.tests.base import TenantTestCase


class StartGatesS4Tests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Housing")
        self.step = Steps.objects.create(tenant=t, name="Mill", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-S4", quantity=2,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=t, ERP_id="S4-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step,
                                         part_status="IN_PROGRESS")
        self.visit = StepExecution.objects.create(tenant=t, part=self.part, step=self.step,
                                                  visit_number=1, status="PENDING")
        self.operator = get_user_model().objects.create_user(
            username="s4-op", email="s4op@t.test", password="x", tenant=t)

    def _start(self, user=None):
        v = StepExecution.objects.get(pk=self.visit.pk)
        return start_execution(v, user or self.user_a)

    def _machine(self, status="IN_SERVICE", eq_type=None):
        machine = Equipments.objects.create(tenant=self.tenant_a, name="Haas VF-2",
                                            status=status, equipment_type=eq_type)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant_a, step=self.step, equipment=machine,
            affinity=StepEquipmentAffinity.Affinity.DIALED_IN)
        return machine

    def _codes(self, ctx):
        return [b.code for b in ctx.exception.blockers]

    # --- machine down
    def test_a_machine_in_maintenance_refuses_the_start(self):
        self._machine(status="IN_MAINTENANCE")
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.EQUIPMENT_DOWN])
        self.assertIn("Haas VF-2", ctx.exception.messages[0])

    def test_a_machine_in_service_starts(self):
        self._machine()
        self._start()

    def test_open_downtime_refuses_the_start_until_it_is_resolved(self):
        """User ruling 2026-11-16: downtime recorded on a machine (Report exception, or the
        operator's Machine problem — both post this) refuses starts on it until it is
        resolved; the andon waits on the downtime, routed as a machine down."""
        from unittest import mock
        machine = self._machine()
        self.authenticate_superuser(tenant=self.tenant_a)
        r = self.client.post("/api/DowntimeEvents/", {
            "equipment": str(machine.id), "category": "UNPLANNED", "reason": "Spindle drive fault",
            "description": "", "start_time": timezone.now().isoformat(), "work_order": None,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        with mock.patch('Tracker.services.mes.andon.notify_start_refused.apply_async') as send:
            resp = self.client.post(f"/api/StepExecutions/{self.visit.id}/claim/", {}, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        blocker = resp.json()['blockers'][0]
        self.assertEqual(blocker['code'], 'equipment_down')
        self.assertIn("Haas VF-2 is down (Spindle drive fault) since", blocker['message'])
        self.assertIn("until the downtime is resolved", blocker['message'])
        self.assertEqual(blocker['waiting_on'], "the machine's downtime to be resolved")
        _tenant, calls, _hour = send.call_args.kwargs['args']
        self.assertEqual([(c['gate'], c['cause']) for c in calls], [('equipment_down', 'downtime')])
        # Resolved: the machine runs work again.
        r = self.client.post(f"/api/DowntimeEvents/{r.json()['id']}/resolve/", {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self._start()

    def test_downtime_already_over_does_not_refuse(self):
        from Tracker.models import DowntimeEvent
        machine = self._machine()
        start = timezone.now() - timedelta(hours=3)
        DowntimeEvent.objects.create(tenant=self.tenant_a, equipment=machine, category="PLANNED",
                                     reason="Seal change", start_time=start,
                                     end_time=start + timedelta(hours=1), reported_by=self.user_a)
        self._start()

    def test_a_refused_start_is_kept_on_the_visit_until_it_starts(self):
        """Scheduling review item 11: the refusal is kept for planning, and a start
        clears it."""
        machine = self._machine(status="IN_MAINTENANCE")
        with self.assertRaises(StartRefused):
            self._start()
        v = StepExecution.objects.get(pk=self.visit.pk)
        self.assertEqual(v.last_refusal_code, 'equipment_down')
        self.assertIn("Haas VF-2", v.last_refusal_message)
        self.assertIsNotNone(v.last_refused_at)
        Equipments.objects.filter(pk=machine.pk).update(status="IN_SERVICE")
        self._start()
        v.refresh_from_db()
        self.assertEqual((v.last_refusal_code, v.last_refusal_message, v.last_refused_at),
                         ('', '', None))

    def test_a_refused_start_with_no_visit_leaves_the_waiting_visit_holding_it(self):
        """Session's walk 2026-11-16: a part Add Parts placed at its first step has no
        visit; a refused start rolled back the one it made, so nothing held the
        refusal. Now, after the request, the part gets the PENDING visit its arrival
        would have made, with the refusal on it."""
        placed = Parts.objects.create(tenant=self.tenant_a, ERP_id="S4-ADDED", part_type=self.pt,
                                      work_order=self.wo, step=self.step, part_status="PENDING")
        self._machine(status="IN_MAINTENANCE")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            "add_stepexecution", "view_stepexecution", "change_stepexecution",
            "full_tenant_access"])
        self.authenticate_as(self.user_a, self.tenant_a)
        r = self.client.post("/api/StepExecutions/", {
            "part": str(placed.id), "step": str(self.step.id), "status": "IN_PROGRESS",
        }, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        visits = StepExecution.objects.filter(part=placed, step=self.step)
        self.assertEqual(visits.count(), 1)
        v = visits.get()
        self.assertEqual((v.status, v.last_refusal_code), ('PENDING', 'equipment_down'))
        self.assertIn("Haas VF-2", v.last_refusal_message)

    def test_late_cause_names_a_refused_start(self):
        from datetime import timedelta
        from Tracker.models import ScheduleResult, ScheduledTask
        from Tracker.services.scheduling.late_cause import attribute_late_causes
        from Tracker.services.core.clock import plant_tz
        now = timezone.now()
        StepExecution.objects.filter(pk=self.visit.pk).update(
            last_refusal_code='equipment_down', last_refusal_message="Haas VF-2 is in maintenance.",
            last_refused_at=now)
        WorkOrder.objects.filter(pk=self.wo.pk).update(expected_completion=now.date() - timedelta(days=1))
        sched = ScheduleResult.objects.create(tenant=self.tenant_a, horizon_start=now,
                                              horizon_end=now + timedelta(days=7), is_active=True)
        task = ScheduledTask.objects.create(tenant=self.tenant_a, schedule=sched, part=self.part,
                                            step=self.step, start_time=now,
                                            end_time=now + timedelta(hours=1))
        attribute_late_causes(sched)
        task.refresh_from_db()
        self.assertEqual(task.late_cause,
                         f"Last refused at start ({now.astimezone(plant_tz()).date():%Y-%m-%d}): "
                         "Haas VF-2 is in maintenance.")

    def test_a_machine_past_its_calibration_refuses_the_start(self):
        mill = EquipmentType.objects.create(tenant=self.tenant_a, name="CNC mill",
                                            requires_calibration=True)
        self._machine(eq_type=mill)  # never calibrated = overdue
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.EQUIPMENT_DOWN])
        self.assertIn("calibration", ctx.exception.messages[0])
        self.assertEqual(ctx.exception.blockers[0].cause, 'calibration')

    # --- the machine chosen at Start Work
    def _second_machine(self, status="IN_SERVICE"):
        other = Equipments.objects.create(tenant=self.tenant_a, name="Haas VF-4", status=status)
        StepEquipmentAffinity.objects.create(
            tenant=self.tenant_a, step=self.step, equipment=other,
            affinity=StepEquipmentAffinity.Affinity.ELIGIBLE)
        return other

    def test_a_chosen_machine_is_judged_and_recorded(self):
        from Tracker.models.qms import StepExecutionEquipment
        self._machine(status="IN_MAINTENANCE")  # the planned one is down
        other = self._second_machine()
        v = StepExecution.objects.get(pk=self.visit.pk)
        start_execution(v, self.user_a, machine=other)  # runs on the other: starts
        links = StepExecutionEquipment.objects.filter(step_execution=v, role='PRODUCTION')
        self.assertEqual([l.equipment_id for l in links], [other.id])

    def test_a_chosen_machine_that_is_down_refuses(self):
        self._machine()
        other = self._second_machine(status="OUT_OF_SERVICE")
        with self.assertRaises(StartRefused) as ctx:
            start_execution(StepExecution.objects.get(pk=self.visit.pk), self.user_a, machine=other)
        self.assertIn("Haas VF-4", ctx.exception.messages[0])

    def test_a_machine_the_step_does_not_run_on_is_refused(self):
        from django.core.exceptions import ValidationError
        self._machine()
        stray = Equipments.objects.create(tenant=self.tenant_a, name="Lathe 9")
        with self.assertRaisesMessage(ValidationError, "isn't a machine"):
            start_execution(StepExecution.objects.get(pk=self.visit.pk), self.user_a, machine=stray)

    def test_a_per_equipment_first_piece_judges_the_planned_machine(self):
        """An unstarted visit with no machine recorded used to be 'unknown' — refused,
        and nothing could record one. The machine planned now decides its context."""
        from Tracker.models import FPIRecord
        from Tracker.services.mes.step_gates import FLOOR_GATES, set_step_gates
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES]
                       + [{'gate': 'first_piece', 'fpi_scope': 'PER_EQUIPMENT'}])
        machine = self._machine()
        self._start()
        record = FPIRecord.objects.get(work_order=self.wo, step=self.step)
        self.assertEqual(record.equipment_id, machine.id)

    # --- P5: the supervisor gates behind a floor refusal are named too
    def test_a_floor_refusal_also_names_the_training_still_needed(self):
        from unittest import mock
        from Tracker.services.mes.andon import call_for
        course = TrainingType.objects.create(tenant=self.tenant_a, name="Mill setup")
        TrainingRequirement.objects.create(tenant=self.tenant_a, training_type=course, step=self.step)
        self._machine(status="IN_MAINTENANCE")
        with self.assertRaises(StartRefused) as ctx:
            self._start(self.operator)
        codes = [(b.code, b.pending) for b in ctx.exception.blockers]
        self.assertEqual(codes, [(GateCode.EQUIPMENT_DOWN, False), (GateCode.TRAINING, True)])
        self.assertIn("Also needed once that's cleared: a supervisor (not qualified: Mill setup)",
                      ctx.exception.messages[1])
        self.assertTrue(ctx.exception.blockers[1].to_dict()['pending_behind_floor'])
        with mock.patch('Tracker.services.mes.andon.notify_start_refused.apply_async') as send:
            call_for(ctx.exception.blockers, self.tenant_a.id)
        _tenant, calls, _hour = send.call_args.kwargs['args']
        self.assertEqual([c['gate'] for c in calls], ['equipment_down'])  # the floor only

    def test_a_floor_refusal_with_a_supervisor_signed_in_doesnt_ask_for_one(self):
        """P5 walk 2026-11-16: the request carried valid supervisor credentials, yet the
        refusal said "Also needed once that's cleared: a supervisor". Judged with the
        supervisor, the floor refusal stands alone."""
        course = TrainingType.objects.create(tenant=self.tenant_a, name="Mill setup")
        TrainingRequirement.objects.create(tenant=self.tenant_a, training_type=course, step=self.step)
        self._machine(status="IN_MAINTENANCE")
        supervisor = get_user_model().objects.create_user(
            username="s4-sup", email="s4sup@t.test", password="sup-pass", tenant=self.tenant_a)
        self.grant_tenant_permissions(supervisor, self.tenant_a, ["override_training_gate"])
        self.grant_tenant_permissions(self.operator, self.tenant_a, [
            "view_stepexecution", "change_stepexecution", "add_stepexecution", "full_tenant_access"])
        self.authenticate_as(self.operator, self.tenant_a)
        resp = self.client.post(f"/api/StepExecutions/{self.visit.id}/claim/", {
            'override_email': "s4sup@t.test", 'override_password': "sup-pass",
            'override_reason': "Covering the shift"}, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        blockers = resp.json()['blockers']
        self.assertEqual([b['code'] for b in blockers], ['equipment_down'])
        self.assertNotIn("Also needed", resp.json()['detail'])

    # --- one open visit per part and step (gate walk 2026-11-12, D1)
    def test_a_create_for_a_part_with_an_open_visit_starts_that_visit(self):
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.post("/api/StepExecutions/", {
            'part': str(self.part.id), 'step': str(self.step.id), 'status': 'IN_PROGRESS',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['id'], str(self.visit.id))
        open_visits = StepExecution.objects.filter(part=self.part, step=self.step,
                                                   exited_at__isnull=True)
        self.assertEqual(open_visits.count(), 1)
        self.assertEqual(open_visits.first().status, 'IN_PROGRESS')

    # --- the andon
    def test_a_refused_start_at_the_api_calls_whoever_clears_it(self):
        from unittest import mock
        Parts.objects.filter(pk=self.part.pk).update(part_status="ON_HOLD")
        self.authenticate_superuser(tenant=self.tenant_a)
        with mock.patch('Tracker.services.mes.andon.notify_start_refused.apply_async') as send:
            resp = self.client.post(f"/api/StepExecutions/{self.visit.id}/claim/", {}, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.json()['blockers'][0]['waiting_on'], "the part's hold to be released")
        self.assertNotIn(".;", resp.json()['detail'])
        self.assertIs(resp.json()['blockers'][0]['pending_behind_floor'], False)  # a boolean
        tenant_id, calls, _hour = send.call_args.kwargs['args']
        self.assertEqual(tenant_id, str(self.tenant_a.id))
        self.assertEqual([c['gate'] for c in calls], ['part_on_hold'])
        self.assertEqual(calls[0]['part_number'], "S4-1")

    def test_a_first_piece_refusal_calls_nobody(self):
        from unittest import mock
        from Tracker.services.mes.andon import call_for
        from Tracker.services.mes.gates import Blocker
        with mock.patch('Tracker.services.mes.andon.notify_start_refused.apply_async') as send:
            call_for([Blocker(GateCode.FIRST_PIECE_PENDING, "waiting")], self.tenant_a.id)
        send.assert_not_called()

    def test_the_andon_calls_render_what_is_held_and_link_to_the_work_order(self):
        """start.refused and fpi.requested have their own templates: the generic one
        rendered 'Quality event fired at now.' with no link."""
        from dataclasses import asdict
        from django.template import Context, Template
        from Tracker.services.core.notifications.system_templates import (
            FPI_DECIDED, FPI_REQUESTED, START_REFUSED, TOOL_LIFE_WARNING,
        )
        from Tracker.services.mes.events import StartRefusedPayload, ToolLifeWarningPayload
        from Tracker.services.qms.events import FpiDecidedPayload, FpiRequestedPayload
        tool = asdict(ToolLifeWarningPayload.sample())
        url = Template(TOOL_LIFE_WARNING['in_app']['action_url_template']).render(Context({'payload': tool}))
        self.assertEqual(url, f"/editor/equipment/{tool['equipment_id']}/edit")
        for spec, payload in ((START_REFUSED, StartRefusedPayload.sample()),
                              (FPI_REQUESTED, FpiRequestedPayload.sample()),
                              (FPI_DECIDED, FpiDecidedPayload.sample())):
            ctx = Context({'payload': asdict(payload), 'branding': {}})
            in_app = spec['in_app']
            subject = Template(in_app['subject']).render(ctx)
            url = Template(in_app['action_url_template']).render(ctx)
            self.assertNotIn('event', subject.lower())
            self.assertEqual(url, f"/workorder/{payload.work_order_id}/control")
        # Subjects render as plain text (render.py), so not escaped.
        start = Template(START_REFUSED['in_app']['subject']).render(
            Context({'payload': asdict(StartRefusedPayload.sample())}, autoescape=False))
        self.assertIn("WO-2026-0007-001", start)
        self.assertIn("the work order's hold to clear", start)
        # QA's call names the pieces to inspect.
        waiting = Template(FPI_REQUESTED['in_app']['body_text']).render(
            Context({'payload': asdict(FpiRequestedPayload.sample())}, autoescape=False))
        self.assertIn("WO-2026-0007-001, WO-2026-0007-002", waiting)

    def test_the_starter_rules_route_each_gate(self):
        from Tracker.services.core.notifications.system_rules import list_starter_rule_specs
        rules = {r['conditions_source']: r['recipient_group_names']
                 for r in list_starter_rule_specs() if r['event_code'] == 'start.refused'}
        self.assertEqual(rules['payload.gate == "work_order_not_workable"'], ["Production Manager"])
        self.assertNotIn('payload.gate == "first_piece_pending"', rules)
        # A machine past its calibration also calls QA (P1 walk, 2026-11-12).
        self.assertEqual(rules['payload.gate == "equipment_down" && payload.cause == "calibration"'],
                         ["QA Manager"])

    def test_a_calibration_lapse_waits_on_calibration_and_says_so(self):
        """P1 walk 2026-11-12: a machine past its calibration read 'waiting on the machine
        to return to service'; it waits on calibration, and the andon payload says why."""
        from Tracker.services.mes.andon import _payload
        from Tracker.services.mes.gates import Blocker, GateCode
        cal = Blocker(GateCode.EQUIPMENT_DOWN, "Lathe is past its calibration", cause='calibration')
        down = Blocker(GateCode.EQUIPMENT_DOWN, "Lathe is in maintenance")
        self.assertEqual(cal.to_dict()['waiting_on'], "the machine to be calibrated")
        self.assertEqual(down.to_dict()['waiting_on'], "the machine to return to service")
        self.assertEqual(_payload(cal, self.tenant_a.id)['cause'], 'calibration')
        self.assertEqual(_payload(down, self.tenant_a.id)['cause'], '')
        # A call queued before `cause` existed still builds its payload (the P1 re-walk
        # lost six calls to "missing 1 required positional argument: 'cause'").
        from Tracker.services.mes.events import StartRefusedPayload
        old_shape = _payload(down, self.tenant_a.id)
        old_shape.pop('cause')
        self.assertEqual(StartRefusedPayload(**old_shape).cause, '')

    # --- resume
    def test_resuming_your_own_visit_is_not_refused_by_a_start_only_gate(self):
        tracking = self._life(self.part, 10, 100)
        self._start()
        tracking.increment(200)  # the limit lapses mid-visit
        self._start()            # going back to it: not refused
        Parts.objects.filter(pk=self.part.pk).update(part_status="ON_HOLD")
        with self.assertRaises(StartRefused):
            self._start()        # a hold still stops it

    def test_an_ended_visit_is_not_started_again(self):
        from django.core.exceptions import ValidationError
        StepExecution.objects.filter(pk=self.visit.pk).update(status='ROLLED_BACK',
                                                              exited_at=timezone.now())
        with self.assertRaisesMessage(ValidationError, "has ended"):
            self._start()

    def test_a_revised_limit_judges_by_its_current_version(self):
        tracking = self._life(self.part, 100, 100)
        definition = tracking.definition
        definition.create_new_version(user=self.user_a, change_description="Raised after test",
                                      hard_limit=Decimal(150))
        self._start()  # the old version's tracking no longer refuses

    # --- part on hold
    def test_a_part_on_hold_refuses_start_work(self):
        Parts.objects.filter(pk=self.part.pk).update(part_status="ON_HOLD")
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.PART_ON_HOLD])

    def test_rework_needed_stays_startable(self):
        Parts.objects.filter(pk=self.part.pk).update(part_status="REWORK_NEEDED")
        self._start()

    # --- machine-type training
    def test_training_for_the_machines_type_is_checked_at_start(self):
        mill = EquipmentType.objects.create(tenant=self.tenant_a, name="5-axis mill")
        self._machine(eq_type=mill)
        course = TrainingType.objects.create(tenant=self.tenant_a, name="5-axis setup")
        TrainingRequirement.objects.create(tenant=self.tenant_a, training_type=course,
                                           equipment_type=mill)
        with self.assertRaises(NotQualified):
            self._start(self.operator)
        TrainingRecord.objects.create(tenant=self.tenant_a, user=self.operator,
                                      training_type=course, completed_date=date.today())
        self._start(self.operator)

    # --- life limit at start
    def _life(self, obj, accumulated, hard):
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant_a, name=f"Cycles {hard}", unit="cycles", unit_label="Cycles",
            hard_limit=Decimal(hard))
        return LifeTracking.for_object(obj, definition, accumulated=Decimal(accumulated))[0]

    def test_a_life_limit_refuses_at_start_not_release(self):
        self._life(self.part, 100, 100)
        with self.assertRaises(StartRefused) as ctx:
            self._start()
        self.assertEqual(self._codes(ctx), [GateCode.LIFE_LIMIT])
        from Tracker.services.mes.gates import release_blockers
        se = StepExecution.objects.get(pk=self.visit.pk)
        self.assertNotIn(GateCode.LIFE_LIMIT,
                         [b.code for b in release_blockers(self.step, se, self.wo)])

    def test_an_extension_lets_it_start(self):
        tracking = self._life(self.part, 100, 100)
        tracking.apply_override(hard_limit=Decimal(120), reason="Re-inspected",
                                approved_by=self.user_a)
        self._start()

    # --- reman cycles
    def _core(self, number, serial, disassembled=False):
        from Tracker.services.reman.core_part import create_core
        core = create_core(tenant=self.tenant_a, core_number=number, core_type=self.pt,
                           serial_number=serial, received_date=date.today(),
                           received_by=self.user_a,
                           work_order=None if disassembled else self.wo,
                           step=None if disassembled else self.step)
        if disassembled:
            type(core).objects.filter(pk=core.pk).update(
                status='DISASSEMBLED', disassembly_started_at=timezone.now() - timedelta(days=400))
        return core

    def _reman_limit(self, hard):
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant_a, name="Remans", unit="remans", unit_label="Remans",
            hard_limit=Decimal(hard))
        PartTypeLifeLimit.objects.create(tenant=self.tenant_a, part_type=self.pt,
                                         definition=definition)
        return definition

    def _core_visit(self, core):
        return StepExecution.objects.create(tenant=self.tenant_a, part=core.part, step=self.step,
                                            visit_number=1, status="PENDING")

    def test_a_reman_is_counted_when_it_starts(self):
        definition = self._reman_limit(3)
        self._core("C-OLD-1", "SN-77", disassembled=True)
        core = self._core("C-NEW", "SN-77")
        tracking = LifeTracking.objects.for_object(core).get(definition=definition)
        self.assertEqual(tracking.accumulated, Decimal(1))  # its history
        start_execution(self._core_visit(core), self.user_a)
        tracking.refresh_from_db()
        self.assertEqual(tracking.accumulated, Decimal(2))

    def test_the_part_page_shows_its_cores_limits(self):
        """A life_limit refusal leads to the part's page; a core's limits live on the
        core, so the part's life list includes them (what the gate judges)."""
        definition = self._reman_limit(3)
        core = self._core("C-PAGE", "SN-PG")
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.get("/api/LifeTracking/for_object/",
                               {'content_type': 'tracker.parts', 'object_id': str(core.part_id)})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r['definition'] for r in resp.json()], [str(definition.id)])
        self.assertEqual(resp.json()[0]['item_label'], "Core SN-PG")  # it's the core's

    def test_the_reman_that_reaches_the_limit_is_not_stopped_by_it(self):
        from Tracker.services.mes.gates import StartContext, floor_blockers
        self._reman_limit(2)
        self._core("C-OLD-1", "SN-99", disassembled=True)
        core = self._core("C-NEW", "SN-99")
        start_execution(self._core_visit(core), self.user_a)  # the 2nd reman: now at 2 of 2
        core.part.refresh_from_db()
        ctx = StartContext(part=core.part, step=self.step, work_order=self.wo, operator=self.user_a)
        self.assertEqual(floor_blockers(ctx), [])  # its next steps still start

    def test_a_unit_at_its_reman_limit_is_refused_before_teardown(self):
        self._reman_limit(2)
        self._core("C-OLD-1", "SN-88", disassembled=True)
        self._core("C-OLD-2", "SN-88", disassembled=True)
        core = self._core("C-NEW", "SN-88")
        with self.assertRaises(StartRefused) as ctx:
            start_execution(self._core_visit(core), self.user_a)
        self.assertEqual(self._codes(ctx), [GateCode.LIFE_LIMIT])
        core.refresh_from_db()
        self.assertEqual(core.status, 'RECEIVED')

    # --- expired lots at staging
    def test_an_expired_lot_is_refused_at_staging(self):
        from Tracker.services.life_tracking.shelf_life import attach_shelf_life
        from Tracker.services.mes.staging import record_pick
        today = timezone.now().date()
        lot = MaterialLot.objects.create(
            tenant=self.tenant_a, lot_number="LOT-OLD", material_type=self.pt,
            received_date=today, received_by=self.user_a, quantity=Decimal(10),
            quantity_remaining=Decimal(10), unit_of_measure="EA",
            manufacture_date=today - timedelta(days=400), expiration_date=today - timedelta(days=5))
        attach_shelf_life(lot)
        with self.assertRaisesMessage(ValueError, "shelf-life expired"):
            record_pick(self.tenant_a, self.wo.id, self.step.id, self.pt.id, 1,
                        [{'lot_id': str(lot.id), 'lot_number': lot.lot_number, 'qty': 1}],
                        self.user_a, kind='PART_TYPE')


class QuarantinedInProgressTests(TenantTestCase):
    """User rulings 2026-11-17: a part quarantined while in progress is held at its step
    (the floor's quarantine hold). The hold names the disposition and calls QA; the
    operator's Up next shows it held, then cleared once QA decides use as is."""

    def setUp(self):
        super().setUp()
        from Tracker.models import QuarantineDisposition
        t = self.tenant_a
        self.pt = PartTypes.objects.create(tenant=t, name="Housing")
        self.step = Steps.objects.create(tenant=t, name="Mill", part_type=self.pt)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-QH", quantity=1,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=t, ERP_id="QH-1", part_type=self.pt,
                                         work_order=self.wo, step=self.step,
                                         part_status="QUARANTINED")
        self.visit = StepExecution.objects.create(
            tenant=t, part=self.part, step=self.step, visit_number=1, status="IN_PROGRESS",
            assigned_to=self.user_a, started_at=timezone.now() - timedelta(minutes=30))
        self.disp = QuarantineDisposition.objects.create(tenant=t, part=self.part,
                                                         description="Torque out of spec")
        self.authenticate_superuser(self.tenant_a)

    def _queue_row(self):
        rows = self.client.get("/api/WorkQueue/").json()
        rows = rows["results"] if isinstance(rows, dict) else rows
        return next(r for r in rows if r["work_order_erp_id"] == "WO-QH")

    def test_the_hold_names_the_disposition_and_calls_qa(self):
        from unittest import mock
        from Tracker.services.mes.gates import release_blockers
        self.assertIn('quarantine_hold', set(self.step.requirements.values_list('gate', flat=True)))
        [hold] = [b for b in release_blockers(self.step, self.visit, self.wo)
                  if b.code == 'quarantine_hold']
        self.assertEqual(hold.message, f"QH-1 is quarantined — {self.disp.disposition_number} "
                                       "decides what happens to it; it moves on once that's decided.")
        with mock.patch('Tracker.services.mes.andon.notify_start_refused.apply_async') as send:
            r = self.client.post(f"/api/Parts/{self.part.id}/complete_step/", {}, format="json")
        self.assertEqual(r.json()["status"], "blocked", r.content)
        _tenant, calls, _hour = send.call_args.kwargs['args']
        self.assertEqual([c['gate'] for c in calls], ['part_quarantined'])

    def test_up_next_shows_it_held_then_cleared(self):
        from Tracker.models import QuarantineDisposition
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_workorder', 'view_steps', 'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        row = self._queue_row()
        self.assertEqual(row["mine_held_dispositions"], [self.disp.disposition_number])
        self.assertEqual(row["qty_mine_cleared"], 0)
        # QA decides use as is: the part is back in progress, the operator's to complete.
        QuarantineDisposition.objects.filter(pk=self.disp.pk).update(
            disposition_type="USE_AS_IS", current_state="CLOSED",
            decision_authorized_at=timezone.now())
        Parts.objects.filter(pk=self.part.pk).update(part_status="IN_PROGRESS")
        row = self._queue_row()
        self.assertEqual(row["mine_held_dispositions"], [])
        self.assertEqual(row["qty_mine_cleared"], 1)
