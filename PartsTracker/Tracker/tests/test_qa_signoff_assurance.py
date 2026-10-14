"""How sure we are of who released a step is the process author's choice.

`Steps.qa_signoff_assurance` is the step-level twin of a substep sign-off block's
assurance: NONE, where the inspector signs under their login, or PASSWORD, where they
re-enter their own. Whichever path writes the `QaApproval` — the sign-off surface or
the first-piece buy-off — the record says how identity was proven, so the same gate
reads the same way however it was satisfied.

The password is the signer's own rather than a second person's because the inspector
is the one signed in. Independence is segregation's job, and that is enforced
separately: whoever did the work cannot sign it off.
"""
from django.contrib.auth import get_user_model

from Tracker.models import (
    FPIRecord, FPIStatus, PartTypes, Parts, Processes, ProcessStep, QaApproval,
    StepExecution, Steps, Substep, SubstepCompletion, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.services.qms.fpi import pass_fpi, waive_fpi
from Tracker.services.qms.step_signoff import sign_off_step
from Tracker.tests.base import TenantContextMixin, VectorTestCase

PASSWORD = "inspector-pw-1"


class _Fixture(TenantContextMixin, VectorTestCase):
    """A QA-gated step, an operator who did the work and an inspector who didn't."""

    fpi_gated = False

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="QA Assurance", slug="qa-assurance", tier="PRO")
        self.set_tenant_context(self.tenant)
        User = get_user_model()
        self.operator = User.objects.create_user(
            username="op-qa", email="op@qa.test", password="other-pw", tenant=self.tenant)
        self.inspector = User.objects.create_user(
            username="insp-qa", email="insp@qa.test", password=PASSWORD, tenant=self.tenant)

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Widget")
        self.process = Processes.objects.create(tenant=self.tenant, name="P-QA", part_type=self.pt)
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Final Release", step_type="TASK",
            requires_qa_signoff=True, requires_first_piece_inspection=self.fpi_gated)
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-QA-1", workorder_status=WorkOrderStatus.IN_PROGRESS,
            quantity=1, process=self.process)
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-QA-1", part_type=self.pt, work_order=self.wo, step=self.step)
        self.se = StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step, visit_number=1, status="IN_PROGRESS")
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, title="Visual", order=1)
        # The operator did the work, so segregation lets the inspector sign.
        SubstepCompletion.objects.create(
            tenant=self.tenant, step_execution=self.se, substep=self.substep,
            completed_by=self.operator)

    def set_assurance(self, value):
        self.step.qa_signoff_assurance = value
        self.step.save(update_fields=["qa_signoff_assurance"])

    def approval(self):
        return QaApproval.objects.filter(step=self.step, work_order=self.wo).first()


class StepSignOffAssuranceTests(_Fixture):
    def test_a_check_off_step_asks_for_no_password_and_says_so(self):
        sign_off_step(self.wo, self.step, self.inspector)
        a = self.approval()
        self.assertEqual(a.qa_staff_id, self.inspector.id)
        self.assertEqual(a.verification_method, "NONE")
        self.assertIsNone(a.verified_at)

    def test_a_password_step_refuses_a_sign_off_with_no_password(self):
        self.set_assurance("PASSWORD")
        with self.assertRaises(ValueError):
            sign_off_step(self.wo, self.step, self.inspector)
        self.assertIsNone(self.approval())

    def test_a_password_step_refuses_somebody_elses_password(self):
        self.set_assurance("PASSWORD")
        with self.assertRaises(ValueError):
            sign_off_step(self.wo, self.step, self.inspector, password="other-pw")
        self.assertIsNone(self.approval())

    def test_the_right_password_records_the_evidence(self):
        self.set_assurance("PASSWORD")
        sign_off_step(self.wo, self.step, self.inspector, password=PASSWORD, ip_address="10.0.0.9")
        a = self.approval()
        self.assertEqual(a.verification_method, "PASSWORD")
        self.assertIsNotNone(a.verified_at)
        self.assertEqual(a.ip_address, "10.0.0.9")

    def test_the_meaning_is_server_derived_and_names_what_was_released(self):
        sign_off_step(self.wo, self.step, self.inspector)
        self.assertEqual(self.approval().signature_meaning,
                         "QA release of Final Release for WO-QA-1")

    def test_segregation_still_bites_before_the_password_is_ever_asked_for(self):
        """Whoever did the work can't buy a release with their own password."""
        self.set_assurance("PASSWORD")
        # One completion per (execution, substep) — the inspector did this work
        # rather than the operator, so hand the existing row over.
        SubstepCompletion.objects.filter(step_execution=self.se, substep=self.substep).update(
            completed_by=self.inspector)
        with self.assertRaises(ValueError) as caught:
            sign_off_step(self.wo, self.step, self.inspector, password=PASSWORD)
        self.assertIn("Segregation of duties", str(caught.exception))


class FpiBuyOffAssuranceTests(_Fixture):
    """The authored assurance can't be walked around by releasing through FPI."""

    fpi_gated = True

    def setUp(self):
        super().setUp()
        self.fpi = FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step, part_type=self.pt,
            designated_part=self.part, status=FPIStatus.PENDING)

    def test_a_pass_on_a_password_step_needs_the_password(self):
        self.set_assurance("PASSWORD")
        with self.assertRaises(ValueError):
            pass_fpi(self.fpi, self.inspector)
        self.assertIsNone(self.approval())

    def test_a_pass_with_the_password_records_the_same_evidence_as_a_sign_off(self):
        self.set_assurance("PASSWORD")
        pass_fpi(self.fpi, self.inspector, password=PASSWORD, ip_address="10.0.0.9")
        a = self.approval()
        self.assertEqual(a.verification_method, "PASSWORD")
        self.assertIsNotNone(a.verified_at)
        self.assertEqual(a.ip_address, "10.0.0.9")
        self.assertEqual(a.signature_meaning, "QA release of Final Release for WO-QA-1")

    def test_a_waive_is_a_release_too_and_meets_the_same_bar(self):
        self.set_assurance("PASSWORD")
        with self.assertRaises(ValueError):
            waive_fpi(self.fpi, self.inspector, reason="Prototype run, captures deferred.")
        self.assertIsNone(self.approval())
        waive_fpi(self.fpi, self.inspector, reason="Prototype run, captures deferred.",
                  password=PASSWORD)
        self.assertEqual(self.approval().verification_method, "PASSWORD")

    def test_a_co_signature_is_not_asked_for_a_second_password(self):
        """The co-sign path already proved identity with email AND password, which is
        stronger than re-entering your own — asking again would be ceremony."""
        self.set_assurance("PASSWORD")
        pass_fpi(self.fpi, self.inspector, identity_verified=True)
        self.assertEqual(self.approval().verification_method, "PASSWORD")

    def test_a_check_off_step_is_unchanged_by_any_of_this(self):
        pass_fpi(self.fpi, self.inspector)
        a = self.approval()
        self.assertEqual(a.verification_method, "NONE")
        self.assertIsNone(a.verified_at)
