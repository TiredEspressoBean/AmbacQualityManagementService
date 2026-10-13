"""A signature taken in the step player records who actually signed, at the server's
clock (2026-10-13).

`user_id` and `signed_at` came from the browser and were stored as sent — into the
response and into the QR personnel roster — so any operator could record anyone as
an inspection's verifier. `_stamp_signers` (services/dwi/operator_capture.py) now
stamps the submitter; a signature naming someone else survives only as the
unchanged carry-over of what was already stored.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from Tracker.models import PartTypes, SubstepResponse, SubstepResponseKind
from Tracker.services.dwi.operator_capture import _stamp_signers
from Tracker.tests.base import TenantTestCase
from Tracker.tests.test_advancement_engine import _build_lot


class SignatureStampingTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.inspector = get_user_model().objects.create_user(
            username="qa-sig", email="qa-sig@t.test", password="x", tenant=self.tenant_a)
        pt = PartTypes.objects.create(tenant=self.tenant_a, name="Sig PT", ID_prefix="SG")
        lot = _build_lot(tenant=self.tenant_a, user=self.user_a, part_type=pt, wo_erp_id="WO-SIG")
        self.se = lot["execs"][0]
        self.substep = lot["substeps_by_step"][0][0]

    def _stamp(self, cap, user):
        return _stamp_signers(cap, user=user, substep=self.substep, step_execution=self.se,
                              batch_execution=None)

    def test_the_submitter_is_the_signer_whatever_the_client_says_about_time(self):
        cap = {"node_id": "n1", "kind": "attestation",
               "signature": {"user_id": None, "signed_at": "1999-01-01T00:00:00Z"}}
        sig = self._stamp(cap, self.user_a)["signature"]
        self.assertEqual(sig["user_id"], self.user_a.pk)
        self.assertEqual(sig["username"], self.user_a.get_username())
        self.assertNotEqual(sig["signed_at"], "1999-01-01T00:00:00Z")

    def test_signing_as_someone_else_is_refused(self):
        cap = {"node_id": "n1", "kind": "signatures",
               "detected": {"user_id": self.user_a.pk},
               "verified": {"user_id": self.inspector.pk, "signed_at": "2026-01-01T00:00:00Z"}}
        with self.assertRaisesRegex(ValidationError, "sign as yourself"):
            self._stamp(cap, self.user_a)

    def test_an_earlier_signature_by_someone_else_carries_over_unchanged(self):
        verified = {"user_id": self.inspector.pk, "username": "qa-sig",
                    "signed_at": "2026-10-13T09:00:00+00:00"}
        SubstepResponse.objects.create(
            tenant=self.tenant_a, step_execution=self.se, substep=self.substep, node_id="n1",
            kind=SubstepResponseKind.SIGNATURES, value_json={"verified": verified},
            responded_by=self.inspector)
        cap = {"node_id": "n1", "kind": "signatures",
               "detected": {"user_id": self.user_a.pk}, "verified": dict(verified)}
        out = self._stamp(cap, self.user_a)
        self.assertEqual(out["verified"], verified)
        self.assertEqual(out["detected"]["user_id"], self.user_a.pk)
