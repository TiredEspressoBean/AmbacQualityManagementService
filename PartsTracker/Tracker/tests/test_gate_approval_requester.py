"""A gate-raised approval has no requester, and its decision still reaches someone.

`_require_approval` recorded the incidental request user as the approval's
requester. Beyond the same mis-attribution as `_raise_capa_or_scar`, that had
a sharper consequence: `submit_approval_response` treats
``requested_by == approver`` as self-approval and blocks it unless the
template allows self-approval AND the approver writes a 10-char
justification. So the conflict-of-interest guard fired on coincidence —
whoever happened to save the threshold-crossing record, if they were also an
approver, got pushed down the self-approval path for an approval they never
requested.

Removing the requester fixes that but exposes a second hole:
`notify_status_change` skipped the decision notification entirely when
`requested_by` was NULL, so nobody learned the outcome. That hole was
already live for gate-raised CAPAs before this change, since
`auto_request_capa_approval` passes `requested_by=capa.initiated_by` and
gate CAPAs have no initiator. It now falls back to the approved object's
assignee.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model

from Tracker.models import (
    ApprovalRequest, ApprovalTemplate, Approval_Type, CAPA, NotificationTask,
    PartTypes, Processes, ProcessStep, SamplingRuleSet, StepGateFiring, Steps,
    Tenant, TenantGroup, UserRole,
)
from Tracker.services.core.approval import notify_status_change
from Tracker.services.qms.quality_gate import _require_approval
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class GateApprovalRequesterTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Gate Appr", slug="gate-appr", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()

        # The operator who trips the gate. Pre-fix, this user became the
        # approval's requester.
        self.operator = User.objects.create_user(
            username="ga2-op", email="ga2-op@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(
            user=self.operator,
            group=TenantGroup.objects.get(tenant=self.tenant, name='Operator'),
        )
        self.qa_manager = User.objects.create_user(
            username="ga2-qam", email="ga2-qam@test.test", password="x",
            tenant=self.tenant,
        )
        UserRole.objects.create(
            user=self.qa_manager,
            group=TenantGroup.objects.get(tenant=self.tenant, name='QA Manager'),
        )

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-GA2", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Gate Step",
            step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)

        self.template = ApprovalTemplate.objects.create(
            tenant=self.tenant,
            template_name="Gate Approval",
            approval_type=Approval_Type.CAPA_APPROVAL,
            is_current_version=True,
        )
        self.ruleset = SamplingRuleSet.objects.create(
            tenant=self.tenant, name="RS-GA2", step=self.step,
            part_type=self.pt,
            gate_metric='FAIL_RATE_PCT', gate_threshold=Decimal('10.000'),
            gate_actions=['REQUIRE_APPROVAL'],
            gate_approval_template=self.template,
        )

    def _firing(self):
        """A real StepGateFiring - it is the approval's content_object, so a
        stand-in object can't back the generic FK. Note it has NO
        `assigned_to`: a gate firing is not somebody's task, which is the
        no-owner case the decision-notification fallback must tolerate."""
        return StepGateFiring.objects.create(
            tenant=self.tenant, ruleset=self.ruleset, step=self.step,
            metric='FAIL_RATE_PCT', metric_value=Decimal('25.000'),
            threshold=Decimal('10.000'),
        )

    # -- attribution --------------------------------------------------------

    def test_gate_approval_has_no_requester(self):
        """The core fix."""
        ar = _require_approval(self.ruleset, self._firing(), user=self.operator)
        self.assertIsNone(
            ar.requested_by,
            'a gate-raised approval must not name the tripping user as '
            'requester — it drives the self-approval guard',
        )

    def test_tripping_user_is_not_pushed_into_self_approval(self):
        """The consequence that made this more than cosmetic: with the
        operator recorded as requester, `requested_by == approver` would be
        True and the self-approval branch would fire on coincidence."""
        ar = _require_approval(self.ruleset, self._firing(), user=self.operator)
        self.assertNotEqual(ar.requested_by_id, self.operator.id)
        # This is the comparison submit_approval_response makes.
        self.assertFalse(ar.requested_by == self.operator)

    def test_reason_still_records_the_gate(self):
        ar = _require_approval(self.ruleset, self._firing(), user=self.operator)
        self.assertIn('RS-GA2', ar.reason)
        self.assertIn('Gate Step', ar.reason)

    # -- the decision still reaches someone ---------------------------------

    def _capa_approval(self, assigned_to):
        capa = CAPA.objects.create(
            tenant=self.tenant, capa_type="CORRECTIVE", severity="MAJOR",
            status="OPEN", problem_statement="Auto-raised by quality gate.",
            initiated_by=None,          # system-raised
            assigned_to=assigned_to,
        )
        return ApprovalRequest.objects.create(
            tenant=self.tenant,
            approval_number=f'AR-GA2-{"A" if assigned_to else "N"}',
            content_object=capa,
            approval_type=Approval_Type.CAPA_APPROVAL,
            requested_by=None,
            reason='Gate CAPA needs approval',
        )

    def test_decision_falls_back_to_the_assignee(self):
        """Pre-fix this notified nobody, so a rejected approval sat unread
        on a CAPA its owner was waiting on."""
        ar = self._capa_approval(self.qa_manager)
        before = NotificationTask.objects.count()
        notify_status_change(ar, 'APPROVED')
        self.assertEqual(NotificationTask.objects.count(), before + 1)
        task = NotificationTask.objects.order_by('-id').first()
        self.assertEqual(task.recipient_id, self.qa_manager.id)

    def test_no_requester_and_no_assignee_is_a_quiet_no_op(self):
        """Must not raise — the approver's response submission runs through
        here, and a NOT NULL insert error would abort their decision."""
        ar = self._capa_approval(None)
        before = NotificationTask.objects.count()
        notify_status_change(ar, 'APPROVED')     # no exception
        self.assertEqual(NotificationTask.objects.count(), before)

    def test_content_object_without_assigned_to_is_a_quiet_no_op(self):
        """A StepGateFiring has no owner to tell; the approvers are the
        actors. Must degrade quietly rather than AttributeError."""
        ar = _require_approval(self.ruleset, self._firing(), user=self.operator)
        before = NotificationTask.objects.count()
        notify_status_change(ar, 'APPROVED')     # no exception
        self.assertEqual(NotificationTask.objects.count(), before)

    def test_real_requester_still_gets_the_decision(self):
        """Regression guard: the fallback must not shadow a real requester."""
        capa = CAPA.objects.create(
            tenant=self.tenant, capa_type="CORRECTIVE", severity="MAJOR",
            status="OPEN", problem_statement="Hand-authored",
            initiated_by=self.qa_manager, assigned_to=self.operator,
        )
        ar = ApprovalRequest.objects.create(
            tenant=self.tenant, approval_number='AR-GA2-REAL',
            content_object=capa, approval_type=Approval_Type.CAPA_APPROVAL,
            requested_by=self.qa_manager,
            reason='Manually requested',
        )
        notify_status_change(ar, 'APPROVED')
        task = NotificationTask.objects.order_by('-id').first()
        self.assertEqual(task.recipient_id, self.qa_manager.id,
                         'requester wins over assignee')
