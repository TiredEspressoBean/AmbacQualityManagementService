"""A Major/Critical CAPA's plan is the QA Manager's decision (user, 2026-10-20).

While its approval is PENDING (or was REJECTED), corrective and preventive work and
the root-cause analysis wait; containment never does. "Work cannot begin until
approved" was only copy before: nothing refused the work.
"""
from django.utils import timezone

from Tracker.models import CAPA, CapaTasks
from Tracker.services.qms.capa import capa_plan_refusal, complete_capa_task
from Tracker.tests.base import TenantTestCase


class CapaPlanGateTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.capa = CAPA.objects.create(
            capa_type='CORRECTIVE', severity='MAJOR', problem_statement="Bores oversize",
            initiated_by=self.user_a, assigned_to=self.user_a)
        # tenant-safe: test fixture, scoped by pk
        CAPA.objects.filter(pk=self.capa.pk).update(approval_required=True, approval_status='PENDING')
        self.capa.refresh_from_db()
        self.corrective = CapaTasks.objects.create(
            capa=self.capa, task_type='CORRECTIVE', description="Re-tool the bore", assigned_to=self.user_a)
        self.containment = CapaTasks.objects.create(
            capa=self.capa, task_type='CONTAINMENT', description="Sort the WIP", assigned_to=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_capa', 'view_capatasks', 'change_capatasks', 'view_rcarecord', 'add_rcarecord',
            'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_corrective_work_waits_for_the_approval(self):
        with self.assertRaisesMessage(ValueError, "awaiting approval"):
            complete_capa_task(self.corrective, self.user_a, notes="done")
        resp = self.client.patch(f"/api/CapaTasks/{self.corrective.id}/", {"status": "IN_PROGRESS"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_containment_never_waits(self):
        complete_capa_task(self.containment, self.user_a, notes="WIP sorted")
        self.containment.refresh_from_db()
        self.assertEqual(self.containment.status, "COMPLETED")

    def test_root_cause_analysis_waits_for_the_approval(self):
        resp = self.client.post("/api/RcaRecords/", {
            "capa": str(self.capa.id), "rca_method": "FIVE_WHYS",
            "problem_description": "Bores oversize", "conducted_by": self.user_a.id,
            "conducted_date": str(timezone.now().date())}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("approval", resp.content.decode())

    def test_a_rejected_plan_says_so(self):
        CAPA.objects.filter(pk=self.capa.pk).update(approval_status='REJECTED')  # tenant-safe: fixture
        self.capa.refresh_from_db()
        self.assertIn("was rejected", capa_plan_refusal(self.capa))

    def test_an_approved_or_unrequired_plan_is_worked(self):
        for state in ('APPROVED', 'NOT_REQUIRED'):
            CAPA.objects.filter(pk=self.capa.pk).update(approval_status=state)  # tenant-safe: fixture
            self.capa.refresh_from_db()
            self.assertIsNone(capa_plan_refusal(self.capa))
        self.corrective.refresh_from_db()
        complete_capa_task(self.corrective, self.user_a, notes="done")


class CapaPlanApproverTests(TenantTestCase):
    """Who approves a Major/Critical CAPA's plan (user, 2026-10-20): a QA Manager or a
    Production Manager — either, the first approval decides it. The requester decides
    their own only when nobody else can, with a justification on record."""

    def setUp(self):
        super().setUp()
        from Tracker.models import ApprovalTemplate, TenantGroup, User, UserRole
        self.qa_group, _ = TenantGroup.objects.get_or_create(tenant=self.tenant_a, name="QA Manager")
        self.pm_group, _ = TenantGroup.objects.get_or_create(tenant=self.tenant_a, name="Production Manager")
        self.maria = User.objects.create_user(username='maria', password='pw', tenant=self.tenant_a)
        UserRole.objects.create(user=self.maria, group=self.qa_group)
        template, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="CAPA_MAJOR",
            defaults={"template_name": "Major CAPA Approval", "approval_flow_type": "ANY",
                      "approval_sequence": "PARALLEL", "auto_assign_by_role": "QA Manager",
                      "allow_self_approval": False, "default_due_days": 5})
        template.default_groups.set([self.qa_group, self.pm_group])

    def _request(self, capa):
        from django.contrib.contenttypes.models import ContentType
        from Tracker.models import ApprovalRequest
        return ApprovalRequest.objects.get(content_type=ContentType.objects.get_for_model(CAPA), object_id=capa.pk)

    def test_a_production_manager_decides_a_qa_managers_capa(self):
        from django.core.exceptions import ValidationError
        from Tracker.models import User, UserRole
        from Tracker.services.core.approval import submit_approval_response
        jennifer = User.objects.create_user(username='jennifer', password='pw', tenant=self.tenant_a)
        UserRole.objects.create(user=jennifer, group=self.pm_group)
        capa = CAPA.objects.create(capa_type='CORRECTIVE', severity='MAJOR', problem_statement="Repeat burr",
                                   initiated_by=self.maria, assigned_to=self.maria)
        req = self._request(capa)
        with self.assertRaisesMessage(ValidationError, "someone else can decide it"):
            submit_approval_response(req, self.maria, 'APPROVED', comments="I raised it; go ahead")
        submit_approval_response(req, jennifer, 'APPROVED')
        capa.refresh_from_db()
        self.assertEqual(capa.approval_status, 'APPROVED')

    def test_the_only_approver_self_approves_with_a_justification(self):
        from django.core.exceptions import ValidationError
        from Tracker.services.core.approval import submit_approval_response
        capa = CAPA.objects.create(capa_type='CORRECTIVE', severity='MAJOR', problem_statement="Repeat burr",
                                   initiated_by=self.maria, assigned_to=self.maria)
        req = self._request(capa)
        with self.assertRaisesMessage(ValidationError, "Justification required"):
            submit_approval_response(req, self.maria, 'APPROVED', comments="ok")
        response = submit_approval_response(
            req, self.maria, 'APPROVED', comments="Sole QA Manager, no Production Manager on staff")
        self.assertTrue(response.self_approved)
        capa.refresh_from_db()
        self.assertEqual(capa.approval_status, 'APPROVED')

    def test_awaiting_my_approval_omits_my_own_request_when_someone_else_decides(self):
        """It listed CAPAs the viewer requested and couldn't decide (PM walk 2026-10-21)."""
        from Tracker.models import User, UserRole
        jennifer = User.objects.create_user(username='jen2', password='pw', tenant=self.tenant_a)
        UserRole.objects.create(user=jennifer, group=self.pm_group)
        capa = CAPA.objects.create(capa_type='CORRECTIVE', severity='MAJOR', problem_statement="Repeat burr",
                                   initiated_by=self.maria, assigned_to=self.maria)
        req = self._request(capa)
        self.grant_tenant_permissions(self.maria, self.tenant_a, ['view_approvalrequest', 'full_tenant_access'])
        self.authenticate_as(self.maria, self.tenant_a)
        body = self.client.get("/api/ApprovalRequests/my-pending/").json()
        ids = {r["id"] for r in (body["results"] if isinstance(body, dict) else body)}
        self.assertNotIn(str(req.id), ids)
