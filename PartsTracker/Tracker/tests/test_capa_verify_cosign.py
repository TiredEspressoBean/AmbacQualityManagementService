"""Recording a CAPA's effectiveness verification is a co-signable authorized act.

Effectiveness verification is two-stage: the *plan* (method + criteria) is plain
CRUD; recording the *outcome* is the authorized act (verify_capa). Before this it
was a bare field write on `CapaVerification.effectiveness_result` — which never
ran the self-verification SoD check and never closed/reopened the CAPA (the
`verify_capa_effectiveness` service existed but nothing called it). Now the
outcome goes through `POST /CapaVerifications/{id}/verify/`, gated by verify_capa
with the same second-person path as the FPI buy-off and disposition decision.

Pins:
* the OR gate (holder verifies directly; a non-holder needs a verified cosigner)
  and that it isn't weakened (no creds + no perm → refused);
* attribution follows the signer (`verified_by`);
* the outcome actually drives the CAPA — CONFIRMED closes it, NOT_EFFECTIVE
  reopens it and spawns a follow-up task (the gap this fixes);
* the self-verification SoD rule still bites (initiator/assignee can't verify
  without allow_self_verification);
* the outcome can't be set via a bare PATCH (read-only).
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from Tracker.models import (
    CAPA, CapaSeverity, CapaStatus, CapaType, CapaTasks, CapaVerification,
    EffectivenessResult, Tenant,
)
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class CapaVerifyCosignTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Capa Cosign T", slug="capa-cosign-t")
        self.set_tenant_context(self.tenant)

        # The engineer who owns the CAPA (initiator/assignee) — not a verifier.
        self.owner = User.objects.create_user(
            username="cv-own", email="own@cv.test", password="ownpass", tenant=self.tenant)
        # QA Manager who may verify effectiveness.
        self.qa = User.objects.create_user(
            username="cv-qa", email="qa@cv.test", password="qapass", tenant=self.tenant)
        # Valid login, no verify_capa.
        self.bystander = User.objects.create_user(
            username="cv-by", email="by@cv.test", password="bypass", tenant=self.tenant)

        self._grant(self.owner, "view_capa", "view_capaverification", "full_tenant_access",
                    group="cv-owners")
        self._grant(self.qa, "view_capa", "view_capaverification", "verify_capa",
                    "change_capaverification", "full_tenant_access", group="cv-qas")
        self._grant(self.bystander, "view_capa", "view_capaverification", "full_tenant_access",
                    group="cv-bys")

        self.capa = CAPA.objects.create(
            tenant=self.tenant, capa_number="CAPA-CV-1", problem_statement="scoring",
            capa_type=CapaType.CORRECTIVE, severity=CapaSeverity.MAJOR,
            initiated_by=self.owner, assigned_to=self.owner, status=CapaStatus.IN_PROGRESS,
        )
        self.verification = CapaVerification.objects.create(
            tenant=self.tenant, capa=self.capa,
            verification_method="Monitor 30 days.", verification_criteria="Zero defects.",
        )
        self.assertEqual(self.verification.effectiveness_result, EffectivenessResult.INCONCLUSIVE)

        self._keys = {
            f"capa_verify_fail:{self.tenant.id}:{e}" for e in ("qa@cv.test", "by@cv.test", "own@cv.test")
        } | {
            f"second_person_fail:{self.tenant.id}:{e}" for e in ("qa@cv.test", "by@cv.test", "own@cv.test")
        }

    def tearDown(self):
        for k in self._keys:
            cache.delete(k)
        super().tearDown()

    def _grant(self, user, *codenames, group):
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        grp, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant, name=group, defaults={"is_custom": True})
        grp.permissions.add(*Permission.objects.filter(codename__in=codenames))
        UserRole.objects.get_or_create(user=user, group=grp)
        user.clear_permission_cache(self.tenant)

    def _client(self, user):
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(user=user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def _verify_url(self):
        return reverse("CapaVerifications-verify", kwargs={"pk": str(self.verification.id)})

    def _verify(self, actor, **body):
        return self._client(actor).post(self._verify_url(), body, format="json")

    # -- the OR, and the outcome actually drives the CAPA -------------------

    def test_holder_verifies_and_confirmed_closes_the_capa(self):
        resp = self._verify(self.qa, effectiveness_result="CONFIRMED", notes="clean 30d")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.verification.refresh_from_db()
        self.capa.refresh_from_db()
        self.assertEqual(self.verification.effectiveness_result, EffectivenessResult.CONFIRMED)
        self.assertEqual(self.verification.verified_by_id, self.qa.id)
        self.assertEqual(self.capa.status, CapaStatus.CLOSED)  # the gap this fixes

    def test_not_effective_reopens_and_spawns_followup(self):
        resp = self._verify(self.qa, effectiveness_result="NOT_EFFECTIVE", notes="still failing")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.capa.refresh_from_db()
        self.assertEqual(self.capa.status, CapaStatus.IN_PROGRESS)
        self.assertTrue(CapaTasks.objects.filter(capa=self.capa).exists())

    def test_inspector_with_qa_cosign_is_attributed_to_the_qa_person(self):
        resp = self._verify(self.bystander, effectiveness_result="CONFIRMED", notes="ok",
                            cosign_email="qa@cv.test", cosign_password="qapass")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.verified_by_id, self.qa.id)
        self.assertNotEqual(self.verification.verified_by_id, self.bystander.id)

    def test_no_permission_no_credentials_is_refused(self):
        resp = self._verify(self.bystander, effectiveness_result="CONFIRMED")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.effectiveness_result, EffectivenessResult.INCONCLUSIVE)

    # -- credential failure modes -------------------------------------------

    def test_cosigner_without_the_permission_is_refused(self):
        # The owner holds no verify_capa; claiming them as cosigner is not permitted.
        resp = self._verify(self.bystander, effectiveness_result="CONFIRMED", notes="ok",
                            cosign_email="own@cv.test", cosign_password="ownpass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_not_permitted")

    def test_cosigner_with_wrong_password_is_refused(self):
        resp = self._verify(self.bystander, effectiveness_result="CONFIRMED", notes="ok",
                            cosign_email="qa@cv.test", cosign_password="WRONG")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_auth_failed")

    def test_cosigning_as_yourself_is_refused(self):
        resp = self._verify(self.bystander, effectiveness_result="CONFIRMED", notes="ok",
                            cosign_email="by@cv.test", cosign_password="bypass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_self")

    # -- self-verification SoD (service-level) still bites ------------------

    def test_self_verification_by_the_owner_is_refused(self):
        """The CAPA owner holds verify_capa but is the assignee; with
        allow_self_verification off, the service refuses (→ 400, not 500)."""
        self._grant(self.owner, "verify_capa", group="cv-owners")
        resp = self._verify(self.owner, effectiveness_result="CONFIRMED", notes="my own work")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("self-verification", resp.data["detail"].lower())
        self.capa.refresh_from_db()
        self.assertEqual(self.capa.status, CapaStatus.IN_PROGRESS)  # not closed

    # -- guards + the PATCH bypass is closed --------------------------------

    def test_invalid_result_is_refused(self):
        resp = self._verify(self.qa, effectiveness_result="INCONCLUSIVE")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.data["code"], "verify_result_required")

    def test_effectiveness_result_cannot_be_set_via_patch(self):
        url = reverse("CapaVerifications-detail", kwargs={"pk": str(self.verification.id)})
        resp = self._client(self.qa).patch(url, {"effectiveness_result": "CONFIRMED"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.verification.refresh_from_db()
        self.capa.refresh_from_db()
        self.assertEqual(self.verification.effectiveness_result, EffectivenessResult.INCONCLUSIVE)
        self.assertEqual(self.capa.status, CapaStatus.IN_PROGRESS)  # PATCH didn't verify/close
