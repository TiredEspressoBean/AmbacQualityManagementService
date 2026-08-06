"""The disposition DECISION accepts a second-person co-signature.

Choosing a `disposition_type` (rework / repair / scrap / use-as-is / return-to-
supplier) is the authorized act under AS9100 & ISO 9001 8.7 and 21 CFR 820.90 —
the record must carry the signature of the individual authorizing the
disposition. Before this it was an ungated field write; `approve_disposition`
was declared but enforced nowhere.

Now it goes through `POST /QuarantineDispositions/{id}/decide/`, gated by
`approve_disposition` with the same second-person path as the FPI buy-off:

* **Authorization is an OR, not a weakening.** Either the caller holds
  `approve_disposition`, or a verified cosigner does. No credentials + no
  permission is still refused.
* **Attribution follows the authorizer.** `decision_authorized_by` names whoever
  signed — the caller, or the inline co-signer — never merely whoever was logged
  in.
* **USE_AS_IS / REPAIR need a concession.** Accepting nonconforming product
  requires a recorded customer/design-approval reference, or the decision is a
  400.
* **The PATCH bypass is closed.** `disposition_type` is read-only on update, so
  the decision cannot be set outside the co-signable `decide` action.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from Tracker.models import QuarantineDisposition, Tenant
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class DispositionDecideCosignTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Disp Cosign T", slug="disp-cosign-t")
        self.set_tenant_context(self.tenant)

        # Inspector at the keyboard: no approve_disposition.
        self.inspector = User.objects.create_user(
            username="dc-insp", email="insp@dc.test", password="insppass",
            tenant=self.tenant,
        )
        # QA Manager who may authorize disposition decisions.
        self.qa = User.objects.create_user(
            username="dc-qa", email="qa@dc.test", password="qapass",
            tenant=self.tenant,
        )
        # Valid login, no approve_disposition — a real account is not enough.
        self.bystander = User.objects.create_user(
            username="dc-by", email="by@dc.test", password="bypass",
            tenant=self.tenant,
        )

        self._grant(self.inspector, "view_quarantinedisposition", "full_tenant_access",
                    group="dc-insps")
        self._grant(self.qa, "view_quarantinedisposition", "change_quarantinedisposition",
                    "approve_disposition", "full_tenant_access", group="dc-qas")
        self._grant(self.bystander, "view_quarantinedisposition", "full_tenant_access",
                    group="dc-bys")

        # OPEN, no disposition_type yet — the auto-created-then-decided flow.
        self.disp = QuarantineDisposition.unscoped.create(
            tenant=self.tenant, severity="MINOR", description="decide test",
        )
        self.assertEqual(self.disp.current_state, "OPEN")
        self.assertEqual(self.disp.disposition_type, "")

        self._keys = {
            f"disposition_decide_fail:{self.tenant.id}:{e}"
            for e in ("qa@dc.test", "by@dc.test", "insp@dc.test")
        } | {
            f"second_person_fail:{self.tenant.id}:{e}"
            for e in ("qa@dc.test", "by@dc.test", "insp@dc.test")
        }

    def tearDown(self):
        for k in self._keys:
            cache.delete(k)
        super().tearDown()

    # -- helpers ------------------------------------------------------------

    def _grant(self, user, *codenames, group):
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        grp, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant, name=group, defaults={"is_custom": True},
        )
        grp.permissions.add(*Permission.objects.filter(codename__in=codenames))
        UserRole.objects.get_or_create(user=user, group=grp)
        user.clear_permission_cache(self.tenant)

    def _client(self, user):
        from rest_framework.test import APIClient
        c = APIClient()
        c.force_authenticate(user=user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def _decide_url(self, disp=None):
        return reverse("QuarantineDispositions-decide",
                       kwargs={"pk": str((disp or self.disp).id)})

    def _decide(self, actor, **body):
        return self._client(actor).post(self._decide_url(), body, format="json")

    # -- the OR, and that it isn't a weakening ------------------------------

    def test_authorized_user_decides_directly(self):
        resp = self._decide(self.qa, disposition_type="REWORK", notes="rework per drawing")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "REWORK")
        self.assertEqual(self.disp.current_state, "IN_PROGRESS")  # save() auto-advanced
        self.assertEqual(self.disp.decision_authorized_by_id, self.qa.id)
        self.assertIsNotNone(self.disp.decision_authorized_at)

    def test_inspector_with_no_credentials_is_refused(self):
        # No permission and no co-signature claim → the permission layer refuses
        # before the view runs (a generic 403), so the gate is not weakened. The
        # view's own `cosign_required` is the belt-and-braces path for a caller
        # the layer let through; both layers refuse an unauthorized caller.
        resp = self._decide(self.inspector, disposition_type="REWORK")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "")
        self.assertEqual(self.disp.current_state, "OPEN")

    def test_inspector_with_qa_cosign_succeeds(self):
        resp = self._decide(
            self.inspector, disposition_type="SCRAP",
            cosign_email="qa@dc.test", cosign_password="qapass",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "SCRAP")

    def test_decision_is_attributed_to_the_cosigner(self):
        self._decide(self.inspector, disposition_type="REWORK",
                     cosign_email="qa@dc.test", cosign_password="qapass")
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.decision_authorized_by_id, self.qa.id,
                         "the authority belongs to whoever authorized it")
        self.assertNotEqual(self.disp.decision_authorized_by_id, self.inspector.id)

    # -- credential failure modes -------------------------------------------

    def test_cosigner_without_the_permission_is_refused(self):
        resp = self._decide(self.inspector, disposition_type="REWORK",
                            cosign_email="by@dc.test", cosign_password="bypass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_not_permitted")
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "")

    def test_cosigner_with_wrong_password_is_refused(self):
        resp = self._decide(self.inspector, disposition_type="REWORK",
                            cosign_email="qa@dc.test", cosign_password="WRONG")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_auth_failed")

    def test_authorizing_as_yourself_is_refused(self):
        """A second person means a *different* person. Without this, someone who
        knows their own password would self-authorize."""
        resp = self._decide(self.bystander, disposition_type="REWORK",
                            cosign_email="by@dc.test", cosign_password="bypass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_self")

    # -- USE_AS_IS / REPAIR need a concession -------------------------------

    def test_use_as_is_without_customer_approval_is_refused(self):
        resp = self._decide(self.qa, disposition_type="USE_AS_IS")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("customer", resp.data["detail"].lower())
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "")

    def test_use_as_is_with_customer_approval_succeeds(self):
        resp = self._decide(self.qa, disposition_type="USE_AS_IS",
                            customer_approval_reference="DEV-2026-014")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "USE_AS_IS")
        self.assertTrue(self.disp.requires_customer_approval)
        self.assertTrue(self.disp.customer_approval_received)
        self.assertEqual(self.disp.customer_approval_reference, "DEV-2026-014")

    def test_repair_also_requires_a_concession(self):
        resp = self._decide(self.qa, disposition_type="REPAIR")
        self.assertEqual(resp.status_code, 400, resp.content)

    # -- guards --------------------------------------------------------------

    def test_decide_on_a_closed_disposition_is_refused(self):
        self.disp.disposition_type = "SCRAP"
        self.disp.current_state = "CLOSED"
        self.disp.save()
        resp = self._decide(self.qa, disposition_type="REWORK")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "SCRAP")  # unchanged

    def test_unknown_type_is_refused(self):
        resp = self._decide(self.qa, disposition_type="TELEPORT")
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_missing_type_is_refused(self):
        resp = self._decide(self.qa)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.data["code"], "decide_type_required")

    # -- the PATCH bypass is closed -----------------------------------------

    def test_disposition_type_cannot_be_set_via_patch(self):
        """The whole point: the decision must go through `decide`. A plain PATCH
        of `disposition_type` is silently dropped (read-only on update), so the
        gate can't be bypassed."""
        url = reverse("QuarantineDispositions-detail", kwargs={"pk": str(self.disp.id)})
        resp = self._client(self.qa).patch(url, {"disposition_type": "SCRAP"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "")  # untouched
        self.assertEqual(self.disp.current_state, "OPEN")

    def test_patch_can_still_change_a_decided_type_only_via_decide(self):
        """After a decision, PATCH still can't overwrite it — only `decide` can."""
        self._decide(self.qa, disposition_type="REWORK")
        url = reverse("QuarantineDispositions-detail", kwargs={"pk": str(self.disp.id)})
        self._client(self.qa).patch(url, {"disposition_type": "SCRAP"}, format="json")
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "REWORK")  # PATCH ignored
        # ...but a fresh authorized decision can correct it.
        resp = self._decide(self.qa, disposition_type="SCRAP")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.disp.refresh_from_db()
        self.assertEqual(self.disp.disposition_type, "SCRAP")
