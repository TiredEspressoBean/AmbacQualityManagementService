"""Tool and fixture life (gate redesign S5, user decisions 2026-11-11).

- An equipment type with a life-limit definition is life-limited; each item is
  tracked. A step's authored tool goes on the visit at start and is counted:
  parts = distinct parts, cycles = a load once, hours = at completion.
- The opt-in tool_life gate refuses a start on a tool at its hard limit; an extension
  or a reset clears it. No supervisor override.
- A work instruction capturing a tool at its hard limit is refused.
- A Fixture with an equipment type schedules as many as are in service and within
  life; one without keeps its typed quantity.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from Tracker.models import (
    Equipments, EquipmentType, Fixture, Parts, PartTypes, StepEquipmentAffinity,
    StepExecution, Steps, WorkOrder,
)
from Tracker.models.life_tracking import LifeLimitDefinition, LifeTracking
from Tracker.services.life_tracking import tool_life
from Tracker.services.mes.gates import GateCode, StartRefused
from Tracker.services.mes.lifecycle import start_execution
from Tracker.services.mes.step_gates import FLOOR_GATES, set_step_gates
from Tracker.tests.base import TenantTestCase


class ToolLifeTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.die_type = EquipmentType.objects.create(tenant=t, name="Press die")
        self.die = Equipments.objects.create(tenant=t, name="Die #1", equipment_type=self.die_type)
        self.pt = PartTypes.objects.create(tenant=t, name="Nozzle body")
        self.step = Steps.objects.create(tenant=t, name="Press", part_type=self.pt)
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES] + [{'gate': 'tool_life'}])
        self.step = Steps.objects.get(pk=self.step.pk)
        StepEquipmentAffinity.objects.create(tenant=t, step=self.step, equipment=self.die,
                                             affinity=StepEquipmentAffinity.Affinity.DIALED_IN)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-TL", quantity=3,
                                           workorder_status="IN_PROGRESS")
        self.parts = [Parts.objects.create(tenant=t, ERP_id=f"TL-{i}", part_type=self.pt,
                                           work_order=self.wo, step=self.step,
                                           part_status="IN_PROGRESS") for i in range(3)]

    def _limit(self, unit, hard, soft=None):
        return LifeLimitDefinition.objects.create(
            tenant=self.tenant_a, name=f"Die {unit}", unit=unit, unit_label=unit.title(),
            hard_limit=Decimal(hard), soft_limit=Decimal(soft) if soft is not None else None,
            equipment_type=self.die_type)

    def _visit(self, i, visit_number=1):
        return StepExecution.objects.create(tenant=self.tenant_a, part=self.parts[i], step=self.step,
                                            visit_number=visit_number, status="PENDING")

    def _tracking(self, definition):
        return LifeTracking.objects.for_object(self.die).get(definition=definition)

    def test_the_authored_tool_goes_on_the_visit_and_counts_distinct_parts(self):
        parts = self._limit('parts', 100)
        v = start_execution(self._visit(0), self.user_a)
        self.assertEqual([e.id for e in tool_life.visit_tools(v)], [self.die.id])
        start_execution(self._visit(1), self.user_a)
        self.assertEqual(self._tracking(parts).accumulated, Decimal(2))
        # a repeat visit of a part already counted isn't counted again
        StepExecution.objects.filter(pk=v.pk).update(status='COMPLETED', exited_at=timezone.now())
        start_execution(self._visit(0, visit_number=2), self.user_a)
        self.assertEqual(self._tracking(parts).accumulated, Decimal(2))

    def test_a_load_counts_one_cycle(self):
        from Tracker.services.dwi.batch_lifecycle import start_load
        cycles = self._limit('cycles', 100)
        start_load(work_order=self.wo, step=self.step, parts=self.parts, user=self.user_a)
        self.assertEqual(self._tracking(cycles).accumulated, Decimal(1))

    def test_hours_accrue_when_the_visit_completes(self):
        hours = self._limit('hours', 100)
        v = start_execution(self._visit(0), self.user_a)
        start = timezone.now() - timedelta(hours=2)
        StepExecution.objects.filter(pk=v.pk).update(started_at=start, exited_at=start + timedelta(hours=2))
        tool_life.on_complete(StepExecution.objects.get(pk=v.pk))
        self.assertEqual(self._tracking(hours).accumulated, Decimal('2.00'))

    def test_a_tool_at_its_hard_limit_refuses_the_start(self):
        parts = self._limit('parts', 1)
        start_execution(self._visit(0), self.user_a)  # the last part it has life for
        with self.assertRaises(StartRefused) as ctx:
            start_execution(self._visit(1), self.user_a)
        self.assertEqual([b.code for b in ctx.exception.blockers], [GateCode.TOOL_LIFE])
        self.assertIn("Die #1", ctx.exception.messages[0])
        # an approved extension clears it
        self._tracking(parts).apply_override(hard_limit=Decimal(5), reason="Re-inspected",
                                             approved_by=self.user_a)
        start_execution(self._visit(1), self.user_a)

    def test_a_reset_clears_it(self):
        parts = self._limit('parts', 1)
        start_execution(self._visit(0), self.user_a)
        self._tracking(parts).reset(user=self.user_a, reason="Refurbished")
        start_execution(self._visit(1), self.user_a)

    def test_without_the_gate_row_the_start_goes_ahead(self):
        self._limit('parts', 1)
        set_step_gates(self.step, [{'gate': g} for g in FLOOR_GATES])
        self.step = Steps.objects.get(pk=self.step.pk)
        start_execution(self._visit(0), self.user_a)
        start_execution(self._visit(1), self.user_a)

    def test_the_soft_limit_notifies(self):
        from unittest import mock
        self._limit('parts', 10, soft=1)
        with mock.patch.object(tool_life, '_notify_soft_limit') as notify:
            start_execution(self._visit(0), self.user_a)
        notify.assert_called_once()

    def test_a_capture_refuses_a_tool_at_its_hard_limit(self):
        parts = self._limit('parts', 1)
        LifeTracking.for_object(self.die, parts, accumulated=Decimal(1))
        with self.assertRaisesMessage(ValidationError, "reached its life limit"):
            tool_life.capture(None, self.die, 'TOOL')

    # --- the Life section: reset / extend (P4, user ruling 2026-11-11)
    def test_the_refusal_leads_to_the_tools_page(self):
        self._limit('parts', 1)
        start_execution(self._visit(0), self.user_a)
        with self.assertRaises(StartRefused) as ctx:
            start_execution(self._visit(1), self.user_a)
        self.assertEqual(ctx.exception.blockers[0].to_dict()['link'],
                         f"/editor/equipment/{self.die.id}/edit")

    def test_a_reset_needs_a_reason_and_the_list_marks_superseded_limits(self):
        definition = self._limit('parts', 5)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(5))[0]
        definition.create_new_version(user=self.user_a, change_description="Raised", hard_limit=Decimal(8))
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.post(f"/api/LifeTracking/{tracking.id}/reset/", {}, format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        resp = self.client.get("/api/LifeTracking/for_object/",
                               {'content_type': 'tracker.equipments', 'object_id': str(self.die.id)})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r['definition_is_current'] for r in resp.json()], [False])

    # --- an extension is an approval request (user ruling 2026-11-11)
    def test_an_extension_waits_for_someone_else_to_approve_it(self):
        from Tracker.services.core.approval import add_approver, submit_approval_response
        from Tracker.services.life_tracking.extension import request_extension
        definition = self._limit('parts', 2)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(2))[0]
        approval = request_extension(tracking, self.user_a, hard_limit=5,
                                     reason="Re-inspected, edges within wear spec")
        tracking.refresh_from_db()
        self.assertEqual(tracking.pending_hard_limit, Decimal(5))
        self.assertEqual(tracking.effective_hard_limit, Decimal(2))  # not raised yet
        # The requester may even hold the authority: they still can't decide their own.
        add_approver(approval, self.user_a, is_required=False)
        with self.assertRaises(ValidationError):
            submit_approval_response(approval, self.user_a, "APPROVED", comments="mine")
        add_approver(approval, self.user_b)
        submit_approval_response(approval, self.user_b, "APPROVED", comments="Agreed")
        tracking.refresh_from_db()
        self.assertEqual(tracking.effective_hard_limit, Decimal(5))
        self.assertEqual(tracking.override_approved_by, self.user_b)
        self.assertIsNone(tracking.pending_hard_limit)

    def test_a_rejected_extension_changes_nothing(self):
        from Tracker.services.core.approval import add_approver, submit_approval_response
        from Tracker.services.life_tracking.extension import request_extension
        definition = self._limit('parts', 2)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(2))[0]
        approval = request_extension(tracking, self.user_a, hard_limit=5,
                                     reason="Re-inspected, edges within wear spec")
        add_approver(approval, self.user_b)
        submit_approval_response(approval, self.user_b, "REJECTED", comments="Edges worn")
        tracking.refresh_from_db()
        self.assertEqual(tracking.effective_hard_limit, Decimal(2))
        self.assertIsNone(tracking.pending_hard_limit)

    def test_the_inbox_routes_an_extension_to_the_tools_page(self):
        from Tracker.serializers.core import ApprovalRequestSerializer
        from Tracker.services.life_tracking.extension import request_extension
        definition = self._limit('parts', 2)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(2))[0]
        approval = request_extension(tracking, self.user_a, hard_limit=5,
                                     reason="Re-inspected, edges within wear spec")
        info = ApprovalRequestSerializer(approval).data['content_object_info']
        self.assertEqual(info['page'], f"/editor/equipment/{self.die.id}/edit")

    def test_the_direct_override_route_is_closed_for_life_limits(self):
        definition = self._limit('parts', 2)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(2))[0]
        self.authenticate_superuser(tenant=self.tenant_a)
        resp = self.client.post(f"/api/LifeTracking/{tracking.id}/apply_override/",
                                {'hard_limit': '9', 'reason': 'Straight past the approval tier'},
                                format='json')
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("approval request", resp.json()['detail'])
        tracking.refresh_from_db()
        self.assertIsNone(tracking.hard_limit_override)

    def test_an_extension_must_raise_the_limit_and_give_a_reason(self):
        from Tracker.services.life_tracking.extension import request_extension
        definition = self._limit('parts', 2)
        tracking = LifeTracking.for_object(self.die, definition, accumulated=Decimal(2))[0]
        with self.assertRaisesMessage(ValidationError, "raises the limit"):
            request_extension(tracking, self.user_a, hard_limit=2, reason="Re-inspected and fine")
        with self.assertRaisesMessage(ValidationError, "Say why"):
            request_extension(tracking, self.user_a, hard_limit=5, reason="ok")

    # --- scheduling capacity
    def test_a_typed_fixture_schedules_the_items_in_service_and_within_life(self):
        parts = self._limit('parts', 10)
        Equipments.objects.create(tenant=self.tenant_a, name="Die #2", equipment_type=self.die_type)
        Equipments.objects.create(tenant=self.tenant_a, name="Die #3", equipment_type=self.die_type,
                                  status='IN_MAINTENANCE')
        fixture = Fixture.objects.create(tenant=self.tenant_a, name="Press dies", kind='DIE',
                                         quantity=9, equipment_type=self.die_type)
        self.assertEqual(tool_life.fixture_capacity(fixture), 2)
        LifeTracking.for_object(self.die, parts, accumulated=Decimal(10))  # Die #1 worn out
        self.assertEqual(tool_life.fixture_capacity(fixture), 1)
        from Tracker.services.scheduling.data import get_fixture_availability
        self.assertEqual(get_fixture_availability(self.tenant_a)[fixture.id].quantity, 1)

    def test_an_untyped_fixture_keeps_its_quantity(self):
        fixture = Fixture.objects.create(tenant=self.tenant_a, name="NC program 12", kind='PROGRAM',
                                         quantity=3)
        self.assertEqual(tool_life.fixture_capacity(fixture), 3)
