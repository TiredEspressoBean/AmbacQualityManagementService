"""FPI signoff — segregation of duties + step-level QA-approval side effect.

FPI Pass / Waive is the step-level QA signoff for the first piece run — it
must create a QaApproval so `can_advance_from_step` sees the step-level
QA-signoff blocker as satisfied. Without this, any step that both requires
FPI and requires QA signoff is unadvancable: the QA-signoff requirement has
no other user-facing creation path in the running app.

Also: FPI Pass / Waive can't be signed by whoever ran the first piece's
inspection substeps. QMS/AS9100 SOD principle — a second qualified
inspector must approve.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    FPIRecord, FPIStatus, PartTypes, Parts, Processes, ProcessStep,
    QaApproval, StepExecution, Steps, SubstepCompletion, Substep,
    Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.qms.fpi import pass_fpi, fail_fpi, waive_fpi
from Tracker.tests.base import TenantContextMixin, VectorTestCase


class FpiSodAndQaApprovalTests(TenantContextMixin, VectorTestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(
            name="Fpi SOD", slug="fpi-sod", tier="PRO",
        )
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        # Two distinct users so we can exercise SOD: the operator who signed
        # the substeps vs. a separate qualified inspector who buys off.
        self.operator = User.objects.create_user(
            username="op-sod", email="op@sod.test", password="x", tenant=self.tenant,
        )
        self.qa = User.objects.create_user(
            username="qa-sod", email="qa@sod.test", password="x", tenant=self.tenant,
        )

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="P-SOD", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Op-SOD",
            step_type="TASK",
            requires_first_piece_inspection=True,
            requires_qa_signoff=True,
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-SOD-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
            process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-SOD-1", part_type=self.pt,
            work_order=self.wo, step=self.step,
        )
        self.se = StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step,
            visit_number=1, status="IN_PROGRESS",
        )
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, title="Visual", order=1,
        )
        self.fpi = FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step,
            part_type=self.pt, designated_part=self.part,
            status=FPIStatus.PENDING,
        )

    def _sign_substep(self, user):
        """Record that `user` signed the designated first piece's substep."""
        SubstepCompletion.objects.create(
            tenant=self.tenant, step_execution=self.se,
            substep=self.substep, completed_by=user,
        )

    def test_pass_creates_qa_approval(self):
        """FPI Pass records a QaApproval on (step, WO) so the step-level
        QA-signoff blocker is satisfied for advancement."""
        # Operator did the substeps; QA (a different user) buys off.
        self._sign_substep(self.operator)
        self.assertFalse(
            QaApproval.objects.filter(step=self.step, work_order=self.wo).exists()
        )

        pass_fpi(self.fpi, self.qa)

        approval = QaApproval.objects.filter(
            step=self.step, work_order=self.wo,
        ).first()
        self.assertIsNotNone(approval)
        self.assertEqual(approval.qa_staff, self.qa)

    def test_waive_creates_qa_approval(self):
        """FPI Waive with a reason also records a QaApproval — a documented
        waive IS the QA signoff for the first piece run."""
        self._sign_substep(self.operator)
        waive_fpi(self.fpi, self.qa, reason="Prototype run; captures deferred to lot 2.")
        self.assertTrue(
            QaApproval.objects.filter(
                step=self.step, work_order=self.wo, qa_staff=self.qa,
            ).exists()
        )

    def test_fail_does_not_create_qa_approval(self):
        """A FAILED FPI leaves the batch blocked. It must NOT satisfy the
        step-level QA-signoff — production shouldn't advance."""
        self._sign_substep(self.operator)
        fail_fpi(self.fpi, self.qa, notes="Nozzle geometry off spec — investigate.")
        self.assertFalse(
            QaApproval.objects.filter(step=self.step, work_order=self.wo).exists()
        )

    def test_self_signoff_pass_blocked(self):
        """The operator who signed a substep cannot ALSO Pass the FPI on
        their own work. SOD."""
        self._sign_substep(self.operator)
        with self.assertRaises(ValueError) as ctx:
            pass_fpi(self.fpi, self.operator)
        self.assertIn("Segregation of duties", str(ctx.exception))
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)  # unchanged

    def test_self_signoff_fail_blocked(self):
        """Same SOD applies to Fail — a substep signer cannot fail their own
        first-piece inspection."""
        self._sign_substep(self.operator)
        with self.assertRaises(ValueError) as ctx:
            fail_fpi(self.fpi, self.operator)
        self.assertIn("Segregation of duties", str(ctx.exception))
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)

    def test_self_signoff_waive_blocked(self):
        """Same SOD applies to Waive — waiving your own FPI is the exact
        auto-approval SOD exists to prevent."""
        self._sign_substep(self.operator)
        with self.assertRaises(ValueError) as ctx:
            waive_fpi(self.fpi, self.operator, reason="I signed my own captures, waive it.")
        self.assertIn("Segregation of duties", str(ctx.exception))
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)

    def test_different_qa_user_can_signoff(self):
        """The happy path: operator signs substeps, a different QA signs off.
        Both records exist, SOD holds."""
        self._sign_substep(self.operator)
        pass_fpi(self.fpi, self.qa)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PASSED)
        self.assertEqual(self.fpi.inspected_by, self.qa)

    def test_signoff_without_prior_substep_signature_allowed(self):
        """If no substep completions exist yet on the first piece's
        step-execution, the SOD check has nothing to compare against and
        passes. (Prevents the check from over-blocking bare / unusual states.)"""
        # No _sign_substep call.
        pass_fpi(self.fpi, self.qa)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PASSED)

    def test_advancement_gate_clears_after_pass(self):
        """After FPI Pass, `can_advance_from_step` should see both the FPI
        blocker AND the step-level QA-signoff blocker as satisfied. This is
        the whole point of creating the QaApproval on Pass."""
        self._sign_substep(self.operator)
        # Before Pass: both blockers present.
        _, blockers_before = self.step.can_advance_from_step(self.se, self.wo)
        self.assertTrue(any("First Piece Inspection required" in b for b in blockers_before))
        self.assertTrue(any("QA signoff required" in b for b in blockers_before))

        pass_fpi(self.fpi, self.qa)

        # After Pass: neither blocker remains.
        _, blockers_after = self.step.can_advance_from_step(self.se, self.wo)
        self.assertFalse(any("First Piece Inspection required" in b for b in blockers_after))
        self.assertFalse(any("QA signoff required" in b for b in blockers_after))
