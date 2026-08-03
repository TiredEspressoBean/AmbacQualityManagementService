"""Approval notification context tolerates a NULL requester.

`ApprovalRequest.requested_by` is nullable and legitimately NULL when a
system process opened the request. The live path:

    quality gate trips
      -> CAPA created with initiated_by=None (system-raised)
      -> trigger_approval_for_critical_capa (MAJOR is the gate default)
      -> auto_request_capa_approval passes requested_by=capa.initiated_by
      -> notify_approvers queues an APPROVAL_REQUEST NotificationTask
      -> at SEND time build_approval_request_context dereferenced
         requested_by.get_full_name() -> AttributeError

Because the crash was at send time rather than create time, the approval
request and the notification row both looked fine — the approvers just
never heard that work was waiting on them. `services.core.approval`
already guarded the decision-notification path for exactly this case
(and its docstring names "created by a system process"), and the reminder
task in tasks.py already had a 'System' fallback; only these two context
builders disagreed.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    ApprovalRequest, Approval_Type, CAPA, NotificationTask, Tenant,
)
from Tracker.notifications.handlers import (
    build_approval_escalation_context,
    build_approval_request_context,
)
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class ApprovalContextNullRequesterTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Null Req", slug="null-req", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.approver = User.objects.create_user(
            username="nr-appr", email="nr-appr@test.test", password="x",
            tenant=self.tenant,
        )
        # A system-raised CAPA: no initiator, exactly what the quality gate
        # produces.
        self.capa = CAPA.objects.create(
            tenant=self.tenant,
            capa_type="CORRECTIVE",
            severity="MAJOR",
            status="OPEN",
            problem_statement="Auto-raised by quality gate 'RS' at step S.",
            initiated_by=None,
        )

    def _task(self, notification_type, approval_request):
        from django.contrib.contenttypes.models import ContentType
        from django.utils import timezone
        return NotificationTask.objects.create(
            notification_type=notification_type,
            recipient=self.approver,
            channel_type='EMAIL',
            interval_type='FIXED',
            related_content_type=ContentType.objects.get_for_model(ApprovalRequest),
            related_object_id=approval_request.pk,
            next_send_at=timezone.now(),
        )

    def _approval_request(self, requested_by):
        return ApprovalRequest.objects.create(
            tenant=self.tenant,
            approval_number=f'AR-NR-{"SYS" if requested_by is None else "USR"}',
            content_object=self.capa,
            approval_type=Approval_Type.CAPA_APPROVAL,
            requested_by=requested_by,
            reason='Gate-raised CAPA needs approval',
        )

    def test_request_context_renders_system_for_null_requester(self):
        ar = self._approval_request(None)
        task = self._task('APPROVAL_REQUEST', ar)
        ctx = build_approval_request_context(task)
        self.assertIsNotNone(ctx, 'context must build, not raise')
        self.assertEqual(ctx['requested_by'], 'System')

    def test_escalation_context_renders_system_for_null_requester(self):
        """The other unguarded site — an escalation on a system-raised
        approval would crash the same way."""
        ar = self._approval_request(None)
        task = self._task('APPROVAL_ESCALATION', ar)
        ctx = build_approval_escalation_context(task)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx['requested_by'], 'System')

    def test_real_requester_is_still_named(self):
        """Regression guard: the fallback must not swallow a real requester."""
        User = get_user_model()
        requester = User.objects.create_user(
            username="nr-req", email="nr-req@test.test", password="x",
            tenant=self.tenant, first_name="Dana", last_name="Reyes",
        )
        ar = self._approval_request(requester)
        task = self._task('APPROVAL_REQUEST', ar)
        ctx = build_approval_request_context(task)
        self.assertEqual(ctx['requested_by'], 'Dana Reyes')

    def test_requester_with_no_full_name_falls_back_to_username(self):
        User = get_user_model()
        requester = User.objects.create_user(
            username="nr-nameless", email="nr-nameless@test.test", password="x",
            tenant=self.tenant,
        )
        ar = self._approval_request(requester)
        task = self._task('APPROVAL_REQUEST', ar)
        ctx = build_approval_request_context(task)
        self.assertEqual(ctx['requested_by'], 'nr-nameless')
