"""Compliance-evidence holes closed 2026-10-06 (from a read-only pass of the API).

Each was a way to write evidence that should only come from an authorized act:
1. an approval response (an e-signature) POSTed directly, for anyone;
2. a disposition DECISION set on create, skipping the co-signed `decide`;
3. SPC baselines writable by any tenant user (model permissions dropped);
4. gate attestations signed as someone else, backdated, "verified";
5. step overrides created APPROVED, or approved by their own requester;
6. life tracking: accumulated life / limit overrides edited directly;
7. a machine with a failed calibration PATCHed back IN_SERVICE.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from Tracker.models import (
    CalibrationRecord, Equipments, EquipmentType, LifeLimitDefinition, LifeTracking, Parts,
    PartTypes, Processes, ProcessStep, StepExecution, StepOverride, Steps, Substep,
    SubstepGateCompletion, Tenant, TenantGroup, UserRole, WorkOrder,
)
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class _Fixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name="Holes", slug="compliance-holes-1006", tier="PRO")
        token = set_current_tenant_id(cls.tenant.id)
        try:
            cls.boss = User.objects.create_user(username="boss", email="boss@x.test", password="x",
                                                tenant=cls.tenant, is_staff=True)
            cls.boss.is_superuser = True
            cls.boss.save(update_fields=["is_superuser"])
            cls.other = User.objects.create_user(username="other", email="other@x.test", password="x",
                                                 tenant=cls.tenant)
            cls.part_type = PartTypes.objects.create(tenant=cls.tenant, name="Spacer", ID_prefix="SPC")
            process = Processes.objects.create(tenant=cls.tenant, name="Turn", part_type=cls.part_type,
                                               status="APPROVED")
            cls.step = Steps.objects.create(tenant=cls.tenant, name="OD Turn", part_type=cls.part_type)
            ProcessStep.objects.create(process=process, step=cls.step, order=1)
            wo = WorkOrder.objects.create(tenant=cls.tenant, ERP_id="WO-H-1", quantity=1, process=process)
            cls.part = Parts.objects.create(tenant=cls.tenant, ERP_id="SPC-H-1", part_type=cls.part_type,
                                            work_order=wo, step=cls.step)
            cls.execution = StepExecution.objects.create(tenant=cls.tenant, part=cls.part, step=cls.step,
                                                         visit_number=1)
            cls.substep = Substep.objects.create(tenant=cls.tenant, step=cls.step, order=0, title="Sign off")
        finally:
            reset_current_tenant(token)

    def setUp(self):
        self._token = set_current_tenant_id(self.tenant.id)
        self.as_user(self.boss)

    def tearDown(self):
        reset_current_tenant(self._token)

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        self.client.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))

    def limited(self, *codenames):
        """A user holding exactly these permissions (plus tenant access)."""
        u = User.objects.create_user(username=f"u{User.objects.count()}", email=f"u{User.objects.count()}@x.test",
                                     password="x", tenant=self.tenant)
        g = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{u.username}", is_custom=True)
        g.permissions.add(*Permission.objects.filter(codename__in=[*codenames, "full_tenant_access"]))
        UserRole.objects.create(user=u, group=g)
        return u


class ApprovalResponseTests(_Fixture):
    def test_responses_cannot_be_written_directly(self):
        resp = self.client.post("/api/ApprovalResponses/", {"decision": "APPROVED"}, format="json")
        self.assertEqual(resp.status_code, 405)


class DispositionTests(_Fixture):
    def test_a_type_on_create_needs_decision_authority_and_records_who(self):
        from Tracker.models import QualityReports
        report = QualityReports.objects.create(tenant=self.tenant, status="FAIL", part=self.part,
                                               detected_by=self.boss)
        clerk = self.limited("add_quarantinedisposition", "view_quarantinedisposition")
        self.as_user(clerk)
        resp = self.client.post("/api/QuarantineDispositions/", {
            "part": str(self.part.id), "quality_reports": [str(report.id)],
            "disposition_type": "USE_AS_IS", "description": "burr"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.part.refresh_from_db()
        self.assertNotEqual(self.part.part_status, "READY_FOR_NEXT_STEP")

        self.as_user(self.boss)
        resp = self.client.post("/api/QuarantineDispositions/", {
            "part": str(self.part.id), "quality_reports": [str(report.id)],
            "disposition_type": "SCRAP", "description": "crack"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["decision_authorized_by"], self.boss.id)


class SpcBaselineTests(_Fixture):
    def test_no_direct_writes_and_operators_cannot_freeze(self):
        self.assertEqual(self.client.post("/api/spc-baselines/", {}, format="json").status_code, 405)
        operator = self.limited("view_spcbaseline", "add_measurementresult")
        self.as_user(operator)
        resp = self.client.post("/api/spc-baselines/freeze/", {}, format="json")
        self.assertEqual(resp.status_code, 403)


class GateCompletionTests(_Fixture):
    def test_the_signer_is_whoever_is_logged_in_and_it_cannot_be_edited(self):
        resp = self.client.post("/api/SubstepGateCompletions/", {
            "step_execution": str(self.execution.id), "substep": str(self.substep.id), "node_id": "n1",
            "completed_by": self.other.id, "verification_method": "PASSWORD",
            "verified_at": "2020-01-01T00:00:00Z"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        gate = SubstepGateCompletion.objects.get(pk=resp.json()["id"])
        self.assertEqual(gate.completed_by_id, self.boss.id)
        self.assertEqual(gate.verification_method, "NONE")
        self.assertIsNone(gate.verified_at)
        patch = self.client.patch(f"/api/SubstepGateCompletions/{gate.id}/", {"node_id": "n2"}, format="json")
        self.assertEqual(patch.status_code, 405)


class StepOverrideTests(_Fixture):
    def _request(self):
        return self.client.post("/api/StepOverrides/", {
            "step_execution": str(self.execution.id), "block_type": "MEASUREMENT_FAILED",
            "reason": "gauge drift", "status": "APPROVED", "approved_by": self.other.id,
            "requested_by": self.other.id}, format="json")

    def test_created_pending_by_the_requester_and_never_self_approved(self):
        resp = self._request()
        self.assertEqual(resp.status_code, 201, resp.content)
        override = StepOverride.objects.get(pk=resp.json()["id"])
        self.assertEqual((override.status, override.requested_by_id, override.approved_by_id),
                         ("PENDING", self.boss.id, None))
        self.assertFalse(override.is_valid)
        mine = self.client.post(f"/api/StepOverrides/{override.id}/approve/", {}, format="json")
        self.assertEqual(mine.status_code, 400)

    def test_approving_needs_approve_stepoverride(self):
        override = StepOverride.objects.get(pk=self._request().json()["id"])
        self.as_user(self.limited("view_stepoverride", "add_stepoverride", "change_stepoverride"))
        resp = self.client.post(f"/api/StepOverrides/{override.id}/approve/", {}, format="json")
        self.assertEqual(resp.status_code, 403)


class LifeTrackingTests(_Fixture):
    def setUp(self):
        super().setUp()
        definition = LifeLimitDefinition.objects.create(
            tenant=self.tenant, name="Cycles", unit="cycles", unit_label="Cycles", hard_limit=Decimal(1000))
        self.tracking, _ = LifeTracking.for_object(self.part, definition, accumulated=Decimal(500))

    def test_accumulated_life_and_overrides_are_not_edited_directly(self):
        url = f"/api/LifeTracking/{self.tracking.id}/"
        resp = self.client.patch(url, {"accumulated": "0"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.client.patch(url, {"hard_limit_override": "999999", "override_approved_by": self.other.id},
                          format="json")
        self.tracking.refresh_from_db()
        self.assertIsNone(self.tracking.hard_limit_override)

    def test_reset_needs_life_limit_authority(self):
        self.as_user(self.limited("view_lifetracking", "add_lifetracking", "change_lifetracking"))
        resp = self.client.post(f"/api/LifeTracking/{self.tracking.id}/reset/", {"reason": "x"}, format="json")
        self.assertEqual(resp.status_code, 403)


class EquipmentStatusTests(_Fixture):
    def test_a_failed_gauge_cannot_be_patched_back_into_service(self):
        gauge_type = EquipmentType.objects.create(tenant=self.tenant, name="Micrometer", requires_calibration=True)
        gauge = Equipments.objects.create(tenant=self.tenant, name="MIC-1", equipment_type=gauge_type)
        today = datetime.date.today()
        CalibrationRecord.objects.create(tenant=self.tenant, equipment=gauge, calibration_date=today,
                                         due_date=today + datetime.timedelta(days=180), result="FAIL")
        gauge.refresh_from_db()
        self.assertEqual(gauge.status, "OUT_OF_SERVICE")
        resp = self.client.patch(f"/api/Equipment/{gauge.id}/", {"status": "IN_SERVICE"}, format="json")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("calibration", str(resp.json()))
