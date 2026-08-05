"""Resolving a MANUAL decision point accepts a second-person co-signature.

Same category mismatch as FPI buy-off, in the same place. A MANUAL
decision-point step is a *lead's* routing choice, but the operator meets it at
their station, mid-run, with the part physically stopped there — and lacks
`resolve_step_decision`. `DecisionResolverPanel` rendered them a sentence ("a
manager or lead must resolve this decision") and no affordance, so the only way
forward was to find a lead with their own terminal.

This gate warrants the care more than most: `resolve_decision` calls
`advance_part_step(skip_gate_check=True)`, deliberately bypassing the
per-part advancement gate, so the permission is the *only* control on the
routing choice.

What these tests pin:

* **Authorization is an OR, not a weakening** — no credentials while lacking
  the permission is still refused.
* **Authority and labor come apart.** `advance_part_step`'s `operator` argument
  serves two roles: the transition's actor, and (on a
  `revisit_assignment='same'` step) the next StepExecution's `assigned_to`.
  Under a co-signature those are different people. The transition log must name
  the lead who chose the branch; the next step must stay assigned to the
  operator who is doing the work. Attributing both to the cosigner would hand a
  lead who walked past a station the operator's next job.
* **The routing choice itself is unaffected** — a co-signed ALTERNATE goes to
  the same step a lead's own ALTERNATE does.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from Tracker.models import (
    EdgeType, Parts, PartTypes, ProcessStep, Processes, StepEdge, StepExecution,
    Steps, Tenant, WorkOrder, WorkOrderStatus,
)
from Tracker.models.qms import StepTransitionLog
from Tracker.tests.base import TenantContextMixin

User = get_user_model()


class DecisionCosignTests(TenantContextMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Dec T", slug="dec-cosign-t")
        self.set_tenant_context(self.tenant)

        # At the keyboard, no resolve_step_decision.
        self.operator = User.objects.create_user(
            username="dc-op", email="op@dc.test", password="oppass",
            first_name="Olive", last_name="Op", tenant=self.tenant,
        )
        # The lead who may choose the branch.
        self.lead = User.objects.create_user(
            username="dc-lead", email="lead@dc.test", password="leadpass",
            first_name="Lena", last_name="Lead", tenant=self.tenant,
        )
        # A real account without the perm — proves a valid login isn't enough.
        self.bystander = User.objects.create_user(
            username="dc-by", email="by@dc.test", password="bypass",
            tenant=self.tenant,
        )

        self.pt = PartTypes.objects.create(tenant=self.tenant, name="Dc Widget")
        self.process = Processes.objects.create(
            tenant=self.tenant, name="Dc Process", part_type=self.pt,
        )
        # revisit_assignment='same' is the case that separates authority from
        # labor: the next step inherits `operator` as its assignee.
        self.gate = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Dc Decide",
            step_type="TASK", is_decision_point=True, decision_type="MANUAL",
        )
        self.pass_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Dc Final",
            step_type="TASK", revisit_assignment="same",
        )
        self.fail_step = Steps.objects.create(
            tenant=self.tenant, part_type=self.pt, name="Dc Rework",
            step_type="REWORK", revisit_assignment="same",
        )
        for order, step in enumerate((self.gate, self.pass_step, self.fail_step), start=1):
            ProcessStep.objects.create(process=self.process, step=step, order=order)
        StepEdge.objects.create(
            process=self.process, from_step=self.gate,
            to_step=self.pass_step, edge_type=EdgeType.DEFAULT,
        )
        StepEdge.objects.create(
            process=self.process, from_step=self.gate,
            to_step=self.fail_step, edge_type=EdgeType.ALTERNATE,
        )

        self.wo = WorkOrder.objects.create(
            tenant=self.tenant, ERP_id="WO-DC-1",
            workorder_status=WorkOrderStatus.IN_PROGRESS, quantity=1,
            process=self.process,
        )
        self.part = Parts.objects.create(
            tenant=self.tenant, ERP_id="P-DC-1", part_type=self.pt,
            work_order=self.wo, step=self.gate,
        )
        StepExecution.objects.create(
            tenant=self.tenant, part=self.part, step=self.gate, visit_number=1,
            status="IN_PROGRESS", assigned_to=self.operator,
        )

        self._grant(self.operator, "view_parts", "change_parts",
                    "full_tenant_access", group="dc-ops")
        self._grant(self.lead, "view_parts", "change_parts",
                    "resolve_step_decision", "full_tenant_access", group="dc-leads")
        self._grant(self.bystander, "view_parts", "full_tenant_access",
                    group="dc-bys")

        # Both throttle tiers; targeted deletes only, never cache.clear().
        self._keys = {
            f"{prefix}:{self.tenant.id}:{email}"
            for prefix in ("decision_cosign_fail", "second_person_fail")
            for email in ("lead@dc.test", "by@dc.test", "op@dc.test")
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

    def _resolve(self, actor, decision="ALTERNATE", **body):
        return self._client(actor).post(
            f"/api/Parts/{self.part.id}/resolve_decision/",
            {"decision": decision, **body}, format="json")

    def _cosign(self):
        return {"cosign_email": "lead@dc.test", "cosign_password": "leadpass"}

    # -- the OR, and that it isn't a weakening ------------------------------

    def test_lead_resolves_with_no_credentials(self):
        """The pre-existing path is untouched."""
        resp = self._resolve(self.lead)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.fail_step.id)

    def test_operator_with_no_credentials_is_refused(self):
        resp = self._resolve(self.operator)
        self.assertEqual(resp.status_code, 403, resp.content)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.gate.id,
                         'a refused resolution must not route the part')

    def test_operator_with_lead_cosign_succeeds(self):
        resp = self._resolve(self.operator, **self._cosign())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.fail_step.id)

    def test_cosigner_lacking_the_permission_is_refused(self):
        resp = self._resolve(
            self.operator,
            cosign_email="by@dc.test", cosign_password="bypass",
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data.get("code"), "cosign_not_permitted")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.gate.id)

    def test_cosigner_with_a_wrong_password_is_refused(self):
        resp = self._resolve(
            self.operator,
            cosign_email="lead@dc.test", cosign_password="nope",
        )
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data.get("code"), "cosign_auth_failed")
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.gate.id)

    def test_lead_cannot_cosign_for_themselves(self):
        """A second person must actually be a second person. The lead holds the
        perm so they never reach this — the check bites when a *cosigner* names
        the caller, which is what a shared-terminal replay attack looks like."""
        resp = self._client(self.bystander).post(
            f"/api/Parts/{self.part.id}/resolve_decision/",
            {"decision": "ALTERNATE",
             "cosign_email": "by@dc.test", "cosign_password": "bypass"},
            format="json")
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.data.get("code"), "cosign_self")

    # -- authority vs. labor ------------------------------------------------

    def test_transition_log_names_the_lead_who_authorized_it(self):
        self._resolve(self.operator, **self._cosign())
        log = StepTransitionLog.objects.filter(
            part=self.part, step=self.fail_step).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.operator_id, self.lead.id,
                         'the routing choice belongs to whoever authorized it')

    def test_next_step_stays_assigned_to_the_operator(self):
        """The bug this guards against: passing the cosigner as `operator`
        would make `_get_operator_for_step` hand a revisit_assignment='same'
        step to the lead who merely walked past and typed a password."""
        self._resolve(self.operator, **self._cosign())
        se = StepExecution.objects.filter(
            part=self.part, step=self.fail_step).first()
        self.assertIsNotNone(se)
        self.assertEqual(se.assigned_to_id, self.operator.id,
                         'the operator keeps the work they are doing')

    def test_uncosigned_path_attributes_both_to_the_caller(self):
        """`decided_by` defaults to `operator`, so a lead resolving from their
        own terminal behaves exactly as before the change."""
        self._resolve(self.lead)
        log = StepTransitionLog.objects.filter(
            part=self.part, step=self.fail_step).first()
        se = StepExecution.objects.filter(
            part=self.part, step=self.fail_step).first()
        self.assertEqual(log.operator_id, self.lead.id)
        self.assertEqual(se.assigned_to_id, self.lead.id)

    def test_response_echoes_the_authorizer(self):
        resp = self._resolve(self.operator, **self._cosign())
        self.assertEqual(resp.data.get("decided_by"), "Lena Lead")

    # -- the decision itself is unaffected ----------------------------------

    def test_cosigned_default_branch_routes_like_a_leads_own(self):
        resp = self._resolve(self.operator, decision="DEFAULT", **self._cosign())
        self.assertEqual(resp.status_code, 200, resp.content)
        self.part.refresh_from_db()
        self.assertEqual(self.part.step_id, self.pass_step.id)

    def test_bad_decision_value_is_rejected_before_the_throttle(self):
        """Ordering matters: a typo'd branch name must not consume a co-sign
        attempt, or a fat-fingered operator locks the lead out of the tenant."""
        resp = self._resolve(
            self.operator, decision="SIDEWAYS",
            cosign_email="lead@dc.test", cosign_password="nope",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIsNone(
            cache.get(f"decision_cosign_fail:{self.tenant.id}:lead@dc.test"),
            'validation runs before verification, so no attempt was counted')
