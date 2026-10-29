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

    def test_the_api_says_not_your_turn_rather_than_403(self):
        self.grant_tenant_permissions(self.mgr, self.tenant_a, [
            'view_approvalrequest', 'respond_to_approval', 'full_tenant_access'])
        self.authenticate_as(self.mgr, self.tenant_a)
        r = self.client.post(f"/api/ApprovalRequests/{self.req.id}/submit-response/",
                             {"decision": "APPROVED", "comments": "ok"}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Not your turn", r.content.decode())
        outsider = User.objects.create_user(username="out", email="out@a.test", password="x",
                                            tenant=self.tenant_a)
        self.grant_tenant_permissions(outsider, self.tenant_a, [
            'view_approvalrequest', 'respond_to_approval', 'full_tenant_access'])
        self.authenticate_as(outsider, self.tenant_a)
        r = self.client.post(f"/api/ApprovalRequests/{self.req.id}/submit-response/",
                             {"decision": "APPROVED", "comments": "ok"}, format="json")
        self.assertEqual(r.status_code, 403, r.content)

    def test_the_request_shows_its_stages_and_the_viewers_turn(self):
        self.grant_tenant_permissions(self.mgr, self.tenant_a, ['view_approvalrequest', 'full_tenant_access'])
        self.authenticate_as(self.mgr, self.tenant_a)
        body = self.client.get(f"/api/ApprovalRequests/{self.req.id}/").json()
        self.assertEqual([st["open"] for st in body["stages"]], [True, False, False])
        self.assertEqual(body["stages"][1]["members"][0]["kind"], "group")
        self.assertIn("Not your turn — waiting on eng", body["turn_refusal"])
        self._approve(self.eng)
        self._approve(self.qa1)
        body = self.client.get(f"/api/ApprovalRequests/{self.req.id}/").json()
        self.assertIsNone(body["turn_refusal"])
        self.assertEqual([st["done"] for st in body["stages"]], [True, True, False])
        self.assertEqual(body["stages"][1]["members"][0]["for_group"], "QA reviewers")

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


class LegacyTemplateStagesTests(TenantTestCase):
    """A sequential template with groups and an auto-assign role but no stages (the PCR
    starter's shape): the role joins the groups' stage, so a lone QA Manager — in the
    role and the group — can approve without deadlock."""

    def test_pcr_shape_completes_with_one_qa_manager_and_one_pm(self):
        t = self.tenant_a
        qam = User.objects.create_user(username="qam", email="qam@a.test", password="x", tenant=t)
        pm = User.objects.create_user(username="pm1", email="pm1@a.test", password="x", tenant=t)
        author = User.objects.create_user(username="auth2", email="auth2@a.test", password="x", tenant=t)
        qa_g, _ = TenantGroup.objects.get_or_create(tenant=t, name="QA Manager")
        pm_g, _ = TenantGroup.objects.get_or_create(tenant=t, name="Production Manager")
        UserRole.objects.filter(group__in=[qa_g, pm_g]).delete()  # only these two people
        UserRole.objects.create(user=qam, group=qa_g)
        UserRole.objects.create(user=pm, group=pm_g)
        template = ApprovalTemplate.objects.create(
            tenant=t, template_name="PCR", approval_type="PCR_APPROVAL",
            approval_sequence="SEQUENTIAL", approval_flow_type="ALL_REQUIRED",
            auto_assign_by_role="QA Manager")
        template.default_groups.set([qa_g, pm_g])
        req = create_approval_from_template(qa_g, template, author)
        submit_approval_response(req, qam, "APPROVED", comments="ok")
        submit_approval_response(req, pm, "APPROVED", comments="ok")
        req.refresh_from_db()
        self.assertEqual(req.status, "APPROVED")


class StarterAndSpecTests(TenantTestCase):

    def test_process_approval_starter_is_parallel_any(self):
        from Tracker.services.defaults_service import APPROVAL_TEMPLATES
        [pa] = [x for x in APPROVAL_TEMPLATES if x["approval_type"] == "PROCESS_APPROVAL"]
        self.assertEqual((pa["approval_sequence"], pa["approval_flow_type"]), ("PARALLEL", "ANY"))

    def test_a_spec_nominal_of_1800_is_storable(self):
        from Tracker.models import MeasurementDefinition, PartTypes, Steps
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Inj", ID_prefix="I")
        step = Steps.objects.create(tenant=self.tenant_a, part_type=pt, name="Pop test", step_type="TASK")
        md = MeasurementDefinition.objects.create(tenant=self.tenant_a, step=step, label="Opening pressure",
                                                  type="NUMERIC", unit="bar", nominal="1800",
                                                  upper_tol="25", lower_tol="25")
        md.refresh_from_db()
        self.assertEqual(str(md.nominal), "1800.000000")
