"""The server enforces what the compliance pages say it does (audit, 2026-10-28).

Each class was first a probe that performed the forbidden act through the API and
found it accepted; each now asserts the refusal.

- Approvals: an approval through the API is signed (drawing + password), a rejection
  says why, and the password re-auth is throttled.
- Approval responses under the immutability trigger: withdraw / answer again /
  delegate still work; any other change to a response, and any delete, is refused.
- Group permission changes land in the audit log with who made them.
- No reading is recorded against a failed gauge, by any write path.
- A part with an open disposition changes status only through that disposition.
- A decided disposition's severity and concession evidence don't change by edit.
- Only QA turns on a CAPA's self-verification.
"""
import datetime
from io import StringIO

from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import call_command
from django.db import DatabaseError, transaction

from Tracker.models import (
    CAPA, ApprovalRequest, ApprovalResponse, ApprovalTemplate, CalibrationRecord, Documents,
    Equipments, EquipmentStatus, EquipmentType, MeasurementDefinition, Parts, PartTypes,
    Processes, ProcessStep, QuarantineDisposition, StepExecution, StepExecutionMeasurement,
    Steps, Substep, TenantGroup, WorkOrder, WorkOrderStatus,
)
from Tracker.tests.base import TenantTestCase

User = get_user_model()

SIGNATURE = "data:image/png;base64,iVBORw0KGgo="


class _ApprovalFixture(TenantTestCase):
    """A document under review, with a DOCUMENT_RELEASE request assigned to
    `self.approver`. user_a is the requester."""

    flow_type = "ANY"
    extra_approver = False

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        self.approver = User.objects.create_user(
            username="ce-approver", email="ce-approver@tenant-a.com",
            password="right-password", tenant=t)
        approvers = [self.approver]
        if self.extra_approver:
            approvers.append(User.objects.create_user(
                username="ce-approver-2", email="ce-approver-2@tenant-a.com",
                password="right-password", tenant=t))
        tpl, _ = ApprovalTemplate.objects.update_or_create(
            approval_type="DOCUMENT_RELEASE", tenant=t,
            defaults={"template_name": "Document Release", "approval_flow_type": self.flow_type,
                      "approval_sequence": "PARALLEL", "allow_self_approval": False,
                      "auto_assign_by_role": None, "is_current_version": True, "archived": False})
        tpl.default_groups.clear()
        tpl.default_approvers.set(approvers)
        self.document = Documents.objects.create(
            tenant=t, file_name="ce-wi.pdf", uploaded_by=self.user_a, status="UNDER_REVIEW")
        self.request_ = ApprovalRequest.create_from_template(
            content_object=self.document, template=tpl, requested_by=self.user_a)
        self.grant_tenant_permissions(self.approver, t, [
            "respond_to_approval", "view_approvalrequest", "full_tenant_access"])
        self.authenticate_as(self.approver, t)
        # Targeted deletes of both throttle tiers, never cache.clear().
        self._keys = [f"{p}:{t.id}:ce-approver@tenant-a.com"
                      for p in ("approval_reauth", "second_person_fail")]
        for k in self._keys:
            cache.delete(k)

    def tearDown(self):
        for k in self._keys:
            cache.delete(k)
        super().tearDown()

    def _submit(self, payload):
        return self.client.post(f"/api/ApprovalRequests/{self.request_.id}/submit-response/",
                                payload, format="json")


