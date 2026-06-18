"""First Piece Inspection gate in the advancement engine.

A step flagged `requires_first_piece_inspection` must not let ANY part leave it
until a PASSED or WAIVED FPIRecord exists for the (work order, step) — setup is
verified before the run proceeds. A FAILED FPI keeps the step locked until a
re-inspection passes. Scope is per-work-order (the only scope wired until the
scheduling engine lands).
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    FPIRecord,
    FPIStatus,
    PartTypes,
    Parts,
    Processes,
    ProcessStep,
    StepExecution,
    Steps,
    Tenant,
    WorkOrder,
    WorkOrderStatus,
)
from Tracker.services.mes.advancement import try_advance_lot
from Tracker.tests.base import TenantContextMixin
from django.test import TestCase


class FpiGateTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Fpi", slug="fpi-gate", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.user = User.objects.create_user(
            username="op-fpi", email="fpi@c.test", password="x", tenant=self.tenant,
        )
        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P", part_type=self.pt)
        # step1 gates on FPI; step2 is the destination.
        self.step1 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op1", step_type="TASK",
            requires_first_piece_inspection=True,
        )
        self.step2 = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op2", step_type="TASK",
        )
        ProcessStep.objects.create(process=self.process, step=self.step1, order=1)
        ProcessStep.objects.create(process=self.process, step=self.step2, order=2)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-FPI-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1, process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-FPI-1", part_type=self.pt,
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

    def _fpi_blocked(self, result):
        """True if any per-part blocker is the FPI gate (raised by
        can_advance_from_step → get_fpi_status, the single source of truth)."""
        return any(
            "First Piece Inspection" in b
            for lst in result.blockers_by_part.values() for b in lst
        )

    def test_blocked_without_fpi(self):
        result = self._advance()
        self.assertEqual(result.status, "blocked")
        self.assertTrue(self._fpi_blocked(result))
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step1.id, "part must not leave the FPI step")

    def test_failed_fpi_keeps_step_locked(self):
        FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step1,
            part_type=self.pt, status=FPIStatus.FAILED,
        )
        result = self._advance()
        self.assertEqual(result.status, "blocked")
        self.assertTrue(self._fpi_blocked(result))
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step1.id)

    def test_passed_fpi_unlocks_advance(self):
        FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step1,
            part_type=self.pt, status=FPIStatus.PASSED,
        )
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

    def test_waived_fpi_unlocks_advance(self):
        FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step1,
            part_type=self.pt, status=FPIStatus.WAIVED,
        )
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)

    def test_no_gate_when_fpi_not_required(self):
        self.step1.requires_first_piece_inspection = False
        self.step1.save(update_fields=["requires_first_piece_inspection"])
        result = self._advance()
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step2.id)
