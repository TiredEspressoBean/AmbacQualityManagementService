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
        # A name to show on the record, not the login.
        self.assertEqual(sig["display_name"],
                         self.user_a.get_full_name().strip() or self.user_a.get_username())

    def test_signing_as_someone_else_is_refused(self):
        cap = {"node_id": "n1", "kind": "attestation",
               "signature": {"user_id": self.inspector.pk, "signed_at": "2026-01-01T00:00:00Z"}}
        with self.assertRaisesRegex(ValidationError, "sign as yourself"):
            self._stamp(cap, self.user_a)

    def test_the_operator_cannot_fill_the_verifying_slot_themselves(self):
        """A verification is a second person's, and a shop terminal has one session.
        So the slot is not stamped from the session at all: the verifier enters their
        own email and password here. The operator naming themselves — or anyone
        else — without those is refused."""
        cap = {"node_id": "n1", "kind": "signatures",
               "detected": {"user_id": self.user_a.pk},
               "verified": {"user_id": self.user_a.pk}}
        with self.assertRaisesRegex(ValidationError, "second person"):
            self._stamp(cap, self.user_a)

    def test_a_verifier_co_signs_with_their_own_credentials(self):
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole

        self.inspector.set_password("qa-pw")
        self.inspector.save()
        group = TenantGroup.objects.create(tenant=self.tenant_a, name="QA", is_custom=True)
        group.permissions.add(*Permission.objects.filter(
            codename__in=["sign_off_fpi", "full_tenant_access"]))
        UserRole.objects.create(user=self.inspector, group=group)

        cap = {"node_id": "n1", "kind": "signatures",
               "detected": {"user_id": self.user_a.pk},
               "verified": {"cosign_email": self.inspector.email, "cosign_password": "qa-pw"}}
        out = self._stamp(cap, self.user_a)
        self.assertEqual(out["verified"]["user_id"], self.inspector.pk)
        self.assertEqual(out["detected"]["user_id"], self.user_a.pk)
        # The credentials are consumed, never stored.
        self.assertNotIn("cosign_password", out["verified"])

    def test_the_finder_signs_with_their_own_password_when_the_author_asks(self):
        """The finder's slot is the author's choice: a click, or their own drawn
        signature and password. It is still their own signature, so it is their
        password — not a second person's."""
        self.substep.body_blocks = {"type": "doc", "content": [
            {"type": "inspectionSignatures", "attrs": {
                "node_id": "n1", "require_detected": True,
                "detected_assurance": "signature"}},
        ]}
        self.substep.save()
        self.user_a.set_password("op-pw")
        self.user_a.save()

        cap = {"node_id": "n1", "kind": "signatures", "detected": {"user_id": self.user_a.pk}}
        with self.assertRaisesRegex(ValidationError, "Draw your signature"):
            self._stamp(cap, self.user_a)

        cap["detected"] = {"user_id": self.user_a.pk, "data_uri": "data:image/png;base64,x"}
        with self.assertRaisesRegex(ValidationError, "password"):
            self._stamp(cap, self.user_a)

        cap["detected"]["password"] = "op-pw"
        out = self._stamp(cap, self.user_a)
        self.assertEqual(out["detected"]["user_id"], self.user_a.pk)
        self.assertNotIn("password", out["detected"])  # consumed, never stored

    def test_a_clicked_finding_still_only_needs_a_click(self):
        cap = {"node_id": "n1", "kind": "signatures", "detected": {"user_id": self.user_a.pk}}
        out = self._stamp(cap, self.user_a)  # the block's default is confirm
        self.assertEqual(out["detected"]["user_id"], self.user_a.pk)

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
        # Carried through untouched, and QA is not asked to stand at the terminal
        # again just because the operator re-saved the substep.
        self.assertEqual(out["verified"], verified)
        self.assertEqual(out["detected"]["user_id"], self.user_a.pk)
