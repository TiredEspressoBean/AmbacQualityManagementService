"""QA sign-off of a QA-gated step (services/qms/step_signoff.py, 2026-10-07).

A step with requires_qa_signoff blocks until a QaApproval exists for (step, work
order). Only FPI pass/waive used to create one, so a QA-gated step without first
piece inspection (reman Core Receiving) parked the unit with nothing for an inspector
to sign. Now: the unit appears as pending, an inspector signs, the lot advances —
and whoever did the step's work can't sign it.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from Tracker.models import QaApproval, Tenant, TenantGroup, UserRole
from Tracker.services.qms.inspection_inbox import build_inbox_rows
from Tracker.services.qms.step_signoff import pending_signoffs, sign_off_step
from Tracker.tests.test_advancement_engine import _build_lot, _complete_substeps_for_part
from Tracker.utils.tenant_context import reset_current_tenant, set_current_tenant_id

User = get_user_model()


class QaStepSignoffTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Signoff Shop", slug="qa-step-signoff")
        self._token = set_current_tenant_id(self.tenant.id)
        self.operator = User.objects.create_user(username="op", email="op@x.test", password="x",
                                                 tenant=self.tenant)
        self.inspector = User.objects.create_user(username="qa", email="qa@x.test", password="x",
                                                  tenant=self.tenant)
        from Tracker.models import PartTypes
        part_type = PartTypes.objects.create(tenant=self.tenant, name="Core", ID_prefix="CR")
        self.lot = _build_lot(tenant=self.tenant, user=self.operator, part_type=part_type,
                              num_steps=2, num_parts=1, substeps_per_step=1, wo_erp_id="WO-SIGN")
        self.step_a, self.step_b = self.lot["steps"]
        self.step_a.requires_qa_signoff = True
        self.step_a.save(update_fields=["requires_qa_signoff"])
        self.part = self.lot["parts"][0]
        self.wo = self.lot["wo"]

    def tearDown(self):
        reset_current_tenant(self._token)

    def _submit(self):
        _complete_substeps_for_part(tenant=self.tenant, user=self.operator, part=self.part,
                                    substeps=self.lot["substeps_by_step"][0])

    def _client(self, user, *perms):
        g = TenantGroup.objects.create(tenant=self.tenant, name=f"g-{user.username}", is_custom=True)
        g.permissions.add(*Permission.objects.filter(codename__in=[*perms, "full_tenant_access"]))
        UserRole.objects.create(user=user, group=g)
        c = APIClient()
        c.force_authenticate(user=user)
        c.credentials(HTTP_X_TENANT_ID=str(self.tenant.id))
        return c

    def test_pending_only_once_the_work_is_submitted(self):
        self.assertEqual(pending_signoffs(), [])
        self._submit()
        pending = pending_signoffs()
        self.assertEqual([(p["work_order"], p["step"], p["units"]) for p in pending],
                         [("WO-SIGN", self.step_a.name, 1)])
        self.assertIn("qa_signoff", [r["type"] for r in build_inbox_rows()])

    def test_the_inspector_signs_and_the_lot_moves_on(self):
        self._submit()
        result = sign_off_step(self.wo, self.step_a, self.inspector)
        self.assertTrue(QaApproval.objects.filter(step=self.step_a, work_order=self.wo,
                                                  qa_staff=self.inspector).exists())
        self.assertEqual(result.status, "advanced")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.step_b.id)
        self.assertEqual(pending_signoffs(), [])

    def test_whoever_did_the_work_cannot_sign_it(self):
        self._submit()
        with self.assertRaisesRegex(ValueError, "Segregation of duties"):
            sign_off_step(self.wo, self.step_a, self.operator)

    def test_whoever_ran_the_step_cannot_sign_it_even_without_substeps(self):
        """D6 (2026-10-29): the open visit's assignee is barred too, not only substep
        signers."""
        from Tracker.models import StepExecution
        self._submit()
        lead = User.objects.create_user(username="lead", email="lead@x.test", password="x",
                                        tenant=self.tenant)
        StepExecution.objects.filter(part=self.part, step=self.step_a, exited_at__isnull=True
                                     ).update(assigned_to=lead)
        with self.assertRaisesRegex(ValueError, "Segregation of duties"):
            sign_off_step(self.wo, self.step_a, lead)

    def test_fpi_gated_steps_are_left_to_their_buy_off(self):
        self.step_a.requires_first_piece_inspection = True
        self.step_a.save(update_fields=["requires_first_piece_inspection"])
        self._submit()
        self.assertEqual(pending_signoffs(), [])
        with self.assertRaisesRegex(ValueError, "first piece"):
            sign_off_step(self.wo, self.step_a, self.inspector)

    def test_the_endpoint_needs_sign_off_authority(self):
        self._submit()
        body = {"work_order": str(self.wo.id), "step": str(self.step_a.id)}
        operator = self._client(self.operator, "view_stepexecution")  # as the Operator preset
        refused = operator.post("/api/InspectionInbox/sign-off-step/", body, format="json")
        self.assertEqual(refused.status_code, 403)
        ok = self._client(self.inspector, "sign_off_fpi").post("/api/InspectionInbox/sign-off-step/", body,
                                                               format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.json()["parts_advanced"], 1)
        listed = operator.get(f"/api/InspectionInbox/qa-signoffs/?work_order={self.wo.id}")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])
