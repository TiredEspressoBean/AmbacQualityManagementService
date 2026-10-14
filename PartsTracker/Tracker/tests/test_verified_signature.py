"""Verified sign-off: an authored, opt-in signature level (2026-10-13).

A substep with `requires_signature` is signed by drawing a signature AND re-entering
the signer's own password — two components at signing, the meaning, server time.
Without the flag a signature node stays a one-click attestation under the signed-in
user. The flag used to promise "signature required" and enforce nothing, and the
client could claim `verification_method=PASSWORD` without one.

Also pins void-then-recapture: a voided completion used to be rewritten in place
(still voided), so the re-capture never counted.
"""
from django.core.cache import cache
from django.core.exceptions import ValidationError

from Tracker.models import PartTypes, SubstepCompletion
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_advancement_engine import _build_lot

SIG = "data:image/png;base64,iVBORw0KGgo="


class VerifiedSignatureTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()  # throttle counters live in the cache
        self.user_a.set_password("right-pw")
        self.user_a.save()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Vs PT", ID_prefix="VS")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-VS")
        self.se = lot["execs"][0]
        self.substep = lot["substeps_by_step"][0][0]
        self.substep.requires_signature = True
        self.substep.save(update_fields=["requires_signature"])

    def _submit(self, **kw):
        return submit_substep(substep=self.substep, step_execution=self.se, user=self.user_a,
                              captures=[], **kw)

    def _completion(self):
        return SubstepCompletion.objects.get(step_execution=self.se, substep=self.substep,
                                             deleted_at__isnull=True)

    def test_a_verified_sign_off_needs_the_drawing_and_the_password(self):
        with self.assertRaisesRegex(ValidationError, "needs your signature"):
            self._submit(password="right-pw")
        with self.assertRaisesRegex(ValidationError, "password"):
            self._submit(signature_data=SIG)
        with self.assertRaisesRegex(ValidationError, "isn't right"):
            self._submit(signature_data=SIG, password="wrong")
        self.assertFalse(SubstepCompletion.objects.filter(step_execution=self.se).exists())

    def test_a_good_signature_is_recorded_as_password_verified(self):
        self._submit(signature_data=SIG, password="right-pw")
        c = self._completion()
        self.assertEqual(c.verification_method, "PASSWORD")
        self.assertEqual(c.signature_meaning, self.substep.title)
        self.assertEqual(c.signature_data, SIG)
        self.assertIsNotNone(c.verified_at)

    def test_the_client_cannot_claim_a_password_verification(self):
        self.substep.requires_signature = False
        self.substep.save(update_fields=["requires_signature"])
        self._submit(signature_data=SIG, verification_method="PASSWORD")
        self.assertEqual(self._completion().verification_method, "NONE")

    def test_na_and_seeded_history_need_no_password(self):
        self.substep.allow_not_applicable = True
        self.substep.save(update_fields=["allow_not_applicable"])
        self._submit(marked_not_applicable=True, na_reason_code="NOT_APPLICABLE")
        self.assertTrue(self._completion().marked_not_applicable)
        SubstepCompletion.objects.all().delete()
        self._submit(signature_data=SIG, preverified=True)
        self.assertEqual(self._completion().verification_method, "NONE")

    def test_repeated_wrong_passwords_are_throttled(self):
        for _ in range(5):
            with self.assertRaises(ValidationError):
                self._submit(signature_data=SIG, password="wrong")
        with self.assertRaisesRegex(ValidationError, "Too many"):
            self._submit(signature_data=SIG, password="right-pw")

    def test_a_batch_substep_is_signed_once_for_the_whole_load(self):
        """The claim the browser walk could only show on a one-part load: a BATCH
        substep takes ONE signature for the load, recorded against the
        BatchExecution rather than per part."""
        from Tracker.models import BatchExecution, Substep, SubstepScope
        batch_substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.se.step, order=5, title="Run the wash cycle",
            scope=SubstepScope.BATCH, requires_signature=True)
        parts = [self.se.part] + [
            type(self.se.part).objects.create(
                tenant=self.tenant_a, ERP_id=f"VS-BATCH-{i}", part_type=self.se.part.part_type,
                work_order=self.se.part.work_order, step=self.se.step)
            for i in range(2)
        ]
        batch = BatchExecution.objects.create(
            tenant=self.tenant_a, work_order=self.se.part.work_order, step=self.se.step,
            started_by=self.user_a)
        batch.parts.set(parts)

        with self.assertRaisesRegex(ValidationError, "needs your signature"):
            submit_substep(substep=batch_substep, batch_execution=batch, user=self.user_a,
                           captures=[])
        submit_substep(substep=batch_substep, batch_execution=batch, user=self.user_a,
                       captures=[], signature_data=SIG, password="right-pw")

        rows = SubstepCompletion.objects.filter(substep=batch_substep, deleted_at__isnull=True)
        self.assertEqual(rows.count(), 1, "one signature covers the load, not one per part")
        row = rows.get()
        self.assertEqual(row.verification_method, "PASSWORD")
        self.assertEqual(row.batch_execution_id, batch.id)
        self.assertIsNone(row.step_execution_id)
        self.assertEqual(len(parts), 3)  # the load really had more than one part

    def test_a_voided_completion_is_captured_again_as_a_new_live_one(self):
        self._submit(signature_data=SIG, password="right-pw")
        first = self._completion()
        first.void(self.user_a, "signed the wrong unit")
        self._submit(signature_data=SIG, password="right-pw")
        live = self._completion()
        self.assertNotEqual(live.pk, first.pk)
        self.assertFalse(live.is_voided)
        first.refresh_from_db()
        self.assertTrue(first.is_voided)  # kept as history
