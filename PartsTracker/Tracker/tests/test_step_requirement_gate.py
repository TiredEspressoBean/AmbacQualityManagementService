"""Fail-closed gating for unimplemented mandatory StepRequirement types.

`StepRequirement.is_satisfied` has automated checks for MEASUREMENT / QA_APPROVAL
/ FPI_PASSED / SIGNOFF. The resource/safety types (EQUIPMENT_CHECK / MATERIAL_SCAN
/ TRAINING_VALID / CALIBRATION_VALID) are not yet wired, so a *mandatory*
requirement of those types must fail CLOSED (block advancement) rather than
silently pass. Non-mandatory ones aren't checked by the gate, and DOCUMENT /
CUSTOM stay advisory. Mirrors the FPI-gate test setup (`test_fpi_gate.py`).
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from Tracker.models import (
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    RequirementType,
    StepExecution,
    StepRequirement,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin


class StepRequirementGateTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Req", slug="req-gate", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-req", email="req@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK",
        )
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-REQ-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-REQ-1", part_type=self.pt,
            work_order=self.wo, step=self.step1,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step1, visit_number=1, status="IN_PROGRESS",
        )

    def _advance(self):
        return try_advance_lot(
            work_order_id=str(self.wo.id), step_id=str(self.step1.id),
            tenant_id=str(self.tenant.id), operator=self.user,
        )

    def _req_blocked(self, result):
        return any(
            "Requirement not met" in b
            for lst in result.blockers_by_part.values() for b in lst
        )

    def test_mandatory_unimplemented_safety_type_blocks(self):
        StepRequirement.objects.create(
            step=self.step1, requirement_type=RequirementType.CALIBRATION_VALID,
            name="Gauge calibration", is_mandatory=True,
        )
        result = self._advance()
        self.assertEqual(result.status, "blocked")
        self.assertTrue(self._req_blocked(result))
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step1.id, "must not leave the gated step")

    def test_non_mandatory_unimplemented_type_does_not_block(self):
        # Only mandatory requirements are enforced by the gate.
        StepRequirement.objects.create(
            step=self.step1, requirement_type=RequirementType.MATERIAL_SCAN,
            name="Scan (advisory)", is_mandatory=False,
        )
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

    def test_no_requirement_advances(self):
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)
