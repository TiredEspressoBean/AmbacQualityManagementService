"""FPI buy-off accepts a second-person co-signature.

`FPIRecord` is keyed on `(work_order, step, part_type, designated_part)` — a
step-level QA gate. Its UI, however, lives inside the *part-level operator work
session*, so QA had to claim the operator's `StepExecution` to sign it and got
`409 assigned_to_other`. The fix is the standard DWI / regulated-manufacturing
pattern: the operator's screen holds at the buy-off, an authorized QA person
authenticates inline at that same terminal, and *their* identity is recorded.

What these tests pin:

* **Authorization is an OR, not a weakening.** Either the caller holds
  `sign_off_fpi`, or a verified cosigner does. Supplying no credentials while
  lacking the permission is still refused — `permissions.py` admits a caller
  who *claims* a cosigner only so the view can check them properly (it needs
  the cosigner's identity, and needs to distinguish 429/self/not-permitted
  rather than collapse them into one opaque 403).
* **Attribution follows the cosigner.** `services.qms.fpi` takes the acting
  user explicitly, so `inspected_by`, `QaApproval.qa_staff` and the
  segregation-of-duties check must all name the QA person, not the operator
  who happened to be logged in.
* **SOD still bites.** A cosigner who signed the first piece's substeps cannot
  buy off their own work — and that refusal is a 400, not the 500 it used to be.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from Tracker.models import (
    FPIRecord, FPIStatus, Parts, PartTypes, ProcessStep, Processes, QaApproval,
    StepExecution, Steps, Substep, SubstepCompletion, Tenant, WorkOrder,
    WorkOrderStatus,
)
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class FpiCosignTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Cosign T", slug="cosign-t")
        self.set_tenant_context(self.tenant)

        # The operator at the keyboard: no sign_off_fpi.
        self.operator = User.objects.create_user(
            username="cs-op", email="op@cs.test", password="oppass",
            tenant=self.tenant,
        )
        # The QA inspector who may buy off.
        self.qa = User.objects.create_user(
            username="cs-qa", email="qa@cs.test", password="qapass",
            tenant=self.tenant,
        )
        # A valid login with no sign_off_fpi — proves a real account is not
        # enough on its own.
        self.bystander = User.objects.create_user(
            username="cs-by", email="by@cs.test", password="bypass",
            tenant=self.tenant,
        )

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Cs Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Cs Process", part_type=self.pt,
        )
        self.step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Cs Inspect",
            step_type="TASK", requires_first_piece_inspection=True,
        )
        ProcessStep.objects.create(process=self.process, step=self.step, order=1)
        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-CS-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=2,
            process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-CS-1", part_type=self.pt,
            work_order=self.wo, step=self.step,
        )
        self.substep = Substep.objects.create(
            tenant=self.tenant, step=self.step, order=1,
            title="Cs check", body_blocks={},
        )
        self.execution = StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.step, visit_number=1,
            status="IN_PROGRESS",
            training_authorization={'authorized': True, 'missing': [], 'verified': []},
        )
        self.fpi = FPIRecord.objects.create(
            tenant=self.tenant, work_order=self.wo, step=self.step,
            part_type=self.pt, designated_part=self.part,
            status=FPIStatus.PENDING,
        )

        # The operator performs the first piece. `pass_inspection` blocks on
        # "Substep not completed for this part" without this, which is correct:
        # you cannot buy off work that hasn't been done. Note it checks
        # SubstepCompletion, not the captured responses — which is why the
        # seeded exhibit is signable even though its runtime shows
        # "0 of 2 confirmed" (it has completions but no response values).
        self._sign_substep_as(self.operator)

        self._grant(self.operator, "view_fpirecord", "add_fpirecord",
                    "change_fpirecord", "full_tenant_access", group="cs-ops")
        self._grant(self.qa, "view_fpirecord", "add_fpirecord",
                    "change_fpirecord", "sign_off_fpi", "full_tenant_access",
                    group="cs-qas")
        self._grant(self.bystander, "view_fpirecord", "full_tenant_access",
                    group="cs-bys")

        # Failures write both throttle tiers; clean up targeted keys only
        # (never cache.clear() — see test_second_person_throttle).
        self._keys = {
            f"fpi_cosign_fail:{self.tenant.id}:qa@cs.test",
            f"fpi_cosign_fail:{self.tenant.id}:by@cs.test",
            f"fpi_cosign_fail:{self.tenant.id}:op@cs.test",
            f"second_person_fail:{self.tenant.id}:qa@cs.test",
            f"second_person_fail:{self.tenant.id}:by@cs.test",
            f"second_person_fail:{self.tenant.id}:op@cs.test",
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

    def _pass(self, actor, **body):
        return self._client(actor).post(
            f"/api/FPIRecords/{self.fpi.id}/pass/", body, format="json")

    def _sign_substep_as(self, user):
        SubstepCompletion.objects.update_or_create(
            tenant=self.tenant, step_execution=self.execution,
            substep=self.substep, defaults={'completed_by': user},
        )

    # -- the OR, and that it isn't a weakening ------------------------------

    def test_qa_signs_off_with_no_credentials(self):
        """The pre-existing path: someone holding the permission just signs."""
        resp = self._pass(self.qa, notes="setup verified")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PASSED)
        self.assertEqual(self.fpi.inspected_by_id, self.qa.id)

    def test_operator_with_no_credentials_is_refused(self):
        """The gate is not weakened: lacking the permission and supplying
        nothing is still a 403."""
        resp = self._pass(self.operator, notes="let me through")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)

    def test_operator_with_qa_cosign_succeeds(self):
        """The point of the change — QA signing at the operator's station."""
        resp = self._pass(
            self.operator, notes="nozzle geometry matches drawing",
            cosign_email="qa@cs.test", cosign_password="qapass",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PASSED)

    def test_cosigned_verdict_is_attributed_to_the_qa_person(self):
        self._pass(self.operator, notes="ok",
                   cosign_email="qa@cs.test", cosign_password="qapass")
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.inspected_by_id, self.qa.id,
                         'the attestation belongs to whoever signed it')
        self.assertNotEqual(self.fpi.inspected_by_id, self.operator.id)

    def test_cosign_records_whose_station_it_was(self):
        """`inspected_by` is the cosigner, but who was at the keyboard is real
        audit context and must not be lost."""
        self._pass(self.operator, notes="ok",
                   cosign_email="qa@cs.test", cosign_password="qapass")
        self.fpi.refresh_from_db()
        self.assertIn("Co-signed at", self.fpi.notes)
        self.assertIn(self.operator.username, self.fpi.notes)

    def test_cosign_sets_performed_by_to_the_operator(self):
        """The station operator is captured structurally, not only in a note —
        so co-signature history is queryable. `performed_by` is the operator;
        `inspected_by` is the attesting QA person; the two differ."""
        self._pass(self.operator, notes="ok",
                   cosign_email="qa@cs.test", cosign_password="qapass")
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.performed_by_id, self.operator.id,
                         'performed_by is the operator at whose station QA signed')
        self.assertEqual(self.fpi.inspected_by_id, self.qa.id)
        self.assertNotEqual(self.fpi.performed_by_id, self.fpi.inspected_by_id)

    def test_direct_qa_signoff_leaves_performed_by_null(self):
        """No co-signature → no separate station → performed_by stays null,
        so the field marks *exactly* the co-signed records and nothing else."""
        resp = self._pass(self.qa, notes="direct")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.fpi.refresh_from_db()
        self.assertIsNone(self.fpi.performed_by_id)
        self.assertEqual(self.fpi.inspected_by_id, self.qa.id)

    def test_qa_approval_is_created_for_the_cosigner(self):
        """The FPI pass IS the step-level QA signoff; the QaApproval must name
        the QA person, or the step stays blocked on 'QA signoff required'."""
        self._pass(self.operator, notes="ok",
                   cosign_email="qa@cs.test", cosign_password="qapass")
        approval = QaApproval.objects.filter(
            step=self.step, work_order=self.wo).first()
        self.assertIsNotNone(approval)
        self.assertEqual(approval.qa_staff_id, self.qa.id)

    # -- credential failure modes -------------------------------------------

    def test_cosigner_without_the_permission_is_refused(self):
        resp = self._pass(self.operator, notes="ok",
                          cosign_email="by@cs.test", cosign_password="bypass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_not_permitted")
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)

    def test_cosigner_with_wrong_password_is_refused(self):
        resp = self._pass(self.operator, notes="ok",
                          cosign_email="qa@cs.test", cosign_password="WRONG")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_auth_failed")

    def test_cosigning_as_yourself_is_refused(self):
        """A second person means a *different* person. Without this, an
        operator who knows their own password would self-authorize."""
        resp = self._pass(self.operator, notes="ok",
                          cosign_email="op@cs.test", cosign_password="oppass")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data["code"], "cosign_self")

    def test_qa_cosigning_at_their_own_session_is_not_treated_as_self(self):
        """QA already holds the permission, so the cosign path is never
        consulted — stray credentials must not lock them out of their own
        signoff."""
        resp = self._pass(self.qa, notes="ok",
                          cosign_email="qa@cs.test", cosign_password="qapass")
        self.assertEqual(resp.status_code, 200, resp.content)

    # -- segregation of duties ----------------------------------------------

    def test_cosigner_who_signed_the_substeps_is_refused_with_400(self):
        """SOD: you cannot buy off first-piece work you performed. This used to
        escape `_reject_self_signoff` as an uncaught ValueError → 500."""
        self._sign_substep_as(self.qa)
        resp = self._pass(self.operator, notes="ok",
                          cosign_email="qa@cs.test", cosign_password="qapass")
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("Segregation of duties", resp.data["detail"])
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.status, FPIStatus.PENDING)

    def test_sod_check_follows_the_cosigner_not_the_caller(self):
        """The operator signed the substeps (as setUp arranges), but QA is
        attesting — so SOD must NOT fire. Getting this backwards would block
        every real co-signature, since the operator always signs the work."""
        resp = self._pass(self.operator, notes="ok",
                          cosign_email="qa@cs.test", cosign_password="qapass")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.fpi.refresh_from_db()
        self.assertEqual(self.fpi.inspected_by_id, self.qa.id)


