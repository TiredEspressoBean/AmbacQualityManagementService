"""Approving a routing honours change-control mode (user decision 2026-10-28).

A revision of an approved routing goes through a PCR, which in REGULATED mode another
person signs. A brand-new routing's first version had no such gate: the editor's
Approve locked it for production in either mode, the author included. Now:
  - SIMPLIFIED: the editor approves it directly, as before;
  - REGULATED: direct approval is refused; it is submitted for approval, and the
    author can't sign it (the Process Approval template's allow_self_approval);
  - either mode: a draft that is a PCR's working copy is approved through the PCR.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import (
    ApprovalResponse, ApprovalTemplate, EdgeType, PartTypes, Processes,
    ProcessChangeRequest, ProcessStatus, ProcessStep, StepEdge, Steps,
)
from Tracker.services.change_control.sequencing import next_artifact_number
from Tracker.services.mes.processes import approve_process_directly
from Tracker.tests.base import TenantTestCase


class RoutingApprovalModeTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.approver = get_user_model().objects.create_user(
            username="qa-signer", email="qa-signer@tenant-a.com", password="x", tenant=t)
        tpl, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="PROCESS_APPROVAL", tenant=t,
            defaults={"template_name": "Process Approval", "approval_flow_type": "ANY",
                      "approval_sequence": "PARALLEL", "allow_self_approval": False,
                      "is_current_version": True, "archived": False})
        # The author is an eligible approver too, so refusing them tests the
        # self-approval rule rather than eligibility.
        tpl.default_approvers.set([self.user_a, self.approver])
        pt = PartTypes.objects.create(tenant=t, name="Pump")
        self.process = Processes.objects.create(tenant=t, name="Pump build", part_type=pt,
                                                status=ProcessStatus.DRAFT)
        start = Steps.objects.create(tenant=t, part_type=pt, name="Start", step_type="START")
        done = Steps.objects.create(tenant=t, part_type=pt, name="Done", is_terminal=True)
        ProcessStep.objects.create(process=self.process, step=start, order=0)
        ProcessStep.objects.create(process=self.process, step=done, order=1)
        StepEdge.objects.create(process=self.process, from_step=start, to_step=done,
                                edge_type=EdgeType.DEFAULT)

    def _regulated(self):
        type(self.tenant_a).objects.filter(pk=self.tenant_a.pk).update(change_control_mode="REGULATED")
        self.process.tenant.refresh_from_db()

    def test_simplified_approves_from_the_editor(self):
        approve_process_directly(self.process, self.user_a)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.APPROVED)

    def test_regulated_refuses_direct_approval(self):
        self._regulated()
        with self.assertRaisesMessage(ValueError, "submit the routing for approval"):
            approve_process_directly(self.process, self.user_a)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.DRAFT)

    def test_regulated_api_approve_is_400_and_submit_works(self):
        self._regulated()
        self.authenticate_superuser(self.tenant_a)
        r = self.client.post(f"/api/Processes_with_steps/{self.process.id}/approve/")
        self.assertEqual(r.status_code, 400, r.content)
        r = self.client.post(f"/api/Processes_with_steps/{self.process.id}/submit_for_approval/",
                             {}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.PENDING_APPROVAL)

    def test_the_author_cannot_sign_and_another_approver_can(self):
        self._regulated()
        ar = self.process.submit_for_approval(self.user_a)
        self.assertEqual(self.process.status, ProcessStatus.PENDING_APPROVAL)
        with self.assertRaises(ValidationError):
            ApprovalResponse.submit_response(approval_request=ar, approver=self.user_a,
                                             decision="APPROVED")
        # The response recomputes the request and cascades the approval to the process.
        ApprovalResponse.submit_response(approval_request=ar, approver=self.approver,
                                         decision="APPROVED")
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.APPROVED)
        self.assertEqual(self.process.approved_by_id, self.approver.id)

    def test_a_pcr_draft_is_approved_through_its_pcr_in_either_mode(self):
        ProcessChangeRequest.objects.create(
            tenant=self.tenant_a,
            artifact_number=next_artifact_number(tenant_id=self.tenant_a.id, artifact_type="PCR"),
            target_process=self.process, draft_process_version=self.process,
            title="Tighten", proposed_change="x", justification="x", risk_analysis="x",
            created_by=self.user_a)
        with self.assertRaisesMessage(ValueError, "process change request"):
            approve_process_directly(self.process, self.user_a)