class ApprovalSignatureEnforcementTests(_ApprovalFixture):

    def test_an_approval_needs_a_signature_and_the_password(self):
        r = self._submit({"decision": "APPROVED"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Sign to approve", r.json()["detail"])
        r = self._submit({"decision": "APPROVED", "signature_data": SIGNATURE})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("password", r.json()["detail"])
        self.assertFalse(ApprovalResponse.objects.filter(approval_request=self.request_).exists())

        r = self._submit({"decision": "APPROVED", "signature_data": SIGNATURE,
                          "password": "right-password"})
        self.assertEqual(r.status_code, 200, r.content)
        resp = ApprovalResponse.objects.get(approval_request=self.request_, approver=self.approver)
        self.assertEqual(resp.verification_method, "PASSWORD")
        self.assertIsNotNone(resp.verified_at)

    def test_a_rejection_says_why(self):
        r = self._submit({"decision": "REJECTED"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("why", r.json()["detail"])
        r = self._submit({"decision": "REJECTED", "comments": "Section 4 cites the old spec"})
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_password_is_throttled(self):
        for i in range(5):
            r = self._submit({"decision": "APPROVED", "signature_data": SIGNATURE,
                              "password": f"wrong-{i}"})
            self.assertEqual(r.status_code, 400, r.content)
            self.assertIn("isn't right", r.json()["detail"])
        # Capped: even the right password is refused until the window passes.
        r = self._submit({"decision": "APPROVED", "signature_data": SIGNATURE,
                          "password": "right-password"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Too many", r.json()["detail"])
        self.assertFalse(ApprovalResponse.objects.filter(approval_request=self.request_).exists())


class ApprovalResponseTriggerTests(_ApprovalFixture):
    """The immutability trigger (installed per test; Postgres DDL rolls back with it)."""

    flow_type = "ALL_REQUIRED"
    extra_approver = True

    def setUp(self):
        super().setUp()
        self.response = ApprovalResponse.submit_response(
            approval_request=self.request_, approver=self.approver, decision="APPROVED",
            password="right-password")
        self.request_.refresh_from_db()
        self.assertEqual(self.request_.status, "PENDING")  # still waiting on approver 2
        call_command("setup_audit_triggers", stdout=StringIO())

    def test_withdraw_then_answer_again(self):
        r = self.client.post(f"/api/ApprovalRequests/{self.request_.id}/withdraw-response/",
                             {"reason": "Answered on the wrong document"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self._submit({"decision": "REJECTED", "comments": "Section 4 cites the old spec"})
        self.assertEqual(r.status_code, 200, r.content)
        self.response.refresh_from_db()
        self.assertEqual(self.response.decision, "REJECTED")

    def test_a_signed_response_is_not_rewritten(self):
        with self.assertRaisesMessage(DatabaseError, "COMPLIANCE VIOLATION"):
            with transaction.atomic():
                ApprovalResponse.objects.filter(pk=self.response.pk).update(comments="edited later")
        with self.assertRaisesMessage(DatabaseError, "COMPLIANCE VIOLATION"):
            with transaction.atomic():
                ApprovalResponse.objects.filter(pk=self.response.pk).update(decision="REJECTED")

    def test_a_past_decision_is_dated_as_it_is_recorded(self):
        """What the seeds do: no UPDATE afterward, so the trigger never sees one."""
        from django.utils import timezone
        from Tracker.services.core.approval import submit_approval_response
        when = timezone.now() - datetime.timedelta(days=10)
        second = User.objects.get(username="ce-approver-2")
        response = submit_approval_response(self.request_, second, "APPROVED", decided_at=when)
        response.refresh_from_db()
        self.assertEqual(response.decision_date, when)
        self.assertEqual(response.created_at, when)

    def test_a_response_is_not_deleted(self):
        with self.assertRaisesMessage(DatabaseError, "COMPLIANCE VIOLATION"):
            with transaction.atomic():
                ApprovalResponse.objects.filter(pk=self.response.pk).delete()


class GroupPermissionAuditTests(TenantTestCase):

    def test_a_permission_change_is_logged_with_who_made_it(self):
        t = self.tenant_a
        target = TenantGroup.objects.create(tenant=t, name="CE Inspectors",
                                            description="ce", is_custom=True)
        self.grant_tenant_permissions(self.user_a, t, ["change_tenantgroup", "view_tenantgroup"])
        # A session login, as the browser makes: the audit middleware names the actor
        # from it (force_authenticate happens past the middleware, so it would not).
        self.client.force_login(self.user_a)
        self.client.credentials(HTTP_X_TENANT_ID=str(t.id))

        r = self.client.put(f"/api/TenantGroups/{target.id}/permissions/",
                            {"permissions": ["view_parts", "change_parts"]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.client.delete(f"/api/TenantGroups/{target.id}/permissions/",
                               {"permissions": ["change_parts"]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

        entries = [e for e in LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(TenantGroup), object_pk=str(target.pk))
            if "permissions" in (e.changes or {})]
        self.assertEqual(len(entries), 2, [e.changes for e in entries])
        for e in entries:
            self.assertEqual(e.actor_id, self.user_a.id)
        ops = sorted(e.changes["permissions"]["operation"] for e in entries)
        self.assertEqual(ops, ["add", "delete"])


class FailedGaugeTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        pt = PartTypes.objects.create(tenant=t, name="CE Widget")
        process = Processes.objects.create(tenant=t, name="P-CE-G6", part_type=pt)
        self.step = Steps.objects.create(tenant=t, part_type=pt, name="Measure", step_type="TASK")
        ProcessStep.objects.create(process=process, step=self.step, order=1)
        wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-CE-G6",
                                      workorder_status=WorkOrderStatus.IN_PROGRESS,
                                      quantity=1, process=process)
        part = Parts.objects.create(tenant=t, ERP_id="P-CE-G6", part_type=pt,
                                    work_order=wo, step=self.step)
        self.step_execution = StepExecution.objects.create(
            tenant=t, part=part, step=self.step, visit_number=1, status="IN_PROGRESS",
            training_authorization={"authorized": True, "missing": [], "verified": []})
        self.md = MeasurementDefinition.objects.create(
            tenant=t, step=self.step, label="Bore diameter", unit="mm",
            nominal=10.0, upper_tol=0.05, lower_tol=0.05, type="NUMERIC")
        self.substep = Substep.objects.create(tenant=t, step=self.step, order=1,
                                              title="Measure bore", body_blocks={})
        gauge_type = EquipmentType.objects.create(tenant=t, name="Micrometer",
                                                  requires_calibration=True)
        self.gauge = Equipments.objects.create(tenant=t, name="MIC-FAILED",
                                               equipment_type=gauge_type,
                                               status=EquipmentStatus.IN_SERVICE)
        today = datetime.date.today()
        CalibrationRecord.objects.create(tenant=t, equipment=self.gauge, calibration_date=today,
                                         due_date=today + datetime.timedelta(days=180),
                                         result="FAIL")
        self.gauge.refresh_from_db()
        self.assertEqual(self.gauge.calibration_status, "FAILED")
        self.grant_tenant_permissions(self.user_a, t, [
            "add_stepexecutionmeasurement", "view_stepexecutionmeasurement",
            # Held, and still no edit or delete: the routes don't exist.
            "change_stepexecutionmeasurement", "delete_stepexecutionmeasurement",
            "full_tenant_access"])
        self.authenticate_as(self.user_a, t)

    def test_plain_create_is_refused(self):
        r = self.client.post("/api/StepExecutionMeasurements/", {
            "step_execution": str(self.step_execution.id),
            "measurement_definition": str(self.md.id),
            "value": "10.01",
            "equipment": str(self.gauge.id),
            "substep": str(self.substep.id),
            "recorded_by": self.user_a.id,
        }, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("OUT_OF_SERVICE", r.content.decode())
        self.assertFalse(StepExecutionMeasurement.objects.filter(equipment=self.gauge).exists())

    def test_a_recorded_reading_is_not_edited_or_deleted(self):
        good = Equipments.objects.create(tenant=self.tenant_a, name="MIC-GOOD",
                                         equipment_type=self.gauge.equipment_type,
                                         status=EquipmentStatus.IN_SERVICE)
        reading = StepExecutionMeasurement.objects.create(
            tenant=self.tenant_a, step_execution=self.step_execution,
            measurement_definition=self.md, substep=self.substep, value=10.01,
            equipment=good, recorded_by=self.user_a)
        url =f"/api/StepExecutionMeasurements/{reading.id}/"
        self.assertEqual(self.client.patch(url, {"value": "10.30"}, format="json").status_code, 405)
        self.assertEqual(self.client.put(url, {"value": "10.30"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        reading.refresh_from_db()
        self.assertEqual(float(reading.value), 10.01)

    def test_bulk_record_is_refused(self):
        r = self.client.post("/api/StepExecutionMeasurements/bulk-record/", {
            "step_execution": str(self.step_execution.id),
            "measurements": [{"measurement_definition": str(self.md.id),
                              "substep": str(self.substep.id), "value": 10.01,
                              "equipment": str(self.gauge.id)}],
        }, format="json")
        body = r.json()
        self.assertEqual(body["created_count"], 0, body)
        self.assertIn("OUT_OF_SERVICE", body["errors"][0]["detail"])
        self.assertFalse(StepExecutionMeasurement.objects.filter(equipment=self.gauge).exists())


class _QuarantineFixture(TenantTestCase):

    def setUp(self):
        super().setUp()
        t = self.tenant_a
        pt = PartTypes.objects.create(tenant=t, name="CE Injector")
        self.step = Steps.objects.create(tenant=t, name="Flow test", part_type=pt)
        self.wo = WorkOrder.objects.create(tenant=t, ERP_id="WO-CE-Q", quantity=1,
                                           workorder_status="IN_PROGRESS")
        self.part = Parts.objects.create(tenant=t, ERP_id="CE-Q-1", part_type=pt,
                                         work_order=self.wo, step=self.step,
                                         part_status="QUARANTINED")


class OpenDispositionHoldsThePartTests(_QuarantineFixture):

    def setUp(self):
        super().setUp()
        self.disp = QuarantineDisposition.objects.create(
            tenant=self.tenant_a, part=self.part, step=self.step, assigned_to=self.user_a)
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            "view_parts", "change_parts", "full_tenant_access"])
        self.authenticate_as(self.user_a, self.tenant_a)

    def test_an_edit_cannot_release_it(self):
        for status in ("COMPLETED", "IN_STOCK", "SCRAPPED"):
            r = self.client.patch(f"/api/Parts/{self.part.id}/", {"part_status": status},
                                  format="json")
            self.assertEqual(r.status_code, 400, r.content)
            self.assertIn(self.disp.disposition_number, r.content.decode())
        self.part.refresh_from_db()
        self.assertEqual(self.part.part_status, "QUARANTINED")

    def test_bulk_set_status_cannot_release_it(self):
        from Tracker.services.mes.parts import bulk_set_status
        [result] = bulk_set_status(self.tenant_a.id, [self.part.id], "COMPLETED", self.user_a)
        self.assertFalse(result.ok)
        self.assertIn(self.disp.disposition_number, result.error)

    def test_once_closed_the_status_is_editable_again(self):
        QuarantineDisposition.objects.filter(pk=self.disp.pk).update(current_state="CLOSED")  # tenant-safe: fixture
        r = self.client.patch(f"/api/Parts/{self.part.id}/", {"part_status": "IN_PROGRESS"},
                              format="json")
        self.assertEqual(r.status_code, 200, r.content)


class DecidedDispositionTests(_QuarantineFixture):

    def setUp(self):
        super().setUp()
        from Tracker.services.qms.disposition import decide_disposition
        self.disp = QuarantineDisposition.objects.create(
            tenant=self.tenant_a, part=self.part, step=self.step, assigned_to=self.user_a,
            severity="MAJOR")
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            "view_quarantinedisposition", "change_quarantinedisposition", "full_tenant_access"])
        self.authenticate_as(self.user_a, self.tenant_a)
        self._decide = lambda: decide_disposition(
            self.disp, disposition_type="USE_AS_IS", authorized_by=self.user_a,
            notes="Concession granted", customer_approval={"reference": "CONC-CE-1"})

    def _patch(self, data):
        return self.client.patch(f"/api/QuarantineDispositions/{self.disp.id}/", data,
                                 format="json")

    def test_severity_is_editable_until_the_decision(self):
        r = self._patch({"severity": "CRITICAL"})
        self.assertEqual(r.status_code, 200, r.content)

    def test_the_concession_reference_stays(self):
        self.disp = self._decide()
        r = self._patch({"customer_approval_reference": ""})
        self.assertEqual(r.status_code, 400, r.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.customer_approval_reference, "CONC-CE-1")

    def test_severity_is_not_lowered(self):
        self.disp = self._decide()
        r = self._patch({"severity": "MINOR"})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("may only be raised", r.content.decode())
        # Echoing it back unchanged is fine: forms send the whole record.
        r = self._patch({"severity": "MAJOR", "description": "Bore oversize by 0.02"})
        self.assertEqual(r.status_code, 200, r.content)
        # Raising it only asks more of the close.
        r = self._patch({"severity": "CRITICAL"})
        self.assertEqual(r.status_code, 200, r.content)


class CapaSelfVerificationSwitchTests(TenantTestCase):

    def setUp(self):
        super().setUp()
        self.capa = CAPA.objects.create(
            capa_type='CORRECTIVE', severity='MINOR', problem_statement="Burr on flange",
            initiated_by=self.user_a, assigned_to=self.user_a)
        self.authenticate_as(self.user_a, self.tenant_a)

    def _flip(self):
        return self.client.patch(f"/api/CAPAs/{self.capa.id}/",
                                 {"allow_self_verification": True}, format="json")

    def test_the_owner_without_qa_cannot_turn_it_on(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_capa', 'change_capa', 'full_tenant_access'])
        r = self._flip()
        self.assertEqual(r.status_code, 403, r.content)
        self.capa.refresh_from_db()
        self.assertFalse(self.capa.allow_self_verification)
        # Other edits still go through.
        r = self.client.patch(f"/api/CAPAs/{self.capa.id}/",
                              {"problem_statement": "Burr on flange, both sides"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_qa_may_turn_it_on_even_as_owner(self):
        self.grant_tenant_permissions(self.user_a, self.tenant_a, [
            'view_capa', 'change_capa', 'verify_capa', 'full_tenant_access'])
        r = self._flip()
        self.assertEqual(r.status_code, 200, r.content)
        self.capa.refresh_from_db()
        self.assertTrue(self.capa.allow_self_verification)
