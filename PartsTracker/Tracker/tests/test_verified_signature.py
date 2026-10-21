"""Signing a block inside a substep, and undoing it before the substep is submitted.

An attestation block chooses its own assurance: `confirm` is a tick under the
signer's login, `signature` means they draw and re-enter their own password. The
signature belongs to the block, so its label is the meaning, and
`Substep.requires_signature` is derived from the body rather than toggled
separately — which is what let a substep demand a signature inline AND again at
completion (three of the four seeded substeps made the operator sign twice).

Until the substep is submitted a signature is provisional and can be undone: by
the signer always, by a supervisor holding `clear_gate_signature` when the signer
has gone off shift. Afterwards it stands, and only a QA void retracts it.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError

from Tracker.models import (
    BatchExecution, PartTypes, SubstepCompletion, SubstepGateCompletion, Substep,
    SubstepScope, TenantGroup, UserRole,
)
from Tracker.services.dwi.gate_signature import (
    clear_gate_signature, sign_gate, signature_node_ids, unsigned_signature_blocks,
)
from Tracker.services.dwi.operator_capture import submit_substep
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_advancement_engine import _build_lot

SIG = "data:image/png;base64,iVBORw0KGgo="
NODE = "11111111-1111-1111-1111-111111111111"


def _body(kind: str, label: str = "Release sign-off", node_id: str = NODE) -> dict:
    return {"type": "doc", "content": [
        {"type": "attestationCheckpoint",
         # `required` is about capturing a value; the signature requirement is
         # derived from `kind` and enforced separately. Off here so the capture
         # check doesn't fire first and mask what these tests are about.
         "attrs": {"node_id": node_id, "kind": kind, "label": label, "required": False}},
    ]}


class VerifiedSignatureTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()  # the signing throttle lives in the cache
        self.user_a.set_password("right-pw")
        self.user_a.save()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Vs PT", ID_prefix="VS")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-VS")
        self.se = lot["execs"][0]
        self.substep = lot["substeps_by_step"][0][0]
        self.substep.body_blocks = _body("signature")
        self.substep.save()

    def _sign(self, **kw):
        kw.setdefault("signature_data", SIG)
        kw.setdefault("password", "right-pw")
        return sign_gate(substep=self.substep, step_execution=self.se, node_id=NODE,
                         user=self.user_a, **kw)

    def _submit(self, **kw):
        return submit_substep(substep=self.substep, step_execution=self.se,
                              user=self.user_a, captures=[], **kw)

    # -- the flag follows the body -------------------------------------------

    def test_requires_signature_is_derived_from_the_blocks(self):
        self.substep.refresh_from_db()
        self.assertTrue(self.substep.requires_signature)
        self.assertEqual(signature_node_ids(self.substep), [NODE])

        self.substep.body_blocks = _body("confirm")
        self.substep.save()
        self.substep.refresh_from_db()
        self.assertFalse(self.substep.requires_signature,
                         "a check-off block asks for no signature")

    # -- signing a block ------------------------------------------------------

    def test_a_signature_needs_the_drawing_and_the_right_password(self):
        with self.assertRaisesRegex(ValidationError, "Draw your signature"):
            self._sign(signature_data="")
        with self.assertRaisesRegex(ValidationError, "password"):
            self._sign(password="")
        with self.assertRaisesRegex(ValidationError, "isn't right"):
            self._sign(password="wrong")
        self.assertFalse(SubstepGateCompletion.objects.filter(substep=self.substep).exists())

    def test_a_signed_block_records_who_what_and_when(self):
        gate = self._sign()
        self.assertEqual(gate.completed_by_id, self.user_a.pk)
        self.assertEqual(gate.verification_method, "PASSWORD")
        # The block's own label, not the substep's title: the record says what was
        # signed for.
        self.assertEqual(gate.signature_meaning, "Release sign-off")
        self.assertEqual(gate.signature_data, SIG)
        self.assertIsNotNone(gate.verified_at)

    def test_a_block_cannot_be_signed_twice(self):
        self._sign()
        with self.assertRaisesRegex(ValidationError, "already signed"):
            self._sign()

    def test_only_a_signature_block_can_be_signed(self):
        self.substep.body_blocks = _body("confirm")
        self.substep.save()
        with self.assertRaisesRegex(ValidationError, "doesn't ask for a signature"):
            self._sign()

    def test_repeated_wrong_passwords_are_throttled(self):
        for _ in range(5):
            with self.assertRaises(ValidationError):
                self._sign(password="wrong")
        with self.assertRaisesRegex(ValidationError, "Too many"):
            self._sign()

    # -- submitting -----------------------------------------------------------

    def test_submitting_checks_the_blocks_were_signed_rather_than_asking_again(self):
        self.assertEqual(unsigned_signature_blocks(self.substep, self.se), ["Release sign-off"])
        with self.assertRaisesRegex(ValidationError, "Release sign-off"):
            self._submit()
        self._sign()
        self._submit()
        completion = SubstepCompletion.objects.get(step_execution=self.se, substep=self.substep,
                                                   deleted_at__isnull=True)
        # The completion carries the summary the review list reads; the evidence
        # itself lives on the block's row.
        self.assertEqual(completion.verification_method, "PASSWORD")

    def test_seeded_history_needs_no_signature(self):
        self._submit(preverified=True)
        self.assertTrue(SubstepCompletion.objects.filter(step_execution=self.se).exists())

    # -- undo -----------------------------------------------------------------

    def test_the_signer_can_undo_their_own_before_submission_and_sign_again(self):
        gate = self._sign()
        clear_gate_signature(gate, self.user_a)
        gate.refresh_from_db()
        self.assertIsNotNone(gate.deleted_at)
        self.assertEqual(unsigned_signature_blocks(self.substep, self.se), ["Release sign-off"])
        again = self._sign()  # the slot is free again
        self.assertNotEqual(again.pk, gate.pk)

    def test_undo_is_refused_once_the_substep_is_submitted(self):
        gate = self._sign()
        self._submit()
        with self.assertRaisesRegex(ValidationError, "has been submitted"):
            clear_gate_signature(gate, self.user_a)

    def test_someone_elses_signature_needs_clearing_authority(self):
        gate = self._sign()
        other = get_user_model().objects.create_user(
            username="mate", email="mate@t.test", password="x", tenant=self.tenant_a)
        with self.assertRaisesRegex(ValidationError, "signature"):
            clear_gate_signature(gate, other)

        group = TenantGroup.objects.create(tenant=self.tenant_a, name="Leads", is_custom=True)
        group.permissions.add(*Permission.objects.filter(
            codename__in=["clear_gate_signature", "full_tenant_access"]))
        UserRole.objects.create(user=other, group=group)
        other.set_password("lead-pw")
        other.save()
        # The lead is not the signed-in user — one terminal, one session — so they
        # identify themselves here, the same second-person act as an FPI co-sign.
        clear_gate_signature(gate, self.user_a, email=other.email, password="lead-pw")
        gate.refresh_from_db()
        self.assertIsNotNone(gate.deleted_at)

    # -- batch ----------------------------------------------------------------

    def test_a_batch_block_is_signed_once_for_the_whole_load(self):
        batch_substep = Substep.objects.create(
            tenant=self.tenant_a, step=self.se.step, order=5, title="Run the wash cycle",
            scope=SubstepScope.BATCH, body_blocks=_body("signature", label="Cycle release"))
        parts = [self.se.part] + [
            type(self.se.part).objects.create(
                tenant=self.tenant_a, ERP_id=f"VS-B-{i}", part_type=self.se.part.part_type,
                work_order=self.se.part.work_order, step=self.se.step)
            for i in range(2)
        ]
        batch = BatchExecution.objects.create(
            tenant=self.tenant_a, work_order=self.se.part.work_order, step=self.se.step,
            started_by=self.user_a)
        batch.parts.set(parts)

        gate = sign_gate(substep=batch_substep, batch_execution=batch, node_id=NODE,
                         user=self.user_a, signature_data=SIG, password="right-pw")
        self.assertEqual(gate.batch_execution_id, batch.id)
        self.assertIsNone(gate.step_execution_id)
        self.assertEqual(
            SubstepGateCompletion.objects.filter(substep=batch_substep,
                                                 deleted_at__isnull=True).count(),
            1, "one signature covers the load, not one per part")
        self.assertEqual(len(parts), 3)


class BatchSignatureEndpointTests(TenantTestCase):
    """A signature on a BATCH substep, through the endpoint the runtime uses. The
    viewset dropped batch_execution, so the row had no execution and broke the
    exactly-one check (500, "Could not sign") — no wash load could be sealed in the UI
    (Operator walk 2026-10-20)."""

    def setUp(self):
        super().setUp()
        cache.clear()
        self.user_a.set_password("right-pw")
        self.user_a.save()
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Bs PT", ID_prefix="BS")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-BS")
        self.se = lot["execs"][0]
        self.substep = lot["substeps_by_step"][0][0]
        self.substep.body_blocks = _body("signature")
        self.substep.save()

    def test_a_batch_substep_is_signed_against_the_batch(self):
        from Tracker.models import BatchExecution, SubstepGateCompletion
        batch = BatchExecution.objects.create(
            tenant=self.tenant_a, work_order=self.se.part.work_order, step=self.substep.step,
            started_by=self.user_a)
        batch.parts.set([self.se.part])
        self.grant_tenant_permissions(self.user_a, self.tenant_a,
                                      ['add_substepgatecompletion', 'view_substepgatecompletion',
                                       'full_tenant_access'])
        self.authenticate_as(self.user_a, self.tenant_a)
        body = {"batch_execution": str(batch.id), "substep": self.substep.id, "node_id": NODE,
                "signature_data": SIG, "password": "right-pw"}
        resp = self.client.post("/api/SubstepGateCompletions/", body, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        gate = SubstepGateCompletion.objects.get(substep=self.substep, node_id=NODE)
        self.assertEqual((gate.batch_execution_id, gate.step_execution_id), (batch.id, None))
        # Neither execution: a 400 with a reason, not the constraint's 500.
        body.pop("batch_execution")
        self.assertEqual(self.client.post("/api/SubstepGateCompletions/", body, format="json").status_code, 400)