class CosignPermissionLayerTests(TenantContextMixin, TestCase):
    """Isolates the `cosign_actions` branch in `TenantModelPermissions`.

    The endpoint tests above can't prove this layer works, because
    `_resolve_signer` *also* refuses a caller with no credentials — so
    weakening the permission class leaves the HTTP behaviour unchanged (both
    layers refuse, by design). That is good defence in depth and a bad test:
    deleting the branch would go unnoticed.

    These assert the permission class's own verdict, so the pre-check can't
    silently rot into a no-op that only the view is holding up.
    """

    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Perm T", slug="perm-t")
        self.set_tenant_context(self.tenant)
        self.plain = User.objects.create_user(
            username="pl-user", email="pl@perm.test", password="x",
            tenant=self.tenant,
        )
        self.signer = User.objects.create_user(
            username="pl-qa", email="plqa@perm.test", password="x",
            tenant=self.tenant,
        )
        from django.contrib.auth.models import Permission
        from Tracker.models import TenantGroup, UserRole
        grp, _ = TenantGroup.objects.get_or_create(
            tenant=self.tenant, name="pl-qas", defaults={"is_custom": True},
        )
        grp.permissions.add(
            *Permission.objects.filter(codename__in=["sign_off_fpi", "view_fpirecord"]))
        UserRole.objects.get_or_create(user=self.signer, group=grp)
        self.signer.clear_permission_cache(self.tenant)

    def _verdict(self, user, data):
        """Ask TenantModelPermissions directly about a pass_inspection POST."""
        from Tracker.models import FPIRecord
        from Tracker.permissions import TenantModelPermissions

        class _View:
            action = 'pass_inspection'
            # Mirrors FPIRecordViewSet's declarations.
            crud_exempt_actions = {'pass_inspection', 'fail_inspection', 'waive',
                                   'acknowledge'}
            cosign_actions = {'pass_inspection': 'sign_off_fpi'}
            action_permissions = {'acknowledge': ['sign_off_fpi']}
            queryset = FPIRecord.unscoped.all()

        class _Req:
            method = 'POST'

        req = _Req()
        req.user = user
        req.data = data
        return TenantModelPermissions().has_permission(req, _View())

    def test_permission_layer_refuses_when_no_credentials_offered(self):
        """The branch's whole job. If this passes while the branch is deleted,
        only the view is protecting the endpoint."""
        self.assertFalse(self._verdict(self.plain, {}))

    def test_permission_layer_refuses_a_half_supplied_credential(self):
        """An email with no password isn't a claim to check — it would reach the
        view and be refused there, but there's no reason to admit it."""
        self.assertFalse(self._verdict(self.plain, {'cosign_email': 'plqa@perm.test'}))
        self.assertFalse(self._verdict(self.plain, {'cosign_password': 'x'}))
        self.assertFalse(self._verdict(self.plain, {'cosign_email': '   ',
                                                   'cosign_password': 'x'}))

    def test_permission_layer_admits_a_claimed_cosigner(self):
        """Admitted only to be *checked* — the credentials here are deliberately
        wrong, and the view is what rejects them."""
        self.assertTrue(self._verdict(
            self.plain, {'cosign_email': 'plqa@perm.test', 'cosign_password': 'nope'}))

    def test_permission_layer_admits_a_holder_with_no_credentials(self):
        self.assertTrue(self._verdict(self.signer, {}))
