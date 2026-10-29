"""Sequential approvals as ordered stages (user decision 2026-10-29;
services/core/approval_stages.py).

Out-of-sequence approval and rejection are refused; a group stage is required and any
one member satisfies it; only the open stage is waited on; withdraw stands down once a
later stage has answered; parallel templates are untouched.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import ApprovalTemplate, TenantGroup, UserRole
from Tracker.services.core.approval import (
    create_approval_from_template, submit_approval_response, withdraw_response,
)
from Tracker.tests.base import TenantTestCase

User = get_user_model()


class SequentialStagesTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        mk = lambda n: User.objects.create_user(username=n, email=f"{n}@a.test", password="x", tenant=t)
        self.author, self.eng, self.qa1, self.qa2, self.mgr = (mk(n) for n in ("author", "eng", "qa1", "qa2", "mgr"))
        self.qa = TenantGroup.objects.create(tenant=t, name="QA reviewers", is_custom=True)
        UserRole.objects.create(user=self.qa1, group=self.qa)
        UserRole.objects.create(user=self.qa2, group=self.qa)
        self.template = ApprovalTemplate.objects.create(
            tenant=t, template_name="Seq", approval_type="DOCUMENT_RELEASE",
            approval_sequence="SEQUENTIAL", approval_flow_type="ALL_REQUIRED",
            approval_stages=[{"users": [self.eng.id]}, {"groups": [str(self.qa.id)]},
                             {"users": [self.mgr.id]}])
        self.req = create_approval_from_template(self.qa, self.template, self.author)

    def _approve(self, user, comments="ok"):
        return submit_approval_response(self.req, user, "APPROVED", comments=comments)

    def test_stages_go_in_order_and_out_of_turn_is_refused(self):
        self.assertEqual(self.req.get_pending_approvers(), [self.eng])
        with self.assertRaisesRegex(ValidationError, "Not your turn — waiting on eng"):
            self._approve(self.mgr)
        with self.assertRaisesRegex(ValidationError, "Not your turn"):
            submit_approval_response(self.req, self.qa1, "REJECTED", comments="no")
        self._approve(self.eng)
        self.assertEqual(sorted(u.username for u in self.req.get_pending_approvers()), ["qa1", "qa2"])
        self._approve(self.qa2)      # any one member satisfies the group stage
        self.assertEqual(self.req.get_pending_approvers(), [self.mgr])
        with self.assertRaises(ValidationError):
            self._approve(self.qa1)  # the group stage is done
        self._approve(self.mgr)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "APPROVED")

    def test_the_group_stage_is_required(self):
        self._approve(self.eng)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "PENDING")
        self.assertFalse(self.req.can_approve(self.mgr))

    def test_a_rejection_at_any_stage_ends_it(self):
        self._approve(self.eng)
        submit_approval_response(self.req, self.qa1, "REJECTED", comments="Wrong revision")
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, "REJECTED")

    def test_withdraw_stands_down_once_a_later_stage_answered(self):
        first = self._approve(self.eng)
        self._approve(self.qa1)
        with self.assertRaisesRegex(ValidationError, "later stage"):
            withdraw_response(first, self.eng, "Changed my mind")

    def test_my_pending_lists_it_only_at_your_turn(self):
        self.grant_tenant_permissions(self.mgr, self.tenant_a, ['view_approvalrequest', 'full_tenant_access'])
        self.authenticate_as(self.mgr, self.tenant_a)
        ids = lambda: [r['id'] for r in self.client.get('/api/ApprovalRequests/my-pending/').json()['results']]
        self.assertNotIn(str(self.req.id), ids())
        self._approve(self.eng)
        self._approve(self.qa1)
        self.assertIn(str(self.req.id), ids())

    def test_template_edits_dont_reorder_a_request_in_flight(self):
        self.template.approval_stages = [{"users": [self.mgr.id]}]
        self.template.save(update_fields=["approval_stages"])
        self.assertEqual(self.req.get_pending_approvers(), [self.eng])


class ParallelUnchangedTests(TenantTestCase):

    def test_parallel_approvers_answer_in_any_order(self):
        t = self.tenant_a
        a = User.objects.create_user(username="pa", email="pa@a.test", password="x", tenant=t)
        b = User.objects.create_user(username="pb", email="pb@a.test", password="x", tenant=t)
        template = ApprovalTemplate.objects.create(
            tenant=t, template_name="Par", approval_type="DOCUMENT_RELEASE",
            approval_sequence="PARALLEL", approval_flow_type="ALL_REQUIRED")
        template.default_approvers.set([a, b])
        group = TenantGroup.objects.create(tenant=t, name="Any", is_custom=True)
        req = create_approval_from_template(group, template, self.user_a)
        submit_approval_response(req, b, "APPROVED", comments="ok")
        submit_approval_response(req, a, "APPROVED", comments="ok")
        req.refresh_from_db()
        self.assertEqual(req.status, "APPROVED")
